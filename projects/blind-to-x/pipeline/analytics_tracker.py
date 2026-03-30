"""Fetch tweet performance metrics and sync them into Notion."""

from __future__ import annotations

import logging
import os
import re

import tweepy

from pipeline.notion_upload import NotionUploader

logger = logging.getLogger(__name__)


def _env_flag(name: str):
    raw = os.environ.get(name)
    if raw is None:
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class AnalyticsTracker:
    def __init__(self, config_mgr):
        self.config_mgr = config_mgr
        env_enabled = _env_flag("TWITTER_ENABLED")
        self.enabled = env_enabled if env_enabled is not None else config_mgr.get("twitter.enabled", False)
        self.consumer_key = os.environ.get("TWITTER_CONSUMER_KEY") or config_mgr.get("twitter.consumer_key")
        self.consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET") or config_mgr.get("twitter.consumer_secret")
        self.access_token = os.environ.get("TWITTER_ACCESS_TOKEN") or config_mgr.get("twitter.access_token")
        self.access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET") or config_mgr.get(
            "twitter.access_token_secret"
        )
        self.notion_uploader = NotionUploader(config_mgr)

        if not self.enabled:
            self.client_v2 = None
            return

        try:
            if not all([self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret]):
                raise ValueError("Missing one or more Twitter API credentials")
            self.client_v2 = tweepy.Client(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )
        except Exception as exc:
            logger.error("Failed to initialize Twitter client for analytics: %s", exc)
            self.client_v2 = None
            self.enabled = False

    @staticmethod
    def extract_tweet_id(url):
        if not url:
            return None
        match = re.search(r"status/(\d+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _performance_grade(
        views: int,
        likes: int = 0,
        retweets: int = 0,
    ) -> str:
        """다차원 성과 등급 산정 (P1-B1).

        조회수 기반 베이스 + 좋아요율·리트윗율 보너스 포인트 합산.
        S: 100점+, A: 70점+, B: 45점+, C: 20점+, D: 나머지
        """
        # 조회수 베이스 점수 (0-80)
        if views >= 100_000:
            base = 80
        elif views >= 50_000:
            base = 65
        elif views >= 10_000:
            base = 45
        elif views >= 3_000:
            base = 25
        elif views >= 1_000:
            base = 15
        else:
            base = max(0, views / 100)  # 0-10

        # 좋아요율 보너스 (0-15)
        like_rate = (likes / views * 100) if views > 0 else 0
        like_bonus = min(15.0, like_rate * 3)

        # 리트윗율 보너스 (0-15)
        rt_rate = (retweets / views * 100) if views > 0 else 0
        rt_bonus = min(15.0, rt_rate * 5)

        total = base + like_bonus + rt_bonus

        if total >= 100:
            return "S"
        if total >= 70:
            return "A"
        if total >= 45:
            return "B"
        if total >= 20:
            return "C"
        return "D"

    @staticmethod
    def _kst_time_slot() -> str:
        """현재 KST 시간대 슬롯 반환 (P1-B1)."""
        import datetime as _dt

        try:
            kst_hour = (_dt.datetime.now(_dt.timezone.utc).hour + 9) % 24
        except Exception:
            import time as _time

            kst_hour = (_time.gmtime().tm_hour + 9) % 24
        if 6 <= kst_hour < 12:
            return "오전"
        elif 12 <= kst_hour < 14:
            return "점심"
        elif 14 <= kst_hour < 18:
            return "오후"
        elif 18 <= kst_hour < 22:
            return "저녁"
        return "심야"

    async def sync_metrics(self):
        if not self.enabled or not self.client_v2:
            logger.info("Twitter tracking is disabled.")
            return

        if not await self.notion_uploader.ensure_schema():
            logger.error("Notion schema validation failed in AnalyticsTracker.")
            return

        props = self.notion_uploader.props
        db_props = self.notion_uploader._db_properties
        tweet_url_prop = props.get("tweet_url")
        if not tweet_url_prop or tweet_url_prop not in db_props:
            logger.warning("No tweet_url property mapped in Notion. Cannot track analytics.")
            return

        prop_type = db_props[tweet_url_prop]["type"]
        if prop_type == "url":
            filter_params = {"property": tweet_url_prop, "url": {"is_not_empty": True}}
        else:
            filter_params = {"property": tweet_url_prop, "rich_text": {"is_not_empty": True}}

        try:
            response = await self.notion_uploader.query_collection(filter=filter_params, page_size=100)
            pages = response.get("results", [])
            tweet_to_page = {}
            for page in pages:
                url_str = self.notion_uploader.get_page_property_value(page, "tweet_url", default="")
                tweet_id = self.extract_tweet_id(url_str)
                if tweet_id:
                    tweet_to_page[tweet_id] = page.get("id")

            if not tweet_to_page:
                logger.info("No valid tweet IDs found.")
                return

            updated_count = 0
            time_slot = self._kst_time_slot()
            tweet_ids = list(tweet_to_page.keys())
            for start in range(0, len(tweet_ids), 100):
                chunk = tweet_ids[start : start + 100]
                response = self.client_v2.get_tweets(ids=chunk, tweet_fields=["public_metrics"])
                if not response.data:
                    continue

                for tweet in response.data:
                    metrics = tweet.public_metrics or {}
                    page_id = tweet_to_page.get(str(tweet.id))
                    if not page_id:
                        continue

                    views = metrics.get("impression_count", 0) or 0
                    likes = metrics.get("like_count", 0) or 0
                    retweets = metrics.get("retweet_count", 0) or 0
                    update_payload = {
                        "views": views,
                        "likes": likes,
                        "retweets": retweets,
                        "performance_grade": self._performance_grade(int(views), int(likes), int(retweets)),
                    }
                    success = await self.notion_uploader.update_page_properties(
                        page_id,
                        update_payload,
                    )
                    if success:
                        updated_count += 1

            logger.info(
                "Successfully synced metrics for %s tweets (time_slot=%s).",
                updated_count,
                time_slot,
            )
        except Exception as exc:  # pragma: no cover - depends on remote API
            logger.error("Error during analytics sync: %s", exc)
