from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import execution.youtube_analytics_collector as yac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_youtube_service(response_items: list[dict] | None = None):
    """Build a fake YouTube Data API v3 service object."""
    service = MagicMock()
    response = {"items": response_items or []}
    service.videos.return_value.list.return_value.execute.return_value = response
    return service


# ---------------------------------------------------------------------------
# _build_youtube_service
# ---------------------------------------------------------------------------


def test_build_youtube_service_raises_when_token_missing(monkeypatch):
    monkeypatch.setattr(yac.os.path, "exists", lambda _path: False)

    with pytest.raises(FileNotFoundError, match="OAuth"):
        yac._build_youtube_service()


def test_build_youtube_service_refreshes_expired_token(monkeypatch):
    monkeypatch.setattr(yac.os.path, "exists", lambda _path: True)

    creds = MagicMock()
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "refresh-tok"

    monkeypatch.setattr(
        yac.Credentials,
        "from_authorized_user_file",
        lambda _path, _scopes: creds,
    )
    built_service = MagicMock()
    monkeypatch.setattr(yac, "build", lambda *a, **kw: built_service)

    result = yac._build_youtube_service()

    creds.refresh.assert_called_once()
    assert result is built_service


def test_build_youtube_service_raises_when_no_refresh_token(monkeypatch):
    monkeypatch.setattr(yac.os.path, "exists", lambda _path: True)

    creds = MagicMock()
    creds.valid = False
    creds.expired = True
    creds.refresh_token = None

    monkeypatch.setattr(
        yac.Credentials,
        "from_authorized_user_file",
        lambda _path, _scopes: creds,
    )

    with pytest.raises(RuntimeError, match="refresh 불가"):
        yac._build_youtube_service()


def test_build_youtube_service_raises_when_not_expired_but_invalid(monkeypatch):
    """Token is not valid AND not expired (edge case) => RuntimeError."""
    monkeypatch.setattr(yac.os.path, "exists", lambda _path: True)

    creds = MagicMock()
    creds.valid = False
    creds.expired = False

    monkeypatch.setattr(
        yac.Credentials,
        "from_authorized_user_file",
        lambda _path, _scopes: creds,
    )

    with pytest.raises(RuntimeError, match="refresh 불가"):
        yac._build_youtube_service()


def test_build_youtube_service_returns_service_when_valid(monkeypatch):
    monkeypatch.setattr(yac.os.path, "exists", lambda _path: True)

    creds = MagicMock()
    creds.valid = True

    monkeypatch.setattr(
        yac.Credentials,
        "from_authorized_user_file",
        lambda _path, _scopes: creds,
    )
    built_service = MagicMock()
    monkeypatch.setattr(yac, "build", lambda *a, **kw: built_service)

    result = yac._build_youtube_service()
    assert result is built_service


# ---------------------------------------------------------------------------
# fetch_video_stats
# ---------------------------------------------------------------------------


def test_fetch_video_stats_returns_parsed_stats(monkeypatch):
    items = [
        {
            "id": "vid-1",
            "statistics": {"viewCount": "100", "likeCount": "10", "commentCount": "2"},
        },
        {
            "id": "vid-2",
            "statistics": {"viewCount": "200", "likeCount": "20", "commentCount": "5"},
        },
    ]
    monkeypatch.setattr(yac, "_build_youtube_service", lambda: _fake_youtube_service(items))

    result = yac.fetch_video_stats(["vid-1", "vid-2"])

    assert result["vid-1"] == {"views": 100, "likes": 10, "comments": 2}
    assert result["vid-2"] == {"views": 200, "likes": 20, "comments": 5}


def test_fetch_video_stats_empty_list(monkeypatch):
    monkeypatch.setattr(yac, "_build_youtube_service", lambda: _fake_youtube_service())

    result = yac.fetch_video_stats([])

    assert result == {}


def test_fetch_video_stats_handles_missing_statistics(monkeypatch):
    """Video returned by API but with empty statistics dict."""
    items = [{"id": "vid-1", "statistics": {}}]
    monkeypatch.setattr(yac, "_build_youtube_service", lambda: _fake_youtube_service(items))

    result = yac.fetch_video_stats(["vid-1"])

    assert result["vid-1"] == {"views": 0, "likes": 0, "comments": 0}


def test_fetch_video_stats_batches_over_50(monkeypatch):
    """Verify batching: 75 IDs should result in 2 API calls (50 + 25)."""
    service = MagicMock()
    call_count = {"n": 0}

    def fake_execute():
        call_count["n"] += 1
        return {"items": []}

    service.videos.return_value.list.return_value.execute = fake_execute
    monkeypatch.setattr(yac, "_build_youtube_service", lambda: service)

    ids = [f"vid-{i}" for i in range(75)]
    yac.fetch_video_stats(ids)

    assert call_count["n"] == 2


def test_fetch_video_stats_video_not_returned_by_api(monkeypatch):
    """API returns fewer items than requested: missing IDs are not in result."""
    items = [
        {"id": "vid-1", "statistics": {"viewCount": "50", "likeCount": "5", "commentCount": "1"}},
    ]
    monkeypatch.setattr(yac, "_build_youtube_service", lambda: _fake_youtube_service(items))

    result = yac.fetch_video_stats(["vid-1", "vid-2", "vid-3"])

    assert "vid-1" in result
    assert "vid-2" not in result
    assert "vid-3" not in result


