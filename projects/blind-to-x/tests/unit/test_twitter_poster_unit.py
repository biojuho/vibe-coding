"""Tests for pipeline.twitter_poster — TwitterPoster init and post_tweet branches."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.twitter_poster import TwitterPoster, _env_flag


# ── _env_flag tests ──────────────────────────────────────────────────


class TestEnvFlag:
    def test_none_when_missing(self, monkeypatch):
        monkeypatch.delenv("TEST_FLAG", raising=False)
        assert _env_flag("TEST_FLAG") is None

    def test_true_values(self, monkeypatch):
        for val in ("1", "true", "yes", "on", "TRUE", " True "):
            monkeypatch.setenv("TEST_FLAG", val)
            assert _env_flag("TEST_FLAG") is True

    def test_false_values(self, monkeypatch):
        for val in ("0", "false", "no", "off", "random"):
            monkeypatch.setenv("TEST_FLAG", val)
            assert _env_flag("TEST_FLAG") is False


# ── TwitterPoster init ───────────────────────────────────────────────


class FakeConfig:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)


class TestTwitterPosterInit:
    def test_disabled_by_config(self, monkeypatch):
        monkeypatch.delenv("TWITTER_ENABLED", raising=False)
        monkeypatch.delenv("TWITTER_CONSUMER_KEY", raising=False)
        monkeypatch.delenv("TWITTER_CONSUMER_SECRET", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN_SECRET", raising=False)

        poster = TwitterPoster(FakeConfig({"twitter.enabled": False}))
        assert poster.enabled is False
        assert poster.api_v1 is None
        assert poster.client_v2 is None

    def test_enabled_but_missing_keys(self, monkeypatch):
        """Enabled but missing credentials disables the poster."""
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.delenv("TWITTER_CONSUMER_KEY", raising=False)
        monkeypatch.delenv("TWITTER_CONSUMER_SECRET", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN_SECRET", raising=False)

        with patch("pipeline.twitter_poster.tweepy"):
            # ValueError raised for missing credentials
            poster = TwitterPoster(FakeConfig({"twitter.enabled": True}))
            assert poster.enabled is False

    def test_enabled_with_keys_init_fails(self, monkeypatch):
        """OAuth init failure disables the poster."""
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.setenv("TWITTER_CONSUMER_KEY", "ck")
        monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "cs")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "at")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ats")

        with patch("pipeline.twitter_poster.tweepy") as mock_tweepy:
            mock_tweepy.OAuth1UserHandler.side_effect = Exception("OAuth failed")
            poster = TwitterPoster(FakeConfig({"twitter.enabled": True}))
            assert poster.enabled is False
            assert poster.api_v1 is None
            assert poster.client_v2 is None

    def test_env_flag_overrides_config(self, monkeypatch):
        """TWITTER_ENABLED env overrides config."""
        monkeypatch.setenv("TWITTER_ENABLED", "false")
        poster = TwitterPoster(FakeConfig({"twitter.enabled": True}))
        assert poster.enabled is False


# ── TwitterPoster.post_tweet ─────────────────────────────────────────


class TestPostTweet:
    def _make_poster(self, enabled=True):
        poster = TwitterPoster.__new__(TwitterPoster)
        poster.enabled = enabled
        poster.api_v1 = MagicMock()
        poster.client_v2 = MagicMock()
        return poster

    @pytest.mark.asyncio
    async def test_disabled_returns_none(self):
        poster = self._make_poster(enabled=False)
        result = await poster.post_tweet("hello")
        assert result is None

    @pytest.mark.asyncio
    async def test_successful_tweet_no_image(self):
        poster = self._make_poster()

        mock_response = SimpleNamespace(data={"id": "12345"})

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            result = await poster.post_tweet("hello world")

        assert result is not None
        assert "12345" in result

    @pytest.mark.asyncio
    async def test_successful_tweet_with_image(self):
        poster = self._make_poster()

        mock_media = SimpleNamespace(media_id=99999)
        mock_tweet_response = SimpleNamespace(data={"id": "67890"})

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_media  # media_upload
            return mock_tweet_response  # create_tweet

        with patch("asyncio.to_thread", side_effect=side_effect):
            result = await poster.post_tweet("hello", image_path="/tmp/test.png")

        assert result is not None
        assert "67890" in result

    @pytest.mark.asyncio
    async def test_rate_limit_retry_exhausted(self):
        """TooManyRequests retries and eventually gives up."""
        poster = self._make_poster()

        import tweepy

        with patch("asyncio.to_thread", side_effect=tweepy.TooManyRequests(MagicMock(status_code=429))):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await poster.post_tweet("hello", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_server_error_retry_exhausted(self):
        """TwitterServerError retries and eventually gives up."""
        poster = self._make_poster()

        import tweepy

        with patch("asyncio.to_thread", side_effect=tweepy.TwitterServerError(MagicMock(status_code=503))):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await poster.post_tweet("hello", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_generic_exception_returns_none(self):
        """Generic exception -> no retry, immediate None."""
        poster = self._make_poster()

        with patch("asyncio.to_thread", side_effect=RuntimeError("unknown error")):
            result = await poster.post_tweet("hello", max_retries=3)

        assert result is None
