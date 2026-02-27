from __future__ import annotations

from unittest.mock import MagicMock, patch

import execution.notion_client as nc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int = 200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


def _configure(monkeypatch, api_key="fake-notion-key-for-tests", db_id="db_abc123"):
    monkeypatch.setattr(nc, "NOTION_API_KEY", api_key)
    monkeypatch.setattr(nc, "NOTION_TASK_DB", db_id)
    monkeypatch.setattr(nc, "NOTION_TASK_TITLE_PROPERTY", None)
    monkeypatch.setattr(nc, "NOTION_TASK_STATUS_PROPERTY", None)
    monkeypatch.setattr(nc, "NOTION_TASK_DUE_PROPERTY", None)
    nc._get_database_schema.cache_clear()


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------

def test_is_configured_true(monkeypatch):
    _configure(monkeypatch)
    assert nc.is_configured() is True


def test_is_configured_false_no_key(monkeypatch):
    monkeypatch.setattr(nc, "NOTION_API_KEY", "")
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "db_abc")
    assert nc.is_configured() is False


def test_is_configured_false_no_db(monkeypatch):
    monkeypatch.setattr(nc, "NOTION_API_KEY", "ntn_key")
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "")
    assert nc.is_configured() is False


# ---------------------------------------------------------------------------
# _headers
# ---------------------------------------------------------------------------

def test_headers_contain_auth_and_version(monkeypatch):
    monkeypatch.setattr(nc, "NOTION_API_KEY", "ntn_mykey")
    headers = nc._headers()
    assert headers["Authorization"] == "Bearer ntn_mykey"
    assert headers["Notion-Version"] == nc.NOTION_VERSION
    assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# _pick_property_by_type
# ---------------------------------------------------------------------------

def test_pick_property_finds_title():
    props = {"Name": {"type": "title"}, "Status": {"type": "status"}}
    assert nc._pick_property_by_type(props, "title") == "Name"


def test_pick_property_finds_select():
    props = {"Name": {"type": "title"}, "Stage": {"type": "select"}}
    assert nc._pick_property_by_type(props, "select") == "Stage"


def test_pick_property_returns_none_when_missing():
    props = {"Name": {"type": "title"}}
    assert nc._pick_property_by_type(props, "date") is None


# ---------------------------------------------------------------------------
# _resolve_task_schema
# ---------------------------------------------------------------------------

def test_resolve_schema_auto_detection(monkeypatch):
    monkeypatch.setattr(nc, "NOTION_TASK_TITLE_PROPERTY", None)
    monkeypatch.setattr(nc, "NOTION_TASK_STATUS_PROPERTY", None)
    monkeypatch.setattr(nc, "NOTION_TASK_DUE_PROPERTY", None)
    monkeypatch.setattr(
        nc,
        "_get_database_schema",
        lambda: {
            "properties": {
                "Name": {"type": "title"},
                "Stage": {"type": "status"},
                "Deadline": {"type": "date"},
            }
        },
    )
    schema = nc._resolve_task_schema()
    assert schema["title_name"] == "Name"
    assert schema["status_name"] == "Stage"
    assert schema["due_name"] == "Deadline"
    assert schema["status_type"] == "status"


def test_resolve_schema_env_override_takes_priority(monkeypatch):
    monkeypatch.setattr(nc, "NOTION_TASK_TITLE_PROPERTY", "Task Name")
    monkeypatch.setattr(nc, "NOTION_TASK_STATUS_PROPERTY", "State")
    monkeypatch.setattr(nc, "NOTION_TASK_DUE_PROPERTY", "Due")
    monkeypatch.setattr(
        nc,
        "_get_database_schema",
        lambda: {
            "properties": {
                "Task Name": {"type": "title"},
                "State": {"type": "select"},
                "Due": {"type": "date"},
                "Name": {"type": "title"},
            }
        },
    )
    schema = nc._resolve_task_schema()
    assert schema["title_name"] == "Task Name"
    assert schema["status_name"] == "State"
    assert schema["due_name"] == "Due"


