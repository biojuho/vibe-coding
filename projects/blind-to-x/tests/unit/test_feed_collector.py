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
        "feed_filter.fetch_multiplier": 3,
        "feed_filter.min_engagement_score": 5.0,
        "feed_filter.min_pre_editorial_score": 35.0,
        "feed_filter.title_blacklist": ["광고", "사자"],
        "schedule.enabled": True,
        "dedup.cross_source_enabled": True,
        "dedup.title_similarity_threshold": 0.6,
        "scrape_limits_per_source": {"blind": 2, "dcinside": 2},
    }

    def mock_get(key, default=None):
        return config_dict.get(key, default)

    config.get.side_effect = mock_get
    return config


@pytest.fixture
def mock_scrapers():
    blind_scraper = AsyncMock()
    blind_scraper.get_feed_candidates.return_value = [
        MockCandidate("연봉 3200인데 실수령 260 듣고 회의실이 조용해진 날", "https://teamblind.com/1", score=10.0),
        MockCandidate("사자 추천합니다", "https://teamblind.com/2", score=20.0),
        MockCandidate("연봉 2800인데 팀장 한마디 듣고 현타 온 글", "https://teamblind.com/3", score=2.0),
        MockCandidate("성과급 200 얘기 나오자 단톡방 댓글이 갈린 이유", "https://teamblind.com/4", score=15.0),
        MockCandidate("출근길에 월급 240 들은 날 다들 한숨 쉰 장면", "https://teamblind.com/5", score=14.0),
        MockCandidate("팀장 면담에서 '이직 생각 없냐' 듣고 웃픈 후기", "https://teamblind.com/6", score=12.0),
    ]

    dc_scraper = AsyncMock()
    dc_scraper.get_feed_candidates.return_value = [
        MockCandidate("출근길 카톡에 연봉 3000 vs 이직 얘기 올라온 날", "https://gall.dcinside.com/1", score=30.0),
        MockCandidate("광고성 글", "https://gall.dcinside.com/2", score=50.0),
        MockCandidate("회의실에서 실수령 240 듣고 정적이 온 순간", "https://gall.dcinside.com/1", score=30.0),
    ]

    return {"blind": blind_scraper, "dcinside": dc_scraper}


@pytest.mark.asyncio
async def test_collect_feed_items_normal(mock_config, mock_scrapers):
    args = Namespace(urls=None, popular=False, trending=True, limit=5)

    items, stats = await collect_feed_items(mock_config, args, mock_scrapers)

    assert len(items) <= 5
    assert stats["blacklist_skips"] == 2
    assert stats["low_engagement_skips"] == 1
    assert stats["editorial_skips"] == 0

    urls = [i["url"] for i in items]
    assert "https://teamblind.com/2" not in urls
    assert "https://teamblind.com/3" not in urls
    assert "https://teamblind.com/6" not in urls
    assert all(item["pre_editorial_score"] >= 60 for item in items)
    assert all("pre_editorial_reasons" in item for item in items)


@pytest.mark.asyncio
async def test_collect_feed_items_manual_urls(mock_config, mock_scrapers):
    args = Namespace(
        urls=["https://teamblind.com/custom1", "https://teamblind.com/custom2"],
        popular=False,
        trending=False,
        limit=5,
    )

    items, stats = await collect_feed_items(mock_config, args, mock_scrapers)

    assert len(items) == 3
    assert stats["blacklist_skips"] == 1

    manual_items = [item for item in items if item["feed_mode"] == "manual"]
    assert len(manual_items) == 2
    assert all(item["pre_editorial_score"] == 100 for item in manual_items)


@pytest.mark.asyncio
async def test_collect_feed_items_popular_mode(mock_config, mock_scrapers):
    args = Namespace(urls=None, popular=True, trending=False, limit=5)
    items, _stats = await collect_feed_items(mock_config, args, mock_scrapers)

    assert len(items) > 0
    assert all(item["feed_mode"] == "popular" for item in items)


@pytest.mark.asyncio
async def test_collect_feed_items_filters_abstract_titles(mock_config, mock_scrapers):
    """Title-only pre-screening uses a lower bar (default 35).

    Very abstract titles still get filtered, but borderline ones pass
    through to the full content-based editorial gate in process.py.
    """
    config_dict = {
        "scrape_limit": 5,
        "feed_filter.fetch_multiplier": 3,
        "feed_filter.min_engagement_score": 0.0,
        "feed_filter.min_pre_editorial_score": 35.0,
        "dedup.cross_source_enabled": False,
        "scrape_limits_per_source": {},
    }
    mock_config.get.side_effect = lambda k, d=None: config_dict.get(k, d)

    abstract_scraper = AsyncMock()
    abstract_scraper.get_feed_candidates.return_value = [
        # blind empty title: score ~44 (workplace bonus) → passes pre-screen (≥ 35)
        MockCandidate("", "https://teamblind.com/empty", score=99.0),
        # score ~42 → passes pre-screen
        MockCandidate("요즘 사람들 생각해봅시다", "https://teamblind.com/abstract", score=99.0),
        # score ~68 → passes pre-screen
        MockCandidate("실수령 260 듣고 다들 한숨 쉰 날", "https://teamblind.com/good", score=20.0),
    ]

    items, stats = await collect_feed_items(
        mock_config,
        Namespace(urls=None, popular=False, trending=True, limit=5),
        {"blind": abstract_scraper},
    )

    # All three pass the lenient title-only pre-screen (threshold=35);
    # full editorial scoring with content runs later in process.py.
    assert len(items) == 3
    assert stats["editorial_skips"] == 0
