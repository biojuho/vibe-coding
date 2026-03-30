from __future__ import annotations

import importlib
import io
import os
import sys
import time
import types
from datetime import datetime, timedelta

import execution.shorts_daily_runner as sdr


def test_recover_stale_jobs_marks_only_old_running_items(monkeypatch):
    stale_time = (datetime.now() - timedelta(hours=sdr.STALE_HOURS + 1)).strftime("%Y-%m-%d %H:%M:%S")
    fresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items = [
        {"id": 1, "status": "running", "updated_at": stale_time},
        {"id": 2, "status": "running", "updated_at": fresh_time},
        {"id": 3, "status": "success", "updated_at": stale_time},
    ]
    updates = []

    monkeypatch.setattr(sdr, "get_all", lambda: items)
    monkeypatch.setattr(sdr, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))

    count = sdr._recover_stale_jobs()

    assert count == 1
    assert updates == [(1, {"status": "failed", "notes": "stale running → auto-failed"})]


def test_pick_topics_selects_oldest_pending_per_channel(monkeypatch):
    monkeypatch.setattr(sdr, "get_channels", lambda: ["history", "space"])

    def fake_get_all(channel=None):
        payloads = {
            "history": [
                {"id": 30, "status": "pending", "topic": "new history", "channel": "history"},
                {"id": 31, "status": "pending", "topic": "old history", "channel": "history"},
            ],
            "space": [
                {"id": 10, "status": "success", "topic": "done", "channel": "space"},
                {"id": 11, "status": "pending", "topic": "new space", "channel": "space"},
                {"id": 12, "status": "pending", "topic": "old space", "channel": "space"},
            ],
        }
        return payloads[channel]

    monkeypatch.setattr(sdr, "get_all", fake_get_all)

    selected = sdr.pick_topics(limit_per_channel=1)

    assert [item["topic"] for item in selected] == ["old history", "old space"]


def test_pick_topics_returns_empty_without_channels(monkeypatch):
    monkeypatch.setattr(sdr, "get_channels", lambda: [])

    assert sdr.pick_topics() == []


