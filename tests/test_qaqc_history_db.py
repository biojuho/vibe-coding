"""QaQcHistoryDB 단위 테스트."""

from pathlib import Path

from execution.qaqc_history_db import QaQcHistoryDB


def _make_db(tmp_path: Path) -> QaQcHistoryDB:
    return QaQcHistoryDB(db_path=tmp_path / "test_qaqc.db")


def _sample_report(**overrides) -> dict:
    base = {
        "timestamp": "2026-03-22T12:00:00",
        "verdict": "PASS",
        "total": {"passed": 100, "failed": 0},
        "elapsed_sec": 5.2,
        "projects": {"root": {"passed": 80, "failed": 0}},
        "ast_check": {"ok": True},
        "security_scan": {"issues": 0},
        "infrastructure": {"status": "healthy"},
    }
    base.update(overrides)
    return base


class TestQaQcHistoryDB:
    def test_init_creates_db(self, tmp_path: Path):
        db = _make_db(tmp_path)
        assert db.db_path.exists()

    def test_save_and_get_latest(self, tmp_path: Path):
        db = _make_db(tmp_path)
        report = _sample_report()
        row_id = db.save_run(report)
        assert row_id >= 1

        latest = db.get_latest_run()
        assert latest is not None
        assert latest["verdict"] == "PASS"
        assert latest["total_passed"] == 100

    def test_get_recent_runs(self, tmp_path: Path):
        db = _make_db(tmp_path)
        db.save_run(_sample_report(verdict="PASS"))
        db.save_run(_sample_report(verdict="FAIL", total={"passed": 90, "failed": 10}))

        runs = db.get_recent_runs(days=1)
        assert len(runs) == 2
        assert runs[0]["verdict"] == "FAIL"  # DESC order

    def test_get_recent_runs_empty(self, tmp_path: Path):
        db = _make_db(tmp_path)
        runs = db.get_recent_runs(days=1)
        assert runs == []

    def test_get_trend_data(self, tmp_path: Path):
        db = _make_db(tmp_path)
        db.save_run(_sample_report())
        db.save_run(_sample_report(verdict="FAIL"))

        trend = db.get_trend_data(days=1)
        assert len(trend) == 2
        assert trend[0]["date"] == "2026-03-22"
        assert "passed" in trend[0]

    def test_latest_run_none_when_empty(self, tmp_path: Path):
        db = _make_db(tmp_path)
        assert db.get_latest_run() is None

    def test_projects_json_roundtrip(self, tmp_path: Path):
        db = _make_db(tmp_path)
        db.save_run(_sample_report(projects={"blind-to-x": {"passed": 50}}))
        latest = db.get_latest_run()
        assert latest["projects"]["blind-to-x"]["passed"] == 50
