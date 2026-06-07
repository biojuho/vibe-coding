"""Unit tests for `execution/tasks_done_rotator.py`."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROTATOR_PATH = REPO_ROOT / "execution" / "tasks_done_rotator.py"


def _load_rotator():
    spec = importlib.util.spec_from_file_location("tasks_done_rotator", ROTATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["tasks_done_rotator"] = module
    spec.loader.exec_module(module)
    return module


rotator = _load_rotator()


def _done_row(task_id: str, note: str = "done note") -> str:
    return f"| {task_id} | {note} | Codex | 2026-06-07 |"


def _write_tasks(
    tmp_path: Path,
    done_rows: list[str],
    *,
    todo_rows: list[str] | None = None,
    done_label: int = 5,
) -> Path:
    tasks = tmp_path / ".ai" / "TASKS.md"
    tasks.parent.mkdir(parents=True, exist_ok=True)
    todo_block = ("\n".join(todo_rows) + "\n\n") if todo_rows else ""
    body = (
        "# TASKS - AI Kanban Board\n\n"
        "## TODO\n\n"
        f"{todo_block}"
        "## IN_PROGRESS\n\n"
        "| ID | Task | Owner | Started | Notes |\n"
        "|---|---|---|---|---|\n\n"
        f"## DONE (Latest {done_label})\n\n" + "\n".join(done_rows) + "\n"
    )
    tasks.write_text(body, encoding="utf-8")
    return tasks


def test_parse_done_entries_are_scoped_to_done():
    tmp_lines = (
        "# TASKS\n\n## TODO\n\n| T-900 | todo row | x | y |\n\n"
        "## DONE (Latest 5)\n\n" + _done_row("T-100") + "\n" + _done_row("T-099") + "\n"
    ).splitlines()
    rng = rotator.find_done_section(tmp_lines)
    assert rng is not None
    entries = rotator.parse_done_entries(tmp_lines, *rng)
    assert [e.task_id for e in entries] == ["T-100", "T-099"]


def test_rotate_keeps_newest_n(tmp_path):
    rows = [_done_row(f"T-{100 + i}", f"entry-{i}") for i in range(8)]
    tasks = _write_tasks(tmp_path, rows)
    result = rotator.rotate(tmp_path, keep_count=5, today=date(2026, 6, 7))
    assert result["status"] == "rotated"
    assert result["kept"] == 5
    assert result["archived"] == 3

    text = tasks.read_text(encoding="utf-8")
    assert "entry-0" in text  # newest kept
    assert "entry-4" in text  # fifth-newest kept
    assert "entry-5" not in text  # archived
    assert "entry-7" not in text

    archive = (tmp_path / ".ai" / "archive" / "TASKS_DONE_archive_2026-06-07.md").read_text(encoding="utf-8")
    assert "entry-7" in archive
    assert "Rotation 2026-06-07" in archive


def test_rotate_normalizes_latest_heading(tmp_path):
    rows = [_done_row(f"T-{100 + i}") for i in range(8)]
    tasks = _write_tasks(tmp_path, rows, done_label=5)
    rotator.rotate(tmp_path, keep_count=3, today=date(2026, 6, 7))
    text = tasks.read_text(encoding="utf-8")
    assert "## DONE (Latest 3)" in text
    assert "(Latest 5)" not in text


def test_rotate_does_not_touch_todo_or_in_progress(tmp_path):
    rows = [_done_row(f"T-{100 + i}", f"entry-{i}") for i in range(8)]
    tasks = _write_tasks(
        tmp_path,
        rows,
        todo_rows=["> Latest note: T-901 keep me", "| T-902 | survive | x | y |"],
    )
    rotator.rotate(tmp_path, keep_count=5, today=date(2026, 6, 7))
    text = tasks.read_text(encoding="utf-8")
    assert "T-901 keep me" in text
    assert "survive" in text  # a table row in TODO must not be archived
    assert "## IN_PROGRESS" in text


def test_rotate_noop_when_under_cap(tmp_path):
    rows = [_done_row(f"T-{100 + i}") for i in range(3)]
    _write_tasks(tmp_path, rows)
    result = rotator.rotate(tmp_path, keep_count=5, today=date(2026, 6, 7))
    assert result["status"] == "noop"
    assert result["archived"] == 0
    assert result["kept"] == 3


def test_rotate_is_idempotent(tmp_path):
    rows = [_done_row(f"T-{100 + i}") for i in range(8)]
    _write_tasks(tmp_path, rows)
    first = rotator.rotate(tmp_path, keep_count=5, today=date(2026, 6, 7))
    assert first["status"] == "rotated"
    second = rotator.rotate(tmp_path, keep_count=5, today=date(2026, 6, 7))
    assert second["status"] == "noop"
    assert second["archived"] == 0


def test_rotate_dry_run_does_not_write(tmp_path):
    rows = [_done_row(f"T-{100 + i}") for i in range(8)]
    tasks = _write_tasks(tmp_path, rows)
    original = tasks.read_text(encoding="utf-8")
    result = rotator.rotate(tmp_path, keep_count=5, today=date(2026, 6, 7), dry_run=True)
    assert result["status"] == "rotated"
    assert result["dry_run"] is True
    assert tasks.read_text(encoding="utf-8") == original
    assert not (tmp_path / ".ai" / "archive" / "TASKS_DONE_archive_2026-06-07.md").exists()


def test_rotate_skip_when_tasks_missing(tmp_path):
    result = rotator.rotate(tmp_path, keep_count=5, today=date(2026, 6, 7))
    assert result["status"] == "skip"


def test_rotate_skip_when_no_done_section(tmp_path):
    tasks = tmp_path / ".ai" / "TASKS.md"
    tasks.parent.mkdir(parents=True, exist_ok=True)
    tasks.write_text("# TASKS\n\n## TODO\n\n- nothing done yet\n", encoding="utf-8")
    result = rotator.rotate(tmp_path, keep_count=5, today=date(2026, 6, 7))
    assert result["status"] == "skip"
