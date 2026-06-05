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


def _passed_result(project: str, check: str, *, passed: int = 2) -> dict[str, object]:
    return {
        "project": project,
        "check": check,
        "status": "passed",
        "returncode": 0,
        "duration_seconds": 1.0,
        "command": f"{project} {check}",
        "resolved_command": f"{project} {check}",
        "stdout_tail": f"{passed} passed in 1.0s",
        "stderr_tail": "",
    }


def _full_workspace_results() -> list[dict[str, object]]:
    return [
        _passed_result(project, check.id)
        for project, project_config in MODULE.PROJECTS.items()
        for check in project_config.checks
    ]


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
    assert "--no-cov" not in payload["plan"][0]["command"]
    assert "-o addopts=" in payload["plan"][0]["command"]
    assert "--basetemp" in payload["plan"][0]["command"]
    assert str(Path(".tmp") / "project-qc-temp" / "blind-to-x") in payload["plan"][0]["command"]
    assert "basetemp-" in payload["plan"][0]["command"]


def test_resolve_command_prefers_project_venv_python(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    if MODULE.sys.platform == "win32":
        candidate = project / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = project / ".venv" / "bin" / "python"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("", encoding="utf-8")
    if MODULE.sys.platform != "win32":
        candidate.chmod(candidate.stat().st_mode | 0o111)

    monkeypatch.setattr(MODULE, "python_has_module", lambda python_path, module_name: True)

    resolved = MODULE.resolve_command(("python", "-m", "pytest"), project)

    assert resolved == (str(candidate), "-m", "pytest")


def test_resolve_command_skips_project_python_without_required_module(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project_python = tmp_path / "project-python"
    fallback_python = tmp_path / "fallback-python"
    project_python.write_text("", encoding="utf-8")
    fallback_python.write_text("", encoding="utf-8")
    if MODULE.sys.platform != "win32":
        project_python.chmod(project_python.stat().st_mode | 0o111)
        fallback_python.chmod(fallback_python.stat().st_mode | 0o111)

    monkeypatch.setattr(MODULE, "project_python_candidates", lambda cwd: (project_python, fallback_python))
    monkeypatch.setattr(
        MODULE, "python_has_module", lambda python_path, module_name: python_path == str(fallback_python)
    )

    resolved = MODULE.resolve_command(("python", "-m", "pytest"), project)

    assert resolved == (str(fallback_python), "-m", "pytest")


def test_run_plan_reports_subprocess_failures(monkeypatch) -> None:
    plan = MODULE.build_plan(["knowledge-dashboard"], ["test"])

    def fake_run(*args, **kwargs):
        return MODULE.subprocess.CompletedProcess(args[0], 1, stdout="failed stdout", stderr="failed stderr")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    results = MODULE.run_plan(plan, timeout_seconds=5, stop_on_failure=False)

    assert MODULE.exit_code_for_results(results) == 1
    assert results[0]["status"] == "failed"
    assert results[0]["stdout_tail"] == "failed stdout"


def test_pytest_checks_use_repo_local_temp(monkeypatch) -> None:
    plan = MODULE.build_plan(["blind-to-x"], ["test"])
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs["env"]
        return MODULE.subprocess.CompletedProcess(args[0], 0, stdout="ok", stderr="")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    monkeypatch.setattr(MODULE, "python_has_module", lambda python_path, module_name: True)

    results = MODULE.run_plan(plan, timeout_seconds=5, stop_on_failure=False)

    env = captured["env"]
    assert results[0]["status"] == "passed"
    assert env["TMP"].endswith(str(Path(".tmp") / "project-qc-temp" / "blind-to-x"))
    assert env["TEMP"] == env["TMP"]


def test_run_plan_reports_missing_executable(monkeypatch) -> None:
    plan = MODULE.build_plan(["knowledge-dashboard"], ["test"])

    monkeypatch.setattr(MODULE, "resolve_command", lambda command, cwd=None: command)
    monkeypatch.setattr(
        MODULE.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("nope"))
    )

    results = MODULE.run_plan(plan, timeout_seconds=5, stop_on_failure=False)

    assert MODULE.exit_code_for_results(results) == 1
    assert results[0]["status"] == "failed"
    assert "nope" in results[0]["stderr_tail"]


def test_readiness_artifact_aggregates_project_results() -> None:
    results = [
        {
            "project": "blind-to-x",
            "check": "test",
            "status": "passed",
            "returncode": 0,
            "duration_seconds": 1.2,
            "command": "python -m pytest",
            "resolved_command": "python -m pytest",
            "stdout_tail": "12 passed, 1 skipped in 1.2s",
            "stderr_tail": "",
        },
        {
            "project": "blind-to-x",
            "check": "lint",
            "status": "passed",
            "returncode": 0,
            "duration_seconds": 0.3,
            "command": "python -m ruff check .",
            "resolved_command": "python -m ruff check .",
            "stdout_tail": "All checks passed!",
            "stderr_tail": "",
        },
        {
            "project": "hanwoo-dashboard",
            "check": "test",
            "status": "failed",
            "returncode": 1,
            "duration_seconds": 2.0,
            "command": "npm test",
            "resolved_command": "npm.cmd test",
            "stdout_tail": "# pass 70\n# fail 1\n# skipped 2\n",
            "stderr_tail": "",
        },
    ]

    artifact = MODULE.build_readiness_artifact(results, timestamp="2026-06-04T00:00:00Z")

    assert artifact["source"] == "project_qc_runner"
    assert artifact["schema_version"] == MODULE.READINESS_ARTIFACT_SCHEMA_VERSION
    assert artifact["timestamp"] == "2026-06-04T00:00:00Z"
    assert artifact["projects"]["blind-to-x"]["status"] == "PASS"
    assert artifact["projects"]["blind-to-x"]["passed"] == 12
    assert artifact["projects"]["blind-to-x"]["coverage"] == "complete"
    assert artifact["projects"]["blind-to-x"]["missing_checks"] == []
    assert artifact["projects"]["hanwoo-dashboard"]["status"] == "FAIL"
    assert artifact["projects"]["hanwoo-dashboard"]["failed"] == 1
    assert artifact["projects"]["hanwoo-dashboard"]["coverage"] == "partial"
    assert artifact["projects"]["hanwoo-dashboard"]["missing_checks"] == ["build", "lint", "smoke"]
    assert artifact["total"]["passed"] == 82


def test_readiness_artifact_parses_node_test_runner_info_summary() -> None:
    results = [
        {
            "project": "knowledge-dashboard",
            "check": "test",
            "status": "passed",
            "returncode": 0,
            "duration_seconds": 0.9,
            "command": "npm test",
            "resolved_command": "npm.cmd test",
            "stdout_tail": "\u2139 tests 61\n\u2139 pass 61\n\u2139 fail 0\n\u2139 skipped 0\n",
            "stderr_tail": "",
        },
        {
            "project": "knowledge-dashboard",
            "check": "lint",
            "status": "passed",
            "returncode": 0,
            "duration_seconds": 1.0,
            "command": "npm run lint",
            "resolved_command": "npm.cmd run lint",
            "stdout_tail": "",
            "stderr_tail": "",
        },
        {
            "project": "knowledge-dashboard",
            "check": "build",
            "status": "passed",
            "returncode": 0,
            "duration_seconds": 1.0,
            "command": "npm run build",
            "resolved_command": "npm.cmd run build",
            "stdout_tail": "",
            "stderr_tail": "",
        },
        {
            "project": "knowledge-dashboard",
            "check": "smoke",
            "status": "passed",
            "returncode": 0,
            "duration_seconds": 1.0,
            "command": "npm run smoke",
            "resolved_command": "npm.cmd run smoke",
            "stdout_tail": "",
            "stderr_tail": "",
        },
    ]

    artifact = MODULE.build_readiness_artifact(results, timestamp="2026-06-05T00:00:00Z")

    assert artifact["projects"]["knowledge-dashboard"]["status"] == "PASS"
    assert artifact["projects"]["knowledge-dashboard"]["coverage"] == "complete"
    assert artifact["projects"]["knowledge-dashboard"]["passed"] == 61
    assert artifact["projects"]["knowledge-dashboard"]["failed"] == 0
    assert artifact["projects"]["knowledge-dashboard"]["skipped"] == 0
    assert artifact["total"]["passed"] == 61


def test_main_writes_project_qc_artifact(monkeypatch, tmp_path: Path) -> None:
    fake_results = [
        {
            "project": "blind-to-x",
            "check": "test",
            "status": "passed",
            "returncode": 0,
            "duration_seconds": 1.0,
            "command": "python -m pytest",
            "resolved_command": "python -m pytest",
            "stdout_tail": "2 passed in 1.0s",
            "stderr_tail": "",
        }
    ]
    monkeypatch.setattr(MODULE, "run_plan", lambda plan, timeout_seconds, stop_on_failure: fake_results)

    output_path = tmp_path / "project_qc.json"
    code, output = run_main(["--project", "blind-to-x", "--json", "--artifact", str(output_path)])

    payload = json.loads(output)
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["artifact_path"] == str(output_path)
    assert persisted["schema_version"] == MODULE.READINESS_ARTIFACT_SCHEMA_VERSION
    assert persisted["projects"]["blind-to-x"]["status"] == "PASS"
    assert persisted["projects"]["blind-to-x"]["coverage"] == "partial"
    assert persisted["projects"]["blind-to-x"]["missing_checks"] == ["lint"]
    assert persisted["projects"]["blind-to-x"]["passed"] == 2


def test_default_partial_run_does_not_overwrite_canonical_latest(monkeypatch, tmp_path: Path) -> None:
    fake_results = [_passed_result("blind-to-x", "test")]
    latest_path = tmp_path / "project_qc_runner_latest.json"
    partial_path = tmp_path / "project_qc_runner_partial_latest.json"
    monkeypatch.setattr(MODULE, "DEFAULT_ARTIFACT_PATH", latest_path)
    monkeypatch.setattr(MODULE, "DEFAULT_PARTIAL_ARTIFACT_PATH", partial_path)
    monkeypatch.setattr(MODULE, "run_plan", lambda plan, timeout_seconds, stop_on_failure: fake_results)

    code, output = run_main(["--project", "blind-to-x", "--check", "test", "--json"])

    payload = json.loads(output)
    persisted = json.loads(partial_path.read_text(encoding="utf-8"))
    assert code == 0
    assert not latest_path.exists()
    assert payload["artifact_path"] == str(partial_path)
    assert payload["artifact_full_workspace_coverage"] is False
    assert payload["artifact_canonical_latest_written"] is False
    assert "did not overwrite canonical" in payload["artifact_note"]
    assert persisted["projects"]["blind-to-x"]["coverage"] == "partial"


def test_default_full_workspace_run_updates_canonical_latest(monkeypatch, tmp_path: Path) -> None:
    latest_path = tmp_path / "project_qc_runner_latest.json"
    partial_path = tmp_path / "project_qc_runner_partial_latest.json"
    monkeypatch.setattr(MODULE, "DEFAULT_ARTIFACT_PATH", latest_path)
    monkeypatch.setattr(MODULE, "DEFAULT_PARTIAL_ARTIFACT_PATH", partial_path)
    monkeypatch.setattr(MODULE, "run_plan", lambda plan, timeout_seconds, stop_on_failure: _full_workspace_results())

    code, output = run_main(["--json"])

    payload = json.loads(output)
    persisted = json.loads(latest_path.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["artifact_path"] == str(latest_path)
    assert payload["artifact_full_workspace_coverage"] is True
    assert payload["artifact_canonical_latest_written"] is True
    assert "artifact_note" not in payload
    assert not partial_path.exists()
    assert set(persisted["projects"]) == set(MODULE.PROJECTS)
    assert all(project["coverage"] == "complete" for project in persisted["projects"].values())


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
        "smoke",
    ]
