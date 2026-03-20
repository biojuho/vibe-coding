"""
YouTube 채널 성장 트래커 — 채널 레벨 성장 지표 자동 수집.

5채널 독립 추적: 구독자 수, 총 조회수, 영상 수 등을 주기적으로 수집하여
시계열 성장 데이터를 구축합니다.

Usage:
    python execution/channel_growth_tracker.py init
    python execution/channel_growth_tracker.py add --channel-id "UCxxxx" --name "AI/기술"
    python execution/channel_growth_tracker.py collect
    python execution/channel_growth_tracker.py report
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

DB_PATH = _ROOT / ".tmp" / "channel_growth.db"


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
            CREATE TABLE IF NOT EXISTS channels (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id      TEXT NOT NULL UNIQUE,
                name            TEXT NOT NULL DEFAULT '',
                custom_url      TEXT DEFAULT '',
                thumbnail_url   TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS growth_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_db_id   INTEGER NOT NULL,
                subscribers     INTEGER DEFAULT 0,
                total_views     INTEGER DEFAULT 0,
                video_count     INTEGER DEFAULT 0,
                collected_at    TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (channel_db_id) REFERENCES channels(id)
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_channel
                ON growth_snapshots(channel_db_id, collected_at);
        """)
        conn.commit()
    finally:
        conn.close()


# ── CRUD ─────────────────────────────────────────────────────
def add_channel(channel_id: str, name: str = "") -> int:
    """채널 등록. 이미 존재하면 기존 id 반환."""
    conn = _conn()
    try:
        existing = conn.execute("SELECT id FROM channels WHERE channel_id = ?", (channel_id,)).fetchone()
        if existing:
            logger.info("이미 등록된 채널: %s (id=%d)", channel_id, existing["id"])
            return existing["id"]

        cur = conn.execute(
            "INSERT INTO channels (channel_id, name) VALUES (?, ?)",
            (channel_id, name.strip()),
        )
        conn.commit()
        row_id = cur.lastrowid or 0
    finally:
        conn.close()
    logger.info("채널 등록 (id=%d): %s [%s]", row_id, name, channel_id)
    return row_id


