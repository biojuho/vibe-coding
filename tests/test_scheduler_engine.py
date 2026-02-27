from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import execution.scheduler_engine as se


def _configure_tmp_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(se, "DB_PATH", tmp_path / "scheduler.db")
    monkeypatch.setattr(se, "WORKSPACE", tmp_path)
    se.init_db()


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

def test_add_and_run_task_success(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script_path = tmp_path / "ok.py"
    script_path.write_text("print('ok')\n", encoding="utf-8")

    task_id = se.add_task(
        name="ok",
        executable="python",
        args=[str(script_path.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=30,
    )
    log = se.run_task(task_id)
    assert log.exit_code == 0
    assert "ok" in log.stdout


def test_auto_disable_after_consecutive_failures(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task(
        name="bad",
        executable="definitely_missing_executable_123",
        args=[],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=10,
    )

    for _ in range(se.MAX_FAILURE_COUNT):
        se.run_task(task_id)

    task = se.list_tasks()[0]
    assert task.failure_count >= se.MAX_FAILURE_COUNT
    assert not task.enabled


def test_run_due_tasks_marks_schedule_trigger(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script_path = tmp_path / "due.py"
    script_path.write_text("print('due')\n", encoding="utf-8")

    task_id = se.add_task(
        name="due",
        executable="python",
        args=[str(script_path.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=30,
    )

    conn = se._conn()
    conn.execute("UPDATE tasks SET next_run = ? WHERE id = ?", ("2000-01-01 00:00:00", task_id))
    conn.commit()
    conn.close()

    logs = se.run_due_tasks()
    assert logs
    assert logs[0].trigger_type == "schedule"


def test_scheduler_schema_identifier_validation(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    conn = se._conn()
    try:
        with pytest.raises(ValueError):
            se._table_columns(conn, "tasks; DROP TABLE tasks")
        with pytest.raises(ValueError):
            se._ensure_column(conn, "tasks", "unexpected_column", "TEXT")
        with pytest.raises(ValueError):
            se._ensure_column(conn, "tasks", "command", "TEXT")
    finally:
        conn.close()


def test_init_db_migrates_legacy_columns_and_backfills(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy_scheduler.db"
    monkeypatch.setattr(se, "DB_PATH", db_path)
    monkeypatch.setattr(se, "WORKSPACE", tmp_path)

    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT DEFAULT '',
            cwd TEXT NOT NULL DEFAULT '.',
            cron_expression TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            exit_code INTEGER,
            stdout TEXT DEFAULT '',
            stderr TEXT DEFAULT '',
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        """
    )
    conn.execute(
        """
        INSERT INTO tasks (name, command, cwd, cron_expression, next_run)
        VALUES (?, ?, '.', '*/5 * * * *', '2000-01-01 00:00:00')
        """,
        ("legacy", "python legacy_task.py"),
    )
    conn.commit()
    conn.close()

    se.init_db()

    migrated = se._conn()
    try:
        tasks_columns = se._table_columns(migrated, "tasks")
        logs_columns = se._table_columns(migrated, "task_logs")
        assert "executable" in tasks_columns
        assert "args_json" in tasks_columns
        assert "timeout_sec" in tasks_columns
        assert "failure_count" in tasks_columns
        assert "duration_ms" in logs_columns
        assert "trigger_type" in logs_columns
        assert "error_type" in logs_columns

        row = migrated.execute(
            "SELECT command, executable, args_json FROM tasks WHERE name = ?",
            ("legacy",),
        ).fetchone()
        assert row is not None
        assert row["executable"] == "python"
        assert se._deserialize_args(row["args_json"]) == ["legacy_task.py"]
    finally:
        migrated.close()


# ---------------------------------------------------------------------------
# ScheduledTask.command property
# ---------------------------------------------------------------------------

def test_task_command_property_posix():
    task = se.ScheduledTask(
        id=1, name="t", executable="python", args=["script.py", "--flag"],
        cwd=".", cron_expression="*/5 * * * *", timeout_sec=300,
        enabled=True, last_run=None, next_run=None,
        created_at="2026-01-01 00:00:00", failure_count=0,
    )
    with patch("execution.scheduler_engine.os.name", "posix"):
        result = task.command
    assert "python" in result
    assert "script.py" in result


def test_task_command_property_windows():
    task = se.ScheduledTask(
        id=1, name="t", executable="python", args=["script.py"],
        cwd=".", cron_expression="*/5 * * * *", timeout_sec=300,
        enabled=True, last_run=None, next_run=None,
        created_at="2026-01-01 00:00:00", failure_count=0,
    )
    with patch("execution.scheduler_engine.os.name", "nt"):
        result = task.command
    assert "python" in result
    assert "script.py" in result


# ---------------------------------------------------------------------------
# _parse_command_text
# ---------------------------------------------------------------------------

def test_parse_command_text_empty_raises():
    with pytest.raises(ValueError, match="Empty command"):
        se._parse_command_text("")


def test_parse_command_text_whitespace_raises():
    with pytest.raises(ValueError, match="Empty command"):
        se._parse_command_text("   ")


def test_parse_command_text_valid():
    exe, args = se._parse_command_text("python script.py --flag")
    assert exe == "python"
    assert "script.py" in args


def test_parse_command_text_raises_when_shlex_returns_empty(monkeypatch):
    """Line 155: _parse_command_text raises when shlex.split produces no tokens."""
    monkeypatch.setattr(se.shlex, "split", lambda *a, **kw: [])
    with pytest.raises(ValueError, match="Could not parse command"):
        se._parse_command_text("anything")


# ---------------------------------------------------------------------------
# _deserialize_args
# ---------------------------------------------------------------------------

def test_deserialize_args_none():
    assert se._deserialize_args(None) == []


def test_deserialize_args_empty_string():
    assert se._deserialize_args("") == []


def test_deserialize_args_invalid_json():
    assert se._deserialize_args("not valid json {{{") == []


def test_deserialize_args_non_list_json():
    assert se._deserialize_args('"just a string"') == []


def test_deserialize_args_valid():
    result = se._deserialize_args('["a", "b", "c"]')
    assert result == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# _resolve_executable
# ---------------------------------------------------------------------------

def test_resolve_executable_python():
    exe, args = se._resolve_executable("python", ["script.py"])
    assert exe == sys.executable
    assert args == ["script.py"]


def test_resolve_executable_streamlit():
    exe, args = se._resolve_executable("streamlit", ["run", "app.py"])
    assert exe == sys.executable
    assert args[:2] == ["-m", "streamlit"]
    assert "run" in args
    assert "app.py" in args


def test_resolve_executable_npm_on_windows():
    with patch("execution.scheduler_engine.os.name", "nt"):
        exe, args = se._resolve_executable("npm", ["install"])
    assert exe == "npm.cmd"
    assert args == ["install"]


def test_resolve_executable_passthrough():
    with patch("execution.scheduler_engine.os.name", "posix"):
        exe, args = se._resolve_executable("node", ["index.js"])
    assert exe == "node"
    assert args == ["index.js"]


# ---------------------------------------------------------------------------
# init_db backfill edge cases
# ---------------------------------------------------------------------------

def test_init_db_backfill_skips_empty_command(monkeypatch, tmp_path):
    """Legacy row with blank command is skipped without crashing."""
    db_path = tmp_path / "sched.db"
    monkeypatch.setattr(se, "DB_PATH", db_path)
    monkeypatch.setattr(se, "WORKSPACE", tmp_path)

    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT DEFAULT '',
            cwd TEXT NOT NULL DEFAULT '.',
            cron_expression TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run TEXT, next_run TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL, task_name TEXT NOT NULL,
            started_at TEXT NOT NULL, finished_at TEXT, exit_code INTEGER,
            stdout TEXT DEFAULT '', stderr TEXT DEFAULT '',
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        """
    )
    conn.execute(
        "INSERT INTO tasks (name, command, cwd, cron_expression) VALUES (?, ?, '.', '*/5 * * * *')",
        ("empty-cmd", ""),
    )
    conn.commit()
    conn.close()

    se.init_db()  # should not raise

    conn2 = se._conn()
    row = conn2.execute("SELECT executable FROM tasks WHERE name = 'empty-cmd'").fetchone()
    conn2.close()
    assert row["executable"] == "" or row["executable"] is None


def test_init_db_backfill_skips_invalid_command(monkeypatch, tmp_path):
    """Legacy row with unparseable command is skipped without crashing."""
    db_path = tmp_path / "sched2.db"
    monkeypatch.setattr(se, "DB_PATH", db_path)
    monkeypatch.setattr(se, "WORKSPACE", tmp_path)

    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT DEFAULT '',
            cwd TEXT NOT NULL DEFAULT '.',
            cron_expression TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run TEXT, next_run TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL, task_name TEXT NOT NULL,
            started_at TEXT NOT NULL, finished_at TEXT, exit_code INTEGER,
            stdout TEXT DEFAULT '', stderr TEXT DEFAULT '',
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        """
    )
    conn.execute(
        "INSERT INTO tasks (name, command, cwd, cron_expression) VALUES (?, ?, '.', '*/5 * * * *')",
        ("bad-cmd", "   "),  # whitespace-only → _parse_command_text raises ValueError
    )
    conn.commit()
    conn.close()

    se.init_db()  # should not raise


# ---------------------------------------------------------------------------
# add_task_from_command
# ---------------------------------------------------------------------------

def test_add_task_from_command(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task_from_command(
        name="from-cmd",
        command_text="python script.py --flag",
        cwd=".",
        cron_expression="*/5 * * * *",
    )
    assert isinstance(task_id, int)
    tasks = se.list_tasks()
    assert any(t.id == task_id and t.name == "from-cmd" for t in tasks)


# ---------------------------------------------------------------------------
# list_tasks with legacy command fallback
# ---------------------------------------------------------------------------

def test_list_tasks_legacy_command_fallback(monkeypatch, tmp_path):
    """Task with empty executable but populated command is parsed on list."""
    _configure_tmp_db(monkeypatch, tmp_path)
    conn = se._conn()
    conn.execute(
        """
        INSERT INTO tasks (name, command, executable, args_json, cwd, cron_expression)
        VALUES ('legacy', 'python legacy.py', '', '[]', '.', '*/5 * * * *')
        """
    )
    conn.commit()
    conn.close()

    tasks = se.list_tasks()
    legacy = next(t for t in tasks if t.name == "legacy")
    assert legacy.executable == "python"
    assert "legacy.py" in legacy.args


def test_list_tasks_legacy_command_invalid_falls_back_empty(monkeypatch, tmp_path):
    """Unparseable legacy command yields empty executable gracefully."""
    _configure_tmp_db(monkeypatch, tmp_path)
    conn = se._conn()
    conn.execute(
        """
        INSERT INTO tasks (name, command, executable, args_json, cwd, cron_expression)
        VALUES ('bad-legacy', '   ', '', '[]', '.', '*/5 * * * *')
        """
    )
    conn.commit()
    conn.close()

    tasks = se.list_tasks()
    bad = next(t for t in tasks if t.name == "bad-legacy")
    assert bad.executable == ""
    assert bad.args == []


# ---------------------------------------------------------------------------
# toggle_task / delete_task
# ---------------------------------------------------------------------------

def test_toggle_task(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task(
        name="toggle-me", executable="python", args=[],
        cwd=".", cron_expression="*/5 * * * *",
    )
    se.toggle_task(task_id, False)
    task = next(t for t in se.list_tasks() if t.id == task_id)
    assert not task.enabled

    se.toggle_task(task_id, True)
    task = next(t for t in se.list_tasks() if t.id == task_id)
    assert task.enabled


def test_delete_task(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task(
        name="delete-me", executable="python", args=[],
        cwd=".", cron_expression="*/5 * * * *",
    )
    assert any(t.id == task_id for t in se.list_tasks())
    se.delete_task(task_id)
    assert not any(t.id == task_id for t in se.list_tasks())


# ---------------------------------------------------------------------------
# run_task edge cases
# ---------------------------------------------------------------------------

def test_run_task_not_found_raises(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="not found"):
        se.run_task(99999)


def test_run_task_cwd_not_found(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task(
        name="no-cwd", executable="python", args=["x.py"],
        cwd="nonexistent_path_xyz",
        cron_expression="*/5 * * * *",
    )
    log = se.run_task(task_id)
    assert log.exit_code == -3
    assert log.error_type == "cwd_not_found"


def test_run_task_empty_executable(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    # Insert directly with empty executable so validation is bypassed at insert time
    conn = se._conn()
    from croniter import croniter as _cron
    from datetime import datetime as _dt
    next_run = _cron("*/5 * * * *", _dt.now()).get_next(_dt).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO tasks (name, command, executable, args_json, cwd, cron_expression, next_run)
           VALUES ('empty-exe', '', '', '[]', '.', '*/5 * * * *', ?)""",
        (next_run,),
    )
    conn.commit()
    task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    log = se.run_task(task_id)
    assert log.exit_code == -5
    assert log.error_type == "invalid_command"


def test_run_task_non_zero_exit(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script = tmp_path / "fail.py"
    script.write_text("import sys; sys.exit(1)\n", encoding="utf-8")
    task_id = se.add_task(
        name="fail", executable="python", args=[str(script.name)],
        cwd=".", cron_expression="*/5 * * * *",
    )
    log = se.run_task(task_id)
    assert log.exit_code == 1
    assert log.error_type == "non_zero_exit"


def test_run_task_timeout(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script = tmp_path / "slow.py"
    script.write_text("import time; time.sleep(30)\n", encoding="utf-8")
    task_id = se.add_task(
        name="slow", executable="python", args=[str(script.name)],
        cwd=".", cron_expression="*/5 * * * *",
        timeout_sec=1,
    )
    log = se.run_task(task_id)
    assert log.exit_code == -1
    assert log.error_type == "timeout"


def test_run_task_exec_not_found(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task(
        name="missing-exe", executable="definitely_nonexistent_bin_xyz",
        args=[], cwd=".", cron_expression="*/5 * * * *",
    )
    log = se.run_task(task_id)
    assert log.exit_code == -4
    assert log.error_type == "exec_not_found"


def test_run_task_legacy_command_fallback_in_run(monkeypatch, tmp_path):
    """run_task falls back to parsing legacy command when executable is empty."""
    _configure_tmp_db(monkeypatch, tmp_path)
    script = tmp_path / "ok.py"
    script.write_text("print('legacy-ok')\n", encoding="utf-8")

    conn = se._conn()
    from croniter import croniter as _cron
    from datetime import datetime as _dt
    next_run = _cron("*/5 * * * *", _dt.now()).get_next(_dt).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO tasks (name, command, executable, args_json, cwd, cron_expression, next_run)
           VALUES (?, ?, '', '[]', '.', '*/5 * * * *', ?)""",
        ("legacy-run", f"python {script.name}", next_run),
    )
    conn.commit()
    task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    log = se.run_task(task_id)
    assert log.exit_code == 0
    assert "legacy-ok" in log.stdout


# ---------------------------------------------------------------------------
# get_logs
# ---------------------------------------------------------------------------

def test_get_logs_empty(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    logs = se.get_logs()
    assert logs == []


def test_get_logs_returns_after_run(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script = tmp_path / "x.py"
    script.write_text("print('x')\n", encoding="utf-8")
    task_id = se.add_task(
        name="x", executable="python", args=[str(script.name)],
        cwd=".", cron_expression="*/5 * * * *",
    )
    se.run_task(task_id)
    logs = se.get_logs()
    assert len(logs) >= 1
    assert logs[0].task_name == "x"


def test_get_logs_filtered_by_task_id(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script = tmp_path / "y.py"
    script.write_text("print('y')\n", encoding="utf-8")
    task_id = se.add_task(
        name="y", executable="python", args=[str(script.name)],
        cwd=".", cron_expression="*/5 * * * *",
    )
    se.run_task(task_id)
    logs = se.get_logs(task_id=task_id)
    assert all(lg.task_id == task_id for lg in logs)


def test_get_logs_nonexistent_task_returns_empty(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    logs = se.get_logs(task_id=9999)
    assert logs == []


# ---------------------------------------------------------------------------
# get_scheduler_kpis
# ---------------------------------------------------------------------------

def test_get_scheduler_kpis_empty(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    kpis = se.get_scheduler_kpis()
    assert kpis["total_runs"] == 0
    assert kpis["successful_runs"] == 0
    assert kpis["scheduler_success_rate"] == 0.0
    assert kpis["scheduler_backlog"] == 0


def test_get_scheduler_kpis_after_success(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script = tmp_path / "kpi.py"
    script.write_text("print('kpi')\n", encoding="utf-8")
    task_id = se.add_task(
        name="kpi", executable="python", args=[str(script.name)],
        cwd=".", cron_expression="*/5 * * * *",
    )
    se.run_task(task_id)
    kpis = se.get_scheduler_kpis(days=7)
    assert kpis["total_runs"] >= 1
    assert kpis["successful_runs"] >= 1
    assert kpis["scheduler_success_rate"] == 100.0


def test_get_scheduler_kpis_backlog(monkeypatch, tmp_path):
    """Tasks overdue appear in backlog count."""
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task(
        name="overdue", executable="python", args=[],
        cwd=".", cron_expression="*/5 * * * *",
    )
    conn = se._conn()
    conn.execute("UPDATE tasks SET next_run = '2000-01-01 00:00:00' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    kpis = se.get_scheduler_kpis()
    assert kpis["scheduler_backlog"] >= 1


# ---------------------------------------------------------------------------
# _ensure_column: line 146 – no ALTER TABLE SQL defined for column
# ---------------------------------------------------------------------------

def test_ensure_column_raises_when_no_alter_sql(monkeypatch, tmp_path):
    """_ensure_column raises ValueError when the column is known in the migration
    definitions but there is no corresponding ALTER TABLE SQL entry."""
    import sqlite3

    db = tmp_path / "bare.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    # Create a tasks table missing the 'command' column
    conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    conn.commit()

    # Remove the ALTER SQL for ("tasks", "command") so line 146 is reached
    patched_alter = {k: v for k, v in se._ALTER_TABLE_ADD_SQL.items() if k != ("tasks", "command")}
    monkeypatch.setattr(se, "_ALTER_TABLE_ADD_SQL", patched_alter)

    with pytest.raises(ValueError, match="No migration SQL defined"):
        se._ensure_column(conn, "tasks", "command", "TEXT DEFAULT ''")
    conn.close()


# ---------------------------------------------------------------------------
# _migrate_legacy_commands: lines 254-255 – ValueError skipped silently
# ---------------------------------------------------------------------------

def test_migrate_legacy_commands_skips_unparseable(monkeypatch, tmp_path):
    """init_db does not raise when _parse_command_text raises for a legacy row."""
    _configure_tmp_db(monkeypatch, tmp_path)

    # Insert a legacy task: empty executable, non-empty command
    conn = se._conn()
    conn.execute(
        "INSERT INTO tasks (name, command, executable, args_json, cwd, cron_expression)"
        " VALUES ('legacy-bad', 'some cmd', '', '[]', '.', '*/5 * * * *')"
    )
    conn.commit()
    conn.close()

    # Patch _parse_command_text to raise ValueError for this command
    original = se._parse_command_text

    def bad_parse(cmd: str):
        if cmd == "some cmd":
            raise ValueError("simulated parse failure")
        return original(cmd)

    monkeypatch.setattr(se, "_parse_command_text", bad_parse)
    se.init_db()  # must not raise; bad row is silently skipped


# ---------------------------------------------------------------------------
# run_task: lines 427-431 – legacy command parse failure at runtime
# ---------------------------------------------------------------------------

def test_run_task_legacy_command_parse_error(monkeypatch, tmp_path):
    """run_task handles ValueError from _parse_command_text gracefully,
    falling back to exit_code -5 / error_type 'invalid_command'."""
    _configure_tmp_db(monkeypatch, tmp_path)

    task_id = se.add_task(
        name="legacy-parse-err",
        executable="python",
        args=["script.py"],
        cwd=".",
        cron_expression="*/5 * * * *",
    )

    # Force the row into legacy mode: clear executable, set command to something
    conn = se._conn()
    conn.execute(
        "UPDATE tasks SET executable = '', command = 'broken cmd' WHERE id = ?",
        (task_id,),
    )
    conn.commit()
    conn.close()

    original = se._parse_command_text

    def bad_parse(cmd: str):
        if cmd == "broken cmd":
            raise ValueError("cannot parse")
        return original(cmd)

    monkeypatch.setattr(se, "_parse_command_text", bad_parse)

    log = se.run_task(task_id)
    assert log.exit_code == -5
    assert log.error_type == "invalid_command"
