"""Unit tests for the auto-research next experiment selector."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "next_experiment_selector.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("next_experiment_selector", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["next_experiment_selector"] = module
    spec.loader.exec_module(module)
    return module


next_experiment_selector = _load_module()


def _readiness(
    *,
    workspace: int = 0,
    local: int = 0,
    agent: int = 0,
    external: int = 0,
    stale_qc: bool = False,
    missing_actions: bool = False,
) -> dict[str, object]:
    task = {"id": "T-251", "owner": "User", "task": "Supabase credential reset required"}
    recommendations = ["Refresh project QC; latest recorded run is stale."] if stale_qc else ["Keep warm."]
    workflow_status = "missing" if missing_actions else "completed"
    workflow_conclusion = None if missing_actions else "success"
    return {
        "overall": {
            "score": 96 if external else 100,
            "state": "blocked" if external or workspace or local or agent else "ready",
            "workspace_blocker_count": workspace,
            "local_blocker_count": local,
            "agent_task_count": agent,
            "environment_blocker_count": 0,
            "external_blocker_count": external,
        },
        "next_actions": [
            {
                "project": "hanwoo-dashboard" if external else "workspace",
                "action": "Wait for 1 user-owned task blocker(s) before rerunning local launch checks: T-251."
                if external
                else "Resolve local launch blocker.",
            }
        ],
        "projects": [
            {
                "name": "hanwoo-dashboard",
                "path": "projects/hanwoo-dashboard",
                "tasks": [task] if external else [],
                "recommendations": recommendations,
            }
        ],
        "workspace_gates": {
            "github_release": {
                "required_workflows": [
                    {
                        "name": "root-quality-gate",
                        "status": workflow_status,
                        "conclusion": workflow_conclusion,
                    },
                    {
                        "name": "active-project-matrix",
                        "status": workflow_status,
                        "conclusion": workflow_conclusion,
                    },
                ]
            }
        },
    }


def _github(*, dirty: int = 0, prs: int = 0, ahead: int = 0) -> dict[str, object]:
    status = "## main...origin/main"
    if ahead:
        status += f" [ahead {ahead}]"
    return {
        "git": {"dirty_count": dirty, "status": {"stdout": status}},
        "open_prs": {"available": True, "count": prs},
        "recommendations": [],
    }


def _browser(*, missing: int = 0, fresh: int = 4, usable: int = 4, nonblank: int = 4) -> dict[str, object]:
    return {
        "summary": {
            "browser_project_count": 4,
            "missing_count": missing,
            "fresh_screenshot_project_count": fresh,
            "fresh_usable_screenshot_project_count": usable,
            "fresh_nonblank_screenshot_project_count": nonblank,
        },
        "recommendations": [],
    }


def _dependency(*, candidates: int = 0) -> dict[str, object]:
    return {
        "summary": {
            "candidate_dependency_count": candidates,
            "candidate_project_count": 1 if candidates else 0,
        },
        "projects": [
            {"path": "projects/word-chain", "candidate_count": candidates},
        ]
        if candidates
        else [],
    }


def _select(**overrides):
    data = {
        "readiness": _readiness(),
        "github_inventory": _github(),
        "browser_inventory": _browser(),
        "dependency_inventory": _dependency(),
    }
    data.update(overrides)
    return next_experiment_selector.select_next_experiment(**data)


def test_dependency_candidate_is_selected_when_direct_updates_exist() -> None:
    result = _select(dependency_inventory=_dependency(candidates=2))

    assert result["status"] == "candidate"
    assert result["selected"]["kind"] == "dependency_candidate"
    assert result["selected"]["project"] == "projects/word-chain"
    assert "official release notes" in result["selected"]["required_gates"][0]


def test_browser_refresh_outranks_dependency_candidate() -> None:
    result = _select(browser_inventory=_browser(missing=1), dependency_inventory=_dependency(candidates=2))

    assert result["status"] == "candidate"
    assert result["selected"]["kind"] == "browser_qa_refresh"
    assert "direct app-click QA" in result["selected"]["required_gates"]


def test_external_only_blocker_is_not_an_adoptable_experiment() -> None:
    result = _select(readiness=_readiness(external=1))

    assert result["status"] == "blocked_external_only"
    assert result["summary"]["adoptable_candidate_count"] == 0
    assert result["selected"]["kind"] == "external_user_blocker"
    assert result["selected"]["blocked"] is True
    assert result["selected"]["blockers"] == ["1 external/user-owned blocker(s): T-251"]
    assert any("Do not retry T-251" in guardrail for guardrail in result["selected"]["guardrails"])


def test_local_readiness_blocker_outranks_external_blocker() -> None:
    result = _select(readiness=_readiness(local=1, external=1))

    assert result["status"] == "candidate"
    assert result["selected"]["kind"] == "local_readiness_blocker"


def test_ahead_current_head_actions_are_push_authorization_boundary() -> None:
    result = _select(
        readiness=_readiness(workspace=1, local=1, external=1, missing_actions=True),
        github_inventory=_github(ahead=1),
    )

    assert result["status"] == "blocked"
    assert result["selected"]["kind"] == "current_head_release_checks_unproven"
    assert result["selected"]["blocked"] is True
    assert "explicit push authorization or user push" in result["selected"]["required_gates"]
    assert any("Do not push without explicit user authorization" in item for item in result["selected"]["guardrails"])
    assert any("root-quality-gate" in item for item in result["selected"]["evidence"])


def test_ready_workspace_routes_to_completion_audit() -> None:
    result = _select()

    assert result["status"] == "ready_for_completion_audit"
    assert result["selected"]["kind"] == "completion_audit"
    assert result["summary"]["selected_kind"] == "completion_audit"


def test_missing_readiness_schema_routes_to_input_evidence_refresh() -> None:
    result = _select(readiness={})

    assert result["status"] == "candidate"
    assert result["selected"]["kind"] == "input_evidence_unavailable"
    assert "product_readiness_score.py --json" in result["selected"]["required_gates"]
    assert any("readiness: missing required key" in item for item in result["selected"]["evidence"])


def test_cli_writes_ascii_json_artifact(tmp_path: Path, capsys) -> None:
    readiness = tmp_path / "readiness.json"
    github = tmp_path / "github.json"
    browser = tmp_path / "browser.json"
    dependency = tmp_path / "dependency.json"
    output = tmp_path / "next.json"
    readiness.write_text(json.dumps(_readiness(external=1)), encoding="utf-8")
    github.write_text(json.dumps(_github()), encoding="utf-8")
    browser.write_text(json.dumps(_browser()), encoding="utf-8")
    dependency.write_text(json.dumps(_dependency()), encoding="utf-8")

    code = next_experiment_selector.main(
        [
            "--readiness",
            str(readiness),
            "--github",
            str(github),
            "--browser",
            str(browser),
            "--dependency",
            str(dependency),
            "--output",
            str(output),
            "--json",
        ]
    )
    stdout = capsys.readouterr().out
    persisted = json.loads(output.read_text(encoding="utf-8"))

    assert code == 0
    assert json.loads(stdout)["status"] == "blocked_external_only"
    assert persisted["selected"]["kind"] == "external_user_blocker"
    assert output.read_text(encoding="utf-8").isascii()


def test_cli_missing_input_artifact_does_not_route_to_completion(tmp_path: Path, capsys) -> None:
    github = tmp_path / "github.json"
    browser = tmp_path / "browser.json"
    dependency = tmp_path / "dependency.json"
    output = tmp_path / "next.json"
    github.write_text(json.dumps(_github()), encoding="utf-8")
    browser.write_text(json.dumps(_browser()), encoding="utf-8")
    dependency.write_text(json.dumps(_dependency()), encoding="utf-8")

    code = next_experiment_selector.main(
        [
            "--readiness",
            str(tmp_path / "missing-readiness.json"),
            "--github",
            str(github),
            "--browser",
            str(browser),
            "--dependency",
            str(dependency),
            "--output",
            str(output),
            "--json",
        ]
    )
    stdout = json.loads(capsys.readouterr().out)
    persisted = json.loads(output.read_text(encoding="utf-8"))

    assert code == 0
    assert stdout["status"] == "candidate"
    assert stdout["selected"]["kind"] == "input_evidence_unavailable"
    assert persisted["selected"]["kind"] == "input_evidence_unavailable"
    assert any("missing artifact" in item for item in stdout["selected"]["evidence"])


def test_cli_reads_utf16_input_artifacts(tmp_path: Path, capsys) -> None:
    readiness = tmp_path / "readiness.json"
    github = tmp_path / "github.json"
    browser = tmp_path / "browser.json"
    dependency = tmp_path / "dependency.json"
    readiness.write_text(json.dumps(_readiness(external=1)), encoding="utf-16")
    github.write_text(json.dumps(_github()), encoding="utf-8")
    browser.write_text(json.dumps(_browser()), encoding="utf-8")
    dependency.write_text(json.dumps(_dependency()), encoding="utf-8")

    code = next_experiment_selector.main(
        [
            "--readiness",
            str(readiness),
            "--github",
            str(github),
            "--browser",
            str(browser),
            "--dependency",
            str(dependency),
            "--json",
        ]
    )
    stdout = json.loads(capsys.readouterr().out)

    assert code == 0
    assert stdout["status"] == "blocked_external_only"
    assert stdout["selected"]["kind"] == "external_user_blocker"
