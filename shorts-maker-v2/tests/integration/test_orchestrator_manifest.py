from __future__ import annotations

import json
from pathlib import Path

import yaml

from shorts_maker_v2.config import load_config
from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator


class StubScriptStep:
    def run(self, topic: str, **kwargs):
        return (
            "stub-title",
            [ScenePlan(scene_id=1, narration_ko=f"{topic} narration", visual_prompt_en="prompt", target_sec=5.0)],
            "shocking_stat",
        )


class StubMediaStep:
    def run(self, scene_plans, run_dir: Path, cost_guard, logger=None):  # noqa: ARG002
        run_dir.mkdir(parents=True, exist_ok=True)
        dummy_audio = run_dir / "dummy.mp3"
        dummy_audio.write_bytes(b"fake")
        cost_guard.add_tts_cost(5.0)
        return [
            SceneAsset(
                scene_id=1,
                audio_path=str(dummy_audio),
                visual_type="image",
                visual_path=str(dummy_audio),
                duration_sec=5.0,
            )
        ], []


class StubRenderStep:
    def run(
        self,
        scene_plans,
        scene_assets,
        output_dir: Path,
        output_filename: str,
        run_dir: Path,
        title: str = "",
        topic: str = "",
    ):  # noqa: ARG002
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        output_path.write_bytes(b"mp4")
        return output_path


def _make_config_file(tmp_path: Path) -> Path:
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
        "costs": {"llm_per_job": 0.25, "tts_per_second": 0.001, "veo_per_second": 0.03, "image_per_scene": 0.04},
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


def test_orchestrator_writes_manifest(tmp_path: Path) -> None:
    config_path = _make_config_file(tmp_path)
    config = load_config(config_path)
    orchestrator = PipelineOrchestrator(
        config=config,
        base_dir=tmp_path,
        script_step=StubScriptStep(),
        media_step=StubMediaStep(),
        render_step=StubRenderStep(),
    )

    manifest = orchestrator.run(topic="테스트 주제", output_filename="sample.mp4")
    assert manifest.status == "success"
    assert manifest.output_path.endswith("sample.mp4")
    assert manifest.estimated_cost_usd > 0

    output_manifest_path = Path(tmp_path / "output" / f"{manifest.job_id}_manifest.json")
    assert output_manifest_path.exists()
    loaded = json.loads(output_manifest_path.read_text(encoding="utf-8"))
    assert loaded["job_id"] == manifest.job_id
    assert loaded["status"] == "success"
