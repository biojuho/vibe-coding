"""Best-of-N comment-weight 튜닝 (dry-run 분석).

최근 발행된 draft_analytics 로우의 실제 engagement_rate 와 각 점수 축의 상관관계를
계산해 llm.best_of_n_comment_weight 의 적정값을 추천한다. **config 를 수정하지 않으며**
표준출력에 보고만 한다 (opt-in).

분석 단계:
1. 축별 Pearson 상관계수: hook/virality/fit/final_rank ↔ engagement_rate.
2. (가능할 때) Comment-trigger 가중치 sweep: w∈{0.0..1.0}에서
   combined = avg_score*(1-w) + comment_trigger_avg*w 의 engagement_rate 대비
   Pearson r 을 계산해 최적 w 를 보고.
3. 데이터 부족 시 "수집 후 재실행" 메시지로 종료 (exit 0).

사용:
    python scripts/tune_best_of_n_weight.py [--days 30] [--min-samples 10]
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_BTX_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB_PATH = _BTX_ROOT / ".tmp" / "btx_costs.db"


def _select_column(existing_cols: set[str], name: str) -> str:
    return name if name in existing_cols else f"NULL AS {name}"


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson 상관계수. 데이터가 부족하거나 분산이 0이면 None."""
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den_x = sum((xs[i] - mean_x) ** 2 for i in range(n))
    den_y = sum((ys[i] - mean_y) ** 2 for i in range(n))
    if den_x <= 0 or den_y <= 0:
        return None
    return num / ((den_x**0.5) * (den_y**0.5))


def correlate_axis(rows: list[dict], axis_key: str, target_key: str) -> tuple[float | None, int]:
    """단일 축 vs 타깃 메트릭 Pearson r 과 사용된 표본 수를 반환."""
    pairs: list[tuple[float, float]] = []
    for row in rows:
        axis = row.get(axis_key)
        target = row.get(target_key)
        if axis is None or target is None:
            continue
        try:
            axis_value = float(axis)
            target_value = float(target)
        except (TypeError, ValueError):
            continue
        # 둘 다 0 인 케이스는 정보가 없으니 제외
        if axis_value == 0 and target_value == 0:
            continue
        pairs.append((axis_value, target_value))
    if len(pairs) < 2:
        return None, len(pairs)
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    return pearson(xs, ys), len(pairs)


def sweep_comment_weights(
    rows: list[dict],
    *,
    target_key: str = "engagement_rate",
    step: float = 0.1,
) -> tuple[float | None, float | None, int]:
    """avg_score * (1-w) + comment_trigger_avg * w sweep.

    반환: (best_w, best_r, sample_count). best_w 가 None 이면 데이터 부족.
    """
    triples: list[tuple[float, float, float]] = []
    for row in rows:
        avg = row.get("final_rank_score")
        ct_avg = row.get("comment_trigger_avg")
        target = row.get(target_key)
        if avg is None or ct_avg is None or target is None:
            continue
        try:
            avg_value = float(avg)
            ct_value = float(ct_avg)
            target_value = float(target)
        except (TypeError, ValueError):
            continue
        if ct_value <= 0:
            continue
        triples.append((avg_value, ct_value, target_value))
    if len(triples) < 5:
        return None, None, len(triples)
    # step 을 [0,1] 안에서 11개 (또는 step 에 맞게) 후보로
    safe_step = max(0.01, min(0.5, float(step)))
    steps = []
    current = 0.0
    while current <= 1.0 + 1e-9:
        steps.append(round(current, 4))
        current = round(current + safe_step, 4)
    best_w: float | None = None
    best_r: float | None = None
    for w in steps:
        combined = [a * (1 - w) + b * w for a, b, _ in triples]
        targets = [t for _, _, t in triples]
        r = pearson(combined, targets)
        if r is None:
            continue
        if best_r is None or r > best_r:
            best_r = r
            best_w = w
    return best_w, best_r, len(triples)


