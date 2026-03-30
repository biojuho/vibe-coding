"""Reprocess command: publish approved Notion items."""

from __future__ import annotations

import logging

from pipeline.draft_analytics import record_draft_event, refresh_ml_scorer_if_needed
from pipeline.stages.persist import extract_preferred_tweet_text

logger = logging.getLogger(__name__)


async def run_reprocess_approved(config_mgr, notion_uploader, twitter_poster, limit):
    """Re-publish Notion items with review_status == '승인됨'.

    Args:
        config_mgr: ConfigManager instance.
        notion_uploader: NotionUploader instance.
        twitter_poster: TwitterPoster instance.
        limit: Max number of pages to process.

    Returns:
        List of result dicts with page_id and success/failure info.
    """
    if not twitter_poster.enabled:
        logger.warning("Twitter posting is disabled. Skipping approved reprocess flow.")
        return []

    pages = await notion_uploader.get_pages_by_review_status("승인됨", limit=limit)
    results = []
    for page in pages:
        record = notion_uploader.extract_page_record(page)
        tweet_text = extract_preferred_tweet_text(
            {"twitter": record.get("tweet_body", "")},
            preferred_style=record.get("chosen_draft_type"),
        )
        if not tweet_text:
            results.append(
                {
                    "page_id": record["page_id"],
                    "success": False,
                    "error": "Missing tweet draft text",
                }
            )
            continue

        twitter_url = await twitter_poster.post_tweet(text=tweet_text, image_path=None)
        if twitter_url:
            await notion_uploader.update_page_properties(
                record["page_id"],
                {
                    "status": "발행완료",
                    "review_status": "발행완료",
                },
            )
            record_draft_event(
                source=record.get("source", ""),
                topic_cluster=record.get("topic_cluster", ""),
                hook_type=record.get("hook_type", ""),
                emotion_axis=record.get("emotion_axis", ""),
                draft_style=record.get("chosen_draft_type") or record.get("draft_style") or "",
                provider_used="",
                final_rank_score=float(record.get("final_rank_score", 0.0) or 0.0),
                published=True,
                content_url=record.get("url", ""),
                notion_page_id=record["page_id"],
            )
            refresh_ml_scorer_if_needed()
            results.append({"page_id": record["page_id"], "success": True, "twitter_url": twitter_url})
        else:
            results.append({"page_id": record["page_id"], "success": False, "error": "Twitter post failed"})
    return results
