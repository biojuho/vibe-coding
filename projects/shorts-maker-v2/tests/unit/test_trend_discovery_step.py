"""Unit tests for TrendDiscoveryStep."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.pipeline.trend_discovery_step import (
    TrendCandidate,
    TrendDiscoveryStep,
    _CHANNEL_RSS_IDS,
    _CHANNEL_TREND_SEEDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_config():
    return MagicMock()


@pytest.fixture()
def mock_llm_router():
    router = MagicMock()
    router.generate_json.return_value = {
        "candidates": [
            {"keyword": "AI가 바꾼 직업", "rationale": "인기 주제", "score": 0.9},
            {"keyword": "Claude 승인창 이유", "rationale": "인지 부조화", "score": 0.85},
            {"keyword": "바이브코딩 격차", "rationale": "트렌드", "score": 0.8},
        ]
    }
    return router


@pytest.fixture()
def step(mock_config, mock_llm_router):
    return TrendDiscoveryStep(mock_config, llm_router=mock_llm_router)


# ---------------------------------------------------------------------------
# TrendCandidate Tests
# ---------------------------------------------------------------------------

class TestTrendCandidate:
    def test_basic_creation(self):
        c = TrendCandidate(keyword="AI 트렌드", source="youtube_rss", score=0.8, channel="ai_tech")
        assert c.keyword == "AI 트렌드"
        assert c.source == "youtube_rss"
        assert c.score == 0.8
        assert c.channel == "ai_tech"
        assert c.raw_title == ""
        assert c.related_queries == []

    def test_with_all_fields(self):
        c = TrendCandidate(
            keyword="Claude",
            source="google_trends",
            score=0.95,
            channel="ai_tech",
            raw_title="Claude 3.5 Sonnet 출시",
            related_queries=["claude api", "claude vs chatgpt"],
        )
        assert c.raw_title == "Claude 3.5 Sonnet 출시"
        assert len(c.related_queries) == 2


# ---------------------------------------------------------------------------
# Channel Config Tests
# ---------------------------------------------------------------------------

class TestChannelConfig:
    @pytest.mark.parametrize("ch", ["ai_tech", "psychology", "history", "space", "health"])
    def test_rss_ids_have_all_channels(self, ch):
        assert ch in _CHANNEL_RSS_IDS

    @pytest.mark.parametrize("ch", ["ai_tech", "psychology", "history", "space", "health"])
    def test_trend_seeds_have_all_channels(self, ch):
        assert ch in _CHANNEL_TREND_SEEDS
        assert len(_CHANNEL_TREND_SEEDS[ch]) >= 3


# ---------------------------------------------------------------------------
# YouTube RSS Parsing Tests
# ---------------------------------------------------------------------------

class TestParseYouTubeRSS:
    _SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/">
  <title>Test Channel</title>
  <entry>
    <id>yt:video:abc123</id>
    <title>AI가 바꾼 직업 TOP 5</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=abc123"/>
  </entry>
  <entry>
    <id>yt:video:def456</id>
    <title>Claude 승인창을 없앤 이유</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=def456"/>
  </entry>
</feed>"""

    def test_parse_titles(self):
        entries = TrendDiscoveryStep._parse_youtube_rss(self._SAMPLE_RSS)
        assert len(entries) == 2
        assert entries[0]["title"] == "AI가 바꾼 직업 TOP 5"
        assert entries[1]["title"] == "Claude 승인창을 없앤 이유"

    def test_parse_links(self):
        entries = TrendDiscoveryStep._parse_youtube_rss(self._SAMPLE_RSS)
        assert "youtube.com" in entries[0]["link"]

    def test_empty_xml(self):
        entries = TrendDiscoveryStep._parse_youtube_rss("")
        assert entries == []

    def test_malformed_xml(self):
        entries = TrendDiscoveryStep._parse_youtube_rss("not xml at all <<<")
        assert entries == []

    def test_xml_no_entries(self):
        xml = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Empty</title></feed>"""
        entries = TrendDiscoveryStep._parse_youtube_rss(xml)
        assert entries == []


# ---------------------------------------------------------------------------
# LLM Brainstorm Tests
# ---------------------------------------------------------------------------

class TestLLMBrainstorm:
    def test_returns_candidates(self, step, mock_llm_router):
        candidates = step._from_llm_brainstorm("ai_tech", n=3)
        assert len(candidates) == 3
        assert all(c.source == "llm_brainstorm" for c in candidates)
        assert all(c.channel == "ai_tech" for c in candidates)

    def test_score_range(self, step, mock_llm_router):
        candidates = step._from_llm_brainstorm("ai_tech", n=3)
        for c in candidates:
            assert 0.0 <= c.score <= 1.0

    def test_channel_unknown_falls_back_to_channel_key(self, step, mock_llm_router):
        candidates = step._from_llm_brainstorm("unknown_channel", n=2)
        assert all(c.channel == "unknown_channel" for c in candidates)

    def test_llm_error_returns_empty(self, mock_config, mock_llm_router):
        mock_llm_router.generate_json.side_effect = RuntimeError("API down")
        step = TrendDiscoveryStep(mock_config, llm_router=mock_llm_router)
        result = step._from_llm_brainstorm("ai_tech", n=3)
        assert result == []

    def test_llm_non_dict_response_returns_empty(self, mock_config, mock_llm_router):
        mock_llm_router.generate_json.return_value = "invalid"
        step = TrendDiscoveryStep(mock_config, llm_router=mock_llm_router)
        result = step._from_llm_brainstorm("ai_tech", n=3)
        assert result == []

    def test_no_llm_router_returns_empty(self, mock_config):
        step = TrendDiscoveryStep(mock_config, llm_router=None)
        result = step._from_llm_brainstorm("ai_tech", n=3)
        assert result == []


# ---------------------------------------------------------------------------
# run() Integration Tests (mocked sources)
# ---------------------------------------------------------------------------

class TestRun:
    def test_run_deduplicates(self, step, mock_llm_router):
        """중복 키워드는 제거되어야 한다."""
        mock_llm_router.generate_json.return_value = {
            "candidates": [
                {"keyword": "중복 주제", "score": 0.9},
                {"keyword": "중복 주제", "score": 0.8},  # 중복
                {"keyword": "다른 주제", "score": 0.7},
            ]
        }
        # RSS와 Google Trends는 빈 채널로 패스스루 (no channel IDs = empty list)
        with patch.object(step, "_from_youtube_rss", return_value=[]):
            with patch.object(step, "_from_google_trends", return_value=[]):
                candidates = step.run(channel_key="ai_tech", n=10)
        # "중복 주제"는 1개만 있어야 한다
        keywords = [c.keyword for c in candidates]
        assert keywords.count("중복 주제") == 1

    def test_run_sorts_by_score(self, step, mock_llm_router):
        """결과는 score 내림차순이어야 한다."""
        mock_llm_router.generate_json.return_value = {
            "candidates": [
                {"keyword": "낮은 점수", "score": 0.3},
                {"keyword": "높은 점수", "score": 0.95},
                {"keyword": "중간 점수", "score": 0.6},
            ]
        }
        with patch.object(step, "_from_youtube_rss", return_value=[]):
            with patch.object(step, "_from_google_trends", return_value=[]):
                candidates = step.run(channel_key="ai_tech", n=10)
        scores = [c.score for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_run_limits_results(self, step, mock_llm_router):
        """n 개 이상 반환하지 않아야 한다."""
        mock_llm_router.generate_json.return_value = {
            "candidates": [{"keyword": f"주제{i}", "score": 0.5} for i in range(20)]
        }
        with patch.object(step, "_from_youtube_rss", return_value=[]):
            with patch.object(step, "_from_google_trends", return_value=[]):
                candidates = step.run(channel_key="ai_tech", n=3)
        assert len(candidates) <= 3

    def test_run_rss_failure_uses_fallback(self, step, mock_llm_router):
        """RSS 실패 시 LLM brainstorm fallback이 작동해야 한다."""
        with patch.object(step, "_from_youtube_rss", side_effect=Exception("network error")):
            with patch.object(step, "_from_google_trends", return_value=[]):
                candidates = step.run(channel_key="ai_tech", n=5)
        assert len(candidates) > 0
        assert all(c.source == "llm_brainstorm" for c in candidates)

    def test_run_returns_empty_if_all_fail(self, mock_config):
        """모든 소스 실패 시 빈 리스트 반환."""
        step = TrendDiscoveryStep(mock_config, llm_router=None)
        with patch.object(step, "_from_youtube_rss", return_value=[]):
            with patch.object(step, "_from_google_trends", return_value=[]):
                candidates = step.run(channel_key="ai_tech", n=5)
        assert candidates == []


# ---------------------------------------------------------------------------
# httpx not installed
# ---------------------------------------------------------------------------

class TestMissingDependencies:
    def test_from_youtube_rss_raises_import_error_without_httpx(self, step):
        with patch.dict("sys.modules", {"httpx": None}):
            with pytest.raises(ImportError, match="httpx"):
                step._from_youtube_rss("ai_tech")

    def test_from_google_trends_raises_import_error_without_pytrends(self, step):
        with patch.dict("sys.modules", {"pytrends": None, "pytrends.request": None}):
            with pytest.raises(ImportError, match="pytrends"):
                step._from_google_trends("ai_tech")