def test_resolve_schema_falls_back_to_select_if_no_status(monkeypatch):
    monkeypatch.setattr(nc, "NOTION_TASK_TITLE_PROPERTY", None)
    monkeypatch.setattr(nc, "NOTION_TASK_STATUS_PROPERTY", None)
    monkeypatch.setattr(nc, "NOTION_TASK_DUE_PROPERTY", None)
    monkeypatch.setattr(
        nc,
        "_get_database_schema",
        lambda: {
            "properties": {
                "Name": {"type": "title"},
                "Priority": {"type": "select"},
            }
        },
    )
    schema = nc._resolve_task_schema()
    assert schema["status_name"] == "Priority"
    assert schema["status_type"] == "select"


# ---------------------------------------------------------------------------
# _extract_title
# ---------------------------------------------------------------------------

def test_extract_title_from_schema_name():
    schema = {"title_name": "Name", "title_type": "title"}
    props = {"Name": {"type": "title", "title": [{"plain_text": "Buy groceries"}]}}
    assert nc._extract_title(props, schema) == "Buy groceries"


def test_extract_title_empty_when_no_title_array():
    schema = {"title_name": "Name", "title_type": "title"}
    props = {"Name": {"type": "title", "title": []}}
    assert nc._extract_title(props, schema) == ""


def test_extract_title_fallback_scan():
    schema = {"title_name": None}
    props = {"Task": {"type": "title", "title": [{"plain_text": "Fallback Task"}]}}
    assert nc._extract_title(props, schema) == "Fallback Task"


def test_extract_title_returns_empty_when_no_title_anywhere():
    schema = {"title_name": None}
    props = {"Status": {"type": "select"}}
    assert nc._extract_title(props, schema) == ""


# ---------------------------------------------------------------------------
# _extract_status
# ---------------------------------------------------------------------------

def test_extract_status_type_status():
    schema = {"status_name": "Stage", "status_type": "status"}
    props = {"Stage": {"type": "status", "status": {"name": "In Progress"}}}
    assert nc._extract_status(props, schema) == "In Progress"


def test_extract_status_type_select():
    schema = {"status_name": "Stage", "status_type": "select"}
    props = {"Stage": {"type": "select", "select": {"name": "Done"}}}
    assert nc._extract_status(props, schema) == "Done"


def test_extract_status_null_node():
    schema = {"status_name": "Stage"}
    props = {"Stage": {"type": "status", "status": None}}
    assert nc._extract_status(props, schema) == ""


def test_extract_status_missing_prop():
    schema = {"status_name": "Stage"}
    props = {}
    assert nc._extract_status(props, schema) == ""


def test_extract_status_no_status_name():
    schema = {"status_name": None}
    props = {"Stage": {"type": "status", "status": {"name": "To Do"}}}
    assert nc._extract_status(props, schema) == ""


# ---------------------------------------------------------------------------
# _extract_due_date
# ---------------------------------------------------------------------------

def test_extract_due_date_from_schema_name():
    schema = {"due_name": "Deadline"}
    props = {"Deadline": {"type": "date", "date": {"start": "2026-03-01"}}}
    assert nc._extract_due_date(props, schema) == "2026-03-01"


def test_extract_due_date_fallback_scan():
    schema = {"due_name": None}
    props = {"DueAt": {"type": "date", "date": {"start": "2026-04-15"}}}
    assert nc._extract_due_date(props, schema) == "2026-04-15"


def test_extract_due_date_returns_none_when_absent():
    schema = {"due_name": None}
    props = {"Status": {"type": "select"}}
    assert nc._extract_due_date(props, schema) is None


def test_extract_due_date_null_date_object():
    schema = {"due_name": "Due"}
    props = {"Due": {"type": "date", "date": None}}
    assert nc._extract_due_date(props, schema) is None


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------

def test_list_tasks_not_configured(monkeypatch):
    monkeypatch.setattr(nc, "NOTION_API_KEY", "")
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "")
    assert nc.list_tasks() == []


def test_list_tasks_http_error(monkeypatch):
    _configure(monkeypatch)
    schema = {
        "title_name": "Name", "title_type": "title",
        "status_name": "Status", "status_type": "status",
        "due_name": None, "due_type": None,
    }
    monkeypatch.setattr(nc, "_resolve_task_schema", lambda: schema)
    monkeypatch.setattr(nc, "_request", lambda *a, **kw: _make_response(500))
    assert nc.list_tasks() == []


