from __future__ import annotations

import json
import sys
import types
import builtins
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

import execution.telegram_notifier as tn


def _make_response(status_code: int = 200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {"ok": True}
    return response


def _configure_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654321")
    monkeypatch.setenv("TELEGRAM_NOTIFY_SCHEDULER", "failures")


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ENABLED", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_NOTIFY_SCHEDULER", raising=False)

    config = tn.load_config()

    assert config.enabled is True
    assert config.bot_token == ""
    assert config.chat_id == ""
    assert config.scheduler_mode == "failures"


def test_load_config_invalid_scheduler_mode_falls_back(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setenv("TELEGRAM_NOTIFY_SCHEDULER", "invalid")

    config = tn.load_config()

    assert config.scheduler_mode == "failures"


def test_validate_message_truncates_long_text():
    message = "x" * (tn.DEFAULT_MESSAGE_LIMIT + 25)

    result = tn._validate_message(message)

    assert len(result) == tn.DEFAULT_MESSAGE_LIMIT
    assert result.endswith("...")


def test_raise_for_telegram_error_raises_runtime_error():
    response = _make_response(json_data={"ok": False, "description": "bad request"})

    with pytest.raises(RuntimeError, match="bad request"):
        tn._raise_for_telegram_error(response)


def test_get_me_requires_bot_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        tn.get_me()


def test_get_me_returns_bot_payload(monkeypatch):
    _configure_env(monkeypatch)
    payload = {"ok": True, "result": {"username": "joolife_bot"}}

    with patch("execution.telegram_notifier.requests.get", return_value=_make_response(json_data=payload)):
        result = tn.get_me()

    assert result["result"]["username"] == "joolife_bot"


def test_send_message_posts_to_telegram(monkeypatch):
    _configure_env(monkeypatch)

    with patch(
        "execution.telegram_notifier.requests.post",
        return_value=_make_response(json_data={"ok": True, "result": {"message_id": 42}}),
    ) as mock_post:
        result = tn.send_message("hello from tests")

    assert result["result"]["message_id"] == 42
    request_json = mock_post.call_args.kwargs["json"]
    assert request_json["chat_id"] == "987654321"
    assert request_json["text"] == "hello from tests"


def test_send_message_rejects_empty_message(monkeypatch):
    _configure_env(monkeypatch)

    try:
        tn.send_message("   ")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:  # pragma: no cover - safety assertion
        raise AssertionError("Expected ValueError for empty message")


def test_send_message_rejects_when_disabled(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setenv("TELEGRAM_ENABLED", "0")

    with pytest.raises(RuntimeError, match="disabled"):
        tn.send_message("hello")


def test_send_message_rejects_missing_bot_token(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        tn.send_message("hello")


def test_send_message_rejects_missing_chat_id(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(ValueError, match="TELEGRAM_CHAT_ID"):
        tn.send_message("hello")


def test_send_message_allows_chat_id_override(monkeypatch):
    _configure_env(monkeypatch)

    with patch(
        "execution.telegram_notifier.requests.post",
        return_value=_make_response(json_data={"ok": True, "result": {"message_id": 9}}),
    ) as mock_post:
        tn.send_message("hello", chat_id="222", disable_notification=True)

    request_json = mock_post.call_args.kwargs["json"]
    assert request_json["chat_id"] == "222"
    assert request_json["disable_notification"] is True


def test_maybe_send_scheduler_notification_skips_success_when_failures_mode(monkeypatch):
    _configure_env(monkeypatch)

    with patch("execution.telegram_notifier.requests.post") as mock_post:
        result = tn.maybe_send_scheduler_notification(
            task_name="ok-task",
            exit_code=0,
            trigger_type="schedule",
            duration_ms=120,
        )

    assert result is None
    mock_post.assert_not_called()


def test_maybe_send_scheduler_notification_skips_when_not_configured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ENABLED", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    result = tn.maybe_send_scheduler_notification(
        task_name="missing-config",
        exit_code=1,
        trigger_type="schedule",
        duration_ms=20,
    )

    assert result is None


def test_maybe_send_scheduler_notification_sends_failure(monkeypatch):
    _configure_env(monkeypatch)

    with patch(
        "execution.telegram_notifier.requests.post",
        return_value=_make_response(json_data={"ok": True, "result": {"message_id": 77}}),
    ) as mock_post:
        result = tn.maybe_send_scheduler_notification(
            task_name="broken-task",
            exit_code=1,
            trigger_type="schedule",
            duration_ms=500,
            error_type="non_zero_exit",
            stderr="boom",
            auto_disabled=True,
        )

    assert result is not None
    message_text = mock_post.call_args.kwargs["json"]["text"]
    assert "broken-task" in message_text
    assert "FAILED" in message_text
    assert "Auto-disabled: yes" in message_text


def test_maybe_send_scheduler_notification_skips_when_mode_none(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setenv("TELEGRAM_NOTIFY_SCHEDULER", "none")

    with patch("execution.telegram_notifier.requests.post") as mock_post:
        result = tn.maybe_send_scheduler_notification(
            task_name="quiet-task",
            exit_code=1,
            trigger_type="schedule",
            duration_ms=50,
        )

    assert result is None
    mock_post.assert_not_called()


def test_maybe_send_scheduler_notification_sends_success_when_mode_all(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setenv("TELEGRAM_NOTIFY_SCHEDULER", "all")

    with patch(
        "execution.telegram_notifier.requests.post",
        return_value=_make_response(json_data={"ok": True, "result": {"message_id": 99}}),
    ):
        result = tn.maybe_send_scheduler_notification(
            task_name="ok-task",
            exit_code=0,
            trigger_type="manual",
            duration_ms=42,
        )

    assert result["result"]["message_id"] == 99


def test_get_updates_returns_result_list(monkeypatch):
    _configure_env(monkeypatch)
    payload = {"ok": True, "result": [{"update_id": 1}, {"update_id": 2}]}

    with patch("execution.telegram_notifier.requests.get", return_value=_make_response(json_data=payload)):
        updates = tn.get_updates(limit=2, timeout=0)

    assert [update["update_id"] for update in updates] == [1, 2]


def test_get_updates_requires_bot_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        tn.get_updates()


def test_send_daily_report_delegates_to_send_message(monkeypatch):
    report = {"date": "2026-02-28", "summary": {}, "git_activity": {"commits": []}}
    calls = []
    monkeypatch.setattr(tn, "send_message", lambda text: calls.append(text) or {"ok": True})

    result = tn.send_daily_report(report)

    assert result == {"ok": True}
    assert calls and "[Joolife][Daily Report]" in calls[0]


def test_format_daily_report_message_includes_summary():
    report = {
        "date": "2026-02-28",
        "summary": {
            "total_commits": 3,
            "active_repos": 2,
            "files_modified": 7,
            "scheduler_tasks_run": 4,
        },
        "git_activity": {
            "commits": [
                {"repo": "repo-a", "hash": "abc12345", "message": "feat: add bot"},
                {"repo": "repo-b", "hash": "def67890", "message": "fix: scheduler"},
            ]
        },
    }

    message = tn.format_daily_report_message(report)

    assert "[Joolife][Daily Report] 2026-02-28" in message
    assert "Commits: 3" in message
    assert "- [repo-a] abc12345 feat: add bot" in message


def test_build_check_payload_includes_bot_info(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setattr(tn, "get_me", lambda: {"result": {"username": "joolife_bot"}})

    payload = tn._build_check_payload()

    assert payload["configured"] is True
    assert payload["bot"]["username"] == "joolife_bot"


def test_build_check_payload_includes_bot_error(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setattr(tn, "get_me", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    payload = tn._build_check_payload()

    assert payload["bot_error"] == "boom"


def test_parse_date_supports_explicit_and_default():
    assert tn._parse_date("2026-02-28") == date(2026, 2, 28)
    assert tn._parse_date(None) == date.today()


def test_main_check_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["telegram_notifier.py", "check"])
    monkeypatch.setattr(tn, "_build_check_payload", lambda: {"configured": True})

    result = tn.main()

    assert result == 0
    assert json.loads(capsys.readouterr().out)["configured"] is True


def test_main_updates_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["telegram_notifier.py", "updates", "--limit", "2", "--timeout", "1"])
    monkeypatch.setattr(tn, "get_updates", lambda limit, timeout: [{"update_id": limit + timeout}])

    result = tn.main()

    assert result == 0
    assert json.loads(capsys.readouterr().out)[0]["update_id"] == 3


def test_main_send_command(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["telegram_notifier.py", "send", "--message", "hello", "--disable-notification"],
    )
    monkeypatch.setattr(
        tn,
        "send_message",
        lambda message, disable_notification=False: {
            "result": {"message_id": 321, "disable_notification": disable_notification, "text": message}
        },
    )

    result = tn.main()

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["message_id"] == 321


def test_main_daily_report_command(monkeypatch, capsys):
    fake_report = {"date": "2026-02-28", "summary": {}, "git_activity": {"commits": []}}
    fake_module = types.SimpleNamespace(generate_report=lambda parsed_date: fake_report)

    monkeypatch.setattr(sys, "argv", ["telegram_notifier.py", "daily-report", "--date", "2026-02-28"])
    monkeypatch.setitem(sys.modules, "execution.daily_report", fake_module)
    monkeypatch.setattr(tn, "send_daily_report", lambda report: {"result": {"message_id": 555}})

    result = tn.main()

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"date": "2026-02-28", "message_id": 555}


def test_main_daily_report_command_uses_fallback_import(monkeypatch, capsys):
    fake_report = {"date": "2026-02-28", "summary": {}, "git_activity": {"commits": []}}
    fallback_module = types.ModuleType("daily_report")
    fallback_module.generate_report = lambda parsed_date: fake_report

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "execution.daily_report":
            raise ModuleNotFoundError("execution.daily_report missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(sys, "argv", ["telegram_notifier.py", "daily-report", "--date", "2026-02-28"])
    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setitem(sys.modules, "daily_report", fallback_module)
    monkeypatch.setattr(tn, "send_daily_report", lambda report: {"result": {"message_id": 777}})

    result = tn.main()

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"date": "2026-02-28", "message_id": 777}


def test_main_without_command_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["telegram_notifier.py"])

    result = tn.main()

    assert result == 1
    assert "usage:" in capsys.readouterr().out.lower()
