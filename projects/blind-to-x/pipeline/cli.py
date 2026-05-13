"""Command Line Interface and orchestration."""

import argparse
import logging
import os
from pathlib import Path
import sys
import time

from config import ConfigManager
from pipeline import NotificationManager, NotionUploader, TwitterPoster
from pipeline.bootstrap import init_scrapers, check_budget, init_components
from pipeline.runner import execute_pipeline, handle_single_commands

logger = logging.getLogger(__name__)

_LOCK_FILE = Path(".tmp/.running.lock")
_LOCK_MAX_AGE_SECONDS = 3600  # 1시간 초과 lock은 stale로 간주


def build_parser():
    parser = argparse.ArgumentParser(description="Blind to X Automation Pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--urls", nargs="+", help="Specific URLs to process")
    parser.add_argument("--trending", action="store_true", help="Fetch trending posts automatically")
    parser.add_argument("--popular", action="store_true", help="Fetch popular posts automatically")
    parser.add_argument("--limit", type=int, help="Limit number of posts (default from config)")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and generate drafts without uploading")
    parser.add_argument(
        "--parallel", type=int, default=3, metavar="N", help="Process up to N posts concurrently (default: 3)"
    )
    parser.add_argument(
        "--source",
        default="auto",
        help="Source scraper to use. Use 'auto' for configured primary/input_sources, or 'multi' for all input_sources.",
    )
    parser.add_argument("--review-only", action="store_true", help="Queue items for review without publishing")
    parser.add_argument("--reprocess-approved", action="store_true", help="Publish approved Notion items only")
    parser.add_argument(
        "--newsletter-build", action="store_true", help="Build newsletter edition from approved Notion items"
    )
    parser.add_argument(
        "--newsletter-preview", action="store_true", help="Preview newsletter edition without publishing"
    )
    parser.add_argument("--digest", action="store_true", help="Generate and send daily digest")
    parser.add_argument("--digest-date", type=str, default=None, help="Digest date (YYYY-MM-DD, default: today)")
    parser.add_argument("--sentiment-report", action="store_true", help="Show current emotion trends")
    return parser


def _is_process_alive(pid: int) -> bool:
    """Windows/Unix 호환 프로세스 생존 확인."""
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True  # Windows
    except (OSError, ValueError):
        return False


def acquire_lock() -> bool:
    """Acquire the run lock. Returns True if lock acquired, False if already running."""
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOCK_FILE.exists():
        try:
            lock_content = _LOCK_FILE.read_text().strip()
            parts = lock_content.split(":", 1)
            pid = int(parts[0])
            lock_ts = float(parts[1]) if len(parts) > 1 else 0.0
            lock_age = time.time() - lock_ts if lock_ts else float("inf")

            if lock_age > _LOCK_MAX_AGE_SECONDS:
                logger.warning("Stale lock 감지 (%.0f초 경과, PID=%s). 덮어씁니다.", lock_age, pid)
            elif _is_process_alive(pid):
                logger.warning("이미 실행 중인 프로세스가 있습니다 (PID=%s). 종료합니다.", pid)
                return False
            else:
                logger.info("프로세스 %s 종료됨. Stale lock 제거.", pid)
        except (ValueError, IndexError):
            pass
    _LOCK_FILE.write_text(f"{os.getpid()}:{time.time()}")
    return True


async def run_main():
    parser = build_parser()
    args = parser.parse_args()

    if not acquire_lock():
        return

    try:
        config_mgr = ConfigManager(args.config)
    except Exception:
        logger.warning("Could not load %s. Using empty config.", args.config)
        config_mgr = ConfigManager("nonexistent")
        config_mgr.config = {}

    notifier = NotificationManager(config_mgr)
    notion_uploader = NotionUploader(config_mgr)
    twitter_poster = TwitterPoster(config_mgr)

    # ── Harness preflight security check ─────────────────────────────────
    try:
        from pipeline.harness_guard import run_preflight, is_harness_enabled

        if is_harness_enabled():
            preflight_result = run_preflight()
            if not preflight_result["passed"]:
                logger.error("Harness preflight failed. Aborting pipeline.")
                await notifier.send_message(
                    f"Blind-to-X harness preflight FAILED\nIssues: {len(preflight_result['issues'])}건",
                    level="CRITICAL",
                )
                sys.exit(1)
            elif not preflight_result["skipped"]:
                logger.info("Harness preflight passed.")
    except Exception as exc:
        logger.warning("Harness preflight check error (non-fatal): %s", exc)

    if await handle_single_commands(args, config_mgr, notifier, notion_uploader, twitter_poster):
        return

    scrapers = init_scrapers(config_mgr, args)
    if not scrapers:
        logger.error("No valid scrapers found.")
        sys.exit(1)

    cost_tracker = await check_budget(config_mgr, notifier)
    image_uploader, image_generator, draft_generator, top_examples, trend_monitor = await init_components(
        args, config_mgr, scrapers, notion_uploader, cost_tracker
    )

    try:
        await execute_pipeline(
            args,
            config_mgr,
            scrapers,
            notifier,
            notion_uploader,
            twitter_poster,
            image_uploader,
            image_generator,
            draft_generator,
            top_examples,
            trend_monitor,
        )
    except Exception as exc:
        logger.exception("Critical error in main: %s", exc)
        await notifier.send_message(f"Blind-to-X pipeline crash\nError: `{exc}`", level="CRITICAL")
        sys.exit(1)
    finally:
        _LOCK_FILE.unlink(missing_ok=True)
