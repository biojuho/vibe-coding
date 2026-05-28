"""Direct unit tests for `pipeline.cost_db_schema`.

The schema module was split from `pipeline.cost_db` (T-1199) so the DDL
surface can be exercised against an in-memory SQLite connection without
constructing CostDatabase. These tests guard the contract that
`init_db()` and `ensure_column()` honor `MIGRATION_COLUMNS` exactly.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.cost_db_schema import (  # noqa: E402
    MIGRATION_COLUMNS,
    ensure_column,
    init_db,
    validate_allowed_name,
    validate_migration_column,
)


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_init_db_creates_all_expected_tables() -> None:
    """init_db() must produce the full base schema on a fresh connection."""
    conn = _fresh_conn()
    try:
        init_db(conn)
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    finally:
        conn.close()
    assert {
        "daily_text_costs",
        "daily_image_costs",
        "draft_analytics",
        "provider_failures",
        "cross_source_insights",
        "trend_spikes",
    } <= tables


def test_init_db_applies_every_migration_column() -> None:
    """Every entry in MIGRATION_COLUMNS must be present after init_db()."""
    conn = _fresh_conn()
    try:
        init_db(conn)
        for table_name, columns in MIGRATION_COLUMNS.items():
            actual = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
            missing = set(columns) - actual
            assert not missing, f"{table_name} missing migration columns: {missing}"
    finally:
        conn.close()


def test_init_db_is_idempotent() -> None:
    """Running init_db() twice must not raise (CREATE IF NOT EXISTS + ALTER guard)."""
    conn = _fresh_conn()
    try:
        init_db(conn)
        init_db(conn)
    finally:
        conn.close()


def test_ensure_column_is_idempotent_when_column_already_present() -> None:
    conn = _fresh_conn()
    try:
        init_db(conn)  # populates draft_analytics.content_url
        ensure_column(conn, "draft_analytics", "content_url", "TEXT DEFAULT ''")  # second pass no-op
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(draft_analytics)").fetchall()}
        # Single-instance, not double-added.
        assert sum(1 for c in columns if c == "content_url") == 1
    finally:
        conn.close()


def test_validate_allowed_name_rejects_non_member_and_strips_whitespace() -> None:
    assert validate_allowed_name("  draft_analytics  ", {"draft_analytics"}, "table") == "draft_analytics"
    with pytest.raises(ValueError, match="Unsupported table"):
        validate_allowed_name("evil_table", {"draft_analytics"}, "table")


def test_validate_migration_column_rejects_unknown_column_and_definition_drift() -> None:
    with pytest.raises(ValueError, match="Unsupported migration column"):
        validate_migration_column("draft_analytics", "unknown_col", "TEXT DEFAULT ''")
    with pytest.raises(ValueError, match="Unexpected definition"):
        # known table+column but altered DDL
        validate_migration_column("draft_analytics", "content_url", "TEXT")
