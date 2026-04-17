"""Core pipeline execution logic."""

import asyncio
from contextlib import AsyncExitStack
from datetime import datetime
import logging
import sys

from pipeline import calculate_run_metrics, process_single_post, PipelineServices
from pipeline.commands import run_digest, run_dry_run_single, run_reprocess_approved, run_sentiment_report
from pipeline.daily_queue_floor import resolve_daily_queue_floor
from pipeline.feed_collector import collect_feed_items

logger = logging.getLogger(__name__)

async def handle_single_commands(args, config_mgr, notifier, notion_uploader, twitter_poster) -> bool:
    """Handle one-shot commands (reprocess, digest, sentiment). Returns True if handled."""
    if getattr(args, "reprocess_approved", False):
        limit_val = getattr(args, "limit", None)
        results = await run_reprocess_approved(
            config_mgr,
            notion_uploader,
            twitter_poster,
            limit=limit_val or config_mgr.get("review.queue_limit_per_run", 10),
        )
        success_count = len([item for item in results if item.get("success")])
        fail_count = len(results) - success_count
        if results:
            logger.info("Approved reprocess completed. success=%s fail=%s", success_count, fail_count)
        if fail_count:
            await notifier.send_message(f"Blind-to-X 승인 재발행 완료\n성공 {success_count}건 / 실패 {fail_count}건")
        return True

    if getattr(args, "digest", False):
        await run_digest(config_mgr, notion_uploader, date=getattr(args, "digest_date", None))
        return True

    if getattr(args, "sentiment_report", False):
        run_sentiment_report()
        return True

    return False


async def execute_pipeline(
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
):
    """Core pipeline: collect → process → report."""
    async with AsyncExitStack() as stack:
        for scraper in scrapers.values():
            await stack.enter_async_context(scraper)

        effective_review_only = getattr(args, "review_only", False) or config_mgr.get("content_strategy.require_human_approval", True)
        daily_queue_floor = await resolve_daily_queue_floor(config_mgr, notion_uploader, effective_review_only)

        urls_to_process, feed_stats = await collect_feed_items(
            config_mgr,
            args,
            scrapers,
            daily_queue_floor=daily_queue_floor,
        )
        if not urls_to_process:
            logger.info("No valid posts to process.")
            return

        results = []
        start_time = datetime.now()
        output_formats = config_mgr.get("output_formats", ["twitter"])

        services = PipelineServices(
            scraper=None,  # Will be set per-item
            image_uploader=image_uploader,
            image_generator=image_generator,
            draft_generator=draft_generator,
            notion_uploader=notion_uploader,
            twitter_poster=twitter_poster,
        )

        dry_run = getattr(args, "dry_run", False)
        parallel = getattr(args, "parallel", 3)

        if dry_run or parallel <= 1:
            for index, item in enumerate(urls_to_process, start=1):
                print(f"  [{index}/{len(urls_to_process)}] [{item['source']}] {item['url']}")
                if dry_run:
                    result = await run_dry_run_single(item, config_mgr, draft_generator, notion_uploader, top_examples)
                else:
                    item_services = PipelineServices(
                        scraper=item["scraper"],
                        image_uploader=services.image_uploader,
                        image_generator=services.image_generator,
                        draft_generator=services.draft_generator,
                        notion_uploader=services.notion_uploader,
                        twitter_poster=services.twitter_poster,
                    )
                    result = await process_single_post(
                        url=item["url"],
                        top_tweets=top_examples,
                        source_name=item["source"],
                        output_formats=output_formats,
                        config=config_mgr,
                        feed_mode=item["feed_mode"],
                        review_only=effective_review_only,
                        post_data_hint={"feed_title": item.get("feed_title", "")},
                        services=item_services,
                        daily_queue_floor=daily_queue_floor,
                    )
                results.append(result)
        else:
            semaphore = asyncio.Semaphore(max(1, parallel))
            counter = {"done": 0}
            counter_lock = asyncio.Lock()

            async def _bounded(item):
                async with semaphore:
                    async with counter_lock:
                        counter["done"] += 1
                        index = counter["done"]
                    print(f"  [{index}/{len(urls_to_process)}] [{item['source']}] {item['url']}")
                    item_services = PipelineServices(
                        scraper=item["scraper"],
                        image_uploader=services.image_uploader,
                        image_generator=services.image_generator,
                        draft_generator=services.draft_generator,
                        notion_uploader=services.notion_uploader,
                        twitter_poster=services.twitter_poster,
                    )
                    return await process_single_post(
                        url=item["url"],
                        top_tweets=top_examples,
                        source_name=item["source"],
                        output_formats=output_formats,
                        config=config_mgr,
                        feed_mode=item["feed_mode"],
                        review_only=effective_review_only,
                        post_data_hint={"feed_title": item.get("feed_title", "")},
                        services=item_services,
                        daily_queue_floor=daily_queue_floor,
                    )

            results = await asyncio.gather(*[_bounded(item) for item in urls_to_process])

        # ── 크로스소스 인사이트 생성 ─────────────────────────────────────
        if not dry_run and config_mgr.get("cross_source_insight.enabled", True):
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
        if trend_monitor and not dry_run:
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
        metrics = calculate_run_metrics(results, dry_run=dry_run)
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
        if not dry_run:
            print(
                f"  Upload Success Rate: {metrics['upload_success_rate']:.1f}% "
                f"({len(metrics['live_upload_success'])}/{metrics['live_upload_attempts']})"
            )
        print(f"{'=' * 55}")

        if not dry_run:
            review_ready = len([item for item in results if item.get("status") == "검토필요"])
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
