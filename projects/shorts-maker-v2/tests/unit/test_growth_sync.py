from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from shorts_maker_v2.growth.sync import sync_growth_report


def _make_config() -> SimpleNamespace:
    return SimpleNamespace(
        paths=SimpleNamespace(output_dir="output", logs_dir="logs", runs_dir="runs"),
    )


def _write_manifest(
    output_dir: Path,
    *,
    job_id: str,
    topic: str,
    status: str = "success",
    ab_variant: dict[str, str] | None = None,
) -> None:
    payload = {
        "job_id": job_id,
        "topic": topic,
        "status": status,
        "created_at": "2026-04-05T00:00:00+00:00",
        "ab_variant": ab_variant or {"caption_combo": "bold_white"},
    }
    (output_dir / f"{job_id}_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_sync_growth_report_refreshes_and_writes_ranked_report(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    _write_manifest(
        output_dir,
        job_id="job-1",
        topic="AI agents",
        ab_variant={"caption_combo": "winner", "hook_pattern": "question"},
    )
    _write_manifest(
        output_dir,
        job_id="job-2",
        topic="Legacy miss",
        status="failed",
        ab_variant={"caption_combo": "ignored"},
    )

    fake_db = SimpleNamespace(
        init_db=lambda: None,
        get_all=lambda channel=None: [
            {
                "job_id": "job-1",
                "channel": "ai_tech",
                "topic": "AI agents",
                "youtube_status": "uploaded",
                "youtube_video_id": "vid-1",
                "yt_views": 18000,
                "yt_likes": 920,
                "yt_comments": 140,
                "yt_avg_watch_sec": 27.0,
                "yt_ctr": 0.045,
                "duration_sec": 36.0,
                "yt_stats_updated_at": "2026-04-05 10:00:00",
                "youtube_uploaded_at": "2026-04-04 10:00:00",
                "updated_at": "2026-04-05 10:00:00",
            },
            {
                "job_id": "job-missing",
                "channel": "ai_tech",
                "topic": "No manifest",
                "youtube_status": "uploaded",
                "youtube_video_id": "vid-2",
                "yt_views": 99999,
                "yt_likes": 10,
                "yt_comments": 2,
                "yt_avg_watch_sec": 5.0,
                "yt_ctr": 0.01,
                "duration_sec": 40.0,
                "yt_stats_updated_at": "2026-04-05 10:00:00",
                "youtube_uploaded_at": "2026-04-04 10:00:00",
                "updated_at": "2026-04-05 10:00:00",
            },
        ],
    )
    fake_collector = SimpleNamespace(
        collect_and_update=lambda channel=None: {"updated": 1, "skipped": 0, "errors": []},
    )

    monkeypatch.setattr("shorts_maker_v2.growth.sync._load_content_db_module", lambda: fake_db)
    monkeypatch.setattr("shorts_maker_v2.growth.sync._load_youtube_collector_module", lambda: fake_collector)

    result = sync_growth_report(
        config=_make_config(),
        base_dir=tmp_path,
        channel="ai_tech",
        since_days=30,
        variant_field="caption_combo",
    )

    assert result.snapshot_count == 1
    assert result.refresh_summary["status"] == "ok"
    assert result.report.ranked_variants[0].variant == "winner"
    assert result.report.ranked_variants[0].average_view_percentage == 75.0
    assert result.report_path.exists()

    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["snapshot_count"] == 1
    assert payload["report"]["ranked_variants"][0]["variant"] == "winner"


def test_sync_growth_report_keeps_existing_metrics_when_refresh_fails(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    _write_manifest(output_dir, job_id="job-1", topic="AI agents")

    fake_db = SimpleNamespace(
        init_db=lambda: None,
        get_all=lambda channel=None: [
            {
                "job_id": "job-1",
                "channel": "ai_tech",
                "topic": "AI agents",
                "youtube_status": "uploaded",
                "youtube_video_id": "vid-1",
                "yt_views": 5400,
                "yt_likes": 210,
                "yt_comments": 36,
                "yt_avg_watch_sec": 16.0,
                "yt_ctr": 0.031,
                "duration_sec": 32.0,
                "yt_stats_updated_at": "2026-04-05 10:00:00",
                "youtube_uploaded_at": "2026-04-04 10:00:00",
                "updated_at": "2026-04-05 10:00:00",
            }
        ],
    )

    def _boom():
        raise RuntimeError("oauth missing")

    monkeypatch.setattr("shorts_maker_v2.growth.sync._load_content_db_module", lambda: fake_db)
    monkeypatch.setattr("shorts_maker_v2.growth.sync._load_youtube_collector_module", _boom)

    result = sync_growth_report(
        config=_make_config(),
        base_dir=tmp_path,
        channel="ai_tech",
        refresh_metrics=True,
    )

    assert result.snapshot_count == 1
    assert result.refresh_summary["status"] == "failed"
    assert "oauth missing" in result.refresh_summary["errors"][0]
