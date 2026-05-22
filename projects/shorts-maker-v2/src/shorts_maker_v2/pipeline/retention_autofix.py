"""Retention Auto-Fix — 리텐션 자가 치유(closed-loop).

`RetentionSimulatorStep` 이 합성 시청자 시뮬레이션으로 "이 영상은 약하다
(verdict=degraded)" 고 판정했을 때, 이 모듈이 폐루프를 닫는다:

  1. 시뮬레이션이 지목한 가장 약한 씬을 가져온다.
  2. `rewrite_directive` 와 앞뒤 씬 맥락을 LLM 에 주고 나레이션을 재작성한다.
  3. 재작성본이 채널 철학(CTA 금지 등)을 어기지 않는지 검증한다.
  4. 재작성본으로 *다시 시뮬레이션*해서 예측 리텐션이 실제로 올라가는지 본다.
  5. 개선이 확인된 재작성만 채택한다. 아니면 원본을 유지한다.

즉 "합성 관객이 약점을 지목 → AI 가 고치고 → 합성 관객이 개선을 재확인"
하는 자가 치유 루프다. 일반 Shorts 툴에 없는 구조다.

**중요**: 이 단계는 현재 렌더 입력을 바꾸지 않는다. 시뮬레이션은 TTS/미디어
생성 *후* 에 돌기 때문에, 나레이션을 갈아끼우면 이미 만든 오디오와 desync
된다. 검증된 재작성본은 `manifest.retention_autofix` 에 기록되어 다음
이터레이션·시리즈 후속편에 반영된다 (advisory closed-loop).
"""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from typing import Any

from shorts_maker_v2.models import (
    RetentionAutoFixResult,
    RetentionSimulationResult,
    SceneAsset,
    ScenePlan,
)
from shorts_maker_v2.pipeline.retention_simulator import RetentionSimulatorStep

logger = logging.getLogger(__name__)

# 채널 철학상 금지 — CTA / 행동 강요 어휘. script_step 의 정책과 동일선상.
_CTA_FORBIDDEN = (
    "구독",
    "좋아요",
    "댓글",
    "팔로우",
    "알림 설정",
    "공유",
    "클릭",
    "subscribe",
    "like",
    "comment",
)
_HANGUL_RE = re.compile(r"[가-힣]")
_MIN_NARRATION_LEN = 5
_MAX_NARRATION_LEN = 200


