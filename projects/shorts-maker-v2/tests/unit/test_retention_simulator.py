"""Unit tests — RetentionSimulatorStep (합성 시청자 리텐션 시뮬레이션).

검증 범위:
  - 휴리스틱 엔진: LLM 없이도 항상 유효한 리텐션 곡선을 산출한다.
  - LLM 엔진: 정상 응답 파싱, 단조 비증가 강제, 누락 필드 보강.
  - 강등 경로: LLM 예외/비-dict 응답 시 휴리스틱으로 폴백한다.
  - 게이트 판정: 예측 리텐션 vs 임계값으로 pass/degraded 를 정한다.
"""

from __future__ import annotations

import pytest

from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.retention_simulator import (
    PERSONAS,
    RetentionSimulatorStep,
)


class _StubLLMRouter:
    """RetentionSimulatorStep 테스트용 generate_json stub."""

    def __init__(self, *, response=None, raise_exc=None):
        self.response = response
        self.raise_exc = raise_exc
        self.calls: list[dict] = []

    def generate_json(self, *, system_prompt, user_prompt, temperature=0.7):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
            }
        )
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.response


def _plans() -> list[ScenePlan]:
    return [
        ScenePlan(
            scene_id=1,
            narration_ko="놓치면 후회할 첫 단서가 여기 있다",
            visual_prompt_en="p1",
            target_sec=3.0,
            structure_role="hook",
        ),
        ScenePlan(
            scene_id=2,
            narration_ko="문제의 본질은 생각보다 가까운 곳에 있었다",
            visual_prompt_en="p2",
            target_sec=7.0,
            structure_role="problem",
        ),
        ScenePlan(
            scene_id=3,
            narration_ko="여기서 작은 반전이 시작된다",
            visual_prompt_en="p3",
            target_sec=8.0,
            structure_role="insight",
        ),
        ScenePlan(
            scene_id=4,
            narration_ko="조용한 여운으로 마무리",
            visual_prompt_en="p4",
            target_sec=4.0,
            structure_role="closing",
        ),
    ]


def _assets(durations: dict[int, float]) -> list[SceneAsset]:
    return [
        SceneAsset(
            scene_id=sid,
            audio_path=f"a{sid}.mp3",
            visual_type="video",
            visual_path=f"v{sid}.mp4",
            duration_sec=dur,
        )
        for sid, dur in durations.items()
    ]


# ── 휴리스틱 엔진 ───────────────────────────────────────────────────


class TestHeuristicEngine:
    def test_no_llm_router_uses_heuristic(self) -> None:
        step = RetentionSimulatorStep(llm_router=None, min_retention=0.5)
        result = step.run(_plans())
        assert result.source == "heuristic"
        assert result.verdict in {"pass", "degraded"}
        assert len(result.retention_curve) == 4

    def test_curve_is_monotonically_non_increasing(self) -> None:
        step = RetentionSimulatorStep(llm_router=None)
        result = step.run(_plans())
        remaining = [p["viewers_remaining"] for p in result.retention_curve]
        assert remaining == sorted(remaining, reverse=True)
        assert all(0.0 <= r <= 1.0 for r in remaining)

    def test_empty_plans_returns_error(self) -> None:
        step = RetentionSimulatorStep(llm_router=None)
        result = step.run([])
        assert result.verdict == "error"
        assert result.retention_curve == []

    def test_heuristic_produces_all_personas(self) -> None:
        step = RetentionSimulatorStep(llm_router=None)
        result = step.run(_plans())
        names = {p["name"] for p in result.persona_breakdown}
        assert names == {p.name for p in PERSONAS}

    def test_long_scene_drives_bigger_dropoff(self) -> None:
        """긴 씬은 휴리스틱에서 더 큰 이탈을 만들어야 한다."""
        short = RetentionSimulatorStep(llm_router=None).run(_plans())
        long_plans = _plans()
        long_assets = _assets({1: 3.0, 2: 7.0, 3: 20.0, 4: 4.0})
        longed = RetentionSimulatorStep(llm_router=None).run(long_plans, long_assets)
        assert longed.predicted_retention <= short.predicted_retention
        assert longed.weakest_scene_id == 3

    def test_scene_assets_duration_overrides_target(self) -> None:
        step = RetentionSimulatorStep(llm_router=None)
        assets = _assets({1: 3.0, 2: 3.0, 3: 3.0, 4: 3.0})
        result = step.run(_plans(), assets)
        assert len(result.retention_curve) == 4

    def test_rewrite_directive_non_empty(self) -> None:
        step = RetentionSimulatorStep(llm_router=None)
        result = step.run(_plans())
        assert result.rewrite_directive
        assert str(result.weakest_scene_id) in result.rewrite_directive


# ── LLM 엔진 ────────────────────────────────────────────────────────


