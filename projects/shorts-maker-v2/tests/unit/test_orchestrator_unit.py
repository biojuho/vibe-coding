"""orchestrator.py unit tests — helper methods & error paths.

integration test_orchestrator_manifest.py covers the happy-path run().
This file covers:
  - JsonlLogger
  - renderer_mode validation
  - _load_channel_profile
  - _new_job_id
  - _save_manifest
  - _cleanup_run_dir
  - _smart_retry_strategy
  - run() error paths (TopicUnsuitableError, generic, media incomplete, resume)
  - _try_shorts_factory_render delegation
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

from shorts_maker_v2.models import (
    JobManifest,
    RetentionAutoFixResult,
    RetentionSimulationResult,
    SceneAsset,
    ScenePlan,
    SemanticQCResult,
)
from shorts_maker_v2.pipeline.error_types import PipelineErrorType
from shorts_maker_v2.pipeline.orchestrator import (
    JsonlLogger,
    PipelineOrchestrator,
)
from shorts_maker_v2.pipeline.retention_autofix import RetentionAutoFixer

# ── helpers ─────────────────────────────────────────────────────────────────


def _make_config_yaml(tmp_path: Path) -> Path:
    payload = {
        "project": {"language": "ko-KR", "default_scene_count": 1, "structure_validation": "off"},
        "video": {
            "target_duration_sec": [35, 45],
            "resolution": [1080, 1920],
            "fps": 30,
            "scene_video_duration_sec": 5,
            "aspect_ratio": "9:16",
        },
        "providers": {
            "llm": "openai",
            "tts": "openai",
            "visual_primary": "google-veo",
            "visual_fallback": "openai-image",
        },
        "limits": {"max_cost_usd": 2.0, "max_retries": 1, "request_timeout_sec": 5},
        "costs": {
            "llm_per_job": 0.25,
            "tts_per_second": 0.001,
            "veo_per_second": 0.03,
            "image_per_scene": 0.04,
        },
        "paths": {"output_dir": "output", "logs_dir": "logs", "runs_dir": "runs"},
        "captions": {
            "font_size": 64,
            "margin_x": 90,
            "bottom_offset": 240,
            "text_color": "#FFD700",
            "stroke_color": "#000000",
            "stroke_width": 4,
            "line_spacing": 12,
            "font_candidates": ["C:/Windows/Fonts/malgun.ttf"],
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def _load_cfg(tmp_path: Path):
    from shorts_maker_v2.config import load_config

    return load_config(_make_config_yaml(tmp_path))


class FakeQcResult:
    def __init__(self, verdict: str, *, issues: list[str] | None = None, checks: dict | None = None):
        self.verdict = verdict
        self.issues = issues or []
        self.checks = checks or {}
        self.retry_count = 0

    def to_dict(self):
        return {
            "verdict": self.verdict,
            "issues": list(self.issues),
            "checks": dict(self.checks),
            "retry_count": self.retry_count,
        }


def _set_frozen_attr(obj, name: str, value) -> None:
    object.__setattr__(obj, name, value)


class StubScript:
    def run(self, topic, **kw):
        return (
            "title",
            [ScenePlan(scene_id=1, narration_ko="n", visual_prompt_en="p", target_sec=5.0)],
            "hook",
        )


class WeakHookScript:
    def run(self, topic, **kw):
        return (
            "title",
            [
                ScenePlan(
                    scene_id=1,
                    narration_ko="평범한 설명입니다",
                    visual_prompt_en="p",
                    target_sec=5.0,
                    structure_role="hook",
                )
            ],
            "hook",
        )


class StubMedia:
    def run(self, scene_plans, run_dir, cost_guard, logger=None):
        run_dir.mkdir(parents=True, exist_ok=True)
        a = run_dir / "a.mp3"
        a.write_bytes(b"f")
        cost_guard.add_tts_cost(5.0)
        return [
            SceneAsset(scene_id=1, audio_path=str(a), visual_type="image", visual_path=str(a), duration_sec=5.0)
        ], []


class StubRender:
    def run(self, scene_plans, scene_assets, output_dir, output_filename, run_dir, title="", topic=""):
        output_dir.mkdir(parents=True, exist_ok=True)
        p = output_dir / output_filename
        p.write_bytes(b"mp4")
        return p


# ── JsonlLogger ─────────────────────────────────────────────────────────────


class TestJsonlLogger:
    def test_info_writes_jsonl(self, tmp_path: Path):
        log = tmp_path / "test.jsonl"
        jl = JsonlLogger(log)
        jl.info("test_event", key="val")
        lines = log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["level"] == "INFO"
        assert data["event"] == "test_event"
        assert data["key"] == "val"
        assert "timestamp" in data

    def test_warning_and_error(self, tmp_path: Path):
        log = tmp_path / "test.jsonl"
        jl = JsonlLogger(log)
        jl.warning("warn_evt")
        jl.error("err_evt")
        lines = log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["level"] == "WARNING"
        assert json.loads(lines[1])["level"] == "ERROR"

    def test_creates_parent_dirs(self, tmp_path: Path):
        log = tmp_path / "sub" / "deep" / "test.jsonl"
        jl = JsonlLogger(log)
        jl.info("ok")
        assert log.exists()

    def test_recreates_parent_dirs_between_writes(self, tmp_path: Path):
        log = tmp_path / "sub" / "deep" / "test.jsonl"
        jl = JsonlLogger(log)
        jl.info("before")
        shutil.rmtree(log.parent)

        jl.warning("after")

        data = json.loads(log.read_text(encoding="utf-8").strip())
        assert data["level"] == "WARNING"
        assert data["event"] == "after"


# ── renderer_mode validation ────────────────────────────────────────────────


class TestRendererModeValidation:
    def test_invalid_mode_raises(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        with pytest.raises(ValueError, match="Unsupported renderer_mode"):
            PipelineOrchestrator(
                config=cfg,
                base_dir=tmp_path,
                script_step=StubScript(),
                media_step=StubMedia(),
                render_step=StubRender(),
                renderer_mode="nonexistent",
            )

    def test_native_mode(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
            renderer_mode="native",
        )
        assert orch._renderer_mode == "native"

    def test_full_init_uses_channel_profile_optional_clients_and_research(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg, "_channel_key", "ai_tech")
        _set_frozen_attr(cfg.providers, "visual_stock", "pexels")
        _set_frozen_attr(cfg.providers, "llm_providers", ("openai", "mimo"))
        _set_frozen_attr(cfg.providers, "llm_models", {"mimo": "mimo-v2"})
        _set_frozen_attr(cfg.video, "stock_mix_ratio", 0.3)
        _set_frozen_attr(cfg.research, "enabled", True)
        _set_frozen_attr(cfg.research, "provider", "gemini")

        openai_client = MagicMock(name="openai_client")
        google_client = MagicMock(name="google_client")
        pexels_client = MagicMock(name="pexels_client")
        llm_router = MagicMock(name="llm_router")
        script_step = MagicMock(name="script_step")
        media_step = MagicMock(name="media_step")
        render_step = MagicMock(name="render_step")
        thumbnail_step = MagicMock(name="thumbnail_step")
        research_step = MagicMock(name="research_step")

        with (
            patch.dict(
                "os.environ",
                {
                    "OPENAI_API_KEY": "openai-key",
                    "GEMINI_API_KEY": "gemini-key",
                    "PEXELS_API_KEY": "pexels-key",
                },
                clear=False,
            ),
            patch("shorts_maker_v2.pipeline.orchestrator.OpenAIClient", return_value=openai_client) as openai_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.GoogleClient", return_value=google_client) as google_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.PexelsClient", return_value=pexels_client) as pexels_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.LLMRouter", return_value=llm_router) as llm_router_cls,
            patch(
                "shorts_maker_v2.pipeline.orchestrator.ScriptStep.from_channel_profile",
                return_value=script_step,
            ) as from_profile,
            patch("shorts_maker_v2.pipeline.orchestrator.MediaStep", return_value=media_step) as media_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.RenderStep", return_value=render_step) as render_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.ThumbnailStep", return_value=thumbnail_step) as thumbnail_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.ResearchStep", return_value=research_step) as research_cls,
            patch.object(PipelineOrchestrator, "_load_channel_profile", return_value={"hook_pattern": "myth_busting"}),
        ):
            orch = PipelineOrchestrator(config=cfg, base_dir=tmp_path)

        assert orch.script_step is script_step
        assert orch.media_step is media_step
        assert orch.render_step is render_step
        assert orch.thumbnail_step is thumbnail_step
        assert orch.research_step is research_step
        openai_cls.assert_called_once()
        google_cls.assert_called_once()
        pexels_cls.assert_called_once()
        llm_router_cls.assert_called()
        from_profile.assert_called_once()
        media_cls.assert_called_once()
        render_cls.assert_called_once()
        thumbnail_cls.assert_called_once()
        assert thumbnail_cls.call_args.kwargs["google_client"] is google_client
        research_cls.assert_called_once_with(config=cfg, google_client=google_client, llm_router=llm_router)

    def test_full_init_without_channel_profile_uses_plain_script_step(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg, "_channel_key", "")
        _set_frozen_attr(cfg.providers, "visual_stock", "")
        _set_frozen_attr(cfg.providers, "llm_providers", ())
        _set_frozen_attr(cfg.providers, "llm_models", {})
        _set_frozen_attr(cfg.video, "stock_mix_ratio", 0.0)
        _set_frozen_attr(cfg.research, "enabled", False)

        openai_client = MagicMock(name="openai_client")
        llm_router = MagicMock(name="llm_router")
        script_step = MagicMock(name="script_step")
        media_step = MagicMock(name="media_step")
        render_step = MagicMock(name="render_step")
        thumbnail_step = MagicMock(name="thumbnail_step")

        with (
            patch.dict(
                "os.environ",
                {
                    "OPENAI_API_KEY": "openai-key",
                    "GEMINI_API_KEY": "",
                    "PEXELS_API_KEY": "",
                },
                clear=False,
            ),
            patch("shorts_maker_v2.pipeline.orchestrator.OpenAIClient", return_value=openai_client),
            patch("shorts_maker_v2.pipeline.orchestrator.GoogleClient") as google_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.PexelsClient") as pexels_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.LLMRouter", return_value=llm_router),
            patch("shorts_maker_v2.pipeline.orchestrator.ScriptStep", return_value=script_step) as script_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.ScriptStep.from_channel_profile") as from_profile,
            patch("shorts_maker_v2.pipeline.orchestrator.MediaStep", return_value=media_step),
            patch("shorts_maker_v2.pipeline.orchestrator.RenderStep", return_value=render_step),
            patch("shorts_maker_v2.pipeline.orchestrator.ThumbnailStep", return_value=thumbnail_step),
        ):
            orch = PipelineOrchestrator(config=cfg, base_dir=tmp_path)

        assert orch.script_step is script_step
        assert orch.research_step is None
        script_cls.assert_called_once()
        from_profile.assert_not_called()
        google_cls.assert_not_called()
        pexels_cls.assert_not_called()
        assert orch._use_shorts_factory is False

    def test_auto_mode(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
            renderer_mode="auto",
        )
        assert orch._use_shorts_factory is True

    def test_use_shorts_factory_flag(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
            use_shorts_factory=True,
        )
        assert orch._renderer_mode == "auto"

    def test_use_shorts_factory_false(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
            use_shorts_factory=False,
        )
        assert orch._renderer_mode == "native"


# ── _load_channel_profile ───────────────────────────────────────────────────


class TestLoadChannelProfile:
    def test_no_file(self, tmp_path: Path):
        result = PipelineOrchestrator._load_channel_profile("ai_tech", tmp_path)
        assert result is None

    def test_valid_profile(self, tmp_path: Path):
        profiles = {"channels": {"ai_tech": {"name": "AI Tech", "tone": "exciting"}}}
        (tmp_path / "channel_profiles.yaml").write_text(yaml.safe_dump(profiles), encoding="utf-8")
        result = PipelineOrchestrator._load_channel_profile("ai_tech", tmp_path)
        assert result == {"name": "AI Tech", "tone": "exciting"}

    def test_missing_channel(self, tmp_path: Path):
        profiles = {"channels": {"other": {}}}
        (tmp_path / "channel_profiles.yaml").write_text(yaml.safe_dump(profiles), encoding="utf-8")
        result = PipelineOrchestrator._load_channel_profile("ai_tech", tmp_path)
        assert result is None

    def test_invalid_yaml(self, tmp_path: Path):
        (tmp_path / "channel_profiles.yaml").write_text(":::invalid", encoding="utf-8")
        result = PipelineOrchestrator._load_channel_profile("ai_tech", tmp_path)
        assert result is None


# ── _new_job_id ─────────────────────────────────────────────────────────────


def test_new_job_id_format():
    jid = PipelineOrchestrator._new_job_id()
    parts = jid.split("-")
    assert len(parts) == 3  # YYYYMMDD-HHMMSS-hex8
    assert len(parts[0]) == 8  # date
    assert len(parts[1]) == 6  # time
    assert len(parts[2]) == 8  # uuid hex


def test_new_job_id_unique():
    ids = {PipelineOrchestrator._new_job_id() for _ in range(10)}
    assert len(ids) == 10


# ── _save_manifest ──────────────────────────────────────────────────────────


def test_save_manifest(tmp_path: Path):
    cfg = _load_cfg(tmp_path)
    orch = PipelineOrchestrator(
        config=cfg,
        base_dir=tmp_path,
        script_step=StubScript(),
        media_step=StubMedia(),
        render_step=StubRender(),
    )
    manifest = JobManifest(job_id="test-001", topic="t", status="success")
    run_dir = tmp_path / "runs" / "test-001"
    run_dir.mkdir(parents=True, exist_ok=True)

    run_path, out_path = orch._save_manifest(manifest, run_dir)
    assert run_path.exists()
    assert out_path.exists()
    data = json.loads(run_path.read_text(encoding="utf-8"))
    assert data["job_id"] == "test-001"
    assert data["status"] == "success"


# ── _cleanup_run_dir ────────────────────────────────────────────────────────


class TestCleanupRunDir:
    def test_cleans_media_keeps_manifest(self, tmp_path: Path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "audio.mp3").write_bytes(b"x")
        (run_dir / "image.png").write_bytes(b"x")
        (run_dir / "manifest.json").write_text("{}")
        (run_dir / "notes.txt").write_text("keep")

        mock_logger = MagicMock()
        PipelineOrchestrator._cleanup_run_dir(run_dir, mock_logger)

        assert not (run_dir / "audio.mp3").exists()
        assert not (run_dir / "image.png").exists()
        assert (run_dir / "manifest.json").exists()
        assert (run_dir / "notes.txt").exists()

    def test_cleanup_exception_logged(self, tmp_path: Path):
        mock_logger = MagicMock()
        # non-existent dir should not raise, just log warning
        PipelineOrchestrator._cleanup_run_dir(tmp_path / "nonexist", mock_logger)
        # no crash

    def test_cleanup_logs_warning_when_scan_fails(self, tmp_path: Path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        mock_logger = MagicMock()

        with patch.object(Path, "rglob", side_effect=OSError("scan failed")):
            PipelineOrchestrator._cleanup_run_dir(run_dir, mock_logger)

        mock_logger.warning.assert_called_once()


# ── _smart_retry_strategy ──────────────────────────────────────────────────


class TestSmartRetryStrategy:
    def test_non_retryable_aborts(self):
        exc = Exception("invalid API key")
        with patch(
            "shorts_maker_v2.pipeline.orchestrator.classify_error",
            return_value=PipelineErrorType.AUTH_ERROR,
        ):
            result = PipelineOrchestrator._smart_retry_strategy(exc, "script", attempt=1)
        assert result["action"] == "abort"
        assert result["error_type"] == PipelineErrorType.AUTH_ERROR

    def test_retryable_first_attempt(self):
        exc = Exception("timeout")
        with patch(
            "shorts_maker_v2.pipeline.orchestrator.classify_error",
            return_value=PipelineErrorType.NETWORK_ERROR,
        ):
            result = PipelineOrchestrator._smart_retry_strategy(exc, "media", attempt=1)
        assert result["action"] == "retry"
        assert result["wait_sec"] > 0

    def test_max_attempts_abort(self):
        exc = Exception("timeout")
        with patch(
            "shorts_maker_v2.pipeline.orchestrator.classify_error",
            return_value=PipelineErrorType.NETWORK_ERROR,
        ):
            result = PipelineOrchestrator._smart_retry_strategy(exc, "script", attempt=3, max_attempts=3)
        assert result["action"] in {"abort", "fallback"}

    def test_max_attempts_thumbnail_fallback(self):
        exc = Exception("timeout")
        with patch(
            "shorts_maker_v2.pipeline.orchestrator.classify_error",
            return_value=PipelineErrorType.NETWORK_ERROR,
        ):
            result = PipelineOrchestrator._smart_retry_strategy(exc, "thumbnail", attempt=3, max_attempts=3)
        assert result["action"] == "fallback"

    def test_rate_limit_progressive_backoff(self):
        exc = Exception("429")
        with patch(
            "shorts_maker_v2.pipeline.orchestrator.classify_error",
            return_value=PipelineErrorType.RATE_LIMIT,
        ):
            r1 = PipelineOrchestrator._smart_retry_strategy(exc, "script", attempt=1)
            r2 = PipelineOrchestrator._smart_retry_strategy(exc, "script", attempt=2)
        assert r2["wait_sec"] >= r1["wait_sec"]


# ── run() error paths ──────────────────────────────────────────────────────


class TestRunErrorPaths:
    def _make_orchestrator(self, tmp_path, script=None, media=None, render=None):
        cfg = _load_cfg(tmp_path)
        # Error-path tests don't ship API keys, so StructureStep would
        # always exhaust LLM retries and trip the new fallback-degraded
        # signal — that flips happy-path runs to status="degraded".
        # Disable structure validation here; the dedicated structure
        # tests below opt in explicitly with "strict".
        _set_frozen_attr(cfg.project, "structure_validation", "off")
        return PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=script or StubScript(),
            media_step=media or StubMedia(),
            render_step=render or StubRender(),
        )

    def test_topic_unsuitable(self, tmp_path: Path):
        from shorts_maker_v2.pipeline.script_step import TopicUnsuitableError

        class FailScript:
            def run(self, topic, **kw):
                raise TopicUnsuitableError("not enough data")

        orch = self._make_orchestrator(tmp_path, script=FailScript())
        manifest = orch.run(topic="bad topic")
        assert manifest.status == "topic_unsuitable"
        assert any("TopicUnsuitableError" in f.get("code", "") for f in manifest.failed_steps)

    def test_generic_exception_marks_failed(self, tmp_path: Path):
        class FailScript:
            def run(self, topic, **kw):
                raise RuntimeError("boom")

        orch = self._make_orchestrator(tmp_path, script=FailScript())
        manifest = orch.run(topic="test")
        assert manifest.status == "failed"
        assert len(manifest.failed_steps) > 0

    def test_media_incomplete_raises(self, tmp_path: Path):
        """If media produces fewer assets than plans, run() catches RuntimeError."""

        class IncompleteMedia:
            def run(self, scene_plans, run_dir, cost_guard, logger=None):
                run_dir.mkdir(parents=True, exist_ok=True)
                cost_guard.add_tts_cost(1.0)
                return [], []  # 0 assets for 1 plan

        orch = self._make_orchestrator(tmp_path, media=IncompleteMedia())
        manifest = orch.run(topic="test")
        assert manifest.status == "failed"

    def test_resume_nonexistent_raises(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        with pytest.raises(FileNotFoundError, match="Cannot resume"):
            orch.run(topic="test", resume_job_id="nonexistent-id")

    def test_resume_with_checkpoint(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        # Create a fake run dir with checkpoint
        job_id = "20260326-120000-abcd1234"
        run_dir = tmp_path / "runs" / job_id
        run_dir.mkdir(parents=True, exist_ok=True)
        cp_data = {
            "title": "Resumed Title",
            "hook_pattern": "shocking_stat",
            "ab_variant": {},
            "scene_plans": [
                {
                    "scene_id": 1,
                    "narration_ko": "resumed narration",
                    "visual_prompt_en": "prompt",
                    "target_sec": 5.0,
                    "structure_role": "body",
                }
            ],
        }
        (run_dir / "checkpoint.json").write_text(json.dumps(cp_data, ensure_ascii=False), encoding="utf-8")

        manifest = orch.run(topic="resumed topic", resume_job_id=job_id)
        assert manifest.job_id == job_id
        assert manifest.title == "Resumed Title"
        assert manifest.scene_count == 1

    def test_happy_path_success(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        manifest = orch.run(topic="test topic", output_filename="test.mp4")
        assert manifest.status == "success"
        assert manifest.estimated_cost_usd > 0
        assert manifest.scene_count == 1
        assert "test.mp4" in manifest.output_path
        assert manifest.step_timings.get("total", 0) > 0

    def test_step_timings_recorded(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        manifest = orch.run(topic="timing test")
        assert "script" in manifest.step_timings
        assert "media" in manifest.step_timings
        assert "render" in manifest.step_timings
        assert "total" in manifest.step_timings

    def test_run_covers_optional_pipeline_branches_and_hold_path(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "strict")
        _set_frozen_attr(cfg.project, "scene_qc_enabled", True)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=MagicMock(),
            render_step=StubRender(),
            renderer_mode="auto",
        )

        heavy_audio = tmp_path / "run" / "heavy.mp3"
        heavy_audio.parent.mkdir(parents=True, exist_ok=True)
        heavy_audio.write_bytes(b"audio")
        original_asset = SceneAsset(
            scene_id=1,
            audio_path=str(heavy_audio),
            visual_type="image",
            visual_path=str(heavy_audio),
            duration_sec=50.0,
        )
        regenerated_asset = SceneAsset(
            scene_id=1,
            audio_path=str(heavy_audio),
            visual_type="image",
            visual_path=str(heavy_audio),
            duration_sec=50.0,
        )
        orch.media_step.run.return_value = (
            [original_asset],
            [{"scene_id": 1, "message": "asset timeout"}],
        )
        orch.media_step.regenerate_scene.return_value = (regenerated_asset, [{"scene_id": 1, "message": "retry ok"}])
        orch.thumbnail_step = MagicMock()
        orch.thumbnail_step.run.return_value = None
        orch.research_step = MagicMock()
        orch.research_step.run.return_value = SimpleNamespace(
            facts=["fact one"],
            key_data_points=["point"],
            elapsed_sec=1.2,
        )

        production_plan = SimpleNamespace(
            concept="A concept worth recording",
            target_persona="Curious viewers",
            to_dict=lambda: {"concept": "A concept worth recording"},
        )
        structure_outline = SimpleNamespace(
            scenes=[SimpleNamespace(role="hook")],
            narrative_arc="rise",
            to_dict=lambda: {"narrative_arc": "rise"},
        )
        fail_qc = FakeQcResult("fail", issues=["visual blur"], checks={"audio_ok": True})
        pass_qc = FakeQcResult("pass", checks={"audio_ok": True})
        gate3_fail = SimpleNamespace(verdict="fail", checks={"duration_ok": False}, issues=["too long"])
        gate4_hold = SimpleNamespace(verdict="hold", checks={"safe": False}, issues=["needs review"])

        with (
            patch("shorts_maker_v2.pipeline.orchestrator.PlanningStep") as planning_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.StructureStep") as structure_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate_scene_qc", side_effect=[fail_qc, pass_qc]),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate3_media", return_value=gate3_fail),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate4_final", return_value=gate4_hold),
            patch.object(orch, "_try_shorts_factory_render", return_value=(True, None)) as sf_render,
            patch("shorts_maker_v2.pipeline.orchestrator.export_srt", side_effect=RuntimeError("srt failed")),
            patch("shorts_maker_v2.pipeline.orchestrator.SeriesEngine") as series_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.CostTracker") as tracker_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.classify_error", return_value=PipelineErrorType.NETWORK_ERROR),
            patch("shorts_maker_v2.pipeline.orchestrator.logger.warning") as warning_logger,
        ):
            planning_cls.return_value.run.return_value = production_plan
            structure_cls.return_value.run.return_value = structure_outline
            series_cls.return_value.suggest_next.side_effect = RuntimeError("series failed")
            tracker_cls.return_value.record.side_effect = RuntimeError("tracker failed")

            manifest = orch.run(topic="test topic", channel="ai_tech")

        assert manifest.status == "hold"
        assert manifest.production_plan == {"concept": "A concept worth recording"}
        assert manifest.structure_outline == {"narrative_arc": "rise"}
        assert manifest.scene_qc_results[0]["retry_count"] == 1
        assert manifest.failed_steps[0]["error_type"] == PipelineErrorType.NETWORK_ERROR.value
        assert manifest.ab_variant["renderer"] == "shorts_factory"
        assert manifest.thumbnail_path == ""
        assert manifest.qc_result["verdict"] == "hold"
        sf_render.assert_called_once()
        orch.media_step.regenerate_scene.assert_called_once()
        assert warning_logger.called

    def test_early_kill_aborts_before_render_when_unresolved_exceeds_threshold(self, tmp_path: Path):
        """scene QC 미해결 씬이 임계 이상이면 렌더 전에 중단한다 (status=failed, step=early_kill)."""
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "scene_qc_enabled", True)
        _set_frozen_attr(cfg.project, "scene_qc_max_retries", 0)
        _set_frozen_attr(cfg.project, "early_kill_enabled", True)
        _set_frozen_attr(cfg.project, "early_kill_max_unresolved_scenes", 1)
        render = MagicMock()
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=render,
        )
        fail_qc = FakeQcResult("fail", issues=["visual blur"], checks={"visual_ok": False})

        with patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate_scene_qc", return_value=fail_qc):
            manifest = orch.run(topic="test topic", channel="ai_tech")

        assert manifest.status == "failed"
        assert manifest.failed_steps[0]["step"] == "early_kill"
        assert manifest.failed_steps[0]["error_type"] == "quality_gate"
        assert manifest.failed_steps[0]["is_retryable"] is False
        assert any(d["step"] == "scene_qc" for d in manifest.degraded_steps)
        render.run.assert_not_called()

    def test_early_kill_disabled_by_default_does_not_abort(self, tmp_path: Path):
        """early_kill_enabled=False(기본)면 미해결 씬이 있어도 렌더까지 진행한다."""
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "scene_qc_enabled", True)
        _set_frozen_attr(cfg.project, "scene_qc_max_retries", 0)
        assert cfg.project.early_kill_enabled is False
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )
        fail_qc = FakeQcResult("fail", issues=["visual blur"], checks={"visual_ok": False})

        with patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate_scene_qc", return_value=fail_qc):
            manifest = orch.run(topic="test topic", channel="ai_tech")

        assert manifest.status != "failed"
        assert any(d["step"] == "scene_qc" for d in manifest.degraded_steps)

    def test_scene_qc_duration_failure_regenerates_audio(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "off")
        _set_frozen_attr(cfg.project, "scene_qc_enabled", True)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=MagicMock(),
            render_step=StubRender(),
        )
        orch.thumbnail_step = MagicMock()
        orch.thumbnail_step.run.return_value = None

        audio = tmp_path / "run" / "a.mp3"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(b"audio")
        original_asset = SceneAsset(
            scene_id=1,
            audio_path=str(audio),
            visual_type="image",
            visual_path=str(audio),
            duration_sec=20.0,
        )
        regenerated_asset = SceneAsset(
            scene_id=1,
            audio_path=str(audio),
            visual_type="image",
            visual_path=str(audio),
            duration_sec=5.0,
        )
        orch.media_step.run.return_value = ([original_asset], [])
        orch.media_step.regenerate_scene.return_value = (regenerated_asset, [])

        duration_fail = FakeQcResult(
            "fail",
            issues=["Duration 20.0s outside [1.0,8.0]s"],
            checks={"audio_ok": True, "visual_ok": True, "duration_ok": False},
        )
        pass_qc = FakeQcResult("pass", checks={"audio_ok": True, "visual_ok": True, "duration_ok": True})
        gate3_pass = SimpleNamespace(verdict="pass", checks={"ok": True}, issues=[])
        gate4_pass = SimpleNamespace(verdict="pass", checks={"ok": True}, issues=[])

        with (
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate_scene_qc", side_effect=[duration_fail, pass_qc]),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate3_media", return_value=gate3_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate4_final", return_value=gate4_pass),
        ):
            manifest = orch.run(topic="duration retry")

        assert manifest.scene_qc_results[0]["retry_count"] == 1
        assert orch.media_step.regenerate_scene.call_args.kwargs["component"] == "audio"

    def test_run_success_path_covers_upload_thumbnail_srt_and_series(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "upload_ready_dir", str(tmp_path / "upload-ready"))
        # No LLM API keys are provided in tests, so StructureStep would
        # exhaust its retries and trip the fallback-degraded signal.
        # This test asserts a clean happy path; disable structure here.
        _set_frozen_attr(cfg.project, "structure_validation", "off")
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )
        thumb_file = tmp_path / "output" / "thumb.png"
        thumb_file.parent.mkdir(parents=True, exist_ok=True)
        thumb_file.write_bytes(b"thumb")
        orch.thumbnail_step = MagicMock()
        orch.thumbnail_step.run.return_value = str(thumb_file)

        gate3_pass = SimpleNamespace(verdict="pass", checks={"duration_ok": True}, issues=[])
        gate4_pass = SimpleNamespace(verdict="pass", checks={"final_ok": True}, issues=[])
        srt_file = tmp_path / "output" / "job.srt"
        series_plan = SimpleNamespace(
            series_id="series-1",
            episode=2,
            suggested_title="Next episode",
            to_dict=lambda: {"series_id": "series-1", "episode": 2},
        )

        def _export_srt(**kwargs):
            del kwargs
            srt_file.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
            return srt_file

        with (
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate3_media", return_value=gate3_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate4_final", return_value=gate4_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.export_srt", side_effect=_export_srt),
            patch("shorts_maker_v2.pipeline.orchestrator.SeriesEngine") as series_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.CostTracker") as tracker_cls,
        ):
            series_cls.return_value.suggest_next.return_value = series_plan
            manifest = orch.run(topic="test topic", output_filename="upload.mp4")

        copied_output = Path(cfg.project.upload_ready_dir) / "upload.mp4"
        assert manifest.status == "success"
        assert manifest.thumbnail_path == str(thumb_file)
        assert manifest.srt_path.endswith(".srt")
        assert manifest.series_suggestion == {"series_id": "series-1", "episode": 2}
        assert copied_output.exists()
        tracker_cls.return_value.record.assert_called_once()

    def test_run_marks_manifest_degraded_when_structure_falls_back(self, tmp_path: Path):
        # Quality regression guard for the 2026-05-11 silent-fallback case:
        # StructureStep 이 LLM 재시도 모두 실패해 결정론 폴백을 반환하면,
        # 영상은 ship 되지만 manifest.status 는 "success" 가 아닌 "degraded" 로
        # 떨어져야 한다. silently 보일러플레이트 outline 으로 영상이 ship
        # 되는 사례가 production 에서 한 번 잡혔다 (runs/20260511-003133-*).
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "strict")
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )

        production_plan = SimpleNamespace(
            concept="quiet topic",
            target_persona="curious viewer",
            to_dict=lambda: {"concept": "quiet topic"},
        )
        fallback_outline = SimpleNamespace(
            scenes=[SimpleNamespace(role="hook")],
            narrative_arc="quiet_storytelling",
            is_fallback=True,
            to_dict=lambda: {
                "narrative_arc": "quiet_storytelling",
                "is_fallback": True,
            },
        )
        gate3_pass = SimpleNamespace(verdict="pass", checks={"duration_ok": True}, issues=[])
        gate4_pass = SimpleNamespace(verdict="pass", checks={"final_ok": True}, issues=[])

        with (
            patch("shorts_maker_v2.pipeline.orchestrator.PlanningStep") as planning_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.StructureStep") as structure_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate3_media", return_value=gate3_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate4_final", return_value=gate4_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.CostTracker"),
        ):
            planning_cls.return_value.run.return_value = production_plan
            structure_cls.return_value.run.return_value = fallback_outline
            manifest = orch.run(topic="structure fallback topic")

        assert manifest.status == "degraded"
        structure_dgr = [d for d in manifest.degraded_steps if d.get("step") == "structure"]
        assert len(structure_dgr) == 1, manifest.degraded_steps
        assert structure_dgr[0]["error_type"] == "outline_fallback"
        assert structure_dgr[0]["blocking"] is False

    def test_run_does_not_mark_structure_degraded_on_normal_outline(self, tmp_path: Path):
        # 정상 outline (is_fallback=False) 일 때는 structure entry 가 degraded_steps
        # 에 들어가면 안 된다 — false positive 가 새지 않게 한다.
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "strict")
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )

        production_plan = SimpleNamespace(
            concept="quiet topic",
            target_persona="curious viewer",
            to_dict=lambda: {"concept": "quiet topic"},
        )
        good_outline = SimpleNamespace(
            scenes=[SimpleNamespace(role="hook")],
            narrative_arc="quiet_storytelling",
            is_fallback=False,
            to_dict=lambda: {
                "narrative_arc": "quiet_storytelling",
                "is_fallback": False,
            },
        )
        gate3_pass = SimpleNamespace(verdict="pass", checks={"duration_ok": True}, issues=[])
        gate4_pass = SimpleNamespace(verdict="pass", checks={"final_ok": True}, issues=[])

        with (
            patch("shorts_maker_v2.pipeline.orchestrator.PlanningStep") as planning_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.StructureStep") as structure_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate3_media", return_value=gate3_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate4_final", return_value=gate4_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.CostTracker"),
        ):
            planning_cls.return_value.run.return_value = production_plan
            structure_cls.return_value.run.return_value = good_outline
            manifest = orch.run(topic="structure happy topic")

        assert manifest.status == "success"
        assert not any(d.get("step") == "structure" for d in manifest.degraded_steps)

    def test_run_marks_manifest_degraded_when_hook_score_is_weak(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "off")
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=WeakHookScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )
        gate3_pass = SimpleNamespace(verdict="pass", checks={"duration_ok": True}, issues=[])
        gate4_pass = SimpleNamespace(verdict="pass", checks={"final_ok": True}, issues=[])

        with (
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate3_media", return_value=gate3_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate4_final", return_value=gate4_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.CostTracker"),
        ):
            manifest = orch.run(topic="weak hook topic")

        assert manifest.status == "degraded"
        assert manifest.hook_score is not None
        assert manifest.hook_score["passed"] is False
        matches = [d for d in manifest.degraded_steps if d.get("step") == "hook_score"]
        assert len(matches) == 1, manifest.degraded_steps
        assert matches[0]["error_type"] == "hook_below_threshold"
        assert matches[0]["is_retryable"] is True
        assert matches[0]["blocking"] is False

    def test_run_marks_manifest_degraded_when_research_fails(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )
        orch.research_step = MagicMock()
        orch.research_step.run.side_effect = RuntimeError("research timeout")
        gate3_pass = SimpleNamespace(verdict="pass", checks={"duration_ok": True}, issues=[])
        gate4_pass = SimpleNamespace(verdict="pass", checks={"final_ok": True}, issues=[])

        with (
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate3_media", return_value=gate3_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.QCStep.gate4_final", return_value=gate4_pass),
            patch("shorts_maker_v2.pipeline.orchestrator.CostTracker"),
        ):
            manifest = orch.run(topic="research failure topic")

        assert manifest.status == "degraded"
        assert manifest.failed_steps == []
        assert manifest.degraded_steps[0]["step"] == "research"

    def test_shorts_factory_mode_with_channel_fails_fast_when_adapter_fails(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
            renderer_mode="shorts_factory",
        )

        with patch.object(orch, "_try_shorts_factory_render", return_value=(False, "sf boom")):
            manifest = orch.run(topic="adapter fail", channel="ai_tech")

        assert manifest.status == "failed"
        assert any("sf boom" in step["message"] for step in manifest.failed_steps)


# ── _try_shorts_factory_render ──────────────────────────────────────────────


def test_try_shorts_factory_delegates_to_render_step():
    mock_logger = MagicMock()
    plans = [ScenePlan(scene_id=1, narration_ko="n", visual_prompt_en="p", target_sec=5.0)]
    assets = [SceneAsset(scene_id=1, audio_path="a.mp3", visual_type="image", visual_path="i.png", duration_sec=5.0)]

    with patch(
        "shorts_maker_v2.pipeline.orchestrator.RenderStep.try_render_with_adapter",
        return_value=(False, "not installed"),
    ) as mock_adapter:
        ok, err = PipelineOrchestrator._try_shorts_factory_render(
            channel="ai_tech",
            scene_plans=plans,
            scene_assets=assets,
            output_path=Path("out.mp4"),
            logger=mock_logger,
        )
    assert ok is False
    assert err == "not installed"
    mock_adapter.assert_called_once()


# ── renderer_mode="shorts_factory" without channel ──────────────────────────


def test_shorts_factory_mode_without_channel_raises(tmp_path: Path):
    """renderer_mode=shorts_factory + no channel -> RuntimeError in run()."""
    cfg = _load_cfg(tmp_path)
    orch = PipelineOrchestrator(
        config=cfg,
        base_dir=tmp_path,
        script_step=StubScript(),
        media_step=StubMedia(),
        render_step=StubRender(),
        renderer_mode="shorts_factory",
    )
    # channel="" triggers the error branch
    manifest = orch.run(topic="test", channel="")
    assert manifest.status == "failed"


# ── Scene QC summary aggregation ────────────────────────────────────────────


class TestAggregateSceneQCSummary:
    """_aggregate_scene_qc_summary: 재시도 후 잔여 실패를 manifest로 표면화한다."""

    def test_empty_list_returns_zero_totals(self):
        summary = PipelineOrchestrator._aggregate_scene_qc_summary([])
        assert summary == {"passed": 0, "total": 0, "unresolved": [], "verdict": "pass"}

    def test_all_pass_returns_pass_verdict(self):
        results = [
            {"scene_id": 1, "verdict": "pass", "issues": [], "retry_count": 0},
            {"scene_id": 2, "verdict": "pass", "issues": [], "retry_count": 1},
        ]
        summary = PipelineOrchestrator._aggregate_scene_qc_summary(results)
        assert summary["passed"] == 2
        assert summary["total"] == 2
        assert summary["unresolved"] == []
        assert summary["verdict"] == "pass"

    def test_partial_fail_lists_unresolved_scenes(self):
        results = [
            {"scene_id": 1, "verdict": "pass", "issues": [], "retry_count": 0},
            {
                "scene_id": 2,
                "verdict": "fail_retry",
                "issues": ["Audio file missing", "Visual dimensions 320x240 below minimum 540px"],
                "retry_count": 2,
            },
            {
                "scene_id": 3,
                "verdict": "fail_retry",
                "issues": ["Narration/audio rate 50.0 chars/s outside [1.5,10.0]"],
                "retry_count": 2,
            },
        ]
        summary = PipelineOrchestrator._aggregate_scene_qc_summary(results)
        assert summary["passed"] == 1
        assert summary["total"] == 3
        assert summary["verdict"] == "degraded"
        assert [u["scene_id"] for u in summary["unresolved"]] == [2, 3]
        assert summary["unresolved"][0]["retry_count"] == 2
        assert "Audio file missing" in summary["unresolved"][0]["issues"]

    def test_missing_keys_are_tolerated(self):
        # FakeQcResult.to_dict()처럼 scene_id 누락된 케이스도 KeyError 없이 처리.
        results = [
            {"verdict": "pass"},
            {"verdict": "fail_retry", "issues": ["x"]},
        ]
        summary = PipelineOrchestrator._aggregate_scene_qc_summary(results)
        assert summary["passed"] == 1
        assert summary["total"] == 2
        assert summary["verdict"] == "degraded"
        assert summary["unresolved"][0]["scene_id"] is None
        assert summary["unresolved"][0]["retry_count"] == 0


# ── SemanticQCStep orchestrator integration ─────────────────────────────────


class TestSceneQCRetryComponent:
    """Scene QC retry routing should regenerate the component that can fix the issue."""

    def test_audio_timing_failure_regenerates_audio(self):
        result = FakeQcResult(
            "fail",
            issues=["Duration 20.0s outside [1.0,8.0]s"],
            checks={"audio_ok": True, "visual_ok": True, "duration_ok": False},
        )

        assert PipelineOrchestrator._scene_qc_retry_component(result) == "audio"

    def test_visual_failure_regenerates_visual(self):
        result = FakeQcResult(
            "fail",
            issues=["Visual dimensions 320x240 below minimum 540px"],
            checks={"audio_ok": True, "visual_ok": False},
        )

        assert PipelineOrchestrator._scene_qc_retry_component(result) == "visual"

    def test_audio_integrity_failure_regenerates_both(self):
        result = FakeQcResult(
            "fail",
            issues=["Audio file missing"],
            checks={"audio_ok": False, "visual_ok": True},
        )

        assert PipelineOrchestrator._scene_qc_retry_component(result) == "both"

    def test_script_only_failure_does_not_spend_media_retry(self):
        result = FakeQcResult(
            "fail",
            issues=["Hook narration too long"],
            checks={"audio_ok": True, "visual_ok": True, "hook_concise": False},
        )

        assert PipelineOrchestrator._scene_qc_retry_component(result) is None


class TestSemanticQCIntegration:
    """SemanticQCStep wiring inside PipelineOrchestrator.run().

    Covers the opt-in semantic_qc block: default-disabled skip, pass populates
    manifest, degraded adds a non-blocking degraded_steps entry with weak
    transitions, error swallows silently, and exceptions never crash the run.
    """

    def _make_orchestrator(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "off")
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )
        return cfg, orch

    def test_disabled_skips_semantic_qc_block(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        assert cfg.project.semantic_qc_enabled is False
        with patch("shorts_maker_v2.pipeline.orchestrator.SemanticQCStep") as semantic_cls:
            manifest = orch.run(topic="off path")
        semantic_cls.assert_not_called()
        assert manifest.semantic_qc is None
        assert "semantic_qc" not in manifest.step_timings
        assert not any(d.get("step") == "semantic_qc" for d in manifest.degraded_steps)

    def test_enabled_pass_populates_manifest_and_records_timing(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "semantic_qc_enabled", True)
        _set_frozen_attr(cfg.project, "semantic_qc_min_score", 6)
        fake_result = SemanticQCResult(
            scene_flow_score=8,
            tone_consistency_score=7,
            overall_score=8,
            verdict="pass",
            feedback="cohesive",
        )
        with patch("shorts_maker_v2.pipeline.orchestrator.SemanticQCStep") as semantic_cls:
            semantic_cls.return_value.run.return_value = fake_result
            manifest = orch.run(topic="pass path")
        semantic_cls.assert_called_once()
        _, kwargs = semantic_cls.call_args
        assert kwargs["min_score"] == 6
        assert manifest.semantic_qc is not None
        assert manifest.semantic_qc["verdict"] == "pass"
        assert manifest.semantic_qc["scene_flow_score"] == 8
        assert not any(d.get("step") == "semantic_qc" for d in manifest.degraded_steps)
        assert "semantic_qc" in manifest.step_timings

    def test_enabled_degraded_adds_non_blocking_step_with_weak_transitions(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "semantic_qc_enabled", True)
        _set_frozen_attr(cfg.project, "semantic_qc_min_score", 7)
        weak = [{"from": 1, "to": 2, "reason": "abrupt tone shift"}]
        fake_result = SemanticQCResult(
            scene_flow_score=4,
            tone_consistency_score=3,
            overall_score=3,
            weak_transitions=weak,
            verdict="degraded",
            feedback="flow weak",
        )
        with patch("shorts_maker_v2.pipeline.orchestrator.SemanticQCStep") as semantic_cls:
            semantic_cls.return_value.run.return_value = fake_result
            manifest = orch.run(topic="degraded path")
        assert manifest.semantic_qc["verdict"] == "degraded"
        matches = [d for d in manifest.degraded_steps if d.get("step") == "semantic_qc"]
        assert len(matches) == 1
        entry = matches[0]
        assert entry["error_type"] == "semantic_below_threshold"
        assert entry["is_retryable"] is False
        assert entry["blocking"] is False
        assert entry["weak_transitions"] == weak
        assert "min=7" in entry["message"]
        assert "flow=4" in entry["message"]
        assert "tone=3" in entry["message"]

    def test_enabled_error_verdict_records_manifest_but_no_degraded_step(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "semantic_qc_enabled", True)
        fake_result = SemanticQCResult(verdict="error", feedback="LLM returned non-dict")
        with patch("shorts_maker_v2.pipeline.orchestrator.SemanticQCStep") as semantic_cls:
            semantic_cls.return_value.run.return_value = fake_result
            manifest = orch.run(topic="error path")
        assert manifest.semantic_qc["verdict"] == "error"
        assert not any(d.get("step") == "semantic_qc" for d in manifest.degraded_steps)
        assert "semantic_qc" in manifest.step_timings

    def test_enabled_run_exception_is_swallowed(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "semantic_qc_enabled", True)
        with patch("shorts_maker_v2.pipeline.orchestrator.SemanticQCStep") as semantic_cls:
            semantic_cls.return_value.run.side_effect = RuntimeError("LLM died")
            manifest = orch.run(topic="exception path")
        assert manifest.semantic_qc is None
        assert not any(d.get("step") == "semantic_qc" for d in manifest.degraded_steps)
        assert "semantic_qc" in manifest.step_timings


class TestRetentionSimulatorIntegration:
    """RetentionSimulatorStep wiring inside PipelineOrchestrator.run().

    Covers the opt-in retention_sim block: default-disabled skip, pass
    populates manifest, degraded adds a non-blocking degraded_steps entry
    carrying the weakest scene + rewrite directive, and exceptions never
    crash the run.
    """

    def _make_orchestrator(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "off")
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )
        return cfg, orch

    def test_disabled_skips_retention_sim_block(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        assert cfg.project.retention_sim_enabled is False
        with patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls:
            manifest = orch.run(topic="off path")
        sim_cls.assert_not_called()
        assert manifest.retention_simulation is None
        assert "retention_simulation" not in manifest.step_timings

    def test_enabled_pass_populates_manifest_and_records_timing(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_sim_enabled", True)
        _set_frozen_attr(cfg.project, "retention_sim_min_retention", 0.55)
        fake_result = RetentionSimulationResult(
            predicted_retention=0.72,
            loop_probability=0.4,
            verdict="pass",
            source="llm",
            feedback="strong retention",
        )
        with patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls:
            sim_cls.return_value.run.return_value = fake_result
            manifest = orch.run(topic="pass path")
        sim_cls.assert_called_once()
        _, kwargs = sim_cls.call_args
        assert kwargs["min_retention"] == 0.55
        assert manifest.retention_simulation is not None
        assert manifest.retention_simulation["verdict"] == "pass"
        assert manifest.retention_simulation["predicted_retention"] == 0.72
        assert not any(d.get("step") == "retention_simulation" for d in manifest.degraded_steps)
        assert "retention_simulation" in manifest.step_timings

    def test_enabled_run_writes_retention_report_md(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_sim_enabled", True)
        fake_result = RetentionSimulationResult(
            predicted_retention=0.7,
            verdict="pass",
            source="llm",
            feedback="solid",
        )
        with patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls:
            sim_cls.return_value.run.return_value = fake_result
            orch.run(topic="report path")
        reports = list(tmp_path.rglob("retention_report.md"))
        assert len(reports) == 1
        content = reports[0].read_text(encoding="utf-8")
        assert "리텐션 리포트" in content
        assert "예측 요약" in content

    def test_disabled_run_writes_no_retention_report(self, tmp_path: Path):
        _cfg, orch = self._make_orchestrator(tmp_path)
        orch.run(topic="no report path")
        assert list(tmp_path.rglob("retention_report.md")) == []

    def test_enabled_degraded_adds_non_blocking_step(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_sim_enabled", True)
        _set_frozen_attr(cfg.project, "retention_sim_min_retention", 0.6)
        fake_result = RetentionSimulationResult(
            predicted_retention=0.32,
            loop_probability=0.2,
            weakest_scene_id=2,
            first_dropoff_scene_id=2,
            rewrite_directive="Tighten scene 2.",
            verdict="degraded",
            source="heuristic",
            feedback="weak middle",
        )
        with patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls:
            sim_cls.return_value.run.return_value = fake_result
            manifest = orch.run(topic="degraded path")
        assert manifest.retention_simulation["verdict"] == "degraded"
        matches = [d for d in manifest.degraded_steps if d.get("step") == "retention_simulation"]
        assert len(matches) == 1
        entry = matches[0]
        assert entry["error_type"] == "retention_below_threshold"
        assert entry["is_retryable"] is False
        assert entry["blocking"] is False
        assert entry["weakest_scene_id"] == 2
        assert entry["first_dropoff_scene_id"] == 2
        assert "Tighten scene 2." in entry["message"]
        assert "source=heuristic" in entry["message"]

    def test_enabled_run_exception_is_swallowed(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_sim_enabled", True)
        with patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls:
            sim_cls.return_value.run.side_effect = RuntimeError("LLM died")
            manifest = orch.run(topic="exception path")
        assert manifest.retention_simulation is None
        assert not any(d.get("step") == "retention_simulation" for d in manifest.degraded_steps)
        assert "retention_simulation" in manifest.step_timings


class TestRetentionAutoFixIntegration:
    """RetentionAutoFixer wiring inside PipelineOrchestrator.run().

    The auto-fix closed-loop runs only when retention_sim produced a
    `degraded` verdict and retention_autofix_enabled is set. Covers the
    default-off skip, the enabled+degraded path populating the manifest,
    the pass-verdict no-op, and exception isolation.
    """

    def _make_orchestrator(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "off")
        _set_frozen_attr(cfg.project, "retention_sim_enabled", True)
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )
        return cfg, orch

    @staticmethod
    def _degraded_sim() -> RetentionSimulationResult:
        return RetentionSimulationResult(
            predicted_retention=0.32,
            verdict="degraded",
            weakest_scene_id=1,
            rewrite_directive="fix it",
        )

    def test_disabled_skips_autofix_block(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        assert cfg.project.retention_autofix_enabled is False
        with (
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionAutoFixer") as fixer_cls,
        ):
            sim_cls.return_value.run.return_value = self._degraded_sim()
            manifest = orch.run(topic="autofix off")
        fixer_cls.assert_not_called()
        assert manifest.retention_autofix is None
        assert "retention_autofix" not in manifest.step_timings

    def test_enabled_degraded_runs_autofix_and_populates_manifest(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_autofix_enabled", True)
        _set_frozen_attr(cfg.project, "retention_autofix_max_passes", 2)
        autofix_result = RetentionAutoFixResult(
            applied=True,
            passes=1,
            before_retention=0.32,
            after_retention=0.61,
            verdict="improved",
            feedback="rewrote scene 1",
        )
        with (
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionAutoFixer") as fixer_cls,
        ):
            sim_cls.return_value.run.return_value = self._degraded_sim()
            fixer_cls.return_value.fix.return_value = autofix_result
            manifest = orch.run(topic="autofix degraded")
        fixer_cls.assert_called_once()
        _, kwargs = fixer_cls.call_args
        assert kwargs["max_passes"] == 2
        assert manifest.retention_autofix is not None
        assert manifest.retention_autofix["verdict"] == "improved"
        assert manifest.retention_autofix["after_retention"] == 0.61
        assert "retention_autofix" in manifest.step_timings

    def test_pass_verdict_does_not_trigger_autofix(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_autofix_enabled", True)
        passing_sim = RetentionSimulationResult(predicted_retention=0.8, verdict="pass")
        with (
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionAutoFixer") as fixer_cls,
        ):
            sim_cls.return_value.run.return_value = passing_sim
            manifest = orch.run(topic="autofix pass")
        fixer_cls.assert_not_called()
        assert manifest.retention_autofix is None

    def test_autofix_exception_is_swallowed(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_autofix_enabled", True)
        with (
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls,
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionAutoFixer") as fixer_cls,
        ):
            sim_cls.return_value.run.return_value = self._degraded_sim()
            fixer_cls.return_value.fix.side_effect = RuntimeError("rewrite died")
            manifest = orch.run(topic="autofix boom")
        assert manifest.retention_autofix is None
        assert "retention_autofix" in manifest.step_timings


class TestRetentionPreAssetStage:
    """retention_sim_stage='pre_asset' — 진짜 closed-loop.

    pre_asset 스테이지에서는 리텐션 시뮬레이션과 자가 치유가 TTS/미디어
    생성 *전* 에 실행돼, 검증된 재작성이 scene_plans 에 반영되고 개선된
    대본이 그대로 렌더된다. post_asset 블록은 중복 실행되지 않는다.
    """

    def _make_orchestrator(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "structure_validation", "off")
        _set_frozen_attr(cfg.project, "retention_sim_enabled", True)
        _set_frozen_attr(cfg.project, "retention_sim_stage", "pre_asset")
        orch = PipelineOrchestrator(
            config=cfg,
            base_dir=tmp_path,
            script_step=StubScript(),
            media_step=StubMedia(),
            render_step=StubRender(),
        )
        return cfg, orch

    def test_pre_asset_simulates_before_assets_and_only_once(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        passing = RetentionSimulationResult(predicted_retention=0.7, verdict="pass", source="llm")
        with patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls:
            sim_cls.return_value.run.return_value = passing
            manifest = orch.run(topic="pre asset")
        assert manifest.retention_simulation is not None
        assert manifest.retention_simulation["verdict"] == "pass"
        # pre_asset 단계라 실제 씬 길이(asset) 없이 호출된다.
        assert sim_cls.return_value.run.call_args.kwargs["scene_assets"] is None
        # post_asset 블록 중복 실행 없음 — 시뮬레이션은 정확히 1회.
        assert sim_cls.return_value.run.call_count == 1

    def test_pre_asset_autofix_rewrite_reaches_render(self, tmp_path: Path):
        import json as _json

        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_autofix_enabled", True)
        degraded = RetentionSimulationResult(
            predicted_retention=0.3,
            verdict="degraded",
            weakest_scene_id=1,
            rewrite_directive="fix scene 1",
        )
        new_narration = "자가치유로 새로 쓴 hook 나레이션"
        improved = RetentionAutoFixResult(
            applied=True,
            verdict="improved",
            before_retention=0.3,
            after_retention=0.62,
            rewrites=[{"scene_id": 1, "after": new_narration, "accepted": True}],
        )
        with (
            patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls,
            patch.object(RetentionAutoFixer, "fix", return_value=improved),
        ):
            sim_cls.return_value.run.return_value = degraded
            manifest = orch.run(topic="pre asset autofix")
        assert manifest.retention_autofix is not None
        assert manifest.retention_autofix["applied_to_render"] is True
        # 체크포인트가 재작성된 대본을 기록했는지 — 재작성이 파이프라인에 반영된 증거.
        checkpoints = list(tmp_path.rglob("checkpoint.json"))
        assert checkpoints, "checkpoint.json not found"
        cp = _json.loads(checkpoints[0].read_text(encoding="utf-8"))
        narrations = [s["narration_ko"] for s in cp["scene_plans"]]
        assert new_narration in narrations

    def test_post_asset_stage_does_not_run_at_pre_asset(self, tmp_path: Path):
        cfg, orch = self._make_orchestrator(tmp_path)
        _set_frozen_attr(cfg.project, "retention_sim_stage", "post_asset")
        with patch("shorts_maker_v2.pipeline.orchestrator.RetentionSimulatorStep") as sim_cls:
            sim_cls.return_value.run.return_value = RetentionSimulationResult(predicted_retention=0.7, verdict="pass")
            manifest = orch.run(topic="post asset")
        # post_asset 단계라 실제 씬 길이로 호출된다 (scene_assets 가 None 이 아님).
        assert sim_cls.return_value.run.call_args.kwargs["scene_assets"] is not None
        assert manifest.retention_simulation is not None
