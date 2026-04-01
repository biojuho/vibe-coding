"""
스케줄러 엔진 - Joolife Hub용.
cron 기반 태스크 스케줄링을 SQLite로 관리.

Usage:
    python workspace/execution/scheduler_engine.py list
    python workspace/execution/scheduler_engine.py add --name "Daily Backup" --exec python --args "workspace/scripts/backup_data.py" --cron "0 9 * * *"
    python workspace/execution/scheduler_engine.py add --name "Legacy Cmd" --command "python workspace/scripts/backup_data.py" --cron "0 9 * * *"
    python workspace/execution/scheduler_engine.py run-due
    python workspace/execution/scheduler_engine.py logs --limit 50
    python workspace/execution/scheduler_engine.py kpis
"""

import argparse
import json
import os
import shlex
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from croniter import croniter

DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "scheduler.db"
WORKSPACE = Path(__file__).resolve().parent.parent
DEFAULT_TIMEOUT_SEC = 300
MAX_FAILURE_COUNT = int(os.getenv("SCHEDULER_MAX_FAILURES", "5"))
WORKER_NAME_DEFAULT = "default"
WORKER_STALE_AFTER_SEC = int(os.getenv("SCHEDULER_STALE_AFTER_SEC", "180"))
OPS_STATUS_HEALTHY = "healthy"
OPS_STATUS_WARNING = "warning"
OPS_STATUS_CRITICAL = "critical"
OPS_STATUS_SETUP_REQUIRED = "setup_required"

_SCHEMA_TABLE_INFO_SQL = {
    "tasks": "PRAGMA table_info(tasks)",
    "task_logs": "PRAGMA table_info(task_logs)",
    "worker_runtime": "PRAGMA table_info(worker_runtime)",
}

_SCHEMA_MIGRATION_DEFINITIONS = {
    "tasks": {
        "command": "TEXT DEFAULT ''",
        "executable": "TEXT DEFAULT ''",
        "args_json": "TEXT DEFAULT '[]'",
        "timeout_sec": "INTEGER NOT NULL DEFAULT 300",
        "failure_count": "INTEGER NOT NULL DEFAULT 0",
    },
    "task_logs": {
        "duration_ms": "INTEGER NOT NULL DEFAULT 0",
        "trigger_type": "TEXT NOT NULL DEFAULT 'manual'",
        "error_type": "TEXT NOT NULL DEFAULT ''",
    },
    "worker_runtime": {
        "worker_name": "TEXT PRIMARY KEY",
        "last_heartbeat": "TEXT NOT NULL",
        "status": "TEXT NOT NULL DEFAULT 'healthy'",
        "note": "TEXT DEFAULT ''",
        "updated_at": "TEXT NOT NULL",
    },
}

_ALTER_TABLE_ADD_SQL = {
    ("tasks", "command"): "ALTER TABLE tasks ADD COLUMN command TEXT DEFAULT ''",
    ("tasks", "executable"): "ALTER TABLE tasks ADD COLUMN executable TEXT DEFAULT ''",
    ("tasks", "args_json"): "ALTER TABLE tasks ADD COLUMN args_json TEXT DEFAULT '[]'",
    ("tasks", "timeout_sec"): "ALTER TABLE tasks ADD COLUMN timeout_sec INTEGER NOT NULL DEFAULT 300",
    ("tasks", "failure_count"): "ALTER TABLE tasks ADD COLUMN failure_count INTEGER NOT NULL DEFAULT 0",
    ("task_logs", "duration_ms"): "ALTER TABLE task_logs ADD COLUMN duration_ms INTEGER NOT NULL DEFAULT 0",
    ("task_logs", "trigger_type"): "ALTER TABLE task_logs ADD COLUMN trigger_type TEXT NOT NULL DEFAULT 'manual'",
    ("task_logs", "error_type"): "ALTER TABLE task_logs ADD COLUMN error_type TEXT NOT NULL DEFAULT ''",
    ("worker_runtime", "worker_name"): "ALTER TABLE worker_runtime ADD COLUMN worker_name TEXT PRIMARY KEY",
    (
        "worker_runtime",
        "last_heartbeat",
    ): "ALTER TABLE worker_runtime ADD COLUMN last_heartbeat TEXT NOT NULL DEFAULT ''",
    ("worker_runtime", "status"): "ALTER TABLE worker_runtime ADD COLUMN status TEXT NOT NULL DEFAULT 'healthy'",
    ("worker_runtime", "note"): "ALTER TABLE worker_runtime ADD COLUMN note TEXT DEFAULT ''",
    ("worker_runtime", "updated_at"): "ALTER TABLE worker_runtime ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
}