class TestLLMEngine:
    def _good_response(self, final: float = 0.72) -> dict:
        return {
            "retention_curve": [
                {"scene_id": 1, "viewers_remaining": 0.95, "drop_reason": "hook ok"},
                {"scene_id": 2, "viewers_remaining": 0.85, "drop_reason": "slows down"},
                {"scene_id": 3, "viewers_remaining": 0.78, "drop_reason": "twist lands"},
                {"scene_id": 4, "viewers_remaining": final, "drop_reason": "ending"},
            ],
            "personas": [
                {"name": "scroller", "swiped_at_scene": 2, "note": "left early"},
                {"name": "completionist", "swiped_at_scene": None, "note": "watched all"},
            ],
            "predicted_retention": final,
            "loop_probability": 0.4,
            "weakest_scene_id": 2,
            "rewrite_directive": "Tighten scene 2.",
            "feedback": "Solid short.",
        }

    def test_llm_success_yields_llm_source(self) -> None:
        stub = _StubLLMRouter(response=self._good_response())
        step = RetentionSimulatorStep(llm_router=stub, min_retention=0.55)
        result = step.run(_plans())
        assert result.source == "llm"
        assert result.verdict == "pass"
        assert result.predicted_retention == pytest.approx(0.72)
        assert result.weakest_scene_id == 2
        assert len(stub.calls) == 1
        assert stub.calls[0]["temperature"] == 0.3

    def test_low_retention_yields_degraded(self) -> None:
        stub = _StubLLMRouter(response=self._good_response(final=0.30))
        step = RetentionSimulatorStep(llm_router=stub, min_retention=0.55)
        result = step.run(_plans())
        assert result.verdict == "degraded"
        assert result.predicted_retention == pytest.approx(0.30)

    def test_llm_exception_falls_back_to_heuristic(self) -> None:
        stub = _StubLLMRouter(raise_exc=RuntimeError("api down"))
        step = RetentionSimulatorStep(llm_router=stub)
        result = step.run(_plans())
        assert result.source == "heuristic"
        assert result.verdict in {"pass", "degraded"}
        assert len(result.retention_curve) == 4

    def test_llm_non_dict_falls_back_to_heuristic(self) -> None:
        stub = _StubLLMRouter(response="not json")
        step = RetentionSimulatorStep(llm_router=stub)
        result = step.run(_plans())
        assert result.source == "heuristic"

    def test_non_monotonic_curve_is_forced_non_increasing(self) -> None:
        """LLM 이 시청자가 늘어나는 곡선을 줘도 단조 비증가로 교정한다."""
        bad = self._good_response()
        bad["retention_curve"][2]["viewers_remaining"] = 0.99  # scene3 가 scene2 보다 큼
        stub = _StubLLMRouter(response=bad)
        step = RetentionSimulatorStep(llm_router=stub)
        result = step.run(_plans())
        remaining = [p["viewers_remaining"] for p in result.retention_curve]
        assert remaining == sorted(remaining, reverse=True)

    def test_invalid_weakest_scene_id_is_recomputed(self) -> None:
        bad = self._good_response()
        bad["weakest_scene_id"] = 999  # 존재하지 않는 씬
        stub = _StubLLMRouter(response=bad)
        step = RetentionSimulatorStep(llm_router=stub)
        result = step.run(_plans())
        assert result.weakest_scene_id in {1, 2, 3, 4}

    def test_missing_fields_are_backfilled(self) -> None:
        stub = _StubLLMRouter(response={"retention_curve": []})
        step = RetentionSimulatorStep(llm_router=stub)
        result = step.run(_plans())
        # 곡선이 비면 휴리스틱 곡선으로 보강된다.
        assert len(result.retention_curve) == 4
        assert result.rewrite_directive
        assert result.feedback

    def test_string_percent_retention_is_coerced(self) -> None:
        resp = self._good_response()
        resp["predicted_retention"] = "68%"
        stub = _StubLLMRouter(response=resp)
        step = RetentionSimulatorStep(llm_router=stub, min_retention=0.55)
        result = step.run(_plans())
        assert result.predicted_retention == pytest.approx(0.68)
        assert result.verdict == "pass"

    def test_curve_drops_out_of_range_scene_ids(self) -> None:
        resp = self._good_response()
        resp["retention_curve"].append({"scene_id": 99, "viewers_remaining": 0.5, "drop_reason": "ghost"})
        stub = _StubLLMRouter(response=resp)
        step = RetentionSimulatorStep(llm_router=stub)
        result = step.run(_plans())
        assert all(p["scene_id"] in {1, 2, 3, 4} for p in result.retention_curve)


# ── 게이트 판정 / 설정 ──────────────────────────────────────────────


class TestGateAndConfig:
    def test_min_retention_is_clamped(self) -> None:
        step_hi = RetentionSimulatorStep(llm_router=None, min_retention=5.0)
        step_lo = RetentionSimulatorStep(llm_router=None, min_retention=-1.0)
        assert step_hi.min_retention == 1.0
        assert step_lo.min_retention == 0.0

    def test_first_dropoff_scene_id_detected(self) -> None:
        resp = {
            "retention_curve": [
                {"scene_id": 1, "viewers_remaining": 0.9, "drop_reason": "ok"},
                {"scene_id": 2, "viewers_remaining": 0.6, "drop_reason": "drop"},
                {"scene_id": 3, "viewers_remaining": 0.55, "drop_reason": "ok"},
                {"scene_id": 4, "viewers_remaining": 0.5, "drop_reason": "ok"},
            ],
            "predicted_retention": 0.5,
        }
        stub = _StubLLMRouter(response=resp)
        step = RetentionSimulatorStep(llm_router=stub)
        result = step.run(_plans())
        assert result.first_dropoff_scene_id == 2

    def test_to_dict_is_json_safe(self) -> None:
        step = RetentionSimulatorStep(llm_router=None)
        d = step.run(_plans()).to_dict()
        assert set(d) >= {
            "predicted_retention",
            "loop_probability",
            "retention_curve",
            "persona_breakdown",
            "verdict",
            "source",
        }
