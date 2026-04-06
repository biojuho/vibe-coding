"""Tests for pipeline.analytics_tracker — sync_metrics path coverage."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class FakeConfig:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)


def _make_tracker(*, enabled=True, monkeypatch=None):
    """Create an AnalyticsTracker with mocked internals."""
    with patch("pipeline.analytics_tracker.NotionUploader") as mock_notion_cls:
        mock_notion = MagicMock()
        mock_notion_cls.return_value = mock_notion

        from pipeline.analytics_tracker import AnalyticsTracker

        cfg = FakeConfig({"twitter.enabled": enabled})
        if monkeypatch:
            if enabled:
                monkeypatch.setenv("TWITTER_ENABLED", "true")
                monkeypatch.setenv("TWITTER_CONSUMER_KEY", "k")
                monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "s")
                monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "t")
                monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ts")
            else:
                monkeypatch.setenv("TWITTER_ENABLED", "false")
                monkeypatch.delenv("TWITTER_CONSUMER_KEY", raising=False)

        tracker = AnalyticsTracker(cfg)
        return tracker, mock_notion


# ── sync_metrics: disabled path ──────────────────────────────────


class TestSyncMetricsDisabled:
    def test_disabled_tracker_returns_early(self, monkeypatch):
        monkeypatch.setenv("TWITTER_ENABLED", "false")
        with patch("pipeline.analytics_tracker.NotionUploader"):
            from pipeline.analytics_tracker import AnalyticsTracker

            tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": False}))
            # Should complete without error
            asyncio.run(tracker.sync_metrics())

    def test_none_client_returns_early(self, monkeypatch):
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.delenv("TWITTER_CONSUMER_KEY", raising=False)
        with patch("pipeline.analytics_tracker.NotionUploader"):
            from pipeline.analytics_tracker import AnalyticsTracker

            tracker = AnalyticsTracker(FakeConfig())
            # enabled=False due to missing creds
            asyncio.run(tracker.sync_metrics())


# ── sync_metrics: schema validation failed ───────────────────────


class TestSyncMetricsSchemaFail:
    def test_schema_validation_fails(self, monkeypatch):
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.setenv("TWITTER_CONSUMER_KEY", "k")
        monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "s")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "t")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ts")

        with patch("pipeline.analytics_tracker.NotionUploader") as mock_cls:
            mock_notion = MagicMock()
            mock_notion.ensure_schema = AsyncMock(return_value=False)
            mock_cls.return_value = mock_notion

            with patch("pipeline.analytics_tracker.tweepy") as mock_tweepy:
                mock_client = MagicMock()
                mock_tweepy.Client.return_value = mock_client

                from pipeline.analytics_tracker import AnalyticsTracker

                tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": True}))
                asyncio.run(tracker.sync_metrics())

                # ensure_schema was called
                mock_notion.ensure_schema.assert_called_once()


# ── sync_metrics: no tweet_url property ──────────────────────────


class TestSyncMetricsNoTweetUrl:
    def test_no_tweet_url_prop(self, monkeypatch):
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.setenv("TWITTER_CONSUMER_KEY", "k")
        monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "s")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "t")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ts")

        with patch("pipeline.analytics_tracker.NotionUploader") as mock_cls:
            mock_notion = MagicMock()
            mock_notion.ensure_schema = AsyncMock(return_value=True)
            mock_notion.props = {}  # no tweet_url prop
            mock_notion._db_properties = {}
            mock_cls.return_value = mock_notion

            with patch("pipeline.analytics_tracker.tweepy") as mock_tweepy:
                mock_client = MagicMock()
                mock_tweepy.Client.return_value = mock_client

                from pipeline.analytics_tracker import AnalyticsTracker

                tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": True}))
                asyncio.run(tracker.sync_metrics())


# ── sync_metrics: full happy path ────────────────────────────────


class TestSyncMetricsHappyPath:
    def test_full_sync_flow(self, monkeypatch):
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.setenv("TWITTER_CONSUMER_KEY", "k")
        monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "s")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "t")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ts")

        with patch("pipeline.analytics_tracker.NotionUploader") as mock_cls:
            mock_notion = MagicMock()
            mock_notion.ensure_schema = AsyncMock(return_value=True)
            mock_notion.props = {"tweet_url": "트윗 URL"}
            mock_notion._db_properties = {"트윗 URL": {"type": "url"}}
            mock_notion.query_collection = AsyncMock(
                return_value={
                    "results": [
                        {"id": "page-1", "properties": {}},
                    ]
                }
            )
            mock_notion.get_page_property_value = MagicMock(return_value="https://x.com/user/status/111222333")
            mock_notion.update_page_properties = AsyncMock(return_value=True)
            mock_cls.return_value = mock_notion

            with patch("pipeline.analytics_tracker.tweepy") as mock_tweepy:
                # Mock tweet data
                fake_tweet = MagicMock()
                fake_tweet.id = "111222333"
                fake_tweet.public_metrics = {
                    "impression_count": 5000,
                    "like_count": 100,
                    "retweet_count": 30,
                }
                mock_client = MagicMock()
                mock_client.get_tweets.return_value = MagicMock(data=[fake_tweet])
                mock_tweepy.Client.return_value = mock_client

                from pipeline.analytics_tracker import AnalyticsTracker

                tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": True}))
                asyncio.run(tracker.sync_metrics())

                mock_notion.update_page_properties.assert_called_once()
                call_args = mock_notion.update_page_properties.call_args
                payload = call_args[0][1]
                assert payload["views"] == 5000
                assert payload["likes"] == 100
                assert payload["retweets"] == 30
                assert payload["performance_grade"] in ("S", "A", "B", "C", "D")

    def test_rich_text_type_filter(self, monkeypatch):
        """When tweet_url is rich_text type, filter should use rich_text."""
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.setenv("TWITTER_CONSUMER_KEY", "k")
        monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "s")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "t")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ts")

        with patch("pipeline.analytics_tracker.NotionUploader") as mock_cls:
            mock_notion = MagicMock()
            mock_notion.ensure_schema = AsyncMock(return_value=True)
            mock_notion.props = {"tweet_url": "트윗 URL"}
            mock_notion._db_properties = {"트윗 URL": {"type": "rich_text"}}
            mock_notion.query_collection = AsyncMock(return_value={"results": []})
            mock_cls.return_value = mock_notion

            with patch("pipeline.analytics_tracker.tweepy") as mock_tweepy:
                mock_tweepy.Client.return_value = MagicMock()
                from pipeline.analytics_tracker import AnalyticsTracker

                tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": True}))
                asyncio.run(tracker.sync_metrics())

                call_args = mock_notion.query_collection.call_args
                assert "rich_text" in str(call_args)

    def test_no_valid_tweet_ids(self, monkeypatch):
        """Pages with no extractable tweet IDs → early return."""
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.setenv("TWITTER_CONSUMER_KEY", "k")
        monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "s")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "t")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ts")

        with patch("pipeline.analytics_tracker.NotionUploader") as mock_cls:
            mock_notion = MagicMock()
            mock_notion.ensure_schema = AsyncMock(return_value=True)
            mock_notion.props = {"tweet_url": "트윗 URL"}
            mock_notion._db_properties = {"트윗 URL": {"type": "url"}}
            mock_notion.query_collection = AsyncMock(return_value={"results": [{"id": "page-1", "properties": {}}]})
            mock_notion.get_page_property_value = MagicMock(return_value="https://example.com/no-tweet")
            mock_cls.return_value = mock_notion

            with patch("pipeline.analytics_tracker.tweepy") as mock_tweepy:
                mock_tweepy.Client.return_value = MagicMock()
                from pipeline.analytics_tracker import AnalyticsTracker

                tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": True}))
                asyncio.run(tracker.sync_metrics())

    def test_empty_tweet_response(self, monkeypatch):
        """Twitter API returns no data for tweet IDs."""
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.setenv("TWITTER_CONSUMER_KEY", "k")
        monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "s")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "t")
        monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ts")

        with patch("pipeline.analytics_tracker.NotionUploader") as mock_cls:
            mock_notion = MagicMock()
            mock_notion.ensure_schema = AsyncMock(return_value=True)
            mock_notion.props = {"tweet_url": "트윗 URL"}
            mock_notion._db_properties = {"트윗 URL": {"type": "url"}}
            mock_notion.query_collection = AsyncMock(return_value={"results": [{"id": "page-1"}]})
            mock_notion.get_page_property_value = MagicMock(return_value="https://x.com/u/status/999")
            mock_cls.return_value = mock_notion

            with patch("pipeline.analytics_tracker.tweepy") as mock_tweepy:
                mock_client = MagicMock()
                mock_client.get_tweets.return_value = MagicMock(data=None)
                mock_tweepy.Client.return_value = mock_client

                from pipeline.analytics_tracker import AnalyticsTracker

                tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": True}))
                asyncio.run(tracker.sync_metrics())
