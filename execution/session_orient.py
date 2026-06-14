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
    from rich.align import Align
    from rich.box import ASCII, ROUNDED
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

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
NEXT_PRIORITIES_ROW_RE = re.compile(r"^\|\s*Next Priorities\s*\|\s*(.*?)\s*\|\s*$", re.IGNORECASE | re.MULTILINE)
WORK_ROW_RE = re.compile(r"^\|\s*Work\s*\|\s*(.*?)\s*\|\s*$", re.IGNORECASE | re.MULTILINE)
PRIMARY_WORK_TASK_ID_RE = re.compile(r"^\s*(?:[*_`]+)?\s*T-(\d{1,6})(?:[a-z])?\b", re.IGNORECASE)
NEXT_PRIORITY_CLOSEOUT_ACTION_RE = re.compile(r"\b(commit(?:ted)?|push(?:ed)?|rerun|re-run)\b", re.IGNORECASE)
NEXT_PRIORITY_CLOSEOUT_CONTEXT_RE = re.compile(
    r"\b(closeout|context head|new context head|final live checks|release[- ]gates?|relay update|clean[- ]state|completion audit|launch[- ]objective audit)\b|\bpost[- ]push\b",
    re.IGNORECASE,
)
TASK_ID_RE = re.compile(r"\bT-(\d{1,6})(?:[a-z])?\b", re.IGNORECASE)
REQUIRED_RELEASE_WORKFLOWS = frozenset({"root-quality-gate", "active-project-matrix"})
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


def _current_addendum_dates(lines: list[str]) -> list[date]:
    """Parse dated rows inside the HANDOFF Current Addendum section."""
    in_current = False
    dates: list[date] = []
    for line in lines:
        stripped = line.rstrip()
        if stripped == "## Current Addendum":
            in_current = True
            continue
        if in_current and stripped.startswith("## "):
            break
        if not in_current:
            continue
        match = DATE_LINE_RE.match(stripped)
        if match:
            dates.append(date.fromisoformat(match.group(1)))
    return dates


def _handoff_rotation_fields(dates: list[date], today: date) -> dict[str, Any]:
    """Build HANDOFF rotation metadata from parsed addendum dates."""
    if not dates:
        return {
            "archivable_addendum_count": 0,
            "rotation_suggested": False,
        }

    oldest = min(dates)
    newest = max(dates)
    cutoff = today - timedelta(days=7)
    archivable_count = sum(1 for entry_date in dates if entry_date < cutoff)
    return {
        "oldest_addendum": oldest.isoformat(),
        "newest_addendum": newest.isoformat(),
        "oldest_age_days": (today - oldest).days,
        "rotation_cutoff": cutoff.isoformat(),
        "archivable_addendum_count": archivable_count,
        "rotation_suggested": archivable_count > 0,
    }


def _current_addendum_blocks(lines: list[str]) -> list[str]:
    """Return addendum blocks under `## Current Addendum` in document order."""
    in_current = False
    current_block: list[str] = []
    blocks: list[str] = []

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
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
        if stripped or current_block:
            current_block.append(stripped)

    if current_block:
        blocks.append("\n".join(current_block))

    return blocks


def _latest_current_addendum_text(lines: list[str]) -> str:
    """Return the first addendum block under `## Current Addendum`."""
    blocks = _current_addendum_blocks(lines)
    return blocks[0] if blocks else ""


def _highest_task_id(text: str) -> int | None:
    work_match = WORK_ROW_RE.search(text)
    if work_match:
        task_source = work_match.group(1)
        primary_match = PRIMARY_WORK_TASK_ID_RE.search(task_source)
        if primary_match:
            return int(primary_match.group(1))
    else:
        task_source = text
    values = [int(match.group(1)) for match in TASK_ID_RE.finditer(task_source)]
    return max(values) if values else None


def _effective_latest_addendum_by_task_id(blocks: list[str]) -> tuple[str, int | None]:
    """Return the block with the highest task id, falling back to document order."""
    if not blocks:
        return "", None

    best_block = blocks[0]
    best_task_id = _highest_task_id(best_block)
    for block in blocks[1:]:
        task_id = _highest_task_id(block)
        if task_id is not None and (best_task_id is None or task_id > best_task_id):
            best_block = block
            best_task_id = task_id
    return best_block, best_task_id


