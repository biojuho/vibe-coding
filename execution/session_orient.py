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
the whole report. Now built with Rich (Textualize) for an exceptional Terminal UI (TUI) experience.
Now optimized with absolute safety for Windows CP949 encoding environments.

Usage:
    python execution/session_orient.py             # Rich TUI dashboard
    python execution/session_orient.py --json      # JSON for automation
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# Rich imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    from rich.box import ROUNDED, ASCII

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DATE_LINE_RE = re.compile(r"^\|\s*Date\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*$")
GOAL_FIELD_RE = re.compile(r"^-\s*(Status|Goal|Owner|Started|Success):\s*(.*?)\s*$", re.IGNORECASE)
HEAD_CLAIM_RE = re.compile(
    r"\bcurrent\b(?:(?!\|).){0,160}\bhead\b(?:(?!\|).){0,80}`([0-9a-f]{7,40})`",
    re.IGNORECASE,
)
IS_WINDOWS = sys.platform == "win32"

# Windows-safe symbols (Unicode-safe for CP949 console)
SYM_ROCKET = "LAUNCH" if IS_WINDOWS else "🚀"
SYM_GIT = "GIT" if IS_WINDOWS else "📂"
SYM_HANDOFF = "HANDOFF" if IS_WINDOWS else "📝"
SYM_TASKS = "TASKS" if IS_WINDOWS else "🎯"
SYM_COMMIT = "COMMIT" if IS_WINDOWS else "🕰️"
SYM_PR = "PR" if IS_WINDOWS else "🔌"
SYM_GOAL = "GOAL" if IS_WINDOWS else "🎯"
SYM_DIAG = "DIAG" if IS_WINDOWS else "🛠️"
SYM_WARN = "WARN" if IS_WINDOWS else "⚠️"
SYM_TODO = "TODO" if IS_WINDOWS else "📋"
SYM_FLASH = "PROGRESS" if IS_WINDOWS else "⚡"


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


def _latest_current_addendum_text(lines: list[str]) -> str:
    """Return the first addendum block under `## Current Addendum`."""
    in_current = False
    in_first_block = False
    block: list[str] = []

    for line in lines:
        stripped = line.rstrip()
        if stripped == "## Current Addendum":
            in_current = True
            continue
        if in_current and stripped.startswith("## "):
            break
        if not in_current:
            continue
        if stripped.startswith("| Field | Value |"):
            if in_first_block:
                break
            in_first_block = True
        if in_first_block:
            block.append(stripped)

    return "\n".join(block)


def _extract_head_claims(text: str) -> list[str]:
    """Find explicit latest-addendum claims about the current git HEAD."""
    return [match.group(1) for match in HEAD_CLAIM_RE.finditer(text)]


def _head_claim_matches(claim: str, current_head: str) -> bool:
    claim_norm = claim.lower()
    current_norm = current_head.lower()
    return current_norm.startswith(claim_norm) or claim_norm.startswith(current_norm)


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


