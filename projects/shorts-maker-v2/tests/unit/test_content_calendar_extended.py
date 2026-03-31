from __future__ import annotations

from typing import Any

import pytest

from shorts_maker_v2.utils.content_calendar import NotionContentCalendar


def _make_calendar() -> NotionContentCalendar:
    return NotionContentCalendar(api_key="test-key", database_id="test-db")


def test_get_pending_topics_parses_results_and_builds_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()
    captured: dict[str, Any] = {}

    def fake_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["json_body"] = json_body
        return {
            "results": [
                {
                    "id": "page-1",
                    "properties": {
                        "Name": {"title": [{"text": {"content": "Topic A"}}]},
                        "Channel": {"select": {"name": "ai_tech"}},
                    },
                }
            ]
        }

    monkeypatch.setattr(calendar, "_request", fake_request)

    topics = calendar.get_pending_topics(channel="ai_tech", limit=3)

    assert topics == [
        {
            "id": "page-1",
            "topic": "Topic A",
            "channel": "ai_tech",
            "status": "pending",
        }
    ]
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "/databases/test-db/query"
    assert captured["json_body"]["page_size"] == 3
    channel_filter = captured["json_body"]["filter"]["and"][1]
    assert channel_filter == {"property": "Channel", "select": {"equals": "ai_tech"}}


def test_get_pending_topics_returns_empty_on_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()

    def fake_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        del method, endpoint, json_body
        raise RuntimeError("notion unavailable")

    monkeypatch.setattr(calendar, "_request", fake_request)

    assert calendar.get_pending_topics(channel="ai_tech") == []


def test_update_status_includes_optional_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()
    captured: dict[str, Any] = {}

    def fake_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["json_body"] = json_body
        return {}

    monkeypatch.setattr(calendar, "_request", fake_request)

    calendar.update_status(
        page_id="page-1",
        status="done",
        job_id="job-123",
        video_path="output/video.mp4",
        cost_usd=1.23456,
        duration_sec=42.78,
    )

    properties = captured["json_body"]["properties"]
    assert captured["method"] == "PATCH"
    assert captured["endpoint"] == "/pages/page-1"
    assert properties["Status"]["status"]["name"] == "done"
    assert properties["Job ID"]["rich_text"][0]["text"]["content"] == "job-123"
    assert properties["Video Path"]["rich_text"][0]["text"]["content"] == "output/video.mp4"
    assert properties["Cost USD"]["number"] == 1.2346
    assert properties["Duration"]["number"] == 42.8


def test_add_topic_skips_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()

    monkeypatch.setattr(calendar, "_check_duplicate", lambda topic: True)

    called = False

    def fake_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        del method, endpoint, json_body
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(calendar, "_request", fake_request)

    assert calendar.add_topic("Duplicate topic", channel="ai_tech") is None
    assert called is False


def test_add_topic_creates_page(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(calendar, "_check_duplicate", lambda topic: False)

    def fake_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["json_body"] = json_body
        return {"id": "new-page-id"}

    monkeypatch.setattr(calendar, "_request", fake_request)

    page_id = calendar.add_topic("Fresh topic", channel="space", scheduled_date="2026-03-25")

    assert page_id == "new-page-id"
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "/pages"
    props = captured["json_body"]["properties"]
    assert props["Name"]["title"][0]["text"]["content"] == "Fresh topic"
    assert props["Channel"]["select"]["name"] == "space"
    assert props["Scheduled Date"]["date"]["start"] == "2026-03-25"


def test_get_next_topics_parses_scheduled_date(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()

    def fake_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        del method, endpoint, json_body
        return {
            "results": [
                {
                    "id": "page-42",
                    "properties": {
                        "Name": {"title": [{"text": {"content": "Next topic"}}]},
                        "Channel": {"select": {"name": "history"}},
                        "Scheduled Date": {"date": {"start": "2026-03-29"}},
                    },
                }
            ]
        }

    monkeypatch.setattr(calendar, "_request", fake_request)

    topics = calendar.get_next_topics(channel="history", count=1)

    assert topics == [
        {
            "topic": "Next topic",
            "channel": "history",
            "scheduled_date": "2026-03-29",
            "notion_page_id": "page-42",
        }
    ]


def test_mark_topic_used_handles_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()

    monkeypatch.setattr(calendar, "_request", lambda method, endpoint, json_body=None: {})
    assert calendar.mark_topic_used("page-1") is True

    def failing_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        del method, endpoint, json_body
        raise RuntimeError("patch failed")

    monkeypatch.setattr(calendar, "_request", failing_request)
    assert calendar.mark_topic_used("page-2") is False


def test_suggest_topics_from_trends_filters_duplicates_and_similar_topics() -> None:
    trends = [
        "OpenAI launches agent mode",
        "OpenAI launches agent mode",
        "AI chip race heats up",
        "Healthy sleep habit tips",
    ]
    existing_topics = [
        "OpenAI launch agent mode",
        "How to sleep better",
    ]

    suggestions = NotionContentCalendar.suggest_topics_from_trends(trends, existing_topics)

    assert suggestions == ["AI chip race heats up", "Healthy sleep habit tips"]


def test_balance_weekly_topics_filters_recent_similar_topics(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()

    monkeypatch.setattr(
        calendar,
        "_get_recent_topics",
        lambda channel, days=7: [
            {"topic": "OpenAI launches agent mode", "channel": channel, "status": "done"},
            {"topic": "Mars colony update", "channel": channel, "status": "done"},
        ],
    )

    balanced = calendar.balance_weekly_topics(
        channel="ai_tech",
        topics=[
            "OpenAI launch agent mode",
            "AI chip race heats up",
            "Mars colony update",
        ],
    )

    assert balanced == ["AI chip race heats up"]


def test_get_recent_topics_parses_status_and_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar = _make_calendar()

    def fake_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        del method, endpoint, json_body
        return {
            "results": [
                {
                    "properties": {
                        "Name": {"title": [{"text": {"content": "Recent topic"}}]},
                        "Channel": {"select": {"name": "ai_tech"}},
                        "Status": {"status": {"name": "done"}},
                    }
                }
            ]
        }

    monkeypatch.setattr(calendar, "_request", fake_request)

    recent = calendar._get_recent_topics(channel="ai_tech", days=3)
    assert recent == [{"topic": "Recent topic", "channel": "ai_tech", "status": "done"}]

    def failing_request(method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        del method, endpoint, json_body
        raise RuntimeError("query failed")

    monkeypatch.setattr(calendar, "_request", failing_request)
    assert calendar._get_recent_topics(channel="ai_tech", days=3) == []
