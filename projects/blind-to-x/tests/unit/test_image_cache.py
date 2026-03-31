from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.image_cache import ImageCache, _cache_key  # noqa: E402


def test_cache_key_normalizes_whitespace() -> None:
    assert _cache_key(" career ", " curious ") == _cache_key("career", "curious")
    assert _cache_key("career", "curious") != _cache_key("career", "serious")


def test_image_cache_round_trip_for_remote_urls(tmp_path) -> None:
    cache = ImageCache(tmp_path / "image_cache.db")
    url = "https://cdn.example.com/image.png"

    assert cache.get("career", "curious") is None

    cache.set("career", "curious", url, provider="gemini")

    assert cache.get("career", "curious") == url
    assert cache.stats() == {"total": 1, "alive": 1, "expired": 0}


def test_image_cache_evicts_missing_local_files_and_expired_rows(tmp_path) -> None:
    cache = ImageCache(tmp_path / "image_cache.db")
    missing_path = str(tmp_path / "missing.png")

    cache.set("career", "anxious", missing_path)
    assert cache.get("career", "anxious") is None
    assert cache.stats()["total"] == 0

    expired_key = _cache_key("career", "expired")
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with cache._conn() as conn:
        conn.execute(
            """
            INSERT INTO image_cache (cache_key, topic, emotion, image_path, provider, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (expired_key, "career", "expired", "https://cdn.example.com/old.png", "gemini", past, past),
        )

    assert cache.stats() == {"total": 1, "alive": 0, "expired": 1}
    assert cache.evict_expired() == 1
    assert cache.stats() == {"total": 0, "alive": 0, "expired": 0}


def test_image_cache_gracefully_handles_database_failures(tmp_path, monkeypatch) -> None:
    cache = ImageCache(tmp_path / "image_cache.db")

    @contextmanager
    def broken_conn():
        raise sqlite3.OperationalError("db offline")
        yield  # pragma: no cover

    monkeypatch.setattr(cache, "_conn", broken_conn)

    assert cache.get("career", "curious") is None
    cache.set("career", "curious", "https://cdn.example.com/image.png")
    assert cache.evict_expired() == 0
    assert cache.stats() == {"total": 0, "alive": 0, "expired": 0}
