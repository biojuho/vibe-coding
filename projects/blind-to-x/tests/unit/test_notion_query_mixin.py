from __future__ import annotations

from datetime import UTC, datetime, timedelta
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.notion._query import NotionQueryMixin  # noqa: E402


class FakeQueryHost(NotionQueryMixin):
    DEFAULT_PROPS = [
        "title",
        "tweet_body",
        "chosen_draft_type",
        "views",
        "likes",
        "retweets",
        "published_at",
        "date",
        "final_rank_score",
        "topic_cluster",
        "hook_type",
        "emotion_axis",
        "status",
    ]

    def __init__(self):
        self.props = {key: key for key in self.DEFAULT_PROPS}
        self._db_properties = {
            "title": {"type": "title"},
            "status": {"type": "status"},
            "views": {"type": "number"},
        }
        self.database_id = "db123"
        self.client = AsyncMock()
        self._ensure_schema_result = True
        self.query_response = {"results": []}
        self.last_query_kwargs = None

    async def ensure_schema(self):
        return self._ensure_schema_result

    async def query_collection(self, **kwargs):
        self.last_query_kwargs = kwargs
        return self.query_response


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _page_with_properties(**properties):
    return {"id": "page-1", "url": "https://notion.so/page-1", "properties": properties}


def test_get_page_property_value_supports_common_notion_types():
    host = FakeQueryHost()
    page = _page_with_properties(
        title={"type": "title", "title": [{"plain_text": "Hello"}]},
        tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "Body"}]},
        views={"type": "number", "number": 123},
        checked={"type": "checkbox", "checkbox": True},
        link={"type": "url", "url": "https://example.com"},
        status={"type": "status", "status": {"name": "Approved"}},
        stage={"type": "select", "select": {"name": "Draft"}},
        published_at={"type": "date", "date": {"start": "2026-03-31"}},
    )

    assert host.get_page_property_value(page, "title") == "Hello"
    assert host.get_page_property_value(page, "tweet_body") == "Body"
    assert host.get_page_property_value(page, "views") == 123
    assert host.get_page_property_value(page, "checked") is True
    assert host.get_page_property_value(page, "link") == "https://example.com"
    assert host.get_page_property_value(page, "status") == "Approved"
    assert host.get_page_property_value(page, "stage") == "Draft"
    assert host.get_page_property_value(page, "published_at") == "2026-03-31"
    assert host.get_page_property_value(page, "missing", default="fallback") == "fallback"


def test_extract_page_record_maps_core_fields():
    host = FakeQueryHost()
    page = _page_with_properties(
        title={"type": "title", "title": [{"plain_text": "Post"}]},
        tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "Tweet text"}]},
        chosen_draft_type={"type": "rich_text", "rich_text": [{"plain_text": "story"}]},
        views={"type": "number", "number": 100},
    )

    record = host.extract_page_record(page)

    assert record["page_id"] == "page-1"
    assert record["page_url"] == "https://notion.so/page-1"
    assert record["text"] == "Tweet text"
    assert record["draft_style"] == "story"
    assert record["views"] == 100


@pytest.mark.asyncio
async def test_get_top_performing_posts_filters_and_sorts_recent_results():
    host = FakeQueryHost()
    recent = _now_iso()
    stale = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    host.query_response = {
        "results": [
            _page_with_properties(
                tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "stale"}]},
                chosen_draft_type={"type": "rich_text", "rich_text": [{"plain_text": "story"}]},
                views={"type": "number", "number": 999},
                likes={"type": "number", "number": 1},
                retweets={"type": "number", "number": 1},
                published_at={"type": "date", "date": {"start": stale}},
            ),
            _page_with_properties(
                tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "second"}]},
                chosen_draft_type={"type": "rich_text", "rich_text": [{"plain_text": "story"}]},
                views={"type": "number", "number": 50},
                likes={"type": "number", "number": 30},
                retweets={"type": "number", "number": 2},
                published_at={"type": "date", "date": {"start": recent}},
            ),
            _page_with_properties(
                tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "top"}]},
                chosen_draft_type={"type": "rich_text", "rich_text": [{"plain_text": "question"}]},
                views={"type": "number", "number": 100},
                likes={"type": "number", "number": 10},
                retweets={"type": "number", "number": 5},
                published_at={"type": "date", "date": {"start": recent}},
            ),
        ]
    }

    records = await host.get_top_performing_posts(limit=2, lookback_days=30, minimum_posts=0)

    assert [item["text"] for item in records] == ["top", "second"]
    assert host.last_query_kwargs == {
        "filter": {"property": "views", "number": {"greater_than": 0}},
        "page_size": 20,
    }


