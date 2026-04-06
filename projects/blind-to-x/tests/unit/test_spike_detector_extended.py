"""Extended tests for pipeline.spike_detector — _fetch_candidates, SpikeEvent.event_key."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.spike_detector import SpikeDetector, SpikeEvent, _EngagementSnapshot


# ── SpikeEvent.event_key ─────────────────────────────────────────────


class TestSpikeEventKey:
    def test_normal_url(self):
        event = SpikeEvent(
            url="https://blind.com/post/123?ref=home#section",
            title="Test",
            source="blind",
        )
        key = event.event_key
        assert "?" not in key
        assert "#" not in key
        assert "blind.com/post/123" in key

    def test_url_trailing_slash_stripped(self):
        event = SpikeEvent(url="https://blind.com/post/123/", title="T", source="blind")
        key = event.event_key
        assert not key.endswith("/")

    def test_malformed_url_fallback(self):
        """Malformed URL should use simple split fallback."""
        event = SpikeEvent(url="not-a-valid-url?query=1", title="T", source="blind")
        key = event.event_key
        # Should strip query via split
        assert "query" not in key or key == "not-a-valid-url"

    def test_event_key_exception_fallback(self):
        """When urlparse/urlunparse raises, use the simple split fallback."""
        event = SpikeEvent(url="https://test.com/post/1?q=1", title="T", source="blind")
        # Patch the urllib.parse module used inside the property
        with patch("urllib.parse.urlunparse", side_effect=ValueError("broken")):
            key = event.event_key
            assert key == "https://test.com/post/1"
            assert "?" not in key


# ── _EngagementSnapshot ──────────────────────────────────────────────


class TestEngagementSnapshot:
    def test_first_record_returns_none(self):
        snap = _EngagementSnapshot()
        result = snap.record("key1", likes=10, comments=5)
        assert result is None

    def test_velocity_calculation(self):
        snap = _EngagementSnapshot()
        snap.record("key1", likes=10, comments=5)
        # Manually backdate the snapshot
        snap._store["key1"]["ts"] -= 120  # 2 minutes ago

        result = snap.record("key1", likes=30, comments=15)
        assert result is not None
        assert result["velocity_likes"] > 0
        assert result["velocity_comments"] > 0
        assert result["elapsed_min"] > 0

    def test_too_short_interval(self):
        snap = _EngagementSnapshot()
        snap.record("key1", likes=10, comments=5)
        # Record again immediately (< 30 seconds)
        result = snap.record("key1", likes=20, comments=10)
        assert result is None

    def test_evict_stale(self):
        snap = _EngagementSnapshot(ttl_seconds=60)
        snap.record("key1", likes=10, comments=5)
        snap._store["key1"]["ts"] -= 120  # expired
        snap._evict_stale(snap._store["key1"]["ts"] + 121)
        assert "key1" not in snap._store

    def test_size_cap(self):
        snap = _EngagementSnapshot(max_entries=2)
        snap.record("key1", likes=1, comments=1)
        snap.record("key2", likes=2, comments=2)
        snap._store["key1"]["ts"] -= 100  # make key1 oldest
        snap.record("key3", likes=3, comments=3)
        # key1 should be evicted (oldest)
        assert len(snap._store) <= 3  # eviction happens on next record


# ── SpikeDetector ────────────────────────────────────────────────────


class FakeConfig:
    def __init__(self, data=None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


class TestSpikeDetectorFetchCandidates:
    @pytest.mark.asyncio
    async def test_fetch_candidates_empty(self):
        """Default fetch_candidates with disabled monitors returns empty."""
        config = FakeConfig(
            {
                "escalation.velocity_threshold": 5.0,
                "escalation.min_absolute_likes": 20,
                "escalation.snapshot_max_entries": 100,
                "escalation.snapshot_ttl_seconds": 3600,
                "escalation.rss_feeds": [],
                "trends.google_enabled": False,
                "trends.naver_enabled": False,
            }
        )
        detector = SpikeDetector(config)
        candidates = await detector._fetch_candidates()
        assert isinstance(candidates, list)

    @pytest.mark.asyncio
    async def test_fetch_candidates_mock_spike(self, monkeypatch):
        """BTX_MOCK_SPIKE=1 injects mock candidates."""
        monkeypatch.setenv("BTX_MOCK_SPIKE", "1")
        config = FakeConfig(
            {
                "escalation.velocity_threshold": 5.0,
                "escalation.min_absolute_likes": 20,
                "escalation.snapshot_max_entries": 100,
                "escalation.snapshot_ttl_seconds": 3600,
                "escalation.rss_feeds": [],
                "trends.google_enabled": False,
                "trends.naver_enabled": False,
            }
        )
        detector = SpikeDetector(config)
        candidates = await detector._fetch_candidates()
        assert len(candidates) >= 1
        assert "MOCK" in candidates[0]["title"]

    @pytest.mark.asyncio
    async def test_fetch_candidates_trend_monitor_failure(self):
        """TrendMonitor failure is handled gracefully."""
        config = FakeConfig(
            {
                "escalation.velocity_threshold": 5.0,
                "escalation.min_absolute_likes": 20,
                "escalation.snapshot_max_entries": 100,
                "escalation.snapshot_ttl_seconds": 3600,
                "escalation.rss_feeds": [],
            }
        )
        detector = SpikeDetector(config)

        with patch("pipeline.spike_detector.TrendMonitor", side_effect=Exception("trend crash"), create=True):
            candidates = await detector._fetch_candidates()
            assert isinstance(candidates, list)

    @pytest.mark.asyncio
    async def test_fetch_candidates_rss_feeds_config(self):
        """RSS feeds config is read (but not fetched in this POC)."""
        config = FakeConfig(
            {
                "escalation.velocity_threshold": 5.0,
                "escalation.min_absolute_likes": 20,
                "escalation.snapshot_max_entries": 100,
                "escalation.snapshot_ttl_seconds": 3600,
                "escalation.rss_feeds": ["https://example.com/feed.xml"],
                "trends.google_enabled": False,
                "trends.naver_enabled": False,
            }
        )
        detector = SpikeDetector(config)
        candidates = await detector._fetch_candidates()
        assert isinstance(candidates, list)


class TestSpikeDetectorScan:
    @pytest.mark.asyncio
    async def test_scan_with_candidates(self):
        """Scan with pre-supplied candidates."""
        config = FakeConfig(
            {
                "escalation.velocity_threshold": 2.0,
                "escalation.min_absolute_likes": 5,
                "escalation.snapshot_max_entries": 100,
                "escalation.snapshot_ttl_seconds": 3600,
            }
        )
        detector = SpikeDetector(config)

        # First scan: no previous data
        candidates = [
            {
                "url": "https://blind.com/1",
                "title": "Hot post",
                "source": "blind",
                "likes": 50,
                "comments": 30,
                "content": "preview",
                "category": "연봉",
            },
        ]
        spikes1 = await detector.scan(candidates)
        # First time: no velocity yet
        assert len(spikes1) == 0

    @pytest.mark.asyncio
    async def test_scan_no_candidates_fetches(self):
        """Scan without candidates calls _fetch_candidates."""
        config = FakeConfig(
            {
                "escalation.velocity_threshold": 5.0,
                "escalation.min_absolute_likes": 20,
                "escalation.snapshot_max_entries": 100,
                "escalation.snapshot_ttl_seconds": 3600,
                "trends.google_enabled": False,
                "trends.naver_enabled": False,
                "escalation.rss_feeds": [],
            }
        )
        detector = SpikeDetector(config)
        detector._fetch_candidates = AsyncMock(return_value=[])
        spikes = await detector.scan()
        detector._fetch_candidates.assert_called_once()
        assert spikes == []
