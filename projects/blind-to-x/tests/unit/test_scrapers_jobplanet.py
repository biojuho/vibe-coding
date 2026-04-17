import pytest
from unittest.mock import AsyncMock, patch

from scrapers.jobplanet import JobplanetScraper


@pytest.fixture
def mock_config():
    return {
        "headless": True,
        "screenshot_dir": "./mock_screenshots",
        "scrape_quality.save_failure_snapshot": False,
    }


@pytest.fixture
def scraper(mock_config):
    return JobplanetScraper(mock_config)


@pytest.mark.asyncio
async def test_normalize_url(scraper):
    assert scraper._normalize_url("/community/posts/123") == "https://www.jobplanet.co.kr/community/posts/123"
    assert (
        scraper._normalize_url("https://www.jobplanet.co.kr/community/posts/456")
        == "https://www.jobplanet.co.kr/community/posts/456"
    )
    assert scraper._normalize_url(None) is None
    assert scraper._normalize_url("https://example.com/post") is None


@pytest.mark.asyncio
async def test_determine_category(scraper):
    assert scraper._determine_category("대리 연봉 5000", "너무 적네요") == "money"
    assert scraper._determine_category("이직 고민", "어떻게 할까요") == "career"
    assert scraper._determine_category("야근이 너무 많아", "힘들다") == "work-life"
    assert scraper._determine_category("스타트업 vs 대기업", "추천점") == "company"
    assert scraper._determine_category("일반적인 글", "별내용없음") == "general"


@pytest.mark.asyncio
@patch("scrapers.jobplanet.JobplanetScraper._new_page", new_callable=AsyncMock)
async def test_fetch_post_urls(mock_new_page, scraper):
    page_mock = AsyncMock()
    mock_new_page.return_value = page_mock

    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.json.return_value = {
        "data": {
            "items": [
                {"id": 1001},
                {"id": 1002},
            ]
        }
    }
    page_mock.goto.return_value = response_mock

    urls = await scraper._fetch_post_urls("http://dummy_api", limit=2)
    assert len(urls) == 2
    assert "https://www.jobplanet.co.kr/community/posts/1001" in urls


@pytest.mark.asyncio
@patch("scrapers.jobplanet.JobplanetScraper._new_page", new_callable=AsyncMock)
async def test_get_feed_candidates(mock_new_page, scraper):
    page_mock = AsyncMock()
    mock_new_page.return_value = page_mock

    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.json.return_value = {
        "data": {
            "items": [{"id": 1001, "title": "잡플래닛 글", "like_count": 10, "comment_count": 5, "view_count": 100}]
        }
    }
    page_mock.goto.return_value = response_mock

    candidates = await scraper.get_feed_candidates(mode="popular", limit=1)
    assert len(candidates) == 1
    assert candidates[0].url == "https://www.jobplanet.co.kr/community/posts/1001"
    assert candidates[0].title == "잡플래닛 글"
    assert candidates[0].likes == 10
    assert candidates[0].comments == 5


@pytest.mark.asyncio
@patch("scrapers.jobplanet.os.makedirs")
@patch("scrapers.jobplanet.JobplanetScraper._new_page", new_callable=AsyncMock)
async def test_scrape_post_success(mock_new_page, mock_mkdir, scraper):
    page_mock = AsyncMock()
    mock_new_page.return_value = page_mock

    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.json.return_value = {
        "data": {
            "title": "잡플래닛 면접 후기",
            "content": "이 코드는 면접과 관련된 내용이 충분히 깁니다.",
            "likes_count": 42,
            "comments_count": 3,
            "community_category": {"name": "면접"},
        }
    }
    page_mock.goto.return_value = response_mock

    body_mock = AsyncMock()
    body_mock.screenshot = AsyncMock()
    page_mock.query_selector.return_value = body_mock

    result = await scraper.scrape_post("https://www.jobplanet.co.kr/community/posts/9999")

    assert result.get("_scrape_error") is None
    assert result["title"] == "잡플래닛 면접 후기"
    assert "이 코드는 면접과 관련된 내용이 충분히 깁니다" in result["content"]
    assert result["likes"] == 42
    assert "screenshot_path" in result


@pytest.mark.asyncio
@patch("scrapers.jobplanet.JobplanetScraper._new_page", new_callable=AsyncMock)
async def test_scrape_post_insufficient_length(mock_new_page, scraper):
    page_mock = AsyncMock()
    mock_new_page.return_value = page_mock

    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.json.return_value = {
        "data": {
            "title": "짧은 글",
            "content": "ㅋㅋ",
        }
    }
    page_mock.goto.return_value = response_mock

    result = await scraper.scrape_post("https://www.jobplanet.co.kr/community/posts/1234")

    assert result.get("_scrape_error") is True
    assert result["failure_reason"] == "insufficient_content_length"
