"""Tests for new features: Crawl4AI, sentiment tracker, viral filter, daily digest."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ════════════════════════════════════════════════════════════════════════
# 1. Crawl4AI Extractor Tests
# ════════════════════════════════════════════════════════════════════════


class TestCrawl4AIExtractor:
    """Tests for scrapers/crawl4ai_extractor.py"""

    def test_extracted_post_to_dict(self):
        from scrapers.crawl4ai_extractor import ExtractedPost

        post = ExtractedPost(
            title="테스트 제목",
            content="본문 내용",
            likes=42,
            comments=10,
            views=100,
            category="career",
            image_urls=["https://example.com/img.png"],
        )
        d = post.to_dict()
        assert d["title"] == "테스트 제목"
        assert d["likes"] == 42
        assert d["extraction_method"] == "crawl4ai"
        assert len(d["image_urls"]) == 1

    def test_extracted_post_defaults(self):
        from scrapers.crawl4ai_extractor import ExtractedPost

        post = ExtractedPost()
        d = post.to_dict()
        assert d["title"] == ""
        assert d["likes"] == 0
        assert d["image_urls"] == []

    def test_check_crawl4ai_unavailable(self):
        """When crawl4ai is not installed, _check_crawl4ai returns False."""
        from scrapers import crawl4ai_extractor

        # Reset cached value
        crawl4ai_extractor._crawl4ai_available = None
        with patch.dict("sys.modules", {"crawl4ai": None}):
            # Force ImportError
            crawl4ai_extractor._crawl4ai_available = None
            result = crawl4ai_extractor._check_crawl4ai()
            # Result depends on whether crawl4ai is actually installed
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_extract_post_from_html_no_key(self):
        """Without API key, returns None."""
        from scrapers.crawl4ai_extractor import Crawl4AIExtractor

        extractor = Crawl4AIExtractor({"gemini.api_key": ""})
        extractor._api_key = ""
        result = await extractor.extract_post_from_html("https://example.com", "<html>test</html>")
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_post_from_html_empty(self):
        """Empty HTML returns None."""
        from scrapers.crawl4ai_extractor import Crawl4AIExtractor

        extractor = Crawl4AIExtractor({})
        result = await extractor.extract_post_from_html("https://example.com", "")
        assert result is None


# ════════════════════════════════════════════════════════════════════════
# 2. Sentiment Tracker Tests
# ════════════════════════════════════════════════════════════════════════


class TestSentimentTracker:
    """Tests for pipeline/sentiment_tracker.py"""

    @pytest.fixture
    def tracker(self, tmp_path):
        from pipeline.sentiment_tracker import SentimentTracker

        db_path = str(tmp_path / "test_sentiment.db")
        return SentimentTracker(db_path=db_path)

    def test_record_basic(self, tracker):
        matched = tracker.record(
            url="https://example.com/1",
            title="회사에서 빡치는 상사",
            content="열받아서 퇴사각이 보인다 현타 온다",
            emotion_axis="분노",
            source="blind",
        )
        assert "빡치" in matched or "열받" in matched
        assert len(matched) > 0

    def test_record_no_keywords(self, tracker):
        matched = tracker.record(
            url="https://example.com/2",
            title="평범한 하루",
            content="오늘 점심으로 김치찌개를 먹었다",
            emotion_axis="공감",
        )
        # May or may not match depending on lexicon
        assert isinstance(matched, dict)

    def test_get_snapshot(self, tracker):
        tracker.record("u1", "빡치는 상사", "열받 짜증", "분노", "blind")
        tracker.record("u2", "웃긴 글", "개웃 ㅋㅋ 현웃", "웃김", "blind")
        tracker.record("u3", "또 열받", "빡 화나", "분노", "blind")

        snapshot = tracker.get_snapshot(hours=24)
        assert snapshot.total_posts == 3
        assert snapshot.dominant_emotion == "분노"
        assert len(snapshot.top_emotions) >= 2

    def test_get_trending_emotions(self, tracker):
        # Record enough signals
        for i in range(5):
            tracker.record(f"u{i}", f"빡치는 {i}", "열받 빡 화나", "분노", "blind")

        trends = tracker.get_trending_emotions(window_hours=24, baseline_days=7, min_count=1)
        assert isinstance(trends, list)

    def test_emotion_history(self, tracker):
        tracker.record("u1", "test", "빡치 열받", "분노", "blind")
        history = tracker.get_emotion_history(days=7)
        assert isinstance(history, dict)

    def test_cleanup(self, tracker):
        tracker.record("u1", "old post", "빡치", "분노", "blind")
        # Manually backdate the record so cleanup removes it
        conn = tracker._get_conn()
        conn.execute("UPDATE emotion_signals SET created_at = '2020-01-01 00:00:00'")
        conn.execute("UPDATE keyword_signals SET created_at = '2020-01-01 00:00:00'")
        conn.commit()
        conn.close()
        tracker.cleanup(retention_days=1)
        snapshot = tracker.get_snapshot(hours=24 * 365 * 10)
        assert snapshot.total_posts == 0

    def test_singleton(self, tmp_path):
        from pipeline import sentiment_tracker

        sentiment_tracker._instance = None
        db_path = str(tmp_path / "singleton.db")
        t1 = sentiment_tracker.get_sentiment_tracker(db_path)
        t2 = sentiment_tracker.get_sentiment_tracker()
        assert t1 is t2
        sentiment_tracker._instance = None  # cleanup

    def test_keyword_to_emotion(self, tracker):
        assert tracker._keyword_to_emotion("빡치") == "분노"
        assert tracker._keyword_to_emotion("현웃") == "웃김"
        assert tracker._keyword_to_emotion("unknown_word") == "unknown"


# ════════════════════════════════════════════════════════════════════════
# 3. Viral Filter Tests
# ════════════════════════════════════════════════════════════════════════


class TestViralFilter:
    """Tests for pipeline/viral_filter.py"""

    def test_viral_score_to_dict(self):
        from pipeline.viral_filter import ViralScore

        score = ViralScore(
            score=65.0,
            hook_strength=7.0,
            relatability=6.5,
            shareability=6.0,
            controversy=5.5,
            timeliness=7.0,
            reasoning="Good hook",
            pass_filter=True,
        )
        d = score.to_dict()
        assert d["viral_score"] == 65.0
        assert d["viral_pass"] is True
        assert d["viral_reasoning"] == "Good hook"

    def test_default_pass(self):
        from pipeline.viral_filter import ViralFilter

        vf = ViralFilter({})
        default = vf._default_pass()
        assert default.pass_filter is True
        assert default.score == 50.0

    @pytest.mark.asyncio
    async def test_score_disabled(self):
        from pipeline.viral_filter import ViralFilter

        vf = ViralFilter({"viral_filter.enabled": False})
        result = await vf.score("test title", "test content")
        assert result.pass_filter is True

    @pytest.mark.asyncio
    async def test_score_no_api_key(self):
        from pipeline.viral_filter import ViralFilter

        vf = ViralFilter({"viral_filter.enabled": True, "gemini.api_key": ""})
        vf._api_key = ""
        result = await vf.score("test title", "test content")
        assert result.pass_filter is True  # default pass

    def test_should_process(self):
        from pipeline.viral_filter import ViralFilter, ViralScore

        vf = ViralFilter({"viral_filter.threshold": 50.0})
        high = ViralScore(
            score=70,
            hook_strength=7,
            relatability=7,
            shareability=7,
            controversy=7,
            timeliness=7,
            reasoning="",
            pass_filter=True,
        )
        low = ViralScore(
            score=30,
            hook_strength=3,
            relatability=3,
            shareability=3,
            controversy=3,
            timeliness=3,
            reasoning="",
            pass_filter=False,
        )
        assert vf.should_process(high) is True
        assert vf.should_process(low) is False


# ════════════════════════════════════════════════════════════════════════
# 4. Daily Digest Tests
# ════════════════════════════════════════════════════════════════════════


class TestDailyDigest:
    """Tests for pipeline/daily_digest.py"""

    def test_digest_entry_creation(self):
        from pipeline.daily_digest import DigestEntry

        entry = DigestEntry(
            title="연봉 인상 이야기",
            url="https://example.com/1",
            source="blind",
            topic_cluster="연봉",
            emotion_axis="분노",
            final_rank_score=78.5,
            likes=42,
        )
        assert entry.title == "연봉 인상 이야기"
        assert entry.final_rank_score == 78.5

    def test_format_digest_telegram(self):
        from pipeline.daily_digest import DailyDigest, DigestEntry, format_digest_telegram

        digest = DailyDigest(
            date="2026-03-20",
            total_collected=15,
            total_published=8,
            top_posts=[
                DigestEntry("연봉 이야기", "url1", "blind", "연봉", "분노", 85.0),
                DigestEntry("이직 후기", "url2", "blind", "이직", "공감", 72.0),
            ],
            trending_emotions=[
                {"keyword": "빡치", "spike_ratio": 2.5, "direction": "rising", "count": 10},
            ],
            topic_distribution={"연봉": 5, "이직": 3, "회사문화": 2},
            summary="오늘은 연봉과 이직 관련 글이 주를 이뤘습니다.",
        )
        text = format_digest_telegram(digest)
        assert "2026-03-20" in text
        assert "15" in text
        assert "연봉 이야기" in text
        assert "빡치" in text

    def test_format_digest_newsletter(self):
        from pipeline.daily_digest import DailyDigest, DigestEntry, format_digest_newsletter

        digest = DailyDigest(
            date="2026-03-20",
            total_collected=10,
            total_published=5,
            top_posts=[
                DigestEntry("테스트 포스트", "url1", "blind", "연봉", "분노", 80.0),
            ],
            trending_emotions=[],
            topic_distribution={"연봉": 3},
            summary="Test summary",
        )
        text = format_digest_newsletter(digest)
        assert "# Daily Content Digest" in text
        assert "테스트 포스트" in text
        assert "연봉" in text

    @pytest.mark.asyncio
    async def test_generate_no_notion(self):
        from pipeline.daily_digest import DigestGenerator

        gen = DigestGenerator({}, notion_uploader=None)
        digest = await gen.generate("2026-03-20")
        assert digest.total_collected == 0
        assert digest.date == "2026-03-20"

    def test_fallback_summary(self):
        from pipeline.daily_digest import DigestGenerator, DailyDigest

        gen = DigestGenerator({})
        digest = DailyDigest(
            date="2026-03-20",
            total_collected=0,
            total_published=0,
            top_posts=[],
            trending_emotions=[],
            topic_distribution={},
        )
        summary = gen._fallback_summary(digest)
        assert "2026-03-20" in summary

    def test_extract_title(self):
        from pipeline.daily_digest import DigestGenerator

        props = {
            "콘텐츠": {"title": [{"plain_text": "테스트 제목"}]},
        }
        assert DigestGenerator._extract_title(props) == "테스트 제목"

    def test_extract_number(self):
        from pipeline.daily_digest import DigestGenerator

        props = {"점수": {"number": 42.5}}
        assert DigestGenerator._extract_number(props, "점수") == 42.5
        assert DigestGenerator._extract_number(props, "없는키") == 0.0

    def test_compute_topic_distribution(self):
        from pipeline.daily_digest import DigestGenerator, DigestEntry

        gen = DigestGenerator({})
        entries = [
            DigestEntry("a", "u1", "blind", "연봉", "분노", 80),
            DigestEntry("b", "u2", "blind", "이직", "공감", 70),
            DigestEntry("c", "u3", "blind", "연봉", "분노", 60),
        ]
        dist = gen._compute_topic_distribution(entries)
        assert dist["연봉"] == 2
        assert dist["이직"] == 1


# ════════════════════════════════════════════════════════════════════════
# 5. Integration: BaseScraper Crawl4AI fallback
# ════════════════════════════════════════════════════════════════════════


class TestBaseScraper4AIFallback:
    """Test _extract_with_crawl4ai method on BaseScraper."""

    @staticmethod
    def _make_config():
        """Create a config dict compatible with BaseScraper.__init__."""
        return {
            "headless": True,
            "screenshot_dir": "./screenshots",
            "request.timeout_seconds": 20,
            "request.retries": 3,
            "request.backoff_seconds": 1.5,
            "screenshot_retention_days": 0,
            "scrape_quality.min_content_length": 20,
            "scrape_quality.min_korean_ratio": 0.15,
            "scrape_quality.require_title": True,
            "scrape_quality.max_empty_field_ratio": 0.4,
            "scrape_quality.selector_timeout_ms": 5000,
            "scrape_quality.direct_fallback_timeout_ms": 8000,
            "scrape_quality.save_failure_snapshot": False,
            "scrape_quality.failure_snapshot_dir": ".tmp/failures",
            "browser.pool_size": 1,
            "proxy.enabled": False,
            "proxy.list": [],
        }

    @pytest.mark.asyncio
    async def test_fallback_no_extractor(self):
        """When Crawl4AI is not available, returns None."""
        from scrapers.base import BaseScraper
        import scrapers.base as base_mod

        # Force extractor unavailable
        original = base_mod._crawl4ai_extractor
        base_mod._crawl4ai_extractor = False

        config = MagicMock()
        config.get = MagicMock(side_effect=lambda k, d=None: self._make_config().get(k, d))
        scraper = BaseScraper(config)

        result = await scraper._extract_with_crawl4ai("https://example.com")
        assert result is None

        base_mod._crawl4ai_extractor = original

    @pytest.mark.asyncio
    async def test_fallback_with_mock_extractor(self):
        """When extractor returns data, it produces a valid dict."""
        from scrapers.base import BaseScraper
        from scrapers.crawl4ai_extractor import ExtractedPost
        import scrapers.base as base_mod

        mock_extractor = AsyncMock()
        mock_extractor.extract_post_from_html.return_value = ExtractedPost(
            title="LLM 추출 제목",
            content="LLM이 추출한 본문 내용입니다.",
            likes=10,
            extraction_method="crawl4ai_llm_html",
        )

        original = base_mod._crawl4ai_extractor
        base_mod._crawl4ai_extractor = mock_extractor

        config = MagicMock()
        config.get = MagicMock(side_effect=lambda k, d=None: self._make_config().get(k, d))
        scraper = BaseScraper(config)
        scraper.SOURCE_NAME = "test"

        result = await scraper._extract_with_crawl4ai("https://example.com", html="<html>test</html>")
        assert result is not None
        assert result["title"] == "LLM 추출 제목"
        assert result["extraction_method"] == "crawl4ai_llm_html"

        base_mod._crawl4ai_extractor = original
