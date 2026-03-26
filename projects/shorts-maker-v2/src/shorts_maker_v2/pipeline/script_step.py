from __future__ import annotations

import copy
import json
import logging
import math
import re
import threading
from pathlib import Path
from typing import Any

import yaml

try:
    from pydantic import BaseModel, Field, ValidationError, model_validator

    _HAS_PYDANTIC = True
except ImportError:  # graceful degradation
    try:
        from pydantic import BaseModel, Field, ValidationError

        model_validator = None
        _HAS_PYDANTIC = True
    except ImportError:
        model_validator = None
        _HAS_PYDANTIC = False

logger = logging.getLogger(__name__)

from shorts_maker_v2.config import AppConfig  # noqa: E402
from shorts_maker_v2.models import ScenePlan  # noqa: E402, E501
from shorts_maker_v2.providers.llm_router import LLMRouter  # noqa: E402


def _deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


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
        structure_role: str = Field(default="body", pattern=r"^(hook|body|cta)$")

        if model_validator is not None:

            @model_validator(mode="before")
            @classmethod
            def _normalize_scene_aliases(cls, value: Any) -> Any:
                if not isinstance(value, dict):
                    return value

                normalized = dict(value)
                if not normalized.get("narration_ko"):
                    normalized["narration_ko"] = (
                        normalized.get("narration") or normalized.get("voiceover") or ""
                    )
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


