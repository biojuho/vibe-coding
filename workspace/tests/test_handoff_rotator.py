"""Unit tests for `execution/handoff_rotator.py`."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROTATOR_PATH = REPO_ROOT / "execution" / "handoff_rotator.py"


def _load_rotator():
    spec = importlib.util.spec_from_file_location("handoff_rotator", ROTATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["handoff_rotator"] = module
    spec.loader.exec_module(module)
    return module


rotator = _load_rotator()


def _build_addendum(d: str, work: str = "Sample work entry.") -> str:
    return (
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Date | {d} |\n"
        "| Tool | TestTool |\n"
        f"| Work | {work} |\n"
        "| Next Priorities | None. |\n"
    )


def _write_handoff(tmp_path: Path, addenda: list[str], suffix: str = "") -> Path:
    handoff = tmp_path / ".ai" / "HANDOFF.md"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# HANDOFF - AI Context Relay\n"
        "\n"
        "## Current Addendum\n"
        "\n" + "\n".join(addenda) + ("\n" + suffix if suffix else "")
    )
    handoff.write_text(body, encoding="utf-8")
    return handoff


def test_parse_three_addenda(tmp_path):
    handoff = _write_handoff(
        tmp_path,
        [
            _build_addendum("2026-05-08", "today"),
            _build_addendum("2026-05-01", "boundary"),
            _build_addendum("2026-04-15", "old"),
        ],
    )
    lines = handoff.read_text(encoding="utf-8").splitlines()
    rng = rotator.find_current_addendum_range(lines)
    assert rng is not None
    addenda = rotator.parse_addenda(lines, *rng)
    assert [a.date for a in addenda] == [
        date(2026, 5, 8),
        date(2026, 5, 1),
        date(2026, 4, 15),
    ]


def test_rotate_archives_old_addenda(tmp_path):
    _write_handoff(
        tmp_path,
        [
            _build_addendum("2026-05-08", "keep recent"),
            _build_addendum("2026-05-01", "keep boundary"),
            _build_addendum("2026-04-30", "archive day-before"),
            _build_addendum("2026-04-15", "archive ancient"),
        ],
    )
    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    assert result["status"] == "rotated"
    assert result["archived"] == 2
    assert result["kept"] == 2
    assert result["cutoff"] == "2026-05-01"

    handoff_text = (tmp_path / ".ai" / "HANDOFF.md").read_text(encoding="utf-8")
    assert "keep recent" in handoff_text
    assert "keep boundary" in handoff_text
    assert "archive day-before" not in handoff_text
    assert "archive ancient" not in handoff_text

    archive_text = (tmp_path / ".ai" / "archive" / "HANDOFF_archive_2026-05-08.md").read_text(encoding="utf-8")
    assert "archive day-before" in archive_text
    assert "archive ancient" in archive_text
    assert "Rotation 2026-05-08" in archive_text


def test_rotate_is_idempotent(tmp_path):
    _write_handoff(
        tmp_path,
        [
            _build_addendum("2026-05-08", "recent"),
            _build_addendum("2026-04-15", "old"),
        ],
    )
    first = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    assert first["status"] == "rotated"
    second = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    assert second["status"] == "noop"
    assert second["kept"] == 1
    assert second["archived"] == 0


def test_rotate_noop_when_all_recent(tmp_path):
    _write_handoff(
        tmp_path,
        [
            _build_addendum("2026-05-08", "today"),
            _build_addendum("2026-05-02", "still in window"),
        ],
    )
    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    assert result["status"] == "noop"
    assert result["archived"] == 0


def test_rotate_skip_when_handoff_missing(tmp_path):
    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    assert result["status"] == "skip"


def test_rotate_skip_when_no_current_addendum(tmp_path):
    handoff = tmp_path / ".ai" / "HANDOFF.md"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text("# HANDOFF\n\n## Notes\n\nnothing here\n", encoding="utf-8")
    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    assert result["status"] == "skip"


def test_rotate_dry_run_does_not_write(tmp_path):
    _write_handoff(
        tmp_path,
        [
            _build_addendum("2026-05-08", "keep"),
            _build_addendum("2026-04-15", "would-archive"),
        ],
    )
    original = (tmp_path / ".ai" / "HANDOFF.md").read_text(encoding="utf-8")
    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8), dry_run=True)
    assert result["status"] == "rotated"
    assert result["dry_run"] is True
    assert (tmp_path / ".ai" / "HANDOFF.md").read_text(encoding="utf-8") == original
    assert not (tmp_path / ".ai" / "archive" / "HANDOFF_archive_2026-05-08.md").exists()


def test_rotate_preserves_sections_after_current_addendum(tmp_path):
    addenda = [
        _build_addendum("2026-05-08", "keep"),
        _build_addendum("2026-04-01", "drop"),
    ]
    suffix = "\n## Notes\n\n- preserved note\n"
    _write_handoff(tmp_path, addenda, suffix=suffix)
    rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    text = (tmp_path / ".ai" / "HANDOFF.md").read_text(encoding="utf-8")
    assert "## Notes" in text
    assert "- preserved note" in text
    assert "drop" not in text


def test_rotate_appends_to_existing_archive(tmp_path):
    _write_handoff(
        tmp_path,
        [
            _build_addendum("2026-05-08", "keep"),
            _build_addendum("2026-04-15", "first archive"),
        ],
    )
    rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    # Add another stale addendum and rotate again on the same day.
    handoff = tmp_path / ".ai" / "HANDOFF.md"
    new_text = handoff.read_text(encoding="utf-8") + "\n" + _build_addendum("2026-04-10", "second archive")
    handoff.write_text(new_text, encoding="utf-8")

    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    assert result["status"] == "rotated"

    archive_text = (tmp_path / ".ai" / "archive" / "HANDOFF_archive_2026-05-08.md").read_text(encoding="utf-8")
    assert "first archive" in archive_text
    assert "second archive" in archive_text


@pytest.mark.parametrize("keep_days,expected_archived", [(0, 3), (7, 2), (60, 0)])
def test_keep_days_parameter(tmp_path, keep_days, expected_archived):
    _write_handoff(
        tmp_path,
        [
            _build_addendum("2026-05-08"),
            _build_addendum("2026-05-02"),
            _build_addendum("2026-04-30"),
            _build_addendum("2026-04-15"),
        ],
    )
    result = rotator.rotate(
        tmp_path,
        keep_days=keep_days,
        today=date(2026, 5, 8),
    )
    if expected_archived == 0:
        assert result["status"] == "noop"
        assert result["archived"] == 0
    else:
        assert result["status"] == "rotated"
        assert result["archived"] == expected_archived
