import pytest
from unittest.mock import AsyncMock, patch
from scrapers.base import BrowserUnavailableError
from scrapers.blind import BlindScraper


@pytest.fixture
def mock_config():
    return {
        "headless": True,
        "screenshot_dir": "./mock_screenshots",
        "scrape_quality.save_failure_snapshot": False,
        "blind.email": "test@test.com",
        "blind.password": "password123",
    }


@pytest.fixture
def scraper(mock_config):
    return BlindScraper(mock_config)


def test_extract_count():
    assert BlindScraper._extract_count("좋아요 1,234 댓글 56", ["좋아요"]) == 1234
    assert BlindScraper._extract_count("조회 100", ["좋아요"]) == 0
    assert BlindScraper._extract_count(None, ["좋아요"]) == 0


def test_determine_category(scraper):
    assert scraper._determine_category("소개팅 남친", "고민입니다") == "relationship"
    assert scraper._determine_category("주식 투자 가이드", "떡상") == "money"
    assert scraper._determine_category("이직", "이력서") == "career"


@pytest.mark.asyncio
async def test_login_success(scraper):
    page_mock = AsyncMock()
    # pretend goto and wait_for_selector pass

    success = await scraper._login(page_mock)
    assert success is True
    page_mock.goto.assert_called_with("https://www.teamblind.com/kr/login")
    page_mock.fill.assert_any_call('input[type="email"]', "test@test.com")
    page_mock.fill.assert_any_call('input[type="password"]', "password123")
    page_mock.click.assert_called_with('button[type="submit"]')


@pytest.mark.asyncio
async def test_login_skip(mock_config):
    # If no credentials
    config_no_auth = mock_config.copy()
    config_no_auth["blind.email"] = ""
    scraper = BlindScraper(config_no_auth)

    page_mock = AsyncMock()
    success = await scraper._login(page_mock)
    assert success is True
    page_mock.goto.assert_not_called()


@pytest.mark.asyncio
@patch("scrapers.blind.BlindScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_fetch_post_urls(mock_fetch, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    el_mock = AsyncMock()
    el_mock.get_attribute.return_value = "/kr/topic/123"
    page_mock.query_selector_all.return_value = [el_mock]

    scraper._new_page = AsyncMock(return_value=page_mock)
    scraper._login = AsyncMock()

    urls = await scraper._fetch_post_urls("http://dummy", limit=1)

    assert len(urls) == 1
    assert urls[0] == "https://www.teamblind.com/kr/topic/123"
    scraper._login.assert_called_once_with(page_mock)


@pytest.mark.asyncio
@patch("scrapers.blind.BlindScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_get_feed_candidates(mock_fetch, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    row_mock = AsyncMock()
    link_mock = AsyncMock()
    link_mock.get_attribute.return_value = "/kr/topic/123"
    link_mock.inner_text.return_value = "블라인드글"
    row_mock.query_selector.side_effect = lambda sel: link_mock if "a" in sel else None

    page_mock.query_selector_all.return_value = [row_mock]

    scraper._new_page = AsyncMock(return_value=page_mock)
    scraper._login = AsyncMock()

    candidates = await scraper.get_feed_candidates(mode="popular", limit=1)

    assert len(candidates) == 1
    assert candidates[0].url == "https://www.teamblind.com/kr/topic/123"
    assert candidates[0].title == "블라인드글"


@pytest.mark.asyncio
@patch("scrapers.blind.os.makedirs")
@patch("scrapers.blind.BlindScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_scrape_post_success(mock_fetch, mock_mkdir, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    main_container_mock = AsyncMock()
    page_mock.query_selector.return_value = main_container_mock

    title_el = AsyncMock()
    title_el.inner_text.return_value = "이직 면접 연봉 협상 어떻게 하나요"

    content_el = AsyncMock()
    content_el.inner_text.return_value = "이직 면접에서 연봉 협상할 때 꿀팁 좀요. 자세히 알려주세요."

    def side_effect(sel):
        if "h2" in sel or "h1" in sel:
            return title_el
        return content_el

    main_container_mock.query_selector.side_effect = side_effect

    like_el = AsyncMock()
    like_el.inner_text.return_value = "10"
    page_mock.query_selector.side_effect = lambda sel: like_el if ".wrap-info " in sel else main_container_mock

    scraper._new_page = AsyncMock(return_value=page_mock)

    main_container_mock.screenshot = AsyncMock()

    result = await scraper.scrape_post("https://www.teamblind.com/kr/topic/111")

    assert result.get("_scrape_error") is None
    assert result["title"] == "이직 면접 연봉 협상 어떻게 하나요"
    assert "이직 면접에서 연봉 협상할 때 꿀팁" in result["content"]
    assert result["category"] == "career"
    assert "screenshot_path" in result


@pytest.mark.asyncio
@patch("scrapers.blind.os.makedirs")
@patch("scrapers.blind.BlindScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_scrape_post_insufficient_length(mock_fetch, mock_mkdir, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    main_container_mock = AsyncMock()
    page_mock.query_selector.return_value = main_container_mock

    title_el = AsyncMock()
    title_el.inner_text.return_value = "짧은 글"

    content_el = AsyncMock()
    content_el.inner_text.return_value = "ㅋㅋ"

    def side_effect(sel):
        if "h2" in sel or "h1" in sel:
            return title_el
        return content_el

    main_container_mock.query_selector.side_effect = side_effect
    scraper._new_page = AsyncMock(return_value=page_mock)

    result = await scraper.scrape_post("https://www.teamblind.com/kr/topic/111")

    assert result.get("_scrape_error") is True
    assert result["failure_reason"] == "insufficient_content_length"


@pytest.mark.asyncio
async def test_fetch_post_urls_browser_unavailable_uses_html_only_fallback(scraper):
    scraper._new_page = AsyncMock(side_effect=BrowserUnavailableError("browser missing"))
    scraper._fetch_html_via_session = AsyncMock(
        return_value="""
        <html>
          <body>
            <a href="/kr/post/test-a-123">첫 번째 글</a>
            <a href="/kr/post/test-b-456">두 번째 글</a>
          </body>
        </html>
        """
    )

    urls = await scraper._fetch_post_urls("https://www.teamblind.com/kr/topics/trending", limit=2)

    assert urls == [
        "https://www.teamblind.com/kr/post/test-a-123",
        "https://www.teamblind.com/kr/post/test-b-456",
    ]


@pytest.mark.asyncio
async def test_scrape_post_browser_unavailable_uses_html_only_fallback(scraper):
    scraper._new_page = AsyncMock(side_effect=BrowserUnavailableError("browser missing"))
    scraper._fetch_html_via_session = AsyncMock(
        return_value="""
        <html>
          <head>
            <meta property="og:title" content="연봉 협상 팁" />
          </head>
          <body>
            <article>
              <h1>연봉 협상 팁</h1>
              <p>이직 직전에 꼭 체크해야 할 연봉 협상 포인트를 정리했습니다.</p>
            </article>
          </body>
        </html>
        """
    )
    scraper._extract_with_crawl4ai = AsyncMock(return_value=None)
    scraper._extract_clean_text = lambda _html: "이직 직전에 꼭 체크해야 할 연봉 협상 포인트를 정리했습니다."

    result = await scraper.scrape_post("https://www.teamblind.com/kr/post/test-a-123")

    assert result.get("_scrape_error") is None
    assert result["title"] == "연봉 협상 팁"
    assert "연봉 협상 포인트" in result["content"]
    assert result["screenshot_path"] is None
