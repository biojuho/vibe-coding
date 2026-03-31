"""Post processing pipeline and run metrics calculation."""

from __future__ import annotations

import logging
import uuid

from config import (
    ERROR_DUPLICATE_CONTENT,
    ERROR_DUPLICATE_URL,
    ERROR_FILTERED_LOW_QUALITY,
    ERROR_FILTERED_SHORT,
    ERROR_FILTERED_SPAM,
    ERROR_NOTION_DUPLICATE_CHECK_FAILED,
    ERROR_NOTION_SCHEMA_MISMATCH,
    ERROR_SCRAPE_FEED_FAILED,
    ERROR_SCRAPE_PARSE_FAILED,
)
from pipeline.process_stages.context import ProcessRunContext, build_process_result, mark_stage
from pipeline.process_stages.dedup_stage import run_dedup_stage
from pipeline.process_stages.fetch_stage import run_fetch_stage
from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage as run_filter_stage
from pipeline.process_stages.generate_review_stage import run_generate_review_stage as run_generate_stage
from pipeline.process_stages.persist_stage import run_persist_stage
from pipeline.process_stages import runtime as _stage_runtime
from pipeline.process_stages import filter_profile_stage as _filter_stage_module
from pipeline.process_stages.runtime import SPAM_KEYWORDS, extract_preferred_tweet_text

logger = logging.getLogger(__name__)

# P6: 성과 피드백 루프 (선택적 — 실패 시 무시)
try:
    from pipeline.performance_tracker import PerformanceTracker

    _perf_tracker: PerformanceTracker | None = PerformanceTracker()
except Exception:
    _perf_tracker = None

# 파이프라인 에러 자동 캡처 (debug_history_db 연동)
try:
    import importlib.util as _ilu
    import pathlib as _pl

    _spec = _ilu.spec_from_file_location(
        "workspace.execution.debug_history_db",
        _pl.Path(__file__).resolve().parents[3] / "workspace" / "execution" / "debug_history_db.py",
    )
    _dbmod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_dbmod)  # type: ignore[union-attr]
    _auto_log_error = _dbmod.auto_log_error
except Exception:
    _auto_log_error = None  # type: ignore[assignment]

# Backward-compatible globals kept for test monkeypatches and runtime overrides.
_ViralFilterCls = _stage_runtime._ViralFilterCls
_viral_filter_instance = _stage_runtime._viral_filter_instance
_sentiment_tracker = _stage_runtime.sentiment_tracker
_nlm_enrich = _stage_runtime.notebooklm_enricher
build_content_profile = _filter_stage_module.build_content_profile
build_review_decision = _filter_stage_module.build_review_decision


def _sync_runtime_overrides() -> None:
    """Propagate process-level monkeypatches into the staged runtime."""

    _stage_runtime._ViralFilterCls = _ViralFilterCls
    _stage_runtime._viral_filter_instance = _viral_filter_instance
    _stage_runtime.sentiment_tracker = _sentiment_tracker
    _stage_runtime.notebooklm_enricher = _nlm_enrich
    _filter_stage_module.build_content_profile = build_content_profile
    _filter_stage_module.build_review_decision = build_review_decision


