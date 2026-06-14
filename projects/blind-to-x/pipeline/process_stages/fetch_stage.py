"""Fetch stage for `process_single_post()`."""

from __future__ import annotations

import logging

from config import ERROR_SCRAPE_FAILED, ERROR_SCRAPE_PARSE_FAILED
from config import as_bool as _as_bool
from pipeline.models import ScrapedPost
from pipeline.scrape_integrity import DEFAULT_MIN_ARTICLE_CHARS, classify_scrape_integrity

from .context import ProcessRunContext, mark_stage
from .runtime import log_scrape_quality

logger = logging.getLogger(__name__)


def _check_scrape_integrity(ctx: ProcessRunContext, scraper) -> bool:
    """추출된 콘텐츠가 실제 게시물인지 검증 (D-033).

    로그인 월·삭제된 글·봇 차단/캡차 페이지는 한국어 비율·길이 검사를 통과해
    검토 큐를 오염시킨다. 이를 수집 실패로 분류해 큐 진입 전에 차단한다.
    실패 시 `ctx.result`를 채우고 False를 반환한다.
    """
    config = getattr(scraper, "config", None)
    enabled = True
    min_chars = DEFAULT_MIN_ARTICLE_CHARS
    if config is not None:
        try:
            enabled = _as_bool(config.get("scrape_quality.integrity_check_enabled", True), default=True)
            min_chars = int(config.get("scrape_quality.min_article_chars", DEFAULT_MIN_ARTICLE_CHARS))
        except Exception as exc:
            logger.debug("fetch_stage config parse failed, using defaults: %s", exc)
    if not enabled:
        return True

    verdict = classify_scrape_integrity(
        ctx.post_data.get("title", ""),
        ctx.content_text,
        min_article_chars=min_chars,
    )
    if verdict["ok"]:
        return True

    ctx.result["error"] = f"Non-article page detected ({verdict['category']}): '{verdict['matched']}'"
    ctx.result["error_code"] = ERROR_SCRAPE_FAILED if verdict["category"] == "blocked" else ERROR_SCRAPE_PARSE_FAILED
    ctx.result["failure_stage"] = "post_fetch"
    ctx.result["failure_reason"] = verdict["failure_reason"]
    logger.warning(
        "SKIP [scrape_integrity] %s - %s (matched=%r)",
        ctx.url,
        verdict["failure_reason"],
        verdict["matched"],
    )
    mark_stage(ctx, "fetch", "failed", verdict["failure_reason"])
    return False


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
        ctx.post_data = validated_data.model_dump()
    except Exception as v_err:
        logger.error("Scraped data validation failed for %s: %s", ctx.url, v_err)
        ctx.result["error"] = f"Validation failed: {str(v_err)}"
        ctx.result["error_code"] = ERROR_SCRAPE_PARSE_FAILED
        ctx.result["failure_stage"] = "post_fetch_validation"
        ctx.result["failure_reason"] = "data_validation_error"
        mark_stage(ctx, "fetch", "failed", "data_validation_error")
        return False

    ctx.content_text = ctx.post_data.get("content", "")

    # 추출된 것이 실제 게시물인지 검증 — 로그인 월·삭제 글·봇 차단 페이지 차단 (D-033).
    if not _check_scrape_integrity(ctx, scraper):
        return False

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
        except Exception as exc:
            logger.debug("log_scrape_quality failed (non-critical): %s", exc)

    mark_stage(ctx, "fetch", "completed")
    return True
