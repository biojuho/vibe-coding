"""
X(Twitter) 성과 자동 수집 — 자체 트윗의 공개 통계를 추적.

X API v2 Free Tier (월 1,500 reads) 제한 내에서
최신 + 고성과 트윗을 우선순위 기반으로 샘플링합니다.

Usage:
    from blind_to_x.pipeline.x_analytics import XAnalytics
    analytics = XAnalytics()
    result = analytics.collect_tweet_stats()
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")

DB_PATH = _ROOT / ".tmp" / "x_analytics.db"

# X API Free Tier: 월 1,500 reads
MONTHLY_READ_LIMIT = 1500
READS_PER_COLLECT = 50  # 1회 수집 시 최대 요청 수


# ── DB 연결 ──────────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """DB 및 테이블 초기화."""
    conn = _conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tracked_tweets (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id        TEXT NOT NULL UNIQUE,
                text_preview    TEXT DEFAULT '',
                topic           TEXT DEFAULT '',
                channel         TEXT DEFAULT '',
                published_at    TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS tweet_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_db_id     INTEGER NOT NULL,
                impressions     INTEGER DEFAULT 0,
                likes           INTEGER DEFAULT 0,
                retweets        INTEGER DEFAULT 0,
                replies         INTEGER DEFAULT 0,
                quotes          INTEGER DEFAULT 0,
                bookmarks       INTEGER DEFAULT 0,
                snapshot_type   TEXT DEFAULT 'manual',
                collected_at    TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (tweet_db_id) REFERENCES tracked_tweets(id)
            );

            CREATE TABLE IF NOT EXISTS api_usage_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                reads_used      INTEGER DEFAULT 0,
                month           TEXT DEFAULT '',
                logged_at       TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_tweet
                ON tweet_snapshots(tweet_db_id, collected_at);
        """)
        conn.commit()
    finally:
        conn.close()


