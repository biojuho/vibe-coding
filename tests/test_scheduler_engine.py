from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import execution.scheduler_engine as se


def _configure_tmp_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(se, "DB_PATH", tmp_path / "scheduler.db")
    monkeypatch.setattr(se, "WORKSPACE", tmp_path)
    se.init_db()


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
