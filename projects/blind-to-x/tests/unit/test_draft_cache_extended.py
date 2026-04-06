"""Extended tests for pipeline.draft_cache — DraftCache SQLite backend."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.draft_cache import DraftCache


# ── DraftCache SQLite backend ────────────────────────────────────────


class TestDraftCacheSQLite:
    @pytest.fixture
    def cache(self, tmp_path):
        """Fresh DraftCache with SQLite backend in tmp_path."""
        # The conftest already patches _DEFAULT_DB_PATH to tmp_path.
        # We also need to ensure the redis backend is not loaded.
        with patch("pipeline.db_backend.get_cache_backend", side_effect=ImportError("no redis"), create=True):
            return DraftCache(db_path=tmp_path / "test_cache.db", ttl_hours=72)

    def test_set_and_get(self, cache):
        drafts = {"twitter": "Hello world", "_provider_used": "gemini"}
        cache.set("key1", drafts, "anime style image prompt", provider="gemini")

        result = cache.get("key1")
        assert result is not None
        stored_drafts, image_prompt = result
        assert stored_drafts["twitter"] == "Hello world"
        assert image_prompt == "anime style image prompt"

    def test_get_missing_key(self, cache):
        result = cache.get("nonexistent")
        assert result is None

    def test_overwrite(self, cache):
        cache.set("key1", {"v": 1}, "prompt1", provider="a")
        cache.set("key1", {"v": 2}, "prompt2", provider="b")
        result = cache.get("key1")
        assert result is not None
        assert result[0]["v"] == 2
        assert result[1] == "prompt2"

    def test_delete(self, cache):
        cache.set("key1", {"v": 1}, None)
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self, cache):
        cache.set("key1", {"v": 1}, None)
        cache.set("key2", {"v": 2}, None)
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_expired_entry(self, cache):
        """Expired entries should return None and be deleted."""
        cache.set("key1", {"v": 1}, None)
        # Manually expire the entry
        with cache._conn() as conn:
            conn.execute(
                "UPDATE draft_cache SET expires_at = '2000-01-01T00:00:00+00:00' WHERE cache_key = ?",
                ("key1",),
            )
        result = cache.get("key1")
        assert result is None

    def test_none_image_prompt(self, cache):
        cache.set("key1", {"v": 1}, None, provider="test")
        result = cache.get("key1")
        assert result is not None
        assert result[1] is None

    def test_unicode_content(self, cache):
        drafts = {"twitter": "연봉 인상 후기! 🎉"}
        cache.set("korean", drafts, "한국어 프롬프트")
        result = cache.get("korean")
        assert result is not None
        assert result[0]["twitter"] == "연봉 인상 후기! 🎉"

    def test_set_exception_handled(self, cache, monkeypatch):
        """SQLite write failure is handled gracefully."""

        def broken_conn():
            raise RuntimeError("disk full")

        monkeypatch.setattr(cache, "_conn", broken_conn)
        # Should not raise
        cache.set("key1", {"v": 1}, None)

    def test_get_exception_handled(self, cache, monkeypatch):
        """SQLite read failure is handled gracefully."""

        def broken_conn():
            raise RuntimeError("corrupt db")

        monkeypatch.setattr(cache, "_conn", broken_conn)
        result = cache.get("key1")
        assert result is None


# ── DraftCache Redis backend ─────────────────────────────────────────


class TestDraftCacheRedis:
    def _make_mock_backend(self, get_val=None, get_exc=None, set_exc=None):
        """Create a mock redis-like backend."""
        backend = MagicMock()
        if get_exc:
            backend.get.side_effect = get_exc
        else:
            backend.get.return_value = get_val
        if set_exc:
            backend.set.side_effect = set_exc
        return backend

    def _make_cache_with_redis(self, tmp_path, mock_backend):
        """Create a DraftCache with a mock redis backend injected."""
        with patch("pipeline.db_backend.get_cache_backend", return_value=mock_backend, create=True):
            cache = DraftCache(db_path=tmp_path / "unused.db")
        # Ensure the redis backend is set
        cache._redis_backend = mock_backend
        return cache

    def test_get_redis_hit(self, tmp_path):
        mock_backend = self._make_mock_backend(get_val={"drafts": {"v": 1}, "image_prompt": "prompt"})
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        result = cache.get("key1")
        assert result is not None
        assert result[0]["v"] == 1
        assert result[1] == "prompt"

    def test_get_redis_miss(self, tmp_path):
        mock_backend = self._make_mock_backend(get_val=None)
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        result = cache.get("key1")
        assert result is None

    def test_get_redis_exception(self, tmp_path):
        mock_backend = self._make_mock_backend(get_exc=RuntimeError("redis down"))
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        result = cache.get("key1")
        assert result is None

    def test_set_redis(self, tmp_path):
        mock_backend = self._make_mock_backend()
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        cache.set("key1", {"v": 1}, "prompt", provider="test")
        mock_backend.set.assert_called_once()

    def test_set_redis_exception(self, tmp_path):
        mock_backend = self._make_mock_backend(set_exc=RuntimeError("redis down"))
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        # Should not raise
        cache.set("key1", {"v": 1}, None)

    def test_delete_redis(self, tmp_path):
        mock_backend = self._make_mock_backend()
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        cache.delete("key1")
        mock_backend.delete.assert_called_once_with("key1")

    def test_clear_redis(self, tmp_path):
        mock_backend = self._make_mock_backend()
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        cache.clear()
        mock_backend.clear.assert_called_once()

    def test_delete_redis_exception(self, tmp_path):
        mock_backend = self._make_mock_backend()
        mock_backend.delete.side_effect = RuntimeError("redis down")
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        # Should not raise
        cache.delete("key1")

    def test_clear_redis_exception(self, tmp_path):
        mock_backend = self._make_mock_backend()
        mock_backend.clear.side_effect = RuntimeError("redis down")
        cache = self._make_cache_with_redis(tmp_path, mock_backend)
        # Should not raise
        cache.clear()
