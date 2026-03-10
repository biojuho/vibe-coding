"""
tests/unit/test_persona_pipeline.py
=====================================
3-페르소나 파이프라인 단위 테스트.
LLMRouter를 Mock으로 교체해 실제 API 호출 없이 흐름을 검증합니다.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from shorts_maker_v2.pipeline.persona_pipeline import (
    generate_shorts_pipeline,
    run_haewon,
    run_jinsol,
    run_jiwoo,
)


# ──────────────────────────────────────────────────────────────────────────────
# 픽스처 — Mock LLM 응답
# ──────────────────────────────────────────────────────────────────────────────

MOCK_HAEWON_OUTPUT: dict = {
    "planner_comment": "AI 의료 기술의 혁신성을 공포→호기심→희망 감정 곡선으로 설계했습니다.",
    "title_ideas": [
        "암세포가 미쳐날뛰는 이유, 이중항체로 잡는다",
        "내성 생긴 항암제, AI가 해결책 찾았다",
    ],
    "script_structure": {
        "0_2s_Hook": "표적항암제 내성, 전 세계 암 환자 60%가 경험합니다",
        "2_15s_Context": "기존 항체는 암세포 하나만 잡는 '단안 저격수'. 이중항체는 두 곳을 동시 타격.",
        "15_35s_Core_Value": "T세포 리크루팅 메커니즘과 바이스페시픽 항체 임상 3상 데이터 시각화",
        "35_45s_CTA_Loop": "당신이라면 이중항체 vs 면역관문억제제 어느 쪽에 투자하겠습니까?",
    },
}

MOCK_JINSOL_OUTPUT: dict = {
    "writer_comment": "GLP-1 비유로 접근성 확보. 12초 주기 Retention Spike 4회. CTA 루프 훅과 연결.",
    "total_character_count": 258,
    "narration_script": [
        {
            "phase": "Hook",
            "timing_sec": "0-8",
            "text": "표적항암제 맞아도 암세포가 안 죽는다고요? 이거 60%한테 일어나는 얘깁니다.",
            "emphasis_words": ["60%", "안 죽는다"],
        },
        {
            "phase": "Body_1",
            "timing_sec": "8-22",
            "text": "기존 항체는 단안 저격수예요. 암세포 하나만 잡다가 다른 놈이 도망가버리죠. 근데 여기서 끝이 아니에요.",
            "emphasis_words": ["단안 저격수", "도망가버리죠"],
        },
        {
            "phase": "Body_2",
            "timing_sec": "22-38",
            "text": "이중항체는 양손에 무기 들고 두 군데를 동시에 잠급니다. T세포까지 끌어들여서 내성 자체를 못 만들게 막아요.",
            "emphasis_words": ["양손에 무기", "내성 자체"],
        },
        {
            "phase": "CTA_Loop",
            "timing_sec": "38-58",
            "text": "이중항체 vs 면역관문억제제, 당신은 어느 쪽 베팅하겠어요? 댓글로 알려주세요. 처음 질문 다시 떠오르죠?",
            "emphasis_words": ["베팅", "다시 떠오르죠"],
        },
    ],
}

MOCK_JIWOO_OUTPUT: dict = {
    "editing_strategy": "0-8초 나노 페이싱 0.7초 컷. A/V 펀치 18회 배치. 예측 리텐션 97% 달성. 마지막 4초 루프 설계.",
    "timeline_data": [
        {
            "clip_index": 1,
            "estimated_time_sec": "0.0-2.0",
            "narration_text": "표적항암제 맞아도 암세포가 안 죽는다고요?",
            "b_roll_prompt_en": (
                "Extreme macro shot of glowing cancer cells multiplying rapidly against black background, "
                "neon red particles bursting outward, dramatic volumetric lighting, 8K 60fps cinematic"
            ),
            "visual_effect": "Zoom Burst on 60% text + Color Pop Explosion (red)",
            "sound_effect": "Hyper whoosh + sub bass hit + digital glitch",
            "transition_type": "AI particle dissolve",
        },
        {
            "clip_index": 2,
            "estimated_time_sec": "2.0-8.0",
            "narration_text": "이거 60%한테 일어나는 얘깁니다.",
            "b_roll_prompt_en": (
                "Dynamic infographic animation of 60% statistic exploding onto screen, "
                "glowing data streams, corporate dark background, orbital camera spin, 8K 60fps"
            ),
            "visual_effect": "Screen Shake + Particle Impact on '60%'",
            "sound_effect": "Impact punch + rising synth tone",
            "transition_type": "Flash cut",
        },
    ],
}


def _make_mock_router(*responses: dict) -> MagicMock:
    """순서대로 responses를 반환하는 Mock LLMRouter 생성."""
    router = MagicMock()
    router.generate_json.side_effect = list(responses)
    return router


# ──────────────────────────────────────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────────────────────────────────────

class TestHaewonPhase:
    def test_output_schema(self):
        """해원 output이 필수 키를 모두 포함해야 한다."""
        router = _make_mock_router(MOCK_HAEWON_OUTPUT)
        result = run_haewon("이중항체 기술", router)

        assert "planner_comment" in result
        assert "title_ideas" in result
        assert "script_structure" in result
        assert isinstance(result["title_ideas"], list)
        assert len(result["title_ideas"]) >= 1

    def test_missing_key_raises(self):
        """필수 키 누락 시 ValueError를 발생시켜야 한다."""
        bad_output = {"planner_comment": "ok"}  # title_ideas, script_structure 누락
        router = _make_mock_router(bad_output)
        with pytest.raises(ValueError, match="해원"):
            run_haewon("이중항체", router)

    def test_script_structure_has_four_segments(self):
        """script_structure에 4개 구간이 있어야 한다."""
        router = _make_mock_router(MOCK_HAEWON_OUTPUT)
        result = run_haewon("이중항체", router)
        ss = result["script_structure"]
        for key in ("0_2s_Hook", "2_15s_Context", "15_35s_Core_Value", "35_45s_CTA_Loop"):
            assert key in ss, f"script_structure에 '{key}' 누락"


class TestJinsolPhase:
    def test_output_schema(self):
        """진솔 output이 필수 키를 모두 포함해야 한다."""
        router = _make_mock_router(MOCK_JINSOL_OUTPUT)
        result = run_jinsol(MOCK_HAEWON_OUTPUT, router)

        assert "writer_comment" in result
        assert "total_character_count" in result
        assert "narration_script" in result

    def test_narration_script_has_four_phases(self):
        """narration_script에 4개 phase가 있어야 한다."""
        router = _make_mock_router(MOCK_JINSOL_OUTPUT)
        result = run_jinsol(MOCK_HAEWON_OUTPUT, router)
        phases = [s["phase"] for s in result["narration_script"]]
        assert "Hook" in phases
        assert "CTA_Loop" in phases
        assert len(phases) == 4

    def test_character_count_in_range(self):
        """total_character_count가 245~275 범위여야 한다."""
        router = _make_mock_router(MOCK_JINSOL_OUTPUT)
        result = run_jinsol(MOCK_HAEWON_OUTPUT, router)
        count = result["total_character_count"]
        assert 245 <= count <= 275, f"글자 수 {count}가 245~275 범위를 벗어남"

    def test_missing_narration_script_raises(self):
        """narration_script 누락 시 ValueError를 발생시켜야 한다."""
        bad_output = {"writer_comment": "ok", "total_character_count": 260}
        router = _make_mock_router(bad_output)
        with pytest.raises(ValueError, match="진솔"):
            run_jinsol(MOCK_HAEWON_OUTPUT, router)

    def test_empty_narration_script_raises(self):
        """narration_script가 빈 리스트일 때 ValueError를 발생시켜야 한다."""
        bad_output = {
            "writer_comment": "ok",
            "total_character_count": 260,
            "narration_script": [],
        }
        router = _make_mock_router(bad_output)
        with pytest.raises(ValueError, match="비어 있습니다"):
            run_jinsol(MOCK_HAEWON_OUTPUT, router)


class TestJiwooPhase:
    def test_output_schema(self):
        """지우 output이 필수 키를 모두 포함해야 한다."""
        router = _make_mock_router(MOCK_JIWOO_OUTPUT)
        result = run_jiwoo(MOCK_JINSOL_OUTPUT, router)

        assert "editing_strategy" in result
        assert "timeline_data" in result
        assert isinstance(result["timeline_data"], list)

    def test_timeline_clips_have_required_fields(self):
        """각 클립에 필수 필드가 존재해야 한다."""
        router = _make_mock_router(MOCK_JIWOO_OUTPUT)
        result = run_jiwoo(MOCK_JINSOL_OUTPUT, router)
        required_fields = {
            "clip_index", "estimated_time_sec", "narration_text",
            "b_roll_prompt_en", "visual_effect", "sound_effect", "transition_type",
        }
        for clip in result["timeline_data"]:
            missing = required_fields - clip.keys()
            assert not missing, f"클립 {clip.get('clip_index')}에 필드 누락: {missing}"

    def test_b_roll_prompt_is_english(self):
        """b_roll_prompt_en은 영어여야 한다 (한글 포함 시 경고 수준 체크)."""
        router = _make_mock_router(MOCK_JIWOO_OUTPUT)
        result = run_jiwoo(MOCK_JINSOL_OUTPUT, router)
        for clip in result["timeline_data"]:
            prompt = clip["b_roll_prompt_en"]
            # 한글 유니코드 범위 포함 여부 체크
            has_korean = any("\uAC00" <= ch <= "\uD7A3" for ch in prompt)
            assert not has_korean, f"b_roll_prompt_en에 한글 포함: {prompt[:50]}"


MOCK_FFMPEG_OUTPUT: dict = {
    "ffmpeg_strategy": "1080x1920 @60fps libx264 CRF18. filter_complex 병렬 B-roll 합성. 나노 컷 18회.",
    "global_settings": {
        "resolution": "1080x1920",
        "fps": 60,
        "codec": "libx264",
        "audio_codec": "aac",
        "crf": 18,
    },
    "clips": [
        {
            "clip_index": 1,
            "input_type": "ai_generated",
            "b_roll_prompt_en": "Extreme macro glowing cancer cells, neon red, 8K 60fps",
            "duration_sec": 2.0,
            "filter_chain": "scale=1080:1920,setsar=1",
            "overlay_text": "표적항암제 맞아도 암세포가 안 죽는다고요?",
            "audio_track": "tts",
        }
    ],
    "audio_mix": {"tts_volume": 1.0, "bgm_volume": 0.12, "sfx_volume": 0.35},
    "output_filename": "output_shorts.mp4",
}


class TestShortsAutomationMaster:
    """ShortsAutomationMaster 클래스 단위 테스트."""

    def test_run_pipeline_calls_llm_three_times(self):
        """run_pipeline() 실행 시 LLM이 정확히 3회 호출돼야 한다."""
        router = _make_mock_router(
            MOCK_JINSOL_OUTPUT,
            MOCK_JIWOO_OUTPUT,
            MOCK_FFMPEG_OUTPUT,
        )
        from shorts_maker_v2.pipeline.persona_pipeline import ShortsAutomationMaster
        master = ShortsAutomationMaster("이중항체 기술", router)
        result = master.run_pipeline()

        assert router.generate_json.call_count == 3
        assert result is master.ffmpeg_config

    def test_state_is_stored_after_each_phase(self):
        """각 phase 완료 후 인스턴스 속성에 데이터가 저장돼야 한다."""
        router = _make_mock_router(
            MOCK_JINSOL_OUTPUT,
            MOCK_JIWOO_OUTPUT,
            MOCK_FFMPEG_OUTPUT,
        )
        from shorts_maker_v2.pipeline.persona_pipeline import ShortsAutomationMaster
        master = ShortsAutomationMaster("이중항체 기술", router)
        master.run_pipeline()

        assert master.script_data is not None
        assert master.editing_data is not None
        assert master.ffmpeg_config is not None

    def test_phase2_without_phase1_raises(self):
        """phase1 없이 phase2 호출 시 RuntimeError를 발생시켜야 한다."""
        router = _make_mock_router()
        from shorts_maker_v2.pipeline.persona_pipeline import ShortsAutomationMaster
        master = ShortsAutomationMaster("이중항체 기술", router)
        with pytest.raises(RuntimeError, match="phase1"):
            master.phase2_generate_editing()

    def test_phase3_without_phase2_raises(self):
        """phase2 없이 phase3 호출 시 RuntimeError를 발생시켜야 한다."""
        router = _make_mock_router()
        from shorts_maker_v2.pipeline.persona_pipeline import ShortsAutomationMaster
        master = ShortsAutomationMaster("이중항체 기술", router)
        with pytest.raises(RuntimeError, match="phase2"):
            master.phase3_generate_ffmpeg()

    def test_ffmpeg_output_schema(self):
        """ffmpeg_config에 필수 키가 모두 있어야 한다."""
        router = _make_mock_router(
            MOCK_JINSOL_OUTPUT,
            MOCK_JIWOO_OUTPUT,
            MOCK_FFMPEG_OUTPUT,
        )
        from shorts_maker_v2.pipeline.persona_pipeline import ShortsAutomationMaster
        master = ShortsAutomationMaster("이중항체 기술", router)
        master.run_pipeline()

        for key in ("ffmpeg_strategy", "global_settings", "clips", "output_filename"):
            assert key in master.ffmpeg_config

    def test_master_guideline_injected_in_prompt(self):
        """master_guideline이 진솔 호출 프롬프트에 포함돼야 한다."""
        router = _make_mock_router(
            MOCK_JINSOL_OUTPUT,
            MOCK_JIWOO_OUTPUT,
            MOCK_FFMPEG_OUTPUT,
        )
        from shorts_maker_v2.pipeline.persona_pipeline import ShortsAutomationMaster
        master = ShortsAutomationMaster("이중항체 기술", router, tone="도발적으로")
        master.run_pipeline()

        first_call_kwargs = router.generate_json.call_args_list[0].kwargs
        user_prompt = first_call_kwargs.get("user_prompt", "")
        assert "이중항체 기술" in user_prompt
        assert "도발적으로" in user_prompt


class TestFullPipeline:
    def test_e2e_mock(self):
        """3단계 전체 파이프라인이 올바른 순서로 실행되고 최종 dict를 반환해야 한다."""
        router = _make_mock_router(
            MOCK_HAEWON_OUTPUT,
            MOCK_JINSOL_OUTPUT,
            MOCK_JIWOO_OUTPUT,
        )
        result = generate_shorts_pipeline("이중항체 기술", router)

        # 최종 반환 구조 검증
        assert "haewon" in result
        assert "jinsol" in result
        assert "jiwoo" in result

        # LLM이 정확히 3번 호출됐는지 확인
        assert router.generate_json.call_count == 3

    def test_e2e_data_flow(self):
        """해원 output이 진솔 호출의 user_prompt에 포함되어야 한다."""
        router = _make_mock_router(
            MOCK_HAEWON_OUTPUT,
            MOCK_JINSOL_OUTPUT,
            MOCK_JIWOO_OUTPUT,
        )
        generate_shorts_pipeline("이중항체 기술", router)

        calls = router.generate_json.call_args_list
        # Phase 2 (진솔) 호출 시 user_prompt에 해원 output 내용이 포함돼야 함
        jinsol_call_kwargs = calls[1].kwargs
        user_prompt = jinsol_call_kwargs.get("user_prompt", "")
        assert "planner_comment" in user_prompt or "script_structure" in user_prompt

    def test_haewon_failure_propagates(self):
        """Phase 1 실패 시 전체 파이프라인이 ValueError를 발생시켜야 한다."""
        bad_router = _make_mock_router({"wrong_key": "no data"})
        with pytest.raises(ValueError, match="해원"):
            generate_shorts_pipeline("이중항체 기술", bad_router)
