"""Dedup stage for `process_single_post()`."""

from __future__ import annotations

from config import ERROR_DUPLICATE_CONTENT, ERROR_DUPLICATE_URL, ERROR_NOTION_SCHEMA_MISMATCH
from pipeline.dedup import find_similar_in_notion

from .context import ProcessRunContext, mark_stage
from .runtime import logger


async def run_dedup_stage(
    ctx: ProcessRunContext,
    notion_uploader,
    config,
    post_data_hint,
) -> bool:
    mark_stage(ctx, "dedup", "running")
    if notion_uploader is None:
        mark_stage(ctx, "dedup", "skipped", "no_notion_uploader")
        return True

    duplicate = await notion_uploader.is_duplicate(ctx.url)
    logger.info("[%s] Processing: %s", ctx.trace_id, ctx.url)
    if duplicate is None:
        ctx.result["error"] = notion_uploader.last_error_message or "Notion schema validation failed"
        ctx.result["error_code"] = notion_uploader.last_error_code or ERROR_NOTION_SCHEMA_MISMATCH
        ctx.result["failure_stage"] = "upload"
        ctx.result["failure_reason"] = "duplicate_check_failed_or_schema_invalid"
        mark_stage(ctx, "dedup", "failed", "duplicate_check_failed_or_schema_invalid")
        return False
    if duplicate:
        ctx.result["error"] = "Duplicate (already in Notion)"
        ctx.result["error_code"] = ERROR_DUPLICATE_URL
        ctx.result["success"] = True
        ctx.result["notion_url"] = "(skipped-duplicate)"
        logger.info("Skipping duplicate: %s", ctx.url)
        mark_stage(ctx, "dedup", "skipped", "duplicate_url")
        return False

    feed_title = (post_data_hint or {}).get("feed_title", "")
    notion_check_enabled = bool(config.get("dedup.notion_check_enabled", True)) if config else True
    if feed_title and notion_check_enabled:
        sim_threshold = float(config.get("dedup.title_similarity_threshold", 0.6)) if config else 0.6
        lookback = int(config.get("dedup.lookback_days", 14)) if config else 14
        similar = await find_similar_in_notion(
            notion_uploader,
            feed_title,
            threshold=sim_threshold,
            lookback_days=lookback,
        )
        if similar:
            best = similar[0]
            ctx.result["error"] = f"Similar content exists (sim={best['similarity']:.2f}: '{best['title'][:40]}')"
            ctx.result["error_code"] = ERROR_DUPLICATE_CONTENT
            ctx.result["success"] = True
            ctx.result["notion_url"] = "(skipped-similar)"
            logger.info("SKIP [similar content] %s sim=%.2f with '%s'", ctx.url, best["similarity"], best["title"][:50])
            mark_stage(ctx, "dedup", "skipped", "similar_content")
            return False

    mark_stage(ctx, "dedup", "completed")
    return True