def test_find_latest_manifest_returns_newest_valid_payload(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    after_ts = datetime.now() - timedelta(seconds=10)
    now = time.time()

    older = output_dir / "older_manifest.json"
    older.write_text('{"status":"success","job_id":"old"}', encoding="utf-8")
    os.utime(older, (now - 20, now - 20))

    valid = output_dir / "valid_manifest.json"
    valid.write_text('{"status":"success","job_id":"new"}', encoding="utf-8")
    os.utime(valid, (now - 5, now - 5))

    invalid = output_dir / "invalid_manifest.json"
    invalid.write_text("{not json}", encoding="utf-8")
    os.utime(invalid, (now - 1, now - 1))

    manifest = sdr._find_latest_manifest(output_dir, after_ts)

    assert manifest == {"status": "success", "job_id": "new"}


def test_find_latest_manifest_returns_none_when_no_valid_candidate(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    after_ts = datetime.now() - timedelta(seconds=10)
    now = time.time()

    invalid = output_dir / "invalid_manifest.json"
    invalid.write_text("{not json}", encoding="utf-8")
    os.utime(invalid, (now - 1, now - 1))

    manifest = sdr._find_latest_manifest(output_dir, after_ts)

    assert manifest is None


def test_run_one_success_updates_job(monkeypatch):
    updates = []
    run_calls = []

    monkeypatch.setattr(sdr, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(
        sdr.subprocess,
        "run",
        lambda cmd, **kwargs: run_calls.append((cmd, kwargs)) or types.SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        sdr,
        "_find_latest_manifest",
        lambda output_dir, after_ts: {
            "status": "success",
            "job_id": "job-123",
            "title": "Fresh title",
            "output_path": "video.mp4",
            "thumbnail_path": "thumb.png",
            "estimated_cost_usd": 0.75,
            "total_duration_sec": 29.5,
        },
    )

    result = sdr.run_one({"id": 7, "topic": "Black holes", "channel": "space"})

    assert result["status"] == "success"
    assert result["cost"] == 0.75
    assert updates[0] == (7, {"status": "running"})
    assert updates[1][1]["status"] == "success"
    assert updates[1][1]["job_id"] == "job-123"
    assert run_calls[0][1]["cwd"] == str(sdr._V2_DIR)
    assert "--channel" in run_calls[0][0]
    assert "space" in run_calls[0][0]


def test_run_one_marks_timeout_as_failed(monkeypatch):
    updates = []

    monkeypatch.setattr(sdr, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(
        sdr.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            sdr.subprocess.TimeoutExpired(cmd="runner", timeout=sdr.RUN_TIMEOUT_SEC)
        ),
    )

    result = sdr.run_one({"id": 8, "topic": "Mars", "channel": "space"})

    assert result["status"] == "failed"
    assert result["reason"] == "timeout"
    assert updates[-1][1]["notes"] == f"timeout ({sdr.RUN_TIMEOUT_SEC}s)"


def test_run_one_marks_unexpected_exception_as_failed(monkeypatch):
    updates = []

    monkeypatch.setattr(sdr, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(
        sdr.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = sdr.run_one({"id": 9, "topic": "Venus", "channel": "space"})

    assert result["status"] == "failed"
    assert result["reason"] == "boom"
    assert updates[-1][1]["notes"] == "boom"


def test_run_one_uses_manifest_failed_steps_for_reason(monkeypatch):
    updates = []

    monkeypatch.setattr(sdr, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(sdr.subprocess, "run", lambda *args, **kwargs: types.SimpleNamespace(returncode=2))
    monkeypatch.setattr(
        sdr,
        "_find_latest_manifest",
        lambda output_dir, after_ts: {
            "status": "failed",
            "failed_steps": [{"step": "render", "message": "no assets"}],
        },
    )

    result = sdr.run_one({"id": 10, "topic": "Saturn", "channel": "space"})

    assert result["status"] == "failed"
    assert result["reason"] == "render: no assets"
    assert updates[-1][1]["notes"] == "render: no assets"


def test_main_returns_zero_when_no_topics(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["shorts_daily_runner.py"])
    monkeypatch.setattr(sdr, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(sdr, "init_db", lambda: None)
    monkeypatch.setattr(sdr, "_recover_stale_jobs", lambda: 0)
    monkeypatch.setattr(sdr, "pick_topics", lambda limit_per_channel: [])

    result = sdr.main()

    assert result == 0
    assert "대기 중인 주제가 없습니다" in capsys.readouterr().out


def test_main_dry_run_skips_execution(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["shorts_daily_runner.py", "--per-ch", "2", "--dry-run"])
    monkeypatch.setattr(sdr, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(sdr, "init_db", lambda: None)
    monkeypatch.setattr(sdr, "_recover_stale_jobs", lambda: 1)
    monkeypatch.setattr(
        sdr,
        "pick_topics",
        lambda limit_per_channel: [{"id": 1, "topic": "Topic A", "channel": "space"}],
    )
    monkeypatch.setattr(
        sdr,
        "run_one",
        lambda item: (_ for _ in ()).throw(AssertionError("run_one should not be called")),
    )

    result = sdr.main()

    assert result == 0
    output = capsys.readouterr().out
    assert "stale running 1건" in output
    assert "(dry-run 모드" in output


def test_main_runs_selected_topics_and_replenishes(monkeypatch, capsys):
    results = [
        {"id": 1, "channel": "space", "topic": "Topic A", "status": "success", "cost": 1.2, "duration": 30.0},
        {"id": 2, "channel": "history", "topic": "Topic B", "status": "failed", "reason": "render failed"},
    ]
    replenish_calls = []

    monkeypatch.setattr(sys, "argv", ["shorts_daily_runner.py"])
    monkeypatch.setattr(sdr, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(sdr, "init_db", lambda: None)
    monkeypatch.setattr(sdr, "_recover_stale_jobs", lambda: 0)
    monkeypatch.setattr(
        sdr,
        "pick_topics",
        lambda limit_per_channel: [
            {"id": 1, "topic": "Topic A", "channel": "space"},
            {"id": 2, "topic": "Topic B", "channel": "history"},
        ],
    )
    monkeypatch.setattr(sdr, "run_one", lambda item: results.pop(0))
    monkeypatch.setitem(
        sys.modules,
        "execution.topic_auto_generator",
        types.SimpleNamespace(check_and_replenish=lambda: replenish_calls.append("ok")),
    )

    result = sdr.main()

    assert result == 1
    output = capsys.readouterr().out
    assert "성공 1 / 실패 1" in output
    assert "[주제 보충 체크]" in output
    assert replenish_calls == ["ok"]


def test_main_ignores_replenish_exception(monkeypatch, caplog):
    monkeypatch.setattr(sys, "argv", ["shorts_daily_runner.py"])
    monkeypatch.setattr(sdr, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(sdr, "init_db", lambda: None)
    monkeypatch.setattr(sdr, "_recover_stale_jobs", lambda: 0)
    monkeypatch.setattr(
        sdr,
        "pick_topics",
        lambda limit_per_channel: [{"id": 1, "topic": "Topic A", "channel": "space"}],
    )
    monkeypatch.setattr(
        sdr,
        "run_one",
        lambda item: {
            "id": 1,
            "channel": "space",
            "topic": "Topic A",
            "status": "success",
            "cost": 1.0,
            "duration": 10.0,
        },
    )
    monkeypatch.setitem(
        sys.modules,
        "execution.topic_auto_generator",
        types.SimpleNamespace(check_and_replenish=lambda: (_ for _ in ()).throw(RuntimeError("boom"))),
    )

    with caplog.at_level("WARNING"):
        result = sdr.main()

    assert result == 0
    assert "주제 보충 실패" in caplog.text


def test_reload_wraps_stdout_for_non_utf8(monkeypatch):
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp949")
    fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp949")

    monkeypatch.setattr(sys, "stdout", fake_stdout)
    monkeypatch.setattr(sys, "stderr", fake_stderr)

    importlib.reload(sdr)

    assert sys.stdout.encoding.lower() == "utf-8"
    assert sys.stderr.encoding.lower() == "utf-8"

    monkeypatch.setattr(sys, "stdout", original_stdout)
    monkeypatch.setattr(sys, "stderr", original_stderr)
    importlib.reload(sdr)


# ---------------------------------------------------------------------------
# Notion sync paths (lines 139-143)
# ---------------------------------------------------------------------------


def test_run_one_notion_sync_success(monkeypatch, capsys):
    """Notion sync success path: is_configured() True + sync_item returns result."""
    updates = []

    monkeypatch.setattr(sdr, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(
        sdr.subprocess,
        "run",
        lambda cmd, **kwargs: types.SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        sdr,
        "_find_latest_manifest",
        lambda output_dir, after_ts: {
            "status": "success",
            "job_id": "job-notion",
            "title": "Notion title",
            "output_path": "v.mp4",
            "thumbnail_path": "t.png",
            "estimated_cost_usd": 0.5,
            "total_duration_sec": 20.0,
        },
    )

    # Mock notion_shorts_sync module
    fake_notion_sync = types.SimpleNamespace(
        is_configured=lambda: True,
        sync_item=lambda item_id: {"action": "created", "page_id": "abcdef1234567890"},
    )
    monkeypatch.setitem(sys.modules, "execution.notion_shorts_sync", fake_notion_sync)

    result = sdr.run_one({"id": 50, "topic": "Notion test", "channel": "space"})

    assert result["status"] == "success"
    output = capsys.readouterr().out
    assert "[Notion] created page_id=abcdef12" in output


def test_run_one_notion_sync_not_configured(monkeypatch, capsys):
    """Notion sync skipped when is_configured() returns False."""
    updates = []

    monkeypatch.setattr(sdr, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(
        sdr.subprocess,
        "run",
        lambda cmd, **kwargs: types.SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        sdr,
        "_find_latest_manifest",
        lambda output_dir, after_ts: {
            "status": "success",
            "job_id": "job-no-notion",
            "output_path": "v.mp4",
            "estimated_cost_usd": 0.3,
            "total_duration_sec": 15.0,
        },
    )

    fake_notion_sync = types.SimpleNamespace(
        is_configured=lambda: False,
        sync_item=lambda item_id: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    monkeypatch.setitem(sys.modules, "execution.notion_shorts_sync", fake_notion_sync)

    result = sdr.run_one({"id": 51, "topic": "No notion", "channel": "space"})

    assert result["status"] == "success"
    output = capsys.readouterr().out
    assert "[Notion]" not in output


def test_run_one_notion_sync_exception(monkeypatch, capsys):
    """Notion sync exception path: error is printed but run_one still returns success."""
    updates = []

    monkeypatch.setattr(sdr, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(
        sdr.subprocess,
        "run",
        lambda cmd, **kwargs: types.SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        sdr,
        "_find_latest_manifest",
        lambda output_dir, after_ts: {
            "status": "success",
            "job_id": "job-err-notion",
            "output_path": "v.mp4",
            "estimated_cost_usd": 0.2,
            "total_duration_sec": 10.0,
        },
    )

    fake_notion_sync = types.SimpleNamespace(
        is_configured=lambda: (_ for _ in ()).throw(RuntimeError("notion import fail")),
    )
    monkeypatch.setitem(sys.modules, "execution.notion_shorts_sync", fake_notion_sync)

    result = sdr.run_one({"id": 52, "topic": "Notion error", "channel": "space"})

    assert result["status"] == "success"
    output = capsys.readouterr().out
    assert "[Notion] 동기화 실패 (건너뜀)" in output
