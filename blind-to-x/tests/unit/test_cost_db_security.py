from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.cost_db import CostDatabase  # noqa: E402


def _draft_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE draft_analytics (id INTEGER PRIMARY KEY AUTOINCREMENT)")
    return conn


def test_ensure_column_rejects_unknown_table() -> None:
    conn = _draft_conn()
    try:
        with pytest.raises(ValueError, match="Unsupported migration table"):
            CostDatabase._ensure_column(conn, "unexpected_table", "content_url", "TEXT DEFAULT ''")
    finally:
        conn.close()


def test_ensure_column_rejects_unexpected_definition() -> None:
    conn = _draft_conn()
    try:
        with pytest.raises(ValueError, match="Unexpected definition"):
            CostDatabase._ensure_column(conn, "draft_analytics", "content_url", "TEXT")
    finally:
        conn.close()


def test_ensure_column_adds_known_column() -> None:
    conn = _draft_conn()
    try:
        CostDatabase._ensure_column(conn, "draft_analytics", "content_url", "TEXT DEFAULT ''")
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(draft_analytics)").fetchall()}
        assert "content_url" in columns
    finally:
        conn.close()
