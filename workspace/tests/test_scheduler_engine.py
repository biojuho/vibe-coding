from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
import builtins
import types
from unittest.mock import patch

import pytest

import execution.scheduler_engine as se


# ---------------------------------------------------------------------------
# Windows: pytest stdout 캡처가 subprocess PIPE와 충돌하여 WinError 6 발생.
# 이 파일의 모든 테스트에서 캡처를 비활성화하여 해결.
# ---------------------------------------------------------------------------

if sys.platform == "win32":

    @pytest.fixture(autouse=True)
    def _disable_capture_for_subprocess(request):
        capman = request.config.pluginmanager.getplugin("capturemanager")
        if capman is None:
            yield
            return
        capman.suspend_global_capture(in_=True)
        try:
            yield
        finally:
            capman.resume_global_capture()


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
        id=1,
        name="t",
        executable="python",
        args=["script.py", "--flag"],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=300,
        enabled=True,
        last_run=None,
        next_run=None,
        created_at="2026-01-01 00:00:00",
        failure_count=0,
    )
    with patch("execution.scheduler_engine.os.name", "posix"):
        result = task.command
    assert "python" in result
    assert "script.py" in result


def test_task_command_property_windows():
    task = se.ScheduledTask(
        id=1,
        name="t",
        executable="python",
        args=["script.py"],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=300,
        enabled=True,
        last_run=None,
        next_run=None,
        created_at="2026-01-01 00:00:00",
        failure_count=0,
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
        name="toggle-me",
        executable="python",
        args=[],
        cwd=".",
        cron_expression="*/5 * * * *",
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
        name="delete-me",
        executable="python",
        args=[],
        cwd=".",
        cron_expression="*/5 * * * *",
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
        name="no-cwd",
        executable="python",
        args=["x.py"],
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
        name="fail",
        executable="python",
        args=[str(script.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
    )
    log = se.run_task(task_id)
    assert log.exit_code == 1
    assert log.error_type == "non_zero_exit"


def test_run_task_timeout(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script = tmp_path / "slow.py"
    script.write_text("import time; time.sleep(30)\n", encoding="utf-8")
    task_id = se.add_task(
        name="slow",
        executable="python",
        args=[str(script.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=1,
    )
    log = se.run_task(task_id)
    assert log.exit_code == -1
    assert log.error_type == "timeout"


def test_run_task_calls_telegram_notifier(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script_path = tmp_path / "notify_ok.py"
    script_path.write_text("print('notify')\n", encoding="utf-8")

    task_id = se.add_task(
        name="notify-ok",
        executable="python",
        args=[str(script_path.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=30,
    )

    calls = []
    monkeypatch.setattr(
        se,
        "_maybe_notify_telegram_task",
        lambda log, auto_disabled=False: calls.append((log, auto_disabled)),
    )

    log = se.run_task(task_id)

    assert log.exit_code == 0
    assert len(calls) == 1
    assert calls[0][0].task_name == "notify-ok"
    assert calls[0][1] is False


def test_maybe_notify_telegram_task_ignores_import_failure(monkeypatch):
    log = se.TaskLog(
        id=1,
        task_id=1,
        task_name="notify",
        started_at="2026-01-01 00:00:00",
        finished_at="2026-01-01 00:00:01",
        exit_code=0,
        stdout="",
        stderr="",
        duration_ms=10,
        trigger_type="manual",
        error_type="",
    )
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "execution.telegram_notifier":
            raise ImportError("missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    se._maybe_notify_telegram_task(log)


def test_maybe_notify_telegram_task_ignores_send_failure(monkeypatch):
    log = se.TaskLog(
        id=1,
        task_id=1,
        task_name="notify",
        started_at="2026-01-01 00:00:00",
        finished_at="2026-01-01 00:00:01",
        exit_code=0,
        stdout="",
        stderr="boom",
        duration_ms=10,
        trigger_type="manual",
        error_type="",
    )
    stub_module = types.ModuleType("execution.telegram_notifier")

    def fake_send(**kwargs):
        raise RuntimeError("telegram down")

    stub_module.maybe_send_scheduler_notification = fake_send
    monkeypatch.setitem(sys.modules, "execution.telegram_notifier", stub_module)

    se._maybe_notify_telegram_task(log, auto_disabled=True)


def test_run_task_marks_auto_disabled_in_telegram_notification(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task(
        name="notify-fail",
        executable="definitely_missing_executable_123",
        args=[],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=10,
    )

    auto_disabled_flags = []
    monkeypatch.setattr(
        se,
        "_maybe_notify_telegram_task",
        lambda log, auto_disabled=False: auto_disabled_flags.append(auto_disabled),
    )

    for _ in range(se.MAX_FAILURE_COUNT):
        se.run_task(task_id)

    assert auto_disabled_flags
    assert auto_disabled_flags[-1] is True


def test_run_task_exec_not_found(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task(
        name="missing-exe",
        executable="definitely_nonexistent_bin_xyz",
        args=[],
        cwd=".",
        cron_expression="*/5 * * * *",
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
        name="x",
        executable="python",
        args=[str(script.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
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
        name="y",
        executable="python",
        args=[str(script.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
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
        name="kpi",
        executable="python",
        args=[str(script.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
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
        name="overdue",
        executable="python",
        args=[],
        cwd=".",
        cron_expression="*/5 * * * *",
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


def test_scheduler_ops_summary_requires_setup_without_heartbeat(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)

    summary = se.get_scheduler_ops_summary(stale_after_sec=180)
    assert summary["status"] == se.OPS_STATUS_SETUP_REQUIRED
    assert summary["seconds_since_heartbeat"] is None
    assert "run-due" in summary["next_action"]


def test_touch_worker_heartbeat_and_summary_healthy(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)

    se.touch_worker_heartbeat(note="boot")
    summary = se.get_scheduler_ops_summary(stale_after_sec=180)

    assert summary["status"] == se.OPS_STATUS_HEALTHY
    assert summary["seconds_since_heartbeat"] is not None
    assert summary["note"] == "boot"


def test_scheduler_ops_summary_turns_critical_when_stale(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    se.touch_worker_heartbeat(note="old")

    conn = se._conn()
    conn.execute(
        """
        UPDATE worker_runtime
        SET last_heartbeat = ?, updated_at = ?
        WHERE worker_name = ?
        """,
        ("2000-01-01 00:00:00", "2000-01-01 00:00:00", se.WORKER_NAME_DEFAULT),
    )
    conn.commit()
    conn.close()

    summary = se.get_scheduler_ops_summary(stale_after_sec=60)
    assert summary["status"] == se.OPS_STATUS_CRITICAL
    assert summary["is_stale"] is True
    assert summary["seconds_since_heartbeat"] is not None


def test_run_due_tasks_updates_worker_heartbeat(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    script_path = tmp_path / "due_hb.py"
    script_path.write_text("print('hb')\n", encoding="utf-8")

    task_id = se.add_task(
        name="due-hb",
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

    heartbeat = se.get_worker_heartbeat()
    assert heartbeat is not None
    assert heartbeat["worker_name"] == se.WORKER_NAME_DEFAULT
    assert heartbeat["note"].startswith("last_task_")


def test_get_recent_failure_summary_orders_by_recent_failures(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    missing_task_id = se.add_task(
        name="missing-exec",
        executable="definitely_missing_executable_123",
        args=[],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=10,
    )
    script_path = tmp_path / "fail_once.py"
    script_path.write_text("import sys\nsys.exit(2)\n", encoding="utf-8")
    script_task_id = se.add_task(
        name="script-fail",
        executable="python",
        args=[str(script_path.name)],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=10,
    )

    se.run_task(missing_task_id)
    se.run_task(missing_task_id)
    se.run_task(script_task_id)

    summary = se.get_recent_failure_summary(limit=5, within_hours=24)
    assert len(summary) >= 2
    assert summary[0]["task_id"] == missing_task_id
    assert summary[0]["recent_failures"] >= 2
    assert summary[0]["failure_count"] >= 2
    assert summary[0]["last_error_type"] in {"exec_not_found", "non_zero_exit", "auto_disabled"}
    assert summary[0]["next_action"]


def test_get_attention_queue_prioritizes_disabled_and_overdue(monkeypatch, tmp_path):
    _configure_tmp_db(monkeypatch, tmp_path)
    disabled_id = se.add_task(
        name="disabled-failure",
        executable="definitely_missing_executable_123",
        args=[],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=10,
    )
    overdue_id = se.add_task(
        name="overdue-task",
        executable="python",
        args=["-c", "print('ok')"],
        cwd=".",
        cron_expression="*/5 * * * *",
        timeout_sec=10,
    )

    for _ in range(se.MAX_FAILURE_COUNT):
        se.run_task(disabled_id)

    conn = se._conn()
    conn.execute("UPDATE tasks SET next_run = ? WHERE id = ?", ("2000-01-01 00:00:00", overdue_id))
    conn.commit()
    conn.close()

    queue = se.get_attention_queue(limit=10)
    assert len(queue) >= 2
    assert queue[0]["task_id"] == disabled_id
    assert "auto_disabled" in queue[0]["reasons"]
    overdue = next(item for item in queue if item["task_id"] == overdue_id)
    assert "overdue" in overdue["reasons"]


# ---------------------------------------------------------------------------
# _parse_datetime (lines 335-341)
# ---------------------------------------------------------------------------


def test_parse_datetime_valid():
    result = se._parse_datetime("2026-03-07 14:30:00")
    assert result is not None
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 7


def test_parse_datetime_none():
    assert se._parse_datetime(None) is None


def test_parse_datetime_empty_string():
    assert se._parse_datetime("") is None


def test_parse_datetime_invalid_format():
    assert se._parse_datetime("not-a-date") is None


def test_parse_datetime_partial_format():
    assert se._parse_datetime("2026-03-07") is None


# ---------------------------------------------------------------------------
# get_scheduler_ops_summary edge cases (lines 360-387)
# ---------------------------------------------------------------------------


def test_scheduler_ops_summary_unparseable_heartbeat(monkeypatch, tmp_path):
    """Heartbeat exists but datetime is unparseable -> OPS_STATUS_CRITICAL."""
    _configure_tmp_db(monkeypatch, tmp_path)
    se.touch_worker_heartbeat(note="test")

    # Set heartbeat to an unparseable string
    conn = se._conn()
    conn.execute(
        "UPDATE worker_runtime SET last_heartbeat = ? WHERE worker_name = ?",
        ("invalid-datetime-format", se.WORKER_NAME_DEFAULT),
    )
    conn.commit()
    conn.close()

    summary = se.get_scheduler_ops_summary(stale_after_sec=180)
    assert summary["status"] == se.OPS_STATUS_CRITICAL
    assert summary["seconds_since_heartbeat"] is None
    assert summary["is_stale"] is True
    assert "형식" in summary["next_action"]


def test_scheduler_ops_summary_warning_state(monkeypatch, tmp_path):
    """Worker heartbeat is older than stale_after_sec//2 but not stale -> WARNING."""
    _configure_tmp_db(monkeypatch, tmp_path)
    se.touch_worker_heartbeat(note="half-stale")

    from datetime import datetime as _dt, timedelta as _td

    # Set heartbeat to stale_after_sec//2 + 10 seconds ago (triggers warning but not critical)
    stale_sec = 180
    half_plus = stale_sec // 2 + 10  # 100 seconds ago
    old_time = (_dt.now() - _td(seconds=half_plus)).strftime("%Y-%m-%d %H:%M:%S")

    conn = se._conn()
    conn.execute(
        "UPDATE worker_runtime SET last_heartbeat = ?, updated_at = ? WHERE worker_name = ?",
        (old_time, old_time, se.WORKER_NAME_DEFAULT),
    )
    conn.commit()
    conn.close()

    summary = se.get_scheduler_ops_summary(stale_after_sec=stale_sec)
    assert summary["status"] == se.OPS_STATUS_WARNING
    assert summary["is_stale"] is False
    assert "점검" in summary["next_action"]


# ---------------------------------------------------------------------------
# get_attention_queue edge cases (lines 855-902)
# ---------------------------------------------------------------------------


def test_get_attention_queue_empty_when_all_healthy(monkeypatch, tmp_path):
    """No disabled/failed/overdue tasks -> empty queue."""
    _configure_tmp_db(monkeypatch, tmp_path)
    se.add_task(
        name="healthy-task",
        executable="python",
        args=["-c", "print('ok')"],
        cwd=".",
        cron_expression="*/5 * * * *",
    )

    queue = se.get_attention_queue(limit=10)
    assert queue == []


def test_get_attention_queue_repeated_failures_only(monkeypatch, tmp_path):
    """Task with repeated failures but still enabled -> 'repeated_failures' reason."""
    _configure_tmp_db(monkeypatch, tmp_path)

    # Create task and manually set failure_count high but keep enabled
    task_id = se.add_task(
        name="failing-task",
        executable="python",
        args=["-c", "print('ok')"],
        cwd=".",
        cron_expression="*/5 * * * *",
    )
    failure_threshold = max(2, se.MAX_FAILURE_COUNT // 2)

    conn = se._conn()
    conn.execute(
        "UPDATE tasks SET failure_count = ? WHERE id = ?",
        (failure_threshold, task_id),
    )
    conn.commit()
    conn.close()

    queue = se.get_attention_queue(limit=10)
    task_entry = next(item for item in queue if item["task_id"] == task_id)
    assert "repeated_failures" in task_entry["reasons"]
    assert "연속 실패" in task_entry["next_action"]


# ---------------------------------------------------------------------------
# get_scheduler_ops_summary: persisted status=setup_required (line 383)
# ---------------------------------------------------------------------------


def test_scheduler_ops_summary_setup_required_status(monkeypatch, tmp_path):
    """Persisted status 'setup_required' triggers setup next_action."""
    from datetime import datetime as _dt

    _configure_tmp_db(monkeypatch, tmp_path)
    # Insert heartbeat with status=setup_required and recent timestamp
    conn = se._conn()
    now_str = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO worker_runtime (worker_name, last_heartbeat, status, note, updated_at) VALUES (?, ?, ?, ?, ?)",
        (se.WORKER_NAME_DEFAULT, now_str, se.OPS_STATUS_SETUP_REQUIRED, "needs setup", now_str),
    )
    conn.commit()
    conn.close()
    result = se.get_scheduler_ops_summary()
    assert result["status"] == se.OPS_STATUS_SETUP_REQUIRED
    assert "워커를 실행" in result["next_action"]


# ---------------------------------------------------------------------------
# get_attention_queue: disabled task (line 855)
# ---------------------------------------------------------------------------


def test_recent_failure_summary_disabled_task(monkeypatch, tmp_path):
    """Disabled task in get_recent_failure_summary gets '오류 수정 후 재활성화' (line 855)."""
    _configure_tmp_db(monkeypatch, tmp_path)
    task_id = se.add_task("disabled_task", "echo", ["disabled"], str(tmp_path), "*/5 * * * *")
    # Disable the task and add a failure
    conn = se._conn()
    conn.execute("UPDATE tasks SET enabled = 0, failure_count = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    summary = se.get_recent_failure_summary(limit=10)
    task_entry = next(item for item in summary if item["task_id"] == task_id)
    assert task_entry["enabled"] is False
    assert task_entry["next_action"] == "오류 수정 후 재활성화"
