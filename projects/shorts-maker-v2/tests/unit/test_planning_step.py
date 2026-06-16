from __future__ import annotations

from types import SimpleNamespace

from shorts_maker_v2.models import GateVerdict, ProductionPlan
from shorts_maker_v2.pipeline.planning_step import PlanningStep


class FakeRouter:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def generate_json(self, *, system_prompt: str, user_prompt: str, temperature: float) -> object:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
            }
        )
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_run_returns_pass_on_first_valid_response() -> None:
    router = FakeRouter(
        [
            {
                "concept": "Explain a concrete AI launch",
                "target_persona": "29-year-old backend engineer worried about AI tooling changes",
                "core_message": "This launch changes daily developer workflow",
                "visual_keywords": ["ai", "dashboard", "benchmark"],
                "forbidden_elements": ["vague claims"],
                "tone": "analytical",
                "audience_analysis": {
                    "desire": "How to adapt to the new AI changes",
                    "emotional_state": "anxious",
                    "knowledge_level": "intermediate",
                    "consumption_context": "commuting",
                },
            }
        ]
    )
    step = PlanningStep(config=SimpleNamespace(), llm_router=router)

    plan, verdict = step.run(topic="OpenAI agent mode", channel_key="ai_tech")

    assert verdict == GateVerdict.PASS
    assert plan.core_message == "This launch changes daily developer workflow"
    assert len(router.calls) == 1
    assert "developer or tech worker" in str(router.calls[0]["user_prompt"])


def test_run_retries_after_gate_failure_then_succeeds() -> None:
    router = FakeRouter(
        [
            {
                "concept": "AI",
                "target_persona": "people",
                "core_message": "ok",
                "visual_keywords": ["ai"],
                "forbidden_elements": [],
                "tone": "fast",
            },
            {
                "concept": "Show how one release affects engineers",
                "target_persona": "31-year-old ML engineer worried about job displacement",
                "core_message": "Specific AI features change hiring expectations",
                "visual_keywords": ["chip", "terminal", "robot"],
                "forbidden_elements": ["fearmongering"],
                "tone": "grounded",
                "audience_analysis": {
                    "desire": "I want to know if my job is safe",
                    "emotional_state": "worried",
                    "knowledge_level": "intermediate",
                    "consumption_context": "before sleep",
                },
            },
        ]
    )
    step = PlanningStep(config=SimpleNamespace(), llm_router=router)

    plan, verdict = step.run(topic="AI jobs", channel_key="")

    assert verdict == GateVerdict.PASS
    assert plan.target_persona.startswith("31-year-old")
    assert len(router.calls) == 2
    assert "IMPORTANT: The previous plan was rejected." in str(router.calls[1]["user_prompt"])


def test_run_uses_fallback_plan_after_exhausting_retries() -> None:
    router = FakeRouter(
        [
            "not-a-dict",
            RuntimeError("provider outage"),
        ]
    )
    step = PlanningStep(config=SimpleNamespace(), llm_router=router)

    plan, verdict = step.run(topic="Mars mission", channel_key="space")

    assert verdict == GateVerdict.PASS
    assert plan.concept.startswith("Mars mission")
    assert plan.visual_keywords == ["modern", "minimalist", "infographic"]
    assert len(router.calls) == 2


def test_parse_plan_strips_values_and_filters_blank_entries() -> None:
    step = PlanningStep(config=SimpleNamespace(), llm_router=FakeRouter([]))

    plan = step._parse_plan(
        {
            "concept": "  Simple concept  ",
            "target_persona": "  specific viewer  ",
            "core_message": "  one big takeaway  ",
            "visual_keywords": [" robot ", "", "terminal"],
            "forbidden_elements": [" hype ", " "],
            "tone": " calm ",
            "audience_analysis": {
                "desire": "  to learn something new  ",
                "emotional_state": "  curious  ",
                "knowledge_level": "  intermediate  ",
                "consumption_context": "  on the bus  ",
            },
        }
    )

    assert plan == ProductionPlan(
        concept="Simple concept",
        target_persona="specific viewer",
        core_message="one big takeaway",
        visual_keywords=["robot", "terminal"],
        forbidden_elements=["hype"],
        tone="calm",
        audience_profile={
            "desire": "to learn something new",
            "emotional_state": "curious",
            "knowledge_level": "intermediate",
            "consumption_context": "on the bus",
        },
    )


def test_gate1_check_collects_all_relevant_issues() -> None:
    verdict, issues = PlanningStep._gate1_check(
        ProductionPlan(
            concept="bad",
            target_persona="vague",
            core_message="",
            visual_keywords=["one"],
            forbidden_elements=[],
            tone="",
        )
    )

    assert verdict == GateVerdict.FAIL_RETRY
    assert "concept too short or missing" in issues
    assert "target_persona too vague (need age/job/worry)" in issues
    assert "core_message missing or too short" in issues
    assert "visual_keywords only 1, need 3+" in issues
    assert "forbidden_elements empty" in issues
    assert "audience_analysis missing" in issues


def test_fallback_plan_uses_topic_in_concept_and_message() -> None:
    plan = PlanningStep._fallback_plan("AI 자동화", "ai_tech")
    assert "AI 자동화" in plan.concept
    assert "AI 자동화" in plan.core_message


def test_fallback_plan_has_three_visual_keywords() -> None:
    plan = PlanningStep._fallback_plan("이직", "history")
    assert len(plan.visual_keywords) == 3


def test_fallback_plan_has_forbidden_elements() -> None:
    plan = PlanningStep._fallback_plan("건강", "health")
    assert len(plan.forbidden_elements) > 0


def test_fallback_plan_lacks_audience_profile_by_design() -> None:
    """_fallback_plan은 audience_profile 없이 반환됨.

    run()에서 폴백 기획서를 사용할 때는 Gate1을 거치지 않고
    직접 GateVerdict.PASS를 반환하므로 이 누락은 의도된 동작임.
    """
    plan = PlanningStep._fallback_plan("Python 비동기 프로그래밍의 핵심", "ai_tech")
    assert plan.audience_profile is None
    # Gate1 관점에서는 fail이지만 run()에서 bypass됨
    verdict, issues = PlanningStep._gate1_check(plan)
    assert verdict.name == "FAIL_RETRY"
    assert "audience_analysis missing" in issues


def test_fallback_plan_empty_topic_still_returns_valid_plan() -> None:
    plan = PlanningStep._fallback_plan("", "space")
    assert isinstance(plan, ProductionPlan)
    assert plan.tone != ""
    assert plan.visual_keywords  # non-empty list


def test_fallback_plan_is_independent_of_channel_key() -> None:
    """channel_key는 현재 _fallback_plan에서 사용되지 않음 — 동일한 구조 보장."""
    plan_ai = PlanningStep._fallback_plan("우주", "ai_tech")
    plan_health = PlanningStep._fallback_plan("우주", "health")
    # visual_keywords and tone should be the same regardless of channel
    assert plan_ai.visual_keywords == plan_health.visual_keywords
    assert plan_ai.tone == plan_health.tone
