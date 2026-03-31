from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


class _DummyBlock:
    def __init__(self, streamlit_module: "_FakeStreamlit") -> None:
        self._streamlit = streamlit_module

    def __enter__(self) -> "_DummyBlock":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def __getattr__(self, name: str):
        return getattr(self._streamlit, name)


class _FakeStreamlit(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.session_state: dict[str, object] = {}
        self.events: list[tuple[str, object]] = []

    def _record(self, name: str, payload: object = None) -> None:
        self.events.append((name, payload))

    def set_page_config(self, **kwargs) -> None:
        self._record("set_page_config", kwargs)

    def error(self, message: object) -> None:
        self._record("error", message)

    def warning(self, message: object) -> None:
        self._record("warning", message)

    def success(self, message: object) -> None:
        self._record("success", message)

    def info(self, message: object) -> None:
        self._record("info", message)

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def subheader(self, *args, **kwargs) -> None:
        self._record("subheader", args[0] if args else None)

    def caption(self, *args, **kwargs) -> None:
        self._record("caption", args[0] if args else None)

    def markdown(self, *args, **kwargs) -> None:
        self._record("markdown", args[0] if args else None)

    def metric(self, *args, **kwargs) -> None:
        self._record("metric", args[0] if args else None)

    def divider(self) -> None:
        self._record("divider")

    def title(self, *args, **kwargs) -> None:
        self._record("title", args[0] if args else None)

    def code(self, *args, **kwargs) -> None:
        self._record("code", args[0] if args else None)

    def image(self, *args, **kwargs) -> None:
        self._record("image", args[0] if args else None)

    def rerun(self) -> None:
        self._record("rerun")

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def tabs(self, labels):
        return [_DummyBlock(self) for _ in labels]

    def container(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def form(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def expander(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def selectbox(self, label, options, index=0, **kwargs):
        return options[index]

    def text_area(self, label, value="", **kwargs):
        return value

    def text_input(self, label, value="", **kwargs):
        return value

    def checkbox(self, label, value=False, **kwargs):
        return value

    def number_input(self, label, min_value=None, max_value=None, value=0, step=1, **kwargs):
        return value

    def button(self, *args, **kwargs) -> bool:
        return False

    def form_submit_button(self, *args, **kwargs) -> bool:
        return False


def _make_path_contract_module(tmp_path: Path) -> types.ModuleType:
    module = types.ModuleType("path_contract")

    def resolve_project_dir(name: str, required_paths=()):
        project_dir = tmp_path / "projects" / name
        project_dir.mkdir(parents=True, exist_ok=True)
        for rel_path in required_paths:
            target = project_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("test", encoding="utf-8")
        return project_dir

    module.resolve_project_dir = resolve_project_dir
    return module


def _make_content_db_module() -> types.ModuleType:
    module = types.ModuleType("execution.content_db")
    module.add_topic = lambda *args, **kwargs: 1
    module.delete_item = lambda *args, **kwargs: None
    module.get_all = lambda *args, **kwargs: []
    module.get_channel_settings = lambda *args, **kwargs: None
    module.get_channel_readiness_summary = lambda *args, **kwargs: []
    module.get_kpis = lambda *args, **kwargs: {
        "total": 0,
        "success_count": 0,
        "pending_count": 0,
        "running_count": 0,
        "failed_count": 0,
        "total_cost_usd": 0.0,
    }
    module.get_manifest_sync_diffs = lambda *args, **kwargs: {
        "summary": {
            "missing_in_db_count": 0,
            "pending_sync_count": 0,
            "missing_output_file_count": 0,
            "missing_manifest_count": 0,
        },
        "pending_sync": [],
        "missing_in_db": [],
        "missing_output_file": [],
        "missing_manifest": [],
    }
    module.get_recent_failure_items = lambda *args, **kwargs: []
    module.get_review_queue_items = lambda *args, **kwargs: []
    module.get_youtube_stats = lambda *args, **kwargs: {"uploaded": 0, "awaiting": 0}
    module.init_db = lambda: None
    module.update_job = lambda *args, **kwargs: None
    module.upsert_channel_settings = lambda *args, **kwargs: None
    return module


def _make_youtube_module() -> types.ModuleType:
    module = types.ModuleType("execution.youtube_uploader")
    module.get_auth_status = lambda: {
        "has_credentials_file": False,
        "has_token_file": False,
        "token_valid_or_refreshable": False,
        "ready": False,
        "reason": "credentials missing",
    }
    module.upload_pending_items = lambda **kwargs: []
    module.upload_video = lambda **kwargs: {
        "video_id": "video-123",
        "youtube_url": "https://youtube.test/watch?v=video-123",
    }
    return module


def _make_notion_module() -> types.ModuleType:
    module = types.ModuleType("execution.notion_shorts_sync")
    module.is_configured = lambda: False
    module.sync_all = lambda: []
    module.sync_item = lambda item_id: {"action": "error", "error": "disabled", "page_id": ""}
    return module


@pytest.fixture()
def shorts_manager(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    module_name = "execution.pages.shorts_manager"
    sys.modules.pop(module_name, None)

    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setitem(sys.modules, "path_contract", _make_path_contract_module(tmp_path))
    monkeypatch.setitem(sys.modules, "execution.content_db", _make_content_db_module())
    monkeypatch.setitem(sys.modules, "execution.youtube_uploader", _make_youtube_module())
    monkeypatch.setitem(sys.modules, "execution.notion_shorts_sync", _make_notion_module())

    module = importlib.import_module(module_name)
    yield module
    sys.modules.pop(module_name, None)


def test_flash_helpers_emit_and_clear_state(shorts_manager) -> None:
    shorts_manager._set_flash("success", "done")
    assert shorts_manager.st.session_state[shorts_manager._FLASH_KEY] == {"level": "success", "message": "done"}

    shorts_manager._render_flash()

    assert shorts_manager._FLASH_KEY not in shorts_manager.st.session_state
    assert ("success", "done") in shorts_manager.st.events


def test_formatting_helpers_cover_badges_and_display(shorts_manager) -> None:
    assert "완료" in shorts_manager._status_badge("success")
    assert shorts_manager._fmt_dur(125) == "2:05"
    assert shorts_manager._fmt_dur(0) == "-"
    assert shorts_manager._fmt_cost(0.0) == "-"
    assert shorts_manager._fmt_cost(1.23456) == "$1.2346"
    assert "YT 실패" in shorts_manager._youtube_badge("failed")
    assert "주의" in shorts_manager._ops_badge("warning")


def test_youtube_badge_escapes_user_supplied_url(shorts_manager) -> None:
    badge = shorts_manager._youtube_badge("uploaded", "https://example.com/?q='x'&next=<tag>")
    assert "target='_blank'" in badge
    assert "<tag>" not in badge
    assert "&#x27;x&#x27;" in badge


def test_format_issue_labels_and_settings_indexes(shorts_manager) -> None:
    assert shorts_manager._format_issue_labels(["preflight:missing_brand_assets", "low_disk_space"]) == [
        "missing brand assets",
        "low disk space",
    ]
    assert shorts_manager._voice_index({"voice": "nova"}) == shorts_manager.VOICE_OPTIONS.index("nova")
    assert shorts_manager._voice_index({"voice": "unknown"}) == 0
    assert shorts_manager._style_index({"style_preset": "bold"}) == shorts_manager.STYLE_OPTIONS.index("bold")
    assert shorts_manager._style_index({"style_preset": "unknown"}) == 0


def test_default_auth_status_and_upload_gate(shorts_manager, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shorts_manager, "_YT_OK", False)
    monkeypatch.setattr(shorts_manager, "_YT_ERR", "missing module")

    status = shorts_manager._default_auth_status()

    assert status["ready"] is False
    assert "missing module" in status["reason"]
    assert shorts_manager._can_attempt_upload({"has_credentials_file": True}) is False

    monkeypatch.setattr(shorts_manager, "_YT_OK", True)
    assert shorts_manager._can_attempt_upload({"has_credentials_file": True}) is True
    assert shorts_manager._can_attempt_upload({"has_credentials_file": False}) is False


def test_build_upload_metadata_and_reset_fields(shorts_manager, monkeypatch: pytest.MonkeyPatch) -> None:
    assert shorts_manager._build_upload_metadata({"topic": "Black Hole", "channel": "우주/천문학"}) == (
        "#우주/천문학 #Black Hole",
        ["우주/천문학", "shorts"],
    )
    assert shorts_manager._build_upload_metadata({"topic": "Black Hole"}) == ("#Black Hole", ["shorts"])

    updates: list[tuple[int, dict[str, object]]] = []
    monkeypatch.setattr(
        shorts_manager,
        "update_job",
        lambda item_id, **kwargs: updates.append((item_id, kwargs)),
    )

    shorts_manager._reset_youtube_fields(7)

    assert updates == [
        (
            7,
            {
                "youtube_video_id": "",
                "youtube_status": "",
                "youtube_url": "",
                "youtube_uploaded_at": "",
                "youtube_error": "",
            },
        )
    ]


def test_upload_single_retry_resets_and_updates(shorts_manager, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(shorts_manager, "_reset_youtube_fields", lambda item_id: events.append(("reset", item_id)))
    monkeypatch.setattr(
        shorts_manager,
        "yt_upload",
        lambda **kwargs: {
            "video_id": "video-42",
            "youtube_url": "https://youtube.test/watch?v=video-42",
        },
    )
    monkeypatch.setattr(
        shorts_manager,
        "update_job",
        lambda item_id, **kwargs: events.append(("update", item_id, kwargs)),
    )

    result = shorts_manager._upload_single(
        {
            "id": 42,
            "topic": "Solar Storms",
            "title": "Solar Storms Explained",
            "channel": "우주/천문학",
            "video_path": "video.mp4",
        },
        retry=True,
    )

    assert result["video_id"] == "video-42"
    assert events[0] == ("reset", 42)
    assert events[1][0] == "update"
    assert events[1][1] == 42
    assert events[1][2]["youtube_status"] == "uploaded"
    assert events[1][2]["youtube_video_id"] == "video-42"
    assert events[1][2]["youtube_url"].endswith("video-42")
    assert events[1][2]["youtube_uploaded_at"]


def test_upload_single_raises_when_video_id_missing(shorts_manager, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shorts_manager, "yt_upload", lambda **kwargs: {"error": "permission denied"})

    with pytest.raises(RuntimeError, match="permission denied"):
        shorts_manager._upload_single(
            {
                "id": 1,
                "topic": "Topic",
                "channel": "AI/기술",
                "video_path": "video.mp4",
            }
        )


def test_scan_manifests_updates_matching_jobs(shorts_manager, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    v2_dir = tmp_path / "shorts-maker-v2"
    output_dir = v2_dir / "output"
    output_dir.mkdir(parents=True)

    (output_dir / "job-1_manifest.json").write_text(
        json.dumps(
            {
                "job_id": "job-1",
                "status": "success",
                "title": "New Title",
                "output_path": "video.mp4",
                "thumbnail_path": "thumb.png",
                "estimated_cost_usd": 1.25,
                "total_duration_sec": 59.0,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "broken_manifest.json").write_text("{", encoding="utf-8")
    (output_dir / "empty_manifest.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

    updates: list[tuple[int, dict[str, object]]] = []
    monkeypatch.setattr(shorts_manager, "_V2_DIR", v2_dir)
    monkeypatch.setattr(shorts_manager, "get_all", lambda: [{"id": 9, "job_id": "job-1", "status": "pending"}])
    monkeypatch.setattr(
        shorts_manager,
        "update_job",
        lambda item_id, **kwargs: updates.append((item_id, kwargs)),
    )

    shorts_manager._scan_manifests()

    assert updates == [
        (
            9,
            {
                "status": "success",
                "title": "New Title",
                "video_path": "video.mp4",
                "thumbnail_path": "thumb.png",
                "cost_usd": 1.25,
                "duration_sec": 59.0,
            },
        )
    ]


def test_launch_v2_starts_process_and_handles_failure(
    shorts_manager, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    v2_dir = tmp_path / "shorts-maker-v2"
    v2_dir.mkdir(parents=True)
    (v2_dir / "config.yaml").write_text("pipeline: test", encoding="utf-8")

    class _Proc:
        pid = 321

    updates: list[tuple[int, dict[str, object]]] = []
    launch_args: dict[str, object] = {}

    def fake_update_job(item_id: int, **kwargs) -> None:
        updates.append((item_id, kwargs))

    def fake_popen(cmd, cwd, stdout, stderr):
        launch_args["cmd"] = cmd
        launch_args["cwd"] = cwd
        return _Proc()

    monkeypatch.setattr(shorts_manager, "_V2_DIR", v2_dir)
    monkeypatch.setattr(shorts_manager, "update_job", fake_update_job)
    monkeypatch.setattr(shorts_manager.subprocess, "Popen", fake_popen)

    pid = shorts_manager._launch_v2(11, "Dark Matter", "우주/천문학")

    assert pid == "321"
    assert launch_args["cwd"] == str(v2_dir)
    assert "--topic" in launch_args["cmd"]
    assert "--channel" in launch_args["cmd"]
    assert updates[-1] == (11, {"status": "running"})

    monkeypatch.setattr(
        shorts_manager.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("spawn failed")),
    )

    failed_pid = shorts_manager._launch_v2(12, "Failed Launch", "AI/기술")

    assert failed_pid is None
    assert updates[-1] == (12, {"status": "failed", "notes": "spawn failed"})


def test_render_auth_status_covers_missing_and_ready_states(shorts_manager) -> None:
    shorts_manager.st.events.clear()
    shorts_manager._render_auth_status(
        {
            "has_credentials_file": False,
            "has_token_file": False,
            "token_valid_or_refreshable": False,
            "ready": False,
            "reason": "credentials missing",
        }
    )
    assert ("error", "credentials.json 없음") in shorts_manager.st.events

    shorts_manager.st.events.clear()
    shorts_manager._render_auth_status(
        {
            "has_credentials_file": True,
            "has_token_file": True,
            "token_valid_or_refreshable": True,
            "ready": True,
            "reason": "",
        }
    )
    assert ("success", "토큰 준비 완료") in shorts_manager.st.events


def test_render_channel_readiness_sorts_and_formats_issues(shorts_manager, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        shorts_manager,
        "get_channel_readiness_summary",
        lambda channels: [
            {
                "channel": "역사/고고학",
                "status": "healthy",
                "voice": "alloy",
                "style_preset": "default",
                "bgm_ready": True,
                "brand_assets_ready": True,
                "failed_count": 0,
                "running_count": 0,
                "pending_count": 1,
                "next_action": "없음",
                "issues": [],
            },
            {
                "channel": "AI/기술",
                "status": "critical",
                "voice": "nova",
                "style_preset": "bold",
                "bgm_ready": False,
                "brand_assets_ready": False,
                "failed_count": 3,
                "running_count": 1,
                "pending_count": 2,
                "next_action": "브랜드 에셋 보강",
                "issues": ["preflight:missing_brand_assets", "runtime:missing_bgm"],
            },
        ],
    )
    shorts_manager.st.events.clear()

    shorts_manager._render_channel_readiness(shorts_manager.CHANNELS)

    markdowns = [payload for name, payload in shorts_manager.st.events if name == "markdown"]
    captions = [payload for name, payload in shorts_manager.st.events if name == "caption"]
    assert markdowns
    assert "AI/기술" in markdowns[0]
    assert any("missing brand assets, missing bgm" in str(payload) for payload in captions)


def test_render_failure_triage_and_review_queue(shorts_manager, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        shorts_manager,
        "get_recent_failure_items",
        lambda limit=6: [
            {
                "channel": "AI/기술",
                "title": "Launch Failure",
                "updated_at": "2026-03-31 18:30:00",
                "retry_recommended": True,
                "failure_reason": "network timeout",
                "issues": ["preflight:missing_brand_assets"],
                "next_action": "설정 점검",
            }
        ],
    )
    monkeypatch.setattr(
        shorts_manager,
        "get_review_queue_items",
        lambda limit=6: [
            {
                "channel": "우주/천문학",
                "review_status": "warning",
                "title": "Review Me",
                "updated_at": "2026-03-31 19:00:00",
                "video_exists": True,
                "thumbnail_exists": False,
                "notes": "thumbnail missing",
                "next_action": "썸네일 재생성",
            }
        ],
    )

    shorts_manager.st.events.clear()
    shorts_manager._render_failure_triage()
    shorts_manager._render_manual_review_queue()

    captions = [str(payload) for name, payload in shorts_manager.st.events if name == "caption"]
    assert any("사전 점검: missing brand assets" in payload for payload in captions)
    assert any("메모: thumbnail missing" in payload for payload in captions)


def test_render_manifest_sync_panel_shows_summary_details(shorts_manager, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        shorts_manager,
        "get_manifest_sync_diffs",
        lambda limit=5: {
            "summary": {
                "missing_in_db_count": 1,
                "pending_sync_count": 1,
                "missing_output_file_count": 1,
                "missing_manifest_count": 1,
            },
            "pending_sync": [{"channel": "AI/기술", "topic": "Topic A", "mismatches": ["status", "title"]}],
            "missing_in_db": [{"job_id": "job-7", "title": "Lost Item"}],
            "missing_output_file": [{"channel": "우주/천문학", "topic": "Topic B"}],
            "missing_manifest": [{"channel": "역사/고고학", "topic": "Topic C", "status": "success"}],
        },
    )
    shorts_manager.st.events.clear()

    shorts_manager._render_manifest_sync_panel()

    captions = [str(payload) for name, payload in shorts_manager.st.events if name == "caption"]
    assert "동기화 필요" in captions
    assert any("Topic A / status, title" in payload for payload in captions)
    assert any("job-7 / Lost Item" in payload for payload in captions)
    assert any("Topic B" in payload for payload in captions)
    assert any("Topic C / success" in payload for payload in captions)
