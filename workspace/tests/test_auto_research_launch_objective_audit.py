"""Unit tests for the auto-research launch objective audit manifest builder."""

from __future__ import annotations

import importlib.util
import json
import os
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
                "next_experiment_selector.py",
                "release_authorization_packet.py",
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
        "next_experiment_selector.py",
        "release_authorization_packet.py",
    ):
        (scripts / name).write_text("# helper\n", encoding="utf-8")


def _write_ai_relay(
    root: Path,
    *,
    ab_evidence: bool = True,
    goal_status: str = "active",
    goal_text: str = "Product launch auto-research loop across GitHub, browser QA, and A/B adoption.",
) -> None:
    ai = root / ".ai"
    ai.mkdir()
    (ai / "TASKS.md").write_text(
        "A/B `adopt_candidate` score_delta 1.0" if ab_evidence else "No A/B evidence",
        encoding="utf-8",
    )
    for name in ("HANDOFF.md", "SESSION_LOG.md", "CONTEXT.md"):
        (ai / name).write_text("relay\n", encoding="utf-8")
    (ai / "GOAL.md").write_text(
        "\n".join(
            [
                "# GOAL - Active Workspace Goal",
                "",
                "## Active Goal",
                "",
                f"- Status: {goal_status}",
                f"- Goal: {goal_text}",
                "- Owner: Codex",
                "- Started: 2026-06-05",
                "- Success: Launch audit complete with every explicit requirement verified.",
            ]
        ),
        encoding="utf-8",
    )
    _write_shorts_feature_checklist(root)


def _write_ab_manifest(
    root: Path,
    *,
    gate_passes: bool = True,
    name: str = "ab-manifest-t-test.json",
    encoding: str = "utf-8",
    experiment: str = "T-test launch audit A/B manifest evidence",
) -> Path:
    tmp = root / ".tmp"
    tmp.mkdir(exist_ok=True)
    manifest = {
        "experiment": experiment,
        "baseline": {"metrics": {"evidence_strength": 0}},
        "candidate": {
            "metrics": {"evidence_strength": 1},
            "gates": {"focused_tests": gate_passes, "diff_check": True},
        },
        "directions": {"evidence_strength": "higher"},
        "required_gates": ["focused_tests", "diff_check"],
        "min_delta": 0,
    }
    path = tmp / name
    path.write_text(json.dumps(manifest), encoding=encoding)
    return path


def _write_shorts_feature_checklist(root: Path, *, complete: bool = True) -> None:
    feature = root / "projects" / "shorts-maker-v2" / "FEATURE.md"
    feature.parent.mkdir(parents=True, exist_ok=True)
    marker = "x" if complete else " "
    feature.write_text(
        "\n".join(
            [
                "# FEATURE",
                "",
                "## Acceptance criteria",
                "",
                f"- [{marker}] ProjectSettings exposes qc_strictness and scene_qc_max_retries.",
                f"- [{marker}] QCStep supports strict, lenient, and off strictness modes.",
            ]
        ),
        encoding="utf-8",
    )


