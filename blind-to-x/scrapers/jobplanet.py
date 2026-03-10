"""Jobplanet (jobplanet.co.kr) community scraper implementation."""

import asyncio
import logging
import os
import re
import uuid

try:
    from patchright.async_api import TimeoutError as PlaywrightTimeoutError
except ImportError:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config import ERROR_SCRAPE_FAILED, ERROR_SCRAPE_PARSE_FAILED
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


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
        page = await self._new_page()

        try:
            logger.info(f"Fetching {label} from API: {feed_url}...")
            response = await page.goto(feed_url, timeout=30000)
            if response and response.status == 200:
                json_data = await response.json()
                
                items = json_data.get('data', {}).get('items', [])
                for item in items[:limit]:
                    post_id = item.get('id')
                    if post_id:
                        urls.append(f"{self.BASE_URL}/community/posts/{post_id}")
                
                logger.info(f"Found {len(urls)} {label} from JSON API.")
            elif response and response.status in [403, 404]:
                logger.warning(f"API fetch returned status {response.status} for {label}")
                self.last_feed_fetch_error = f"API fetch blocked ({label}): Status {response.status}"
                self.last_feed_fetch_reason = "api_fetch_blocked"
            else:
                self.last_feed_fetch_error = f"API fetch failed ({label}): Status {response.status if response else 'Unknown'}"
                self.last_feed_fetch_reason = "api_fetch_failed"
                logger.error(self.last_feed_fetch_error)
        except Exception as e:
            self.last_feed_fetch_error = f"Feed fetch failed ({label}): {e}"
            self.last_feed_fetch_reason = "feed_fetch_failed"
            logger.error(self.last_feed_fetch_error)
        finally:
            await page.close()

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
    async def scrape_post(self, url):
        logger.info(f"Scraping Jobplanet post (API + Screenshot): {url}")
        page = await self._new_page()
        failure_stage = "post_fetch"
        failure_reason = "unknown"

        try:
            delay = self.config.get("delay_seconds", 5)
            if delay > 0:
                await asyncio.sleep(delay)

            # 1. Fetch data from JSON API
            match = re.search(r"/posts/(\d+)", url)
            if not match:
                failure_reason = "invalid_url_format"
                raise ValueError(f"Could not extract post ID from URL: {url}")
            
            post_id = match.group(1)
            api_url = f"{self.BASE_URL}/api/v5/community/posts/{post_id}"
            
            logger.info(f"Fetching post detail from API: {api_url}")
            response = await page.goto(api_url, timeout=30000)
            
            if not response or response.status in [403, 404]:
                failure_reason = f"http_{response.status if response else 'unknown'}"
                raise Exception(f"API fetch failed with status {response.status if response else 'unknown'}")
                
            json_data = await response.json()
            post_data = json_data.get("data", {})
            
            content = post_data.get("content", "").strip()
            title = post_data.get("title", "").strip()
            
            if not title:
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                title = lines[0] if lines else "제목 없음"
                if len(title) > 50:
                    title = title[:47] + "..."
                    
            if title == "제목 없음" and not content:
                failure_reason = "title_and_content_missing"
                raise Exception(f"Could not parse title/content on {url}")

            likes = post_data.get("likes_count", 0)
            comments = post_data.get("comments_count", 0)
            views = post_data.get("views_count", 0)
            
            cat_info = post_data.get("community_category")
            category = cat_info.get("name", "기타") if isinstance(cat_info, dict) else "기타"
            
            failure_stage = "screenshot"
            # 2. Navigate to actual URL just to take a screenshot
            logger.info(f"Navigating to HTML page for screenshot: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3) # Wait for SPA to render
            
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

            return {
                "url": url,
                "title": title.strip(),
                "content": content,
                "category": category,
                "likes": likes,
                "comments": comments,
                "screenshot_path": filepath,
                "source": self.SOURCE_NAME,
            }

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            await self._save_failure_snapshot(page, url, failure_stage, failure_reason)
            error_code = ERROR_SCRAPE_PARSE_FAILED if failure_stage == "parse" else ERROR_SCRAPE_FAILED
            return {
                "_scrape_error": True,
                "url": url,
                "error_code": error_code,
                "failure_stage": failure_stage,
                "failure_reason": failure_reason,
                "error_message": str(e),
            }
        finally:
            await page.close()
