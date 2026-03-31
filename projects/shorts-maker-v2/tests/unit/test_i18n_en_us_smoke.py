from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from shorts_maker_v2.config import load_config
from shorts_maker_v2.pipeline.media_step import MediaStep
from shorts_maker_v2.pipeline.script_step import ScriptStep
from shorts_maker_v2.render.caption_pillow import CaptionStyle, render_caption_image


def _write_config(path: Path) -> Path:
    config_path = path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "project": {"language": "en-US", "default_scene_count": 2},
                "video": {
                    "target_duration_sec": [8, 14],
                    "resolution": [1080, 1920],
                    "fps": 30,
                    "scene_video_duration_sec": 5,
                    "aspect_ratio": "9:16",
                },
                "providers": {
                    "llm": "openai",
                    "tts": "edge-tts",
                    "visual_primary": "openai-image",
                    "visual_fallback": "openai-image",
                },
                "limits": {"max_cost_usd": 2.0, "max_retries": 1, "request_timeout_sec": 30},
                "costs": {
                    "llm_per_job": 0.25,
                    "tts_per_second": 0.0008,
                    "veo_per_second": 0.03,
                    "image_per_scene": 0.04,
                },
                "paths": {"output_dir": "output", "logs_dir": "logs", "runs_dir": "runs"},
                "captions": {},
                "canva": {"enabled": False, "design_id": "", "token_file": ""},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return config_path


def test_en_us_locale_smoke_covers_script_audio_and_caption_paths(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path))

    script_step = ScriptStep(config=config, llm_router=MagicMock(), channel_key="ai_tech")
    _, tone_guide = script_step._next_tone_preset()
    system_prompt = script_step._build_system_prompt(
        scene_count=2,
        language=config.project.language,
        char_min=20,
        char_max=40,
        hook_instruction="Lead with a surprising fact.",
        tone_guide=tone_guide,
        channel_key="ai_tech",
    )

    assert "English Writing Rules" in system_prompt
    assert "narration:" in system_prompt
    assert "visual_prompt:" in system_prompt
    assert "narration_ko" not in system_prompt
    assert config.captions.font_candidates[0] == "C:/Windows/Fonts/arialbd.ttf"

    media_step = MediaStep(config=config, openai_client=MagicMock())
    audio_path = tmp_path / "audio.mp3"

    def _fake_generate_tts(**kwargs):
        kwargs["output_path"].write_bytes(b"audio")
        kwargs["words_json_path"].write_text("[]", encoding="utf-8")
        return kwargs["output_path"]

    with patch(
        "shorts_maker_v2.pipeline.media_step.EdgeTTSClient.generate_tts", side_effect=_fake_generate_tts
    ) as generate:
        result = media_step._generate_audio("Hello from the new locale", audio_path, role="hook")

    assert result == audio_path
    assert generate.call_args.kwargs["language"] == "en-US"

    caption_style = CaptionStyle(
        font_size=config.captions.font_size,
        margin_x=config.captions.margin_x,
        bottom_offset=config.captions.bottom_offset,
        text_color=config.captions.text_color,
        stroke_color=config.captions.stroke_color,
        stroke_width=config.captions.stroke_width,
        line_spacing=config.captions.line_spacing,
        font_candidates=config.captions.font_candidates,
    )
    caption_path = tmp_path / "caption.png"

    render_caption_image("Hello world", 1080, caption_style, caption_path)

    assert caption_path.exists()
