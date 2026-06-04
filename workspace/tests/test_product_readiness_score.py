"""Unit tests for `execution/product_readiness_score.py`."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


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


def _write_project_files(root: Path) -> None:
    for profile in readiness.PROJECTS.values():
        project_root = root / profile.path
        project_root.mkdir(parents=True, exist_ok=True)
        for relative in profile.required_files:
            target = project_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok\n", encoding="utf-8")


def _write_required_env(root: Path) -> None:
    (root / "projects" / "hanwoo-dashboard" / ".env").write_text(
        "DATABASE_URL=postgres://user:secret@example/db\n",
        encoding="utf-8",
    )
    (root / "projects" / "shorts-maker-v2" / ".env").write_text(
        "OPENAI_API_KEY=sk-real-test-key\n",
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
        "hanwoo-dashboard": ["test", "lint", "build"],
        "knowledge-dashboard": ["test", "lint", "build"],
    }
    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-05-13T00:00:00+00:00",
                "source": "project_qc_runner",
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


def _write_qaqc_timestamp(path: Path, timestamp: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["timestamp"] = timestamp
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_tasks(root: Path, body: str) -> None:
    ai = root / ".ai"
    ai.mkdir(parents=True, exist_ok=True)
    (ai / "TASKS.md").write_text(body, encoding="utf-8")


def test_hanwoo_placeholder_marks_project_blocked(tmp_path: Path):
    _write_project_files(tmp_path)
    (tmp_path / "projects" / "shorts-maker-v2" / ".env").write_text(
        "OPENAI_API_KEY=sk-real-test-key\n",
        encoding="utf-8",
    )
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
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    hanwoo = next(project for project in report["projects"] if project["name"] == "hanwoo-dashboard")
    assert report["overall"]["state"] == "blocked"
    assert hanwoo["state"] == "blocked"
    assert hanwoo["env"]["checks"][0]["severity"] == "blocker"
    assert hanwoo["env"]["checks"][0]["message"] == "Supabase DATABASE_URL still contains a placeholder."
    assert any("Supabase" in item for item in hanwoo["recommendations"])


def test_missing_hanwoo_env_reports_missing_file_instead_of_configured(tmp_path: Path):
    _write_project_files(tmp_path)
    (tmp_path / "projects" / "shorts-maker-v2" / ".env").write_text(
        "OPENAI_API_KEY=sk-real-test-key\n",
        encoding="utf-8",
    )
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
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    assert report["overall"]["state"] == "ready"
    assert report["overall"]["score"] >= 85
    assert all(project["score"] >= 85 for project in report["projects"])


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
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["available"] is True
    assert blind["qc"]["status"] == "PASS"
    assert blind["recommendations"][0] != "Refresh project QC so the score reflects the latest test/lint/build state."
    assert report["overall"]["state"] == "ready"


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

    report = readiness.build_report(
        tmp_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    blind = next(project for project in report["projects"] if project["name"] == "blind-to-x")
    assert blind["qc"]["available"] is False
    assert blind["qc"]["status"] == "PARTIAL"
    assert blind["qc"]["missing_checks"] == ["test"]
    assert blind["recommendations"][0] == "Refresh project QC so the score reflects the latest test/lint/build state."


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
    assert blind["score"] < 85
    assert "Refresh project QC" in blind["recommendations"][0]


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


def test_missing_shorts_provider_keys_block_launch_readiness(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    (tmp_path / "projects" / "hanwoo-dashboard" / ".env").write_text(
        "DATABASE_URL=postgres://user:secret@example/db\n",
        encoding="utf-8",
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
