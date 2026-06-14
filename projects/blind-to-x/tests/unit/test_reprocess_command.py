"""Tests for pipeline.commands.reprocess — approved item reprocessing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.commands.reprocess import run_reprocess_approved


@pytest.fixture
def mock_deps():
    config = MagicMock()
    notion = AsyncMock()
    twitter = AsyncMock()
    twitter.enabled = True
    twitter.post_tweet = AsyncMock(return_value="https://x.com/post/123")
    notion.get_pages_by_status = AsyncMock(return_value=[])
    notion.extract_page_record = MagicMock()
    notion.update_page_properties = AsyncMock(return_value=True)
    return config, notion, twitter


@pytest.mark.asyncio
async def test_disabled_twitter_returns_empty(mock_deps):
    config, notion, twitter = mock_deps
    twitter.enabled = False
    result = await run_reprocess_approved(config, notion, twitter, limit=10)
    assert result == []


@pytest.mark.asyncio
async def test_no_approved_pages(mock_deps):
    config, notion, twitter = mock_deps
    notion.get_pages_by_status.return_value = []
    result = await run_reprocess_approved(config, notion, twitter, limit=10)
    assert result == []


@pytest.mark.asyncio
@patch("pipeline.commands.reprocess.refresh_ml_scorer_if_needed")
@patch("pipeline.commands.reprocess.record_draft_event")
async def test_successful_reprocess(mock_record, mock_refresh, mock_deps):
    config, notion, twitter = mock_deps
    page = MagicMock()
    notion.get_pages_by_status.return_value = [page]
    notion.extract_page_record.return_value = {
        "page_id": "page-1",
        "tweet_body": "Test tweet content",
        "chosen_draft_type": "twitter",
        "source": "blind",
        "topic_cluster": "tech",
        "hook_type": "question",
        "emotion_axis": "curiosity",
        "draft_style": "twitter",
        "final_rank_score": 85.0,
        "url": "https://blind.com/1",
    }

    result = await run_reprocess_approved(config, notion, twitter, limit=10)

    assert len(result) == 1
    assert result[0]["success"] is True
    assert result[0]["twitter_url"] == "https://x.com/post/123"
    assert result[0]["x_publish_status"] == "Published"
    assert result[0]["notion_update_success"] is True
    notion.update_page_properties.assert_called_once()
    page_id, updates = notion.update_page_properties.await_args.args
    assert page_id == "page-1"
    assert updates["x_publish_status"] == "Published"
    assert updates["x_post_url"] == "https://x.com/post/123"
    assert "x_published_at" in updates
    assert updates["x_publish_error"] == ""
    assert updates["status"]
    mock_record.assert_called_once()
    mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_missing_tweet_text(mock_deps):
    config, notion, twitter = mock_deps
    page = MagicMock()
    notion.get_pages_by_status.return_value = [page]
    notion.extract_page_record.return_value = {
        "page_id": "page-1",
        "tweet_body": "",
        "chosen_draft_type": None,
    }

    result = await run_reprocess_approved(config, notion, twitter, limit=10)

    assert len(result) == 1
    assert result[0]["success"] is False
    assert "Missing tweet" in result[0]["error"]
    assert result[0]["x_publish_status"] == "Blocked"
    assert result[0]["notion_update_success"] is True
    notion.update_page_properties.assert_awaited_once_with(
        "page-1",
        {
            "x_publish_status": "Blocked",
            "x_publish_error": "Missing tweet draft text",
        },
    )


@pytest.mark.asyncio
@patch("pipeline.commands.reprocess.record_draft_event")
async def test_twitter_post_failure(mock_record, mock_deps):
    config, notion, twitter = mock_deps
    page = MagicMock()
    notion.get_pages_by_status.return_value = [page]
    notion.extract_page_record.return_value = {
        "page_id": "page-1",
        "tweet_body": "Some tweet",
        "chosen_draft_type": "twitter",
    }
    twitter.post_tweet.return_value = None  # Twitter post failed

    result = await run_reprocess_approved(config, notion, twitter, limit=10)

    assert len(result) == 1
    assert result[0]["success"] is False
    assert "Twitter post failed" in result[0]["error"]
    assert result[0]["x_publish_status"] == "Blocked"
    assert result[0]["notion_update_success"] is True
    notion.update_page_properties.assert_awaited_once_with(
        "page-1",
        {
            "x_publish_status": "Blocked",
            "x_publish_error": "Twitter post failed",
        },
    )
    mock_record.assert_not_called()


@pytest.mark.asyncio
@patch("pipeline.commands.reprocess.refresh_ml_scorer_if_needed")
@patch("pipeline.commands.reprocess.record_draft_event")
async def test_successful_reprocess_reports_notion_update_failure(mock_record, mock_refresh, mock_deps):
    config, notion, twitter = mock_deps
    page = MagicMock()
    notion.get_pages_by_status.return_value = [page]
    notion.extract_page_record.return_value = {
        "page_id": "page-1",
        "tweet_body": "Test tweet content",
        "chosen_draft_type": "twitter",
        "source": "blind",
        "topic_cluster": "tech",
        "hook_type": "question",
        "emotion_axis": "curiosity",
        "draft_style": "twitter",
        "final_rank_score": 85.0,
        "url": "https://blind.com/1",
    }
    notion.update_page_properties.return_value = False
    notion.last_error_code = "NOTION_UPLOAD_FAILED"
    notion.last_error_message = "Failed to update Notion page properties: Service Overload"
    notion.last_notion_retry_report = {
        "attempt_count": 3,
        "retry_count": 2,
        "max_retries": 3,
        "final_state": "failed",
        "final_error": "Service Overload",
        "last_status": 529,
        "retryable": True,
        "attempts": [
            {
                "attempt": 3,
                "status": 529,
                "retry_after_seconds": 6,
                "retryable": True,
                "will_retry": False,
                "delay_seconds": None,
                "error_type": "HTTPStatusError",
                "error": "Service Overload",
            }
        ],
    }

    result = await run_reprocess_approved(config, notion, twitter, limit=10)

    assert len(result) == 1
    assert result[0]["success"] is True
    assert result[0]["notion_update_success"] is False
    assert result[0]["error"] == "Notion publish-state update failed after X post"
    assert result[0]["operator_action_required"] is True
    assert result[0]["notion_update_error_code"] == "NOTION_UPLOAD_FAILED"
    assert "Service Overload" in result[0]["notion_update_error_message"]
    assert result[0]["notion_retry_summary"] == {
        "final_state": "failed",
        "attempt_count": 3,
        "retry_count": 2,
        "last_status": 529,
        "retryable": True,
    }
    assert result[0]["notion_operator_action"] == (
        "Retry the Notion X publish-state update after at least 6s, then reduce request rate if it repeats."
    )
    mock_record.assert_called_once()
    mock_refresh.assert_called_once()