def load_recent_rows(*, days: int = 30) -> list[dict]:
    """draft_analytics 에서 최근 days 일치 published 로우를 로드.

    comment_trigger_avg 컬럼이 존재하면 그것도 selecte한다 (없으면 None 으로 채움).
    """
    if not _DEFAULT_DB_PATH.exists():
        return []
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows: list[dict] = []
    try:
        with sqlite3.connect(str(_DEFAULT_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            column_info = conn.execute("PRAGMA table_info(draft_analytics)").fetchall()
            existing_cols = {r["name"] for r in column_info}
            if not {"date", "published"}.issubset(existing_cols):
                return []
            sql = (
                "SELECT "
                f"date, {_select_column(existing_cols, 'hook_score')}, "
                f"{_select_column(existing_cols, 'virality_score')}, {_select_column(existing_cols, 'fit_score')}, "
                f"{_select_column(existing_cols, 'final_rank_score')}, "
                f"{_select_column(existing_cols, 'engagement_rate')}, {_select_column(existing_cols, 'yt_views')}, "
                f"{_select_column(existing_cols, 'impression_count')}, published, "
                f"{_select_column(existing_cols, 'comment_trigger_avg')} "
                "  FROM draft_analytics "
                " WHERE date >= ? AND published = 1"
            )
            for record in conn.execute(sql, (cutoff,)).fetchall():
                rows.append(dict(record))
    except Exception as exc:  # pragma: no cover - DB env dependent
        logger.warning("draft_analytics 로드 실패: %s", exc)
        return []
    return rows


def build_report(
    rows: list[dict],
    *,
    days: int,
    min_samples: int,
) -> tuple[str, dict]:
    """텍스트 보고서 + 머신리더블 dict 를 둘 다 반환."""
    summary: dict = {
        "sample_count": len(rows),
        "days": days,
        "min_samples": min_samples,
        "axis_correlations": {},
        "comment_trigger_sweep": None,
        "recommendation": None,
    }

    if len(rows) < min_samples:
        text = (
            f"수집된 published 샘플이 부족합니다 ({len(rows)} < {min_samples}).\n"
            f"최소 {min_samples}건의 published + engagement_rate 데이터가 필요합니다.\n"
            "현재 단계 권장: 기본값 0.5 유지."
        )
        summary["recommendation"] = {
            "weight": 0.5,
            "reason": "insufficient_samples",
            "samples": len(rows),
        }
        return text, summary

    lines: list[str] = []
    lines.append("=== Best-of-N comment-weight tuning (dry-run) ===")
    lines.append(f"기간: 최근 {days}일 / published 샘플: {len(rows)}건")
    lines.append("")
    lines.append("[축별 Pearson r vs engagement_rate]")
    for axis in ("hook_score", "virality_score", "fit_score", "final_rank_score"):
        r, n = correlate_axis(rows, axis, "engagement_rate")
        summary["axis_correlations"][axis] = {"r": r, "n": n}
        if r is None:
            lines.append(f"  - {axis}: 데이터 부족 (n={n})")
        else:
            lines.append(f"  - {axis}: r={r:+.3f} (n={n})")
    lines.append("")

    best_w, best_r, ct_n = sweep_comment_weights(rows, target_key="engagement_rate")
    summary["comment_trigger_sweep"] = {
        "best_w": best_w,
        "best_r": best_r,
        "samples": ct_n,
    }

    lines.append("[Comment-trigger 가중치 sweep]")
    if best_w is None:
        lines.append("  - `comment_trigger_avg` 표본이 5건 미만입니다 (Best-of-N 발행 후 영속화되며, 누적 대기 중).")
        lines.append("  - 현재로서는 final_rank_score 의 engagement_rate 상관관계만 신호로 사용됩니다.")
        # final_rank_score 의 신호에 따라 weight 의 방향 추천
        final_corr = summary["axis_correlations"]["final_rank_score"]["r"]
        if final_corr is None:
            summary["recommendation"] = {
                "weight": 0.5,
                "reason": "no_engagement_signal_yet",
                "samples": len(rows),
            }
            lines.append("권장: 기본값 0.5 유지 (engagement 시그널 불확정).")
        elif final_corr >= 0.3:
            summary["recommendation"] = {
                "weight": 0.4,
                "reason": "final_rank_already_predictive",
                "samples": len(rows),
                "final_rank_r": final_corr,
            }
            lines.append(f"권장: 0.4 — final_rank_score r={final_corr:+.3f} 이미 강해 4축 비중을 살짝 줄여도 안전.")
        elif final_corr <= 0.0:
            summary["recommendation"] = {
                "weight": 0.6,
                "reason": "final_rank_weak_predictor",
                "samples": len(rows),
                "final_rank_r": final_corr,
            }
            lines.append(f"권장: 0.6 — final_rank_score r={final_corr:+.3f} 약함, 4축 비중을 늘려 시그널 다양화.")
        else:
            summary["recommendation"] = {
                "weight": 0.5,
                "reason": "final_rank_moderate",
                "samples": len(rows),
                "final_rank_r": final_corr,
            }
            lines.append(f"권장: 기본 0.5 유지 — final_rank_score r={final_corr:+.3f} 중간.")
    else:
        lines.append(f"  - 사용 표본: {ct_n}건")
        lines.append(f"  - 최적 w = {best_w:.2f} (Pearson r = {best_r:+.3f})")
        lines.append("")
        summary["recommendation"] = {
            "weight": best_w,
            "reason": "sweep_best",
            "samples": ct_n,
            "pearson_r": best_r,
        }
        lines.append(
            f"권장: config.yaml `llm.best_of_n_comment_weight: {best_w:.2f}` (Pearson r={best_r:+.3f}, n={ct_n})"
        )

    return "\n".join(lines), summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--days", type=int, default=30, help="조회 기간(일). 기본 30.")
    parser.add_argument(
        "--min-samples",
        type=int,
        default=10,
        help="권장 계산에 필요한 최소 published 샘플 수. 기본 10.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="머신리더블 JSON 으로 출력 (자동화용).",
    )
    args = parser.parse_args(argv)

    if args.days <= 0:
        print("--days 는 1 이상이어야 합니다.", file=sys.stderr)
        return 2
    if args.min_samples <= 0:
        print("--min-samples 는 1 이상이어야 합니다.", file=sys.stderr)
        return 2

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = load_recent_rows(days=args.days)
    text, summary = build_report(rows, days=args.days, min_samples=args.min_samples)

    if args.json:
        import json

        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    else:
        print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
