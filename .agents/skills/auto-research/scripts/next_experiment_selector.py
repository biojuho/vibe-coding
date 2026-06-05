#!/usr/bin/env python3
"""Select the next bounded auto-research experiment from current evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(".agents") / "skills" / "auto-research" / "scripts"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


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


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _count(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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
    }


def _local_readiness_candidate(readiness: dict[str, Any]) -> dict[str, Any] | None:
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


def _github_candidate(github_inventory: dict[str, Any]) -> dict[str, Any] | None:
    git = _as_dict(github_inventory.get("git"))
    open_prs = _as_dict(github_inventory.get("open_prs"))
    recommendations = [str(item) for item in _as_list(github_inventory.get("recommendations"))]
    dirty_count = _count(git.get("dirty_count"))
    open_pr_count = _count(open_prs.get("count"))
    if dirty_count == 0 and open_pr_count == 0 and not recommendations:
        return None
    evidence = [
        f"github dirty_count={dirty_count}",
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
        required_gates=["github_project_inventory.py --include-prs --json", "session_orient.py --json"],
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
        required_gates=["browser_qa_inventory.py --json", "direct app-click QA", "console/network inspection"],
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
        required_gates=["official release notes or npm metadata", "focused tests", "lint/build", "A/B decision"],
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
            required_gates=["execution/project_qc_runner.py --json", "product_readiness_score.py --json"],
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
) -> dict[str, Any]:
    candidates = [
        _local_readiness_candidate(readiness),
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
        status = "blocked_external_only" if selected["kind"] == "external_user_blocker" else "blocked"
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
    if args.readiness:
        readiness = _load_json(args.readiness)
    else:
        readiness = _run_json(root, [sys.executable, "execution/product_readiness_score.py", "--json"], args.timeout)[
            "data"
        ]
    if args.github:
        github_inventory = _load_json(args.github)
    else:
        github_inventory = _run_json(
            root,
            [
                sys.executable,
                str(SCRIPT_ROOT / "github_project_inventory.py"),
                "--root",
                str(root),
                "--include-prs",
                "--json",
            ],
            args.timeout,
        )["data"]
    if args.browser:
        browser_inventory = _load_json(args.browser)
    else:
        browser_inventory = _run_json(
            root,
            [sys.executable, str(SCRIPT_ROOT / "browser_qa_inventory.py"), "--root", str(root), "--json"],
            args.timeout,
        )["data"]
    if args.dependency:
        dependency_inventory = _load_json(args.dependency)
    else:
        dependency_inventory = _run_json(
            root,
            [sys.executable, str(SCRIPT_ROOT / "dependency_freshness_inventory.py"), "--root", str(root), "--json"],
            args.timeout,
        )["data"]
    return {
        "readiness": readiness,
        "github_inventory": github_inventory,
        "browser_inventory": browser_inventory,
        "dependency_inventory": dependency_inventory,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--readiness", type=Path, help="Existing product_readiness_score JSON artifact")
    parser.add_argument("--github", type=Path, help="Existing github_project_inventory JSON artifact")
    parser.add_argument("--browser", type=Path, help="Existing browser_qa_inventory JSON artifact")
    parser.add_argument("--dependency", type=Path, help="Existing dependency_freshness_inventory JSON artifact")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for each live helper command")
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
