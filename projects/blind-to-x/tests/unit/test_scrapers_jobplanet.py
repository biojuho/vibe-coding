import pytest
from unittest.mock import AsyncMock, patch

from config import ERROR_SCRAPE_PARSE_FAILED
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


def test_extract_post_id(scraper):
    assert scraper._extract_post_id("https://www.jobplanet.co.kr/community/posts/1234") == "1234"


def test_extract_post_id_rejects_invalid_url(scraper):
    with pytest.raises(Exception) as exc_info:
        scraper._extract_post_id("https://www.jobplanet.co.kr/community")

    assert exc_info.value.reason == "invalid_url_format"


def test_extract_post_payload_uses_content_title_fallback(scraper):
    first_line = "This first line is long enough to become a fallback title for Jobplanet"
    payload = scraper._extract_post_payload(
        {
            "title": "",
            "content": f"{first_line}\nDetailed body text for the community post.",
            "likes_count": 7,
            "comments_count": 2,
            "community_category": {"name": "culture"},
        }
    )

    assert payload["title"].endswith("...")
    assert len(payload["title"]) == 50
    assert payload["content"].startswith(first_line)
    assert payload["category"] == "culture"
    assert payload["likes"] == 7
    assert payload["comments"] == 2


def test_extract_post_payload_rejects_short_content(scraper):
    with pytest.raises(Exception) as exc_info:
        scraper._extract_post_payload({"title": "Title", "content": "short"})

    assert exc_info.value.reason == "insufficient_content_length"


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
    assert result["error_code"] == ERROR_SCRAPE_PARSE_FAILED
    assert result["failure_stage"] == "parse"
    assert result["failure_reason"] == "insufficient_content_length"


@pytest.mark.asyncio
@patch("scrapers.jobplanet.JobplanetScraper._new_page", new_callable=AsyncMock)
async def test_scrape_post_invalid_url_classified_before_fetch(mock_new_page, scraper):
    page_mock = AsyncMock()
    mock_new_page.return_value = page_mock

    result = await scraper.scrape_post("https://www.jobplanet.co.kr/community/posts/not-a-number")

    assert result.get("_scrape_error") is True
    assert result["failure_stage"] == "post_fetch"
    assert result["failure_reason"] == "invalid_url_format"
    page_mock.goto.assert_not_called()


@pytest.mark.asyncio
@patch("scrapers.jobplanet.JobplanetScraper._new_page", new_callable=AsyncMock)
async def test_scrape_post_screenshot_failure_classified(mock_new_page, scraper):
    page_mock = AsyncMock()
    mock_new_page.return_value = page_mock

    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.json.return_value = {
        "data": {
            "title": "Jobplanet post",
            "content": "Long enough Jobplanet content for the parser.",
        }
    }
    page_mock.goto.side_effect = [response_mock, RuntimeError("screenshot navigation failed")]

    result = await scraper.scrape_post("https://www.jobplanet.co.kr/community/posts/1234")

    assert result.get("_scrape_error") is True
    assert result["failure_stage"] == "screenshot"
    assert result["failure_reason"] == "screenshot_capture_failed"


@pytest.mark.asyncio
@patch("scrapers.jobplanet.JobplanetScraper._new_page", new_callable=AsyncMock)
async def test_scrape_post_uses_content_title_fallback(mock_new_page, scraper):
    page_mock = AsyncMock()
    mock_new_page.return_value = page_mock

    first_line = "This first content line is intentionally longer than fifty characters for fallback"
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.json.return_value = {
        "data": {
            "title": "",
            "content": f"{first_line}\nSecond line has enough content.",
            "likes_count": 7,
            "comments_count": 2,
        }
    }
    page_mock.goto.return_value = response_mock

    body_mock = AsyncMock()
    body_mock.screenshot = AsyncMock()
    page_mock.query_selector.return_value = body_mock

    result = await scraper.scrape_post("https://www.jobplanet.co.kr/community/posts/7777")

    assert result.get("_scrape_error") is None
    assert result["title"] == first_line[:47] + "..."
    assert result["category"] == "기타"
    assert result["likes"] == 7
    assert result["comments"] == 2


@pytest.mark.asyncio
@patch("scrapers.jobplanet.JobplanetScraper._new_page", new_callable=AsyncMock)
async def test_scrape_post_invalid_url_reports_reason(mock_new_page, scraper):
    page_mock = AsyncMock()
    mock_new_page.return_value = page_mock

    result = await scraper.scrape_post("https://www.jobplanet.co.kr/community/not-a-post")

    assert result.get("_scrape_error") is True
    assert result["failure_stage"] == "post_fetch"
    assert result["failure_reason"] == "invalid_url_format"
    assert "Could not extract post ID" in result["error_message"]
