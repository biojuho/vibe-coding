"""Tests for pipeline.x_analytics."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from pipeline.x_analytics import (
    init_db,
    add_tweet,
    get_tracked_tweets,
    save_snapshot,
    get_latest_snapshot,
    get_snapshot_history,
    get_monthly_api_usage,
    _log_api_usage,
    get_remaining_api_reads,
    prioritize_tweets,
    collect_tweet_stats,
    get_performance_summary
)
import pipeline.x_analytics as xa

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    orig_path = xa.DB_PATH
    xa.DB_PATH = tmp_path / "test_x_analytics.db"
    init_db()

    yield

    xa.DB_PATH = orig_path

def test_add_and_get_tracked():
    # Insert new
    t_id1 = add_tweet("123", text_preview="First tweet", topic="Test", channel="mychannel")
    assert t_id1 > 0

    # Insert duplicate returns existing
    t_id2 = add_tweet("123", text_preview="Duplicate tweet")
    assert t_id1 == t_id2

    add_tweet("456", text_preview="Second", channel="other")

    # Get all
    tweets = get_tracked_tweets()
    assert len(tweets) == 2

    # Get by channel
    channel_tweets = get_tracked_tweets(channel="mychannel")
    assert len(channel_tweets) == 1
    assert channel_tweets[0]["tweet_id"] == "123"

def test_save_and_get_snapshot():
    db_id = add_tweet("111")
    save_snapshot(db_id, impressions=100, likes=5, snapshot_type="auto")
    save_snapshot(db_id, impressions=500, likes=20, snapshot_type="auto")

    latest = get_latest_snapshot(db_id)
    assert latest is not None
    assert latest["impressions"] == 500

    history = get_snapshot_history(db_id)
    assert len(history) == 2

def test_api_usage_tracking():
    _log_api_usage(50)
    _log_api_usage(20)

    usage = get_monthly_api_usage()
    assert usage == 70

    remaining = get_remaining_api_reads()
    assert remaining == xa.MONTHLY_READ_LIMIT - 70

def test_prioritize_tweets():
    # 1. 48시간 이내
    add_tweet("recent", published_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    t_recent = get_tracked_tweets()[0]

    # 2. 7일 이내
    add_tweet("mid", published_at=(datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"))
    t_mid = [t for t in get_tracked_tweets() if t["tweet_id"] == "mid"][0]

    # 3. 7일 이상 & 스냅샷 임프레션 1500 (높은 점수 보너스)
    add_tweet("old_high", published_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"))
    t_old_high = [t for t in get_tracked_tweets() if t["tweet_id"] == "old_high"][0]
    save_snapshot(t_old_high["id"], impressions=1500)

    res = prioritize_tweets([t_recent, t_mid, t_old_high], max_samples=2)
    assert len(res) == 2

@patch("pipeline.x_analytics.os.getenv")
@patch("pipeline.x_analytics.requests.get")
def test_collect_tweet_stats(mock_get, mock_getenv):
    mock_getenv.return_value = "fake_token"

    # Setup track
    add_tweet("100")
    add_tweet("101")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "100", "public_metrics": {"impression_count": 1000, "like_count": 50}}
        ]
    }
    mock_get.return_value = mock_resp

    res = collect_tweet_stats(tweet_ids=["100", "101"])
    assert res["updated"] == 1
    assert res["reads_used"] == 1

    # Check snapshot created
    t100_id = [t["id"] for t in get_tracked_tweets() if t["tweet_id"] == "100"][0]
    latest = get_latest_snapshot(t100_id)
    assert latest["impressions"] == 1000
    assert latest["likes"] == 50

@patch("pipeline.x_analytics.os.getenv")
def test_collect_tweet_stats_no_token(mock_getenv):
    mock_getenv.return_value = ""
    res = collect_tweet_stats(tweet_ids=["100"])
    assert "error" in res

def test_get_performance_summary():
    id1 = add_tweet("800")
    id2 = add_tweet("801")

    save_snapshot(id1, impressions=1000, likes=10)
    save_snapshot(id2, impressions=200, likes=2)

    summary = get_performance_summary()
    assert summary["total_tweets"] == 2
    assert summary["total_impressions"] == 1200
    assert summary["avg_impressions"] == 600
