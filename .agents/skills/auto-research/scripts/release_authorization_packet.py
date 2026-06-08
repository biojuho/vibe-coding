#!/usr/bin/env python3
"""Build a current-head publish authorization evidence packet."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_REQUIRED_WORKFLOWS = ("root-quality-gate", "active-project-matrix")
DEFAULT_COMMIT_PREVIEW_LIMIT = 25
DEFAULT_LLM_WIKI_STRICT_EVIDENCE_PATH = Path(".tmp/llm-wiki-strict-audit-current.json")


def _run(root: Path, args: list[str], timeout: int) -> dict[str, Any]:
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
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _run_readiness(root: Path, timeout: int) -> dict[str, Any]:
    result = _run(root, [sys.executable, "execution/product_readiness_score.py", "--json"], timeout)
    if not result["ok"] or not result["stdout"]:
        return {}
    try:
        parsed = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_ahead_count(branch_status: str) -> int:
    match = re.search(r"\bahead\s+(\d+)", branch_status)
    if not match:
        return 0
    return int(match.group(1))


def _dirty_paths(short_status: str) -> list[str]:
    paths: list[str] = []
    for line in short_status.splitlines():
        if not line or line.startswith("## "):
            continue
        paths.append(line[3:].strip() if len(line) > 3 else line.strip())
    return paths


def _workflow_rows(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    github_release = _as_dict(_as_dict(readiness.get("workspace_gates")).get("github_release"))
    rows: list[dict[str, Any]] = []
    for workflow in _as_list(github_release.get("required_workflows")):
        if not isinstance(workflow, dict):
            continue
        rows.append(
            {
                "name": str(workflow.get("name") or "unknown"),
                "status": workflow.get("status"),
                "conclusion": workflow.get("conclusion"),
                "databaseId": workflow.get("databaseId"),
                "url": workflow.get("url"),
            }
        )
    return rows


def _unproven_workflows(workflows: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for workflow in workflows:
        if workflow.get("status") != "completed" or workflow.get("conclusion") != "success":
            missing.append(str(workflow.get("name") or "unknown"))
    return missing


def _commit_rows(commit_log: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in commit_log.splitlines():
        text = line.strip()
        if not text:
            continue
        parts = text.split(" ", 1)
        rows.append({"sha": parts[0], "subject": parts[1] if len(parts) > 1 else ""})
    return rows


def _commit_preview(commits: list[Any], limit: int) -> list[Any]:
    bounded_limit = max(0, limit)
    return commits[:bounded_limit]


def _review_commands(git_info: dict[str, Any]) -> list[str]:
    upstream = str(git_info.get("upstream") or "").strip()
    if not upstream:
        return [
            "git log --oneline --decorate=no -n 25",
            "git diff --stat HEAD~25..HEAD",
        ]
    return [
        f"git log --oneline --decorate=no {upstream}..HEAD",
        f"git diff --stat {upstream}..HEAD",
    ]


def _collect_git_info(root: Path, timeout: int) -> dict[str, Any]:
    status = _run(root, ["git", "status", "--short", "--branch"], timeout)
    branch = _run(root, ["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout)
    head = _run(root, ["git", "rev-parse", "HEAD"], timeout)
    upstream = _run(root, ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], timeout)

    branch_status = status["stdout"].splitlines()[0] if status["stdout"] else ""
    upstream_ref = upstream["stdout"] if upstream["ok"] else ""
    commit_range = f"{upstream_ref}..HEAD" if upstream_ref else "-n"
    log_args = ["git", "log", "--oneline", "--decorate=no"]
    if upstream_ref:
        log_args.append(commit_range)
    else:
        log_args.extend(["-n", "25"])
    commit_log = _run(root, log_args, timeout)

    return {
        "available": status["ok"] and branch["ok"] and head["ok"],
        "branch_status": branch_status,
        "short_status": status["stdout"],
        "branch": branch["stdout"],
        "head_sha": head["stdout"],
        "upstream": upstream_ref,
        "dirty_paths": _dirty_paths(status["stdout"]),
        "commits": _commit_rows(commit_log["stdout"] if commit_log["ok"] else ""),
    }


def _external_task_ids(readiness: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for project in _as_list(readiness.get("projects")):
        if not isinstance(project, dict):
            continue
        for task in _as_list(project.get("tasks")):
            if not isinstance(task, dict):
                continue
            owner = str(task.get("owner") or "").strip().lower()
            task_id = str(task.get("id") or "").strip()
            if owner == "user" and task_id:
                ids.append(task_id)
    return sorted(set(ids))


def _llm_wiki_strict_evidence(root: Path, current_head_sha: str) -> dict[str, Any]:
    path = root / DEFAULT_LLM_WIKI_STRICT_EVIDENCE_PATH
    data = _load_json(path)
    rel_path = _rel(root, path)
    if not data:
        return {
            "available": False,
            "path": rel_path,
            "status": "missing",
            "head_matches_current": None,
        }

    release_gate = _as_dict(data.get("release_gate"))
    git = _as_dict(data.get("git"))
    report = _as_dict(data.get("report"))
    report_summary = _as_dict(report.get("summary"))
    evidence_head_sha = str(git.get("head_sha") or "").strip()
    current_head_sha = str(current_head_sha or "").strip()
    head_matches_current = evidence_head_sha == current_head_sha if evidence_head_sha and current_head_sha else None

    return {
        "available": True,
        "path": rel_path,
        "schema_version": data.get("schema_version"),
        "evidence_type": data.get("evidence_type"),
        "generated_at": data.get("generated_at"),
        "artifact_path": data.get("artifact_path") or rel_path,
        "command": data.get("command"),
        "status": str(release_gate.get("status") or "unknown"),
        "audit_status": str(report_summary.get("status") or "unknown"),
        "head_sha": evidence_head_sha or None,
        "head_matches_current": head_matches_current,
        "accepted_manifest_warning_count": _int(release_gate.get("accepted_manifest_warning_count")),
        "unexpected_manifest_warning_count": _int(release_gate.get("unexpected_manifest_warning_count")),
        "strict_manifest_warning_failure": bool(release_gate.get("strict_manifest_warning_failure")),
        "source_inventory_count": _int(report_summary.get("source_inventory_count")),
    }


def build_packet(
    root: Path,
    *,
    readiness: dict[str, Any],
    git_info: dict[str, Any] | None = None,
    max_commits: int = DEFAULT_COMMIT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    git_info = git_info or _collect_git_info(root, timeout=30)
    branch_status = str(git_info.get("branch_status") or "")
    ahead_count = _int(_as_dict(_as_dict(readiness.get("workspace_gates")).get("github_release")).get("ahead_count"))
    if ahead_count == 0:
        ahead_count = _parse_ahead_count(branch_status)
    dirty_paths = [str(path) for path in _as_list(git_info.get("dirty_paths"))]
    workflows = _workflow_rows(readiness)
    if not workflows:
        workflows = [
            {"name": name, "status": "missing", "conclusion": None, "databaseId": None, "url": None}
            for name in DEFAULT_REQUIRED_WORKFLOWS
        ]
    unproven = _unproven_workflows(workflows)
    external_task_ids = _external_task_ids(readiness)
    llm_wiki_evidence = _llm_wiki_strict_evidence(root, str(git_info.get("head_sha") or ""))

    if not git_info.get("available", True):
        status = "git_unavailable"
    elif dirty_paths:
        status = "blocked_dirty_worktree"
    elif ahead_count <= 0:
        status = "not_required"
    elif unproven:
        status = "ready_for_authorization"
    else:
        status = "already_verified"

    push_command = (
        f"git push origin {git_info.get('branch') or 'main'}" if ahead_count > 0 and not dirty_paths else None
    )
    blockers: list[str] = []
    if dirty_paths:
        blockers.append(f"dirty worktree paths: {len(dirty_paths)}")
    if ahead_count > 0 and unproven:
        blockers.append("current-head Actions unavailable until push authorization/user push")
    if external_task_ids:
        blockers.append("external/user-owned blocker(s): " + ", ".join(external_task_ids))
    if not llm_wiki_evidence.get("available"):
        blockers.append(f"LLM Wiki strict release evidence artifact missing: {llm_wiki_evidence.get('path')}")
    elif llm_wiki_evidence.get("status") != "pass":
        blockers.append(f"LLM Wiki strict release evidence status={llm_wiki_evidence.get('status')}")
    elif llm_wiki_evidence.get("head_matches_current") is False:
        blockers.append("LLM Wiki strict release evidence head does not match current HEAD")

    commits = _as_list(git_info.get("commits"))
    commit_count = max(len(commits), ahead_count if ahead_count > 0 else 0)
    commits_preview = _commit_preview(commits, max_commits)
    commits_omitted = max(0, commit_count - len(commits_preview))

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(root.resolve()),
        "status": status,
        "summary": {
            "branch": git_info.get("branch"),
            "head": git_info.get("head_sha"),
            "head_short": str(git_info.get("head_sha") or "")[:8],
            "ahead_count": ahead_count,
            "dirty_count": len(dirty_paths),
            "unproven_workflow_count": len(unproven),
            "external_blocker_ids": external_task_ids,
            "commit_count": commit_count,
            "commit_preview_count": len(commits_preview),
            "commit_omitted_count": commits_omitted,
            "authorization_required": ahead_count > 0 and not dirty_paths,
            "llm_wiki_strict_evidence_status": llm_wiki_evidence.get("status"),
            "llm_wiki_strict_evidence_head_matches_current": llm_wiki_evidence.get("head_matches_current"),
            "llm_wiki_strict_evidence_unexpected_count": llm_wiki_evidence.get("unexpected_manifest_warning_count"),
            "llm_wiki_strict_evidence_path": llm_wiki_evidence.get("path"),
        },
        "git": {
            "branch": git_info.get("branch"),
            "upstream": git_info.get("upstream"),
            "head_sha": git_info.get("head_sha"),
            "branch_status": branch_status,
            "ahead_count": ahead_count,
            "dirty_count": len(dirty_paths),
            "dirty_paths": dirty_paths,
            "commits_ahead": commits_preview,
            "commits_ahead_preview": commits_preview,
            "commits_ahead_limit": max(0, max_commits),
            "commits_ahead_omitted": commits_omitted,
            "commit_count": commit_count,
            "review_commands": _review_commands(git_info),
        },
        "required_workflows": workflows,
        "unproven_workflows": unproven,
        "llm_wiki_strict_evidence": llm_wiki_evidence,
        "authorization": {
            "push_required": ahead_count > 0,
            "allowed_without_explicit_user_authorization": False,
            "suggested_command": push_command,
            "post_push_gates": unproven or [workflow["name"] for workflow in workflows],
            "guardrails": [
                "Do not push without explicit user authorization.",
                "After push, wait for root-quality-gate and active-project-matrix on the exact current HEAD.",
                "Do not retry external T-251 until Supabase credentials were reset.",
            ],
        },
        "blockers": blockers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--readiness", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--max-commits",
        type=int,
        default=DEFAULT_COMMIT_PREVIEW_LIMIT,
        help="Maximum ahead commits to include in the default packet preview.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    readiness = _load_json(args.readiness) if args.readiness else _run_readiness(root, args.timeout)
    packet = build_packet(
        root,
        readiness=readiness,
        git_info=_collect_git_info(root, args.timeout),
        max_commits=args.max_commits,
    )

    text = json.dumps(packet, ensure_ascii=True, indent=2)
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    if args.json or not args.output:
        print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
