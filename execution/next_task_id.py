"""Suggest a collision-safe next task ID for `.ai/TASKS.md`.

Multiple AI tools (Claude Code, Codex, Gemini, ...) edit `.ai/TASKS.md`
in parallel. Each tool typically picks `max(existing IDs) + 1` from its
own snapshot of the file, which causes the same ID to be assigned twice
when their snapshots overlap (this week alone produced T-1107×2,
T-1108×2, T-1195×2, T-1199×2 collisions, all visible in `git log`).

This script reduces the collision surface by checking BOTH:
  1. Every `T-####` reference in `.ai/TASKS.md` (current working state)
  2. Every `T-####` reference in the last N commit subjects + bodies
     (so an ID another tool already committed but not yet visible in
     YOUR TASKS.md snapshot still gets skipped)

It prints a single suggested ID to stdout. The caller (tool/agent) is
expected to use that ID when filling in TASKS.md / HANDOFF.md / commit
message. Re-running the script right before each commit narrows the
race window to "seconds-with-write-conflict" rather than
"minutes-with-stale-snapshot".

Usage:
    python execution/next_task_id.py             # → "T-1201"
    python execution/next_task_id.py --json      # → JSON for automation
    python execution/next_task_id.py --git-window 50   # scan 50 commits

Limits:
  - Cannot prevent collisions if two tools sample at the same instant
    (within ~1s). For those, the convention is: whichever tool commits
    second appends a letter suffix (e.g. T-1201b) and explains in the
    commit body, per the organic pattern already in use (see commit
    e940de77 for an example).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_MD = ROOT / ".ai" / "TASKS.md"
HANDOFF_MD = ROOT / ".ai" / "HANDOFF.md"

_ID_PATTERN = re.compile(r"T-(\d{4,})")


def _ids_in_file(path: Path) -> set[int]:
    if not path.is_file():
        return set()
    return {int(m.group(1)) for m in _ID_PATTERN.finditer(path.read_text(encoding="utf-8", errors="replace"))}


def _ids_in_git_log(window: int) -> set[int]:
    """T-#### references in the last `window` commit subjects + bodies.

    Forces UTF-8 with `replace` on decode error so Windows CP949 default
    encoding does not blow up on Korean commit messages (see memory
    `windows_korean_path_encode_strict`).
    """
    try:
        result = subprocess.run(
            ["git", "log", f"-{window}", "--format=%s%n%b"],
            capture_output=True,
            cwd=str(ROOT),
            check=False,
        )
    except FileNotFoundError:
        return set()
    if result.returncode != 0:
        return set()
    text = result.stdout.decode("utf-8", errors="replace")
    return {int(m.group(1)) for m in _ID_PATTERN.finditer(text)}


def suggest_next_id(*, git_window: int = 30, max_step: int = 50) -> dict[str, object]:
    md_ids = _ids_in_file(TASKS_MD)
    handoff_ids = _ids_in_file(HANDOFF_MD)
    git_ids = _ids_in_git_log(git_window)
    all_ids = md_ids | handoff_ids | git_ids
    base = max(all_ids) if all_ids else 1000
    for step in range(1, max_step + 1):
        candidate = base + step
        if candidate not in all_ids:
            return {
                "suggested_id": f"T-{candidate}",
                "base": base,
                "step": step,
                "scanned": {
                    "tasks_md": len(md_ids),
                    "handoff_md": len(handoff_ids),
                    "git_log_window": git_window,
                    "git_log_ids": len(git_ids),
                },
            }
    # All max_step candidates collided — unlikely but explicit fallback.
    return {
        "suggested_id": f"T-{base + max_step + 1}",
        "base": base,
        "step": max_step + 1,
        "scanned": {
            "tasks_md": len(md_ids),
            "handoff_md": len(handoff_ids),
            "git_log_window": git_window,
            "git_log_ids": len(git_ids),
        },
        "warning": "All in-range candidates collided; using base + max_step + 1.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Suggest a collision-safe next task ID for .ai/TASKS.md.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of plain ID (for tooling/automation).",
    )
    parser.add_argument(
        "--git-window",
        type=int,
        default=30,
        help="Number of recent git commits to scan for T-#### references (default: 30).",
    )
    args = parser.parse_args(argv)
    result = suggest_next_id(git_window=args.git_window)
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(result["suggested_id"] + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