def _handoff_task_order_issue(blocks: list[str]) -> dict[str, Any] | None:
    """Detect when a later Current Addendum has a higher T-ID than the first block."""
    if len(blocks) < 2:
        return None

    first_id = _highest_task_id(blocks[0])
    later_ids = [_highest_task_id(block) for block in blocks[1:]]
    later_ids = [task_id for task_id in later_ids if task_id is not None]
    if first_id is None or not later_ids:
        return None

    max_later = max(later_ids)
    if max_later <= first_id:
        return None

    return {
        "first_task_id": f"T-{first_id}",
        "newer_task_id": f"T-{max_later}",
        "reason": f"Current Addendum first block is T-{first_id}, but a later block mentions T-{max_later}.",
    }


def _extract_head_claims(text: str) -> list[str]:
    """Find explicit latest-addendum claims about the current git HEAD."""
    return [match.group(1) for match in HEAD_CLAIM_RE.finditer(text)]


def _extract_next_priorities(text: str) -> str:
    """Return the latest addendum's `Next Priorities` cell text."""
    match = NEXT_PRIORITIES_ROW_RE.search(text)
    return match.group(1).strip() if match else ""


def _head_claim_matches(claim: str, current_head: str) -> bool:
    claim_norm = claim.lower()
    current_norm = current_head.lower()
    return current_norm.startswith(claim_norm) or claim_norm.startswith(current_norm)


def _is_closeout_next_priority(next_priorities: str) -> bool:
    if not next_priorities:
        return False
    return bool(
        NEXT_PRIORITY_CLOSEOUT_ACTION_RE.search(next_priorities)
        and NEXT_PRIORITY_CLOSEOUT_CONTEXT_RE.search(next_priorities)
    )


def _stale_next_priority_reason(
    next_priorities: str,
    git_clean_synced: bool | None,
    release_checks_green: bool | None,
) -> str | None:
    if (
        git_clean_synced is not True
        or release_checks_green is not True
        or not _is_closeout_next_priority(next_priorities)
    ):
        return None
    return (
        "git clean/synced with green release checks but latest Next Priorities still asks for post-push closeout work"
    )


def _next_priority_note(
    next_priorities: str,
    worktree_clean: bool | None,
    git_clean_synced: bool | None,
) -> str | None:
    if not _is_closeout_next_priority(next_priorities):
        return None
    if worktree_clean is not True or git_clean_synced is not False:
        return None
    if not re.search(r"\bcommit(?:ted)?\b", next_priorities, re.IGNORECASE):
        return None
    return (
        "worktree clean; any commit-this-relay-update closeout step is already satisfied locally, "
        "while publish/CI/user blockers may still remain"
    )


def _git_clean_synced(git: dict[str, Any]) -> bool | None:
    if not git.get("available"):
        return None
    if git.get("worktree", {}).get("clean") is not True:
        return False
    ahead = git.get("ahead")
    behind = git.get("behind")
    if ahead is None or behind is None:
        return None
    return ahead == 0 and behind == 0


def _head_matches_run(current_head: str, run_head: str) -> bool:
    current_norm = current_head.lower()
    run_norm = run_head.lower()
    return run_norm.startswith(current_norm) or current_norm.startswith(run_norm)


def _required_release_checks_green(ci: dict[str, Any], current_head: str | None) -> bool | None:
    if not current_head or not ci.get("available"):
        return None

    matching: dict[str, dict[str, Any]] = {}
    for run in ci.get("recent_runs", []):
        if not isinstance(run, dict):
            continue
        name = str(run.get("name") or "")
        head_sha = str(run.get("headSha") or "")
        if name in REQUIRED_RELEASE_WORKFLOWS and head_sha and _head_matches_run(current_head, head_sha):
            matching[name] = run

    if not REQUIRED_RELEASE_WORKFLOWS.issubset(matching):
        return None

    return all(run.get("status") == "completed" and run.get("conclusion") == "success" for run in matching.values())


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


