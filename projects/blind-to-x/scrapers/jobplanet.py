"""Jobplanet (jobplanet.co.kr) community scraper implementation."""

import asyncio
import logging
import os
import re
import uuid

try:
    from patchright.async_api import TimeoutError as PlaywrightTimeoutError  # noqa: F401
except ImportError:
    pass

from config import ERROR_SCRAPE_FAILED, ERROR_SCRAPE_PARSE_FAILED
from scrapers.base import BaseScraper, FeedCandidate

logger = logging.getLogger(__name__)


class _JobplanetScrapeFailure(Exception):
    def __init__(self, message: str, *, reason: str, stage: str = "post_fetch"):
        super().__init__(message)
        self.reason = reason
        self.stage = stage


class JobplanetScraper(BaseScraper):
    """Scraper for jobplanet.co.kr Korean workplace community."""

    SOURCE_NAME = "jobplanet"

    BASE_URL = "https://www.jobplanet.co.kr"

    # ── URL helpers ──────────────────────────────────────────────────
    def _normalize_url(self, href):
        if not href:
            return None
        if href.startswith("/"):
            return f"{self.BASE_URL}{href}"
        if "jobplanet.co.kr" in href:
            return href
        return None

    # ── Feed URL fetching ────────────────────────────────────────────
    async def _fetch_post_urls(self, feed_url, label="posts", limit=5):
        """잡플래닛 커뮤니티 API에서 게시글 URL을 수집합니다."""
        urls = []
        self.last_feed_fetch_error = None
        self.last_feed_fetch_reason = None
        async with self._new_page_cm() as page:
            try:
                logger.info(f"Fetching {label} from API: {feed_url}...")
                response = await page.goto(feed_url, timeout=30000)
                if response and response.status == 200:
                    json_data = await response.json()

                    items = json_data.get("data", {}).get("items", [])
                    for item in items[:limit]:
                        post_id = item.get("id")
                        if post_id:
                            urls.append(f"{self.BASE_URL}/community/posts/{post_id}")

                    logger.info(f"Found {len(urls)} {label} from JSON API.")
                elif response and response.status in [403, 404]:
                    logger.warning(f"API fetch returned status {response.status} for {label}")
                    self.last_feed_fetch_error = f"API fetch blocked ({label}): Status {response.status}"
                    self.last_feed_fetch_reason = "api_fetch_blocked"
                else:
                    self.last_feed_fetch_error = (
                        f"API fetch failed ({label}): Status {response.status if response else 'Unknown'}"
                    )
                    self.last_feed_fetch_reason = "api_fetch_failed"
                    logger.error(self.last_feed_fetch_error)
            except Exception as e:
                self.last_feed_fetch_error = f"Feed fetch failed ({label}): {e}"
                self.last_feed_fetch_reason = "feed_fetch_failed"
                logger.warning(self.last_feed_fetch_error)

        return urls

    async def get_popular_urls(self, limit=5):
        """잡플래닛 커뮤니티 인기글(베스트) 목록에서 URL을 수집합니다."""
        return await self._fetch_post_urls(
            f"{self.BASE_URL}/api/v5/community/posts/popular?limit={max(10, limit)}&is_shuffle=true",
            label="popular posts (잡플래닛 인기글)",
            limit=limit,
        )

    async def get_trending_urls(self, limit=5):
        """잡플래닛 커뮤니티 최신 인기 목록에서 URL을 수집합니다."""
        return await self._fetch_post_urls(
            f"{self.BASE_URL}/api/v5/community/posts?limit={max(20, limit)}&order_by=recent",
            label="trending posts (잡플래닛 HOT)",
            limit=limit,
        )

    async def get_feed_urls(self, mode="trending", limit=5):
        """통합 피드 URL getter. mode: 'trending' 또는 'popular'."""
        if mode == "popular":
            return await self.get_popular_urls(limit=limit)
        return await self.get_trending_urls(limit=limit)

    # ── Feed candidates with titles ──────────────────────────────────
    async def get_feed_candidates(self, mode="trending", limit=5):
        """JSON API에서 제목 + 좋아요/댓글을 추출하여 FeedCandidate 반환."""
        api_url = (
            f"{self.BASE_URL}/api/v5/community/posts/popular?limit={max(10, limit)}&is_shuffle=true"
            if mode == "popular"
            else f"{self.BASE_URL}/api/v5/community/posts?limit={max(20, limit)}&order_by=recent"
        )
        candidates: list[FeedCandidate] = []
        async with self._new_page_cm() as page:
            try:
                response = await page.goto(api_url, timeout=30000)
                if response and response.status == 200:
                    json_data = await response.json()
                    items = json_data.get("data", {}).get("items", [])
                    for item in items[:limit]:
                        post_id = item.get("id")
                        if not post_id:
                            continue
                        url = f"{self.BASE_URL}/community/posts/{post_id}"
                        title = (item.get("title") or item.get("content", ""))[:120].strip()
                        likes = int(item.get("like_count", 0) or 0)
                        comments = int(item.get("comment_count", 0) or 0)
                        views = int(item.get("view_count", 0) or 0)
                        c = FeedCandidate(
                            url=url,
                            title=title,
                            likes=likes,
                            comments=comments,
                            views=views,
                            source=self.SOURCE_NAME,
                        )
                        c.compute_engagement()
                        candidates.append(c)
                else:
                    logger.warning("JobPlanet API returned status %s", response.status if response else "N/A")
            except Exception as e:
                logger.warning("JobPlanet feed candidates failed: %s", e)
        candidates.sort(key=lambda c: c.engagement_score, reverse=True)
        return candidates[:limit]

    # ── Category classification ──────────────────────────────────────
    def _determine_category(self, title, content):
        text = (title + " " + content).lower()
        if any(kw in text for kw in ["이직", "취업", "면접", "커리어", "채용", "연봉 협상"]):
            return "career"
        elif any(kw in text for kw in ["회사", "직장", "팀장", "문화", "야근", "워라밸"]):
            return "work-life"
        elif any(kw in text for kw in ["연봉", "월급", "급여", "연봉 인상", "스톡옵션"]):
            return "money"
        elif any(kw in text for kw in ["스타트업", "대기업", "중소기업", "상장"]):
            return "company"
        return "general"

    # ── Post scraping ────────────────────────────────────────────────
    def _extract_post_id(self, url):
        match = re.search(r"/posts/(\d+)", url)
        if not match:
            raise _JobplanetScrapeFailure(
                f"Could not extract post ID from URL: {url}",
                reason="invalid_url_format",
            )
        return match.group(1)

    async def _fetch_post_detail(self, page, post_id):
        api_url = f"{self.BASE_URL}/api/v5/community/posts/{post_id}"
        logger.info(f"Fetching post detail from API: {api_url}")
        response = await page.goto(api_url, timeout=30000)
        if not response or response.status in [403, 404]:
            status = response.status if response else "unknown"
            raise _JobplanetScrapeFailure(
                f"API fetch failed with status {status}",
                reason=f"http_{status}",
            )
        json_data = await response.json()
        return json_data.get("data", {})

    def _resolve_post_title(self, post_data):
        title = post_data.get("title", "").strip()
        content = post_data.get("content", "").strip()
        if title:
            return title

        lines = [line.strip() for line in content.split("\n") if line.strip()]
        title = lines[0] if lines else "제목 없음"
        if len(title) > 50:
            title = title[:47] + "..."
        return title

    def _extract_post_payload(self, post_data):
        content = post_data.get("content", "").strip()
        title = self._resolve_post_title(post_data)
        if len(content) < 10:
            raise _JobplanetScrapeFailure(
                "Insufficient text content (minimum 10 chars).",
                reason="insufficient_content_length",
                stage="parse",
            )

        cat_info = post_data.get("community_category")
        category = cat_info.get("name", "기타") if isinstance(cat_info, dict) else "기타"
        return {
            "title": title,
            "content": content,
            "category": category,
            "likes": post_data.get("likes_count", 0),
            "comments": post_data.get("comments_count", 0),
        }

    async def _save_post_screenshot(self, page, url, title):
        logger.info(f"Navigating to HTML page for screenshot: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)  # Wait for SPA to render

        await self._clean_ui_for_screenshot(page)

        short_id = uuid.uuid4().hex[:8]
        safe_title = "".join(x for x in title[:20] if x.isalnum() or x in " -_").strip()
        if not safe_title:
            safe_title = "post"
        filename = f"jobplanet_{safe_title}_{short_id}.png"
        filepath = os.path.join(self.screenshot_dir, filename)

        body = await page.query_selector("body")
        if body:
            await asyncio.wait_for(body.screenshot(path=filepath), timeout=30)
        else:
            await asyncio.wait_for(page.screenshot(path=filepath, full_page=True), timeout=30)

        logger.info(f"Saved screenshot: {filepath}")
        return filepath

    def _build_success_result(self, url, payload, screenshot_path):
        return {
            "url": url,
            "title": payload["title"].strip(),
            "content": payload["content"],
            "category": payload["category"],
            "likes": payload["likes"],
            "comments": payload["comments"],
            "screenshot_path": screenshot_path,
            "source": self.SOURCE_NAME,
        }

    def _build_error_result(self, url, exc, failure_stage, failure_reason):
        error_code = ERROR_SCRAPE_PARSE_FAILED if failure_stage == "parse" else ERROR_SCRAPE_FAILED
        return {
            "_scrape_error": True,
            "url": url,
            "error_code": error_code,
            "failure_stage": failure_stage,
            "failure_reason": failure_reason,
            "error_message": str(exc),
        }

    async def scrape_post(self, url):
        logger.info(f"Scraping Jobplanet post (API + Screenshot): {url}")
        failure_stage = "post_fetch"
        failure_reason = "unknown"

        async with self._new_page_cm() as page:
            try:
                delay = self.config.get("delay_seconds", 5)
                if delay > 0:
                    await asyncio.sleep(delay)

                post_id = self._extract_post_id(url)
                post_data = await self._fetch_post_detail(page, post_id)
                payload = self._extract_post_payload(post_data)

                failure_stage = "screenshot"
                failure_reason = "screenshot_capture_failed"
                filepath = await self._save_post_screenshot(page, url, payload["title"])
                return self._build_success_result(url, payload, filepath)

            except _JobplanetScrapeFailure as e:
                failure_stage = e.stage
                failure_reason = e.reason
                logger.error(f"Error scraping {url}: {e}")
                await self._save_failure_snapshot(page, url, failure_stage, failure_reason)
                return self._build_error_result(url, e, failure_stage, failure_reason)
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                await self._save_failure_snapshot(page, url, failure_stage, failure_reason)
                return self._build_error_result(url, e, failure_stage, failure_reason)
