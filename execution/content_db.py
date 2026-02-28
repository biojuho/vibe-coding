"""
콘텐츠 DB - Shorts Manager용.
SQLite 기반 콘텐츠 큐 및 생성 이력 관리.

Usage:
    python execution/content_db.py init
    python execution/content_db.py add --topic "블랙홀의 미스터리 5가지" --channel "우주/천문학"
    python execution/content_db.py list
    python execution/content_db.py channels
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "content.db"
UPDATABLE_COLUMNS = {
    "status",
    "job_id",
    "title",
    "video_path",
    "thumbnail_path",
    "cost_usd",
    "duration_sec",
    "notes",
    "channel",
}


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS content_queue (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            topic          TEXT NOT NULL,
            channel        TEXT NOT NULL DEFAULT '',
            status         TEXT NOT NULL DEFAULT 'pending',
            job_id         TEXT DEFAULT '',
            title          TEXT DEFAULT '',
            video_path     TEXT DEFAULT '',
            thumbnail_path TEXT DEFAULT '',
            cost_usd       REAL DEFAULT 0.0,
            duration_sec   REAL DEFAULT 0.0,
            notes          TEXT DEFAULT '',
            created_at     TEXT DEFAULT (datetime('now','localtime')),
            updated_at     TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    # 기존 DB migration: channel 컬럼 없으면 추가
    try:
        conn.execute("ALTER TABLE content_queue ADD COLUMN channel TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 이미 존재
    conn.commit()
    conn.close()


def add_topic(topic: str, notes: str = "", channel: str = "") -> int:
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO content_queue (topic, notes, channel) VALUES (?, ?, ?)",
        (topic.strip(), notes.strip(), channel.strip()),
    )
    conn.commit()
    row_id = cur.lastrowid or 0
    conn.close()
    return row_id


def get_all(channel: str | None = None) -> list[dict[str, Any]]:
    conn = _conn()
    if channel:
        rows = conn.execute(
            "SELECT * FROM content_queue WHERE channel = ? ORDER BY created_at DESC",
            (channel,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM content_queue ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_channels() -> list[str]:
    """채널 목록 반환 (중복 제거, 알파벳 순)."""
    conn = _conn()
    rows = conn.execute(
        "SELECT DISTINCT channel FROM content_queue WHERE channel != '' ORDER BY channel"
    ).fetchall()
    conn.close()
    return [r["channel"] for r in rows]


def update_job(item_id: int, **kwargs: Any) -> None:
    if not kwargs:
        return
    invalid_keys = set(kwargs) - UPDATABLE_COLUMNS
    if invalid_keys:
        invalid_list = ", ".join(sorted(invalid_keys))
        raise ValueError(f"Unsupported update fields: {invalid_list}")
    kwargs["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [item_id]
    query = f"UPDATE content_queue SET {set_clause} WHERE id = ?"
    conn = _conn()
    conn.execute(query, values)  # noqa: S608
    conn.commit()
    conn.close()


def delete_item(item_id: int) -> None:
    conn = _conn()
    conn.execute("DELETE FROM content_queue WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def get_kpis(channel: str | None = None) -> dict[str, Any]:
    conn = _conn()
    params = (channel,) if channel else ()
    base_query = """
        SELECT
            COUNT(*)                                               AS total,
            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END)    AS success_count,
            SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END)    AS failed_count,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END)    AS pending_count,
            SUM(CASE WHEN status='running' THEN 1 ELSE 0 END)    AS running_count,
            COALESCE(SUM(cost_usd), 0.0)                          AS total_cost_usd,
            COALESCE(AVG(CASE WHEN status='success' THEN cost_usd END), 0.0) AS avg_cost_usd
        FROM content_queue
    """
    if channel:
        base_query += " WHERE channel = ?"
    row = conn.execute(base_query, params).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_daily_stats(days: int = 30) -> list[dict[str, Any]]:
    """일별 생성 건수 + 비용 집계 (최근 N일)."""
    conn = _conn()
    rows = conn.execute("""
        SELECT
            date(updated_at) AS day,
            COUNT(*)                                            AS total,
            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS success,
            SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END) AS failed,
            COALESCE(SUM(cost_usd), 0.0)                       AS cost_usd
        FROM content_queue
        WHERE updated_at >= date('now', 'localtime', ?)
          AND status IN ('success', 'failed')
        GROUP BY date(updated_at)
        ORDER BY day
    """, (f"-{days} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_channel_stats() -> list[dict[str, Any]]:
    """채널별 성공/실패/비용/길이 집계."""
    conn = _conn()
    rows = conn.execute("""
        SELECT
            channel,
            COUNT(*)                                            AS total,
            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS success,
            SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END) AS failed,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
            COALESCE(SUM(cost_usd), 0.0)                       AS total_cost,
            COALESCE(AVG(CASE WHEN status='success' THEN cost_usd END), 0.0)         AS avg_cost,
            COALESCE(AVG(CASE WHEN status='success' THEN duration_sec END), 0.0)     AS avg_duration
        FROM content_queue
        WHERE channel != ''
        GROUP BY channel
        ORDER BY channel
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_performing_topics(
    limit: int = 10,
    channel: str | None = None,
) -> list[dict[str, Any]]:
    """성공한 주제 중 비용 효율이 좋은 상위 N개 반환."""
    conn = _conn()
    base_query = """
        SELECT topic, channel, cost_usd, duration_sec, title, notes, updated_at
        FROM content_queue
        WHERE status = 'success'
    """
    params: list[Any] = []
    if channel:
        base_query += " AND channel = ?"
        params.append(channel)
    base_query += " ORDER BY cost_usd ASC, updated_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(base_query, params).fetchall()  # noqa: S608
    conn.close()
    return [dict(r) for r in rows]


