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


# ---------------------------------------------------------------------------
# upsert_channel_settings — invalid fields ValueError (line 189)
# ---------------------------------------------------------------------------


def test_upsert_channel_settings_invalid_field(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    try:
        cdb.upsert_channel_settings("space", bad_field="bad")
    except ValueError as exc:
        assert "bad_field" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported field")


# ---------------------------------------------------------------------------
# get_youtube_stats — zero row (line 390)
# ---------------------------------------------------------------------------


def test_get_youtube_stats_empty_db(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    stats = cdb.get_youtube_stats()
    assert stats == {"uploaded": 0, "failed": 0, "awaiting": 0}


# ---------------------------------------------------------------------------
# _derive_ops_status / _derive_next_action branches (lines 437, 450-454)
# ---------------------------------------------------------------------------


def test_derive_ops_status_critical():
    assert cdb._derive_ops_status(["critical:something"]) == cdb.OPS_STATUS_CRITICAL


def test_derive_ops_status_healthy():
    assert cdb._derive_ops_status([]) == cdb.OPS_STATUS_HEALTHY


def test_derive_next_action_bgm_missing():
    assert cdb._derive_next_action(["warning:bgm_missing"]) == "BGM 추가 또는 스킵 확인"


def test_derive_next_action_failed_jobs():
    assert cdb._derive_next_action(["warning:failed_jobs"]) == "실패 건 확인"


def test_derive_next_action_fallback():
    assert cdb._derive_next_action(["unknown:something"]) == "운영 상태 점검"


# ---------------------------------------------------------------------------
# get_recent_failure_items — channel filter, various issue branches
# (lines 530-531, 546, 553, 556-561)
# ---------------------------------------------------------------------------


def test_get_recent_failure_items_with_channel_filter(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    bgm_dir = tmp_path / "shorts-maker-v2" / "assets" / "bgm"
    brand_dir = tmp_path / "shorts-maker-v2" / "assets" / "channels"
    monkeypatch.setattr(cdb, "_SHORTS_BGM_DIR", bgm_dir)
    monkeypatch.setattr(cdb, "_SHORTS_BRAND_DIR", brand_dir)

    cdb.upsert_channel_settings("space", voice="nova")
    space_id = cdb.add_topic("Mars", channel="space")
    cdb.update_job(space_id, status="failed")

    hist_id = cdb.add_topic("Rome", channel="history")
    cdb.update_job(hist_id, status="failed")

    # Filter by channel
    space_failures = cdb.get_recent_failure_items(channel="space", limit=10)
    assert len(space_failures) == 1
    assert space_failures[0]["channel"] == "space"


def test_get_recent_failure_items_no_settings_issue(monkeypatch, tmp_path):
    """채널 설정이 없으면 setup: 이슈와 '채널 설정 저장 후 재실행' next_action."""
    _patch_db(monkeypatch, tmp_path)
    bgm_dir = tmp_path / "shorts-maker-v2" / "assets" / "bgm"
    brand_dir = tmp_path / "shorts-maker-v2" / "assets" / "channels"
    monkeypatch.setattr(cdb, "_SHORTS_BGM_DIR", bgm_dir)
    monkeypatch.setattr(cdb, "_SHORTS_BRAND_DIR", brand_dir)

    # No settings for this channel
    fid = cdb.add_topic("NoSettings", channel="orphan")
    cdb.update_job(fid, status="failed")

    failures = cdb.get_recent_failure_items(limit=5)
    item = [f for f in failures if f["channel"] == "orphan"][0]
    assert "setup:channel_settings_missing" in item["issues"]
    assert item["next_action"] == "채널 설정 저장 후 재실행"
    assert item["has_settings"] is False
    assert item["retry_recommended"] is False


def test_get_recent_failure_items_no_notes_next_action(monkeypatch, tmp_path):
    """메모 없는 실패 건 → '최근 로그 확인 후 재실행'."""
    _patch_db(monkeypatch, tmp_path)
    bgm_dir = tmp_path / "shorts-maker-v2" / "assets" / "bgm"
    brand_dir = tmp_path / "shorts-maker-v2" / "assets" / "channels"
    # Create BGM so bgm_missing is not an issue
    bgm_dir.mkdir(parents=True, exist_ok=True)
    (bgm_dir / "calm.mp3").write_bytes(b"mp3")
    # Create brand assets
    ch_dir = brand_dir / "test_ch"
    ch_dir.mkdir(parents=True, exist_ok=True)
    (ch_dir / "intro.png").write_bytes(b"png")
    (ch_dir / "outro.png").write_bytes(b"png")
    monkeypatch.setattr(cdb, "_SHORTS_BGM_DIR", bgm_dir)
    monkeypatch.setattr(cdb, "_SHORTS_BRAND_DIR", brand_dir)

    cdb.upsert_channel_settings("test_ch", voice="nova")
    fid = cdb.add_topic("NoNotes", channel="test_ch")
    cdb.update_job(fid, status="failed")

    failures = cdb.get_recent_failure_items(limit=5)
    item = [f for f in failures if f["topic"] == "NoNotes"][0]
    assert item["next_action"] == "최근 로그 확인 후 재실행"


def test_get_recent_failure_items_with_notes_next_action(monkeypatch, tmp_path):
    """메모 있는 실패 건 → '실패 메모 확인 후 재실행'."""
    _patch_db(monkeypatch, tmp_path)
    bgm_dir = tmp_path / "shorts-maker-v2" / "assets" / "bgm"
    brand_dir = tmp_path / "shorts-maker-v2" / "assets" / "channels"
    bgm_dir.mkdir(parents=True, exist_ok=True)
    (bgm_dir / "calm.mp3").write_bytes(b"mp3")
    ch_dir = brand_dir / "note_ch"
    ch_dir.mkdir(parents=True, exist_ok=True)
    (ch_dir / "intro.png").write_bytes(b"png")
    (ch_dir / "outro.png").write_bytes(b"png")
    monkeypatch.setattr(cdb, "_SHORTS_BGM_DIR", bgm_dir)
    monkeypatch.setattr(cdb, "_SHORTS_BRAND_DIR", brand_dir)

    cdb.upsert_channel_settings("note_ch", voice="nova")
    fid = cdb.add_topic("WithNotes", notes="render timeout", channel="note_ch")
    cdb.update_job(fid, status="failed")

    failures = cdb.get_recent_failure_items(limit=5)
    item = [f for f in failures if f["topic"] == "WithNotes"][0]
    assert item["next_action"] == "실패 메모 확인 후 재실행"
    assert item["failure_reason"] == "render timeout"


# ---------------------------------------------------------------------------
# _load_manifest_payloads — edge cases (lines 581, 592-593, 595)
# ---------------------------------------------------------------------------


def test_load_manifest_payloads_nonexistent_dir(tmp_path):
    result = cdb._load_manifest_payloads(output_dir=tmp_path / "nonexistent")
    assert result == []


def test_load_manifest_payloads_invalid_json(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "bad_manifest.json").write_text("not valid json{{{", encoding="utf-8")
    result = cdb._load_manifest_payloads(output_dir=output_dir)
    assert result == []


def test_load_manifest_payloads_non_dict_json(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "list_manifest.json").write_text("[1, 2, 3]", encoding="utf-8")
    result = cdb._load_manifest_payloads(output_dir=output_dir)
    assert result == []


# ---------------------------------------------------------------------------
# get_manifest_sync_diffs — manifest with empty job_id (line 619)
# ---------------------------------------------------------------------------


def test_manifest_sync_diffs_skips_empty_job_id(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(cdb, "_SHORTS_OUTPUT_DIR", output_dir)

    # Manifest with no job_id
    (output_dir / "empty_manifest.json").write_text(
        json.dumps({"title": "No Job ID", "status": "success"}),
        encoding="utf-8",
    )
    diff = cdb.get_manifest_sync_diffs(output_dir=output_dir, limit=10)
    assert diff["summary"]["missing_in_db_count"] == 0


# ---------------------------------------------------------------------------
# get_review_queue_items / get_uploadable_items — channel filter (lines 713-714)
# ---------------------------------------------------------------------------


def test_get_review_queue_items_channel_filter(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    video = tmp_path / "vid.mp4"
    video.write_bytes(b"video")

    s1 = cdb.add_topic("Space Vid", channel="space")
    cdb.update_job(s1, status="success", video_path=str(video))

    h1 = cdb.add_topic("History Vid", channel="history")
    cdb.update_job(h1, status="success", video_path=str(video))

    queue = cdb.get_review_queue_items(channel="space", limit=10)
    assert len(queue) == 1
    assert queue[0]["channel"] == "space"


def test_get_upload_queue_channel_filter(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    s1 = cdb.add_topic("Space Upload", channel="space")
    cdb.update_job(s1, status="success", video_path="space.mp4")

    h1 = cdb.add_topic("History Upload", channel="history")
    cdb.update_job(h1, status="success", video_path="history.mp4")

    items = cdb.get_uploadable_items(channel="space", limit=10)
    assert len(items) == 1
    assert items[0]["channel"] == "space"


# ---------------------------------------------------------------------------
# get_performance_stats — channel filter, min_views (lines 788-804)
# ---------------------------------------------------------------------------


def test_get_performance_stats_with_filters(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    s1 = cdb.add_topic("High Views", channel="space")
    s2 = cdb.add_topic("Low Views", channel="space")
    s3 = cdb.add_topic("History Views", channel="history")
    cdb.update_job(s1, status="success", video_path="a.mp4")

    conn = cdb._conn()
    try:
        conn.execute(
            "UPDATE content_queue SET youtube_status='uploaded', yt_views=5000, hook_pattern='question' WHERE id=?",
            (s1,),
        )
        conn.execute(
            "UPDATE content_queue SET status='success', youtube_status='uploaded', yt_views=10, hook_pattern='stat' WHERE id=?",
            (s2,),
        )
        conn.execute(
            "UPDATE content_queue SET status='success', youtube_status='uploaded', yt_views=3000, hook_pattern='question' WHERE id=?",
            (s3,),
        )
        conn.commit()
    finally:
        conn.close()

    # Channel filter
    space_stats = cdb.get_performance_stats(channel="space")
    assert all(s["channel"] == "space" for s in space_stats)
    assert len(space_stats) == 2

    # min_views filter
    high_stats = cdb.get_performance_stats(min_views=1000)
    assert all(s["yt_views"] >= 1000 for s in high_stats)
    assert len(high_stats) == 2

    # Both filters
    combined = cdb.get_performance_stats(channel="space", min_views=1000)
    assert len(combined) == 1
    assert combined[0]["topic"] == "High Views"


# ---------------------------------------------------------------------------
# get_hook_pattern_performance (lines 809-826)
# ---------------------------------------------------------------------------


def test_get_hook_pattern_performance(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    topic_ids = []
    data = [("question", 5000), ("question", 3000), ("stat", 1000)]
    for i, (hook, views) in enumerate(data):
        topic_ids.append(cdb.add_topic(f"Topic{i}", channel="space"))

    conn = cdb._conn()
    try:
        for (hook, views), topic_id in zip(data, topic_ids):
            conn.execute(
                "UPDATE content_queue SET status='success', youtube_status='uploaded', "
                "yt_views=?, yt_likes=?, yt_ctr=?, yt_avg_watch_sec=?, hook_pattern=? WHERE id=?",
                (views, views // 10, 5.0, 30.0, hook, topic_id),
            )
        conn.commit()
    finally:
        conn.close()

    results = cdb.get_hook_pattern_performance()
    assert len(results) == 2
    # Sorted by avg_views DESC
    assert results[0]["hook_pattern"] == "question"
    assert results[0]["count"] == 2
    assert results[0]["avg_views"] == 4000.0


# ---------------------------------------------------------------------------
# get_channel_performance_summary (lines 831-848)
# ---------------------------------------------------------------------------


def test_get_channel_performance_summary(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)

    data = [("space", 5000, 1.0), ("space", 3000, 0.5), ("history", 2000, 0.75)]
    topic_ids = []
    for channel, views, cost in data:
        topic_ids.append(cdb.add_topic(f"T-{channel}-{views}", channel=channel))

    conn = cdb._conn()
    try:
        for (channel, views, cost), topic_id in zip(data, topic_ids):
            conn.execute(
                "UPDATE content_queue SET status='success', youtube_status='uploaded', "
                "yt_views=?, cost_usd=?, yt_ctr=5.0, yt_avg_watch_sec=30.0 WHERE id=?",
                (views, cost, topic_id),
            )
        conn.commit()
    finally:
        conn.close()

    results = cdb.get_channel_performance_summary()
    assert len(results) == 2
    by_channel = {r["channel"]: r for r in results}
    assert by_channel["space"]["video_count"] == 2
    assert by_channel["space"]["total_views"] == 8000
    assert by_channel["history"]["video_count"] == 1
    assert by_channel["history"]["total_cost"] == 0.75


# ---------------------------------------------------------------------------
# CLI channel-get with no settings (line 920)
# ---------------------------------------------------------------------------


def test_cli_channel_get_no_settings(monkeypatch, tmp_path, capsys):
    _patch_db(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["content_db.py", "channel-get", "--channel", "nonexistent"])
    cdb._cli()
    output = capsys.readouterr().out
    assert "설정 없음" in output


# ---------------------------------------------------------------------------
# get_youtube_stats empty table returns default (line 390)
# ---------------------------------------------------------------------------


def test_get_youtube_stats_empty_table(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    result = cdb.get_youtube_stats()
    assert result["uploaded"] == 0
    assert result["failed"] == 0
    assert result["awaiting"] == 0


# ---------------------------------------------------------------------------
# get_recent_failure_items: bgm_missing only path (line 557)
# ---------------------------------------------------------------------------


def test_get_recent_failure_items_bgm_missing_only(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    cdb.upsert_channel_settings("testch", voice="nova")
    item_id = cdb.add_topic("fail topic", channel="testch")
    cdb.update_job(item_id, status="failed")
    monkeypatch.setattr(cdb, "_resolve_bgm_readiness", lambda: False)
    monkeypatch.setattr(cdb, "_resolve_brand_asset_readiness", lambda ch: True)
    failures = cdb.get_recent_failure_items(channel="testch")
    assert len(failures) >= 1
    assert failures[0]["next_action"] == "BGM 스킵 가능 여부 확인"


# ---------------------------------------------------------------------------
# _check_manifest_vs_db / _check_db_vs_manifests tests (T-114)
# ---------------------------------------------------------------------------


def test_check_manifest_vs_db_missing_in_db():
    manifests = [
        {"job_id": "j1", "title": "T1", "status": "success", "_manifest_path": "/p/m1.json"},
    ]
    missing_in_db, pending_sync = cdb._check_manifest_vs_db(manifests, {})
    assert len(missing_in_db) == 1
    assert missing_in_db[0]["job_id"] == "j1"
    assert pending_sync == []


def test_check_manifest_vs_db_pending_sync():
    manifests = [
        {
            "job_id": "j2",
            "title": "New Title",
            "status": "success",
            "output_path": "/new/video.mp4",
            "_manifest_path": "/p/m2.json",
        }
    ]
    job_lookup = {
        "j2": {
            "id": 10,
            "job_id": "j2",
            "status": "pending",
            "title": "Old Title",
            "video_path": "/old/video.mp4",
            "topic": "T",
            "channel": "CH",
        }
    }
    missing_in_db, pending_sync = cdb._check_manifest_vs_db(manifests, job_lookup)
    assert missing_in_db == []
    assert len(pending_sync) == 1
    assert "status" in pending_sync[0]["mismatches"]
    assert "video_path" in pending_sync[0]["mismatches"]
    assert "title" in pending_sync[0]["mismatches"]


def test_check_manifest_vs_db_no_job_id_skipped():
    manifests = [{"title": "NoId", "_manifest_path": "/p/m3.json"}]
    missing_in_db, pending_sync = cdb._check_manifest_vs_db(manifests, {})
    assert missing_in_db == []
    assert pending_sync == []


def test_check_db_vs_manifests_missing_manifest():
    items = [{"id": 1, "job_id": "j3", "topic": "T", "channel": "C", "status": "pending", "video_path": ""}]
    missing_output_file, missing_manifest = cdb._check_db_vs_manifests(items, set())
    assert len(missing_manifest) == 1
    assert missing_manifest[0]["job_id"] == "j3"
    assert missing_output_file == []


def test_check_db_vs_manifests_missing_output_file(tmp_path):
    items = [
        {
            "id": 2,
            "job_id": "j4",
            "topic": "T",
            "channel": "C",
            "status": "success",
            "video_path": str(tmp_path / "nonexistent.mp4"),
        }
    ]
    missing_output_file, missing_manifest = cdb._check_db_vs_manifests(items, {"j4"})
    assert len(missing_output_file) == 1
    assert missing_output_file[0]["job_id"] == "j4"
    assert missing_manifest == []


def test_check_db_vs_manifests_no_issues(tmp_path):
    video = tmp_path / "ok.mp4"
    video.write_bytes(b"")
    items = [
        {
            "id": 3,
            "job_id": "j5",
            "topic": "T",
            "channel": "C",
            "status": "success",
            "video_path": str(video),
        }
    ]
    missing_output_file, missing_manifest = cdb._check_db_vs_manifests(items, {"j5"})
    assert missing_output_file == []
    assert missing_manifest == []
