from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.pipeline.script_step import (
    ScriptStep,
    _load_script_step_locale_bundle,
)


class FakeLLMRouter:
    def __init__(self, responses: list[dict]):
        self._responses = list(responses)

    def generate_json(self, *, system_prompt="", user_prompt="", temperature=0.7, thinking_level=None):
        del system_prompt, user_prompt, temperature, thinking_level
        if not self._responses:
            raise AssertionError("No more fake responses")
        return self._responses.pop(0)


def make_config():
    return SimpleNamespace(
        providers=SimpleNamespace(
            llm="openai",
            llm_model="gpt-4o-mini",
            tts_speed=1.05,
            thinking_level="low",
            thinking_level_review="high",
            embedding_model="gemini-embedding-2-preview",
        ),
        project=SimpleNamespace(
            default_scene_count=2,
            language="ko-KR",
            script_review_enabled=False,
            script_review_min_score=6,
            structure_presets={},
        ),
        video=SimpleNamespace(
            target_duration_sec=(8, 14),
        ),
    )


def test_load_script_step_locale_bundle_reads_ko_kr_yaml() -> None:
    bundle = _load_script_step_locale_bundle("ko-KR")

    assert bundle["tone_presets"]
    assert "ai_tech" in bundle["channel_persona"]
    assert "prompt_copy" in bundle


def test_load_script_step_locale_bundle_reads_en_us_yaml() -> None:
    bundle = _load_script_step_locale_bundle("en-US")

    assert bundle["tone_presets"]
    assert "ai_tech" in bundle["channel_persona"]
    assert bundle["review_copy"]["base_review_system"]
    assert bundle["field_names"]["narration"] == "narration"
    assert "ai_tech" in bundle["channel_review_criteria"]


def test_load_script_step_locale_bundle_returns_empty_for_missing_language() -> None:
    assert _load_script_step_locale_bundle("zz-ZZ") == {}


def test_script_step_applies_locale_prompt_and_persona_overrides() -> None:
    custom_bundle = {
        "tone_presets": [{"name": "custom", "guide": "Custom guide"}],
        "channel_persona": {
            "ai_tech": {
                "role_description": "Custom persona role.",
                "tone": "Custom persona tone.",
                "forbidden": "Custom persona forbidden.",
                "required": "Custom persona required.",
            }
        },
        "prompt_copy": {
            "system_intro": "Locale intro.\n",
            "user_instructions": "Locale user instructions.\n",
        },
    }

    with patch("shorts_maker_v2.pipeline.script_step._load_script_step_locale_bundle", return_value=custom_bundle):
        step = ScriptStep(config=make_config(), llm_router=FakeLLMRouter([]), channel_key="ai_tech")
        tone_name, tone_guide = step._next_tone_preset()
        system_prompt = step._build_system_prompt(
            scene_count=2,
            language="ko-KR",
            char_min=20,
            char_max=40,
            hook_instruction="Hook here",
            tone_guide=tone_guide,
            channel_key="ai_tech",
        )
        user_prompt = step._build_user_prompt(
            topic="테스트 주제",
            duration_range=(8, 14),
            attempt=1,
            previous_total_sec=None,
            previous_scene_count=2,
        )

    assert tone_name == "custom"
    assert tone_guide == "Custom guide"
    assert "Locale intro." in system_prompt
    assert "Custom persona role." in system_prompt
    assert "Locale user instructions." in user_prompt


def test_script_step_applies_locale_persona_keywords_and_review_copy() -> None:
    custom_bundle = {
        "persona_keywords": {
            "ai_tech": ["tensor", "inference"],
        },
        "review_copy": {
            "base_review_system": "Locale review base.\n",
            "feedback_rule": "Locale feedback rule.\n",
            "output_rule": "Locale output {json_example}",
        },
    }

    with patch("shorts_maker_v2.pipeline.script_step._load_script_step_locale_bundle", return_value=custom_bundle):
        step = ScriptStep(config=make_config(), llm_router=FakeLLMRouter([]), channel_key="ai_tech")
        review_system, _, _ = step._build_review_system()
        score = ScriptStep._score_persona_match(
            [
                ScenePlan(
                    scene_id=1,
                    narration_ko="tensor inference 이야기입니다",
                    visual_prompt_en="clean tech illustration",
                    target_sec=3.0,
                    structure_role="body",
                )
            ],
            "ai_tech",
            step._persona_keywords,
        )

    assert "Locale review base." in review_system
    assert "Locale feedback rule." in review_system
    assert "Locale output" in review_system
    assert score == 1.0


def test_script_step_applies_locale_review_criteria_and_field_names() -> None:
    custom_bundle = {
        "field_names": {
            "narration": "narration",
            "visual_prompt": "visual_prompt",
        },
        "channel_review_criteria": {
            "ai_tech": {
                "extra_dimensions": "  freshness_score : Does the script feel current? (1=stale, 10=fresh)\n",
                "extra_keys": ["freshness_score"],
                "min_score_override": 9,
                "context_note": "Locale-specific AI review context.",
            }
        },
    }

    with patch("shorts_maker_v2.pipeline.script_step._load_script_step_locale_bundle", return_value=custom_bundle):
        step = ScriptStep(config=make_config(), llm_router=FakeLLMRouter([]), channel_key="ai_tech")
        _, tone_guide = step._next_tone_preset()
        system_prompt = step._build_system_prompt(
            scene_count=2,
            language="en-US",
            char_min=20,
            char_max=40,
            hook_instruction="Hook here",
            tone_guide=tone_guide,
            channel_key="ai_tech",
        )
        review_system, review_keys, min_score = step._build_review_system()

    assert "narration:" in system_prompt
    assert "visual_prompt:" in system_prompt
    assert "narration_ko" not in system_prompt
    assert "freshness_score" in review_system
    assert "Locale-specific AI review context." in review_system
    assert review_keys[-1] == "freshness_score"
    assert min_score == 9


def test_run_passes_locale_specific_cta_words_to_validator() -> None:
    custom_bundle = {
        "cta_forbidden_words": ["join"],
    }
    payload = {
        "title": "Locale CTA",
        "scenes": [
            {
                "narration_ko": "충격적인 후크입니다",
                "visual_prompt_en": "dramatic opening",
                "structure_role": "hook",
            },
            {
                "narration_ko": "오늘은 join 루틴을 바로 시작해보세요",
                "visual_prompt_en": "simple ending",
                "structure_role": "cta",
            },
        ],
    }

    with patch("shorts_maker_v2.pipeline.script_step._load_script_step_locale_bundle", return_value=custom_bundle):
        step = ScriptStep(config=make_config(), llm_router=FakeLLMRouter([payload, payload, payload]))
        with patch.object(ScriptStep, "_validate_cta", return_value=[]) as validator:
            step.run("locale topic")

    validator.assert_called_once()
    assert validator.call_args.args[1] == ("join",)
