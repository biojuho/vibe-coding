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


def _write_project_files(root: Path) -> None:
    for profile in readiness.PROJECTS.values():
        project_root = root / profile.path
        project_root.mkdir(parents=True, exist_ok=True)
        for relative in profile.required_files:
            target = project_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok\n", encoding="utf-8")


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
                    "root": {"status": "PASS", "passed": 40, "failed": 0, "errors": 0},
                }
            },
        ),
        encoding="utf-8",
    )
    return path


def _write_tasks(root: Path, body: str) -> None:
    ai = root / ".ai"
    ai.mkdir(parents=True, exist_ok=True)
    (ai / "TASKS.md").write_text(body, encoding="utf-8")


def test_hanwoo_placeholder_marks_project_blocked(tmp_path: Path):
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
    assert any("Supabase" in item for item in hanwoo["recommendations"])


def test_clean_projects_with_docs_and_qc_score_ready(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    (tmp_path / "projects" / "hanwoo-dashboard" / ".env").write_text(
        "DATABASE_URL=postgres://user:secret@example/db\n",
        encoding="utf-8",
    )

    report = readiness.build_report(
        tmp_path,
        qaqc_path=qaqc_path,
        git_status_text="",
        now=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )

    assert report["overall"]["state"] == "ready"
    assert report["overall"]["score"] >= 85
    assert all(project["score"] >= 85 for project in report["projects"])


def test_dirty_paths_lower_the_matching_project_only(tmp_path: Path):
    _write_project_files(tmp_path)
    qaqc_path = _write_qaqc(tmp_path)
    _write_tasks(
        tmp_path, "# TASKS\n\n## TODO\n\n| ID | Task | Owner | Priority | Auto | Created |\n|---|---|---|---|---|---|\n"
    )
    (tmp_path / "projects" / "hanwoo-dashboard" / ".env").write_text(
        "DATABASE_URL=postgres://user:secret@example/db\n",
        encoding="utf-8",
    )

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
