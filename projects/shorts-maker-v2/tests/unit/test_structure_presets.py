"""구조 프리셋 로테이션 및 시스템 프롬프트 반영 테스트."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from shorts_maker_v2.config import (
    AppConfig,
    AudioSettings,
    CanvaSettings,
    CaptionSettings,
    CostTable,
    LimitSettings,
    PathSettings,
    ProjectSettings,
    ProviderSettings,
    VideoSettings,
)
from shorts_maker_v2.pipeline.script_step import ScriptStep


def _make_config(presets: dict[str, list[str]] | None = None) -> AppConfig:
    return AppConfig(
        project=ProjectSettings(
            language="ko-KR",
            default_scene_count=7,
            script_review_enabled=False,
            structure_presets=presets,
        ),
        video=VideoSettings(
            target_duration_sec=(30, 40),
            resolution=(1080, 1920),
            fps=30,
            scene_video_duration_sec=5,
            aspect_ratio="9:16",
        ),
        providers=ProviderSettings(
            llm="openai",
            tts="edge-tts",
            visual_primary="google-veo",
            visual_fallback="openai-image",
            llm_model="gpt-4o-mini",
            tts_model="tts-1",
            tts_voice="alloy",
            tts_speed=1.1,
            image_model="dall-e-3",
            image_size="1024x1792",
            image_quality="standard",
            veo_model="veo-2.0-generate-001",
        ),
        limits=LimitSettings(max_cost_usd=2.0, max_retries=3, request_timeout_sec=180),
        costs=CostTable(llm_per_job=0.25, tts_per_second=0.0, veo_per_second=0.03, image_per_scene=0.04),
        paths=PathSettings(output_dir="output", logs_dir="logs", runs_dir="runs"),
        captions=CaptionSettings(
            font_size=64,
            margin_x=90,
            bottom_offset=240,
            text_color="#FFD700",
            stroke_color="#000000",
            stroke_width=4,
            line_spacing=12,
            font_candidates=("C:/Windows/Fonts/malgunbd.ttf",),
        ),
        audio=AudioSettings(),
        canva=CanvaSettings(enabled=False, design_id="", token_file=""),
    )


class TestStructurePresetRotation(unittest.TestCase):
    def setUp(self):
        # 카운터 리셋
        ScriptStep._structure_counter = 0

    def test_no_presets_returns_none(self):
        config = _make_config(presets=None)
        step = ScriptStep(config=config, llm_router=MagicMock())
        name, flow = step._next_structure_preset()
        self.assertIsNone(name)
        self.assertIsNone(flow)

    def test_preset_rotation(self):
        presets = {
            "listicle": ["hook", "body", "body", "body", "body", "body", "cta"],
            "countdown": ["hook", "rank5", "rank4", "rank3", "rank2", "rank1", "cta"],
        }
        config = _make_config(presets=presets)
        step = ScriptStep(config=config, llm_router=MagicMock())

        name1, flow1 = step._next_structure_preset()
        name2, flow2 = step._next_structure_preset()
        name3, flow3 = step._next_structure_preset()

        self.assertEqual(name1, "listicle")
        self.assertEqual(name2, "countdown")
        self.assertEqual(name3, "listicle")  # wraps around
        self.assertEqual(flow1[0], "hook")
        self.assertEqual(flow1[-1], "cta")

    def test_system_prompt_contains_flow(self):
        presets = {
            "quiz": ["hook", "question", "hint", "answer", "explain", "bonus", "cta"],
        }
        config = _make_config(presets=presets)
        step = ScriptStep(config=config, llm_router=MagicMock())

        prompt = step._build_system_prompt(
            scene_count=7,
            language="ko-KR",
            char_min=20,
            char_max=60,
            structure_flow=presets["quiz"],
        )
        self.assertIn("1:hook", prompt)
        self.assertIn("2:question", prompt)
        self.assertIn("7:cta", prompt)
        self.assertIn("Scene flow:", prompt)

    def test_system_prompt_default_without_flow(self):
        config = _make_config(presets=None)
        step = ScriptStep(config=config, llm_router=MagicMock())

        prompt = step._build_system_prompt(
            scene_count=7,
            language="ko-KR",
            char_min=20,
            char_max=60,
        )
        self.assertIn('structure_role: "hook"', prompt)
        self.assertIn('structure_role: "body"', prompt)
        self.assertIn('structure_role: "closing"', prompt)
        self.assertNotIn("Scene flow:", prompt)


if __name__ == "__main__":
    unittest.main()
