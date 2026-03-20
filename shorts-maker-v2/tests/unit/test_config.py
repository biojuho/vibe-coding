from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from shorts_maker_v2.config import ConfigError, load_config


def _write_config(path: Path, payload: dict) -> Path:
    config_path = path / "config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def test_load_config_success(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        {
            "project": {"language": "ko-KR", "default_scene_count": 7},
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
            "limits": {"max_cost_usd": 2.0, "max_retries": 3, "request_timeout_sec": 180},
            "costs": {"llm_per_job": 0.25, "tts_per_second": 0.0008, "veo_per_second": 0.03, "image_per_scene": 0.04},
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
        },
    )
    config = load_config(config_path)
    assert config.project.default_scene_count == 7
    assert config.video.target_duration_sec == (35, 45)
    assert config.providers.visual_primary == "google-veo"
    assert config.rendering.engine == "native"


def test_load_config_invalid_duration_range(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        {
            "project": {"language": "ko-KR", "default_scene_count": 7},
            "video": {
                "target_duration_sec": [45, 35],
                "resolution": [1080, 1920],
                "fps": 30,
                "scene_video_duration_sec": 5,
                "aspect_ratio": "9:16",
            },
            "providers": {},
            "limits": {},
            "costs": {},
            "paths": {},
            "captions": {"font_candidates": ["C:/Windows/Fonts/malgun.ttf"]},
        },
    )
    with pytest.raises(ConfigError):
        load_config(config_path)


# ─── Phase 2-B: range validation tests ────────────────────────────────────


def _base_config(**overrides: dict) -> dict:
    """Minimal valid config with overrides applied."""
    cfg: dict = {
        "project": {"language": "ko-KR", "default_scene_count": 7},
        "video": {
            "target_duration_sec": [35, 45],
            "resolution": [1080, 1920],
            "fps": 30,
            "scene_video_duration_sec": 5,
        },
        "providers": {},
        "limits": {},
        "costs": {},
        "paths": {},
        "captions": {"font_candidates": ["C:/Windows/Fonts/malgun.ttf"]},
    }
    for key, val in overrides.items():
        section, field = key.split(".", 1)
        cfg[section][field] = val
    return cfg


def test_config_rejects_crf_out_of_range(tmp_path: Path) -> None:
    path = _write_config(tmp_path, _base_config(**{"video.encoding_crf": 99}))
    with pytest.raises(ConfigError, match="encoding_crf"):
        load_config(path)


def test_config_rejects_bg_opacity_out_of_range(tmp_path: Path) -> None:
    path = _write_config(tmp_path, _base_config(**{"captions.bg_opacity": 300}))
    with pytest.raises(ConfigError, match="bg_opacity"):
        load_config(path)


def test_config_rejects_stock_mix_ratio_out_of_range(tmp_path: Path) -> None:
    path = _write_config(tmp_path, _base_config(**{"video.stock_mix_ratio": 1.5}))
    with pytest.raises(ConfigError, match="stock_mix_ratio"):
        load_config(path)


def test_config_rejects_negative_tts_speed(tmp_path: Path) -> None:
    path = _write_config(tmp_path, _base_config(**{"providers.tts_speed": -1.0}))
    with pytest.raises(ConfigError, match="tts_speed"):
        load_config(path)


def test_config_loads_rendering_engine_override(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        {
            **_base_config(),
            "rendering": {"engine": "auto"},
        },
    )
    config = load_config(path)
    assert config.rendering.engine == "auto"


def test_config_rejects_invalid_rendering_engine(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        {
            **_base_config(),
            "rendering": {"engine": "broken"},
        },
    )
    with pytest.raises(ConfigError, match="rendering.engine"):
        load_config(path)
