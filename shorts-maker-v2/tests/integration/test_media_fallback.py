from __future__ import annotations

from pathlib import Path

from PIL import Image
import yaml

from shorts_maker_v2.config import load_config
from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.pipeline.media_step import MediaStep
from shorts_maker_v2.utils.cost_guard import CostGuard


class FakeOpenAIClient:
    def generate_tts(self, *, model: str, voice: str, speed: float, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"not-real-mp3")
        return output_path

    def generate_image(self, *, model: str, prompt: str, size: str, quality: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (640, 1136), color=(20, 40, 60))
        image.save(output_path, format="PNG")
        return output_path


class FailingGoogleClient:
    def generate_video(self, **_: object) -> Path:
        raise RuntimeError("veo unavailable")


def _make_config(tmp_path: Path):
    payload = {
        "project": {"language": "ko-KR", "default_scene_count": 1},
        "video": {"target_duration_sec": [35, 45], "resolution": [1080, 1920], "fps": 30, "scene_video_duration_sec": 5, "aspect_ratio": "9:16"},
        "providers": {"llm": "openai", "tts": "openai", "visual_primary": "google-veo", "visual_fallback": "openai-image"},
        "limits": {"max_cost_usd": 2.0, "max_retries": 1, "request_timeout_sec": 5},
        "costs": {"llm_per_job": 0.25, "tts_per_second": 0.001, "veo_per_second": 0.03, "image_per_scene": 0.04},
        "paths": {"output_dir": "output", "logs_dir": "logs", "runs_dir": "runs"},
        "captions": {"font_size": 64, "margin_x": 90, "bottom_offset": 240, "text_color": "#FFD700", "stroke_color": "#000000", "stroke_width": 4, "line_spacing": 12, "font_candidates": ["C:/Windows/Fonts/malgun.ttf"]},
        "cache": {"enabled": False},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return load_config(config_path)


def test_media_step_fallbacks_to_image_when_video_fails(tmp_path: Path, monkeypatch) -> None:
    config = _make_config(tmp_path)
    step = MediaStep(config=config, openai_client=FakeOpenAIClient(), google_client=FailingGoogleClient())
    monkeypatch.setattr(step, "_read_audio_duration", lambda *_, **__: 5.0)

    scene_plans = [ScenePlan(scene_id=1, narration_ko="안녕하세요", visual_prompt_en="A cinematic vertical scene", target_sec=5.0)]
    cost_guard = CostGuard(max_cost_usd=config.limits.max_cost_usd, price_table=config.costs)

    assets, failures = step.run(scene_plans=scene_plans, run_dir=tmp_path / "run", cost_guard=cost_guard, logger=None)

    assert len(assets) == 1
    assert assets[0].visual_type == "image"
    assert Path(assets[0].visual_path).exists()
    assert failures
    assert failures[0]["step"] == "visual_primary"
