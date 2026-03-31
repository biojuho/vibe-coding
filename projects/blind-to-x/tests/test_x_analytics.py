"""T4-4: X Analytics 단위 테스트."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# blind-to-x is accessed via 'pipeline.' prefix, add parent
_BLIND_TO_X_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BLIND_TO_X_ROOT))


# ── DB 격리를 위한 fixture ──────────────────────────────────
@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pipeline.x_analytics.DB_PATH",
        tmp_path / "test_x_analytics.db",
    )


from pipeline.x_analytics import (  # noqa: E402
    add_tweet,
    get_latest_snapshot,
    get_monthly_api_usage,
    get_remaining_api_reads,
    get_snapshot_history,
    get_tracked_tweets,
    init_db,
    prioritize_tweets,
    save_snapshot,
    MONTHLY_READ_LIMIT,
)


def test_init_db_creates_tables(tmp_path: Path) -> None:
    init_db()
    from pipeline.x_analytics import DB_PATH

    conn = sqlite3.connect(str(DB_PATH))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    assert "tracked_tweets" in tables
    assert "tweet_snapshots" in tables
    assert "api_usage_log" in tables


def test_add_tweet_and_get() -> None:
    init_db()
    tid = add_tweet("12345", text_preview="테스트 트윗", topic="AI", channel="tech")
    assert tid > 0

    tweets = get_tracked_tweets()
    assert len(tweets) == 1
    assert tweets[0]["tweet_id"] == "12345"


def test_add_tweet_duplicate() -> None:
    init_db()
    id1 = add_tweet("dup_id", text_preview="A")
    id2 = add_tweet("dup_id", text_preview="B")
    assert id1 == id2

    tweets = get_tracked_tweets()
    assert len(tweets) == 1


def test_save_and_get_snapshot() -> None:
    init_db()
    db_id = add_tweet("snap_tweet", text_preview="스냅샷 테스트")
    save_snapshot(
        tweet_db_id=db_id,
        impressions=1000,
        likes=50,
        retweets=10,
        replies=5,
        quotes=2,
        bookmarks=8,
    )

    latest = get_latest_snapshot(db_id)
    assert latest is not None
    assert latest["impressions"] == 1000
    assert latest["likes"] == 50


def test_snapshot_history() -> None:
    init_db()
    db_id = add_tweet("hist_tweet")
    save_snapshot(db_id, impressions=100, likes=5)
    save_snapshot(db_id, impressions=200, likes=10)

    history = get_snapshot_history(db_id)
    assert len(history) == 2
    assert history[0]["impressions"] == 100
    assert history[1]["impressions"] == 200


def test_api_usage_tracking() -> None:
    init_db()
    usage = get_monthly_api_usage()
    assert usage == 0

    remaining = get_remaining_api_reads()
    assert remaining == MONTHLY_READ_LIMIT


def test_prioritize_tweets_empty() -> None:
    result = prioritize_tweets([], max_samples=10)
    assert result == []


def test_prioritize_tweets_recent_first() -> None:
    init_db()
    now = datetime.now()
    old_time = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    new_time = (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")

    _id_old = add_tweet("old_tweet", published_at=old_time)
    _id_new = add_tweet("new_tweet", published_at=new_time)

    tweets = get_tracked_tweets()
    prioritized = prioritize_tweets(tweets, max_samples=2)
    assert len(prioritized) == 2
    # 최근 트윗이 우선
    assert prioritized[0]["tweet_id"] == "new_tweet"


def test_prioritize_tweets_limit() -> None:
    init_db()
    for i in range(10):
        add_tweet(f"tweet_{i}", text_preview=f"트윗 {i}")

    tweets = get_tracked_tweets()
    prioritized = prioritize_tweets(tweets, max_samples=3)
    assert len(prioritized) == 3


def test_get_tracked_tweets_channel_filter() -> None:
    init_db()
    add_tweet("t1", channel="ai")
    add_tweet("t2", channel="crypto")
    add_tweet("t3", channel="ai")

    ai_tweets = get_tracked_tweets(channel="ai")
    assert len(ai_tweets) == 2

    all_tweets = get_tracked_tweets()
    assert len(all_tweets) == 3
