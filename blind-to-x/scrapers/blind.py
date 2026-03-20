"""Blind (teamblind.com) scraper implementation."""

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
from scrapers.base import BaseScraper, FeedCandidate

logger = logging.getLogger(__name__)


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
    async def _fetch_post_urls(self, feed_url, label="posts", limit=5):
        """Generic helper: fetch post URLs from any Blind list page."""
        urls = []
        self.last_feed_fetch_error = None
        self.last_feed_fetch_reason = None
        page = await self._new_page()

        async def _collect_urls():
            # .tit h3 a: 제목 링크만 선택 (.tit 안에는 h3>a(제목)와 p.pre-txt>a(미리보기)가
            # 같은 href를 가지므로, h3>a 만 잡아 중복 수집을 방지)
            selector = ".article-list .tit h3 a"
            await page.wait_for_selector(selector, timeout=self.selector_timeout_ms)
            elements = await page.query_selector_all(selector)
            collected = []
            for i in range(min(limit, len(elements))):
                href = await elements[i].get_attribute("href")
                normalized = self._normalize_url(href)
                if normalized:
                    collected.append(normalized)
            return collected

        try:
            await self._login(page)

            logger.info(f"Fetching {label} via curl_cffi...")
            html_content = await self._fetch_html_via_session(feed_url)

            async def intercept(route):
                await route.fulfill(body=html_content, content_type="text/html")

            try:
                await page.route(feed_url, intercept)
                await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                urls = await _collect_urls()
                logger.info(f"Found {len(urls)} {label} (intercept mode).")
            except Exception as intercept_err:
                logger.warning(f"Intercept feed fetch failed for {label}: {intercept_err}. Trying direct navigation.")
                try:
                    await page.unroute(feed_url)
                except Exception:
                    pass
                try:
                    await page.goto(feed_url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(2)
                    urls = await _collect_urls()
                    logger.info(f"Found {len(urls)} {label} (direct fallback).")
                except Exception as direct_err:
                    self.last_feed_fetch_error = f"Feed fetch failed ({label}): {direct_err}"
                    self.last_feed_fetch_reason = "feed_fetch_failed_after_fallback"
                    logger.error(self.last_feed_fetch_error)
                    return []
        except Exception as e:
            self.last_feed_fetch_error = f"Feed fetch failed ({label}): {e}"
            self.last_feed_fetch_reason = "feed_fetch_failed"
            logger.error(self.last_feed_fetch_error)
        finally:
            await page.close()

        return urls

    async def get_trending_urls(self, limit=5):
        return await self._fetch_post_urls(
            "https://www.teamblind.com/kr/topics/trending",
            label="trending topics",
            limit=limit,
        )

    async def get_popular_urls(self, limit=5):
        return await self._fetch_post_urls(
            "https://www.teamblind.com/kr/topics/%ED%86%A0%ED%94%BD-%EB%B2%A0%EC%8A%A4%ED%8A%B8",
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
        feed_url = (
            "https://www.teamblind.com/kr/topics/%ED%86%A0%ED%94%BD-%EB%B2%A0%EC%8A%A4%ED%8A%B8"
            if mode == "popular"
            else "https://www.teamblind.com/kr/topics/trending"
        )
        candidates = []
        page = await self._new_page()
        try:
            await self._login(page)
            html_content = await self._fetch_html_via_session(feed_url)

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
                await page.goto(feed_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

            # 각 게시글 행에서 제목 + 인기도 추출
            rows = await page.query_selector_all(".article-list li, .article-list > div")
            for row in rows[:limit * 3]:
                link = await row.query_selector(".tit h3 a")
                if not link:
                    link = await row.query_selector("a")
                if not link:
                    continue
                href = await link.get_attribute("href")
                url = self._normalize_url(href)
                if not url:
                    continue
                title = (await link.inner_text()).strip()

                # 좋아요/댓글 수 추출 (Blind 목록 구조)
                likes = 0
                comments = 0
                meta_text = ""
                for sel in [".meta", ".info", ".count", "[class*='like']", "[class*='comment']"]:
                    el = await row.query_selector(sel)
                    if el:
                        meta_text += " " + (await el.inner_text()).strip()
                likes = self._extract_count(meta_text, ["좋아요", "like", "👍"])
                comments = self._extract_count(meta_text, ["댓글", "comment", "💬"])

                candidate = FeedCandidate(
                    url=url, title=title, likes=likes,
                    comments=comments, source=self.SOURCE_NAME,
                )
                candidate.compute_engagement()
                if candidate.url not in {c.url for c in candidates}:
                    candidates.append(candidate)

            logger.info("Blind feed candidates: %d collected, sorting by engagement.", len(candidates))
        except Exception as e:
            logger.warning("Feed candidate extraction failed: %s. Falling back to URL-only.", e)
            urls = await self.get_feed_urls(mode=mode, limit=limit)
            return [FeedCandidate(url=u, source=self.SOURCE_NAME) for u in urls]
        finally:
            await page.close()

        candidates.sort(key=lambda c: c.engagement_score, reverse=True)
        return candidates[:limit]

    # ── Category classification ──────────────────────────────────────
    def _determine_category(self, title, content):
        text = (title + " " + content).lower()
        if any(kw in text for kw in ["연애", "결혼", "남친", "여친", "데이트", "relationship", "couple", "marriage"]):
            return "relationship"
        elif any(kw in text for kw in ["이직", "취업", "면접", "커리어", "채용", "career", "job", "interview"]):
            return "career"
        elif any(kw in text for kw in ["회사", "직장", "출근", "팀", "문화", "work", "office", "manager"]):
            return "work-life"
        elif any(kw in text for kw in ["부모", "가족", "남편", "아내", "family", "parents"]):
            return "family"
        elif any(kw in text for kw in ["주식", "코인", "부동산", "재테크", "투자", "finance", "investment"]):
            return "money"
        return "general"

    # ── Post scraping ────────────────────────────────────────────────
    async def scrape_post(self, url):
        logger.info(f"Scraping post: {url}")
        page = await self._new_page()
        failure_stage = "post_fetch"
        failure_reason = "unknown"
        try:
            delay = self.config.get("delay_seconds", 5)
            if delay > 0:
                await asyncio.sleep(delay)

            logger.info("Fetching HTML via curl_cffi to bypass bot detection...")
            try:
                html_content = await self._fetch_html_via_session(url)
            except Exception as fetch_err:
                err_str = str(fetch_err).lower()
                if "403" in err_str:
                    failure_reason = "http_403_forbidden"
                elif "404" in err_str:
                    failure_reason = "http_404_not_found"
                elif "timeout" in err_str:
                    failure_reason = "fetch_timeout"
                else:
                    failure_reason = "html_fetch_failed"
                raise

            async def intercept_post(route):
                await route.fulfill(body=html_content, content_type="text/html")

            await page.route(url, intercept_post)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            content_selectors = [
                ".contents",
                ".wrapped",
                "main",
                ".article-wrap",
                "article",
                ".post-content",
                "#__next",
                "body",
            ]
            main_container = None
            for selector in content_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=self.selector_timeout_ms)
                    main_container = await page.query_selector(selector)
                    if main_container:
                        logger.info(f"Found content container with selector: {selector}")
                        break
                except PlaywrightTimeoutError:
                    continue

            # Fallback: direct navigation if intercept mode fails
            if not main_container:
                logger.warning(f"Intercept mode failed for {url}. Retrying with direct navigation...")
                failure_reason = "intercept_selector_not_found"
                try:
                    await page.unroute(url)
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(3)
                    for selector in [".contents", ".wrapped", "main", "article"]:
                        try:
                            await page.wait_for_selector(selector, timeout=self.direct_fallback_timeout_ms)
                            main_container = await page.query_selector(selector)
                            if main_container:
                                logger.info(f"Direct navigation succeeded with selector: {selector}")
                                break
                        except PlaywrightTimeoutError:
                            continue
                except Exception as fallback_err:
                    failure_reason = "direct_navigation_failed"
                    logger.error(f"Fallback direct navigation also failed: {fallback_err}")

            if not main_container:
                # Crawl4AI LLM fallback: extract using LLM when all selectors fail
                crawl4ai_result = await self._extract_with_crawl4ai(url, html_content)
                if crawl4ai_result and crawl4ai_result.get("content"):
                    logger.info("Crawl4AI fallback succeeded for %s", url)
                    # Take screenshot from page before returning
                    short_id = uuid.uuid4().hex[:8]
                    safe_t = "".join(x for x in crawl4ai_result.get("title", "post")[:20] if x.isalnum() or x in " -_").strip() or "post"
                    filepath = os.path.join(self.screenshot_dir, f"blind_{safe_t}_{short_id}.png")
                    await self._take_screenshot(page, filepath)
                    crawl4ai_result["screenshot_path"] = filepath
                    crawl4ai_result["category"] = self._determine_category(
                        crawl4ai_result.get("title", ""), crawl4ai_result.get("content", "")
                    )
                    return crawl4ai_result

                failure_stage = "parse"
                failure_reason = "main_container_not_found"
                raise Exception(f"Could not find main content container on {url}")

            failure_stage = "parse"

            # Extract title
            title = ""
            title_selectors = [".article-view-head h2", "h2", "h1"]
            for selector in title_selectors:
                title_el = await main_container.query_selector(selector)
                if title_el:
                    text = (await title_el.inner_text()).strip()
                    if text:
                        title = text
                        break
            if not title:
                title = "제목 없음"

            # Extract content
            content = ""
            content_sel = [".article-view-text", ".contents-txt", ".article-view", "p"]
            for selector in content_sel:
                content_el = await main_container.query_selector(selector)
                if content_el:
                    text = (await content_el.inner_text()).strip()
                    if text:
                        content = text
                        break
            # trafilatura 폴백: 셀렉터 추출 실패 시 HTML에서 클린 텍스트 추출
            if not content:
                try:
                    raw_html = await page.content()
                    content = self._extract_clean_text(raw_html)
                    if content:
                        logger.info("Content extracted via trafilatura fallback")
                except Exception:
                    pass

            if title == "제목 없음" and not content:
                failure_reason = "title_and_content_missing"
                raise Exception(f"Could not parse title/content on {url}")

            # Extract likes/comments from .wrap-info elements
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

            category = self._determine_category(title, content)
            logger.info(f"Extracted metadata: Title '{title[:20]}...', Likes {likes}, Comments {comments}")

            await self._clean_ui_for_screenshot(page)

            short_id = uuid.uuid4().hex[:8]
            safe_title = "".join(x for x in title[:20] if x.isalnum() or x in " -_").strip()
            if not safe_title:
                safe_title = "post"
            filename = f"blind_{safe_title}_{short_id}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            await asyncio.sleep(0.5)
            try:
                await asyncio.wait_for(
                    main_container.screenshot(path=filepath),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                failure_reason = "screenshot_timeout"
                logger.error(f"Screenshot timed out after 30s for {url}")
                raise
            logger.info(f"Saved screenshot: {filepath}")

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
            await page.close()
