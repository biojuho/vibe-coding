"""Rotate surplus `## DONE` rows from `.ai/TASKS.md` into `.ai/archive/`.

`.ai/TASKS.md` is the shared AI Kanban board. Its `## DONE (Latest N)` section is
meant to hold only the most recently finished tasks, but nothing enforced the
cap: every session appended one more `| T-NNNN | ... | Owner | Date |` row and
the section drifted to hundreds of entries (~626KB / 793 rows observed), so the
session-start board became too large to even open.

This is the same class of bloat that `handoff_rotator.py` fixes for HANDOFF.md.
This script keeps the newest `--keep-count` DONE rows (default 5, matching the
`(Latest 5)` heading) and appends the rest to
`.ai/archive/TASKS_DONE_archive_<rotation_date>.md`. It is scoped strictly to the
`## DONE` section, so the `## TODO`/`## IN_PROGRESS` sections are never touched.

Usage:
    python execution/tasks_done_rotator.py            # keep newest 5
    python execution/tasks_done_rotator.py --check     # dry-run summary
    python execution/tasks_done_rotator.py --check --json
    python execution/tasks_done_rotator.py --keep-count 10
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DONE_HEADING_RE = re.compile(r"^##\s+DONE\b.*$")
DONE_HEADING_COUNT_RE = re.compile(r"^(##\s+DONE\s*\(Latest\s+)(\d+)(\s*\).*)$")
SECTION_RE = re.compile(r"^##\s+")
# A DONE entry can be a shared-board table row or a project-local checklist row.
# Suffixes like `T-1579b` are valid collision-avoidance ids in this workspace.
TABLE_ENTRY_RE = re.compile(r"^\|\s*(T-\d+[A-Za-z]*)\s*\|")
CHECKLIST_ENTRY_RE = re.compile(r"^-\s+\[[xX]\]\s+(T-\d+[A-Za-z]*)\b")


@dataclass(frozen=True)
class DoneEntry:
    index: int  # absolute line index of the row
    task_id: str


@dataclass(frozen=True)
class _PreparedWrite:
    target: Path
    temp: Path


class _WriteFailure(Exception):
    def __init__(self, path: Path, error: OSError) -> None:
        self.path = path
        self.error = error
        super().__init__(f"{path}: {error}")


def find_done_section(lines: list[str]) -> tuple[int, int] | None:
    """Return absolute (start, end) line indices of the DONE section body.

    The range excludes the `## DONE` heading itself and ends at the next `## `
    heading or end-of-file. Returns ``None`` when no DONE heading exists.
    """
    start: int | None = None
    heading_index: int | None = None
    for i, line in enumerate(lines):
        if DONE_HEADING_RE.match(line):
            heading_index = i
            start = i + 1
            break
    if start is None or heading_index is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if SECTION_RE.match(lines[j]):
            end = j
            break
    return start, end


def parse_done_entries(lines: list[str], start: int, end: int) -> list[DoneEntry]:
    """Return DONE entry rows in document order (newest first, top of section)."""
    entries: list[DoneEntry] = []
    for i in range(start, end):
        line = lines[i].rstrip()
        match = TABLE_ENTRY_RE.match(line) or CHECKLIST_ENTRY_RE.match(line)
        if match:
            task_id = match.group(1)
            entries.append(DoneEntry(index=i, task_id=task_id))
    return entries


def _normalize_heading(lines: list[str], keep_count: int) -> None:
    """Keep the `(Latest N)` heading honest by syncing N to ``keep_count``."""
    for i, line in enumerate(lines):
        match = DONE_HEADING_COUNT_RE.match(line)
        if match:
            lines[i] = f"{match.group(1)}{keep_count}{match.group(3)}"
            return
        if line.rstrip() == "## DONE":
            lines[i] = f"## DONE (Latest {keep_count})"
            return


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


def rotate(
    repo_root: Path,
    *,
    keep_count: int,
    today: date,
    dry_run: bool = False,
) -> dict:
    """Rotate surplus DONE rows. Returns a structured result dict.

    Status values:
      - "skip":   TASKS.md missing or no DONE section.
      - "noop":   DONE already holds <= keep_count rows.
      - "rotated": rows beyond the newest keep_count were moved to archive.
    """
    tasks = repo_root / ".ai" / "TASKS.md"
    if not tasks.exists():
        return {"status": "skip", "reason": "TASKS.md not found"}

    text = tasks.read_text(encoding="utf-8")
    lines = text.splitlines()
    rng = find_done_section(lines)
    if rng is None:
        return {"status": "skip", "reason": "DONE heading not found"}

    section_start, section_end = rng
    entries = parse_done_entries(lines, section_start, section_end)
    to_archive = entries[keep_count:]
    to_keep = entries[:keep_count]

    if not to_archive:
        return {
            "status": "noop",
            "kept": len(to_keep),
            "archived": 0,
            "keep_count": keep_count,
        }

    archive_indices = {entry.index for entry in to_archive}
    new_lines = [line for idx, line in enumerate(lines) if idx not in archive_indices]
    _normalize_heading(new_lines, keep_count)
    cleaned = _collapse_blank_runs(new_lines)
    new_text = "\n".join(cleaned).rstrip() + "\n"

    chunks = [lines[entry.index].rstrip() for entry in to_archive]
    archive_block = (
        f"## Rotation {today.isoformat()} "
        f"(archived DONE rows beyond the newest {keep_count})\n\n" + "\n".join(chunks) + "\n"
    )

    archive_dir = repo_root / ".ai" / "archive"
    archive_file = archive_dir / f"TASKS_DONE_archive_{today.isoformat()}.md"

    if not dry_run:
        try:
            if archive_file.exists():
                existing = archive_file.read_text(encoding="utf-8").rstrip()
                archive_text = existing + "\n\n" + archive_block
            else:
                archive_text = archive_block
            prepared = [
                _prepare_text_write(archive_file, archive_text),
                _prepare_text_write(tasks, new_text),
            ]
            _commit_prepared_writes(prepared)
        except _WriteFailure as exc:
            return {
                "status": "write_failed",
                "kept": len(to_keep),
                "archived": len(to_archive),
                "keep_count": keep_count,
                "archive_file": str(archive_file.relative_to(repo_root)).replace("\\", "/"),
                "dry_run": dry_run,
                "write_error": str(exc.error),
                "write_error_path": str(exc.path),
            }

    return {
        "status": "rotated",
        "kept": len(to_keep),
        "archived": len(to_archive),
        "keep_count": keep_count,
        "archive_file": str(archive_file.relative_to(repo_root)).replace("\\", "/"),
        "dry_run": dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rotate surplus .ai/TASKS.md DONE rows into .ai/archive/.",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument(
        "--keep-count",
        type=int,
        default=5,
        help="Keep the newest N DONE rows (default: 5, matching the heading).",
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
        keep_count=args.keep_count,
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
