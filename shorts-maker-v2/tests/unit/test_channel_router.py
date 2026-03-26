from __future__ import annotations

from pathlib import Path

import yaml

from shorts_maker_v2.config import load_config
from shorts_maker_v2.utils import channel_router as channel_router_module
from shorts_maker_v2.utils.channel_router import ChannelRouter, get_router


def _write_profiles(path: Path) -> Path:
    payload = {
        "channels": {
            "ai_tech": {
                "display_name": "Future Synapse",
                "category": "AI",
                "youtube_url": "https://example.com/ai",
                "persona_channel_context": "tech context",
                "notion_channel_name": "AI Board",
                "tts_voice": "voice-ai",
                "tts_speed": 1.2,
                "tts_voice_roles": {"hook": "hook-voice"},
                "visual_styles": ["style-a", "style-b"],
                "target_duration_sec": [30, 40],
                "default_structure": ["hook", "body", "cta"],
            }
        }
    }
    profile_path = path / "profiles.yaml"
    profile_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return profile_path


def _write_config(path: Path) -> Path:
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
            "llm_model": "gpt-4o-mini",
            "tts_model": "tts-1",
            "tts_voice": "base-voice",
            "tts_speed": 1.0,
            "image_model": "dall-e-3",
            "image_size": "1024x1792",
            "image_quality": "standard",
            "veo_model": "veo-2.0-generate-001",
            "tts_voice_roles": {"body": "body-voice"},
            "visual_styles": ["base-style"],
        },
        "limits": {"max_cost_usd": 2.0, "max_retries": 2, "request_timeout_sec": 10},
        "costs": {"llm_per_job": 0.01, "tts_per_second": 0.001, "veo_per_second": 0.03, "image_per_scene": 0.04},
        "paths": {"output_dir": "output", "logs_dir": "logs", "runs_dir": "runs"},
        "captions": {
            "font_size": 64,
            "margin_x": 90,
            "bottom_offset": 240,
            "text_color": "#FFFFFF",
            "stroke_color": "#000000",
            "stroke_width": 4,
            "line_spacing": 12,
            "font_candidates": ["C:/Windows/Fonts/malgun.ttf"],
        },
        "audio": {},
        "canva": {"enabled": False, "design_id": "", "token_file": ""},
        "intro_outro": {},
        "thumbnail": {},
    }
    config_path = path / "config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def test_channel_router_lists_channels_and_getters(tmp_path: Path) -> None:
    router = ChannelRouter(_write_profiles(tmp_path))

    assert router.list_channels() == [
        {
            "key": "ai_tech",
            "display_name": "Future Synapse",
            "category": "AI",
            "youtube_url": "https://example.com/ai",
        }
    ]
    assert router.get_channel_context("ai_tech") == "tech context"
    assert router.get_notion_channel_name("ai_tech") == "AI Board"


def test_channel_router_handles_missing_and_unknown_profiles(tmp_path: Path) -> None:
    missing_router = ChannelRouter(tmp_path / "missing.yaml")
    assert missing_router.list_channels() == []

    router = ChannelRouter(_write_profiles(tmp_path))
    try:
        router.get_profile("unknown")
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing channel")


def test_channel_router_apply_merges_profile_overrides(tmp_path: Path) -> None:
    router = ChannelRouter(_write_profiles(tmp_path))
    config = load_config(_write_config(tmp_path))

    updated = router.apply(config, "ai_tech")

    assert updated.providers.tts_voice == "voice-ai"
    assert updated.providers.tts_speed == 1.2
    assert updated.providers.tts_voice_roles == {"body": "body-voice", "hook": "hook-voice"}
    assert updated.providers.visual_styles == ("style-a", "style-b")
    assert updated.video.target_duration_sec == (30, 40)
    assert updated._channel_default_structure == ["hook", "body", "cta"]
    assert config.providers.tts_voice == "base-voice"


def test_channel_router_apply_returns_original_for_empty_or_unknown_channel(tmp_path: Path) -> None:
    router = ChannelRouter(_write_profiles(tmp_path))
    config = load_config(_write_config(tmp_path))

    assert router.apply(config, "") is config
    assert router.apply(config, "missing") is config


def test_get_router_returns_singleton(tmp_path: Path, monkeypatch) -> None:
    profile_path = _write_profiles(tmp_path)
    monkeypatch.setattr(channel_router_module, "_router_singleton", None)

    first = get_router(profile_path)
    second = get_router(profile_path)

    assert first is second
