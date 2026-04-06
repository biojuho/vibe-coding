"""
Debt History DB - SQLite time-series storage for VibeDebt audit results.

Tracks TDR, dimension scores, and top debtors over time for trend analysis.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from execution.vibe_debt_auditor import AuditResult

_WORKSPACE_DIR = Path(__file__).resolve().parents[1]
_TMP_ROOT = _WORKSPACE_DIR.parent / ".tmp"

_DB_FILENAME = "workspace.db"


class DebtHistoryDB:
    """Manages the SQLite database for debt audit history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (_TMP_ROOT / _DB_FILENAME)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS audit_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    overall_tdr REAL NOT NULL,
                    overall_grade TEXT NOT NULL,
                    total_files INTEGER NOT NULL,
                    total_principal_hours REAL NOT NULL,
                    total_interest_monthly_hours REAL NOT NULL,
                    scan_duration_seconds REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS project_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_id INTEGER NOT NULL REFERENCES audit_snapshots(id),
                    project_name TEXT NOT NULL,
                    file_count INTEGER NOT NULL,
                    total_lines INTEGER NOT NULL,
                    total_code_lines INTEGER NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    tdr_percent REAL NOT NULL,
                    tdr_grade TEXT NOT NULL,
                    total_principal_minutes REAL NOT NULL,
                    total_interest_monthly REAL NOT NULL,
                    dimension_averages_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS top_debtors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_id INTEGER NOT NULL REFERENCES audit_snapshots(id),
                    project_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    score REAL NOT NULL,
                    principal_minutes REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_snapshots(timestamp);
                CREATE INDEX IF NOT EXISTS idx_proj_snap ON project_snapshots(audit_id, project_name);
            """)

    def record_audit(self, result: "AuditResult") -> int:
        """Persist a full audit result. Returns the audit_id."""
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO audit_snapshots
                   (timestamp, overall_tdr, overall_grade, total_files,
                    total_principal_hours, total_interest_monthly_hours, scan_duration_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.timestamp,
                    result.overall_tdr,
                    result.overall_grade,
                    result.total_files,
                    result.total_principal_hours,
                    result.total_interest_monthly_hours,
                    result.scan_duration_seconds,
                ),
            )
            audit_id = cur.lastrowid

            for proj in result.projects:
                conn.execute(
                    """INSERT INTO project_snapshots
                       (audit_id, project_name, file_count, total_lines, total_code_lines,
                        avg_score, max_score, tdr_percent, tdr_grade,
                        total_principal_minutes, total_interest_monthly, dimension_averages_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        audit_id,
                        proj.name,
                        proj.file_count,
                        proj.total_lines,
                        proj.total_code_lines,
                        proj.avg_score,
                        proj.max_score,
                        proj.tdr_percent,
                        proj.tdr_grade,
                        proj.total_principal_minutes,
                        proj.total_interest_monthly,
                        json.dumps(proj.dimension_averages, ensure_ascii=False),
                    ),
                )

                for debtor in proj.top_debtors[:10]:
                    conn.execute(
                        """INSERT INTO top_debtors
                           (audit_id, project_name, file_path, score, principal_minutes)
                           VALUES (?, ?, ?, ?, ?)""",
                        (audit_id, proj.name, debtor["file"], debtor["score"], debtor["principal_min"]),
                    )

        return audit_id

    def get_trend_data(self, days: int = 30) -> List[Dict]:
        """Get TDR trend data for the last N days."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT timestamp, overall_tdr, overall_grade, total_files,
                          total_principal_hours, total_interest_monthly_hours
                   FROM audit_snapshots
                   WHERE timestamp >= datetime('now', ?)
                   ORDER BY timestamp ASC""",
                (f"-{days} days",),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_project_trend(self, project_name: str, days: int = 30) -> List[Dict]:
        """Get per-project TDR trend."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT a.timestamp, p.tdr_percent, p.tdr_grade, p.avg_score,
                          p.max_score, p.file_count, p.dimension_averages_json
                   FROM project_snapshots p
                   JOIN audit_snapshots a ON a.id = p.audit_id
                   WHERE p.project_name = ? AND a.timestamp >= datetime('now', ?)
                   ORDER BY a.timestamp ASC""",
                (project_name, f"-{days} days"),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["dimension_averages"] = json.loads(d.pop("dimension_averages_json", "{}"))
            result.append(d)
        return result

    def get_latest_top_debtors(self, project_name: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get top debtor files from the latest audit."""
        with self._connect() as conn:
            latest = conn.execute("SELECT MAX(id) FROM audit_snapshots").fetchone()
            if not latest or not latest[0]:
                return []
            audit_id = latest[0]

            query = "SELECT * FROM top_debtors WHERE audit_id = ?"
            params: list = [audit_id]
            if project_name:
                query += " AND project_name = ?"
                params.append(project_name)
            query += " ORDER BY score DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_consecutive_increases(self, threshold: int = 3) -> bool:
        """Check if TDR has increased for N consecutive audits."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT overall_tdr FROM audit_snapshots ORDER BY id DESC LIMIT ?",
                (threshold + 1,),
            ).fetchall()

        if len(rows) < threshold + 1:
            return False

        tdrs = [r["overall_tdr"] for r in rows]
        # Check if each is higher than the next (older)
        for i in range(threshold):
            if tdrs[i] <= tdrs[i + 1]:
                return False
        return True
