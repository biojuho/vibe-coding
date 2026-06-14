from __future__ import annotations

import copy
import logging
import math
import re
import threading
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _load_script_step_locale_bundle(language_code: str) -> dict[str, Any]:
    """Load script_step.yaml bundle for the given language code from locales/."""
    try:
        current_dir = Path(__file__).resolve().parent
        yaml_path = current_dir.parent.parent.parent / "locales" / language_code / "script_step.yaml"
        if yaml_path.exists():
            with yaml_path.open(encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
    except Exception as exc:
        logger.warning("Failed to load locale bundle for %s: %s", language_code, exc)
    return {}


def _deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_tone_presets(raw_tone_presets: Any) -> list[tuple[str, str]]:
    if not isinstance(raw_tone_presets, list):
        return []

    normalized_tones: list[tuple[str, str]] = []
    for item in raw_tone_presets:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        guide = str(item.get("guide", "")).strip()
        if name and guide:
            normalized_tones.append((name, guide))
    return normalized_tones


def _normalize_string_tuple(raw_values: Any) -> tuple[str, ...]:
    if not isinstance(raw_values, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in raw_values if str(item).strip())


def _merge_channel_persona(
    base_persona: dict[str, dict[str, str]],
    raw_persona: Any,
) -> dict[str, dict[str, str]]:
    merged_persona = copy.deepcopy(base_persona)
    if not isinstance(raw_persona, dict):
        return merged_persona

    for key, value in raw_persona.items():
        if not isinstance(value, dict):
            continue
        if key not in merged_persona:
            merged_persona[key] = {}
        merged_persona[key].update(value)
    return merged_persona


def _merge_persona_keywords(
    base_keywords: dict[str, tuple[str, ...]],
    raw_keywords: Any,
) -> dict[str, tuple[str, ...]]:
    merged_keywords = copy.deepcopy(base_keywords)
    if not isinstance(raw_keywords, dict):
        return merged_keywords

    for key, value in raw_keywords.items():
        normalized_keywords = _normalize_string_tuple(value) if isinstance(value, list) else ()
        if normalized_keywords:
            merged_keywords[str(key)] = normalized_keywords
    return merged_keywords


def _merge_prompt_field_names(
    base_field_names: dict[str, str],
    raw_field_names: Any,
) -> dict[str, str]:
    merged_field_names = copy.deepcopy(base_field_names)
    if not isinstance(raw_field_names, dict):
        return merged_field_names

    for key, value in raw_field_names.items():
        normalized_key = str(key).strip()
        normalized_value = str(value).strip()
        if normalized_key in merged_field_names and normalized_value:
            merged_field_names[normalized_key] = normalized_value
    return merged_field_names


def _merge_channel_review_criteria(
    base_criteria: dict[str, dict[str, Any]],
    raw_criteria: Any,
) -> dict[str, dict[str, Any]]:
    merged_criteria = copy.deepcopy(base_criteria)
    if not isinstance(raw_criteria, dict):
        return merged_criteria

    for key, value in raw_criteria.items():
        if not isinstance(value, dict):
            continue
        normalized_criteria = copy.deepcopy(merged_criteria.get(str(key), {}))
        extra_dimensions = value.get("extra_dimensions")
        if isinstance(extra_dimensions, str) and extra_dimensions.strip():
            normalized_criteria["extra_dimensions"] = extra_dimensions
        normalized_extra_keys = _normalize_string_tuple(value.get("extra_keys"))
        if normalized_extra_keys:
            normalized_criteria["extra_keys"] = normalized_extra_keys
        min_score_override = value.get("min_score_override")
        if isinstance(min_score_override, (int, float)):
            normalized_criteria["min_score_override"] = int(min_score_override)
        context_note = value.get("context_note")
        if isinstance(context_note, str) and context_note.strip():
            normalized_criteria["context_note"] = context_note
        if normalized_criteria:
            merged_criteria[str(key)] = normalized_criteria
    return merged_criteria


class ScriptPromptsMixin:
    """Prompt building, tone/hook pattern rotation, duration estimation.

    Designed to be mixed into ScriptStep. Accesses self.config, self.channel_key, etc.
    """

    duration_estimate_chars_per_sec = 2.8  # 실측 SSML+edge-tts 보정: 씬별 prosody/emphasis/break 오버헤드 반영

    # 5가지 Hook 패턴 (로테이션) — cognitive_dissonance는 topic_angle_generator의 주요 패턴
    HOOK_PATTERNS: list[tuple[str, str]] = [
        (
            "cognitive_dissonance",
            "Open with a result that defies expectation: [반전 결과] + [이유]. Make viewers think '어? 왜?' instantly.",
        ),
        ("shocking_stat", "Open with a shocking statistic or number that makes the viewer stop scrolling."),
        (
            "relatable_frustration",
            "Open with a relatable frustration or common pain point the viewer instantly identifies with.",
        ),
        (
            "counterintuitive_question",
            "Open with a counterintuitive or provocative question that challenges common assumptions.",
        ),
        ("myth_busting", "Open by stating a popular misconception, then immediately hint that it's wrong."),
    ]
    _counter_lock = threading.Lock()
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

    # ── 채널별 페르소나 정의 ──────────────────────────────────────────────────
    _CHANNEL_PERSONA: dict[str, dict[str, str]] = {
        "ai_tech": {
            "role_description": "You are a tech journalist delivering breaking AI/tech news in crisp, exciting Korean.",
            "tone": (
                "Tone: Fast-paced, precise, data-driven. Use present tense. "
                "Every sentence should feel like a revelation. No filler phrases."
            ),
            "forbidden": (
                "Forbidden: Vague hype without specifics (e.g. '놀라운 기술' without naming it), "
                "'사실', '실제로' as filler, melodramatic exaggeration."
            ),
            "required": (
                "Required: At least 1 specific number, date, or product name in the body. "
                "Hook must name the exact technology or company."
            ),
        },
        "history": {
            "role_description": "You are a dramatic storyteller bringing history to life in vivid Korean narrative.",
            "tone": (
                "Tone: Cinematic, suspenseful. Use past tense for events. "
                "Build tension through scene-setting and unexpected plot twists. "
                "Speak as if recounting an epic tale."
            ),
            "forbidden": (
                "Forbidden: Dry chronological lists without drama, "
                "modern slang that feels anachronistic, generic openings like '오늘은 OO에 대해'."
            ),
            "required": (
                "Required: The hook must introduce an unexpected paradox or reversal "
                "(e.g. the famous hero was actually a villain). "
                "Include at least one plot twist in the body."
            ),
        },
        "psychology": {
            "role_description": "You are a warm, empathetic therapist-friend sharing psychological insights in conversational Korean.",  # noqa: E501
            "tone": (
                "Tone: Gentle, validating, emotionally safe. Use second person '당신' sparingly. "
                "Speak as if you completely understand the viewer's inner world. "
                "Normalize their feelings before offering insight."
            ),
            "forbidden": (
                "Forbidden: Cold clinical terminology without emotional warmth, "
                "judgmental framing, rushed advice without empathy first."
            ),
            "required": (
                "Required: Hook must make the viewer feel 'someone finally understands me'. "
                "Body must validate before informing. "
                "CTA must be gentle and optional (never commanding)."
            ),
        },
        "space": {
            "role_description": "You are a cosmos explorer conveying the mind-bending scale and wonder of the universe in poetic Korean.",  # noqa: E501
            "tone": (
                "Tone: Awe-inspiring, contemplative, occasionally poetic. "
                "Use analogies to convey cosmic scale (e.g. 지구가 모래알이라면 태양계는 축구장). "
                "End each thought with a sense of wonder."
            ),
            "forbidden": (
                "Forbidden: Mundane framing without cosmic perspective, "
                "technical jargon without analogy, closing without an awe-inspiring thought."
            ),
            "required": (
                "Required: Include at least one scale analogy in the body. "
                "Hook must immediately convey something that shatters the viewer's sense of scale or reality."
            ),
        },
        "health": {
            "role_description": "You are a knowledgeable, caring health guide sharing evidence-based tips in warm, encouraging Korean.",  # noqa: E501
            "tone": (
                "Tone: Warm, encouraging, trustworthy. Never alarmist. "
                "Frame health information as empowering insights, not warnings. "
                "Sound like a supportive friend who happens to know a lot about health."
            ),
            "forbidden": (
                "Forbidden: Alarmist language ('당신은 지금 위험합니다'), "
                "unverified medical claims, scare tactics, any claim not backed by consensus science."
            ),
            "required": (
                "Required: Cite the basis of claims (e.g. '연구에 따르면', 'WHO 권고안'). "
                "CTA must be a single safe, immediately actionable habit."
            ),
        },
    }

    # ── YPP CTA 금지어 목록 ──────────────────────────────────────────────────
    _CTA_FORBIDDEN_WORDS: tuple[str, ...] = (
        "구독",
        "좋아요",
        "subscribe",
        "like",
        "알림",
        "벨",
        "bell",
        "follow",
        "팔로우",
        "눌러",
        "눌러주",
        "부탁",
        "잊지 마",
        "잊지마",
    )

    # ── 채널별 페르소나 키워드 (스코어링용) ──────────────────────────────────
    # T-AB027: 페르소나 키워드 품질 개선
    # - ai_tech: "%" (기호 — 텍스트 매칭 불가), "실제로" (범용 필러) → "LLM", "자동화"
    # - psychology: "당신" (모든 2인칭 콘텐츠에 등장 → 신호 약화) → "뇌"
    # - health: "연구" (ai_tech와 중복 → 채널간 오염), "효과" (범용) → "예방", "질병"
    _PERSONA_KEYWORDS: dict[str, tuple[str, ...]] = {
        "ai_tech": ("AI", "데이터", "기술", "모델", "LLM", "연구", "자동화", "개발", "알고리즘", "소프트웨어"),
        "psychology": ("마음", "감정", "공감", "뇌", "느끼", "심리", "이해", "관계", "자신", "불안"),
        "history": ("년", "시대", "왕", "전쟁", "역사", "당시", "사건", "제국", "혁명", "문명"),
        "space": ("우주", "광년", "행성", "은하", "태양", "지구", "빛", "별", "블랙홀", "망원경"),
        "health": ("건강", "예방", "권고", "습관", "질병", "몸", "영양", "운동", "식단", "수면"),
    }

    _PROMPT_FIELD_NAMES: dict[str, str] = {
        "narration": "narration_ko",
        "visual_prompt": "visual_prompt_en",
    }

    _PROMPT_COPY: dict[str, str] = {
        "system_intro": (
            "You are a YouTube Shorts scriptwriter. You write in the Hook-Body-Closing format.\n"
            "Output ONLY valid JSON.\n"
            "Schema:\n"
            "{\n"
            '  "title": "string",\n'
            '  "scenes": [...],\n'
            '  "no_reliable_source": false\n'
            "}\n"
        ),
        "source_rule": (
            "CRITICAL SOURCE RULE:\n"
            "  - You MUST base all claims on verifiable facts you are confident about.\n"
            "  - If you cannot recall specific data, studies, or established facts for this topic,\n"
            "    DO NOT invent or guess. Instead, return:\n"
            '    {"title": "", "scenes": [], "no_reliable_source": true,\n'
            '     "reason": "<why no reliable source was found>"}\n'
            "  - It is FAR BETTER to admit 'I don't have reliable data' than to hallucinate facts.\n"
            "  - For each factual claim in the Body, mentally ask: 'Can a viewer Google this and confirm it?'\n"
            "    If the answer is no, either remove the claim or flag no_reliable_source.\n"
        ),
        "hook_rules": (
            "Hook rules:\n"
            "  - {hook_rule}\n"
            "  - Stop the scroll within 3 seconds. One or two punchy spoken sentences.\n"
            "  - {narration_field}: up to {hook_max} English characters (short and punchy).\n"
        ),
        "hook_rules_ko": (
            "Korean Hook Quality Rules (CRITICAL — the Korean hook scorer rejects hooks scoring below 0.6):\n"
            "  - The hook MUST include at least 2 of these 4 elements:\n"
            "    1) A specific number (year, %, count, scale — e.g. '38조 개', '0.3초', '1996년')\n"
            "    2) A direct question or shock word\n"
            "       (놀랍게도, 충격적, 진실, 비밀, 사실은, 어떻게, 왜, 진짜)\n"
            "    3) An information gap framing\n"
            "       (~인 이유, ~하는 방법, ~의 비결, ~의 원인, ~의 진실)\n"
            "    4) A specific proper noun (named person, org, place, brand —\n"
            "       e.g. NASA, MIT, 하버드, 일론 머스크, 1500년대 베네치아,\n"
            "            GPT-4o, OpenAI, 구글, 삼성, 딥마인드, 애플, KAIST)\n"
            "  - Vague openers are FORBIDDEN: '오늘은', '오늘의', '이번에는', '이번엔',\n"
            "    '여러분', '우리는', '우리가', '안녕하세요', '지금부터', '잠깐만',\n"
            "    '~에 대해 알아볼게요' — start with the most concrete element instead.\n"
            "  - Keep {narration_field} ≤ 25 characters when possible (the brevity scorer\n"
            "    rewards ≤15 chars maximally and penalizes ≥40 chars).\n"
        ),
        "body_rules": (
            "Body rules:\n"
            "  - Build depth in this order: analogy first -> fact or data -> cause or solution.\n"
            "  - Each body scene should naturally flow into the next. No bullet points.\n"
            "  - {narration_field}: {body_min}-{body_max} English characters (detailed and spoken).\n"
        ),
        "cta_rules": (
            "CTA rules:\n"
            "  - Suggest ONE specific, immediate real-world action the viewer can do right now.\n"
            "  - Do NOT mention subscriptions, likes, follows, or channel actions.\n"
            "  - After the action, add one sentence of creator insight, like a personal takeaway or observation.\n"
            "  - {narration_field}: up to {cta_max} English characters (brief and direct).\n"
        ),
        "closing_rules": (
            "Closing rules (IMPORTANT — this channel uses quiet endings, NOT CTAs):\n"
            "  - End with a contemplative thought that lingers in the viewer's mind.\n"
            "  - Think of it as the last line of a bedtime story — leave an afterimage.\n"
            "  - NO action demands. NO 'subscribe/like/comment'. NO imperative commands.\n"
            "  - A gentle observation, a poetic question, or a moment of wonder works best.\n"
            "  - {narration_field}: up to {cta_max} English characters.\n"
            '  - structure_role for the last scene must be "closing".\n'
        ),
        "general_rules": (
            "General rules:\n"
            "  - {narration_field} must be in {language}\n"
            "  - return exactly {scene_count} scenes\n"
            "  - narration must sound natural when spoken aloud, not like bullet points\n"
            "  - Do NOT use '...' (ellipsis) in {narration_field}. Write complete sentences.\n"
            "  - estimated_seconds must realistically match the spoken length of that scene\n"
            "  - {visual_prompt_field}: English only, describe camera angle, lighting, action, artistic style for DALL-E 3\n"
            "  - {visual_prompt_field} MUST be DALL-E safe: NO medical imagery, anatomical details, injuries, blood,\n"
            "    violence, weapons, drugs, or explicit body parts. Use abstract metaphors instead.\n"
            "    (e.g. 'a person resting on a couch' instead of 'sedentary lifestyle causing muscle atrophy')\n"
            "  - do not include markdown\n"
        ),
        "korean_rules": (
            "English Writing Rules (CRITICAL):\n"
            "  - All {narration_field} text must be natural spoken English.\n"
            "  - Check spelling, punctuation, and contractions for fluency.\n"
            "  - Avoid stiff textbook phrasing or unnatural repetition.\n"
            "  - Proofread each {narration_field} line before outputting.\n"
        ),
        "user_header": (
            "Topic: {topic}\n"
            "Target total duration: {target_min}-{target_max} seconds.\n"
            "Target midpoint: about {target_mid:.1f} seconds.\n"
        ),
        "user_instructions": (
            "Write a Hook-Body-Closing script for YouTube Shorts in natural spoken English:\n"
            "  Hook    - Open with a surprising fact or relatable problem. Stop the scroll instantly.\n"
            "  Body    - Guide through analogy -> data or fact -> cause or solution. Build naturally.\n"
            "  Closing - End with a quiet, lingering thought that stays with the viewer.\n"
            "            No action demands, no subscription requests, no imperative commands.\n"
        ),
        "retry_too_short": (
            "The previous draft was too short at about {previous_total_sec:.1f} seconds.\n"
            "Make each scene narration meaningfully longer with more spoken detail.\n"
        ),
        "retry_too_long": (
            "The previous draft was too long at about {previous_total_sec:.1f} seconds.\n"
            "Tighten each scene narration while keeping the same clarity.\n"
        ),
        "retry_keep_scene_count": "Keep exactly {previous_scene_count} scenes unless that prevents the duration target.\n",
    }

    def _next_hook_pattern(self) -> tuple[str, str]:
        """Hook 패턴 로테이션. 호출할 때마다 다음 패턴 반환."""
        with ScriptPromptsMixin._counter_lock:
            idx = ScriptPromptsMixin._hook_counter % len(self.HOOK_PATTERNS)
            ScriptPromptsMixin._hook_counter += 1
        return self.HOOK_PATTERNS[idx]

    def _get_hook_pattern(self) -> tuple[str, str]:
        """채널별 고정 패턴이 있으면 해당 패턴을 반환, 없으면 로테이션 패턴을 반환."""
        if self.channel_hook_pattern:
            for name, instruction in self.HOOK_PATTERNS:
                if name == self.channel_hook_pattern:
                    logger.info("[Hook] 채널 고정 패턴 적용: %s", name)
                    return name, instruction
            logger.warning(
                "[Hook] channel_hook_pattern '%s'를 찾을 수 없어 로테이션으로 폴백.",
                self.channel_hook_pattern,
            )
        return self._next_hook_pattern()

    def _next_tone_preset(self) -> tuple[str, str]:
        """톤 프리셋 로테이션. 호출할 때마다 다음 톤 반환."""
        with ScriptPromptsMixin._counter_lock:
            idx = ScriptPromptsMixin._tone_counter % len(self._tone_presets)
            ScriptPromptsMixin._tone_counter += 1
        return self._tone_presets[idx]

    def _next_structure_preset(
        self,
    ) -> tuple[str, list[str]] | tuple[None, None]:
        """구조 프리셋 로테이션. config에 프리셋이 없으면 (None, None)."""
        presets = self.config.project.structure_presets
        if not presets:
            return None, None
        names = list(presets.keys())
        with ScriptPromptsMixin._counter_lock:
            idx = ScriptPromptsMixin._structure_counter % len(names)
            ScriptPromptsMixin._structure_counter += 1
        name = names[idx]
        return name, presets[name]

    @staticmethod
    def estimate_narration_duration_sec(
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
        spoken_sec = weighted_units / ScriptPromptsMixin.duration_estimate_chars_per_sec
        pause_sec = punctuation_pauses * 0.22
        speed = max(0.7, float(tts_speed))

        estimated = (spoken_sec + pause_sec) / speed
        if language.lower().startswith("ko"):
            estimated += 0.15
        return round(max(1.2, estimated), 3)

    @staticmethod
    def estimate_total_duration_sec(scene_plans: list) -> float:
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
        channel_key: str = "",
    ) -> str:
        last = scene_count
        body_count = scene_count - 2  # hook(1) + cta(1)
        hook_max = max(40, int(char_max * 0.65))
        body_min = max(40, int(char_min * 1.3))
        body_max = int(char_max * 1.30)
        cta_max = max(25, int(char_max * 0.40))
        hook_rule = (
            hook_instruction or "Open with a shocking stat, a relatable frustration, or a counterintuitive question."
        )

        persona_section = ""
        persona = self._channel_persona.get(channel_key or self.channel_key)
        if persona:
            persona_section = (
                "\n"
                f"Channel Persona (CRITICAL - defines your entire voice for this video):\n"
                f"  Role: {persona['role_description']}\n"
                f"  {persona['tone']}\n"
                f"  {persona['forbidden']}\n"
                f"  {persona['required']}\n"
            )

        tone_section = ""
        narration_field = self._prompt_field_names["narration"]
        visual_prompt_field = self._prompt_field_names["visual_prompt"]
        if tone_guide:
            tone_section = (
                "\n"
                "Tone & Voice Guide (MUST follow throughout ALL scenes):\n"
                f"  - {tone_guide}\n"
                f"  - Apply this tone consistently in {narration_field} for every scene.\n"
            )

        # 구성안 기반 구조 또는 기본 Hook-Body-CTA/Closing 구조
        use_closing = False
        if structure_flow:
            structure_section = (
                "  Scene flow: " + " -> ".join(f"{i + 1}:{role}" for i, role in enumerate(structure_flow)) + "\n"
                "  Use these roles as structure_role values for each scene.\n"
            )
            use_closing = structure_flow and structure_flow[-1] == "closing"
        else:
            structure_section = (
                f'  Scene 1        -> structure_role: "hook"\n'
                f'  Scenes 2-{last - 1}  -> structure_role: "body"  ({body_count} scenes)\n'
                f'  Scene {last}        -> structure_role: "closing"\n'
            )
            use_closing = True

        # closing 역할이면 closing_rules 사용, 아니면 기존 cta_rules
        ending_rules_key = "closing_rules" if use_closing else "cta_rules"

        return (
            self._prompt_copy["system_intro"]
            + f"{persona_section}"
            + "\n"
            + self._prompt_copy["source_rule"]
            + "\n"
            + f"Structure - exactly {scene_count} scenes:\n"
            + structure_section
            + f"{tone_section}"
            + "\n"
            + self._prompt_copy["hook_rules"].format(
                hook_rule=hook_rule,
                hook_max=hook_max,
                narration_field=narration_field,
            )
            + (
                self._prompt_copy.get("hook_rules_ko", "").format(narration_field=narration_field)
                if language.lower().startswith("ko")
                else ""
            )
            + "\n"
            + self._prompt_copy["body_rules"].format(
                body_min=body_min,
                body_max=body_max,
                narration_field=narration_field,
            )
            + "\n"
            + self._prompt_copy[ending_rules_key].format(
                cta_max=cta_max,
                narration_field=narration_field,
            )
            + "\n"
            + self._prompt_copy["general_rules"].format(
                language=language,
                scene_count=scene_count,
                narration_field=narration_field,
                visual_prompt_field=visual_prompt_field,
            )
            + "\n"
            + self._prompt_copy["korean_rules"].format(narration_field=narration_field)
        )

    def _build_user_prompt(
        self,
        *,
        topic: str,
        duration_range: tuple[int, int],
        attempt: int,
        previous_total_sec: float | None,
        previous_scene_count: int | None,
        research_block: str = "",
        structure_block: str = "",
    ) -> str:
        target_min, target_max = duration_range
        target_mid = (target_min + target_max) / 2
        prompt = self._prompt_copy["user_header"].format(
            topic=topic,
            target_min=target_min,
            target_max=target_max,
            target_mid=target_mid,
        )
        if research_block:
            prompt += research_block
        if structure_block:
            prompt += "\n" + structure_block + "\n"
        prompt += self._prompt_copy["user_instructions"]
        if attempt > 1 and previous_total_sec is not None:
            if previous_total_sec < target_min:
                prompt += self._prompt_copy["retry_too_short"].format(previous_total_sec=previous_total_sec)
            elif previous_total_sec > target_max:
                prompt += self._prompt_copy["retry_too_long"].format(previous_total_sec=previous_total_sec)
            if previous_scene_count is not None:
                prompt += self._prompt_copy["retry_keep_scene_count"].format(previous_scene_count=previous_scene_count)
        return prompt

    @staticmethod
    def _duration_error(total_sec: float, duration_range: tuple[int, int]) -> float:
        target_mid = (duration_range[0] + duration_range[1]) / 2
        if duration_range[0] <= total_sec <= duration_range[1]:
            return 0.0
        return abs(total_sec - target_mid)

    def _apply_locale_overrides(self) -> None:
        self._tone_presets = list(self.TONE_PRESETS)
        self._channel_persona = copy.deepcopy(self._CHANNEL_PERSONA)
        self._cta_forbidden_words = tuple(self._CTA_FORBIDDEN_WORDS)
        self._persona_keywords = copy.deepcopy(self._PERSONA_KEYWORDS)
        self._prompt_copy = copy.deepcopy(self._PROMPT_COPY)
        self._review_copy = copy.deepcopy(self._REVIEW_COPY)
        self._prompt_field_names = copy.deepcopy(self._PROMPT_FIELD_NAMES)
        self._channel_review_criteria = copy.deepcopy(self._CHANNEL_REVIEW_CRITERIA)

        lang = self.config.project.language
        # Look up the function through the concrete class's module so that
        # tests patching shorts_maker_v2.pipeline.script_step._load_script_step_locale_bundle
        # take effect (backward compatibility).
        import sys

        _host_mod = sys.modules.get(type(self).__module__)
        _loader = getattr(_host_mod, "_load_script_step_locale_bundle", None) or _load_script_step_locale_bundle
        bundle = _loader(lang)
        if not bundle:
            return

        normalized_tones = _normalize_tone_presets(bundle.get("tone_presets"))
        if normalized_tones:
            self._tone_presets = normalized_tones

        self._channel_persona = _merge_channel_persona(
            self._channel_persona,
            bundle.get("channel_persona"),
        )

        normalized_words = _normalize_string_tuple(bundle.get("cta_forbidden_words"))
        if normalized_words:
            self._cta_forbidden_words = normalized_words

        self._persona_keywords = _merge_persona_keywords(
            self._persona_keywords,
            bundle.get("persona_keywords"),
        )

        prompt_copy = bundle.get("prompt_copy")
        if isinstance(prompt_copy, dict):
            self._prompt_copy = _deep_merge_dicts(self._prompt_copy, prompt_copy)

        review_copy = bundle.get("review_copy")
        if isinstance(review_copy, dict):
            self._review_copy = _deep_merge_dicts(self._review_copy, review_copy)

        self._prompt_field_names = _merge_prompt_field_names(
            self._prompt_field_names,
            bundle.get("field_names"),
        )
        self._channel_review_criteria = _merge_channel_review_criteria(
            self._channel_review_criteria,
            bundle.get("channel_review_criteria"),
        )
