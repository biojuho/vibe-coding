"""FMKorea (fmkorea.com) best/humor post scraper implementation."""

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


class FMKoreaScraper(BaseScraper):
    """Scraper for fmkorea.com Korean community (best/humor boards)."""

    SOURCE_NAME = "fmkorea"

    BASE_URL = "https://www.fmkorea.com"

    # ── URL helpers ──────────────────────────────────────────────────
    def _normalize_url(self, href):
        if not href:
            return None
        # 상대 경로 → 절대 경로
        if href.startswith("/"):
            return f"{self.BASE_URL}{href}"
        if "fmkorea.com" in href:
            return href
        return None

    # ── Feed URL fetching ────────────────────────────────────────────
    async def _fetch_post_urls(self, feed_url, label="posts", limit=5):
        """FMKorea 베스트/유머 목록 페이지에서 게시글 URL을 수집합니다."""
        urls = []
        self.last_feed_fetch_error = None
        self.last_feed_fetch_reason = None
        page = await self._new_page()

        # FMKorea 목록 링크 셀렉터 (우선순위 순)
        link_selectors = [
            "li.li_best_img_zoom a.hotdeal_var8",  # 베스트 이미지형
            "li.li_best a.hotdeal_var8",
            "ul.list_best li h3.title a",
            "article.li_best h3 a",
            "li[class*='li_best'] h3 a",
            "h3.title a[href*='/best/']",
            "a[href*='/best/'][class*='title']",
            ".bd_lst_wrp a[href*='/best/']",
            "a[href*='/humor/']",
            "a[href*='/best/']",
        ]

        async def _collect_urls():
            collected = []
            for selector in link_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=self.selector_timeout_ms)
                    elements = await page.query_selector_all(selector)
                    for el in elements[:limit * 3]:
                        href = await el.get_attribute("href")
                        normalized = self._normalize_url(href)
                        if normalized and normalized not in collected:
                            # 실제 게시글 URL 패턴만 허용 (숫자 ID 포함)
                            if re.search(r"/\d+$", normalized) or re.search(r"[?&]document_srl=\d+", normalized):
                                collected.append(normalized)
                        if len(collected) >= limit:
                            break
                    if collected:
                        logger.info(f"Found {len(collected)} URLs with selector: {selector}")
                        return collected[:limit]
                except PlaywrightTimeoutError:
                    continue
            # 마지막 폴백: 페이지 내 모든 링크에서 숫자 ID 포함 게시글 URL 수집
            if not collected:
                try:
                    all_links = await page.query_selector_all("a[href]")
                    for el in all_links:
                        href = await el.get_attribute("href")
                        normalized = self._normalize_url(href)
                        if normalized and normalized not in collected:
                            if re.search(r"/\d{8,}$", normalized):
                                collected.append(normalized)
                        if len(collected) >= limit:
                            break
                except Exception:
                    pass
            return collected[:limit]

        try:
            logger.info(f"Fetching {label} from {feed_url}...")

            # 1차 시도: curl_cffi로 HTML 가져와 인터셉트 모드
            html_content = None
            try:
                html_content = await self._fetch_html_via_session(feed_url)
            except Exception as fetch_err:
                logger.warning(f"curl_cffi fetch failed for {label}: {fetch_err}. Falling back to direct navigation.")

            if html_content:
                async def intercept(route):
                    await route.fulfill(body=html_content, content_type="text/html")

                try:
                    await page.route(feed_url, intercept)
                    await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                    urls = await _collect_urls()
                    logger.info(f"Found {len(urls)} {label} (intercept mode).")
                    if urls:
                        return urls
                except Exception as intercept_err:
                    logger.warning(f"Intercept mode failed for {label}: {intercept_err}.")
                finally:
                    try:
                        await page.unroute(feed_url)
                    except Exception:
                        pass

            # 2차 시도: 직접 Playwright 네비게이션 (domcontentloaded — networkidle은 광고 때문에 타임아웃)
            logger.info(f"Trying direct navigation for {label}...")
            try:
                await page.goto(feed_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                urls = await _collect_urls()
                logger.info(f"Found {len(urls)} {label} (direct navigation).")
            except Exception as direct_err:
                self.last_feed_fetch_error = f"Feed fetch failed ({label}): {direct_err}"
                self.last_feed_fetch_reason = "feed_fetch_failed_after_fallback"
                logger.error(self.last_feed_fetch_error)
        except Exception as e:
            self.last_feed_fetch_error = f"Feed fetch failed ({label}): {e}"
            self.last_feed_fetch_reason = "feed_fetch_failed"
            logger.error(self.last_feed_fetch_error)
        finally:
            await page.close()

        return urls

    async def get_popular_urls(self, limit=5):
        """FMKorea 실시간 베스트 게시글 URL 수집."""
        return await self._fetch_post_urls(
            f"{self.BASE_URL}/best",
            label="popular posts (FMKorea 실시간 베스트)",
            limit=limit,
        )

    async def get_trending_urls(self, limit=5):
        """FMKorea 유머 게시판 최신 인기글 URL 수집."""
        return await self._fetch_post_urls(
            f"{self.BASE_URL}/humor",
            label="trending posts (FMKorea 유머)",
            limit=limit,
        )

    async def get_feed_urls(self, mode="popular", limit=5):
        """통합 피드 URL getter. mode: 'popular' 또는 'trending'."""
        if mode == "trending":
            return await self.get_trending_urls(limit=limit)
        return await self.get_popular_urls(limit=limit)

    # ── Category classification ──────────────────────────────────────
    def _determine_category(self, title, content):
        text = (title + " " + content).lower()
        if any(kw in text for kw in ["유머", "웃긴", "개그", "ㅋㅋ", "ㅎㅎ", "드립", "짤"]):
            return "humor"
        elif any(kw in text for kw in ["이직", "취업", "면접", "커리어", "채용", "연봉"]):
            return "career"
        elif any(kw in text for kw in ["연애", "결혼", "남친", "여친", "썸"]):
            return "relationship"
        elif any(kw in text for kw in ["게임", "롤", "배그", "오버워치", "스팀"]):
            return "gaming"
        elif any(kw in text for kw in ["정치", "뉴스", "사회", "이슈", "논란"]):
            return "news"
        return "general"

    # ── Post scraping ────────────────────────────────────────────────
    async def scrape_post(self, url):
        logger.info(f"Scraping FMKorea post: {url}")
        page = await self._new_page()
        failure_stage = "post_fetch"
        failure_reason = "unknown"

        try:
            delay = self.config.get("delay_seconds", 5)
            if delay > 0:
                await asyncio.sleep(delay)

            logger.info("Fetching HTML via curl_cffi...")
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

            # FMKorea 게시글 컨테이너 셀렉터 (우선순위 순)
            content_selectors = [
                ".rd_body",           # 게시글 본문 영역
                ".xe_content",        # XE CMS 게시글 내용
                "#bd_contents",       # 콘텐츠 래퍼
                ".document_read",     # 일부 게시판 클래스
                "article",
                "main",
                "#__xe_content",
                "body",
            ]
            main_container = None
            for selector in content_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=self.selector_timeout_ms)
                    main_container = await page.query_selector(selector)
                    if main_container:
                        logger.info(f"Found content container: {selector}")
                        break
                except PlaywrightTimeoutError:
                    continue

            if not main_container:
                logger.warning(f"Intercept mode failed for {url}. Trying direct navigation...")
                failure_reason = "intercept_selector_not_found"
                try:
                    await page.unroute(url)
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(3)
                    for selector in [".rd_body", ".xe_content", "main", "article", "body"]:
                        try:
                            await page.wait_for_selector(selector, timeout=self.direct_fallback_timeout_ms)
                            main_container = await page.query_selector(selector)
                            if main_container:
                                break
                        except PlaywrightTimeoutError:
                            continue
                except Exception as fallback_err:
                    failure_reason = "direct_navigation_failed"
                    logger.error(f"Fallback navigation failed: {fallback_err}")

            if not main_container:
                failure_stage = "parse"
                failure_reason = "main_container_not_found"
                raise Exception(f"Could not find content container on {url}")

            failure_stage = "parse"

            # 제목 추출
            title = ""
            title_selectors = [
                "h1.np_18px_span",
                ".rd_hd h1",
                ".np_18px",
                "h1[class*='title']",
                ".document_view_title",
                "h1",
                "h2",
            ]
            for selector in title_selectors:
                el = await page.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text:
                        title = text
                        break
            if not title:
                title = "제목 없음"

            # 본문 추출
            content = ""
            body_selectors = [
                ".xe_content",
                ".rd_body .xe_content",
                ".document_read .xe_content",
                ".rd_body",
                "p",
            ]
            for selector in body_selectors:
                el = await main_container.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text and len(text) > 10:
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

            # 추천/댓글 수 추출
            likes = 0
            comments = 0
            like_selectors = [
                ".voted_count",
                "[class*='like'] span",
                ".count_vote",
                ".btn_like .count",
            ]
            cmt_selectors = [
                ".comment_count",
                "[class*='comment'] .count",
                ".count_comment",
                ".cmt_count",
            ]

            for selector in like_selectors:
                el = await page.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    match = re.search(r"\d+", text)
                    if match:
                        likes = int(match.group())
                        break

            for selector in cmt_selectors:
                el = await page.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    match = re.search(r"\d+", text)
                    if match:
                        comments = int(match.group())
                        break

            category = self._determine_category(title, content)
            logger.info(f"Extracted: '{title[:20]}...' | Likes {likes} | Comments {comments}")

            await self._clean_ui_for_screenshot(page)

            short_id = uuid.uuid4().hex[:8]
            safe_title = "".join(x for x in title[:20] if x.isalnum() or x in " -_").strip()
            if not safe_title:
                safe_title = "post"
            filename = f"fmkorea_{safe_title}_{short_id}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            await asyncio.sleep(0.5)
            try:
                await asyncio.wait_for(
                    main_container.screenshot(path=filepath),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                failure_reason = "screenshot_timeout"
                logger.error(f"Screenshot timed out for {url}")
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
