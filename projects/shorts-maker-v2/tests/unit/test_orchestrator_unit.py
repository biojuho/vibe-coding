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
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

from shorts_maker_v2.models import (
    JobManifest,
    SceneAsset,
    ScenePlan,
)
from shorts_maker_v2.pipeline.error_types import PipelineErrorType
from shorts_maker_v2.pipeline.orchestrator import (
    JsonlLogger,
    PipelineOrchestrator,
)

# ── helpers ─────────────────────────────────────────────────────────────────


def _make_config_yaml(tmp_path: Path) -> Path:
    payload = {
        "project": {"language": "ko-KR", "default_scene_count": 1},
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
        assert manifest.scene_qc_results[0]["retry_count"] == 0
        assert manifest.failed_steps[0]["error_type"] == PipelineErrorType.NETWORK_ERROR.value
        assert manifest.ab_variant["renderer"] == "shorts_factory"
        assert manifest.thumbnail_path == ""
        assert manifest.qc_result["verdict"] == "hold"
        sf_render.assert_called_once()
        orch.media_step.regenerate_scene.assert_called_once()
        assert warning_logger.called

    def test_run_success_path_covers_upload_thumbnail_srt_and_series(self, tmp_path: Path):
        cfg = _load_cfg(tmp_path)
        _set_frozen_attr(cfg.project, "upload_ready_dir", str(tmp_path / "upload-ready"))
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
