"""Extended tests for pipeline.trend_monitor — async paths, Naver, spikes velocity."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.trend_monitor import TrendMonitor


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def monitor():
    """TrendMonitor with sources disabled."""
    return TrendMonitor(
        config={
            "trends.google_enabled": False,
            "trends.naver_enabled": False,
            "trends.cache_ttl_minutes": 1,
            "trends.spike_threshold": 80.0,
        }
    )


# ── fetch_google_trends (async wrapper) ──────────────────────────────


@pytest.mark.asyncio
async def test_fetch_google_trends_disabled(monitor):
    """Google disabled -> empty dict."""
    monitor.google_enabled = False
    result = await monitor.fetch_google_trends()
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_google_trends_timeout(monitor):
    """Timeout should return empty dict."""
    monitor.google_enabled = True

    async def slow_executor(*args, **kwargs):
        await asyncio.sleep(100)
        return {}

    with patch.object(asyncio, "wait_for", side_effect=asyncio.TimeoutError):
        result = await monitor.fetch_google_trends()
        assert result == {}


@pytest.mark.asyncio
async def test_fetch_google_trends_exception(monitor):
    """Generic exception should return empty dict."""
    monitor.google_enabled = True

    def failing_sync():
        raise RuntimeError("network error")

    monitor._fetch_google_trends_sync = failing_sync
    with patch("asyncio.get_event_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=RuntimeError("fail"))
        # The await wrapper catches the exception
        result = await monitor.fetch_google_trends()
        assert result == {}


# ── fetch_naver_trends ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_naver_trends_disabled():
    """Naver disabled -> empty dict."""
    mon = TrendMonitor({"trends.naver_enabled": False})
    result = await mon.fetch_naver_trends()
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_naver_trends_success(monkeypatch):
    """Mock successful Naver API response."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test_id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test_secret")

    mon = TrendMonitor(
        {
            "trends.naver_enabled": True,
            "trends.google_enabled": False,
            "trends.topic_keywords": {"연봉": ["연봉"]},
        }
    )

    mock_response_data = {
        "results": [
            {
                "title": "연봉",
                "data": [{"ratio": 80.0}, {"ratio": 90.0}],
            }
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_response_data)

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_session_ctx)

    mock_session_wrapper = AsyncMock()
    mock_session_wrapper.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_wrapper.__aexit__ = AsyncMock(return_value=False)

    with patch("pipeline.trend_monitor.aiohttp.ClientSession", return_value=mock_session_wrapper):
        result = await mon.fetch_naver_trends()
        assert "연봉" in result
        assert result["연봉"] == pytest.approx(85.0)


@pytest.mark.asyncio
async def test_fetch_naver_trends_api_error(monkeypatch):
    """Naver API returns non-200 -> skipped batch, empty result."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test_id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test_secret")

    mon = TrendMonitor(
        {
            "trends.naver_enabled": True,
            "trends.google_enabled": False,
            "trends.topic_keywords": {"연봉": ["연봉"]},
        }
    )

    mock_resp = AsyncMock()
    mock_resp.status = 403
    mock_resp.text = AsyncMock(return_value="Forbidden")

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_session_ctx)

    mock_session_wrapper = AsyncMock()
    mock_session_wrapper.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_wrapper.__aexit__ = AsyncMock(return_value=False)

    with patch("pipeline.trend_monitor.aiohttp.ClientSession", return_value=mock_session_wrapper):
        result = await mon.fetch_naver_trends()
        assert result == {}


@pytest.mark.asyncio
async def test_fetch_naver_trends_exception(monkeypatch):
    """Network exception -> empty result."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test_id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test_secret")

    mon = TrendMonitor(
        {
            "trends.naver_enabled": True,
            "trends.google_enabled": False,
            "trends.topic_keywords": {"연봉": ["연봉"]},
        }
    )

    with patch("pipeline.trend_monitor.aiohttp.ClientSession", side_effect=Exception("network down")):
        result = await mon.fetch_naver_trends()
        assert result == {}


# ── get_trending_keywords ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_trending_keywords_cache_expired(monitor):
    """Expired cache should re-fetch."""
    monitor._cache = {"old": 50.0}
    monitor._cache_ts = time.time() - 999  # expired
    monitor.google_enabled = False
    monitor.naver_enabled = False

    result = await monitor.get_trending_keywords()
    # Both disabled -> empty merge
    assert result == {}
    # Cache timestamp should be updated
    assert monitor._cache_ts > time.time() - 5


