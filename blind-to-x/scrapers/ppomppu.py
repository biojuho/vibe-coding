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
    async def _fetch_post_urls(self, feed_url, board_id, label="posts", limit=5, any_board=False):
        """뽐뿌 게시판 목록 페이지에서 게시글 URL을 수집합니다."""
        urls = []
        self.last_feed_fetch_error = None
        self.last_feed_fetch_reason = None
        page = await self._new_page()

        # 뽐뿌는 ZBoard 엔진 사용 — 게시글 링크 셀렉터
        if any_board:
            # hot.php (핫게시판)는 전체 게시판 인기글이므로 board_id 필터 없이 수집
            link_selectors = [
                "a[href*='view.php']",
                "td.title a[href*='view.php']",
                "td[class*='title'] a[href*='view.php']",
                ".list_table td.title a",
            ]
        else:
            link_selectors = [
                f"a[href*='view.php?id={board_id}']",
                f"a[href*='id={board_id}&no=']",
                "td.title a[href*='view.php']",
                "td[class*='title'] a[href*='view.php']",
                ".list_table td.title a",
                "a[href*='view.php']",
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
                            # 실제 게시글 URL만 허용 (no= 포함)
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
                    # response.text는 이미 Unicode(UTF-8)로 디코딩됨 → charset=utf-8 선언
                    await route.fulfill(body=html_content, content_type="text/html; charset=utf-8")

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
        """뽐뿌 핫게시판 인기글 URL 수집 (전체 게시판 인기 모음)."""
        return await self._fetch_post_urls(
            f"{self.BASE_URL}/hot.php",
            board_id="humor",
            label="popular posts (뽐뿌 핫게시판)",
            limit=limit,
            any_board=True,
        )

    async def get_trending_urls(self, limit=5):
        """뽐뿌 유머 게시판 최신글 URL 수집."""
        return await self._fetch_post_urls(
            f"{self.BASE_URL}/zboard/zboard.php?id=humor",
            board_id="humor",
            label="trending posts (뽐뿌 유머 최신)",
            limit=limit,
        )

    async def get_feed_urls(self, mode="popular", limit=5):
        """통합 피드 URL getter. mode: 'popular' 또는 'trending'."""
        if mode == "trending":
            return await self.get_trending_urls(limit=limit)
        return await self.get_popular_urls(limit=limit)

    async def get_feed_candidates(self, mode="trending", limit=5):
        """피드 목록에서 제목 + 조회수/추천수/댓글수를 사전 추출하여 인기순 정렬."""
        feed_url = f"{self.BASE_URL}/hot.php" if mode == "popular" else f"{self.BASE_URL}/zboard/zboard.php?id=humor"
        candidates = []
        page = await self._new_page()
        try:
            html_content = None
            try:
                html_content = await self._fetch_html_via_session(feed_url)
            except Exception as fetch_err:
                logger.warning("curl_cffi fetch failed for candidates: %s", fetch_err)

            if html_content:

                async def intercept(route):
                    await route.fulfill(body=html_content, content_type="text/html; charset=utf-8")

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
            else:
                await page.goto(feed_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)

            # 뽐뿌 목록 행에서 제목 + 조회수 + 추천수 + 댓글수 추출
            rows = await page.query_selector_all("tr")
            for row in rows[: limit * 4]:
                # 제목 + URL
                title_el = await row.query_selector(
                    "td.title a[href*='view.php'], td[class*='title'] a[href*='view.php'], a[href*='view.php?id=']"
                )
                if not title_el:
                    continue
                href = await title_el.get_attribute("href")
                url = self._normalize_url(href)
                if not url or "no=" not in url:
                    continue
                # regulation 보드 (게시판 규칙)는 콘텐츠가 아니므로 스킵
                if "id=regulation" in url:
                    continue
                if url in {c.url for c in candidates}:
                    continue
                raw_title = (await title_el.inner_text()).strip()
                # [댓글수] 제거
                comments = 0
                cmt_match = re.search(r"\[(\d+)\]", raw_title)
                if cmt_match:
                    comments = int(cmt_match.group(1))
                title = re.sub(r"\s*\[\d+\]\s*$", "", raw_title).strip()

                # 조회수
                views = 0
                tds = await row.query_selector_all("td")
                for td in tds:
                    text = (await td.inner_text()).strip()
                    if text.isdigit() and int(text) > 10:
                        views = max(views, int(text))

                # 추천수
                likes = 0
                rec_el = await row.query_selector("td.recommend, td.vote")
                if rec_el:
                    rec_text = (await rec_el.inner_text()).strip()
                    if rec_text.lstrip("-").isdigit():
                        likes = max(0, int(rec_text))

                # 이미지 아이콘/썸네일 여부 (뽐뿌 목록에서 이미지 글 표시)
                has_image = False
                image_count = 0
                img_icon = await row.query_selector("img[src*='icon_pic'], .pic_icon, img[alt*='사진']")
                if img_icon:
                    has_image = True
                    image_count = 1  # 목록에서는 정확한 개수 알 수 없음
                # 썸네일 이미지가 있으면 이미지 글로 판단
                thumb = await row.query_selector("img[src*='thumb'], img[src*='no_unnamed']")
                if thumb:
                    has_image = True
                    image_count = max(image_count, 1)

                candidate = FeedCandidate(
                    url=url,
                    title=title,
                    likes=likes,
                    comments=comments,
                    views=views,
                    source=self.SOURCE_NAME,
                    has_image=has_image,
                    image_count=image_count,
                )
                candidate.compute_engagement()
                candidates.append(candidate)

            logger.info("Ppomppu feed candidates: %d collected, sorting by engagement.", len(candidates))
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
        if any(kw in text for kw in ["유머", "웃긴", "개그", "ㅋㅋ", "ㅎㅎ", "드립", "짤", "병맛"]):
            return "humor"
        elif any(kw in text for kw in ["쇼핑", "할인", "구매", "뽐뿌", "핫딜", "특가"]):
            return "deal"
        elif any(kw in text for kw in ["연애", "결혼", "남친", "여친", "썸"]):
            return "relationship"
        elif any(kw in text for kw in ["정치", "뉴스", "사회", "이슈", "논란"]):
            return "news"
        return "general"

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
                # response.text는 이미 Unicode(UTF-8)로 디코딩됨 → charset=utf-8 선언
                await route.fulfill(body=html_content, content_type="text/html; charset=utf-8")

            await page.route(url, intercept_post)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 뽐뿌 게시글 컨테이너 셀렉터 (우선순위 순, 2026-03 구조 반영)
            content_selectors = [
                ".board-contents",  # 실제 본문 td (현행)
                ".JS_ContentMain",  # JS 렌더링 콘텐츠 영역 (현행)
                ".bbsDetail",  # 레거시
                "#view_content",
                ".view_content",
                "td.view_content",
                ".zb_content",
                "main",
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
                    for selector in [
                        ".board-contents",
                        ".JS_ContentMain",
                        ".bbsDetail",
                        "#view_content",
                        "main",
                        "body",
                    ]:
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
            image_urls = []

            # 제목 추출 (2026-03 구조: h1에 제목 있음)
            title = ""
            title_selectors = [
                "h1",  # 현행 뽐뿌 제목 위치
                ".topTitle-mainbox",  # 제목 영역 래퍼
                ".bbsSubject",  # 레거시
                ".view_title",
                "td.title_subject",
                ".subject",
                "h2",
            ]
            for selector in title_selectors:
                el = await page.query_selector(selector)
                if el:
                    # h1 내부 #comment span (댓글수) 제거 후 제목만 추출
                    cmt_el = await el.query_selector("#comment")
                    if cmt_el:
                        await cmt_el.evaluate("el => el.remove()")
                    text = (await el.inner_text()).strip()
                    if text:
                        title = text
                        break
            if not title:
                title = "제목 없음"

            # 본문 추출 (2026-03 구조: .board-contents 또는 .JS_ContentMain)
            content = ""
            body_selectors = [
                ".board-contents",  # 현행 본문 td
                ".JS_ContentMain",  # JS 렌더링 콘텐츠
                "#view_content",  # 레거시
                ".view_content",
                "td.view_content",
                ".zb_content",
                ".bbsDetail td",
            ]
            for selector in body_selectors:
                el = await main_container.query_selector(selector)
                if not el:
                    el = await page.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text and len(text) > 10:
                        content = text
                        # 이미지 소스 추출
                        img_elements = await el.query_selector_all("img")
                        for img_el in img_elements:
                            src = await img_el.get_attribute("src")
                            if src and "cdn" not in src.lower() and "icon" not in src.lower():
                                image_urls.append(src)
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

            # 추천/댓글 수 추출 (2026-03 구조 반영)
            likes = 0
            comments = 0

            # 추천수: #vote_list_btn_txt 안에 숫자가 있음
            vote_el = await page.query_selector("#vote_list_btn_txt")
            if vote_el:
                vote_text = (await vote_el.inner_text()).strip()
                if vote_text.isdigit():
                    likes = int(vote_text)

            # 댓글수: h1 내부 #comment span
            cmt_span = await page.query_selector("h1 #comment")
            if cmt_span:
                cmt_text = (await cmt_span.inner_text()).strip()
                if cmt_text.isdigit():
                    comments = int(cmt_text)
            else:
                # 폴백: 실제 댓글 div 개수 카운팅
                comment_divs = await page.query_selector_all(".comment_line")
                comments = len(comment_divs)

            category = self._determine_category(title, content)

            # ── 본문 이미지 URL 추출 (X/Twitter 노출용) ──────────────
            image_urls = []
            body_el = None
            for sel in [".board-contents", ".JS_ContentMain", "#view_content"]:
                body_el = await page.query_selector(sel)
                if body_el:
                    break
            if body_el:
                img_elements = await body_el.query_selector_all("img")
                for img in img_elements:
                    src = await img.get_attribute("src")
                    if not src:
                        continue
                    # 이모티콘/아이콘 제외, 실제 콘텐츠 이미지만
                    if any(skip in src for skip in ["icon", "emoji", "smiley", "blank.", "spacer", "1x1"]):
                        continue
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = f"{self.BASE_URL}{src}"
                    if src.startswith("http"):
                        image_urls.append(src)
            has_images = len(image_urls) > 0
            logger.info(
                f"Extracted: '{title[:20]}...' | Likes {likes} | Comments {comments} | Images {len(image_urls)}"
            )

            await self._clean_ui_for_screenshot(page)

            short_id = uuid.uuid4().hex[:8]
            safe_title = "".join(x for x in title[:20] if x.isalnum() or x in " -_").strip()
            if not safe_title:
                safe_title = "post"
            filename = f"ppomppu_{safe_title}_{short_id}.png"
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
