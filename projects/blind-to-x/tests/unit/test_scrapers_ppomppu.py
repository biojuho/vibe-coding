import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.ppomppu import PpomppuScraper


@pytest.fixture
def mock_config():
    return {
        "headless": True,
        "screenshot_dir": "./mock_screenshots",
        "scrape_quality.save_failure_snapshot": False,
    }


@pytest.fixture
def scraper(mock_config):
    s = PpomppuScraper(mock_config)
    # mock proxy manager to not actually get a proxy to avoid errors
    s.proxy_manager = MagicMock()
    s.proxy_manager.get_random_proxy.return_value = None
    return s


class _FeedElement:
    def __init__(self, *, text="", href=None):
        self._text = text
        self._href = href

    async def get_attribute(self, name):
        return self._href if name == "href" else None

    async def inner_text(self):
        return self._text


class _FeedRow:
    def __init__(self, *, href, title, likes="0", cells=None, has_thumb=False):
        self._link = _FeedElement(text=title, href=href)
        self._recommend = _FeedElement(text=likes)
        self._cells = [_FeedElement(text=cell) for cell in (cells or [])]
        self._has_thumb = has_thumb

    async def query_selector(self, selector):
        if "view.php" in selector:
            return self._link
        if selector == "td.recommend, td.vote":
            return self._recommend
        if "thumb" in selector and self._has_thumb:
            return _FeedElement()
        return None

    async def query_selector_all(self, selector):
        return self._cells if selector == "td" else []


def test_normalize_url(scraper):
    assert scraper._normalize_url("/zboard/123") == "https://www.ppomppu.co.kr/zboard/123"
    assert scraper._normalize_url("view.php?id=1") == "https://www.ppomppu.co.kr/zboard/view.php?id=1"
    assert scraper._normalize_url("https://www.ppomppu.co.kr/test") == "https://www.ppomppu.co.kr/test"
    assert scraper._normalize_url("https://example.com/other") is None


def test_determine_category(scraper):
    assert scraper._determine_category("유머글ㅋㅋ", "내용") == "humor"
    assert scraper._determine_category("할인 핫딜", "구매완료") == "deal"
    assert scraper._determine_category("일반인", "평범") == "general"


@pytest.mark.asyncio
@patch("scrapers.ppomppu.PpomppuScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_fetch_post_urls(mock_fetch, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    el_mock = AsyncMock()
    el_mock.get_attribute = AsyncMock(return_value="/zboard/view.php?id=humor&no=123")
    page_mock.query_selector_all.return_value = [el_mock]

    scraper._new_page = AsyncMock(return_value=page_mock)

    urls = await scraper._fetch_post_urls("http://dummy_feed", "humor")

    assert len(urls) == 1
    assert urls[0] == "https://www.ppomppu.co.kr/zboard/view.php?id=humor&no=123"


@pytest.mark.asyncio
@patch("scrapers.ppomppu.PpomppuScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_get_feed_candidates(mock_fetch, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    row_mock = AsyncMock()

    def title_query(sel):
        if "title" in sel or "href" in sel:
            link = AsyncMock()
            link.get_attribute = AsyncMock(return_value="/zboard/view.php?id=humor&no=456")
            link.inner_text = AsyncMock(return_value="뽐뿌글 [10]")
            return link
        return None

    row_mock.query_selector.side_effect = title_query
    row_mock.query_selector_all.return_value = []  # for tds

    page_mock.query_selector_all.side_effect = lambda sel: [row_mock] if sel == "tr" else []

    scraper._new_page = AsyncMock(return_value=page_mock)

    candidates = await scraper.get_feed_candidates(mode="popular", limit=1)

    assert len(candidates) == 1
    assert candidates[0].url == "https://www.ppomppu.co.kr/zboard/view.php?id=humor&no=456"
    assert candidates[0].title == "뽐뿌글"
    assert candidates[0].comments == 10


@pytest.mark.asyncio
async def test_collect_feed_candidates_sorts_and_filters_rows(scraper):
    page_mock = AsyncMock()
    page_mock.query_selector_all.return_value = [
        _FeedRow(
            href="/zboard/view.php?id=humor&no=low",
            title="low [1]",
            likes="1",
            cells=["9", "20"],
        ),
        _FeedRow(
            href="/zboard/view.php?id=humor&no=high",
            title="high [3]",
            likes="4",
            cells=["120"],
            has_thumb=True,
        ),
        _FeedRow(
            href="/zboard/view.php?id=humor&no=high",
            title="duplicate [99]",
            likes="100",
            cells=["999"],
        ),
        _FeedRow(
            href="/zboard/view.php?id=regulation&no=skip",
            title="rules [1]",
            likes="99",
            cells=["999"],
        ),
    ]

    candidates = await scraper._collect_feed_candidates_from_page(page_mock, limit=2)

    assert [candidate.url for candidate in candidates] == [
        "https://www.ppomppu.co.kr/zboard/view.php?id=humor&no=high",
        "https://www.ppomppu.co.kr/zboard/view.php?id=humor&no=low",
    ]
    assert candidates[0].title == "high"
    assert candidates[0].comments == 3
    assert candidates[0].likes == 4
    assert candidates[0].views == 120
    assert candidates[0].has_image is True


@pytest.mark.asyncio
@patch("scrapers.ppomppu.os.makedirs")
@patch("scrapers.ppomppu.PpomppuScraper._fetch_html_via_session", new_callable=AsyncMock)
async def test_scrape_post_success(mock_fetch, mock_mkdir, scraper):
    mock_fetch.return_value = "<html><body></body></html>"
    page_mock = AsyncMock()

    main_container_mock = AsyncMock()
    page_mock.query_selector.return_value = main_container_mock

    title_el = AsyncMock()
    title_el.inner_text = AsyncMock(return_value="뽐뿌 할인!")
    title_el.query_selector = AsyncMock(return_value=None)

    content_el = AsyncMock()
    content_el.inner_text = AsyncMock(
        return_value="내용입니다.     이것은 10자 이상입니다."
    )  # Length should be > 10 for ppomppu check!
    content_el.query_selector = AsyncMock(return_value=None)  # Important! This ensures nested queries return None
    content_el.query_selector_all = AsyncMock(return_value=[])

    # query_selector logic mapping
    def qs_map(sel):
        if "h1" == sel:
            return title_el
        if "#vote_list_btn_txt" == sel:
            vote = AsyncMock()
            vote.inner_text = AsyncMock(return_value="5")
            return vote
        if "h1 #comment" == sel:
            cmt = AsyncMock()
            cmt.inner_text = AsyncMock(return_value="10")
            return cmt
        return content_el  # Fallback to returning content_el directly

    page_mock.query_selector.side_effect = qs_map
    main_container_mock.query_selector.side_effect = lambda sel: content_el

    scraper._new_page = AsyncMock(return_value=page_mock)
    main_container_mock.screenshot = AsyncMock()

    result = await scraper.scrape_post("https://www.ppomppu.co.kr/zboard/view.php?no=111")

    assert result.get("_scrape_error") is None
    assert result["title"] == "뽐뿌 할인!"
    assert result["content"] == "내용입니다.     이것은 10자 이상입니다."
    assert result["category"] == "deal"
    assert result["likes"] == 5
    assert result["comments"] == 10
