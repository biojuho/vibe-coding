"""Unit tests for NotificationManager.send_surge_alert — 바이럴 에스컬레이션 알림.

타겟: pipeline/notification.py :: send_surge_alert()
커버 범위:
  - Happy Path: 정상 이벤트 → 소스 라벨 매핑, 이모지 등급, inline keyboard 생성, 메시지 전송 성공
  - Edge Cases: 속성 누락 이벤트, velocity_score 경계값, send_message 예외 발생
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import pipeline.notification as notification_module


# ── 공통 Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _disable_telegram(monkeypatch):
    """모든 테스트에서 TELEGRAM_AVAILABLE을 False로 고정."""
    monkeypatch.setattr(notification_module, "TELEGRAM_AVAILABLE", False)


@pytest.fixture
def surge_manager():
    """capture 기능이 내장된 NotificationManager + 캡처된 메시지/키보드 접근."""
    manager = notification_module.NotificationManager(FakeConfig())
    captured_messages: list[str] = []
    captured_keyboards: list[dict | None] = []

    async def capture_send(message, level="INFO", reply_markup=None):
        captured_messages.append(message)
        captured_keyboards.append(reply_markup)

    manager.send_message = capture_send
    manager._captured_messages = captured_messages  # type: ignore[attr-defined]
    manager._captured_keyboards = captured_keyboards  # type: ignore[attr-defined]
    return manager


class FakeConfig:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


def _make_event(
    url="https://blind.com/post/123",
    title="연봉 1억 후기",
    source="blind",
    velocity_score=15.0,
    event_id=42,
    event_key="blind-123",
):
    """send_surge_alert에 전달되는 이벤트 목 객체."""
    return SimpleNamespace(
        id=event_id,
        url=url,
        title=title,
        source=source,
        velocity_score=velocity_score,
        event_key=event_key,
    )


# ── Happy Path 테스트 ──────────────────────────────────────────────────────


class TestSendSurgeAlertHappyPath:
    """정상 동작 시나리오."""

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, surge_manager):
        """send_message가 정상 실행되면 True 반환."""  # [QA 수정] Q1 fixture 활용
        event = _make_event()
        result = await surge_manager.send_surge_alert(event, draft_x="🔥 트윗", draft_threads="스레드 글")

        assert result is True
        assert len(surge_manager._captured_messages) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "src,expected_label",
        [("blind", "블라인드"), ("ppomppu", "뽐뿌"), ("fmkorea", "에펨코리아"), ("jobplanet", "잡플래닛")],
    )
    async def test_source_label_mapping(self, src, expected_label):
        """각 소스가 한글 라벨로 변환."""  # [QA 수정] Q1 parametrize로 반복 제거
        manager = notification_module.NotificationManager(FakeConfig())
        captured = []

        async def cap(msg, level="INFO", reply_markup=None):
            captured.append(msg)

        manager.send_message = cap
        event = _make_event(source=src)
        await manager.send_surge_alert(event)

        assert any(expected_label in msg for msg in captured), f"소스 '{src}'가 '{expected_label}'로 변환되어야 함"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "v_score,expected_emoji",
        [(25.0, "🔥🔥🔥"), (20.0, "🔥🔥🔥"), (10.0, "🔥🔥"), (15.0, "🔥🔥"), (5.0, "🔥")],
    )
    async def test_velocity_emoji_tiers(self, v_score, expected_emoji, surge_manager):
        """velocity_score에 따른 이모지 등급 분류."""  # [QA 수정] Q1 fixture + parametrize
        event = _make_event(velocity_score=v_score)
        await surge_manager.send_surge_alert(event)

        assert any(expected_emoji in msg for msg in surge_manager._captured_messages), (
            f"velocity={v_score}일 때 '{expected_emoji}' 이모지 포함 필요"
        )

    @pytest.mark.asyncio
    async def test_message_includes_drafts_and_time(self, surge_manager):
        """draft_x, draft_threads, generation_time이 메시지에 포함."""  # [QA 수정] Q1
        event = _make_event()
        await surge_manager.send_surge_alert(
            event,
            draft_x="트윗 초안입니다",
            draft_threads="스레드 초안입니다",
            generation_time=3.5,
        )

        full_msg = surge_manager._captured_messages[0]
        assert "X 초안" in full_msg
        assert "트윗 초안입니다" in full_msg
        assert "Threads 초안" in full_msg
        assert "스레드 초안입니다" in full_msg
        assert "3.5초" in full_msg

    @pytest.mark.asyncio
    async def test_inline_keyboard_contains_approve_reject(self, surge_manager):
        """reply_markup에 승인/거부 버튼이 포함."""  # [QA 수정] Q1
        event = _make_event(event_id=42)
        await surge_manager.send_surge_alert(event)

        keyboard = surge_manager._captured_keyboards[0]
        assert keyboard is not None
        buttons = keyboard["inline_keyboard"][0]
        assert len(buttons) == 2
        assert "approve_42" in buttons[0]["callback_data"]
        assert "reject_42" in buttons[1]["callback_data"]


# ── Edge Case 테스트 ─────────────────────────────────────────────────────


class TestSendSurgeAlertEdgeCases:
    """엣지 케이스 및 방어 로직."""

    @pytest.mark.asyncio
    async def test_event_without_id_uses_hash_fallback(self, surge_manager):
        """event.id가 없으면 hash fallback 사용."""  # [QA 수정] Q1
        # id 속성이 None인 이벤트
        event = SimpleNamespace(
            id=None,
            url="https://blind.com/post/999",
            title="ID 없는 이벤트",
            source="blind",
            velocity_score=8.0,
            event_key="fallback-key",
        )
        await surge_manager.send_surge_alert(event)

        keyboard = surge_manager._captured_keyboards[0]
        buttons = keyboard["inline_keyboard"][0]
        # hash 기반 ID가 생성되었는지 확인 — 숫자여야 함
        approve_data = buttons[0]["callback_data"]
        assert approve_data.startswith("approve_")
        fallback_id = approve_data.replace("approve_", "")
        assert fallback_id.isdigit() or fallback_id.lstrip("-").isdigit()

    @pytest.mark.asyncio
    async def test_event_without_url_or_event_key(self, surge_manager):
        """url, event_key 모두 없어도 크래시 없이 동작."""  # [QA 수정] Q1
        event = SimpleNamespace(
            id=None,
            title="최소 이벤트",
            source="unknown_source",
            velocity_score=3.0,
        )
        # getattr fallback이 "mock"으로 떨어짐
        result = await surge_manager.send_surge_alert(event)
        assert result is True

    @pytest.mark.asyncio
    async def test_unknown_source_uses_raw_value(self, surge_manager):
        """알 수 없는 소스는 원문 그대로 표시."""  # [QA 수정] Q1
        event = _make_event(source="reddit")
        await surge_manager.send_surge_alert(event)

        assert any("reddit" in msg for msg in surge_manager._captured_messages)

    @pytest.mark.asyncio
    async def test_send_message_exception_returns_false(self):
        """send_message가 예외를 던지면 False 반환."""
        manager = notification_module.NotificationManager(FakeConfig())

        async def raising_send(*args, **kwargs):
            raise RuntimeError("Discord 연결 실패")

        manager.send_message = raising_send
        event = _make_event()
        result = await manager.send_surge_alert(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_zero_velocity_score(self, surge_manager):
        """velocity_score=0일 때도 정상 동작."""  # [QA 수정] Q1
        event = _make_event(velocity_score=0.0)
        result = await surge_manager.send_surge_alert(event)

        assert result is True
        assert any("0.0" in msg for msg in surge_manager._captured_messages)

    @pytest.mark.asyncio
    async def test_empty_drafts_not_included(self, surge_manager):
        """draft_x/draft_threads가 빈 문자열이면 초안 섹션 미포함."""  # [QA 수정] Q1
        event = _make_event()
        await surge_manager.send_surge_alert(event, draft_x="", draft_threads="")

        full_msg = surge_manager._captured_messages[0]
        assert "X 초안" not in full_msg
        assert "Threads 초안" not in full_msg

    @pytest.mark.asyncio
    async def test_zero_generation_time_not_included(self, surge_manager):
        """generation_time=0이면 생성시간 미표시."""  # [QA 수정] Q1
        event = _make_event()
        await surge_manager.send_surge_alert(event, generation_time=0.0)

        full_msg = surge_manager._captured_messages[0]
        assert "생성시간" not in full_msg
