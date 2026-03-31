from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

from shorts_maker_v2.models import ScenePlan  # noqa: E402


class ScriptReviewMixin:
    """Quality review, validation, truncation for scripts.

    Designed to be mixed into ScriptStep. Accesses self.config, self.llm_router,
    self.channel_key, self._channel_review_criteria, self._review_copy, etc.
    """

    # ── Sprint 4: 채널별 대본 검증 기준 ────────────────────────────────────────
    _CHANNEL_REVIEW_CRITERIA: dict[str, dict[str, Any]] = {
        "health": {
            "extra_dimensions": (
                "  source_score : Does the script cite specific data sources "
                "(e.g. WHO, specific studies)? (1=no sources, 10=multiple cited)\n"
                "  safety_score : Does the script avoid dangerous medical claims, "
                "unverified treatments, or misleading health info? (1=dangerous, 10=fully safe)\n"
            ),
            "extra_keys": ("source_score", "safety_score"),
            "min_score_override": 8,  # 건강 채널은 더 엄격
            "context_note": (
                "This is a HEALTH/MEDICAL channel. Patient safety is paramount. "
                "Score very strictly on safety_score. Any unverified medical claim = score 1."
            ),
        },
        "ai_tech": {
            "extra_dimensions": (
                "  data_score : Does the script use specific numbers, dates, or data points "
                "rather than vague claims? (1=all vague, 10=data-rich)\n"
            ),
            "extra_keys": ("data_score",),
            "min_score_override": 7,
            "context_note": (
                "This is an AI/TECH channel targeting developers and tech enthusiasts. "
                "Vague hype without specifics should score low on data_score."
            ),
        },
        "psychology": {
            "extra_dimensions": (
                "  empathy_score : Does the script feel warm, relatable, and emotionally safe? "
                "(1=cold/clinical, 10=deeply empathetic)\n"
            ),
            "extra_keys": ("empathy_score",),
            "min_score_override": 7,
            "context_note": (
                "This is a PSYCHOLOGY channel focused on emotional safety and self-understanding. "
                "Cold academic tone should score low on empathy_score."
            ),
        },
        "history": {
            "extra_dimensions": (
                "  narrative_score : Does the script tell a compelling story with dramatic tension? "
                "(1=boring list, 10=gripping narrative)\n"
            ),
            "extra_keys": ("narrative_score",),
            "min_score_override": 7,
            "context_note": (
                "This is a HISTORY channel. Dry chronological lists should score low. "
                "Dramatic storytelling with twists scores high."
            ),
        },
        "space": {
            "extra_dimensions": (
                "  wonder_score : Does the script evoke a sense of awe and cosmic scale? "
                "(1=mundane, 10=mind-blowing wonder)\n"
            ),
            "extra_keys": ("wonder_score",),
            "min_score_override": 7,
            "context_note": (
                "This is a SPACE/ASTRONOMY channel. Content should make viewers feel the "
                "vastness and wonder of the cosmos. Use analogies to convey scale."
            ),
        },
    }

    _REVIEW_COPY: dict[str, str] = {
        "base_review_system": (
            "You are a YouTube Shorts script quality evaluator. "
            "Score the given script on these dimensions from 1-10:\n"
            "  hook_score : How well does the Hook stop the scroll? (1=boring, 10=irresistible)\n"
            "  flow_score : How naturally does the Body build and connect? (1=choppy, 10=seamless)\n"
            "  cta_score  : How clear and actionable is the CTA? (1=vague, 10=immediately doable)\n"
            "  verifiability_score : Can a viewer verify the factual claims easily? "
            "(1=not credible, 10=highly verifiable)\n"
            "  spelling_score : Is the English spelling, grammar, and punctuation clean and natural for spoken delivery? "
            "(1=many issues, 10=excellent)\n"
        ),
        "feedback_rule": "Also provide a brief 'feedback' string (max 80 chars) with the main weakness.\n",
        "output_rule": 'Output ONLY valid JSON: {{{json_example}, "feedback": "..."}}',
    }

    def _build_review_system(self) -> tuple[str, tuple[str, ...], int]:
        """채널별 리뷰 시스템 프롬프트 + 필수 키 + min_score를 반환.

        Returns:
            (system_prompt, required_score_keys, effective_min_score)
        """
        base_keys = ("hook_score", "flow_score", "cta_score", "verifiability_score", "spelling_score")
        extra_dimensions = ""
        extra_keys: tuple[str, ...] = ()
        min_score = self.config.project.script_review_min_score
        context_note = ""

        if self.channel_key and self.channel_key in self._channel_review_criteria:
            criteria = self._channel_review_criteria[self.channel_key]
            extra_dimensions = criteria.get("extra_dimensions", "")
            extra_keys = criteria.get("extra_keys", ())
            min_score = criteria.get("min_score_override", min_score)
            context_note = criteria.get("context_note", "")

        all_keys = base_keys + extra_keys
        json_example = ", ".join(f'"{k}": n' for k in all_keys)

        system_prompt = (
            self._review_copy.get("base_review_system", "")
            + extra_dimensions
            + self._review_copy.get("feedback_rule", "")
        )
        if context_note:
            system_prompt += f"\nChannel Context: {context_note}\n"
        output_rule = self._review_copy.get(
            "output_rule", 'Output ONLY valid JSON: {{{json_example}, "feedback": "..."}}'
        )
        system_prompt += output_rule.format(json_example=json_example)

        return system_prompt, all_keys, min_score

    def _review_script(self, title: str, scenes: list[ScenePlan]) -> dict[str, Any]:
        """LLM으로 생성된 스크립트 품질 채점 (채널별 차별화된 기준 적용).

        Gemini 3.1: thinking_level='high'로 심층 추론.
        건강 채널 팩트체크 등 복잡한 판단에서 정확도 향상.
        """
        system_prompt, _, _ = self._build_review_system()
        script_text = f"Title: {title}\n\n"
        for s in scenes:
            script_text += f"[{s.structure_role.upper()}] {s.narration_ko}\n"
        # Sprint 4.1: thinking_level_review (기본 'high') — 깊은 추론으로 품질 검증
        review_thinking = self.config.providers.thinking_level_review
        result = self.llm_router.generate_json(
            system_prompt=system_prompt,
            user_prompt=script_text,
            temperature=0.2,
            thinking_level=review_thinking,
        )
        return result if isinstance(result, dict) else {}

    # ── 패턴 #3: MARL 자기검증 (리서치 일관성 검증) ────────────────────────

    def _verify_with_research(
        self,
        title: str,
        scenes: list[ScenePlan],
        research_context: Any,
    ) -> dict[str, Any]:
        """MARL 단계 2: 대본과 리서치 결과의 일관성을 LLM으로 자기검증.

        SiteAgent의 MARL 메타인지 패턴(생성->자기검증->수정) 중 '자기검증' 단계.
        리서치에서 확인된 팩트와 대본의 주장이 일치하는지, 과장이나 왜곡이 없는지 확인.

        Args:
            title: 대본 제목
            scenes: 생성된 씬 목록
            research_context: 리서치 스텝 결과 (to_prompt_block 메서드 필요)

        Returns:
            검증 결과 딕셔너리:
            {
                "consistent": true/false,
                "issues": ["과장된 부분 설명", ...],
                "fixes": [{"scene_id": 2, "original": "...", "suggested": "..."}, ...],
                "confidence": 0.0-1.0
            }
        """
        if not hasattr(research_context, "to_prompt_block"):
            return {"consistent": True, "issues": [], "fixes": [], "confidence": 1.0}

        research_block = research_context.to_prompt_block()
        if not research_block:
            return {"consistent": True, "issues": [], "fixes": [], "confidence": 1.0}

        script_text = f"Title: {title}\n\n"
        for s in scenes:
            script_text += f"[Scene {s.scene_id} / {s.structure_role.upper()}]\n{s.narration_ko}\n\n"

        system_prompt = (
            "You are a fact-checking editor for YouTube Shorts scripts. "
            "Compare the SCRIPT against the RESEARCH FACTS below.\n\n"
            "For each factual claim in the script, check:\n"
            "  1. Is it supported by the research facts?\n"
            "  2. Is it exaggerated or distorted from the original data?\n"
            "  3. Are any important facts from the research missing?\n\n"
            "Output ONLY valid JSON:\n"
            "{\n"
            '  "consistent": true/false,\n'
            '  "issues": ["description of each inconsistency"],\n'
            '  "fixes": [{"scene_id": N, "original": "problematic text", "suggested": "corrected text"}],\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )

        user_prompt = f"=== RESEARCH FACTS ===\n{research_block}\n\n=== SCRIPT TO VERIFY ===\n{script_text}"

        try:
            result = self.llm_router.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                thinking_level="medium",
            )
            return (
                result
                if isinstance(result, dict)
                else {"consistent": True, "issues": [], "fixes": [], "confidence": 1.0}
            )
        except Exception as exc:
            logger.warning("[MARL] verification failed (skipped): %s", exc)
            return {"consistent": True, "issues": [], "fixes": [], "confidence": 1.0}

    def _apply_verification_fixes(
        self,
        scenes: list[ScenePlan],
        verification: dict[str, Any],
    ) -> list[ScenePlan]:
        """MARL 단계 3: 자기검증에서 발견된 문제를 자동 수정.

        Args:
            scenes: 원본 씬 목록
            verification: _verify_with_research의 반환값

        Returns:
            수정된 씬 목록 (수정 사항이 없으면 원본 그대로)
        """
        fixes = verification.get("fixes", [])
        if not fixes:
            return scenes

        # scene_id -> suggested narration 매핑
        fix_map: dict[int, str] = {}
        for fix in fixes:
            sid = fix.get("scene_id")
            suggested = fix.get("suggested", "")
            if sid and suggested:
                fix_map[int(sid)] = suggested

        if not fix_map:
            return scenes

        patched: list[ScenePlan] = []
        for scene in scenes:
            if scene.scene_id in fix_map:
                new_narration = fix_map[scene.scene_id]
                new_target = self.estimate_narration_duration_sec(
                    new_narration,
                    language=self.config.project.language,
                    tts_speed=self.config.providers.tts_speed,
                )
                patched.append(
                    ScenePlan(
                        scene_id=scene.scene_id,
                        narration_ko=new_narration,
                        visual_prompt_en=scene.visual_prompt_en,
                        target_sec=new_target,
                        structure_role=scene.structure_role,
                    )
                )
                logger.info(
                    "[MARL] Scene %d narration patched (%.0f->%.0f chars)",
                    scene.scene_id,
                    len(scene.narration_ko),
                    len(new_narration),
                )
            else:
                patched.append(scene)

        return patched

    # ── 패턴 #4: Pydantic 스키마 출력 검증 ────────────────────────────────

    @staticmethod
    def _validate_script_schema(payload: dict[str, Any]) -> list[str]:
        """Pydantic 모델로 LLM 응답 스키마를 검증.

        SiteAgent의 Zod -> OpenAI Tool 패턴을 Pydantic으로 구현.
        Pydantic이 없으면 빈 리스트 반환 (graceful degradation).

        Returns:
            에러 메시지 리스트 (비어있으면 유효)
        """
        # Import locally to avoid circular dependency with script_step models
        from shorts_maker_v2.pipeline.script_step import _HAS_PYDANTIC, ScriptOutput

        if not _HAS_PYDANTIC:
            return []

        try:
            from pydantic import ValidationError

            normalized_payload = copy.deepcopy(payload)
            scenes = normalized_payload.get("scenes")
            if isinstance(scenes, list):
                normalized_scenes: list[Any] = []
                for raw_scene in scenes:
                    if not isinstance(raw_scene, dict):
                        normalized_scenes.append(raw_scene)
                        continue
                    scene = dict(raw_scene)
                    if not scene.get("narration_ko"):
                        scene["narration_ko"] = scene.get("narration") or scene.get("voiceover") or ""
                    if not scene.get("visual_prompt_en"):
                        scene["visual_prompt_en"] = scene.get("visual_prompt") or scene.get("image_prompt") or ""
                    normalized_scenes.append(scene)
                normalized_payload["scenes"] = normalized_scenes

            ScriptOutput.model_validate(normalized_payload)
            return []
        except ValidationError as e:
            return [str(err) for err in e.errors()]

    def _passes_review(self, review: dict[str, Any], min_score: int) -> bool:
        """채널별 필수 키 전체가 min_score 이상이면 통과."""
        _, required_keys, _ = self._build_review_system()
        return all(int(review.get(k, 0)) >= min_score for k in required_keys)

    @classmethod
    def _validate_cta(
        cls,
        narration: str,
        forbidden_words: tuple[str, ...] | None = None,
    ) -> list[str]:
        """CTA 나레이션에 금지어가 포함되어 있으면 위반 항목 리스트를 반환한다.

        반환값이 빈 리스트이면 통과. 비어있지 않으면 위반 항목이 로그에 기록된다.
        forbidden_words가 None이면 클래스 기본 속성을 사용한다.
        """
        from shorts_maker_v2.pipeline.script_prompts import ScriptPromptsMixin

        words = forbidden_words if forbidden_words is not None else ScriptPromptsMixin._CTA_FORBIDDEN_WORDS
        return [w for w in words if w in narration.lower()]

    @classmethod
    def _score_persona_match(
        cls,
        scenes: list[ScenePlan],
        channel_key: str,
        persona_keywords: dict[str, tuple[str, ...]] | None = None,
    ) -> float:
        """채널 페르소나 키워드 밀도 기반 매칭 스코어를 반환한다 (0.0~1.0).

        알 수 없는 채널 키 -> 0.5 중립 반환.
        씬이 없으면 -> 0.0 반환.
        persona_keywords가 None이면 클래스 기본 속성을 사용한다.
        """
        from shorts_maker_v2.pipeline.script_prompts import ScriptPromptsMixin

        if not scenes:
            return 0.0
        kw_map = persona_keywords if persona_keywords is not None else ScriptPromptsMixin._PERSONA_KEYWORDS
        keywords = kw_map.get(channel_key)
        if not keywords:
            return 0.5  # 알 수 없는 채널은 중립
        all_text = " ".join(s.narration_ko for s in scenes)
        hit_count = sum(1 for kw in keywords if kw in all_text)
        return round(hit_count / len(keywords), 3)

    def _truncate_to_fit(
        self,
        scenes: list[ScenePlan],
        max_total_sec: float,
        language: str,
        tts_speed: float,
    ) -> list[ScenePlan]:
        """총 길이를 max_total_sec에 맞추기 위해 각 장면의 나레이션을 강제로 자릅니다."""
        current_total_sec = self.estimate_total_duration_sec(scenes)
        if current_total_sec <= max_total_sec:
            return scenes

        # 각 장면의 목표 길이를 비례적으로 줄입니다.
        reduction_ratio = max_total_sec / current_total_sec
        truncated_scenes: list[ScenePlan] = []

        for scene in scenes:
            original_narration = scene.narration_ko
            original_target_sec = scene.target_sec

            # 새로운 목표 시간 계산 (최소 1.2초는 유지)
            new_target_sec = max(1.2, original_target_sec * reduction_ratio)

            effective_chars_per_sec = self.duration_estimate_chars_per_sec / max(0.7, tts_speed)

            # 구두점 보정은 무시하고 단순 문자 수로만 계산
            max_chars_for_new_target = int(new_target_sec * effective_chars_per_sec)

            truncated_narration = original_narration
            if len(original_narration) > max_chars_for_new_target:
                truncated_narration = (
                    original_narration[:max_chars_for_new_target].rsplit(" ", 1)[0] + "..."
                    if " " in original_narration[:max_chars_for_new_target]
                    else original_narration[:max_chars_for_new_target] + "..."
                )
                # 너무 짧아지는 것을 방지 (최소 10자)
                if len(truncated_narration) < 10:
                    truncated_narration = (
                        original_narration[:10] + "..." if len(original_narration) > 10 else original_narration
                    )

            # 다시 추정하여 실제 반영될 시간 확인
            re_estimated_sec = self.estimate_narration_duration_sec(
                truncated_narration, language=language, tts_speed=tts_speed
            )

            truncated_scenes.append(
                ScenePlan(
                    scene_id=scene.scene_id,
                    narration_ko=truncated_narration,
                    visual_prompt_en=scene.visual_prompt_en,
                    target_sec=re_estimated_sec,
                    structure_role=scene.structure_role,
                )
            )
        return truncated_scenes
