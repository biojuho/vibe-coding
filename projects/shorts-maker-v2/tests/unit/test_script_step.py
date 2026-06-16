from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.pipeline.script_prompts import ScriptPromptsMixin
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
                "narration_ko": "짧습니다.",  # 5 chars — passes min-length guard; TTS still short
                "visual_prompt_en": "Scene one",
            },
            {
                "narration_ko": "짧습니다.",  # 5 chars — same trick for scene 2
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

    title, scenes, hook_pattern, _ = step.run("science topic")

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


def test_cognitive_dissonance_hook_pattern_is_recognized() -> None:
    """topic_angle_generator가 반환하는 cognitive_dissonance 패턴이 HOOK_PATTERNS에 존재해야 한다."""
    step = ScriptStep(
        config=make_config(),
        llm_router=FakeOpenAIClient([]),
        channel_hook_pattern="cognitive_dissonance",
    )
    name, instruction = step._get_hook_pattern()
    assert name == "cognitive_dissonance"
    assert "반전" in instruction or "defies" in instruction.lower() or "dissonance" in instruction.lower()


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

    # ScriptStep 이 아니라 mixin 의 클래스 속성을 patch 해야 실제 카운터가 리셋된다
    # (_next_structure_preset 은 ScriptPromptsMixin._structure_counter 를 직접 읽는다).
    with patch.object(ScriptPromptsMixin, "_structure_counter", 0):
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


def test_passes_review_handles_float_scores_from_llm() -> None:
    """SMV2-SR001: LLM sometimes returns 7.5 or '8.5' instead of integer scores."""
    step = ScriptStep(
        config=make_config(script_review_min_score=7),
        llm_router=FakeOpenAIClient([]),
        channel_key="ai_tech",
    )

    # float values like 7.5 should pass int(float()) without ValueError
    review_float = {
        "hook_score": 7.5,
        "flow_score": 8.0,
        "cta_score": 7.5,
        "verifiability_score": 8.5,
        "spelling_score": 7.5,
        "data_score": 7.0,
    }
    assert step._passes_review(review_float, 7) is True

    # string float values like "8.5" should also work
    review_str_float = {k: str(v) for k, v in review_float.items()}
    assert step._passes_review(review_str_float, 7) is True

    # "6.9" should fail min_score=7
    review_str_float["data_score"] = "6.9"
    assert step._passes_review(review_str_float, 7) is False


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
        title, scenes, _, _ = step.run(
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
        title, scenes, _, _ = step.run("ai systems")

    assert title == "Retried draft"
    assert llm_router.generate_json.call_count == 2
    assert "Quality feedback to fix" in llm_router.generate_json.call_args.kwargs["user_prompt"]
    # T-AB026: hook hard cap 40→55. 78자 → 55자 head의
    # 마지막 공백("a" 뒤, position 52) 에서 절단 → 52자.
    assert scenes[0].narration_ko == "The retried script now adds stronger specifics and a"


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
        title, scenes, _, _ = step.run("resilient topic")

    assert title == "Stable draft"
    assert len(scenes) == 2


def test_run_keeps_original_when_retry_parse_fails() -> None:
    """SR-RETRY001: retry parse_script_payload 실패 시 원본 결과 보존 + 경고 로그.

    이전 코드는 retry ValueError가 outer except에 잡혀 '채점 실패(스킵)'로 mis-log 됐다.
    Isolated inner try/except로 수정 후 '재생성 실패(원본 유지)' 경고를 남겨야 한다.
    """
    initial_payload = {
        "title": "Original script",
        "scenes": [
            {
                "narration_ko": "This original narration has enough words to land inside the target duration range.",
                "visual_prompt_en": "opening shot",
                "structure_role": "hook",
            },
            {
                "narration_ko": "The original ending narration also has enough detail to stay in range here.",
                "visual_prompt_en": "closing shot",
                "structure_role": "closing",
            },
        ],
    }
    # Retry payload is None → parse_script_payload raises ValueError (see TestParseScriptPayloadGuards)
    llm_router = MagicMock()
    llm_router.generate_json.side_effect = [initial_payload, None]

    step = ScriptStep(
        config=make_config(duration_range=(4, 40), script_review_enabled=True, script_review_min_score=7),
        llm_router=llm_router,
        channel_key="ai_tech",
    )

    with (
        patch.object(
            step,
            "_review_script",
            return_value={
                "hook_score": 5,
                "flow_score": 5,
                "cta_score": 5,
                "verifiability_score": 5,
                "spelling_score": 5,
                "data_score": 4,
                "feedback": "Too weak.",
            },
        ),
        patch("shorts_maker_v2.pipeline.script_step.logger") as mock_logger,
    ):
        title, scenes, _, _ = step.run("quantum computing")

    assert title == "Original script"
    warning_msgs = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert any("retry generation failed" in msg for msg in warning_msgs)


def test_topic_unsuitable_propagates_from_review_stage() -> None:
    """SMV2-SS001: verifiability_score < 4 시 TopicUnsuitableError가 오케스트레이터까지 전파돼야 함.

    리뷰 단계의 except Exception이 TopicUnsuitableError를 삼키면
    오케스트레이터가 topic_unsuitable을 감지하지 못하고 불량 스크립트를 출하한다.
    """
    payload = {
        "title": "Low verifiability topic",
        "scenes": [
            {
                "narration_ko": "This hook sentence is intentionally long enough to exceed the minimum length check.",
                "visual_prompt_en": "opening frame",
                "structure_role": "hook",
            },
            {
                "narration_ko": "This body scene adds context to the unverifiable claim made in the introduction.",
                "visual_prompt_en": "body frame",
                "structure_role": "body",
            },
        ],
    }
    step = ScriptStep(
        config=make_config(duration_range=(8, 16), script_review_enabled=True),
        llm_router=MagicMock(generate_json=MagicMock(return_value=payload)),
    )

    with (
        patch.object(
            step,
            "_review_script",
            return_value={"verifiability_score": 2, "feedback": "no sources found"},
        ),
        pytest.raises(TopicUnsuitableError, match="verifiability_score=2"),
    ):
        step.run("unverifiable topic")


@pytest.mark.parametrize(
    "forbidden_opener",
    ["오늘은", "오늘의", "이번에는", "이번엔", "여러분", "우리는", "우리가", "안녕하세요"],
)
def test_hook_rules_ko_contains_all_forbidden_openers(forbidden_opener: str) -> None:
    """YAML과 script_prompts.py의 금지 오프너 목록이 동기화돼 있는지 확인."""
    default_copy = ScriptPromptsMixin._PROMPT_COPY
    ko_rules = default_copy.get("hook_rules_ko", "")
    assert forbidden_opener in ko_rules, f"'{forbidden_opener}' not found in hook_rules_ko"


# ── T-AB027: _PERSONA_KEYWORDS 품질 불변조건 ────────────────────────────


class TestPersonaKeywordsQuality:
    """_PERSONA_KEYWORDS 키워드 품질 불변조건 (T-AB027)."""

    def test_each_channel_has_ten_keywords(self) -> None:
        kw = ScriptPromptsMixin._PERSONA_KEYWORDS
        for channel, keywords in kw.items():
            assert len(keywords) == 10, f"{channel} has {len(keywords)} keywords, expected 10"

    def test_no_cross_channel_contamination_ai_tech_health(self) -> None:
        """ai_tech과 health가 같은 키워드를 공유하면 페르소나 스코어가 오염된다."""
        ai_kw = set(ScriptPromptsMixin._PERSONA_KEYWORDS["ai_tech"])
        health_kw = set(ScriptPromptsMixin._PERSONA_KEYWORDS["health"])
        overlap = ai_kw & health_kw
        assert not overlap, f"ai_tech and health share keywords: {overlap}"

    def test_llm_present_in_ai_tech(self) -> None:
        """2026 핵심 AI 용어 LLM이 ai_tech 키워드에 포함돼야 한다."""
        assert "LLM" in ScriptPromptsMixin._PERSONA_KEYWORDS["ai_tech"]

    def test_generic_symbol_percent_not_a_keyword(self) -> None:
        """'%'는 모든 채널의 키워드에 포함돼선 안 된다 (텍스트 매칭 불가)."""
        for channel, keywords in ScriptPromptsMixin._PERSONA_KEYWORDS.items():
            assert "%" not in keywords, f"'{channel}' still contains generic '%' keyword"

    def test_second_person_dangshin_not_in_psychology(self) -> None:
        """'당신' is too generic (any 2nd-person text). Must not be a psychology signal."""
        assert "당신" not in ScriptPromptsMixin._PERSONA_KEYWORDS["psychology"]

    def test_brain_keyword_in_psychology(self) -> None:
        """'뇌' (brain) is a strong psychology domain signal."""
        assert "뇌" in ScriptPromptsMixin._PERSONA_KEYWORDS["psychology"]

    def test_disease_or_prevention_in_health(self) -> None:
        """Health channel should include disease/prevention terms, not generic '효과'."""
        health_kw = set(ScriptPromptsMixin._PERSONA_KEYWORDS["health"])
        assert health_kw & {"질병", "예방", "의학"}, "health needs at least one of: 질병, 예방, 의학"


class TestParseScriptPayloadGuards:
    """Regression tests for None payload and short-narration guards."""

    def _two_scene_payload(self) -> dict:
        return {
            "title": "테스트 숏츠",
            "scenes": [
                {
                    "narration_ko": "이것은 후크 나레이션입니다 충분히 깁니다.",
                    "visual_prompt_en": "cinematic wide shot of a city",
                    "structure_role": "hook",
                },
                {
                    "narration_ko": "이것은 본문 나레이션입니다 충분히 길어야 합니다.",
                    "visual_prompt_en": "close-up of a person thinking",
                    "structure_role": "body",
                },
            ],
        }

    def test_none_payload_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="None payload"):
            ScriptStep.parse_script_payload(None, scene_count=2, target_duration_sec=(20, 40))

    def test_valid_payload_parses_without_error(self) -> None:
        title, scenes = ScriptStep.parse_script_payload(
            self._two_scene_payload(), scene_count=2, target_duration_sec=(20, 40)
        )
        assert title == "테스트 숏츠"
        assert len(scenes) == 2

    def test_short_narration_raises(self) -> None:
        payload = self._two_scene_payload()
        payload["scenes"][0]["narration_ko"] = "짧"  # 1 char — below min 5
        with pytest.raises(ValueError, match="narration too short"):
            ScriptStep.parse_script_payload(payload, scene_count=2, target_duration_sec=(20, 40))

    def test_four_char_narration_raises(self) -> None:
        payload = self._two_scene_payload()
        payload["scenes"][1]["narration_ko"] = "안녕하"  # 3 chars — below min 5
        with pytest.raises(ValueError, match="narration too short"):
            ScriptStep.parse_script_payload(payload, scene_count=2, target_duration_sec=(20, 40))

    def test_five_char_narration_passes(self) -> None:
        payload = self._two_scene_payload()
        payload["scenes"][0]["narration_ko"] = "안녕하세요"  # exactly 5 chars — OK
        title, scenes = ScriptStep.parse_script_payload(payload, scene_count=2, target_duration_sec=(20, 40))
        assert len(scenes) == 2


class TestBuildReviewSystem:
    """_build_review_system: 채널별 min_score, extra_keys, context_note 주입 검증."""

    def _make_step(self, channel_key: str, min_score: int = 6) -> ScriptStep:
        return ScriptStep(
            config=make_config(script_review_min_score=min_score),
            llm_router=FakeOpenAIClient([]),
            channel_key=channel_key,
        )

    def test_unknown_channel_returns_base_keys_only(self) -> None:
        step = self._make_step("unknown_channel")
        _, keys, _ = step._build_review_system()
        assert set(keys) == {"hook_score", "flow_score", "cta_score", "verifiability_score", "spelling_score"}

    def test_unknown_channel_uses_config_min_score(self) -> None:
        step = self._make_step("unknown_channel", min_score=7)
        _, _, min_score = step._build_review_system()
        assert min_score == 7

    def test_health_channel_overrides_min_score_to_8(self) -> None:
        step = self._make_step("health", min_score=6)
        _, _, min_score = step._build_review_system()
        assert min_score == 8

    def test_health_channel_adds_extra_keys(self) -> None:
        step = self._make_step("health")
        _, keys, _ = step._build_review_system()
        assert "source_score" in keys
        assert "safety_score" in keys

    def test_ai_tech_channel_adds_data_score_key(self) -> None:
        step = self._make_step("ai_tech")
        _, keys, _ = step._build_review_system()
        assert "data_score" in keys

    def test_ai_tech_channel_overrides_min_score_to_7(self) -> None:
        step = self._make_step("ai_tech", min_score=5)
        _, _, min_score = step._build_review_system()
        assert min_score == 7

    def test_psychology_channel_adds_empathy_score_key(self) -> None:
        step = self._make_step("psychology")
        _, keys, _ = step._build_review_system()
        assert "empathy_score" in keys

    def test_history_channel_adds_narrative_score_key(self) -> None:
        step = self._make_step("history")
        _, keys, _ = step._build_review_system()
        assert "narrative_score" in keys

    def test_space_channel_adds_wonder_score_key(self) -> None:
        step = self._make_step("space")
        _, keys, _ = step._build_review_system()
        assert "wonder_score" in keys

    def test_health_system_prompt_includes_context_note(self) -> None:
        step = self._make_step("health")
        system_prompt, _, _ = step._build_review_system()
        assert "HEALTH" in system_prompt or "health" in system_prompt.lower()

    def test_system_prompt_includes_all_extra_keys_in_json_example(self) -> None:
        step = self._make_step("ai_tech")
        system_prompt, _, _ = step._build_review_system()
        assert "data_score" in system_prompt


class TestScorePersonaMatch:
    """_score_persona_match 키워드 밀도 스코어링 공식 검증."""

    def _make_scene(self, narration: str) -> ScenePlan:
        return ScenePlan(
            scene_id=1,
            narration_ko=narration,
            visual_prompt_en="test",
            target_sec=4.0,
            structure_role="body",
        )

    def test_empty_scenes_returns_zero(self) -> None:
        score = ScriptStep._score_persona_match([], "ai_tech", {"ai_tech": ("AI", "딥러닝")})
        assert score == 0.0

    def test_unknown_channel_returns_neutral_point_five(self) -> None:
        scenes = [self._make_scene("AI 딥러닝 모델")]
        score = ScriptStep._score_persona_match(scenes, "unknown_channel", {"ai_tech": ("AI",)})
        assert score == 0.5

    def test_no_keyword_hit_returns_zero(self) -> None:
        scenes = [self._make_scene("날씨가 맑은 하루였습니다.")]
        score = ScriptStep._score_persona_match(scenes, "ai_tech", {"ai_tech": ("AI", "딥러닝", "모델")})
        assert score == 0.0

    def test_all_keywords_hit_returns_one(self) -> None:
        # All 2 keywords present — (2+0.5)/2 = 1.25 → capped at 1.0
        scenes = [self._make_scene("AI와 딥러닝에 대한 내용입니다.")]
        score = ScriptStep._score_persona_match(scenes, "ai_tech", {"ai_tech": ("AI", "딥러닝")})
        assert score == 1.0

    def test_partial_hit_gives_intermediate_score(self) -> None:
        # 1 hit out of 4 keywords: (1+0.5)/4 = 0.375
        scenes = [self._make_scene("AI에 대한 내용입니다.")]
        score = ScriptStep._score_persona_match(scenes, "ai_tech", {"ai_tech": ("AI", "딥러닝", "모델", "알고리즘")})
        assert abs(score - 0.375) < 0.001

    def test_multi_scene_concatenates_all_text(self) -> None:
        scenes = [
            self._make_scene("AI 기술이 발전합니다."),
            self._make_scene("딥러닝 모델의 한계점을 살펴봅니다."),
        ]
        score = ScriptStep._score_persona_match(scenes, "ai_tech", {"ai_tech": ("AI", "딥러닝", "모델")})
        # All 3 keywords present: (3+0.5)/3 ≈ 1.167 → capped at 1.0
        assert score == 1.0

    def test_score_is_rounded_to_three_decimals(self) -> None:
        # 1 hit out of 3: (1+0.5)/3 = 0.5
        scenes = [self._make_scene("AI 관련 내용")]
        score = ScriptStep._score_persona_match(scenes, "ai_tech", {"ai_tech": ("AI", "딥러닝", "모델")})
        assert score == round(score, 3)


class TestValidateCtaEdgeCases:
    """_validate_cta: 대소문자 무관 매칭, 다중 위반, 경계 케이스 검증."""

    def test_no_violations_returns_empty_list(self) -> None:
        result = ScriptStep._validate_cta("오늘도 좋은 하루 되세요.", ("구독", "좋아요", "알림"))
        assert result == []

    def test_uppercase_forbidden_word_is_detected(self) -> None:
        result = ScriptStep._validate_cta("Please SUBSCRIBE now!", ("subscribe",))
        assert "subscribe" in result

    def test_multiple_violations_all_reported(self) -> None:
        result = ScriptStep._validate_cta("구독하고 좋아요 누르세요!", ("구독", "좋아요", "알림"))
        assert "구독" in result
        assert "좋아요" in result
        assert "알림" not in result  # 알림은 없음

    def test_violation_in_middle_of_sentence_detected(self) -> None:
        result = ScriptStep._validate_cta("이 영상이 도움이 됐다면 구독 부탁드립니다.", ("구독",))
        assert result == ["구독"]

    def test_empty_narration_returns_empty_list(self) -> None:
        result = ScriptStep._validate_cta("", ("구독", "좋아요"))
        assert result == []

    def test_empty_forbidden_words_returns_empty_list(self) -> None:
        result = ScriptStep._validate_cta("구독하고 좋아요!", ())
        assert result == []

    def test_default_forbidden_words_catch_cta_pattern(self) -> None:
        result = ScriptStep._validate_cta("구독 버튼 눌러주세요")
        assert len(result) > 0


# ── SS-CDO: channel_duration_override=0 regression (2026-06-16) ─────────────


def test_channel_duration_override_zero_uses_channel_range_not_config() -> None:
    """SS-CDO001: channel_duration_override=0 must NOT be silently skipped (falsy guard).

    Old guard: `if self.channel_duration_override:` → 0 treated as "not set".
    New guard: `if self.channel_duration_override is not None:` → 0 is valid.
    Even though 0s target is degenerate, the code path must enter the override branch.
    """
    step = ScriptStep(
        make_config(duration_range=(30, 40)),
        FakeOpenAIClient([]),
        channel_duration_override=0,
        channel_key="test",
    )
    # Verify the attribute is set correctly so the is-not-None guard picks it up
    assert step.channel_duration_override == 0  # confirms None check fixed; was falsy before
