"""Reprocess command: publish approved Notion items."""

from __future__ import annotations

import logging
from datetime import datetime

from pipeline.draft_analytics import record_draft_event, refresh_ml_scorer_if_needed
from pipeline.notion_retry_diagnostics import notion_retry_diagnostics
from pipeline.process_stages.runtime import extract_preferred_tweet_text

logger = logging.getLogger(__name__)

PUBLISHED_STATUS = "발행완료"


async def _update_x_publish_state(
    notion_uploader,
    page_id: str,
    *,
    x_publish_status: str,
    status: str | None = None,
    x_post_url: str | None = None,
    x_published_at: str | None = None,
    x_publish_error: str | None = None,
) -> bool:
    updates = {"x_publish_status": x_publish_status}
    if status:
        updates["status"] = status
    if x_post_url:
        updates["x_post_url"] = x_post_url
    if x_published_at:
        updates["x_published_at"] = x_published_at
    if x_publish_error is not None:
        updates["x_publish_error"] = x_publish_error
    return bool(await notion_uploader.update_page_properties(page_id, updates))


def _text_attr(obj, name: str) -> str:
    value = getattr(obj, name, "")
    return value.strip() if isinstance(value, str) else ""


def _notion_update_failure_details(notion_uploader) -> dict:
    details = {
        "notion_update_success": False,
        "operator_action_required": True,
    }
    error_code = _text_attr(notion_uploader, "last_error_code")
    error_message = _text_attr(notion_uploader, "last_error_message")
    if error_code:
        details["notion_update_error_code"] = error_code
    if error_message:
        details["notion_update_error_message"] = error_message

    details.update(notion_retry_diagnostics(notion_uploader, retry_label="the Notion X publish-state update"))
    if "notion_operator_action" not in details:
        details["notion_operator_action"] = (
            "Inspect the Notion publish-state update error, then rerun --reprocess-approved after fixing it."
        )
    return details


def _attach_notion_update_failure(result: dict, notion_uploader) -> None:
    result.update(_notion_update_failure_details(notion_uploader))


async def run_reprocess_approved(config_mgr, notion_uploader, twitter_poster, limit):
    """Re-publish Notion items with status == '승인됨'.

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

    pages = await notion_uploader.get_pages_by_status("승인됨", limit=limit)
    results = []
    for page in pages:
        record = notion_uploader.extract_page_record(page)
        page_id = record["page_id"]
        tweet_text = extract_preferred_tweet_text(
            {"twitter": record.get("tweet_body", "")},
            preferred_style=record.get("chosen_draft_type"),
        )
        if not tweet_text:
            error = "Missing tweet draft text"
            notion_update_success = await _update_x_publish_state(
                notion_uploader,
                page_id,
                x_publish_status="Blocked",
                x_publish_error=error,
            )
            result = {
                "page_id": page_id,
                "success": False,
                "error": error,
                "x_publish_status": "Blocked",
                "notion_update_success": notion_update_success,
            }
            if not notion_update_success:
                _attach_notion_update_failure(result, notion_uploader)
            results.append(result)
            continue

        twitter_url = await twitter_poster.post_tweet(text=tweet_text, image_path=None)
        if twitter_url:
            published_at = datetime.now().astimezone().isoformat()
            notion_update_success = await _update_x_publish_state(
                notion_uploader,
                page_id,
                status=PUBLISHED_STATUS,
                x_publish_status="Published",
                x_post_url=twitter_url,
                x_published_at=published_at,
                x_publish_error="",
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
                notion_page_id=page_id,
            )
            refresh_ml_scorer_if_needed()
            result = {
                "page_id": page_id,
                "success": True,
                "twitter_url": twitter_url,
                "x_publish_status": "Published",
                "x_published_at": published_at,
                "notion_update_success": notion_update_success,
            }
            if not notion_update_success:
                result["error"] = "Notion publish-state update failed after X post"
                _attach_notion_update_failure(result, notion_uploader)
            results.append(result)
        else:
            error = "Twitter post failed"
            notion_update_success = await _update_x_publish_state(
                notion_uploader,
                page_id,
                x_publish_status="Blocked",
                x_publish_error=error,
            )
            result = {
                "page_id": page_id,
                "success": False,
                "error": error,
                "x_publish_status": "Blocked",
                "notion_update_success": notion_update_success,
            }
            if not notion_update_success:
                _attach_notion_update_failure(result, notion_uploader)
            results.append(result)
    return results
