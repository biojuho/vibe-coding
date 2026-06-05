#!/usr/bin/env python3
"""Build a launch-objective completion audit manifest from current evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_OBJECTIVE = (
    "Product launch evidence covers the auto-research self-improvement loop, GitHub project inventory, "
    "browser-click QA, A/B adoption, current-code triage, and launch readiness gates."
)
SKILL_ARTIFACTS = (
    ".agents/skills/auto-research/SKILL.md",
    ".agents/skills/auto-research/scripts/ab_decision.py",
    ".agents/skills/auto-research/scripts/browser_qa_inventory.py",
    ".agents/skills/auto-research/scripts/completion_audit.py",
    ".agents/skills/auto-research/scripts/dependency_freshness_inventory.py",
    ".agents/skills/auto-research/scripts/github_project_inventory.py",
    ".agents/skills/auto-research/scripts/launch_objective_audit.py",
)
AI_RELAY_ARTIFACTS = (
    ".ai/HANDOFF.md",
    ".ai/TASKS.md",
    ".ai/SESSION_LOG.md",
    ".ai/CONTEXT.md",
)


def _exists(root: Path, rel_path: str) -> bool:
    return (root / rel_path).exists()


def _read_text(root: Path, rel_path: str) -> str:
    try:
        return (root / rel_path).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


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
            "stdout": "",
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
            if isinstance(parsed, dict):
                data = parsed
            else:
                available = False
                data = {"parse_error": "JSON root was not an object"}
    return {
        "available": available,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": completed.stderr.strip(),
        "data": data,
    }


def _item(
    requirement: str,
    artifacts: list[str],
    evidence: list[str],
    *,
    complete: bool,
    blockers: list[str] | None = None,
    verified: bool = True,
) -> dict[str, Any]:
    return {
        "requirement": requirement,
        "artifacts": artifacts,
        "evidence": evidence,
        "verified": verified,
        "coverage": "complete" if complete else "partial",
        "blockers": blockers or [],
    }


def _skill_item(root: Path) -> dict[str, Any]:
    missing = [path for path in SKILL_ARTIFACTS if not _exists(root, path)]
    skill_text = _read_text(root, ".agents/skills/auto-research/SKILL.md").lower()
    required_terms = (
        "ab_decision.py",
        "browser_qa_inventory.py",
        "completion_audit.py",
        "dependency_freshness_inventory.py",
        "github_project_inventory.py",
        "launch_objective_audit.py",
    )
    missing_terms = [term for term in required_terms if term not in skill_text]
    complete = not missing and not missing_terms
    evidence = [
        f"{len(SKILL_ARTIFACTS) - len(missing)}/{len(SKILL_ARTIFACTS)} required auto-research artifacts exist.",
        "SKILL.md documents A/B, completion audit, launch objective audit, GitHub inventory, "
        "browser QA inventory, and dependency freshness commands."
        if not missing_terms
        else "SKILL.md is missing documented command reference(s): " + ", ".join(missing_terms),
    ]
    blockers = []
    if missing:
        blockers.append("Missing auto-research artifact(s): " + ", ".join(missing))
    if missing_terms:
        blockers.append("Missing SKILL.md command reference(s): " + ", ".join(missing_terms))
    return _item(
        "Create and document the Karpathy-style auto-research self-improvement skill.",
        list(SKILL_ARTIFACTS),
        evidence,
        complete=complete,
        blockers=blockers,
    )


def _github_item(github_inventory: dict[str, Any]) -> dict[str, Any]:
    git = github_inventory.get("git") if isinstance(github_inventory.get("git"), dict) else {}
    open_prs = github_inventory.get("open_prs") if isinstance(github_inventory.get("open_prs"), dict) else {}
    projects = github_inventory.get("projects") if isinstance(github_inventory.get("projects"), list) else []
    workflows = github_inventory.get("workflows") if isinstance(github_inventory.get("workflows"), list) else []
    recommendations = github_inventory.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []
    open_pr_count = open_prs.get("count")
    open_pr_available = open_prs.get("available") is True
    dirty_count = git.get("dirty_count")
    complete = bool(projects) and open_pr_available and open_pr_count == 0 and dirty_count == 0 and not recommendations
    blockers: list[str] = []
    if not projects:
        blockers.append("No GitHub/local projects were discovered.")
    if not open_pr_available:
        blockers.append("Open PR inventory is unavailable.")
    elif open_pr_count:
        blockers.append(f"{open_pr_count} open PR(s) remain.")
    if dirty_count:
        blockers.append(f"Git inventory reports dirty_count={dirty_count}.")
    blockers.extend(str(item) for item in recommendations)
    return _item(
        "Find GitHub-related projects and PR/workflow surfaces before choosing improvements.",
        [".github/workflows", ".github/dependabot.yml", "projects"],
        [
            f"github_project_inventory discovered {len(projects)} project(s) and {len(workflows)} workflow file(s).",
            f"open_prs.available={open_pr_available}, open_prs.count={open_pr_count}.",
            f"git.dirty_count={dirty_count}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(github_inventory),
    )


def _browser_item(browser_inventory: dict[str, Any]) -> dict[str, Any]:
    summary = browser_inventory.get("summary") if isinstance(browser_inventory.get("summary"), dict) else {}
    recommendations = browser_inventory.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []
    browser_count = int(summary.get("browser_project_count") or 0)
    covered_count = int(summary.get("covered_count") or 0)
    missing_count = int(summary.get("missing_count") or 0)
    screenshot_count = int(summary.get("current_screenshot_project_count") or 0)
    fresh_screenshot_count = int(summary.get("fresh_screenshot_project_count", screenshot_count) or 0)
    stale_screenshot_count = int(summary.get("stale_screenshot_project_count") or 0)
    complete = (
        browser_count > 0
        and missing_count == 0
        and covered_count == browser_count
        and screenshot_count == browser_count
        and fresh_screenshot_count == browser_count
    )
    blockers = [str(item) for item in recommendations]
    if missing_count:
        blockers.append("Browser QA missing project(s): " + ", ".join(summary.get("missing_projects") or []))
    if browser_count and screenshot_count < browser_count:
        blockers.append(f"Only {screenshot_count}/{browser_count} browser project(s) have retained screenshots.")
    if browser_count and fresh_screenshot_count < browser_count:
        blockers.append(
            f"Only {fresh_screenshot_count}/{browser_count} browser project(s) have fresh retained screenshots."
        )
    return _item(
        "Use Codex/browser automation to click through every browser app and retain evidence.",
        ["output/playwright", ".ai/TASKS.md", ".ai/HANDOFF.md", ".ai/SESSION_LOG.md"],
        [
            f"browser_qa_inventory coverage {covered_count}/{browser_count}, missing_count={missing_count}.",
            f"current screenshot coverage {screenshot_count}/{browser_count}.",
            f"fresh screenshot coverage {fresh_screenshot_count}/{browser_count}; stale={stale_screenshot_count}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(browser_inventory),
    )


def _dependency_peer_blocker_evidence(dependency_inventory: dict[str, Any]) -> str:
    projects = dependency_inventory.get("projects") if isinstance(dependency_inventory.get("projects"), list) else []
    labels: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        project_path = str(project.get("path") or "unknown")
        dependencies = project.get("dependencies") if isinstance(project.get("dependencies"), list) else []
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            if not dependency.get("deferred") or dependency.get("peer_blocker_check") != "blocked":
                continue
            labels.append(
                f"{project_path}/{dependency.get('name') or 'unknown'} "
                f"peer_blocker_count={int(dependency.get('peer_blocker_count') or 0)}"
            )

    if labels:
        return "Peer-blocked deferred majors: " + "; ".join(labels) + "."
    return "Peer-blocked deferred majors: none."


def _dependency_item(dependency_inventory: dict[str, Any]) -> dict[str, Any]:
    summary = dependency_inventory.get("summary") if isinstance(dependency_inventory.get("summary"), dict) else {}
    recommendations = dependency_inventory.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []
    candidate_count = int(summary.get("candidate_dependency_count") or 0)
    deferred_count = int(summary.get("deferred_dependency_count") or 0)
    unavailable_count = int(summary.get("unavailable_project_count") or 0)
    complete = candidate_count == 0 and unavailable_count == 0
    blockers = []
    if candidate_count:
        blockers.append(f"{candidate_count} direct patch/minor dependency candidate(s) remain.")
    if unavailable_count:
        blockers.append(f"{unavailable_count} package project(s) had unavailable npm freshness inventory.")
    return _item(
        "Research current dependency/code freshness and adopt only safe, evidence-backed improvements.",
        [
            ".agents/skills/auto-research/scripts/dependency_freshness_inventory.py",
            "package.json",
            "pnpm-lock.yaml",
            "projects",
        ],
        [
            f"dependency_freshness_inventory candidate_dependency_count={candidate_count}.",
            f"deferred_dependency_count={deferred_count}; deferred major/channel items require separate explicit experiments.",
            f"unavailable_project_count={unavailable_count}.",
            _dependency_peer_blocker_evidence(dependency_inventory),
            "Recommendations: " + "; ".join(str(item) for item in recommendations)
            if recommendations
            else "Recommendations: none.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(dependency_inventory),
    )


def _readiness_item(readiness: dict[str, Any]) -> dict[str, Any]:
    overall = readiness.get("overall") if isinstance(readiness.get("overall"), dict) else {}
    gates = readiness.get("workspace_gates") if isinstance(readiness.get("workspace_gates"), dict) else {}
    github_gate = gates.get("github_release") if isinstance(gates.get("github_release"), dict) else {}
    workflows = github_gate.get("required_workflows") if isinstance(github_gate.get("required_workflows"), list) else []
    local_blockers = int(overall.get("local_blocker_count") or 0)
    workspace_blockers = int(overall.get("workspace_blocker_count") or 0)
    agent_tasks = int(overall.get("agent_task_count") or 0)
    complete = local_blockers == 0 and workspace_blockers == 0 and agent_tasks == 0
    blockers = []
    if local_blockers:
        blockers.append(f"local_blocker_count={local_blockers}")
    if workspace_blockers:
        blockers.append(f"workspace_blocker_count={workspace_blockers}")
    if agent_tasks:
        blockers.append(f"agent_task_count={agent_tasks}")
    return _item(
        "Verify local product-readiness gates before claiming launch readiness.",
        ["execution/product_readiness_score.py", ".tmp/project_qc_runner_latest.json", ".github/workflows"],
        [
            f"product_readiness_score overall score={overall.get('score')}, state={overall.get('state')}.",
            f"workspace/local/agent blockers={workspace_blockers}/{local_blockers}/{agent_tasks}.",
            "Required workflows: "
            + ", ".join(
                f"{workflow.get('name')}={workflow.get('conclusion') or workflow.get('status')}"
                for workflow in workflows
            ),
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(readiness),
    )


def _external_blocker_item(readiness: dict[str, Any]) -> dict[str, Any]:
    overall = readiness.get("overall") if isinstance(readiness.get("overall"), dict) else {}
    external_blockers = int(overall.get("external_blocker_count") or 0)
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    task_ids: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        for task in project.get("tasks") or []:
            if isinstance(task, dict) and task.get("owner") == "User" and task.get("id"):
                task_ids.append(str(task["id"]))
    complete = external_blockers == 0
    blockers = []
    if external_blockers:
        blockers.append(
            f"{external_blockers} external/user-owned blocker(s) remain: {', '.join(task_ids) or 'unknown'}"
        )
    return _item(
        "Separate externally blocked live checks from local product-polish completion.",
        [".ai/TASKS.md", "projects/hanwoo-dashboard", "execution/product_readiness_score.py"],
        [
            f"product_readiness_score external_blocker_count={external_blockers}.",
            f"user-owned task ids: {', '.join(task_ids) if task_ids else 'none'}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(readiness),
    )


def _ab_loop_item(root: Path) -> dict[str, Any]:
    tasks_text = _read_text(root, ".ai/TASKS.md").lower()
    handoff_text = _read_text(root, ".ai/HANDOFF.md").lower()
    has_ab_script = _exists(root, ".agents/skills/auto-research/scripts/ab_decision.py")
    has_completion_script = _exists(root, ".agents/skills/auto-research/scripts/completion_audit.py")
    has_recent_ab_evidence = "a/b `adopt_candidate`" in tasks_text or "a/b `adopt_candidate`" in handoff_text
    complete = has_ab_script and has_completion_script and has_recent_ab_evidence
    blockers = []
    if not has_ab_script:
        blockers.append("Missing ab_decision.py.")
    if not has_completion_script:
        blockers.append("Missing completion_audit.py.")
    if not has_recent_ab_evidence:
        blockers.append("No recent A/B adoption evidence found in .ai relay files.")
    return _item(
        "Run bounded A/B experiments and adopt only candidates that improve verified metrics.",
        [".agents/skills/auto-research/scripts/ab_decision.py", ".ai/TASKS.md", ".ai/HANDOFF.md"],
        [
            "A/B decision helper exists." if has_ab_script else "A/B decision helper is missing.",
            "Recent .ai relay includes adopt_candidate evidence."
            if has_recent_ab_evidence
            else "No recent relay A/B evidence found.",
        ],
        complete=complete,
        blockers=blockers,
    )


def _relay_item(root: Path) -> dict[str, Any]:
    missing = [path for path in AI_RELAY_ARTIFACTS if not _exists(root, path)]
    complete = not missing
    blockers = ["Missing .ai relay artifact(s): " + ", ".join(missing)] if missing else []
    return _item(
        "Keep the self-improvement loop resumable across tools and sessions.",
        list(AI_RELAY_ARTIFACTS),
        [
            f"{len(AI_RELAY_ARTIFACTS) - len(missing)}/{len(AI_RELAY_ARTIFACTS)} relay files exist.",
            "HANDOFF/TASKS/SESSION_LOG/CONTEXT provide the next-session continuation surface.",
        ],
        complete=complete,
        blockers=blockers,
    )


def build_manifest(
    root: Path,
    *,
    objective: str = DEFAULT_OBJECTIVE,
    readiness: dict[str, Any] | None = None,
    github_inventory: dict[str, Any] | None = None,
    browser_inventory: dict[str, Any] | None = None,
    dependency_inventory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    return {
        "objective": objective,
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(root),
        "success_criteria": [
            "Every explicit launch objective requirement is mapped to concrete artifacts and current evidence.",
            "Local launch gates are green before claiming product readiness.",
            "Externally blocked live checks remain explicit blockers instead of being hidden by proxy signals.",
        ],
        "items": [
            _skill_item(root),
            _github_item(github_inventory or {}),
            _browser_item(browser_inventory or {}),
            _dependency_item(dependency_inventory or {}),
            _readiness_item(readiness or {}),
            _external_blocker_item(readiness or {}),
            _ab_loop_item(root),
            _relay_item(root),
        ],
    }


def collect_current_inputs(root: Path, timeout: int) -> dict[str, dict[str, Any]]:
    python = sys.executable
    commands = {
        "readiness": [python, "execution/product_readiness_score.py", "--json"],
        "github_inventory": [
            python,
            ".agents/skills/auto-research/scripts/github_project_inventory.py",
            "--root",
            ".",
            "--include-prs",
            "--json",
        ],
        "browser_inventory": [
            python,
            ".agents/skills/auto-research/scripts/browser_qa_inventory.py",
            "--root",
            ".",
            "--json",
        ],
        "dependency_inventory": [
            python,
            ".agents/skills/auto-research/scripts/dependency_freshness_inventory.py",
            "--root",
            ".",
            "--json",
        ],
    }
    return {name: _run_json(root, command, timeout) for name, command in commands.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Workspace root")
    parser.add_argument("--objective", default=DEFAULT_OBJECTIVE, help="Objective text for the manifest")
    parser.add_argument("--output", type=Path, help="Write manifest JSON to this path")
    parser.add_argument("--timeout-seconds", type=int, default=120, help="Timeout per evidence command")
    parser.add_argument("--json", action="store_true", help="Print JSON manifest to stdout")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    collected = collect_current_inputs(root, args.timeout_seconds)
    manifest = build_manifest(
        root,
        objective=args.objective,
        readiness=collected["readiness"]["data"],
        github_inventory=collected["github_inventory"]["data"],
        browser_inventory=collected["browser_inventory"]["data"],
        dependency_inventory=collected["dependency_inventory"]["data"],
    )
    manifest["evidence_commands"] = {
        name: {
            "available": result["available"],
            "returncode": result["returncode"],
            "stderr": result["stderr"],
        }
        for name, result in collected.items()
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    if args.json or not args.output:
        json.dump(manifest, sys.stdout, ensure_ascii=True, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
