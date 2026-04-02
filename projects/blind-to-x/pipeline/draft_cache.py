"""SQLite-backed draft cache shared across blind-to-x runs."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "draft_cache.db"
CACHE_TTL_HOURS = 72


class DraftCache:
    """Persistent draft cache keyed by prompt fingerprint."""

    def __init__(self, db_path: str | Path | None = None, ttl_hours: int = CACHE_TTL_HOURS):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.ttl_hours = ttl_hours
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    @contextmanager
    def _conn(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            try:
                yield conn
                conn.commit()
                try:
                    # Flush recent WAL writes so follow-up reads from fresh
                    # connections can see cache entries deterministically.
                    conn.execute("PRAGMA wal_checkpoint(FULL)")
                except sqlite3.DatabaseError:
                    pass
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS draft_cache (
                    cache_key    TEXT PRIMARY KEY,
                    drafts_json  TEXT NOT NULL,
                    image_prompt TEXT,
                    provider     TEXT NOT NULL DEFAULT '',
                    created_at   TEXT NOT NULL,
                    expires_at   TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_draft_cache_expires ON draft_cache(expires_at);
                """
            )

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _expires_iso(self) -> str:
        return (datetime.now(timezone.utc) + timedelta(hours=self.ttl_hours)).isoformat()

    def get(self, cache_key: str) -> tuple[dict, str | None] | None:
        now = self._now_iso()
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT drafts_json, image_prompt, expires_at FROM draft_cache WHERE cache_key = ?",
                    (cache_key,),
                ).fetchone()
            if row is None:
                return None
            if row["expires_at"] < now:
                self.delete(cache_key)
                return None
            return json.loads(row["drafts_json"]), row["image_prompt"]
        except Exception as exc:
            logger.warning("DraftCache.get() failed (graceful): %s", exc)
            return None

    def set(self, cache_key: str, drafts: dict, image_prompt: str | None, provider: str = "") -> None:
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO draft_cache
                    (cache_key, drafts_json, image_prompt, provider, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cache_key,
                        json.dumps(drafts, ensure_ascii=False),
                        image_prompt,
                        provider,
                        self._now_iso(),
                        self._expires_iso(),
                    ),
                )
        except Exception as exc:
            logger.warning("DraftCache.set() failed (graceful): %s", exc)

    def delete(self, cache_key: str) -> None:
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM draft_cache WHERE cache_key = ?", (cache_key,))
        except Exception:
            pass

    def clear(self) -> None:
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM draft_cache")
        except Exception:
            pass
