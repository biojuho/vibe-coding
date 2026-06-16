"""Tests for script_prompts.py helper functions."""

from __future__ import annotations

from shorts_maker_v2.pipeline.script_prompts import (
    ScriptPromptsMixin,
    _deep_merge_dicts,
    _merge_channel_persona,
    _merge_channel_review_criteria,
    _merge_persona_keywords,
    _merge_prompt_field_names,
    _normalize_string_tuple,
    _normalize_tone_presets,
)


class TestNormalizeTonePresets:
    def test_empty_list_returns_empty(self) -> None:
        assert _normalize_tone_presets([]) == []

    def test_non_list_returns_empty(self) -> None:
        assert _normalize_tone_presets(None) == []  # type: ignore[arg-type]
        assert _normalize_tone_presets({}) == []  # type: ignore[arg-type]
        assert _normalize_tone_presets("string") == []  # type: ignore[arg-type]

    def test_valid_items_extracted(self) -> None:
        raw = [{"name": "professor", "guide": "차분한 톤"}, {"name": "friend", "guide": "편한 반말"}]
        result = _normalize_tone_presets(raw)
        assert result == [("professor", "차분한 톤"), ("friend", "편한 반말")]

    def test_items_missing_name_or_guide_skipped(self) -> None:
        raw = [
            {"name": "ok", "guide": "guide text"},
            {"name": "", "guide": "no name"},
            {"guide": "no name key"},
            {"name": "no guide"},
            {"name": "empty guide", "guide": "   "},
        ]
        result = _normalize_tone_presets(raw)
        assert result == [("ok", "guide text")]

    def test_non_dict_items_skipped(self) -> None:
        raw = [{"name": "valid", "guide": "guide"}, "string", 42, None]
        result = _normalize_tone_presets(raw)
        assert result == [("valid", "guide")]


class TestNormalizeStringTuple:
    def test_list_of_strings(self) -> None:
        assert _normalize_string_tuple(["a", "b", "c"]) == ("a", "b", "c")

    def test_strips_whitespace(self) -> None:
        assert _normalize_string_tuple(["  hello  ", " world "]) == ("hello", "world")

    def test_empty_strings_filtered(self) -> None:
        assert _normalize_string_tuple(["a", "", "   ", "b"]) == ("a", "b")

    def test_non_list_returns_empty(self) -> None:
        assert _normalize_string_tuple(None) == ()  # type: ignore[arg-type]
        assert _normalize_string_tuple({}) == ()  # type: ignore[arg-type]
        assert _normalize_string_tuple("string") == ()  # type: ignore[arg-type]

    def test_tuple_input_accepted(self) -> None:
        assert _normalize_string_tuple(("x", "y")) == ("x", "y")


