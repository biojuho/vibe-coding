"""Main entry point for the Blind-to-X pipeline."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import AsyncExitStack
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
import time

if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from config import ConfigManager, load_env, setup_logging
from pipeline import (
    FeedbackLoop,
    ImageGenerator,
    ImageUploader,
    NotionUploader,
    NotificationManager,
    TweetDraftGenerator,
    TwitterPoster,
    calculate_run_metrics,
    process_single_post,
)
from pipeline.analytics_tracker import AnalyticsTracker
from pipeline.commands import run_digest, run_dry_run_single, run_reprocess_approved, run_sentiment_report
from pipeline.feed_collector import collect_feed_items
from scrapers import get_scraper

logger = logging.getLogger(__name__)

_LOCK_FILE = Path(".tmp/.running.lock")
_LOCK_MAX_AGE_SECONDS = 3600  # 1시간 초과 lock은 stale로 간주


# ── CLI ─────────────────────────────────────────────────────────────────────

def _build_parser():
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
    parser.add_argument("--source", default="blind", help="Source scraper to use")
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


def _resolve_input_sources(config_mgr, args):
    configured_sources = config_mgr.get("input_sources", ["blind"])
    primary_source = config_mgr.get("content_strategy.primary_source", "blind")

    if args.source != "blind":
        return [args.source]

    if primary_source in configured_sources and primary_source != "multi":
        return [primary_source]

    return configured_sources or ["blind"]


async def _load_feedback_examples(config_mgr, notion_uploader):
    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    try:
        return await feedback_loop.get_few_shot_examples()
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Failed to load feedback examples: %s", exc)
        return []


def _is_process_alive(pid: int) -> bool:
    """Windows/Unix 호환 프로세스 생존 확인."""
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True  # Windows: 프로세스 존재하지만 권한 없음 → 살아있다고 판단
    except (OSError, ValueError):
        return False


# ── 실행 루프 ────────────────────────────────────────────────────────────────

async def _run_pipeline(args, config_mgr, scrapers, notifier, notion_uploader,
                        twitter_poster, image_uploader, image_generator,
                        draft_generator, top_examples, trend_monitor):
    """Core pipeline: collect → process → report."""
    async with AsyncExitStack() as stack:
        for scraper in scrapers.values():
            await stack.enter_async_context(scraper)

        urls_to_process, feed_stats = await collect_feed_items(config_mgr, args, scrapers)
        if not urls_to_process:
            logger.info("No valid posts to process.")
            return

        results = []
        start_time = datetime.now()
        output_formats = config_mgr.get("output_formats", ["twitter"])
        effective_review_only = args.review_only or config_mgr.get("content_strategy.require_human_approval", True)

        if args.dry_run or args.parallel <= 1:
            for index, item in enumerate(urls_to_process, start=1):
                print(f"  [{index}/{len(urls_to_process)}] [{item['source']}] {item['url']}")
                if args.dry_run:
                    result = await run_dry_run_single(item, config_mgr, draft_generator, notion_uploader, top_examples)
                else:
                    result = await process_single_post(
                        url=item["url"],
                        scraper=item["scraper"],
                        image_uploader=image_uploader,
                        image_generator=image_generator,
                        draft_generator=draft_generator,
                        notion_uploader=notion_uploader,
                        twitter_poster=twitter_poster,
                        top_tweets=top_examples,
                        source_name=item["source"],
                        output_formats=output_formats,
                        config=config_mgr,
                        feed_mode=item["feed_mode"],
                        review_only=effective_review_only,
                        post_data_hint={"feed_title": item.get("feed_title", "")},
                    )
                results.append(result)
        else:
            semaphore = asyncio.Semaphore(max(1, args.parallel))
            counter = {"done": 0}
            counter_lock = asyncio.Lock()

            async def _bounded(item):
                async with semaphore:
                    async with counter_lock:
                        counter["done"] += 1
                        index = counter["done"]
                    print(f"  [{index}/{len(urls_to_process)}] [{item['source']}] {item['url']}")
                    return await process_single_post(
                        url=item["url"],
                        scraper=item["scraper"],
                        image_uploader=image_uploader,
                        image_generator=image_generator,
                        draft_generator=draft_generator,
                        notion_uploader=notion_uploader,
                        twitter_poster=twitter_poster,
                        top_tweets=top_examples,
                        source_name=item["source"],
                        output_formats=output_formats,
                        config=config_mgr,
                        feed_mode=item["feed_mode"],
                        review_only=effective_review_only,
                        post_data_hint={"feed_title": item.get("feed_title", "")},
                    )

            results = await asyncio.gather(*[_bounded(item) for item in urls_to_process])

        # ── 크로스소스 인사이트 생성 ─────────────────────────────────────
        if not args.dry_run and config_mgr.get("cross_source_insight.enabled", True):
            try:
                from pipeline.cross_source_insight import process_cross_source_insights

                insight_results = await process_cross_source_insights(
                    results=list(results),
                    draft_generator=draft_generator,
                    notion_uploader=notion_uploader,
                    image_uploader=image_uploader,
                    image_generator=image_generator,
                    config=config_mgr,
                    output_formats=output_formats,
                    top_examples=top_examples,
                    trend_monitor=trend_monitor,
                )
                if insight_results:
                    results = list(results) + insight_results
                    logger.info("크로스소스 인사이트 %d건 추가", len(insight_results))
            except Exception as exc:
                logger.warning("크로스소스 인사이트 생성 실패 (무시): %s", exc)

        # ── 트렌드 스파이크 기록 ──────────────────────────────────────────
        if trend_monitor and not args.dry_run:
            try:
                spikes = await trend_monitor.detect_spikes()
                if spikes:
                    from pipeline.cost_db import get_cost_db

                    db = get_cost_db()
                    for spike in spikes[:10]:
                        matched = trend_monitor.match_topic_cluster(spike["keyword"])
                        db.record_trend_spike(
                            keyword=spike["keyword"],
                            source=spike["source"],
                            score=spike["score"],
                            matched_topic=matched or "",
                        )
            except Exception as exc:
                logger.debug("트렌드 스파이크 기록 실패: %s", exc)

        # ── 결과 출력 ─────────────────────────────────────────────────────
        elapsed = (datetime.now() - start_time).total_seconds()
        metrics = calculate_run_metrics(results, dry_run=args.dry_run)
        successful = metrics["successful"]
        failed = metrics["failed"]
        content_dup_skips = len(metrics.get("content_duplicate_skips", []))

        print(f"\n{'=' * 55}")
        print(f"  EXECUTION SUMMARY  ({elapsed:.1f}s)")
        print(f"  Total: {len(results)}  |  OK {len(successful)}  |  FAIL {len(failed)}")
        print(f"  Duplicate Skips: {len(metrics['duplicate_skips'])}")
        print(f"  Content Similarity Skips: {content_dup_skips}")
        print(f"  Low Engagement Skips: {feed_stats['low_engagement_skips']}")
        print(f"  Blacklist Skips: {feed_stats['blacklist_skips']}")
        print(f"  Cross-Source Dedup: {feed_stats['cross_source_dedup_count']}")
        print(f"  Filtered Skips: {len(metrics['filtered_skips'])}")
        print(f"  Avg Quality Score (success): {metrics['avg_quality_score']:.1f}")
        if not args.dry_run:
            print(
                f"  Upload Success Rate: {metrics['upload_success_rate']:.1f}% "
                f"({len(metrics['live_upload_success'])}/{metrics['live_upload_attempts']})"
            )
        print(f"{'=' * 55}")

        if not args.dry_run:
            review_ready = len([item for item in results if item.get("review_status") == "검토필요"])
            level = "INFO"
            if len(failed) > 0:
                level = "WARNING"
            if failed and not successful:
                level = "CRITICAL"

            await notifier.send_message(
                "Blind-to-X 실행 완료\n"
                f"수집 {len(results)}건 / 성공 {len(successful)}건 / 실패 {len(failed)}건\n"
                f"검토필요 {review_ready}건 / 평균 품질점수 {metrics['avg_quality_score']:.1f}",
                level=level,
            )

        if failed and not successful:
            error_reasons = "; ".join([str(f.get("error", "unknown")) for f in failed])
            logger.error(f"Exit 1: All {len(failed)} items failed. Reasons: {error_reasons}")
            sys.exit(1)

        # Auto-send daily digest if configured
        if config_mgr.get("digest.enabled", False) and config_mgr.get("digest.telegram_enabled", False):
            try:
                from pipeline.daily_digest import generate_and_send

                await generate_and_send(config_mgr, notion_uploader=notion_uploader)
            except Exception as _dg_exc:
                logger.debug("Auto digest skipped: %s", _dg_exc)


# ── 진입점 ───────────────────────────────────────────────────────────────────

async def main():
    parser = _build_parser()
    args = parser.parse_args()

    # ── 중복 실행 가드 ──────────────────────────────────────────────────────
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
                return
            else:
                logger.info("프로세스 %s 종료됨. Stale lock 제거.", pid)
        except (ValueError, IndexError):
            pass  # 잘못된 lock 파일 → 덮어쓰기
    _LOCK_FILE.write_text(f"{os.getpid()}:{time.time()}")

    try:
        config_mgr = ConfigManager(args.config)
    except Exception:
        logger.warning("Could not load %s. Using empty config.", args.config)
        config_mgr = ConfigManager("nonexistent")
        config_mgr.config = {}

    notifier = NotificationManager(config_mgr)
    notion_uploader = NotionUploader(config_mgr)
    twitter_poster = TwitterPoster(config_mgr)

    # ── 1회성 커맨드 처리 ────────────────────────────────────────────────────
    if args.reprocess_approved:
        results = await run_reprocess_approved(
            config_mgr,
            notion_uploader,
            twitter_poster,
            limit=args.limit or config_mgr.get("review.queue_limit_per_run", 10),
        )
        success_count = len([item for item in results if item.get("success")])
        fail_count = len(results) - success_count
        if results:
            logger.info("Approved reprocess completed. success=%s fail=%s", success_count, fail_count)
        if fail_count:
            await notifier.send_message(f"Blind-to-X 승인 재발행 완료\n성공 {success_count}건 / 실패 {fail_count}건")
        return

    if getattr(args, "digest", False):
        await run_digest(config_mgr, notion_uploader, date=args.digest_date)
        return

    if getattr(args, "sentiment_report", False):
        run_sentiment_report()
        return

    # ── 스크래퍼 초기화 ──────────────────────────────────────────────────────
    input_sources = _resolve_input_sources(config_mgr, args)
    scrapers = {}
    for source in input_sources:
        try:
            scrapers[source] = get_scraper(source)(config_mgr)
        except Exception as exc:
            logger.warning("Could not init scraper %s: %s", source, exc)

    if not scrapers:
        logger.error("No valid scrapers found.")
        sys.exit(1)

    # ── 예산 초과 가드 ────────────────────────────────────────────────────────
    from pipeline.cost_tracker import CostTracker

    cost_tracker = CostTracker(config_mgr)
    if cost_tracker.is_budget_exceeded():
        logger.error(
            "Daily API budget exceeded: $%.3f >= $%.3f",
            cost_tracker.current_cost,
            cost_tracker.daily_budget,
        )
        await notifier.send_message(
            f"Blind-to-X budget exceeded\nCurrent Cost: ${cost_tracker.current_cost:.3f} / Limit: ${cost_tracker.daily_budget:.3f}",
            level="CRITICAL",
        )
        sys.exit(1)

    image_uploader = ImageUploader(config_mgr)
    image_generator = None if args.dry_run else ImageGenerator(config_mgr, cost_tracker=cost_tracker)
    draft_generator = TweetDraftGenerator(config_mgr, cost_tracker=cost_tracker)
    analytics_tracker = AnalyticsTracker(config_mgr)

    for scraper in scrapers.values():
        scraper.cleanup_old_screenshots()

    if config_mgr.get("twitter.enabled", False):
        try:
            await analytics_tracker.sync_metrics()
        except Exception as exc:
            logger.warning("Analytics sync failed before run: %s", exc)
    top_examples = await _load_feedback_examples(config_mgr, notion_uploader)

    # Notion URL 캐시 웜업 (중복 체크 O(1) 확보)
    await notion_uploader.warm_cache()

    # 실시간 트렌드 모니터 초기화 (opt-in)
    trend_monitor = None
    if config_mgr.get("trends.enabled", False):
        try:
            from pipeline.trend_monitor import TrendMonitor

            trend_monitor = TrendMonitor(config_mgr)
            await trend_monitor.get_trending_keywords()
            logger.info("TrendMonitor 초기화 완료")
        except Exception as exc:
            logger.warning("TrendMonitor 초기화 실패 (무시): %s", exc)

    # 성과 기반 가중치 자동 조정
    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    adaptive_weights = await feedback_loop.compute_adaptive_weights()
    if adaptive_weights:
        config_mgr.config.setdefault("ranking", {})["weights"] = adaptive_weights
        logger.info("랭킹 가중치 적응형으로 교체: %s", adaptive_weights)
    else:
        logger.info("기본 랭킹 가중치 유지 (성과 데이터 부족 또는 상관관계 없음)")

    try:
        await _run_pipeline(
            args, config_mgr, scrapers, notifier, notion_uploader,
            twitter_poster, image_uploader, image_generator,
            draft_generator, top_examples, trend_monitor,
        )
    except Exception as exc:
        logger.exception("Critical error in main: %s", exc)
        await notifier.send_message(f"Blind-to-X pipeline crash\nError: `{exc}`", level="CRITICAL")
        sys.exit(1)
    finally:
        _LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    load_env()
    setup_logging()

    # Windows 특유의 asyncio 파이프 종료 타이밍 버그 우회
    if sys.platform == "win32":
        try:
            from asyncio.proactor_events import _ProactorBasePipeTransport

            original_del = _ProactorBasePipeTransport.__del__

            def silenced_del(self, *args, **kwargs):
                try:
                    original_del(self, *args, **kwargs)
                except ValueError as e:
                    if "closed pipe" not in str(e):
                        raise

            _ProactorBasePipeTransport.__del__ = silenced_del
        except ImportError:
            pass

        try:
            from asyncio.base_subprocess import BaseSubprocessTransport

            original_subprocess_del = BaseSubprocessTransport.__del__

            def silenced_subprocess_del(self, *args, **kwargs):
                try:
                    original_subprocess_del(self, *args, **kwargs)
                except ValueError as e:
                    if "closed pipe" not in str(e):
                        raise

            BaseSubprocessTransport.__del__ = silenced_subprocess_del
        except ImportError:
            pass

    asyncio.run(main())
