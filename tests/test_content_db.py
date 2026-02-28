from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta

import execution.content_db as cdb


def _patch_db(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cdb, "DB_PATH", tmp_path / "content.db")
    cdb.init_db()


def _table_columns(db_path) -> set[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("PRAGMA table_info(content_queue)").fetchall()
        return {row[1] for row in rows}
    finally:
        conn.close()


def test_init_db_migrates_legacy_channel_column(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy_content.db"
    monkeypatch.setattr(cdb, "DB_PATH", db_path)

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE content_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT DEFAULT ''
        )
        """
    )
    conn.commit()
    conn.close()

    cdb.init_db()

    assert "channel" in _table_columns(db_path)


def test_add_get_update_delete_and_channels(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    first_id = cdb.add_topic("  Black Holes  ", notes="  urgent ", channel="  space ")
    second_id = cdb.add_topic("Ancient Rome", channel="history")

    all_items = cdb.get_all()
    assert {item["topic"] for item in all_items} == {"Black Holes", "Ancient Rome"}

    space_items = cdb.get_all(channel="space")
    assert len(space_items) == 1
    assert space_items[0]["notes"] == "urgent"
    assert cdb.get_channels() == ["history", "space"]

    cdb.update_job(first_id, status="success", job_id="job-1", cost_usd=1.25, duration_sec=31.5)
    updated = next(item for item in cdb.get_all() if item["id"] == first_id)
    assert updated["status"] == "success"
    assert updated["job_id"] == "job-1"
    assert updated["cost_usd"] == 1.25
    assert updated["duration_sec"] == 31.5
    assert updated["updated_at"]

    # No-op update should leave the record intact.
    cdb.update_job(first_id)
    same_row = next(item for item in cdb.get_all() if item["id"] == first_id)
    assert same_row["job_id"] == "job-1"

    cdb.delete_item(second_id)
    remaining_ids = [item["id"] for item in cdb.get_all()]
    assert remaining_ids == [first_id]


def test_update_job_rejects_unknown_fields(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    row_id = cdb.add_topic("Black Holes", channel="space")

    try:
        cdb.update_job(row_id, unexpected="value")
    except ValueError as exc:
        assert "unexpected" in str(exc)
    else:  # pragma: no cover - safety assertion
        raise AssertionError("Expected ValueError for unsupported update field")


def test_get_kpis_daily_stats_and_channel_stats(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    success_id = cdb.add_topic("Space Topic", channel="space")
    failed_id = cdb.add_topic("Moon Topic", channel="space")
    pending_id = cdb.add_topic("History Topic", channel="history")

    conn = cdb._conn()
    try:
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'success', cost_usd = 2.5, duration_sec = 42.0, updated_at = ?, created_at = ?
            WHERE id = ?
            """,
            (today, today, success_id),
        )
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'failed', cost_usd = 1.0, duration_sec = 0.0, updated_at = ?, created_at = ?
            WHERE id = ?
            """,
            (yesterday, yesterday, failed_id),
        )
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'pending', updated_at = ?, created_at = ?
            WHERE id = ?
            """,
            (today, today, pending_id),
        )
        conn.commit()
    finally:
        conn.close()

    kpis = cdb.get_kpis()
    assert kpis["total"] == 3
    assert kpis["success_count"] == 1
    assert kpis["failed_count"] == 1
    assert kpis["pending_count"] == 1
    assert kpis["running_count"] == 0
    assert kpis["total_cost_usd"] == 3.5
    assert kpis["avg_cost_usd"] == 2.5

    space_kpis = cdb.get_kpis(channel="space")
    assert space_kpis["total"] == 2
    assert space_kpis["failed_count"] == 1

    daily_stats = cdb.get_daily_stats(days=2)
    assert len(daily_stats) == 2
    assert sum(item["total"] for item in daily_stats) == 2
    assert sum(item["cost_usd"] for item in daily_stats) == 3.5

    channel_stats = {item["channel"]: item for item in cdb.get_channel_stats()}
    assert channel_stats["space"]["total"] == 2
    assert channel_stats["space"]["success"] == 1
    assert channel_stats["space"]["failed"] == 1
    assert channel_stats["space"]["total_cost"] == 3.5
    assert channel_stats["space"]["avg_cost"] == 2.5
    assert channel_stats["space"]["avg_duration"] == 42.0
    assert channel_stats["history"]["pending"] == 1


def test_get_top_performing_topics_and_hourly_stats(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    best_id = cdb.add_topic("Cheap win", channel="space")
    pricey_id = cdb.add_topic("Expensive win", channel="space")
    other_channel_id = cdb.add_topic("History win", channel="history")

    conn = cdb._conn()
    try:
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'success', cost_usd = 0.25, duration_sec = 15.0, updated_at = '2026-02-28 09:10:00'
            WHERE id = ?
            """,
            (best_id,),
        )
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'success', cost_usd = 1.50, duration_sec = 18.0, updated_at = '2026-02-28 09:30:00'
            WHERE id = ?
            """,
            (pricey_id,),
        )
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'success', cost_usd = 0.75, duration_sec = 12.0, updated_at = '2026-02-28 10:00:00'
            WHERE id = ?
            """,
            (other_channel_id,),
        )
        conn.commit()
    finally:
        conn.close()

    top_topics = cdb.get_top_performing_topics(limit=2, channel="space")
    assert [item["topic"] for item in top_topics] == ["Cheap win", "Expensive win"]

    hourly = cdb.get_hourly_stats(days=4000)
    by_hour = {item["hour"]: item for item in hourly}
    assert by_hour[9]["total"] == 2
    assert by_hour[9]["success"] == 2
    assert by_hour[9]["success_rate"] == 100.0
    assert by_hour[10]["total"] == 1


def test_cli_commands(monkeypatch, tmp_path, capsys):
    _patch_db(monkeypatch, tmp_path)

    monkeypatch.setattr(sys, "argv", ["content_db.py", "init"])
    cdb._cli()
    assert "DB 초기화 완료" in capsys.readouterr().out

    monkeypatch.setattr(
        sys,
        "argv",
        ["content_db.py", "add", "--topic", "Comets", "--notes", "watch", "--channel", "space"],
    )
    cdb._cli()
    add_output = capsys.readouterr().out
    assert "추가 완료" in add_output
    assert "Comets" in add_output

    monkeypatch.setattr(sys, "argv", ["content_db.py", "list", "--channel", "space"])
    cdb._cli()
    list_output = capsys.readouterr().out
    assert "Comets" in list_output
    assert "pending" in list_output

    monkeypatch.setattr(sys, "argv", ["content_db.py", "channels"])
    cdb._cli()
    assert capsys.readouterr().out.strip() == "space"

    monkeypatch.setattr(sys, "argv", ["content_db.py", "kpis"])
    cdb._cli()
    kpi_output = capsys.readouterr().out
    payload = json.loads(kpi_output)
    assert payload["total"] == 1


def test_cli_prints_help_without_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["content_db.py"])

    cdb._cli()

    assert "usage:" in capsys.readouterr().out.lower()
