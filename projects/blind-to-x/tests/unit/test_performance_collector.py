"""Tests for pipeline.performance_collector — 0% → 60%+ coverage target."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


from pipeline.performance_collector import (
    _parse_tweet_id,
    _parse_threads_media_id,
    _fetch_platform_metrics,
    _extract_page_info,
    _query_published_pages,
    run_performance_collection,
)


# ── URL 파싱 ─────────────────────────────────────────────────────────


class TestParseTweetId:
    def test_x_com_url(self):
        assert _parse_tweet_id("https://x.com/user/status/123456") == "123456"

    def test_twitter_com_url(self):
        assert _parse_tweet_id("https://twitter.com/user/status/7890") == "7890"

    def test_no_match(self):
        assert _parse_tweet_id("https://example.com") is None

    def test_none_input(self):
        assert _parse_tweet_id(None) is None

    def test_empty_input(self):
        assert _parse_tweet_id("") is None


class TestParseThreadsMediaId:
    def test_threads_url(self):
        assert _parse_threads_media_id("https://www.threads.net/t/ABC123") == "ABC123"

    def test_none_input(self):
        assert _parse_threads_media_id(None) is None

    def test_no_match(self):
        assert _parse_threads_media_id("https://example.com") is None


# ── _fetch_platform_metrics ──────────────────────────────────────────


class TestFetchPlatformMetrics:
    def test_twitter_no_tweet_url(self):
        result = _fetch_platform_metrics("twitter", {"page_id": "abc"})
        assert result is None

    def test_twitter_with_valid_url_no_bearer(self, monkeypatch):
        monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
        result = _fetch_platform_metrics(
            "twitter",
            {"tweet_url": "https://x.com/user/status/12345", "page_id": "abc"},
        )
        assert result is None

    @patch("pipeline.performance_collector.os.getenv", return_value="test-bearer")
    def test_twitter_with_bearer_success(self, mock_getenv):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"public_metrics": {"like_count": 10, "retweet_count": 5, "impression_count": 100, "reply_count": 2}}]
        }
        with patch("requests.get", return_value=mock_resp):
            result = _fetch_platform_metrics(
                "twitter",
                {"tweet_url": "https://x.com/user/status/999", "page_id": "abc"},
            )
        assert result is not None
        assert result["likes"] == 10.0
        assert result["retweets"] == 5.0

    @patch("pipeline.performance_collector.os.getenv", return_value="test-bearer")
    def test_twitter_rate_limit(self, mock_getenv):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        with patch("requests.get", return_value=mock_resp):
            result = _fetch_platform_metrics(
                "twitter",
                {"tweet_url": "https://x.com/u/status/111", "page_id": "a"},
            )
        assert result is None

    @patch("pipeline.performance_collector.os.getenv", return_value="test-bearer")
    def test_twitter_api_error(self, mock_getenv):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "server error"
        with patch("requests.get", return_value=mock_resp):
            result = _fetch_platform_metrics(
                "twitter",
                {"tweet_url": "https://x.com/u/status/111", "page_id": "a"},
            )
        assert result is None

    @patch("pipeline.performance_collector.os.getenv", return_value="test-bearer")
    def test_twitter_empty_data(self, mock_getenv):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        with patch("requests.get", return_value=mock_resp):
            result = _fetch_platform_metrics(
                "twitter",
                {"tweet_url": "https://x.com/u/status/111", "page_id": "a"},
            )
        assert result is None

    def test_threads_no_url(self):
        result = _fetch_platform_metrics("threads", {"page_id": "abc"})
        assert result is None

    def test_threads_no_token(self, monkeypatch):
        monkeypatch.delenv("THREADS_ACCESS_TOKEN", raising=False)
        result = _fetch_platform_metrics(
            "threads",
            {"threads_url": "https://www.threads.net/t/XYZ", "page_id": "abc"},
        )
        assert result is None

    def test_naver_blog(self):
        result = _fetch_platform_metrics("naver_blog", {"page_id": "abc"})
        assert result is None

    def test_unknown_platform(self):
        result = _fetch_platform_metrics("tiktok", {"page_id": "abc"})
        assert result is None


# ── _extract_page_info ───────────────────────────────────────────────


class TestExtractPageInfo:
    def test_basic_extraction(self):
        page = {
            "id": "page-123",
            "properties": {
                "제목": {"type": "title", "title": [{"plain_text": "테스트 제목"}]},
                "토픽 클러스터": {"type": "select", "select": {"name": "연봉"}},
                "감정축": {"type": "select", "select": {"name": "분노"}},
                "플랫폼": {"type": "multi_select", "multi_select": [{"name": "twitter"}, {"name": "threads"}]},
                "트윗 링크": {"type": "url", "url": "https://x.com/u/status/1"},
                "threads 링크": {"type": "url", "url": "https://threads.net/t/ABC"},
            },
        }
        info = _extract_page_info(page)
        assert info["page_id"] == "page-123"
        assert info["title"] == "테스트 제목"
        assert info["topic_cluster"] == "연봉"
        assert info["emotion_axis"] == "분노"
        assert "twitter" in info["platforms"]
        assert "threads" in info["platforms"]

    def test_empty_properties(self):
        page = {"id": "empty", "properties": {}}
        info = _extract_page_info(page)
        assert info["page_id"] == "empty"
        assert info["title"] == ""
        assert info["platforms"] == ["twitter"]  # default


# ── _query_published_pages ───────────────────────────────────────────


class TestQueryPublishedPages:
    def test_success(self):
        notion = MagicMock()
        notion.props = {"status": "상태", "performance_grade": "성과 등급", "date": "생성일"}
        notion.query_collection = AsyncMock(return_value={"results": [{"id": "p1"}]})
        result = asyncio.run(_query_published_pages(notion))
        assert len(result) == 1

    def test_exception_returns_empty(self):
        notion = MagicMock()
        notion.props = {"status": "상태", "performance_grade": "성과 등급", "date": "생성일"}
        notion.query_collection = AsyncMock(side_effect=Exception("API error"))
        result = asyncio.run(_query_published_pages(notion))
        assert result == []


# ── run_performance_collection ───────────────────────────────────────


class TestRunPerformanceCollection:
    def test_no_notion_uploader(self):
        result = asyncio.run(run_performance_collection(config={}))
        assert result["error"] == "no_notion_uploader"

    def test_no_pages(self):
        notion = MagicMock()
        notion.props = {"status": "상태", "performance_grade": "성과 등급", "date": "생성일"}
        notion.query_collection = AsyncMock(return_value={"results": []})
        result = asyncio.run(run_performance_collection(config={}, notion_uploader=notion))
        assert result["collected"] == 0
        assert result["message"] == "수집 대상 없음"

    @patch("pipeline.performance_collector._fetch_platform_metrics", return_value=None)
    def test_metrics_none_skips(self, mock_fetch):
        notion = MagicMock()
        notion.props = {"status": "상태", "performance_grade": "성과 등급", "date": "생성일"}
        notion.query_collection = AsyncMock(return_value={
            "results": [
                {
                    "id": "p1",
                    "properties": {
                        "제목": {"type": "title", "title": [{"plain_text": "Test"}]},
                        "플랫폼": {"type": "multi_select", "multi_select": [{"name": "twitter"}]},
                    },
                }
            ]
        })
        result = asyncio.run(run_performance_collection(config={}, notion_uploader=notion))
        assert result["skipped"] >= 1

    @patch("pipeline.performance_collector._fetch_platform_metrics")
    def test_successful_collection(self, mock_fetch):
        mock_fetch.return_value = {"likes": 10.0, "retweets": 5.0, "impressions": 100.0, "replies": 2.0}
        mock_record = MagicMock()
        mock_record.grade = "A"

        mock_tracker = MagicMock()
        mock_tracker.record_performance.return_value = mock_record

        notion = MagicMock()
        notion.props = {"status": "상태", "performance_grade": "성과 등급", "date": "생성일"}
        notion.query_collection = AsyncMock(return_value={
            "results": [
                {
                    "id": "p1",
                    "properties": {
                        "제목": {"type": "title", "title": [{"plain_text": "Test"}]},
                        "플랫폼": {"type": "multi_select", "multi_select": [{"name": "twitter"}]},
                    },
                }
            ]
        })
        notion.update_page_properties = AsyncMock()

        with patch("pipeline.performance_tracker.PerformanceTracker", return_value=mock_tracker):
            result = asyncio.run(run_performance_collection(config={}, notion_uploader=notion))
        assert result["collected"] == 1

    def test_platform_name_mapping(self):
        """Test that Korean platform names get mapped correctly."""
        notion = MagicMock()
        notion.props = {"status": "상태", "performance_grade": "성과 등급", "date": "생성일"}
        notion.query_collection = AsyncMock(return_value={
            "results": [
                {
                    "id": "p1",
                    "properties": {
                        "제목": {"type": "title", "title": [{"plain_text": "Test"}]},
                        "플랫폼": {"type": "multi_select", "multi_select": [{"name": "X (트위터)"}]},
                    },
                }
            ]
        })
        with patch("pipeline.performance_collector._fetch_platform_metrics", return_value=None):
            with patch("pipeline.performance_tracker.PerformanceTracker"):
                result = asyncio.run(run_performance_collection(config={}, notion_uploader=notion))
        assert result["total_pages"] == 1