def handoff_snapshot(
    repo_root: Path,
    today: date | None = None,
    current_head: str | None = None,
    git_clean_synced: bool | None = None,
    release_checks_green: bool | None = None,
    worktree_clean: bool | None = None,
) -> dict[str, Any]:
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
    dates = _current_addendum_dates(lines)
    snap["current_addendum_count"] = len(dates)
    snap.update(_handoff_rotation_fields(dates, today))

    addendum_blocks = _current_addendum_blocks(lines)
    latest_addendum = addendum_blocks[0] if addendum_blocks else ""
    effective_latest_addendum, effective_latest_task_id = _effective_latest_addendum_by_task_id(addendum_blocks)
    task_order_issue = _handoff_task_order_issue(addendum_blocks)
    snap["latest_addendum_order_status"] = "out_of_order" if task_order_issue else "ok"
    snap["latest_addendum_order_issue"] = task_order_issue
    snap["effective_latest_task_id"] = f"T-{effective_latest_task_id}" if effective_latest_task_id is not None else None
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

    next_priorities = _extract_next_priorities(latest_addendum)
    effective_next_priorities = _extract_next_priorities(effective_latest_addendum)
    stale_next_priority_reason = _stale_next_priority_reason(next_priorities, git_clean_synced, release_checks_green)
    latest_next_priority_note = _next_priority_note(next_priorities, worktree_clean, git_clean_synced)
    snap["latest_next_priorities"] = next_priorities
    snap["effective_latest_next_priorities"] = effective_next_priorities
    snap["stale_next_priority_reason"] = stale_next_priority_reason
    snap["latest_next_priority_note"] = latest_next_priority_note
    if not next_priorities:
        snap["latest_next_priority_status"] = "none"
    elif task_order_issue:
        snap["latest_next_priority_status"] = "out_of_order"
    elif stale_next_priority_reason:
        snap["latest_next_priority_status"] = "stale"
    elif (
        git_clean_synced is None or (git_clean_synced is True and release_checks_green is None)
    ) and _is_closeout_next_priority(next_priorities):
        snap["latest_next_priority_status"] = "unavailable"
    else:
        snap["latest_next_priority_status"] = "ok"
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


def graph_snapshot(repo_root: Path, current_head: str | None = None) -> dict[str, Any]:
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
        if current_head:
            _annotate_graph_freshness(snap, current_head)
        return snap

    snap["reason"] = "code_review_graph status failed (graph not built?)"
    return snap


