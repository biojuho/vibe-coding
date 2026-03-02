"""
Shorts 일일 자동 생성 스크립트.

매일 스케줄러가 호출 → 채널당 pending 1개씩 선택 → v2 파이프라인 순차 실행.

Usage:
    python execution/shorts_daily_runner.py              # 채널당 1편
    python execution/shorts_daily_runner.py --per-ch 2   # 채널당 2편
    python execution/shorts_daily_runner.py --dry-run    # 실제 실행 없이 선택만 확인
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Windows cp949 인코딩 문제 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
_V2_DIR = _ROOT / "shorts-maker-v2"
_CONFIG_PATH = _V2_DIR / "config.yaml"

sys.path.insert(0, str(_ROOT))

from execution.content_db import get_all, get_channels, init_db, update_job  # noqa: E402

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
RUN_TIMEOUT_SEC = 600  # 1편당 최대 10분
STALE_HOURS = 2        # 이 시간 이상 running이면 stale 처리


def _recover_stale_jobs() -> int:
    """2시간 이상 running 상태인 항목을 failed로 전환."""
    cutoff = datetime.now() - timedelta(hours=STALE_HOURS)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    for item in get_all():
        if item["status"] == "running" and (item.get("updated_at", "") < cutoff_str):
            update_job(item["id"], status="failed", notes="stale running → auto-failed")
            count += 1
    return count


def pick_topics(limit_per_channel: int = 1) -> list[dict]:
    """채널당 가장 오래된 pending 항목을 limit_per_channel개 선택."""
    channels = get_channels()
    if not channels:
        return []

    selected: list[dict] = []
    for ch in channels:
        items = get_all(channel=ch)
        # get_all은 created_at DESC → pending 중 가장 오래된 것 = 리스트 끝
        pending = [i for i in items if i["status"] == "pending"]
        pending.reverse()  # 오래된 순
        selected.extend(pending[:limit_per_channel])
    return selected


def _find_latest_manifest(output_dir: Path, after_ts: datetime) -> dict | None:
    """output_dir에서 after_ts 이후에 생성된 가장 최근 manifest를 찾는다."""
    candidates = sorted(output_dir.glob("*_manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for mf in candidates:
        if datetime.fromtimestamp(mf.stat().st_mtime) > after_ts:
            try:
                return json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


def run_one(item: dict) -> dict:
    """v2 파이프라인 1건 실행 (blocking). 결과 dict 반환."""
    item_id = item["id"]
    topic = item["topic"]
    channel = item.get("channel", "")

    update_job(item_id, status="running")
    before = datetime.now()

    cmd = [
        sys.executable, "-m", "shorts_maker_v2",
        "run",
        "--topic", topic,
        "--config", str(_CONFIG_PATH),
    ]
    if channel:
        cmd.extend(["--channel", channel])

    try:
        result = subprocess.run(
            cmd,
            cwd=str(_V2_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RUN_TIMEOUT_SEC,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        update_job(item_id, status="failed", notes=f"timeout ({RUN_TIMEOUT_SEC}s)")
        return {"id": item_id, "channel": channel, "topic": topic, "status": "failed", "reason": "timeout"}
    except Exception as exc:
        update_job(item_id, status="failed", notes=str(exc))
        return {"id": item_id, "channel": channel, "topic": topic, "status": "failed", "reason": str(exc)}

    # manifest 스캔
    output_dir = _V2_DIR / "output"
    manifest = _find_latest_manifest(output_dir, before)

    if manifest and manifest.get("status") == "success":
        update_job(
            item_id,
            status="success",
            job_id=manifest.get("job_id", ""),
            title=manifest.get("title", ""),
            video_path=manifest.get("output_path", ""),
            thumbnail_path=manifest.get("thumbnail_path", ""),
            cost_usd=manifest.get("estimated_cost_usd", 0.0),
            duration_sec=manifest.get("total_duration_sec", 0.0),
        )
        return {
            "id": item_id, "channel": channel, "topic": topic,
            "status": "success",
            "cost": manifest.get("estimated_cost_usd", 0),
            "duration": manifest.get("total_duration_sec", 0),
        }

    # 실패
    reason = "exit_code=" + str(exit_code)
    if manifest and manifest.get("failed_steps"):
        reason = "; ".join(f['step'] + ": " + f['message'] for f in manifest["failed_steps"])
    update_job(item_id, status="failed", notes=reason[:500])
    return {"id": item_id, "channel": channel, "topic": topic, "status": "failed", "reason": reason[:200]}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Shorts 일일 자동 생성")
    parser.add_argument("--per-ch", type=int, default=1, help="채널당 생성 수 (기본: 1)")
    parser.add_argument("--dry-run", action="store_true", help="실제 실행 없이 선택만 확인")
    args = parser.parse_args()

    load_dotenv(_ROOT / ".env")
    load_dotenv(_V2_DIR / ".env", override=False)
    init_db()

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Shorts Daily Runner 시작")
    print(f"  채널당: {args.per_ch}편 | dry-run: {args.dry_run}")

    # stale 복구
    stale = _recover_stale_jobs()
    if stale:
        print(f"  stale running {stale}건 → failed 전환")

    # 대상 선택
    topics = pick_topics(limit_per_channel=args.per_ch)
    if not topics:
        print("  대기 중인 주제가 없습니다. 종료.")
        return 0

    print(f"  선택된 주제: {len(topics)}건")
    for t in topics:
        print(f"    [{t.get('channel','')}] {t['topic']}")

    if args.dry_run:
        print("  (dry-run 모드 — 실행 건너뜀)")
        return 0

    # 순차 실행
    results: list[dict] = []
    for i, item in enumerate(topics, 1):
        print(f"\n--- [{i}/{len(topics)}] {item.get('channel','')} | {item['topic']} ---")
        result = run_one(item)
        results.append(result)
        status = result["status"]
        if status == "success":
            print(f"  -> 성공 | 비용: ${result.get('cost', 0):.3f} | 길이: {result.get('duration', 0):.1f}s")
        else:
            print(f"  -> 실패 | {result.get('reason', '')[:100]}")

    # 요약
    success = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - success
    total_cost = sum(r.get("cost", 0) for r in results)
    print(f"\n=== 완료: 성공 {success} / 실패 {failed} / 비용 ${total_cost:.3f} ===")

    # 주제 자동 보충
    try:
        import logging as _logging
        from execution.topic_auto_generator import check_and_replenish
        print("\n[주제 보충 체크]")
        check_and_replenish()
    except Exception as exc:
        _logging.getLogger(__name__).warning("주제 보충 실패 (무시): %s", exc)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
