from __future__ import annotations

import logging
from pathlib import Path

from shorts_maker_v2.utils.cost_tracker import CostTracker


def test_record_and_summary(tmp_path: Path) -> None:
    """레코드 기록 후 summary가 올바른 통계 반환."""
    tracker = CostTracker(logs_dir=tmp_path)

    tracker.record(job_id="j1", cost_usd=0.17, topic="블랙홀", channel="space")
    tracker.record(job_id="j2", cost_usd=0.25, topic="우주", channel="space")

    s = tracker.summary()
    assert s["daily_jobs"] == 2
    assert abs(s["daily_cost_usd"] - 0.42) < 0.01
    assert s["total_jobs"] == 2
    assert abs(s["avg_cost_per_job"] - 0.21) < 0.01


def test_daily_total(tmp_path: Path) -> None:
    """daily_total이 당일 비용만 합산."""
    tracker = CostTracker(logs_dir=tmp_path)

    tracker.record(job_id="j1", cost_usd=0.10, topic="test1")
    tracker.record(job_id="j2", cost_usd=0.20, topic="test2")

    total = tracker.daily_total()
    assert abs(total - 0.30) < 0.01


def test_monthly_total(tmp_path: Path) -> None:
    """monthly_total이 당월 비용만 합산."""
    tracker = CostTracker(logs_dir=tmp_path)

    tracker.record(job_id="j1", cost_usd=0.15, topic="test1")
    tracker.record(job_id="j2", cost_usd=0.35, topic="test2")
    tracker.record(job_id="j3", cost_usd=0.50, topic="test3")

    total = tracker.monthly_total()
    assert abs(total - 1.0) < 0.01


def test_empty_summary(tmp_path: Path) -> None:
    """레코드 없을 때 summary가 0 반환."""
    tracker = CostTracker(logs_dir=tmp_path)
    s = tracker.summary()

    assert s["total_jobs"] == 0
    assert s["total_cost_usd"] == 0.0
    assert s["avg_cost_per_job"] == 0.0


def test_record_with_status(tmp_path: Path) -> None:
    """실패 레코드도 정상 기록."""
    tracker = CostTracker(logs_dir=tmp_path)
    tracker.record(job_id="j1", cost_usd=0.05, topic="test", status="failed")
    tracker.record(job_id="j2", cost_usd=0.10, topic="test2", status="success")

    s = tracker.summary()
    assert s["total_jobs"] == 2
    assert abs(s["total_cost_usd"] - 0.15) < 0.01


def test_print_summary_uses_logger_not_stdout(tmp_path: Path, caplog: object, capsys) -> None:
    """print_summary() emits via logger.info (not print()) so log aggregators capture it."""
    tracker = CostTracker(logs_dir=tmp_path)
    tracker.record(job_id="j1", cost_usd=0.10, topic="test")

    with caplog.at_level(logging.INFO, logger="shorts_maker_v2.utils.cost_tracker"):
        tracker.print_summary()

    # Must appear in log records, not stdout
    assert any("비용 대시보드" in r.message for r in caplog.records)
    out, _ = capsys.readouterr()
    assert "비용 대시보드" not in out


def test_print_summary_includes_cost_values(tmp_path: Path, caplog: object) -> None:
    """print_summary() log output includes date, job counts, and cost figures."""
    tracker = CostTracker(logs_dir=tmp_path)
    tracker.record(job_id="j1", cost_usd=0.1234, topic="test")

    with caplog.at_level(logging.INFO, logger="shorts_maker_v2.utils.cost_tracker"):
        tracker.print_summary()

    combined = " ".join(r.message for r in caplog.records)
    assert "1" in combined  # job count
    assert "0.1234" in combined  # cost value
