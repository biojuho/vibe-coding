"""Blind (teamblind.com) scraper implementation."""

import asyncio
import html
import logging
import os
import re
import uuid

try:
    from patchright.async_api import TimeoutError as PlaywrightTimeoutError
except ImportError:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config import ERROR_SCRAPE_FAILED, ERROR_SCRAPE_PARSE_FAILED
from scrapers.base import BaseScraper, BrowserUnavailableError, FeedCandidate

logger = logging.getLogger(__name__)

_TRENDING_FEED_URL = "https://www.teamblind.com/kr/topics/trending"
_POPULAR_FEED_URL = "https://www.teamblind.com/kr/topics/%ED%86%A0%ED%94%BD-%EB%B2%A0%EC%8A%A4%ED%8A%B8"
_FEED_META_SELECTORS = (".meta", ".info", ".count", "[class*='like']", "[class*='comment']")
_POST_CONTAINER_SELECTORS = (
    ".contents",
    ".wrapped",
    "main",
    ".article-wrap",
    "article",
    ".post-content",
    "#__next",
    "body",
)
_DIRECT_POST_CONTAINER_SELECTORS = (".contents", ".wrapped", "main", "article")
_POST_TITLE_SELECTORS = (".article-view-head h2", "h2", "h1")
_POST_CONTENT_SELECTORS = (".article-view-text", ".contents-txt", ".article-view", "p")
_CATEGORY_KEYWORDS = (
    ("relationship", ("연애", "결혼", "남친", "여친", "데이트", "relationship", "couple", "marriage")),
    ("career", ("이직", "취업", "면접", "커리어", "채용", "career", "job", "interview")),
    ("work-life", ("회사", "직장", "출근", "팀", "문화", "work", "office", "manager")),
    ("family", ("부모", "가족", "남편", "아내", "family", "parents")),
    ("money", ("주식", "코인", "부동산", "재테크", "투자", "finance", "investment")),
)


