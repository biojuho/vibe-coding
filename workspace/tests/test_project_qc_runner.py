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
    assert "--no-cov" in payload["plan"][0]["command"]
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

    monkeypatch.setattr(MODULE, "run_subprocess_capture", fake_run)

    results = MODULE.run_plan(plan, timeout_seconds=5, stop_on_failure=False)

    assert MODULE.exit_code_for_results(results) == 1
    assert results[0]["status"] == "failed"
    assert results[0]["stdout_tail"] == "failed stdout"


def test_run_plan_normalizes_windows_pytest_postpass_returncode(monkeypatch) -> None:
    plan = MODULE.build_plan(["blind-to-x"], ["test"])

    def fake_run(*args, **kwargs):
        return MODULE.subprocess.CompletedProcess(
            args[0],
            4294967295,
            stdout="12 passed, 1 skipped in 1.2s\n",
            stderr="",
        )

    monkeypatch.setattr(MODULE, "PROJECT_QC_HEARTBEAT_SECONDS", 0)
    monkeypatch.setattr(MODULE, "run_subprocess_capture", fake_run)
    monkeypatch.setattr(MODULE, "python_has_module", lambda python_path, module_name: True)

    results = MODULE.run_plan(plan, timeout_seconds=5, stop_on_failure=False)

    assert MODULE.exit_code_for_results(results) == 0
    assert results[0]["status"] == "passed"
    assert results[0]["returncode"] == 0
    assert results[0]["raw_returncode"] == 4294967295
    assert results[0]["returncode_normalized_reason"] == "windows_pytest_postpass_returncode"


def test_run_plan_keeps_windows_pytest_postpass_returncode_when_summary_is_not_success(monkeypatch) -> None:
    plan = MODULE.build_plan(["blind-to-x"], ["test"])

    def fake_run(*args, **kwargs):
        return MODULE.subprocess.CompletedProcess(
            args[0],
            4294967295,
            stdout="1 failed, 11 passed in 1.2s\n",
            stderr="",
        )

    monkeypatch.setattr(MODULE, "PROJECT_QC_HEARTBEAT_SECONDS", 0)
    monkeypatch.setattr(MODULE, "run_subprocess_capture", fake_run)
    monkeypatch.setattr(MODULE, "python_has_module", lambda python_path, module_name: True)

    results = MODULE.run_plan(plan, timeout_seconds=5, stop_on_failure=False)

    assert MODULE.exit_code_for_results(results) == 1
    assert results[0]["status"] == "failed"
    assert results[0]["returncode"] == 4294967295
    assert "raw_returncode" not in results[0]


def test_run_item_retries_transient_next_build_lock(monkeypatch) -> None:
    item = MODULE.build_plan(["hanwoo-dashboard"], ["build"])[0]
    calls: list[object] = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        if len(calls) == 1:
            return MODULE.subprocess.CompletedProcess(
                args[0],
                1,
                stdout="",
                stderr="Another next build process is already running.",
            )
        return MODULE.subprocess.CompletedProcess(args[0], 0, stdout="build passed", stderr="")

    monkeypatch.setattr(MODULE, "PROJECT_QC_HEARTBEAT_SECONDS", 0)
    monkeypatch.setattr(MODULE, "PROJECT_QC_TRANSIENT_RETRY_SECONDS", 0)
    monkeypatch.setattr(MODULE, "run_subprocess_capture", fake_run)

    result = MODULE.run_item(item, timeout_seconds=5)

    assert result["status"] == "passed"
    assert result["attempts"] == 2
    assert result["transient_retry_count"] == 1
    assert result["transient_retry_reason"] == "next_build_lock"


def test_pytest_checks_use_repo_local_temp(monkeypatch) -> None:
    plan = MODULE.build_plan(["blind-to-x"], ["test"])
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs["env"]
        return MODULE.subprocess.CompletedProcess(args[0], 0, stdout="ok", stderr="")

    monkeypatch.setattr(MODULE, "run_subprocess_capture", fake_run)
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
        MODULE, "run_subprocess_capture", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("nope"))
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

    artifact = MODULE.build_readiness_artifact(
        results,
        timestamp="2026-06-04T00:00:00Z",
        git_metadata={
            "available": True,
            "head_sha": "abc123",
            "branch": "main",
            "dirty_count": 0,
            "dirty_paths": [],
        },
    )

    assert artifact["source"] == "project_qc_runner"
    assert artifact["schema_version"] == MODULE.READINESS_ARTIFACT_SCHEMA_VERSION
    assert artifact["timestamp"] == "2026-06-04T00:00:00Z"
    assert artifact["git"]["head_sha"] == "abc123"
    assert artifact["git"]["dirty_count"] == 0
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


