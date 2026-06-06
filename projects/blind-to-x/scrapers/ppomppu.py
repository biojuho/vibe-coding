"""Ppomppu (ppomppu.co.kr) humor board scraper implementation."""

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

_POPULAR_FEED_PATH = "/hot.php"
_TRENDING_FEED_PATH = "/zboard/zboard.php?id=humor"
_FEED_TITLE_SELECTOR = "td.title a[href*='view.php'], td[class*='title'] a[href*='view.php'], a[href*='view.php?id=']"
_FEED_RECOMMEND_SELECTOR = "td.recommend, td.vote"
_FEED_IMAGE_ICON_SELECTOR = "img[src*='icon_pic'], .pic_icon, img[alt*='사진']"
_FEED_THUMB_SELECTOR = "img[src*='thumb'], img[src*='no_unnamed']"
_POST_CONTAINER_SELECTORS = (
    ".board-contents",
    ".JS_ContentMain",
    ".bbsDetail",
    "#view_content",
    ".view_content",
    "td.view_content",
    ".zb_content",
    "main",
    "body",
)
_DIRECT_POST_CONTAINER_SELECTORS = (".board-contents", ".JS_ContentMain", ".bbsDetail", "#view_content", "main", "body")
_POST_TITLE_SELECTORS = ("h1", ".topTitle-mainbox", ".bbsSubject", ".view_title", "td.title_subject", ".subject", "h2")
_POST_BODY_SELECTORS = (
    ".board-contents",
    ".JS_ContentMain",
    "#view_content",
    ".view_content",
    "td.view_content",
    ".zb_content",
    ".bbsDetail td",
)
_POST_IMAGE_BODY_SELECTORS = (".board-contents", ".JS_ContentMain", "#view_content")