def _annotate_graph_freshness(snap: dict[str, Any], current_head: str) -> None:
    """Mark whether the graph build belongs to the current git HEAD."""
    snap["current_head"] = current_head
    built_at_commit = str(snap.get("built_at_commit") or "").strip()
    if not built_at_commit:
        snap["freshness"] = "unknown"
        snap["stale"] = None
        snap["stale_reason"] = "graph status did not report built_at_commit"
        return

    if _head_matches_run(current_head, built_at_commit):
        snap["freshness"] = "current"
        snap["stale"] = False
        return

    snap["freshness"] = "stale"
    snap["stale"] = True
    snap["stale_reason"] = f"built_at_commit {built_at_commit[:8]} != current_head {current_head[:8]}"


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
    ci = ci_snapshot(repo_root)
    return {
        "repo_root": str(repo_root),
        "git": git,
        "pull_requests": pr_snapshot(repo_root),
        "handoff": handoff_snapshot(
            repo_root,
            today=today,
            current_head=current_head,
            git_clean_synced=_git_clean_synced(git),
            release_checks_green=_required_release_checks_green(ci, current_head),
            worktree_clean=git.get("worktree", {}).get("clean") if git.get("available") else None,
        ),
        "tasks": tasks_snapshot(repo_root),
        "goal": goal_snapshot(repo_root),
        "workspace_db": workspace_db_snapshot(repo_root),
        "graph": graph_snapshot(repo_root, current_head=current_head),
        "ci": ci,
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
        if h.get("latest_next_priority_status") == "stale":
            lines.append(f"    stale latest next priority: {h.get('stale_next_priority_reason')}")
        if h.get("latest_next_priority_status") == "out_of_order":
            issue = h.get("latest_addendum_order_issue") or {}
            lines.append(
                f"    out-of-order latest addendum: {issue.get('reason', 'newer addendum appears below first block')}"
            )
            if h.get("effective_latest_task_id"):
                lines.append(
                    "    effective latest next priority "
                    f"({h.get('effective_latest_task_id')}): {h.get('effective_latest_next_priorities', '')}"
                )
        if h.get("latest_next_priority_note"):
            lines.append(f"    latest next priority note: {h.get('latest_next_priority_note')}")
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
        suffix = ""
        if graph.get("freshness") == "stale":
            suffix = f", stale ({graph.get('stale_reason', 'commit mismatch')})"
        elif graph.get("freshness") == "current":
            suffix = ", current HEAD"
        elif graph.get("freshness") == "unknown":
            suffix = f", freshness unknown ({graph.get('stale_reason', 'missing build commit')})"
        return [
            f"  code-review-graph: nodes={graph.get('nodes')}, "
            f"edges={graph.get('edges')}, files={graph.get('files')}, "
            f"updated {graph.get('last_updated', '?')}{suffix}"
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


def _rich_dashboard_title_panel() -> Any:
    title_text = Text(
        f"\n {SYM_ROCKET} VIBE CODING - COLLABORATIVE SESSION DASHBOARD {SYM_ROCKET} \n",
        style="bold white on rgb(65,40,90)",
    )
    return Panel(
        Align.center(title_text),
        box=ROUNDED if not IS_WINDOWS else ASCII,
        border_style="rgb(120,60,200)",
    )


def _rich_worktree_details(worktree: dict[str, Any]) -> list[str]:
    details = []
    if worktree.get("staged", 0) > 0:
        details.append(f"[bold green]Staged: {worktree['staged']}[/]")
    if worktree.get("modified", 0) > 0:
        details.append(f"[bold yellow]Modified: {worktree['modified']}[/]")
    if worktree.get("untracked", 0) > 0:
        details.append(f"[bold cyan]Untracked: {worktree['untracked']}[/]")
    if worktree.get("unmerged", 0) > 0:
        details.append(f"[bold red]Unmerged: {worktree['unmerged']}[/]")
    return details


def _rich_git_panel(git_snap: dict[str, Any], box_style: Any) -> Any:
    if not git_snap.get("available"):
        return Panel(
            "[bold red]Git Unavailable[/]",
            title=f"{SYM_GIT} Git Repository",
            border_style="red",
            box=box_style,
        )

    ahead = git_snap.get("ahead", 0)
    behind = git_snap.get("behind", 0)
    worktree = git_snap.get("worktree", {})
    wt_details = _rich_worktree_details(worktree)
    wt_str = ", ".join(wt_details) if wt_details else "[dim green]Clean[/]"
    git_desc = (
        f"[bold magenta]Branch:[/] [bold cyan]{git_snap.get('branch')}[/]\n"
        f"[bold magenta]Sync:[/] [green]Ahead {ahead}[/] / [red]Behind {behind}[/]\n"
        f"[bold magenta]Stash Count:[/] {git_snap.get('stash_count', 0)}\n"
        f"[bold magenta]Worktree:[/] {wt_str}"
    )
    return Panel(
        git_desc,
        title=f"{SYM_GIT} Git Repository",
        border_style="rgb(160,80,220)",
        box=box_style,
    )


def _rich_handoff_panel(handoff: dict[str, Any], box_style: Any) -> Any:
    ho_str = "[bold red]Handoff Not Available[/]"
    ho_style = "red"
    if handoff.get("available"):
        rot_alert = ""
        ho_style = "rgb(160,80,220)"
        if handoff.get("rotation_suggested"):
            rot_alert = f"\n[bold orange3]{SYM_WARN} Rotation Suggested! (Old/Large Handoff)[/]"
            ho_style = "orange3"
        priority_alert = ""
        if handoff.get("latest_next_priority_status") == "stale":
            priority_alert = (
                f"\n[bold orange3]{SYM_WARN} Stale next priority: {handoff.get('stale_next_priority_reason')}[/]"
            )
            ho_style = "orange3"
        if handoff.get("latest_next_priority_status") == "out_of_order":
            issue = handoff.get("latest_addendum_order_issue") or {}
            effective_task = handoff.get("effective_latest_task_id") or "newer task"
            effective_next = handoff.get("effective_latest_next_priorities") or ""
            priority_alert = (
                f"\n[bold orange3]{SYM_WARN} Out-of-order addendum: "
                f"{issue.get('reason', 'newer addendum appears below first block')}[/]"
                f"\n[bold orange3]Effective latest ({effective_task}): {effective_next}[/]"
            )
            ho_style = "orange3"
        ho_str = (
            f"[bold magenta]Lines:[/] {handoff.get('line_count')}\n"
            f"[bold magenta]Addenda count:[/] {handoff.get('current_addendum_count')} (Last 7d)\n"
            f"[bold magenta]Oldest Addendum:[/] {handoff.get('oldest_addendum')} "
            f"({handoff.get('oldest_age_days')}d old)"
            f"{rot_alert}"
            f"{priority_alert}"
        )
    return Panel(ho_str, title=f"{SYM_HANDOFF} HANDOFF Status", border_style=ho_style, box=box_style)


def _rich_tasks_panel(tasks: dict[str, Any], box_style: Any) -> Any:
    t_str = "[bold red]TASKS Not Available[/]"
    if tasks.get("available"):
        t_str = (
            f"[bold yellow]{SYM_TODO} TODO Tasks:[/] [bold yellow]{tasks.get('todo')}[/]\n\n"
            f"[bold green]{SYM_FLASH} In Progress:[/] [bold green]{tasks.get('in_progress')}[/]"
        )
    return Panel(
        t_str,
        title=f"{SYM_TASKS} TASKS Kanban Summary",
        border_style="rgb(160,80,220)",
        box=box_style,
    )


def _rich_metrics_grid(snap: dict[str, Any], box_style: Any) -> Any:
    metrics_grid = Table.grid(expand=True)
    metrics_grid.add_column(ratio=1)
    metrics_grid.add_column(ratio=1)
    metrics_grid.add_column(ratio=1)
    metrics_grid.add_row(
        _rich_git_panel(snap.get("git", {}), box_style),
        _rich_handoff_panel(snap.get("handoff", {}), box_style),
        _rich_tasks_panel(snap.get("tasks", {}), box_style),
    )
    return metrics_grid


def _rich_commit_table(git_snap: dict[str, Any], box_style: Any) -> Any:
    commit_table = Table(
        title=f"{SYM_COMMIT} Recent 5 Repository Commits",
        expand=True,
        box=box_style,
        border_style="rgb(80,80,180)",
    )
    commit_table.add_column("SHA", style="bold cyan", width=8)
    commit_table.add_column("Author", style="yellow", width=15)
    commit_table.add_column("Subject", style="green", ratio=1)

    if git_snap.get("available") and git_snap.get("recent_commits"):
        for commit in git_snap.get("recent_commits", []):
            commit_table.add_row(commit["sha"], commit["author"], commit["subject"])
    else:
        commit_table.add_row("-", "-", "No recent commits found")
    return commit_table


def _rich_pr_table(pr_snap: dict[str, Any], box_style: Any) -> Any:
    pr_table = Table(
        title=f"{SYM_PR} Open Pull Requests",
        expand=True,
        box=box_style,
        border_style="rgb(80,80,180)",
    )
    pr_table.add_column("No", style="bold yellow", width=6)
    pr_table.add_column("Title", style="white", ratio=1)
    pr_table.add_column("Merge State", style="bold green", width=15)

    if pr_snap.get("available") and pr_snap.get("open"):
        for pull_request in pr_snap.get("open", []):
            state = pull_request.get("mergeStateStatus", "?")
            state_color = "green" if state == "CLEAN" else "red" if state == "BLOCKED" else "yellow"
            pr_table.add_row(f"#{pull_request.get('number')}", pull_request.get("title"), f"[{state_color}]{state}[/]")
    else:
        pr_table.add_row("-", pr_snap.get("reason", "No open PRs found"), "-")
    return pr_table


def _rich_left_flow(snap: dict[str, Any], box_style: Any) -> Any:
    left_flow = Table.grid(expand=True)
    left_flow.add_column(ratio=1)
    left_flow.add_row(_rich_commit_table(snap.get("git", {}), box_style))
    left_flow.add_row("")
    left_flow.add_row(_rich_pr_table(snap.get("pull_requests", {}), box_style))
    return left_flow


def _rich_goal_panel(goal: dict[str, Any], box_style: Any) -> Any:
    if goal.get("available") and goal.get("active"):
        goal_content = (
            f"[bold magenta]Active Goal:[/] {goal.get('goal')}\n"
            f"[bold magenta]Owner:[/] [bold yellow]{goal.get('owner')}[/]\n"
            f"[bold magenta]Started:[/] {goal.get('started')}\n"
            f"[bold magenta]Success Rule:[/] [green]{goal.get('success')}[/]"
        )
        return Panel(goal_content, title=f"{SYM_GOAL} ACTIVE GOAL", border_style="gold1", box=box_style)
    return Panel(
        "[dim white]No active system goals currently registered.[/]",
        title=f"{SYM_GOAL} ACTIVE GOAL",
        border_style="grey50",
        box=box_style,
    )


def _rich_workspace_db_text(db_snap: dict[str, Any]) -> str:
    if not db_snap.get("available"):
        return "[bold red]Database Unavailable[/]"
    missing = db_snap.get("missing_recommended", [])
    missing_str = f" [bold red](missing {len(missing)} indexes!)[/]" if missing else " [bold green](All indexes OK)[/]"
    return f"Tables: {db_snap.get('table_count')}, Indexes: {db_snap.get('index_count')}{missing_str}"


def _rich_graph_text(graph: dict[str, Any]) -> str:
    if not graph.get("available"):
        return "[bold red]Graph Status Unavailable[/]"
    g_str = f"Nodes: {graph.get('nodes')}, Edges: {graph.get('edges')}, Files: {graph.get('files')}"
    if graph.get("freshness") == "stale":
        g_str += f"\n[bold yellow]Stale:[/] {graph.get('stale_reason', 'commit mismatch')}"
    elif graph.get("freshness") == "current":
        g_str += "\n[bold green]Freshness:[/] current HEAD"
    elif graph.get("freshness") == "unknown":
        g_str += f"\n[bold yellow]Freshness unknown:[/] {graph.get('stale_reason', 'missing build commit')}"
    return g_str


def _rich_ci_lines(ci_snap: dict[str, Any]) -> list[str]:
    if not ci_snap.get("available"):
        return [f"[dim red]CI stats unavailable ({ci_snap.get('reason', '?')})[/]"]
    runs = ci_snap.get("recent_runs", [])
    if not runs:
        return ["[dim]No recent runs on this branch[/]"]

    lines = []
    for run in runs[:2]:
        status = run.get("conclusion") or run.get("status") or "?"
        color = (
            "bold green"
            if status in {"success", "completed"}
            else "bold yellow"
            if status == "in_progress"
            else "bold red"
        )
        lines.append(f"* {run.get('name', 'Workflow')}: [{color}]{status}[/]")
    return lines


def _rich_diagnostics_panel(snap: dict[str, Any], box_style: Any) -> Any:
    ci_str = "\n".join(_rich_ci_lines(snap.get("ci", {})))
    diag_str = (
        f"[bold magenta]Workspace DB:[/] {_rich_workspace_db_text(snap.get('workspace_db', {}))}\n\n"
        f"[bold magenta]Review Graph:[/] {_rich_graph_text(snap.get('graph', {}))}\n\n"
        f"[bold magenta]Recent CI runs:[/]\n{ci_str}"
    )
    return Panel(
        diag_str,
        title=f"{SYM_DIAG} System Diagnostics & Graph",
        border_style="rgb(100,100,100)",
        box=box_style,
    )


def _rich_right_flow(snap: dict[str, Any], box_style: Any) -> Any:
    right_flow = Table.grid(expand=True)
    right_flow.add_column(ratio=1)
    right_flow.add_row(_rich_goal_panel(snap.get("goal", {}), box_style))
    right_flow.add_row("")
    right_flow.add_row(_rich_diagnostics_panel(snap, box_style))
    return right_flow


def _rich_center_table(snap: dict[str, Any], box_style: Any) -> Any:
    center_table = Table.grid(expand=True)
    center_table.add_column(ratio=6)
    center_table.add_column(ratio=4)
    center_table.add_row(_rich_left_flow(snap, box_style), _rich_right_flow(snap, box_style))
    return center_table


def render_rich_dashboard(snap: dict[str, Any]) -> None:
    """Rich TUI Dashboard renderer with CP949 compatibility guards."""
    console = Console(safe_box=True)
    box_style = ASCII if IS_WINDOWS else ROUNDED

    console.print(_rich_dashboard_title_panel())
    console.print(_rich_metrics_grid(snap, box_style))
    console.print()
    console.print(_rich_center_table(snap, box_style))
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
