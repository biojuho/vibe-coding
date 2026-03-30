import pytest
from unittest.mock import AsyncMock, MagicMock
from pipeline.commands.dry_run import run_dry_run_single


@pytest.fixture
def mock_deps():
    scraper = MagicMock()
    scraper.scrape_post = AsyncMock()
    scraper.scrape_post.return_value = {
        "title": "Test Title",
        "content": "Test content that is long enough",
        "url": "https://test.com/1",
    }
    scraper.min_content_length = 5
    scraper.assess_quality = MagicMock()
    scraper.assess_quality.return_value = {"score": 80}

    config = MagicMock()
    config.get.side_effect = lambda k, d=None: d

    draft_gen = AsyncMock()
    draft_gen.generate_drafts.return_value = ({"twitter": "Test draft"}, "image prompt")

    notion = AsyncMock()
    notion.is_duplicate.return_value = False

    return scraper, config, draft_gen, notion


@pytest.mark.asyncio
async def test_run_dry_run_single_success(mock_deps, monkeypatch):
    scraper, config, draft_gen, notion = mock_deps
    item = {"url": "https://test.com/1", "source": "test_src", "scraper": scraper}

    # Mock build_review_decision to return should_queue=True
    import pipeline.commands.dry_run

    monkeypatch.setattr(
        pipeline.commands.dry_run,
        "build_review_decision",
        lambda c, pd, p: {"should_queue": True, "review_reason": "", "review_status": "approved"},
    )

    res = await run_dry_run_single(item, config, draft_gen, notion, [])
    assert res["success"] is True
    assert res["url"] == "https://test.com/1"
    assert res["notion_url"] == "(dry-run)"


@pytest.mark.asyncio
async def test_run_dry_run_single_scrape_error(mock_deps):
    scraper, config, draft_gen, notion = mock_deps
    scraper.scrape_post.return_value = {"_scrape_error": True, "error_message": "Failed"}
    item = {"url": "https://test.com/1", "source": "test_src", "scraper": scraper}

    res = await run_dry_run_single(item, config, draft_gen, notion, [])
    assert res["success"] is False
    assert res["error"] == "Failed"


@pytest.mark.asyncio
async def test_run_dry_run_single_duplicate(mock_deps):
    scraper, config, draft_gen, notion = mock_deps
    notion.is_duplicate.return_value = True
    item = {"url": "https://test.com/1", "source": "test_src", "scraper": scraper}

    res = await run_dry_run_single(item, config, draft_gen, notion, [])
    assert res["success"] is True
    assert res["notion_url"] == "(skipped-duplicate)"


@pytest.mark.asyncio
async def test_run_dry_run_single_filter_short(mock_deps):
    scraper, config, draft_gen, notion = mock_deps
    scraper.min_content_length = 1000  # Will trigger short filter
    item = {"url": "https://test.com/1", "source": "test_src", "scraper": scraper}

    res = await run_dry_run_single(item, config, draft_gen, notion, [])
    assert res["error_code"] == "FILTERED_SHORT"


@pytest.mark.asyncio
async def test_run_dry_run_single_filter_spam(mock_deps):
    scraper, config, draft_gen, notion = mock_deps
    scraper.scrape_post.return_value["content"] = "스팸대출 등 스팸성 키워드"
    item = {"url": "https://test.com/1", "source": "test_src", "scraper": scraper}

    res = await run_dry_run_single(item, config, draft_gen, notion, [])
    assert res["error_code"] == "FILTERED_SPAM"


@pytest.mark.asyncio
async def test_run_dry_run_single_filter_low_quality(mock_deps, monkeypatch):
    scraper, config, draft_gen, notion = mock_deps
    item = {"url": "https://test.com/1", "source": "test_src", "scraper": scraper}

    # Mock build_review_decision to return should_queue=False
    import pipeline.commands.dry_run

    monkeypatch.setattr(
        pipeline.commands.dry_run,
        "build_review_decision",
        lambda c, pd, p: {"should_queue": False, "review_reason": "low_score", "review_status": "rejected"},
    )

    res = await run_dry_run_single(item, config, draft_gen, notion, [])
    assert res["error_code"] == "FILTERED_LOW_QUALITY"


@pytest.mark.asyncio
async def test_run_dry_run_single_no_post_data(mock_deps):
    scraper, config, draft_gen, notion = mock_deps
    scraper.scrape_post.return_value = None
    item = {"url": "https://test.com/1", "source": "test_src", "scraper": scraper}

    res = await run_dry_run_single(item, config, draft_gen, notion, [])
    assert res["success"] is False
    assert res["error"] == "Scraping failed"
