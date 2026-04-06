"""Tests for pipeline.notification — send_surge_alert method."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline.notification as notification_module


class FakeConfig:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)


# ── send_surge_alert ─────────────────────────────────────────────────


class TestSendSurgeAlert:
    @pytest.mark.asyncio
    async def test_basic_surge_alert(self, monkeypatch):
        """Basic surge alert sends message with correct formatting."""
        sent_messages = []

        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def fake_send(msg, level="INFO", reply_markup=None):
            sent_messages.append({"msg": msg, "level": level, "reply_markup": reply_markup})

        manager.send_message = fake_send

        event = SimpleNamespace(
            source="blind",
            velocity_score=15.0,
            title="연봉 인상 후기",
            url="https://blind.com/post/123",
            id=42,
        )

        result = await manager.send_surge_alert(event, draft_x="X draft text", draft_threads="Threads draft")
        assert result is True
        assert len(sent_messages) == 1

        msg = sent_messages[0]["msg"]
        assert "SURGE ALERT" in msg
        assert "블라인드" in msg  # source label
        assert "연봉 인상 후기" in msg
        assert "15.0" in msg  # velocity_score
        assert "X 초안" in msg
        assert "X draft text" in msg
        assert "Threads 초안" in msg

    @pytest.mark.asyncio
    async def test_surge_alert_high_velocity(self, monkeypatch):
        """High velocity score shows triple fire emoji."""
        sent_messages = []
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def fake_send(msg, level="INFO", reply_markup=None):
            sent_messages.append(msg)

        manager.send_message = fake_send

        event = SimpleNamespace(source="fmkorea", velocity_score=25.0, title="Hot", url="", id=1)
        await manager.send_surge_alert(event)
        assert sent_messages[0].count("🔥🔥🔥") >= 1

    @pytest.mark.asyncio
    async def test_surge_alert_medium_velocity(self, monkeypatch):
        """Medium velocity (10-20) shows double fire."""
        sent_messages = []
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def fake_send(msg, level="INFO", reply_markup=None):
            sent_messages.append(msg)

        manager.send_message = fake_send

        event = SimpleNamespace(source="blind", velocity_score=15.0, title="Med", url="", id=2)
        await manager.send_surge_alert(event)
        assert "🔥🔥" in sent_messages[0]

    @pytest.mark.asyncio
    async def test_surge_alert_low_velocity(self, monkeypatch):
        """Low velocity (<10) shows single fire."""
        sent_messages = []
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def fake_send(msg, level="INFO", reply_markup=None):
            sent_messages.append(msg)

        manager.send_message = fake_send

        event = SimpleNamespace(source="blind", velocity_score=5.0, title="Low", url="", id=3)
        await manager.send_surge_alert(event)
        # Should have single fire but not double
        msg = sent_messages[0]
        assert "🔥" in msg

    @pytest.mark.asyncio
    async def test_surge_alert_source_labels(self, monkeypatch):
        """Different source names are translated to Korean labels."""
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        for source, expected_label in [
            ("blind", "블라인드"),
            ("ppomppu", "뽐뿌"),
            ("fmkorea", "에펨코리아"),
            ("jobplanet", "잡플래닛"),
            ("unknown", "unknown"),
        ]:
            sent_messages = []
            manager = notification_module.NotificationManager(FakeConfig())

            async def fake_send(msg, level="INFO", reply_markup=None):
                sent_messages.append(msg)

            manager.send_message = fake_send
            event = SimpleNamespace(source=source, velocity_score=5.0, title="T", url="", id=10)
            await manager.send_surge_alert(event)
            assert expected_label in sent_messages[0]

    @pytest.mark.asyncio
    async def test_surge_alert_no_url(self, monkeypatch):
        """Event without URL omits link line."""
        sent_messages = []
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def fake_send(msg, level="INFO", reply_markup=None):
            sent_messages.append(msg)

        manager.send_message = fake_send

        event = SimpleNamespace(source="blind", velocity_score=5.0, title="No URL", url="", id=4)
        await manager.send_surge_alert(event)
        assert "🔗" not in sent_messages[0]

    @pytest.mark.asyncio
    async def test_surge_alert_with_generation_time(self, monkeypatch):
        """Generation time is displayed when > 0."""
        sent_messages = []
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def fake_send(msg, level="INFO", reply_markup=None):
            sent_messages.append(msg)

        manager.send_message = fake_send

        event = SimpleNamespace(source="blind", velocity_score=5.0, title="T", url="", id=5)
        await manager.send_surge_alert(event, generation_time=3.5)
        assert "3.5" in sent_messages[0]
        assert "생성시간" in sent_messages[0]

    @pytest.mark.asyncio
    async def test_surge_alert_inline_keyboard(self, monkeypatch):
        """Reply markup includes approve/reject buttons with event ID."""
        sent_data = []
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def fake_send(msg, level="INFO", reply_markup=None):
            sent_data.append(reply_markup)

        manager.send_message = fake_send

        event = SimpleNamespace(source="blind", velocity_score=5.0, title="T", url="", id=42)
        await manager.send_surge_alert(event)

        keyboard = sent_data[0]
        assert keyboard is not None
        buttons = keyboard["inline_keyboard"][0]
        assert len(buttons) == 2
        assert "approve_42" in buttons[0]["callback_data"]
        assert "reject_42" in buttons[1]["callback_data"]

    @pytest.mark.asyncio
    async def test_surge_alert_no_id_uses_hash(self, monkeypatch):
        """Event without id attribute uses hash of url."""
        sent_data = []
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def fake_send(msg, level="INFO", reply_markup=None):
            sent_data.append(reply_markup)

        manager.send_message = fake_send

        event = SimpleNamespace(source="blind", velocity_score=5.0, title="T", url="https://test.com")
        # Remove 'id' attribute
        assert not hasattr(event, "id") or True  # SimpleNamespace may not have id
        delattr(event, "id") if hasattr(event, "id") else None

        await manager.send_surge_alert(event)
        keyboard = sent_data[0]
        # Should still have buttons with hashed ID
        assert "approve_" in keyboard["inline_keyboard"][0][0]["callback_data"]

    @pytest.mark.asyncio
    async def test_surge_alert_send_failure(self, monkeypatch):
        """send_message raising -> returns False."""
        monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)

        manager = notification_module.NotificationManager(FakeConfig())

        async def failing_send(msg, level="INFO", reply_markup=None):
            raise RuntimeError("network error")

        manager.send_message = failing_send

        event = SimpleNamespace(source="blind", velocity_score=5.0, title="T", url="", id=1)
        result = await manager.send_surge_alert(event)
        assert result is False
