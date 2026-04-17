"""Advisory session lock checker for `.ai/LOCKS/` convention.

Part of Tech Debt Review 2026-04-15 Phase 4. This script is informational
only - it NEVER blocks a commit. It surfaces concurrent-session warnings
so a human operator (or AI agent) can decide whether to wait, coordinate,
or proceed.

Usage:
    python execution/session_lock_check.py --tool claude-opus
    python execution/session_lock_check.py --tool codex --files .ai/HANDOFF.md

Exit codes:
    0 - always (advisory only)

Stdout:
    INFO: listing of active locks
    WARN: if another tool's lock is active
    HINT: if caller has no lock but is touching shared files
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path

# Windows cp949 console can't encode some punctuation. Force UTF-8 stdout/stderr
# so operators see clean output regardless of terminal locale.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCKS_DIR = REPO_ROOT / ".ai" / "LOCKS"
SHARED_FILES = {
    ".ai/HANDOFF.md",
    ".ai/TASKS.md",
    ".ai/SESSION_LOG.md",
    ".ai/CONTEXT.md",
    ".ai/DECISIONS.md",
}
STALE_HOURS = 1


def _parse_lock(path: Path) -> dict[str, str]:
    data: dict[str, str] = {"_name": path.stem}
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            if "=" not in raw:
                continue
            key, _, value = raw.partition("=")
            data[key.strip()] = value.strip()
    except OSError:
        return data
    return data


def _lock_age_hours(lock: dict[str, str]) -> float | None:
    started = lock.get("started")
    if not started:
        return None
    try:
        dt = _dt.datetime.fromisoformat(started)
    except ValueError:
        return None
    now = _dt.datetime.now(dt.tzinfo) if dt.tzinfo else _dt.datetime.now()
    return (now - dt).total_seconds() / 3600


def _active_locks() -> list[dict[str, str]]:
    if not LOCKS_DIR.exists():
        return []
    locks: list[dict[str, str]] = []
    for entry in sorted(LOCKS_DIR.glob("*.lock")):
        lock = _parse_lock(entry)
        locks.append(lock)
    return locks


def _render_lock(lock: dict[str, str]) -> str:
    bits = [lock["_name"]]
    if branch := lock.get("branch"):
        bits.append(f"branch={branch}")
    if started := lock.get("started"):
        bits.append(f"started={started}")
    age = _lock_age_hours(lock)
    if age is not None:
        marker = " (STALE)" if age > STALE_HOURS else ""
        bits.append(f"age={age:.2f}h{marker}")
    return " ".join(bits)


def main() -> int:
    parser = argparse.ArgumentParser(description="Advisory session lock checker (never blocks)")
    parser.add_argument(
        "--tool",
        required=False,
        default=os.environ.get("BTX_AI_TOOL", ""),
        help="Caller tool id (e.g. claude-opus, codex, gemini-antigravity)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Files being touched (to check if they are shared .ai/* docs)",
    )
    args = parser.parse_args()

    locks = _active_locks()
    caller_tool = (args.tool or "").strip()

    if not locks:
        print("INFO: no active session locks")
    else:
        print("INFO: active session locks:")
        for lock in locks:
            print(f"  - {_render_lock(lock)}")

    others = [lock for lock in locks if lock["_name"] != caller_tool]
    fresh_others = [lock for lock in others if (age := _lock_age_hours(lock)) is None or age <= STALE_HOURS]
    if fresh_others:
        print("WARN: concurrent session(s) active - consider coordinating:")
        for lock in fresh_others:
            print(f"  - {_render_lock(lock)}")

    caller_has_lock = any(lock["_name"] == caller_tool for lock in locks)
    if caller_tool and not caller_has_lock:
        touched_shared = False
        if args.files:
            normalized = {f.replace("\\", "/").lstrip("./") for f in args.files}
            touched_shared = bool(normalized & SHARED_FILES)
        if touched_shared or not args.files:
            print(
                f"HINT: no lock for '{caller_tool}'. Create one with:\n"
                f"  echo -e 'pid={os.getpid()}\\nstarted={_dt.datetime.now().isoformat()}\\n"
                f"branch=$(git branch --show-current)' > .ai/LOCKS/{caller_tool}.lock"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
