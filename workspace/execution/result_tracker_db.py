"""
결과 추적 DB — 수동 업로드 후 성과 관리용.

"자동 업로드"가 아닌 "수동 업로드 + 자동 결과 관리" 철학.
사용자가 직접 YouTube/X에 업로드 후, URL만 등록하면
공개 통계를 자동으로 수집하여 성과를 추적합니다.

Usage:
    python workspace/execution/result_tracker_db.py init
    python workspace/execution/result_tracker_db.py add --platform youtube --url "..." --title "제목"
    python workspace/execution/result_tracker_db.py list
    python workspace/execution/result_tracker_db.py collect   # YouTube 통계 자동 수집
"""

from __future__ import annotations

import argparse

# [QA 수정] json import 제거 (미사용)
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from execution._logging import logger  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

DB_PATH = _ROOT / ".tmp" / "result_tracker.db"

# ── 지원 플랫폼 ─────────────────────────────────────────────
PLATFORMS = {
    "youtube": {"display": "YouTube", "emoji": "🎬", "auto_stats": True},
    "x": {"display": "X (Twitter)", "emoji": "𝕏", "auto_stats": False},
    "threads": {"display": "Threads", "emoji": "🧵", "auto_stats": False},
    "blog": {"display": "네이버 블로그", "emoji": "📝", "auto_stats": False},
}


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
            CREATE TABLE IF NOT EXISTS published_content (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                platform       TEXT NOT NULL DEFAULT 'youtube',
                url            TEXT NOT NULL DEFAULT '',
                video_id       TEXT DEFAULT '',
                title          TEXT NOT NULL DEFAULT '',
                channel        TEXT DEFAULT '',
                tags           TEXT DEFAULT '',
                memo           TEXT DEFAULT '',

                -- YouTube 통계 (API Key로 자동 수집)
                views          INTEGER DEFAULT 0,
                likes          INTEGER DEFAULT 0,
                comments       INTEGER DEFAULT 0,

                -- X/Threads 통계 (수동 입력)
                impressions    INTEGER DEFAULT 0,
                retweets       INTEGER DEFAULT 0,
                bookmarks      INTEGER DEFAULT 0,

                -- 메타
                published_at   TEXT DEFAULT '',
                stats_updated  TEXT DEFAULT '',
                created_at     TEXT DEFAULT (datetime('now','localtime')),
                updated_at     TEXT DEFAULT (datetime('now','localtime')),

                -- [QA 수정] 같은 URL 중복 등록 방지
                UNIQUE(platform, url)
            );

            CREATE TABLE IF NOT EXISTS stats_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id      INTEGER NOT NULL,
                views           INTEGER DEFAULT 0,
                likes           INTEGER DEFAULT 0,
                comments        INTEGER DEFAULT 0,
                impressions     INTEGER DEFAULT 0,
                retweets        INTEGER DEFAULT 0,
                bookmarks       INTEGER DEFAULT 0,
                collected_at    TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (content_id) REFERENCES published_content(id)
            );
        """)
        conn.commit()
    finally:
        conn.close()


# ── URL → Video ID 파싱 ─────────────────────────────────────
def extract_youtube_video_id(url: str) -> str:
    """YouTube URL에서 video ID 추출."""
    patterns = [
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return ""


# ── CRUD ─────────────────────────────────────────────────────
def add_content(
    platform: str,
    url: str,
    title: str,
    channel: str = "",
    tags: str = "",
    memo: str = "",
    published_at: str = "",
) -> int:
    """콘텐츠 등록. 같은 platform+url 조합은 중복 등록 불가."""
    video_id = ""
    if platform == "youtube":
        video_id = extract_youtube_video_id(url)

    if not published_at:
        published_at = datetime.now().strftime("%Y-%m-%d")

    url_clean = url.strip()

    # [QA 수정] 중복 URL 체크
    conn = _conn()
    try:
        existing = conn.execute(
            "SELECT id FROM published_content WHERE platform = ? AND url = ?",
            (platform, url_clean),
        ).fetchone()
        if existing:
            conn.close()
            logger.warning("중복 URL, 기존 id=%d 반환: %s", existing["id"], url_clean)
            return existing["id"]

        cur = conn.execute(
            """INSERT INTO published_content
               (platform, url, video_id, title, channel, tags, memo, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (platform, url_clean, video_id, title.strip(), channel.strip(), tags.strip(), memo.strip(), published_at),
        )
        conn.commit()
        row_id = cur.lastrowid or 0
    finally:
        conn.close()
    logger.info("등록 완료 (id=%d): [%s] %s", row_id, platform, title)
    return row_id


