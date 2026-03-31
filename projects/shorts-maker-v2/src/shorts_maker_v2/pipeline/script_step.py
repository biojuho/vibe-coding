from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, Field, ValidationError, model_validator

    _HAS_PYDANTIC = True
except ImportError:  # graceful degradation
    try:
        from pydantic import BaseModel, Field, ValidationError  # noqa: F401

        model_validator = None
        _HAS_PYDANTIC = True
    except ImportError:
        model_validator = None
        _HAS_PYDANTIC = False

from shorts_maker_v2.config import AppConfig  # noqa: E402
from shorts_maker_v2.models import ScenePlan  # noqa: E402
from shorts_maker_v2.pipeline.script_prompts import (  # noqa: E402
    ScriptPromptsMixin,
    _deep_merge_dicts,  # noqa: F401 — re-exported for backward compat (tests import from here)
    _load_script_step_locale_bundle,  # noqa: F401 — re-exported for backward compat
)
from shorts_maker_v2.pipeline.script_review import ScriptReviewMixin  # noqa: E402
from shorts_maker_v2.providers.llm_router import LLMRouter  # noqa: E402


class TopicUnsuitableError(Exception):
    """LLM이 신뢰할 수 있는 자료가 부족하다고 판단한 경우 발생.

    orchestrator/batch에서 이 에러를 잡아 다른 주제로 전환하거나,
    n8n 워크플로우에서 'topic_unsuitable' 상태를 분기 조건으로 사용.
    """

    pass


# ── 패턴 #4: Pydantic 스키마 기반 출력 검증 ────────────────────────────────

if _HAS_PYDANTIC:

    class SceneOutput(BaseModel):
        """LLM이 반환해야 하는 개별 씬 스키마."""

        narration_ko: str = Field(..., min_length=5, description="한국어 나레이션")
        visual_prompt_en: str = Field(..., min_length=5, description="DALL-E용 영어 비주얼 프롬프트")
        estimated_seconds: float = Field(default=5.0, ge=1.0, le=30.0)
        structure_role: str = Field(default="body", pattern=r"^(hook|body|cta|closing)$")

        if model_validator is not None:

            @model_validator(mode="before")
            @classmethod
            def _normalize_scene_aliases(cls, value: Any) -> Any:
                if not isinstance(value, dict):
                    return value

                normalized = dict(value)
                if not normalized.get("narration_ko"):
                    normalized["narration_ko"] = normalized.get("narration") or normalized.get("voiceover") or ""
                if not normalized.get("visual_prompt_en"):
                    normalized["visual_prompt_en"] = normalized.get("visual_prompt") or ""
                return normalized

    class ScriptOutput(BaseModel):
        """LLM 대본 생성 전체 출력 스키마.

        SiteAgent의 zodToOpenAITool 패턴을 Pydantic으로 구현.
        LLM 응답이 이 스키마에 맞지 않으면 ValidationError 발생.
        """

        title: str = Field(..., min_length=1, max_length=100)
        scenes: list[SceneOutput] = Field(..., min_length=1)
        no_reliable_source: bool = Field(default=False)
        reason: str = Field(default="")