def get_channels() -> list[dict]:
    """등록된 모든 채널 조회."""
    conn = _conn()
    rows = conn.execute("SELECT * FROM channels ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_snapshot(channel_db_id: int) -> dict | None:
    """채널의 최신 스냅샷 조회."""
    conn = _conn()
    row = conn.execute(
        """SELECT * FROM growth_snapshots
           WHERE channel_db_id = ?
           ORDER BY collected_at DESC LIMIT 1""",
        (channel_db_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_growth_history(channel_db_id: int, days: int = 90) -> list[dict]:
    """채널의 성장 히스토리 조회."""
    conn = _conn()
    rows = conn.execute(
        """SELECT * FROM growth_snapshots
           WHERE channel_db_id = ?
             AND collected_at >= datetime('now', 'localtime', ?)
           ORDER BY collected_at""",
        (channel_db_id, f"-{days} days"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _save_snapshot(
    channel_db_id: int,
    subscribers: int,
    total_views: int,
    video_count: int,
) -> None:
    """스냅샷 저장."""
    conn = _conn()
    try:
        conn.execute(
            """INSERT INTO growth_snapshots
               (channel_db_id, subscribers, total_views, video_count)
               VALUES (?, ?, ?, ?)""",
            (channel_db_id, subscribers, total_views, video_count),
        )
        conn.commit()
    finally:
        conn.close()


# ── YouTube API 수집 ─────────────────────────────────────────
def collect_channel_stats() -> dict[str, Any]:
    """등록된 모든 채널의 통계를 YouTube API로 수집.

    Returns:
        수집 결과 딕셔너리: updated, skipped, errors
    """
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "YOUTUBE_API_KEY 환경변수가 없습니다.", "updated": 0}

    channels = get_channels()
    if not channels:
        return {"updated": 0, "message": "등록된 채널이 없습니다."}

    channel_ids = [ch["channel_id"] for ch in channels]
    stats_map: dict[str, dict] = {}

    # 50개씩 배치 API 호출
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i : i + 50]
        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "part": "statistics,snippet",
                    "id": ",".join(batch),
                    "key": api_key,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error("YouTube API 오류: %s %s", resp.status_code, resp.text[:200])
                continue

            for item in resp.json().get("items", []):
                cid = item["id"]
                s = item.get("statistics", {})
                snippet = item.get("snippet", {})
                stats_map[cid] = {
                    "subscribers": int(s.get("subscriberCount", 0)),
                    "total_views": int(s.get("viewCount", 0)),
                    "video_count": int(s.get("videoCount", 0)),
                    "title": snippet.get("title", ""),
                    "custom_url": snippet.get("customUrl", ""),
                    "thumbnail_url": (snippet.get("thumbnails", {}).get("default", {}).get("url", "")),
                }
        except Exception as exc:
            logger.error("YouTube API 호출 실패: %s", exc)

    updated = 0
    errors = 0
    for ch in channels:
        cid = ch["channel_id"]
        if cid not in stats_map:
            errors += 1
            continue

        data = stats_map[cid]
        _save_snapshot(
            channel_db_id=ch["id"],
            subscribers=data["subscribers"],
            total_views=data["total_views"],
            video_count=data["video_count"],
        )

        # 채널 메타 업데이트
        conn = _conn()
        try:
            conn.execute(
                """UPDATE channels SET name = CASE WHEN name = '' THEN ? ELSE name END,
                       custom_url = ?, thumbnail_url = ?
                   WHERE id = ?""",
                (data["title"], data["custom_url"], data["thumbnail_url"], ch["id"]),
            )
            conn.commit()
        finally:
            conn.close()

        updated += 1
        logger.info(
            "✅ [%s] %s → %d구독/%d조회/%d영상",
            ch["name"] or data["title"],
            cid,
            data["subscribers"],
            data["total_views"],
            data["video_count"],
        )

    return {"updated": updated, "skipped": len(channels) - updated - errors, "errors": errors}


# ── 성장률 분석 ──────────────────────────────────────────────
def calculate_growth_rate(channel_db_id: int, days: int = 7) -> dict[str, float]:
    """최근 N일간 성장률 계산.

    Returns:
        {
            "subscriber_growth_rate": float (%),
            "view_growth_rate": float (%),
            "subscriber_daily_avg": float,
        }
    """
    history = get_growth_history(channel_db_id, days=days)
    if len(history) < 2:
        return {
            "subscriber_growth_rate": 0.0,
            "view_growth_rate": 0.0,
            "subscriber_daily_avg": 0.0,
        }

    oldest = history[0]
    newest = history[-1]

    sub_old = max(oldest["subscribers"], 1)
    sub_new = newest["subscribers"]
    sub_rate = ((sub_new - sub_old) / sub_old) * 100

    view_old = max(oldest["total_views"], 1)
    view_new = newest["total_views"]
    view_rate = ((view_new - view_old) / view_old) * 100

    sub_daily = (sub_new - oldest["subscribers"]) / max(days, 1)

    return {
        "subscriber_growth_rate": round(sub_rate, 2),
        "view_growth_rate": round(view_rate, 2),
        "subscriber_daily_avg": round(sub_daily, 1),
    }


def get_channel_comparison() -> list[dict]:
    """모든 채널의 최신 통계 + 7일 성장률 비교."""
    channels = get_channels()
    result = []
    for ch in channels:
        latest = get_latest_snapshot(ch["id"])
        growth = calculate_growth_rate(ch["id"], days=7)
        result.append(
            {
                "name": ch["name"],
                "channel_id": ch["channel_id"],
                "subscribers": latest["subscribers"] if latest else 0,
                "total_views": latest["total_views"] if latest else 0,
                "video_count": latest["video_count"] if latest else 0,
                "sub_growth_7d": growth["subscriber_growth_rate"],
                "view_growth_7d": growth["view_growth_rate"],
                "sub_daily_avg": growth["subscriber_daily_avg"],
            }
        )
    return result


# ── CLI ──────────────────────────────────────────────────────
def _cli() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="YouTube 채널 성장 트래커")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init", help="DB 초기화")

    add_p = sub.add_parser("add", help="채널 등록")
    add_p.add_argument("--channel-id", required=True, help="YouTube Channel ID")
    add_p.add_argument("--name", default="", help="채널 별칭")

    sub.add_parser("collect", help="모든 채널 통계 수집")
    sub.add_parser("report", help="채널 비교 리포트")

    args = parser.parse_args()

    if args.cmd == "init":
        init_db()
        print(f"✅ DB 초기화 완료: {DB_PATH}")
    elif args.cmd == "add":
        init_db()
        row_id = add_channel(args.channel_id, args.name)
        print(f"✅ 채널 등록 (id={row_id}): {args.name} [{args.channel_id}]")
    elif args.cmd == "collect":
        init_db()
        result = collect_channel_stats()
        print(f"📊 수집 결과: {result}")
    elif args.cmd == "report":
        init_db()
        comparison = get_channel_comparison()
        print(f"\n{'─' * 70}")
        print("  📈 채널 성장 비교 (7일)")
        print(f"{'─' * 70}")
        for ch in comparison:
            print(
                f"  {ch['name']:20s} | "
                f"구독 {ch['subscribers']:>8,} ({ch['sub_growth_7d']:+.1f}%) | "
                f"조회 {ch['total_views']:>12,} ({ch['view_growth_7d']:+.1f}%)"
            )
        print(f"{'─' * 70}\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
