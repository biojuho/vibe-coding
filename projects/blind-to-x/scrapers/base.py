"""Base scraper with shared browser lifecycle, screenshot, and quality logic."""

import asyncio
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from curl_cffi.requests import AsyncSession

try:
    # patchright: Playwright 드롭인 대체 — 더 강한 스텔스 (Cloudflare/DataDome 우회)
    from patchright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from config import ProxyManager

logger = logging.getLogger(__name__)

# Lazy-loaded Crawl4AI extractor (fallback when CSS selectors fail)
_crawl4ai_extractor = None


class BrowserUnavailableError(RuntimeError):
    """Raised when no Playwright-capable browser runtime is available."""


def _get_crawl4ai_extractor(config):
    """Singleton accessor for Crawl4AI extractor."""
    global _crawl4ai_extractor
    if _crawl4ai_extractor is None:
        try:
            from scrapers.crawl4ai_extractor import Crawl4AIExtractor, _check_crawl4ai

            if _check_crawl4ai():
                _crawl4ai_extractor = Crawl4AIExtractor(config)
                logger.info("Crawl4AI extractor initialized (LLM fallback enabled).")
            else:
                _crawl4ai_extractor = False  # sentinel: unavailable
        except Exception as exc:
            logger.debug("Crawl4AI extractor not available: %s", exc)
            _crawl4ai_extractor = False
    return _crawl4ai_extractor if _crawl4ai_extractor is not False else None


@dataclass
class FeedCandidate:
    """Pre-scrape candidate with feed-level engagement signals."""

    url: str
    title: str = ""
    likes: int = 0
    comments: int = 0
    views: int = 0
    source: str = ""
    engagement_score: float = 0.0
    has_image: bool = False
    image_count: int = 0

    def compute_engagement(self):
        self.engagement_score = self.likes + self.comments * 1.5 + self.views * 0.01
        # 이미지가 있는 글에 가산점 (X/Twitter 노출에 유리)
        if self.has_image:
            self.engagement_score += 50 + min(self.image_count, 5) * 10
        return self.engagement_score


