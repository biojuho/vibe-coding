"""바이럴 에스컬레이션 이벤트 큐 (Viral Escalation Engine — Layer 2).

SpikeDetector가 감지한 스파이크 이벤트를 우선순위 큐로 관리하며,
중복 필터링, TTL 만료, 처리 상태 추적을 담당한다.

Architecture:
    SpikeDetector ──▶ EscalationQueue ──▶ ExpressDraftPipeline
    (spike_detector.py)   (이 모듈)         (express_draft.py)

Persistence: SQLite (cost_db.py와 같은 패턴)
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

_BTX_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _BTX_ROOT / "data" / "escalation_queue.db"


class EventStatus(Enum):
    """에스컬레이션 이벤트 상태."""

    PENDING = "pending"  # 초안 생성 대기
    DRAFTING = "drafting"  # 초안 생성 중
    AWAITING_APPROVAL = "awaiting"  # 텔레그램 승인 대기
    APPROVED = "approved"  # 승인 완료
    REJECTED = "rejected"  # 거부됨
    EXPIRED = "expired"  # TTL 만료
    PUBLISHED = "published"  # 발행 완료


@dataclass
class QueuedEvent:
    """큐에 저장된 에스컬레이션 이벤트."""

    id: int
    url: str
    title: str
    source: str
    velocity_score: float
    status: EventStatus
    created_at: float
    updated_at: float
    content_preview: str = ""
    draft_x: str = ""
    draft_threads: str = ""
    notion_page_id: str = ""
    telegram_message_id: str = ""
    metadata_json: str = "{}"


class EscalationQueue:
    """영속 에스컬레이션 이벤트 큐.

    Args:
        db_path: SQLite DB 파일 경로 (기본: data/escalation_queue.db).
        event_ttl_seconds: 이벤트 만료 시간 (기본: 2시간 = 골든타임 이후 의미 없음).
        max_pending: 동시 대기 중인 최대 이벤트 수 (기본: 10).
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        event_ttl_seconds: int = 7200,
        max_pending: int = 10,
    ):
        self._db_path = Path(db_path) if db_path else _DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ttl = event_ttl_seconds
        self._max_pending = max_pending
        self._lock = threading.RLock()
        self._init_schema()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        """SQLite 연결 context manager — WAL 모드, busy_timeout 설정."""
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """에스컬레이션 큐 테이블 생성."""
        with self._lock, self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS escalation_events (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    url              TEXT NOT NULL,
                    url_canonical    TEXT NOT NULL,
                    title            TEXT NOT NULL DEFAULT '',
                    source           TEXT NOT NULL DEFAULT 'unknown',
                    velocity_score   REAL NOT NULL DEFAULT 0.0,
                    status           TEXT NOT NULL DEFAULT 'pending',
                    created_at       REAL NOT NULL,
                    updated_at       REAL NOT NULL,
                    content_preview  TEXT NOT NULL DEFAULT '',
                    draft_x          TEXT NOT NULL DEFAULT '',
                    draft_threads    TEXT NOT NULL DEFAULT '',
                    notion_page_id   TEXT NOT NULL DEFAULT '',
                    telegram_msg_id  TEXT NOT NULL DEFAULT '',
                    metadata_json    TEXT NOT NULL DEFAULT '{}'
                )
            """)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(escalation_events)").fetchall()}
            if "content_preview" not in columns:
                conn.execute("ALTER TABLE escalation_events ADD COLUMN content_preview TEXT NOT NULL DEFAULT ''")
                logger.info("EscalationQueue: content_preview 컬럼 마이그레이션 완료")
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_esc_status
                ON escalation_events(status)
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_esc_url_canonical
                ON escalation_events(url_canonical)
                WHERE status NOT IN ('expired', 'rejected', 'published')
            """)

    def _canonicalize(self, url: str) -> str:
        """URL 정규화 — 쿼리/프래그먼트 제거."""
        try:
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(url)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))
        except Exception:
            return url.split("?")[0].rstrip("/")

    # ── 큐 조작 API ──────────────────────────────────────────────────

    def enqueue(self, spike_event: Any) -> int | None:
        """SpikeEvent를 큐에 추가.

        이미 활성 상태(pending/drafting/awaiting)인 동일 URL은 무시.

        Returns:
            새로 생성된 이벤트 ID, 또는 중복/용량 초과 시 None.
        """
        now = time.time()
        canonical = self._canonicalize(spike_event.url)

        with self._lock, self._conn() as conn:
            # 중복 체크 (활성 이벤트)
            existing = conn.execute(
                """SELECT id FROM escalation_events
                   WHERE url_canonical = ?
                     AND status NOT IN ('expired', 'rejected', 'published')""",
                (canonical,),
            ).fetchone()
            if existing:
                logger.debug("EscalationQueue: 중복 스킵 — %s", spike_event.url[:60])
                return None

            # 용량 체크
            pending_count = conn.execute(
                """SELECT COUNT(*) FROM escalation_events
                   WHERE status IN ('pending', 'drafting', 'awaiting')""",
            ).fetchone()[0]
            if pending_count >= self._max_pending:
                logger.warning(
                    "EscalationQueue: 최대 대기(%d) 초과. 이벤트 거부.",
                    self._max_pending,
                )
                return None

            content_preview = getattr(spike_event, "content_preview", "") or ""
            cursor = conn.execute(
                """INSERT INTO escalation_events
                   (url, url_canonical, title, source, velocity_score,
                    status, created_at, updated_at, content_preview, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    spike_event.url,
                    canonical,
                    spike_event.title,
                    spike_event.source,
                    spike_event.velocity_score,
                    EventStatus.PENDING.value,
                    now,
                    now,
                    content_preview[:200],  # 200자 제한 (경량 초안용)
                    "{}",
                ),
            )
            event_id = cursor.lastrowid
            logger.info(
                "EscalationQueue: 이벤트 등록 #%d — [%s] %s (v=%.2f)",
                event_id,
                spike_event.source,
                spike_event.title[:40],
                spike_event.velocity_score,
            )
            return event_id

    def dequeue_pending(self, limit: int = 1) -> list[QueuedEvent]:
        """가장 높은 velocity_score의 PENDING 이벤트를 DRAFTING으로 전환 후 반환."""
        now = time.time()
        with self._lock, self._conn() as conn:
            # TTL 만료 처리 먼저
            conn.execute(
                """UPDATE escalation_events
                   SET status = ?, updated_at = ?
                   WHERE status IN ('pending', 'drafting', 'awaiting')
                     AND created_at < ?""",
                (EventStatus.EXPIRED.value, now, now - self._ttl),
            )

            rows = conn.execute(
                """SELECT * FROM escalation_events
                   WHERE status = ?
                   ORDER BY velocity_score DESC
                   LIMIT ?""",
                (EventStatus.PENDING.value, limit),
            ).fetchall()

            events = []
            for row in rows:
                conn.execute(
                    """UPDATE escalation_events
                       SET status = ?, updated_at = ?
                       WHERE id = ?""",
                    (EventStatus.DRAFTING.value, now, row["id"]),
                )
                events.append(self._row_to_event(row, override_status=EventStatus.DRAFTING))

            return events

    def update_status(
        self,
        event_id: int,
        status: EventStatus,
        draft_x: str | None = None,
        draft_threads: str | None = None,
        notion_page_id: str | None = None,
        telegram_msg_id: str | None = None,
    ) -> bool:
        """이벤트 상태 업데이트."""
        now = time.time()
        with self._lock, self._conn() as conn:
            assignments = ["status = ?", "updated_at = ?"]
            params: list[Any] = [status.value, now]

            if draft_x is not None:
                assignments.append("draft_x = ?")
                params.append(draft_x)
            if draft_threads is not None:
                assignments.append("draft_threads = ?")
                params.append(draft_threads)
            if notion_page_id is not None:
                assignments.append("notion_page_id = ?")
                params.append(notion_page_id)
            if telegram_msg_id is not None:
                assignments.append("telegram_msg_id = ?")
                params.append(telegram_msg_id)

            params.append(event_id)
            sql = "UPDATE escalation_events SET " + ", ".join(assignments) + " WHERE id = ?"  # nosec B608
            result = conn.execute(
                sql,
                params,
            )
            return result.rowcount > 0

    def get_event(self, event_id: int) -> QueuedEvent | None:
        """이벤트 ID로 조회."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM escalation_events WHERE id = ?",
                (event_id,),
            ).fetchone()
            if row:
                return self._row_to_event(row)
            return None

    def get_stats(self) -> dict[str, int]:
        """큐 상태 통계."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM escalation_events GROUP BY status",
            ).fetchall()
            return {row["status"]: row["cnt"] for row in rows}

    # ── 내부 헬퍼 ────────────────────────────────────────────────────

    @staticmethod
    def _row_to_event(row: sqlite3.Row, override_status: EventStatus | None = None) -> QueuedEvent:
        # content_preview가 없는 레거시 DB 행 대응
        try:
            content_preview = row["content_preview"]
        except (IndexError, KeyError):
            content_preview = ""
        return QueuedEvent(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            source=row["source"],
            velocity_score=row["velocity_score"],
            status=override_status or EventStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            content_preview=content_preview,
            draft_x=row["draft_x"],
            draft_threads=row["draft_threads"],
            notion_page_id=row["notion_page_id"],
            telegram_message_id=row["telegram_msg_id"],
            metadata_json=row["metadata_json"],
        )
