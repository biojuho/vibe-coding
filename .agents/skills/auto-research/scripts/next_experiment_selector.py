#!/usr/bin/env python3
"""Select the next bounded auto-research experiment from current evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(".agents") / "skills" / "auto-research" / "scripts"
INPUT_ERROR_KEY = "_input_error"
DEFAULT_LIVE_HELPER_TIMEOUT = 60
DEFAULT_DEPENDENCY_HELPER_TIMEOUT = 60
DEFAULT_CACHE_MAX_AGE_SECONDS = 6 * 60 * 60
PRODUCT_READINESS_GATE = "python execution/product_readiness_score.py --json"
GITHUB_INVENTORY_GATE = (
    "python .agents/skills/auto-research/scripts/github_project_inventory.py --root . --include-prs --json"
)
BROWSER_QA_INVENTORY_GATE = "python .agents/skills/auto-research/scripts/browser_qa_inventory.py --root . --json"
DEPENDENCY_INVENTORY_GATE = (
    "python .agents/skills/auto-research/scripts/dependency_freshness_inventory.py --root . --json"
)
DIRTY_HANDOFF_PLAN_GATE = (
    "python .agents/skills/auto-research/scripts/dirty_worktree_handoff_plan.py --root . "
    "--output-json .tmp/scoped-dirty-worktree-handoff-plan-current.json "
    "--output-md .tmp/scoped-dirty-worktree-handoff-plan-current.md --json"
)
DEBUG_INVENTORY_COMPLETION_BLOCKED_GATE = (
    "python .agents/skills/auto-research/scripts/debug_loop_inventory.py --root . "
    "--output-md .tmp/debug-loop-known-bugs-current.md "
    "--output-json .tmp/debug-loop-known-bugs-current.json --json --fail-on-completion-blocked"
)
GITHUB_INVENTORY_CACHE = Path(".tmp") / "github-project-inventory.json"
BROWSER_INVENTORY_CACHE = Path(".tmp") / "browser-qa-inventory.json"
DEPENDENCY_INVENTORY_CACHE = Path(".tmp") / "dependency-freshness-inventory.json"
DIRTY_HANDOFF_PLAN_CACHE = Path(".tmp") / "scoped-dirty-worktree-handoff-plan-current.json"


def _input_error(label: str, reason: str, **extra: Any) -> dict[str, Any]:
    payload = {"label": label, "reason": reason}
    payload.update({key: value for key, value in extra.items() if value not in (None, "")})
    return {INPUT_ERROR_KEY: payload}


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        try:
            raw = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            raw = path.read_text(encoding="utf-16")
        parsed = json.loads(raw)
    except FileNotFoundError:
        return _input_error(label, "missing artifact", path=str(path))
    except OSError as exc:
        return _input_error(label, "unreadable artifact", path=str(path), detail=str(exc))
    except UnicodeError as exc:
        return _input_error(label, "unsupported artifact encoding", path=str(path), detail=str(exc))
    except json.JSONDecodeError as exc:
        return _input_error(label, "invalid JSON artifact", path=str(path), detail=str(exc))
    if not isinstance(parsed, dict):
        return _input_error(label, "JSON root was not an object", path=str(path))
    return parsed


def _run_json(root: Path, args: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(root),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "returncode": None,
            "stderr": str(exc),
            "data": {},
        }
    stdout = completed.stdout.strip()
    data: dict[str, Any] = {}
    available = completed.returncode == 0
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            available = False
            data = {"parse_error": str(exc)}
        else:
            data = parsed if isinstance(parsed, dict) else {"parse_error": "JSON root was not an object"}
            available = available and isinstance(parsed, dict)
    return {
        "available": available,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
        "data": data,
    }


def _run_data(result: dict[str, Any], *, label: str) -> dict[str, Any]:
    data = _as_dict(result.get("data"))
    if result.get("available") is True and data:
        return data
    return _input_error(
        label,
        "helper command unavailable",
        returncode=result.get("returncode"),
        detail=result.get("stderr"),
    )


def _load_recent_json(path: Path, *, label: str, max_age_seconds: int) -> dict[str, Any] | None:
    try:
        age_seconds = time.time() - path.stat().st_mtime
    except FileNotFoundError:
        return None
    except OSError as exc:
        return _input_error(label, "unreadable cached artifact", path=str(path), detail=str(exc))
    if age_seconds < 0:
        age_seconds = 0
    if age_seconds > max_age_seconds:
        return None
    return _load_json(path, label=label)


def _run_data_with_recent_fallback(
    result: dict[str, Any],
    *,
    label: str,
    fallback_path: Path,
    max_age_seconds: int,
) -> dict[str, Any]:
    data = _run_data(result, label=label)
    if INPUT_ERROR_KEY not in data:
        return data
    fallback = _load_recent_json(fallback_path, label=label, max_age_seconds=max_age_seconds)
    if fallback is None:
        return data
    return fallback


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _count(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _github_recommendations(github_inventory: dict[str, Any]) -> list[str]:
    return [str(item) for item in _as_list(github_inventory.get("recommendations"))]


def _actionable_github_recommendations(github_inventory: dict[str, Any]) -> list[str]:
    recommendations = _github_recommendations(github_inventory)
    return [item for item in recommendations if not item.lower().startswith("worktree is dirty")]


def _project_action(readiness: dict[str, Any], fallback: str) -> tuple[str, str]:
    for action in _as_list(readiness.get("next_actions")):
        if not isinstance(action, dict):
            continue
        text = str(action.get("action") or "")
        if text and fallback in text:
            return str(action.get("project") or "workspace"), text
    return "workspace", fallback


def _external_task_ids(readiness: dict[str, Any]) -> list[str]:
    task_ids: list[str] = []
    for project in _as_list(readiness.get("projects")):
        if not isinstance(project, dict):
            continue
        for task in _as_list(project.get("tasks")):
            if not isinstance(task, dict):
                continue
            owner = str(task.get("owner") or "").strip().lower()
            task_id = str(task.get("id") or "").strip()
            if owner == "user" and task_id:
                task_ids.append(task_id)
    return sorted(set(task_ids))


def _gate_expectation(*, gate: str, expected_exit_codes: list[int], meaning: str) -> dict[str, Any]:
    return {
        "gate": gate,
        "expected_exit_codes": expected_exit_codes,
        "meaning": meaning,
    }


def _candidate(
    *,
    kind: str,
    priority: int,
    project: str,
    action: str,
    reason: str,
    evidence: list[str],
    required_gates: list[str],
    blocked: bool = False,
    blockers: list[str] | None = None,
    guardrails: list[str] | None = None,
    gate_expectations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "priority": priority,
        "project": project,
        "action": action,
        "reason": reason,
        "evidence": evidence,
        "required_gates": required_gates,
        "blocked": blocked,
        "blockers": blockers or [],
        "guardrails": guardrails or [],
        "gate_expectations": gate_expectations or [],
    }


def _input_evidence_candidate(
    readiness: dict[str, Any],
    github_inventory: dict[str, Any],
    browser_inventory: dict[str, Any],
    dependency_inventory: dict[str, Any],
) -> dict[str, Any] | None:
    inputs = {
        "readiness": (readiness, "overall"),
        "github": (github_inventory, "git"),
        "browser": (browser_inventory, "summary"),
        "dependency": (dependency_inventory, "summary"),
    }
    evidence: list[str] = []
    for label, (payload, required_key) in inputs.items():
        error = _as_dict(payload.get(INPUT_ERROR_KEY))
        if error:
            evidence.append(
                f"{label}: {error.get('reason')} ({error.get('path') or error.get('detail') or 'no detail'})"
            )
            continue
        if required_key not in payload:
            evidence.append(f"{label}: missing required key `{required_key}`")
    if not evidence:
        return None
    return _candidate(
        kind="input_evidence_unavailable",
        priority=5,
        project="workspace",
        action="Regenerate missing or invalid auto-research input artifact(s) before selecting the next experiment.",
        reason="The selector must not route to completion audit when required inventory evidence is missing or unreadable.",
        evidence=evidence,
        required_gates=[
            PRODUCT_READINESS_GATE,
            GITHUB_INVENTORY_GATE,
            BROWSER_QA_INVENTORY_GATE,
            DEPENDENCY_INVENTORY_GATE,
        ],
        guardrails=[
            "Run artifact-producing helpers before selector evaluation.",
            "Do not retry external T-251 unless credentials were reset.",
        ],
    )


def _github_status_text(github_inventory: dict[str, Any]) -> str:
    git = _as_dict(github_inventory.get("git"))
    status = _as_dict(git.get("status"))
    return str(status.get("stdout") or "")


def _branch_is_ahead(github_inventory: dict[str, Any]) -> bool:
    status_text = _github_status_text(github_inventory)
    return "[ahead " in status_text or "ahead " in status_text


def _unproven_required_workflows(readiness: dict[str, Any]) -> list[str]:
    gates = _as_dict(readiness.get("workspace_gates"))
    github_release = _as_dict(gates.get("github_release"))
    workflows = _as_list(github_release.get("required_workflows"))
    missing: list[str] = []
    for workflow in workflows:
        if not isinstance(workflow, dict):
            continue
        status = str(workflow.get("status") or "")
        conclusion = str(workflow.get("conclusion") or "")
        if status != "completed" or conclusion != "success":
            missing.append(str(workflow.get("name") or "unknown"))
    return missing


def _current_head_release_candidate(
    readiness: dict[str, Any], github_inventory: dict[str, Any]
) -> dict[str, Any] | None:
    missing_workflows = _unproven_required_workflows(readiness)
    git = _as_dict(github_inventory.get("git"))
    if _count(git.get("dirty_count")):
        return None
    if not missing_workflows or not _branch_is_ahead(github_inventory):
        return None

    return _candidate(
        kind="current_head_release_checks_unproven",
        priority=10,
        project="workspace",
        action="Publish the scoped current HEAD or get explicit push authorization, then wait for required Actions.",
        reason=(
            "The worktree is clean but the current local HEAD is ahead of origin, so GitHub Actions cannot prove "
            "the exact launch evidence commit yet."
        ),
        evidence=[
            f"git status: {_github_status_text(github_inventory).strip() or 'unknown'}",
            "unproven required workflows: " + ", ".join(missing_workflows),
            f"github dirty_count={_count(git.get('dirty_count'))}",
            "release authorization packet required before push authorization.",
        ],
        required_gates=[
            "release_authorization_packet.py --json",
            "explicit push authorization or user push",
            "current-head root-quality-gate success",
            "current-head active-project-matrix success",
            "product_readiness_score.py --json",
        ],
        blocked=True,
        blockers=[
            "Current HEAD GitHub Actions are unproven because the local branch is ahead of origin.",
        ],
        guardrails=[
            "Do not push without explicit user authorization.",
            "Preserve unrelated dirty-tree work.",
            "Do not retry external T-251 unless credentials were reset.",
        ],
    )


def _local_readiness_candidate(readiness: dict[str, Any], github_inventory: dict[str, Any]) -> dict[str, Any] | None:
    overall = _as_dict(readiness.get("overall"))
    blocker_counts = {
        "workspace": _count(overall.get("workspace_blocker_count")),
        "local": _count(overall.get("local_blocker_count")),
        "agent": _count(overall.get("agent_task_count")),
        "environment": _count(overall.get("environment_blocker_count")),
    }
    total = sum(blocker_counts.values())
    if total == 0:
        return None
    git = _as_dict(github_inventory.get("git"))
    if _count(git.get("dirty_count")):
        return None
    release_candidate = _current_head_release_candidate(readiness, github_inventory)
    if release_candidate is not None:
        return release_candidate
    project, action = _project_action(readiness, "Resolve local launch blocker")
    return _candidate(
        kind="local_readiness_blocker",
        priority=10,
        project=project,
        action=action,
        reason="Local, workspace, agent, or environment readiness blockers must be cleared before launch claims.",
        evidence=[
            "readiness local blocker counts: " + ", ".join(f"{name}={count}" for name, count in blocker_counts.items())
        ],
        required_gates=["focused blocker regression", "product_readiness_score.py --json"],
        guardrails=[
            "Preserve unrelated dirty-tree work.",
            "Do not retry external T-251 unless credentials were reset.",
        ],
    )


def _normalized_path_list(value: Any) -> list[str]:
    return sorted({str(path).replace("\\", "/").strip() for path in _as_list(value) if str(path).strip()})


def _dirty_inventory_paths(github_inventory: dict[str, Any]) -> list[str]:
    git = _as_dict(github_inventory.get("git"))
    paths = _normalized_path_list(git.get("dirty_paths"))
    if paths:
        return paths
    sampled: list[str] = []
    for group in _as_list(git.get("dirty_path_groups")):
        sampled.extend(_normalized_path_list(_as_dict(group).get("paths")))
    return sorted(set(sampled))


def _dirty_handoff_plan_matches_inventory(
    dirty_handoff_plan: dict[str, Any],
    github_inventory: dict[str, Any],
) -> tuple[bool, list[str]]:
    if not dirty_handoff_plan:
        return False, []
    freshness = _as_dict(dirty_handoff_plan.get("freshness"))
    previous_freshness = _as_dict(dirty_handoff_plan.get("previous_plan_freshness"))
    signature = _as_dict(dirty_handoff_plan.get("dirty_signature"))
    signature_input = _as_dict(signature.get("input"))
    git = _as_dict(github_inventory.get("git"))
    evidence = [f"handoff plan status={dirty_handoff_plan.get('status')}"]
    if signature.get("value"):
        evidence.append(f"handoff plan signature={signature.get('value')}")
    if dirty_handoff_plan.get("status") != "handoff_required":
        evidence.append(f"handoff plan freshness={freshness.get('status')}")
        return False, evidence
    if _count(signature_input.get("dirty_count")) != _count(git.get("dirty_count")):
        evidence.append(f"handoff plan freshness={freshness.get('status')}")
        evidence.append(
            "handoff plan dirty_count mismatch: "
            f"plan={_count(signature_input.get('dirty_count'))}, inventory={_count(git.get('dirty_count'))}"
        )
        return False, evidence
    plan_paths = _normalized_path_list(signature_input.get("dirty_paths"))
    inventory_paths = _dirty_inventory_paths(github_inventory)
    if not plan_paths or not inventory_paths:
        evidence.append(f"handoff plan freshness={freshness.get('status')}")
        evidence.append("handoff plan dirty_paths unavailable")
        return False, evidence
    if plan_paths != inventory_paths:
        evidence.append(f"handoff plan freshness={freshness.get('status')}")
        evidence.append("handoff plan dirty_paths mismatch")
        return False, evidence
    freshness_status = str(freshness.get("status") or "unknown")
    evidence.append(
        "handoff plan freshness=current"
        if freshness_status == "current"
        else f"handoff plan freshness=current_by_signature (recorded={freshness_status})"
    )
    if previous_freshness:
        evidence.append(f"previous handoff plan freshness={previous_freshness.get('status')}")
    evidence.append("handoff plan signature matches current dirty inventory")
    group_order = [
        str(_as_dict(group).get("key"))
        for group in _as_list(dirty_handoff_plan.get("group_order"))
        if _as_dict(group).get("key")
    ]
    if group_order:
        evidence.append("handoff plan groups: " + ", ".join(group_order[:8]))
    return True, evidence


def _dirty_worktree_candidate(
    github_inventory: dict[str, Any],
    dirty_handoff_plan: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    git = _as_dict(github_inventory.get("git"))
    open_prs = _as_dict(github_inventory.get("open_prs"))
    dirty_count = _count(git.get("dirty_count"))
    open_pr_count = _count(open_prs.get("count"))
    recommendations = _actionable_github_recommendations(github_inventory)
    if dirty_count == 0 or open_pr_count or recommendations:
        return None

    dirty_groups = _as_list(git.get("dirty_path_groups"))
    evidence = [
        f"github dirty_count={dirty_count}",
        f"open_prs.available={open_prs.get('available') is True}, open_prs.count={open_pr_count}",
    ]
    if dirty_groups:
        group_summary = ", ".join(
            f"{_as_dict(group).get('key')}={_count(_as_dict(group).get('path_count'))}" for group in dirty_groups[:5]
        )
        evidence.append(f"dirty groups: {group_summary}")

    plan_matches, plan_evidence = _dirty_handoff_plan_matches_inventory(dirty_handoff_plan or {}, github_inventory)
    if plan_matches:
        return _candidate(
            kind="dirty_worktree_handoff_current",
            priority=15,
            project="workspace",
            action="Wait for explicit scoped staging/commit authorization or keep the current dirty handoff plan.",
            reason=(
                "A machine-readable dirty handoff plan already matches the current dirty inventory, so the selector "
                "should stop treating handoff generation as an adoptable experiment."
            ),
            evidence=[*evidence, *plan_evidence],
            required_gates=[
                DIRTY_HANDOFF_PLAN_GATE,
                GITHUB_INVENTORY_GATE,
                "python execution/session_orient.py --json",
                PRODUCT_READINESS_GATE,
                DEBUG_INVENTORY_COMPLETION_BLOCKED_GATE,
            ],
            blocked=True,
            blockers=[
                "Current dirty handoff plan matches the current dirty inventory; "
                "explicit scoped staging/commit authorization is required before product changes."
            ],
            guardrails=[
                "Do not stage, commit, push, or revert without explicit user authorization.",
                "Do not start unrelated product changes while the dirty handoff boundary remains current.",
                "Do not retry T-251 until Supabase credentials are reset.",
                "Treat the debug inventory fail gate exit code 1 as expected proof that completion is still blocked.",
            ],
            gate_expectations=[
                _gate_expectation(
                    gate=DEBUG_INVENTORY_COMPLETION_BLOCKED_GATE,
                    expected_exit_codes=[1],
                    meaning=(
                        "Completion is still blocked by dirty handoff or external boundaries; this is proof, "
                        "not a source failure."
                    ),
                )
            ],
        )

    return _candidate(
        kind="dirty_worktree_handoff",
        priority=15,
        project="workspace",
        action="Commit or hand off scoped worktree changes before selecting product changes.",
        reason=(
            "The GitHub inventory has no open PRs or actionable GitHub recommendations, so dirty worktree state "
            "should be handled as a local handoff boundary instead of reselecting the inventory loop."
        ),
        evidence=evidence,
        required_gates=[
            GITHUB_INVENTORY_GATE,
            DIRTY_HANDOFF_PLAN_GATE,
            "python execution/session_orient.py --json",
            PRODUCT_READINESS_GATE,
        ],
        guardrails=[
            "Commit only scoped work or record a handoff for unrelated dirty paths.",
            "Do not stage unrelated dirty work.",
            "Do not push without explicit user authorization.",
        ],
    )


def _github_candidate(github_inventory: dict[str, Any]) -> dict[str, Any] | None:
    open_prs = _as_dict(github_inventory.get("open_prs"))
    recommendations = _actionable_github_recommendations(github_inventory)
    open_pr_count = _count(open_prs.get("count"))
    if open_pr_count == 0 and not recommendations:
        return None
    evidence = [
        f"open_prs.available={open_prs.get('available') is True}, open_prs.count={open_pr_count}",
    ]
    evidence.extend(recommendations[:3])
    return _candidate(
        kind="github_inventory_followup",
        priority=20,
        project="workspace",
        action="Resolve GitHub inventory follow-up before selecting product changes.",
        reason="Dirty work, open PRs, or inventory recommendations can invalidate A/B comparisons.",
        evidence=evidence,
        required_gates=[GITHUB_INVENTORY_GATE, "python execution/session_orient.py --json"],
        guardrails=["Commit only scoped work.", "Do not merge or close unrelated PRs."],
    )


def _browser_candidate(browser_inventory: dict[str, Any]) -> dict[str, Any] | None:
    summary = _as_dict(browser_inventory.get("summary"))
    recommendations = [str(item) for item in _as_list(browser_inventory.get("recommendations"))]
    browser_count = _count(summary.get("browser_project_count"))
    missing = _count(summary.get("missing_count"))
    fresh = _count(summary.get("fresh_screenshot_project_count"))
    usable = _count(summary.get("fresh_usable_screenshot_project_count"))
    nonblank = _count(summary.get("fresh_nonblank_screenshot_project_count"))
    if (
        browser_count
        and missing == 0
        and fresh >= browser_count
        and usable >= browser_count
        and nonblank >= browser_count
    ):
        return None
    evidence = [
        f"browser coverage missing={missing}/{browser_count}",
        f"fresh screenshots={fresh}/{browser_count}",
        f"fresh usable={usable}/{browser_count}",
        f"fresh nonblank={nonblank}/{browser_count}",
    ]
    evidence.extend(recommendations[:3])
    return _candidate(
        kind="browser_qa_refresh",
        priority=30,
        project="browser apps",
        action="Run direct browser-click QA and refresh retained screenshot evidence.",
        reason="Browser launch evidence is missing, stale, invalid, or blank.",
        evidence=evidence,
        required_gates=[BROWSER_QA_INVENTORY_GATE, "direct app-click QA", "console/network inspection"],
        guardrails=["Start local dev servers only as needed.", "Capture screenshots for visual regressions."],
    )


def _dependency_candidate(dependency_inventory: dict[str, Any]) -> dict[str, Any] | None:
    summary = _as_dict(dependency_inventory.get("summary"))
    candidate_count = _count(summary.get("candidate_dependency_count"))
    if candidate_count == 0:
        return None
    projects: list[str] = []
    for project in _as_list(dependency_inventory.get("projects")):
        if isinstance(project, dict) and _count(project.get("candidate_count")):
            projects.append(str(project.get("path") or "unknown"))
    target = projects[0] if projects else "workspace"
    return _candidate(
        kind="dependency_candidate",
        priority=40,
        project=target,
        action=f"Evaluate {candidate_count} direct dependency candidate(s) with official release evidence.",
        reason="Patch/minor dependency candidates can improve launch freshness without forcing major migrations.",
        evidence=[
            f"candidate_dependency_count={candidate_count}",
            f"candidate_project_count={summary.get('candidate_project_count')}",
        ],
        required_gates=[
            DEPENDENCY_INVENTORY_GATE,
            "official release notes or npm metadata",
            "focused tests",
            "lint/build",
            "A/B decision",
        ],
        guardrails=["Do not force peer-blocked major migrations.", "Keep package and lockfile changes scoped."],
    )


def _project_qc_candidate(readiness: dict[str, Any]) -> dict[str, Any] | None:
    for project in _as_list(readiness.get("projects")):
        if not isinstance(project, dict):
            continue
        recommendations = [str(item) for item in _as_list(project.get("recommendations"))]
        refresh = [item for item in recommendations if item.startswith("Refresh project QC")]
        if not refresh:
            continue
        return _candidate(
            kind="project_qc_refresh",
            priority=50,
            project=str(project.get("path") or project.get("name") or "workspace"),
            action=refresh[0],
            reason="Stale or missing QC evidence weakens launch readiness even when the code is otherwise ready.",
            evidence=refresh,
            required_gates=["python execution/project_qc_runner.py --json", PRODUCT_READINESS_GATE],
            guardrails=["Use repo-local basetemp on Windows for focused pytest runs."],
        )
    return None


def _external_candidate(readiness: dict[str, Any]) -> dict[str, Any] | None:
    overall = _as_dict(readiness.get("overall"))
    external_count = _count(overall.get("external_blocker_count"))
    if external_count == 0:
        return None
    task_ids = _external_task_ids(readiness)
    blocker_label = ", ".join(task_ids) if task_ids else "unknown external/user-owned blocker"
    return _candidate(
        kind="external_user_blocker",
        priority=90,
        project="projects/hanwoo-dashboard" if "T-251" in task_ids else "workspace",
        action=f"Wait for user-owned external blocker(s): {blocker_label}.",
        reason="All local launch gates can be green while live external credentials remain outside agent control.",
        evidence=[
            f"external_blocker_count={external_count}",
            f"user_owned_task_ids={blocker_label}",
        ],
        required_gates=["Supabase credential reset by user", "Hanwoo live Prisma CRUD E2E after reset"],
        blocked=True,
        blockers=[f"{external_count} external/user-owned blocker(s): {blocker_label}"],
        guardrails=["Do not retry T-251 until Supabase Dashboard credentials are reset."],
    )


def _ready_candidate(readiness: dict[str, Any]) -> dict[str, Any]:
    overall = _as_dict(readiness.get("overall"))
    return _candidate(
        kind="completion_audit",
        priority=100,
        project="workspace",
        action="Run launch objective audit and completion audit before marking the goal complete.",
        reason="No immediate local, GitHub, browser, dependency, or external blocker was detected.",
        evidence=[
            f"readiness score={overall.get('score')}",
            f"readiness state={overall.get('state')}",
        ],
        required_gates=["launch_objective_audit.py --json", "completion_audit.py --json"],
    )


def select_next_experiment(
    *,
    readiness: dict[str, Any],
    github_inventory: dict[str, Any],
    browser_inventory: dict[str, Any],
    dependency_inventory: dict[str, Any],
    dirty_handoff_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = [
        _input_evidence_candidate(readiness, github_inventory, browser_inventory, dependency_inventory),
        _local_readiness_candidate(readiness, github_inventory),
        _dirty_worktree_candidate(github_inventory, dirty_handoff_plan),
        _github_candidate(github_inventory),
        _browser_candidate(browser_inventory),
        _dependency_candidate(dependency_inventory),
        _project_qc_candidate(readiness),
        _external_candidate(readiness),
    ]
    ranked = sorted((candidate for candidate in candidates if candidate), key=lambda item: item["priority"])
    adoptable = [candidate for candidate in ranked if not candidate["blocked"]]
    if adoptable:
        selected = adoptable[0]
        status = "candidate"
    elif ranked:
        selected = ranked[0]
        if selected["kind"] == "external_user_blocker":
            status = "blocked_external_only"
        elif selected["kind"] == "current_head_release_checks_unproven":
            status = "blocked_publish_only"
        else:
            status = "blocked"
    else:
        selected = _ready_candidate(readiness)
        ranked = [selected]
        status = "ready_for_completion_audit"
    return {
        "status": status,
        "selected": selected,
        "ranked_candidates": ranked,
        "summary": {
            "adoptable_candidate_count": len(adoptable),
            "blocked_candidate_count": sum(1 for candidate in ranked if candidate["blocked"]),
            "selected_kind": selected["kind"],
        },
    }


def _collect_inputs(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    root = args.root.resolve()
    dependency_timeout = max(1, min(args.timeout, DEFAULT_DEPENDENCY_HELPER_TIMEOUT))
    if args.readiness:
        readiness = _load_json(args.readiness, label="readiness")
    else:
        readiness = _run_data(
            _run_json(root, [sys.executable, "execution/product_readiness_score.py", "--json"], args.timeout),
            label="readiness",
        )
    if args.github:
        github_inventory = _load_json(args.github, label="github")
    else:
        github_inventory = _run_data_with_recent_fallback(
            _run_json(
                root,
                [
                    sys.executable,
                    str(SCRIPT_ROOT / "github_project_inventory.py"),
                    "--root",
                    str(root),
                    "--include-prs",
                    "--output",
                    str(root / GITHUB_INVENTORY_CACHE),
                    "--json",
                ],
                args.timeout,
            ),
            label="github",
            fallback_path=root / GITHUB_INVENTORY_CACHE,
            max_age_seconds=args.cache_max_age_seconds,
        )
    if args.browser:
        browser_inventory = _load_json(args.browser, label="browser")
    else:
        browser_inventory = _run_data_with_recent_fallback(
            _run_json(
                root,
                [
                    sys.executable,
                    str(SCRIPT_ROOT / "browser_qa_inventory.py"),
                    "--root",
                    str(root),
                    "--output",
                    str(root / BROWSER_INVENTORY_CACHE),
                    "--json",
                ],
                args.timeout,
            ),
            label="browser",
            fallback_path=root / BROWSER_INVENTORY_CACHE,
            max_age_seconds=args.cache_max_age_seconds,
        )
    if args.dependency:
        dependency_inventory = _load_json(args.dependency, label="dependency")
    else:
        dependency_inventory = _run_data_with_recent_fallback(
            _run_json(
                root,
                [
                    sys.executable,
                    str(SCRIPT_ROOT / "dependency_freshness_inventory.py"),
                    "--root",
                    str(root),
                    "--timeout",
                    str(dependency_timeout),
                    "--output",
                    str(root / DEPENDENCY_INVENTORY_CACHE),
                    "--json",
                ],
                args.timeout,
            ),
            label="dependency",
            fallback_path=root / DEPENDENCY_INVENTORY_CACHE,
            max_age_seconds=args.cache_max_age_seconds,
        )
    if args.dirty_handoff_plan:
        dirty_handoff_plan = _load_json(args.dirty_handoff_plan, label="dirty_handoff_plan")
    else:
        dirty_handoff_plan = (
            _load_recent_json(
                root / DIRTY_HANDOFF_PLAN_CACHE,
                label="dirty_handoff_plan",
                max_age_seconds=args.cache_max_age_seconds,
            )
            or {}
        )
    return {
        "readiness": readiness,
        "github_inventory": github_inventory,
        "browser_inventory": browser_inventory,
        "dependency_inventory": dependency_inventory,
        "dirty_handoff_plan": dirty_handoff_plan,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _print_text(selection: dict[str, Any]) -> None:
    selected = selection["selected"]
    print(f"next experiment status: {selection['status']}")
    print(f"selected: {selected['kind']} ({selected['project']})")
    print(f"action: {selected['action']}")
    for blocker in selected["blockers"]:
        print(f"blocker: {blocker}")
    for gate in selected["required_gates"]:
        print(f"gate: {gate}")
    for expectation in selected["gate_expectations"]:
        expectation_dict = _as_dict(expectation)
        gate = str(expectation_dict.get("gate") or "unknown")
        codes = ", ".join(str(code) for code in _as_list(expectation_dict.get("expected_exit_codes")))
        meaning = str(expectation_dict.get("meaning") or "").strip()
        suffix = f" meaning={meaning}" if meaning else ""
        print(f"gate_expectation: {gate} expected_exit_codes={codes or 'unknown'}{suffix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--readiness", type=Path, help="Existing product_readiness_score JSON artifact")
    parser.add_argument("--github", type=Path, help="Existing github_project_inventory JSON artifact")
    parser.add_argument("--browser", type=Path, help="Existing browser_qa_inventory JSON artifact")
    parser.add_argument("--dependency", type=Path, help="Existing dependency_freshness_inventory JSON artifact")
    parser.add_argument("--dirty-handoff-plan", type=Path, help="Existing dirty handoff plan JSON artifact")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_LIVE_HELPER_TIMEOUT,
        help="Timeout for each live helper command",
    )
    parser.add_argument(
        "--cache-max-age-seconds",
        type=int,
        default=DEFAULT_CACHE_MAX_AGE_SECONDS,
        help="Maximum age for fallback .tmp inventory artifacts when a live helper times out",
    )
    parser.add_argument("--output", type=Path, help="Optional path to write the selection JSON")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    inputs = _collect_inputs(args)
    selection = select_next_experiment(**inputs)
    if args.output:
        _write_json(args.output, selection)
    if args.json:
        json.dump(selection, sys.stdout, ensure_ascii=True, indent=2)
        print()
    else:
        _print_text(selection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
