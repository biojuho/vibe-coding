"""Schema, migrations, and DDL helpers for cost_db.

Split from `pipeline/cost_db.py` to separate the schema/migration concerns
from the runtime query layer. The `CostDatabase` class re-imports the
public symbols and re-exports the legacy private aliases (`_MIGRATION_COLUMNS`,
`_PRAGMA_TABLE_INFO_SQL`, `_ALTER_TABLE_ADD_SQL`, `_validate_*`) so existing
call sites and tests keep working without modification.

Why pure functions, not class methods:
    `init_db(conn)` and `ensure_column(conn, ...)` operate on a connection
    that the caller owns. Keeping them as module-level functions lets us
    unit-test the schema with an in-memory `sqlite3.connect(":memory:")`
    and zero CostDatabase machinery.
"""

from __future__ import annotations

import sqlite3
from typing import Final

# Adds-only migration table. Every entry here is wired into `init_db()`'s
# idempotent ALTER TABLE pass at the end. DDL strings are exact-match
# verified by `validate_migration_column` — keep them stable. Insertion
# order matters: it dictates the migration order during init_db.
MIGRATION_COLUMNS: Final[dict[str, dict[str, str]]] = {
    "draft_analytics": {
        "content_url": "TEXT DEFAULT ''",
        "notion_page_id": "TEXT DEFAULT ''",
        "published_at": "TEXT DEFAULT ''",
        "hook_score": "REAL DEFAULT 0.0",
        "virality_score": "REAL DEFAULT 0.0",
        "fit_score": "REAL DEFAULT 0.0",
        "yt_views": "INTEGER DEFAULT 0",
        "engagement_rate": "REAL DEFAULT 0.0",
        "impression_count": "INTEGER DEFAULT 0",
        "comment_trigger_avg": "REAL DEFAULT 0.0",
    },
    "daily_text_costs": {
        "cache_creation_tokens": "INTEGER DEFAULT 0",
        "cache_read_tokens": "INTEGER DEFAULT 0",
    },
}
PRAGMA_TABLE_INFO_SQL: Final[dict[str, str]] = {
    table_name: f"PRAGMA table_info({table_name})" for table_name in MIGRATION_COLUMNS
}
ALTER_TABLE_ADD_SQL: Final[dict[tuple[str, str], str]] = {
    (table_name, column_name): f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"
    for table_name, columns in MIGRATION_COLUMNS.items()
    for column_name, ddl in columns.items()
}

# Initial CREATE TABLE + CREATE INDEX script. `init_db()` runs this first,
# then iterates MIGRATION_COLUMNS to add any subsequently-added columns
# idempotently (CREATE TABLE IF NOT EXISTS does not back-fill new columns
# on existing tables).
CREATE_TABLES_SCRIPT: Final[str] = """
    CREATE TABLE IF NOT EXISTS daily_text_costs (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at    TEXT    NOT NULL DEFAULT (datetime('now')),
        date           TEXT    NOT NULL,
        provider       TEXT    NOT NULL,
        tokens_input   INTEGER DEFAULT 0,
        tokens_output  INTEGER DEFAULT 0,
        usd_estimated  REAL    DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS daily_image_costs (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at    TEXT    NOT NULL DEFAULT (datetime('now')),
        date           TEXT    NOT NULL,
        provider       TEXT    NOT NULL,
        image_count    INTEGER DEFAULT 0,
        usd_estimated  REAL    DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS draft_analytics (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at    TEXT    NOT NULL DEFAULT (datetime('now')),
        date           TEXT    NOT NULL,
        content_url    TEXT    DEFAULT '',
        notion_page_id TEXT    DEFAULT '',
        source         TEXT    DEFAULT '',
        topic_cluster  TEXT    DEFAULT '',
        hook_type      TEXT    DEFAULT '',
        emotion_axis   TEXT    DEFAULT '',
        draft_style    TEXT    DEFAULT '',
        provider_used  TEXT    DEFAULT '',
        final_rank_score REAL  DEFAULT 0.0,
        published      INTEGER DEFAULT 0,
        published_at   TEXT    DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS provider_failures (
        provider       TEXT    PRIMARY KEY,
        fail_count     INTEGER DEFAULT 0,
        last_fail_at   TEXT    NOT NULL DEFAULT (datetime('now')),
        skip_until     TEXT    DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS cross_source_insights (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at    TEXT NOT NULL DEFAULT (datetime('now')),
        date           TEXT NOT NULL,
        topic_cluster  TEXT NOT NULL,
        sources        TEXT NOT NULL DEFAULT '[]',
        post_count     INTEGER DEFAULT 0,
        notion_page_id TEXT DEFAULT '',
        published      INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS trend_spikes (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at    TEXT NOT NULL DEFAULT (datetime('now')),
        date           TEXT NOT NULL,
        keyword        TEXT NOT NULL,
        source         TEXT NOT NULL DEFAULT 'combined',
        score          REAL DEFAULT 0.0,
        matched_topic  TEXT DEFAULT '',
        triggered      INTEGER DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_text_date  ON daily_text_costs(date);
    CREATE INDEX IF NOT EXISTS idx_image_date ON daily_image_costs(date);
    CREATE INDEX IF NOT EXISTS idx_draft_date ON draft_analytics(date);
    CREATE INDEX IF NOT EXISTS idx_draft_content_url ON draft_analytics(content_url);
    CREATE INDEX IF NOT EXISTS idx_draft_page_id ON draft_analytics(notion_page_id);
    CREATE INDEX IF NOT EXISTS idx_insight_date ON cross_source_insights(date);
    CREATE INDEX IF NOT EXISTS idx_spike_date ON trend_spikes(date);
"""


def validate_allowed_name(name: str, allowed: set[str] | tuple[str, ...], kind: str) -> str:
    cleaned = name.strip()
    if cleaned not in allowed:
        raise ValueError(f"Unsupported {kind}: {name}")
    return cleaned


def validate_migration_column(table_name: str, column_name: str, ddl: str) -> str:
    safe_table = validate_allowed_name(table_name, set(MIGRATION_COLUMNS), "migration table")
    expected_ddl = MIGRATION_COLUMNS[safe_table].get(column_name)
    if expected_ddl is None:
        raise ValueError(f"Unsupported migration column: {safe_table}.{column_name}")
    if ddl != expected_ddl:
        raise ValueError(f"Unexpected definition for {safe_table}.{column_name}: {ddl}")
    return safe_table


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
    """Idempotently add `column_name` (with `ddl`) to `table_name` if missing."""
    safe_table = validate_migration_column(table_name, column_name, ddl)
    columns = {row["name"] for row in conn.execute(PRAGMA_TABLE_INFO_SQL[safe_table]).fetchall()}
    if column_name not in columns:
        alter_sql = ALTER_TABLE_ADD_SQL.get((safe_table, column_name))
        if alter_sql is None:
            raise ValueError(f"No migration SQL defined for {safe_table}.{column_name}")
        conn.execute(alter_sql)


def init_db(conn: sqlite3.Connection) -> None:
    """Run CREATE TABLE/INDEX script then idempotent column migrations."""
    conn.executescript(CREATE_TABLES_SCRIPT)
    for table_name, columns in MIGRATION_COLUMNS.items():
        for column_name, ddl in columns.items():
            ensure_column(conn, table_name, column_name, ddl)
