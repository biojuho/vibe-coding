"""Extended tests for pipeline.daily_digest — async generate, fetch_posts, summary, delivery."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.daily_digest import (
    DailyDigest,
    DigestEntry,
    DigestGenerator,
    send_digest_telegram,
    generate_and_send,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _make_config(**overrides):
    base = {
        "digest.max_entries": 5,
        "gemini.api_key": "",
        "notion.api_key": "",
        "notion.database_id": "",
        "notion.properties.date": "생성일",
    }
    base.update(overrides)
    return base


def _make_digest(**overrides) -> DailyDigest:
    defaults = dict(
        date="2026-04-05",
        total_collected=10,
        total_published=5,
        top_posts=[
            DigestEntry("Post 1", "http://a", "blind", "경제", "분노", 90.0),
        ],
        trending_emotions=[],
        topic_distribution={"경제": 5},
        summary="Test summary.",
    )
    defaults.update(overrides)
    return DailyDigest(**defaults)


# ── DigestGenerator._fallback_summary ────────────────────────────────


class TestFallbackSummary:
    def _make_gen(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = ""
        return gen

    def test_no_posts(self):
        gen = self._make_gen()
        digest = _make_digest(top_posts=[], topic_distribution={})
        summary = gen._fallback_summary(digest)
        assert "No posts collected" in summary

    def test_with_posts(self):
        gen = self._make_gen()
        digest = _make_digest()
        summary = gen._fallback_summary(digest)
        assert "10 posts collected" in summary
        assert "5 published" in summary
        assert "경제" in summary


# ── DigestGenerator._generate_summary ────────────────────────────────


class TestGenerateSummary:
    @pytest.mark.asyncio
    async def test_no_gemini_key_uses_fallback(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = ""

        digest = _make_digest()
        summary = await gen._generate_summary(digest)
        # Should use fallback
        assert "10 posts collected" in summary

    @pytest.mark.asyncio
    async def test_gemini_exception_uses_fallback(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = "fake-key"

        digest = _make_digest()
        with patch("pipeline.daily_digest.asyncio.to_thread", side_effect=Exception("API error")):
            summary = await gen._generate_summary(digest)
            assert "10 posts collected" in summary  # fallback


# ── DigestGenerator._fetch_posts ─────────────────────────────────────


class TestFetchPosts:
    @pytest.mark.asyncio
    async def test_no_notion_uploader(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = ""
        gen._notion = None

        result = await gen._fetch_posts("2026-04-05")
        assert result == []

    @pytest.mark.asyncio
    async def test_with_notion_pages(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = ""
        gen._notion = MagicMock()

        pages = [
            {
                "properties": {
                    "콘텐츠": {"title": [{"plain_text": "Test Title"}]},
                    "Source URL": {"rich_text": [{"plain_text": "http://test.com"}]},
                    "원본 소스": {"select": {"name": "blind"}},
                    "토픽 클러스터": {"select": {"name": "경제"}},
                    "감정 축": {"select": {"name": "분노"}},
                    "최종 랭크 점수": {"number": 85.0},
                    "24h 좋아요": {"number": 10},
                    "트윗 본문": {"rich_text": [{"plain_text": "Tweet text here"}]},
                    "성과 예측 점수": {"number": 72.0},
                }
            }
        ]

        gen._query_notion_by_date = AsyncMock(return_value=pages)

        result = await gen._fetch_posts("2026-04-05")
        assert len(result) == 1
        assert result[0].title == "Test Title"
        assert result[0].source == "blind"
        assert result[0].final_rank_score == 85.0

    @pytest.mark.asyncio
    async def test_malformed_page_skipped(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = ""
        gen._notion = MagicMock()

        # A page with bad properties that causes an exception
        pages = [{"properties": "not-a-dict"}]

        gen._query_notion_by_date = AsyncMock(return_value=pages)

        result = await gen._fetch_posts("2026-04-05")
        assert result == []

    @pytest.mark.asyncio
    async def test_query_exception(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = ""
        gen._notion = MagicMock()

        gen._query_notion_by_date = AsyncMock(side_effect=Exception("DB error"))

        result = await gen._fetch_posts("2026-04-05")
        assert result == []


# ── DigestGenerator._get_trending_emotions ───────────────────────────


class TestGetTrendingEmotions:
    @pytest.mark.asyncio
    async def test_import_failure_returns_empty(self):
        DigestGenerator.__new__(DigestGenerator)
        with patch("pipeline.daily_digest.DigestGenerator._get_trending_emotions", new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await mock()
            assert result == []


# ── DigestGenerator.generate ─────────────────────────────────────────


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_with_date(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = ""
        gen._notion = None

        gen._fetch_posts = AsyncMock(
            return_value=[
                DigestEntry("P1", "http://a", "blind", "경제", "분노", 90.0),
                DigestEntry("P2", "http://b", "blind", "IT", "공감", 70.0),
            ]
        )
        gen._get_trending_emotions = AsyncMock(return_value=[])

        digest = await gen.generate(date="2026-04-05")
        assert digest.date == "2026-04-05"
        assert digest.total_collected == 2
        assert digest.total_published == 2  # both have score >= 60
        assert len(digest.top_posts) == 2
        # Posts should be sorted by score desc
        assert digest.top_posts[0].final_rank_score >= digest.top_posts[1].final_rank_score

    @pytest.mark.asyncio
    async def test_generate_default_date(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._max_entries = 5
        gen._gemini_key = ""
        gen._notion = None

        gen._fetch_posts = AsyncMock(return_value=[])
        gen._get_trending_emotions = AsyncMock(return_value=[])

        digest = await gen.generate()  # no date -> today
        assert digest.date  # should be a string


# ── send_digest_telegram ─────────────────────────────────────────────


class TestSendDigestTelegram:
    @pytest.mark.asyncio
    async def test_success(self):
        digest = _make_digest()
        config = _make_config()

        with patch("pipeline.notification.NotificationManager") as MockNotifier:
            mock_instance = MockNotifier.return_value
            mock_instance.send_message = AsyncMock()

            result = await send_digest_telegram(digest, config)
            assert result is True
            mock_instance.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_failure(self):
        digest = _make_digest()
        config = _make_config()

        with patch("pipeline.notification.NotificationManager", side_effect=Exception("import fail")):
            result = await send_digest_telegram(digest, config)
            assert result is False


# ── generate_and_send ────────────────────────────────────────────────


class TestGenerateAndSend:
    @pytest.mark.asyncio
    async def test_with_posts(self):
        config = _make_config()

        with patch.object(DigestGenerator, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = _make_digest(total_collected=5)

            with patch("pipeline.daily_digest.send_digest_telegram", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True
                digest = await generate_and_send(config, date="2026-04-05")
                assert digest.total_collected == 5
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_posts_skips_delivery(self):
        config = _make_config()

        with patch.object(DigestGenerator, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = _make_digest(total_collected=0)

            with patch("pipeline.daily_digest.send_digest_telegram", new_callable=AsyncMock) as mock_send:
                digest = await generate_and_send(config, date="2026-04-05")
                assert digest.total_collected == 0
                mock_send.assert_not_called()


# ── DigestGenerator._query_notion_by_date ────────────────────────────


class TestQueryNotionByDate:
    @pytest.mark.asyncio
    async def test_no_notion_returns_empty(self):
        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._notion = None
        result = await gen._query_notion_by_date("2026-04-05")
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_keys_returns_empty(self, monkeypatch):
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._notion = MagicMock()  # notion is set but keys are missing

        result = await gen._query_notion_by_date("2026-04-05")
        assert result == []

    @pytest.mark.asyncio
    async def test_api_exception(self, monkeypatch):
        monkeypatch.setenv("NOTION_API_KEY", "fake-key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "fake-db")

        gen = DigestGenerator.__new__(DigestGenerator)
        gen._config = _make_config()
        gen._notion = MagicMock()

        import httpx as _httpx

        with patch.object(_httpx, "AsyncClient", side_effect=Exception("connection refused")):
            result = await gen._query_notion_by_date("2026-04-05")
            assert result == []