class ScriptStep:
    duration_estimate_chars_per_sec = 2.8  # 실측 SSML+edge-tts 보정: 씬별 prosody/emphasis/break 오버헤드 반영  # noqa: E501
    max_generation_attempts = 3

    # 4가지 Hook 패턴 (로테이션)
    HOOK_PATTERNS: list[tuple[str, str]] = [
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

    # ── Sprint 4: 채널별 대본 검증 기준 ────────────────────────────────────────
    # 각 채널에 특화된 추가 채점 항목 + min_score 오버라이드
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

    # ── 채널별 페르소나 정의 ──────────────────────────────────────────────────
    # 각 채널의 고유한 서술 스타일, 음성 톤, 금지 패턴, 필수 요소를 정의.
    # _build_system_prompt가 이 딕셔너리를 참조하여 LLM 프롬프트를 강화한다.
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
    # 구독/좋아요 등 채널 행동 유도를 포함한 CTA는 YouTube 품질 심사(YPP) 위험.
    # _validate_cta()가 이 목록을 순회하여 위반 항목을 반환한다.
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
    # 대본 본문 키워드 밀도로 채널 톤 이탈 여부를 수치화한다.
    # _score_persona_match()가 이 딕셔너리를 참조한다.
    _PERSONA_KEYWORDS: dict[str, tuple[str, ...]] = {
        "ai_tech": ("AI", "데이터", "기술", "모델", "%", "연구", "실제로", "개발", "알고리즘", "소프트웨어"),
        "psychology": ("마음", "감정", "공감", "당신", "느끼", "심리", "이해", "관계", "자신", "불안"),
        "history": ("년", "시대", "왕", "전쟁", "역사", "당시", "사건", "제국", "혁명", "문명"),
        "space": ("우주", "광년", "행성", "은하", "태양", "지구", "빛", "별", "블랙홀", "망원경"),
        "health": ("건강", "연구", "권고", "습관", "효과", "몸", "영양", "운동", "식단", "수면"),
    }

    _PROMPT_FIELD_NAMES: dict[str, str] = {
        "narration": "narration_ko",
        "visual_prompt": "visual_prompt_en",
    }

    _PROMPT_COPY: dict[str, str] = {
        "system_intro": (
            "You are a YouTube Shorts scriptwriter. You write in the Hook-Body-CTA format.\n"
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
            "Write a Hook-Body-CTA script for YouTube Shorts in natural spoken English:\n"
            "  Hook  - Open with a surprising fact or relatable problem. Stop the scroll instantly.\n"
            "  Body  - Guide through analogy -> data or fact -> cause or solution. Build naturally.\n"
            "  CTA   - One specific action the viewer can do right now. No subscription requests.\n"
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
        words = forbidden_words if forbidden_words is not None else cls._CTA_FORBIDDEN_WORDS
        return [w for w in words if w in narration.lower()]

    @classmethod
    def _score_persona_match(
        cls,
        scenes: list[ScenePlan],
        channel_key: str,
        persona_keywords: dict[str, tuple[str, ...]] | None = None,
    ) -> float:
        """채널 페르소나 키워드 밀도 기반 매칭 스코어를 반환한다 (0.0~1.0).

        알 수 없는 채널 키 → 0.5 중립 반환.
        씬이 없으면 → 0.0 반환.
        persona_keywords가 None이면 클래스 기본 속성을 사용한다.
        """
        if not scenes:
            return 0.0
        kw_map = persona_keywords if persona_keywords is not None else cls._PERSONA_KEYWORDS
        keywords = kw_map.get(channel_key)
        if not keywords:
            return 0.5  # 알 수 없는 채널은 중립
        all_text = " ".join(s.narration_ko for s in scenes)
        hit_count = sum(1 for kw in keywords if kw in all_text)
        return round(hit_count / len(keywords), 3)

    def _next_hook_pattern(self) -> tuple[str, str]:
        """Hook 패턴 로테이션. 호출할 때마다 다음 패턴 반환."""
        with ScriptStep._counter_lock:
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
                "[Hook] channel_hook_pattern '%s'를 찾을 수 없어 로테이션으로 폴백.",
                self.channel_hook_pattern,
            )
        return self._next_hook_pattern()

    def _next_tone_preset(self) -> tuple[str, str]:
        """톤 프리셋 로테이션. 호출할 때마다 다음 톤 반환."""
        with ScriptStep._counter_lock:
            idx = ScriptStep._tone_counter % len(self._tone_presets)
            ScriptStep._tone_counter += 1
        return self._tone_presets[idx]

    def _next_structure_preset(
        self,
    ) -> tuple[str, list[str]] | tuple[None, None]:
        """구조 프리셋 로테이션. config에 프리셋이 없으면 (None, None)."""
        presets = self.config.project.structure_presets
        if not presets:
            return None, None
        names = list(presets.keys())
        with ScriptStep._counter_lock:
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
            if raw_role in ("hook", "body", "cta"):
                structure_role = raw_role
            elif idx == 1:
                structure_role = "hook"
            elif idx == total:
                structure_role = "cta"
            else:
                structure_role = "body"
            # ── Hook 15자 트림 (화면 임팩트 극대화) ─────────────────────────
            # Hook은 3초 이내에 시청자를 사로잡아야 하므로 15자 이내를 강제한다.
            # TTS는 원본 narration을 읽으므로 음성 품질에는 영향 없음.
            # 자막 렌더(caption_pillow) 픽셀 넘침 방지 목적으로 자동 트림한다.
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
        bundle = _load_script_step_locale_bundle(lang)
        if not bundle:
            return

        tone_presets = bundle.get("tone_presets")
        if isinstance(tone_presets, list):
            normalized_tones: list[tuple[str, str]] = []
            for item in tone_presets:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()
                guide = str(item.get("guide", "")).strip()
                if name and guide:
                    normalized_tones.append((name, guide))
            if normalized_tones:
                self._tone_presets = normalized_tones

        channel_persona = bundle.get("channel_persona")
        if isinstance(channel_persona, dict):
            for key, value in channel_persona.items():
                if not isinstance(value, dict):
                    continue
                if key not in self._channel_persona:
                    self._channel_persona[key] = {}
                self._channel_persona[key].update(value)

        cta_forbidden_words = bundle.get("cta_forbidden_words")
        if isinstance(cta_forbidden_words, list):
            normalized_words = tuple(str(word).strip() for word in cta_forbidden_words if str(word).strip())
            if normalized_words:
                self._cta_forbidden_words = normalized_words

        persona_keywords = bundle.get("persona_keywords")
        if isinstance(persona_keywords, dict):
            merged_keywords = copy.deepcopy(self._persona_keywords)
            for key, value in persona_keywords.items():
                if isinstance(value, list):
                    normalized_keywords = tuple(str(item).strip() for item in value if str(item).strip())
                    if normalized_keywords:
                        merged_keywords[str(key)] = normalized_keywords
            self._persona_keywords = merged_keywords

        prompt_copy = bundle.get("prompt_copy")
        if isinstance(prompt_copy, dict):
            self._prompt_copy = _deep_merge_dicts(self._prompt_copy, prompt_copy)

        review_copy = bundle.get("review_copy")
        if isinstance(review_copy, dict):
            self._review_copy = _deep_merge_dicts(self._review_copy, review_copy)

        field_names = bundle.get("field_names")
        if isinstance(field_names, dict):
            for key, value in field_names.items():
                normalized_key = str(key).strip()
                normalized_value = str(value).strip()
                if normalized_key in self._prompt_field_names and normalized_value:
                    self._prompt_field_names[normalized_key] = normalized_value

        channel_review_criteria = bundle.get("channel_review_criteria")
        if isinstance(channel_review_criteria, dict):
            merged_criteria = copy.deepcopy(self._channel_review_criteria)
            for key, value in channel_review_criteria.items():
                if not isinstance(value, dict):
                    continue
                normalized_criteria = copy.deepcopy(merged_criteria.get(str(key), {}))
                extra_dimensions = value.get("extra_dimensions")
                if isinstance(extra_dimensions, str) and extra_dimensions.strip():
                    normalized_criteria["extra_dimensions"] = extra_dimensions
                extra_keys = value.get("extra_keys")
                if isinstance(extra_keys, (list, tuple)):
                    normalized_extra_keys = tuple(str(item).strip() for item in extra_keys if str(item).strip())
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
            self._channel_review_criteria = merged_criteria

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

        if structure_flow:
            structure_section = (
                "  Scene flow: " + " -> ".join(f"{i + 1}:{role}" for i, role in enumerate(structure_flow)) + "\n"
                "  Use these roles as structure_role values for each scene.\n"
            )
        else:
            structure_section = (
                f'  Scene 1        -> structure_role: "hook"\n'
                f'  Scenes 2-{last - 1}  -> structure_role: "body"  ({body_count} scenes)\n'
                f'  Scene {last}        -> structure_role: "cta"\n'
            )

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
            + "\n"
            + self._prompt_copy["body_rules"].format(
                body_min=body_min,
                body_max=body_max,
                narration_field=narration_field,
            )
            + "\n"
            + self._prompt_copy["cta_rules"].format(
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
        prompt += self._prompt_copy["user_instructions"]
        if attempt > 1 and previous_total_sec is not None:
            if previous_total_sec < target_min:
                prompt += self._prompt_copy["retry_too_short"].format(previous_total_sec=previous_total_sec)
            elif previous_total_sec > target_max:
                prompt += self._prompt_copy["retry_too_long"].format(previous_total_sec=previous_total_sec)
            if previous_scene_count is not None:
                prompt += self._prompt_copy["retry_keep_scene_count"].format(
                    previous_scene_count=previous_scene_count
                )
        return prompt

    @staticmethod
    def _duration_error(total_sec: float, duration_range: tuple[int, int]) -> float:
        target_mid = (duration_range[0] + duration_range[1]) / 2
        if duration_range[0] <= total_sec <= duration_range[1]:
            return 0.0
        return abs(total_sec - target_mid)

    # ── 스크립트 품질 검토 (Sprint 4: 채널별 차별화) ──────────────────────────

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
        output_rule = self._review_copy.get("output_rule", "Output ONLY valid JSON: {{{json_example}, \"feedback\": \"...\"}}")
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

        SiteAgent의 MARL 메타인지 패턴(생성→자기검증→수정) 중 '자기검증' 단계.
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

        # scene_id → suggested narration 매핑
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
                    "[MARL] Scene %d narration patched (%.0f→%.0f chars)",
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

        SiteAgent의 Zod → OpenAI Tool 패턴을 Pydantic으로 구현.
        Pydantic이 없으면 빈 리스트 반환 (graceful degradation).

        Returns:
            에러 메시지 리스트 (비어있으면 유효)
        """
        if not _HAS_PYDANTIC:
            return []

        try:
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

    def run(self, topic: str, research_context: Any | None = None) -> tuple[str, list[ScenePlan], str]:
        """
        대본 생성.

        Args:
            topic: 영상 주제
            research_context: ResearchContext 객체 (리서치 스텝 결과). None이면 리서치 없이 생성.

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
        # YouTube Shorts 상한 (45초) — 시청 완료율 최적화 + 60초 플랫폼 제한 내 안전 여유  # noqa: E501
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

        # ── CTA 금지어 검증 ───────────────────────────────────────────────────
        # 구독/좋아요 등 채널 행동 CTA는 YPP 품질 심사에서 감점 요인.
        final_title, final_scenes = best_result
        cta_scenes = [s for s in final_scenes if s.structure_role == "cta"]
        for cta_scene in cta_scenes:
            violations = self._validate_cta(cta_scene.narration_ko, self._cta_forbidden_words)
            if violations:
                logger.warning(
                    "[CTAGuard] Scene %d CTA contains forbidden words: %s — "
                    "consider revising to organic CTA.",
                    cta_scene.scene_id,
                    ", ".join(repr(v) for v in violations),
                )

        # ── 페르소나 매칭 스코어 ─────────────────────────────────────────────
        # 채널 키워드 밀도로 대본이 채널 톤을 유지하는지 수치화한다.
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
