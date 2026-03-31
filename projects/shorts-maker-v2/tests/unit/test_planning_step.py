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
