"""Unit tests — RetentionAutoFixer (리텐션 자가 치유 closed-loop).

검증 범위:
  - 게이트: verdict 가 degraded 가 아니거나 max_passes=0 이면 skip.
  - 에러 경로: 입력 없음 / llm_router 없음 / LLM 실패 → verdict='error'.
  - 재작성 검증: CTA 금지어·길이·한글 위반 재작성은 거부된다.
  - 폐루프: 재시뮬레이션이 개선을 확인할 때만 채택, 아니면 원본 유지.
  - 멀티 패스: 임계값 회복 시 조기 종료.
"""

from __future__ import annotations

from shorts_maker_v2.models import (
    RetentionAutoFixResult,
    RetentionSimulationResult,
    ScenePlan,
)
from shorts_maker_v2.pipeline.retention_autofix import RetentionAutoFixer


class _StubLLMRouter:
    """narration_ko 를 돌려주는 generate_json stub."""

    def __init__(self, *, narration=None, response=None, raise_exc=None):
        if response is not None:
            self.response = response
        elif narration is not None:
            self.response = {"narration_ko": narration, "rationale": "tighter"}
        else:
            self.response = None
        self.raise_exc = raise_exc
        self.calls: list[dict] = []

    def generate_json(self, *, system_prompt, user_prompt, temperature=0.7):
        self.calls.append({"user_prompt": user_prompt, "temperature": temperature})
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.response


class _FakeSimulator:
    """재시뮬레이션 결과를 큐에서 순서대로 돌려주는 가짜 시뮬레이터."""

    def __init__(self, results: list[RetentionSimulationResult]):
        self._results = list(results)
        self.calls = 0

    def run(self, *, scene_plans, scene_assets=None, structure_outline=None):
        self.calls += 1
        if self._results:
            return self._results.pop(0)
        # 큐가 비면 마지막 결과를 반복
        return RetentionSimulationResult(predicted_retention=0.5, verdict="degraded")


def _plans() -> list[ScenePlan]:
    return [
        ScenePlan(
            scene_id=1,
            narration_ko="시작을 알리는 첫 장면이다",
            visual_prompt_en="p1",
            target_sec=3.0,
            structure_role="hook",
        ),
        ScenePlan(
            scene_id=2,
            narration_ko="여기 약한 중간 장면",
            visual_prompt_en="p2",
            target_sec=8.0,
            structure_role="insight",
        ),
        ScenePlan(
            scene_id=3,
            narration_ko="조용한 여운으로 마무리한다",
            visual_prompt_en="p3",
            target_sec=4.0,
            structure_role="closing",
        ),
    ]


def _degraded(weakest: int = 2, retention: float = 0.40) -> RetentionSimulationResult:
    return RetentionSimulationResult(
        predicted_retention=retention,
        verdict="degraded",
        weakest_scene_id=weakest,
        rewrite_directive="씬 2를 더 구체적으로",
    )


def _sim(retention: float, verdict: str = "degraded", weakest: int = 2) -> RetentionSimulationResult:
    return RetentionSimulationResult(
        predicted_retention=retention,
        verdict=verdict,
        weakest_scene_id=weakest,
        rewrite_directive="개선",
    )


# ── 게이트 / no-op ──────────────────────────────────────────────────


class TestGate:
    def test_pass_verdict_is_skipped(self) -> None:
        llm = _StubLLMRouter(narration="x")
        sim = _FakeSimulator([])
        fixer = RetentionAutoFixer(llm_router=llm, simulator=sim, max_passes=1)
        result = fixer.fix(_plans(), _sim(0.8, verdict="pass"))
        assert result.verdict == "skipped"
        assert result.applied is False
        assert llm.calls == []

    def test_max_passes_zero_is_skipped(self) -> None:
        llm = _StubLLMRouter(narration="x")
        fixer = RetentionAutoFixer(llm_router=llm, simulator=_FakeSimulator([]), max_passes=0)
        result = fixer.fix(_plans(), _degraded())
        assert result.verdict == "skipped"
        assert llm.calls == []

    def test_empty_plans_is_error(self) -> None:
        fixer = RetentionAutoFixer(
            llm_router=_StubLLMRouter(narration="x"),
            simulator=_FakeSimulator([]),
            max_passes=1,
        )
        result = fixer.fix([], _degraded())
        assert result.verdict == "error"

    def test_no_llm_router_is_error(self) -> None:
        fixer = RetentionAutoFixer(llm_router=None, simulator=_FakeSimulator([]), max_passes=1)
        result = fixer.fix(_plans(), _degraded())
        assert result.verdict == "error"


# ── 에러 경로 ───────────────────────────────────────────────────────


