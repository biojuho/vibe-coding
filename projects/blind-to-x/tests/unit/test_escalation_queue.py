"""Unit tests for pipeline.escalation_queue — EscalationQueue."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock


from pipeline.escalation_queue import EscalationQueue, EventStatus, QueuedEvent


def _make_queue(tmp_path: Path, **kwargs) -> EscalationQueue:
    """테스트용 EscalationQueue (임시 DB)."""
    db_path = tmp_path / "test_escalation.db"
    return EscalationQueue(db_path=db_path, **kwargs)


def _make_spike_event(url="https://blind.com/1", title="테스트", source="blind", velocity=10.0):
    """간이 SpikeEvent mock."""
    event = MagicMock()
    event.url = url
    event.title = title
    event.source = source
    event.velocity_score = velocity
    return event


class TestEscalationQueue:
    """EscalationQueue 단위 테스트."""

    def test_enqueue_returns_id(self, tmp_path):
        q = _make_queue(tmp_path)
        event = _make_spike_event()
        event_id = q.enqueue(event)
        assert event_id is not None
        assert isinstance(event_id, int)
        assert event_id > 0

    def test_duplicate_url_rejected(self, tmp_path):
        q = _make_queue(tmp_path)
        event = _make_spike_event(url="https://blind.com/same")
        first_id = q.enqueue(event)
        second_id = q.enqueue(event)
        assert first_id is not None
        assert second_id is None, "같은 URL은 중복 거부"

    def test_different_urls_accepted(self, tmp_path):
        q = _make_queue(tmp_path)
        e1 = _make_spike_event(url="https://blind.com/1")
        e2 = _make_spike_event(url="https://blind.com/2")
        id1 = q.enqueue(e1)
        id2 = q.enqueue(e2)
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2

    def test_max_pending_capacity(self, tmp_path):
        q = _make_queue(tmp_path, max_pending=2)
        e1 = _make_spike_event(url="https://a.com/1")
        e2 = _make_spike_event(url="https://b.com/2")
        e3 = _make_spike_event(url="https://c.com/3")

        assert q.enqueue(e1) is not None
        assert q.enqueue(e2) is not None
        assert q.enqueue(e3) is None, "용량 초과 시 거부"

    def test_dequeue_pending_returns_highest_velocity(self, tmp_path):
        q = _make_queue(tmp_path)
        e_low = _make_spike_event(url="https://a.com/low", velocity=3.0)
        e_high = _make_spike_event(url="https://b.com/high", velocity=15.0)
        q.enqueue(e_low)
        q.enqueue(e_high)

        events = q.dequeue_pending(limit=1)
        assert len(events) == 1
        assert events[0].velocity_score == 15.0
        assert events[0].status == EventStatus.DRAFTING

    def test_dequeue_changes_status_to_drafting(self, tmp_path):
        q = _make_queue(tmp_path)
        event = _make_spike_event()
        q.enqueue(event)

        dequeued = q.dequeue_pending(limit=1)
        assert len(dequeued) == 1
        assert dequeued[0].status == EventStatus.DRAFTING

        # 다시 dequeue하면 이미 DRAFTING이므로 비어야 함
        second = q.dequeue_pending(limit=1)
        assert len(second) == 0

    def test_update_status(self, tmp_path):
        q = _make_queue(tmp_path)
        event = _make_spike_event()
        event_id = q.enqueue(event)

        success = q.update_status(
            event_id,
            EventStatus.AWAITING_APPROVAL,
            draft_x="tweet draft",
            draft_threads="thread draft",
        )
        assert success is True

        saved = q.get_event(event_id)
        assert saved is not None
        assert saved.status == EventStatus.AWAITING_APPROVAL
        assert saved.draft_x == "tweet draft"
        assert saved.draft_threads == "thread draft"

    def test_update_status_persists_all_optional_fields(self, tmp_path):
        q = _make_queue(tmp_path)
        event_id = q.enqueue(_make_spike_event())

        success = q.update_status(
            event_id,
            EventStatus.APPROVED,
            draft_x="x draft",
            draft_threads="threads draft",
            notion_page_id="page-123",
            telegram_msg_id="msg-456",
        )

        assert success is True
        saved = q.get_event(event_id)
        assert saved is not None
        assert saved.status == EventStatus.APPROVED
        assert saved.draft_x == "x draft"
        assert saved.draft_threads == "threads draft"
        assert saved.notion_page_id == "page-123"
        assert saved.telegram_message_id == "msg-456"

    def test_update_status_nonexistent_id(self, tmp_path):
        q = _make_queue(tmp_path)
        success = q.update_status(99999, EventStatus.APPROVED)
        assert success is False

    def test_ttl_expiration_on_dequeue(self, tmp_path):
        q = _make_queue(tmp_path, event_ttl_seconds=1)
        event = _make_spike_event()
        event_id = q.enqueue(event)

        # _fast_sleeps 픽스처 영향 회피: DB created_at을 TTL 초과 과거로 직접 설정
        import sqlite3
        past_time = time.time() - 10  # 10초 전 → TTL(1초) 확실히 초과
        conn = sqlite3.connect(str(q._db_path))
        conn.execute("UPDATE escalation_events SET created_at = ? WHERE id = ?", (past_time, event_id))
        conn.commit()
        conn.close()

        events = q.dequeue_pending(limit=1)
        assert len(events) == 0, "TTL 만료 이벤트는 자동 EXPIRED 처리"

    def test_get_stats(self, tmp_path):
        q = _make_queue(tmp_path)
        e1 = _make_spike_event(url="https://a.com/1")
        e2 = _make_spike_event(url="https://b.com/2")
        q.enqueue(e1)
        q.enqueue(e2)

        stats = q.get_stats()
        assert stats.get("pending", 0) == 2

    def test_expired_url_can_be_reenqueued(self, tmp_path):
        """만료된 이벤트의 URL은 다시 등록 가능."""
        q = _make_queue(tmp_path, event_ttl_seconds=1)
        event = _make_spike_event(url="https://blind.com/reuse")
        first_id = q.enqueue(event)
        assert first_id is not None

        # _fast_sleeps 픽스처 영향 회피: DB created_at을 TTL 초과 과거로 직접 설정
        import sqlite3
        past_time = time.time() - 10
        conn = sqlite3.connect(str(q._db_path))
        conn.execute("UPDATE escalation_events SET created_at = ? WHERE id = ?", (past_time, first_id))
        conn.commit()
        conn.close()

        q.dequeue_pending()  # TTL 만료 트리거

        second_id = q.enqueue(event)
        assert second_id is not None, "만료 후 재등록 가능"

    def test_schema_is_idempotent(self, tmp_path):
        """DB 스키마 생성이 멱등적."""
        db_path = tmp_path / "idempotent.db"
        EscalationQueue(db_path=db_path)
        q2 = EscalationQueue(db_path=db_path)  # 같은 DB로 다시 초기화
        event = _make_spike_event()
        event_id = q2.enqueue(event)
        assert event_id is not None


class TestQueuedEvent:
    """QueuedEvent 데이터 클래스 테스트."""

    def test_defaults(self):
        event = QueuedEvent(
            id=1,
            url="https://a.com",
            title="T",
            source="blind",
            velocity_score=5.0,
            status=EventStatus.PENDING,
            created_at=time.time(),
            updated_at=time.time(),
        )
        assert event.draft_x == ""
        assert event.draft_threads == ""
        assert event.notion_page_id == ""


class TestEventStatus:
    """EventStatus enum 값 확인."""

    def test_all_values(self):
        expected = {"pending", "drafting", "awaiting", "approved", "rejected", "expired", "published"}
        actual = {e.value for e in EventStatus}
        assert actual == expected
