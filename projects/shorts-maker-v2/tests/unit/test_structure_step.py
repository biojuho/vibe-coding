"""StructureStep (Gate 2) 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shorts_maker_v2.models import (
    GateVerdict,
    ProductionPlan,
    SceneOutline,
    StructureOutline,
)
from shorts_maker_v2.pipeline.structure_step import StructureStep


@pytest.fixture()
def _config():
    cfg = MagicMock()
    cfg.video.target_duration_sec = (35, 45)
    cfg.project.default_scene_count = 7
    cfg.project.structure_validation = "strict"
    cfg.providers.llm_providers = ("google",)
    cfg.providers.llm_models = {"google": "gemini-2.0-flash"}
    cfg.limits.max_retries = 2
    cfg.limits.request_timeout_sec = 30
    return cfg


@pytest.fixture()
def _plan():
    return ProductionPlan(
        concept="블랙홀이 시간을 왜곡하는 원리",
        target_persona="28세 과학 유튜브 시청자, 우주에 빠진",
        core_message="블랙홀 근처에서는 시간이 느려진다",
        visual_keywords=["black hole", "time dilation", "cosmic"],
        forbidden_elements=["지루한 수치 나열"],
        tone="경이롭고 차분한",
        audience_profile={
            "desire": "블랙홀의 신비로운 시간 왜곡 원리를 쉽게 이해하고 싶다",
            "emotional_state": "호기심과 경이감",
            "knowledge_level": "beginner",
            "consumption_context": "잠들기 전 침대에서",
        },
    )


def _make_valid_llm_response(scene_count: int = 7) -> dict:
    scenes = [
        {
            "role": "hook",
            "intent": "블랙홀의 시간 왜곡이라는 신비로운 원리로 주의 끌기",
            "visual_direction": "Dark cosmic background with massive black hole",
            "emotional_beat": "shock and wonder",
            "target_sec": 5.0,
        },
    ]
    for i in range(2, scene_count):
        scenes.append(
            {
                "role": "body",
                "intent": f"블랙홀 시간 왜곡의 원리를 쉽게 이해할 수 있도록 설명 {i - 1}",
                "visual_direction": "Space visualization with distorted grid",
                "emotional_beat": "understanding" if i % 2 == 0 else "awe",
                "target_sec": 5.0,
            }
        )
    scenes.append(
        {
            "role": "closing",
            "intent": "우리 모두 시간의 강 위에 떠 있다는 여운 남기기",
            "visual_direction": "Wide peaceful starfield, gentle fade",
            "emotional_beat": "quiet contemplation",
            "target_sec": 5.0,
        }
    )
    return {"narrative_arc": "quiet_storytelling", "scenes": scenes}


class TestStructureStepParsing:
    """구성안 파싱 테스트."""

    def test_parse_valid_outline(self, _config):
        step = StructureStep(config=_config, llm_router=MagicMock())
        data = _make_valid_llm_response(7)
        outline = step._parse_outline(data)
        assert len(outline.scenes) == 7
        assert outline.scenes[0].role == "hook"
        assert outline.scenes[-1].role == "closing"
        assert outline.narrative_arc == "quiet_storytelling"

    def test_cta_auto_converted_to_closing(self, _config):
        step = StructureStep(config=_config, llm_router=MagicMock())
        data = {
            "narrative_arc": "test",
            "scenes": [
                {
                    "role": "hook",
                    "intent": "test",
                    "visual_direction": "test",
                    "emotional_beat": "test",
                    "target_sec": 5,
                },
                {
                    "role": "cta",
                    "intent": "subscribe!",
                    "visual_direction": "test",
                    "emotional_beat": "test",
                    "target_sec": 5,
                },
            ],
        }
        outline = step._parse_outline(data)
        assert outline.scenes[-1].role == "closing"

    def test_empty_scenes_raises(self, _config):
        step = StructureStep(config=_config, llm_router=MagicMock())
        with pytest.raises(ValueError, match="No scenes"):
            step._parse_outline({"scenes": []})


class TestGate2Validation:
    """Gate 2 검증 테스트."""

    def test_valid_outline_passes(self, _config, _plan):
        step = StructureStep(config=_config, llm_router=MagicMock())
        data = _make_valid_llm_response(7)
        outline = step._parse_outline(data)
        verdict, issues = step._gate2_validate(outline, _plan)
        assert verdict == GateVerdict.PASS
        assert not issues

    def test_no_hook_fails(self, _config, _plan):
        step = StructureStep(config=_config, llm_router=MagicMock())
        data = _make_valid_llm_response(7)
        data["scenes"][0]["role"] = "body"
        outline = step._parse_outline(data)
        verdict, issues = step._gate2_validate(outline, _plan)
        assert verdict == GateVerdict.FAIL_RETRY
        assert any("hook" in i for i in issues)

    def test_no_closing_fails(self, _config, _plan):
        step = StructureStep(config=_config, llm_router=MagicMock())
        data = _make_valid_llm_response(7)
        data["scenes"][-1]["role"] = "body"
        outline = step._parse_outline(data)
        verdict, issues = step._gate2_validate(outline, _plan)
        assert verdict == GateVerdict.FAIL_RETRY
        assert any("closing" in i for i in issues)

    def test_cta_in_closing_fails(self, _config, _plan):
        step = StructureStep(config=_config, llm_router=MagicMock())
        data = _make_valid_llm_response(7)
        data["scenes"][-1]["intent"] = "구독과 좋아요 부탁드립니다"
        outline = step._parse_outline(data)
        verdict, issues = step._gate2_validate(outline, _plan)
        assert verdict == GateVerdict.FAIL_RETRY
        assert any("forbidden" in i.lower() or "CTA" in i for i in issues)

    def test_too_few_scenes_fails(self, _config, _plan):
        step = StructureStep(config=_config, llm_router=MagicMock())
        data = _make_valid_llm_response(3)  # only 3 scenes
        outline = step._parse_outline(data)
        verdict, issues = step._gate2_validate(outline, _plan)
        assert verdict == GateVerdict.FAIL_RETRY
        assert any("few" in i.lower() for i in issues)


class TestFallbackOutline:
    """폴백 구성안 테스트."""

    def test_fallback_has_hook_and_closing(self, _config):
        step = StructureStep(config=_config, llm_router=MagicMock())
        outline = step._fallback_outline("블랙홀", None)
        assert outline.scenes[0].role == "hook"
        assert outline.scenes[-1].role == "closing"
        assert len(outline.scenes) == 7  # default_scene_count


class TestStructureOutlinePromptBlock:
    """StructureOutline.to_prompt_block() 테스트."""

    def test_prompt_block_contains_all_scenes(self):
        scenes = [
            SceneOutline(1, "hook", "Grab attention", "Dark bg", "curiosity", 5.0),
            SceneOutline(2, "body", "Explain main point", "Infographic", "understanding", 5.0),
            SceneOutline(3, "closing", "Leave lingering thought", "Peaceful landscape", "contemplation", 5.0),
        ]
        outline = StructureOutline(scenes=scenes, total_estimated_sec=15.0)
        block = outline.to_prompt_block()
        assert "Scene 1 [hook]" in block
        assert "Scene 2 [body]" in block
        assert "Scene 3 [closing]" in block
        assert "lingering thought" in block
