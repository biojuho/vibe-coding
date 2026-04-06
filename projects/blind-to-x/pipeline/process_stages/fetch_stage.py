"""Fetch stage for `process_single_post()`."""

from __future__ import annotations

import logging

from config import ERROR_SCRAPE_FAILED, ERROR_SCRAPE_PARSE_FAILED
from pipeline.models import ScrapedPost

from .context import ProcessRunContext, mark_stage
from .runtime import log_scrape_quality

logger = logging.getLogger(__name__)


async def run_fetch_stage(
    ctx: ProcessRunContext,
    scraper,
    source_name,
    feed_mode,
) -> bool:
    mark_stage(ctx, "fetch", "running")

    scrape_with_retry = getattr(scraper, "scrape_post_with_retry", None)
    if callable(scrape_with_retry):
        post_data = await scrape_with_retry(ctx.url)
    else:
        post_data = await scraper.scrape_post(ctx.url)
    if not post_data:
        ctx.result["error"] = "Scraping failed"
        ctx.result["error_code"] = ERROR_SCRAPE_FAILED
        ctx.result["failure_stage"] = "post_fetch"
        ctx.result["failure_reason"] = "empty_scrape_result"
        mark_stage(ctx, "fetch", "failed", "empty_scrape_result")
        return False

    if post_data.get("_scrape_error"):
        ctx.result["error"] = post_data.get("error_message", "Scraping failed")
        ctx.result["error_code"] = post_data.get("error_code", ERROR_SCRAPE_FAILED)
        ctx.result["failure_stage"] = post_data.get("failure_stage", "post_fetch")
        ctx.result["failure_reason"] = post_data.get("failure_reason", "scrape_error")
        mark_stage(ctx, "fetch", "failed", ctx.result["failure_reason"])
        return False

    post_data["source"] = source_name or post_data.get("source") or "blind"
    post_data["feed_mode"] = feed_mode or post_data.get("feed_mode") or "trending"

    # Pydantic을 이용한 데이터 무결성 검증 (V2.0 Phase 1)
    try:
        validated_data = ScrapedPost(**post_data)
        ctx.post_data = validated_data.dict()
    except Exception as v_err:
        logger.error("Scraped data validation failed for %s: %s", ctx.url, v_err)
        ctx.result["error"] = f"Validation failed: {str(v_err)}"
        ctx.result["error_code"] = ERROR_SCRAPE_PARSE_FAILED
        ctx.result["failure_stage"] = "post_fetch_validation"
        ctx.result["failure_reason"] = "data_validation_error"
        mark_stage(ctx, "fetch", "failed", "data_validation_error")
        return False

    ctx.content_text = ctx.post_data.get("content", "")
    ctx.quality = scraper.assess_quality(post_data)
    ctx.result["quality_score"] = ctx.quality["score"]

    if log_scrape_quality is not None:
        try:
            log_scrape_quality(
                source=post_data.get("source", "unknown"),
                url=ctx.url,
                quality_score=ctx.quality["score"],
                issues=ctx.quality.get("reasons", []),
            )
        except Exception:
            pass

    mark_stage(ctx, "fetch", "completed")
    return True