@pytest.mark.asyncio
async def test_get_top_performing_posts_uses_fallback_examples_when_needed():
    host = FakeQueryHost()
    host.query_response = {
        "results": [
            _page_with_properties(
                tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "only"}]},
                views={"type": "number", "number": 5},
                published_at={"type": "date", "date": {"start": _now_iso()}},
            )
        ]
    }
    host.get_recent_approved_posts = AsyncMock(return_value=[{"text": "fallback-1"}, {"text": "fallback-2"}])

    records = await host.get_top_performing_posts(limit=1, minimum_posts=2, allow_fallback_examples=True)

    assert records == [{"text": "fallback-1"}]


@pytest.mark.asyncio
async def test_get_recent_approved_posts_filters_empty_or_stale_records():
    host = FakeQueryHost()
    recent = _now_iso()
    older = (datetime.now(UTC) - timedelta(days=45)).isoformat()
    host.get_pages_by_status = AsyncMock(
        return_value=[
            _page_with_properties(
                tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "recent"}]},
                final_rank_score={"type": "number", "number": 70},
                published_at={"type": "date", "date": {"start": recent}},
            ),
            _page_with_properties(
                tweet_body={"type": "rich_text", "rich_text": [{"plain_text": ""}]},
                final_rank_score={"type": "number", "number": 99},
                published_at={"type": "date", "date": {"start": recent}},
            ),
            _page_with_properties(
                tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "old"}]},
                final_rank_score={"type": "number", "number": 90},
                published_at={"type": "date", "date": {"start": older}},
            ),
        ]
    )

    records = await host.get_recent_approved_posts(limit=2, lookback_days=30)

    assert [item["text"] for item in records] == ["recent"]


@pytest.mark.asyncio
async def test_get_top_performing_tweets_shapes_output_defaults():
    host = FakeQueryHost()
    host.get_top_performing_posts = AsyncMock(return_value=[{"views": 10, "text": "hello"}])

    tweets = await host.get_top_performing_tweets(limit=1)

    assert tweets[0]["views"] == 10
    assert tweets[0]["text"] == "hello"
    assert tweets[0]["topic_cluster"]
    assert tweets[0]["hook_type"]
    assert tweets[0]["emotion_axis"]
    assert tweets[0]["draft_style"]


@pytest.mark.asyncio
async def test_get_pages_by_status_switches_between_status_and_select_filters():
    host = FakeQueryHost()
    host.query_response = {"results": [{"id": "page-1"}]}

    await host.get_pages_by_status("Approved", limit=3)
    assert host.last_query_kwargs == {
        "filter": {"property": "status", "status": {"equals": "Approved"}},
        "page_size": 3,
    }

    host._db_properties["status"]["type"] = "select"
    await host.get_pages_by_status("Queued", limit=2)
    assert host.last_query_kwargs == {
        "filter": {"property": "status", "select": {"equals": "Queued"}},
        "page_size": 2,
    }


@pytest.mark.asyncio
async def test_search_pages_by_title_and_recent_pages_filters_results():
    host = FakeQueryHost()
    host.query_response = {"results": [{"id": "match"}]}
    host.client.search.return_value = {
        "results": [
            {
                "id": "keep-db",
                "parent": {"type": "database_id", "database_id": "db-123"},
                "created_time": _now_iso(),
            },
            {
                "id": "keep-data-source",
                "parent": {"type": "data_source_id", "data_source_id": "db123"},
                "created_time": _now_iso(),
            },
            {
                "id": "drop-old",
                "parent": {"type": "database_id", "database_id": "db123"},
                "created_time": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
            },
            {
                "id": "drop-other-parent",
                "parent": {"type": "database_id", "database_id": "other"},
                "created_time": _now_iso(),
            },
        ]
    }

    search_results = await host.search_pages_by_title("career", limit=5)
    recent_pages = await host.get_recent_pages(days=7, limit=10)

    assert search_results == [{"id": "match"}]
    assert host.last_query_kwargs == {
        "filter": {"property": "title", "title": {"contains": "career"}},
        "page_size": 5,
    }
    assert [page["id"] for page in recent_pages] == ["keep-db", "keep-data-source"]


@pytest.mark.asyncio
async def test_search_pages_by_title_handles_query_failure_and_fetch_recent_records_maps_pages():
    host = FakeQueryHost()
    host.query_collection = AsyncMock(side_effect=RuntimeError("boom"))
    host.get_recent_pages = AsyncMock(
        return_value=[_page_with_properties(tweet_body={"type": "rich_text", "rich_text": [{"plain_text": "mapped"}]})]
    )

    assert await host.search_pages_by_title("career", limit=5) == []

    records = await host.fetch_recent_records(lookback_days=14, limit=10)
    assert records[0]["text"] == "mapped"
