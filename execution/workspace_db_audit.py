"""Audit and tune the consolidated workspace SQLite database.

Background: the 8-DB consolidation (memory note `workspace_db_consolidation.md`)
left every logical alias pointing at `.tmp/workspace.db`. The biggest tables
(`top_debtors`, `scrape_quality_log`, `api_calls`) had no covering indexes, and
the heavy query patterns from `api_usage_tracker.py`, `debt_history_db.py`, and
`debug_history_db.py` filter by date or foreign key columns that were missing
from `sqlite_master`. This script reports the current schema/index state and
optionally applies a curated set of recommended indexes.

Recommended indexes are scoped to query patterns that already exist in code,
not speculative ones:

| Table                | Index                                            | Trigger query                                   |
|----------------------|--------------------------------------------------|-------------------------------------------------|
| api_calls            | (timestamp)                                      | api_usage_tracker WHERE timestamp >= ?          |
| api_calls            | (provider, timestamp)                            | api_usage_tracker GROUP BY provider since ts    |
| top_debtors          | (audit_id, score DESC)                           | debt_history_db.get_latest_top_debtors          |
| scrape_quality_log   | (logged_at)                                      | debug_history_db cleanup + analytics            |
| debug_entries        | (created_at)                                     | debug_history_db.get_entries date filters       |
| debug_entries        | (module, created_at)                             | get_recent_for_symptom dedup probe              |
| stats_history        | (content_id, collected_at)                       | result_tracker_db history fetch                 |

Usage:
    python execution/workspace_db_audit.py --report          # current state
    python execution/workspace_db_audit.py --apply           # idempotent CREATE IF NOT EXISTS
    python execution/workspace_db_audit.py --apply --json    # machine output
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
WORKSPACE_DB_DEFAULT = REPO_ROOT_DEFAULT / ".tmp" / "workspace.db"


@dataclass(frozen=True)
class IndexSpec:
    name: str
    table: str
    columns: str  # raw SQL fragment after the table name, e.g. "(timestamp)"

    def create_sql(self) -> str:
        return f"CREATE INDEX IF NOT EXISTS {self.name} ON {self.table}{self.columns}"


RECOMMENDED_INDEXES: tuple[IndexSpec, ...] = (
    IndexSpec("idx_api_calls_timestamp", "api_calls", "(timestamp)"),
    IndexSpec("idx_api_calls_provider_ts", "api_calls", "(provider, timestamp)"),
    IndexSpec("idx_top_debtors_audit_score", "top_debtors", "(audit_id, score DESC)"),
    IndexSpec("idx_scrape_quality_logged_at", "scrape_quality_log", "(logged_at)"),
    IndexSpec("idx_debug_entries_created_at", "debug_entries", "(created_at)"),
    IndexSpec(
        "idx_debug_entries_module_created",
        "debug_entries",
        "(module, created_at)",
    ),
    IndexSpec(
        "idx_stats_history_content_collected",
        "stats_history",
        "(content_id, collected_at)",
    ),
)


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r["name"] for r in rows]


def list_indexes(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT name, tbl_name, sql FROM sqlite_master "
        "WHERE type='index' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY tbl_name, name"
    ).fetchall()
    return [dict(r) for r in rows]


def table_row_counts(conn: sqlite3.Connection, tables: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in tables:
        # Identifier is sourced from sqlite_master and verified against the
        # whitelist of existing tables — safe to interpolate.
        cur = conn.execute(f"SELECT COUNT(*) AS n FROM {table}")  # noqa: S608
        counts[table] = int(cur.fetchone()["n"])
    return counts


def existing_index_names(conn: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in list_indexes(conn)}


def apply_indexes(
    conn: sqlite3.Connection,
    specs: tuple[IndexSpec, ...] = RECOMMENDED_INDEXES,
) -> dict:
    """Apply recommended indexes idempotently. Skips specs whose table is missing."""
    tables = set(list_tables(conn))
    before = existing_index_names(conn)
    created: list[str] = []
    skipped_missing_table: list[str] = []
    skipped_already_present: list[str] = []
    for spec in specs:
        if spec.table not in tables:
            skipped_missing_table.append(spec.name)
            continue
        if spec.name in before:
            skipped_already_present.append(spec.name)
            continue
        conn.execute(spec.create_sql())
        created.append(spec.name)
    conn.commit()
    return {
        "created": created,
        "skipped_already_present": skipped_already_present,
        "skipped_missing_table": skipped_missing_table,
    }


@dataclass
class AuditReport:
    db_path: str
    tables: list[str]
    row_counts: dict[str, int]
    indexes: list[dict]
    recommended: list[dict]
    missing_recommended: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def audit(db_path: Path, specs: tuple[IndexSpec, ...] = RECOMMENDED_INDEXES) -> AuditReport:
    conn = _connect(db_path)
    try:
        tables = list_tables(conn)
        existing = existing_index_names(conn)
        missing = [spec.name for spec in specs if spec.table in set(tables) and spec.name not in existing]
        return AuditReport(
            db_path=str(db_path),
            tables=tables,
            row_counts=table_row_counts(conn, tables),
            indexes=list_indexes(conn),
            recommended=[{"name": s.name, "table": s.table, "columns": s.columns} for s in specs],
            missing_recommended=missing,
        )
    finally:
        conn.close()


def run(
    db_path: Path,
    *,
    apply: bool,
    specs: tuple[IndexSpec, ...] = RECOMMENDED_INDEXES,
) -> dict:
    if not db_path.exists():
        return {"status": "skip", "reason": f"DB not found: {db_path}"}
    if apply:
        conn = _connect(db_path)
        try:
            result = apply_indexes(conn, specs)
        finally:
            conn.close()
        return {
            "status": "applied",
            "db_path": str(db_path),
            **result,
        }
    return {"status": "report", **audit(db_path, specs).to_dict()}


def render_text(result: dict) -> str:
    if result.get("status") == "skip":
        return f"[workspace-db-audit] skip: {result.get('reason')}"
    if result.get("status") == "applied":
        lines = [f"[workspace-db-audit] applied to {result['db_path']}"]
        if result["created"]:
            lines.append(f"  created: {', '.join(result['created'])}")
        else:
            lines.append("  created: (none — all recommended indexes already present)")
        if result["skipped_already_present"]:
            lines.append(f"  skipped (already present): {len(result['skipped_already_present'])}")
        if result["skipped_missing_table"]:
            lines.append(f"  skipped (table missing): {', '.join(result['skipped_missing_table'])}")
        return "\n".join(lines)
    # report
    lines = [
        f"[workspace-db-audit] {result['db_path']}",
        f"  tables: {len(result['tables'])}",
        f"  indexes: {len(result['indexes'])}",
        f"  missing recommended: {len(result['missing_recommended'])}",
    ]
    if result["missing_recommended"]:
        for name in result["missing_recommended"]:
            lines.append(f"    - {name}")
    nonzero = sorted(
        ((t, n) for t, n in result["row_counts"].items() if n > 0),
        key=lambda kv: kv[1],
        reverse=True,
    )
    if nonzero:
        lines.append("  top tables by rows:")
        for table, n in nonzero[:5]:
            lines.append(f"    - {table}: {n}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit and tune the consolidated workspace SQLite database.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=WORKSPACE_DB_DEFAULT,
        help=f"Path to workspace.db (default: {WORKSPACE_DB_DEFAULT})",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--report",
        action="store_true",
        help="Report current schema/index state without modifying the DB (default).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply recommended indexes idempotently (CREATE IF NOT EXISTS).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    result = run(args.db, apply=args.apply)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
