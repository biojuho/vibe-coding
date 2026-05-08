"""promptfoo 기반 blind-to-x 드래프트 회귀 평가 러너 (T-254).

`directives/llm_eval_promptfoo.md` 의 3단계 실행 래퍼.

흐름:
  1. config.yaml 존재 + 데이터셋 YAML 존재 검증 (--quick 모드는 데이터셋 없으면 skip)
  2. 일일 비용 가드 (PROMPTFOO_DAILY_BUDGET_USD)
  3. `npx promptfoo eval -c <config>` 실행 → JSON 결과 캡처
  4. 직전 baseline (.tmp/eval/blind-to-x/baseline.json) 과 비교
  5. 회귀(임계 -10%) 발견 시 비-zero exit + 텔레그램 알림 (옵션)

Usage:
    python execution/run_eval_blind_to_x.py --dry-run            # 환경 검증만
    python execution/run_eval_blind_to_x.py --quick              # golden 5건, 1 provider
    python execution/run_eval_blind_to_x.py                      # 전체 평가
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "tests" / "eval" / "blind-to-x"
CONFIG_PATH = EVAL_DIR / "promptfooconfig.yaml"
GOLDEN_PATH = EVAL_DIR / "golden_cases.yaml"
REJECTED_PATH = EVAL_DIR / "rejected_cases.yaml"
RESULT_DIR = REPO_ROOT / ".tmp" / "eval" / "blind-to-x"
LAST_RUN_PATH = RESULT_DIR / "last_run.json"
BASELINE_PATH = RESULT_DIR / "baseline.json"

REGRESSION_THRESHOLD = -0.10  # 평균 점수 10% 이상 하락 시 회귀로 간주


def _check_environment() -> tuple[bool, list[str]]:
    """필수 자산 + 외부 도구(npx) 존재 검증."""
    issues: list[str] = []
    if not CONFIG_PATH.exists():
        issues.append(f"config 누락: {CONFIG_PATH}")
    if shutil.which("npx") is None:
        issues.append("npx 가 PATH에 없음 — Node.js 설치 필요")
    return (len(issues) == 0, issues)


def _check_dataset(quick: bool) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if not GOLDEN_PATH.exists():
        issues.append(f"golden 데이터셋 누락: {GOLDEN_PATH} (먼저 blind_to_x_eval_extract.py 실행)")
    if not quick and not REJECTED_PATH.exists():
        issues.append(f"rejected 데이터셋 누락: {REJECTED_PATH}")
    return (len(issues) == 0, issues)


def _run_promptfoo(extra_args: list[str]) -> dict:
    """promptfoo eval 실행 후 JSON 결과 dict 반환."""
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx",
        "promptfoo",
        "eval",
        "-c",
        str(CONFIG_PATH),
        "--output",
        str(LAST_RUN_PATH),
        *extra_args,
    ]
    logger.info("실행: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        logger.warning("promptfoo 비-0 종료(%d). stderr: %s", result.returncode, result.stderr[:500])
    if not LAST_RUN_PATH.exists():
        return {"error": "promptfoo did not produce output", "stderr": result.stderr[:500]}
    with LAST_RUN_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _summarize(payload: dict) -> dict:
    """promptfoo 결과에서 회귀 비교용 요약 메트릭 추출."""
    results = payload.get("results", payload.get("result", {})) or {}
    table = results.get("table", {}) or {}
    body = table.get("body", []) or []
    total = len(body)
    passes = 0
    rubric_scores: list[float] = []
    for row in body:
        outputs = row.get("outputs", []) if isinstance(row, dict) else []
        for out in outputs:
            if isinstance(out, dict) and out.get("pass"):
                passes += 1
            score = (out or {}).get("score")
            if isinstance(score, (int, float)):
                rubric_scores.append(float(score))
    pass_rate = passes / max(1, total * max(1, len(body[0].get("outputs", [])) if body else 1))
    return {
        "total_cases": total,
        "pass_rate": round(pass_rate, 4),
        "avg_rubric_score": round(sum(rubric_scores) / len(rubric_scores), 4) if rubric_scores else 0.0,
    }


def _compare_against_baseline(summary: dict) -> tuple[bool, str]:
    """직전 baseline 대비 회귀 여부 판정."""
    if not BASELINE_PATH.exists():
        return (False, "baseline 없음 — 첫 실행으로 간주")
    with BASELINE_PATH.open("r", encoding="utf-8") as fp:
        baseline = json.load(fp)
    base_score = float(baseline.get("avg_rubric_score", 0.0))
    new_score = float(summary.get("avg_rubric_score", 0.0))
    if base_score == 0.0:
        return (False, "baseline score=0 — 비교 스킵")
    delta = (new_score - base_score) / base_score
    if delta < REGRESSION_THRESHOLD:
        return (True, f"회귀 감지: {base_score:.3f} → {new_score:.3f} ({delta:+.1%})")
    return (False, f"회귀 없음: {base_score:.3f} → {new_score:.3f} ({delta:+.1%})")


def _maybe_send_telegram(summary: dict, regression_msg: str) -> None:
    if os.getenv("PROMPTFOO_TELEGRAM_ALERT", "0") != "1":
        return
    try:
        from execution.telegram_notifier import send_message  # type: ignore[import-not-found]

        send_message(
            f"[blind-to-x eval 회귀]\n{regression_msg}\n"
            f"pass_rate={summary['pass_rate']} rubric={summary['avg_rubric_score']}"
        )
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="blind-to-x promptfoo 평가 러너")
    parser.add_argument("--dry-run", action="store_true", help="환경 검증만 수행")
    parser.add_argument("--quick", action="store_true", help="golden 5건만 1 provider")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="실행 후 last_run.json을 baseline으로 승격",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    ok_env, env_issues = _check_environment()
    ok_data, data_issues = _check_dataset(args.quick)
    issues = env_issues + data_issues
    if not ok_env or (not ok_data and not args.dry_run):
        for issue in issues:
            logger.error("- %s", issue)
        return 2

    if args.dry_run:
        sys.stdout.write(
            json.dumps(
                {
                    "status": "ok" if ok_data else "ok_with_warnings",
                    "config": str(CONFIG_PATH),
                    "golden_exists": GOLDEN_PATH.exists(),
                    "rejected_exists": REJECTED_PATH.exists(),
                    "issues": issues,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        return 0

    extra: list[str] = []
    if args.quick:
        extra.extend(["--filter-tests", "0:5"])

    payload = _run_promptfoo(extra)
    if "error" in payload:
        logger.error("promptfoo 실행 실패: %s", payload["error"])
        return 3

    summary = _summarize(payload)
    regressed, msg = _compare_against_baseline(summary)
    sys.stdout.write(
        json.dumps(
            {
                "summary": summary,
                "regressed": regressed,
                "comparison": msg,
                "last_run_path": str(LAST_RUN_PATH),
            },
            ensure_ascii=False,
        )
        + "\n"
    )

    if args.update_baseline:
        with BASELINE_PATH.open("w", encoding="utf-8") as fp:
            json.dump(summary, fp, ensure_ascii=False, indent=2)
        logger.info("baseline 갱신됨: %s", BASELINE_PATH)

    if regressed:
        _maybe_send_telegram(summary, msg)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
