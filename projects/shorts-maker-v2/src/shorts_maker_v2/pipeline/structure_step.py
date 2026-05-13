"""StructureStep — Gate 2: 씬별 구성안 생성 + 검증.

대본 작성 전에 씬별 의도·비주얼 방향·감정 박자를 먼저 설계한다.
"무슨 이야기를 할지"만 정하고 "어떻게 말할지"는 ScriptStep에서 결정.

Gate 2 검증:
  - 마지막 씬이 closing(여운)인지
  - CTA 언어가 포함되지 않았는지
  - 감정 변화가 있는지
  - 씬 수가 적정 범위(5-12)인지
  - 총 시간이 타겟에 부합하는지
"""

from __future__ import annotations

import logging
from typing import Any

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import (
    GateVerdict,
    SceneOutline,
    StructureOutline,
)
from shorts_maker_v2.providers.llm_router import LLMRouter

logger = logging.getLogger(__name__)

# CTA 금지어 (closing 씬에서 사용 금지)
_CLOSING_FORBIDDEN_WORDS: tuple[str, ...] = (
    "구독",
    "좋아요",
    "알림",
    "설정",
    "subscribe",
    "like",
    "comment",
    "follow",
    "bell",
    "notification",
    "channel",
    "링크",
    "클릭",
)