class RetentionAutoFixer:
    """리텐션 자가 치유 1회 실행 (최대 N 패스)."""

    _SYSTEM_PROMPT = (
        "You are a YouTube Shorts script doctor. A synthetic-audience "
        "simulation flagged ONE scene as the biggest retention drop. "
        "Rewrite ONLY that scene's Korean narration so viewers keep "
        "watching, while preserving the scene's role in the story and "
        "staying coherent with the surrounding scenes.\n\n"
        "The channel philosophy is 'quiet storytelling — stealing the "
        "viewer's time'. STRICT rules:\n"
        "  - No CTAs, no hype, no action demands (no '구독', '좋아요', "
        "'댓글', '팔로우', '공유').\n"
        "  - Keep a calm narrator voice; do not shout.\n"
        "  - Korean narration, roughly the same length as the original "
        "(it must fit the same scene duration).\n"
        "  - Strengthen the hook / curiosity gap / connective tissue as "
        "the directive asks.\n\n"
        "Output ONLY valid JSON:\n"
        '{"narration_ko": "<rewritten Korean narration>", '
        '"rationale": "<one short line on what you changed>"}'
    )

    def __init__(
        self,
        llm_router: Any,
        simulator: RetentionSimulatorStep,
        max_passes: int = 1,
    ):
        self.llm_router = llm_router
        self.simulator = simulator
        self.max_passes = max(0, int(max_passes))

    # ── public API ──────────────────────────────────────────────
    def fix(
        self,
        scene_plans: list[ScenePlan],
        simulation: RetentionSimulationResult,
        scene_assets: list[SceneAsset] | None = None,
        structure_outline: Any | None = None,
    ) -> RetentionAutoFixResult:
        """약한 씬을 재작성하고 재시뮬레이션으로 개선을 검증한다.

        시뮬레이션 verdict 가 ``degraded`` 가 아니거나 max_passes 가 0 이면
        아무것도 하지 않고 ``verdict="skipped"`` 를 반환한다.
        """
        before = float(simulation.predicted_retention)
        if simulation.verdict != "degraded" or self.max_passes == 0:
            return RetentionAutoFixResult(
                applied=False,
                before_retention=before,
                after_retention=before,
                verdict="skipped",
                feedback=(
                    "시뮬레이션 verdict 가 degraded 가 아니라 자가 치유 불필요"
                    if simulation.verdict != "degraded"
                    else "retention_autofix_max_passes=0 — 자가 치유 비활성"
                ),
            )
        if not scene_plans:
            return RetentionAutoFixResult(
                verdict="error",
                feedback="No scene_plans provided",
                before_retention=before,
            )
        if self.llm_router is None:
            return RetentionAutoFixResult(
                verdict="error",
                feedback="No llm_router — 자가 치유는 LLM 재작성이 필수",
                before_retention=before,
            )

        current_plans = list(scene_plans)
        current_sim = simulation
        rewrites: list[dict[str, Any]] = []

        for pass_idx in range(self.max_passes):
            weak_id = current_sim.weakest_scene_id
            weak_scene = next((p for p in current_plans if p.scene_id == weak_id), None)
            if weak_scene is None:
                logger.info("[RetentionAutoFix] no weakest scene to fix — stop")
                break

            rewritten = self._llm_rewrite(weak_scene, current_plans, current_sim.rewrite_directive, structure_outline)
            if rewritten is None:
                if not rewrites:  # 첫 패스부터 실패
                    return RetentionAutoFixResult(
                        verdict="error",
                        feedback="LLM 재작성 호출 실패",
                        before_retention=before,
                        after_retention=current_sim.predicted_retention,
                    )
                break

            reject_reason = self._validate_narration(rewritten)
            if reject_reason:
                rewrites.append(
                    {
                        "scene_id": weak_scene.scene_id,
                        "role": weak_scene.structure_role,
                        "before": weak_scene.narration_ko,
                        "after": rewritten,
                        "accepted": False,
                        "projected_retention": round(current_sim.predicted_retention, 3),
                        "reject_reason": reject_reason,
                    }
                )
                logger.info("[RetentionAutoFix] rewrite rejected: %s", reject_reason)
                break

            candidate_plans = [
                replace(p, narration_ko=rewritten) if p.scene_id == weak_scene.scene_id else p for p in current_plans
            ]
            candidate_sim = self.simulator.run(
                scene_plans=candidate_plans,
                scene_assets=scene_assets,
                structure_outline=structure_outline,
            )
            accepted = candidate_sim.predicted_retention > current_sim.predicted_retention
            rewrites.append(
                {
                    "scene_id": weak_scene.scene_id,
                    "role": weak_scene.structure_role,
                    "before": weak_scene.narration_ko,
                    "after": rewritten,
                    "accepted": accepted,
                    "projected_retention": round(candidate_sim.predicted_retention, 3),
                }
            )
            logger.info(
                "[RetentionAutoFix] pass=%d scene=%d %.3f -> %.3f accepted=%s",
                pass_idx + 1,
                weak_scene.scene_id,
                current_sim.predicted_retention,
                candidate_sim.predicted_retention,
                accepted,
            )
            if not accepted:
                break  # 개선 없음 — 원본 유지하고 종료
            current_plans = candidate_plans
            current_sim = candidate_sim
            if current_sim.verdict != "degraded":
                break  # 임계값 회복 — 종료

        accepted_count = sum(1 for r in rewrites if r.get("accepted"))
        after = float(current_sim.predicted_retention)
        if accepted_count > 0:
            verdict = "improved"
            feedback = f"{accepted_count}개 씬 재작성 채택, 예측 리텐션 {before:.0%} → {after:.0%}"
        elif rewrites:
            verdict = "no_improvement"
            feedback = "재작성을 시도했으나 예측 리텐션 개선 실패 — 원본 유지"
        else:
            verdict = "skipped"
            feedback = "재작성할 약한 씬을 찾지 못함"

        return RetentionAutoFixResult(
            applied=accepted_count > 0,
            passes=accepted_count,
            before_retention=round(before, 3),
            after_retention=round(after, 3),
            rewrites=rewrites,
            verdict=verdict,
            feedback=feedback,
            source="llm",
        )

    @staticmethod
    def apply_to_plans(
        scene_plans: list[ScenePlan],
        result: RetentionAutoFixResult,
    ) -> list[ScenePlan]:
        """채택된(accepted) 재작성을 scene_plans 에 반영한 새 리스트를 반환.

        pre-asset 스테이지에서 호출 — 개선된 나레이션이 그대로 TTS·렌더로
        흘러가 진짜 closed-loop 가 된다. 채택된 재작성이 없으면 원본 사본을
        그대로 돌려준다 (입력을 변형하지 않는다).
        """
        accepted = {
            r["scene_id"]: r["after"]
            for r in result.rewrites
            if isinstance(r, dict)
            and r.get("accepted")
            and isinstance(r.get("after"), str)
            and r.get("scene_id") is not None
        }
        if not accepted:
            return list(scene_plans)
        return [replace(p, narration_ko=accepted[p.scene_id]) if p.scene_id in accepted else p for p in scene_plans]

    # ── LLM 재작성 ───────────────────────────────────────────────
    def _llm_rewrite(
        self,
        weak_scene: ScenePlan,
        scene_plans: list[ScenePlan],
        directive: str,
        structure_outline: Any | None,
    ) -> str | None:
        """약한 씬 1개의 나레이션 재작성. 실패 시 None."""
        user_prompt = self._build_rewrite_prompt(weak_scene, scene_plans, directive)
        try:
            response = self.llm_router.generate_json(
                system_prompt=self._SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.7,
            )
        except Exception as exc:
            logger.warning("[RetentionAutoFix] LLM rewrite failed: %s", exc)
            return None
        if not isinstance(response, dict):
            logger.warning("[RetentionAutoFix] LLM returned non-dict: %s", type(response).__name__)
            return None
        narration = response.get("narration_ko")
        if not isinstance(narration, str):
            return None
        return narration.strip()

    @staticmethod
    def _build_rewrite_prompt(
        weak_scene: ScenePlan,
        scene_plans: list[ScenePlan],
        directive: str,
    ) -> str:
        idx = next(
            (i for i, p in enumerate(scene_plans) if p.scene_id == weak_scene.scene_id),
            None,
        )
        lines = ["=== FULL SHORT (for context) ==="]
        for i, plan in enumerate(scene_plans):
            marker = "  <-- REWRITE THIS SCENE" if i == idx else ""
            lines.append(f"Scene {plan.scene_id} [{plan.structure_role}]: {plan.narration_ko!r}{marker}")
        lines.append("")
        lines.append(
            f"=== WEAK SCENE === Scene {weak_scene.scene_id} "
            f"[{weak_scene.structure_role}], "
            f"target {weak_scene.target_sec:.1f}s"
        )
        lines.append(f"Original narration: {weak_scene.narration_ko!r}")
        lines.append("")
        lines.append(f"=== DIRECTIVE === {directive or '(none — improve retention)'}")
        lines.append("")
        lines.append("Rewrite ONLY the weak scene's narration_ko. Output JSON only.")
        return "\n".join(lines)

    # ── 검증 ─────────────────────────────────────────────────────
    @staticmethod
    def _validate_narration(text: str) -> str | None:
        """재작성 나레이션 검증. 통과하면 None, 실패하면 사유 문자열."""
        stripped = (text or "").strip()
        if len(stripped) < _MIN_NARRATION_LEN:
            return f"too short ({len(stripped)} chars)"
        if len(stripped) > _MAX_NARRATION_LEN:
            return f"too long ({len(stripped)} chars)"
        if not _HANGUL_RE.search(stripped):
            return "no Korean characters"
        lowered = stripped.lower()
        for word in _CTA_FORBIDDEN:
            if word.lower() in lowered:
                return f"contains forbidden CTA term: {word}"
        return None