def get_all(platform: str | None = None, channel: str | None = None) -> list[dict]:
    """전체 콘텐츠 조회."""
    conn = _conn()
    query = "SELECT * FROM published_content WHERE 1=1"
    params: list[Any] = []
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_by_id(content_id: int) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM published_content WHERE id = ?", (content_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_stats(
    content_id: int,
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    impressions: int = 0,
    retweets: int = 0,
    bookmarks: int = 0,
) -> None:
    """통계 업데이트 + 히스토리 기록."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # [QA 수정] try-finally로 DB 연결 안전성 보장
    conn = _conn()
    try:
        conn.execute(
            """UPDATE published_content
               SET views=?, likes=?, comments=?,
                   impressions=?, retweets=?, bookmarks=?,
                   stats_updated=?, updated_at=?
               WHERE id=?""",
            (views, likes, comments, impressions, retweets, bookmarks, now, now, content_id),
        )
        conn.execute(
            """INSERT INTO stats_history
               (content_id, views, likes, comments, impressions, retweets, bookmarks)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (content_id, views, likes, comments, impressions, retweets, bookmarks),
        )
        conn.commit()
    finally:
        conn.close()


def update_manual_stats(
    content_id: int,
    **kwargs: int,
) -> None:
    """X/Threads 등 수동 통계 입력."""
    allowed = {"views", "likes", "comments", "impressions", "retweets", "bookmarks"}
    filtered = {k: v for k, v in kwargs.items() if k in allowed}
    if not filtered:
        return

    existing = get_by_id(content_id)
    if not existing:
        return

    update_stats(
        content_id,
        views=filtered.get("views", existing.get("views", 0)),
        likes=filtered.get("likes", existing.get("likes", 0)),
        comments=filtered.get("comments", existing.get("comments", 0)),
        impressions=filtered.get("impressions", existing.get("impressions", 0)),
        retweets=filtered.get("retweets", existing.get("retweets", 0)),
        bookmarks=filtered.get("bookmarks", existing.get("bookmarks", 0)),
    )


def delete_content(content_id: int) -> None:
    # [QA 수정] try-finally로 DB 연결 안전성 보장
    conn = _conn()
    try:
        conn.execute("DELETE FROM stats_history WHERE content_id = ?", (content_id,))
        conn.execute("DELETE FROM published_content WHERE id = ?", (content_id,))
        conn.commit()
    finally:
        conn.close()


def get_stats_history(content_id: int) -> list[dict]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM stats_history WHERE content_id = ? ORDER BY collected_at",
        (content_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── YouTube 공개 통계 자동 수집 (API Key 방식) ────────────────
def collect_youtube_stats() -> dict[str, Any]:
    """
    등록된 YouTube 콘텐츠의 공개 통계를 자동 수집.
    YOUTUBE_API_KEY만 필요 (OAuth 불필요, 계정 리스크 0%).
    """
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "YOUTUBE_API_KEY 환경변수가 없습니다.", "updated": 0}

    items = get_all(platform="youtube")
    yt_items = [it for it in items if it.get("video_id")]

    if not yt_items:
        return {"updated": 0, "skipped": 0, "message": "수집 대상 YouTube 콘텐츠 없음"}

    # 50개씩 배치 API 호출
    video_ids = [it["video_id"] for it in yt_items]
    stats_map: dict[str, dict] = {}

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "statistics",
                    "id": ",".join(batch),
                    "key": api_key,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error("YouTube API 오류: %s %s", resp.status_code, resp.text[:200])
                continue

            for item in resp.json().get("items", []):
                vid = item["id"]
                s = item.get("statistics", {})
                stats_map[vid] = {
                    "views": int(s.get("viewCount", 0)),
                    "likes": int(s.get("likeCount", 0)),
                    "comments": int(s.get("commentCount", 0)),
                }
        except Exception as exc:
            logger.error("YouTube API 호출 실패: %s", exc)

    updated = 0
    for it in yt_items:
        vid = it["video_id"]
        if vid in stats_map:
            s = stats_map[vid]
            update_stats(
                it["id"],
                views=s["views"],
                likes=s["likes"],
                comments=s["comments"],
            )
            updated += 1
            logger.info("✅ [%s] %s → %d views", it["channel"], it["title"][:30], s["views"])

    return {
        "updated": updated,
        "skipped": len(yt_items) - updated,
        "total": len(yt_items),
    }


