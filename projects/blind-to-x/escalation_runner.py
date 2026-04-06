"""바이럴 에스컬레이션 엔진 — 메인 실행기.

main.py와 독립적으로 실행되는 경량 데몬(또는 Task Scheduler 5분 간격 실행).
SpikeDetector → EscalationQueue → ExpressDraft → 텔레그램 알림 까지의
전체 파이프라인을 하나의 루프로 오케스트레이션한다.

Usage:
    # 1회 스캔 (Task Scheduler용)
    python escalation_runner.py --once

    # 상시 모니터링 (데몬 모드, 5분 간격)
    python escalation_runner.py --daemon --interval 300

    # 드라이런 (알림 없이 감지만)
    python escalation_runner.py --once --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# UTF-8 강제
if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# 프로젝트 루트를 sys.path에 추가 (blind-to-x root)
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Workspace 경로를 sys.path에 추가 (execution.telegram_notifier 모듈용)
_WORKSPACE_ROOT = _PROJECT_ROOT.parent.parent / "workspace"
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

from config import ConfigManager, load_env, setup_logging

logger = logging.getLogger("escalation_runner")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Blind-to-X Viral Escalation Engine")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--once", action="store_true", help="1회 스캔 후 종료")
    parser.add_argument("--daemon", action="store_true", help="상시 모니터링 모드")
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="스캔 간격 (초, 기본 300=5분)",
    )
    parser.add_argument("--dry-run", action="store_true", help="알림 없이 감지만")
    return parser


async def _run_cycle(
    config_mgr,
    dry_run: bool = False,
) -> int:
    """1회 에스컬레이션 사이클 실행.

    Returns:
        처리된 스파이크 이벤트 수.
    """
    from pipeline.spike_detector import SpikeDetector
    from pipeline.escalation_queue import EscalationQueue, EventStatus
    from pipeline.express_draft import ExpressDraftPipeline

    # ── 1단계: 스파이크 감지 ─────────────────────────────────────────
    detector = SpikeDetector(config_mgr)
    spikes = await detector.scan()

    if not spikes:
        logger.debug("이번 사이클: 스파이크 없음")
        return 0

    logger.info("🔥 %d건 스파이크 감지됨", len(spikes))

    # ── 2단계: 큐 등록 ───────────────────────────────────────────────
    queue = EscalationQueue()
    enqueued_count = 0
    for spike in spikes:
        event_id = queue.enqueue(spike)
        if event_id is not None:
            enqueued_count += 1

    if enqueued_count == 0:
        logger.info("전부 중복 또는 용량 초과 → 스킵")
        return 0

    logger.info("큐에 %d건 등록", enqueued_count)

    # ── 3단계: 급행 초안 생성 ────────────────────────────────────────
    pipeline = ExpressDraftPipeline(config_mgr)
    pending_events = queue.dequeue_pending(limit=3)  # 최대 3건 동시 처리

    processed = 0
    for event in pending_events:
        logger.info(
            "초안 생성 시작: #%d [%s] %s",
            event.id,
            event.source,
            event.title[:40],
        )

        result = await pipeline.generate(
            title=event.title,
            content_preview="",  # TODO: 큐에서 content_preview 가져오기
            source=event.source,
            velocity_score=event.velocity_score,
        )

        if result.success:
            queue.update_status(
                event.id,
                EventStatus.AWAITING_APPROVAL,
                draft_x=result.draft_x,
                draft_threads=result.draft_threads,
            )
            processed += 1

            # ── 4단계: 텔레그램 알림 ─────────────────────────────────
            if not dry_run:
                await _send_surge_notification(
                    config_mgr,
                    event,
                    result,
                )
            else:
                logger.info(
                    "[DRY-RUN] 알림 건너뜀: #%d — X초안: %s...",
                    event.id,
                    result.draft_x[:60],
                )
        else:
            queue.update_status(event.id, EventStatus.EXPIRED)
            logger.warning(
                "초안 생성 실패: #%d — %s",
                event.id,
                result.error,
            )

    # ── 통계 출력 ────────────────────────────────────────────────────
    stats = queue.get_stats()
    logger.info(
        "사이클 완료: 감지=%d, 등록=%d, 초안=%d | 큐: %s",
        len(spikes),
        enqueued_count,
        processed,
        stats,
    )
    return processed


async def _send_surge_notification(
    config_mgr,
    event,
    draft_result,
) -> None:
    """텔레그램으로 Surge 알림 전송.

    TODO: inline keyboard 버튼으로 1-click 승인 구현 (Phase 2).
    """
    try:
        from pipeline.notification import NotificationManager

        notifier = NotificationManager(config_mgr)
        await notifier.send_surge_alert(
            event=event,
            draft_x=draft_result.draft_x,
            draft_threads=draft_result.draft_threads,
            generation_time=draft_result.generation_time_sec,
        )
    except Exception as exc:
        logger.error("텔레그램 알림 실패: %s", exc)


async def _process_callback(query: dict, queue) -> None:
    """텔레그램 callback_query 처리."""
    from execution.telegram_notifier import answer_callback_query, edit_message_reply_markup
    from pipeline.escalation_queue import EventStatus

    cb_id = query.get("id")
    data = query.get("data", "")
    message = query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if not cb_id:
        return

    loop = asyncio.get_running_loop()

    # "approve_123" / "reject_url"
    if data.startswith("approve_") or data.startswith("reject_"):
        action, event_key = data.split("_", 1)

        # 1. DB (또는 메모리)에서 event 찾기
        # queue.get_event or queue.update_status
        # EventStatus: APPROVED / REJECTED
        new_status = EventStatus.APPROVED if action == "approve" else EventStatus.REJECTED

        try:
            event_id_int = int(event_key)
            event_obj = queue.get_event(event_id_int)
        except ValueError:
            event_obj = None

        if event_obj:
            queue.update_status(event_obj.id, new_status)
            text = "✅ 발행이 승인되었습니다!" if action == "approve" else "❌ 발행이 거부되었습니다."
        else:
            text = "⚠️ 이벤트를 찾을 수 없습니다."

        try:
            await loop.run_in_executor(None, lambda: answer_callback_query(cb_id, text=text))
        except Exception as e:
            logger.error("Callback answer 실패: %s", e)

        if chat_id and message_id:
            try:
                # Remove inline keyboard
                await loop.run_in_executor(None, lambda: edit_message_reply_markup(chat_id, message_id, None))
            except Exception as e:
                logger.error("Markup 초기화 실패: %s", e)


async def _poll_and_wait(interval: int, config_mgr, dry_run: bool) -> None:
    from execution.telegram_notifier import get_updates
    from pipeline.escalation_queue import EscalationQueue

    # TELEGRAM_API_BASE가 로드되는지 확인하여 설정 안된 환경이면 구버전처럼 sleep
    try:
        from execution.telegram_notifier import is_configured

        if not is_configured():
            await asyncio.sleep(interval)
            return
    except ImportError:
        await asyncio.sleep(interval)
        return

    queue = EscalationQueue()
    start_time = time.monotonic()
    offset = None
    loop = asyncio.get_running_loop()

    while time.monotonic() - start_time < interval:
        try:
            updates = await loop.run_in_executor(None, lambda: get_updates(limit=10, timeout=10, offset=offset))
            for update in updates:
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    await _process_callback(update["callback_query"], queue)

        except Exception as e:
            logger.debug("텔레그램 폴링 에러 (패스): %s", e)
            await asyncio.sleep(2)

        # 남은 시간 정산
        elapsed = time.monotonic() - start_time
        if interval - elapsed > 10:
            await asyncio.sleep(1)  # 부하 조절
        else:
            await asyncio.sleep(max(0.1, interval - elapsed))
            break


async def _daemon_loop(config_mgr, interval: int, dry_run: bool) -> None:
    """상시 모니터링 루프."""
    logger.info("에스컬레이션 데몬 시작 (간격: %d초, dry_run: %s)", interval, dry_run)
    while True:
        try:
            await _run_cycle(config_mgr, dry_run=dry_run)
        except KeyboardInterrupt:
            logger.info("에스컬레이션 데몬 종료 (KeyboardInterrupt)")
            break
        except Exception as exc:
            logger.error("사이클 에러 (계속 실행): %s", exc)

        logger.debug("다음 스캔까지 %d초 대기 & 텔레그램 콜백 모니터링...", interval)
        try:
            await _poll_and_wait(interval, config_mgr, dry_run=dry_run)
        except KeyboardInterrupt:
            logger.info("에스컬레이션 데몬 종료 (KeyboardInterrupt)")
            break


async def main():
    parser = _build_parser()
    args = parser.parse_args()

    try:
        config_mgr = ConfigManager(args.config)
    except Exception:
        logger.warning("Config 로드 실패. 빈 config 사용.")
        config_mgr = ConfigManager("nonexistent")
        config_mgr.config = {}

    if args.daemon:
        await _daemon_loop(config_mgr, args.interval, args.dry_run)
    else:
        # 기본: 1회 실행
        count = await _run_cycle(config_mgr, dry_run=args.dry_run)
        if count > 0:
            print(f"\n✅ {count}건의 Surge 이벤트 처리 완료")
        else:
            print("\n😴 현재 트렌딩 스파이크 없음")


if __name__ == "__main__":
    load_env()
    setup_logging()
    asyncio.run(main())
