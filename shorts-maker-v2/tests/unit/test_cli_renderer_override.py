from __future__ import annotations

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import yaml

ffmpeg_path = shutil.which("ffmpeg")
if ffmpeg_path:
    os.environ.setdefault("IMAGEIO_FFMPEG_EXE", ffmpeg_path)
    os.environ.setdefault("FFMPEG_BINARY", ffmpeg_path)

from shorts_maker_v2.cli import _apply_channel_overrides
from shorts_maker_v2.config import load_config


def _write_config(path: Path, engine: str = "native") -> Path:
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
            "visual_primary": "openai-image",
            "visual_fallback": "openai-image",
        },
        "limits": {"max_cost_usd": 2.0, "max_retries": 1, "request_timeout_sec": 5},
        "costs": {"llm_per_job": 0.01, "tts_per_second": 0.001, "veo_per_second": 0.03, "image_per_scene": 0.04},
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
        "rendering": {"engine": engine},
    }
    config_path = path / "config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def test_apply_channel_overrides_keeps_config_renderer_when_cli_empty(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path, engine="auto"))
    args = SimpleNamespace(
        channel="",
        tts_voice="",
        style_preset="",
        font_color="",
        image_prefix="",
        renderer="",
    )

    updated = _apply_channel_overrides(config, args)

    assert updated.rendering.engine == "auto"


def test_apply_channel_overrides_prefers_cli_renderer(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path, engine="native"))
    args = SimpleNamespace(
        channel="",
        tts_voice="",
        style_preset="",
        font_color="",
        image_prefix="",
        renderer="shorts_factory",
    )

    updated = _apply_channel_overrides(config, args)

    assert updated.rendering.engine == "shorts_factory"