class TestErrorPaths:
    def test_llm_exception_first_pass_is_error(self) -> None:
        llm = _StubLLMRouter(raise_exc=RuntimeError("api down"))
        fixer = RetentionAutoFixer(llm_router=llm, simulator=_FakeSimulator([]), max_passes=1)
        result = fixer.fix(_plans(), _degraded())
        assert result.verdict == "error"
        assert result.before_retention == 0.40

    def test_llm_non_dict_is_error(self) -> None:
        llm = _StubLLMRouter(response="not json")
        fixer = RetentionAutoFixer(llm_router=llm, simulator=_FakeSimulator([]), max_passes=1)
        result = fixer.fix(_plans(), _degraded())
        assert result.verdict == "error"

    def test_weakest_scene_not_in_plans_skips(self) -> None:
        llm = _StubLLMRouter(narration="x")
        fixer = RetentionAutoFixer(llm_router=llm, simulator=_FakeSimulator([]), max_passes=1)
        result = fixer.fix(_plans(), _degraded(weakest=999))
        assert result.verdict == "skipped"
        assert llm.calls == []


# ── 폐루프: 채택 / 거부 ─────────────────────────────────────────────


class TestClosedLoop:
    def test_improvement_is_accepted(self) -> None:
        llm = _StubLLMRouter(narration="훨씬 더 구체적이고 흥미로운 중간 장면으로 바꾼다")
        sim = _FakeSimulator([_sim(0.72, verdict="pass")])
        fixer = RetentionAutoFixer(llm_router=llm, simulator=sim, max_passes=1)
        result = fixer.fix(_plans(), _degraded(retention=0.40))
        assert result.verdict == "improved"
        assert result.applied is True
        assert result.passes == 1
        assert result.before_retention == 0.40
        assert result.after_retention == 0.72
        assert result.rewrites[0]["accepted"] is True
        assert result.rewrites[0]["scene_id"] == 2

    def test_no_improvement_keeps_original(self) -> None:
        llm = _StubLLMRouter(narration="별로 나아지지 않은 중간 장면 나레이션")
        sim = _FakeSimulator([_sim(0.38)])  # 0.40 -> 0.38 — 악화
        fixer = RetentionAutoFixer(llm_router=llm, simulator=sim, max_passes=1)
        result = fixer.fix(_plans(), _degraded(retention=0.40))
        assert result.verdict == "no_improvement"
        assert result.applied is False
        assert result.after_retention == 0.40  # 원본 유지
        assert result.rewrites[0]["accepted"] is False

    def test_cta_rewrite_is_rejected(self) -> None:
        llm = _StubLLMRouter(narration="이 영상이 좋았다면 구독과 좋아요 부탁드립니다")
        sim = _FakeSimulator([])
        fixer = RetentionAutoFixer(llm_router=llm, simulator=sim, max_passes=1)
        result = fixer.fix(_plans(), _degraded())
        assert result.verdict == "no_improvement"
        assert result.applied is False
        assert "CTA" in result.rewrites[0]["reject_reason"]
        assert sim.calls == 0  # 거부됐으니 재시뮬레이션 안 함

    def test_too_short_rewrite_is_rejected(self) -> None:
        llm = _StubLLMRouter(narration="짧음")
        fixer = RetentionAutoFixer(llm_router=llm, simulator=_FakeSimulator([]), max_passes=1)
        result = fixer.fix(_plans(), _degraded())
        assert result.rewrites[0]["accepted"] is False
        assert "short" in result.rewrites[0]["reject_reason"]

    def test_non_korean_rewrite_is_rejected(self) -> None:
        llm = _StubLLMRouter(narration="this is an english narration with no hangul")
        fixer = RetentionAutoFixer(llm_router=llm, simulator=_FakeSimulator([]), max_passes=1)
        result = fixer.fix(_plans(), _degraded())
        assert result.rewrites[0]["accepted"] is False
        assert "Korean" in result.rewrites[0]["reject_reason"]

    def test_multipass_stops_when_verdict_recovers(self) -> None:
        llm = _StubLLMRouter(narration="개선된 중간 장면 나레이션을 충분히 길게 작성")
        # 첫 패스에서 0.40 -> 0.62 (pass) — 두 번째 패스는 돌지 않아야 한다.
        sim = _FakeSimulator([_sim(0.62, verdict="pass")])
        fixer = RetentionAutoFixer(llm_router=llm, simulator=sim, max_passes=3)
        result = fixer.fix(_plans(), _degraded(retention=0.40))
        assert result.verdict == "improved"
        assert sim.calls == 1  # 1패스만
        assert len(llm.calls) == 1

    def test_to_dict_is_json_safe(self) -> None:
        llm = _StubLLMRouter(narration="개선된 중간 장면 나레이션을 충분히 길게")
        sim = _FakeSimulator([_sim(0.7, verdict="pass")])
        fixer = RetentionAutoFixer(llm_router=llm, simulator=sim, max_passes=1)
        d = fixer.fix(_plans(), _degraded()).to_dict()
        assert set(d) >= {
            "applied",
            "applied_to_render",
            "passes",
            "before_retention",
            "after_retention",
            "rewrites",
            "verdict",
        }


