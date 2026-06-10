"""Unit tests for the auto-research next experiment selector."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
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
_input_evidence_candidate = next_experiment_selector._input_evidence_candidate
_dirty_worktree_candidate = next_experiment_selector._dirty_worktree_candidate
_github_candidate = next_experiment_selector._github_candidate
_browser_candidate = next_experiment_selector._browser_candidate
_dependency_candidate = next_experiment_selector._dependency_candidate
_project_qc_candidate = next_experiment_selector._project_qc_candidate


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


def _github(
    *,
    dirty: int = 0,
    prs: int = 0,
    ahead: int = 0,
    dirty_groups: list[dict[str, object]] | None = None,
    dirty_paths: list[str] | None = None,
) -> dict[str, object]:
    status = "## main...origin/main"
    if ahead:
        status += f" [ahead {ahead}]"
    return {
        "git": {
            "dirty_count": dirty,
            "dirty_paths": dirty_paths or [],
            "dirty_path_groups": dirty_groups or [],
            "status": {"stdout": status},
        },
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


def _dirty_plan(
    *,
    dirty_count: int = 2,
    dirty_paths: list[str] | None = None,
    current: bool = True,
    previous_status: str | None = None,
) -> dict[str, object]:
    paths = dirty_paths or [".ai/HANDOFF.md", ".agents/skills/auto-research/scripts/next_experiment_selector.py"]
    plan: dict[str, object] = {
        "status": "handoff_required",
        "freshness": {"status": "current" if current else "stale", "current": current},
        "dirty_signature": {
            "algorithm": "sha256",
            "value": "test-signature",
            "input": {"dirty_count": dirty_count, "dirty_paths": paths},
        },
        "group_order": [
            {"key": "auto-research"},
            {"key": "ai-context"},
        ],
    }
    if previous_status is not None:
        plan["previous_plan_freshness"] = {"status": previous_status, "current": previous_status == "current"}
    return plan


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
    assert next_experiment_selector.DEPENDENCY_INVENTORY_GATE in result["selected"]["required_gates"]
    assert any("official release notes" in gate for gate in result["selected"]["required_gates"])


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

    assert result["status"] == "blocked_publish_only"
    assert result["selected"]["kind"] == "current_head_release_checks_unproven"
    assert result["selected"]["blocked"] is True
    assert "release_authorization_packet.py --json" in result["selected"]["required_gates"]
    assert "explicit push authorization or user push" in result["selected"]["required_gates"]
    assert any("release authorization packet" in item for item in result["selected"]["evidence"])
    assert any("Do not push without explicit user authorization" in item for item in result["selected"]["guardrails"])
    assert any("root-quality-gate" in item for item in result["selected"]["evidence"])


def test_dirty_ahead_branch_routes_to_worktree_handoff_before_publish_authorization() -> None:
    result = _select(
        readiness=_readiness(workspace=1, local=1, external=1, missing_actions=True),
        github_inventory=_github(
            dirty=2,
            ahead=1,
            dirty_groups=[{"key": "ai-context", "path_count": 1}, {"key": "auto-research", "path_count": 1}],
        ),
    )

    assert result["status"] == "candidate"
    assert result["selected"]["kind"] == "dirty_worktree_handoff"
    assert result["selected"]["required_gates"][0] == next_experiment_selector.GITHUB_INVENTORY_GATE
    assert next_experiment_selector.DIRTY_HANDOFF_PLAN_GATE in result["selected"]["required_gates"]
    assert "python execution/session_orient.py --json" in result["selected"]["required_gates"]
    assert next_experiment_selector.PRODUCT_READINESS_GATE in result["selected"]["required_gates"]
    assert "dirty groups: ai-context=1, auto-research=1" in result["selected"]["evidence"]
    assert all(candidate["kind"] != "current_head_release_checks_unproven" for candidate in result["ranked_candidates"])


def test_current_dirty_handoff_plan_blocks_repeated_handoff_generation() -> None:
    dirty_paths = [".ai/HANDOFF.md", ".agents/skills/auto-research/scripts/next_experiment_selector.py"]
    result = _select(
        readiness=_readiness(workspace=1, local=1, external=1, missing_actions=True),
        github_inventory=_github(
            dirty=2,
            ahead=1,
            dirty_paths=dirty_paths,
            dirty_groups=[{"key": "ai-context", "path_count": 1}, {"key": "auto-research", "path_count": 1}],
        ),
        dirty_handoff_plan=_dirty_plan(dirty_paths=dirty_paths),
    )

    assert result["status"] == "blocked"
    assert result["summary"]["adoptable_candidate_count"] == 0
    assert result["selected"]["kind"] == "dirty_worktree_handoff_current"
    assert result["selected"]["blocked"] is True
    assert next_experiment_selector.DIRTY_HANDOFF_PLAN_GATE in result["selected"]["required_gates"]
    assert next_experiment_selector.DEBUG_INVENTORY_COMPLETION_BLOCKED_GATE in result["selected"]["required_gates"]
    assert any("handoff plan freshness=current" in item for item in result["selected"]["evidence"])
    assert any("handoff plan signature=test-signature" in item for item in result["selected"]["evidence"])
    assert any("explicit scoped staging/commit authorization" in item for item in result["selected"]["blockers"])
    assert any("exit code 1" in item for item in result["selected"]["guardrails"])
    expectation = result["selected"]["gate_expectations"][0]
    assert expectation["gate"] == next_experiment_selector.DEBUG_INVENTORY_COMPLETION_BLOCKED_GATE
    assert expectation["expected_exit_codes"] == [1]
    assert "not a source failure" in expectation["meaning"]


def test_matching_dirty_handoff_signature_blocks_even_when_previous_plan_was_stale() -> None:
    dirty_paths = [".ai/HANDOFF.md", "docs/wiki/llm/27-data-retention-privacy-logging.md"]
    result = _select(
        readiness=_readiness(workspace=1, local=1, external=1, missing_actions=True),
        github_inventory=_github(dirty=2, dirty_paths=dirty_paths),
        dirty_handoff_plan=_dirty_plan(dirty_paths=dirty_paths, previous_status="stale"),
    )

    assert result["status"] == "blocked"
    assert result["selected"]["kind"] == "dirty_worktree_handoff_current"
    assert any("handoff plan freshness=current" in item for item in result["selected"]["evidence"])
    assert any("previous handoff plan freshness=stale" in item for item in result["selected"]["evidence"])
    assert any("signature matches current dirty inventory" in item for item in result["selected"]["evidence"])
    blocker_text = "\n".join(result["selected"]["blockers"])
    assert "matches the current dirty inventory" in blocker_text
    assert "plan is fresh" not in blocker_text


def test_legacy_stale_dirty_handoff_plan_match_is_labeled_current_by_signature() -> None:
    dirty_paths = [".ai/HANDOFF.md", "docs/wiki/llm/27-data-retention-privacy-logging.md"]
    result = _select(
        readiness=_readiness(workspace=1, local=1, external=1, missing_actions=True),
        github_inventory=_github(dirty=2, dirty_paths=dirty_paths),
        dirty_handoff_plan=_dirty_plan(dirty_paths=dirty_paths, current=False),
    )

    assert result["status"] == "blocked"
    assert result["selected"]["kind"] == "dirty_worktree_handoff_current"
    assert any(
        "handoff plan freshness=current_by_signature (recorded=stale)" in item
        for item in result["selected"]["evidence"]
    )


def test_dirty_handoff_plan_matches_inventory_evidence_separates_current_and_previous_freshness() -> None:
    dirty_paths = [".ai/HANDOFF.md", "docs/wiki/llm/27-data-retention-privacy-logging.md"]
    matches, evidence = next_experiment_selector._dirty_handoff_plan_matches_inventory(
        _dirty_plan(dirty_paths=dirty_paths, previous_status="stale"),
        _github(dirty=2, dirty_paths=dirty_paths),
    )

    assert matches is True
    assert "handoff plan freshness=current" in evidence
    assert "previous handoff plan freshness=stale" in evidence
    assert "handoff plan freshness=stale" not in evidence


def test_stale_or_mismatched_dirty_handoff_plan_still_requests_refresh() -> None:
    result = _select(
        github_inventory=_github(
            dirty=2,
            dirty_paths=[".ai/HANDOFF.md", ".agents/skills/auto-research/scripts/next_experiment_selector.py"],
        ),
        dirty_handoff_plan=_dirty_plan(dirty_paths=["different.py"]),
    )

    assert result["status"] == "candidate"
    assert result["selected"]["kind"] == "dirty_worktree_handoff"
    assert result["selected"]["gate_expectations"] == []
    assert result["selected"]["blocked"] is False


def test_open_pr_routes_to_github_inventory_followup() -> None:
    result = _select(github_inventory=_github(prs=1))

    assert result["status"] == "candidate"
    assert result["selected"]["kind"] == "github_inventory_followup"
    assert any("open_prs.count=1" in item for item in result["selected"]["evidence"])


def test_ready_workspace_routes_to_completion_audit() -> None:
    result = _select()

    assert result["status"] == "ready_for_completion_audit"
    assert result["selected"]["kind"] == "completion_audit"
    assert result["summary"]["selected_kind"] == "completion_audit"


def test_missing_readiness_schema_routes_to_input_evidence_refresh() -> None:
    result = _select(readiness={})

    assert result["status"] == "candidate"
    assert result["selected"]["kind"] == "input_evidence_unavailable"
    assert next_experiment_selector.PRODUCT_READINESS_GATE in result["selected"]["required_gates"]
    assert next_experiment_selector.GITHUB_INVENTORY_GATE in result["selected"]["required_gates"]
    assert any("readiness: missing required key" in item for item in result["selected"]["evidence"])


def test_candidate_helpers_emit_executable_required_gates() -> None:
    input_candidate = _input_evidence_candidate({}, _github(), _browser(), _dependency())
    dirty_candidate = _dirty_worktree_candidate(_github(dirty=1))
    github_candidate = _github_candidate(_github(prs=1))
    browser_candidate = _browser_candidate(_browser(missing=1))
    dependency_candidate = _dependency_candidate(_dependency(candidates=1))
    project_qc_candidate = _project_qc_candidate(_readiness(stale_qc=True))

    assert input_candidate is not None
    assert input_candidate["required_gates"] == [
        next_experiment_selector.PRODUCT_READINESS_GATE,
        next_experiment_selector.GITHUB_INVENTORY_GATE,
        next_experiment_selector.BROWSER_QA_INVENTORY_GATE,
        next_experiment_selector.DEPENDENCY_INVENTORY_GATE,
    ]
    assert dirty_candidate is not None
    assert dirty_candidate["required_gates"] == [
        next_experiment_selector.GITHUB_INVENTORY_GATE,
        next_experiment_selector.DIRTY_HANDOFF_PLAN_GATE,
        "python execution/session_orient.py --json",
        next_experiment_selector.PRODUCT_READINESS_GATE,
    ]
    assert github_candidate is not None
    assert github_candidate["required_gates"] == [
        next_experiment_selector.GITHUB_INVENTORY_GATE,
        "python execution/session_orient.py --json",
    ]
    assert browser_candidate is not None
    assert browser_candidate["required_gates"][0] == next_experiment_selector.BROWSER_QA_INVENTORY_GATE
    assert dependency_candidate is not None
    assert dependency_candidate["required_gates"][0] == next_experiment_selector.DEPENDENCY_INVENTORY_GATE
    assert project_qc_candidate is not None
    assert project_qc_candidate["required_gates"] == [
        "python execution/project_qc_runner.py --json",
        next_experiment_selector.PRODUCT_READINESS_GATE,
    ]


def test_candidate_helper_defaults_and_preserves_gate_expectations() -> None:
    candidate = next_experiment_selector._candidate(
        kind="test_candidate",
        priority=1,
        project="workspace",
        action="Run focused gate.",
        reason="Unit test contract.",
        evidence=["evidence"],
        required_gates=["gate"],
    )
    expectation = next_experiment_selector._gate_expectation(
        gate="gate",
        expected_exit_codes=[1],
        meaning="expected blocked proof",
    )
    candidate_with_expectation = next_experiment_selector._candidate(
        kind="test_candidate",
        priority=1,
        project="workspace",
        action="Run focused gate.",
        reason="Unit test contract.",
        evidence=["evidence"],
        required_gates=["gate"],
        gate_expectations=[expectation],
    )

    assert candidate["gate_expectations"] == []
    assert candidate_with_expectation["gate_expectations"] == [expectation]


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


def test_cli_reads_dirty_handoff_plan_artifact(tmp_path: Path, capsys) -> None:
    dirty_paths = [".ai/HANDOFF.md", ".agents/skills/auto-research/scripts/next_experiment_selector.py"]
    readiness = tmp_path / "readiness.json"
    github = tmp_path / "github.json"
    browser = tmp_path / "browser.json"
    dependency = tmp_path / "dependency.json"
    dirty_plan = tmp_path / "dirty-plan.json"
    readiness.write_text(json.dumps(_readiness(workspace=1, local=1, external=1)), encoding="utf-8")
    github.write_text(json.dumps(_github(dirty=2, dirty_paths=dirty_paths)), encoding="utf-8")
    browser.write_text(json.dumps(_browser()), encoding="utf-8")
    dependency.write_text(json.dumps(_dependency()), encoding="utf-8")
    dirty_plan.write_text(json.dumps(_dirty_plan(dirty_paths=dirty_paths)), encoding="utf-8")

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
            "--dirty-handoff-plan",
            str(dirty_plan),
            "--json",
        ]
    )
    stdout = json.loads(capsys.readouterr().out)

    assert code == 0
    assert stdout["status"] == "blocked"
    assert stdout["selected"]["kind"] == "dirty_worktree_handoff_current"
    assert next_experiment_selector.DEBUG_INVENTORY_COMPLETION_BLOCKED_GATE in stdout["selected"]["required_gates"]
    expectation = stdout["selected"]["gate_expectations"][0]
    assert expectation["gate"] == next_experiment_selector.DEBUG_INVENTORY_COMPLETION_BLOCKED_GATE
    assert expectation["expected_exit_codes"] == [1]
    assert "not a source failure" in expectation["meaning"]


def test_cli_live_helper_defaults_are_bounded(tmp_path: Path, capsys, monkeypatch) -> None:
    calls = []

    def fake_run_json(root: Path, command: list[str], timeout: int) -> dict[str, object]:
        calls.append((root, command, timeout))
        command_text = " ".join(command)
        if "product_readiness_score.py" in command_text:
            data = _readiness(external=1)
        elif "github_project_inventory.py" in command_text:
            data = _github()
        elif "browser_qa_inventory.py" in command_text:
            data = _browser()
        elif "dependency_freshness_inventory.py" in command_text:
            data = _dependency()
        else:
            data = {}
        return {"available": True, "returncode": 0, "stderr": "", "data": data}

    monkeypatch.setattr(next_experiment_selector, "_run_json", fake_run_json)

    code = next_experiment_selector.main(["--root", str(tmp_path), "--json"])
    stdout = json.loads(capsys.readouterr().out)

    assert code == 0
    assert stdout["status"] == "blocked_external_only"
    assert calls
    assert all(timeout == next_experiment_selector.DEFAULT_LIVE_HELPER_TIMEOUT for _, _, timeout in calls)
    inventory_commands = {
        "github": [command for _, command, _ in calls if "github_project_inventory.py" in " ".join(command)][0],
        "browser": [command for _, command, _ in calls if "browser_qa_inventory.py" in " ".join(command)][0],
        "dependency": [command for _, command, _ in calls if "dependency_freshness_inventory.py" in " ".join(command)][
            0
        ],
    }
    expected_outputs = {
        "github": tmp_path / next_experiment_selector.GITHUB_INVENTORY_CACHE,
        "browser": tmp_path / next_experiment_selector.BROWSER_INVENTORY_CACHE,
        "dependency": tmp_path / next_experiment_selector.DEPENDENCY_INVENTORY_CACHE,
    }
    for label, command in inventory_commands.items():
        assert "--output" in command
        assert command[command.index("--output") + 1] == str(expected_outputs[label])
    dependency_calls = [command for _, command, _ in calls if "dependency_freshness_inventory.py" in " ".join(command)]
    assert dependency_calls
    dependency_command = dependency_calls[0]
    assert "--timeout" in dependency_command
    assert dependency_command[dependency_command.index("--timeout") + 1] == str(
        next_experiment_selector.DEFAULT_DEPENDENCY_HELPER_TIMEOUT
    )


def test_cli_uses_recent_inventory_artifacts_when_live_helpers_timeout(tmp_path: Path, capsys, monkeypatch) -> None:
    artifact_dir = tmp_path / ".tmp"
    artifact_dir.mkdir()
    (artifact_dir / "browser-qa-inventory.json").write_text(json.dumps(_browser()), encoding="utf-8")
    (artifact_dir / "dependency-freshness-inventory.json").write_text(json.dumps(_dependency()), encoding="utf-8")

    def fake_run_json(root: Path, command: list[str], timeout: int) -> dict[str, object]:
        command_text = " ".join(command)
        if "product_readiness_score.py" in command_text:
            return {"available": True, "returncode": 0, "stderr": "", "data": _readiness(external=1)}
        if "github_project_inventory.py" in command_text:
            return {"available": True, "returncode": 0, "stderr": "", "data": _github()}
        return {"available": False, "returncode": None, "stderr": "timed out", "data": {}}

    monkeypatch.setattr(next_experiment_selector, "_run_json", fake_run_json)

    code = next_experiment_selector.main(["--root", str(tmp_path), "--json"])
    stdout = json.loads(capsys.readouterr().out)

    assert code == 0
    assert stdout["status"] == "blocked_external_only"
    assert stdout["selected"]["kind"] == "external_user_blocker"
    assert all(candidate["kind"] != "input_evidence_unavailable" for candidate in stdout["ranked_candidates"])


def test_cli_ignores_stale_inventory_artifact_fallbacks(tmp_path: Path, capsys, monkeypatch) -> None:
    artifact_dir = tmp_path / ".tmp"
    artifact_dir.mkdir()
    browser = artifact_dir / "browser-qa-inventory.json"
    dependency = artifact_dir / "dependency-freshness-inventory.json"
    browser.write_text(json.dumps(_browser()), encoding="utf-8")
    dependency.write_text(json.dumps(_dependency()), encoding="utf-8")
    stale_mtime = time.time() - 10
    os.utime(browser, (stale_mtime, stale_mtime))
    os.utime(dependency, (stale_mtime, stale_mtime))

    def fake_run_json(root: Path, command: list[str], timeout: int) -> dict[str, object]:
        command_text = " ".join(command)
        if "product_readiness_score.py" in command_text:
            return {"available": True, "returncode": 0, "stderr": "", "data": _readiness(external=1)}
        if "github_project_inventory.py" in command_text:
            return {"available": True, "returncode": 0, "stderr": "", "data": _github()}
        return {"available": False, "returncode": None, "stderr": "timed out", "data": {}}

    monkeypatch.setattr(next_experiment_selector, "_run_json", fake_run_json)

    code = next_experiment_selector.main(["--root", str(tmp_path), "--cache-max-age-seconds", "1", "--json"])
    stdout = json.loads(capsys.readouterr().out)

    assert code == 0
    assert stdout["status"] == "candidate"
    assert stdout["selected"]["kind"] == "input_evidence_unavailable"
    assert any("helper command unavailable" in item for item in stdout["selected"]["evidence"])


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


def test_print_text_includes_blockers_gates_and_expected_failure_contract(capsys) -> None:
    next_experiment_selector._print_text(
        {
            "status": "blocked",
            "selected": {
                "kind": "dirty_worktree_handoff_current",
                "project": "workspace",
                "action": "Wait for authorization.",
                "blockers": ["Scoped staging authorization required."],
                "required_gates": ["python execution/session_orient.py --json"],
                "gate_expectations": [
                    {
                        "gate": "debug_loop_inventory.py --fail-on-completion-blocked",
                        "expected_exit_codes": [1],
                        "meaning": "blocked completion proof",
                    }
                ],
            },
        }
    )

    output = capsys.readouterr().out
    assert "next experiment status: blocked" in output
    assert "selected: dirty_worktree_handoff_current (workspace)" in output
    assert "blocker: Scoped staging authorization required." in output
    assert "gate: python execution/session_orient.py --json" in output
    assert (
        "gate_expectation: debug_loop_inventory.py --fail-on-completion-blocked "
        "expected_exit_codes=1 meaning=blocked completion proof"
    ) in output
