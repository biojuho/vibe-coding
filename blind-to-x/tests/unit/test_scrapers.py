"""Phase 3-A: 스크래퍼 및 브라우저 풀 테스트.

커버리지 대상:
  - scrapers/base.py  (BaseScraper: quality assess, screenshot helper, HTML suggest)
  - scrapers/browser_pool.py (BrowserContextPool: context release, pool lifecycle)
  - scrapers/dedup 로직 (URL scheme validation, Jaccard)
  - pipeline/dedup.py (cross_source dedup)
  - pipeline/image_generator.py (fallback chain)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── 경로 추가 ───────────────────────────────────────────────────────────
_BTX_ROOT = Path(__file__).resolve().parent.parent
if str(_BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(_BTX_ROOT))


# ════════════════════════════════════════════════════════════════════════
# BaseScraper 단위 테스트
# ════════════════════════════════════════════════════════════════════════

class _FakeConfig:
    """ConfigManager 최소 mock."""
    def get(self, key, default=None):
        defaults = {
            "headless": True,
            "screenshot_dir": "/tmp/screenshots",
            "request.timeout_seconds": "10",
            "request.retries": "1",
            "request.backoff_seconds": "0.1",
            "screenshot_retention_days": "0",
            "scrape_quality.min_content_length": "20",
            "scrape_quality.min_korean_ratio": "0.15",
            "scrape_quality.require_title": True,
            "scrape_quality.max_empty_field_ratio": "0.4",
            "scrape_quality.selector_timeout_ms": "5000",
            "scrape_quality.direct_fallback_timeout_ms": "8000",
            "scrape_quality.save_failure_snapshot": False,
            "scrape_quality.failure_snapshot_dir": "/tmp/failures",
            "browser.pool_size": "1",
            "proxy.enabled": False,
            "proxy.list": [],
        }
        return defaults.get(key, default)


def _make_scraper():
    """ProxyManager를 mock하여 BaseScraper 생성."""
    with patch("scrapers.base.ProxyManager") as MockPM:
        MockPM.return_value.get_random_proxy.return_value = None
        from scrapers.base import BaseScraper
        return BaseScraper(_FakeConfig())


# ── assess_quality ────────────────────────────────────────────────────

class TestAssessQuality:
    def test_good_korean_post(self):
        scraper = _make_scraper()
        post = {"title": "연봉 올리는 법", "content": "저도 이직을 고민하고 있는 직장인입니다 연봉이 너무 낮아서요"}
        result = scraper.assess_quality(post)
        assert result["score"] > 50
        assert not result["reasons"]

    def test_missing_title_penalty(self):
        scraper = _make_scraper()
        post = {"title": "", "content": "직장인 이야기입니다 연봉 이직 회사문화 관련 내용입니다"}
        result = scraper.assess_quality(post)
        assert "missing_title" in result["reasons"]
        assert result["score"] < 70

    def test_short_content_penalty(self):
        scraper = _make_scraper()
        post = {"title": "짧은글", "content": "짧음"}
        result = scraper.assess_quality(post)
        assert "short_content" in result["reasons"]

    def test_non_korean_penalty(self):
        scraper = _make_scraper()
        post = {"title": "English Title Only", "content": "This is all english content without korean"}
        result = scraper.assess_quality(post)
        assert "low_korean_ratio" in result["reasons"]
        assert result["score"] < 60

    def test_score_clamped_to_100(self):
        scraper = _make_scraper()
        post = {"title": "완벽한 직장인 게시글", "content": "연봉 이직 회사문화 복지 상사 이야기 직장인이라면 공감할 내용들 많이 있습니다 정말로요"}
        result = scraper.assess_quality(post)
        assert 0 <= result["score"] <= 100

    def test_score_clamped_to_zero(self):
        scraper = _make_scraper()
        post = {"title": "", "content": "hi"}
        result = scraper.assess_quality(post)
        assert result["score"] >= 0


# ── _take_screenshot ──────────────────────────────────────────────────

class TestTakeScreenshot:
    @pytest.mark.asyncio
    async def test_success(self, tmp_path):
        scraper = _make_scraper()
        fake_page = AsyncMock()
        path = str(tmp_path / "shot.png")
        result = await scraper._take_screenshot(fake_page, path, timeout_seconds=5)
        assert result is True
        fake_page.screenshot.assert_awaited_once_with(path=path, full_page=False)

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, tmp_path):
        scraper = _make_scraper()
        path = str(tmp_path / "shot.png")

        async def slow_screenshot(**kwargs):
            await asyncio.sleep(10)

        fake_page = AsyncMock()
        fake_page.screenshot = slow_screenshot
        result = await scraper._take_screenshot(fake_page, path, timeout_seconds=0.01)
        assert result is False

    @pytest.mark.asyncio
    async def test_exception_returns_false(self, tmp_path):
        scraper = _make_scraper()
        path = str(tmp_path / "shot.png")
        fake_page = AsyncMock()
        fake_page.screenshot.side_effect = RuntimeError("page crash")
        result = await scraper._take_screenshot(fake_page, path, timeout_seconds=5)
        assert result is False


# ── _suggest_selectors_from_html ──────────────────────────────────────

class TestSuggestSelectors:
    def test_finds_id_selector(self):
        from scrapers.base import BaseScraper
        html = '<div id="main-content"><p>' + "직장인 이야기입니다. " * 10 + "</p></div>"
        result = BaseScraper._suggest_selectors_from_html(html)
        assert "#main-content" in result

    def test_finds_class_selector(self):
        from scrapers.base import BaseScraper
        html = '<article class="post-body"><p>' + "연봉 이야기입니다. " * 10 + "</p></article>"
        result = BaseScraper._suggest_selectors_from_html(html)
        assert ".post-body" in result

    def test_returns_empty_on_bad_html(self):
        from scrapers.base import BaseScraper
        result = BaseScraper._suggest_selectors_from_html("")
        assert isinstance(result, list)

    def test_limits_to_5(self):
        from scrapers.base import BaseScraper
        sections = "".join(
            f'<div id="sec{i}"><p>' + "한글 텍스트입니다. " * 20 + "</p></div>"
            for i in range(10)
        )
        result = BaseScraper._suggest_selectors_from_html(sections)
        assert len(result) <= 5


# ════════════════════════════════════════════════════════════════════════
# BrowserContextPool 단위 테스트
# ════════════════════════════════════════════════════════════════════════

class TestBrowserContextPool:
    @pytest.mark.asyncio
    async def test_release_puts_correct_context(self):
        """_release(ctx) 가 올바른 컨텍스트를 큐에 반납하는지 검증."""
        from scrapers.browser_pool import BrowserContextPool

        pool = BrowserContextPool.__new__(BrowserContextPool)
        pool.size = 2
        pool._queue = asyncio.Queue()
        pool._contexts = [MagicMock(name="ctx_A"), MagicMock(name="ctx_B")]
        pool._ready = True

        ctx_a, ctx_b = pool._contexts

        # ctx_B를 반납
        pool._release(ctx_b)
        returned = pool._queue.get_nowait()
        assert returned is ctx_b

    @pytest.mark.asyncio
    async def test_release_fallback_when_ctx_none(self):
        """ctx=None일 때 contexts[0] 을 반납 (폴백 동작)."""
        from scrapers.browser_pool import BrowserContextPool

        pool = BrowserContextPool.__new__(BrowserContextPool)
        pool.size = 1
        pool._queue = asyncio.Queue()
        pool._contexts = [MagicMock(name="ctx_X")]
        pool._ready = True

        pool._release(None)
        returned = pool._queue.get_nowait()
        assert returned is pool._contexts[0]

    @pytest.mark.asyncio
    async def test_acquire_page_returns_pooled_page_with_ctx(self):
        """acquire_page()가 올바른 ctx를 가진 _PooledPage를 반환하는지 검증."""
        from scrapers.browser_pool import BrowserContextPool, _PooledPage

        ctx_mock = AsyncMock()
        page_mock = AsyncMock()
        ctx_mock.new_page = AsyncMock(return_value=page_mock)

        pool = BrowserContextPool.__new__(BrowserContextPool)
        pool.size = 1
        pool._queue = asyncio.Queue()
        await pool._queue.put(ctx_mock)
        pool._contexts = [ctx_mock]
        pool._ready = True

        page = await pool.acquire_page()
        assert isinstance(page, _PooledPage)
        assert page._ctx is ctx_mock
        assert page._page is page_mock

    @pytest.mark.asyncio
    async def test_close_returns_context_to_queue(self):
        """_PooledPage.close() 가 ctx를 풀 큐에 반납하는지 검증."""
        from scrapers.browser_pool import BrowserContextPool, _PooledPage

        ctx_mock = AsyncMock()
        page_mock = AsyncMock()
        ctx_mock.new_page = AsyncMock(return_value=page_mock)

        pool = BrowserContextPool.__new__(BrowserContextPool)
        pool.size = 1
        pool._queue = asyncio.Queue()
        await pool._queue.put(ctx_mock)
        pool._contexts = [ctx_mock]
        pool._ready = True

        page = await pool.acquire_page()
        assert pool._queue.empty()  # ctx가 꺼내진 상태

        await page.close()
        assert not pool._queue.empty()  # close 후 반납되어야 함
        returned = pool._queue.get_nowait()
        assert returned is ctx_mock


# ════════════════════════════════════════════════════════════════════════
# URL validation (scheme 체크)
# ════════════════════════════════════════════════════════════════════════

class TestUrlSchemeValidation:
    def test_valid_http_url(self):
        from pipeline.notion_upload import NotionUploader
        result = NotionUploader.canonicalize_url("http://teamblind.com/post/test-123")
        assert result.startswith("https://")

    def test_valid_https_url(self):
        from pipeline.notion_upload import NotionUploader
        result = NotionUploader.canonicalize_url("https://teamblind.com/post/test-456")
        assert result.startswith("https://")

    def test_no_scheme_gets_https_prefix(self):
        from pipeline.notion_upload import NotionUploader
        result = NotionUploader.canonicalize_url("teamblind.com/post/nill")
        assert result.startswith("https://")

    def test_empty_url_returns_empty(self):
        from pipeline.notion_upload import NotionUploader
        result = NotionUploader.canonicalize_url("")
        assert result == ""

    def test_utm_params_stripped(self):
        from pipeline.notion_upload import NotionUploader
        result = NotionUploader.canonicalize_url(
            "https://teamblind.com/post/abc?utm_source=twitter&utm_medium=social"
        )
        assert "utm_" not in result

    def test_trailing_slash_removed(self):
        from pipeline.notion_upload import NotionUploader
        result = NotionUploader.canonicalize_url("https://teamblind.com/post/abc/")
        assert not result.endswith("/")


# ════════════════════════════════════════════════════════════════════════
# image_generator.py 폴백 체인 테스트
# ════════════════════════════════════════════════════════════════════════

class TestImageGeneratorFallback:
    def _make_generator(self, config_overrides=None):
        cfg = {
            "image.provider": "gemini",
            "image.fallback_to_dalle": False,
            "gemini.api_key": "fake-gemini-key",
            "openai.api_key": "",
            "cloudinary.cloud_name": "",
            "cloudinary.api_key": "",
            "cloudinary.api_secret": "",
        }
        if config_overrides:
            cfg.update(config_overrides)

        class _Cfg:
            def get(self, key, default=None):
                return cfg.get(key, default)

        mock_cache = MagicMock()
        mock_cache.return_value.get.return_value = None  # cache miss
        with patch("pipeline.image_cache.ImageCache", mock_cache):
            from pipeline.image_generator import ImageGenerator
            return ImageGenerator(_Cfg())

    @pytest.mark.asyncio
    async def test_gemini_success(self):
        gen = self._make_generator()
        mock_cache = MagicMock()
        mock_cache.return_value.get.return_value = None  # cache miss
        with (
            patch("pipeline.image_cache.ImageCache", mock_cache),
            patch.object(gen, "_generate_gemini", new_callable=AsyncMock) as mock_g,
        ):
            mock_g.return_value = "/tmp/image.png"
            result = await gen.generate_image("A frustrated office worker sitting alone at a desk", topic_cluster="연봉", emotion_axis="분노")
            assert result == "/tmp/image.png"
            mock_g.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_gemini_none_falls_back_to_pollinations(self):
        """_generate_gemini returning None triggers Pollinations fallback."""
        gen = self._make_generator()
        mock_cache = MagicMock()
        mock_cache.return_value.get.return_value = None
        with (
            patch("pipeline.image_cache.ImageCache", mock_cache),
            patch.object(gen, "_generate_gemini", new_callable=AsyncMock, return_value=None),
            patch.object(gen, "_generate_pollinations", new_callable=AsyncMock) as mock_p,
        ):
            mock_p.return_value = "https://pollinations.ai/img/test.png"
            result = await gen.generate_image("A person contemplating career change in modern office", topic_cluster="이직", emotion_axis="허탈")
            assert result == "https://pollinations.ai/img/test.png"

    @pytest.mark.asyncio
    async def test_both_free_none_returns_none_when_dalle_disabled(self):
        """Both Gemini and Pollinations returning None yields None when DALL-E disabled."""
        gen = self._make_generator()
        mock_cache = MagicMock()
        mock_cache.return_value.get.return_value = None
        with (
            patch("pipeline.image_cache.ImageCache", mock_cache),
            patch.object(gen, "_generate_gemini", new_callable=AsyncMock, return_value=None),
            patch.object(gen, "_generate_pollinations", new_callable=AsyncMock, return_value=None),
        ):
            result = await gen.generate_image("Corporate team culture meeting with coworkers discussing issues", topic_cluster="회사문화", emotion_axis="공감")
            assert result is None


# ════════════════════════════════════════════════════════════════════════
# BrowserContextPool Circuit Breaker / 재진입 테스트
# ════════════════════════════════════════════════════════════════════════

class TestPoolCircuitBreaker:
    @pytest.mark.asyncio
    async def test_pool_full_queue_on_release_ignored(self):
        """큐가 꽉 찼을 때 _release 가 예외를 던지지 않는지 확인."""
        from scrapers.browser_pool import BrowserContextPool

        pool = BrowserContextPool.__new__(BrowserContextPool)
        pool.size = 1
        pool._queue = asyncio.Queue(maxsize=1)
        ctx = MagicMock()
        pool._contexts = [ctx]
        pool._ready = True

        # 큐를 이미 꽉 채움
        pool._queue.put_nowait(ctx)
        # 추가 반납 — QueueFull 이 무음 처리되어야 함
        pool._release(ctx)  # should not raise
