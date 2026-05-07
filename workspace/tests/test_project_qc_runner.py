from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "execution" / "project_qc_runner.py"
SPEC = importlib.util.spec_from_file_location("project_qc_runner", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def run_main(args: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = MODULE.main(args)
    return code, stdout.getvalue()


def test_default_projects_follow_workspace_active_order() -> None:
    assert MODULE.normalize_project_names(None) == [
        "blind-to-x",
        "shorts-maker-v2",
        "hanwoo-dashboard",
        "knowledge-dashboard",
    ]


def test_build_plan_can_filter_cross_project_checks() -> None:
    plan = MODULE.build_plan(["blind-to-x", "hanwoo-dashboard"], ["build"])

    assert [(item.project, item.check.id) for item in plan] == [("hanwoo-dashboard", "build")]


def test_json_dry_run_prints_commands_without_executing() -> None:
    code, output = run_main(["--project", "blind-to-x", "--dry-run", "--json"])
    payload = json.loads(output)

    assert code == 0
    assert payload["status"] == "planned"
    assert payload["plan"][0]["project"] == "blind-to-x"
    assert "pytest" in payload["plan"][0]["command"]


def test_run_plan_reports_subprocess_failures(monkeypatch) -> None:
    plan = MODULE.build_plan(["knowledge-dashboard"], ["test"])

    def fake_run(*args, **kwargs):
        return MODULE.subprocess.CompletedProcess(args[0], 1, stdout="failed stdout", stderr="failed stderr")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    results = MODULE.run_plan(plan, timeout_seconds=5, stop_on_failure=False)

    assert MODULE.exit_code_for_results(results) == 1
    assert results[0]["status"] == "failed"
    assert results[0]["stdout_tail"] == "failed stdout"


def test_run_plan_reports_missing_executable(monkeypatch) -> None:
    plan = MODULE.build_plan(["knowledge-dashboard"], ["test"])

    monkeypatch.setattr(MODULE, "resolve_command", lambda command: command)
    monkeypatch.setattr(
        MODULE.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("nope"))
    )

    results = MODULE.run_plan(plan, timeout_seconds=5, stop_on_failure=False)

    assert MODULE.exit_code_for_results(results) == 1
    assert results[0]["status"] == "failed"
    assert "nope" in results[0]["stderr_tail"]


def test_list_json_includes_all_project_commands() -> None:
    code, output = run_main(["--list", "--json"])
    payload = json.loads(output)

    assert code == 0
    assert payload["status"] == "configured"
    assert "shorts-maker-v2" in payload["projects"]
    assert [check["id"] for check in payload["projects"]["hanwoo-dashboard"]["checks"]] == [
        "test",
        "lint",
        "build",
    ]
