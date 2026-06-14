"""Core pipeline execution logic."""

import asyncio
import logging
import sys
from contextlib import AsyncExitStack
from datetime import datetime

from config import as_bool as _as_bool
from pipeline import PipelineServices, calculate_run_metrics, process_single_post
from pipeline.commands import (
    run_digest,
    run_dry_run_single,
    run_reprocess_approved,
    run_review_queue_report,
    run_sentiment_report,
)
from pipeline.daily_queue_floor import resolve_daily_queue_floor
from pipeline.feed_collector import collect_feed_items

logger = logging.getLogger(__name__)


def _first_operator_action(results: list[dict]) -> str:
    for item in results:
        action = item.get("notion_operator_action") or item.get("operator_action")
        if isinstance(action, str) and action.strip():
            return action.strip()
    return ""


async def handle_single_commands(args, config_mgr, notifier, notion_uploader, twitter_poster) -> bool:
    """Handle one-shot commands (reprocess, digest, sentiment). Returns True if handled."""
    if getattr(args, "review_queue_report", False):
        limit_val = getattr(args, "limit", None)
        lookback_days = getattr(args, "review_queue_lookback_days", None)
        stale_days = getattr(args, "review_queue_stale_days", None)
        action_limit = getattr(args, "review_queue_action_limit", None)
        ready_attention_limit = getattr(args, "review_queue_ready_attention_limit", None)
        output_path = getattr(args, "review_queue_report_output", None) or config_mgr.get(
            "review.queue_report_output",
            ".tmp/review_queue_report_latest.json",
        )
        report = await run_review_queue_report(
            notion_uploader,
            lookback_days=(
                lookback_days if lookback_days is not None else config_mgr.get("review.queue_report_lookback_days", 30)
            ),
            limit=limit_val if limit_val is not None else config_mgr.get("review.queue_report_limit", 50),
            stale_days=stale_days if stale_days is not None else config_mgr.get("review.queue_report_stale_days", 3),
            action_limit=(
                action_limit if action_limit is not None else config_mgr.get("review.queue_report_action_limit", 10)
            ),
            ready_attention_limit=(
                ready_attention_limit
                if ready_attention_limit is not None
                else config_mgr.get("review.queue_report_ready_attention_limit", 3)
            ),
            output_path=output_path,
        )
        from pipeline.commands.review_queue_report import (
            exit_code_for_review_queue_report,
            format_review_queue_report,
        )

        print(format_review_queue_report(report))
        args._single_command_exit_code = exit_code_for_review_queue_report(
            report, fail_on_warning=getattr(args, "review_queue_report_fail_on_warning", False)
        )
        return True

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
        degraded_count = len(
            [item for item in results if item.get("success") and item.get("notion_update_success") is False]
        )
        if results:
            logger.info(
                "Approved reprocess completed. success=%s fail=%s degraded=%s",
                success_count,
                fail_count,
                degraded_count,
            )
        if fail_count or degraded_count:
            operator_action = _first_operator_action(results)
            action_line = f"\noperator_action {operator_action}" if operator_action else ""
            await notifier.send_message(
                "Blind-to-X approved reprocess completed\n"
                f"success {success_count} / fail {fail_count} / notion_sync_warning {degraded_count}"
                f"{action_line}",
                level="WARNING",
            )
        return True

    if getattr(args, "digest", False):
        await run_digest(config_mgr, notion_uploader, date=getattr(args, "digest_date", None))
        return True

    if getattr(args, "sentiment_report", False):
        run_sentiment_report()
        return True

    return False


def _build_base_services(image_uploader, image_generator, draft_generator, notion_uploader, twitter_poster):
    return PipelineServices(
        scraper=None,
        image_uploader=image_uploader,
        image_generator=image_generator,
        draft_generator=draft_generator,
        notion_uploader=notion_uploader,
        twitter_poster=twitter_poster,
    )


def _build_item_services(item, base_services):
    return PipelineServices(
        scraper=item["scraper"],
        image_uploader=base_services.image_uploader,
        image_generator=base_services.image_generator,
        draft_generator=base_services.draft_generator,
        notion_uploader=base_services.notion_uploader,
        twitter_poster=base_services.twitter_poster,
    )


def _print_item_progress(index, total_count, item):
    print(f"  [{index}/{total_count}] [{item['source']}] {item['url']}")


async def _process_live_item(
    item,
    *,
    base_services,
    top_examples,
    output_formats,
    config_mgr,
    effective_review_only,
    daily_queue_floor,
):
    return await process_single_post(
        url=item["url"],
        top_tweets=top_examples,
        source_name=item["source"],
        output_formats=output_formats,
        config=config_mgr,
        feed_mode=item["feed_mode"],
        review_only=effective_review_only,
        post_data_hint={"feed_title": item.get("feed_title", "")},
        services=_build_item_services(item, base_services),
        daily_queue_floor=daily_queue_floor,
    )


async def _process_pipeline_item(
    item,
    *,
    index,
    total_count,
    dry_run,
    config_mgr,
    base_services,
    top_examples,
    output_formats,
    effective_review_only,
    daily_queue_floor,
):
    _print_item_progress(index, total_count, item)
    if dry_run:
        return await run_dry_run_single(
            item,
            config_mgr,
            base_services.draft_generator,
            base_services.notion_uploader,
            top_examples,
        )

    return await _process_live_item(
        item,
        base_services=base_services,
        top_examples=top_examples,
        output_formats=output_formats,
        config_mgr=config_mgr,
        effective_review_only=effective_review_only,
        daily_queue_floor=daily_queue_floor,
    )


