"""
Scheduler due-task worker.

Runs run_due_tasks() in a loop and prevents duplicate worker instances with a lock file.

Usage:
    python workspace/execution/scheduler_worker.py
    python workspace/execution/scheduler_worker.py --interval 30
    python workspace/execution/scheduler_worker.py --once
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from execution.scheduler_engine import run_due_tasks
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from execution.scheduler_engine import run_due_tasks

WORKSPACE = Path(__file__).resolve().parent.parent
LOCK_PATH = WORKSPACE / ".tmp" / "scheduler_worker.lock"


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        # signal 0 checks process existence without killing.
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_lock_pid() -> Optional[int]:
    if not LOCK_PATH.exists():
        return None
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        return int(data.get("pid", 0))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None


def acquire_lock() -> bool:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing_pid = _read_lock_pid()
    if existing_pid and _is_pid_alive(existing_pid):
        return False
    if LOCK_PATH.exists():
        try:
            LOCK_PATH.unlink()
        except OSError:
            return False

    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        LOCK_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return True
    except OSError:
        return False


def release_lock() -> None:
    if not LOCK_PATH.exists():
        return
    lock_pid = _read_lock_pid()
    if lock_pid == os.getpid():
        try:
            LOCK_PATH.unlink()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Joolife Scheduler Worker")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30, clamped to 10~60).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run due-task check once and exit.",
    )
    args = parser.parse_args()

    if not acquire_lock():
        print("Scheduler worker is already running.")
        return 1

    atexit.register(release_lock)

    interval = max(10, min(60, int(args.interval)))
    print(f"Scheduler worker started (pid={os.getpid()}, interval={interval}s)")

    try:
        if args.once:
            logs = run_due_tasks()
            print(f"Executed {len(logs)} due task(s).")
            return 0

        while True:
            logs = run_due_tasks()
            if logs:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executed {len(logs)} due task(s).")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Scheduler worker stopped by user.")
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
