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
    assert "youtube_error" in _table_columns(db_path)


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


def test_get_youtube_stats_and_uploadable_filters(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    uploadable_id = cdb.add_topic("Ready upload", channel="space")
    retry_id = cdb.add_topic("Retry upload", channel="space")
    uploaded_id = cdb.add_topic("Done upload", channel="history")

    conn = cdb._conn()
    try:
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'success', video_path = 'ready.mp4', youtube_status = ''
            WHERE id = ?
            """,
            (uploadable_id,),
        )
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'success', video_path = 'retry.mp4', youtube_status = 'failed', youtube_error = 'boom'
            WHERE id = ?
            """,
            (retry_id,),
        )
        conn.execute(
            """
            UPDATE content_queue
            SET status = 'success', video_path = 'done.mp4', youtube_status = 'uploaded', youtube_url = 'https://youtu.be/abc'
            WHERE id = ?
            """,
            (uploaded_id,),
        )
        conn.commit()
    finally:
        conn.close()

    yt_stats = cdb.get_youtube_stats()
    assert yt_stats == {"uploaded": 1, "failed": 1, "awaiting": 1}

    uploadable = cdb.get_uploadable_items(channel="space", limit=10)
    assert [item["id"] for item in uploadable] == [uploadable_id]

    retryable = cdb.get_uploadable_items(channel="space", limit=10, include_failed=True)
    assert {item["id"] for item in retryable} == {uploadable_id, retry_id}