@dataclass
class ScheduledTask:
    id: int
    name: str
    executable: str
    args: List[str]
    cwd: str
    cron_expression: str
    timeout_sec: int
    enabled: bool
    last_run: Optional[str]
    next_run: Optional[str]
    created_at: str
    failure_count: int

    @property
    def command(self) -> str:
        # Backward-compatible display for existing UI callers.
        if os.name == "nt":
            return subprocess.list2cmdline([self.executable, *self.args]).strip()
        return " ".join(shlex.quote(x) for x in [self.executable, *self.args]).strip()


@dataclass
class TaskLog:
    id: int
    task_id: int
    task_name: str
    started_at: str
    finished_at: Optional[str]
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int
    trigger_type: str
    error_type: str


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _validate_table_name(table_name: str) -> str:
    if table_name not in _SCHEMA_TABLE_INFO_SQL:
        raise ValueError(f"Unsupported table name: {table_name}")
    return table_name


def _validate_migration_column(table_name: str, column_name: str, definition_sql: str) -> str:
    allowed_columns = _SCHEMA_MIGRATION_DEFINITIONS.get(table_name, {})
    expected_definition = allowed_columns.get(column_name)
    if expected_definition is None:
        raise ValueError(f"Unsupported migration column: {table_name}.{column_name}")
    if definition_sql != expected_definition:
        raise ValueError(f"Unexpected definition for {table_name}.{column_name}: {definition_sql}")
    return expected_definition


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    table_name = _validate_table_name(table_name)
    rows = conn.execute(_SCHEMA_TABLE_INFO_SQL[table_name]).fetchall()
    return {row["name"] for row in rows}


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition_sql: str,
) -> None:
    table_name = _validate_table_name(table_name)
    _validate_migration_column(table_name, column_name, definition_sql)
    columns = _table_columns(conn, table_name)
    if column_name not in columns:
        alter_sql = _ALTER_TABLE_ADD_SQL.get((table_name, column_name))
        if alter_sql is None:
            raise ValueError(f"No migration SQL defined for {table_name}.{column_name}")
        conn.execute(alter_sql)


def _parse_command_text(command_text: str) -> Tuple[str, List[str]]:
    if not command_text or not command_text.strip():
        raise ValueError("Empty command is not allowed.")
    parts = shlex.split(command_text, posix=False)
    if not parts:
        raise ValueError("Could not parse command.")
    return parts[0], parts[1:]


def _serialize_args(args: List[str]) -> str:
    return json.dumps(args or [], ensure_ascii=False)


def _deserialize_args(args_json: Optional[str]) -> List[str]:
    if not args_json:
        return []
    try:
        parsed = json.loads(args_json)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _resolve_executable(executable: str, args: List[str]) -> Tuple[str, List[str]]:
    exe = executable.strip()
    exe_lower = exe.lower()
    if exe_lower == "python":
        return sys.executable, args
    if exe_lower == "streamlit":
        return sys.executable, ["-m", "streamlit", *args]
    if os.name == "nt" and exe_lower == "npm":
        return "npm.cmd", args
    return exe, args


def _resolve_target_cwd(cwd: str) -> Optional[Path]:
    target = (WORKSPACE / cwd).resolve()
    if target.exists() and target.is_dir():
        return target
    return None


