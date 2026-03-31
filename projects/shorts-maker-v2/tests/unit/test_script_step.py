from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.pipeline.script_step import ScriptStep, TopicUnsuitableError, _deep_merge_dicts


class FakeOpenAIClient:
    """LLMRouter.generate_json / OpenAIClient.generate_json 양쪽 시그니처 호환."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_json(
        self,
        *,
        model: str = "",
        system_prompt: str = "",
        user_prompt: str = "",
        temperature: float = 0.7,
        thinking_level: str | None = None,
    ):
        del model, system_prompt, user_prompt, temperature, thinking_level
        self.calls += 1
        if not self.responses:
            raise AssertionError("No more fake responses available.")
        return self.responses.pop(0)


def make_config(
    *,
    duration_range=(20, 30),
    tts_speed=1.05,
    script_review_enabled: bool = False,
    script_review_min_score: int = 6,
    structure_presets: dict[str, list[str]] | None = None,
    default_scene_count: int = 2,
    language: str = "ko-KR",
):
    return SimpleNamespace(
        providers=SimpleNamespace(
            llm="openai",
            llm_model="gpt-4o-mini",
            tts_speed=tts_speed,
            thinking_level="low",
            thinking_level_review="high",
            embedding_model="gemini-embedding-2-preview",
        ),
        project=SimpleNamespace(
            default_scene_count=default_scene_count,
            language=language,
            script_review_enabled=script_review_enabled,
            script_review_min_score=script_review_min_score,
            structure_presets=structure_presets or {},
        ),
        video=SimpleNamespace(
            target_duration_sec=duration_range,
        ),
    )


class FakeResearchContext:
    def __init__(self, prompt_block: str):
        self.prompt_block = prompt_block

    def to_prompt_block(self) -> str:
        return self.prompt_block


class FakeStructureOutline:
    def __init__(self, roles: list[str], prompt_block: str):
        self.scenes = [SimpleNamespace(role=role) for role in roles]
        self.prompt_block = prompt_block

    def to_prompt_block(self) -> str:
        return self.prompt_block


def _make_scene(
    scene_id: int,
    narration: str,
    *,
    role: str = "body",
    visual_prompt: str = "Studio-lit documentary frame",
    target_sec: float | None = None,
) -> ScenePlan:
    return ScenePlan(
        scene_id=scene_id,
        narration_ko=narration,
        visual_prompt_en=visual_prompt,
        target_sec=target_sec or 4.0,
        structure_role=role,
    )


def test_parse_script_payload_handles_code_fence() -> None:
    raw = """
    ```json
    {
        "title": "Test",
        "scenes": [
        {
          "narration_ko": "First scene narration.",
          "visual_prompt_en": "Cinematic close-up of a speaker"
        },
        {
          "narration_ko": "Second scene narration.",
          "visual_prompt_en": "Tracking shot over neon city"
        }
      ]
    }
    ```
    """
    title, scenes = ScriptStep.parse_script_payload(
        raw,
        scene_count=2,
        target_duration_sec=(20, 30),
        language="ko-KR",
        tts_speed=1.05,
    )
    assert title == "Test"
    assert len(scenes) == 2
    assert scenes[0].scene_id == 1
    assert scenes[0].target_sec > 1.0
    assert "Cinematic" in scenes[0].visual_prompt_en


def test_parse_script_payload_uses_own_estimation_not_gpt() -> None:
    """GPT estimated_seconds를 무시하고 자체 추정 함수를 사용하는지 확인."""
    payload = {
        "title": "Alias Test",
        "scenes": [
            {
                "narration": "alpha beta gamma delta epsilon",
                "visual_prompt": "A bright studio shot",
                "estimated_seconds": 4.5,
            },
        ],
    }
    title, scenes = ScriptStep.parse_script_payload(
        payload,
        scene_count=1,
        target_duration_sec=(20, 30),
        language="ko-KR",
        tts_speed=1.05,
    )
    assert title == "Alias Test"
    assert len(scenes) == 1
    # GPT의 4.5가 아닌 자체 추정값 사용 (라틴 토큰 기반, 짧은 값)
    assert scenes[0].target_sec != 4.5
    assert scenes[0].target_sec >= 1.2  # 최소값 보장


def test_validate_script_schema_accepts_alias_scene_fields() -> None:
    payload = {
        "title": "Alias Schema",
        "scenes": [
            {
                "narration": "alpha beta gamma delta epsilon",
                "visual_prompt": "A bright studio shot with clean lighting",
                "structure_role": "body",
            }
        ],
    }

    assert ScriptStep._validate_script_schema(payload) == []


def test_estimate_total_duration_uses_scene_targets() -> None:
    payload = {
        "title": "Total Test",
        "scenes": [
            {
                "narration_ko": "This is the first scene with a little more explanation.",
                "visual_prompt_en": "Scene one",
            },
            {
                "narration_ko": "The second scene uses a longer sentence to stretch the estimate.",
                "visual_prompt_en": "Scene two",
            },
        ],
    }
    _, scenes = ScriptStep.parse_script_payload(
        payload,
        scene_count=2,
        target_duration_sec=(20, 30),
        language="ko-KR",
        tts_speed=1.05,
    )
    total_sec = ScriptStep.estimate_total_duration_sec(scenes)
    assert total_sec == round(scenes[0].target_sec + scenes[1].target_sec, 3)


def test_run_retries_when_first_script_is_too_short() -> None:
    short_payload = {
        "title": "Short Draft",
        "scenes": [
            {
                "narration_ko": "짧아.",
                "visual_prompt_en": "Scene one",
            },
            {
                "narration_ko": "짧음.",
                "visual_prompt_en": "Scene two",
            },
        ],
    }
    long_enough_payload = {
        "title": "Longer Draft",
        "scenes": [
            {
                "narration_ko": "첫 번째 장면은 충분히 긴 나레이션으로 구성합니다.",
                "visual_prompt_en": "Scene one",
            },
            {
                "narration_ko": "두 번째 장면도 충분히 긴 나레이션으로 설명합니다.",
                "visual_prompt_en": "Scene two",
            },
        ],
    }
    client = FakeOpenAIClient([short_payload, long_enough_payload])
    step = ScriptStep(config=make_config(duration_range=(8, 16)), llm_router=client, openai_client=client)

    title, scenes, hook_pattern = step.run("science topic")

    assert title == "Longer Draft"
    assert client.calls == 2
    assert 8.0 <= ScriptStep.estimate_total_duration_sec(scenes) <= 16.0
    assert hook_pattern in [p[0] for p in ScriptStep.HOOK_PATTERNS]


def test_deep_merge_dicts_merges_nested_without_mutating_inputs() -> None:
    base = {"prompt": {"intro": "base", "limits": {"hook": 20}}, "tone": "calm"}
    override = {"prompt": {"limits": {"hook": 12, "body": 80}}, "tone": "urgent"}

    merged = _deep_merge_dicts(base, override)

    assert merged == {
        "prompt": {"intro": "base", "limits": {"hook": 12, "body": 80}},
        "tone": "urgent",
    }
    assert base == {"prompt": {"intro": "base", "limits": {"hook": 20}}, "tone": "calm"}


def test_from_channel_profile_sets_channel_overrides() -> None:
    step = ScriptStep.from_channel_profile(
        make_config(),
        FakeOpenAIClient([]),
        {"hook_pattern": "myth_busting", "target_duration_sec": 42},
        channel_key="ai_tech",
    )

    assert step.channel_hook_pattern == "myth_busting"
    assert step.channel_duration_override == 42
    assert step.channel_key == "ai_tech"


def test_trim_hook_to_limit_strips_trailing_space() -> None:
    assert ScriptStep._trim_hook_to_limit("hook line   ", limit=4) == "hook"


def test_validate_cta_and_persona_score_handle_edge_cases() -> None:
    violations = ScriptStep._validate_cta("Please subscribe and hit the bell", ("subscribe", "bell"))
    empty_score = ScriptStep._score_persona_match([], "ai_tech", {"ai_tech": ("tensor",)})
    neutral_score = ScriptStep._score_persona_match(
        [_make_scene(1, "A calm explanatory scene.")],
        "unknown",
        {"ai_tech": ("tensor",)},
    )

    assert violations == ["subscribe", "bell"]
    assert empty_score == 0.0
    assert neutral_score == 0.5


def test_get_hook_pattern_falls_back_when_fixed_pattern_is_missing() -> None:
    step = ScriptStep(
        config=make_config(),
        llm_router=FakeOpenAIClient([]),
        channel_hook_pattern="missing_pattern",
    )

    with patch.object(step, "_next_hook_pattern", return_value=("fallback", "Fallback instruction")) as fallback:
        selected = step._get_hook_pattern()

    assert selected == ("fallback", "Fallback instruction")
    fallback.assert_called_once()


def test_next_structure_preset_rotates_configured_presets() -> None:
    step = ScriptStep(
        config=make_config(
            structure_presets={
                "story_arc": ["hook", "body", "closing"],
                "fast_facts": ["hook", "cta"],
            }
        ),
        llm_router=FakeOpenAIClient([]),
    )

    with patch.object(ScriptStep, "_structure_counter", 0):
        first_name, first_flow = step._next_structure_preset()
        second_name, second_flow = step._next_structure_preset()

    assert (first_name, first_flow) == ("story_arc", ["hook", "body", "closing"])
    assert (second_name, second_flow) == ("fast_facts", ["hook", "cta"])


def test_build_user_prompt_includes_context_and_retry_guidance() -> None:
    step = ScriptStep(config=make_config(), llm_router=FakeOpenAIClient([]))

    prompt = step._build_user_prompt(
        topic="AI chips",
        duration_range=(8, 14),
        attempt=2,
        previous_total_sec=20.0,
        previous_scene_count=3,
        research_block="FACT: latency improved.\n",
        structure_block="STRUCTURE: hook -> body -> closing",
    )

    assert "FACT: latency improved." in prompt
    assert "STRUCTURE: hook -> body -> closing" in prompt
    assert "20.0 seconds" in prompt
    assert "Keep exactly 3 scenes" in prompt


def test_review_script_uses_review_thinking_level() -> None:
    llm_router = MagicMock()
    llm_router.generate_json.return_value = {"hook_score": 8, "flow_score": 8}
    step = ScriptStep(config=make_config(), llm_router=llm_router, channel_key="ai_tech")

    result = step._review_script("AI update", [_make_scene(1, "This hook sentence is long enough.", role="hook")])

    assert result["hook_score"] == 8
    assert llm_router.generate_json.call_args.kwargs["thinking_level"] == "high"
    assert "[HOOK]" in llm_router.generate_json.call_args.kwargs["user_prompt"]


def test_verify_with_research_returns_safe_defaults_when_context_is_missing_or_fails() -> None:
    llm_router = MagicMock()
    llm_router.generate_json.side_effect = RuntimeError("verification service unavailable")
    step = ScriptStep(config=make_config(), llm_router=llm_router)
    scenes = [_make_scene(1, "A factual sentence for validation.", role="body")]

    assert step._verify_with_research("Title", scenes, object()) == {
        "consistent": True,
        "issues": [],
        "fixes": [],
        "confidence": 1.0,
    }
    assert step._verify_with_research("Title", scenes, FakeResearchContext("")) == {
        "consistent": True,
        "issues": [],
        "fixes": [],
        "confidence": 1.0,
    }
    assert step._verify_with_research("Title", scenes, FakeResearchContext("Verified facts")) == {
        "consistent": True,
        "issues": [],
        "fixes": [],
        "confidence": 1.0,
    }


def test_apply_verification_fixes_updates_only_matching_scenes() -> None:
    step = ScriptStep(config=make_config(), llm_router=FakeOpenAIClient([]))
    scenes = [
        _make_scene(1, "Original hook narration with enough words.", role="hook", target_sec=3.5),
        _make_scene(2, "Original closing narration with enough words.", role="closing", target_sec=3.5),
    ]

    patched = step._apply_verification_fixes(
        scenes,
        {
            "fixes": [
                {"scene_id": 2, "suggested": "Updated closing narration with verified details included."},
                {"scene_id": None, "suggested": "ignored"},
            ]
        },
    )

    assert patched[0] is scenes[0]
    assert patched[1].narration_ko == "Updated closing narration with verified details included."
    assert patched[1].target_sec != scenes[1].target_sec
    assert patched[1].structure_role == "closing"


def test_validate_script_schema_returns_errors_for_invalid_scene_objects() -> None:
    errors = ScriptStep._validate_script_schema({"title": "Broken", "scenes": ["not-a-scene"]})

    assert errors


def test_passes_review_checks_all_required_keys_for_channel_specific_review() -> None:
    step = ScriptStep(
        config=make_config(script_review_min_score=7),
        llm_router=FakeOpenAIClient([]),
        channel_key="ai_tech",
    )

    review = {
        "hook_score": 7,
        "flow_score": 7,
        "cta_score": 7,
        "verifiability_score": 7,
        "spelling_score": 7,
        "data_score": 7,
    }

    assert step._passes_review(review, 7) is True
    review["data_score"] = 6
    assert step._passes_review(review, 7) is False


def test_truncate_to_fit_shortens_long_scenes_and_preserves_roles() -> None:
    step = ScriptStep(config=make_config(), llm_router=FakeOpenAIClient([]))
    long_text = " ".join(f"word{i}" for i in range(80))
    scenes = [
        _make_scene(1, long_text, role="hook", target_sec=20.0),
        _make_scene(2, long_text, role="closing", target_sec=20.0),
    ]

    truncated = step._truncate_to_fit(scenes, max_total_sec=12.0, language="en-US", tts_speed=1.0)

    assert ScriptStep.estimate_total_duration_sec(truncated) < ScriptStep.estimate_total_duration_sec(scenes)
    assert truncated[0].structure_role == "hook"
    assert truncated[1].structure_role == "closing"
    assert truncated[0].narration_ko.endswith("...")


def test_run_raises_topic_unsuitable_when_llm_reports_no_reliable_source() -> None:
    payload = {"title": "", "scenes": [], "no_reliable_source": True, "reason": "no supporting sources"}
    step = ScriptStep(config=make_config(), llm_router=FakeOpenAIClient([payload]))

    with pytest.raises(TopicUnsuitableError, match="no supporting sources"):
        step.run("hard-to-source topic")


def test_run_applies_research_fixes_and_truncates_when_over_hard_limit() -> None:
    payload = {
        "title": "Original draft",
        "scenes": [
            {
                "narration_ko": "This opening scene has enough detail to be parsed cleanly by the script step.",
                "visual_prompt_en": "clean opening frame",
                "structure_role": "hook",
            },
            {
                "narration_ko": "This ending scene also has enough detail for parsing before verification runs.",
                "visual_prompt_en": "clean ending frame",
                "structure_role": "closing",
            },
        ],
    }
    verification = {
        "consistent": False,
        "issues": ["scene 2 exaggerates the result"],
        "fixes": [{"scene_id": 2, "suggested": "Corrected ending line with verified facts and calmer wording."}],
        "confidence": 0.62,
    }
    step = ScriptStep(
        config=make_config(duration_range=(45, 60)),
        llm_router=MagicMock(generate_json=MagicMock(return_value=payload)),
        channel_key="ai_tech",
    )
    structure_outline = FakeStructureOutline(["hook", "closing"], "STRUCTURE: hook then closing")
    research_context = FakeResearchContext("FACTS: verified benchmark results only.")

    with (
        patch.object(step, "_verify_with_research", return_value=verification),
        patch.object(step, "_truncate_to_fit", side_effect=lambda scenes, *_args: scenes) as truncate,
        patch.object(step, "estimate_total_duration_sec", side_effect=[50.0, 50.0, 40.0]),
    ):
        title, scenes, _ = step.run(
            "ai topic",
            research_context=research_context,
            structure_outline=structure_outline,
        )

    assert title == "Original draft"
    assert scenes[1].narration_ko == "Corrected ending line with verified facts and calmer wording."
    truncate.assert_called_once()


def test_run_uses_review_retry_when_scores_fail_threshold() -> None:
    initial_payload = {
        "title": "Initial draft",
        "scenes": [
            {
                "narration_ko": "This first script has enough words to land inside the target duration range.",
                "visual_prompt_en": "opening shot",
                "structure_role": "hook",
            },
            {
                "narration_ko": "This closing line also has enough detail to stay within range for the test.",
                "visual_prompt_en": "closing shot",
                "structure_role": "closing",
            },
        ],
    }
    retry_payload = {
        "title": "Retried draft",
        "scenes": [
            {
                "narration_ko": "The retried script now adds stronger specifics and a clearer opening sentence.",
                "visual_prompt_en": "improved opening shot",
                "structure_role": "hook",
            },
            {
                "narration_ko": "The improved ending now includes sharper details and a better final takeaway.",
                "visual_prompt_en": "improved closing shot",
                "structure_role": "closing",
            },
        ],
    }
    llm_router = MagicMock()
    llm_router.generate_json.side_effect = [initial_payload, retry_payload]
    step = ScriptStep(
        config=make_config(duration_range=(4, 40), script_review_enabled=True, script_review_min_score=7),
        llm_router=llm_router,
        channel_key="ai_tech",
    )

    with patch.object(
        step,
        "_review_script",
        return_value={
            "hook_score": 6,
            "flow_score": 6,
            "cta_score": 7,
            "verifiability_score": 7,
            "spelling_score": 7,
            "data_score": 5,
            "feedback": "Needs more specifics.",
        },
    ):
        title, scenes, _ = step.run("ai systems")

    assert title == "Retried draft"
    assert llm_router.generate_json.call_count == 2
    assert "Quality feedback to fix" in llm_router.generate_json.call_args.kwargs["user_prompt"]
    assert scenes[0].narration_ko == "The retried scr"


def test_run_skips_review_errors_and_returns_best_result() -> None:
    payload = {
        "title": "Stable draft",
        "scenes": [
            {
                "narration_ko": "This script should still return even if the review service breaks unexpectedly.",
                "visual_prompt_en": "stable opening shot",
                "structure_role": "hook",
            },
            {
                "narration_ko": "This ending scene remains valid and should be returned unchanged by the step.",
                "visual_prompt_en": "stable ending shot",
                "structure_role": "closing",
            },
        ],
    }
    step = ScriptStep(
        config=make_config(duration_range=(8, 16), script_review_enabled=True),
        llm_router=MagicMock(generate_json=MagicMock(return_value=payload)),
    )

    with patch.object(step, "_review_script", side_effect=RuntimeError("review backend down")):
        title, scenes, _ = step.run("resilient topic")

    assert title == "Stable draft"
    assert len(scenes) == 2
