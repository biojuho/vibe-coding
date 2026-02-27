from __future__ import annotations

import execution.notion_client as nc


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


def test_update_task_status_supports_select(monkeypatch):
    monkeypatch.setattr(nc, "is_configured", lambda: True)
    monkeypatch.setattr(
        nc,
        "_resolve_task_schema",
        lambda: {
            "title_name": "Name",
            "title_type": "title",
            "status_name": "Stage",
            "status_type": "select",
            "due_name": None,
            "due_type": None,
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
