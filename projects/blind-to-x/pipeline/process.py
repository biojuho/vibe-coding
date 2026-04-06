"""Post processing pipeline and run metrics calculation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from config import (
    ERROR_DUPLICATE_CONTENT,
    ERROR_DUPLICATE_URL,
    ERROR_FILTERED_LOW_QUALITY,
    ERROR_FILTERED_SHORT,
    ERROR_FILTERED_SPAM,
    ERROR_NOTION_DUPLICATE_CHECK_FAILED,
    ERROR_NOTION_SCHEMA_MISMATCH,
    ERROR_SCRAPE_FAILED,
    ERROR_SCRAPE_FEED_FAILED,
    ERROR_SCRAPE_PARSE_FAILED,
)
from pipeline.process_stages.context import ProcessRunContext, build_process_result, mark_stage
from pipeline.process_stages.dedup_stage import run_dedup_stage
from pipeline.process_stages.fetch_stage import run_fetch_stage
from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage as run_filter_stage
from pipeline.process_stages.generate_review_stage import run_generate_review_stage as run_generate_stage
from pipeline.process_stages.persist_stage import run_persist_stage
from pipeline.process_stages import filter_profile_stage as _filter_stage_module
from pipeline.process_stages import runtime as _stage_runtime
from pipeline.process_stages.runtime import SPAM_KEYWORDS, extract_preferred_tweet_text

logger = logging.getLogger(__name__)

DEFAULT_FETCH_STAGE_TIMEOUT_SECONDS = 30
DEFAULT_PROCESS_TIMEOUT_SECONDS = 180

# P6: 성과 피드백 루프 (선택적 — 실패 시 무시)
try:
    from pipeline.performance_tracker import PerformanceTracker

    _perf_tracker: PerformanceTracker | None = PerformanceTracker()
except Exception:
    _perf_tracker = None

# Backward-compatible globals kept for external consumers / test monkeypatches.
# These now point directly into the runtime module — no sync needed.
build_content_profile = _filter_stage_module.build_content_profile
build_review_decision = _filter_stage_module.build_review_decision


def _config_int(config: Any, key: str, default: int) -> int:
    if config is None or not hasattr(config, "get"):
        return default

    try:
        value = config.get(key, default)
        parsed = int(value)
        return parsed if parsed > 0 else default
    except Exception:
        return default


def _resolve_fetch_timeout(config: Any) -> int:
    return _config_int(
        config,
        "pipeline.fetch_timeout_seconds",
        max(
            DEFAULT_FETCH_STAGE_TIMEOUT_SECONDS,
            _config_int(config, "request.timeout_seconds", DEFAULT_FETCH_STAGE_TIMEOUT_SECONDS) + 10,
        ),
    )


def _resolve_process_timeout(config: Any) -> int:
    return _config_int(
        config,
        "pipeline.process_timeout_seconds",
        max(
            DEFAULT_PROCESS_TIMEOUT_SECONDS,
            _resolve_fetch_timeout(config) + _config_int(config, "llm.request_timeout_seconds", 45) + 60,
        ),
    )


def _current_running_stage(ctx: ProcessRunContext) -> str:
    for stage_name, stage_info in reversed(list(ctx.stage_status.items())):
        if stage_info.get("status") == "running":
            return stage_name
    return "pipeline"


@dataclass
class PipelineServices:
    """오케스트레이터 및 각 스테이지에 필요한 외부 의존성(Clients) 컨테이너"""

    scraper: Any
    image_uploader: Any
    image_generator: Optional[Any] = None
    draft_generator: Optional[Any] = None
    notion_uploader: Optional[Any] = None
    twitter_poster: Optional[Any] = None


async def process_single_post(
    url,
    scraper=None,
    image_uploader=None,
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
    services: Optional[PipelineServices] = None,
):
    # 하위 호환성 및 명시적 의존성 묶음 적용
    if services:
        scraper = services.scraper
        image_uploader = services.image_uploader
        image_generator = services.image_generator
        draft_generator = services.draft_generator
        notion_uploader = services.notion_uploader
        twitter_poster = services.twitter_poster
    trace_id = uuid.uuid4().hex[:8]
    result = build_process_result(url, trace_id)
    ctx = ProcessRunContext(url=url, trace_id=trace_id, result=result)
    fetch_timeout_seconds = _resolve_fetch_timeout(config)
    process_timeout_seconds = _resolve_process_timeout(config)

    async def _run_pipeline() -> dict[str, Any]:
        if not await run_dedup_stage(ctx, notion_uploader, config, post_data_hint):
            return result
        try:
            fetch_ok = await asyncio.wait_for(
                run_fetch_stage(ctx, scraper, source_name, feed_mode),
                timeout=fetch_timeout_seconds,
            )
        except asyncio.TimeoutError:
            ctx.result["error"] = f"Fetch stage timed out after {fetch_timeout_seconds}s"
            ctx.result["error_code"] = ERROR_SCRAPE_FAILED
            ctx.result["failure_stage"] = "post_fetch"
            ctx.result["failure_reason"] = "fetch_timeout"
            mark_stage(ctx, "fetch", "failed", "fetch_timeout")
            return result
        if not fetch_ok:
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
        return result

    try:
        await asyncio.wait_for(_run_pipeline(), timeout=process_timeout_seconds)
    except asyncio.TimeoutError:
        running_stage = _current_running_stage(ctx)
        result["error"] = f"Process timed out after {process_timeout_seconds}s"
        result["error_code"] = "PROCESS_TIMEOUT"
        result["failure_stage"] = running_stage
        result["failure_reason"] = "process_timeout"
        mark_stage(ctx, running_stage, "failed", "process_timeout")
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
        if _stage_runtime.auto_log_error is not None:
            _stage_runtime.auto_log_error(exc, module="blind-to-x/process", context=url[:80])

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
