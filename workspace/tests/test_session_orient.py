"""Unit tests for `execution/session_orient.py`."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "execution" / "session_orient.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("session_orient", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["session_orient"] = module
    spec.loader.exec_module(module)
    return module


orient = _load_module()


# ----- handoff_snapshot ------------------------------------------------------


def _write_handoff(tmp_path: Path, dates: list[str], extra_sections: str = "") -> None:
    """Build a HANDOFF.md with the listed addendum dates."""
    ai = tmp_path / ".ai"
    ai.mkdir(parents=True, exist_ok=True)
    blocks = []
    for d in dates:
        blocks.append(
            "| Field | Value |\n"
            "|---|---|\n"
            f"| Date | {d} |\n"
            "| Tool | Test |\n"
            "| Work | sample |\n"
            "| Next Priorities | none |\n"
        )
    body = "# HANDOFF - AI Context Relay\n\n## Current Addendum\n\n" + "\n".join(blocks) + extra_sections
    (ai / "HANDOFF.md").write_text(body, encoding="utf-8")


def test_handoff_snapshot_counts_addenda(tmp_path):
    _write_handoff(tmp_path, ["2026-05-08", "2026-05-01", "2026-04-15"])
    snap = orient.handoff_snapshot(tmp_path, today=date(2026, 5, 12))
    assert snap["available"] is True
    assert snap["current_addendum_count"] == 3
    assert snap["oldest_addendum"] == "2026-04-15"
    assert snap["newest_addendum"] == "2026-05-08"
    assert snap["oldest_age_days"] == 27
    assert snap["rotation_suggested"] is True


def test_handoff_snapshot_no_rotation_when_fresh(tmp_path):
    _write_handoff(tmp_path, ["2026-05-12"])
    snap = orient.handoff_snapshot(tmp_path, today=date(2026, 5, 12))
    assert snap["rotation_suggested"] is False


def test_handoff_snapshot_stops_at_next_section(tmp_path):
    """Addenda inside `## Latest Update` or later must not be counted."""
    _write_handoff(
        tmp_path,
        ["2026-05-12"],
        extra_sections="\n## Latest Update\n\n| Field | Value |\n|---|---|\n| Date | 2024-01-01 |\n| Tool | Old |\n| Work | x |\n| Next Priorities | y |\n",
    )
    snap = orient.handoff_snapshot(tmp_path, today=date(2026, 5, 12))
    assert snap["current_addendum_count"] == 1
    assert snap["oldest_addendum"] == "2026-05-12"


def test_handoff_snapshot_missing_file(tmp_path):
    snap = orient.handoff_snapshot(tmp_path, today=date(2026, 5, 12))
    assert snap["available"] is False
    assert "not found" in snap["reason"]


# ----- tasks_snapshot --------------------------------------------------------


def test_tasks_snapshot_counts_rows(tmp_path):
    ai = tmp_path / ".ai"
    ai.mkdir(parents=True)
    (ai / "TASKS.md").write_text(
        "# TASKS\n\n"
        "## TODO\n\n"
        "| ID | Task | Owner | Priority | Auto | Created |\n"
        "|---|---|---|---|---|---|\n"
        "| T-1 | first | u | high | safe | today |\n"
        "| T-2 | second | u | low | safe | today |\n\n"
        "## IN_PROGRESS\n\n"
        "| ID | Task | Owner | Started | Notes |\n"
        "|---|---|---|---|---|\n"
        "| T-3 | active | u | today | none |\n\n"
        "## DONE\n\n"
        "| T-9 | finished | u | yesterday |\n",
        encoding="utf-8",
    )
    snap = orient.tasks_snapshot(tmp_path)
    assert snap["available"] is True
    assert snap["todo"] == 2
    assert snap["in_progress"] == 1


def test_tasks_snapshot_missing_file(tmp_path):
    snap = orient.tasks_snapshot(tmp_path)
    assert snap["available"] is False


# ----- goal_snapshot ---------------------------------------------------------


def test_goal_snapshot_reads_active_goal(tmp_path):
    ai = tmp_path / ".ai"
    ai.mkdir(parents=True)
    (ai / "GOAL.md").write_text(
        "# GOAL\n\n"
        "## Active Goal\n\n"
        "- Status: active\n"
        "- Goal: Keep the current goal visible.\n"
        "- Owner: Codex\n"
        "- Started: 2026-05-12\n"
        "- Success: Session orientation shows it.\n",
        encoding="utf-8",
    )
    snap = orient.goal_snapshot(tmp_path)
    assert snap["available"] is True
    assert snap["active"] is True
    assert snap["goal"] == "Keep the current goal visible."
    assert snap["owner"] == "Codex"


def test_goal_snapshot_missing_file(tmp_path):
    snap = orient.goal_snapshot(tmp_path)
    assert snap["available"] is False
    assert "not found" in snap["reason"]


# ----- render helpers --------------------------------------------------------


def test_git_helpers_parse_and_render_status():
    counts = orient._worktree_counts(" M modified.py\nA  staged.py\n?? new.py\nUU conflict.py\n")
    assert counts == {
        "staged": 1,
        "modified": 1,
        "untracked": 1,
        "unmerged": 1,
        "clean": False,
    }
    assert orient._format_worktree(counts) == "staged=1 modified=1 untracked=1 unmerged=1"

    commits = orient._parse_recent_commits("abc123\tCodex\trefactor helpers\nbad line\n")
    assert commits == [{"sha": "abc123", "author": "Codex", "subject": "refactor helpers"}]

    lines = orient._render_git_section(
        {
            "available": True,
            "branch": "main",
            "ahead": 1,
            "behind": 0,
            "stash_count": 2,
            "worktree": counts,
            "recent_commits": commits,
        }
    )
    assert lines[0] == "  git: main (ahead 1 / behind 0), stash 2, worktree staged=1 modified=1 untracked=1 unmerged=1"
    assert lines[1] == "    abc123 Codex                refactor helpers"


def test_render_section_helpers_cover_available_and_unavailable_states():
    assert orient._render_pr_section({"available": False, "reason": "no gh"}) == ["  PRs: unavailable (no gh)"]
    assert orient._render_handoff_section({"available": False, "reason": "missing"}) == [
        "  HANDOFF: unavailable (missing)"
    ]
    assert orient._render_tasks_section({"available": True, "todo": 2, "in_progress": 1}) == [
        "  TASKS: TODO=2, IN_PROGRESS=1"
    ]
    assert orient._render_goal_section({"available": True, "active": False, "status": "inactive"}) == [
        "  GOAL: inactive"
    ]
    assert orient._render_workspace_db_section({"available": True, "table_count": 1, "index_count": 2}) == [
        "  workspace.db: 1 tables, 2 indexes"
    ]
    assert orient._render_graph_section(
        {"available": True, "nodes": "1", "edges": "2", "files": "3", "last_updated": "now"}
    ) == ["  code-review-graph: nodes=1, edges=2, files=3, updated now"]
    assert orient._render_ci_section({"available": True, "recent_runs": []}) == ["  CI: no recent runs"]


# ----- workspace_db_snapshot ------------------------------------------------


def test_workspace_db_snapshot_reuses_audit(tmp_path, monkeypatch):
    """Should run the audit module if present; degrade gracefully otherwise."""
    # Without the audit script available the snapshot should fail gracefully.
    snap = orient.workspace_db_snapshot(tmp_path)
    assert snap["available"] is False
    assert "not found" in snap["reason"]


# ----- collect_snapshot integration -----------------------------------------


def test_collect_snapshot_smoke(tmp_path, monkeypatch):
    """Smoke test the full collector — every section must return a dict."""
    snap = orient.collect_snapshot(tmp_path)
    assert isinstance(snap, dict)
    for key in (
        "repo_root",
        "git",
        "pull_requests",
        "handoff",
        "tasks",
        "goal",
        "workspace_db",
        "graph",
        "ci",
    ):
        assert key in snap, f"missing section: {key}"
    # Every check returns a dict with an `available` boolean (except `repo_root`).
    for key in (
        "git",
        "pull_requests",
        "handoff",
        "tasks",
        "goal",
        "workspace_db",
        "graph",
        "ci",
    ):
        assert "available" in snap[key]


def test_render_text_includes_each_section(tmp_path):
    snap = orient.collect_snapshot(tmp_path)
    text = orient.render_text(snap)
    for marker in ("git", "PRs", "HANDOFF", "TASKS", "GOAL", "workspace.db", "code-review-graph", "CI"):
        assert marker in text, f"render_text missing section marker: {marker}"


def test_render_text_includes_active_goal():
    text = orient.render_text(
        {
            "git": {"available": False},
            "pull_requests": {"available": False, "reason": "x"},
            "handoff": {"available": False, "reason": "x"},
            "tasks": {"available": True, "todo": 0, "in_progress": 0},
            "goal": {
                "available": True,
                "active": True,
                "goal": "Keep focus.",
                "owner": "Codex",
                "status": "active",
            },
            "workspace_db": {"available": False, "reason": "x"},
            "graph": {"available": False, "reason": "x"},
            "ci": {"available": False, "reason": "x"},
        }
    )
    assert "GOAL: active (Codex) - Keep focus." in text


# ----- git_snapshot (uses real git but tmp_path has no .git) ----------------


def test_git_snapshot_returns_unavailable_outside_git(tmp_path):
    snap = orient.git_snapshot(tmp_path)
    assert snap["available"] is False


# ----- _run helper -----------------------------------------------------------


def test_run_handles_missing_binary(tmp_path):
    rc, out = orient._run(["this-binary-does-not-exist-12345"], tmp_path, timeout=2.0)
    assert rc == 1
    assert out == ""
