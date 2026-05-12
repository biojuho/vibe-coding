"""Multi-tool session orientation snapshot.

Several AI tools (Claude Code, Codex, Gemini, etc.) edit this repo in parallel.
The recurring friction is *visibility*: "did another tool just commit on top of
me?", "is there an open PR I forgot about?", "has HANDOFF.md drifted past the
rotation threshold again?". The existing single-system tools answer related
but different questions:

  * `workspace/scripts/doctor.py`         — local readiness (venv, env, deps)
  * `workspace/execution/health_check.py` — API keys / providers / governance
  * `workspace/execution/governance_checks.py` — SOP → script mapping

This tool fills the missing seat: a fast multi-source snapshot of what changed
between tools. Each section is small and isolated so partial failures (e.g.
`gh` not authenticated, graph not built) degrade gracefully without tanking
the whole report.

Usage:
    python execution/session_orient.py             # text summary
    python execution/session_orient.py --json      # JSON for automation
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DATE_LINE_RE = re.compile(r"^\|\s*Date\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*$")
GOAL_FIELD_RE = re.compile(r"^-\s*(Status|Goal|Owner|Started|Success):\s*(.*?)\s*$", re.IGNORECASE)


def _run(
    cmd: list[str],
    cwd: Path,
    timeout: float = 10.0,
) -> tuple[int, str]:
    """Run a subprocess, returning (exit_code, stdout). Never raises."""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return result.returncode, result.stdout


def _worktree_counts(status: str) -> dict[str, Any]:
    staged = 0
    modified = 0
    untracked = 0
    unmerged = 0
    for line in status.splitlines():
        if not line:
            continue
        head = line[:2]
        if head == "??":
            untracked += 1
        elif "U" in head:
            unmerged += 1
        else:
            if head[0] != " ":
                staged += 1
            if head[1] != " ":
                modified += 1
    return {
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "unmerged": unmerged,
        "clean": (staged + modified + untracked + unmerged) == 0,
    }


def _parse_recent_commits(log_out: str) -> list[dict[str, str]]:
    commits = []
    for line in log_out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            commits.append({"sha": parts[0], "author": parts[1], "subject": parts[2]})
    return commits


def git_snapshot(repo_root: Path) -> dict[str, Any]:
    """Branch name, ahead/behind origin, worktree counts, recent commits."""
    snap: dict[str, Any] = {"available": False}
    if not (repo_root / ".git").exists():
        return snap

    rc, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if rc != 0:
        return snap

    snap["available"] = True
    snap["branch"] = branch.strip()

    upstream = f"origin/{snap['branch']}"
    rc, counts = _run(
        ["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"],
        repo_root,
    )
    if rc == 0 and counts.strip():
        parts = counts.split()
        if len(parts) == 2:
            snap["behind"] = int(parts[0])
            snap["ahead"] = int(parts[1])

    rc, status = _run(["git", "status", "--porcelain"], repo_root)
    if rc == 0:
        snap["worktree"] = _worktree_counts(status)

    rc, stash_list = _run(["git", "stash", "list"], repo_root)
    snap["stash_count"] = len([line for line in stash_list.splitlines() if line.strip()]) if rc == 0 else 0

    rc, log_out = _run(
        ["git", "log", "--pretty=format:%h\t%an\t%s", "-n", "5"],
        repo_root,
    )
    if rc == 0 and log_out.strip():
        snap["recent_commits"] = _parse_recent_commits(log_out)

    return snap


def pr_snapshot(repo_root: Path) -> dict[str, Any]:
    """Open PR list via `gh`. Degrades gracefully if `gh` is unavailable."""
    if shutil.which("gh") is None:
        return {"available": False, "reason": "gh CLI not installed"}
    rc, out = _run(
        ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,mergeStateStatus"],
        repo_root,
        timeout=15.0,
    )
    if rc != 0:
        return {"available": False, "reason": "gh pr list failed"}
    try:
        prs = json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        return {"available": False, "reason": "unparseable gh output"}
    return {"available": True, "open_count": len(prs), "open": prs}


def handoff_snapshot(repo_root: Path, today: date | None = None) -> dict[str, Any]:
    """HANDOFF.md size, Current Addendum date range, rotation suggestion."""
    today = today or date.today()
    handoff = repo_root / ".ai" / "HANDOFF.md"
    if not handoff.exists():
        return {"available": False, "reason": "HANDOFF.md not found"}
    text = handoff.read_text(encoding="utf-8")
    lines = text.splitlines()
    snap: dict[str, Any] = {
        "available": True,
        "line_count": len(lines),
    }
    # Parse | Date | YYYY-MM-DD | rows within "## Current Addendum" only.
    in_current = False
    dates: list[date] = []
    for line in lines:
        if line.rstrip() == "## Current Addendum":
            in_current = True
            continue
        if in_current and line.startswith("## "):
            break
        if in_current:
            m = DATE_LINE_RE.match(line.rstrip())
            if m:
                dates.append(date.fromisoformat(m.group(1)))
    snap["current_addendum_count"] = len(dates)
    if dates:
        snap["oldest_addendum"] = min(dates).isoformat()
        snap["newest_addendum"] = max(dates).isoformat()
        days_old = (today - min(dates)).days
        snap["oldest_age_days"] = days_old
        snap["rotation_suggested"] = days_old > 7 or len(lines) > 200
    else:
        snap["rotation_suggested"] = False
    return snap


def tasks_snapshot(repo_root: Path) -> dict[str, Any]:
    """TODO / IN_PROGRESS row counts in TASKS.md."""
    tasks_file = repo_root / ".ai" / "TASKS.md"
    if not tasks_file.exists():
        return {"available": False, "reason": "TASKS.md not found"}
    text = tasks_file.read_text(encoding="utf-8")
    section: str | None = None
    todo = 0
    in_progress = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## TODO"):
            section = "todo"
            continue
        if stripped.startswith("## IN_PROGRESS"):
            section = "in_progress"
            continue
        if stripped.startswith("## DONE") or stripped.startswith("### "):
            section = None
            continue
        if section in {"todo", "in_progress"} and stripped.startswith("|"):
            # Skip the header + separator rows.
            if stripped.startswith("| ID ") or set(stripped) <= set("|- :"):
                continue
            if section == "todo":
                todo += 1
            else:
                in_progress += 1
    return {"available": True, "todo": todo, "in_progress": in_progress}


def goal_snapshot(repo_root: Path) -> dict[str, Any]:
    """Read the shared active goal file if present."""
    goal_file = repo_root / ".ai" / "GOAL.md"
    if not goal_file.exists():
        return {"available": False, "reason": "GOAL.md not found"}

    text = goal_file.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    in_active_goal = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_active_goal = stripped.lower() == "## active goal"
            continue
        if not in_active_goal:
            continue
        match = GOAL_FIELD_RE.match(stripped)
        if match:
            fields[match.group(1).lower()] = match.group(2).strip()

    status = fields.get("status", "inactive").lower()
    return {
        "available": True,
        "active": status in {"active", "enabled", "in_progress", "in-progress"},
        "status": fields.get("status", "inactive"),
        "goal": fields.get("goal", ""),
        "owner": fields.get("owner", ""),
        "started": fields.get("started", ""),
        "success": fields.get("success", ""),
    }


def workspace_db_snapshot(repo_root: Path) -> dict[str, Any]:
    """Reuse existing `workspace_db_audit` to surface missing recommended indexes."""
    import importlib.util
    import sys as _sys

    audit_path = repo_root / "execution" / "workspace_db_audit.py"
    if not audit_path.exists():
        return {"available": False, "reason": "workspace_db_audit.py not found"}
    try:
        spec = importlib.util.spec_from_file_location("workspace_db_audit", audit_path)
        if spec is None or spec.loader is None:
            return {"available": False, "reason": "cannot load audit module"}
        module = importlib.util.module_from_spec(spec)
        # Python 3.14 dataclass setup looks up forward references in
        # `sys.modules[cls.__module__]`, so the module must be registered
        # before `exec_module` runs.
        _sys.modules["workspace_db_audit"] = module
        spec.loader.exec_module(module)
        db_path = repo_root / ".tmp" / "workspace.db"
        result = module.run(db_path, apply=False)
    except Exception as exc:  # noqa: BLE001 — diagnostic tool, swallow and report
        return {"available": False, "reason": f"audit failed: {exc}"}
    if result.get("status") == "skip":
        return {"available": False, "reason": result.get("reason", "db missing")}
    return {
        "available": True,
        "table_count": len(result.get("tables", [])),
        "index_count": len(result.get("indexes", [])),
        "missing_recommended": result.get("missing_recommended", []),
    }


def graph_snapshot(repo_root: Path) -> dict[str, Any]:
    """code_review_graph status (node/edge/file counts). Lazy import."""
    snap: dict[str, Any] = {"available": False}
    if shutil.which("py") is not None:
        cmd = ["py", "-3.13", "-m", "code_review_graph", "status"]
    else:
        cmd = ["python", "-m", "code_review_graph", "status"]
    rc, out = _run(cmd, repo_root, timeout=15.0)
    if rc != 0 or not out.strip():
        snap["reason"] = "code_review_graph status failed (graph not built?)"
        return snap
    snap["available"] = True
    for line in out.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        snap[key.strip().lower().replace(" ", "_")] = value.strip()
    return snap


def ci_snapshot(repo_root: Path) -> dict[str, Any]:
    """Latest workflow run on the current branch via `gh`."""
    if shutil.which("gh") is None:
        return {"available": False, "reason": "gh CLI not installed"}
    rc, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if rc != 0:
        return {"available": False, "reason": "cannot determine branch"}
    branch_name = branch.strip()
    rc, out = _run(
        [
            "gh",
            "run",
            "list",
            "--branch",
            branch_name,
            "--limit",
            "3",
            "--json",
            "conclusion,status,name,headSha,createdAt",
        ],
        repo_root,
        timeout=15.0,
    )
    if rc != 0:
        return {"available": False, "reason": "gh run list failed"}
    try:
        runs = json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        return {"available": False, "reason": "unparseable gh output"}
    return {"available": True, "branch": branch_name, "recent_runs": runs}


def collect_snapshot(repo_root: Path, today: date | None = None) -> dict[str, Any]:
    """Build the full multi-source snapshot."""
    return {
        "repo_root": str(repo_root),
        "git": git_snapshot(repo_root),
        "pull_requests": pr_snapshot(repo_root),
        "handoff": handoff_snapshot(repo_root, today=today),
        "tasks": tasks_snapshot(repo_root),
        "goal": goal_snapshot(repo_root),
        "workspace_db": workspace_db_snapshot(repo_root),
        "graph": graph_snapshot(repo_root),
        "ci": ci_snapshot(repo_root),
    }


def _format_worktree(worktree: dict[str, Any]) -> str:
    if worktree.get("clean"):
        return "clean"
    return (
        f"staged={worktree.get('staged', 0)} modified={worktree.get('modified', 0)} "
        f"untracked={worktree.get('untracked', 0)} unmerged={worktree.get('unmerged', 0)}"
    )


def _render_git_section(g: dict[str, Any]) -> list[str]:
    if g.get("available"):
        ahead = g.get("ahead", "?")
        behind = g.get("behind", "?")
        lines = [
            f"  git: {g.get('branch')} (ahead {ahead} / behind {behind}), "
            f"stash {g.get('stash_count', 0)}, worktree {_format_worktree(g.get('worktree', {}))}"
        ]
        for c in g.get("recent_commits", [])[:5]:
            lines.append(f"    {c['sha']} {c['author']:<20} {c['subject']}")
        return lines
    return ["  git: unavailable"]


def _render_pr_section(pr: dict[str, Any]) -> list[str]:
    if pr.get("available"):
        lines = [f"  PRs open: {pr.get('open_count', 0)}"]
        for item in pr.get("open", [])[:5]:
            lines.append(f"    #{item.get('number')} {item.get('title', '')} [{item.get('mergeStateStatus', '?')}]")
        return lines
    return [f"  PRs: unavailable ({pr.get('reason', '?')})"]


def _render_handoff_section(h: dict[str, Any]) -> list[str]:
    if h.get("available"):
        rotation = " (rotation suggested)" if h.get("rotation_suggested") else ""
        return [
            f"  HANDOFF.md: {h.get('line_count')} lines, "
            f"{h.get('current_addendum_count')} addenda, "
            f"oldest {h.get('oldest_addendum', '-')} ({h.get('oldest_age_days', 0)}d){rotation}"
        ]
    return [f"  HANDOFF: unavailable ({h.get('reason', '?')})"]


def _render_tasks_section(t: dict[str, Any]) -> list[str]:
    if t.get("available"):
        return [f"  TASKS: TODO={t.get('todo')}, IN_PROGRESS={t.get('in_progress')}"]
    return [f"  TASKS: unavailable ({t.get('reason', '?')})"]


def _render_goal_section(goal: dict[str, Any]) -> list[str]:
    if goal.get("available"):
        if goal.get("active") and goal.get("goal"):
            owner = f" ({goal.get('owner')})" if goal.get("owner") else ""
            return [f"  GOAL: active{owner} - {goal.get('goal')}"]
        return [f"  GOAL: {goal.get('status', 'inactive')}"]
    return [f"  GOAL: unavailable ({goal.get('reason', '?')})"]


def _render_workspace_db_section(db: dict[str, Any]) -> list[str]:
    if db.get("available"):
        missing = db.get("missing_recommended", [])
        suffix = f" (missing {len(missing)})" if missing else ""
        return [f"  workspace.db: {db.get('table_count')} tables, {db.get('index_count')} indexes{suffix}"]
    return [f"  workspace.db: unavailable ({db.get('reason', '?')})"]


def _render_graph_section(graph: dict[str, Any]) -> list[str]:
    if graph.get("available"):
        return [
            f"  code-review-graph: nodes={graph.get('nodes')}, "
            f"edges={graph.get('edges')}, files={graph.get('files')}, "
            f"updated {graph.get('last_updated', '?')}"
        ]
    return [f"  code-review-graph: unavailable ({graph.get('reason', '?')})"]


def _render_ci_section(ci: dict[str, Any]) -> list[str]:
    if ci.get("available"):
        runs = ci.get("recent_runs", [])
        if runs:
            lines = []
            for r in runs[:3]:
                status = r.get("conclusion") or r.get("status") or "?"
                lines.append(f"  CI [{r.get('name', '?')}]: {status}")
            return lines
        return ["  CI: no recent runs"]
    return [f"  CI: unavailable ({ci.get('reason', '?')})"]


def render_text(snap: dict[str, Any]) -> str:
    lines: list[str] = ["[session-orient] multi-tool snapshot"]
    lines.extend(_render_git_section(snap.get("git", {})))
    lines.extend(_render_pr_section(snap.get("pull_requests", {})))
    lines.extend(_render_handoff_section(snap.get("handoff", {})))
    lines.extend(_render_tasks_section(snap.get("tasks", {})))
    lines.extend(_render_goal_section(snap.get("goal", {})))
    lines.extend(_render_workspace_db_section(snap.get("workspace_db", {})))
    lines.extend(_render_graph_section(snap.get("graph", {})))
    lines.extend(_render_ci_section(snap.get("ci", {})))

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Multi-tool session orientation snapshot for parallel AI workflows.",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of the text summary (for automation).",
    )
    args = parser.parse_args(argv)
    snap = collect_snapshot(args.repo_root)
    if args.json:
        print(json.dumps(snap, ensure_ascii=False))
    else:
        print(render_text(snap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
