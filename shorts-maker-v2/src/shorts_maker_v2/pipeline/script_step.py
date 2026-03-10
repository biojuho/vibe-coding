from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.providers.llm_router import LLMRouter


class ScriptStep:
    duration_estimate_chars_per_sec = 8.5  # 실측 TTS(speed=1.05) 기준 보정
    max_generation_attempts = 3

    # 4가지 Hook 패턴 (로테이션)
    HOOK_PATTERNS: list[tuple[str, str]] = [
        ("shocking_stat", "Open with a shocking statistic or number that makes the viewer stop scrolling."),
        ("relatable_frustration", "Open with a relatable frustration or common pain point the viewer instantly identifies with."),
        ("counterintuitive_question", "Open with a counterintuitive or provocative question that challenges common assumptions."),
        ("myth_busting", "Open by stating a popular misconception, then immediately hint that it's wrong."),
    ]
    _hook_counter: int = 0

    # YPP 대응: 5가지 톤 프리셋 (로테이션)
    TONE_PRESETS: list[tuple[str, str]] = [
        ("professor", "대학 강의처럼 차분하고 논리적인 톤. '~입니다' 체. 근거와 데이터를 중시."),
        ("friend", "카톡으로 친구에게 말하듯 편한 반말. '~거든?' '~잖아' 사용. 일상 비유 활용."),
        ("storyteller", "옛날이야기 들려주듯 서사적. '어느 날...' '그런데 말이죠' 사용. 기승전결."),
        ("news_anchor", "뉴스 앵커처럼 객관적이고 단정한 톤. 사실 위주. 감정 절제."),
        ("excited_fan", "놀라운 발견을 공유하는 팬처럼 흥분된 톤. '대박!' '진짜?' 감탄사 활용."),
    ]
    _tone_counter: int = 0
    _structure_counter: int = 0  # YPP: 구조 프리셋 로테이션

    def __init__(self, config: AppConfig, llm_router: LLMRouter, openai_client: Any | None = None,
                 channel_hook_pattern: str | None = None,
                 channel_duration_override: int | None = None):
        self.config = config
        self.llm_router = llm_router
        # Keep openai_client reference for TTS/image (non-LLM) tasks
        self.openai_client = openai_client
        # 채널별 Hook 패턴 고정 (없으면 None → 로테이션 사용)
        # 예: 'shocking_stat', 'relatable_frustration', 'myth_busting', 'counterintuitive_question'
        self.channel_hook_pattern: str | None = channel_hook_pattern
        # 채널별 목표 영상 길이 (초). None이면 config.video.target_duration_sec 사용
        self.channel_duration_override: int | None = channel_duration_override

    @classmethod
    def from_channel_profile(cls, config: AppConfig, llm_router: LLMRouter,
                              channel_profile: dict,
                              openai_client: Any | None = None) -> "ScriptStep":
        """
        channel_profiles.yaml의 채널 딕셔너리를 받아 hook_pattern을 자동 적용합니다.

        예::
            profile = yaml.safe_load(open('channel_profiles.yaml'))['channels']['ai_tech']
            step = ScriptStep.from_channel_profile(config, llm_router, profile)
        """
        hook_pattern = channel_profile.get('hook_pattern', None)
        duration_override = channel_profile.get('target_duration_sec', None)
        return cls(config, llm_router, openai_client=openai_client,
                   channel_hook_pattern=hook_pattern,
                   channel_duration_override=duration_override)

    def _next_hook_pattern(self) -> tuple[str, str]:
        """Hook 패턴 로테이션. 호출할 때마다 다음 패턴 반환."""
        idx = ScriptStep._hook_counter % len(self.HOOK_PATTERNS)
        ScriptStep._hook_counter += 1
        return self.HOOK_PATTERNS[idx]

    def _get_hook_pattern(self) -> tuple[str, str]:
        """
        채널별 고정 패턴이 있으면 해당 패턴을 반환,
        없으면 로테이션 패턴을 반환합니다.
        """
        if self.channel_hook_pattern:
            # 채널쪽 HOOK_PATTERNS에서 이름 일치 탐색
            for name, instruction in self.HOOK_PATTERNS:
                if name == self.channel_hook_pattern:
                    logger.info("[Hook] 채널 고정 패턴 적용: %s", name)
                    return name, instruction
            logger.warning(
                "[Hook] channel_hook_pattern '%s'를 완성 합니가에서 대만 수 없어 로테이션으로 폴백.",
                self.channel_hook_pattern,
            )
        return self._next_hook_pattern()

    def _next_tone_preset(self) -> tuple[str, str]:
        """톤 프리셋 로테이션. 호출할 때마다 다음 톤 반환."""
        idx = ScriptStep._tone_counter % len(self.TONE_PRESETS)
        ScriptStep._tone_counter += 1
        return self.TONE_PRESETS[idx]

    def _next_structure_preset(
        self,
    ) -> tuple[str, list[str]] | tuple[None, None]:
        """구조 프리셋 로테이션. config에 프리셋이 없으면 (None, None)."""
        presets = self.config.project.structure_presets
        if not presets:
            return None, None
        names = list(presets.keys())
        idx = ScriptStep._structure_counter % len(names)
        ScriptStep._structure_counter += 1
        name = names[idx]
        return name, presets[name]

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
    def estimate_narration_duration_sec(
        cls,
        narration: str,
        *,
        language: str = "ko-KR",
        tts_speed: float = 1.0,
    ) -> float:
        normalized = re.sub(r"\s+", " ", narration).strip()
        if not normalized:
            return 0.0

        hangul_chars = len(re.findall(r"[가-힣]", normalized))
        latin_tokens = len(re.findall(r"[A-Za-z0-9]+", normalized))
        punctuation_pauses = len(re.findall(r"[.!?…,:;]", normalized))

        weighted_units = hangul_chars + (latin_tokens * 2.2)
        spoken_sec = weighted_units / cls.duration_estimate_chars_per_sec
        pause_sec = punctuation_pauses * 0.22
        speed = max(0.7, float(tts_speed))

        estimated = (spoken_sec + pause_sec) / speed
        if language.lower().startswith("ko"):
            estimated += 0.15
        return round(max(1.2, estimated), 3)

    @staticmethod
    def estimate_total_duration_sec(scene_plans: list[ScenePlan]) -> float:
        return round(sum(scene.target_sec for scene in scene_plans), 3)

    @classmethod
    def _target_char_range_per_scene(
        cls,
        *,
        target_duration_sec: tuple[int, int],
        scene_count: int,
        tts_speed: float,
    ) -> tuple[int, int]:
        total_min, total_max = target_duration_sec
        min_chars = ((total_min * cls.duration_estimate_chars_per_sec) * max(0.7, tts_speed)) / max(scene_count, 1)
        max_chars = ((total_max * cls.duration_estimate_chars_per_sec) * max(0.7, tts_speed)) / max(scene_count, 1)
        return max(16, math.floor(min_chars)), max(24, math.ceil(max_chars))

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
                raw_scene.get("narration_ko")
                or raw_scene.get("narration")
                or raw_scene.get("voiceover")
                or ""
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
            if raw_role in ("hook", "body", "cta"):
                structure_role = raw_role
            elif idx == 1:
                structure_role = "hook"
            elif idx == total:
                structure_role = "cta"
            else:
                structure_role = "body"
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

    def _build_system_prompt(
        self,
        *,
        scene_count: int,
        language: str,
        char_min: int,
        char_max: int,
        hook_instruction: str = "",
        tone_guide: str = "",
        structure_flow: list[str] | None = None,
    ) -> str:
        last = scene_count
        body_count = scene_count - 2  # hook(1) + cta(1)
        # 역할별 자막 길이 목표 (Hook/CTA는 짧고 임팩트, Body는 풍부하게)
        hook_max = max(30, int(char_max * 0.60))
        body_min = char_min
        body_max = int(char_max * 1.20)
        cta_max = max(30, int(char_max * 0.60))
        hook_rule = hook_instruction or "Open with a shocking stat, a relatable frustration, or a counterintuitive question."

        # YPP: 톤 가이드 섹션
        tone_section = ""
        if tone_guide:
            tone_section = (
                "\n"
                "Tone & Voice Guide (MUST follow throughout ALL scenes):\n"
                f"  - {tone_guide}\n"
                "  - Apply this tone consistently in narration_ko for every scene.\n"
            )

        # 프리셋 기반 vs 기본 구조 섹션
        if structure_flow:
            structure_section = (
                "  Scene flow: " + " → ".join(
                    f'{i+1}:{role}' for i, role in enumerate(structure_flow)
                ) + "\n"
                "  Use these roles as structure_role values for each scene.\n"
            )
        else:
            structure_section = (
                f'  Scene 1        → structure_role: "hook"\n'
                f'  Scenes 2-{last - 1}  → structure_role: "body"  ({body_count} scenes)\n'
                f'  Scene {last}        → structure_role: "cta"\n'
            )

        return (
            "You are a YouTube Shorts scriptwriter. You write in the Hook-Body-CTA format.\n"
            "Output ONLY valid JSON.\n"
            "Schema:\n"
            "{\n"
            '  "title": "string",\n'
            '  "scenes": [\n'
            '    {\n'
            '      "structure_role": "hook" | "body" | "cta",\n'
            '      "narration_ko": "string",\n'
            '      "visual_prompt_en": "string",\n'
            '      "estimated_seconds": number\n'
            '    }\n'
            "  ]\n"
            "}\n"
            f"Structure — exactly {scene_count} scenes:\n"
            + structure_section
            + f"{tone_section}"
            "\n"
            "Hook rules:\n"
            f"  - {hook_rule}\n"
            "  - Must stop the scroll within 3 seconds. One or two punchy sentences.\n"
            f"  - narration_ko: up to {hook_max} Korean characters (short and punchy).\n"
            "\n"
            "Body rules:\n"
            "  - Build depth in this order: analogy first → scientific fact/data → cause or solution.\n"
            "  - Each body scene naturally leads into the next. No bullet points.\n"
            f"  - narration_ko: {body_min}-{body_max} Korean characters (detailed and flowing).\n"
            "\n"
            "CTA rules:\n"
            "  - Suggest ONE specific, immediate real-world action the viewer can do RIGHT NOW.\n"
            "  - Do NOT mention subscriptions, likes, follows, or any channel actions.\n"
            "  - After the action, add one sentence of 'Creator Insight' — a personal observation\n"
            "    like '이걸 알고 나서 제가 직접 OO을 바꿔봤는데, 확실히 달라지더라고요' to show unique perspective.\n"
            f"  - narration_ko: up to {cta_max} Korean characters (brief and direct).\n"
            "\n"
            "General rules:\n"
            f"  - narration_ko must be in {language}\n"
            f"  - return exactly {scene_count} scenes\n"
            "  - narration must sound natural when spoken aloud, not like bullet points\n"
            "  - estimated_seconds must realistically match the spoken length of that scene\n"
            "  - visual_prompt_en: English only, describe camera angle, lighting, action, artistic style for DALL-E 3\n"
            "  - visual_prompt_en MUST be DALL-E safe: NO medical imagery, anatomical details, injuries, blood,\n"
            "    violence, weapons, drugs, or explicit body parts. Use abstract metaphors instead.\n"
            "    (e.g. 'a person resting on a couch' instead of 'sedentary lifestyle causing muscle atrophy')\n"
            "  - do not include markdown"
        )

    def _build_user_prompt(
        self,
        *,
        topic: str,
        duration_range: tuple[int, int],
        attempt: int,
        previous_total_sec: float | None,
        previous_scene_count: int | None,
    ) -> str:
        target_min, target_max = duration_range
        target_mid = (target_min + target_max) / 2
        prompt = (
            f"Topic: {topic}\n"
            f"Target total duration: {target_min}-{target_max} seconds.\n"
            f"Target midpoint: about {target_mid:.1f} seconds.\n"
            "Write a Hook-Body-CTA script for YouTube Shorts:\n"
            "  Hook  — Open with a surprising fact or relatable problem. Stop the scroll instantly.\n"
            "  Body  — Guide through analogy → data/fact → cause or solution. Build naturally.\n"
            "  CTA   — One specific action the viewer can do right now. No subscription requests.\n"
        )
        if attempt > 1 and previous_total_sec is not None:
            if previous_total_sec < target_min:
                prompt += (
                    f"The previous draft was too short at about {previous_total_sec:.1f} seconds.\n"
                    "Make each scene narration meaningfully longer with more spoken detail.\n"
                )
            elif previous_total_sec > target_max:
                prompt += (
                    f"The previous draft was too long at about {previous_total_sec:.1f} seconds.\n"
                    "Tighten each scene narration while keeping the same clarity.\n"
                )
            if previous_scene_count is not None:
                prompt += f"Keep exactly {previous_scene_count} scenes unless that prevents the duration target.\n"
        return prompt

    @staticmethod
    def _duration_error(total_sec: float, duration_range: tuple[int, int]) -> float:
        target_mid = (duration_range[0] + duration_range[1]) / 2
        if duration_range[0] <= total_sec <= duration_range[1]:
            return 0.0
        return abs(total_sec - target_mid)

    # ── 스크립트 품질 검토 ────────────────────────────────────────────────────

    _REVIEW_SYSTEM = (
        "You are a YouTube Shorts script quality evaluator. "
        "Score the given script on three dimensions from 1-10:\n"
        "  hook_score : How well does the Hook stop the scroll? (1=boring, 10=irresistible)\n"
        "  flow_score : How naturally does the Body build and connect? (1=choppy, 10=seamless)\n"
        "  cta_score  : How clear and actionable is the CTA? (1=vague, 10=immediately doable)\n"
        "Also provide a brief 'feedback' string (max 80 chars) with the main weakness.\n"
        "Output ONLY valid JSON: {\"hook_score\": n, \"flow_score\": n, \"cta_score\": n, \"feedback\": \"...\"}"
    )

    def _review_script(
        self, title: str, scenes: list[ScenePlan]
    ) -> dict[str, Any]:
        """GPT로 생성된 스크립트 품질 채점."""
        script_text = f"Title: {title}\n\n"
        for s in scenes:
            script_text += f"[{s.structure_role.upper()}] {s.narration_ko}\n"
        result = self.llm_router.generate_json(
            system_prompt=self._REVIEW_SYSTEM,
            user_prompt=script_text,
            temperature=0.2,
        )
        return result if isinstance(result, dict) else {}

    def _passes_review(self, review: dict[str, Any], min_score: int) -> bool:
        """세 점수 모두 min_score 이상이면 통과."""
        return all(
            int(review.get(k, 0)) >= min_score
            for k in ("hook_score", "flow_score", "cta_score")
        )

    def _truncate_to_fit(
        self,
        scenes: list[ScenePlan],
        max_total_sec: float,
        language: str,
        tts_speed: float,
    ) -> list[ScenePlan]:
        """
        총 길이를 max_total_sec에 맞추기 위해 각 장면의 나레이션을 강제로 자릅니다.
        """
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
            
            # 새로운 목표 시간에 맞는 최대 문자 수 계산
            # estimate_narration_duration_sec의 역산
            # estimated = (spoken_sec + pause_sec) / speed
            # spoken_sec = estimated * speed - pause_sec
            # weighted_units = spoken_sec * cls.duration_estimate_chars_per_sec
            
            # 대략적인 역산 (정확한 역산은 복잡하므로 근사치 사용)
            # TTS 속도와 언어 보정을 고려하여 대략적인 문자당 시간으로 계산
            # cls.duration_estimate_chars_per_sec는 1.05배속 기준이므로, 실제 speed를 곱해줘야 함
            effective_chars_per_sec = self.duration_estimate_chars_per_sec / max(0.7, tts_speed)
            
            # 구두점 보정은 무시하고 단순 문자 수로만 계산
            max_chars_for_new_target = int(new_target_sec * effective_chars_per_sec)

            truncated_narration = original_narration
            if len(original_narration) > max_chars_for_new_target:
                truncated_narration = original_narration[:max_chars_for_new_target].rsplit(' ', 1)[0] + '...' if ' ' in original_narration[:max_chars_for_new_target] else original_narration[:max_chars_for_new_target] + '...'
                # 너무 짧아지는 것을 방지 (최소 10자)
                if len(truncated_narration) < 10:
                    truncated_narration = original_narration[:10] + '...' if len(original_narration) > 10 else original_narration

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

    def run(self, topic: str) -> tuple[str, list[ScenePlan], str]:
        """
        대본 생성.
        Returns: (title, scene_plans, hook_pattern_name)
        """
        # Multi-provider fallback via LLMRouter (no longer OpenAI-only)
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
        # YPP: 구조 프리셋 로테이션
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
        )

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
            )
            payload = self.llm_router.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
            )
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

        # 최종 추정 길이 사전 체크 + 초과 시 강제 Truncation
        final_total = self.estimate_total_duration_sec(best_result[1])
        target_min, target_max = duration_range
        # YouTube Shorts 하드 리밋 (60초) — 채널 목표보다 이게 더 중요
        SHORTS_HARD_LIMIT = 60
        effective_max = min(target_max, SHORTS_HARD_LIMIT)

        if final_total > effective_max:
            logger.warning(
                "[ScriptDuration] estimated %.1fs > limit %ds — truncating narrations",
                final_total, effective_max,
            )
            title_out, scenes_out = best_result
            scenes_out = self._truncate_to_fit(scenes_out, effective_max, language, tts_speed)
            best_result = (title_out, scenes_out)
            final_total = self.estimate_total_duration_sec(scenes_out)
            logger.info("[ScriptDuration] after truncation: %.1fs", final_total)
        elif final_total < target_min:
            logger.warning("[ScriptDuration] estimated %.1fs < target %ds (actual TTS may be shorter)", final_total, target_min)
        else:
            logger.info("[ScriptDuration] OK: estimated %.1fs (target %d-%ds)", final_total, target_min, target_max)

        # 품질 검토 (활성화된 경우)
        if self.config.project.script_review_enabled:
            min_score = self.config.project.script_review_min_score
            title_out, scenes_out = best_result
            try:
                review = self._review_script(title_out, scenes_out)
                scores = {k: review.get(k, 0) for k in ("hook_score", "flow_score", "cta_score")}
                logger.info(
                    "[ScriptReview] hook=%s flow=%s cta=%s / min=%d | %s",
                    scores["hook_score"], scores["flow_score"], scores["cta_score"],
                    min_score, review.get("feedback", ""),
                )
                if not self._passes_review(review, min_score):
                    # 피드백을 추가해 1회 재생성 시도
                    feedback = review.get("feedback", "")
                    retry_prompt = self._build_user_prompt(
                        topic=topic,
                        duration_range=duration_range,
                        attempt=self.max_generation_attempts + 1,
                        previous_total_sec=None,
                        previous_scene_count=scene_count,
                    ) + f"\nQuality feedback to fix: {feedback}\n"
                    retry_payload = self.llm_router.generate_json(
                        system_prompt=system_prompt,
                        user_prompt=retry_prompt,
                        temperature=0.7,
                    )
                    retry_parsed = self.parse_script_payload(
                        retry_payload,
                        scene_count=scene_count,
                        target_duration_sec=duration_range,
                        language=language,
                        tts_speed=tts_speed,
                    )
                    best_result = retry_parsed
                    logger.info("[ScriptReview] regeneration complete")
            except Exception as exc:
                logger.warning("[ScriptReview] scoring failed (skipped): %s", exc)

        return (*best_result, hook_pattern_name)
