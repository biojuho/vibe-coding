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
) -> dict[str, object]:
    task = {
        "id": "T-251",
        "owner": user_task_owner,
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
                "tasks": [task] if external_blockers and include_user_task else [],
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
    assert result["summary"]["issue_count"] == 1
    assert result["issues"] == [
        {
            "index": 7,
            "code": "blocked",
            "message": "Requirement has unresolved blocker(s): 1 external/user-owned blocker(s) remain: T-251",
            "requirement": "Separate externally blocked live checks from local product-polish completion.",
            "blockers": ["1 external/user-owned blocker(s) remain: T-251"],
        }
    ]


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
    assert result["summary"]["blocked_count"] == 1
    assert result["summary"]["issue_count"] == 1
    assert external_item["coverage"] == "complete"
    assert any("T-251" in blocker for item in manifest["items"] for blocker in item["blockers"])
    blocked_issue = next(issue for issue in result["issues"] if issue["code"] == "blocked")
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
    assert result["summary"]["blocked_count"] == 1
    assert result["summary"]["issue_count"] == 2
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
    assert result["summary"]["issue_count"] == 1
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
