"""Unit tests for the auto-research launch objective audit manifest builder."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "launch_objective_audit.py"
COMPLETION_AUDIT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "completion_audit.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


launch_objective_audit = _load_module("launch_objective_audit", SCRIPT_PATH)
completion_audit = _load_module("completion_audit_for_launch_objective_test", COMPLETION_AUDIT_PATH)


def _write_required_skill(root: Path) -> None:
    skill_root = root / ".agents" / "skills" / "auto-research"
    scripts = skill_root / "scripts"
    scripts.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text(
        "\n".join(
            [
                "ab_decision.py",
                "browser_qa_inventory.py",
                "completion_audit.py",
                "dependency_freshness_inventory.py",
                "github_project_inventory.py",
                "launch_objective_audit.py",
            ]
        ),
        encoding="utf-8",
    )
    for name in (
        "ab_decision.py",
        "browser_qa_inventory.py",
        "completion_audit.py",
        "dependency_freshness_inventory.py",
        "github_project_inventory.py",
        "launch_objective_audit.py",
    ):
        (scripts / name).write_text("# helper\n", encoding="utf-8")


def _write_ai_relay(root: Path, *, ab_evidence: bool = True) -> None:
    ai = root / ".ai"
    ai.mkdir()
    (ai / "TASKS.md").write_text(
        "A/B `adopt_candidate` score_delta 1.0" if ab_evidence else "No A/B evidence",
        encoding="utf-8",
    )
    for name in ("HANDOFF.md", "SESSION_LOG.md", "CONTEXT.md"):
        (ai / name).write_text("relay\n", encoding="utf-8")


def _clean_readiness(external_blockers: int = 0) -> dict[str, object]:
    task = {
        "id": "T-251",
        "owner": "User",
        "task": "Supabase password reset required",
    }
    return {
        "overall": {
            "score": 100 if external_blockers == 0 else 96,
            "state": "ready" if external_blockers == 0 else "blocked",
            "workspace_blocker_count": 0,
            "local_blocker_count": 0,
            "agent_task_count": 0,
            "external_blocker_count": external_blockers,
        },
        "workspace_gates": {
            "github_release": {
                "required_workflows": [
                    {"name": "root-quality-gate", "conclusion": "success"},
                    {"name": "active-project-matrix", "conclusion": "success"},
                ]
            }
        },
        "projects": [
            {
                "name": "hanwoo-dashboard",
                "tasks": [task] if external_blockers else [],
            }
        ],
    }


def _github_inventory() -> dict[str, object]:
    return {
        "git": {"dirty_count": 0},
        "projects": [{"path": "projects/hanwoo-dashboard"}],
        "workflows": [".github/workflows/root-quality-gate.yml"],
        "open_prs": {"available": True, "count": 0},
        "recommendations": [],
    }


def _browser_inventory(missing: int = 0) -> dict[str, object]:
    return {
        "summary": {
            "browser_project_count": 4,
            "covered_count": 4 - missing,
            "missing_count": missing,
            "current_screenshot_project_count": 4 - missing,
            "missing_projects": ["projects/word-chain"] if missing else [],
        },
        "recommendations": [],
    }


def _dependency_inventory(candidates: int = 0) -> dict[str, object]:
    return {
        "summary": {
            "candidate_dependency_count": candidates,
            "deferred_dependency_count": 1,
            "unavailable_project_count": 0,
        },
        "recommendations": [],
    }


def test_manifest_is_complete_when_all_requirements_have_current_evidence(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    skill_item = next(item for item in manifest["items"] if item["requirement"].startswith("Create"))

    assert result["status"] == "complete"
    assert result["summary"]["complete_count"] == len(manifest["items"])
    assert any("launch objective audit" in evidence for evidence in skill_item["evidence"])


def test_external_user_blocker_prevents_completion(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(external_blockers=1),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)

    assert result["status"] == "incomplete"
    assert result["summary"]["blocked_count"] == 1
    assert any("T-251" in blocker for item in manifest["items"] for blocker in item["blockers"])


def test_missing_browser_qa_is_reported_as_blocker(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(missing=1),
        dependency_inventory=_dependency_inventory(),
    )
    browser_item = next(item for item in manifest["items"] if item["requirement"].startswith("Use Codex"))

    assert browser_item["coverage"] == "partial"
    assert any("projects/word-chain" in blocker for blocker in browser_item["blockers"])


def test_dependency_candidates_are_not_claimed_complete(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(candidates=2),
    )
    dependency_item = next(item for item in manifest["items"] if item["requirement"].startswith("Research"))

    assert dependency_item["coverage"] == "partial"
    assert "2 direct patch/minor dependency candidate(s) remain." in dependency_item["blockers"]