def init_db() -> None:
    conn = _conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT DEFAULT '',
            executable TEXT DEFAULT '',
            args_json TEXT DEFAULT '[]',
            cwd TEXT NOT NULL DEFAULT '.',
            cron_expression TEXT NOT NULL,
            timeout_sec INTEGER NOT NULL DEFAULT 300,
            enabled INTEGER NOT NULL DEFAULT 1,
            failure_count INTEGER NOT NULL DEFAULT 0,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            exit_code INTEGER,
            stdout TEXT DEFAULT '',
            stderr TEXT DEFAULT '',
            duration_ms INTEGER NOT NULL DEFAULT 0,
            trigger_type TEXT NOT NULL DEFAULT 'manual',
            error_type TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        CREATE TABLE IF NOT EXISTS worker_runtime (
            worker_name TEXT PRIMARY KEY,
            last_heartbeat TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'healthy',
            note TEXT DEFAULT '',
            updated_at TEXT NOT NULL
        );
        """
    )

    # Legacy schema migration.
    _ensure_column(conn, "tasks", "command", "TEXT DEFAULT ''")
    _ensure_column(conn, "tasks", "executable", "TEXT DEFAULT ''")
    _ensure_column(conn, "tasks", "args_json", "TEXT DEFAULT '[]'")
    _ensure_column(conn, "tasks", "timeout_sec", "INTEGER NOT NULL DEFAULT 300")
    _ensure_column(conn, "tasks", "failure_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "task_logs", "duration_ms", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "task_logs", "trigger_type", "TEXT NOT NULL DEFAULT 'manual'")
    _ensure_column(conn, "task_logs", "error_type", "TEXT NOT NULL DEFAULT ''")

    # Backfill executable/args_json from legacy command column when needed.
    rows = conn.execute(
        """
        SELECT id, command, executable, args_json
        FROM tasks
        WHERE (executable IS NULL OR executable = '')
        """
    ).fetchall()
    for row in rows:
        command_text = (row["command"] or "").strip()
        if not command_text:
            continue
        try:
            executable, args = _parse_command_text(command_text)
        except ValueError:
            continue
        conn.execute(
            "UPDATE tasks SET executable = ?, args_json = ? WHERE id = ?",
            (executable, _serialize_args(args), row["id"]),
        )

    conn.commit()
    conn.close()


def _upsert_worker_heartbeat(
    conn: sqlite3.Connection,
    worker_name: str,
    status: str,
    note: str = "",
) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO worker_runtime (worker_name, last_heartbeat, status, note, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(worker_name) DO UPDATE SET
            last_heartbeat = excluded.last_heartbeat,
            status = excluded.status,
            note = excluded.note,
            updated_at = excluded.updated_at
        """,
        (worker_name, now_str, status, note[:500], now_str),
    )


def touch_worker_heartbeat(
    worker_name: str = WORKER_NAME_DEFAULT,
    status: str = OPS_STATUS_HEALTHY,
    note: str = "",
) -> None:
    init_db()
    conn = _conn()
    _upsert_worker_heartbeat(conn, worker_name=worker_name, status=status, note=note)
    conn.commit()
    conn.close()


