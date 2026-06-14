"""Rotate stale `.ai/SESSION_LOG.md` entries into `.ai/archive/`.

The shared AI context policy keeps SESSION_LOG.md to recent activity only.
This script removes entries older than a configurable cutoff from both the
current markdown table and the optional detailed `## YYYY-MM-DD - Tool`
sections, then preserves the archived material under
`.ai/archive/SESSION_LOG_before_<cutoff>.md`.

Usage:
    python execution/session_log_rotator.py
    python execution/session_log_rotator.py --check --json
    python execution/session_log_rotator.py --keep-days 14
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
SESSION_LOG_NAME = "SESSION_LOG.md"
TABLE_ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|")
DETAIL_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+-\s+(.+?)\s*$")
SECTION_RE = re.compile(r"^##\s+")


@dataclass(frozen=True)
class TableRow:
    index: int
    date: date
    tool: str
    summary: str
    files: str
    raw: str


@dataclass(frozen=True)
class DetailSection:
    start: int
    end: int
    date: date
    tool: str


@dataclass(frozen=True)
class _PreparedWrite:
    target: Path
    temp: Path


class _WriteFailure(Exception):
    def __init__(self, path: Path, error: OSError) -> None:
        self.path = path
        self.error = error
        super().__init__(f"{path}: {error}")


def parse_table_rows(lines: list[str]) -> list[TableRow]:
    """Return dated rows from the top SESSION_LOG markdown table."""
    rows: list[TableRow] = []
    for index, line in enumerate(lines):
        match = TABLE_ROW_RE.match(line)
        if not match:
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 4:
            continue
        row_date = date.fromisoformat(match.group(1))
        tool = parts[1]
        summary = " | ".join(parts[2:-1])
        files = parts[-1]
        rows.append(
            TableRow(
                index=index,
                date=row_date,
                tool=tool,
                summary=summary,
                files=files,
                raw=line,
            )
        )
    return rows


def parse_detail_sections(lines: list[str]) -> list[DetailSection]:
    """Return dated detailed sections headed by `## YYYY-MM-DD - Tool`."""
    sections: list[DetailSection] = []
    for index, line in enumerate(lines):
        match = DETAIL_HEADING_RE.match(line)
        if not match:
            continue
        end = len(lines)
        for scan in range(index + 1, len(lines)):
            if SECTION_RE.match(lines[scan]):
                end = scan
                break
        sections.append(
            DetailSection(
                start=index,
                end=end,
                date=date.fromisoformat(match.group(1)),
                tool=match.group(2).strip(),
            )
        )
    return sections


def rotate(
    repo_root: Path,
    *,
    keep_days: int,
    today: date,
    dry_run: bool = False,
) -> dict:
    """Rotate stale SESSION_LOG entries and return a structured result."""
    session_log = repo_root / ".ai" / SESSION_LOG_NAME
    if not session_log.exists():
        return {"status": "skip", "reason": "SESSION_LOG.md not found"}

    text = session_log.read_text(encoding="utf-8")
    lines = text.splitlines()
    cutoff = today - timedelta(days=keep_days)

    table_rows = parse_table_rows(lines)
    detail_sections = parse_detail_sections(lines)
    stale_rows = [row for row in table_rows if row.date < cutoff]
    stale_sections = [section for section in detail_sections if section.date < cutoff]

    if not stale_rows and not stale_sections:
        return {
            "status": "noop",
            "kept_table_rows": len(table_rows),
            "archived_table_rows": 0,
            "archived_detail_sections": 0,
            "cutoff": cutoff.isoformat(),
        }

    stale_indices: set[int] = {row.index for row in stale_rows}
    for section in stale_sections:
        stale_indices.update(range(section.start, section.end))
        if section.end < len(lines) and lines[section.end].strip() == "":
            stale_indices.add(section.end)

    new_lines = [line for index, line in enumerate(lines) if index not in stale_indices]
    new_text = "\n".join(_collapse_blank_runs(new_lines)).rstrip() + "\n"

    archive_dir = repo_root / ".ai" / "archive"
    archive_file = archive_dir / f"SESSION_LOG_before_{cutoff.isoformat()}.md"
    archive_text = _render_archive(today, cutoff, lines, stale_rows, stale_sections)

    if not dry_run:
        try:
            if archive_file.exists():
                existing = archive_file.read_text(encoding="utf-8").rstrip()
                archive_text = existing + "\n\n" + archive_text
            prepared = [
                _prepare_text_write(archive_file, archive_text),
                _prepare_text_write(session_log, new_text),
            ]
            _commit_prepared_writes(prepared)
        except _WriteFailure as exc:
            return {
                "status": "write_failed",
                "kept_table_rows": len(table_rows) - len(stale_rows),
                "archived_table_rows": len(stale_rows),
                "archived_detail_sections": len(stale_sections),
                "cutoff": cutoff.isoformat(),
                "archive_file": str(archive_file.relative_to(repo_root)).replace("\\", "/"),
                "dry_run": dry_run,
                "write_error": str(exc.error),
                "write_error_path": str(exc.path),
            }

    return {
        "status": "rotated",
        "kept_table_rows": len(table_rows) - len(stale_rows),
        "archived_table_rows": len(stale_rows),
        "archived_detail_sections": len(stale_sections),
        "cutoff": cutoff.isoformat(),
        "archive_file": str(archive_file.relative_to(repo_root)).replace("\\", "/"),
        "dry_run": dry_run,
    }


def _render_archive(
    today: date,
    cutoff: date,
    lines: list[str],
    stale_rows: list[TableRow],
    stale_sections: list[DetailSection],
) -> str:
    rendered: list[str] = [
        f"# SESSION_LOG Archive before {cutoff.isoformat()}",
        "",
        f"Rotated on {today.isoformat()}.",
        "",
    ]
    if stale_rows:
        rendered.append("## Table Entries")
        rendered.append("")
        for row in stale_rows:
            rendered.append(f"## {row.date.isoformat()} | {row.tool} | Session log row")
            rendered.append("")
            rendered.append(row.summary)
            if row.files:
                rendered.append("")
                rendered.append(f"Changed Files: {row.files}")
            rendered.append("")

    if stale_sections:
        rendered.append("## Detailed Sections")
        rendered.append("")
        for section in stale_sections:
            rendered.extend(lines[section.start : section.end])
            rendered.append("")

    return "\n".join(rendered).rstrip() + "\n"


def _collapse_blank_runs(lines: list[str]) -> list[str]:
    """Collapse runs of 3+ consecutive blank lines down to 2."""
    out: list[str] = []
    blank = 0
    for line in lines:
        if line.strip() == "":
            blank += 1
            if blank <= 2:
                out.append(line)
        else:
            blank = 0
            out.append(line)
    return out


def _prepare_text_write(path: Path, text: str) -> _PreparedWrite:
    tmp = path.with_name(f"{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if tmp.exists() or tmp.is_symlink():
            if tmp.is_dir() and not tmp.is_symlink():
                raise IsADirectoryError(f"temporary output path is a directory: {tmp}")
            tmp.unlink()
        tmp.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise _WriteFailure(tmp, exc) from exc
    return _PreparedWrite(target=path, temp=tmp)


def _commit_prepared_writes(prepared: list[_PreparedWrite]) -> None:
    replaced: list[_PreparedWrite] = []
    try:
        for item in prepared:
            item.temp.replace(item.target)
            replaced.append(item)
    except OSError as exc:
        path = item.target if "item" in locals() else prepared[0].target
        raise _WriteFailure(path, exc) from exc
    finally:
        for item in prepared:
            if item not in replaced:
                try:
                    if item.temp.exists() or item.temp.is_symlink():
                        item.temp.unlink()
                except OSError:
                    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rotate stale .ai/SESSION_LOG.md entries into .ai/archive/.",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        help="Keep entries dated within the last N days (default: 7).",
    )
    parser.add_argument(
        "--today",
        type=str,
        default=None,
        help="Override today's date (YYYY-MM-DD). Useful for testing.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: report what would be rotated without writing files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the result as JSON instead of a Python repr.",
    )
    args = parser.parse_args(argv)

    today = date.fromisoformat(args.today) if args.today else date.today()
    result = rotate(
        args.repo_root,
        keep_days=args.keep_days,
        today=today,
        dry_run=args.check,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result)
    if result.get("status") == "write_failed":
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
