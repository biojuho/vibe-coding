import asyncio
import logging
import os
from typing import Optional

import tweepy

logger = logging.getLogger(__name__)


def _env_flag(name: str):
    raw = os.environ.get(name)
    if raw is None:
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class TwitterPoster:
    def __init__(self, config_mgr):
        self.config_mgr = config_mgr
        env_enabled = _env_flag("TWITTER_ENABLED")
        self.enabled = env_enabled if env_enabled is not None else config_mgr.get("twitter.enabled", False)
        self.consumer_key = os.environ.get("TWITTER_CONSUMER_KEY") or config_mgr.get("twitter.consumer_key")
        self.consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET") or config_mgr.get("twitter.consumer_secret")
        self.access_token = os.environ.get("TWITTER_ACCESS_TOKEN") or config_mgr.get("twitter.access_token")
        self.access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET") or config_mgr.get("twitter.access_token_secret")

        if self.enabled:
            try:
                if not all([self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret]):
                    raise ValueError("Missing one or more Twitter API credentials")
                # v1.1 API needed for media upload
                auth = tweepy.OAuth1UserHandler(
                    self.consumer_key,
                    self.consumer_secret,
                    self.access_token,
                    self.access_token_secret
                )
                self.api_v1 = tweepy.API(auth)

                # v2 API for tweeting
                self.client_v2 = tweepy.Client(
                    consumer_key=self.consumer_key,
                    consumer_secret=self.consumer_secret,
                    access_token=self.access_token,
                    access_token_secret=self.access_token_secret
                )
            except Exception as e:
                logger.error(f"Failed to initialize Twitter client: {e}")
                self.enabled = False
                self.api_v1 = None
                self.client_v2 = None
        else:
            self.api_v1 = None
            self.client_v2 = None

    async def post_tweet(
        self,
        text: str,
        image_path: Optional[str] = None,
        max_retries: int = 3,
    ) -> Optional[str]:
        """Tweet을 발행합니다. 429 Rate Limit 시 exponential backoff 재시도."""
        if not self.enabled:
            logger.info("Twitter posting is disabled in config or not properly initialized.")
            return None

        for attempt in range(1, max_retries + 1):
            try:
                media_ids = None
                if image_path:
                    logger.info("Uploading media to Twitter: %s", image_path)
                    media = await asyncio.to_thread(self.api_v1.media_upload, filename=image_path)
                    media_ids = [media.media_id]

                logger.info("Posting tweet (attempt %d/%d)...", attempt, max_retries)
                response = await asyncio.to_thread(
                    self.client_v2.create_tweet, text=text, media_ids=media_ids
                )
                tweet_id = response.data["id"]
                tweet_url = f"https://x.com/user/status/{tweet_id}"
                logger.info("Successfully posted to Twitter: %s", tweet_url)
                return tweet_url

            except tweepy.TooManyRequests as e:
                wait = min(60 * (2 ** (attempt - 1)), 300)  # 60s → 120s → 300s (max 5분)
                if attempt < max_retries:
                    logger.warning(
                        "Twitter rate limit (429). %d/%d 재시도 대기 %ds...",
                        attempt, max_retries, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("Twitter rate limit: 최대 재시도 초과. %s", e)
                    return None

            except tweepy.TwitterServerError as e:
                wait = min(10 * attempt, 60)
                if attempt < max_retries:
                    logger.warning("Twitter 5xx 서버 오류. %ds 후 재시도... %s", wait, e)
                    await asyncio.sleep(wait)
                else:
                    logger.error("Twitter 서버 오류 지속. 발행 실패: %s", e)
                    return None

            except Exception as e:
                logger.error("Failed to post to Twitter: %s", e)
                return None

        return None
