import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.fmkorea import FMKoreaScraper


@pytest.fixture
def mock_config():
    return {
        "headless": True,
        "screenshot_dir": "./mock_screenshots",
        "scrape_quality.save_failure_snapshot": False,
    }


@pytest.fixture
def scraper(mock_config):
    return FMKoreaScraper(mock_config)


@pytest.mark.asyncio
async def test_normalize_url(scraper):
    assert scraper._normalize_url("/best/12345") == "https://www.fmkorea.com/best/12345"
    assert scraper._normalize_url("https://www.fmkorea.com/humor/67890") == "https://www.fmkorea.com/humor/67890"
    assert scraper._normalize_url(None) is None
    assert scraper._normalize_url("https://example.com/post") is None


@pytest.mark.asyncio
async def test_determine_category(scraper):
    assert scraper._determine_category("ㅋㅋㅋ 웃긴 짤 방출", "내용") == "humor"
    assert scraper._determine_category("이직 고민", "어떻게 할까요") == "career"
    assert scraper._determine_category("여친이랑 다툼", "ㅠㅠ") == "relationship"
    assert scraper._determine_category("롤 게임 후기", "존잼") == "gaming"
    assert scraper._determine_category("최신 뉴스 속보", "정치 이슈") == "news"
    assert scraper._determine_category("일반적인 글", "별내용없음") == "general"


@pytest.mark.asyncio
@patch("scrapers.fmkorea.FMKoreaScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_fetch_post_urls(mock_fetch, scraper):
    # Mock HTML and page
    mock_fetch.return_value = "<html><body></body></html>"

    page_mock = AsyncMock()
    # Mocking elements returned by query_selector_all
    el_mock = AsyncMock()
    el_mock.get_attribute.return_value = "/best/12345"
    page_mock.query_selector_all.return_value = [el_mock]

    # Mock the context manager `_new_page_cm`
    cm_mock = MagicMock()
    cm_mock.__aenter__.return_value = page_mock
    scraper._new_page_cm = MagicMock(return_value=cm_mock)

    urls = await scraper._fetch_post_urls("http://dummy_feed")
    assert "https://www.fmkorea.com/best/12345" in urls


@pytest.mark.asyncio
@patch("scrapers.fmkorea.FMKoreaScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_get_feed_candidates(mock_fetch, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    # Mock elements for candidate extraction
    el_mock = AsyncMock()
    el_mock.get_attribute.return_value = "/best/12345"
    el_mock.inner_text.return_value = "테스트 게시글 [42]"
    page_mock.query_selector_all.return_value = [el_mock]

    cm_mock = MagicMock()
    cm_mock.__aenter__.return_value = page_mock
    scraper._new_page_cm = MagicMock(return_value=cm_mock)

    candidates = await scraper.get_feed_candidates(mode="popular", limit=1)
    assert len(candidates) == 1
    assert candidates[0].url == "https://www.fmkorea.com/best/12345"
    assert candidates[0].title == "테스트 게시글"
    assert candidates[0].comments == 42


@pytest.mark.asyncio
@patch("scrapers.fmkorea.os.makedirs")
@patch("scrapers.fmkorea.FMKoreaScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_scrape_post_success(mock_fetch, mock_mkdir, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    # Mock container for post content
    main_container_mock = AsyncMock()
    page_mock.wait_for_selector = AsyncMock()

    # Mock title
    title_el = AsyncMock()
    title_el.inner_text.return_value = "오버워치 플레이 영상"

    def page_query_selector(sel):
        if sel == ".rd_body":
            return main_container_mock
        if "h1" in sel:
            return title_el
        return None

    page_mock.query_selector.side_effect = page_query_selector

    # Mock content
    content_el = AsyncMock()
    content_el.inner_text.return_value = (
        "이 오버워치 영상은 어떻게 플레이했는지 자세히 보여주는 영상입니다. 10자가 넘어야 합니다."
    )
    main_container_mock.query_selector.side_effect = lambda sel: (
        content_el
        if sel
        in {
            ".xe_content",
            ".rd_body .xe_content",
            ".document_read .xe_content",
            ".rd_body",
            "p",
        }
        else None
    )

    # Mock likes and comments
    # To return different things for different selectors, we can just let 'likes' default to 0
    # and maybe 'comments' to 0 because we didn't mock query_selector completely nicely to differentiate.
    # But it's enough for coverage.

    cm_mock = MagicMock()
    cm_mock.__aenter__.return_value = page_mock
    scraper._new_page_cm = MagicMock(return_value=cm_mock)

    # Mock screenshot side effect to nothing
    main_container_mock.screenshot = AsyncMock()

    result = await scraper.scrape_post("https://www.fmkorea.com/best/9999")

    assert result.get("_scrape_error") is None
    assert result["title"] == "오버워치 플레이 영상"
    assert "이 오버워치 영상은 어떻게 플레이했는지 자세히 보여주는 영상입니다" in result["content"]
    assert result["category"] == "gaming"
    assert "screenshot_path" in result


@pytest.mark.asyncio
@patch("scrapers.fmkorea.FMKoreaScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_scrape_post_insufficient_length(mock_fetch, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    main_container_mock = AsyncMock()
    page_mock.wait_for_selector = AsyncMock()

    title_el = AsyncMock()
    title_el.inner_text.return_value = "오버워치 플레이 영상"

    def page_query_selector(sel):
        if sel == ".rd_body":
            return main_container_mock
        if "h1" in sel:
            return title_el
        return None

    page_mock.query_selector.side_effect = page_query_selector

    # Length is less than 10
    content_el = AsyncMock()
    content_el.inner_text.return_value = "짧은내용"
    main_container_mock.query_selector.side_effect = lambda sel: (
        content_el
        if sel
        in {
            ".xe_content",
            ".rd_body .xe_content",
            ".document_read .xe_content",
            ".rd_body",
            "p",
        }
        else None
    )

    cm_mock = MagicMock()
    cm_mock.__aenter__.return_value = page_mock
    scraper._new_page_cm = MagicMock(return_value=cm_mock)

    result = await scraper.scrape_post("https://www.fmkorea.com/best/9999")

    assert result.get("_scrape_error") is True
    assert result["failure_reason"] == "insufficient_content_length"


@pytest.mark.asyncio
@patch("scrapers.fmkorea.FMKoreaScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_scrape_post_failure(mock_fetch, scraper):
    # Simulate fetch error
    mock_fetch.side_effect = Exception("403 Forbidden")

    page_mock = AsyncMock()
    cm_mock = MagicMock()
    cm_mock.__aenter__.return_value = page_mock
    scraper._new_page_cm = MagicMock(return_value=cm_mock)

    result = await scraper.scrape_post("https://www.fmkorea.com/best/error")
    assert result.get("_scrape_error") is True
    assert result["failure_reason"] == "http_403_forbidden"
