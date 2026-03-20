from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

try:
    from pydantic import BaseModel, Field, ValidationError

    _HAS_PYDANTIC = True
except ImportError:  # graceful degradation
    _HAS_PYDANTIC = False

logger = logging.getLogger(__name__)

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.providers.llm_router import LLMRouter


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
    duration_estimate_chars_per_sec = 2.8  # 실측 SSML+edge-tts 보정: 씬별 prosody/emphasis/break 오버헤드 반영
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
                "[Hook] channel_hook_pattern '%s'를 찾을 수 없어 로테이션으로 폴백.",
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
        hook_max = max(40, int(char_max * 0.65))
        body_min = max(40, int(char_min * 1.3))  # body 최소 글자수 상향
        body_max = int(char_max * 1.30)
        cta_max = max(25, int(char_max * 0.40))  # CTA 더 짧게
        hook_rule = (
            hook_instruction or "Open with a shocking stat, a relatable frustration, or a counterintuitive question."
        )

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
                "  Scene flow: " + " → ".join(f"{i + 1}:{role}" for i, role in enumerate(structure_flow)) + "\n"
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
            '  "scenes": [...],\n'
            '  "no_reliable_source": false\n'
            "}\n"
            "\n"
            "CRITICAL SOURCE RULE:\n"
            "  - You MUST base all claims on verifiable facts you are confident about.\n"
            "  - If you cannot recall specific data, studies, or established facts for this topic,\n"
            "    DO NOT invent or guess. Instead, return:\n"
            '    {"title": "", "scenes": [], "no_reliable_source": true,\n'
            '     "reason": "<why no reliable source was found>"}\n'
            "  - It is FAR BETTER to admit 'I don't have reliable data' than to hallucinate facts.\n"
            "  - For each factual claim in the Body, mentally ask: 'Can a viewer Google this and confirm it?'\n"
            "    If the answer is no, either remove the claim or flag no_reliable_source.\n"
            "\n"
            f"Structure — exactly {scene_count} scenes:\n" + structure_section + f"{tone_section}"
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
            "  - Do NOT use '...' (ellipsis) in narration_ko. Write complete sentences.\n"
            "  - estimated_seconds must realistically match the spoken length of that scene\n"
            "  - visual_prompt_en: English only, describe camera angle, lighting, action, artistic style for DALL-E 3\n"
            "  - visual_prompt_en MUST be DALL-E safe: NO medical imagery, anatomical details, injuries, blood,\n"
            "    violence, weapons, drugs, or explicit body parts. Use abstract metaphors instead.\n"
            "    (e.g. 'a person resting on a couch' instead of 'sedentary lifestyle causing muscle atrophy')\n"
            "  - do not include markdown\n"
            "\n"
            "Korean Spelling & Spacing Rules (CRITICAL):\n"
            "  - All narration_ko text MUST follow correct Korean spelling (맞춤법) and spacing (띄어쓰기).\n"
            "  - Double-check every sentence for: 되/돼, 안/안돼, 되다/되다, 하던/하던, 의/의, 로서/로써 etc.\n"
            "  - Use standard 받침 rules: 같이/같이, 많은/많은, 나을/나을 etc.\n"
            "  - Common errors to avoid: '잘했다'(✔) vs '잘 했다'(✘), '될까'(✔) vs '될까'(✔), '됩니다'(✔) vs '됬니다'(✘)\n"
            "  - Spacing after particles: '의 사람'(✔), '의사람'(✘).\n"
            "  - Proofread each narration_ko line carefully before outputting."
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
        prompt = (
            f"Topic: {topic}\n"
            f"Target total duration: {target_min}-{target_max} seconds.\n"
            f"Target midpoint: about {target_mid:.1f} seconds.\n"
        )
        if research_block:
            prompt += research_block
        prompt += (
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

    # ── 스크립트 품질 검토 (Sprint 4: 채널별 차별화) ──────────────────────────

    _BASE_REVIEW_SYSTEM = (
        "You are a YouTube Shorts script quality evaluator. "
        "Score the given script on these dimensions from 1-10:\n"
        "  hook_score : How well does the Hook stop the scroll? (1=boring, 10=irresistible)\n"
        "  flow_score : How naturally does the Body build and connect? (1=choppy, 10=seamless)\n"
        "  cta_score  : How clear and actionable is the CTA? (1=vague, 10=immediately doable)\n"
        "  verifiability_score : Can a viewer Google each factual claim and confirm it? "
        "(1=all claims feel fabricated/unverifiable, 10=every claim is well-known or easily verifiable)\n"
        "  spelling_score : Is the Korean spelling (맞춤법) and spacing (띄어쓰기) correct? "
        "(1=many errors, 10=perfect Korean). If errors found, list them in 'spelling_fixes'.\n"
    )

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

        if self.channel_key and self.channel_key in self._CHANNEL_REVIEW_CRITERIA:
            criteria = self._CHANNEL_REVIEW_CRITERIA[self.channel_key]
            extra_dimensions = criteria.get("extra_dimensions", "")
            extra_keys = criteria.get("extra_keys", ())
            min_score = criteria.get("min_score_override", min_score)
            context_note = criteria.get("context_note", "")

        all_keys = base_keys + extra_keys
        json_example = ", ".join(f'"{k}": n' for k in all_keys)

        system_prompt = (
            self._BASE_REVIEW_SYSTEM
            + extra_dimensions
            + "Also provide a brief 'feedback' string (max 80 chars) with the main weakness.\n"
        )
        if context_note:
            system_prompt += f"\nChannel Context: {context_note}\n"
        system_prompt += f'Output ONLY valid JSON: {{{json_example}, "feedback": "..."}}'

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
            ScriptOutput.model_validate(payload)
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
        # YouTube Shorts 상한 (45초) — 시청 완료율 최적화 + 60초 플랫폼 제한 내 안전 여유
        SHORTS_HARD_LIMIT = 45
        effective_max = min(target_max, SHORTS_HARD_LIMIT)

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

        return (*best_result, hook_pattern_name)