def test_channel_settings_roundtrip(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    cdb.upsert_channel_settings(
        "space",
        voice="nova",
        style_preset="neon",
        font_color="#00FFAA",
        image_style_prefix="cinematic",
    )
    settings = cdb.get_channel_settings("space")
    assert settings is not None
    assert settings["voice"] == "nova"
    assert settings["style_preset"] == "neon"
    assert settings["font_color"] == "#00FFAA"
    assert settings["image_style_prefix"] == "cinematic"

    cdb.upsert_channel_settings("space", voice="alloy")
    updated = cdb.get_channel_settings("space")
    assert updated is not None
    assert updated["voice"] == "alloy"
    assert updated["style_preset"] == "neon"


def test_channel_readiness_summary_setup_required_without_settings(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    monkeypatch.setattr(cdb, "_SHORTS_BGM_DIR", tmp_path / "shorts-maker-v2" / "assets" / "bgm")
    monkeypatch.setattr(cdb, "_SHORTS_BRAND_DIR", tmp_path / "shorts-maker-v2" / "assets" / "channels")

    row_id = cdb.add_topic("Mars", channel="space")
    cdb.update_job(row_id, status="pending")

    summary = cdb.get_channel_readiness_summary(channels=["space"])
    assert len(summary) == 1
    item = summary[0]
    assert item["channel"] == "space"
    assert item["status"] == cdb.OPS_STATUS_SETUP_REQUIRED
    assert not item["has_settings"]
    assert item["next_action"] == "채널 설정 저장"
    assert "setup:channel_settings_missing" in item["issues"]


def test_channel_readiness_summary_warning_when_assets_missing(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    bgm_dir = tmp_path / "shorts-maker-v2" / "assets" / "bgm"
    brand_dir = tmp_path / "shorts-maker-v2" / "assets" / "channels"
    monkeypatch.setattr(cdb, "_SHORTS_BGM_DIR", bgm_dir)
    monkeypatch.setattr(cdb, "_SHORTS_BRAND_DIR", brand_dir)

    cdb.upsert_channel_settings(
        "space",
        voice="nova",
        style_preset="neon",
        font_color="#00FFAA",
        image_style_prefix="cinematic",
    )
    row_id = cdb.add_topic("Mars", channel="space")
    cdb.update_job(row_id, status="failed")

    summary = cdb.get_channel_readiness_summary(channels=["space"])
    item = summary[0]
    assert item["status"] == cdb.OPS_STATUS_WARNING
    assert item["has_settings"]
    assert not item["bgm_ready"]
    assert not item["brand_assets_ready"]
    assert item["failed_count"] == 1
    assert item["next_action"] in {"브랜드 에셋 생성", "BGM 추가 또는 스킵 확인", "실패 건 확인"}
    assert item["issues"]


def test_channel_readiness_summary_healthy_when_ready(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    bgm_dir = tmp_path / "shorts-maker-v2" / "assets" / "bgm"
    brand_dir = tmp_path / "shorts-maker-v2" / "assets" / "channels"
    (bgm_dir / "calm.mp3").parent.mkdir(parents=True, exist_ok=True)
    (bgm_dir / "calm.mp3").write_bytes(b"mp3")
    channel_brand_dir = brand_dir / "space"
    channel_brand_dir.mkdir(parents=True, exist_ok=True)
    (channel_brand_dir / "intro.png").write_bytes(b"png")
    (channel_brand_dir / "outro.png").write_bytes(b"png")
    monkeypatch.setattr(cdb, "_SHORTS_BGM_DIR", bgm_dir)
    monkeypatch.setattr(cdb, "_SHORTS_BRAND_DIR", brand_dir)

    cdb.upsert_channel_settings(
        "space",
        voice="nova",
        style_preset="neon",
        font_color="#00FFAA",
        image_style_prefix="cinematic",
    )
    row_id = cdb.add_topic("Mars", channel="space")
    cdb.update_job(row_id, status="success")

    summary = cdb.get_channel_readiness_summary(channels=["space"])
    item = summary[0]
    assert item["status"] == cdb.OPS_STATUS_HEALTHY
    assert item["bgm_ready"]
    assert item["brand_assets_ready"]
    assert item["issues"] == []
    assert item["next_action"] == "렌더 실행 가능"


def test_recent_failure_items_include_next_action(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    bgm_dir = tmp_path / "shorts-maker-v2" / "assets" / "bgm"
    brand_dir = tmp_path / "shorts-maker-v2" / "assets" / "channels"
    monkeypatch.setattr(cdb, "_SHORTS_BGM_DIR", bgm_dir)
    monkeypatch.setattr(cdb, "_SHORTS_BRAND_DIR", brand_dir)

    cdb.upsert_channel_settings("space", voice="nova")
    failed_id = cdb.add_topic("Mars", notes="render failed", channel="space")
    cdb.update_job(failed_id, status="failed")

    failures = cdb.get_recent_failure_items(limit=5)
    assert len(failures) == 1
    item = failures[0]
    assert item["id"] == failed_id
    assert item["failure_reason"] == "render failed"
    assert item["brand_assets_ready"] is False
    assert item["retry_recommended"] is True
    assert item["next_action"] in {"브랜드 에셋 확인 후 재실행", "BGM 스킵 가능 여부 확인"}


def test_manifest_sync_diffs_detects_mismatches(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    output_dir = tmp_path / "shorts-maker-v2" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cdb, "_SHORTS_OUTPUT_DIR", output_dir)

    sync_id = cdb.add_topic("Mars", channel="space")
    cdb.update_job(
        sync_id,
        status="running",
        job_id="job-sync",
        title="Old title",
        video_path="",
        thumbnail_path="",
    )

    missing_file_id = cdb.add_topic("Moon", channel="science")
    cdb.update_job(
        missing_file_id,
        status="success",
        job_id="job-missing-file",
        video_path=str(tmp_path / "missing.mp4"),
    )

    missing_manifest_id = cdb.add_topic("Venus", channel="space")
    existing_video = tmp_path / "venus.mp4"
    existing_video.write_bytes(b"video")
    cdb.update_job(
        missing_manifest_id,
        status="success",
        job_id="job-no-manifest",
        video_path=str(existing_video),
    )

    (output_dir / "job-sync_manifest.json").write_text(
        json.dumps(
            {
                "job_id": "job-sync",
                "status": "success",
                "title": "New title",
                "output_path": "new.mp4",
                "thumbnail_path": "thumb.png",
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "job-orphan_manifest.json").write_text(
        json.dumps(
            {
                "job_id": "job-orphan",
                "status": "success",
                "title": "Orphan",
                "output_path": "orphan.mp4",
            }
        ),
        encoding="utf-8",
    )

    diff = cdb.get_manifest_sync_diffs(output_dir=output_dir, limit=10)
    assert diff["summary"]["missing_in_db_count"] == 1
    assert diff["summary"]["pending_sync_count"] == 1
    assert diff["summary"]["missing_output_file_count"] == 1
    assert diff["summary"]["missing_manifest_count"] >= 1
    assert diff["missing_in_db"][0]["job_id"] == "job-orphan"
    assert diff["pending_sync"][0]["job_id"] == "job-sync"
    assert "status" in diff["pending_sync"][0]["mismatches"]
    assert diff["missing_output_file"][0]["job_id"] == "job-missing-file"


def test_review_queue_items_include_file_readiness(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    video_ok = tmp_path / "ok.mp4"
    thumb_ok = tmp_path / "ok.png"
    video_ok.write_bytes(b"video")
    thumb_ok.write_bytes(b"png")

    healthy_id = cdb.add_topic("Healthy", channel="space")
    cdb.update_job(
        healthy_id,
        status="success",
        video_path=str(video_ok),
        thumbnail_path=str(thumb_ok),
    )

    warning_id = cdb.add_topic("Missing thumb", channel="space")
    cdb.update_job(
        warning_id,
        status="success",
        video_path=str(video_ok),
        thumbnail_path=str(tmp_path / "missing-thumb.png"),
    )

    critical_id = cdb.add_topic("Missing video", channel="space")
    cdb.update_job(
        critical_id,
        status="success",
        video_path=str(tmp_path / "missing-video.mp4"),
        thumbnail_path="",
    )

    queue = cdb.get_review_queue_items(limit=10)
    by_topic = {item["topic"]: item for item in queue}

    assert by_topic["Healthy"]["review_status"] == cdb.OPS_STATUS_HEALTHY
    assert by_topic["Healthy"]["next_action"] == "수동 검수 진행"
    assert by_topic["Missing thumb"]["review_status"] == cdb.OPS_STATUS_WARNING
    assert by_topic["Missing thumb"]["thumbnail_exists"] is False
    assert by_topic["Missing video"]["review_status"] == cdb.OPS_STATUS_CRITICAL
    assert by_topic["Missing video"]["video_exists"] is False


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

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "content_db.py",
            "channel-set",
            "--channel",
            "space",
            "--voice",
            "nova",
            "--style-preset",
            "neon",
            "--font-color",
            "#00FFAA",
            "--image-prefix",
            "cinematic",
        ],
    )
    cdb._cli()
    assert "채널 설정 저장" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["content_db.py", "channel-get", "--channel", "space"])
    cdb._cli()
    channel_output = capsys.readouterr().out
    channel_payload = json.loads(channel_output)
    assert channel_payload["voice"] == "nova"
    assert channel_payload["style_preset"] == "neon"


def test_cli_prints_help_without_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["content_db.py"])

    cdb._cli()

    assert "usage:" in capsys.readouterr().out.lower()