# ── 집계 함수 ────────────────────────────────────────────────
def get_platform_summary() -> list[dict]:
    """플랫폼별 집계."""
    conn = _conn()
    rows = conn.execute("""
        SELECT
            platform,
            COUNT(*) AS count,
            COALESCE(SUM(views), 0) AS total_views,
            COALESCE(SUM(likes), 0) AS total_likes,
            COALESCE(SUM(comments), 0) AS total_comments,
            COALESCE(AVG(views), 0) AS avg_views
        FROM published_content
        GROUP BY platform
        ORDER BY total_views DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_channel_summary() -> list[dict]:
    """채널별 집계."""
    conn = _conn()
    rows = conn.execute("""
        SELECT
            channel,
            platform,
            COUNT(*) AS count,
            COALESCE(SUM(views), 0) AS total_views,
            COALESCE(SUM(likes), 0) AS total_likes,
            COALESCE(SUM(comments), 0) AS total_comments,
            COALESCE(AVG(views), 0) AS avg_views
        FROM published_content
        WHERE channel != ''
        GROUP BY channel, platform
        ORDER BY total_views DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_content(limit: int = 10) -> list[dict]:
    """조회수 기준 TOP N 콘텐츠."""
    conn = _conn()
    rows = conn.execute(
        """
        SELECT * FROM published_content
        WHERE views > 0
        ORDER BY views DESC
        LIMIT ?
    """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_trend(days: int = 30) -> list[dict]:
    """일별 등록 + 조회수 추이."""
    conn = _conn()
    rows = conn.execute(
        """
        SELECT
            date(published_at) AS day,
            COUNT(*) AS count,
            COALESCE(SUM(views), 0) AS total_views,
            COALESCE(SUM(likes), 0) AS total_likes
        FROM published_content
        WHERE published_at >= date('now', 'localtime', ?)
        GROUP BY date(published_at)
        ORDER BY day
    """,
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── CLI ──────────────────────────────────────────────────────
def _cli() -> None:
    parser = argparse.ArgumentParser(description="콘텐츠 결과 추적기")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init", help="DB 초기화")

    add_p = sub.add_parser("add", help="콘텐츠 등록")
    add_p.add_argument("--platform", required=True, choices=list(PLATFORMS.keys()))
    add_p.add_argument("--url", required=True)
    add_p.add_argument("--title", required=True)
    add_p.add_argument("--channel", default="")
    add_p.add_argument("--tags", default="")

    list_p = sub.add_parser("list", help="전체 목록")
    list_p.add_argument("--platform", default="")

    sub.add_parser("collect", help="YouTube 통계 자동 수집")

    args = parser.parse_args()

    if args.cmd == "init":
        init_db()
        print(f"✅ DB 초기화 완료: {DB_PATH}")
    elif args.cmd == "add":
        init_db()
        row_id = add_content(
            platform=args.platform,
            url=args.url,
            title=args.title,
            channel=args.channel,
            tags=args.tags,
        )
        print(f"✅ 등록 (id={row_id}): [{args.platform}] {args.title}")
    elif args.cmd == "list":
        init_db()
        items = get_all(platform=args.platform or None)
        for it in items:
            emoji = PLATFORMS.get(it["platform"], {}).get("emoji", "📄")
            title = it["title"][:40]
            print(f"  {emoji} [{it['id']}] {title:40s} | {it['views']:>6}v {it['likes']:>4}♥ | {it['url'][:50]}")
    elif args.cmd == "collect":
        init_db()
        result = collect_youtube_stats()
        print(f"📊 수집 결과: {result}")
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
