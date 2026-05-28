"""Unit tests for `execution/next_task_id.py`.

These don't touch the real `.ai/` or `git` state — they verify the pure
core (`suggest_next_id`'s ID collision logic) by monkeypatching the
collectors.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "execution") not in sys.path:
    sys.path.insert(0, str(ROOT / "execution"))

import next_task_id  # noqa: E402


def _patch_id_sources(monkeypatch, *, md=None, handoff=None, git=None):
    monkeypatch.setattr(
        next_task_id, "_ids_in_file", lambda path: set(md if path.name == "TASKS.md" else (handoff or []))
    )
    monkeypatch.setattr(next_task_id, "_ids_in_git_log", lambda window: set(git or []))


def test_suggests_max_plus_one_when_no_collision(monkeypatch):
    _patch_id_sources(monkeypatch, md=[1000, 1001, 1002], handoff=[1002], git=[])
    result = next_task_id.suggest_next_id()
    assert result["suggested_id"] == "T-1003"
    assert result["base"] == 1002
    assert result["step"] == 1


def test_uses_git_log_max_when_higher_than_tasks_md(monkeypatch):
    # TASKS.md max is 1100, but git log shows T-1101 was already used in a
    # commit (collision-in-flight from another tool). base is max-of-all-
    # sources = 1101 so suggestion is T-1102.
    _patch_id_sources(monkeypatch, md=[1100], handoff=[], git=[1101])
    result = next_task_id.suggest_next_id()
    assert result["suggested_id"] == "T-1102"
    assert result["base"] == 1101


def test_uses_handoff_max_when_higher(monkeypatch):
    # HANDOFF.md sometimes mentions an in-flight ID before TASKS.md does.
    _patch_id_sources(monkeypatch, md=[1100], handoff=[1103], git=[1102])
    result = next_task_id.suggest_next_id()
    assert result["suggested_id"] == "T-1104"
    assert result["base"] == 1103


def test_returns_base_1000_when_no_ids_anywhere(monkeypatch):
    # Fresh repo with no T-#### references — fall back to 1001 (max=1000 default).
    _patch_id_sources(monkeypatch, md=[], handoff=[], git=[])
    result = next_task_id.suggest_next_id()
    assert result["suggested_id"] == "T-1001"


def test_skips_intermediate_collisions_when_gap_exists(monkeypatch):
    # All sources have a contiguous block 1100..1104 but TASKS.md has been
    # truncated and only 1100 is visible there. git+handoff fill in the gap.
    # base is max-of-all = 1104, suggestion is T-1105.
    _patch_id_sources(
        monkeypatch,
        md=[1100],
        handoff=[1101, 1102],
        git=[1103, 1104],
    )
    result = next_task_id.suggest_next_id()
    assert result["suggested_id"] == "T-1105"
    assert result["base"] == 1104
