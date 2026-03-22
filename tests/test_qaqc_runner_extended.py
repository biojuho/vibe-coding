from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import execution.qaqc_runner as qaqc_runner


def test_run_pytest_uses_all_existing_test_paths(tmp_path, monkeypatch) -> None:
    first = tmp_path / "tests"
    second = tmp_path / "execution-tests"
    first.mkdir()
    second.mkdir()

    calls: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["cwd"] = kwargs["cwd"]
        return SimpleNamespace(stdout="3 passed, 1 skipped in 1.5s", stderr="", returncode=0)

    monkeypatch.setattr(qaqc_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(qaqc_runner, "VENV_PYTHON", Path("python"))

    result = qaqc_runner.run_pytest(
        "root",
        {"test_paths": [first, second], "cwd": tmp_path},
    )

    assert result["status"] == "PASS"
    assert result["passed"] == 3
    assert str(first) in calls["cmd"]
    assert str(second) in calls["cmd"]


def test_run_pytest_skips_when_all_test_paths_missing(tmp_path) -> None:
    result = qaqc_runner.run_pytest(
        "root",
        {"test_paths": [tmp_path / "missing"], "cwd": tmp_path},
    )

    assert result["status"] == "SKIP"
    assert "Test directory not found" in result["message"]


def test_check_infrastructure_handles_missing_tools(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("missing tool")

    monkeypatch.setattr(qaqc_runner.subprocess, "run", fake_run)

    import urllib.request

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    result = qaqc_runner.check_infrastructure()

    assert result["docker"] is False
    assert result["ollama"] is False
    assert result["scheduler"] == {"ready": 0, "total": 0}


def test_run_qaqc_writes_report_and_saves_history(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        qaqc_runner,
        "run_pytest",
        lambda name, config: {"passed": 5, "failed": 0, "skipped": 1, "errors": 0, "status": "PASS"},
    )
    monkeypatch.setattr(qaqc_runner, "check_ast", lambda modules: {"total": 1, "ok": 1, "failures": []})
    monkeypatch.setattr(qaqc_runner, "security_scan", lambda: {"status": "CLEAR", "issues": []})
    monkeypatch.setattr(qaqc_runner, "determine_verdict", lambda *args: "APPROVED")

    saved_reports: list[dict] = []
    fake_qaqc_db = ModuleType("qaqc_history_db")

    class FakeHistoryDB:
        def save_run(self, report: dict) -> int:
            saved_reports.append(report)
            return 1

    fake_qaqc_db.QaQcHistoryDB = FakeHistoryDB
    monkeypatch.setitem(sys.modules, "qaqc_history_db", fake_qaqc_db)

    output_path = tmp_path / "qaqc.json"
    report = qaqc_runner.run_qaqc(target_projects=["root"], skip_infra=True, output_file=str(output_path))

    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["verdict"] == "APPROVED"
    assert persisted["projects"]["root"]["passed"] == 5
    assert saved_reports[0]["verdict"] == "APPROVED"
