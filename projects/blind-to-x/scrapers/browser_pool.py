"""Browser context pool for blind-to-x scrapers.

Maintains a fixed pool of Playwright browser contexts so N posts can be
scraped concurrently without spinning up separate browser processes.

Usage (managed automatically by BaseScraper):
    pool = BrowserContextPool(config, size=3)
    await pool.open()
    page = await pool.acquire_page()    # blocks if all slots busy
    await page.goto(url)
    await page.close()                  # returns slot to pool automatically
    await pool.close()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from patchright.async_api import async_playwright
except ImportError:
    from playwright.async_api import async_playwright
from playwright_stealth import Stealth  # noqa: E402


class _PooledPage:
    """Transparent proxy for a Playwright page that releases the slot on close()."""

    def __init__(self, page: Any, pool: "BrowserContextPool", ctx: Any):
        self._page = page
        self._pool = pool
        self._ctx = ctx  # the specific context this page belongs to
        self._closed = False

    def __getattr__(self, name: str):
        return getattr(self._page, name)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._page.close()
        except Exception as exc:
            logger.debug("PooledPage.close() page error (ignored): %s", exc)
        finally:
            self._pool._release(self._ctx)

    def __del__(self) -> None:
        if not self._closed:
            logger.warning(
                "_PooledPage.__del__: page was garbage-collected without close(). Context slot may be leaked."
            )


class BrowserContextPool:
    """Pool of N Playwright browser contexts sharing one browser process.

    Each context is an independent browsing session (separate cookies/storage).
    An asyncio.Semaphore limits the number of simultaneous active pages.
    """

    def __init__(self, config, size: int = 3):
        self.config = config
        self.size = max(1, size)
        self._pw = None
        self._browser = None
        self._contexts: list[Any] = []
        self._queue: asyncio.Queue = asyncio.Queue()  # available context slots
        self._sem = asyncio.Semaphore(self.size)
        self._ready = False

    async def open(self) -> None:
        """Start browser and pre-create all context slots."""
        if self._ready:
            return

        headless = self.config.get("headless", True)
        self._pw = await async_playwright().start()
        iphone_14_pro = self._pw.devices["iPhone 14 Pro"]

        from config import ProxyManager

        proxy_mgr = ProxyManager(self.config)
        proxy_url = proxy_mgr.get_random_proxy()
        proxy_config = {"server": proxy_url} if proxy_url else None

        launch_kwargs: dict[str, Any] = {"headless": headless}
        if proxy_config:
            launch_kwargs["proxy"] = proxy_config

        self._browser = await self._pw.chromium.launch(**launch_kwargs)

        for i in range(self.size):
            try:
                ctx = await self._browser.new_context(**iphone_14_pro, locale="ko-KR")
                await Stealth().apply_stealth_async(ctx)
                self._contexts.append(ctx)
                await self._queue.put(ctx)
            except Exception as exc:
                logger.warning("BrowserContextPool: failed to create context slot %d: %s", i, exc)

        self._ready = True
        logger.info(
            "BrowserContextPool opened: %d context slots (requested %d, stealth applied)",
            len(self._contexts),
            self.size,
        )

    async def close(self) -> None:
        """Shut down all contexts and the browser."""
        self._ready = False
        for ctx in self._contexts:
            try:
                await ctx.close()
            except Exception as exc:
                logger.debug("BrowserContextPool: context close error (ignored): %s", exc)
        self._contexts.clear()
        # Drain the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        if self._browser:
            try:
                await self._browser.close()
            except Exception as exc:
                logger.debug("BrowserContextPool: browser close error (ignored): %s", exc)
            self._browser = None

        if self._pw:
            try:
                await self._pw.stop()
            except Exception as exc:
                logger.debug("BrowserContextPool: playwright stop error (ignored): %s", exc)
            self._pw = None

        logger.info("BrowserContextPool closed.")

    def _release(self, ctx: Any) -> None:
        """Return a specific context slot to the pool (called by _PooledPage.close()).

        Args:
            ctx: The specific browser context to return. Must not be None.
        """
        if ctx is None:
            logger.error(
                "BrowserContextPool._release called with ctx=None — "
                "slot will NOT be returned to avoid pool corruption. "
                "Expected queue size: %d, actual: %d",
                self.size - 1,  # one slot is in-use by the caller
                self._queue.qsize(),
            )
            return
        try:
            self._queue.put_nowait(ctx)
        except asyncio.QueueFull:
            logger.error(
                "BrowserContextPool._release: queue full (size=%d) — "
                "duplicate release detected, context dropped to prevent corruption",
                self._queue.qsize(),
            )

    async def acquire_page(self) -> _PooledPage:
        """Block until a context slot is available, then return a new page.

        The returned page transparently proxies all Playwright page methods.
        Calling page.close() returns the correct context slot to the pool automatically.
        """
        if not self._ready:
            raise RuntimeError("BrowserContextPool.open() must be called first")

        ctx = await self._queue.get()  # blocks until slot available
        try:
            page = await ctx.new_page()
            # Stealth is already applied at context level in open()
        except Exception as exc:
            # Return the correct context slot even if page creation failed
            self._queue.put_nowait(ctx)
            raise RuntimeError(f"BrowserContextPool: failed to create page: {exc}") from exc

        return _PooledPage(page, self, ctx=ctx)
