"""Retention Simulator — 합성 시청자(Synthetic Audience) 리텐션 시뮬레이션.

기존 `retention_hints.py` 가 씬 길이만 보고 휴리스틱 점수를 매기고,
`SemanticQCStep` 이 씬-씬 연결성/톤을 채점하는 데 반해, 이 모듈은 한 단계
더 나아가 *실제 시청자가 초 단위로 계속 볼지 스와이프할지를 시뮬레이션*한다.

핵심 아이디어 (agent-based modeling):
  - 서로 다른 5명의 시청자 페르소나를 정의한다.
  - LLM 이 각 페르소나가 되어 씬 경계마다 "이탈 / 잔류"를 판단한다.
  - 그 집계가 곧 예측 리텐션 곡선이며, 어느 씬에서 *왜* 이탈이
    발생하는지를 페르소나 단위로 설명한다.
  - 가장 약한 씬과 실행 가능한 재작성 지시를 함께 산출한다.

이 단계는 렌더 *직전* 게이트로 동작한다 — 비싼 렌더링에 들어가기 전에
약한 콘텐츠를 `degraded_steps` 로 표면화한다. LLM 호출이 실패하면
결정론적 휴리스틱 엔진으로 우아하게 강등(`source="heuristic"`)되며,
영상 ship 자체를 막지는 않는다 (opt-in 기능).
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Any

from shorts_maker_v2.models import RetentionSimulationResult, SceneAsset, ScenePlan

logger = logging.getLogger(__name__)


# ── 합성 시청자 페르소나 ────────────────────────────────────────────
# 각 페르소나는 이탈 민감도(impatience)와 무엇에 반응하는지가 다르다.
@dataclass(frozen=True)
class _Persona:
    name: str
    label_ko: str
    impatience: float  # 0..1 — 높을수록 빨리 이탈
    description: str


PERSONAS: tuple[_Persona, ...] = (
    _Persona(
        "scroller",
        "성급한 스크롤러",
        0.85,
        "첫 3초 안에 흥미가 없으면 즉시 스와이프한다. 빠른 결론을 원한다.",
    ),
    _Persona(
        "learner",
        "지식 추구자",
        0.35,
        "정보 가치가 있으면 끝까지 본다. 내용이 얕거나 반복되면 이탈한다.",
    ),
    _Persona(
        "skeptic",
        "회의적 시청자",
        0.55,
        "과장·낚시·CTA 강요를 감지하면 신뢰를 잃고 이탈한다.",
    ),
    _Persona(
        "multitasker",
        "멀티태스커",
        0.6,
        "씬 전환이 매끄럽지 않거나 흐름이 끊기면 주의를 잃고 이탈한다.",
    ),
    _Persona(
        "completionist",
        "완주 지향자",
        0.2,
        "웬만하면 끝까지 본다. 마지막 씬의 여운으로 재시청 여부를 결정한다.",
    ),
)


# ── 휴리스틱 상수 ───────────────────────────────────────────────────
_IDEAL_SCENE_SEC = 6.0  # 씬당 이상적 길이
_LONG_SCENE_SEC = 9.0  # 이 이상이면 이탈 위험
_BASE_DECAY = 0.05  # 씬당 기본 이탈률
_HOOK_LONG_SEC = 5.0  # hook 이 이 이상이면 초반 이탈 가속


@dataclass(frozen=True)
class _SceneView:
    """시뮬레이션 입력용 경량 씬 DTO."""

    scene_id: int
    role: str
    duration_sec: float
    narration: str

    @property
    def narration_len(self) -> int:
        return len(self.narration)


class RetentionSimulatorStep:
    """합성 시청자 리텐션 시뮬레이션 1회 실행.

    LLM judge 한 번을 호출해 5개 페르소나의 초 단위 이탈 판단을 받아
    예측 리텐션 곡선을 만든다. LLM 실패는 raise 하지 않고 휴리스틱
    엔진으로 강등한다.
    """

    _SYSTEM_PROMPT = (
        "You are a synthetic-audience simulator for YouTube Shorts. "
        "You will be given a short's full scene-by-scene narration with each "
        "scene's duration and structure role. Simulate how FIVE distinct "
        "viewer personas watch it second by second, deciding at every scene "
        "boundary whether to keep watching or swipe away.\n\n"
        "PERSONAS:\n" + "\n".join(f"  - {p.name}: {p.description}" for p in PERSONAS) + "\n\n"
        "The channel philosophy is 'quiet storytelling — stealing the "
        "viewer's time'. Penalise CTAs, hype, and action demands; reward a "
        "hook that creates a curiosity gap and a closing scene that leaves a "
        "lingering thought (which drives re-watches / looping).\n\n"
        "For each scene compute `viewers_remaining` — the fraction (0.0-1.0) "
        "of the synthetic audience still watching at the END of that scene. "
        "It must be monotonically NON-INCREASING across scenes.\n\n"
        "Output ONLY valid JSON:\n"
        "{\n"
        '  "retention_curve": [\n'
        '    {"scene_id": <int>, "viewers_remaining": <0.0-1.0>, '
        '"drop_reason": "<short, why viewers left here>"}\n'
        "  ],\n"
        '  "personas": [\n'
        '    {"name": "<persona>", "swiped_at_scene": <scene_id or null>, '
        '"note": "<short>"}\n'
        "  ],\n"
        '  "predicted_retention": <0.0-1.0, audience left at the last scene>,\n'
        '  "loop_probability": <0.0-1.0, chance a viewer re-watches>,\n'
        '  "weakest_scene_id": <scene_id with the biggest single drop>,\n'
        '  "rewrite_directive": "<one concrete instruction to fix that scene>",\n'
        '  "feedback": "<one-line summary>"\n'
        "}"
    )

    def __init__(self, llm_router: Any, min_retention: float = 0.55):
        self.llm_router = llm_router
        # 0..1 로 클램프 — 비정상 설정 방어
        self.min_retention = max(0.0, min(1.0, float(min_retention)))

    # ── public API ──────────────────────────────────────────────
    def run(
        self,
        scene_plans: list[ScenePlan],
        scene_assets: list[SceneAsset] | None = None,
        structure_outline: Any | None = None,
    ) -> RetentionSimulationResult:
        """리텐션 시뮬레이션 1회. 입력이 없을 때만 verdict='error'."""
        scenes = self._build_scene_views(scene_plans, scene_assets)
        if not scenes:
            return RetentionSimulationResult(
                verdict="error",
                source="heuristic",
                feedback="No scene_plans provided",
            )

        # 1) 결정론적 휴리스틱 baseline — 항상 성공한다.
        result = self._heuristic_simulate(scenes)

        # 2) LLM 시뮬레이션 시도. 성공 시 baseline 을 대체한다.
        if self.llm_router is not None:
            llm_result = self._llm_simulate(scenes, structure_outline)
            if llm_result is not None:
                result = llm_result

        # 3) verdict 판정 — predicted_retention 기준.
        result.verdict = "pass" if result.predicted_retention >= self.min_retention else "degraded"

        logger.info(
            "[RetentionSim] source=%s predicted=%.3f loop=%.3f weakest=%s verdict=%s",
            result.source,
            result.predicted_retention,
            result.loop_probability,
            result.weakest_scene_id,
            result.verdict,
        )
        return result

    # ── 입력 정규화 ──────────────────────────────────────────────
    @staticmethod
    def _build_scene_views(
        scene_plans: list[ScenePlan],
        scene_assets: list[SceneAsset] | None,
    ) -> list[_SceneView]:
        """ScenePlan + (선택) SceneAsset 을 씬 뷰 리스트로 병합.

        실제 길이는 SceneAsset.duration_sec 을 우선하고, 없으면 ScenePlan
        의 target_sec 으로 폴백한다.
        """
        if not scene_plans:
            return []
        dur_by_id: dict[int, float] = {}
        for asset in scene_assets or []:
            with contextlib.suppress(AttributeError, TypeError):
                dur_by_id[asset.scene_id] = float(asset.duration_sec)

        views: list[_SceneView] = []
        for plan in scene_plans:
            duration = dur_by_id.get(plan.scene_id)
            if duration is None or duration <= 0:
                with contextlib.suppress(AttributeError, TypeError, ValueError):
                    duration = float(plan.target_sec)
            if duration is None or duration <= 0:
                duration = _IDEAL_SCENE_SEC
            views.append(
                _SceneView(
                    scene_id=plan.scene_id,
                    role=str(plan.structure_role or "body"),
                    duration_sec=duration,
                    narration=str(plan.narration_ko or ""),
                )
            )
        return views

    # ── 휴리스틱 엔진 (LLM 폴백) ─────────────────────────────────
    @classmethod
    def _heuristic_simulate(cls, scenes: list[_SceneView]) -> RetentionSimulationResult:
        """결정론적 리텐션 곡선 추정.

        씬마다 잔류 시청자 비율을 감쇠시킨다. 감쇠율은 ① 씬 길이가
        이상 구간을 벗어난 정도, ② 씬 역할(hook/cta 등), ③ 기본 이탈률
        의 합으로 정해진다. LLM 이 없거나 실패할 때의 안전망이다.
        """
        curve: list[dict[str, Any]] = []
        remaining = 1.0
        drops: list[tuple[int, float]] = []  # (scene_id, drop)
        durations = [s.duration_sec for s in scenes]
        uniform = cls._is_uniform(durations)

        for idx, scene in enumerate(scenes):
            drop, reason = cls._heuristic_scene_drop(scene, idx, len(scenes), uniform)
            prev = remaining
            remaining = max(0.0, remaining - drop)
            actual_drop = prev - remaining
            drops.append((scene.scene_id, actual_drop))
            curve.append(
                {
                    "scene_id": scene.scene_id,
                    "role": scene.role,
                    "viewers_remaining": round(remaining, 3),
                    "drop_reason": reason,
                }
            )

        predicted = round(remaining, 3)
        loop = cls._heuristic_loop(scenes)
        weakest_id = max(drops, key=lambda d: d[1])[0] if drops else None
        first_drop = cls._first_dropoff(curve)
        weakest_scene = next((s for s in scenes if s.scene_id == weakest_id), None)

        return RetentionSimulationResult(
            predicted_retention=predicted,
            loop_probability=loop,
            retention_curve=curve,
            persona_breakdown=cls._heuristic_personas(scenes, curve),
            first_dropoff_scene_id=first_drop,
            weakest_scene_id=weakest_id,
            rewrite_directive=cls._rewrite_directive(weakest_scene),
            verdict="pass",
            feedback=(f"휴리스틱 추정: 예측 리텐션 {predicted:.0%}, 루핑 확률 {loop:.0%}"),
            source="heuristic",
        )

    @staticmethod
    def _is_uniform(durations: list[float]) -> bool:
        """씬 길이가 지나치게 균일하면(단조로움) True."""
        if len(durations) < 3:
            return False
        avg = sum(durations) / len(durations)
        variance = sum((d - avg) ** 2 for d in durations) / len(durations)
        return variance < 1.0

    @staticmethod
    def _heuristic_scene_drop(
        scene: _SceneView,
        idx: int,
        total: int,
        uniform: bool,
    ) -> tuple[float, str]:
        """단일 씬의 이탈률과 사유를 계산."""
        drop = _BASE_DECAY
        reasons: list[str] = []
        is_first = idx == 0
        is_last = idx == total - 1

        # 길이 페널티
        if scene.duration_sec > _LONG_SCENE_SEC:
            over = scene.duration_sec - _LONG_SCENE_SEC
            drop += min(0.18, 0.03 * over)
            reasons.append(f"{scene.duration_sec:.0f}초로 길어 지루함")
        elif scene.duration_sec < 2.0:
            drop += 0.05
            reasons.append("너무 짧아 내용 전달 부족")

        # hook 페널티 — 초반 hook 이 길면 스크롤러가 대거 이탈
        if scene.role == "hook" and scene.duration_sec > _HOOK_LONG_SEC:
            drop += 0.12
            reasons.append("hook 이 길어 초반 이탈 가속")

        # cta 페널티 — 채널 철학상 CTA 는 회의적 시청자 이탈 유발
        if scene.role == "cta":
            drop += 0.07
            reasons.append("CTA 가 몰입을 끊음")

        # 내용 빈약 — 나레이션이 매우 짧은 body 씬
        if scene.role in {"body", "problem", "insight"} and scene.narration_len < 12:
            drop += 0.06
            reasons.append("나레이션이 빈약함")

        # 단조로움 — 길이 변주 부족
        if uniform and not is_first:
            drop += 0.02
            reasons.append("씬 리듬이 단조로움")

        # 마지막 씬은 이미 본 사람이라 이탈이 거의 없음
        if is_last:
            drop = min(drop, _BASE_DECAY)
            reasons = ["마무리 씬 — 정상 이탈"]

        if not reasons:
            reasons.append("정상 이탈")
        return min(drop, 0.45), "; ".join(reasons)

    @staticmethod
    def _heuristic_loop(scenes: list[_SceneView]) -> float:
        """루핑(재시청) 확률 추정. 마지막 씬이 짧고 여운형이면 높다."""
        if not scenes:
            return 0.0
        score = 0.3
        last = scenes[-1]
        first = scenes[0]
        if last.duration_sec <= 4.0:
            score += 0.2
        if last.role in {"closing", "body"}:
            score += 0.15
        if last.role == "cta":
            score -= 0.1
        if first.narration_len > 0 and last.narration_len > 0:
            ratio = min(first.narration_len, last.narration_len) / max(first.narration_len, last.narration_len)
            if ratio > 0.6:
                score += 0.1
        return round(max(0.0, min(1.0, score)), 3)

    @staticmethod
    def _heuristic_personas(
        scenes: list[_SceneView],
        curve: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """페르소나별 이탈 씬 추정 — 곡선과 페르소나 민감도를 교차."""
        breakdown: list[dict[str, Any]] = []
        for persona in PERSONAS:
            # 잔류율이 (1 - impatience) 밑으로 처음 떨어지는 씬에서 이탈한다고 본다.
            threshold = 1.0 - persona.impatience
            swiped_at: int | None = None
            for point in curve:
                if point["viewers_remaining"] < threshold:
                    swiped_at = point["scene_id"]
                    break
            note = "끝까지 시청" if swiped_at is None else f"씬 {swiped_at}에서 이탈 추정"
            breakdown.append({"name": persona.name, "swiped_at_scene": swiped_at, "note": note})
        return breakdown

    @staticmethod
    def _first_dropoff(curve: list[dict[str, Any]], threshold: float = 0.7) -> int | None:
        """잔류율이 임계치 밑으로 처음 떨어지는 씬 id."""
        for point in curve:
            if point["viewers_remaining"] < threshold:
                return point["scene_id"]
        return None

    @staticmethod
    def _rewrite_directive(scene: _SceneView | None) -> str:
        """가장 약한 씬에 대한 실행 가능한 재작성 지시 생성."""
        if scene is None:
            return ""
        role = scene.role
        if role == "hook":
            return (
                f"씬 {scene.scene_id}(hook): 첫 문장에 호기심 격차(curiosity gap)를 "
                "만들고 3초 이내로 압축해 스크롤러 이탈을 막을 것."
            )
        if role == "cta":
            return f"씬 {scene.scene_id}(cta): 행동 강요 대신 여운을 남기는 마무리로 바꿔 회의적 시청자 이탈을 줄일 것."
        if scene.duration_sec > _LONG_SCENE_SEC:
            return f"씬 {scene.scene_id}: {scene.duration_sec:.0f}초로 길다 — 핵심만 남기고 6초 안팎으로 압축할 것."
        return (
            f"씬 {scene.scene_id}({role}): 다음 씬으로의 연결을 강화하고 "
            "나레이션에 구체적 디테일을 더해 몰입을 유지할 것."
        )

    # ── LLM 엔진 ─────────────────────────────────────────────────
    def _llm_simulate(
        self,
        scenes: list[_SceneView],
        structure_outline: Any | None,
    ) -> RetentionSimulationResult | None:
        """LLM 시뮬레이션 1회. 실패하면 None 을 반환해 휴리스틱으로 폴백."""
        user_prompt = self._build_user_prompt(scenes, structure_outline)
        try:
            response = self.llm_router.generate_json(
                system_prompt=self._SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
            )
        except Exception as exc:
            logger.warning("[RetentionSim] LLM call failed, falling back: %s", exc)
            return None

        if not isinstance(response, dict):
            logger.warning(
                "[RetentionSim] LLM returned non-dict (%s), falling back",
                type(response).__name__,
            )
            return None

        return self._parse_llm_response(response, scenes)

    @classmethod
    def _parse_llm_response(
        cls,
        response: dict[str, Any],
        scenes: list[_SceneView],
    ) -> RetentionSimulationResult:
        """LLM 응답을 견고하게 파싱. 누락 필드는 휴리스틱 값으로 보강."""
        valid_ids = {s.scene_id for s in scenes}
        role_by_id = {s.scene_id: s.role for s in scenes}

        # 리텐션 곡선 — 단조 비증가로 강제.
        curve: list[dict[str, Any]] = []
        raw_curve = response.get("retention_curve", [])
        prev_remaining = 1.0
        if isinstance(raw_curve, list):
            for item in raw_curve[: len(scenes) + 5]:
                if not isinstance(item, dict):
                    continue
                sid = cls._coerce_int(item.get("scene_id"))
                if sid not in valid_ids:
                    continue
                remaining = cls._coerce_float(item.get("viewers_remaining"), default=prev_remaining)
                remaining = min(remaining, prev_remaining)  # 시청자는 늘어날 수 없다
                prev_remaining = remaining
                curve.append(
                    {
                        "scene_id": sid,
                        "role": role_by_id.get(sid, "body"),
                        "viewers_remaining": round(remaining, 3),
                        "drop_reason": str(item.get("drop_reason", ""))[:200],
                    }
                )

        # 곡선이 비었으면 휴리스틱 곡선으로 대체.
        heuristic = cls._heuristic_simulate(scenes)
        if not curve:
            curve = heuristic.retention_curve

        # predicted_retention — 명시값 우선, 없으면 곡선 마지막 점.
        predicted = response.get("predicted_retention")
        if predicted is None and curve:
            predicted = curve[-1]["viewers_remaining"]
        predicted = cls._coerce_float(predicted, default=heuristic.predicted_retention)
        predicted = max(0.0, min(1.0, predicted))

        loop = cls._coerce_float(response.get("loop_probability"), default=heuristic.loop_probability)
        loop = max(0.0, min(1.0, loop))

        # 페르소나 분해.
        personas: list[dict[str, Any]] = []
        raw_personas = response.get("personas", [])
        if isinstance(raw_personas, list):
            for item in raw_personas[:10]:
                if not isinstance(item, dict):
                    continue
                swiped = item.get("swiped_at_scene")
                swiped_id = cls._coerce_int(swiped) if swiped is not None else None
                if swiped_id is not None and swiped_id not in valid_ids:
                    swiped_id = None
                personas.append(
                    {
                        "name": str(item.get("name", "unknown"))[:40],
                        "swiped_at_scene": swiped_id,
                        "note": str(item.get("note", ""))[:200],
                    }
                )
        if not personas:
            personas = heuristic.persona_breakdown

        # weakest scene — 명시값 검증, 없으면 곡선 최대 낙폭으로 산출.
        weakest = cls._coerce_int(response.get("weakest_scene_id"), default=0)
        if weakest not in valid_ids:
            weakest = cls._weakest_from_curve(curve) or heuristic.weakest_scene_id

        directive = str(response.get("rewrite_directive", "")).strip()[:400]
        if not directive:
            weakest_scene = next((s for s in scenes if s.scene_id == weakest), None)
            directive = cls._rewrite_directive(weakest_scene)

        feedback = str(response.get("feedback", "")).strip()[:300]
        if not feedback:
            feedback = f"LLM 시뮬레이션: 예측 리텐션 {predicted:.0%}"

        return RetentionSimulationResult(
            predicted_retention=round(predicted, 3),
            loop_probability=round(loop, 3),
            retention_curve=curve,
            persona_breakdown=personas,
            first_dropoff_scene_id=cls._first_dropoff(curve),
            weakest_scene_id=weakest,
            rewrite_directive=directive,
            verdict="pass",  # run() 에서 최종 판정
            feedback=feedback,
            source="llm",
            raw_response=str(response)[:1000],
        )

    @staticmethod
    def _weakest_from_curve(curve: list[dict[str, Any]]) -> int | None:
        """리텐션 곡선에서 단일 낙폭이 가장 큰 씬 id."""
        weakest: int | None = None
        max_drop = -1.0
        prev = 1.0
        for point in curve:
            drop = prev - point["viewers_remaining"]
            if drop > max_drop:
                max_drop = drop
                weakest = point["scene_id"]
            prev = point["viewers_remaining"]
        return weakest

    @staticmethod
    def _build_user_prompt(
        scenes: list[_SceneView],
        structure_outline: Any | None,
    ) -> str:
        lines = ["=== SHORT — SCENE BY SCENE ==="]
        for s in scenes:
            lines.append(f"Scene {s.scene_id} [{s.role}] ({s.duration_sec:.1f}s): {s.narration!r}")
        outline_scenes = getattr(structure_outline, "scenes", None)
        if outline_scenes:
            lines.append("")
            lines.append("=== INTENDED STRUCTURE ===")
            for sc in outline_scenes:
                intent = getattr(sc, "intent", "")
                beat = getattr(sc, "emotional_beat", "")
                lines.append(
                    f"Scene {getattr(sc, 'scene_id', '?')} "
                    f"[{getattr(sc, 'role', '?')}]: intent={intent!r} beat={beat!r}"
                )
        lines.append("")
        lines.append("Simulate the 5 personas now. Output JSON only.")
        return "\n".join(lines)

    # ── 안전한 타입 강제 ─────────────────────────────────────────
    @staticmethod
    def _coerce_int(value: Any, *, default: int = 0) -> int:
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            with contextlib.suppress(ValueError):
                return int(float(value))
        return default

    @staticmethod
    def _coerce_float(value: Any, *, default: float = 0.0) -> float:
        """float 로 강제. `"68%"` 같은 퍼센트 문자열은 0.68 로 환산한다."""
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            s = value.strip()
            is_percent = s.endswith("%")
            s = s.rstrip("%").strip()
            with contextlib.suppress(ValueError):
                num = float(s)
                return num / 100.0 if is_percent else num
        return default
