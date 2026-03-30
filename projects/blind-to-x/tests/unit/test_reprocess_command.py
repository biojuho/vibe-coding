"""Tests for pipeline.commands.reprocess — approved item reprocessing."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.commands.reprocess import run_reprocess_approved


@pytest.fixture
def mock_deps():
    config = MagicMock()
    notion = AsyncMock()
    twitter = AsyncMock()
    twitter.enabled = True
    twitter.post_tweet = AsyncMock(return_value="https://x.com/post/123")
    notion.get_pages_by_review_status = AsyncMock(return_value=[])
    notion.extract_page_record = MagicMock()
    notion.update_page_properties = AsyncMock()
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
    notion.get_pages_by_review_status.return_value = []
    result = await run_reprocess_approved(config, notion, twitter, limit=10)
    assert result == []


@pytest.mark.asyncio
@patch("pipeline.commands.reprocess.refresh_ml_scorer_if_needed")
@patch("pipeline.commands.reprocess.record_draft_event")
async def test_successful_reprocess(mock_record, mock_refresh, mock_deps):
    config, notion, twitter = mock_deps
    page = MagicMock()
    notion.get_pages_by_review_status.return_value = [page]
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
    notion.update_page_properties.assert_called_once()
    mock_record.assert_called_once()
    mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_missing_tweet_text(mock_deps):
    config, notion, twitter = mock_deps
    page = MagicMock()
    notion.get_pages_by_review_status.return_value = [page]
    notion.extract_page_record.return_value = {
        "page_id": "page-1",
        "tweet_body": "",
        "chosen_draft_type": None,
    }

    result = await run_reprocess_approved(config, notion, twitter, limit=10)

    assert len(result) == 1
    assert result[0]["success"] is False
    assert "Missing tweet" in result[0]["error"]


@pytest.mark.asyncio
@patch("pipeline.commands.reprocess.record_draft_event")
async def test_twitter_post_failure(mock_record, mock_deps):
    config, notion, twitter = mock_deps
    page = MagicMock()
    notion.get_pages_by_review_status.return_value = [page]
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
    mock_record.assert_not_called()