def _clean_readiness(
    external_blockers: int = 0,
    *,
    include_user_task: bool = True,
    user_task_owner: str = "User",
    blind_score: int = 100,
    blind_state: str = "ready",
    blind_qc_status: str = "PASS",
    blind_qc_failed: int = 0,
    blind_qc_stale: bool = False,
    blind_env_ok: bool = True,
    shorts_score: int = 100,
    shorts_state: str = "ready",
    shorts_qc_status: str = "PASS",
    shorts_qc_failed: int = 0,
    shorts_qc_stale: bool = False,
    shorts_env_ok: bool = True,
    hanwoo_score: int | None = None,
    hanwoo_state: str | None = None,
    hanwoo_qc_status: str = "PASS",
    hanwoo_qc_failed: int = 0,
    hanwoo_qc_stale: bool = False,
    hanwoo_env_ok: bool = True,
) -> dict[str, object]:
    task = {
        "id": "T-251",
        "owner": user_task_owner,
        "task": "Supabase password reset required",
    }
    resolved_hanwoo_score = hanwoo_score if hanwoo_score is not None else (86 if external_blockers else 100)
    resolved_hanwoo_state = hanwoo_state if hanwoo_state is not None else ("blocked" if external_blockers else "ready")
    return {
        "overall": {
            "score": 100 if external_blockers == 0 else 96,
            "state": "ready" if external_blockers == 0 else "blocked",
            "workspace_blocker_count": 0,
            "local_blocker_count": 0,
            "publish_blocker_count": 0,
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
                "name": "blind-to-x",
                "path": "projects/blind-to-x",
                "score": blind_score,
                "state": blind_state,
                "qc": {
                    "available": True,
                    "status": blind_qc_status,
                    "passed": 1723,
                    "failed": blind_qc_failed,
                    "skipped": 9,
                    "stale": blind_qc_stale,
                },
                "docs": [
                    {"path": "projects/blind-to-x/README.md", "present": True},
                    {"path": "projects/blind-to-x/config.example.yaml", "present": True},
                    {"path": "projects/blind-to-x/docs/ops-runbook.md", "present": True},
                ],
                "env": {
                    "checks": [
                        {
                            "name": "Notion review queue keys",
                            "ok": blind_env_ok,
                        },
                        {
                            "name": "blind-to-x LLM provider keys",
                            "ok": blind_env_ok,
                        },
                    ]
                },
                "tasks": [],
                "dirty_paths": [],
            },
            {
                "name": "shorts-maker-v2",
                "path": "projects/shorts-maker-v2",
                "score": shorts_score,
                "state": shorts_state,
                "qc": {
                    "available": True,
                    "status": shorts_qc_status,
                    "passed": 1577,
                    "failed": shorts_qc_failed,
                    "skipped": 12,
                    "stale": shorts_qc_stale,
                },
                "docs": [
                    {"path": "projects/shorts-maker-v2/README.md", "present": True},
                    {"path": "projects/shorts-maker-v2/ARCHITECTURE.md", "present": True},
                    {"path": "projects/shorts-maker-v2/CLAUDE.md", "present": True},
                    {"path": "projects/shorts-maker-v2/FEATURE.md", "present": True},
                    {"path": "projects/shorts-maker-v2/pyproject.toml", "present": True},
                ],
                "env": {
                    "checks": [
                        {
                            "name": "Shorts generation provider keys",
                            "ok": shorts_env_ok,
                        },
                    ]
                },
                "tasks": [],
                "dirty_paths": [],
            },
            {
                "name": "hanwoo-dashboard",
                "path": "projects/hanwoo-dashboard",
                "score": resolved_hanwoo_score,
                "state": resolved_hanwoo_state,
                "qc": {
                    "available": True,
                    "status": hanwoo_qc_status,
                    "passed": 500,
                    "failed": hanwoo_qc_failed,
                    "skipped": 0,
                    "stale": hanwoo_qc_stale,
                },
                "docs": [
                    {"path": "projects/hanwoo-dashboard/README.md", "present": True},
                    {"path": "projects/hanwoo-dashboard/API_SPEC.md", "present": True},
                    {"path": "projects/hanwoo-dashboard/package.json", "present": True},
                    {"path": "projects/hanwoo-dashboard/.env.example", "present": True},
                ],
                "env": {
                    "checks": [
                        {
                            "name": "Supabase DATABASE_URL",
                            "ok": hanwoo_env_ok,
                        },
                    ]
                },
                "tasks": [task] if external_blockers and include_user_task else [],
                "dirty_paths": [],
            },
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


def _browser_inventory(
    missing: int = 0,
    *,
    fresh: int | None = None,
    stale: int = 0,
    fresh_usable: int | None = None,
    fresh_nonblank: int | None = None,
) -> dict[str, object]:
    screenshot_count = 4 - missing
    fresh_count = screenshot_count if fresh is None else fresh
    return {
        "summary": {
            "browser_project_count": 4,
            "covered_count": 4 - missing,
            "missing_count": missing,
            "current_screenshot_project_count": screenshot_count,
            "fresh_screenshot_project_count": fresh_count,
            "stale_screenshot_project_count": stale,
            "fresh_usable_screenshot_project_count": fresh_count if fresh_usable is None else fresh_usable,
            "fresh_nonblank_screenshot_project_count": fresh_count if fresh_nonblank is None else fresh_nonblank,
            "missing_projects": ["projects/word-chain"] if missing else [],
        },
        "recommendations": [],
    }


def _dependency_inventory(
    candidates: int = 0,
    *,
    peer_blocked: bool = False,
    prerelease_current: bool = False,
) -> dict[str, object]:
    deferred_count = 2 if peer_blocked else 1
    inventory: dict[str, object] = {
        "summary": {
            "candidate_dependency_count": candidates,
            "deferred_dependency_count": deferred_count,
            "outdated_dependency_count": candidates + deferred_count + (1 if prerelease_current else 0),
            "unavailable_project_count": 0,
        },
        "recommendations": [],
    }
    if peer_blocked:
        inventory["projects"] = [
            {
                "path": "projects/hanwoo-dashboard",
                "dependencies": [
                    {
                        "name": "eslint",
                        "deferred": True,
                        "peer_blocker_check": "blocked",
                        "peer_blocker_count": 4,
                        "peer_blocker_latest_check": "partial_upstream_support",
                        "peer_blocker_latest_supported_count": 1,
                        "peer_blocker_latest_blocked_count": 3,
                        "peer_blocker_latest_unavailable_count": 0,
                    }
                ],
            },
            {
                "path": "projects/knowledge-dashboard",
                "dependencies": [
                    {
                        "name": "eslint",
                        "deferred": True,
                        "peer_blocker_check": "blocked",
                        "peer_blocker_count": 3,
                        "peer_blocker_latest_check": "still_blocked",
                        "peer_blocker_latest_supported_count": 0,
                        "peer_blocker_latest_blocked_count": 3,
                        "peer_blocker_latest_unavailable_count": 0,
                    }
                ],
            },
        ]
        inventory["recommendations"] = [
            "No direct npm patch/minor adoption candidates; wait for upstream peer support before major migrations."
        ]
    if prerelease_current:
        projects = inventory.setdefault("projects", [])
        assert isinstance(projects, list)
        projects.append(
            {
                "path": "projects/hanwoo-dashboard",
                "dependencies": [
                    {
                        "name": "next-auth",
                        "current": "5.0.0-beta.31",
                        "latest": "4.24.14",
                        "classification": "current_prerelease_channel",
                        "dist_tag_channel": "beta",
                        "dist_tag_version": "5.0.0-beta.31",
                    }
                ],
            }
        )
    return inventory


def _session_orientation(*, freshness: str = "current") -> dict[str, object]:
    return {
        "graph": {
            "freshness": freshness,
            "built_at_commit": "abcdef123456",
            "current_head": "abcdef12",
            "stale": freshness != "current",
        }
    }


def _code_review_gate(*, status: str = "pass", risk_score: float = 0.0) -> dict[str, object]:
    return {
        "status": status,
        "risk_score": risk_score,
        "changed_files": [".ai/HANDOFF.md"],
        "test_gaps": [] if status == "pass" else ["missing direct test"],
    }


def _selector_selection(
    status: str = "blocked_external_only",
    *,
    kind: str = "external_user_blocker",
    blocked: bool = True,
    project: str = "projects/hanwoo-dashboard",
    guardrails: list[str] | None = None,
    required_gates: list[str] | None = None,
) -> dict[str, object]:
    selected = {
        "kind": kind,
        "project": project,
        "action": "Wait for user-owned external blocker(s): T-251."
        if kind == "external_user_blocker"
        else "Resolve local launch blocker",
        "blocked": blocked,
        "blockers": ["1 external/user-owned blocker(s): T-251"] if blocked else [],
        "guardrails": guardrails
        if guardrails is not None
        else ["Do not retry T-251 until Supabase Dashboard credentials are reset."],
        "required_gates": required_gates
        if required_gates is not None
        else ["Supabase credential reset by user", "Hanwoo live Prisma CRUD E2E after reset"],
    }
    return {
        "status": status,
        "selected": selected,
        "ranked_candidates": [selected],
        "summary": {
            "adoptable_candidate_count": 0 if blocked else 1,
            "blocked_candidate_count": 1 if blocked else 0,
            "selected_kind": kind,
        },
    }


def _release_packet(
    *,
    status: str = "ready_for_authorization",
    ahead_count: int = 3,
    dirty_count: int = 0,
    allowed_without_authorization: bool = False,
    blockers: list[str] | None = None,
) -> dict[str, object]:
    resolved_blockers = (
        blockers
        if blockers is not None
        else [
            "current-head Actions unavailable until push authorization/user push",
            "external/user-owned blocker(s): T-251",
        ]
    )
    return {
        "status": status,
        "git": {
            "branch": "main",
            "head_sha": "abcdef123456",
            "ahead_count": ahead_count,
            "dirty_count": dirty_count,
            "dirty_paths": ["workspace/tests/example.py"] if dirty_count else [],
        },
        "required_workflows": [
            {"name": "root-quality-gate", "status": "missing", "conclusion": None},
            {"name": "active-project-matrix", "status": "missing", "conclusion": None},
        ],
        "unproven_workflows": ["root-quality-gate", "active-project-matrix"] if ahead_count else [],
        "authorization": {
            "push_required": ahead_count > 0,
            "allowed_without_explicit_user_authorization": allowed_without_authorization,
            "suggested_command": "git push origin main" if ahead_count and not dirty_count else None,
            "post_push_gates": ["root-quality-gate", "active-project-matrix"],
            "guardrails": [
                "Do not push without explicit user authorization.",
                "Do not retry external T-251 until Supabase credentials were reset.",
            ],
        },
        "blockers": resolved_blockers,
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
    assert any("next experiment selector" in evidence for evidence in skill_item["evidence"])


def test_readiness_publish_boundary_has_complete_coverage_with_blocker(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    readiness = _clean_readiness()
    assert isinstance(readiness["overall"], dict)
    readiness["overall"]["state"] = "blocked"
    readiness["overall"]["workspace_blocker_count"] = 1
    readiness["overall"]["publish_blocker_count"] = 1
    assert isinstance(readiness["workspace_gates"], dict)
    readiness["workspace_gates"]["github_release"] = {
        "required_workflows": [
            {"name": "root-quality-gate", "status": "missing", "conclusion": None},
            {"name": "active-project-matrix", "status": "missing", "conclusion": None},
        ],
        "blockers": [
            {
                "name": "Required GitHub Actions",
                "severity": "blocker",
                "blocker_type": "publish",
                "message": "Push only with explicit authorization.",
            }
        ],
    }

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=readiness,
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    readiness_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Verify local product-readiness")
    )

    assert readiness_item["coverage"] == "complete"
    assert readiness_item["blockers"] == ["workspace_blocker_count=1"]
    assert any("workspace/local/publish/agent blockers=1/0/1/0" in item for item in readiness_item["evidence"])


def test_readiness_local_workspace_blocker_remains_partial(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    readiness = _clean_readiness()
    assert isinstance(readiness["overall"], dict)
    readiness["overall"]["state"] = "blocked"
    readiness["overall"]["workspace_blocker_count"] = 1
    readiness["overall"]["local_blocker_count"] = 1

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=readiness,
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    readiness_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Verify local product-readiness")
    )

    assert readiness_item["coverage"] == "partial"
    assert readiness_item["blockers"] == ["local_blocker_count=1", "workspace_blocker_count=1"]
    assert any("workspace/local/publish/agent blockers=1/1/0/0" in item for item in readiness_item["evidence"])


def test_release_authorization_packet_publish_boundary_is_direct_audit_item(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        release_authorization_packet=_release_packet(),
    )
    result = completion_audit.audit_manifest(manifest)
    packet_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Generate a no-push release")
    )

    assert packet_item["coverage"] == "complete"
    assert packet_item["blockers"] == [
        "release authorization packet is ready, but explicit push authorization and current-head Actions are still required."
    ]
    assert any("status=ready_for_authorization" in evidence for evidence in packet_item["evidence"])
    assert "release_authorization_packet ahead_count=3, dirty_count=0." in packet_item["evidence"]
    assert any(
        "Post-push gates: root-quality-gate, active-project-matrix" in evidence for evidence in packet_item["evidence"]
    )
    assert any("allowed_without_explicit_user_authorization=False" in evidence for evidence in packet_item["evidence"])
    assert any("Packet blockers:" in evidence and "T-251" in evidence for evidence in packet_item["evidence"])
    assert result["status"] == "incomplete"
    assert not any(issue["code"] == "incomplete_coverage" for issue in result["issues"])


def test_release_authorization_packet_synced_state_does_not_block_manifest(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        release_authorization_packet=_release_packet(
            status="not_required",
            ahead_count=0,
            blockers=["external/user-owned blocker(s): T-251"],
        ),
    )
    result = completion_audit.audit_manifest(manifest)
    packet_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Generate a no-push release")
    )

    assert packet_item["coverage"] == "complete"
    assert packet_item["blockers"] == []
    assert "release_authorization_packet ahead_count=0, dirty_count=0." in packet_item["evidence"]
    assert result["status"] == "complete"


