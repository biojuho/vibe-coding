"""Unit tests for execution/result_tracker_db.py (T-115 — TDR reduction).

Uses a temp-path DB so production data is never touched.
Covers:
- init_db / _conn
- extract_youtube_video_id (pure, no DB)
- add_content (insert + duplicate skip)
- get_all (no filter, platform filter, channel filter)
- get_by_id (found + not found)
- update_stats + stats_history
- update_manual_stats (partial kwargs, missing id)
- delete_content
- get_stats_history
- get_platform_summary / get_channel_summary / get_top_content / get_daily_trend
- collect_youtube_stats (no API key fast-path + no items + API success mocked)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import execution.result_tracker_db as rtdb
from execution.result_tracker_db import (
    add_content,
    collect_youtube_stats,
    delete_content,
    extract_youtube_video_id,
    get_all,
    get_by_id,
    get_channel_summary,
    get_daily_trend,
    get_platform_summary,
    get_stats_history,
    get_top_content,
    init_db,
    update_manual_stats,
    update_stats,
)


# ---------------------------------------------------------------------------
# Fixture: redirect DB_PATH to a temp directory
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    """Redirect DB_PATH so every test gets a fresh, isolated SQLite database."""
    tmp_db = tmp_path / "result_tracker.db"
    monkeypatch.setattr(rtdb, "DB_PATH", tmp_db)
    init_db()
    yield tmp_db


# ---------------------------------------------------------------------------
# extract_youtube_video_id (pure — no DB)
# ---------------------------------------------------------------------------


class TestExtractYoutubeVideoId:
    def test_watch_url(self):
        assert extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_youtube_video_id("https://www.youtube.com/shorts/abc12345678") == "abc12345678"

    def test_youtu_be_url(self):
        assert extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_youtube_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_non_youtube_url_returns_empty(self):
        assert extract_youtube_video_id("https://vimeo.com/12345") == ""

    def test_empty_string(self):
        assert extract_youtube_video_id("") == ""


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(_tmp_db):
    import sqlite3

    conn = sqlite3.connect(str(_tmp_db))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "published_content" in tables
    assert "stats_history" in tables


def test_init_db_idempotent(_tmp_db):
    """Calling init_db twice should not raise."""
    init_db()


# ---------------------------------------------------------------------------
# add_content
# ---------------------------------------------------------------------------


class TestAddContent:
    def test_insert_returns_id(self):
        row_id = add_content("youtube", "https://youtu.be/dQw4w9WgXcQ", "Rick Roll")
        assert isinstance(row_id, int)
        assert row_id > 0

    def test_duplicate_url_returns_existing_id(self):
        id1 = add_content("youtube", "https://youtu.be/dup12345678", "First")
        id2 = add_content("youtube", "https://youtu.be/dup12345678", "Second (same url)")
        assert id1 == id2

    def test_video_id_extracted_for_youtube(self):
        add_content("youtube", "https://www.youtube.com/watch?v=abc12345678", "Test")
        items = get_all(platform="youtube")
        assert items[0]["video_id"] == "abc12345678"

    def test_non_youtube_no_video_id(self):
        add_content("x", "https://twitter.com/i/status/1", "Tweet")
        items = get_all(platform="x")
        assert items[0]["video_id"] == ""

    def test_published_at_defaults_to_today(self):
        add_content("blog", "https://blog.example.com", "Post")
        items = get_all(platform="blog")
        assert items[0]["published_at"]  # non-empty


# ---------------------------------------------------------------------------
# get_all / get_by_id
# ---------------------------------------------------------------------------


class TestGetAll:
    def test_returns_all_without_filter(self):
        add_content("youtube", "https://youtu.be/aaa12345678", "A")
        add_content("x", "https://x.com/1", "B")
        assert len(get_all()) == 2

    def test_platform_filter(self):
        add_content("youtube", "https://youtu.be/bbb12345678", "YT")
        add_content("x", "https://x.com/2", "X")
        result = get_all(platform="youtube")
        assert all(r["platform"] == "youtube" for r in result)

    def test_channel_filter(self):
        add_content("youtube", "https://youtu.be/ccc12345678", "Science", channel="science_ch")
        add_content("youtube", "https://youtu.be/ddd12345678", "Space", channel="space_ch")
        result = get_all(channel="science_ch")
        assert len(result) == 1
        assert result[0]["channel"] == "science_ch"

    def test_empty_returns_empty_list(self):
        assert get_all() == []


class TestGetById:
    def test_found(self):
        row_id = add_content("youtube", "https://youtu.be/eid12345678", "Found")
        item = get_by_id(row_id)
        assert item is not None
        assert item["title"] == "Found"

    def test_not_found_returns_none(self):
        assert get_by_id(99999) is None


# ---------------------------------------------------------------------------
# update_stats / stats_history
# ---------------------------------------------------------------------------


class TestUpdateStats:
    def test_updates_fields(self):
        row_id = add_content("youtube", "https://youtu.be/upd12345678", "Update Me")
        update_stats(row_id, views=100, likes=10, comments=2)
        item = get_by_id(row_id)
        assert item["views"] == 100
        assert item["likes"] == 10

    def test_history_recorded(self):
        row_id = add_content("youtube", "https://youtu.be/his12345678", "History")
        update_stats(row_id, views=50)
        update_stats(row_id, views=80)
        history = get_stats_history(row_id)
        assert len(history) == 2
        assert history[0]["views"] == 50
        assert history[1]["views"] == 80


# ---------------------------------------------------------------------------
# update_manual_stats
# ---------------------------------------------------------------------------


class TestUpdateManualStats:
    def test_partial_update(self):
        row_id = add_content("x", "https://x.com/100", "Tweet", channel="ch")
        update_stats(row_id, views=5)
        update_manual_stats(row_id, likes=3)
        item = get_by_id(row_id)
        assert item["likes"] == 3
        # views should remain 5
        assert item["views"] == 5

    def test_unknown_keys_ignored(self):
        row_id = add_content("x", "https://x.com/101", "T2")
        update_manual_stats(row_id, nonexistent_field=99)
        item = get_by_id(row_id)
        assert item is not None

    def test_missing_content_id_no_error(self):
        """Should silently do nothing when id does not exist."""
        update_manual_stats(99999, likes=5)  # no exception expected


# ---------------------------------------------------------------------------
# delete_content
# ---------------------------------------------------------------------------


class TestDeleteContent:
    def test_delete_removes_content_and_history(self):
        row_id = add_content("youtube", "https://youtu.be/del12345678", "Delete Me")
        update_stats(row_id, views=10)
        delete_content(row_id)
        assert get_by_id(row_id) is None
        assert get_stats_history(row_id) == []


# ---------------------------------------------------------------------------
# Aggregate queries
# ---------------------------------------------------------------------------


class TestAggregates:
    def _seed(self):
        id1 = add_content("youtube", "https://youtu.be/ag112345678", "A", channel="science")
        id2 = add_content("youtube", "https://youtu.be/ag212345678", "B", channel="space")
        id3 = add_content("x", "https://x.com/200", "C", channel="science")
        update_stats(id1, views=100, likes=5)
        update_stats(id2, views=200, likes=10)
        update_stats(id3, impressions=50)
        return id1, id2, id3

    def test_get_platform_summary(self):
        self._seed()
        summary = get_platform_summary()
        platforms = {r["platform"] for r in summary}
        assert "youtube" in platforms

    def test_get_channel_summary(self):
        self._seed()
        summary = get_channel_summary()
        channels = {r["channel"] for r in summary}
        assert "science" in channels or "space" in channels

    def test_get_top_content(self):
        self._seed()
        top = get_top_content(limit=1)
        assert len(top) == 1
        assert top[0]["views"] == 200  # "B" has highest views

    def test_get_daily_trend(self):
        self._seed()
        trend = get_daily_trend(days=30)
        total_views = sum(r["total_views"] for r in trend)
        assert total_views >= 300  # 100 + 200

    def test_empty_top_content(self):
        assert get_top_content() == []


# ---------------------------------------------------------------------------
# collect_youtube_stats
# ---------------------------------------------------------------------------


class TestCollectYoutubeStats:
    def test_no_api_key_returns_error(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "")
        result = collect_youtube_stats()
        assert "error" in result

    def test_no_youtube_items(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "fake_key")
        add_content("x", "https://x.com/300", "Only X")
        result = collect_youtube_stats()
        assert result["updated"] == 0

    def test_api_success_mocked(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "fake_key")
        row_id = add_content("youtube", "https://youtu.be/api12345678", "YT Video")
        # Verify the video_id was stored
        item = get_by_id(row_id)
        assert item["video_id"] == "api12345678"

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "items": [
                {
                    "id": "api12345678",
                    "statistics": {"viewCount": "999", "likeCount": "88", "commentCount": "12"},
                }
            ]
        }

        with patch("execution.result_tracker_db.requests.get", return_value=fake_response):
            result = collect_youtube_stats()

        assert result["updated"] == 1
        updated = get_by_id(row_id)
        assert updated["views"] == 999
        assert updated["likes"] == 88

    def test_api_error_status_continues(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "fake_key")
        add_content("youtube", "https://youtu.be/err12345678", "Error Video")
        fake_response = MagicMock()
        fake_response.status_code = 403
        fake_response.text = "Quota exceeded"

        with patch("execution.result_tracker_db.requests.get", return_value=fake_response):
            result = collect_youtube_stats()

        assert result["updated"] == 0
