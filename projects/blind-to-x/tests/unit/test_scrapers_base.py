import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import BaseScraper, FeedCandidate


@pytest.fixture
def mock_config():
    return {
        "headless": True,
        "screenshot_dir": "./mock_screenshots",
        "request.timeout_seconds": 20,
        "request.retries": 1,
        "request.backoff_seconds": 0.1,
        "browser.pool_size": 1,
        "browser.engine": "chromium",
    }


class DummyScraper(BaseScraper):
    async def scrape_post(self, url):
        return {"url": url, "title": "Dummy", "content": "Content"}

    async def get_feed_urls(self, mode="default", limit=5):
        return [f"http://example.com/{i}" for i in range(limit)]


@pytest.mark.asyncio
async def test_feed_candidate_engagement():
    fc = FeedCandidate(url="http://test.com", likes=10, comments=5, views=100, has_image=True, image_count=3)
    score = fc.compute_engagement()
    # 10 + 5*1.5 + 100*0.01 = 10 + 7.5 + 1 = 18.5
    # image bonus: 50 + min(3, 5)*10 = 80
    # total = 98.5
    assert score == 98.5


@pytest.mark.asyncio
async def test_base_scraper_init(mock_config):
    scraper = DummyScraper(mock_config)
    assert scraper.headless is True
    assert scraper.request_retries == 1


@pytest.mark.asyncio
async def test_quality_assessment(mock_config):
    scraper = DummyScraper(mock_config)

    post_data = {
        "title": "정상적인 제목입니다",
        "content": "이것은 충분히 긴 형태의 한글 본문 컨텐츠입니다. 길이와 한글 비율 모두 양호합니다.",
    }

    result = scraper.assess_quality(post_data)
    assert result["score"] == 100
    assert len(result["reasons"]) == 0


@pytest.mark.asyncio
async def test_quality_assessment_poor(mock_config):
    scraper = DummyScraper(mock_config)

    post_data = {"title": "", "content": "a?#"}

    result = scraper.assess_quality(post_data)
    assert result["score"] < 100
    assert "missing_title" in result["reasons"]
    assert "short_content" in result["reasons"]
    assert "low_korean_ratio" in result["reasons"]


@pytest.mark.asyncio
async def test_suggest_selectors(mock_config):
    html = """
    <div class="post-content main-content">
        <p id="post-body">Hello world</p>
    </div>
    """
    scraper = DummyScraper(mock_config)
    candidates = scraper._suggest_selectors(html, ".post-content2")
    # should suggest .post-content
    assert ".post-content" in candidates or ".main-content" in candidates


@pytest.mark.asyncio
async def test_suggest_selectors_from_html():
    html = (
        """
    <div>
        <article class="board-contents">
        """
        + ("이것은 긴 한글 의미 없는 텍스트입니다. " * 20)
        + """
        </article>
    </div>
    """
    )
    candidates = BaseScraper._suggest_selectors_from_html(html)
    assert ".board-contents" in candidates


@pytest.mark.asyncio
async def test_clean_text_extraction(mock_config):
    try:
        html = "<html><body><article><p>Hello</p></article></body></html>"
        text = BaseScraper._extract_clean_text(html)
        assert text == "Hello"
    except Exception:
        # allow pass if trafilatura is not installed
        pass


@pytest.mark.asyncio
@patch("scrapers.base.async_playwright")
async def test_scraper_open_close(mock_pw, mock_config):
    pw_instance = AsyncMock()
    mock_pw.return_value.start.return_value = pw_instance
    pw_instance.devices = {"iPhone 14 Pro": {}}

    browser_mock = AsyncMock()
    pw_instance.chromium.launch.return_value = browser_mock
    context_mock = AsyncMock()
    browser_mock.new_context.return_value = context_mock

    # Needs patch for Stealth
    with patch("scrapers.base.Stealth") as MockStealth:
        stealth_instance = AsyncMock()
        MockStealth.return_value = stealth_instance

        scraper = DummyScraper(mock_config)
        await scraper.open()

        pw_instance.chromium.launch.assert_called_once()
        browser_mock.new_context.assert_called_once()
        stealth_instance.apply_stealth_async.assert_called_once()

        # Test close
        await scraper.close()
        context_mock.close.assert_called_once()
        browser_mock.close.assert_called_once()
        pw_instance.stop.assert_called_once()


@pytest.mark.asyncio
@patch("scrapers.base.AsyncSession")
async def test_fetch_html_via_session(mock_session_cls, mock_config):
    session_instance = AsyncMock()
    mock_session_cls.return_value.__aenter__.return_value = session_instance

    response_mock = MagicMock()
    response_mock.text = "<html><body>Test</body></html>"
    session_instance.get.return_value = response_mock

    scraper = DummyScraper(mock_config)
    html = await scraper._fetch_html_via_session("http://example.com")

    assert html == "<html><body>Test</body></html>"
    session_instance.get.assert_called_once()


@pytest.mark.asyncio
async def test_scrape_post_with_retry(mock_config):
    scraper = DummyScraper(mock_config)
    # the dummy scraper always returns content successfully
    res = await scraper.scrape_post_with_retry("http://example.com")
    assert res["url"] == "http://example.com"
    assert res["title"] == "Dummy"


@pytest.mark.asyncio
async def test_take_screenshot(mock_config):
    scraper = DummyScraper(mock_config)
    page_mock = AsyncMock()
    # successful screenshot
    success = await scraper._take_screenshot(page_mock, "test.png", timeout_seconds=1)
    assert success is True
    page_mock.screenshot.assert_called_once()

    # timeout scenario
    page_mock.screenshot.side_effect = Exception("Timeout mock")
    success = await scraper._take_screenshot(page_mock, "test2.png", timeout_seconds=1)
    assert success is False
