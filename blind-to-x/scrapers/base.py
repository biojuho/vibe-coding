"""Base scraper with shared browser lifecycle, screenshot, and quality logic."""

import asyncio
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
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
        self._pw = None
        self._browser = None
        self._context = None

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
            await self._pool.open()
            logger.info("Browser opened (pool mode, size=%d).", self._pool_size)
            return

        # Single-context mode (original behaviour)
        if self._browser:
            return
        self._pw = await async_playwright().start()
        iphone_14_pro = self._pw.devices["iPhone 14 Pro"]

        proxy_url = self.proxy_manager.get_random_proxy()
        proxy_config = {"server": proxy_url} if proxy_url else None

        launch_kwargs = {"headless": self.headless}
        if proxy_config:
            launch_kwargs["proxy"] = proxy_config
            logger.info("Playwright launching with proxy.")

        self._browser = await self._pw.chromium.launch(**launch_kwargs)
        self._context = await self._browser.new_context(**iphone_14_pro, locale="ko-KR")
        await Stealth().apply_stealth_async(self._context)
        logger.info("Browser opened (shared instance, stealth applied to context).")

    async def close(self):
        """Shut down the shared browser and context (or pool)."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
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
        logger.warning("_new_page called before open(). Opening shared browser now.")
        await self.open()
        if self._pool is not None:
            return await self._pool.acquire_page()
        page = await self._context.new_page()
        return page

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
                    html = re.sub(r'<script[^>]+src=[^>]+></script>', '', response.text, flags=re.DOTALL)
                    return html
            except Exception as e:
                last_error = e
                if attempt < self.request_retries:
                    sleep_for = self.request_backoff * attempt
                    logger.warning(
                        f"Fetch failed ({attempt}/{self.request_retries}) for {url}: {e}. "
                        f"Retrying in {sleep_for:.1f}s."
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

    async def _clean_ui_for_screenshot(self, page):
        logger.info("Hiding unnecessary UI elements for screenshot...")
        selectors_to_hide = [
            'header', 'nav', 'footer', '.banner', '#gnb',
            '.sticky-banner', '[class*="popup"]', '[class*="ad-"]',
        ]
        for selector in selectors_to_hide:
            try:
                await page.evaluate('''(sel) => {
                    const elements = document.querySelectorAll(sel);
                    elements.forEach(el => el.style.display = 'none');
                }''', selector)
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
                        stage, suggested, meta_path,
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

    # ── Abstract interface ───────────────────────────────────────────
    async def scrape_post(self, url):
        """Scrape a single post. Must be implemented by subclasses."""
        raise NotImplementedError

    async def get_feed_urls(self, mode="default", limit=5):
        """Get feed URLs for the given mode. Must be implemented by subclasses."""
        raise NotImplementedError

    async def get_feed_candidates(self, mode="trending", limit=5):
        """Get feed candidates with engagement signals. Override in subclasses."""
        urls = await self.get_feed_urls(mode=mode, limit=limit)
        return [FeedCandidate(url=u, source=getattr(self, "SOURCE_NAME", "unknown")) for u in urls]