class ScriptStep(ScriptPromptsMixin, ScriptReviewMixin):
    max_generation_attempts = 3

    def __init__(
        self,
        config: AppConfig,
        llm_router: LLMRouter,
        openai_client: Any | None = None,
        channel_hook_pattern: str | None = None,
        channel_duration_override: int | None = None,
        channel_key: str = "",
    ):
        self.config = config
        self.llm_router = llm_router
        # Keep openai_client reference for TTS/image (non-LLM) tasks
        self.openai_client = openai_client
        # 채널별 Hook 패턴 고정 (없으면 None → 로테이션 사용)
        self.channel_hook_pattern: str | None = channel_hook_pattern
        # 채널별 목표 영상 길이 (초). None이면 config.video.target_duration_sec 사용
        self.channel_duration_override: int | None = channel_duration_override
        # Sprint 4: 채널 키 (리뷰 기준 분기용)
        self.channel_key: str = channel_key
        self._apply_locale_overrides()

    @classmethod
    def from_channel_profile(
        cls,
        config: AppConfig,
        llm_router: LLMRouter,
        channel_profile: dict,
        openai_client: Any | None = None,
        channel_key: str = "",
    ) -> ScriptStep:
        """
        channel_profiles.yaml의 채널 딕셔너리를 받아 hook_pattern을 자동 적용합니다.

        예::
            profile = yaml.safe_load(open('channel_profiles.yaml'))['channels']['ai_tech']
            step = ScriptStep.from_channel_profile(config, llm_router, profile, channel_key='ai_tech')
        """
        hook_pattern = channel_profile.get("hook_pattern")
        duration_override = channel_profile.get("target_duration_sec")
        return cls(
            config,
            llm_router,
            openai_client=openai_client,
            channel_hook_pattern=hook_pattern,
            channel_duration_override=duration_override,
            channel_key=channel_key,
        )

    @staticmethod
    def _trim_hook_to_limit(narration: str, limit: int = 15) -> str:
        """Hook narration이 limit자 초과 시 글자 단위로 트림한다.

        TTS 음성은 원본 narration을 그대로 읽으므로 음성 품질에는 영향 없다.
        자막(caption_pillow) 렌더 시 픽셀 넘침 방지가 목적.
        공백으로 끝나는 경우 rstrip으로 정리한다.
        """
        if len(narration) <= limit:
            return narration
        return narration[:limit].rstrip()

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:].strip()
        if cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        return json.loads(cleaned)

    @classmethod
    def parse_script_payload(
        cls,
        payload: dict[str, Any] | str,
        scene_count: int,
        target_duration_sec: tuple[int, int],
        *,
        language: str = "ko-KR",
        tts_speed: float = 1.0,
    ) -> tuple[str, list[ScenePlan]]:
        data = payload if isinstance(payload, dict) else cls._extract_json(payload)
        title = str(data.get("title", "Untitled Shorts")).strip() or "Untitled Shorts"
        raw_scenes = data.get("scenes", [])
        if not isinstance(raw_scenes, list) or not raw_scenes:
            raise ValueError("Script payload must contain a non-empty scenes list.")

        total = len(raw_scenes)
        scenes: list[ScenePlan] = []
        for idx, raw_scene in enumerate(raw_scenes, start=1):
            if not isinstance(raw_scene, dict):
                raise ValueError(f"Scene #{idx} must be an object.")
            narration = str(
                raw_scene.get("narration_ko") or raw_scene.get("narration") or raw_scene.get("voiceover") or ""
            ).strip()
            visual_prompt = str(
                raw_scene.get("visual_prompt_en")
                or raw_scene.get("visual_prompt")
                or raw_scene.get("image_prompt")
                or ""
            ).strip()
            if not narration or not visual_prompt:
                raise ValueError(f"Scene #{idx} is missing narration or visual prompt.")
            # GPT estimated_seconds는 실제 TTS 속도와 괴리가 크므로 항상 자체 추정 사용
            target_sec = cls.estimate_narration_duration_sec(
                narration,
                language=language,
                tts_speed=tts_speed,
            )
            # Infer structure_role from position if LLM omits it
            raw_role = str(raw_scene.get("structure_role", "")).strip().lower()
            if raw_role in ("hook", "body", "cta", "closing"):
                structure_role = raw_role
            elif idx == 1:
                structure_role = "hook"
            elif idx == total:
                structure_role = "closing"
            else:
                structure_role = "body"
            # ── Hook 15자 트림 (화면 임팩트 극대화) ─────────────────────────
            _hook_narration_max_chars = 15
            if structure_role == "hook" and len(narration) > _hook_narration_max_chars:
                logger.warning(
                    "Hook narration exceeds %d chars (%d chars): '%s…' — "
                    "auto-trimming to %d chars for scroll-stop impact.",
                    _hook_narration_max_chars,
                    len(narration),
                    narration[:_hook_narration_max_chars],
                    _hook_narration_max_chars,
                )
                narration = cls._trim_hook_to_limit(narration, _hook_narration_max_chars)
            scenes.append(
                ScenePlan(
                    scene_id=idx,
                    narration_ko=narration,
                    visual_prompt_en=visual_prompt,
                    target_sec=target_sec,
                    structure_role=structure_role,
                )
            )
        return title, scenes

    def run(
        self,
        topic: str,
        research_context: Any | None = None,
        structure_outline: Any | None = None,
    ) -> tuple[str, list[ScenePlan], str]:
        """
        대본 생성.

        Args:
            topic: 영상 주제
            research_context: ResearchContext 객체 (리서치 스텝 결과). None이면 리서치 없이 생성.
            structure_outline: StructureOutline 객체 (구성안). 있으면 씬 수+역할을 구성안에서 가져옴.

        Returns: (title, scene_plans, hook_pattern_name)
        """
        # Multi-provider fallback via LLMRouter (no longer OpenAI-only)
        # 구성안이 제공되면 씬 수를 구성안에서 가져옴
        if structure_outline and hasattr(structure_outline, "scenes") and structure_outline.scenes:
            scene_count = len(structure_outline.scenes)
        else:
            scene_count = self.config.project.default_scene_count
        # 채널별 duration 오버라이드 적용
        if self.channel_duration_override:
            # 채널 목표 ±5초 범위 (예: 45초 → [40, 50])
            ch_dur = self.channel_duration_override
            duration_range = (max(20, ch_dur - 5), ch_dur + 5)
        else:
            duration_range = self.config.video.target_duration_sec
        language = self.config.project.language
        tts_speed = self.config.providers.tts_speed
        char_min, char_max = self._target_char_range_per_scene(
            target_duration_sec=duration_range,
            scene_count=scene_count,
            tts_speed=tts_speed,
        )
        # Hook 패턴: 채널 고정 패턴 우선, 없으면 로테이션
        hook_pattern_name, hook_instruction = self._get_hook_pattern()
        # YPP: 톤 프리셋 로테이션
        tone_name, tone_guide = self._next_tone_preset()
        # YPP: 구조 프리셋 로테이션 (구성안이 있으면 구성안 우선)
        structure_block = ""
        if structure_outline and hasattr(structure_outline, "to_prompt_block"):
            # 구성안에서 역할 흐름 추출 → system prompt의 structure_flow로 사용
            preset_flow = [s.role for s in structure_outline.scenes]
            preset_name = "structure_outline"
            structure_block = structure_outline.to_prompt_block()
            logger.info(
                "[Hook] pattern=%s tone=%s structure=outline(%d scenes)",
                hook_pattern_name,
                tone_name,
                len(structure_outline.scenes),
            )
        else:
            preset_name, preset_flow = self._next_structure_preset()
            if preset_name:
                logger.info("[Hook] pattern=%s tone=%s structure=%s", hook_pattern_name, tone_name, preset_name)
            else:
                logger.info("[Hook] pattern=%s tone=%s", hook_pattern_name, tone_name)
        system_prompt = self._build_system_prompt(
            scene_count=scene_count,
            language=language,
            char_min=char_min,
            char_max=char_max,
            hook_instruction=hook_instruction,
            tone_guide=tone_guide,
            structure_flow=preset_flow,
            channel_key=self.channel_key,  # 채널별 페르소나 주입
        )

        # 리서치 컨텍스트 → 프롬프트 블록 변환
        research_block = ""
        if research_context is not None and hasattr(research_context, "to_prompt_block"):
            research_block = research_context.to_prompt_block()
            if research_block:
                logger.info("[Script] research context injected (%d chars)", len(research_block))

        best_result: tuple[str, list[ScenePlan]] | None = None
        best_error = float("inf")
        previous_total_sec: float | None = None

        for attempt in range(1, self.max_generation_attempts + 1):
            user_prompt = self._build_user_prompt(
                topic=topic,
                duration_range=duration_range,
                attempt=attempt,
                previous_total_sec=previous_total_sec,
                previous_scene_count=scene_count,
                research_block=research_block,
                structure_block=structure_block,
            )
            # Sprint 4.1: 대본 생성은 thinking_level='low' (빠른 속도)
            gen_thinking = self.config.providers.thinking_level
            payload = self.llm_router.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                thinking_level=gen_thinking,
            )

            # ── 패턴 #4: Pydantic 스키마 검증 ─────────────────────────────
            if isinstance(payload, dict):
                schema_errors = self._validate_script_schema(payload)
                if schema_errors:
                    logger.warning(
                        "[ScriptSchema] validation errors (attempt %d): %s",
                        attempt,
                        "; ".join(schema_errors[:3]),
                    )
                    # 스키마 에러가 있어도 기존 로직으로 파싱 시도 (graceful)

            # ── no_reliable_source 감지 (1차: 생성 단계) ─────────────────
            if isinstance(payload, dict) and payload.get("no_reliable_source"):
                reason = payload.get("reason", "LLM이 신뢰할 자료 부족으로 판단")
                logger.warning(
                    "[TopicUnsuitable] LLM self-reported: no_reliable_source=true | reason=%s",
                    reason,
                )
                raise TopicUnsuitableError(f"주제 '{topic}'에 대해 신뢰할 수 있는 자료가 부족합니다: {reason}")

            parsed = self.parse_script_payload(
                payload,
                scene_count=scene_count,
                target_duration_sec=duration_range,
                language=language,
                tts_speed=tts_speed,
            )
            total_sec = self.estimate_total_duration_sec(parsed[1])
            error = self._duration_error(total_sec, duration_range)
            if error < best_error:
                best_error = error
                best_result = parsed
            if error == 0.0:
                break
            previous_total_sec = total_sec

        if best_result is None:
            raise ValueError("Failed to generate a usable script.")

        # ── 패턴 #3: MARL 자기검증 (리서치 일관성 검증) ────────────────────
        if research_context is not None:
            title_out, scenes_out = best_result
            verification = self._verify_with_research(title_out, scenes_out, research_context)
            is_consistent = verification.get("consistent", True)
            issues = verification.get("issues", [])
            confidence = verification.get("confidence", 1.0)

            logger.info(
                "[MARL] verification: consistent=%s, confidence=%.2f, issues=%d",
                is_consistent,
                confidence,
                len(issues),
            )

            if not is_consistent and issues:
                logger.warning("[MARL] inconsistencies found: %s", "; ".join(issues[:3]))
                # 자동 수정 적용
                scenes_out = self._apply_verification_fixes(scenes_out, verification)
                best_result = (title_out, scenes_out)
                logger.info("[MARL] auto-fix applied, %d scenes patched", len(verification.get("fixes", [])))

        # 최종 추정 길이 사전 체크 + 초과 시 강제 Truncation
        final_total = self.estimate_total_duration_sec(best_result[1])
        target_min, target_max = duration_range
        # YouTube Shorts 상한 (45초) — 시청 완료율 최적화 + 60초 플랫폼 제한 내 안전 여유
        _shorts_hard_limit = 45
        effective_max = min(target_max, _shorts_hard_limit)

        if final_total > effective_max:
            logger.warning(
                "[ScriptDuration] estimated %.1fs > limit %ds — truncating narrations",
                final_total,
                effective_max,
            )
            title_out, scenes_out = best_result
            scenes_out = self._truncate_to_fit(scenes_out, effective_max, language, tts_speed)
            best_result = (title_out, scenes_out)
            final_total = self.estimate_total_duration_sec(scenes_out)
            logger.info("[ScriptDuration] after truncation: %.1fs", final_total)
        elif final_total < target_min:
            logger.warning(
                "[ScriptDuration] estimated %.1fs < target %ds (actual TTS may be shorter)", final_total, target_min
            )
        else:
            logger.info("[ScriptDuration] OK: estimated %.1fs (target %d-%ds)", final_total, target_min, target_max)

        # 품질 검토 (활성화된 경우 — Sprint 4: 채널별 차별화)
        if self.config.project.script_review_enabled:
            _, required_keys, effective_min_score = self._build_review_system()
            title_out, scenes_out = best_result
            try:
                review = self._review_script(title_out, scenes_out)
                scores = {k: review.get(k, 0) for k in required_keys}
                scores_str = " ".join(f"{k}={scores[k]}" for k in required_keys)
                logger.info(
                    "[ScriptReview] %s / min=%d (channel=%s) | %s",
                    scores_str,
                    effective_min_score,
                    self.channel_key or "default",
                    review.get("feedback", ""),
                )

                # ── no_reliable_source 감지 (2차: 리뷰 단계) ────────────
                verifiability = int(review.get("verifiability_score", 10))
                if verifiability < 4:
                    logger.warning(
                        "[TopicUnsuitable] verifiability_score=%d < 4 → 자료 부족 주제",
                        verifiability,
                    )
                    raise TopicUnsuitableError(
                        f"주제 '{topic}'의 verifiability_score={verifiability} "
                        f"(4 미만) — 검증 가능한 자료 부족: {review.get('feedback', '')}"
                    )

                if not self._passes_review(review, effective_min_score):
                    # 채널 특화 피드백을 추가해 1회 재생성 시도
                    feedback = review.get("feedback", "")
                    # 미달 점수 키 구체적 안내
                    weak_keys = [k for k in required_keys if int(review.get(k, 0)) < effective_min_score]
                    weak_hint = f"Weak dimensions: {', '.join(weak_keys)}." if weak_keys else ""
                    retry_prompt = (
                        self._build_user_prompt(
                            topic=topic,
                            duration_range=duration_range,
                            attempt=self.max_generation_attempts + 1,
                            previous_total_sec=None,
                            previous_scene_count=scene_count,
                        )
                        + f"\nQuality feedback to fix: {feedback}\n{weak_hint}\n"
                    )
                    # Sprint 4.1: 재생성은 thinking_level='medium' (품질↑ + 속도 균형)
                    retry_payload = self.llm_router.generate_json(
                        system_prompt=system_prompt,
                        user_prompt=retry_prompt,
                        temperature=0.7,
                        thinking_level="medium",
                    )
                    retry_parsed = self.parse_script_payload(
                        retry_payload,
                        scene_count=scene_count,
                        target_duration_sec=duration_range,
                        language=language,
                        tts_speed=tts_speed,
                    )
                    best_result = retry_parsed
                    logger.info(
                        "[ScriptReview] 채널 '%s' 기준 재생성 완료",
                        self.channel_key or "default",
                    )
            except Exception as exc:
                logger.warning("[ScriptReview] scoring failed (skipped): %s", exc)

        # ── CTA/Closing 금지어 검증 ────────────────────────────────────────────
        final_title, final_scenes = best_result
        ending_scenes = [s for s in final_scenes if s.structure_role in ("cta", "closing")]
        for ending_scene in ending_scenes:
            violations = self._validate_cta(ending_scene.narration_ko, self._cta_forbidden_words)
            if violations:
                logger.warning(
                    "[CTAGuard] Scene %d (%s) contains forbidden words: %s — consider revising.",
                    ending_scene.scene_id,
                    ending_scene.structure_role,
                    ", ".join(repr(v) for v in violations),
                )

        # ── 페르소나 매칭 스코어 ─────────────────────────────────────────────
        if self.channel_key:
            persona_score = self._score_persona_match(final_scenes, self.channel_key, self._persona_keywords)
            log_level = logging.WARNING if persona_score < 0.4 else logging.INFO
            logger.log(
                log_level,
                "[PersonaScore] channel=%s score=%.3f%s",
                self.channel_key,
                persona_score,
                " ← LOW: persona drift detected" if persona_score < 0.4 else "",
            )

        return (*best_result, hook_pattern_name)