def handoff_snapshot(repo_root: Path, today: date | None = None, current_head: str | None = None) -> dict[str, Any]:
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
        cutoff = today - timedelta(days=7)
        archivable_count = sum(1 for entry_date in dates if entry_date < cutoff)
        snap["rotation_cutoff"] = cutoff.isoformat()
        snap["archivable_addendum_count"] = archivable_count
        snap["rotation_suggested"] = archivable_count > 0
    else:
        snap["archivable_addendum_count"] = 0
        snap["rotation_suggested"] = False

    latest_addendum = _latest_current_addendum_text(lines)
    head_claims = _extract_head_claims(latest_addendum)
    snap["latest_head_claims"] = head_claims
    if current_head:
        stale_claims = [claim for claim in head_claims if not _head_claim_matches(claim, current_head)]
        snap["current_head"] = current_head
        snap["stale_head_claims"] = stale_claims
        if stale_claims:
            snap["head_claim_status"] = "stale"
        elif head_claims:
            snap["head_claim_status"] = "ok"
        else:
            snap["head_claim_status"] = "none"
    else:
        snap["stale_head_claims"] = []
        snap["head_claim_status"] = "unavailable" if head_claims else "none"
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
        "raw_content": text,
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
    commands = [["python", "-m", "code_review_graph", "status"]]
    if shutil.which("py") is not None:
        commands.append(["py", "-3.13", "-m", "code_review_graph", "status"])

    for cmd in commands:
        rc, out = _run(cmd, repo_root, timeout=15.0)
        if rc != 0 or not out.strip():
            continue
        snap["available"] = True
        for line in out.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            snap[key.strip().lower().replace(" ", "_")] = value.strip()
        return snap

    snap["reason"] = "code_review_graph status failed (graph not built?)"
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
    git = git_snapshot(repo_root)
    current_head = None
    if git.get("available") and git.get("recent_commits"):
        current_head = git["recent_commits"][0].get("sha")
    return {
        "repo_root": str(repo_root),
        "git": git,
        "pull_requests": pr_snapshot(repo_root),
        "handoff": handoff_snapshot(repo_root, today=today, current_head=current_head),
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
        lines = [
            f"  HANDOFF.md: {h.get('line_count')} lines, "
            f"{h.get('current_addendum_count')} addenda, "
            f"oldest {h.get('oldest_addendum', '-')} ({h.get('oldest_age_days', 0)}d){rotation}"
        ]
        if h.get("stale_head_claims"):
            lines.append(
                "    stale latest head claim(s): "
                f"{', '.join(h.get('stale_head_claims', []))} != {h.get('current_head', '?')}"
            )
        return lines
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
    """Standard text output (fallback)."""
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


def render_rich_dashboard(snap: dict[str, Any]) -> None:
    """Rich TUI Dashboard renderer with CP949 compatibility guards."""
    console = Console(safe_box=True)
    box_style = ASCII if IS_WINDOWS else ROUNDED

    # 1. Title Banner
    title_text = Text(
        f"\n {SYM_ROCKET} VIBE CODING - COLLABORATIVE SESSION DASHBOARD {SYM_ROCKET} \n",
        style="bold white on rgb(65,40,90)",
    )
    title_align = Align.center(title_text)
    console.print(Panel(title_align, box=ROUNDED if not IS_WINDOWS else ASCII, border_style="rgb(120,60,200)"))

    # 2. Key Metrics Columns
    metrics_grid = Table.grid(expand=True)
    metrics_grid.add_column(ratio=1)
    metrics_grid.add_column(ratio=1)
    metrics_grid.add_column(ratio=1)

    # Column 1: Git Status Info
    git_snap = snap.get("git", {})
    if git_snap.get("available"):
        ahead = git_snap.get("ahead", 0)
        behind = git_snap.get("behind", 0)
        worktree = git_snap.get("worktree", {})
        stash = git_snap.get("stash_count", 0)

        wt_details = []
        if worktree.get("staged", 0) > 0:
            wt_details.append(f"[bold green]Staged: {worktree['staged']}[/]")
        if worktree.get("modified", 0) > 0:
            wt_details.append(f"[bold yellow]Modified: {worktree['modified']}[/]")
        if worktree.get("untracked", 0) > 0:
            wt_details.append(f"[bold cyan]Untracked: {worktree['untracked']}[/]")
        if worktree.get("unmerged", 0) > 0:
            wt_details.append(f"[bold red]Unmerged: {worktree['unmerged']}[/]")

        wt_str = ", ".join(wt_details) if wt_details else "[dim green]Clean[/]"

        git_desc = (
            f"[bold magenta]Branch:[/] [bold cyan]{git_snap.get('branch')}[/]\n"
            f"[bold magenta]Sync:[/] [green]Ahead {ahead}[/] / [red]Behind {behind}[/]\n"
            f"[bold magenta]Stash Count:[/] {stash}\n"
            f"[bold magenta]Worktree:[/] {wt_str}"
        )
        git_panel = Panel(git_desc, title=f"{SYM_GIT} Git Repository", border_style="rgb(160,80,220)", box=box_style)
    else:
        git_panel = Panel(
            "[bold red]Git Unavailable[/]", title=f"{SYM_GIT} Git Repository", border_style="red", box=box_style
        )

    # Column 2: HANDOFF & TASKS
    ho_snap = snap.get("handoff", {})
    ho_str = "[bold red]Handoff Not Available[/]"
    ho_style = "red"
    if ho_snap.get("available"):
        rot_alert = ""
        ho_style = "rgb(160,80,220)"
        if ho_snap.get("rotation_suggested"):
            rot_alert = f"\n[bold orange3]{SYM_WARN} Rotation Suggested! (Old/Large Handoff)[/]"
            ho_style = "orange3"
        ho_str = (
            f"[bold magenta]Lines:[/] {ho_snap.get('line_count')}\n"
            f"[bold magenta]Addenda count:[/] {ho_snap.get('current_addendum_count')} (Last 7d)\n"
            f"[bold magenta]Oldest Addendum:[/] {ho_snap.get('oldest_addendum')} ({ho_snap.get('oldest_age_days')}d old)"
            f"{rot_alert}"
        )
    handoff_panel = Panel(ho_str, title=f"{SYM_HANDOFF} HANDOFF Status", border_style=ho_style, box=box_style)

    # Column 3: TASKS Kanban Summary
    t_snap = snap.get("tasks", {})
    t_str = "[bold red]TASKS Not Available[/]"
    if t_snap.get("available"):
        t_str = (
            f"[bold yellow]{SYM_TODO} TODO Tasks:[/] [bold yellow]{t_snap.get('todo')}[/]\n\n"
            f"[bold green]{SYM_FLASH} In Progress:[/] [bold green]{t_snap.get('in_progress')}[/]"
        )
    tasks_panel = Panel(t_str, title=f"{SYM_TASKS} TASKS Kanban Summary", border_style="rgb(160,80,220)", box=box_style)

    metrics_grid.add_row(git_panel, handoff_panel, tasks_panel)
    console.print(metrics_grid)
    console.print()

    # 3. Center Section: Left (Commits & PRs) vs Right (Active Goal & Info)
    center_table = Table.grid(expand=True)
    center_table.add_column(ratio=6)
    center_table.add_column(ratio=4)

    # Left: Commits & PRs Tables
    left_flow = Table.grid(expand=True)
    left_flow.add_column(ratio=1)

    # Recent Commits Table
    commit_table = Table(
        title=f"{SYM_COMMIT} Recent 5 Repository Commits", expand=True, box=box_style, border_style="rgb(80,80,180)"
    )
    commit_table.add_column("SHA", style="bold cyan", width=8)
    commit_table.add_column("Author", style="yellow", width=15)
    commit_table.add_column("Subject", style="green", ratio=1)

    if git_snap.get("available") and git_snap.get("recent_commits"):
        for c in git_snap.get("recent_commits", []):
            commit_table.add_row(c["sha"], c["author"], c["subject"])
    else:
        commit_table.add_row("-", "-", "No recent commits found")

    left_flow.add_row(commit_table)
    left_flow.add_row("")

    # PRs Table
    pr_snap = snap.get("pull_requests", {})
    pr_table = Table(title=f"{SYM_PR} Open Pull Requests", expand=True, box=box_style, border_style="rgb(80,80,180)")
    pr_table.add_column("No", style="bold yellow", width=6)
    pr_table.add_column("Title", style="white", ratio=1)
    pr_table.add_column("Merge State", style="bold green", width=15)

    if pr_snap.get("available") and pr_snap.get("open"):
        for p in pr_snap.get("open", []):
            state = p.get("mergeStateStatus", "?")
            state_color = "green" if state == "CLEAN" else "red" if state == "BLOCKED" else "yellow"
            pr_table.add_row(f"#{p.get('number')}", p.get("title"), f"[{state_color}]{state}[/]")
    else:
        reason = pr_snap.get("reason", "No open PRs found")
        pr_table.add_row("-", reason, "-")

    left_flow.add_row(pr_table)

    # Right: Active Goal and Database/Graph Metrics
    right_flow = Table.grid(expand=True)
    right_flow.add_column(ratio=1)

    # Active Goal Panel
    goal_snap = snap.get("goal", {})
    if goal_snap.get("available") and goal_snap.get("active"):
        goal_content = (
            f"[bold magenta]Active Goal:[/] {goal_snap.get('goal')}\n"
            f"[bold magenta]Owner:[/] [bold yellow]{goal_snap.get('owner')}[/]\n"
            f"[bold magenta]Started:[/] {goal_snap.get('started')}\n"
            f"[bold magenta]Success Rule:[/] [green]{goal_snap.get('success')}[/]"
        )
        goal_panel = Panel(goal_content, title=f"{SYM_GOAL} ACTIVE GOAL", border_style="gold1", box=box_style)
    else:
        goal_panel = Panel(
            "[dim white]No active system goals currently registered.[/]",
            title=f"{SYM_GOAL} ACTIVE GOAL",
            border_style="grey50",
            box=box_style,
        )

    right_flow.add_row(goal_panel)
    right_flow.add_row("")

    # Diagnostics Info (DB & code-review-graph & CI)
    db_snap = snap.get("workspace_db", {})
    db_str = "[bold red]Database Unavailable[/]"
    if db_snap.get("available"):
        missing = db_snap.get("missing_recommended", [])
        missing_str = (
            f" [bold red](missing {len(missing)} indexes!)[/]" if missing else " [bold green](All indexes OK)[/]"
        )
        db_str = f"Tables: {db_snap.get('table_count')}, Indexes: {db_snap.get('index_count')}{missing_str}"

    g_snap = snap.get("graph", {})
    g_str = "[bold red]Graph Status Unavailable[/]"
    if g_snap.get("available"):
        g_str = f"Nodes: {g_snap.get('nodes')}, Edges: {g_snap.get('edges')}, Files: {g_snap.get('files')}"

    ci_snap = snap.get("ci", {})
    ci_lines = []
    if ci_snap.get("available"):
        runs = ci_snap.get("recent_runs", [])
        if runs:
            for r in runs[:2]:
                status = r.get("conclusion") or r.get("status") or "?"
                color = (
                    "bold green"
                    if status in {"success", "completed"}
                    else "bold yellow"
                    if status == "in_progress"
                    else "bold red"
                )
                ci_lines.append(f"* {r.get('name', 'Workflow')}: [{color}]{status}[/]")
        else:
            ci_lines.append("[dim]No recent runs on this branch[/]")
    else:
        ci_lines.append(f"[dim red]CI stats unavailable ({ci_snap.get('reason', '?')})[/]")
    ci_str = "\n".join(ci_lines)

    diag_str = (
        f"[bold magenta]Workspace DB:[/] {db_str}\n\n"
        f"[bold magenta]Review Graph:[/] {g_str}\n\n"
        f"[bold magenta]Recent CI runs:[/]\n{ci_str}"
    )
    diag_panel = Panel(
        diag_str, title=f"{SYM_DIAG} System Diagnostics & Graph", border_style="rgb(100,100,100)", box=box_style
    )
    right_flow.add_row(diag_panel)

    center_table.add_row(left_flow, right_flow)
    console.print(center_table)
    console.print()


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_text)


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
        _safe_print(json.dumps(snap, ensure_ascii=True))
    else:
        # If Rich is installed, use rich dashboard
        if RICH_AVAILABLE:
            try:
                render_rich_dashboard(snap)
            except Exception as exc:  # fallback if rich crashes due to environment
                _safe_print(f"Rich rendering failed: {exc}. Falling back to standard text.\n")
                _safe_print(render_text(snap))
        else:
            _safe_print(render_text(snap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