def test_main_artifact_temp_write_failure_returns_structured_json_without_overwriting(
    monkeypatch, tmp_path: Path
) -> None:
    fake_results = [_passed_result("blind-to-x", "test")]
    monkeypatch.setattr(MODULE, "run_plan", lambda plan, timeout_seconds, stop_on_failure: fake_results)

    output_path = tmp_path / "project_qc.json"
    existing = {"status": "existing", "projects": {}}
    output_path.write_text(json.dumps(existing), encoding="utf-8")
    (tmp_path / "project_qc.json.refresh-tmp").mkdir()

    code, output = run_main(["--project", "blind-to-x", "--json", "--artifact", str(output_path)])

    payload = json.loads(output)
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert code == 4
    assert payload["status"] == "artifact_write_failed"
    assert payload["results_status"] == "passed"
    assert payload["artifact_error_path"] == str(output_path)
    assert payload["artifact_intended_path"] == str(output_path)
    assert payload["results"] == fake_results
    assert persisted == existing


def test_main_artifact_blocked_parent_returns_structured_json(monkeypatch, tmp_path: Path) -> None:
    fake_results = [_passed_result("blind-to-x", "test")]
    monkeypatch.setattr(MODULE, "run_plan", lambda plan, timeout_seconds, stop_on_failure: fake_results)

    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("keep me", encoding="utf-8")
    output_path = blocked_parent / "project_qc.json"

    code, output = run_main(["--project", "blind-to-x", "--json", "--artifact", str(output_path)])

    payload = json.loads(output)
    assert code == 4
    assert payload["status"] == "artifact_write_failed"
    assert payload["results_status"] == "passed"
    assert payload["artifact_error_path"] == str(output_path)
    assert payload["artifact_intended_path"] == str(output_path)
    assert payload["results"] == fake_results
    assert blocked_parent.read_text(encoding="utf-8") == "keep me"


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


def test_default_partial_runs_merge_project_latest_artifacts(monkeypatch, tmp_path: Path) -> None:
    latest_path = tmp_path / "project_qc_runner_latest.json"
    partial_path = tmp_path / "project_qc_runner_partial_latest.json"
    monkeypatch.setattr(MODULE, "DEFAULT_ARTIFACT_PATH", latest_path)
    monkeypatch.setattr(MODULE, "DEFAULT_PARTIAL_ARTIFACT_PATH", partial_path)

    def fake_run_plan(plan, timeout_seconds, stop_on_failure):
        return [
            _passed_result(item.project, item.check.id, passed=11 if item.project == "blind-to-x" else 22)
            for item in plan
        ]

    monkeypatch.setattr(MODULE, "run_plan", fake_run_plan)

    blind_code, blind_output = run_main(["--project", "blind-to-x", "--json"])
    shorts_code, shorts_output = run_main(["--project", "shorts-maker-v2", "--json"])

    blind_payload = json.loads(blind_output)
    shorts_payload = json.loads(shorts_output)
    persisted = json.loads(partial_path.read_text(encoding="utf-8"))
    assert blind_code == 0
    assert shorts_code == 0
    assert blind_payload["artifact_path"] == str(partial_path)
    assert shorts_payload["artifact_path"] == str(partial_path)
    assert not latest_path.exists()
    assert set(persisted["projects"]) == {"blind-to-x", "shorts-maker-v2"}
    assert persisted["projects"]["blind-to-x"]["passed"] == 22
    assert persisted["projects"]["shorts-maker-v2"]["passed"] == 44
    assert set(persisted[MODULE.PROJECT_QC_PROJECT_SOURCES_KEY]) == {"blind-to-x", "shorts-maker-v2"}


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


def test_configured_payload_lists_project_commands() -> None:
    payload = MODULE._configured_payload()

    assert payload["status"] == "configured"
    assert "blind-to-x" in payload["projects"]
    assert [check["id"] for check in payload["projects"]["hanwoo-dashboard"]["checks"]] == [
        "test",
        "lint",
        "build",
        "smoke",
    ]
    assert "npm" in payload["projects"]["hanwoo-dashboard"]["checks"][1]["command"]


def test_results_payload_skips_artifact_when_disabled(tmp_path: Path) -> None:
    payload = MODULE._results_payload(
        [_passed_result("blind-to-x", "test")],
        tmp_path / "project_qc.json",
        no_artifact=True,
    )

    assert payload == {
        "status": "passed",
        "results": [_passed_result("blind-to-x", "test")],
    }


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