# ── apply_to_plans: 재작성을 scene_plans 에 실제 반영 ───────────────


class TestApplyToPlans:
    def test_accepted_rewrite_is_applied(self) -> None:
        result = RetentionAutoFixResult(
            applied=True,
            verdict="improved",
            rewrites=[{"scene_id": 2, "after": "완전히 새로워진 중간 장면 나레이션", "accepted": True}],
        )
        updated = RetentionAutoFixer.apply_to_plans(_plans(), result)
        scene2 = next(p for p in updated if p.scene_id == 2)
        assert scene2.narration_ko == "완전히 새로워진 중간 장면 나레이션"
        # 다른 씬은 그대로
        assert next(p for p in updated if p.scene_id == 1).narration_ko == _plans()[0].narration_ko

    def test_rejected_rewrite_is_not_applied(self) -> None:
        result = RetentionAutoFixResult(
            verdict="no_improvement",
            rewrites=[{"scene_id": 2, "after": "거부된 나레이션", "accepted": False}],
        )
        updated = RetentionAutoFixer.apply_to_plans(_plans(), result)
        scene2 = next(p for p in updated if p.scene_id == 2)
        assert scene2.narration_ko == _plans()[1].narration_ko  # 원본 유지

    def test_no_rewrites_returns_copy_of_original(self) -> None:
        plans = _plans()
        updated = RetentionAutoFixer.apply_to_plans(plans, RetentionAutoFixResult())
        assert [p.narration_ko for p in updated] == [p.narration_ko for p in plans]
        assert updated is not plans  # 새 리스트

    def test_rewrite_for_unknown_scene_is_ignored(self) -> None:
        result = RetentionAutoFixResult(
            verdict="improved",
            rewrites=[{"scene_id": 999, "after": "유령 씬", "accepted": True}],
        )
        updated = RetentionAutoFixer.apply_to_plans(_plans(), result)
        assert [p.narration_ko for p in updated] == [p.narration_ko for p in _plans()]

    def test_malformed_rewrite_entries_are_skipped(self) -> None:
        result = RetentionAutoFixResult(
            verdict="improved",
            rewrites=[
                "not a dict",
                {"scene_id": 2, "accepted": True},  # after 누락
                {"scene_id": 3, "after": "새 마무리 나레이션", "accepted": True},
            ],
        )
        updated = RetentionAutoFixer.apply_to_plans(_plans(), result)
        assert next(p for p in updated if p.scene_id == 3).narration_ko == "새 마무리 나레이션"
        assert next(p for p in updated if p.scene_id == 2).narration_ko == _plans()[1].narration_ko


# ── NaN/Inf guard regression tests (RA-NI series) ────────────────────────────


class TestRetentionAutoFixNanInf:
    """RA-NI: NaN/Inf predicted_retention → before/after 유한값 보장."""

    def test_nan_predicted_retention_skipped_verdict_finite(self) -> None:
        """RA-NI001: verdict != degraded 이고 predicted_retention=NaN → before 유한."""
        import math

        sim = RetentionSimulationResult(predicted_retention=float("nan"), verdict="pass")
        fixer = RetentionAutoFixer(llm_router=None, simulator=None, max_passes=0)
        result = fixer.fix(_plans(), sim)
        assert result.verdict == "skipped"
        assert math.isfinite(result.before_retention)

    def test_inf_predicted_retention_returns_zero(self) -> None:
        """RA-NI002: predicted_retention=inf → before=0.0."""
        import math

        sim = RetentionSimulationResult(predicted_retention=float("inf"), verdict="pass")
        fixer = RetentionAutoFixer(llm_router=None, simulator=None, max_passes=0)
        result = fixer.fix(_plans(), sim)
        assert math.isfinite(result.before_retention)
        assert result.before_retention == 0.0

    def test_nan_retention_no_llm_router_error_path_finite(self) -> None:
        """RA-NI003: degraded + NaN retention + no llm_router → error verdict with finite before."""
        import math

        sim = RetentionSimulationResult(
            predicted_retention=float("nan"),
            verdict="degraded",
            weakest_scene_id=1,
        )
        fixer = RetentionAutoFixer(llm_router=None, simulator=None, max_passes=1)
        result = fixer.fix(_plans(), sim)
        assert result.verdict == "error"
        assert math.isfinite(result.before_retention)
