"""Tests for pipeline.trend_monitor — TrendMonitor with Google Trends + Naver DataLab."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.trend_monitor import TrendMonitor  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def monitor():
    """TrendMonitor with both sources disabled (for unit tests)."""
    return TrendMonitor(
        config={
            "trends.google_enabled": False,
            "trends.naver_enabled": False,
            "trends.cache_ttl_minutes": 1,
            "trends.spike_threshold": 80.0,
        }
    )


@pytest.fixture
def monitor_with_cache(monitor):
    """TrendMonitor with pre-populated cache."""
    import time

    monitor._cache = {
        "연봉 인상": 90.0,
        "이직": 85.0,
        "AI": 75.0,
        "부동산": 60.0,
        "커피": 30.0,
    }
    monitor._cache_ts = time.time()
    return monitor


# ── calculate_trend_boost tests ───────────────────────────────────────


def test_trend_boost_no_cache(monitor):
    """캐시 비어있으면 0.0 반환."""
    assert monitor.calculate_trend_boost("연봉 이야기", "연봉 인상 소식") == 0.0


def test_trend_boost_single_match(monitor_with_cache):
    """단일 키워드 매칭 시 점수 반환."""
    boost = monitor_with_cache.calculate_trend_boost("연봉 인상 소식", "올해 연봉이 올랐다")
    assert boost > 0
    assert boost <= 30.0


def test_trend_boost_multiple_matches(monitor_with_cache):
    """다중 키워드 매칭 시 누적 부스트."""
    boost = monitor_with_cache.calculate_trend_boost(
        "연봉 인상 후 이직 고민", "AI 시대에 이직하면서 연봉 인상을 노린다"
    )
    assert boost > monitor_with_cache.calculate_trend_boost("연봉 인상", "올해")


def test_trend_boost_no_match(monitor_with_cache):
    """매칭되는 키워드 없으면 0.0."""
    boost = monitor_with_cache.calculate_trend_boost("오늘 날씨 좋다", "산책 가고 싶다")
    assert boost == 0.0


def test_trend_boost_capped_at_30(monitor_with_cache):
    """최대 30점으로 캡."""
    # 모든 키워드가 매칭되어도 30을 넘지 않아야 함
    text = "연봉 인상 이직 AI 부동산 커피"
    boost = monitor_with_cache.calculate_trend_boost(text, text)
    assert boost <= 30.0


# ── match_topic_cluster tests ─────────────────────────────────────────


def test_match_topic_cluster_exact(monitor):
    """정확한 키워드 매칭."""
    assert monitor.match_topic_cluster("직장인 연봉") == "연봉"
    assert monitor.match_topic_cluster("이직") == "이직"
    assert monitor.match_topic_cluster("AI") == "IT"


def test_match_topic_cluster_no_match(monitor):
    """매칭 없으면 None."""
    assert monitor.match_topic_cluster("날씨") is None
    assert monitor.match_topic_cluster("맛집") is None


# ── detect_spikes tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_detect_spikes_with_cache(monitor_with_cache):
    """캐시 기반 스파이크 감지."""
    spikes = await monitor_with_cache.detect_spikes()
    # 80 이상: "연봉 인상"(90), "이직"(85)
    assert len(spikes) == 2
    keywords = {s["keyword"] for s in spikes}
    assert "연봉 인상" in keywords
    assert "이직" in keywords


@pytest.mark.asyncio
async def test_detect_spikes_empty(monitor):
    """캐시 비어있으면 스파이크 없음."""
    spikes = await monitor.detect_spikes()
    assert spikes == []


# ── get_trending_keywords tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_trending_keywords_cache_hit(monitor_with_cache):
    """캐시 TTL 내에는 캐시된 결과 반환."""
    result = await monitor_with_cache.get_trending_keywords()
    assert result == monitor_with_cache._cache
    assert "연봉 인상" in result


@pytest.mark.asyncio
async def test_trending_keywords_both_disabled(monitor):
    """양쪽 소스 비활성화 시 빈 결과."""
    result = await monitor.get_trending_keywords()
    assert result == {}


# ── Google Trends mock test ───────────────────────────────────────────


def test_google_trends_sync_import_error(monitor):
    """pytrends 미설치 시 빈 결과."""
    monitor.google_enabled = True
    with patch.dict("sys.modules", {"pytrends": None, "pytrends.request": None}):
        result = monitor._fetch_google_trends_sync()
        assert isinstance(result, dict)


# ── Naver DataLab mock test ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_naver_trends_disabled():
    """Naver 비활성화 시 빈 결과."""
    monitor = TrendMonitor({"trends.naver_enabled": False})
    result = await monitor.fetch_naver_trends()
    assert result == {}


# ── Config loading tests ──────────────────────────────────────────────


def test_config_defaults():
    """기본 설정값 확인."""
    monitor = TrendMonitor()
    assert monitor.google_enabled is True
    assert monitor.spike_threshold == 80.0
    assert monitor._cache_ttl == 600  # 10분


def test_config_custom():
    """커스텀 설정값 적용."""
    monitor = TrendMonitor(
        {
            "trends.google_enabled": False,
            "trends.spike_threshold": 50.0,
            "trends.cache_ttl_minutes": 5,
        }
    )
    assert monitor.google_enabled is False
    assert monitor.spike_threshold == 50.0
    assert monitor._cache_ttl == 300
