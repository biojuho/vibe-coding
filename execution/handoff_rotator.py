"""Rotate stale 'Current Addendum' entries from `.ai/HANDOFF.md` into `.ai/archive/`.

The shared AI context policy (`CLAUDE.md`) keeps `.ai/SESSION_LOG.md` to the last
seven days of activity, but `.ai/HANDOFF.md` had no equivalent rotation. As a
result the "Current Addendum" stack drifted to ~280 lines, half of it older than
two weeks. This script reads each addendum block, splits them by date against a
configurable cutoff, rewrites HANDOFF.md with only the recent ones, and appends
the archived blocks to `.ai/archive/HANDOFF_archive_<rotation_date>.md`.

Usage:
    python execution/handoff_rotator.py            # rotate using --keep-days=7
    python execution/handoff_rotator.py --check    # dry-run summary
    python execution/handoff_rotator.py --keep-days 14
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
CURRENT_ADDENDUM_HEADING = "## Current Addendum"
DATE_RE = re.compile(r"^\|\s*Date\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*$")
HEADER_RE = re.compile(r"^\|\s*Field\s*\|\s*Value\s*\|\s*$")
SEPARATOR_RE = re.compile(r"^\|[\s\-:|]+\|\s*$")
SECTION_RE = re.compile(r"^##\s+")


@dataclass(frozen=True)
class Addendum:
    start: int  # absolute line index, inclusive
    end: int  # absolute line index, exclusive
    date: date


def find_current_addendum_range(lines: list[str]) -> tuple[int, int] | None:
    """Return absolute (start, end) line indices of the Current Addendum body.

    The returned range excludes the `## Current Addendum` heading itself and
    ends at the next `## ` heading or end-of-file.
    """
    start: int | None = None
    for i, line in enumerate(lines):
        if line.rstrip() == CURRENT_ADDENDUM_HEADING:
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if SECTION_RE.match(lines[j]):
            end = j
            break
    return start, end


def parse_addenda(lines: list[str], start: int, end: int) -> list[Addendum]:
    """Walk the Current Addendum body and return one Addendum per `| Date |` row.

    Each addendum spans the optional `| Field | Value |` + separator header
    that immediately precedes the Date row, the four data rows
    (`Date`, `Tool`, `Work`, `Next Priorities`), and one trailing blank line
    when present. The optional header is included only when no other addendum
    already claimed it.
    """
    results: list[Addendum] = []
    claimed: set[int] = set()
    i = start
    while i < end:
        match = DATE_RE.match(lines[i].rstrip())
        if not match:
            i += 1
            continue
        addendum_date = date.fromisoformat(match.group(1))
        # Walk forward: Date row + Tool + Work + Next Priorities.
        block_end = min(i + 4, end)
        # Optional trailing blank line.
        if block_end < end and lines[block_end].strip() == "":
            block_end += 1
        # Walk backward: include header+separator if present and unclaimed.
        block_start = i
        scan = i - 1
        while scan >= start and lines[scan].strip() == "" and scan not in claimed:
            scan -= 1
        if (
            scan >= start + 1
            and scan not in claimed
            and (scan - 1) not in claimed
            and SEPARATOR_RE.match(lines[scan].rstrip())
            and HEADER_RE.match(lines[scan - 1].rstrip())
        ):
            block_start = scan - 1
        results.append(Addendum(start=block_start, end=block_end, date=addendum_date))
        claimed.update(range(block_start, block_end))
        i = block_end
    return results


def rotate(
    repo_root: Path,
    *,
    keep_days: int,
    today: date,
    dry_run: bool = False,
) -> dict:
    """Rotate stale addenda. Returns a structured result dict.

    Status values:
      - "skip":   HANDOFF.md missing or no Current Addendum section.
      - "noop":   nothing to archive (everything is within the keep window).
      - "rotated": addenda older than the cutoff were moved to archive.
    """
    handoff = repo_root / ".ai" / "HANDOFF.md"
    if not handoff.exists():
        return {"status": "skip", "reason": "HANDOFF.md not found"}

    text = handoff.read_text(encoding="utf-8")
    lines = text.splitlines()
    rng = find_current_addendum_range(lines)
    if rng is None:
        return {"status": "skip", "reason": "Current Addendum heading not found"}

    section_start, section_end = rng
    addenda = parse_addenda(lines, section_start, section_end)
    cutoff = today - timedelta(days=keep_days)
    to_archive = [a for a in addenda if a.date < cutoff]
    to_keep = [a for a in addenda if a.date >= cutoff]

    if not to_archive:
        return {
            "status": "noop",
            "kept": len(to_keep),
            "archived": 0,
            "cutoff": cutoff.isoformat(),
        }

    archive_indices: set[int] = set()
    for addendum in to_archive:
        archive_indices.update(range(addendum.start, addendum.end))

    new_lines: list[str] = []
    for idx, line in enumerate(lines):
        if idx in archive_indices:
            continue
        new_lines.append(line)
    # Collapse runs of 3+ blank lines down to 2 (one separator) in the section.
    cleaned = _collapse_blank_runs(new_lines)
    new_text = "\n".join(cleaned).rstrip() + "\n"

    chunks: list[str] = []
    for addendum in to_archive:
        block = "\n".join(lines[addendum.start : addendum.end]).rstrip()
        chunks.append(block)
    archive_block = (
        f"## Rotation {today.isoformat()} "
        f"(archived addenda older than {cutoff.isoformat()})\n\n" + "\n\n".join(chunks) + "\n"
    )

    archive_dir = repo_root / ".ai" / "archive"
    archive_file = archive_dir / f"HANDOFF_archive_{today.isoformat()}.md"

    if not dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)
        if archive_file.exists():
            existing = archive_file.read_text(encoding="utf-8").rstrip()
            archive_file.write_text(existing + "\n\n" + archive_block, encoding="utf-8")
        else:
            archive_file.write_text(archive_block, encoding="utf-8")
        handoff.write_text(new_text, encoding="utf-8")

    return {
        "status": "rotated",
        "kept": len(to_keep),
        "archived": len(to_archive),
        "cutoff": cutoff.isoformat(),
        "archive_file": str(archive_file.relative_to(repo_root)).replace("\\", "/"),
        "dry_run": dry_run,
    }


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rotate stale .ai/HANDOFF.md addenda into .ai/archive/.",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        help="Keep addenda dated within the last N days (default: 7).",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