# ---------------------------------------------------------------------------
# collect_and_update
# ---------------------------------------------------------------------------


def test_collect_and_update_normal_flow(monkeypatch):
    """Happy path: 2 uploaded items, both updated successfully."""
    fake_items = [
        {"id": 1, "youtube_status": "uploaded", "youtube_video_id": "vid-A"},
        {"id": 2, "youtube_status": "uploaded", "youtube_video_id": "vid-B"},
        {"id": 3, "youtube_status": "pending", "youtube_video_id": ""},
    ]
    init_calls = []
    update_calls = []

    monkeypatch.setattr("execution.content_db.init_db", lambda: init_calls.append(1))
    monkeypatch.setattr("execution.content_db.get_all", lambda channel=None: fake_items)
    monkeypatch.setattr(
        "execution.content_db.update_job",
        lambda row_id, **kw: update_calls.append((row_id, kw)),
    )
    monkeypatch.setattr(
        yac,
        "fetch_video_stats",
        lambda video_ids: {
            "vid-A": {"views": 100, "likes": 10, "comments": 1},
            "vid-B": {"views": 200, "likes": 20, "comments": 2},
        },
    )

    result = yac.collect_and_update(channel="test")

    assert init_calls == [1]
    assert result["updated"] == 2
    assert result["skipped"] == 0
    assert result["errors"] == []
    assert len(update_calls) == 2
    assert update_calls[0][0] == 1
    assert update_calls[0][1]["yt_views"] == 100
    assert update_calls[1][0] == 2
    assert update_calls[1][1]["yt_likes"] == 20


def test_collect_and_update_no_uploadable_items(monkeypatch):
    """No items with youtube_status=uploaded should return early."""
    monkeypatch.setattr("execution.content_db.init_db", lambda: None)
    monkeypatch.setattr(
        "execution.content_db.get_all",
        lambda channel=None: [
            {"id": 1, "youtube_status": "pending", "youtube_video_id": ""},
        ],
    )

    result = yac.collect_and_update()

    assert result == {"updated": 0, "skipped": 0, "errors": []}


def test_collect_and_update_api_error(monkeypatch):
    """fetch_video_stats raises => all items become skipped, error recorded."""
    fake_items = [
        {"id": 1, "youtube_status": "uploaded", "youtube_video_id": "vid-X"},
        {"id": 2, "youtube_status": "uploaded", "youtube_video_id": "vid-Y"},
    ]
    monkeypatch.setattr("execution.content_db.init_db", lambda: None)
    monkeypatch.setattr("execution.content_db.get_all", lambda channel=None: fake_items)

    def boom(_ids):
        raise RuntimeError("API quota exceeded")

    monkeypatch.setattr(yac, "fetch_video_stats", boom)

    result = yac.collect_and_update()

    assert result["updated"] == 0
    assert result["skipped"] == 2
    assert len(result["errors"]) == 1
    assert "API quota exceeded" in result["errors"][0]


def test_collect_and_update_db_update_error_per_item(monkeypatch):
    """update_job raises for one item but succeeds for another."""
    fake_items = [
        {"id": 1, "youtube_status": "uploaded", "youtube_video_id": "vid-OK"},
        {"id": 2, "youtube_status": "uploaded", "youtube_video_id": "vid-ERR"},
    ]
    monkeypatch.setattr("execution.content_db.init_db", lambda: None)
    monkeypatch.setattr("execution.content_db.get_all", lambda channel=None: fake_items)
    monkeypatch.setattr(
        yac,
        "fetch_video_stats",
        lambda _ids: {
            "vid-OK": {"views": 10, "likes": 1, "comments": 0},
            "vid-ERR": {"views": 20, "likes": 2, "comments": 1},
        },
    )

    def fake_update(row_id, **kw):
        if row_id == 2:
            raise sqlite3_error("DB locked")

    import sqlite3 as sqlite3_mod
    sqlite3_error = sqlite3_mod.OperationalError

    monkeypatch.setattr("execution.content_db.update_job", fake_update)

    result = yac.collect_and_update()

    assert result["updated"] == 1
    assert len(result["errors"]) == 1
    assert "id=2" in result["errors"][0]
    assert result["skipped"] == 0  # 2 uploaded - 1 updated - 1 error = 0


def test_collect_and_update_video_not_in_stats(monkeypatch):
    """Video ID in DB but not returned by API stats => skipped (no error)."""
    fake_items = [
        {"id": 1, "youtube_status": "uploaded", "youtube_video_id": "vid-GONE"},
    ]
    monkeypatch.setattr("execution.content_db.init_db", lambda: None)
    monkeypatch.setattr("execution.content_db.get_all", lambda channel=None: fake_items)
    monkeypatch.setattr(yac, "fetch_video_stats", lambda _ids: {})

    result = yac.collect_and_update()

    assert result["updated"] == 0
    assert result["skipped"] == 1
    assert result["errors"] == []


def test_collect_and_update_passes_channel_to_get_all(monkeypatch):
    """Verify channel parameter is forwarded to content_db.get_all."""
    captured_channels = []

    monkeypatch.setattr("execution.content_db.init_db", lambda: None)
    monkeypatch.setattr(
        "execution.content_db.get_all",
        lambda channel=None: captured_channels.append(channel) or [],
    )

    yac.collect_and_update(channel="science")

    assert captured_channels == ["science"]
