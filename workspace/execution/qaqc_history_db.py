"""
QA/QC 실행 히스토리 SQLite 저장소.

qaqc_runner.py의 결과를 저장하고, 트렌드 분석용 데이터를 제공합니다.

Usage:
    from qaqc_history_db import QaQcHistoryDB
    db = QaQcHistoryDB()
    db.save_run(report_dict)
    recent = db.get_recent_runs(days=30)
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# DB 파일 위치
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "workspace.db"


class QaQcHistoryDB:
    """QA/QC 실행 이력을 SQLite에 저장합니다."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """테이블을 초기화합니다."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS qaqc_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    total_passed INTEGER DEFAULT 0,
                    total_failed INTEGER DEFAULT 0,
                    elapsed_sec REAL DEFAULT 0,
                    projects_json TEXT,
                    ast_json TEXT,
                    security_json TEXT,
                    infra_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_qaqc_timestamp
                ON qaqc_runs(timestamp)
            """)

    def save_run(self, report: dict) -> int:
        """QA/QC 실행 결과를 저장합니다. 삽입된 ID를 반환합니다."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                INSERT INTO qaqc_runs
                    (timestamp, verdict, total_passed, total_failed,
                     elapsed_sec, projects_json, ast_json, security_json, infra_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    report.get("timestamp", datetime.now().isoformat()),
                    report.get("verdict", "UNKNOWN"),
                    report.get("total", {}).get("passed", 0),
                    report.get("total", {}).get("failed", 0),
                    report.get("elapsed_sec", 0),
                    json.dumps(report.get("projects", {}), ensure_ascii=False),
                    json.dumps(report.get("ast_check", {}), ensure_ascii=False),
                    json.dumps(report.get("security_scan", {}), ensure_ascii=False),
                    json.dumps(report.get("infrastructure", {}), ensure_ascii=False),
                ),
            )
            return cursor.lastrowid or 0

    def get_recent_runs(self, days: int = 30, limit: int = 100) -> list[dict]:
        """최근 N일간의 실행 이력을 반환합니다."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM qaqc_runs
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (cutoff, limit),
            ).fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "verdict": row["verdict"],
                    "total_passed": row["total_passed"],
                    "total_failed": row["total_failed"],
                    "elapsed_sec": row["elapsed_sec"],
                    "projects": json.loads(row["projects_json"] or "{}"),
                    "ast": json.loads(row["ast_json"] or "{}"),
                    "security": json.loads(row["security_json"] or "{}"),
                    "infrastructure": json.loads(row["infra_json"] or "{}"),
                }
            )
        return results

    def get_latest_run(self) -> dict | None:
        """가장 최근 실행 결과를 반환합니다."""
        runs = self.get_recent_runs(days=365, limit=1)
        return runs[0] if runs else None

    def get_trend_data(self, days: int = 30) -> list[dict]:
        """트렌드 분석용 요약 데이터를 반환합니다."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT timestamp, verdict, total_passed, total_failed
                FROM qaqc_runs
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """,
                (cutoff,),
            ).fetchall()

        return [
            {
                "date": row["timestamp"][:10],
                "verdict": row["verdict"],
                "passed": row["total_passed"],
                "failed": row["total_failed"],
            }
            for row in rows
        ]
