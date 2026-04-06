"""Tests for pipeline.process_stages.runtime — 57% → 80%+ coverage target."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


from pipeline.process_stages.runtime import (
    SPAM_KEYWORDS,
    INAPPROPRIATE_TITLE_KEYWORDS,
    REJECT_EMOTION_AXES,
    DRAFT_STYLE_LABELS,
    extract_preferred_tweet_text,
    post_to_twitter,
    get_viral_filter,
)


# ── extract_preferred_tweet_text ─────────────────────────────────────


class TestExtractPreferredTweet:
    def test_none_input(self):
        assert extract_preferred_tweet_text(None) == ""

    def test_empty_dict(self):
        assert extract_preferred_tweet_text({}) == ""

    def test_string_input(self):
        result = extract_preferred_tweet_text("직접 텍스트입니다")
        assert result == "직접 텍스트입니다"

    def test_dict_with_twitter_key(self):
        drafts = {"twitter": "[공감형 트윗]연봉이 적어서 힘들다\n[논쟁형 트윗]연봉 논쟁"}
        result = extract_preferred_tweet_text(drafts)
        assert "연봉이 적어서 힘들다" in result

    def test_preferred_style(self):
        drafts = {"twitter": "[공감형 트윗]공감 내용\n[논쟁형 트윗]논쟁 내용"}
        result = extract_preferred_tweet_text(drafts, preferred_style="논쟁형")
        assert "논쟁 내용" in result

    def test_empty_twitter_key(self):
        drafts = {"twitter": "   "}
        assert extract_preferred_tweet_text(drafts) == ""

    def test_no_style_match_returns_full(self):
        drafts = {"twitter": "스타일 태그 없는 텍스트"}
        result = extract_preferred_tweet_text(drafts)
        assert result == "스타일 태그 없는 텍스트"


# ── post_to_twitter ──────────────────────────────────────────────────


class TestPostToTwitter:
    def test_disabled_poster(self):
        import asyncio

        poster = MagicMock()
        poster.enabled = False
        result = asyncio.run(post_to_twitter(poster, "text", None, None))
        assert result is None

    def test_none_poster(self):
        import asyncio

        result = asyncio.run(post_to_twitter(None, "text", None, None))
        assert result is None

    def test_empty_text(self):
        import asyncio

        poster = MagicMock()
        poster.enabled = True
        result = asyncio.run(post_to_twitter(poster, "", None, None))
        assert result is None

    def test_with_screenshot(self):
        import asyncio

        poster = MagicMock()
        poster.enabled = True
        poster.post_tweet = AsyncMock(return_value={"id": "t123"})
        result = asyncio.run(post_to_twitter(poster, "tweet text", None, "/path/to/img.png"))
        poster.post_tweet.assert_called_once()
        assert result == {"id": "t123"}

    def test_with_ai_temp_url(self):
        import asyncio

        poster = MagicMock()
        poster.enabled = True
        poster.post_tweet = AsyncMock(return_value={"id": "t456"})

        # Mock aiohttp to simulate image download
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"fake-png-data")

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_session_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("pipeline.process_stages.runtime.aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(post_to_twitter(poster, "tweet", "https://img.ai/test.png", None))
        assert result is not None


# ── get_viral_filter ─────────────────────────────────────────────────


class TestGetViralFilter:
    def test_returns_none_no_config(self):
        import pipeline.process_stages.runtime as rt

        rt._viral_filter_instance = None
        result = get_viral_filter(None)
        assert result is None

    def test_returns_none_no_class(self):
        import pipeline.process_stages.runtime as rt

        original = rt._ViralFilterCls
        rt._ViralFilterCls = None
        rt._viral_filter_instance = None
        try:
            result = get_viral_filter({"key": "val"})
            assert result is None
        finally:
            rt._ViralFilterCls = original

    def test_creates_instance(self):
        import pipeline.process_stages.runtime as rt

        rt._viral_filter_instance = None
        result = get_viral_filter({"viral_filter.enabled": False})
        if rt._ViralFilterCls is not None:
            assert result is not None
        rt._viral_filter_instance = None  # cleanup


# ── Constants ────────────────────────────────────────────────────────


class TestConstants:
    def test_spam_keywords_not_empty(self):
        assert len(SPAM_KEYWORDS) > 0

    def test_inappropriate_keywords_not_empty(self):
        assert len(INAPPROPRIATE_TITLE_KEYWORDS) > 0

    def test_reject_emotion_axes(self):
        assert "혐오" in REJECT_EMOTION_AXES

    def test_draft_style_labels(self):
        assert "공감형" in DRAFT_STYLE_LABELS
        assert "논쟁형" in DRAFT_STYLE_LABELS
