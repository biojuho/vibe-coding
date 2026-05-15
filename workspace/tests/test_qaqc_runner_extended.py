from __future__ import annotations

import json
import re
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
    assert calls["cmd"][:5] == ["python", "-X", "utf8", "-m", "pytest"]
    assert "-o" in calls["cmd"]
    assert "addopts=" in calls["cmd"]
    assert str(first) in calls["cmd"]
    assert str(second) in calls["cmd"]


def test_run_pytest_skips_when_all_test_paths_missing(tmp_path) -> None:
    result = qaqc_runner.run_pytest(
        "root",
        {"test_paths": [tmp_path / "missing"], "cwd": tmp_path},
    )

    assert result["status"] == "SKIP"
    assert "Test directory not found" in result["message"]


def test_run_pytest_aggregates_split_runs_and_passes_extra_args(tmp_path, monkeypatch) -> None:
    first = tmp_path / "tests"
    second = tmp_path / "execution-tests"
    first.mkdir()
    second.mkdir()

    calls: list[tuple[list[str], dict[str, object]]] = []
    responses = iter(
        [
            SimpleNamespace(stdout="3 passed, 1 skipped in 1.5s", stderr="", returncode=0),
            SimpleNamespace(stdout="2 passed in 0.5s", stderr="", returncode=0),
        ]
    )

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return next(responses)

    monkeypatch.setattr(qaqc_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(qaqc_runner, "VENV_PYTHON", Path("python"))

    result = qaqc_runner.run_pytest(
        "root",
        {
            "test_runs": [
                {"paths": [first]},
                {"paths": [second], "extra_args": ["--ignore=execution/tests/test_sample.py"]},
            ],
            "cwd": tmp_path,
            "timeout": 123,
            "note": "known note",
        },
    )

    assert result["status"] == "PASS"
    assert result["passed"] == 5
    assert result["skipped"] == 1
    assert result["duration_sec"] == 2.0
    assert "known note" in result["message"]
    assert len(result["runs"]) == 2
    assert len(calls) == 2
    assert all(call_kwargs["timeout"] == 123 for _, call_kwargs in calls)
    assert "--ignore=execution/tests/test_sample.py" in calls[1][0]


def test_pytest_command_and_result_helpers(tmp_path, monkeypatch) -> None:
    nested = tmp_path / "tests" / "unit"
    nested.mkdir(parents=True)
    external = tmp_path.parent / "external-tests"

    monkeypatch.setattr(qaqc_runner, "VENV_PYTHON", Path("python"))

    paths = qaqc_runner._pytest_command_paths([nested, external], tmp_path, relative_to_cwd=True)
    cmd = qaqc_runner._build_pytest_command("root", paths, ["--ignore=x.py"])
    result = qaqc_runner._pytest_result_from_output("4 passed, 1 skipped in 2.5s", returncode=0)

    assert paths == [str(Path("tests") / "unit"), str(external)]
    assert cmd[:5] == ["python", "-X", "utf8", "-m", "pytest"]
    assert "--maxfail=50" in cmd
    assert "--ignore=x.py" in cmd
    assert result == {
        "passed": 4,
        "failed": 0,
        "skipped": 1,
        "errors": 0,
        "status": "PASS",
        "duration_sec": 2.5,
    }
    assert qaqc_runner._pytest_status(returncode=0, passed=0, failed=0, errors=0) == "FAIL"


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


def test_check_infrastructure_parses_localized_scheduler_status(monkeypatch) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if cmd[0] == "docker":
            raise FileNotFoundError("docker missing")
        if cmd[0] == "schtasks":
            return SimpleNamespace(
                stdout='"\\\\BlindToX_0500","2026-03-26 오전 5:00:00","준비"\n'
                '"\\\\BlindToX_Pipeline","2026-03-25 오전 9:00:00","Ready"\n',
                stderr="",
                returncode=0,
            )
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(qaqc_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(qaqc_runner.locale, "getencoding", lambda: "cp949")
    monkeypatch.setattr(qaqc_runner.locale, "getpreferredencoding", lambda _=False: "utf-8")

    import urllib.request

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    result = qaqc_runner.check_infrastructure()

    scheduler_call = next(kwargs for cmd, kwargs in calls if cmd[0] == "schtasks")
    assert scheduler_call["encoding"] == "cp949"
    assert result["docker"] is False
    assert result["ollama"] is False
    assert result["scheduler"] == {"ready": 2, "total": 2}


def test_run_qaqc_writes_report_and_saves_history(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        qaqc_runner,
        "run_pytest",
        lambda name, config: {"passed": 5, "failed": 0, "skipped": 1, "errors": 0, "status": "PASS"},
    )
    monkeypatch.setattr(qaqc_runner, "check_ast", lambda modules: {"total": 1, "ok": 1, "failures": []})
    monkeypatch.setattr(qaqc_runner, "security_scan", lambda: {"status": "CLEAR", "issues": []})
    monkeypatch.setattr(qaqc_runner, "governance_scan", lambda: {"status": "CLEAR", "status_detail": "CLEAR"})
    monkeypatch.setattr(qaqc_runner, "determine_verdict", lambda *args: "APPROVED")

    saved_reports: list[dict] = []
    fake_qaqc_db = ModuleType("qaqc_history_db")

    class FakeHistoryDB:
        def save_run(self, report: dict) -> int:
            saved_reports.append(report)
            return 1

    fake_qaqc_db.QaQcHistoryDB = FakeHistoryDB
    monkeypatch.setitem(sys.modules, "execution.qaqc_history_db", fake_qaqc_db)

    output_path = tmp_path / "qaqc.json"
    report = qaqc_runner.run_qaqc(target_projects=["root"], skip_infra=True, output_file=str(output_path))

    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["verdict"] == "APPROVED"
    assert persisted["projects"]["root"]["passed"] == 5
    assert persisted["governance_scan"]["status"] == "CLEAR"
    assert saved_reports[0]["verdict"] == "APPROVED"


def test_security_scan_keeps_machine_status_clear_for_triaged_only_issue(tmp_path, monkeypatch) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text('query = f"SELECT * FROM {table}"\n', encoding="utf-8")

    monkeypatch.setattr(qaqc_runner, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        qaqc_runner,
        "_triage_security_issue",
        lambda issue: {
            **issue,
            "actionable": False,
            "triage": {"classification": "false_positive", "reason": "test rule"},
        },
    )

    result = qaqc_runner.security_scan()

    assert result["status"] == "CLEAR"
    assert result["status_detail"] == "CLEAR (1 triaged issue(s))"
    assert result["issues"] == []
    assert result["triaged_issue_count"] == 1


def test_security_scan_helpers_filter_and_build_issue(tmp_path) -> None:
    sample = tmp_path / "sample.py"
    content = "api_key = 'abcdefghijklmnopqrst'\n"
    sample.write_text(content, encoding="utf-8")
    pattern_str, description, flags = qaqc_runner.SECURITY_PATTERNS[0]
    match = re.search(pattern_str, content, flags)
    assert match is not None

    issue = qaqc_runner._security_issue_from_match(
        filepath=sample,
        root_dir=tmp_path,
        description=description,
        content=content,
        lines=content.splitlines(),
        match=match,
    )

    assert issue == {
        "file": "sample.py",
        "pattern": "Hardcoded secret detected",
        "match_preview": "api_key = 'abcdefghijklmnopqrst'",
    }

    test_file = tmp_path / "test_sample.py"
    test_file.write_text(content, encoding="utf-8")
    assert qaqc_runner._scan_security_file(test_file, tmp_path) == []


def test_security_scan_result_summarizes_actionable_and_triaged(monkeypatch) -> None:
    raw_issues = [{"file": "a.py"}, {"file": "b.py"}]

    def fake_triage(issue):
        if issue["file"] == "a.py":
            return {**issue, "actionable": False}
        return {**issue, "actionable": True}

    monkeypatch.setattr(qaqc_runner, "_triage_security_issue", fake_triage)

    result = qaqc_runner._security_scan_result(raw_issues)

    assert result["status"] == "WARNING"
    assert result["actionable_issue_count"] == 1
    assert result["triaged_issue_count"] == 1


def test_governance_scan_reports_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        qaqc_runner,
        "run_governance_checks",
        lambda: [
            {"name": "directive_mapping", "status": "fail"},
            {"name": "task_backlog_alignment", "status": "ok"},
        ],
    )
    monkeypatch.setattr(
        qaqc_runner,
        "summarize_governance_results",
        lambda results: {"overall": "fail", "counts": {"ok": 1, "warn": 0, "fail": 1}, "total": 2},
    )

    result = qaqc_runner.governance_scan()

    assert result["status"] == "FAIL"
    assert len(result["flagged_checks"]) == 1


def test_scheduler_and_report_helpers() -> None:
    scheduler = qaqc_runner._parse_scheduler_csv(
        '"\\\\BlindToX_0500","time","준비"\n"\\\\Other","time","Ready"\n"\\\\BlindToX_Pipeline","time","Ready"\n'
    )
    assert scheduler == {"ready": 2, "total": 2}

    totals = qaqc_runner._project_totals(
        {
            "root": {"passed": 3, "failed": 0, "errors": 0, "skipped": 1},
            "slow": {"passed": 0, "failed": 0, "errors": 1, "skipped": 0, "status": "TIMEOUT"},
        }
    )
    assert totals == {"passed": 3, "failed": 0, "errors": 1, "skipped": 1, "timeout": ["slow"]}

    report = qaqc_runner._build_report(
        timestamp="2026-05-12T00:00:00",
        verdict="APPROVED",
        elapsed=1.2,
        project_results={"root": {"status": "PASS"}},
        totals=totals,
        ast_result={"ok": 1},
        security_result={"status": "CLEAR"},
        governance_result={"status": "CLEAR"},
        debt_result={},
        infra_result={},
    )
    assert report["total"] == totals
    assert report["projects"]["root"]["status"] == "PASS"


def test_parse_npm_count_handles_tap_and_spec_reporters() -> None:
    tap = "# tests 75\n# pass 75\n# fail 0\n# skipped 0\n# duration_ms 1818.83\n"
    spec = "ℹ tests 75\nℹ pass 73\nℹ fail 2\nℹ skipped 1\nℹ duration_ms 900.5\n"

    assert qaqc_runner._parse_npm_count(tap, "pass") == 75
    assert qaqc_runner._parse_npm_count(tap, "fail") == 0
    assert qaqc_runner._parse_npm_count(spec, "pass") == 73
    assert qaqc_runner._parse_npm_count(spec, "fail") == 2
    assert qaqc_runner._parse_npm_count(spec, "skipped") == 1
    # A test title containing the keyword must not be miscounted.
    assert qaqc_runner._parse_npm_count("ok 1 - pass the payload through\n", "pass") == 0


def test_npm_result_from_output_maps_status_and_duration() -> None:
    passing = "# pass 75\n# fail 0\n# skipped 0\n# duration_ms 2000\n"
    result = qaqc_runner._npm_result_from_output(passing, returncode=0)
    assert result == {
        "passed": 75,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "status": "PASS",
        "duration_sec": 2.0,
    }

    failing = "# pass 70\n# fail 5\n# skipped 0\n"
    failed = qaqc_runner._npm_result_from_output(failing, returncode=1)
    assert failed["status"] == "FAIL"
    assert failed["failed"] == 5


def test_run_npm_test_skips_when_package_json_missing(tmp_path) -> None:
    result = qaqc_runner.run_npm_test("hanwoo-dashboard", {"cwd": tmp_path})
    assert result["status"] == "SKIP"


def test_run_npm_test_parses_subprocess_output(tmp_path, monkeypatch) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    calls: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["cwd"] = kwargs["cwd"]
        return SimpleNamespace(stdout="# pass 75\n# fail 0\n# skipped 0\n", stderr="", returncode=0)

    monkeypatch.setattr(qaqc_runner.subprocess, "run", fake_run)

    result = qaqc_runner.run_npm_test("hanwoo-dashboard", {"cwd": tmp_path, "timeout": 600})

    assert result["status"] == "PASS"
    assert result["passed"] == 75
    assert calls["cmd"][1:] == ["test"]
    assert calls["cwd"] == str(tmp_path)
