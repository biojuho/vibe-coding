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
from scrapers.base import BaseScraper, FeedCandidate

logger = logging.getLogger(__name__)


class _FMKoreaScrapeFailure(Exception):  # noqa: N818
    def __init__(self, message: str, *, reason: str, stage: str = "post_fetch"):
        super().__init__(message)
        self.reason = reason
        self.stage = stage


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
        async with self._new_page_cm() as page:
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
                        for el in elements[: limit * 3]:
                            href = await el.get_attribute("href")
                            normalized = self._normalize_url(href)
                            if normalized and normalized not in collected:
                                if re.search(r"/\d+$", normalized) or re.search(r"[?&]document_srl=\d+", normalized):
                                    collected.append(normalized)
                            if len(collected) >= limit:
                                break
                        if collected:
                            logger.info(f"Found {len(collected)} URLs with selector: {selector}")
                            return collected[:limit]
                    except PlaywrightTimeoutError:
                        continue
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
                    except Exception as exc:
                        logger.debug("Fallback link collection failed (non-critical): %s", exc)
                return collected[:limit]

            try:
                logger.info(f"Fetching {label} from {feed_url}...")

                html_content = None
                try:
                    html_content = await self._fetch_html_via_session(feed_url)
                except Exception as fetch_err:
                    logger.warning(
                        f"curl_cffi fetch failed for {label}: {fetch_err}. Falling back to direct navigation."
                    )

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

    # ── Feed candidates with titles ──────────────────────────────────
    async def get_feed_candidates(self, mode="trending", limit=5):
        """피드 목록에서 제목 + 댓글수를 사전 추출하여 FeedCandidate 반환."""
        feed_url = f"{self.BASE_URL}/best" if mode == "popular" else f"{self.BASE_URL}/humor"
        candidates: list[FeedCandidate] = []
        async with self._new_page_cm() as page:
            html_content = None
            try:
                html_content = await self._fetch_html_via_session(feed_url)
            except Exception as fetch_err:
                logger.warning("curl_cffi fetch failed for candidates: %s", fetch_err)

            if html_content:

                async def intercept(route):
                    await route.fulfill(body=html_content, content_type="text/html")

                try:
                    await page.route(feed_url, intercept)
                    await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                except Exception:
                    try:
                        await page.unroute(feed_url)
                    except Exception:
                        pass
                    await page.goto(feed_url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(3)
                finally:
                    try:
                        await page.unroute(feed_url)
                    except Exception:
                        pass
            else:
                await page.goto(feed_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)

            # 목록에서 제목이 포함된 링크를 추출
            link_selectors = [
                "ul.list_best li h3.title a",
                "li.li_best_img_zoom a.hotdeal_var8",
                "li.li_best a.hotdeal_var8",
                "article.li_best h3 a",
                "li[class*='li_best'] h3 a",
                "h3.title a[href*='/best/']",
                ".bd_lst_wrp a[href*='/best/']",
                "a[href*='/humor/']",
                "a[href*='/best/']",
            ]
            seen_urls: set[str] = set()
            for selector in link_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements[: limit * 3]:
                        href = await el.get_attribute("href")
                        url = self._normalize_url(href)
                        if not url or url in seen_urls:
                            continue
                        if not (re.search(r"/\d+$", url) or re.search(r"[?&]document_srl=\d+", url)):
                            continue
                        seen_urls.add(url)
                        title = (await el.inner_text()).strip()
                        # 제목 끝 [댓글수] 추출 후 제거
                        comments = 0
                        cmt_match = re.search(r"\[(\d+)\]\s*$", title)
                        if cmt_match:
                            comments = int(cmt_match.group(1))
                        title = re.sub(r"\s*\[\d+\]\s*$", "", title).strip()

                        c = FeedCandidate(url=url, title=title, comments=comments, source=self.SOURCE_NAME)
                        c.compute_engagement()
                        candidates.append(c)
                        if len(candidates) >= limit:
                            break
                    if candidates:
                        break
                except PlaywrightTimeoutError:
                    continue
                except Exception as e:
                    logger.debug("fmkorea post extraction failed: %s", e)
                    continue

        if candidates:
            candidates.sort(key=lambda c: c.engagement_score, reverse=True)
            return candidates[:limit]

        # Fallback: title extraction failed → return URL-only candidates
        logger.warning("FMKorea get_feed_candidates: title extraction failed, falling back to URL-only mode.")
        urls = await self.get_feed_urls(mode=mode, limit=limit)
        return [FeedCandidate(url=u, source=self.SOURCE_NAME) for u in urls]

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
    def _classify_post_fetch_failure(self, fetch_err):
        err_str = str(fetch_err).lower()
        if "403" in err_str:
            return "http_403_forbidden"
        if "404" in err_str:
            return "http_404_not_found"
        if "timeout" in err_str:
            return "fetch_timeout"
        return "html_fetch_failed"

    async def _fetch_post_html(self, url):
        logger.info("Fetching HTML via curl_cffi...")
        try:
            return await self._fetch_html_via_session(url)
        except Exception as fetch_err:
            raise _FMKoreaScrapeFailure(
                str(fetch_err),
                reason=self._classify_post_fetch_failure(fetch_err),
            ) from fetch_err

    async def _load_post_html(self, page, url, html_content):
        async def intercept_post(route):
            await route.fulfill(body=html_content, content_type="text/html")

        await page.route(url, intercept_post)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

    async def _find_content_container(self, page, selectors, timeout_ms):
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout_ms)
                main_container = await page.query_selector(selector)
                if main_container:
                    logger.info(f"Found content container: {selector}")
                    return main_container
            except PlaywrightTimeoutError:
                continue
        return None

    async def _resolve_content_container(self, page, url):
        content_selectors = [
            ".rd_body",
            ".xe_content",
            "#bd_contents",
            ".document_read",
            "article",
            "main",
            "#__xe_content",
            "body",
        ]
        main_container = await self._find_content_container(page, content_selectors, self.selector_timeout_ms)
        if main_container:
            return main_container

        logger.warning(f"Intercept mode failed for {url}. Trying direct navigation...")
        try:
            await page.unroute(url)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            main_container = await self._find_content_container(
                page,
                [".rd_body", ".xe_content", "main", "article", "body"],
                self.direct_fallback_timeout_ms,
            )
        except Exception as fallback_err:
            logger.error(f"Fallback navigation failed: {fallback_err}")

        if not main_container:
            raise _FMKoreaScrapeFailure(
                f"Could not find content container on {url}",
                reason="main_container_not_found",
                stage="parse",
            )
        return main_container

    async def _extract_post_title(self, page):
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
                    return text
        return "제목 없음"

    async def _extract_post_content(self, page, main_container):
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
                    return text

        try:
            raw_html = await page.content()
            content = self._extract_clean_text(raw_html)
            if content and len(content) >= 10:
                logger.info("Content extracted via trafilatura fallback")
                return content
        except Exception:
            pass

        raise _FMKoreaScrapeFailure(
            "Insufficient text content (minimum 10 chars).",
            reason="insufficient_content_length",
            stage="parse",
        )

    async def _extract_metric_count(self, page, selectors):
        for selector in selectors:
            el = await page.query_selector(selector)
            if el:
                text = (await el.inner_text()).strip()
                match = re.search(r"\d+", text)
                if match:
                    return int(match.group())
        return 0

    async def _extract_post_counts(self, page):
        likes = await self._extract_metric_count(
            page,
            [
                ".voted_count",
                "[class*='like'] span",
                ".count_vote",
                ".btn_like .count",
            ],
        )
        comments = await self._extract_metric_count(
            page,
            [
                ".comment_count",
                "[class*='comment'] .count",
                ".count_comment",
                ".cmt_count",
            ],
        )
        return likes, comments

    async def _save_post_screenshot(self, page, main_container, title, url):
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
        except TimeoutError as exc:
            logger.error(f"Screenshot timed out for {url}")
            raise _FMKoreaScrapeFailure(
                str(exc),
                reason="screenshot_timeout",
                stage="parse",
            ) from exc
        logger.info(f"Saved screenshot: {filepath}")
        return filepath

    def _build_success_result(self, url, title, content, category, likes, comments, screenshot_path):
        return {
            "url": url,
            "title": title.strip(),
            "content": content.strip(),
            "category": category,
            "likes": likes,
            "comments": comments,
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
        logger.info(f"Scraping FMKorea post: {url}")
        failure_stage = "post_fetch"
        failure_reason = "unknown"

        async with self._new_page_cm() as page:
            try:
                delay = self.config.get("delay_seconds", 5)
                if delay > 0:
                    await asyncio.sleep(delay)

                html_content = await self._fetch_post_html(url)

                await self._load_post_html(page, url, html_content)
                main_container = await self._resolve_content_container(page, url)
                failure_stage = "parse"

                title = await self._extract_post_title(page)
                content = await self._extract_post_content(page, main_container)
                likes, comments = await self._extract_post_counts(page)

                category = self._determine_category(title, content)
                logger.info(f"Extracted: '{title[:20]}...' | Likes {likes} | Comments {comments}")

                filepath = await self._save_post_screenshot(page, main_container, title, url)
                return self._build_success_result(url, title, content, category, likes, comments, filepath)

            except _FMKoreaScrapeFailure as e:
                failure_stage = e.stage
                failure_reason = e.reason
                logger.error(f"Error scraping {url}: {e}")
                await self._save_failure_snapshot(page, url, failure_stage, failure_reason)
                return self._build_error_result(url, e, failure_stage, failure_reason)
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                await self._save_failure_snapshot(page, url, failure_stage, failure_reason)
                return self._build_error_result(url, e, failure_stage, failure_reason)
