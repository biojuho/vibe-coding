"""Dry-run command: scrape and generate drafts without uploading."""

from __future__ import annotations

import logging

from pipeline.content_intelligence import build_content_profile
from pipeline.process import SPAM_KEYWORDS
from pipeline.review_queue import build_review_decision

logger = logging.getLogger(__name__)


async def run_dry_run_single(item, config_mgr, draft_generator, notion_uploader, top_examples):
    """Process a single post in dry-run mode (no upload).

    Args:
        item: Dict with keys ``url``, ``source``, ``scraper``, ``feed_mode``.
        config_mgr: ConfigManager instance.
        draft_generator: TweetDraftGenerator instance.
        notion_uploader: NotionUploader instance.
        top_examples: Few-shot examples list.

    Returns:
        Result dict with success/failure metadata.
    """
    scraper = item["scraper"]
    url = item["url"]
    source_name = item["source"]

    post_data = await scraper.scrape_post(url)
    if not post_data or post_data.get("_scrape_error"):
        return {
            "url": url,
            "success": False,
            "error": (post_data or {}).get("error_message", "Scraping failed"),
            "error_code": (post_data or {}).get("error_code", "SCRAPE_FAILED"),
            "quality_score": None,
            "failure_stage": (post_data or {}).get("failure_stage", "post_fetch"),
            "failure_reason": (post_data or {}).get("failure_reason", "dry_run_scrape_failed"),
        }

    duplicate = await notion_uploader.is_duplicate(url)
    if duplicate:
        return {
            "url": url,
            "success": True,
            "title": post_data.get("title", ""),
            "notion_url": "(skipped-duplicate)",
            "error_code": "DUPLICATE_URL",
        }

    post_data["source"] = source_name
    post_data["feed_mode"] = item.get("feed_mode", "trending")
    quality = scraper.assess_quality(post_data)
    content_text = post_data.get("content", "")

    if len(content_text) < scraper.min_content_length:
        return {
            "url": url,
            "success": True,
            "title": post_data.get("title", ""),
            "notion_url": "(skipped-filtered)",
            "error_code": "FILTERED_SHORT",
            "quality_score": quality["score"],
            "failure_stage": "filter",
            "failure_reason": "content_too_short",
        }

    if any(keyword in content_text for keyword in SPAM_KEYWORDS):
        return {
            "url": url,
            "success": True,
            "title": post_data.get("title", ""),
            "notion_url": "(skipped-filtered)",
            "error_code": "FILTERED_SPAM",
            "quality_score": quality["score"],
            "failure_stage": "filter",
            "failure_reason": "spam_keywords_detected",
        }

    profile = build_content_profile(
        post_data,
        scrape_quality_score=quality["score"],
        historical_examples=top_examples,
        ranking_weights=config_mgr.get("ranking.weights", {}),
    ).to_dict()
    decision = build_review_decision(config_mgr, post_data, profile)

    if not decision["should_queue"]:
        return {
            "url": url,
            "success": True,
            "title": post_data.get("title", ""),
            "notion_url": "(skipped-filtered)",
            "error_code": "FILTERED_LOW_QUALITY",
            "quality_score": profile["scrape_quality_score"],
            "failure_stage": "filter",
            "failure_reason": decision["review_reason"],
        }

    post_data["content_profile"] = profile
    drafts, _image_prompt = await draft_generator.generate_drafts(
        post_data,
        top_tweets=top_examples,
        output_formats=config_mgr.get("output_formats", ["twitter"]),
    )
    return {
        "url": url,
        "success": True,
        "title": post_data.get("title", ""),
        "notion_url": "(dry-run)",
        "drafts_preview": str(drafts)[:160],
        "quality_score": profile["scrape_quality_score"],
        "publishability_score": profile["publishability_score"],
        "performance_score": profile["performance_score"],
        "final_rank_score": profile["final_rank_score"],
        "status": decision.get("status", "검토필요"),
    }