# ── CRUD ─────────────────────────────────────────────────────
def add_tweet(
    tweet_id: str,
    text_preview: str = "",
    topic: str = "",
    channel: str = "",
    published_at: str = "",
) -> int:
    """트윗 등록. 이미 존재하면 기존 id 반환."""
    conn = _conn()
    try:
        existing = conn.execute("SELECT id FROM tracked_tweets WHERE tweet_id = ?", (tweet_id,)).fetchone()
        if existing:
            return existing["id"]

        if not published_at:
            published_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur = conn.execute(
            """INSERT INTO tracked_tweets
               (tweet_id, text_preview, topic, channel, published_at)
               VALUES (?, ?, ?, ?, ?)""",
            (tweet_id, text_preview[:280], topic, channel, published_at),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def get_tracked_tweets(
    limit: int = 50,
    channel: str | None = None,
) -> list[dict]:
    """추적 중인 트윗 목록."""
    conn = _conn()
    query = "SELECT * FROM tracked_tweets WHERE 1=1"
    params: list[Any] = []
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_snapshot(
    tweet_db_id: int,
    impressions: int = 0,
    likes: int = 0,
    retweets: int = 0,
    replies: int = 0,
    quotes: int = 0,
    bookmarks: int = 0,
    snapshot_type: str = "auto",
) -> None:
    """트윗 성과 스냅샷 저장."""
    conn = _conn()
    try:
        conn.execute(
            """INSERT INTO tweet_snapshots
               (tweet_db_id, impressions, likes, retweets,
                replies, quotes, bookmarks, snapshot_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tweet_db_id, impressions, likes, retweets, replies, quotes, bookmarks, snapshot_type),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_snapshot(tweet_db_id: int) -> dict | None:
    """트윗의 최신 스냅샷 조회."""
    conn = _conn()
    row = conn.execute(
        """SELECT * FROM tweet_snapshots
           WHERE tweet_db_id = ?
           ORDER BY collected_at DESC LIMIT 1""",
        (tweet_db_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_snapshot_history(tweet_db_id: int) -> list[dict]:
    """트윗의 스냅샷 히스토리."""
    conn = _conn()
    rows = conn.execute(
        """SELECT * FROM tweet_snapshots
           WHERE tweet_db_id = ?
           ORDER BY collected_at""",
        (tweet_db_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── API 사용량 추적 ──────────────────────────────────────────
def get_monthly_api_usage() -> int:
    """이번 달 API 사용량 조회."""
    month = datetime.now().strftime("%Y-%m")
    conn = _conn()
    row = conn.execute(
        "SELECT COALESCE(SUM(reads_used), 0) AS total FROM api_usage_log WHERE month = ?",
        (month,),
    ).fetchone()
    conn.close()
    return row["total"] if row else 0


def _log_api_usage(reads: int) -> None:
    """API 사용량 기록."""
    month = datetime.now().strftime("%Y-%m")
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO api_usage_log (reads_used, month) VALUES (?, ?)",
            (reads, month),
        )
        conn.commit()
    finally:
        conn.close()


def get_remaining_api_reads() -> int:
    """이번 달 남은 API 읽기 수."""
    return max(0, MONTHLY_READ_LIMIT - get_monthly_api_usage())


# ── 우선순위 기반 샘플링 ─────────────────────────────────────
def prioritize_tweets(
    tweets: list[dict],
    max_samples: int = READS_PER_COLLECT,
) -> list[dict]:
    """우선순위 기반 트윗 샘플링.

    우선순위:
    1. 최근 48시간 이내 발행 (아직 스냅샷 없는 트윗)
    2. 스냅샷이 있지만 7일 경과한 트윗 (업데이트 필요)
    3. 고성과 트윗 (기존 높은 노출 수)

    Returns:
        우선순위 정렬된 트윗 리스트 (최대 max_samples개)
    """
    now = datetime.now()
    scored: list[tuple[float, dict]] = []

    for tw in tweets:
        score = 0.0
        pub_str = tw.get("published_at", "")
        try:
            pub_dt = datetime.strptime(pub_str[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, IndexError):
            pub_dt = now - timedelta(days=30)

        age_hours = (now - pub_dt).total_seconds() / 3600

        # 최근 48시간: 높은 우선순위
        if age_hours <= 48:
            score += 100
        # 7일 이내: 중간 우선순위
        elif age_hours <= 168:
            score += 50

        latest = get_latest_snapshot(tw["id"])
        if latest is None:
            score += 80  # 아직 스냅샷 없음
        else:
            snap_str = latest.get("collected_at", "")
            try:
                snap_dt = datetime.strptime(snap_str[:19], "%Y-%m-%d %H:%M:%S")
                snap_age_hours = (now - snap_dt).total_seconds() / 3600
                if snap_age_hours > 168:  # 7일 이상 경과
                    score += 30
            except (ValueError, IndexError):
                score += 30

            # 고성과 보너스
            imp = latest.get("impressions", 0)
            if imp > 1000:
                score += 20
            elif imp > 500:
                score += 10

        scored.append((score, tw))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [tw for _, tw in scored[:max_samples]]


# ── X API v2 수집 ────────────────────────────────────────────
def collect_tweet_stats(
    tweet_ids: list[str] | None = None,
) -> dict[str, Any]:
    """X API v2로 트윗 성과 수집.

    Args:
        tweet_ids: 특정 트윗 ID만 수집 (None이면 자동 우선순위 샘플링)

    Returns:
        수집 결과 딕셔너리
    """
    bearer_token = os.getenv("X_BEARER_TOKEN", "")
    if not bearer_token:
        return {"error": "X_BEARER_TOKEN 환경변수가 없습니다.", "updated": 0}

    remaining = get_remaining_api_reads()
    if remaining <= 0:
        return {"error": "이번 달 API 읽기 한도 초과 (1,500 reads)", "updated": 0}

    if tweet_ids is None:
        # 우선순위 기반 자동 샘플링
        all_tweets = get_tracked_tweets(limit=200)
        sampled = prioritize_tweets(all_tweets, max_samples=min(remaining, READS_PER_COLLECT))
        tweet_ids = [tw["tweet_id"] for tw in sampled]

    if not tweet_ids:
        return {"updated": 0, "message": "수집 대상 트윗 없음"}

    # X API v2 배치 호출 (100개씩)
    stats_map: dict[str, dict] = {}
    reads_used = 0

    headers = {
        "Authorization": f"Bearer {bearer_token}",
    }

    for i in range(0, len(tweet_ids), 100):
        batch = tweet_ids[i : i + 100]
        try:
            resp = requests.get(
                "https://api.twitter.com/2/tweets",
                params={
                    "ids": ",".join(batch),
                    "tweet.fields": "public_metrics,created_at",
                },
                headers=headers,
                timeout=30,
            )
            reads_used += 1

            if resp.status_code == 429:
                logger.warning("[X API] Rate limit hit, stopping collection")
                break

            if resp.status_code != 200:
                logger.error("[X API] 오류: %s %s", resp.status_code, resp.text[:200])
                continue

            data = resp.json()
            for tweet in data.get("data", []):
                tid = tweet["id"]
                metrics = tweet.get("public_metrics", {})
                stats_map[tid] = {
                    "impressions": metrics.get("impression_count", 0),
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "quotes": metrics.get("quote_count", 0),
                    "bookmarks": metrics.get("bookmark_count", 0),
                }
        except Exception as exc:
            logger.error("[X API] 호출 실패: %s", exc)

    # API 사용량 기록
    _log_api_usage(reads_used)

    # 스냅샷 저장
    updated = 0
    for tw in get_tracked_tweets(limit=500):
        tid = tw["tweet_id"]
        if tid in stats_map:
            s = stats_map[tid]
            save_snapshot(
                tweet_db_id=tw["id"],
                impressions=s["impressions"],
                likes=s["likes"],
                retweets=s["retweets"],
                replies=s["replies"],
                quotes=s["quotes"],
                bookmarks=s["bookmarks"],
                snapshot_type="auto",
            )
            updated += 1

    return {
        "updated": updated,
        "reads_used": reads_used,
        "remaining_this_month": get_remaining_api_reads(),
    }


# ── 성과 분석 ────────────────────────────────────────────────
def get_performance_summary(
    channel: str | None = None,
) -> dict[str, Any]:
    """트윗 성과 요약.

    Returns:
        {"total_tweets": int, "total_impressions": int, ...}
    """
    tweets = get_tracked_tweets(limit=500, channel=channel)
    total_imp = 0
    total_likes = 0
    total_retweets = 0
    tweet_count = 0

    for tw in tweets:
        latest = get_latest_snapshot(tw["id"])
        if latest:
            total_imp += latest.get("impressions", 0)
            total_likes += latest.get("likes", 0)
            total_retweets += latest.get("retweets", 0)
            tweet_count += 1

    return {
        "total_tweets": len(tweets),
        "tracked_with_stats": tweet_count,
        "total_impressions": total_imp,
        "total_likes": total_likes,
        "total_retweets": total_retweets,
        "avg_impressions": round(total_imp / max(tweet_count, 1)),
        "avg_likes": round(total_likes / max(tweet_count, 1), 1),
        "api_reads_remaining": get_remaining_api_reads(),
    }
