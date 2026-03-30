"""Blind-to-X scheduled runner."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_DIR = SCRIPT_PATH.parent
REPO_ROOT = PROJECT_DIR.parent.parent
WORKSPACE_DIR = REPO_ROOT / "workspace"
WORKSPACE_EXECUTION_DIR = WORKSPACE_DIR / "execution"
MAIN_SCRIPT = PROJECT_DIR / "main.py"
PYTHON = sys.executable
LOG_DIR = PROJECT_DIR / ".tmp" / "logs"


def _command_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def build_primary_tasks(python_executable: str) -> list[dict[str, object]]:
    return [
        {
            "name": "Trending Scrape",
            "cmd": [python_executable, str(MAIN_SCRIPT), "--trending"],
            "cwd": PROJECT_DIR,
            "timeout": 600,
            "fatal": True,
        },
        {
            "name": "Popular Scrape",
            "cmd": [python_executable, str(MAIN_SCRIPT), "--popular"],
            "cwd": PROJECT_DIR,
            "timeout": 600,
            "fatal": True,
        },
    ]


def build_follow_up_tasks(python_executable: str) -> list[dict[str, object]]:
    return [
        {
            "name": "Watchdog health check",
            "cmd": [python_executable, "-m", "execution.pipeline_watchdog"],
            "cwd": WORKSPACE_DIR,
            "timeout": 60,
            "fatal": False,
        },
        {
            "name": "OneDrive backup",
            "cmd": [python_executable, "-m", "execution.backup_to_onedrive"],
            "cwd": WORKSPACE_DIR,
            "timeout": 300,
            "fatal": False,
        },
    ]


def _run_logged_task(log, write_log, task: dict[str, object], *, env: dict[str, str]) -> int:
    task_name = str(task["name"])
    cmd = [str(part) for part in task["cmd"]]
    cwd = Path(task["cwd"])
    timeout = int(task["timeout"])

    write_log(f"Running {task_name}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(cwd),
            env=env,
        )
        if result.stdout:
            log.write(result.stdout)
        if result.stderr:
            log.write(result.stderr)
        log.flush()

        if result.returncode != 0:
            write_log(f"ERROR: {task_name} failed with exit code {result.returncode}")
        else:
            write_log(f"OK: {task_name} completed successfully")
        return result.returncode
    except subprocess.TimeoutExpired:
        write_log(f"ERROR: {task_name} timed out ({timeout}s)")
        return 1
    except Exception as exc:  # pragma: no cover - defensive logging path
        write_log(f"ERROR: {task_name} exception: {exc}")
        return 1


def main() -> None:
    os.chdir(PROJECT_DIR)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    log_file = LOG_DIR / f"scheduled_{now.strftime('%Y%m%d_%H%M')}.log"
    env = _command_env()

    with open(log_file, "w", encoding="utf-8") as log:

        def write_log(message: str) -> None:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"[{ts}] {message}\n")
            log.flush()

        write_log("=" * 50)
        write_log("Starting Blind-to-X Scheduled Tasks")
        write_log(f"Project Directory: {PROJECT_DIR}")
        write_log(f"Workspace Directory: {WORKSPACE_DIR}")
        write_log(f"Workspace Execution: {WORKSPACE_EXECUTION_DIR}")
        write_log(f"Python: {PYTHON}")
        write_log(f"CWD: {os.getcwd()}")
        write_log("=" * 50)

        fail_count = 0

        for task in build_primary_tasks(PYTHON):
            result_code = _run_logged_task(log, write_log, task, env=env)
            if task.get("fatal") and result_code != 0:
                fail_count += 1

        write_log("=" * 50)
        write_log(f"Pipeline finished. Failures: {fail_count}")
        write_log("=" * 50)

        for task in build_follow_up_tasks(PYTHON):
            _run_logged_task(log, write_log, task, env=env)

        write_log("=" * 50)
        write_log("All tasks complete.")
        write_log("=" * 50)

    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
