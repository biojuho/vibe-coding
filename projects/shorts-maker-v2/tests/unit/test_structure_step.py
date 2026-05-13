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

    def test_fallback_marks_is_fallback_true(self, _config, _plan):
        step = StructureStep(config=_config, llm_router=MagicMock())
        outline_no_plan = step._fallback_outline("블랙홀", None)
        outline_with_plan = step._fallback_outline("블랙홀", _plan)
        # 두 경로 모두 결정론 폴백이므로 is_fallback=True 가 박혀야 한다 —
        # orchestrator 가 degraded_steps 로 표면화하는 신호가 사라지면 안 됨.
        assert outline_no_plan.is_fallback is True
        assert outline_with_plan.is_fallback is True

    def test_fallback_avoids_legacy_boilerplate_intent(self, _config):
        # 2026-05-11 production run 에서 ship 됐던 보일러플레이트:
        # "{topic}의 핵심 포인트 N을 설명한다". 이 패턴이 다시 새지 않게 막는다.
        step = StructureStep(config=_config, llm_router=MagicMock())
        outline = step._fallback_outline("블랙홀", None)
        for scene in outline.scenes:
            assert "핵심 포인트" not in scene.intent, (
                f"Scene {scene.scene_id} regressed to legacy boilerplate: {scene.intent!r}"
            )

    def test_fallback_emotional_beats_vary_for_gate2(self, _config):
        # Gate 2 의 _gate2_validate 는 최소 3개 unique emotional_beat 를 요구한다.
        # 폴백이 그 기준을 자체적으로 만족해야 사람이 다시 손볼 일이 줄어든다.
        step = StructureStep(config=_config, llm_router=MagicMock())
        outline = step._fallback_outline("블랙홀", None)
        beats = {s.emotional_beat for s in outline.scenes if s.emotional_beat}
        assert len(beats) >= 3, f"Fallback beats not varied enough: {beats}"

    def test_fallback_uses_production_plan_visual_keywords(self, _config, _plan):
        # production_plan.visual_keywords 가 들어있으면 그 키워드들이 씬별
        # visual_direction 에 직접 실려야 한다 — "Clean informational visual" 같은
        # generic placeholder 가 다시 새지 않게 막는다.
        step = StructureStep(config=_config, llm_router=MagicMock())
        outline = step._fallback_outline("블랙홀", _plan)
        kw_set = {kw.lower() for kw in _plan.visual_keywords}
        joined = " ".join(s.visual_direction.lower() for s in outline.scenes)
        # 최소 하나 이상의 키워드가 어딘가 씬 visual_direction 에 실려야 한다
        assert any(kw in joined for kw in kw_set), f"None of {kw_set} appeared in visual_directions: {joined}"
        # 그리고 옛 generic 텍스트가 모든 body 씬에 똑같이 박혀있으면 안 된다
        body_visuals = {s.visual_direction for s in outline.scenes if s.role == "body"}
        assert len(body_visuals) > 1, f"Body visual_directions collapsed to one generic line: {body_visuals}"

    def test_fallback_uses_core_message_in_closing(self, _config, _plan):
        # production_plan.core_message 가 있으면 마지막 body 또는 closing 의
        # intent 에 그 문구가 반영되어야 한다 — 폴백도 "이야기가 어디로
        # 향하는지" 보여주는 신호를 보존해야 한다.
        step = StructureStep(config=_config, llm_router=MagicMock())
        outline = step._fallback_outline("블랙홀", _plan)
        msg_frag = _plan.core_message[:30]
        last_two = outline.scenes[-2:]
        assert any(msg_frag in s.intent for s in last_two), (
            f"core_message fragment {msg_frag!r} not surfaced in closing arc: {[s.intent for s in last_two]}"
        )

    def test_fallback_closing_has_no_cta_word(self, _config, _plan):
        # 폴백이라도 user_shorts_philosophy(CTA 금지) 는 지켜야 한다.
        step = StructureStep(config=_config, llm_router=MagicMock())
        outline = step._fallback_outline("블랙홀", _plan)
        closing_text = (outline.scenes[-1].intent + " " + outline.scenes[-1].emotional_beat).lower()
        for forbidden in ("구독", "좋아요", "알림", "subscribe", "like", "click"):
            assert forbidden not in closing_text, f"Fallback closing leaked CTA word {forbidden!r}: {closing_text!r}"


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