async def _process_collected_items(
    urls_to_process,
    *,
    dry_run,
    parallel,
    config_mgr,
    base_services,
    top_examples,
    output_formats,
    effective_review_only,
    daily_queue_floor,
):
    total_count = len(urls_to_process)

    if dry_run or parallel <= 1:
        results = []
        for index, item in enumerate(urls_to_process, start=1):
            result = await _process_pipeline_item(
                item,
                index=index,
                total_count=total_count,
                dry_run=dry_run,
                config_mgr=config_mgr,
                base_services=base_services,
                top_examples=top_examples,
                output_formats=output_formats,
                effective_review_only=effective_review_only,
                daily_queue_floor=daily_queue_floor,
            )
            results.append(result)
        return results

    semaphore = asyncio.Semaphore(max(1, parallel))
    counter = {"done": 0}
    counter_lock = asyncio.Lock()

    async def _bounded(item):
        async with semaphore:
            async with counter_lock:
                counter["done"] += 1
                index = counter["done"]
            return await _process_pipeline_item(
                item,
                index=index,
                total_count=total_count,
                dry_run=dry_run,
                config_mgr=config_mgr,
                base_services=base_services,
                top_examples=top_examples,
                output_formats=output_formats,
                effective_review_only=effective_review_only,
                daily_queue_floor=daily_queue_floor,
            )

    return await asyncio.gather(*[_bounded(item) for item in urls_to_process])


async def _append_cross_source_insights(
    results,
    *,
    dry_run,
    config_mgr,
    draft_generator,
    notion_uploader,
    image_uploader,
    image_generator,
    output_formats,
    top_examples,
    trend_monitor,
):
    if dry_run or not _as_bool(config_mgr.get("cross_source_insight.enabled", True), default=True):
        return results

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
            combined_results = list(results) + insight_results
            logger.info("크로스소스 인사이트 %d건 추가", len(insight_results))
            return combined_results
    except Exception as exc:
        logger.warning("크로스소스 인사이트 생성 실패 (무시): %s", exc)

    return results


async def _record_trend_spikes(trend_monitor, *, dry_run):
    if not trend_monitor or dry_run:
        return

    try:
        spikes = await trend_monitor.detect_spikes()
        if not spikes:
            return

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


def _calculate_execution_metrics(results, *, dry_run):
    metrics = calculate_run_metrics(results, dry_run=dry_run)
    successful = metrics["successful"]
    failed = metrics["failed"]
    return metrics, successful, failed


def _print_execution_summary(results, feed_stats, metrics, start_time, *, dry_run):
    elapsed = (datetime.now() - start_time).total_seconds()
    content_dup_skips = len(metrics.get("content_duplicate_skips", []))

    print(f"\n{'=' * 55}")
    print(f"  EXECUTION SUMMARY  ({elapsed:.1f}s)")
    print(f"  Total: {len(results)}  |  OK {len(metrics['successful'])}  |  FAIL {len(metrics['failed'])}")
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


async def _send_execution_notification(notifier, results, metrics, successful, failed):
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


def _exit_if_all_failed(successful, failed):
    if not failed or successful:
        return

    error_reasons = "; ".join([str(f.get("error", "unknown")) for f in failed])
    logger.error(f"Exit 1: All {len(failed)} items failed. Reasons: {error_reasons}")
    sys.exit(1)


async def _maybe_send_daily_digest(config_mgr, notion_uploader):
    if not (config_mgr.get("digest.enabled", False) and config_mgr.get("digest.telegram_enabled", False)):
        return

    try:
        from pipeline.daily_digest import generate_and_send

        await generate_and_send(config_mgr, notion_uploader=notion_uploader)
    except Exception as _dg_exc:
        logger.debug("Auto digest skipped: %s", _dg_exc)


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
    """Core pipeline: collect, process, and report."""
    async with AsyncExitStack() as stack:
        for scraper in scrapers.values():
            await stack.enter_async_context(scraper)

        effective_review_only = getattr(args, "review_only", False) or config_mgr.get(
            "content_strategy.require_human_approval", True
        )
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

        start_time = datetime.now()
        output_formats = config_mgr.get("output_formats", ["twitter"])
        dry_run = getattr(args, "dry_run", False)
        parallel = getattr(args, "parallel", 3)
        base_services = _build_base_services(
            image_uploader,
            image_generator,
            draft_generator,
            notion_uploader,
            twitter_poster,
        )

        results = await _process_collected_items(
            urls_to_process,
            dry_run=dry_run,
            parallel=parallel,
            config_mgr=config_mgr,
            base_services=base_services,
            top_examples=top_examples,
            output_formats=output_formats,
            effective_review_only=effective_review_only,
            daily_queue_floor=daily_queue_floor,
        )

        results = await _append_cross_source_insights(
            results,
            dry_run=dry_run,
            config_mgr=config_mgr,
            draft_generator=draft_generator,
            notion_uploader=notion_uploader,
            image_uploader=image_uploader,
            image_generator=image_generator,
            output_formats=output_formats,
            top_examples=top_examples,
            trend_monitor=trend_monitor,
        )
        await _record_trend_spikes(trend_monitor, dry_run=dry_run)

        metrics, successful, failed = _calculate_execution_metrics(results, dry_run=dry_run)
        _print_execution_summary(results, feed_stats, metrics, start_time, dry_run=dry_run)

        if not dry_run:
            await _send_execution_notification(notifier, results, metrics, successful, failed)

        _exit_if_all_failed(successful, failed)
        await _maybe_send_daily_digest(config_mgr, notion_uploader)