@pytest.mark.asyncio
async def test_get_trending_keywords_merge_google_naver(monitor):
    """Merge results from both sources, taking max score."""

    async def fake_google():
        return {"AI": 80.0, "연봉": 60.0}

    async def fake_naver():
        return {"AI": 70.0, "이직": 90.0}

    monitor.fetch_google_trends = fake_google
    monitor.fetch_naver_trends = fake_naver
    monitor._cache = {}
    monitor._cache_ts = 0

    result = await monitor.get_trending_keywords()
    assert result["AI"] == 80.0  # max of 80, 70
    assert result["연봉"] == 60.0
    assert result["이직"] == 90.0


@pytest.mark.asyncio
async def test_get_trending_keywords_google_exception(monitor):
    """Google returns exception -> only Naver results."""

    async def failing_google():
        raise RuntimeError("google fail")

    async def fake_naver():
        return {"이직": 90.0}

    monitor.fetch_google_trends = failing_google
    monitor.fetch_naver_trends = fake_naver
    monitor._cache = {}
    monitor._cache_ts = 0

    result = await monitor.get_trending_keywords()
    assert result.get("이직") == 90.0


@pytest.mark.asyncio
async def test_get_trending_keywords_naver_exception(monitor):
    """Naver returns exception -> only Google results."""

    async def fake_google():
        return {"AI": 80.0}

    async def failing_naver():
        raise RuntimeError("naver fail")

    monitor.fetch_google_trends = fake_google
    monitor.fetch_naver_trends = failing_naver
    monitor._cache = {}
    monitor._cache_ts = 0

    result = await monitor.get_trending_keywords()
    assert result.get("AI") == 80.0


# ── detect_spikes velocity tracking ──────────────────────────────────


@pytest.mark.asyncio
async def test_detect_spikes_velocity(monitor):
    """Velocity is calculated from previous snapshots."""
    # First call: set up cache and detect
    monitor._cache = {"AI": 90.0}
    monitor._cache_ts = time.time()
    spikes1 = await monitor.detect_spikes()
    assert len(spikes1) == 1
    assert spikes1[0]["velocity"] == 0.0  # no previous snapshot

    # Simulate time passing and score change
    monitor._velocity_snapshots["AI"]["ts"] -= 120  # 2 minutes ago
    monitor._velocity_snapshots["AI"]["score"] = 80.0
    monitor._cache = {"AI": 95.0}  # score increased
    monitor._cache_ts = time.time()

    spikes2 = await monitor.detect_spikes()
    assert len(spikes2) == 1
    assert spikes2[0]["velocity"] != 0.0  # should have velocity now
    assert spikes2[0]["velocity_delta"] != 0.0


@pytest.mark.asyncio
async def test_detect_spikes_below_threshold(monitor):
    """Keywords below threshold not included."""
    monitor._cache = {"low_keyword": 50.0}
    monitor._cache_ts = time.time()
    spikes = await monitor.detect_spikes()
    assert spikes == []


@pytest.mark.asyncio
async def test_detect_spikes_too_short_elapsed(monitor):
    """Elapsed time < 30 seconds -> velocity stays 0."""
    monitor._cache = {"AI": 90.0}
    monitor._cache_ts = time.time()

    # First call
    await monitor.detect_spikes()
    # Don't adjust timestamp, call again immediately
    monitor._cache = {"AI": 95.0}
    monitor._cache_ts = time.time()

    spikes = await monitor.detect_spikes()
    assert len(spikes) == 1
    assert spikes[0]["velocity"] == 0.0  # elapsed < 30s


# ── _fetch_google_trends_sync ────────────────────────────────────────


def test_google_trends_sync_general_exception(monitor):
    """General exception in pytrends -> empty dict + warning."""
    monitor.google_enabled = True

    with patch.dict("sys.modules", {"pytrends": MagicMock(), "pytrends.request": MagicMock()}) as mocked:
        mock_module = mocked["pytrends.request"]
        mock_module.TrendReq.side_effect = Exception("unexpected error")

        result = monitor._fetch_google_trends_sync()
        assert isinstance(result, dict)
