"""Unit tests for `execution/workspace_db_audit.py`."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "execution" / "workspace_db_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("workspace_db_audit", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["workspace_db_audit"] = module
    spec.loader.exec_module(module)
    return module


audit = _load_module()


def _build_fixture_db(path: Path) -> None:
    """Mirror the subset of workspace.db schema the audit cares about."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE api_calls (
                id INTEGER PRIMARY KEY,
                provider TEXT,
                tokens_input INTEGER,
                tokens_output INTEGER,
                cost_usd REAL,
                timestamp TEXT
            );
            CREATE TABLE top_debtors (
                id INTEGER PRIMARY KEY,
                audit_id INTEGER NOT NULL,
                project_name TEXT,
                file_path TEXT,
                score REAL
            );
            CREATE TABLE scrape_quality_log (
                id INTEGER PRIMARY KEY,
                logged_at TEXT,
                source TEXT,
                quality_score REAL
            );
            CREATE TABLE debug_entries (
                id INTEGER PRIMARY KEY,
                created_at TEXT,
                module TEXT,
                symptom TEXT
            );
            CREATE TABLE stats_history (
                id INTEGER PRIMARY KEY,
                content_id INTEGER,
                collected_at TEXT
            );
            -- An unrelated table that should be left alone.
            CREATE TABLE misc (id INTEGER PRIMARY KEY, payload TEXT);
            """
        )
        conn.executemany(
            "INSERT INTO api_calls (provider, timestamp) VALUES (?, ?)",
            [("openai", "2026-05-01"), ("anthropic", "2026-05-02")],
        )
        conn.commit()
    finally:
        conn.close()


def test_run_report_lists_recommended_indexes(tmp_path):
    db = tmp_path / "workspace.db"
    _build_fixture_db(db)

    result = audit.run(db, apply=False)
    assert result["status"] == "report"
    assert set(result["tables"]) >= {
        "api_calls",
        "top_debtors",
        "scrape_quality_log",
        "debug_entries",
        "stats_history",
        "misc",
    }
    assert result["row_counts"]["api_calls"] == 2
    expected_missing = {spec.name for spec in audit.RECOMMENDED_INDEXES}
    assert set(result["missing_recommended"]) == expected_missing


def test_run_apply_creates_indexes(tmp_path):
    db = tmp_path / "workspace.db"
    _build_fixture_db(db)

    result = audit.run(db, apply=True)
    assert result["status"] == "applied"
    assert set(result["created"]) == {spec.name for spec in audit.RECOMMENDED_INDEXES}

    conn = sqlite3.connect(db)
    try:
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        }
    finally:
        conn.close()
    assert {spec.name for spec in audit.RECOMMENDED_INDEXES}.issubset(names)


def test_apply_is_idempotent(tmp_path):
    db = tmp_path / "workspace.db"
    _build_fixture_db(db)

    first = audit.run(db, apply=True)
    second = audit.run(db, apply=True)
    assert second["status"] == "applied"
    assert second["created"] == []
    assert sorted(second["skipped_already_present"]) == sorted(first["created"])


def test_apply_skips_missing_tables(tmp_path):
    db = tmp_path / "workspace.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.execute("CREATE TABLE api_calls (id INTEGER PRIMARY KEY, timestamp TEXT, provider TEXT)")
        conn.commit()
    finally:
        conn.close()

    result = audit.run(db, apply=True)
    assert result["status"] == "applied"
    # Only api_calls indexes should land; the rest are missing-table skips.
    assert set(result["created"]) == {
        "idx_api_calls_timestamp",
        "idx_api_calls_provider_ts",
    }
    expected_missing = {spec.name for spec in audit.RECOMMENDED_INDEXES} - set(result["created"])
    assert set(result["skipped_missing_table"]) == expected_missing


def test_run_skip_when_db_missing(tmp_path):
    result = audit.run(tmp_path / "absent.db", apply=False)
    assert result["status"] == "skip"


def test_render_text_report_summary(tmp_path):
    db = tmp_path / "workspace.db"
    _build_fixture_db(db)
    result = audit.run(db, apply=False)
    text = audit.render_text(result)
    assert "tables:" in text
    assert "missing recommended:" in text
    # api_calls has the only nonzero row count and should appear in the summary.
    assert "api_calls: 2" in text


def test_render_text_apply_summary(tmp_path):
    db = tmp_path / "workspace.db"
    _build_fixture_db(db)
    result = audit.run(db, apply=True)
    text = audit.render_text(result)
    assert "applied to" in text
    assert "created:" in text


def test_index_spec_create_sql_is_idempotent_capable():
    spec = audit.IndexSpec("idx_foo", "tbl", "(col)")
    assert spec.create_sql() == "CREATE INDEX IF NOT EXISTS idx_foo ON tbl(col)"
