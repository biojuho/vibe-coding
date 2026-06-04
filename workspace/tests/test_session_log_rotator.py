"""Unit tests for `execution/session_log_rotator.py`."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROTATOR_PATH = REPO_ROOT / "execution" / "session_log_rotator.py"


def _load_rotator():
    spec = importlib.util.spec_from_file_location("session_log_rotator", ROTATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["session_log_rotator"] = module
    spec.loader.exec_module(module)
    return module


rotator = _load_rotator()


def _row(d: str, tool: str = "TestTool", summary: str = "summary", files: str = "`a.py`") -> str:
    return f"| {d} | {tool} | {summary} | {files} |\n"


def _section(d: str, tool: str = "TestTool", body: str = "- details") -> str:
    return f"## {d} - {tool}\n\n{body}\n"


def _write_session_log(tmp_path: Path, rows: list[str], sections: list[str] | None = None) -> Path:
    session_log = tmp_path / ".ai" / "SESSION_LOG.md"
    session_log.parent.mkdir(parents=True, exist_ok=True)
    body = "# SESSION_LOG\n\n| Date | Tool | Summary | Changed Files |\n|---|---|---|---|\n" + "".join(rows)
    if sections:
        body += "\n" + "\n".join(sections)
    session_log.write_text(body, encoding="utf-8")
    return session_log


def test_parse_table_rows_and_detail_sections(tmp_path):
    session_log = _write_session_log(
        tmp_path,
        [_row("2026-05-08", "Codex"), _row("2026-05-01", "Gemini")],
        [_section("2026-05-08", "Codex"), _section("2026-05-01", "Gemini")],
    )
    lines = session_log.read_text(encoding="utf-8").splitlines()

    rows = rotator.parse_table_rows(lines)
    sections = rotator.parse_detail_sections(lines)

    assert [row.date for row in rows] == [date(2026, 5, 8), date(2026, 5, 1)]
    assert [section.date for section in sections] == [date(2026, 5, 8), date(2026, 5, 1)]


def test_rotate_archives_old_rows_and_sections(tmp_path):
    _write_session_log(
        tmp_path,
        [
            _row("2026-05-08", summary="keep recent"),
            _row("2026-05-01", summary="keep boundary"),
            _row("2026-04-30", summary="archive old row"),
        ],
        [
            _section("2026-05-08", body="- keep detail"),
            _section("2026-04-30", body="- archive detail"),
        ],
    )

    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))

    assert result["status"] == "rotated"
    assert result["archived_table_rows"] == 1
    assert result["archived_detail_sections"] == 1
    assert result["kept_table_rows"] == 2
    assert result["cutoff"] == "2026-05-01"

    current_text = (tmp_path / ".ai" / "SESSION_LOG.md").read_text(encoding="utf-8")
    assert "keep recent" in current_text
    assert "keep boundary" in current_text
    assert "archive old row" not in current_text
    assert "- archive detail" not in current_text

    archive_text = (tmp_path / ".ai" / "archive" / "SESSION_LOG_before_2026-05-01.md").read_text(encoding="utf-8")
    assert "## 2026-04-30 | TestTool | Session log row" in archive_text
    assert "archive old row" in archive_text
    assert "- archive detail" in archive_text


def test_rotate_is_idempotent(tmp_path):
    _write_session_log(
        tmp_path,
        [_row("2026-05-08", summary="recent"), _row("2026-04-15", summary="old")],
    )

    first = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))
    second = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))

    assert first["status"] == "rotated"
    assert second["status"] == "noop"
    assert second["archived_table_rows"] == 0


def test_rotate_noop_when_all_recent(tmp_path):
    _write_session_log(
        tmp_path,
        [_row("2026-05-08", summary="today"), _row("2026-05-02", summary="still recent")],
    )

    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))

    assert result["status"] == "noop"
    assert result["kept_table_rows"] == 2


def test_rotate_skip_when_session_log_missing(tmp_path):
    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))

    assert result["status"] == "skip"


def test_rotate_dry_run_does_not_write(tmp_path):
    _write_session_log(
        tmp_path,
        [_row("2026-05-08", summary="keep"), _row("2026-04-15", summary="would archive")],
    )
    session_log = tmp_path / ".ai" / "SESSION_LOG.md"
    original = session_log.read_text(encoding="utf-8")

    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8), dry_run=True)

    assert result["status"] == "rotated"
    assert result["dry_run"] is True
    assert session_log.read_text(encoding="utf-8") == original
    assert not (tmp_path / ".ai" / "archive" / "SESSION_LOG_before_2026-05-01.md").exists()


def test_rotate_appends_to_existing_archive(tmp_path):
    _write_session_log(
        tmp_path,
        [_row("2026-05-08", summary="keep"), _row("2026-04-15", summary="first archive")],
    )
    rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))

    session_log = tmp_path / ".ai" / "SESSION_LOG.md"
    session_log.write_text(
        session_log.read_text(encoding="utf-8") + _row("2026-04-10", summary="second archive"),
        encoding="utf-8",
    )

    result = rotator.rotate(tmp_path, keep_days=7, today=date(2026, 5, 8))

    assert result["status"] == "rotated"
    archive_text = (tmp_path / ".ai" / "archive" / "SESSION_LOG_before_2026-05-01.md").read_text(encoding="utf-8")
    assert "first archive" in archive_text
    assert "second archive" in archive_text


@pytest.mark.parametrize("keep_days,expected_archived", [(0, 3), (7, 2), (60, 0)])
def test_keep_days_parameter(tmp_path, keep_days, expected_archived):
    _write_session_log(
        tmp_path,
        [
            _row("2026-05-08"),
            _row("2026-05-02"),
            _row("2026-04-30"),
            _row("2026-04-15"),
        ],
    )

    result = rotator.rotate(tmp_path, keep_days=keep_days, today=date(2026, 5, 8))

    if expected_archived == 0:
        assert result["status"] == "noop"
    else:
        assert result["status"] == "rotated"
        assert result["archived_table_rows"] == expected_archived