class BaseScraper:
    """Abstract base for all site-specific scrapers."""

    def __init__(self, config):
        self.config = config
        # Selector self-repair: maps failed_selector -> repaired_selector
        self._selector_repairs: dict[str, str] = {}
        self.proxy_manager = ProxyManager(config)
        self.headless = config.get("headless", True)
        self.screenshot_dir = config.get("screenshot_dir", "./screenshots")
        self.request_timeout = int(config.get("request.timeout_seconds", 20))
        self.request_retries = int(config.get("request.retries", 3))
        self.request_backoff = float(config.get("request.backoff_seconds", 1.5))
        self.retention_days = int(config.get("screenshot_retention_days", 0))

        # Scrape quality policy
        self.min_content_length = int(config.get("scrape_quality.min_content_length", 20))
        self.min_korean_ratio = float(config.get("scrape_quality.min_korean_ratio", 0.15))
        self.require_title = bool(config.get("scrape_quality.require_title", True))
        self.max_empty_field_ratio = float(config.get("scrape_quality.max_empty_field_ratio", 0.4))
        self.selector_timeout_ms = int(config.get("scrape_quality.selector_timeout_ms", 5000))
        self.direct_fallback_timeout_ms = int(config.get("scrape_quality.direct_fallback_timeout_ms", 8000))
        self.save_failure_snapshot = bool(config.get("scrape_quality.save_failure_snapshot", True))
        self.failure_snapshot_dir = config.get("scrape_quality.failure_snapshot_dir", ".tmp/failures")

        # Feed fetch state
        self.last_feed_fetch_error = None
        self.last_feed_fetch_reason = None

        # Browser pool (size=1 disables pooling; use config 'browser.pool_size')
        self._pool_size = int(config.get("browser.pool_size", 1))
        self._pool = None  # BrowserContextPool (set in open() if pool_size > 1)

        # Managed browser state (used when pool_size == 1)
        self._camo_ctx = None  # AsyncCamoufox context manager (if using Camoufox)
        self._pw = None
        self._browser = None
        self._context = None
        self._browser_launch_error: Exception | None = None

        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
        if self.save_failure_snapshot and not os.path.exists(self.failure_snapshot_dir):
            os.makedirs(self.failure_snapshot_dir, exist_ok=True)

    # ── Browser lifecycle ────────────────────────────────────────────
    async def open(self):
        """Launch shared browser. Uses context pool when pool_size > 1."""
        # Pool mode
        if self._pool_size > 1:
            if self._pool is not None:
                return
            try:
                from scrapers.browser_pool import BrowserContextPool
            except ImportError:
                from browser_pool import BrowserContextPool
            self._pool = BrowserContextPool(self.config, size=self._pool_size)
            try:
                await self._pool.open()
            except Exception as exc:
                self._pool = None
                self._browser_launch_error = exc
                logger.warning(
                    "Browser pool unavailable; continuing with non-browser fallbacks where possible: %s",
                    exc,
                )
                return
            self._browser_launch_error = None
            logger.info("Browser opened (pool mode, size=%d).", self._pool_size)
            return

        # Single-context mode (original behaviour)
        if self._browser or self._context:
            return
        if self._browser_launch_error is not None:
            return

        proxy_url = self.proxy_manager.get_random_proxy()
        proxy_config = {"server": proxy_url} if proxy_url else None

        # ── Camoufox 우선 시도 (C++ 레벨 핑거프린트 스푸핑) ──────────
        use_camoufox = self.config.get("browser.engine", "auto") != "chromium"
        if use_camoufox:
            try:
                from camoufox.async_api import AsyncCamoufox

                camo_kwargs = {
                    "headless": self.headless,
                    "geoip": True,
                    "locale": "ko-KR",
                }
                if proxy_config:
                    camo_kwargs["proxy"] = proxy_config
                self._camo_ctx = AsyncCamoufox(**camo_kwargs)
                self._browser = await self._camo_ctx.__aenter__()
                self._context = self._browser  # Camoufox context = browser
                self._browser_launch_error = None
                logger.info("Browser opened (Camoufox stealth Firefox).")
                return
            except Exception as exc:
                logger.info("Camoufox unavailable (%s), falling back to Chromium.", exc)

        # ── Patchright/Playwright Chromium 폴백 ──────────────────────
        try:
            self._pw = await async_playwright().start()
            iphone_14_pro = self._pw.devices["iPhone 14 Pro"]

            launch_kwargs = {"headless": self.headless}
            if proxy_config:
                launch_kwargs["proxy"] = proxy_config
                logger.info("Playwright launching with proxy.")

            self._browser = await self._pw.chromium.launch(**launch_kwargs)
            self._context = await self._browser.new_context(**iphone_14_pro, locale="ko-KR")
            await Stealth().apply_stealth_async(self._context)
            self._browser_launch_error = None
            logger.info("Browser opened (Chromium + stealth).")
        except Exception as exc:
            self._browser_launch_error = exc
            logger.warning(
                "Playwright browser unavailable; continuing with non-browser fallbacks where possible: %s",
                exc,
            )
            if self._context:
                try:
                    await self._context.close()
                except Exception:
                    pass
            self._context = None
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
            self._browser = None
            if self._pw:
                try:
                    await self._pw.stop()
                except Exception:
                    pass
            self._pw = None

    async def close(self):
        """Shut down the shared browser and context (or pool)."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            return
        # Camoufox cleanup
        if self._camo_ctx is not None:
            try:
                await self._camo_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Error closing Camoufox: %s", e)
            self._camo_ctx = None
            self._browser = None
            self._context = None
            logger.info("Camoufox browser closed.")
            return
        if self._context:
            try:
                await self._context.close()
            except Exception as e:
                logger.warning(f"Error closing browser context: {e}")
            self._context = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            self._browser = None
        if self._pw:
            try:
                await self._pw.stop()
            except Exception as e:
                logger.warning(f"Error stopping Playwright: {e}")
            self._pw = None
        logger.info("Browser closed.")

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def _new_page(self):
        """Return a new page. Uses pool if enabled, otherwise shared context.

        Stealth is applied at context level in open()/pool.open(),
        so pages automatically inherit all evasions.
        """
        if self._pool is not None:
            return await self._pool.acquire_page()
        if self._context:
            page = await self._context.new_page()
            page.set_default_timeout(30000)
            return page
        if self._browser_launch_error is not None:
            raise BrowserUnavailableError(str(self._browser_launch_error)) from self._browser_launch_error
        logger.warning("_new_page called before open(). Opening shared browser now.")
        await self.open()
        if self._pool is not None:
            return await self._pool.acquire_page()
        if self._context is None:
            if self._browser_launch_error is not None:
                raise BrowserUnavailableError(str(self._browser_launch_error)) from self._browser_launch_error
            raise BrowserUnavailableError("browser context unavailable")
        page = await self._context.new_page()
        return page

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _new_page_cm(self):
        """Async context manager wrapper for _new_page — guarantees page.close().

        Usage:
            async with self._new_page_cm() as page:
                await page.goto(url)
        """
        page = await self._new_page()
        try:
            yield page
        finally:
            try:
                await page.close()
            except Exception:
                pass

    # ── HTTP fetch ───────────────────────────────────────────────────
    async def _fetch_html_via_session(self, url):
        """Fetch raw HTML with retry/backoff using curl_cffi AsyncSession."""
        last_error = None
        for attempt in range(1, self.request_retries + 1):
            proxy_url = self.proxy_manager.get_random_proxy()
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

            try:
                if proxy_url:
                    logger.debug(f"Using proxy {proxy_url} for curl_cffi fetch")
                async with AsyncSession(timeout=self.request_timeout, proxies=proxies) as session:
                    response = await session.get(url, impersonate="chrome120")
                    response.raise_for_status()
                    # 외부 src 스크립트만 제거하고 인라인 스크립트는 보존.
                    html = re.sub(r"<script[^>]+src=[^>]+></script>", "", response.text, flags=re.DOTALL)
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

    # ── Screenshot helpers ───────────────────────────────────────────
    async def _take_screenshot(self, page, path: str, timeout_seconds: int = 30) -> bool:
        """Timeout-protected screenshot helper. Returns True on success.

        Wraps page.screenshot() in asyncio.wait_for() to prevent infinite hang
        on slow or unresponsive pages.
        """
        try:
            await asyncio.wait_for(
                page.screenshot(path=path, full_page=False),
                timeout=float(timeout_seconds),
            )
            return True
        except asyncio.TimeoutError:
            logger.warning("Screenshot timed out after %ds (path=%s)", timeout_seconds, path)
            return False
        except Exception as exc:
            logger.debug("Screenshot failed (path=%s): %s", path, exc)
            return False

    # ── Selector self-repair ─────────────────────────────────────
    def _suggest_selectors(self, html: str, failed_selector: str) -> list[str]:
        """Parse the failed selector and search HTML for similar elements.

        Uses regex-based HTML parsing only (no BeautifulSoup dependency).
        Returns up to 3 candidate selectors ordered by similarity.
        """
        candidates: list[str] = []

        # Extract the target type and value from the failed selector
        # e.g. ".my-class" -> class name "my-class"
        #      "#my-id"    -> id "my-id"
        #      "div.foo"   -> tag "div", class "foo"
        failed_clean = failed_selector.strip()

        # Extract class name from selector (e.g. ".board-contents" -> "board-contents")
        cls_match = re.search(r"\.([a-zA-Z_][\w-]*)", failed_clean)
        target_class = cls_match.group(1) if cls_match else None

        # Extract id from selector (e.g. "#main-content" -> "main-content")
        id_match = re.search(r"#([a-zA-Z_][\w-]*)", failed_clean)
        target_id = id_match.group(1) if id_match else None

        # Extract tag name from selector (e.g. "article.post" -> "article")
        tag_match = re.match(r"^([a-zA-Z][\w]*)", failed_clean)
        target_tag = tag_match.group(1) if tag_match else None

        # Strategy 1: Find elements with similar class names
        if target_class:
            # Split class name by common delimiters to get component words
            parts = re.split(r"[-_]", target_class)
            significant_parts = [p for p in parts if len(p) > 2]

            # Find all class values in the HTML
            all_classes = re.findall(r'class=["\']([^"\']+)["\']', html)
            scored: list[tuple[float, str]] = []
            for class_attr in all_classes:
                for cls in class_attr.split():
                    if cls == target_class:
                        continue  # skip exact match (it didn't work)
                    # Score by how many parts overlap
                    cls_parts = re.split(r"[-_]", cls)
                    if not significant_parts:
                        continue
                    overlap = sum(1 for p in significant_parts if p.lower() in [cp.lower() for cp in cls_parts])
                    if overlap > 0:
                        score = overlap / max(len(significant_parts), len(cls_parts))
                        scored.append((score, f".{cls}"))

            # Deduplicate and sort by score descending
            seen: set[str] = set()
            for _score, sel in sorted(scored, key=lambda x: -x[0]):
                if sel not in seen:
                    seen.add(sel)
                    candidates.append(sel)
                if len(candidates) >= 3:
                    break

        # Strategy 2: Find elements with similar id names
        if target_id and len(candidates) < 3:
            id_parts = re.split(r"[-_]", target_id)
            significant_id_parts = [p for p in id_parts if len(p) > 2]
            all_ids = re.findall(r'id=["\']([^"\']+)["\']', html)
            for eid in all_ids:
                if eid == target_id:
                    continue
                eid_parts = re.split(r"[-_]", eid)
                if significant_id_parts:
                    overlap = sum(1 for p in significant_id_parts if p.lower() in [ep.lower() for ep in eid_parts])
                    if overlap > 0:
                        sel = f"#{eid}"
                        if sel not in {c for c in candidates}:
                            candidates.append(sel)
                if len(candidates) >= 3:
                    break

        # Strategy 3: If we have a tag, look for that tag with content-related classes
        if target_tag and len(candidates) < 3:
            content_hints = ["content", "body", "text", "article", "post", "main", "entry", "detail"]
            tag_pattern = rf'<{re.escape(target_tag)}\s[^>]*class=["\']([^"\']+)["\']'
            tag_classes = re.findall(tag_pattern, html, re.IGNORECASE)
            for class_attr in tag_classes:
                for cls in class_attr.split():
                    cls_lower = cls.lower()
                    if any(hint in cls_lower for hint in content_hints):
                        sel = f"{target_tag}.{cls}"
                        if sel not in {c for c in candidates}:
                            candidates.append(sel)
                    if len(candidates) >= 3:
                        break
                if len(candidates) >= 3:
                    break

        return candidates[:3]

    async def _auto_repair_selector(self, page, failed_selector: str, context: str = "") -> str | None:
        """Attempt to auto-repair a failed CSS selector by analyzing the page HTML.

        Tries up to 3 candidate selectors derived from similarity analysis.
        On success, caches the mapping in self._selector_repairs and returns the
        working selector. Returns None if no candidate works.
        """
        # Check if we already have a cached repair for this selector
        if failed_selector in self._selector_repairs:
            cached = self._selector_repairs[failed_selector]
            logger.info("Selector repair cache hit: '%s' -> '%s'", failed_selector, cached)
            return cached

        try:
            html = await page.content()
        except Exception as exc:
            logger.warning("Cannot get page HTML for selector repair: %s", exc)
            return None

        if not html:
            logger.warning("Empty page HTML, cannot attempt selector repair.")
            return None

        candidates = self._suggest_selectors(html, failed_selector)
        if not candidates:
            logger.warning(
                "Selector repair: no candidates found for '%s'%s",
                failed_selector,
                f" (context: {context})" if context else "",
            )
            return None

        logger.info(
            "Selector repair: trying %d candidate(s) for '%s': %s",
            len(candidates),
            failed_selector,
            candidates,
        )

        for i, candidate in enumerate(candidates, 1):
            try:
                el = await page.query_selector(candidate)
                if el is not None:
                    self._selector_repairs[failed_selector] = candidate
                    logger.info(
                        "Selector repair SUCCESS [%d/%d]: '%s' -> '%s'%s",
                        i,
                        len(candidates),
                        failed_selector,
                        candidate,
                        f" (context: {context})" if context else "",
                    )
                    return candidate
                else:
                    logger.info(
                        "Selector repair candidate [%d/%d] '%s' returned no element.",
                        i,
                        len(candidates),
                        candidate,
                    )
            except Exception as exc:
                logger.info(
                    "Selector repair candidate [%d/%d] '%s' raised error: %s",
                    i,
                    len(candidates),
                    candidate,
                    exc,
                )

        logger.warning(
            "Selector repair FAILED: all %d candidates exhausted for '%s'%s",
            len(candidates),
            failed_selector,
            f" (context: {context})" if context else "",
        )
        return None

    async def _wait_for_selector_with_repair(
        self, page, selector: str, timeout_ms: int | None = None, context: str = ""
    ):
        """Wait for a selector, attempting auto-repair on timeout.

        Returns the located element on success, or None if both the original
        selector and repair attempts fail.
        """
        if timeout_ms is None:
            timeout_ms = self.selector_timeout_ms

        # Check if we have a known repair for this selector
        effective_selector = self._selector_repairs.get(selector, selector)
        if effective_selector != selector:
            logger.info(
                "Using previously repaired selector: '%s' -> '%s'",
                selector,
                effective_selector,
            )

        try:
            el = await page.wait_for_selector(effective_selector, timeout=timeout_ms)
            return el
        except PlaywrightTimeoutError:
            logger.warning(
                "Selector '%s' timed out after %dms, attempting auto-repair...%s",
                effective_selector,
                timeout_ms,
                f" (context: {context})" if context else "",
            )
            repaired = await self._auto_repair_selector(page, selector, context=context)
            if repaired:
                try:
                    el = await page.wait_for_selector(repaired, timeout=timeout_ms)
                    return el
                except PlaywrightTimeoutError:
                    logger.warning("Repaired selector '%s' also timed out.", repaired)
                    return None
            return None

    async def _clean_ui_for_screenshot(self, page):
        logger.info("Hiding unnecessary UI elements for screenshot...")
        selectors_to_hide = [
            "header",
            "nav",
            "footer",
            ".banner",
            "#gnb",
            ".sticky-banner",
            '[class*="popup"]',
            '[class*="ad-"]',
        ]
        for selector in selectors_to_hide:
            try:
                await page.evaluate(
                    """(sel) => {
                    const elements = document.querySelectorAll(sel);
                    elements.forEach(el => el.style.display = 'none');
                }""",
                    selector,
                )
            except Exception as e:
                logger.debug(f"Could not hide '{selector}': {e}")

    def cleanup_old_screenshots(self):
        """Delete screenshots older than retention_days (0 = disabled)."""
        if self.retention_days <= 0:
            return
        from datetime import timezone, timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).timestamp()
        removed = 0
        for fname in os.listdir(self.screenshot_dir):
            fpath = os.path.join(self.screenshot_dir, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                removed += 1
        if removed:
            logger.info(f"Cleaned up {removed} old screenshot(s) (>{self.retention_days}d).")

    @staticmethod
    def _extract_clean_text(html: str) -> str:
        """trafilatura로 HTML에서 클린 본문 텍스트를 추출.

        trafilatura가 없거나 실패하면 빈 문자열 반환 (기존 셀렉터 파싱으로 폴백).
        """
        try:
            import trafilatura

            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
                favor_precision=True,
            )
            return text.strip() if text else ""
        except Exception:
            return ""

    @staticmethod
    def _suggest_selectors_from_html(html: str) -> list[str]:
        """BeautifulSoup으로 본문 후보 CSS 셀렉터를 자동 추출.

        긴 텍스트 블록을 가진 태그에서 id/class 기반 셀렉터를 제안.
        스크래핑 실패 시 셀렉터 업데이트 힌트로 활용.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            candidates: list[str] = []
            for tag in soup.find_all(["article", "section", "div", "p", "main"]):
                text = tag.get_text(strip=True)
                if len(text) < 100:
                    continue
                tag_id = tag.get("id")
                tag_cls = tag.get("class")
                if tag_id:
                    candidates.append(f"#{tag_id}")
                elif tag_cls:
                    candidates.append(f".{tag_cls[0]}")
            # 중복 제거 후 상위 5개
            seen: set[str] = set()
            unique = [c for c in candidates if c not in seen and not seen.add(c)]  # type: ignore[func-returns-value]
            return unique[:5]
        except Exception:
            return []

    async def _save_failure_snapshot(self, page, url, stage, reason):
        if not self.save_failure_snapshot:
            return
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix = uuid.uuid4().hex[:8]
            base = f"{stamp}_{stage}_{suffix}"
            html_path = os.path.join(self.failure_snapshot_dir, f"{base}.html")
            meta_path = os.path.join(self.failure_snapshot_dir, f"{base}.txt")

            html = ""
            if page:
                try:
                    html = await page.content()
                except Exception:
                    html = ""

            # 셀렉터 자동 제안
            suggested = self._suggest_selectors_from_html(html) if html else []

            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(f"url={url}\n")
                f.write(f"stage={stage}\n")
                f.write(f"reason={reason}\n")
                f.write(f"timestamp={datetime.now().isoformat()}\n")
                if suggested:
                    f.write(f"suggested_selectors={','.join(suggested)}\n")
                    logger.info(
                        "셀렉터 자동 제안 [%s] → %s (스냅샷: %s)",
                        stage,
                        suggested,
                        meta_path,
                    )
            if html:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
        except Exception as snapshot_err:
            logger.debug(f"Could not save failure snapshot: {snapshot_err}")

    # ── Quality assessment ───────────────────────────────────────────
    @staticmethod
    def _korean_ratio(text):
        src = text or ""
        if not src:
            return 0.0
        korean_chars = len(re.findall(r"[가-힣]", src))
        return korean_chars / len(src)

    @staticmethod
    def _digit_ratio(text):
        src = text or ""
        if not src:
            return 0.0
        return len(re.findall(r"\d", src)) / len(src)

    @staticmethod
    def _symbol_ratio(text):
        src = text or ""
        if not src:
            return 0.0
        symbols = len(re.findall(r"[^\w\s가-힣]", src))
        return symbols / len(src)

    def assess_quality(self, post_data):
        title = (post_data.get("title") or "").strip()
        content = (post_data.get("content") or "").strip()
        merged = f"{title}\n{content}".strip()

        metrics = {
            "content_length": len(content),
            "korean_ratio": self._korean_ratio(merged),
            "digit_ratio": self._digit_ratio(merged),
            "symbol_ratio": self._symbol_ratio(merged),
            "empty_field_ratio": (int(not title) + int(not content)) / 2.0,
        }

        score = 100
        reasons = []
        if self.require_title and not title:
            score -= 35
            reasons.append("missing_title")
        if metrics["content_length"] < self.min_content_length:
            score -= 30
            reasons.append("short_content")
        if metrics["korean_ratio"] < self.min_korean_ratio:
            score -= 50
            reasons.append("low_korean_ratio")
        if metrics["symbol_ratio"] > 0.45:
            score -= 8
            reasons.append("symbol_heavy")
        if metrics["digit_ratio"] > 0.50:
            score -= 7
            reasons.append("digit_heavy")
        if metrics["empty_field_ratio"] > self.max_empty_field_ratio:
            score -= 20
            reasons.append("sparse_fields")

        score = max(0, min(100, int(score)))
        return {"score": score, "reasons": reasons, "metrics": metrics}

    # ── Crawl4AI LLM fallback ────────────────────────────────────────
    async def _extract_with_crawl4ai(self, url: str, html: str | None = None) -> dict | None:
        """Fallback extraction using Crawl4AI LLM when CSS selectors fail.

        Tries HTML-based extraction first (faster, no browser), then full crawl.
        Returns post_data dict on success, None on failure.
        """
        extractor = _get_crawl4ai_extractor(self.config)
        if not extractor:
            return None

        logger.info("Attempting Crawl4AI LLM extraction for %s", url)
        result = None

        # Try HTML-based extraction first (no extra browser launch)
        if html:
            result = await extractor.extract_post_from_html(url, html)

        # Fall back to full Crawl4AI crawl
        if not result:
            result = await extractor.extract_post(url)

        if not result or not result.content:
            logger.warning("Crawl4AI extraction returned no content for %s", url)
            return None

        logger.info(
            "Crawl4AI extraction SUCCESS for %s: title='%s' (%d chars)",
            url,
            result.title[:30],
            len(result.content),
        )
        return {
            "url": url,
            "title": result.title,
            "content": result.content,
            "likes": result.likes,
            "comments": result.comments,
            "views": result.views,
            "category": result.category,
            "image_urls": result.image_urls or [],
            "source": getattr(self, "SOURCE_NAME", "unknown"),
            "extraction_method": result.extraction_method,
        }

    # ── Abstract interface ───────────────────────────────────────────
    async def scrape_post(self, url):
        """Scrape a single post. Must be implemented by subclasses."""
        raise NotImplementedError

    async def scrape_post_with_retry(self, url, max_retries=None, backoff=None):
        """High-level wrapper for scrape_post with automatic retries and backoff. (V2.0 Phase 1)"""
        retries = max_retries if max_retries is not None else self.request_retries
        delay = backoff if backoff is not None else self.request_backoff
        last_exc = None

        for attempt in range(1, retries + 1):
            try:
                result = await self.scrape_post(url)
                if result and not result.get("_scrape_error"):
                    return result

                # If it's a parse error (e.g. selector not found), we might want to fail early
                # or try again in case of partial load.
                error_msg = result.get("error_message", "Scrape error")
                logger.warning("Scrape attempt %d/%d failed for %s: %s", attempt, retries, url, error_msg)
                last_exc = Exception(error_msg)
            except Exception as e:
                last_exc = e
                logger.warning("Scrape attempt %d/%d raised exception for %s: %s", attempt, retries, url, e)

            if attempt < retries:
                sleep_time = delay * (2 ** (attempt - 1))  # Exponential backoff
                await asyncio.sleep(sleep_time)

        # All retries failed
        logger.error("Scrape failed after %d attempts for %s", retries, url)
        return {
            "_scrape_error": True,
            "url": url,
            "error_code": "SCRAPE_MAX_RETRIES_EXCEEDED",
            "failure_stage": "post_fetch",
            "failure_reason": "max_retries_exceeded",
            "error_message": f"Failed after {retries} attempts: {str(last_exc)}",
        }

    async def get_feed_urls(self, mode="default", limit=5):
        """Get feed URLs for the given mode. Must be implemented by subclasses."""
        raise NotImplementedError

    async def get_feed_candidates(self, mode="trending", limit=5):
        """Get feed candidates with engagement signals. Override in subclasses."""
        urls = await self.get_feed_urls(mode=mode, limit=limit)
        return [FeedCandidate(url=u, source=getattr(self, "SOURCE_NAME", "unknown")) for u in urls]
