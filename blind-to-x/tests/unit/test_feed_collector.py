import pytest
from unittest.mock import AsyncMock, MagicMock
from argparse import Namespace
from pipeline.feed_collector import collect_feed_items

class MockCandidate:
    def __init__(self, title, url, score=10.0, likes=10, comments=5):
        self.title = title
        self.url = url
        self.engagement_score = score
        self.likes = likes
        self.comments = comments

@pytest.fixture
def mock_config():
    config = MagicMock()
    config_dict = {
        "scrape_limit": 5,
        "feed_filter.fetch_multiplier": 2,
        "feed_filter.min_engagement_score": 5.0,
        "feed_filter.title_blacklist": ["투자", "광고"],
        "schedule.enabled": True,
        "dedup.cross_source_enabled": True,
        "dedup.title_similarity_threshold": 0.6,
        "scrape_limits_per_source": {"blind": 2, "dcinside": 2}
    }

    def mock_get(key, default=None):
        return config_dict.get(key, default)

    config.get.side_effect = mock_get
    return config

@pytest.fixture
def mock_scrapers():
    blind_scraper = AsyncMock()
    blind_scraper.get_feed_candidates.return_value = [
        MockCandidate("일반적인 글", "https://teamblind.com/1", score=10.0),
        MockCandidate("투자 추천합니다", "https://teamblind.com/2", score=20.0), # blacklist skip
        MockCandidate("인기 없는 글", "https://teamblind.com/3", score=2.0), # low engagement skip
        MockCandidate("좋은 정보", "https://teamblind.com/4", score=15.0),
        MockCandidate("비슷한 좋은 정보", "https://teamblind.com/5", score=14.0), # dedup / valid
        MockCandidate("너무 많은 블라인드 글", "https://teamblind.com/6", score=12.0) # per source limit skip (limit=2)
    ]

    dc_scraper = AsyncMock()
    dc_scraper.get_feed_candidates.return_value = [
        MockCandidate("디시 일상", "https://gall.dcinside.com/1", score=30.0),
        MockCandidate("광고성 글", "https://gall.dcinside.com/2", score=50.0), # blacklist skip
        MockCandidate("중복 URL", "https://gall.dcinside.com/1", score=30.0), # url dedup
    ]

    return {"blind": blind_scraper, "dcinside": dc_scraper}


@pytest.mark.asyncio
async def test_collect_feed_items_normal(mock_config, mock_scrapers):
    # Test normal trending/popular mode
    args = Namespace(urls=None, popular=False, trending=True, limit=5)

    items, stats = await collect_feed_items(mock_config, args, mock_scrapers)

    assert len(items) <= 5
    assert stats["blacklist_skips"] == 2  # 투자, 광고
    assert stats["low_engagement_skips"] == 1 # 2.0

    urls = [i["url"] for i in items]
    assert "https://teamblind.com/2" not in urls # Blacklisted
    assert "https://teamblind.com/3" not in urls # Low engagement
    assert "https://teamblind.com/6" not in urls # Per-source limit (only highest 2 kept -> 4, 5)

@pytest.mark.asyncio
async def test_collect_feed_items_manual_urls(mock_config, mock_scrapers):
    # Test when manual URLs are provided
    args = Namespace(urls=["https://teamblind.com/custom1", "https://teamblind.com/custom2"], popular=False, trending=False, limit=5)

    items, stats = await collect_feed_items(mock_config, args, mock_scrapers)

    # 2 manual items + 1 valid item from dcinside scraper
    assert len(items) == 3
    # dcinside scraper will return its candidates, adding 1 blacklist skip
    assert stats["blacklist_skips"] == 1

    manual_urls = [item["url"] for item in items if item["feed_mode"] == "manual"]
    assert "https://teamblind.com/custom1" in manual_urls
    assert "https://teamblind.com/custom2" in manual_urls

@pytest.mark.asyncio
async def test_collect_feed_items_popular_mode(mock_config, mock_scrapers):
    args = Namespace(urls=None, popular=True, trending=False, limit=5)
    items, stats = await collect_feed_items(mock_config, args, mock_scrapers)

    assert len(items) > 0
    # The mode should be set to "popular"
    for item in items:
        assert item["feed_mode"] == "popular"

@pytest.mark.asyncio
async def test_collect_feed_items_no_dedup_no_limits(mock_config, mock_scrapers):
    # Override config to disable dedup and limits
    config_dict = {
        "scrape_limit": 5,
        "feed_filter.fetch_multiplier": 1,
        "feed_filter.min_engagement_score": 0.0,
        "dedup.cross_source_enabled": False,
        "scrape_limits_per_source": {}
    }
    mock_config.get.side_effect = lambda k, d=None: config_dict.get(k, d)
    args = Namespace(urls=None, popular=False, trending=True, limit=None)

    items, stats = await collect_feed_items(mock_config, args, mock_scrapers)

    assert stats["cross_source_dedup_count"] == 0
    # URLs shouldn't be limited per source, though global limit (5) applies
    assert len(items) <= 5