async def process_single_post(
    url,
    scraper,
    image_uploader,
    image_generator=None,
    draft_generator=None,
    notion_uploader=None,
    twitter_poster=None,
    top_tweets=None,
    source_name=None,
    output_formats=None,
    config=None,
    feed_mode=None,
    review_only=False,
    post_data_hint=None,
):
    trace_id = uuid.uuid4().hex[:8]
    result = build_process_result(url, trace_id)
    ctx = ProcessRunContext(url=url, trace_id=trace_id, result=result)
    _sync_runtime_overrides()

    try:
        if not await run_dedup_stage(ctx, notion_uploader, config, post_data_hint):
            return result
        if not await run_fetch_stage(ctx, scraper, source_name, feed_mode):
            return result
        if not await run_filter_stage(ctx, scraper, config, top_tweets, review_only=review_only):
            return result
        if not await run_generate_stage(
            ctx,
            draft_generator,
            image_uploader,
            top_tweets,
            output_formats,
            config,
        ):
            return result
        if not await run_persist_stage(
            ctx,
            image_uploader,
            image_generator,
            notion_uploader,
            twitter_poster,
            config,
            review_only,
        ):
            return result
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.error("Error processing %s: %s", url, exc)
        result["error"] = str(exc)
        result["error_code"] = "INTERNAL_EXCEPTION"
        result["failure_stage"] = result.get("failure_stage") or "upload"
        result["failure_reason"] = "internal_exception"
        for stage_name, stage_info in reversed(list(ctx.stage_status.items())):
            if stage_info.get("status") == "running":
                mark_stage(ctx, stage_name, "failed", "internal_exception")
                break
        if _auto_log_error is not None:
            _auto_log_error(exc, module="blind-to-x/process", context=url[:80])
    finally:
        global _viral_filter_instance
        _viral_filter_instance = _stage_runtime._viral_filter_instance

    return result


def calculate_run_metrics(results, dry_run=False):
    successful = [item for item in results if item.get("success")]
    failed = [item for item in results if not item.get("success")]
    duplicate_skips = [item for item in results if item.get("error_code") == ERROR_DUPLICATE_URL]
    content_duplicate_skips = [item for item in results if item.get("error_code") == ERROR_DUPLICATE_CONTENT]
    filtered_skips = [
        item
        for item in results
        if item.get("error_code") in (ERROR_FILTERED_SHORT, ERROR_FILTERED_SPAM, ERROR_FILTERED_LOW_QUALITY)
    ]
    filtered_low_quality = [item for item in results if item.get("error_code") == ERROR_FILTERED_LOW_QUALITY]
    schema_mismatches = [item for item in results if item.get("error_code") == ERROR_NOTION_SCHEMA_MISMATCH]
    duplicate_check_failures = [
        item for item in results if item.get("error_code") == ERROR_NOTION_DUPLICATE_CHECK_FAILED
    ]
    feed_fetch_failures = [item for item in results if item.get("error_code") == ERROR_SCRAPE_FEED_FAILED]
    parse_failures = [item for item in results if item.get("error_code") == ERROR_SCRAPE_PARSE_FAILED]

    quality_scores = [
        item.get("quality_score") for item in successful if isinstance(item.get("quality_score"), (int, float))
    ]
    avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    live_upload_attempts = (
        max(0, len(results) - len(duplicate_skips) - len(content_duplicate_skips) - len(filtered_skips))
        if not dry_run
        else 0
    )
    live_upload_success = [
        item
        for item in results
        if item.get("success")
        and item.get("notion_url")
        and item.get("notion_url")
        not in {"(skipped-duplicate)", "(skipped-filtered)", "(skipped-similar)", "(dry-run)"}
    ]
    upload_success_rate = (len(live_upload_success) / live_upload_attempts * 100) if live_upload_attempts > 0 else 0.0

    return {
        "successful": successful,
        "failed": failed,
        "duplicate_skips": duplicate_skips,
        "content_duplicate_skips": content_duplicate_skips,
        "filtered_skips": filtered_skips,
        "filtered_low_quality": filtered_low_quality,
        "schema_mismatches": schema_mismatches,
        "duplicate_check_failures": duplicate_check_failures,
        "feed_fetch_failures": feed_fetch_failures,
        "parse_failures": parse_failures,
        "avg_quality_score": avg_quality_score,
        "live_upload_attempts": live_upload_attempts,
        "live_upload_success": live_upload_success,
        "upload_success_rate": upload_success_rate,
    }


__all__ = [
    "SPAM_KEYWORDS",
    "build_content_profile",
    "build_review_decision",
    "calculate_run_metrics",
    "extract_preferred_tweet_text",
    "process_single_post",
]