def get_worker_heartbeat(worker_name: str = WORKER_NAME_DEFAULT) -> Optional[Dict[str, Any]]:
    init_db()
    conn = _conn()
    row = conn.execute(
        "SELECT worker_name, last_heartbeat, status, note, updated_at FROM worker_runtime WHERE worker_name = ?",
        (worker_name,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def get_scheduler_ops_summary(
    stale_after_sec: int = WORKER_STALE_AFTER_SEC,
    worker_name: str = WORKER_NAME_DEFAULT,
) -> Dict[str, Any]:
    heartbeat = get_worker_heartbeat(worker_name)
    if heartbeat is None:
        return {
            "worker_name": worker_name,
            "status": OPS_STATUS_SETUP_REQUIRED,
            "last_heartbeat": "",
            "seconds_since_heartbeat": None,
            "is_stale": False,
            "note": "",
            "next_action": "scheduler run-due 워커를 실행하세요.",
        }

    last_heartbeat_raw = str(heartbeat.get("last_heartbeat") or "")
    last_heartbeat_dt = _parse_datetime(last_heartbeat_raw)
    if last_heartbeat_dt is None:
        return {
            "worker_name": worker_name,
            "status": OPS_STATUS_CRITICAL,
            "last_heartbeat": last_heartbeat_raw,
            "seconds_since_heartbeat": None,
            "is_stale": True,
            "note": str(heartbeat.get("note") or ""),
            "next_action": "worker heartbeat 형식을 확인하세요.",
        }

    seconds_since = max(0, int((datetime.now() - last_heartbeat_dt).total_seconds()))
    persisted_status = str(heartbeat.get("status") or OPS_STATUS_HEALTHY)
    status = persisted_status
    if seconds_since >= stale_after_sec:
        status = OPS_STATUS_CRITICAL
    elif seconds_since >= max(30, stale_after_sec // 2) and status == OPS_STATUS_HEALTHY:
        status = OPS_STATUS_WARNING

    next_action = "정상 동작 중입니다."
    if status == OPS_STATUS_SETUP_REQUIRED:
        next_action = "scheduler run-due 워커를 실행하세요."
    elif status == OPS_STATUS_CRITICAL:
        next_action = "scheduler 워커 상태와 최근 로그를 확인하세요."
    elif status == OPS_STATUS_WARNING:
        next_action = "worker heartbeat와 최근 실패 작업을 점검하세요."

    return {
        "worker_name": worker_name,
        "status": status,
        "last_heartbeat": last_heartbeat_raw,
        "seconds_since_heartbeat": seconds_since,
        "is_stale": seconds_since >= stale_after_sec,
        "note": str(heartbeat.get("note") or ""),
        "next_action": next_action,
    }


def compute_next_run(cron_expression: str) -> str:
    cron = croniter(cron_expression, datetime.now())
    return cron.get_next(datetime).strftime("%Y-%m-%d %H:%M:%S")


def add_task(
    name: str,
    executable: str,
    args: List[str],
    cwd: str,
    cron_expression: str,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> int:
    init_db()
    next_run = compute_next_run(cron_expression)
    conn = _conn()
    cur = conn.execute(
        """
        INSERT INTO tasks (
            name, executable, args_json, command, cwd, cron_expression, timeout_sec, next_run
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            executable.strip(),
            _serialize_args(args),
            (
                subprocess.list2cmdline([executable, *args])
                if os.name == "nt"
                else " ".join(shlex.quote(x) for x in [executable, *args])
            ),
            cwd,
            cron_expression,
            int(timeout_sec) if timeout_sec > 0 else DEFAULT_TIMEOUT_SEC,
            next_run,
        ),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def add_task_from_command(
    name: str,
    command_text: str,
    cwd: str,
    cron_expression: str,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> int:
    executable, args = _parse_command_text(command_text)
    return add_task(name, executable, args, cwd, cron_expression, timeout_sec)


def list_tasks() -> List[ScheduledTask]:
    init_db()
    conn = _conn()
    rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    conn.close()

    tasks: List[ScheduledTask] = []
    for r in rows:
        executable = (r["executable"] or "").strip()
        args = _deserialize_args(r["args_json"])
        if not executable and r["command"]:
            try:
                executable, args = _parse_command_text(r["command"])
            except ValueError:
                executable, args = "", []
        tasks.append(
            ScheduledTask(
                id=r["id"],
                name=r["name"],
                executable=executable,
                args=args,
                cwd=r["cwd"],
                cron_expression=r["cron_expression"],
                timeout_sec=int(r["timeout_sec"] or DEFAULT_TIMEOUT_SEC),
                enabled=bool(r["enabled"]),
                last_run=r["last_run"],
                next_run=r["next_run"],
                created_at=r["created_at"],
                failure_count=int(r["failure_count"] or 0),
            )
        )
    return tasks


def toggle_task(task_id: int, enabled: bool) -> None:
    conn = _conn()
    conn.execute("UPDATE tasks SET enabled = ? WHERE id = ?", (int(enabled), task_id))
    conn.commit()
    conn.close()


def delete_task(task_id: int) -> None:
    conn = _conn()
    conn.execute("DELETE FROM task_logs WHERE task_id = ?", (task_id,))
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def _build_task_log(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    started_dt: datetime,
    finished_dt: datetime,
    exit_code: int,
    stdout: str,
    stderr: str,
    trigger_type: str,
    error_type: str,
) -> TaskLog:
    started_at = started_dt.strftime("%Y-%m-%d %H:%M:%S")
    finished_at = finished_dt.strftime("%Y-%m-%d %H:%M:%S")
    duration_ms = int((finished_dt - started_dt).total_seconds() * 1000)

    conn.execute(
        """
        INSERT INTO task_logs (
            task_id, task_name, started_at, finished_at, exit_code,
            stdout, stderr, duration_ms, trigger_type, error_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["id"],
            row["name"],
            started_at,
            finished_at,
            exit_code,
            stdout[:5000],
            stderr[:5000],
            duration_ms,
            trigger_type,
            error_type,
        ),
    )
    log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return TaskLog(
        id=log_id,
        task_id=row["id"],
        task_name=row["name"],
        started_at=started_at,
        finished_at=finished_at,
        exit_code=exit_code,
        stdout=stdout[:5000],
        stderr=stderr[:5000],
        duration_ms=duration_ms,
        trigger_type=trigger_type,
        error_type=error_type,
    )


def _execute_subprocess(
    resolved_exec: str,
    resolved_args: list,
    target_cwd: Path,
    timeout_sec: int,
) -> tuple[int, str, str, str]:
    """서브프로세스를 실행하고 (exit_code, stdout, stderr, error_type)을 반환."""
    exit_code = -2
    stdout = ""
    stderr = ""
    error_type = ""
    proc = None
    try:
        popen_kwargs: dict = dict(
            shell=False,
            cwd=str(target_cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
        )
        if os.name == "nt":
            # Windows: CREATE_NEW_PROCESS_GROUP prevents handle inheritance
            # issues with pytest stdout capture (WinError 6).
            import ctypes  # noqa: F401  – sanity import

            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen([resolved_exec, *resolved_args], **popen_kwargs)

        try:
            out, err = proc.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
            try:
                out, err = proc.communicate()
            except OSError:
                out, err = "", ""
            exit_code = -1
            error_type = "timeout"
            stderr = f"Timeout after {timeout_sec} seconds"
        else:
            exit_code = proc.returncode
            stdout = out or ""
            stderr = err or ""
            if exit_code != 0:
                error_type = "non_zero_exit"
    except FileNotFoundError as exc:
        exit_code = -4
        error_type = "exec_not_found"
        stderr = str(exc)
    except OSError as exc:
        # Non-FileNotFoundError OSError (e.g. WinError 6 on handle issues)
        # — only map to exec_not_found when it's a "not found" style error
        winerror = getattr(exc, "winerror", None)
        if winerror in (2, 3):  # ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND
            exit_code = -4
            error_type = "exec_not_found"
        else:
            exit_code = -2
            error_type = "exception"
        stderr = str(exc)
    except Exception as exc:  # pragma: no cover - defensive path
        exit_code = -2
        error_type = "exception"
        stderr = str(exc)
    return exit_code, stdout, stderr, error_type


def _apply_failure_policy(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    log: "TaskLog",
    exit_code: int,
) -> bool:
    """연속 실패 카운트 업데이트 및 MAX_FAILURE_COUNT 초과 시 자동 비활성화.

    Returns True if the task was auto-disabled.
    """
    failure_count = int(row["failure_count"] or 0)
    enabled = int(row["enabled"])
    auto_disabled = False
    if exit_code == 0:
        failure_count = 0
    else:
        failure_count += 1
        if enabled and failure_count >= MAX_FAILURE_COUNT:
            enabled = 0
            auto_disabled = True
            extra = f"\nTask auto-disabled after {failure_count} consecutive failures (threshold={MAX_FAILURE_COUNT})."
            stderr = (log.stderr + extra).strip()
            conn.execute(
                "UPDATE task_logs SET stderr = ?, error_type = ? WHERE id = ?",
                (stderr[:5000], "auto_disabled", log.id),
            )
            log.stderr = stderr[:5000]
            log.error_type = "auto_disabled"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    next_run = compute_next_run(row["cron_expression"])
    conn.execute(
        "UPDATE tasks SET last_run = ?, next_run = ?, failure_count = ?, enabled = ? WHERE id = ?",
        (now_str, next_run, failure_count, enabled, row["id"]),
    )
    return auto_disabled


def _maybe_notify_telegram_task(log: TaskLog, auto_disabled: bool = False) -> None:
    try:
        from execution.telegram_notifier import maybe_send_scheduler_notification
    except Exception:
        return

    try:
        maybe_send_scheduler_notification(
            task_name=log.task_name,
            exit_code=int(log.exit_code if log.exit_code is not None else -2),
            trigger_type=log.trigger_type,
            duration_ms=log.duration_ms,
            error_type=log.error_type,
            stderr=log.stderr,
            auto_disabled=auto_disabled,
        )
    except Exception:
        # Notifications must not break task persistence or scheduler flow.
        return


def run_task(task_id: int, trigger_type: str = "manual") -> TaskLog:
    """단일 태스크를 실행하고 로그를 저장한다."""
    init_db()
    conn = _conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Task {task_id} not found")
    _upsert_worker_heartbeat(
        conn,
        worker_name=WORKER_NAME_DEFAULT,
        status=OPS_STATUS_HEALTHY,
        note=f"task_start:{row['name']}",
    )
    conn.commit()

    executable = (row["executable"] or "").strip()
    args = _deserialize_args(row["args_json"])
    if not executable and row["command"]:
        try:
            executable, args = _parse_command_text(row["command"])
        except ValueError:
            executable = ""
            args = []

    started_dt = datetime.now()
    exit_code = -2
    stdout = ""
    stderr = ""
    error_type = ""

    target_cwd = _resolve_target_cwd(row["cwd"])
    if not target_cwd:
        exit_code = -3
        error_type = "cwd_not_found"
        stderr = f"Working directory not found: {(WORKSPACE / row['cwd']).resolve()}"
    elif not executable:
        exit_code = -5
        error_type = "invalid_command"
        stderr = "Executable is empty."
    else:
        resolved_exec, resolved_args = _resolve_executable(executable, args)
        timeout_sec = int(row["timeout_sec"] or DEFAULT_TIMEOUT_SEC)
        timeout_sec = timeout_sec if timeout_sec > 0 else DEFAULT_TIMEOUT_SEC
        exit_code, stdout, stderr, error_type = _execute_subprocess(
            resolved_exec, resolved_args, target_cwd, timeout_sec
        )

    finished_dt = datetime.now()
    log = _build_task_log(
        conn=conn,
        row=row,
        started_dt=started_dt,
        finished_dt=finished_dt,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        trigger_type=trigger_type,
        error_type=error_type,
    )

    auto_disabled = _apply_failure_policy(conn, row, log, exit_code)

    heartbeat_status = OPS_STATUS_HEALTHY if exit_code == 0 else OPS_STATUS_WARNING
    heartbeat_note = (
        f"last_task_ok:{row['name']}" if exit_code == 0 else f"last_task_failed:{row['name']}:{error_type or exit_code}"
    )
    _upsert_worker_heartbeat(
        conn,
        worker_name=WORKER_NAME_DEFAULT,
        status=heartbeat_status,
        note=heartbeat_note,
    )
    conn.commit()
    conn.close()
    _maybe_notify_telegram_task(log, auto_disabled=auto_disabled)
    return log


def run_due_tasks() -> List[TaskLog]:
    """현재 시간 기준으로 실행 시간이 지난 활성 태스크를 모두 실행."""
    init_db()
    conn = _conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """
        SELECT id
        FROM tasks
        WHERE enabled = 1 AND next_run IS NOT NULL AND next_run <= ?
        ORDER BY next_run ASC, id ASC
        """,
        (now,),
    ).fetchall()
    _upsert_worker_heartbeat(
        conn,
        worker_name=WORKER_NAME_DEFAULT,
        status=OPS_STATUS_HEALTHY,
        note=f"run_due_scan:{len(rows)}",
    )
    conn.commit()
    conn.close()

    logs: List[TaskLog] = []
    for r in rows:
        logs.append(run_task(r["id"], trigger_type="schedule"))
    return logs


def get_logs(task_id: Optional[int] = None, limit: int = 50) -> List[TaskLog]:
    init_db()
    conn = _conn()
    query = """
        SELECT id, task_id, task_name, started_at, finished_at, exit_code, stdout, stderr,
               COALESCE(duration_ms, 0) AS duration_ms,
               COALESCE(trigger_type, 'manual') AS trigger_type,
               COALESCE(error_type, '') AS error_type
        FROM task_logs
    """
    params: Tuple[Any, ...]
    if task_id is not None:
        query += " WHERE task_id = ? ORDER BY id DESC LIMIT ?"
        params = (task_id, limit)
    else:
        query += " ORDER BY id DESC LIMIT ?"
        params = (limit,)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [
        TaskLog(
            id=r["id"],
            task_id=r["task_id"],
            task_name=r["task_name"],
            started_at=r["started_at"],
            finished_at=r["finished_at"],
            exit_code=r["exit_code"],
            stdout=r["stdout"],
            stderr=r["stderr"],
            duration_ms=int(r["duration_ms"] or 0),
            trigger_type=r["trigger_type"],
            error_type=r["error_type"],
        )
        for r in rows
    ]


def get_scheduler_kpis(days: int = 7) -> Dict[str, Any]:
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    total_runs = conn.execute(
        "SELECT COUNT(*) FROM task_logs WHERE started_at >= ?",
        (since,),
    ).fetchone()[0]
    success_runs = conn.execute(
        "SELECT COUNT(*) FROM task_logs WHERE started_at >= ? AND exit_code = 0",
        (since,),
    ).fetchone()[0]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    backlog = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE enabled = 1 AND next_run IS NOT NULL AND next_run <= ?",
        (now,),
    ).fetchone()[0]
    conn.close()

    success_rate = (success_runs / total_runs * 100) if total_runs else 0.0
    return {
        "days": days,
        "total_runs": total_runs,
        "successful_runs": success_runs,
        "scheduler_success_rate": round(success_rate, 2),
        "scheduler_backlog": backlog,
    }


def get_recent_failure_summary(limit: int = 10, within_hours: int = 24) -> List[Dict[str, Any]]:
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(hours=within_hours)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """
        SELECT
            t.id AS task_id,
            t.name,
            t.enabled,
            t.failure_count,
            t.timeout_sec,
            t.next_run,
            (
                SELECT l.started_at
                FROM task_logs l
                WHERE l.task_id = t.id AND l.exit_code != 0
                ORDER BY l.id DESC
                LIMIT 1
            ) AS last_failed_at,
            (
                SELECT COALESCE(l.error_type, '')
                FROM task_logs l
                WHERE l.task_id = t.id AND l.exit_code != 0
                ORDER BY l.id DESC
                LIMIT 1
            ) AS last_error_type,
            (
                SELECT COALESCE(l.stderr, '')
                FROM task_logs l
                WHERE l.task_id = t.id AND l.exit_code != 0
                ORDER BY l.id DESC
                LIMIT 1
            ) AS last_stderr,
            (
                SELECT COUNT(*)
                FROM task_logs l
                WHERE l.task_id = t.id AND l.exit_code != 0 AND l.started_at >= ?
            ) AS recent_failures
        FROM tasks t
        WHERE t.failure_count > 0
           OR EXISTS (
                SELECT 1
                FROM task_logs l
                WHERE l.task_id = t.id AND l.exit_code != 0 AND l.started_at >= ?
           )
        ORDER BY recent_failures DESC, t.failure_count DESC, last_failed_at DESC, t.id DESC
        LIMIT ?
        """,
        (since, since, limit),
    ).fetchall()
    conn.close()

    summary: List[Dict[str, Any]] = []
    for row in rows:
        recent_failures = int(row["recent_failures"] or 0)
        failure_count = int(row["failure_count"] or 0)
        enabled = bool(row["enabled"])
        if not enabled:
            next_action = "오류 수정 후 재활성화"
        elif recent_failures >= 3 or failure_count >= max(2, MAX_FAILURE_COUNT // 2):
            next_action = "명령과 환경을 우선 점검"
        else:
            next_action = "최근 로그 확인"
        summary.append(
            {
                "task_id": row["task_id"],
                "name": row["name"],
                "enabled": enabled,
                "failure_count": failure_count,
                "recent_failures": recent_failures,
                "timeout_sec": int(row["timeout_sec"] or DEFAULT_TIMEOUT_SEC),
                "next_run": row["next_run"],
                "last_failed_at": row["last_failed_at"] or "",
                "last_error_type": row["last_error_type"] or "",
                "last_stderr": row["last_stderr"] or "",
                "next_action": next_action,
            }
        )
    return summary


def get_attention_queue(limit: int = 10) -> List[Dict[str, Any]]:
    tasks = list_tasks()
    now = datetime.now()
    attention_items: List[Dict[str, Any]] = []
    failure_threshold = max(2, MAX_FAILURE_COUNT // 2)

    for task in tasks:
        reasons: List[str] = []
        next_action = ""
        next_run_dt = _parse_datetime(task.next_run)

        if not task.enabled and task.failure_count > 0:
            reasons.append("auto_disabled")
            next_action = "오류 수정 후 재활성화"
        if task.failure_count >= failure_threshold:
            reasons.append("repeated_failures")
            if not next_action:
                next_action = "연속 실패 원인 점검"
        if task.enabled and next_run_dt is not None and next_run_dt <= now:
            reasons.append("overdue")
            if not next_action:
                next_action = "작업 즉시 실행 또는 worker 확인"

        if not reasons:
            continue

        priority = 0
        if "auto_disabled" in reasons:
            priority -= 20
        if "repeated_failures" in reasons:
            priority -= 10
        if "overdue" in reasons:
            priority -= 5
        priority -= task.failure_count

        attention_items.append(
            {
                "task_id": task.id,
                "name": task.name,
                "enabled": task.enabled,
                "failure_count": task.failure_count,
                "last_run": task.last_run or "",
                "next_run": task.next_run or "",
                "reasons": reasons,
                "next_action": next_action or "상태 확인",
                "priority": priority,
            }
        )

    attention_items.sort(key=lambda item: (item["priority"], item["name"]))
    return attention_items[:limit]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joolife Scheduler Engine")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list")

    p_add = sub.add_parser("add")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--command", help="Legacy command text (e.g. 'python script.py').")
    p_add.add_argument("--exec", dest="executable", help="Executable name (e.g. python).")
    p_add.add_argument("--args", default="", help="Argument string for --exec.")
    p_add.add_argument("--cwd", default=".")
    p_add.add_argument("--cron", required=True)
    p_add.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC)

    sub.add_parser("run-due")

    p_logs = sub.add_parser("logs")
    p_logs.add_argument("--task-id", type=int)
    p_logs.add_argument("--limit", type=int, default=50)

    p_kpis = sub.add_parser("kpis")
    p_kpis.add_argument("--days", type=int, default=7)

    args = parser.parse_args()

    if args.cmd == "list":
        for t in list_tasks():
            payload = asdict(t)
            payload["command"] = t.command
            print(json.dumps(payload, ensure_ascii=False))
    elif args.cmd == "add":
        timeout = int(args.timeout) if args.timeout and args.timeout > 0 else DEFAULT_TIMEOUT_SEC
        if args.command:
            tid = add_task_from_command(args.name, args.command, args.cwd, args.cron, timeout_sec=timeout)
        else:
            if not args.executable:
                parser.error("Either --command or --exec must be provided for add.")
            parsed_args = shlex.split(args.args, posix=False) if args.args else []
            tid = add_task(args.name, args.executable, parsed_args, args.cwd, args.cron, timeout_sec=timeout)
        print(f"Created task #{tid}")
    elif args.cmd == "run-due":
        logs = run_due_tasks()
        for log in logs:
            print(json.dumps(asdict(log), ensure_ascii=False))
    elif args.cmd == "logs":
        for log in get_logs(args.task_id, args.limit):
            print(json.dumps(asdict(log), ensure_ascii=False))
    elif args.cmd == "kpis":
        print(json.dumps(get_scheduler_kpis(args.days), ensure_ascii=False))
    else:
        parser.print_help()
