from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

import execution.content_db as cdb
import execution.notion_shorts_sync as ns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_env(monkeypatch) -> None:
    """Set both required env vars for Notion sync."""
    monkeypatch.setenv("NOTION_API_KEY", "ntn_test_key_abc123")
    monkeypatch.setenv("NOTION_SHORTS_DATABASE_ID", "db-id-1234")


def _patch_db(monkeypatch, tmp_path) -> None:
    """Initialise a temporary content_db so get_by_id / get_all work."""
    monkeypatch.setattr(cdb, "DB_PATH", tmp_path / "content.db")
    cdb.init_db()


def _make_response(status_code: int = 200, json_data=None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _sample_item(**overrides) -> dict:
    """Return a realistic content_db row dict."""
    base = {
        "id": 1,
        "topic": "Black Holes 101",
        "title": "블랙홀의 비밀",
        "channel": "science",
        "status": "success",
        "duration_sec": 35.2,
        "cost_usd": 0.85,
        "job_id": "job-abc-123",
        "youtube_status": "uploaded",
        "youtube_url": "https://youtu.be/xyz",
        "created_at": "2026-03-01 14:30:00",
        "notion_page_id": "",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------


def test_is_configured_true_when_both_set(monkeypatch):
    _patch_env(monkeypatch)
    assert ns.is_configured() is True


def test_is_configured_false_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.setenv("NOTION_SHORTS_DATABASE_ID", "db-id")
    assert ns.is_configured() is False


def test_is_configured_false_when_db_id_missing(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "ntn_key")
    monkeypatch.delenv("NOTION_SHORTS_DATABASE_ID", raising=False)
    assert ns.is_configured() is False


def test_is_configured_false_when_both_missing(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_SHORTS_DATABASE_ID", raising=False)
    assert ns.is_configured() is False


# ---------------------------------------------------------------------------
# get_db_id
# ---------------------------------------------------------------------------


def test_get_db_id_returns_id(monkeypatch):
    monkeypatch.setenv("NOTION_SHORTS_DATABASE_ID", "  my-db-id  ")
    assert ns.get_db_id() == "my-db-id"


def test_get_db_id_raises_when_empty(monkeypatch):
    monkeypatch.setenv("NOTION_SHORTS_DATABASE_ID", "   ")
    with pytest.raises(ValueError, match="NOTION_SHORTS_DATABASE_ID"):
        ns.get_db_id()


def test_get_db_id_raises_when_missing(monkeypatch):
    monkeypatch.delenv("NOTION_SHORTS_DATABASE_ID", raising=False)
    with pytest.raises(ValueError, match="NOTION_SHORTS_DATABASE_ID"):
        ns.get_db_id()


# ---------------------------------------------------------------------------
# _headers
# ---------------------------------------------------------------------------


def test_headers_contains_auth_and_version(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "ntn_secret")
    headers = ns._headers()
    assert headers["Authorization"] == "Bearer ntn_secret"
    assert headers["Content-Type"] == "application/json"
    assert headers["Notion-Version"] == ns._NOTION_VERSION


# ---------------------------------------------------------------------------
# _build_page_properties
# ---------------------------------------------------------------------------


def test_build_page_properties_normal():
    item = _sample_item()
    props = ns._build_page_properties(item)

    assert props["제목"]["title"][0]["text"]["content"] == "블랙홀의 비밀"
    assert props["주제"]["rich_text"][0]["text"]["content"] == "Black Holes 101"
    assert props["상태"]["select"]["name"] == "✅성공"
    assert props["길이(초)"]["number"] == 35.2
    assert props["비용(USD)"]["number"] == 0.85
    assert props["Job ID"]["rich_text"][0]["text"]["content"] == "job-abc-123"
    assert props["유튜브 상태"]["select"]["name"] == "업로드됨"
    assert props["채널"]["select"]["name"] == "science"
    assert props["유튜브 URL"]["url"] == "https://youtu.be/xyz"
    assert props["생성일"]["date"]["start"] == "2026-03-01"


def test_build_page_properties_missing_fields():
    """Minimal item with missing/empty fields should produce defaults."""
    item = {"id": 99}
    props = ns._build_page_properties(item)

    assert props["제목"]["title"][0]["text"]["content"] == "제목 없음"
    assert props["주제"]["rich_text"][0]["text"]["content"] == ""
    assert props["상태"]["select"]["name"] == "⏳대기"
    assert props["길이(초)"]["number"] == 0.0
    assert props["비용(USD)"]["number"] == 0.0
    assert props["유튜브 상태"]["select"]["name"] == "대기중"
    assert "채널" not in props
    assert "유튜브 URL" not in props
    assert "생성일" not in props


def test_build_page_properties_status_mapping():
    for db_status, notion_status in ns._STATUS_MAP.items():
        item = _sample_item(status=db_status)
        props = ns._build_page_properties(item)
        assert props["상태"]["select"]["name"] == notion_status


def test_build_page_properties_youtube_status_mapping():
    for yt_raw, yt_notion in ns._YT_STATUS_MAP.items():
        item = _sample_item(youtube_status=yt_raw)
        props = ns._build_page_properties(item)
        assert props["유튜브 상태"]["select"]["name"] == yt_notion

    # Unknown youtube_status → default "대기중"
    item = _sample_item(youtube_status="something_else")
    props = ns._build_page_properties(item)
    assert props["유튜브 상태"]["select"]["name"] == "대기중"


def test_build_page_properties_date_parsing_invalid():
    """Invalid date string should be silently skipped."""
    item = _sample_item(created_at="not-a-date")
    props = ns._build_page_properties(item)
    assert "생성일" not in props


def test_build_page_properties_truncation():
    """Long title/topic should be truncated to 2000 chars, job_id to 500."""
    item = _sample_item(title="A" * 3000, topic="B" * 3000, job_id="C" * 1000)
    props = ns._build_page_properties(item)

    assert len(props["제목"]["title"][0]["text"]["content"]) == 2000
    assert len(props["주제"]["rich_text"][0]["text"]["content"]) == 2000
    assert len(props["Job ID"]["rich_text"][0]["text"]["content"]) == 500


def test_build_page_properties_title_fallback_to_topic():
    """When title is empty, topic should be used."""
    item = _sample_item(title="", topic="Fallback Topic")
    props = ns._build_page_properties(item)
    assert props["제목"]["title"][0]["text"]["content"] == "Fallback Topic"


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------


def test_create_page_calls_post(monkeypatch):
    _patch_env(monkeypatch)
    item = _sample_item()
    fake_resp = _make_response(200, {"id": "notion-page-id-new"})

    with patch.object(ns, "_request", return_value=fake_resp) as mock_req:
        page_id = ns.create_page(item)

    assert page_id == "notion-page-id-new"
    mock_req.assert_called_once()
    call_args = mock_req.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "pages"
    body = call_args[1]["json"]
    assert body["parent"]["database_id"] == "db-id-1234"
    assert "제목" in body["properties"]


# ---------------------------------------------------------------------------
# update_page
# ---------------------------------------------------------------------------


def test_update_page_calls_patch(monkeypatch):
    _patch_env(monkeypatch)
    item = _sample_item()
    fake_resp = _make_response(200, {"id": "existing-page"})

    with patch.object(ns, "_request", return_value=fake_resp) as mock_req:
        result = ns.update_page("existing-page", item)

    assert result is True
    mock_req.assert_called_once()
    call_args = mock_req.call_args
    assert call_args[0][0] == "PATCH"
    assert "pages/existing-page" in call_args[0][1]
    body = call_args[1]["json"]
    assert "parent" not in body
    assert "제목" in body["properties"]


# ---------------------------------------------------------------------------
# sync_item
# ---------------------------------------------------------------------------


def test_sync_item_create_path(monkeypatch, tmp_path):
    """When item has no notion_page_id, sync_item creates a page and saves the id."""
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    row_id = cdb.add_topic("Mars", channel="science")
    cdb.update_job(row_id, status="success")

    fake_resp = _make_response(200, {"id": "new-notion-id"})
    with patch.object(ns, "_request", return_value=fake_resp):
        with patch.object(ns, "time") as mock_time:
            mock_time.sleep = MagicMock()
            result = ns.sync_item(row_id)

    assert result["action"] == "created"
    assert result["page_id"] == "new-notion-id"
    assert result["error"] == ""

    # Verify DB was updated
    updated_item = cdb.get_by_id(row_id)
    assert updated_item["notion_page_id"] == "new-notion-id"


def test_sync_item_update_path(monkeypatch, tmp_path):
    """When item already has a notion_page_id, sync_item updates the page."""
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    row_id = cdb.add_topic("Moon", channel="science")
    cdb.update_job(row_id, status="success", notion_page_id="existing-notion-page")

    fake_resp = _make_response(200, {})
    with patch.object(ns, "_request", return_value=fake_resp):
        result = ns.sync_item(row_id)

    assert result["action"] == "updated"
    assert result["page_id"] == "existing-notion-page"
    assert result["error"] == ""


def test_sync_item_not_found(monkeypatch, tmp_path):
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    result = ns.sync_item(99999)

    assert result["action"] == "skipped"
    assert "not found" in result["error"]


def test_sync_item_api_error(monkeypatch, tmp_path):
    """When _request raises (via raise_for_status), sync_item catches it."""
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    row_id = cdb.add_topic("Venus", channel="science")
    cdb.update_job(row_id, status="success")

    fake_resp = _make_response(400)
    with patch.object(ns, "_request", return_value=fake_resp):
        result = ns.sync_item(row_id)

    assert result["action"] == "error"
    assert result["error"] != ""


def test_sync_item_db_save_failure(monkeypatch, tmp_path):
    """When create_page succeeds but update_job fails, report error with page_id."""
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    row_id = cdb.add_topic("Jupiter", channel="science")
    cdb.update_job(row_id, status="success")

    fake_resp = _make_response(200, {"id": "orphan-page-id"})

    with patch.object(ns, "_request", return_value=fake_resp):
        with patch("execution.content_db.update_job", side_effect=RuntimeError("DB locked")):
            result = ns.sync_item(row_id)

    assert result["action"] == "created"
    assert result["page_id"] == "orphan-page-id"
    assert "DB 저장 실패" in result["error"]
    assert "DB locked" in result["error"]


# ---------------------------------------------------------------------------
# sync_all
# ---------------------------------------------------------------------------


def test_sync_all_creates_and_updates(monkeypatch, tmp_path):
    """sync_all iterates directly without calling get_by_id (no N+1 pattern)."""
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    # Item 1: no notion_page_id → create
    id1 = cdb.add_topic("Topic A", channel="science")
    cdb.update_job(id1, status="success")

    # Item 2: has notion_page_id → update
    id2 = cdb.add_topic("Topic B", channel="science")
    cdb.update_job(id2, status="success", notion_page_id="existing-page-b")

    fake_resp_create = _make_response(200, {"id": "new-page-a"})
    fake_resp_update = _make_response(200, {})

    call_log = []

    def mock_request(method, endpoint, **kwargs):
        call_log.append((method, endpoint))
        if method == "POST":
            return fake_resp_create
        return fake_resp_update

    with patch.object(ns, "_request", side_effect=mock_request):
        results = ns.sync_all(channel="science")

    assert len(results) == 2
    created = [r for r in results if r["action"] == "created"]
    updated = [r for r in results if r["action"] == "updated"]
    assert len(created) == 1
    assert len(updated) == 1
    assert created[0]["page_id"] == "new-page-a"
    assert updated[0]["page_id"] == "existing-page-b"

    # Verify topic is included in results
    assert any(r["topic"] == "Topic A" for r in results)
    assert any(r["topic"] == "Topic B" for r in results)


def test_sync_all_does_not_call_get_by_id(monkeypatch, tmp_path):
    """Verify sync_all iterates over get_all() results directly, NOT via sync_item/get_by_id."""
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    id1 = cdb.add_topic("Mars", channel="science")
    cdb.update_job(id1, status="success")

    fake_resp = _make_response(200, {"id": "page-1"})
    get_by_id_calls = []
    original_get_by_id = cdb.get_by_id

    def spying_get_by_id(item_id):
        get_by_id_calls.append(item_id)
        return original_get_by_id(item_id)

    with patch.object(ns, "_request", return_value=fake_resp):
        with patch("execution.content_db.get_by_id", side_effect=spying_get_by_id):
            ns.sync_all()

    assert get_by_id_calls == [], "sync_all must NOT call get_by_id (N+1 anti-pattern)"


def test_sync_all_filters_by_since(monkeypatch, tmp_path):
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    id_old = cdb.add_topic("Old Topic", channel="science")
    id_new = cdb.add_topic("New Topic", channel="science")

    # Manually set created_at timestamps
    with cdb._conn() as conn:
        conn.execute("UPDATE content_queue SET created_at = ? WHERE id = ?", ("2026-01-01 00:00:00", id_old))
        conn.execute("UPDATE content_queue SET created_at = ? WHERE id = ?", ("2026-03-02 00:00:00", id_new))

    fake_resp = _make_response(200, {"id": "new-page"})
    with patch.object(ns, "_request", return_value=fake_resp):
        results = ns.sync_all(since="2026-03-01")

    assert len(results) == 1
    assert results[0]["item_id"] == id_new


def test_sync_all_filters_by_status(monkeypatch, tmp_path):
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    id_success = cdb.add_topic("Good Topic", channel="science")
    cdb.update_job(id_success, status="success")

    id_failed = cdb.add_topic("Bad Topic", channel="science")
    cdb.update_job(id_failed, status="failed")

    fake_resp = _make_response(200, {"id": "new-page"})
    with patch.object(ns, "_request", return_value=fake_resp):
        results = ns.sync_all(status="success")

    assert len(results) == 1
    assert results[0]["item_id"] == id_success


def test_sync_all_api_error_per_item(monkeypatch, tmp_path):
    """One item failing should not block the rest."""
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    cdb.add_topic("Topic OK", channel="science")
    cdb.add_topic("Topic Fail", channel="science")

    call_count = 0

    def mock_request(method, endpoint, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First item: raise
            resp = _make_response(500)
            return resp
        # Second item: succeed
        return _make_response(200, {"id": "page-ok"})

    with patch.object(ns, "_request", side_effect=mock_request):
        results = ns.sync_all()

    assert len(results) == 2
    errors = [r for r in results if r["action"] == "error"]
    created = [r for r in results if r["action"] == "created"]
    assert len(errors) == 1
    assert len(created) == 1


def test_sync_all_db_save_failure_in_batch(monkeypatch, tmp_path):
    """When update_job fails during sync_all, the error is recorded but iteration continues."""
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    cdb.add_topic("Topic X", channel="science")

    fake_resp = _make_response(200, {"id": "page-x"})

    with patch.object(ns, "_request", return_value=fake_resp):
        with patch("execution.content_db.update_job", side_effect=RuntimeError("disk full")):
            results = ns.sync_all()

    assert len(results) == 1
    assert results[0]["action"] == "created"
    assert "DB 저장 실패" in results[0]["error"]


def test_sync_all_channel_filter(monkeypatch, tmp_path):
    _patch_env(monkeypatch)
    _patch_db(monkeypatch, tmp_path)

    cdb.add_topic("Science Topic", channel="science")
    cdb.add_topic("History Topic", channel="history")

    fake_resp = _make_response(200, {"id": "page-1"})
    with patch.object(ns, "_request", return_value=fake_resp):
        results = ns.sync_all(channel="history")

    assert len(results) == 1
    assert results[0]["topic"] == "History Topic"


# ---------------------------------------------------------------------------
# _request (verify it assembles URL, calls requests, and sleeps)
# ---------------------------------------------------------------------------


def test_request_assembles_url_and_sleeps(monkeypatch):
    _patch_env(monkeypatch)
    fake_resp = _make_response(200, {"ok": True})

    with patch("execution.notion_shorts_sync.requests.request", return_value=fake_resp) as mock_req:
        with patch("execution.notion_shorts_sync.time.sleep") as mock_sleep:
            resp = ns._request("GET", "/databases/abc")

    mock_req.assert_called_once()
    call_args = mock_req.call_args
    assert call_args[0][0] == "GET"
    assert call_args[0][1] == "https://api.notion.com/v1/databases/abc"
    assert call_args[1]["timeout"] == 30
    mock_sleep.assert_called_once_with(ns._RATE_LIMIT_DELAY)
    assert resp.json() == {"ok": True}


# ---------------------------------------------------------------------------
# CLI (_cli)
# ---------------------------------------------------------------------------


def test_cli_item_id_prints_result(monkeypatch, capsys):
    _patch_env(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["notion_shorts_sync.py", "--item-id", "42"],
    )
    monkeypatch.setattr(
        ns,
        "sync_item",
        lambda item_id: {"action": "created", "page_id": "page-abc", "error": ""},
    )

    ns._cli()

    output = capsys.readouterr().out
    assert "[Notion]" in output
    assert "created" in output


def test_cli_all_prints_summary(monkeypatch, capsys):
    _patch_env(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["notion_shorts_sync.py", "--all", "--channel", "science", "--since", "2026-03-01", "--status", "success"],
    )
    monkeypatch.setattr(
        ns,
        "sync_all",
        lambda channel=None, since=None, status=None: [
            {"action": "created", "page_id": "p1", "error": "", "item_id": 1, "topic": "T1"},
            {"action": "error", "page_id": "", "error": "boom", "item_id": 2, "topic": "T2"},
        ],
    )

    ns._cli()

    output = capsys.readouterr().out
    assert "동기화 완료" in output
    assert "생성 1" in output
    assert "오류 1" in output
    assert "ERROR" in output
    assert "boom" in output


def test_cli_exits_when_not_configured(monkeypatch, capsys):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_SHORTS_DATABASE_ID", raising=False)
    monkeypatch.setattr(sys, "argv", ["notion_shorts_sync.py", "--all"])

    with pytest.raises(SystemExit) as exc_info:
        ns._cli()

    assert exc_info.value.code == 1
    assert "ERROR" in capsys.readouterr().out