def test_list_tasks_returns_parsed_tasks(monkeypatch):
    _configure(monkeypatch)
    schema = {
        "title_name": "Name", "title_type": "title",
        "status_name": "Stage", "status_type": "status",
        "due_name": "Due", "due_type": "date",
    }
    monkeypatch.setattr(nc, "_resolve_task_schema", lambda: schema)
    api_response = {
        "results": [
            {
                "id": "page_001",
                "url": "https://notion.so/page_001",
                "properties": {
                    "Name": {"type": "title", "title": [{"plain_text": "Write tests"}]},
                    "Stage": {"type": "status", "status": {"name": "In Progress"}},
                    "Due": {"type": "date", "date": {"start": "2026-03-10"}},
                },
            }
        ]
    }
    monkeypatch.setattr(nc, "_request", lambda *a, **kw: _make_response(200, api_response))
    tasks = nc.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Write tests"
    assert tasks[0]["status"] == "In Progress"
    assert tasks[0]["due_date"] == "2026-03-10"
    assert tasks[0]["id"] == "page_001"


def test_list_tasks_with_status_filter_status_type(monkeypatch):
    _configure(monkeypatch)
    schema = {
        "title_name": "Name", "title_type": "title",
        "status_name": "Stage", "status_type": "status",
        "due_name": None, "due_type": None,
    }
    monkeypatch.setattr(nc, "_resolve_task_schema", lambda: schema)
    captured = {}

    def fake_request(_method, _endpoint, **kwargs):
        captured["json"] = kwargs.get("json")
        return _make_response(200, {"results": []})

    monkeypatch.setattr(nc, "_request", fake_request)
    nc.list_tasks(status_filter="Done")
    assert captured["json"]["filter"]["status"] == {"equals": "Done"}


def test_list_tasks_with_status_filter_select_type(monkeypatch):
    _configure(monkeypatch)
    schema = {
        "title_name": "Name", "title_type": "title",
        "status_name": "Stage", "status_type": "select",
        "due_name": None, "due_type": None,
    }
    monkeypatch.setattr(nc, "_resolve_task_schema", lambda: schema)
    captured = {}

    def fake_request(_method, _endpoint, **kwargs):
        captured["json"] = kwargs.get("json")
        return _make_response(200, {"results": []})

    monkeypatch.setattr(nc, "_request", fake_request)
    nc.list_tasks(status_filter="Done")
    assert captured["json"]["filter"]["select"] == {"equals": "Done"}


# ---------------------------------------------------------------------------
# update_task_status
# ---------------------------------------------------------------------------

def test_update_task_status_supports_select(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {
            "title_name": "Name", "title_type": "title",
            "status_name": "Stage", "status_type": "select",
            "due_name": None, "due_type": None,
        },
    )
    called = {}

    class Resp:
        status_code = 200

    def fake_request(method: str, endpoint: str, **kwargs):
        called["method"] = method
        called["endpoint"] = endpoint
        called["json"] = kwargs.get("json")
        return Resp()

    monkeypatch.setattr(nc, "_request", fake_request)
    ok = nc.update_task_status("page_123", "Done")
    assert ok
    assert called["method"] == "PATCH"
    assert called["endpoint"] == "pages/page_123"
    assert called["json"]["properties"]["Stage"] == {"select": {"name": "Done"}}


def test_update_task_status_type_status(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {
            "title_name": "Name", "title_type": "title",
            "status_name": "Stage", "status_type": "status",
            "due_name": None, "due_type": None,
        },
    )
    called = {}

    def fake_request(_method, _endpoint, **kwargs):
        called["json"] = kwargs.get("json")
        return _make_response(200)

    monkeypatch.setattr(nc, "_request", fake_request)
    nc.update_task_status("page_456", "In Progress")
    assert called["json"]["properties"]["Stage"] == {"status": {"name": "In Progress"}}


def test_update_task_status_not_configured(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: False)
    assert nc.update_task_status("page_x", "Done") is False


def test_update_task_status_no_status_schema(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {"title_name": "Name", "title_type": "title",
                 "status_name": None, "status_type": None,
                 "due_name": None, "due_type": None},
    )
    assert nc.update_task_status("page_x", "Done") is False


def test_update_task_status_http_failure(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {"title_name": "Name", "title_type": "title",
                 "status_name": "Stage", "status_type": "select",
                 "due_name": None, "due_type": None},
    )
    monkeypatch.setattr(nc, "_request", lambda *a, **kw: _make_response(500))
    assert nc.update_task_status("page_x", "Done") is False


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------

