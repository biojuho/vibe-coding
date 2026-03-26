"""
QA/QC 러너 유닛 테스트.

qaqc_runner.py와 qaqc_history_db.py의 핵심 로직을 검증합니다.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


# execution 경로 추가
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "execution"))

from qaqc_runner import (  # noqa: E402
    _parse_count,
    _parse_duration,
    _triage_security_issue,
    check_ast,
    determine_verdict,
)
from qaqc_history_db import QaQcHistoryDB  # noqa: E402


# ── _parse_count 테스트 ────────────────────────────────────


class TestParseCount:
    """pytest 출력에서 카운트를 파싱하는 로직 테스트."""

    def test_parse_passed(self):
        output = "287 passed, 1 skipped in 45.32s"
        assert _parse_count(output, "passed") == 287

    def test_parse_failed(self):
        output = "200 passed, 3 failed in 12.5s"
        assert _parse_count(output, "failed") == 3

    def test_parse_skipped(self):
        output = "100 passed, 5 skipped"
        assert _parse_count(output, "skipped") == 5

    def test_parse_missing_keyword(self):
        output = "100 passed in 5.0s"
        assert _parse_count(output, "failed") == 0

    def test_parse_from_multiline(self):
        output = "FAILURES\n=====\n50 passed, 2 failed, 1 skipped in 8.3s"
        assert _parse_count(output, "passed") == 50
        assert _parse_count(output, "failed") == 2


# ── _parse_duration 테스트 ─────────────────────────────────


class TestParseDuration:
    """pytest 출력에서 실행 시간을 파싱하는 로직 테스트."""

    def test_parse_normal(self):
        assert _parse_duration("200 passed in 45.32s") == 45.32

    def test_parse_short(self):
        assert _parse_duration("10 passed in 0.5s") == 0.5

    def test_parse_missing(self):
        assert _parse_duration("no timing info") == 0.0


# ── check_ast 테스트 ───────────────────────────────────────


class TestCheckAst:
    """AST 구문 검증 테스트."""

    def test_valid_python_file(self, tmp_path):
        test_file = tmp_path / "valid.py"
        test_file.write_text("x = 1 + 2\nprint(x)\n", encoding="utf-8")

        with patch("qaqc_runner.ROOT_DIR", tmp_path):
            result = check_ast(["valid.py"])
        assert result["total"] == 1
        assert result["ok"] == 1
        assert result["failures"] == []

    def test_invalid_python_file(self, tmp_path):
        test_file = tmp_path / "invalid.py"
        test_file.write_text("def broken(\n", encoding="utf-8")

        with patch("qaqc_runner.ROOT_DIR", tmp_path):
            result = check_ast(["invalid.py"])
        assert result["total"] == 1
        assert result["ok"] == 0
        assert len(result["failures"]) == 1
        assert "SyntaxError" in result["failures"][0]["error"]

    def test_missing_file(self, tmp_path):
        with patch("qaqc_runner.ROOT_DIR", tmp_path):
            result = check_ast(["nonexistent.py"])
        assert result["total"] == 1
        assert result["ok"] == 0
        assert "not found" in result["failures"][0]["error"]


# ── determine_verdict 테스트 ───────────────────────────────


class TestDetermineVerdict:
    """QC 판정 로직 테스트."""

    def test_all_pass(self):
        projects = {"root": {"passed": 100, "failed": 0, "errors": 0}}
        ast_r = {"failures": []}
        sec_r = {"issues": []}
        assert determine_verdict(projects, ast_r, sec_r) == "APPROVED"

    def test_minor_failure(self):
        projects = {"root": {"passed": 100, "failed": 1, "errors": 0}}
        ast_r = {"failures": []}
        sec_r = {"issues": []}
        assert determine_verdict(projects, ast_r, sec_r) == "CONDITIONALLY_APPROVED"

    def test_major_failure(self):
        projects = {"root": {"passed": 100, "failed": 10, "errors": 5}}
        ast_r = {"failures": []}
        sec_r = {"issues": []}
        assert determine_verdict(projects, ast_r, sec_r) == "REJECTED"

    def test_ast_failure(self):
        projects = {"root": {"passed": 100, "failed": 0, "errors": 0}}
        ast_r = {"failures": [{"file": "bad.py", "error": "syntax"}]}
        sec_r = {"issues": []}
        assert determine_verdict(projects, ast_r, sec_r) == "REJECTED"

    def test_security_issue(self):
        projects = {"root": {"passed": 100, "failed": 0, "errors": 0}}
        ast_r = {"failures": []}
        sec_r = {"issues": [{"file": "x.py", "pattern": "secret"}]}
        assert determine_verdict(projects, ast_r, sec_r) == "CONDITIONALLY_APPROVED"

    def test_triaged_security_issue_does_not_block_approval(self):
        projects = {"root": {"passed": 100, "failed": 0, "errors": 0}}
        ast_r = {"failures": []}
        sec_r = {"issues": [], "triaged_issues": [{"file": "x.py"}], "actionable_issue_count": 0}
        assert determine_verdict(projects, ast_r, sec_r) == "APPROVED"


class TestSecurityTriage:
    def test_known_false_positive_is_triaged(self):
        issue = {
            "file": r"blind-to-x\pipeline\cost_db.py",
            "pattern": "Potential SQL injection via f-string",
            "match_preview": 'f"SELECT * FROM {table}',
        }

        triaged = _triage_security_issue(issue)

        assert triaged["actionable"] is False
        assert triaged["triage"]["classification"] == "false_positive"

    def test_unknown_issue_remains_actionable(self):
        triaged = _triage_security_issue(
            {
                "file": "somewhere/else.py",
                "pattern": "Potential SQL injection via f-string",
                "match_preview": 'f"SELECT * FROM {user_table}',
            }
        )

        assert triaged["actionable"] is True


# ── QaQcHistoryDB 테스트 ──────────────────────────────────


class TestQaQcHistoryDB:
    """SQLite 히스토리 DB 테스트."""

    def test_save_and_retrieve(self, tmp_path):
        db = QaQcHistoryDB(db_path=tmp_path / "test.db")
        recent_ts = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        report = {
            "timestamp": recent_ts,
            "verdict": "APPROVED",
            "total": {"passed": 1556, "failed": 0},
            "elapsed_sec": 45.2,
            "projects": {"root": {"passed": 743}},
            "ast_check": {"ok": 20, "total": 20},
            "security_scan": {"status": "CLEAR"},
            "infrastructure": {"docker": True},
        }
        row_id = db.save_run(report)
        assert row_id > 0

        runs = db.get_recent_runs(days=1)
        assert len(runs) == 1
        assert runs[0]["verdict"] == "APPROVED"
        assert runs[0]["total_passed"] == 1556

    def test_get_latest_run(self, tmp_path):
        db = QaQcHistoryDB(db_path=tmp_path / "test.db")
        older_ts = (datetime.now() - timedelta(days=2)).isoformat(timespec="seconds")
        newer_ts = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        db.save_run({"timestamp": older_ts, "verdict": "REJECTED", "total": {"passed": 100, "failed": 5}})
        db.save_run({"timestamp": newer_ts, "verdict": "APPROVED", "total": {"passed": 200, "failed": 0}})

        latest = db.get_latest_run()
        assert latest is not None
        assert latest["verdict"] == "APPROVED"
        assert latest["total_passed"] == 200

    def test_trend_data(self, tmp_path):
        db = QaQcHistoryDB(db_path=tmp_path / "test.db")
        for i in range(5):
            db.save_run(
                {
                    "timestamp": (datetime.now() - timedelta(days=4 - i)).isoformat(timespec="seconds"),
                    "verdict": "APPROVED",
                    "total": {"passed": 1000 + i * 100, "failed": 0},
                }
            )

        trend = db.get_trend_data(days=30)
        assert len(trend) == 5
        assert trend[0]["passed"] == 1000
        assert trend[4]["passed"] == 1400

    def test_empty_db(self, tmp_path):
        db = QaQcHistoryDB(db_path=tmp_path / "empty.db")
        assert db.get_latest_run() is None
        assert db.get_recent_runs() == []
        assert db.get_trend_data() == []
