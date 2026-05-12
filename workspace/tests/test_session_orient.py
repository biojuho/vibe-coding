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
        "workspace_db",
        "graph",
        "ci",
    ):
        assert "available" in snap[key]


def test_render_text_includes_each_section(tmp_path):
    snap = orient.collect_snapshot(tmp_path)
    text = orient.render_text(snap)
    for marker in ("git", "PRs", "HANDOFF", "TASKS", "workspace.db", "code-review-graph", "CI"):
        assert marker in text, f"render_text missing section marker: {marker}"


# ----- git_snapshot (uses real git but tmp_path has no .git) ----------------


def test_git_snapshot_returns_unavailable_outside_git(tmp_path):
    snap = orient.git_snapshot(tmp_path)
    assert snap["available"] is False


# ----- _run helper -----------------------------------------------------------


def test_run_handles_missing_binary(tmp_path):
    rc, out = orient._run(["this-binary-does-not-exist-12345"], tmp_path, timeout=2.0)
    assert rc == 1
    assert out == ""