def test_create_task_not_configured(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: False)
    assert nc.create_task("My Task") is None


def test_create_task_no_title_schema(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {"title_name": None, "title_type": None,
                 "status_name": None, "status_type": None,
                 "due_name": None, "due_type": None},
    )
    assert nc.create_task("My Task") is None


def test_create_task_success_with_status_and_due(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {
            "title_name": "Name", "title_type": "title",
            "status_name": "Stage", "status_type": "status",
            "due_name": "Due", "due_type": "date",
        },
    )
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "db_123")
    captured = {}

    def fake_request(method, _endpoint, **kwargs):
        captured["method"] = method
        captured["json"] = kwargs.get("json")
        return _make_response(200, {"id": "new_page_id"})

    monkeypatch.setattr(nc, "_request", fake_request)
    pid = nc.create_task("New Task", status="To Do", due_date="2026-03-15")
    assert pid == "new_page_id"
    assert captured["method"] == "POST"
    props = captured["json"]["properties"]
    assert props["Name"] == {"title": [{"text": {"content": "New Task"}}]}
    assert props["Stage"] == {"status": {"name": "To Do"}}
    assert props["Due"] == {"date": {"start": "2026-03-15"}}


def test_create_task_select_status(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {
            "title_name": "Name", "title_type": "title",
            "status_name": "Stage", "status_type": "select",
            "due_name": None, "due_type": None,
        },
    )
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "db_123")
    captured = {}

    def fake_request(_method, _endpoint, **kwargs):
        captured["json"] = kwargs.get("json")
        return _make_response(201, {"id": "created_id"})

    monkeypatch.setattr(nc, "_request", fake_request)
    pid = nc.create_task("Select Task", status="Done")
    assert pid == "created_id"
    assert captured["json"]["properties"]["Stage"] == {"select": {"name": "Done"}}


def test_create_task_http_failure(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {"title_name": "Name", "title_type": "title",
                 "status_name": None, "status_type": None,
                 "due_name": None, "due_type": None},
    )
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "db_123")
    monkeypatch.setattr(nc, "_request", lambda *a, **kw: _make_response(400))
    assert nc.create_task("Fail Task") is None


# ---------------------------------------------------------------------------
# _request (direct HTTP layer)
# ---------------------------------------------------------------------------

def test_request_calls_requests_request_and_logs(monkeypatch):
    monkeypatch.setattr(nc, "NOTION_API_KEY", "ntn_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("execution.notion_client.requests.request", return_value=mock_resp) as mock_req, \
         patch("execution.notion_client.log_api_call") as mock_log:
        resp = nc._request("GET", "databases/db_abc")
        assert resp is mock_resp
        mock_req.assert_called_once()
        mock_log.assert_called_once()


# ---------------------------------------------------------------------------
# _get_database_schema
# ---------------------------------------------------------------------------

def test_get_database_schema_not_configured(monkeypatch):
    nc._get_database_schema.cache_clear()
    monkeypatch.setattr(nc, "NOTION_API_KEY", "")
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "")
    assert nc._get_database_schema() == {}


def test_get_database_schema_http_error(monkeypatch):
    nc._get_database_schema.cache_clear()
    monkeypatch.setattr(nc, "NOTION_API_KEY", "ntn_key")
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "db_abc")
    monkeypatch.setattr(nc, "_request", lambda *a, **kw: _make_response(403))
    assert nc._get_database_schema() == {}


def test_get_database_schema_success(monkeypatch):
    nc._get_database_schema.cache_clear()
    monkeypatch.setattr(nc, "NOTION_API_KEY", "ntn_key")
    monkeypatch.setattr(nc, "NOTION_TASK_DB", "db_abc")
    schema_data = {"object": "database", "properties": {"Name": {"type": "title"}}}
    monkeypatch.setattr(nc, "_request", lambda *a, **kw: _make_response(200, schema_data))
    assert nc._get_database_schema() == schema_data


# ---------------------------------------------------------------------------
# _extract_status: unknown property type → fallback ""
# ---------------------------------------------------------------------------

def test_extract_status_unknown_type_returns_empty():
    schema = {"status_name": "Stage", "status_type": "rich_text"}
    props = {"Stage": {"type": "rich_text", "rich_text": [{"plain_text": "some text"}]}}
    assert nc._extract_status(props, schema) == ""