def test_release_authorization_packet_requires_explicit_user_authorization_guard(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        release_authorization_packet=_release_packet(
            status="already_verified",
            blockers=[],
            allowed_without_authorization=True,
        ),
    )
    result = completion_audit.audit_manifest(manifest)
    packet_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Generate a no-push release")
    )

    assert packet_item["coverage"] == "complete"
    assert packet_item["blockers"] == ["release authorization packet did not enforce explicit user authorization."]
    assert result["status"] == "incomplete"


def test_collect_current_inputs_uses_one_snapshot_for_selector(monkeypatch, tmp_path: Path) -> None:
    readiness = _clean_readiness(external_blockers=1)
    assert isinstance(readiness["overall"], dict)
    readiness["overall"]["workspace_blocker_count"] = 1
    readiness["overall"]["publish_blocker_count"] = 1
    assert isinstance(readiness["workspace_gates"], dict)
    readiness["workspace_gates"]["github_release"] = {
        "required_workflows": [
            {"name": "root-quality-gate", "status": "missing", "conclusion": None},
            {"name": "active-project-matrix", "status": "missing", "conclusion": None},
        ]
    }
    github_inventory = _github_inventory()
    assert isinstance(github_inventory["git"], dict)
    github_inventory["git"]["status"] = {"stdout": "## main...origin/main [ahead 9]"}

    calls: list[list[str]] = []

    def fake_run_json(_root: Path, command: list[str], _timeout: int) -> dict[str, object]:
        calls.append(command)
        command_text = " ".join(command)
        if "product_readiness_score.py" in command_text:
            data = readiness
        elif "github_project_inventory.py" in command_text:
            data = github_inventory
        elif "browser_qa_inventory.py" in command_text:
            data = _browser_inventory()
        elif "dependency_freshness_inventory.py" in command_text:
            data = _dependency_inventory()
        else:
            data = _selector_selection(status="candidate", kind="github_inventory_followup", blocked=False)
        return {"available": True, "returncode": 0, "stdout": json.dumps(data), "stderr": "", "data": data}

    monkeypatch.setattr(launch_objective_audit, "_run_json", fake_run_json)
    monkeypatch.setattr(
        launch_objective_audit,
        "_release_authorization_packet_from_inputs",
        lambda _root, packet_readiness: {
            "available": True,
            "returncode": 0,
            "stdout": json.dumps(_release_packet()),
            "stderr": "",
            "data": _release_packet(
                ahead_count=packet_readiness["workspace_gates"]["github_release"].get("ahead_count", 3)
            ),
        },
    )

    collected = launch_objective_audit.collect_current_inputs(tmp_path, timeout=1)

    assert all("next_experiment_selector.py" not in " ".join(command) for command in calls)
    assert "release_authorization_packet" in collected
    assert collected["github_inventory"]["data"] == github_inventory
    selection = collected["next_experiment_selection"]["data"]
    assert selection["status"] == "blocked_publish_only"
    assert selection["selected"]["kind"] == "current_head_release_checks_unproven"
    assert any("github dirty_count=0" in evidence for evidence in selection["selected"]["evidence"])