class StructureStep:
    """Gate 2: 씬별 구성안 생성 + 검증."""

    MAX_RETRIES = 2

    _SYSTEM_PROMPT = (
        "You are a YouTube Shorts content architect. "
        "Your job is to create a STRUCTURAL OUTLINE — NOT a full script.\n\n"
        "For each scene, provide:\n"
        "- intent: What this scene accomplishes (1 sentence)\n"
        "- visual_direction: Visual concept direction (NOT a DALL-E prompt, just the idea)\n"
        "- emotional_beat: What the viewer should feel during this scene\n"
        "- role: One of hook/body/closing\n"
        "- target_sec: Estimated duration in seconds\n\n"
        "Output ONLY valid JSON:\n"
        "{\n"
        '  "narrative_arc": "quiet_storytelling",\n'
        '  "scenes": [\n'
        "    {\n"
        '      "role": "hook",\n'
        '      "intent": "Capture attention with a surprising fact about the topic",\n'
        '      "visual_direction": "Dark cosmic background with a single bright star",\n'
        '      "emotional_beat": "curiosity and wonder",\n'
        '      "target_sec": 5.0\n'
        "    },\n"
        "    ...\n"
        "    {\n"
        '      "role": "closing",\n'
        '      "intent": "Leave a lingering contemplative thought",\n'
        '      "visual_direction": "Wide peaceful landscape at twilight",\n'
        '      "emotional_beat": "quiet wonder, a thought that stays",\n'
        '      "target_sec": 5.0\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "CRITICAL RULES:\n"
        "- First scene MUST have role 'hook' (grab attention in 3 seconds)\n"
        "- Last scene MUST have role 'closing' (lingering thought, NOT an action demand)\n"
        "- Middle scenes have role 'body'\n"
        "- Total scenes: 7-10\n"
        "- Total duration: match the target range\n"
        "- This is a quiet storytelling channel ('시간을 훔치는 이야기').\n"
        "  Viewers listen before sleep or when waking up.\n"
        "  NEVER suggest CTAs, subscribe requests, or action commands.\n"
        "  The closing scene must end with a contemplative afterimage.\n"
        "- Emotional beats MUST vary across scenes (not all the same)\n"
        "- intent should be specific to the topic, not generic\n"
    )

    def __init__(
        self,
        config: AppConfig,
        llm_router: LLMRouter,
        channel_key: str = "",
    ):
        self.config = config
        self.llm_router = llm_router
        self.channel_key = channel_key

    def run(
        self,
        topic: str,
        production_plan: Any | None = None,
        research_context: Any | None = None,
    ) -> StructureOutline:
        """구성안 생성 + Gate 2 검증.

        Args:
            topic: 영상 주제
            production_plan: ProductionPlan 객체 (Gate 1 출력)
            research_context: ResearchContext 객체 (리서치 스텝 출력)

        Returns:
            StructureOutline (검증 통과 또는 폴백)
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            logger.info(
                "[Structure] attempt %d/%d for topic='%s'",
                attempt,
                self.MAX_RETRIES,
                topic,
            )
            try:
                system_prompt, user_prompt = self._build_prompts(
                    topic,
                    production_plan,
                    research_context,
                    attempt,
                )
                result = self.llm_router.generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.7,
                )
                if not isinstance(result, dict):
                    logger.warning("[Structure] LLM returned non-dict: %s", type(result))
                    continue

                outline = self._parse_outline(result)
                verdict, issues = self._gate2_validate(outline, production_plan)

                validation_mode = self.config.project.structure_validation

                if verdict == GateVerdict.PASS:
                    logger.info("[Structure] Gate 2 PASS")
                    return outline

                if validation_mode == "lenient":
                    logger.warning(
                        "[Structure] Gate 2 FAIL (lenient mode, proceeding): %s",
                        "; ".join(issues),
                    )
                    return outline

                logger.warning(
                    "[Structure] Gate 2 FAIL (attempt %d): %s",
                    attempt,
                    "; ".join(issues),
                )

            except Exception as exc:
                logger.warning("[Structure] attempt %d error: %s", attempt, exc)

        logger.warning("[Structure] All retries exhausted, using fallback outline")
        return self._fallback_outline(topic, production_plan)

    def _build_prompts(
        self,
        topic: str,
        production_plan: Any | None,
        research_context: Any | None,
        attempt: int,
    ) -> tuple[str, str]:
        """시스템 프롬프트 + 유저 프롬프트 생성."""
        system_prompt = self._SYSTEM_PROMPT

        # 타겟 시간대
        dur_min, dur_max = self.config.video.target_duration_sec
        user_parts = [
            f"Topic: {topic}",
            f"Target duration: {dur_min}-{dur_max} seconds",
            f"Target scene count: {self.config.project.default_scene_count}",
        ]

        if production_plan and hasattr(production_plan, "to_prompt_block"):
            user_parts.append("")
            user_parts.append(production_plan.to_prompt_block())

        if research_context and hasattr(research_context, "to_prompt_block"):
            block = research_context.to_prompt_block()
            if block:
                user_parts.append("")
                user_parts.append(block)

        if attempt > 1:
            user_parts.append("")
            user_parts.append(
                "IMPORTANT: The previous outline was rejected. "
                "Ensure the last scene has role='closing' with a contemplative emotional beat. "
                "Vary the emotional beats across scenes. "
                "Do NOT include any CTA language."
            )

        return system_prompt, "\n".join(user_parts)

    def _parse_outline(self, data: dict[str, Any]) -> StructureOutline:
        """LLM JSON → StructureOutline 변환."""
        raw_scenes = data.get("scenes", [])
        if not isinstance(raw_scenes, list) or not raw_scenes:
            raise ValueError("No scenes in outline response")

        scenes: list[SceneOutline] = []
        for idx, raw in enumerate(raw_scenes, start=1):
            if not isinstance(raw, dict):
                continue
            role = str(raw.get("role", "body")).strip().lower()
            if role not in ("hook", "body", "closing", "cta"):
                role = "body"
            # cta를 closing으로 자동 변환
            if role == "cta":
                role = "closing"
            scenes.append(
                SceneOutline(
                    scene_id=idx,
                    role=role,
                    intent=str(raw.get("intent", "")).strip(),
                    visual_direction=str(raw.get("visual_direction", "")).strip(),
                    emotional_beat=str(raw.get("emotional_beat", "")).strip(),
                    target_sec=float(raw.get("target_sec", 5.0)),
                )
            )

        total_sec = sum(s.target_sec for s in scenes)
        narrative_arc = str(data.get("narrative_arc", "quiet_storytelling")).strip()

        return StructureOutline(
            scenes=scenes,
            total_estimated_sec=round(total_sec, 1),
            narrative_arc=narrative_arc,
        )

    def _gate2_validate(
        self,
        outline: StructureOutline,
        production_plan: Any | None,
    ) -> tuple[GateVerdict, list[str]]:
        """Gate 2: 구성안 품질 검증.

        Returns:
            (verdict, issues_list)
        """
        issues: list[str] = []
        scenes = outline.scenes

        # 1. 씬 수 체크 (5-12)
        if len(scenes) < 5:
            issues.append(f"Too few scenes: {len(scenes)} (need 5+)")
        if len(scenes) > 12:
            issues.append(f"Too many scenes: {len(scenes)} (max 12)")

        # 2. 첫 씬이 hook인지
        if scenes and scenes[0].role != "hook":
            issues.append(f"First scene role is '{scenes[0].role}', expected 'hook'")

        # 3. 마지막 씬이 closing인지
        if scenes and scenes[-1].role != "closing":
            issues.append(f"Last scene role is '{scenes[-1].role}', expected 'closing'")

        # 4. closing 씬에 CTA 언어가 없는지
        if scenes and scenes[-1].role == "closing":
            closing_text = (scenes[-1].intent + " " + scenes[-1].emotional_beat).lower()
            for forbidden in _CLOSING_FORBIDDEN_WORDS:
                if forbidden.lower() in closing_text:
                    issues.append(f"Closing scene contains forbidden CTA word: '{forbidden}'")
                    break

        # 5. 감정 변화 체크 (최소 3가지 다른 감정)
        beats = {s.emotional_beat.lower().strip() for s in scenes if s.emotional_beat.strip()}
        if len(beats) < 3:
            issues.append(f"Only {len(beats)} unique emotional beats (need 3+ for variety)")

        # 6. 총 시간 체크
        dur_min, dur_max = self.config.video.target_duration_sec
        # 10초 여유 허용
        if outline.total_estimated_sec < dur_min - 10:
            issues.append(f"Total duration {outline.total_estimated_sec}s too short (target: {dur_min}-{dur_max}s)")
        if outline.total_estimated_sec > dur_max + 10:
            issues.append(f"Total duration {outline.total_estimated_sec}s too long (target: {dur_min}-{dur_max}s)")

        # 7. intent가 비어있는 씬 체크
        empty_intents = [s.scene_id for s in scenes if len(s.intent) < 5]
        if empty_intents:
            issues.append(f"Scenes with empty/short intent: {empty_intents}")

        # 8. 청중 desire 정합성 (production_plan이 있을 때)
        if production_plan and hasattr(production_plan, "audience_profile"):
            ap = production_plan.audience_profile
            if ap and isinstance(ap, dict):
                desire = ap.get("desire", "")
                if desire and len(desire) >= 10:
                    # 최소한 하나의 씬 intent에 desire 키워드가 반영되어야 함
                    desire_words = {w for w in desire.lower().split() if len(w) >= 2}
                    intent_text = " ".join(s.intent.lower() for s in scenes)
                    matched = sum(1 for w in desire_words if w in intent_text)
                    if matched < 1 and desire_words:
                        issues.append("Outline intents don't reflect audience desire")

        verdict = GateVerdict.PASS if not issues else GateVerdict.FAIL_RETRY
        return verdict, issues

    # 폴백 body 씬용 감정 아크. 6개 이상이면 cycle 한다. Gate 2의
    # "감정 3가지 이상" 체크를 자동으로 만족시킨다.
    _FALLBACK_BODY_BEATS: tuple[str, ...] = (
        "noticing",
        "questioning",
        "leaning in",
        "small surprise",
        "understanding",
        "gentle clarity",
    )

    def _fallback_outline(
        self,
        topic: str,
        production_plan: Any | None,
    ) -> StructureOutline:
        """결정론 폴백 구성안.

        LLM 재시도가 모두 실패해도 영상은 ship 되어야 하지만, 과거 폴백은
        ``"{topic}의 핵심 포인트 N을 설명한다"`` 보일러플레이트라 영상
        품질이 통째로 무너졌다 (2026-05-11 manifest 케이스). 새 폴백은:

        1. ``production_plan`` 의 ``visual_keywords`` / ``core_message`` /
           ``audience_profile.desire`` 를 씬별로 주입해 generic 텍스트 제거.
        2. body 씬 intent 가 단순 카운트("핵심 포인트 1/2/3")가 아니라
           조용한 스토리 아크(첫 단서 → 의문 → 풀이 → 의미)를 따른다.
        3. 반환된 outline 에 ``is_fallback=True`` 를 박아서 orchestrator
           가 ``manifest.degraded_steps`` 로 표면화할 수 있게 한다.
        """
        scene_count = self.config.project.default_scene_count
        body_count = max(scene_count - 2, 1)  # hook + closing 제외

        # production_plan 에서 사용 가능한 단서 수집
        visual_keywords: list[str] = []
        core_message = ""
        audience_desire = ""
        tone_hint = ""
        if production_plan is not None:
            raw_kw = getattr(production_plan, "visual_keywords", None)
            if isinstance(raw_kw, (list, tuple)):
                visual_keywords = [str(k).strip() for k in raw_kw if str(k).strip()]
            core_message = str(getattr(production_plan, "core_message", "") or "").strip()
            ap = getattr(production_plan, "audience_profile", None)
            if isinstance(ap, dict):
                audience_desire = str(ap.get("desire", "") or "").strip()
            tone_hint = str(getattr(production_plan, "tone", "") or "").strip()

        # hook 씬
        hook_visual = (
            f"Cinematic visualization of {visual_keywords[0]}, dramatic lighting, shallow depth of field"
            if visual_keywords
            else "Dark dramatic background with a single focal point, cinematic mood"
        )
        scenes: list[SceneOutline] = [
            SceneOutline(
                scene_id=1,
                role="hook",
                intent=f"{topic}을(를) 바라보던 흔한 인상에 작은 균열을 낸다",
                visual_direction=hook_visual,
                emotional_beat="curiosity, soft pull",
                target_sec=5.0,
            ),
        ]

        # body 씬 — 카운트가 아닌 흐름. 5단계 아크를 body_count 에 맞춰 펴서 배치.
        for i in range(1, body_count + 1):
            sid = i + 1
            kw = visual_keywords[(i - 1) % len(visual_keywords)] if visual_keywords else ""
            visual_dir = (
                f"Cinematic visualization of {kw}, soft ambient mood, layered detail"
                if kw
                else "Layered visual that lingers on a single mood, soft ambient light"
            )

            if i == 1:
                intent = f"{topic} 이야기의 첫 단서를 차분히 보여준다"
            elif i == 2:
                intent = "보이는 것 너머의 작은 의문을 슬쩍 제시한다"
            elif i == body_count and core_message:
                intent = f"앞의 결들이 '{core_message[:80]}'로 모이는 것을 조용히 비춘다"
            elif i == body_count - 1 and body_count >= 4:
                intent = "흔히 놓치는 의외의 결 하나를 짧게 비춘다"
            elif kw:
                intent = f"{topic} 속 또 다른 결을 {kw}의 관점에서 따라간다"
            elif audience_desire:
                intent = f"'{audience_desire[:60]}'에 가까이 다가가는 한 결을 짚는다"
            else:
                intent = f"{topic}의 또 다른 결을 천천히 따라간다"

            beat = self._FALLBACK_BODY_BEATS[(i - 1) % len(self._FALLBACK_BODY_BEATS)]
            scenes.append(
                SceneOutline(
                    scene_id=sid,
                    role="body",
                    intent=intent,
                    visual_direction=visual_dir,
                    emotional_beat=beat,
                    target_sec=5.0,
                )
            )

        # closing 씬 — CTA 금지, 여운 우선
        closing_visual = (
            f"Wide quiet landscape evoking {visual_keywords[-1]}, gentle ambient light"
            if visual_keywords
            else "Wide peaceful landscape at twilight, soft ambient light"
        )
        closing_intent = (
            f"'{core_message[:80]}'를 한 호흡으로 다시 흘려보내는 여운을 남긴다"
            if core_message
            else "여운이 남는 한 호흡으로 조용히 마무리한다"
        )
        scenes.append(
            SceneOutline(
                scene_id=scene_count,
                role="closing",
                intent=closing_intent,
                visual_direction=closing_visual,
                emotional_beat="quiet afterimage",
                target_sec=5.0,
            )
        )

        logger.info(
            "[Structure] Fallback outline composed (kw=%d, core_msg=%s, tone=%s)",
            len(visual_keywords),
            "yes" if core_message else "no",
            "yes" if tone_hint else "no",
        )

        return StructureOutline(
            scenes=scenes,
            total_estimated_sec=float(scene_count * 5),
            narrative_arc="quiet_storytelling",
            is_fallback=True,
        )