def get_hourly_stats(days: int = 30) -> list[dict[str, Any]]:
    """시간대별 생성 성공률 집계."""
    conn = _conn()
    rows = conn.execute("""
        SELECT
            CAST(strftime('%H', updated_at) AS INTEGER) AS hour,
            COUNT(*)                                            AS total,
            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS success,
            SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END) AS failed,
            ROUND(
                CAST(SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS REAL)
                / MAX(COUNT(*), 1) * 100, 1
            ) AS success_rate
        FROM content_queue
        WHERE updated_at >= date('now', 'localtime', ?)
          AND status IN ('success', 'failed')
        GROUP BY hour
        ORDER BY hour
    """, (f"-{days} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(description="Shorts Content DB CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init", help="DB 초기화")

    add_p = sub.add_parser("add", help="주제 추가")
    add_p.add_argument("--topic", required=True)
    add_p.add_argument("--notes", default="")
    add_p.add_argument("--channel", default="")

    list_p = sub.add_parser("list", help="목록 출력")
    list_p.add_argument("--channel", default="")

    sub.add_parser("channels", help="채널 목록 출력")
    sub.add_parser("kpis", help="KPI 출력")

    args = parser.parse_args()
    if args.cmd == "init":
        init_db()
        print("DB 초기화 완료:", DB_PATH)
    elif args.cmd == "add":
        init_db()
        row_id = add_topic(args.topic, args.notes, args.channel)
        print(f"추가 완료 (id={row_id}): [{args.channel}] {args.topic}")
    elif args.cmd == "list":
        init_db()
        ch = getattr(args, "channel", "")
        for item in get_all(channel=ch or None):
            print(f"[{item['id']}] {item['status']:10s} [{item.get('channel',''):12s}] {item['topic']}")
    elif args.cmd == "channels":
        init_db()
        for ch in get_channels():
            print(ch)
    elif args.cmd == "kpis":
        init_db()
        import json
        print(json.dumps(get_kpis(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