class TestDeepMergeDicts:
    def test_override_flat_key(self) -> None:
        result = _deep_merge_dicts({"a": 1, "b": 2}, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_deep_merge_nested(self) -> None:
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 99, "c": 3}}
        result = _deep_merge_dicts(base, override)
        assert result == {"x": {"a": 1, "b": 99, "c": 3}}

    def test_does_not_mutate_base(self) -> None:
        base = {"a": {"nested": 1}}
        _deep_merge_dicts(base, {"a": {"nested": 2}})
        assert base["a"]["nested"] == 1

    def test_new_key_added(self) -> None:
        result = _deep_merge_dicts({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}


class TestMergeChannelPersona:
    def test_non_dict_raw_returns_base(self) -> None:
        base = {"ai_tech": {"tone": "fast"}}
        result = _merge_channel_persona(base, None)
        assert result == base

    def test_adds_new_channel(self) -> None:
        base: dict = {}
        result = _merge_channel_persona(base, {"ai_tech": {"tone": "fast"}})
        assert result["ai_tech"] == {"tone": "fast"}

    def test_updates_existing_channel(self) -> None:
        base = {"ai_tech": {"tone": "old", "role": "journalist"}}
        result = _merge_channel_persona(base, {"ai_tech": {"tone": "new"}})
        assert result["ai_tech"]["tone"] == "new"
        assert result["ai_tech"]["role"] == "journalist"

    def test_non_dict_channel_value_skipped(self) -> None:
        base = {"ai_tech": {"tone": "fast"}}
        result = _merge_channel_persona(base, {"ai_tech": "not a dict"})
        assert result["ai_tech"] == {"tone": "fast"}


class TestMergePersonaKeywords:
    def test_non_dict_raw_returns_base(self) -> None:
        base = {"ai_tech": ("GPT", "AI")}
        result = _merge_persona_keywords(base, None)
        assert result == base

    def test_adds_new_key(self) -> None:
        base: dict = {}
        result = _merge_persona_keywords(base, {"ai_tech": ["GPT", "AI"]})
        assert result["ai_tech"] == ("GPT", "AI")

    def test_empty_list_does_not_replace(self) -> None:
        base = {"ai_tech": ("GPT", "AI")}
        result = _merge_persona_keywords(base, {"ai_tech": []})
        assert result["ai_tech"] == ("GPT", "AI")


class TestMergePromptFieldNames:
    def test_updates_known_key(self) -> None:
        base = {"title": "제목", "topic": "주제"}
        result = _merge_prompt_field_names(base, {"title": "Title"})
        assert result["title"] == "Title"
        assert result["topic"] == "주제"

    def test_unknown_key_not_added(self) -> None:
        base = {"title": "제목"}
        result = _merge_prompt_field_names(base, {"new_key": "value"})
        assert "new_key" not in result

    def test_non_dict_raw_returns_base(self) -> None:
        base = {"title": "제목"}
        result = _merge_prompt_field_names(base, None)
        assert result == base


class TestMergeChannelReviewCriteria:
    def test_adds_extra_dimensions_string(self) -> None:
        base: dict = {}
        result = _merge_channel_review_criteria(base, {"ai_tech": {"extra_dimensions": "최신 AI 트렌드 반영 여부"}})
        assert result["ai_tech"]["extra_dimensions"] == "최신 AI 트렌드 반영 여부"

    def test_empty_string_extra_dimensions_skipped(self) -> None:
        base: dict = {}
        result = _merge_channel_review_criteria(base, {"ai_tech": {"extra_dimensions": "  "}})
        assert "ai_tech" not in result

    def test_min_score_override_coerced_to_int(self) -> None:
        base: dict = {}
        result = _merge_channel_review_criteria(base, {"ai_tech": {"min_score_override": 7.9}})
        assert result["ai_tech"]["min_score_override"] == 7

    def test_extra_keys_tuple_set(self) -> None:
        base: dict = {}
        result = _merge_channel_review_criteria(base, {"ai_tech": {"extra_keys": ["accuracy", "timeliness"]}})
        assert result["ai_tech"]["extra_keys"] == ("accuracy", "timeliness")

    def test_non_dict_value_skipped(self) -> None:
        base: dict = {"existing": {"extra_dimensions": "text"}}
        result = _merge_channel_review_criteria(base, {"existing": "not a dict"})
        assert result["existing"]["extra_dimensions"] == "text"


class TestScriptPromptsMixinCounters:
    def test_reset_counters_sets_to_zero(self) -> None:
        ScriptPromptsMixin._tone_counter = 5
        ScriptPromptsMixin._structure_counter = 3
        ScriptPromptsMixin._reset_counters()
        assert ScriptPromptsMixin._tone_counter == 0
        assert ScriptPromptsMixin._structure_counter == 0

    def test_hook_patterns_have_name_and_description(self) -> None:
        for name, desc in ScriptPromptsMixin.HOOK_PATTERNS:
            assert isinstance(name, str) and name
            assert isinstance(desc, str) and desc

    def test_tone_presets_have_name_and_guide(self) -> None:
        for name, guide in ScriptPromptsMixin.TONE_PRESETS:
            assert isinstance(name, str) and name
            assert isinstance(guide, str) and guide


# ── estimate_narration_duration_sec NaN/Inf tts_speed 회귀 (SP-NI) ───────────


import math as _math


class TestNarrationDurationTtsSpeedNanInf:
    """estimate_narration_duration_sec 가 NaN/Inf tts_speed 에 폴백해야 함."""

    def test_nan_speed_returns_finite(self):
        """SP-NI001: tts_speed=NaN → 예외 없이 유한한 값 반환."""
        result = ScriptPromptsMixin.estimate_narration_duration_sec(
            "AI 도입했더니 야근이 늘었다.", tts_speed=float("nan")
        )
        assert _math.isfinite(result)
        assert result > 0

    def test_inf_speed_returns_finite(self):
        """SP-NI002: tts_speed=inf → 유한한 값 반환 (0으로 나누기 방지)."""
        result = ScriptPromptsMixin.estimate_narration_duration_sec("테스트 문장입니다.", tts_speed=float("inf"))
        assert _math.isfinite(result)

    def test_string_tts_speed_returns_finite(self):
        """SP-NI003: tts_speed='fast' → 기본 속도 1.0으로 폴백."""
        result = ScriptPromptsMixin.estimate_narration_duration_sec("테스트 문장입니다.", tts_speed="fast")
        assert _math.isfinite(result)
        assert result > 0

    def test_normal_speed_unaffected(self):
        """정상 속도 1.0은 그대로 동작한다."""
        result1 = ScriptPromptsMixin.estimate_narration_duration_sec("안녕하세요", tts_speed=1.0)
        result2 = ScriptPromptsMixin.estimate_narration_duration_sec("안녕하세요", tts_speed=2.0)
        assert result1 > result2  # 빠른 속도는 짧은 추정 시간
