from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline.notification as notification_module  # noqa: E402


class FakeConfig:
    def __init__(self, data: dict):
        self.data = data

    def get(self, key, default=None):
        return self.data.get(key, default)


@pytest.mark.asyncio
async def test_send_message_returns_early_without_webhook(monkeypatch) -> None:
    monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)
    monkeypatch.setattr(
        notification_module.requests,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("requests.post should not run")),
    )

    manager = notification_module.NotificationManager(FakeConfig({"discord.webhook_url": ""}))
    assert await manager.send_message("hello") is None


@pytest.mark.asyncio
async def test_send_message_sends_telegram_and_discord_with_github_link(monkeypatch) -> None:
    telegram_calls: list[tuple[str, str]] = []
    discord_calls: list[tuple[str, dict, int]] = []

    monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", True)
    monkeypatch.setattr(
        notification_module,
        "telegram_send_alert",
        lambda message, level="INFO": telegram_calls.append((level, message)),
        raising=False,
    )
    monkeypatch.setenv("GITHUB_REPOSITORY", "team/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "1234")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.example.com")

    def fake_post(url, json, timeout):
        discord_calls.append((url, json, timeout))
        return SimpleNamespace(status_code=204, text="")

    monkeypatch.setattr(notification_module.requests, "post", fake_post)

    manager = notification_module.NotificationManager(
        FakeConfig({"discord.webhook_url": "https://discord.example/webhook"})
    )
    await manager.send_message("Build failed", level="warning")

    assert telegram_calls == [("warning", "Build failed")]
    assert discord_calls[0][0] == "https://discord.example/webhook"
    assert discord_calls[0][2] == 10
    content = discord_calls[0][1]["content"]
    assert "Build failed" in content
    assert "WARNING" in content
    assert "https://github.example.com/team/repo/actions/runs/1234" in content


@pytest.mark.asyncio
async def test_send_message_logs_http_failures(monkeypatch, caplog) -> None:
    monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)
    monkeypatch.setattr(
        notification_module.requests,
        "post",
        lambda *_args, **_kwargs: SimpleNamespace(status_code=500, text="bad request"),
    )

    manager = notification_module.NotificationManager(
        FakeConfig({"discord.webhook_url": "https://discord.example/webhook"})
    )

    with caplog.at_level("ERROR"):
        await manager.send_message("Oops", level="CRITICAL")

    assert "Discord webhook failed: bad request" in caplog.text


@pytest.mark.asyncio
async def test_send_message_logs_request_exceptions(monkeypatch, caplog) -> None:
    monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

    def raising_post(*_args, **_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(notification_module.requests, "post", raising_post)

    manager = notification_module.NotificationManager(
        FakeConfig({"discord.webhook_url": "https://discord.example/webhook"})
    )

    with caplog.at_level("ERROR"):
        await manager.send_message("Oops", level="INFO")

    assert "Failed to send Discord notification: network down" in caplog.text