def test_selector_external_only_state_is_evidence_not_duplicate_blocker(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(external_blockers=1),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        next_experiment_selection=_selector_selection(),
    )
    result = completion_audit.audit_manifest(manifest)
    selector_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Run the deterministic next-experiment")
    )

    assert selector_item["coverage"] == "complete"
    assert selector_item["blockers"] == []
    assert any("status=blocked_external_only" in item for item in selector_item["evidence"])
    assert result["summary"]["issue_count"] == 2
    assert result["summary"]["blocked_count"] == 2
    assert {issue["requirement"] for issue in result["issues"] if issue["code"] == "blocked"} == {
        "Separate externally blocked live checks from local product-polish completion.",
        "Prove hanwoo-dashboard target product launch readiness with direct project evidence.",
    }
    assert not any(
        issue["requirement"].startswith("Run the deterministic next-experiment") for issue in result["issues"]
    )


def test_target_blind_to_x_item_includes_direct_release_evidence(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    target_item = next(item for item in manifest["items"] if item["requirement"].startswith("Prove blind-to-x"))

    assert target_item["coverage"] == "complete"
    assert target_item["blockers"] == []
    assert "projects/blind-to-x/README.md" in target_item["artifacts"]
    assert "blind-to-x readiness score=100, state=ready." in target_item["evidence"]
    assert any("blind-to-x QC status=PASS" in evidence for evidence in target_item["evidence"])
    assert any("blind-to-x env checks ok 2/2" in evidence for evidence in target_item["evidence"])


def test_target_blind_to_x_item_rejects_stale_or_failing_release_evidence(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(
            blind_score=92,
            blind_state="blocked",
            blind_qc_status="FAIL",
            blind_qc_failed=1,
            blind_qc_stale=True,
            blind_env_ok=False,
        ),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    target_item = next(item for item in manifest["items"] if item["requirement"].startswith("Prove blind-to-x"))

    assert result["status"] == "incomplete"
    assert target_item["coverage"] == "partial"
    assert "blind-to-x readiness is score=92, state=blocked; expected score>=100 and ready." in target_item["blockers"]
    assert "blind-to-x QC is status=FAIL, failed=1, stale=True." in target_item["blockers"]
    assert "blind-to-x env checks ok 0/2." in target_item["blockers"]


def test_target_shorts_maker_v2_item_includes_direct_release_evidence(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    target_item = next(item for item in manifest["items"] if item["requirement"].startswith("Prove shorts-maker-v2"))

    assert target_item["coverage"] == "complete"
    assert target_item["blockers"] == []
    assert "projects/shorts-maker-v2/README.md" in target_item["artifacts"]
    assert "shorts-maker-v2 readiness score=100, state=ready." in target_item["evidence"]
    assert any("shorts-maker-v2 QC status=PASS" in evidence for evidence in target_item["evidence"])
    assert any("shorts-maker-v2 env checks ok 1/1" in evidence for evidence in target_item["evidence"])
    assert "shorts-maker-v2 FEATURE checklist complete 2/2, open=0." in target_item["evidence"]


def test_target_shorts_maker_v2_item_rejects_stale_or_failing_release_evidence(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(
            shorts_score=92,
            shorts_state="blocked",
            shorts_qc_status="FAIL",
            shorts_qc_failed=1,
            shorts_qc_stale=True,
            shorts_env_ok=False,
        ),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    target_item = next(item for item in manifest["items"] if item["requirement"].startswith("Prove shorts-maker-v2"))

    assert result["status"] == "incomplete"
    assert target_item["coverage"] == "partial"
    assert (
        "shorts-maker-v2 readiness is score=92, state=blocked; expected score>=100 and ready."
        in target_item["blockers"]
    )
    assert "shorts-maker-v2 QC is status=FAIL, failed=1, stale=True." in target_item["blockers"]
    assert "shorts-maker-v2 env checks ok 0/1." in target_item["blockers"]


def test_target_shorts_maker_v2_item_rejects_open_feature_checklist(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    _write_shorts_feature_checklist(tmp_path, complete=False)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    target_item = next(item for item in manifest["items"] if item["requirement"].startswith("Prove shorts-maker-v2"))

    assert result["status"] == "incomplete"
    assert target_item["coverage"] == "partial"
    assert "shorts-maker-v2 FEATURE checklist complete 0/2, open=2." in target_item["evidence"]
    assert any(
        blocker.startswith("shorts-maker-v2 FEATURE.md has 2 open acceptance checklist item(s)")
        for blocker in target_item["blockers"]
    )


def test_target_hanwoo_dashboard_item_includes_direct_release_evidence(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    target_item = next(item for item in manifest["items"] if item["requirement"].startswith("Prove hanwoo-dashboard"))

    assert target_item["coverage"] == "complete"
    assert target_item["blockers"] == []
    assert "projects/hanwoo-dashboard/API_SPEC.md" in target_item["artifacts"]
    assert "hanwoo-dashboard readiness score=100, state=ready." in target_item["evidence"]
    assert any("hanwoo-dashboard QC status=PASS" in evidence for evidence in target_item["evidence"])
    assert any("hanwoo-dashboard env checks ok 1/1" in evidence for evidence in target_item["evidence"])
    assert "hanwoo-dashboard tasks=0 (none), dirty_paths=0." in target_item["evidence"]


def test_target_hanwoo_dashboard_item_keeps_t251_as_direct_blocker_not_coverage_gap(tmp_path: Path) -> None:
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
    target_item = next(item for item in manifest["items"] if item["requirement"].startswith("Prove hanwoo-dashboard"))

    assert result["status"] == "incomplete"
    assert target_item["coverage"] == "complete"
    assert "hanwoo-dashboard readiness score=86, state=blocked." in target_item["evidence"]
    assert "hanwoo-dashboard tasks=1 (T-251), dirty_paths=0." in target_item["evidence"]
    assert (
        "hanwoo-dashboard readiness is score=86, state=blocked; expected score>=100 and ready."
        in target_item["blockers"]
    )
    assert "hanwoo-dashboard has 1 unresolved readiness task(s): T-251." in target_item["blockers"]
    assert not any(issue["code"] == "incomplete_coverage" for issue in result["issues"])


def test_selector_local_candidate_prevents_complete_claim(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        next_experiment_selection=_selector_selection(
            status="candidate",
            kind="local_readiness_blocker",
            blocked=False,
            project="workspace",
        ),
    )
    result = completion_audit.audit_manifest(manifest)
    selector_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Run the deterministic next-experiment")
    )

    assert selector_item["coverage"] == "partial"
    assert selector_item["blockers"] == [
        "next_experiment_selector selected unresolved local work: "
        "status=candidate, kind=local_readiness_blocker, project=workspace"
    ]
    assert result["status"] == "incomplete"
    assert result["items"][5]["requirement"].startswith("Run the deterministic next-experiment")
    assert result["items"][5]["passed"] is False


def test_selector_current_head_publish_boundary_has_complete_coverage_with_blocker(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        next_experiment_selection=_selector_selection(
            status="blocked_publish_only",
            kind="current_head_release_checks_unproven",
            blocked=True,
            project="workspace",
            guardrails=["Do not push without explicit user authorization."],
            required_gates=["current-head root-quality-gate success"],
        ),
    )
    result = completion_audit.audit_manifest(manifest)
    selector_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Run the deterministic next-experiment")
    )

    assert selector_item["coverage"] == "complete"
    assert selector_item["blockers"] == [
        "next_experiment_selector selected unresolved publish boundary: "
        "status=blocked_publish_only, kind=current_head_release_checks_unproven, project=workspace"
    ]
    assert any("publish-boundary check" in evidence for evidence in selector_item["evidence"])
    assert result["status"] == "incomplete"
    assert result["items"][5]["issues"] == ["blocked"]


def test_selector_action_evidence_has_single_terminal_punctuation_guardrails_and_gates(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(external_blockers=1),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        next_experiment_selection=_selector_selection(
            guardrails=[
                "Do not retry T-251 until Supabase Dashboard credentials are reset.",
                "Keep local launch gates green",
            ]
        ),
    )
    selector_item = next(
        item for item in manifest["items"] if item["requirement"].startswith("Run the deterministic next-experiment")
    )

    assert "Selected action: Wait for user-owned external blocker(s): T-251." in selector_item["evidence"]
    assert not any("T-251.." in evidence for evidence in selector_item["evidence"])
    assert (
        "Selector guardrails: Do not retry T-251 until Supabase Dashboard credentials are reset. "
        "Keep local launch gates green."
    ) in selector_item["evidence"]
    assert (
        "Selector required gates: Supabase credential reset by user. Hanwoo live Prisma CRUD E2E after reset."
    ) in selector_item["evidence"]


def test_ab_item_includes_latest_local_manifest_artifact(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    manifest_path = _write_ab_manifest(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    ab_item = next(item for item in manifest["items"] if item["requirement"].startswith("Run bounded A/B"))

    assert result["status"] == "complete"
    assert manifest_path.relative_to(tmp_path).as_posix() in ab_item["artifacts"]
    assert any("Latest A/B manifest artifact: .tmp/ab-manifest-t-test.json" in item for item in ab_item["evidence"])
    assert any("required gates passed 2/2" in item for item in ab_item["evidence"])


def test_ab_item_prefers_highest_task_manifest_over_newer_file_mtime(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    selected = _write_ab_manifest(
        tmp_path,
        name="ab-manifest-t1300.json",
        experiment="T-1300 deterministic launch audit A/B manifest selection",
    )
    touched_older_task = _write_ab_manifest(
        tmp_path,
        name="ab-manifest-t1299.json",
        experiment="T-1299 touched after newer task",
    )
    os.utime(selected, (1_700_000_000, 1_700_000_000))
    os.utime(touched_older_task, (1_800_000_000, 1_800_000_000))

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    ab_item = next(item for item in manifest["items"] if item["requirement"].startswith("Run bounded A/B"))

    assert selected.relative_to(tmp_path).as_posix() in ab_item["artifacts"]
    assert touched_older_task.relative_to(tmp_path).as_posix() not in ab_item["artifacts"]
    assert any("Latest A/B manifest selection used task id T-1300" in item for item in ab_item["evidence"])


def test_ab_item_can_use_explicit_manifest_override(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    default_selected = _write_ab_manifest(
        tmp_path,
        name="ab-manifest-t1300.json",
        experiment="T-1300 default latest manifest",
    )
    requested = _write_ab_manifest(
        tmp_path,
        name="ab-manifest-t1299.json",
        experiment="T-1299 requested manifest",
    )

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        ab_manifest_path=Path(".tmp/ab-manifest-t1299.json"),
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    ab_item = next(item for item in manifest["items"] if item["requirement"].startswith("Run bounded A/B"))

    assert requested.relative_to(tmp_path).as_posix() in ab_item["artifacts"]
    assert default_selected.relative_to(tmp_path).as_posix() not in ab_item["artifacts"]
    assert any("Latest A/B manifest selection used task id T-1299" in item for item in ab_item["evidence"])


def test_ab_item_failed_manifest_gate_prevents_complete_claim(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    _write_ab_manifest(tmp_path, gate_passes=False)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    ab_item = next(item for item in manifest["items"] if item["requirement"].startswith("Run bounded A/B"))

    assert ab_item["coverage"] == "partial"
    assert ab_item["blockers"] == ["Latest A/B manifest failed required gate(s): focused_tests"]


def test_ab_item_accepts_utf8_bom_manifest(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    manifest_path = _write_ab_manifest(tmp_path, encoding="utf-8-sig")

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    ab_item = next(item for item in manifest["items"] if item["requirement"].startswith("Run bounded A/B"))

    assert result["status"] == "complete"
    assert manifest_path.relative_to(tmp_path).as_posix() in ab_item["artifacts"]
    assert any("required gates passed 2/2" in item for item in ab_item["evidence"])


def test_ab_manifest_stat_failure_is_ignored(tmp_path: Path, monkeypatch) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    broken_manifest = _write_ab_manifest(tmp_path, name="ab-manifest-broken.json")
    good_manifest = _write_ab_manifest(tmp_path, name="ab-manifest-good.json")
    original_sort_key = launch_objective_audit._ab_manifest_sort_key

    def fake_sort_key(path: Path) -> tuple[int, str] | None:
        if path == broken_manifest:
            return None
        return original_sort_key(path)

    monkeypatch.setattr(launch_objective_audit, "_ab_manifest_sort_key", fake_sort_key)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    ab_item = next(item for item in manifest["items"] if item["requirement"].startswith("Run bounded A/B"))

    assert result["status"] == "complete"
    assert good_manifest.relative_to(tmp_path).as_posix() in ab_item["artifacts"]
    assert broken_manifest.relative_to(tmp_path).as_posix() not in ab_item["artifacts"]
    assert any(
        "Ignored unreadable A/B manifest artifact: .tmp/ab-manifest-broken.json" in item for item in ab_item["evidence"]
    )


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
    external_item = next(item for item in manifest["items"] if item["requirement"].startswith("Separate"))

    assert result["status"] == "incomplete"
    assert result["summary"]["blocked_count"] == 2
    assert result["summary"]["issue_count"] == 2
    assert external_item["coverage"] == "complete"
    assert any("T-251" in blocker for item in manifest["items"] for blocker in item["blockers"])
    blocked_issue = next(
        issue
        for issue in result["issues"]
        if issue["code"] == "blocked" and issue["requirement"].startswith("Separate")
    )
    assert blocked_issue["blockers"] == ["1 external/user-owned blocker(s) remain: T-251"]
    assert "T-251" in blocked_issue["message"]


def test_external_blocker_without_task_id_is_not_claimed_fully_covered(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(external_blockers=1, include_user_task=False),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    external_item = next(item for item in manifest["items"] if item["requirement"].startswith("Separate"))

    assert result["status"] == "incomplete"
    assert result["summary"]["blocked_count"] == 2
    assert result["summary"]["issue_count"] == 3
    assert external_item["coverage"] == "partial"
    assert external_item["blockers"] == ["1 external/user-owned blocker(s) remain: unknown"]


def test_external_user_blocker_owner_matching_is_case_insensitive(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(external_blockers=1, user_task_owner="user"),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    external_item = next(item for item in manifest["items"] if item["requirement"].startswith("Separate"))

    assert result["status"] == "incomplete"
    assert result["summary"]["issue_count"] == 2
    assert external_item["coverage"] == "complete"
    assert external_item["blockers"] == ["1 external/user-owned blocker(s) remain: T-251"]


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


def test_stale_browser_screenshots_are_not_claimed_complete(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(fresh=3, stale=1),
        dependency_inventory=_dependency_inventory(),
    )
    browser_item = next(item for item in manifest["items"] if item["requirement"].startswith("Use Codex"))

    assert browser_item["coverage"] == "partial"
    assert "Only 3/4 browser project(s) have fresh retained screenshots." in browser_item["blockers"]
    assert "fresh screenshot coverage 3/4; stale=1." in browser_item["evidence"]


def test_blank_browser_screenshots_are_not_claimed_complete(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(fresh=4, fresh_usable=3, fresh_nonblank=2),
        dependency_inventory=_dependency_inventory(),
    )
    browser_item = next(item for item in manifest["items"] if item["requirement"].startswith("Use Codex"))

    assert browser_item["coverage"] == "partial"
    assert "fresh usable screenshot coverage 3/4; fresh nonblank=2/4." in browser_item["evidence"]
    assert "Only 3/4 browser project(s) have fresh usable screenshots." in browser_item["blockers"]
    assert "Only 2/4 browser project(s) have fresh nonblank screenshots." in browser_item["blockers"]


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


def test_peer_blocked_deferred_dependency_evidence_is_not_a_direct_candidate_blocker(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(peer_blocked=True),
    )
    dependency_item = next(item for item in manifest["items"] if item["requirement"].startswith("Research"))

    assert dependency_item["coverage"] == "complete"
    assert dependency_item["blockers"] == []
    assert any(
        "projects/hanwoo-dashboard/eslint peer_blocker_count=4" in evidence
        and "projects/knowledge-dashboard/eslint peer_blocker_count=3" in evidence
        and "latest_supported=1, latest_blocked=3, latest_unavailable=0" in evidence
        for evidence in dependency_item["evidence"]
    )


def test_current_prerelease_channel_dependency_evidence_explains_outdated_count(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(peer_blocked=True, prerelease_current=True),
    )
    dependency_item = next(item for item in manifest["items"] if item["requirement"].startswith("Research"))

    assert dependency_item["coverage"] == "complete"
    assert dependency_item["blockers"] == []
    assert "outdated_dependency_count=3." in dependency_item["evidence"]
    assert any(
        "projects/hanwoo-dashboard/next-auth beta=5.0.0-beta.31 current=5.0.0-beta.31 stable_latest=4.24.14" in evidence
        for evidence in dependency_item["evidence"]
    )


def test_current_code_triage_includes_graph_and_gate_evidence(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        session_orientation=_session_orientation(),
        code_review_gate=_code_review_gate(),
    )
    dependency_item = next(item for item in manifest["items"] if item["requirement"].startswith("Research"))

    assert dependency_item["coverage"] == "complete"
    assert dependency_item["blockers"] == []
    assert "execution/session_orient.py" in dependency_item["artifacts"]
    assert "execution/code_review_gate.py" in dependency_item["artifacts"]
    assert any("code_review_graph freshness=current" in evidence for evidence in dependency_item["evidence"])
    assert any("code_review_gate status=pass, risk_score=0.0" in evidence for evidence in dependency_item["evidence"])


def test_current_code_triage_allows_advisory_warn_gate(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        session_orientation=_session_orientation(),
        code_review_gate=_code_review_gate(status="warn", risk_score=0.4),
    )
    dependency_item = next(item for item in manifest["items"] if item["requirement"].startswith("Research"))

    assert dependency_item["coverage"] == "complete"
    assert dependency_item["blockers"] == []
    assert any("code_review_gate status=warn, risk_score=0.4" in evidence for evidence in dependency_item["evidence"])


def test_current_code_triage_allows_stale_graph_without_relevant_changes(tmp_path: Path, monkeypatch) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    monkeypatch.setattr(launch_objective_audit, "_graph_relevant_files_between", lambda root, base, head: [])

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        session_orientation=_session_orientation(freshness="stale"),
        code_review_gate=_code_review_gate(status="pass", risk_score=0.0),
    )
    dependency_item = next(item for item in manifest["items"] if item["requirement"].startswith("Research"))

    assert dependency_item["coverage"] == "complete"
    assert dependency_item["blockers"] == []
    assert "code_review_graph stale range has no graph-relevant file changes." in dependency_item["evidence"]


def test_current_code_triage_blocks_stale_graph_or_failing_gate(tmp_path: Path, monkeypatch) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(tmp_path)
    monkeypatch.setattr(
        launch_objective_audit,
        "_graph_relevant_files_between",
        lambda root, base, head: ["execution/product_readiness_score.py"],
    )

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
        session_orientation=_session_orientation(freshness="stale"),
        code_review_gate=_code_review_gate(status="fail", risk_score=0.8),
    )
    result = completion_audit.audit_manifest(manifest)
    dependency_item = next(item for item in manifest["items"] if item["requirement"].startswith("Research"))

    assert result["status"] == "incomplete"
    assert dependency_item["coverage"] == "partial"
    assert any(
        "graph-relevant changes remain: execution/product_readiness_score.py" in blocker
        for blocker in dependency_item["blockers"]
    )
    assert "code_review_gate status=fail; expected pass or warn." in dependency_item["blockers"]


def test_relay_item_rejects_stale_completed_goal(tmp_path: Path) -> None:
    _write_required_skill(tmp_path)
    _write_ai_relay(
        tmp_path,
        goal_status="completed",
        goal_text="hanwoo-dashboard quality uplift so other people would want to use it.",
    )

    manifest = launch_objective_audit.build_manifest(
        tmp_path,
        readiness=_clean_readiness(),
        github_inventory=_github_inventory(),
        browser_inventory=_browser_inventory(),
        dependency_inventory=_dependency_inventory(),
    )
    result = completion_audit.audit_manifest(manifest)
    relay_item = next(item for item in manifest["items"] if item["requirement"].startswith("Keep the self-improvement"))

    assert result["status"] == "incomplete"
    assert relay_item["coverage"] == "partial"
    assert "GOAL.md status is completed; expected an active launch-loop status." in relay_item["blockers"]
    assert "GOAL.md does not describe the current product launch/auto-research objective." in relay_item["blockers"]


def test_cli_output_file_is_ascii_safe_for_powershell_default_reads(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "박주호"
    root.mkdir()
    _write_required_skill(root)
    _write_ai_relay(root)

    monkeypatch.setattr(
        launch_objective_audit,
        "collect_current_inputs",
        lambda _root, _timeout: {
            "readiness": {"available": True, "returncode": 0, "stderr": "", "data": _clean_readiness()},
            "github_inventory": {"available": True, "returncode": 0, "stderr": "", "data": _github_inventory()},
            "browser_inventory": {"available": True, "returncode": 0, "stderr": "", "data": _browser_inventory()},
            "dependency_inventory": {
                "available": True,
                "returncode": 0,
                "stderr": "",
                "data": _dependency_inventory(),
            },
        },
    )

    output_path = tmp_path / "launch-objective-audit.json"

    assert launch_objective_audit.main(["--root", str(root), "--output", str(output_path)]) == 0

    raw = output_path.read_bytes()
    assert all(byte < 128 for byte in raw)
    assert "\\ubc15\\uc8fc\\ud638" in raw.decode("ascii")
