"""Rotate stale 'Current Addendum' entries from `.ai/HANDOFF.md` into `.ai/archive/`.

The shared AI context policy (`CLAUDE.md`) keeps `.ai/SESSION_LOG.md` to the last
seven days of activity, but `.ai/HANDOFF.md` had no equivalent rotation. As a
result the "Current Addendum" stack drifted to ~280 lines, half of it older than
two weeks. This script reads each addendum block, splits them by date against a
configurable cutoff, rewrites HANDOFF.md with only the recent ones, and appends
the archived blocks to `.ai/archive/HANDOFF_archive_<rotation_date>.md`.

The date cutoff alone is not enough. An automated loop (e.g. the auto-research
self-improvement loop) can append dozens of addenda per day, all dated within
the keep window, so a pure ``--keep-days`` rotation no-ops while the file grows
unbounded (observed: 312 addenda / ~580KB in 3 days). ``--max-lines`` (default
200) and ``--keep-count`` bound the file regardless of dates and implement the
session-close "over 200 lines" trigger that the day cutoff cannot.

Usage:
    python execution/handoff_rotator.py            # --keep-days=7, --max-lines=200
    python execution/handoff_rotator.py --check    # dry-run summary
    python execution/handoff_rotator.py --keep-days 14
    python execution/handoff_rotator.py --keep-count 20   # cap to 20 newest
    python execution/handoff_rotator.py --max-lines 0     # disable the line cap
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
CURRENT_ADDENDUM_HEADING_RE = re.compile(r"^##\s+Current Addendum(?:\s|$)")
DATE_RE = re.compile(r"^\|\s*Date\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*$")
HEADER_RE = re.compile(r"^\|\s*Field\s*\|\s*Value\s*\|\s*$")
SEPARATOR_RE = re.compile(r"^\|[\s\-:|]+\|\s*$")
SECTION_RE = re.compile(r"^##\s+")


@dataclass(frozen=True)
class Addendum:
    start: int  # absolute line index, inclusive
    end: int  # absolute line index, exclusive
    date: date


@dataclass(frozen=True)
class _PreparedWrite:
    target: Path
    temp: Path


class _WriteFailure(Exception):
    def __init__(self, path: Path, error: OSError) -> None:
        self.path = path
        self.error = error
        super().__init__(f"{path}: {error}")


def find_current_addendum_range(lines: list[str]) -> tuple[int, int] | None:
    """Return absolute (start, end) line indices of the Current Addendum body.

    The returned range excludes the `## Current Addendum` heading itself and
    ends at the next `## ` heading or end-of-file.
    """
    start: int | None = None
    for i, line in enumerate(lines):
        if CURRENT_ADDENDUM_HEADING_RE.match(line.rstrip()):
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


def _select_kept(
    recent: list[Addendum],
    *,
    keep_count: int | None,
    max_lines: int | None,
    fixed_overhead: int,
) -> list[Addendum]:
    """Return the newest addenda to keep after applying the count/line caps.

    ``recent`` is in document order (newest first, matching how HANDOFF.md
    stacks the latest addendum on top). The count cap keeps at most
    ``keep_count`` of them; the line cap then greedily keeps newest addenda
    while the rewritten file (``fixed_overhead`` + kept spans) stays within
    ``max_lines``. At least the single newest addendum is always kept whenever
    any recent addendum exists, so a tiny budget never empties the section.
    """
    kept = list(recent)
    if keep_count is not None and keep_count >= 0:
        kept = kept[:keep_count]
    if max_lines is not None and max_lines > 0 and kept:
        budget = max_lines - fixed_overhead
        trimmed: list[Addendum] = []
        used = 0
        for addendum in kept:
            cost = addendum.end - addendum.start
            if trimmed and used + cost > budget:
                break
            trimmed.append(addendum)
            used += cost
        kept = trimmed
    return kept


def rotate(
    repo_root: Path,
    *,
    keep_days: int,
    today: date,
    keep_count: int | None = None,
    max_lines: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Rotate stale addenda. Returns a structured result dict.

    An addendum is archived when it falls outside any configured cap:
      - older than ``keep_days`` (date cutoff), or
      - beyond the newest ``keep_count`` addenda, or
      - beyond the ``max_lines`` budget for the rewritten file.

    The date cutoff alone is not enough: a burst of many addenda dated within
    the keep window (e.g. an automated loop writing dozens per day) leaves the
    file unbounded. ``keep_count``/``max_lines`` bound it regardless of dates,
    which is what the session-close "over 200 lines" trigger relies on.

    Status values:
      - "skip":   HANDOFF.md missing or no Current Addendum section.
      - "noop":   nothing to archive (everything is within the caps).
      - "rotated": addenda outside the caps were moved to archive.
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
    recent = [a for a in addenda if a.date >= cutoff]
    addenda_span = sum(a.end - a.start for a in addenda)
    fixed_overhead = len(lines) - addenda_span
    to_keep = _select_kept(
        recent,
        keep_count=keep_count,
        max_lines=max_lines,
        fixed_overhead=fixed_overhead,
    )
    keep_set = set(to_keep)
    to_archive = [a for a in addenda if a not in keep_set]

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
        try:
            if archive_file.exists():
                existing = archive_file.read_text(encoding="utf-8").rstrip()
                archive_text = existing + "\n\n" + archive_block
            else:
                archive_text = archive_block
            prepared = [
                _prepare_text_write(archive_file, archive_text),
                _prepare_text_write(handoff, new_text),
            ]
            _commit_prepared_writes(prepared)
        except _WriteFailure as exc:
            return {
                "status": "write_failed",
                "kept": len(to_keep),
                "archived": len(to_archive),
                "cutoff": cutoff.isoformat(),
                "archive_file": str(archive_file.relative_to(repo_root)).replace("\\", "/"),
                "dry_run": dry_run,
                "write_error": str(exc.error),
                "write_error_path": str(exc.path),
            }

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
        "--keep-count",
        type=int,
        default=None,
        help="Also keep at most N most-recent addenda regardless of date (default: no count cap).",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=200,
        help="Trim oldest addenda until the rewritten HANDOFF.md fits within N "
        "lines (default: 200; 0 disables). Implements the session-close "
        "'over 200 lines' rotation trigger that the date cutoff alone cannot.",
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
        keep_count=args.keep_count,
        max_lines=args.max_lines,
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