class BlindScraper(BaseScraper):
    """Scraper for teamblind.com (Korean workplace community)."""

    SOURCE_NAME = "blind"

    def __init__(self, config):
        super().__init__(config)
        self.email = config.get("blind.email")
        self.password = config.get("blind.password")

    # ── URL helpers ──────────────────────────────────────────────────
    @staticmethod
    def _normalize_url(href):
        if not href:
            return None
        if href.startswith("/"):
            return f"https://www.teamblind.com{href}"
        if "teamblind.com" in href:
            return href
        return None  # 광고/제휴 링크 등 비-Blind URL 필터링

    @staticmethod
    def _extract_count(meta_text, keywords):
        if not meta_text:
            return 0
        for keyword in keywords:
            pattern = rf"{re.escape(keyword)}\s*([0-9,]+)"
            match = re.search(pattern, meta_text, flags=re.IGNORECASE)
            if match:
                return int(match.group(1).replace(",", ""))
        return 0

    @staticmethod
    def _strip_html_tags(fragment: str) -> str:
        text = re.sub(r"<[^>]+>", " ", fragment or "")
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _extract_feed_candidates_from_html(self, html_content: str, limit: int = 5) -> list[FeedCandidate]:
        candidates: list[FeedCandidate] = []
        seen: set[str] = set()
        pattern = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', flags=re.IGNORECASE | re.DOTALL)
        for href, label_html in pattern.findall(html_content or ""):
            normalized = self._normalize_url(html.unescape(href))
            if not normalized or normalized in seen:
                continue
            if "/post/" not in normalized and "/topic/" not in normalized:
                continue
            label = self._strip_html_tags(label_html)
            if not label or len(label) < 2:
                continue
            seen.add(normalized)
            candidates.append(
                FeedCandidate(
                    url=normalized,
                    title=label,
                    source=self.SOURCE_NAME,
                )
            )
            if len(candidates) >= limit:
                break
        return candidates

    def _extract_urls_from_feed_html(self, html_content: str, limit: int = 5) -> list[str]:
        return [candidate.url for candidate in self._extract_feed_candidates_from_html(html_content, limit=limit)]

    @staticmethod
    def _extract_title_from_html(html_content: str) -> str:
        patterns = (
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
            r"<title[^>]*>(.*?)</title>",
            r"<h1[^>]*>(.*?)</h1>",
            r"<h2[^>]*>(.*?)</h2>",
        )
        for pattern in patterns:
            match = re.search(pattern, html_content or "", flags=re.IGNORECASE | re.DOTALL)
            if match:
                title = BlindScraper._strip_html_tags(match.group(1))
                if title:
                    return title
        return "제목 없음"

    @staticmethod
    def _feed_url_for_mode(mode: str) -> str:
        return _POPULAR_FEED_URL if mode == "popular" else _TRENDING_FEED_URL

    async def _feed_row_meta_text(self, row) -> str:
        text_parts: list[str] = []
        for selector in _FEED_META_SELECTORS:
            element = await row.query_selector(selector)
            if element:
                text = (await element.inner_text()).strip()
                if text:
                    text_parts.append(text)
        return " ".join(text_parts)

    async def _feed_candidate_from_row(self, row) -> FeedCandidate | None:
        link = await row.query_selector(".tit h3 a")
        if not link:
            link = await row.query_selector("a")
        if not link:
            return None

        href = await link.get_attribute("href")
        url = self._normalize_url(href)
        if not url:
            return None

        title = (await link.inner_text()).strip()
        meta_text = await self._feed_row_meta_text(row)
        candidate = FeedCandidate(
            url=url,
            title=title,
            likes=self._extract_count(meta_text, ["좋아요", "like", "👍"]),
            comments=self._extract_count(meta_text, ["댓글", "comment", "💬"]),
            source=self.SOURCE_NAME,
        )
        candidate.compute_engagement()
        return candidate

    async def _collect_feed_candidates_from_page(self, page, limit: int) -> list[FeedCandidate]:
        candidates: list[FeedCandidate] = []
        seen: set[str] = set()
        rows = await page.query_selector_all(".article-list li, .article-list > div")
        for row in rows[: limit * 3]:
            candidate = await self._feed_candidate_from_row(row)
            if not candidate or candidate.url in seen:
                continue
            candidates.append(candidate)
            seen.add(candidate.url)

        candidates.sort(key=lambda c: c.engagement_score, reverse=True)
        return candidates[:limit]

    @staticmethod
    async def _first_text_from_selectors(root, selectors: tuple[str, ...]) -> str:
        for selector in selectors:
            element = await root.query_selector(selector)
            if element:
                text = (await element.inner_text()).strip()
                if text:
                    return text
        return ""

    async def _extract_post_content_text(self, page, main_container) -> str:
        content = await self._first_text_from_selectors(
            main_container,
            _POST_CONTENT_SELECTORS,
        )
        if content:
            return content

        try:
            raw_html = await page.content()
            content = self._extract_clean_text(raw_html)
            if content:
                logger.info("Content extracted via trafilatura fallback")
        except Exception:
            return ""
        return content

    async def _extract_post_counts(self, page) -> tuple[int, int]:
        likes = 0
        comments = 0
        like_el = await page.query_selector(".wrap-info .like")
        if like_el:
            like_text = (await like_el.inner_text()).strip()
            likes = int(re.sub(r"[^0-9]", "", like_text)) if re.search(r"\d", like_text) else 0
        cmt_el = await page.query_selector(".wrap-info .cmt")
        if cmt_el:
            cmt_text = (await cmt_el.inner_text()).strip()
            comments = int(re.sub(r"[^0-9]", "", cmt_text)) if re.search(r"\d", cmt_text) else 0
        return likes, comments

    @staticmethod
    def _post_fetch_failure_reason(fetch_err: Exception) -> str:
        err_str = str(fetch_err).lower()
        if "403" in err_str:
            return "http_403_forbidden"
        if "404" in err_str:
            return "http_404_not_found"
        if "timeout" in err_str:
            return "fetch_timeout"
        return "html_fetch_failed"

    async def _fetch_post_html_content(self, url: str) -> tuple[str | None, str]:
        logger.info("Fetching HTML via curl_cffi to bypass bot detection...")
        try:
            return await self._fetch_html_via_session(url), "unknown"
        except Exception as fetch_err:
            reason = self._post_fetch_failure_reason(fetch_err)
            logger.warning(
                "HTML session fetch failed for %s: %s. Trying direct browser navigation.",
                url,
                fetch_err,
            )
            return None, reason

    async def _navigate_post_page(self, page, url: str, html_content: str | None) -> None:
        if not html_content:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            return

        async def intercept_post(route):
            await route.fulfill(body=html_content, content_type="text/html")

        try:
            await page.route(url, intercept_post)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
        except Exception as intercept_err:
            logger.warning(
                "Intercept post fetch failed for %s: %s. Trying direct navigation.",
                url,
                intercept_err,
            )
            try:
                await page.unroute(url)
            except Exception:
                pass
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
        finally:
            try:
                await page.unroute(url)
            except Exception:
                pass

    async def _find_post_container(self, page, selectors: tuple[str, ...], timeout_ms: int):
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout_ms)
                main_container = await page.query_selector(selector)
                if main_container:
                    logger.info(f"Found content container with selector: {selector}")
                    return main_container
            except PlaywrightTimeoutError:
                continue
        return None

    async def _find_post_container_after_direct_navigation(self, page, url: str):
        logger.warning(f"Intercept mode failed for {url}. Retrying with direct navigation...")
        try:
            await page.unroute(url)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            container = await self._find_post_container(
                page,
                _DIRECT_POST_CONTAINER_SELECTORS,
                self.direct_fallback_timeout_ms,
            )
            return container, "intercept_selector_not_found"
        except Exception as fallback_err:
            logger.error(f"Fallback direct navigation also failed: {fallback_err}")
            return None, "direct_navigation_failed"

    async def _extract_post_with_crawl4ai(self, url: str, html_content: str | None, page):
        crawl4ai_result = await self._extract_with_crawl4ai(url, html_content)
        if not crawl4ai_result or not crawl4ai_result.get("content"):
            return None

        logger.info("Crawl4AI fallback succeeded for %s", url)
        short_id = uuid.uuid4().hex[:8]
        safe_t = (
            "".join(x for x in crawl4ai_result.get("title", "post")[:20] if x.isalnum() or x in " -_").strip() or "post"
        )
        filepath = os.path.join(self.screenshot_dir, f"blind_{safe_t}_{short_id}.png")
        await self._take_screenshot(page, filepath)
        crawl4ai_result["screenshot_path"] = filepath
        crawl4ai_result["category"] = self._determine_category(
            crawl4ai_result.get("title", ""),
            crawl4ai_result.get("content", ""),
        )
        return crawl4ai_result

    async def _save_post_screenshot(self, page, main_container, title: str) -> str:
        await self._clean_ui_for_screenshot(page)

        short_id = uuid.uuid4().hex[:8]
        safe_title = "".join(x for x in title[:20] if x.isalnum() or x in " -_").strip()
        filename = f"blind_{safe_title or 'post'}_{short_id}.png"
        filepath = os.path.join(self.screenshot_dir, filename)

        await asyncio.sleep(0.5)
        try:
            await asyncio.wait_for(main_container.screenshot(path=filepath), timeout=30)
        except asyncio.TimeoutError:
            logger.error("Screenshot timed out after 30s")
            raise
        logger.info(f"Saved screenshot: {filepath}")
        return filepath

    async def _scrape_post_without_browser(self, url: str, html_content: str):
        crawl4ai_result = await self._extract_with_crawl4ai(url, html_content)
        if crawl4ai_result and crawl4ai_result.get("content"):
            crawl4ai_result.setdefault("screenshot_path", None)
            crawl4ai_result.setdefault("likes", 0)
            crawl4ai_result.setdefault("comments", 0)
            crawl4ai_result.setdefault("source", self.SOURCE_NAME)
            crawl4ai_result.setdefault(
                "category",
                self._determine_category(crawl4ai_result.get("title", ""), crawl4ai_result.get("content", "")),
            )
            return crawl4ai_result

        title = self._extract_title_from_html(html_content)
        content = self._extract_clean_text(html_content)
        if not content:
            content = self._strip_html_tags(html_content)
        if len(content.strip()) < 10:
            return {
                "_scrape_error": True,
                "url": url,
                "error_code": ERROR_SCRAPE_PARSE_FAILED,
                "failure_stage": "parse",
                "failure_reason": "browser_unavailable_html_parse_failed",
                "error_message": "Browser unavailable and HTML-only extraction returned insufficient content.",
            }

        return {
            "url": url,
            "title": title.strip(),
            "content": content.strip(),
            "category": self._determine_category(title, content),
            "likes": 0,
            "comments": 0,
            "screenshot_path": None,
            "source": self.SOURCE_NAME,
            "extraction_method": "html_only_fallback",
        }

    # ── Login ────────────────────────────────────────────────────────
    async def _login(self, page):
        if not self.email or not self.password:
            logger.info("Skip login (no credentials provided)")
            return True

        try:
            logger.info("Proceeding with login...")
            await page.goto("https://www.teamblind.com/kr/login")
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            await page.fill('input[type="email"]', self.email)
            await page.fill('input[type="password"]', self.password)

            try:
                await page.click('button[type="submit"]')
            except PlaywrightTimeoutError:
                await page.click('text="로그인"')

            await page.wait_for_selector("header", timeout=10000)
            logger.info("Login successful.")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    # ── Feed URL fetching ────────────────────────────────────────────
    async def _collect_feed_urls_from_page(self, page, limit: int) -> list[str]:
        selector = ".article-list .tit h3 a"
        await page.wait_for_selector(selector, timeout=self.selector_timeout_ms)
        elements = await page.query_selector_all(selector)
        collected = []
        for element in elements[:limit]:
            href = await element.get_attribute("href")
            normalized = self._normalize_url(href)
            if normalized:
                collected.append(normalized)
        return collected

    async def _fetch_feed_urls_html_only(self, feed_url: str, label: str, limit: int) -> list[str]:
        html_content = await self._fetch_html_via_session(feed_url)
        urls = self._extract_urls_from_feed_html(html_content, limit=limit)
        if urls:
            logger.info(f"Found {len(urls)} {label} (HTML-only fallback).")
            return urls
        self.last_feed_fetch_error = f"Feed fetch failed ({label}): browser unavailable and HTML parse yielded no URLs"
        self.last_feed_fetch_reason = "browser_unavailable_no_feed_urls"
        logger.error(self.last_feed_fetch_error)
        return []

    async def _fetch_feed_html_content(self, feed_url: str, label: str) -> str | None:
        try:
            logger.info(f"Fetching {label} via curl_cffi...")
            return await self._fetch_html_via_session(feed_url)
        except Exception as fetch_err:
            logger.warning(
                "Feed HTML fetch failed for %s: %s. Trying direct browser navigation.",
                label,
                fetch_err,
            )
            return None

    async def _collect_feed_urls_with_intercept(
        self,
        page,
        feed_url: str,
        label: str,
        html_content: str,
        limit: int,
    ) -> list[str] | None:
        async def intercept(route):
            await route.fulfill(body=html_content, content_type="text/html")

        try:
            await page.route(feed_url, intercept)
            await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            urls = await self._collect_feed_urls_from_page(page, limit)
            logger.info(f"Found {len(urls)} {label} (intercept mode).")
            return urls
        except Exception as intercept_err:
            logger.warning(
                "Intercept feed fetch failed for %s: %s. Trying direct navigation.",
                label,
                intercept_err,
            )
            return None
        finally:
            try:
                await page.unroute(feed_url)
            except Exception:
                pass

    async def _collect_feed_urls_direct(self, page, feed_url: str, label: str, limit: int) -> list[str] | None:
        try:
            await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            urls = await self._collect_feed_urls_from_page(page, limit)
            logger.info(f"Found {len(urls)} {label} (direct fallback).")
            return urls
        except Exception as direct_err:
            self.last_feed_fetch_error = f"Feed fetch failed ({label}): {direct_err}"
            self.last_feed_fetch_reason = "feed_fetch_failed_after_fallback"
            logger.error(self.last_feed_fetch_error)
            return None

    async def _fetch_post_urls(self, feed_url, label="posts", limit=5):
        """Generic helper: fetch post URLs from any Blind list page."""
        urls = []
        self.last_feed_fetch_error = None
        self.last_feed_fetch_reason = None
        page = None

        try:
            try:
                page = await self._new_page()
            except BrowserUnavailableError as exc:
                logger.warning(
                    "Browser unavailable for %s; using HTML-only feed fallback: %s",
                    label,
                    exc,
                )
                return await self._fetch_feed_urls_html_only(feed_url, label, limit)

            await self._login(page)

            html_content = await self._fetch_feed_html_content(feed_url, label)

            if html_content:
                urls = await self._collect_feed_urls_with_intercept(page, feed_url, label, html_content, limit)
                if urls is not None:
                    return urls

            urls = await self._collect_feed_urls_direct(page, feed_url, label, limit)
            if urls is None:
                return []
        except Exception as e:
            self.last_feed_fetch_error = f"Feed fetch failed ({label}): {e}"
            self.last_feed_fetch_reason = "feed_fetch_failed"
            logger.error(self.last_feed_fetch_error)
        finally:
            if page is not None:
                await page.close()

        return urls

    async def get_trending_urls(self, limit=5):
        return await self._fetch_post_urls(
            _TRENDING_FEED_URL,
            label="trending topics",
            limit=limit,
        )

    async def get_popular_urls(self, limit=5):
        return await self._fetch_post_urls(
            _POPULAR_FEED_URL,
            label="popular topics (토픽 베스트)",
            limit=limit,
        )

    async def get_feed_urls(self, mode="trending", limit=5):
        """Unified feed URL getter. mode: 'trending' or 'popular'."""
        if mode == "popular":
            return await self.get_popular_urls(limit=limit)
        return await self.get_trending_urls(limit=limit)

    async def get_feed_candidates(self, mode="trending", limit=5):
        """피드 목록에서 제목 + 좋아요/댓글 수를 사전 추출하여 인기순 정렬."""
        feed_url = self._feed_url_for_mode(mode)
        candidates = []
        page = None
        try:
            try:
                page = await self._new_page()
            except BrowserUnavailableError as exc:
                logger.warning(
                    "Browser unavailable for feed candidates (%s); using HTML-only fallback: %s",
                    mode,
                    exc,
                )
                html_content = await self._fetch_html_via_session(feed_url)
                candidates = self._extract_feed_candidates_from_html(html_content, limit=limit)
                if candidates:
                    logger.info("Blind feed candidates: %d collected (HTML-only fallback).", len(candidates))
                    return candidates
                urls = self._extract_urls_from_feed_html(html_content, limit=limit)
                return [FeedCandidate(url=u, source=self.SOURCE_NAME) for u in urls]

            await self._login(page)
            html_content = None
            try:
                html_content = await self._fetch_html_via_session(feed_url)
            except Exception as fetch_err:
                logger.warning(
                    "Feed candidate HTML fetch failed for %s: %s. Trying direct browser navigation.",
                    mode,
                    fetch_err,
                )

            if html_content:

                async def intercept(route):
                    await route.fulfill(body=html_content, content_type="text/html")

                try:
                    await page.route(feed_url, intercept)
                    await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                except Exception as nav_err:
                    logger.warning("Feed candidate nav failed: %s. Trying direct.", nav_err)
                    try:
                        await page.unroute(feed_url)
                    except Exception:
                        pass
                    await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                finally:
                    try:
                        await page.unroute(feed_url)
                    except Exception:
                        pass
            else:
                await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)

            candidates = await self._collect_feed_candidates_from_page(page, limit=limit)
            logger.info("Blind feed candidates: %d collected, sorting by engagement.", len(candidates))
        except Exception as e:
            logger.warning("Feed candidate extraction failed: %s. Falling back to URL-only.", e)
            urls = await self.get_feed_urls(mode=mode, limit=limit)
            return [FeedCandidate(url=u, source=self.SOURCE_NAME) for u in urls]
        finally:
            if page is not None:
                await page.close()

        return candidates

    # ── Category classification ──────────────────────────────────────
    def _determine_category(self, title, content):
        text = (title + " " + content).lower()
        for category, keywords in _CATEGORY_KEYWORDS:
            if any(keyword in text for keyword in keywords):
                return category
        return "general"

    # ── Post scraping ────────────────────────────────────────────────
    async def scrape_post(self, url):
        logger.info(f"Scraping post: {url}")
        page = None
        failure_stage = "post_fetch"
        failure_reason = "unknown"
        try:
            try:
                page = await self._new_page()
            except BrowserUnavailableError as exc:
                logger.warning("Browser unavailable for %s; using HTML-only post fallback: %s", url, exc)
                html_content = await self._fetch_html_via_session(url)
                return await self._scrape_post_without_browser(url, html_content)

            delay = self.config.get("delay_seconds", 5)
            if delay > 0:
                await asyncio.sleep(delay)

            html_content, failure_reason = await self._fetch_post_html_content(url)
            await self._navigate_post_page(page, url, html_content)

            main_container = await self._find_post_container(page, _POST_CONTAINER_SELECTORS, self.selector_timeout_ms)

            # Fallback: direct navigation if intercept mode fails
            if not main_container:
                main_container, failure_reason = await self._find_post_container_after_direct_navigation(page, url)

            if not main_container:
                # Crawl4AI LLM fallback: extract using LLM when all selectors fail
                crawl4ai_result = await self._extract_post_with_crawl4ai(url, html_content, page)
                if crawl4ai_result:
                    return crawl4ai_result

                failure_stage = "parse"
                failure_reason = "main_container_not_found"
                raise Exception(f"Could not find main content container on {url}")

            failure_stage = "parse"

            # Extract title
            title = await self._first_text_from_selectors(main_container, _POST_TITLE_SELECTORS)
            title = title or "제목 없음"

            # Extract content
            content = await self._extract_post_content_text(page, main_container)

            if len(content) < 10:
                failure_reason = "insufficient_content_length"
                raise Exception("Insufficient text content (minimum 10 chars).")

            # Extract likes/comments from .wrap-info elements
            likes, comments = await self._extract_post_counts(page)

            category = self._determine_category(title, content)
            logger.info(f"Extracted metadata: Title '{title[:20]}...', Likes {likes}, Comments {comments}")

            try:
                filepath = await self._save_post_screenshot(page, main_container, title)
            except asyncio.TimeoutError:
                failure_reason = "screenshot_timeout"
                raise

            return {
                "url": url,
                "title": title.strip(),
                "content": content.strip(),
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
            if page is not None:
                await page.close()
