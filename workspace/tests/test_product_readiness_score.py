"""Unit tests for `execution/product_readiness_score.py`."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "execution" / "product_readiness_score.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("product_readiness_score", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["product_readiness_score"] = module
    spec.loader.exec_module(module)
    return module


readiness = _load_module()


def test_shorts_root_readme_is_required_launch_document():
    assert "README.md" in readiness.PROJECTS["shorts-maker-v2"].required_files


def test_shorts_provider_key_check_is_required_for_launch_readiness():
    assert "shorts_provider_keys" in readiness.PROJECTS["shorts-maker-v2"].env_checks


def test_blind_to_x_env_check_is_required_for_launch_readiness():
    assert "blind_to_x_launch_env" in readiness.PROJECTS["blind-to-x"].env_checks


def test_knowledge_dashboard_runtime_auth_check_is_required_for_launch_readiness():
    assert "dashboard_runtime_auth" in readiness.PROJECTS["knowledge-dashboard"].env_checks


def test_cli_output_write_failure_returns_structured_json_without_overwriting(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    output_path = tmp_path / "product_readiness.json"
    output_path.write_text('{"status":"existing"}\n', encoding="utf-8")
    output_path.with_name(f"{output_path.name}.refresh-tmp").mkdir()
    monkeypatch.setattr(
        readiness,
        "build_report",
        lambda repo_root: {"generated_at": "2026-06-14T00:00:00Z", "overall": {"state": "blocked"}},
    )

    code = readiness.main(["--repo-root", str(tmp_path), "--output", str(output_path), "--json"])
    stdout = json.loads(capsys.readouterr().out)

    assert code == 4
    assert output_path.read_text(encoding="utf-8") == '{"status":"existing"}\n'
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output_path.as_posix()
    assert stdout["write_error"]
    assert stdout["overall"]["state"] == "blocked"


def test_cli_output_blocked_parent_returns_structured_json(tmp_path: Path, monkeypatch, capsys) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    output_path = blocked_parent / "product_readiness.json"
    blocked_parent.write_text("blocking file\n", encoding="utf-8")
    monkeypatch.setattr(
        readiness,
        "build_report",
        lambda repo_root: {"generated_at": "2026-06-14T00:00:00Z", "overall": {"state": "blocked"}},
    )

    code = readiness.main(["--repo-root", str(tmp_path), "--output", str(output_path), "--json"])
    stdout = json.loads(capsys.readouterr().out)

    assert code == 4
    assert blocked_parent.read_text(encoding="utf-8") == "blocking file\n"
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output_path.as_posix()
    assert "FileExistsError" in stdout["write_error"]


def test_hanwoo_env_example_is_required_launch_document():
    assert ".env.example" in readiness.PROJECTS["hanwoo-dashboard"].required_files


def _write_project_files(root: Path) -> None:
    for profile in readiness.PROJECTS.values():
        project_root = root / profile.path
        project_root.mkdir(parents=True, exist_ok=True)
        for relative in profile.required_files:
            target = project_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok\n", encoding="utf-8")


def _write_required_env(root: Path) -> None:
    (root / "projects" / "blind-to-x" / ".env").write_text(
        "\n".join(
            (
                "NOTION_API_KEY=notion-secret",
                "NOTION_DATABASE_ID=1234567890abcdef1234567890abcdef",
                "OPENAI_API_KEY=sk-real-test-key",
                "",
            )
        ),
        encoding="utf-8",
    )
    (root / "projects" / "hanwoo-dashboard" / ".env").write_text(
        "DATABASE_URL=postgres://user:secret@example/db\n",
        encoding="utf-8",
    )
    (root / "projects" / "shorts-maker-v2" / ".env").write_text(
        "OPENAI_API_KEY=sk-real-test-key\n",
        encoding="utf-8",
    )
    (root / "projects" / "knowledge-dashboard" / ".env.local").write_text(
        "DASHBOARD_API_KEY=knowledge-dashboard-test-key\n",
        encoding="utf-8",
    )


def _write_qaqc(root: Path) -> Path:
    path = root / "projects" / "knowledge-dashboard" / "data" / "qaqc_result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "projects": {
                    "blind-to-x": {"status": "PASS", "passed": 10, "failed": 0, "errors": 0},
                    "shorts-maker-v2": {"status": "PASS", "passed": 20, "failed": 0, "errors": 0},
                    "hanwoo-dashboard": {"status": "PASS", "passed": 30, "failed": 0, "errors": 0},
                    "knowledge-dashboard": {"status": "PASS", "passed": 3, "failed": 0, "errors": 0},
                    "root": {"status": "PASS", "passed": 40, "failed": 0, "errors": 0},
                }
            },
        ),
        encoding="utf-8",
    )
    return path


def _write_latest_project_qc(root: Path) -> Path:
    path = root / ".tmp" / "project_qc_runner_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    complete_checks = {
        "blind-to-x": ["test", "lint"],
        "shorts-maker-v2": ["test", "lint"],
        "hanwoo-dashboard": ["test", "lint", "build", "smoke"],
        "knowledge-dashboard": ["test", "lint", "build", "smoke"],
    }
    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-05-13T00:00:00+00:00",
                "source": "project_qc_runner",
                "schema_version": readiness._current_project_qc_artifact_schema_version(),
                "status": "passed",
                "projects": {
                    name: {
                        "status": "PASS",
                        "passed": passed,
                        "failed": 0,
                        "errors": 0,
                        "coverage": "complete",
                        "expected_checks": checks,
                        "observed_checks": checks,
                        "missing_checks": [],
                    }
                    for name, passed, checks in (
                        ("blind-to-x", 10, complete_checks["blind-to-x"]),
                        ("shorts-maker-v2", 20, complete_checks["shorts-maker-v2"]),
                        ("hanwoo-dashboard", 30, complete_checks["hanwoo-dashboard"]),
                        ("knowledge-dashboard", 3, complete_checks["knowledge-dashboard"]),
                    )
                },
            },
        ),
        encoding="utf-8",
    )
    return path


def _write_partial_project_qc(
    root: Path,
    *,
    project_name: str = "blind-to-x",
    timestamp: str = "2026-05-13T02:00:00+00:00",
    passed: int = 99,
    coverage: str = "complete",
    observed_checks: list[str] | None = None,
    missing_checks: list[str] | None = None,
    head_sha: str = "abc123",
) -> Path:
    path = root / ".tmp" / "project_qc_runner_partial_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    observed = observed_checks or ["test", "lint"]
    missing = missing_checks or []
    path.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "source": "project_qc_runner",
                "schema_version": readiness._current_project_qc_artifact_schema_version(),
                "git": {
                    "available": True,
                    "head_sha": head_sha,
                    "branch": "main",
                    "dirty_count": 0,
                    "dirty_paths": [],
                },
                "status": "passed",
                "projects": {
                    project_name: {
                        "status": "PASS",
                        "passed": passed,
                        "failed": 0,
                        "errors": 0,
                        "coverage": coverage,
                        "expected_checks": ["test", "lint"],
                        "observed_checks": observed,
                        "missing_checks": missing,
                    }
                },
            },
        ),
        encoding="utf-8",
    )
    return path


def _write_qaqc_timestamp(path: Path, timestamp: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["timestamp"] = timestamp
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_tasks(root: Path, body: str) -> None:
    ai = root / ".ai"
    ai.mkdir(parents=True, exist_ok=True)
    (ai / "TASKS.md").write_text(body, encoding="utf-8")


def _passing_github_status() -> dict:
    return {
        "available": True,
        "head_sha": "abc123",
        "branch_status": "## main...origin/main",
        "ahead_count": 0,
        "publish_required": False,
        "open_pr_count": 0,
        "open_prs": [],
        "required_workflows": [
            {
                "name": "root-quality-gate",
                "status": "completed",
                "conclusion": "success",
                "databaseId": 1,
                "url": "https://example.test/root",
            },
            {
                "name": "active-project-matrix",
                "status": "completed",
                "conclusion": "success",
                "databaseId": 2,
                "url": "https://example.test/matrix",
            },
        ],
        "checks": [
            {
                "name": "Open GitHub pull requests",
                "ok": True,
                "severity": "ok",
                "message": "No open GitHub pull requests.",
            },
            {
                "name": "Required GitHub Actions",
                "ok": True,
                "severity": "ok",
                "message": "Required GitHub Actions are green for current HEAD.",
            },
        ],
        "blockers": [],
    }


def _unpublished_head_github_status() -> dict:
    status = _passing_github_status()
    status["branch_status"] = "## main...origin/main [ahead 2]"
    status["ahead_count"] = 2
    status["publish_required"] = True
    status["required_workflows"] = [
        {
            "name": "root-quality-gate",
            "status": "missing",
            "conclusion": None,
            "databaseId": None,
            "url": None,
        },
        {
            "name": "active-project-matrix",
            "status": "missing",
            "conclusion": None,
            "databaseId": None,
            "url": None,
        },
    ]
    status["checks"][1] = {
        "name": "Required GitHub Actions",
        "ok": False,
        "severity": "blocker",
        "message": (
            "Required GitHub Actions are unavailable for current local HEAD because main is ahead of origin "
            "by 2 commit(s): root-quality-gate, active-project-matrix. Push only with explicit authorization, "
            "then wait for Actions."
        ),
        "blocker_type": "publish",
        "ahead_count": 2,
        "requires_publish": True,
    }
    status["blockers"] = [status["checks"][1]]
    return status


def test_project_qc_freshness_merges_time_and_head_staleness() -> None:
    freshness = readiness._project_qc_freshness(
        {"timestamp": "2026-05-01T00:00:00+00:00"},
        "blind-to-x",
        datetime(2026, 5, 13, tzinfo=timezone.utc),
        {
            "artifact_head_sha": "old-head",
            "current_head_sha": "new-head",
            "changed_paths_available": True,
            "changed_paths_since_qc": [
                "projects/blind-to-x/pipeline/process.py",
                "projects/shorts-maker-v2/render.py",
            ],
            "changed_paths_error": "diff failed",
        },
    )

    assert freshness["stale"] is True
    assert freshness["stale_reasons"] == ["age", readiness.PROJECT_QC_ARTIFACT_HEAD_STALE]
    assert freshness["artifact_head_sha"] == "old-head"
    assert freshness["current_head_sha"] == "new-head"
    assert freshness["head_stale"] is True
    assert freshness["changed_paths_available"] is True
    assert freshness["relevant_changes_since_qc"] == ["projects/blind-to-x/pipeline/process.py"]
    assert freshness["changed_paths_error"] == "diff failed"


def test_project_qc_contract_state_reports_schema_and_expected_check_drift(monkeypatch) -> None:
    monkeypatch.setattr(readiness, "_current_project_qc_artifact_schema_version", lambda: "current-schema")
    monkeypatch.setattr(
        readiness,
        "_current_project_qc_expected_checks",
        lambda: {"hanwoo-dashboard": ("build", "lint", "smoke", "test")},
    )

    missing_checks, contract_mismatches = readiness._project_qc_contract_state(
        {"source": readiness.PROJECT_QC_SOURCE, "schema_version": "old-schema"},
        "hanwoo-dashboard",
        {"observed_checks": ["test", "lint"], "missing_checks": []},
        [],
    )

    assert missing_checks == ["build", "smoke"]
    assert contract_mismatches == [readiness.PROJECT_QC_ARTIFACT_CONTRACT_MISMATCH]


def test_project_qc_counts_combines_failures_and_errors() -> None:
    assert readiness._project_qc_counts({"passed": "5", "failed": "2", "errors": "3", "skipped": "1"}) == {
        "passed": 5,
        "failed": 5,
        "skipped": 1,
    }


def test_blind_to_x_launch_env_checks_report_notion_and_provider_blockers(tmp_path: Path) -> None:
    checks = readiness._blind_to_x_launch_env_checks(tmp_path, readiness.PROJECTS["blind-to-x"])

    assert [check["name"] for check in checks] == [
        "Notion review queue keys",
        "blind-to-x LLM provider keys",
    ]
    assert all(check["severity"] == "blocker" for check in checks)
    assert "NOTION_API_KEY" in checks[0]["message"]
    assert "at least one LLM provider API key" in checks[1]["message"]


def test_supabase_password_env_check_accepts_configured_database_url(tmp_path: Path) -> None:
    env_path = tmp_path / "projects" / "hanwoo-dashboard" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("DATABASE_URL=postgres://user:secret@example/db\n", encoding="utf-8")

    checks = readiness._supabase_password_env_checks(tmp_path, readiness.PROJECTS["hanwoo-dashboard"])

    assert checks == [
        {
            "name": "Supabase DATABASE_URL",
            "ok": True,
            "severity": "ok",
            "message": "DATABASE_URL is present; run the live Prisma check to verify current Supabase credentials.",
        }
    ]


def test_shorts_provider_env_check_counts_only_usable_keys(tmp_path: Path) -> None:
    env_path = tmp_path / "projects" / "shorts-maker-v2" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("OPENAI_API_KEY=sk-real-test-key\nGOOGLE_API_KEY=your_google_key\n", encoding="utf-8")

    checks = readiness._shorts_provider_env_checks(tmp_path, readiness.PROJECTS["shorts-maker-v2"])

    assert checks == [
        {
            "name": "Shorts generation provider keys",
            "ok": True,
            "severity": "ok",
            "message": "1 Shorts generation provider key(s) are configured.",
        }
    ]


def test_dashboard_runtime_auth_env_checks_allow_session_secret_fallback(tmp_path: Path) -> None:
    env_path = tmp_path / "projects" / "knowledge-dashboard" / ".env.local"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("DASHBOARD_API_KEY=knowledge-dashboard-test-key\n", encoding="utf-8")

    checks = readiness._dashboard_runtime_auth_env_checks(tmp_path, readiness.PROJECTS["knowledge-dashboard"])

    assert checks == [
        {
            "name": "Dashboard API key",
            "ok": True,
            "severity": "ok",
            "message": "DASHBOARD_API_KEY is configured for authenticated dashboard routes.",
        },
        {
            "name": "Dashboard session signing secret",
            "ok": True,
            "severity": "watch",
            "message": "DASHBOARD_SESSION_SECRET is optional; DASHBOARD_API_KEY fallback will sign sessions.",
        },
    ]


def test_project_score_value_combines_component_scores() -> None:
    score = readiness._project_score_value(
        qc_score=35,
        active_blockers=[],
        docs=[{"present": True}, {"present": True}],
        dirty_paths=[],
        env={"score": 15},
    )

    assert score == 100


def test_project_blocker_breakdown_counts_task_and_env_blockers() -> None:
    breakdown = readiness._project_blocker_breakdown(
        active_blockers=[{"id": "T-1"}, {"id": "T-2"}],
        user_task_blockers=[{"id": "T-1"}],
        agent_task_blockers=[{"id": "T-2"}],
        env_blockers=[{"name": "env"}],
    )

    assert breakdown == {
        "task_count": 2,
        "user_task_count": 1,
        "agent_task_count": 1,
        "environment_count": 1,
    }


def test_hanwoo_placeholder_marks_project_blocked(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_required_env(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path,
        "# TASKS\n\n"
        "## TODO\n\n"
        "| ID | Task | Owner | Priority | Auto | Created |\n"
        "|---|---|---|---|---|---|\n"
        "| T-251 | `[hanwoo-dashboard]` Run live Supabase CRUD check. | User | High | approval | today |\n",
    )
    env_path = tmp_path / "projects" / "hanwoo-dashboard" / ".env"
    env_path.write_text("DATABASE_URL=postgres://user:YOUR_PASSWORD@example/db\n", encoding="utf-8")

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    hanwoo = next(project for project in report["projects"] if project["name"] == "hanwoo-dashboard")
    assert report["overall"]["state"] == "blocked"
    assert report["overall"]["external_blocker_count"] == 1
    assert report["overall"]["local_blocker_count"] == 1
    assert hanwoo["state"] == "blocked"
    assert hanwoo["blocker_breakdown"] == {
        "task_count": 1,
        "user_task_count": 1,
        "agent_task_count": 0,
        "environment_count": 1,
    }
    assert hanwoo["env"]["checks"][0]["severity"] == "blocker"
    assert hanwoo["env"]["checks"][0]["message"] == "Supabase DATABASE_URL still contains a placeholder."
    assert any("Supabase" in item for item in hanwoo["recommendations"])


def test_user_owned_project_task_reports_external_blocker_without_local_blocker(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_required_env(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path,
        "# TASKS\n\n"
        "## TODO\n\n"
        "| ID | Task | Owner | Priority | Auto | Created |\n"
        "|---|---|---|---|---|---|\n"
        "| T-251 | `[hanwoo-dashboard]` Run live Supabase CRUD check. | User | High | approval | today |\n",
    )

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    hanwoo = next(project for project in report["projects"] if project["name"] == "hanwoo-dashboard")
    assert report["overall"]["state"] == "blocked"
    assert report["overall"]["external_blocker_count"] == 1
    assert report["overall"]["local_blocker_count"] == 0
    assert report["overall"]["blocker_breakdown"] == {
        "external": 1,
        "local": 0,
        "user_owned_tasks": 1,
        "agent_owned_tasks": 0,
        "environment": 0,
        "publish": 0,
        "workspace_gate": 0,
    }
    assert hanwoo["blocker_breakdown"] == {
        "task_count": 1,
        "user_task_count": 1,
        "agent_task_count": 0,
        "environment_count": 0,
    }
    message = "Wait for 1 user-owned task blocker(s) before rerunning local launch checks: T-251."
    assert hanwoo["recommendations"][0] == message
    assert report["next_actions"][0]["action"] == message


def test_mixed_project_tasks_prioritize_agent_blocker_before_user_wait(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_required_env(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path,
        "# TASKS\n\n"
        "## TODO\n\n"
        "| ID | Task | Owner | Priority | Auto | Created |\n"
        "|---|---|---|---|---|---|\n"
        "| T-1287 | `[hanwoo-dashboard]` Refresh readiness copy. | Codex | Medium | auto | today |\n"
        "| T-251 | `[hanwoo-dashboard]` Run live Supabase CRUD check. | User | High | approval | today |\n",
    )

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    hanwoo = next(project for project in report["projects"] if project["name"] == "hanwoo-dashboard")
    message = "Resolve 1 agent-owned task blocker(s), then wait for 1 user-owned task blocker(s): T-251."
    assert report["overall"]["state"] == "blocked"
    assert report["overall"]["blocker_breakdown"] == {
        "external": 1,
        "local": 0,
        "user_owned_tasks": 1,
        "agent_owned_tasks": 1,
        "environment": 0,
        "publish": 0,
        "workspace_gate": 0,
    }
    assert hanwoo["blocker_breakdown"] == {
        "task_count": 2,
        "user_task_count": 1,
        "agent_task_count": 1,
        "environment_count": 0,
    }
    assert hanwoo["recommendations"][0] == message
    assert report["next_actions"][0]["action"] == message


def test_missing_hanwoo_env_reports_missing_file_instead_of_configured(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_required_env(tmp_path)
    (tmp_path / "projects" / "hanwoo-dashboard" / ".env").unlink()
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path,
        "# TASKS\n\n"
        "## TODO\n\n"
        "| ID | Task | Owner | Priority | Auto | Created |\n"
        "|---|---|---|---|---|---|\n"
        "| T-251 | `[hanwoo-dashboard]` Run live Supabase CRUD check. | User | High | approval | today |\n",
    )

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    hanwoo = next(project for project in report["projects"] if project["name"] == "hanwoo-dashboard")
    message = hanwoo["env"]["checks"][0]["message"]
    assert hanwoo["env"]["checks"][0]["ok"] is False
    assert "is missing" in message
    assert "configured" not in message
    assert hanwoo["recommendations"][0] == message


def test_clean_projects_with_docs_and_qc_score_ready(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    assert report["overall"]["state"] == "ready"
    assert report["overall"]["score"] >= 85
    assert all(project["score"] >= 85 for project in report["projects"])
    assert report["workspace_gates"]["github_release"]["available"] is True
    assert report["overall"]["workspace_blocker_count"] == 0
    assert report["overall"]["external_blocker_count"] == 0
    assert report["overall"]["local_blocker_count"] == 0


def test_default_report_reads_latest_project_qc_runner_artifact(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_latest_project_qc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["available"] is True
    assert blind["qc"]["status"] == "PASS"
    assert (
        blind["recommendations"][0]
        != "Refresh project QC so the score reflects the latest test/lint/build/smoke state."
    )
    assert report["overall"]["state"] == "ready"


def test_project_qc_artifact_missing_current_runner_check_is_partial(tmp_path: Path):
    _write_project_files(tmp_path)
    path = _write_latest_project_qc(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    hanwoo = data["projects"]["hanwoo-dashboard"]
    hanwoo["expected_checks"] = ["test", "lint", "build"]
    hanwoo["observed_checks"] = ["test", "lint", "build"]
    hanwoo["missing_checks"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    hanwoo_project = next(project for project in report["projects"] if project["name"] == "hanwoo-dashboard")
    assert hanwoo_project["qc"]["available"] is False
    assert hanwoo_project["qc"]["status"] == "PARTIAL"
    assert hanwoo_project["qc"]["missing_checks"] == ["smoke"]
    assert (
        hanwoo_project["recommendations"][0]
        == "Refresh project QC so the score reflects the latest test/lint/build/smoke state."
    )


def test_project_qc_artifact_missing_current_schema_is_partial(tmp_path: Path):
    _write_project_files(tmp_path)
    path = _write_latest_project_qc(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("schema_version", None)
    path.write_text(json.dumps(data), encoding="utf-8")
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["available"] is False
    assert blind["qc"]["status"] == "PARTIAL"
    assert blind["qc"]["contract_mismatches"] == [readiness.PROJECT_QC_ARTIFACT_CONTRACT_MISMATCH]
    assert (
        blind["recommendations"][0]
        == "Refresh project QC so the score reflects the latest test/lint/build/smoke state."
    )


def test_github_release_gate_blocks_open_prs(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)
    github_status = _passing_github_status()
    github_status["open_pr_count"] = 1
    github_status["open_prs"] = [
        {
            "number": 7,
            "title": "Release blocker",
            "url": "https://example.test/pull/7",
            "headRefName": "release-blocker",
        }
    ]
    github_status["checks"][0] = {
        "name": "Open GitHub pull requests",
        "ok": False,
        "severity": "blocker",
        "message": "1 open GitHub pull request(s) must be triaged before launch.",
    }
    github_status["blockers"] = [github_status["checks"][0]]

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=github_status,
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    assert report["overall"]["state"] == "blocked"
    assert report["overall"]["workspace_blocker_count"] == 1
    assert report["overall"]["external_blocker_count"] == 0
    assert report["overall"]["local_blocker_count"] == 1
    assert report["workspace_gates"]["github_release"]["open_pr_count"] == 1
    assert "open GitHub pull request" in report["next_actions"][-1]["action"]


def test_github_release_gate_blocks_missing_required_actions(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)
    github_status = _passing_github_status()
    github_status["required_workflows"][1]["status"] = "in_progress"
    github_status["required_workflows"][1]["conclusion"] = ""
    github_status["checks"][1] = {
        "name": "Required GitHub Actions",
        "ok": False,
        "severity": "blocker",
        "message": "Required GitHub Actions are not green for current HEAD: active-project-matrix.",
    }
    github_status["blockers"] = [github_status["checks"][1]]

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=github_status,
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    assert report["overall"]["state"] == "blocked"
    assert report["overall"]["workspace_blocker_count"] == 1
    assert report["overall"]["external_blocker_count"] == 0
    assert report["overall"]["local_blocker_count"] == 1
    assert report["workspace_gates"]["github_release"]["required_workflows"][1]["status"] == "in_progress"
    assert "Required GitHub Actions" in report["next_actions"][-1]["action"]


def test_github_release_status_marks_unpublished_head_actions_as_publish_blocker(tmp_path: Path, monkeypatch):
    (tmp_path / ".git").mkdir()

    def fake_run_command(
        _repo_root: Path, command: list[str], *, default: Any = "", timeout: int = 10, parse_json: bool = False
    ):
        if command == ["git", "rev-parse", "HEAD"]:
            result = "abc123"
        elif command == ["git", "status", "--short", "--branch"]:
            result = "## main...origin/main [ahead 2]"
        elif command[:3] == ["gh", "pr", "list"]:
            result = []
        elif command[:3] == ["gh", "run", "list"]:
            result = []
        else:
            return default
        if parse_json:
            return result
        if isinstance(result, str):
            return result.strip()
        return result

    monkeypatch.setattr(readiness, "_run_command", fake_run_command)

    status = readiness._github_release_status(tmp_path)

    assert status["available"] is True
    assert status["ahead_count"] == 2
    assert status["publish_required"] is True
    assert status["required_workflows"][0]["status"] == "missing"
    assert status["blockers"][0]["blocker_type"] == "publish"
    assert status["blockers"][0]["requires_publish"] is True
    assert "Push only with explicit authorization" in status["blockers"][0]["message"]


def test_github_release_gate_separates_unpublished_head_from_local_blockers(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=_unpublished_head_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    assert report["overall"]["state"] == "blocked"
    assert report["overall"]["workspace_blocker_count"] == 1
    assert report["overall"]["external_blocker_count"] == 0
    assert report["overall"]["local_blocker_count"] == 0
    assert report["overall"]["publish_blocker_count"] == 1
    assert report["overall"]["blocker_breakdown"]["publish"] == 1
    assert report["workspace_gates"]["github_release"]["publish_required"] is True
    assert report["workspace_gates"]["github_release"]["blockers"][0]["blocker_type"] == "publish"
    assert report["next_actions"][0]["project"] == "workspace"
    assert "explicit authorization" in report["next_actions"][0]["action"]


def test_publish_blocker_is_next_action_before_user_owned_project_wait(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path,
        "# TASKS\n\n"
        "## TODO\n\n"
        "| ID | Task | Owner | Priority | Auto | Created |\n"
        "|---|---|---|---|---|---|\n"
        "| T-251 | `[hanwoo-dashboard]` Run live Supabase CRUD check. | User | High | approval | today |\n",
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=_unpublished_head_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    assert report["overall"]["external_blocker_count"] == 1
    assert report["overall"]["publish_blocker_count"] == 1
    assert report["next_actions"][0]["project"] == "workspace"
    assert "explicit authorization" in report["next_actions"][0]["action"]
    assert report["next_actions"][1]["project"] == "hanwoo-dashboard"
    assert report["next_actions"][1]["action"] == (
        "Wait for 1 user-owned task blocker(s) before rerunning local launch checks: T-251."
    )


def test_github_release_gate_is_unavailable_for_non_git_roots(tmp_path: Path):
    status = readiness._github_release_status(tmp_path)

    assert status["available"] is False
    assert status["blockers"] == []
    assert status["checks"][0]["severity"] == "watch"


def test_partial_project_qc_runner_artifact_does_not_score_as_fresh_qc(tmp_path: Path):
    _write_project_files(tmp_path)
    path = tmp_path / ".tmp" / "project_qc_runner_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-05-13T00:00:00+00:00",
                "source": "project_qc_runner",
                "status": "passed",
                "projects": {
                    "blind-to-x": {
                        "status": "PASS",
                        "passed": 0,
                        "failed": 0,
                        "errors": 0,
                        "coverage": "partial",
                        "expected_checks": ["test", "lint"],
                        "observed_checks": ["lint"],
                        "missing_checks": ["test"],
                    }
                },
            },
        ),
        encoding="utf-8",
    )
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["available"] is False
    assert blind["qc"]["status"] == "PARTIAL"
    assert blind["qc"]["missing_checks"] == ["test"]
    assert (
        blind["recommendations"][0]
        == "Refresh project QC so the score reflects the latest test/lint/build/smoke state."
    )


def test_default_qc_data_uses_newer_complete_partial_project_artifact(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_latest_project_qc(tmp_path)
    _write_partial_project_qc(tmp_path, passed=99)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    shorts = next(project for project in report["projects"] if project["name"] == "shorts-maker-v2")
    assert blind["qc"]["available"] is True
    assert blind["qc"]["passed"] == 99
    assert blind["qc"]["stale"] is False
    assert shorts["qc"]["passed"] == 20


def test_default_qc_data_preserves_merged_partial_projects(tmp_path: Path, monkeypatch):
    _write_project_files(tmp_path)
    _write_latest_project_qc(tmp_path)
    blind_partial_path = _write_partial_project_qc(
        tmp_path,
        project_name="blind-to-x",
        timestamp="2026-05-13T02:00:00+00:00",
        passed=99,
        head_sha="blind-head",
    )
    blind_partial = json.loads(blind_partial_path.read_text(encoding="utf-8"))
    _write_partial_project_qc(
        tmp_path,
        project_name="shorts-maker-v2",
        timestamp="2026-05-13T03:00:00+00:00",
        passed=88,
        head_sha="shorts-head",
    )
    merged_partial = json.loads(blind_partial_path.read_text(encoding="utf-8"))
    merged_partial["projects"]["blind-to-x"] = blind_partial["projects"]["blind-to-x"]
    merged_partial[readiness.PROJECT_QC_PROJECT_SOURCES_KEY] = {
        "blind-to-x": blind_partial,
        "shorts-maker-v2": json.loads(blind_partial_path.read_text(encoding="utf-8")),
    }
    blind_partial_path.write_text(json.dumps(merged_partial), encoding="utf-8")
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    def fake_changed_paths(repo_root: Path, base_sha: str, head_sha: str) -> dict:
        if base_sha == head_sha:
            return {"available": True, "paths": []}
        return {"available": True, "paths": ["projects/blind-to-x/pipeline/process.py"]}

    monkeypatch.setattr(readiness, "_changed_paths_between", fake_changed_paths)
    github_status = _passing_github_status()
    github_status["head_sha"] = "blind-head"

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        github_status=github_status,
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    shorts = next(project for project in report["projects"] if project["name"] == "shorts-maker-v2")
    assert blind["qc"]["passed"] == 99
    assert blind["qc"]["head_stale"] is False
    assert shorts["qc"]["passed"] == 88


def test_newer_incomplete_partial_project_qc_does_not_replace_canonical_complete(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_latest_project_qc(tmp_path)
    _write_partial_project_qc(
        tmp_path,
        passed=99,
        coverage="partial",
        observed_checks=["test"],
        missing_checks=["lint"],
    )
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["available"] is True
    assert blind["qc"]["passed"] == 10
    assert blind["qc"]["missing_checks"] == []


def test_merged_partial_project_qc_uses_project_artifact_head_freshness(tmp_path: Path, monkeypatch):
    _write_project_files(tmp_path)
    latest_path = _write_latest_project_qc(tmp_path)
    data = json.loads(latest_path.read_text(encoding="utf-8"))
    data["git"] = {
        "available": True,
        "head_sha": "old-head",
        "branch": "main",
        "dirty_count": 0,
        "dirty_paths": [],
    }
    latest_path.write_text(json.dumps(data), encoding="utf-8")
    _write_partial_project_qc(tmp_path, passed=99, head_sha="new-head")
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    def fake_changed_paths(repo_root: Path, base_sha: str, head_sha: str) -> dict:
        if base_sha == head_sha:
            return {"available": True, "paths": []}
        return {"available": True, "paths": ["projects/blind-to-x/scrapers/ppomppu.py"]}

    monkeypatch.setattr(readiness, "_changed_paths_between", fake_changed_paths)
    github_status = _passing_github_status()
    github_status["head_sha"] = "new-head"

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        github_status=github_status,
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["passed"] == 99
    assert blind["qc"]["head_stale"] is False
    assert blind["qc"]["stale"] is False


def test_dirty_paths_lower_the_matching_project_only(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text=" M projects/blind-to-x/pipeline/process.py\n M projects/hanwoo-dashboard/README.md\n",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    shorts = next(project for project in report["projects"] if project["name"] == "shorts-maker-v2")
    assert blind["dirty_paths"] == ["projects/blind-to-x/pipeline/process.py"]
    assert shorts["dirty_paths"] == []


def test_dirty_workspace_blocks_launch_readiness(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text=" M execution/product_readiness_score.py\n",
        github_status=_passing_github_status(),
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    worktree = report["workspace_gates"]["worktree"]
    assert report["overall"]["state"] == "blocked"
    assert report["overall"]["workspace_blocker_count"] == 1
    assert report["overall"]["external_blocker_count"] == 0
    assert report["overall"]["local_blocker_count"] == 1
    assert worktree["dirty_count"] == 1
    assert worktree["blockers"][0]["name"] == "Workspace worktree"
    assert "uncommitted workspace path" in report["next_actions"][-1]["action"]


def test_stale_qc_data_lowers_scores_and_recommends_refresh(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_qaqc_timestamp(qaqc_path, "2026-04-01T00:00:00+00:00")
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["stale"] is True
    assert blind["qc"]["age_days"] == 42
    assert blind["score"] < 100
    assert blind["state"] == "needs-review"
    assert "Refresh project QC" in blind["recommendations"][0]


def test_project_qc_artifact_head_stale_when_project_changed_since_run(tmp_path: Path, monkeypatch):
    _write_project_files(tmp_path)
    qaqc_path = _write_latest_project_qc(tmp_path)
    data = json.loads(qaqc_path.read_text(encoding="utf-8"))
    data["git"] = {
        "available": True,
        "head_sha": "old-head",
        "branch": "main",
        "dirty_count": 0,
        "dirty_paths": [],
    }
    qaqc_path.write_text(json.dumps(data), encoding="utf-8")
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    monkeypatch.setattr(
        readiness,
        "_changed_paths_between",
        lambda repo_root, base_sha, head_sha: {
            "available": True,
            "paths": ["projects/blind-to-x/scrapers/ppomppu.py", ".ai/HANDOFF.md"],
        },
    )
    github_status = _passing_github_status()
    github_status["head_sha"] = "new-head"

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=github_status,
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    shorts = next(project for project in report["projects"] if project["name"] == "shorts-maker-v2")
    assert blind["qc"]["stale"] is True
    assert blind["qc"]["head_stale"] is True
    assert blind["qc"]["stale_reasons"] == ["artifact_head"]
    assert blind["qc"]["relevant_changes_since_qc"] == ["projects/blind-to-x/scrapers/ppomppu.py"]
    assert blind["state"] == "needs-review"
    assert "predates current project changes" in blind["recommendations"][0]
    assert shorts["qc"]["stale"] is False


def test_project_qc_artifact_head_allows_context_only_changes(tmp_path: Path, monkeypatch):
    _write_project_files(tmp_path)
    qaqc_path = _write_latest_project_qc(tmp_path)
    data = json.loads(qaqc_path.read_text(encoding="utf-8"))
    data["git"] = {
        "available": True,
        "head_sha": "old-head",
        "branch": "main",
        "dirty_count": 0,
        "dirty_paths": [],
    }
    qaqc_path.write_text(json.dumps(data), encoding="utf-8")
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    monkeypatch.setattr(
        readiness,
        "_changed_paths_between",
        lambda repo_root, base_sha, head_sha: {"available": True, "paths": [".ai/HANDOFF.md", ".ai/GOAL.md"]},
    )
    github_status = _passing_github_status()
    github_status["head_sha"] = "new-head"

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        github_status=github_status,
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["stale"] is False
    assert blind["qc"]["head_stale"] is False
    assert blind["qc"]["changed_paths_available"] is True
    assert blind["qc"]["relevant_changes_since_qc"] == []
    assert blind["state"] == "ready"


def test_missing_project_qc_is_unknown_instead_of_root_fallback(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    data = json.loads(qaqc_path.read_text(encoding="utf-8"))
    data["projects"].pop("knowledge-dashboard")
    data["projects"]["root"] = {"status": "PASS", "passed": 1452, "failed": 0, "errors": 0}
    qaqc_path.write_text(json.dumps(data), encoding="utf-8")
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    _write_required_env(tmp_path)

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    knowledge = next(project for project in report["projects"] if project["name"] == "knowledge-dashboard")
    assert knowledge["qc"]["available"] is False
    assert knowledge["qc"]["status"] == "UNKNOWN"
    assert knowledge["qc"]["passed"] == 0
    assert "Refresh project QC" in knowledge["recommendations"][0]


def test_missing_knowledge_dashboard_api_key_blocks_launch_readiness(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_required_env(tmp_path)
    (tmp_path / "projects" / "knowledge-dashboard" / ".env.local").write_text(
        "DASHBOARD_API_KEY=change-me-to-a-long-random-secret\n",
        encoding="utf-8",
    )
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    knowledge = next(project for project in report["projects"] if project["name"] == "knowledge-dashboard")
    assert knowledge["state"] == "blocked"
    assert knowledge["env"]["checks"][0]["name"] == "Dashboard API key"
    assert knowledge["env"]["checks"][0]["severity"] == "blocker"
    assert "DASHBOARD_API_KEY still contains a placeholder" in knowledge["recommendations"][0]


def test_missing_shorts_provider_keys_block_launch_readiness(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_required_env(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    (tmp_path / "projects" / "shorts-maker-v2" / ".env").write_text(
        "OPENAI_API_KEY=your_openai_api_key\n",
        encoding="utf-8",
    )

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    shorts = next(project for project in report["projects"] if project["name"] == "shorts-maker-v2")
    assert shorts["state"] == "blocked"
    assert shorts["env"]["checks"][0]["severity"] == "blocker"
    assert "No usable Shorts generation provider API key" in shorts["recommendations"][0]


def test_missing_blind_to_x_notion_keys_block_launch_readiness(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_required_env(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    (tmp_path / "projects" / "blind-to-x" / ".env").write_text(
        "\n".join(
            (
                "NOTION_API_KEY=notion-secret",
                "NOTION_DATABASE_ID=your_notion_database_id",
                "OPENAI_API_KEY=sk-real-test-key",
                "",
            )
        ),
        encoding="utf-8",
    )

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["state"] == "blocked"
    assert blind["env"]["checks"][0]["name"] == "Notion review queue keys"
    assert blind["env"]["checks"][0]["severity"] == "blocker"
    assert "NOTION_DATABASE_ID" in blind["recommendations"][0]


def test_missing_blind_to_x_provider_keys_block_launch_readiness(tmp_path: Path):
    _write_project_files(tmp_path)
    _write_required_env(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    (tmp_path / "projects" / "blind-to-x" / ".env").write_text(
        "\n".join(
            (
                "NOTION_API_KEY=notion-secret",
                "NOTION_DATABASE_ID=1234567890abcdef1234567890abcdef",
                "OPENAI_API_KEY=sk-...",
                "",
            )
        ),
        encoding="utf-8",
    )

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["state"] == "blocked"
    assert blind["env"]["checks"][1]["name"] == "blind-to-x LLM provider keys"
    assert blind["env"]["checks"][1]["severity"] == "blocker"
    assert "No usable blind-to-x LLM provider API key" in blind["recommendations"][0]
