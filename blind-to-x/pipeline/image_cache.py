"""Image generation cache with topic+emotion key and 48-hour TTL.

Avoids duplicate image-generation API calls for the same topic/emotion pair.
Uses SQLite for persistence across pipeline runs (.tmp/image_cache.db).

Cache key: sha256(topic_cluster + "|" + emotion_axis)
Cached value: image file path or URL (string)
TTL: 48 hours (configurable via CACHE_TTL_HOURS)

Example:
    cache = ImageCache()
    cached = cache.get("경제위기", "불안")
    if cached:
        return cached
    result = await generate_image(prompt)
    cache.set("경제위기", "불안", result)
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "image_cache.db"
CACHE_TTL_HOURS = 48


def _cache_key(topic_cluster: str, emotion_axis: str) -> str:
    raw = f"{(topic_cluster or '').strip()}|{(emotion_axis or '').strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


class ImageCache:
    """SQLite-backed image result cache with TTL eviction.

    Thread-safe (threading.Lock). Multiple pipeline runs share the same DB.
    """

    def __init__(self, db_path: str | Path | None = None, ttl_hours: int = CACHE_TTL_HOURS):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.ttl_hours = ttl_hours
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _conn(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS image_cache (
                    cache_key   TEXT PRIMARY KEY,
                    topic       TEXT NOT NULL DEFAULT '',
                    emotion     TEXT NOT NULL DEFAULT '',
                    image_path  TEXT NOT NULL,
                    provider    TEXT NOT NULL DEFAULT '',
                    created_at  TEXT NOT NULL,
                    expires_at  TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_expires ON image_cache(expires_at);
            """)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _expires_iso(self) -> str:
        return (datetime.now(timezone.utc) + timedelta(hours=self.ttl_hours)).isoformat()

    # ── Public API ───────────────────────────────────────────────────

    def get(self, topic_cluster: str, emotion_axis: str) -> str | None:
        """Return cached image path/URL if exists and not expired, else None."""
        key = _cache_key(topic_cluster, emotion_axis)
        now = self._now_iso()
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT image_path, expires_at FROM image_cache WHERE cache_key = ?",
                    (key,),
                ).fetchone()
            if row is None:
                return None
            if row["expires_at"] < now:
                logger.debug("ImageCache: expired entry for topic=%s emotion=%s", topic_cluster, emotion_axis)
                self._delete(key)
                return None
            logger.info(
                "ImageCache HIT: topic=%s emotion=%s path=%s",
                topic_cluster, emotion_axis, row["image_path"][:60],
            )
            return row["image_path"]
        except Exception as exc:
            logger.warning("ImageCache.get() failed (graceful): %s", exc)
            return None

    def set(
        self,
        topic_cluster: str,
        emotion_axis: str,
        image_path: str,
        provider: str = "",
    ) -> None:
        """Store an image result in the cache."""
        if not image_path:
            return
        key = _cache_key(topic_cluster, emotion_axis)
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO image_cache
                       (cache_key, topic, emotion, image_path, provider, created_at, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        key,
                        topic_cluster or "",
                        emotion_axis or "",
                        image_path,
                        provider,
                        self._now_iso(),
                        self._expires_iso(),
                    ),
                )
            logger.debug(
                "ImageCache SET: topic=%s emotion=%s provider=%s",
                topic_cluster, emotion_axis, provider,
            )
        except Exception as exc:
            logger.warning("ImageCache.set() failed (graceful): %s", exc)

    def evict_expired(self) -> int:
        """Delete all expired entries. Returns count deleted."""
        now = self._now_iso()
        try:
            with self._conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM image_cache WHERE expires_at < ?", (now,)
                )
                deleted = cursor.rowcount
            if deleted:
                logger.info("ImageCache: evicted %d expired entries", deleted)
            return deleted
        except Exception as exc:
            logger.warning("ImageCache.evict_expired() failed: %s", exc)
            return 0

    def stats(self) -> dict:
        """Return current cache stats for dashboard display."""
        try:
            now = self._now_iso()
            with self._conn() as conn:
                total = conn.execute("SELECT COUNT(*) FROM image_cache").fetchone()[0]
                alive = conn.execute(
                    "SELECT COUNT(*) FROM image_cache WHERE expires_at >= ?", (now,)
                ).fetchone()[0]
            return {"total": total, "alive": alive, "expired": total - alive}
        except Exception:
            return {"total": 0, "alive": 0, "expired": 0}

    def _delete(self, key: str) -> None:
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM image_cache WHERE cache_key = ?", (key,))
        except Exception:
            pass