class PpomppuScraper(BaseScraper):
    """Scraper for ppomppu.co.kr Korean community (humor board)."""

    SOURCE_NAME = "ppomppu"

    BASE_URL = "https://www.ppomppu.co.kr"

    # ── EUC-KR encoding override ──────────────────────────────────
    async def _fetch_html_via_session(self, url):
        """뽐뿌는 EUC-KR 인코딩이므로 response.content를 수동 디코딩합니다."""
        import re as _re
        from curl_cffi.requests import AsyncSession

        last_error = None
        for attempt in range(1, self.request_retries + 1):
            proxy_url = self.proxy_manager.get_random_proxy()
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            try:
                async with AsyncSession(timeout=self.request_timeout, proxies=proxies) as session:
                    response = await session.get(url, impersonate="chrome120")
                    response.raise_for_status()
                    # 뽐뿌 EUC-KR → UTF-8 디코딩 (cp949 superset 먼저 시도)
                    try:
                        html = response.content.decode("cp949")
                    except (UnicodeDecodeError, LookupError):
                        html = response.content.decode("euc-kr", errors="replace")
                    html = _re.sub(r"<script[^>]+src=[^>]+></script>", "", html, flags=_re.DOTALL)
                    return html
            except Exception as e:
                last_error = e
                if attempt < self.request_retries:
                    sleep_for = self.request_backoff * attempt
                    logger.warning(
                        f"Fetch failed ({attempt}/{self.request_retries}) for {url}: {e}. Retrying in {sleep_for:.1f}s."
                    )
                    await asyncio.sleep(sleep_for)
                else:
                    logger.error(f"Fetch failed after {self.request_retries} attempts for {url}: {e}")
        raise RuntimeError(f"Failed to fetch HTML for {url}") from last_error

    # ── URL helpers ──────────────────────────────────────────────────
    def _normalize_url(self, href):
        if not href:
            return None
        if href.startswith("http"):
            if "ppomppu.co.kr" in href:
                return href
            return None
        if href.startswith("/"):
            return f"{self.BASE_URL}{href}"
        # 상대 경로 (view.php?...)
        if href.startswith("view.php") or href.startswith("zboard"):
            return f"{self.BASE_URL}/zboard/{href}"
        return None

    # ── Feed URL fetching ────────────────────────────────────────────
    @staticmethod
    def _feed_link_selectors(board_id, any_board):
        if any_board:
            return [
                "a[href*='view.php']",
                "td.title a[href*='view.php']",
                "td[class*='title'] a[href*='view.php']",
                ".list_table td.title a",
            ]
        return [
            f"a[href*='view.php?id={board_id}']",
            f"a[href*='id={board_id}&no=']",
            "td.title a[href*='view.php']",
            "td[class*='title'] a[href*='view.php']",
            ".list_table td.title a",
            "a[href*='view.php']",
        ]

    async def _collect_feed_urls_from_page(self, page, link_selectors, board_id, limit, any_board):
        collected = []
        for selector in link_selectors:
            try:
                await page.wait_for_selector(selector, timeout=self.selector_timeout_ms)
                elements = await page.query_selector_all(selector)
                for el in elements[: limit * 3]:
                    href = await el.get_attribute("href")
                    normalized = self._normalize_url(href)
                    if normalized and normalized not in collected:
                        if "no=" in normalized and (any_board or board_id in normalized):
                            collected.append(normalized)
                    if len(collected) >= limit:
                        break
                if collected:
                    logger.info(f"Found {len(collected)} URLs with selector: {selector}")
                    return collected[:limit]
            except PlaywrightTimeoutError:
                continue
        return collected[:limit]

    async def _fetch_feed_html_for_urls(self, feed_url, label):
        try:
            return await self._fetch_html_via_session(feed_url)
        except Exception as fetch_err:
            logger.warning(f"curl_cffi fetch failed for {label}: {fetch_err}. Falling back to direct navigation.")
            return None

    async def _try_intercept_feed_urls(
        self, page, feed_url, html_content, link_selectors, board_id, label, limit, any_board
    ):
        if not html_content:
            return []

        async def intercept(route):
            await route.fulfill(body=html_content, content_type="text/html; charset=utf-8")

        try:
            await page.route(feed_url, intercept)
            await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            urls = await self._collect_feed_urls_from_page(page, link_selectors, board_id, limit, any_board)
            logger.info(f"Found {len(urls)} {label} (intercept mode).")
            return urls
        except Exception as intercept_err:
            logger.warning(f"Intercept mode failed for {label}: {intercept_err}.")
            return []
        finally:
            try:
                await page.unroute(feed_url)
            except Exception:
                pass

    async def _try_direct_feed_urls(self, page, feed_url, link_selectors, board_id, label, limit, any_board):
        logger.info(f"Trying direct navigation for {label}...")
        try:
            await page.goto(feed_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            urls = await self._collect_feed_urls_from_page(page, link_selectors, board_id, limit, any_board)
            logger.info(f"Found {len(urls)} {label} (direct navigation).")
            return urls
        except Exception as direct_err:
            self.last_feed_fetch_error = f"Feed fetch failed ({label}): {direct_err}"
            self.last_feed_fetch_reason = "feed_fetch_failed_after_fallback"
            logger.error(self.last_feed_fetch_error)
            return []

    async def _fetch_post_urls(self, feed_url, board_id, label="posts", limit=5, any_board=False):
        """뽐뿌 게시판 목록 페이지에서 게시글 URL을 수집합니다."""
        urls = []
        self.last_feed_fetch_error = None
        self.last_feed_fetch_reason = None
        page = await self._new_page()
        link_selectors = self._feed_link_selectors(board_id, any_board)

        try:
            logger.info(f"Fetching {label} from {feed_url}...")

            html_content = await self._fetch_feed_html_for_urls(feed_url, label)
            urls = await self._try_intercept_feed_urls(
                page,
                feed_url,
                html_content,
                link_selectors,
                board_id,
                label,
                limit,
                any_board,
            )
            if urls:
                return urls

            urls = await self._try_direct_feed_urls(
                page,
                feed_url,
                link_selectors,
                board_id,
                label,
                limit,
                any_board,
            )
        except Exception as e:
            self.last_feed_fetch_error = f"Feed fetch failed ({label}): {e}"
            self.last_feed_fetch_reason = "feed_fetch_failed"
            logger.error(self.last_feed_fetch_error)
        finally:
            await page.close()

        return urls

    async def get_popular_urls(self, limit=5):
        """뽐뿌 핫게시판 인기글 URL 수집 (전체 게시판 인기 모음)."""
        return await self._fetch_post_urls(
            self._feed_url_for_mode("popular"),
            board_id="humor",
            label="popular posts (뽐뿌 핫게시판)",
            limit=limit,
            any_board=True,
        )

    async def get_trending_urls(self, limit=5):
        """뽐뿌 유머 게시판 최신글 URL 수집."""
        return await self._fetch_post_urls(
            self._feed_url_for_mode("trending"),
            board_id="humor",
            label="trending posts (뽐뿌 유머 최신)",
            limit=limit,
        )

    async def get_feed_urls(self, mode="popular", limit=5):
        """통합 피드 URL getter. mode: 'popular' 또는 'trending'."""
        if mode == "trending":
            return await self.get_trending_urls(limit=limit)
        return await self.get_popular_urls(limit=limit)

    def _feed_url_for_mode(self, mode):
        feed_path = _POPULAR_FEED_PATH if mode == "popular" else _TRENDING_FEED_PATH
        return f"{self.BASE_URL}{feed_path}"

    async def _navigate_feed_page(self, page, feed_url, html_content):
        if html_content:

            async def intercept(route):
                await route.fulfill(body=html_content, content_type="text/html; charset=utf-8")

            try:
                await page.route(feed_url, intercept)
                await page.goto(feed_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                return
            except Exception:
                try:
                    await page.unroute(feed_url)
                except Exception:
                    pass

        await page.goto(feed_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

    @staticmethod
    def _feed_comment_count(raw_title):
        cmt_match = re.search(r"\[(\d+)\]", raw_title)
        return int(cmt_match.group(1)) if cmt_match else 0

    @staticmethod
    def _feed_title_without_comment_count(raw_title):
        return re.sub(r"\s*\[\d+\]\s*$", "", raw_title).strip()

    @staticmethod
    async def _feed_row_views(row):
        views = 0
        tds = await row.query_selector_all("td")
        for td in tds:
            text = (await td.inner_text()).strip()
            if text.isdigit() and int(text) > 10:
                views = max(views, int(text))
        return views

    @staticmethod
    async def _feed_row_likes(row):
        rec_el = await row.query_selector(_FEED_RECOMMEND_SELECTOR)
        if not rec_el:
            return 0
        rec_text = (await rec_el.inner_text()).strip()
        if rec_text.lstrip("-").isdigit():
            return max(0, int(rec_text))
        return 0

    @staticmethod
    async def _feed_row_image_state(row):
        has_image = False
        image_count = 0
        img_icon = await row.query_selector(_FEED_IMAGE_ICON_SELECTOR)
        if img_icon:
            has_image = True
            image_count = 1
        thumb = await row.query_selector(_FEED_THUMB_SELECTOR)
        if thumb:
            has_image = True
            image_count = max(image_count, 1)
        return has_image, image_count

    async def _feed_candidate_from_row(self, row):
        title_el = await row.query_selector(_FEED_TITLE_SELECTOR)
        if not title_el:
            return None

        href = await title_el.get_attribute("href")
        url = self._normalize_url(href)
        if not url or "no=" not in url or "id=regulation" in url:
            return None

        raw_title = (await title_el.inner_text()).strip()
        has_image, image_count = await self._feed_row_image_state(row)
        candidate = FeedCandidate(
            url=url,
            title=self._feed_title_without_comment_count(raw_title),
            likes=await self._feed_row_likes(row),
            comments=self._feed_comment_count(raw_title),
            views=await self._feed_row_views(row),
            source=self.SOURCE_NAME,
            has_image=has_image,
            image_count=image_count,
        )
        candidate.compute_engagement()
        return candidate

    async def _collect_feed_candidates_from_page(self, page, limit):
        candidates = []
        seen = set()
        rows = await page.query_selector_all("tr")
        for row in rows[: limit * 4]:
            candidate = await self._feed_candidate_from_row(row)
            if not candidate or candidate.url in seen:
                continue
            candidates.append(candidate)
            seen.add(candidate.url)

        candidates.sort(key=lambda c: c.engagement_score, reverse=True)
        return candidates[:limit]

    async def get_feed_candidates(self, mode="trending", limit=5):
        """피드 목록에서 제목 + 조회수/추천수/댓글수를 사전 추출하여 인기순 정렬."""
        feed_url = self._feed_url_for_mode(mode)
        candidates = []
        page = await self._new_page()
        try:
            html_content = None
            try:
                html_content = await self._fetch_html_via_session(feed_url)
            except Exception as fetch_err:
                logger.warning("curl_cffi fetch failed for candidates: %s", fetch_err)

            await self._navigate_feed_page(page, feed_url, html_content)

            candidates = await self._collect_feed_candidates_from_page(page, limit)
            logger.info("Ppomppu feed candidates: %d collected, sorting by engagement.", len(candidates))
        except Exception as e:
            logger.warning("Feed candidate extraction failed: %s. Falling back to URL-only.", e)
            urls = await self.get_feed_urls(mode=mode, limit=limit)
            return [FeedCandidate(url=u, source=self.SOURCE_NAME) for u in urls]
        finally:
            await page.close()

        return candidates

    # ── Category classification ──────────────────────────────────────
    def _determine_category(self, title, content):
        text = (title + " " + content).lower()
        if any(kw in text for kw in ["유머", "웃긴", "개그", "ㅋㅋ", "ㅎㅎ", "드립", "짤", "병맛"]):
            return "humor"
        elif any(kw in text for kw in ["쇼핑", "할인", "구매", "뽐뿌", "핫딜", "특가"]):
            return "deal"
        elif any(kw in text for kw in ["연애", "결혼", "남친", "여친", "썸"]):
            return "relationship"
        elif any(kw in text for kw in ["정치", "뉴스", "사회", "이슈", "논란"]):
            return "news"
        return "general"

    @staticmethod
    def _post_fetch_failure_reason(fetch_err):
        err_str = str(fetch_err).lower()
        if "403" in err_str:
            return "http_403_forbidden"
        if "404" in err_str:
            return "http_404_not_found"
        if "timeout" in err_str:
            return "fetch_timeout"
        return "html_fetch_failed"

    @staticmethod
    async def _route_post_html(page, url, html_content):
        async def intercept_post(route):
            await route.fulfill(body=html_content, content_type="text/html; charset=utf-8")

        await page.route(url, intercept_post)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

    async def _find_post_container(self, page, selectors, timeout_ms):
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

    async def _find_post_container_after_direct_navigation(self, page, url):
        logger.warning(f"Intercept mode failed for {url}. Trying direct navigation...")
        try:
            await page.unroute(url)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            container = await self._find_post_container(
                page,
                _DIRECT_POST_CONTAINER_SELECTORS,
                self.direct_fallback_timeout_ms,
            )
            return container, "intercept_selector_not_found"
        except Exception as fallback_err:
            logger.error(f"Fallback navigation failed: {fallback_err}")
            return None, "direct_navigation_failed"

    @staticmethod
    async def _extract_post_title(page):
        for selector in _POST_TITLE_SELECTORS:
            element = await page.query_selector(selector)
            if not element:
                continue
            comment_element = await element.query_selector("#comment")
            if comment_element:
                await comment_element.evaluate("el => el.remove()")
            text = (await element.inner_text()).strip()
            if text:
                return text
        return "제목 없음"

    async def _extract_post_content_text(self, page, main_container):
        for selector in _POST_BODY_SELECTORS:
            element = await main_container.query_selector(selector)
            if not element:
                element = await page.query_selector(selector)
            if not element:
                continue
            text = (await element.inner_text()).strip()
            if text and len(text) > 10:
                return text

        try:
            content = self._extract_clean_text(await page.content())
            if content:
                logger.info("Content extracted via trafilatura fallback")
            return content
        except Exception:
            return ""

    @staticmethod
    async def _extract_post_counts(page):
        likes = 0
        comments = 0
        vote_el = await page.query_selector("#vote_list_btn_txt")
        if vote_el:
            vote_text = (await vote_el.inner_text()).strip()
            if vote_text.isdigit():
                likes = int(vote_text)

        comment_span = await page.query_selector("h1 #comment")
        if comment_span:
            comment_text = (await comment_span.inner_text()).strip()
            if comment_text.isdigit():
                comments = int(comment_text)
        else:
            comments = len(await page.query_selector_all(".comment_line"))
        return likes, comments

    async def _extract_post_image_urls(self, page):
        body_el = None
        for selector in _POST_IMAGE_BODY_SELECTORS:
            body_el = await page.query_selector(selector)
            if body_el:
                break
        if not body_el:
            return []

        image_urls = []
        for img in await body_el.query_selector_all("img"):
            src = await img.get_attribute("src")
            if not src or any(skip in src for skip in ["icon", "emoji", "smiley", "blank.", "spacer", "1x1"]):
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = f"{self.BASE_URL}{src}"
            if src.startswith("http"):
                image_urls.append(src)
        return image_urls

    async def _save_post_screenshot(self, page, main_container, title):
        await self._clean_ui_for_screenshot(page)

        short_id = uuid.uuid4().hex[:8]
        safe_title = "".join(x for x in title[:20] if x.isalnum() or x in " -_").strip()
        filename = f"ppomppu_{safe_title or 'post'}_{short_id}.png"
        filepath = os.path.join(self.screenshot_dir, filename)

        await asyncio.sleep(0.5)
        try:
            await asyncio.wait_for(main_container.screenshot(path=filepath), timeout=30)
        except asyncio.TimeoutError:
            logger.error("Screenshot timed out")
            raise
        logger.info(f"Saved screenshot: {filepath}")
        return filepath

    # ── Post scraping ────────────────────────────────────────────────
    async def scrape_post(self, url):
        logger.info(f"Scraping Ppomppu post: {url}")
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
                failure_reason = self._post_fetch_failure_reason(fetch_err)
                raise

            await self._route_post_html(page, url, html_content)
            main_container = await self._find_post_container(page, _POST_CONTAINER_SELECTORS, self.selector_timeout_ms)

            if not main_container:
                main_container, failure_reason = await self._find_post_container_after_direct_navigation(page, url)

            if not main_container:
                failure_stage = "parse"
                failure_reason = "main_container_not_found"
                raise Exception(f"Could not find content container on {url}")

            failure_stage = "parse"

            # 제목 추출 (2026-03 구조: h1에 제목 있음)
            title = await self._extract_post_title(page)

            # 본문 추출 (2026-03 구조: .board-contents 또는 .JS_ContentMain)
            content = await self._extract_post_content_text(page, main_container)

            if title == "제목 없음" and not content:
                failure_reason = "title_and_content_missing"
                raise Exception(f"Could not parse title/content on {url}")

            # 추천/댓글 수 추출 (2026-03 구조 반영)
            likes, comments = await self._extract_post_counts(page)

            category = self._determine_category(title, content)

            # ── 본문 이미지 URL 추출 (X/Twitter 노출용) ──────────────
            image_urls = await self._extract_post_image_urls(page)
            has_images = len(image_urls) > 0
            logger.info(
                f"Extracted: '{title[:20]}...' | Likes {likes} | Comments {comments} | Images {len(image_urls)}"
            )

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
                "image_urls": image_urls,
                "has_images": has_images,
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
