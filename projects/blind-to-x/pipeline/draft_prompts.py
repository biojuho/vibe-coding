"""Prompt building, tone mapping, and example formatting for draft generation."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any

from pipeline.rules_loader import load_rules

logger = logging.getLogger(__name__)

_draft_rules_cache: dict | None = None
_DEFAULT_SYSTEM_ROLE = "당신은 직장인 대상 콘텐츠를 큐레이션하는 시니어 에디터입니다."
_ANTHROPIC_SYSTEM_INSTRUCTION = "아래 게시글을 기반으로 발행 가능한 초안을 작성하세요."

_COMMENT_TRIGGER_PROMPT = """
[독자가 댓글을 달고 싶어지는 4가지 트리거 — 트위터/스레드 한정]
4개 트리거가 모두 들어가야 평균 이상의 글이 됩니다. 하나라도 빠지면 "댓글이 안 달리는 글"입니다.

1. 식별감 (Identifiability)
   - 누가 자기 얘기로 받을지가 한 줄에 드러나야 합니다.
   - 좋은 예: "3년차 개발자", "팀장 첫 분기 보낸 사람", "재택 막 시작한 부서 막내", "성과급 첫 통보 받은 신입"
   - 일반 "직장인" 만으로는 부족합니다. 직군·연차·조직 위치를 한 단어로라도 박으세요.

2. 입장 (Stance)
   - 한쪽 편을 들거나, 한 가지 해석을 분명히 내세요. "이게 맞다" 또는 "이건 좀 그렇다".
   - 양비론·균형·"양쪽 다 일리 있다" 류는 댓글이 안 달립니다.
   - 양쪽을 다 인정하더라도 "근데 결국 X" 식으로 한쪽으로 기울어 끝내세요.
   - 운영자(creator)의 입장이 한 줄이라도 본문에 보여야 합니다.

3. 오픈루프 마무리 (Open Loop)
   - 마지막 문장은 독자가 자기 경험으로 이어 적게 만드는 여백을 남기세요.
   - "?" 로 묻지 말고, 답이 여러 개로 갈리는 평서문으로 끝내세요.
   - 좋은 예: "충성의 가격이 이거임", "그 20분이 진짜 근무시간 아닌가", "쉬는 게 더 피곤"
   - "여기서 끝" 같은 닫힌 마무리(완결된 결론·일반 진리·교훈)는 댓글이 막힙니다.

4. 구체 앵커 (Anchor)
   - 독자가 인용·답글로 그대로 가져다 쓸 한 조각이 있어야 합니다.
   - 짧은 인용 한 줄, 정확한 숫자 하나, 짧은 장면 중 적어도 1개를 본문 안에 분명히 박으세요.
   - 좋은 예: "5천이 월급인데요", "측정해봤음 17분", "세후 450 찍히는 거 보고"
   - 일반 명사("높은 연봉", "긴 시간")로는 댓글이 안 달립니다.

[댓글이 안 달리는 글의 공통점 — 반드시 피하세요]
- 모두에게 다 적용되는 "보편 진리": "직장인이라면 누구나..." 식의 두루뭉술 진술
- 무색무취 요약: 원문에서 일어난 일을 그대로 요약만 하고 운영자 입장이 없는 글
- 닫힌 결론: "이런 면도 있고 저런 면도 있다" 같은 양비론 마무리
- 추상 명사 나열로 끝나는 문장: "소통", "성장", "성과" 같은 큰 단어만 던지고 끝
"""

_DEFAULT_THINKING_BLOCK = """
[사고 과정 — <thinking> 태그 안에 작성]
초안을 작성하기 전에 반드시 아래를 먼저 분석하세요:
1. 이 글의 핵심 인사이트는 무엇인가? (한 문장)
2. 직장인이 공유하고 싶은 포인트는? (공감/분노/놀라움 중 택1과 이유)
3. 가장 강한 훅이 될 숫자/인용구/대비는?
4. 피해야 할 함정은? (상투적 표현, 원문에 없는 내용 날조)
반드시 <thinking> 와 </thinking> 태그 안에만 작성하세요.
"""

_DEFAULT_IMAGE_PROMPT_BLOCK = """[이미지 프롬프트 작성 조건]
1. 마지막에 영어 이미지 프롬프트를 작성하세요.
2. 텍스트 없는 장면 중심 이미지여야 합니다.
3. 직장인 커뮤니티 상황이 한눈에 보이게 묘사하세요.
4. 반드시 <image_prompt> 와 </image_prompt> 태그 안에만 작성하세요.
"""


_ANTHROPIC_USER_PROMPT_TAIL_KEYS = (
    "selection_brief",
    "comment_trigger",
    "research",
    "topic_strategy",
    "regulation_context",
    "thinking",
    "examples",
    "anti_examples",
    "twitter",
    "threads",
    "newsletter",
    "naver_blog",
    "image",
    "regulation_check",
)

_ANTHROPIC_USER_BLOCK_KEYS = ("essence", *_ANTHROPIC_USER_PROMPT_TAIL_KEYS)
_ANTHROPIC_USER_OUTPUT_BLOCK_KEYS = (
    "regulation_context",
    "twitter",
    "threads",
    "newsletter",
    "naver_blog",
    "image",
    "regulation_check",
)
_ANTHROPIC_USER_REFERENCE_BLOCK_KEYS = ("examples",)
_SHORTFORM_OUTPUT_BLOCK_KEYS = ("twitter", "threads")
_LONGFORM_OUTPUT_BLOCK_KEYS = ("newsletter", "naver_blog")
_PLATFORM_OUTPUT_BLOCK_KEYS = ("twitter", "newsletter", "threads", "naver_blog")
_AUXILIARY_OUTPUT_BLOCK_KEYS = ("image", "regulation_context", "regulation_check")
_PROMPT_COMPONENT_BLOCK_KEYS = ("output", "guidance", "reference")
_REGULATION_OUTPUT_BLOCK_KEYS = ("regulation_context", "regulation_check")
_REGULATION_SUPPORTED_OUTPUT_FORMATS = ("twitter", "threads", "naver_blog")
_PROMPT_CONTEXT_KEYS = (
    "essence",
    "content",
    "source",
    "tone",
    "profile",
    "topic_cluster",
    "recommended_draft_type",
    "empathy_anchor",
    "spinoff_angle",
)


@dataclass(frozen=True, slots=True)
class _OutputBlockRequest:
    """Parameter object for output-format block construction."""

    templates: dict[str, Any]
    rules: dict[str, Any]
    output_formats: list[str]
    draft_format: str
    source: str
    recommended_draft_type: str
    profile: dict[str, Any]
    topic_cluster: str
    empathy_anchor: str
    spinoff_angle: str


@dataclass(frozen=True, slots=True)
class _OutputFormatBlockGroups:
    """Grouped output-format blocks before final prompt-order merge."""

    platform_blocks: dict[str, str]
    auxiliary_blocks: dict[str, str]


@dataclass(frozen=True, slots=True)
class _PromptComponentRequest:
    """Parameter object for prompt component block construction."""

    post_data: dict[str, Any]
    top_examples: list[dict[str, Any]] | None
    output_formats: list[str]
    draft_format: str
    context: dict[str, Any]
    rules: dict[str, Any]
    templates: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _PromptComponentBlockGroups:
    """Named prompt component block groups before prompt-order assembly."""

    output_blocks: dict[str, str]
    guidance_blocks: dict[str, str]
    reference_blocks: dict[str, str]


@dataclass(frozen=True, slots=True)
class _AnthropicUserPromptRequest:
    """Parameter object for Anthropic user prompt construction."""

    post_data: dict[str, Any]
    context: dict[str, Any]
    guidance_blocks: dict[str, str]
    output_blocks: dict[str, str]
    reference_blocks: dict[str, str]


@dataclass(frozen=True, slots=True)
class _AnthropicPromptResultRequest:
    """Parameter object for split Anthropic prompt result construction."""

    post_data: dict[str, Any]
    context: dict[str, Any]
    system_role: Any
    guidance_blocks: dict[str, str]
    output_blocks: dict[str, str]
    reference_blocks: dict[str, str]


@dataclass(frozen=True, slots=True)
class _PromptPreparation:
    """Prepared prompt context and template config for prompt orchestration."""

    context: dict[str, Any]
    rules: dict[str, Any]
    templates: dict[str, Any]
    system_role: Any


class DraftPrompt(str):
    """String prompt with optional Anthropic system/user split metadata."""

    anthropic_system_prompt: str
    anthropic_user_prompt: str

    def __new__(
        cls,
        value: str,
        *,
        anthropic_system_prompt: str = "",
        anthropic_user_prompt: str = "",
    ) -> "DraftPrompt":
        obj = str.__new__(cls, value)
        obj.anthropic_system_prompt = anthropic_system_prompt
        obj.anthropic_user_prompt = anthropic_user_prompt
        return obj


def _load_draft_rules() -> dict:
    """Load merged rule sections with in-module caching."""
    global _draft_rules_cache
    if _draft_rules_cache is not None:
        return _draft_rules_cache
    _draft_rules_cache = load_rules()
    return _draft_rules_cache


class DraftPromptsMixin:
    """Mixin providing prompt-building helpers for TweetDraftGenerator.

    Expects the host class to have: ``self.config``, ``self.tone``,
    ``self.max_length``, ``self.threads_tone``, ``self.threads_max_length``,
    ``self.threads_hashtags_count``, ``self.blog_tone``, ``self.blog_min_length``,
    ``self.blog_max_length``, ``self.blog_seo_tags_count``,
    ``self.regulation_checker``.
    """

    _CATEGORY_TONES: dict[str, str] = {
        "relationship": "친구에게 말하듯 다정하고 공감이 강한 톤",
        "money": "인사이트와 팩트를 섞어 정리하는 톤",
        "career": "직장인에게 실질적인 도움을 주는 조언형 톤",
        "work-life": "직장 밈과 현실 공감을 섞은 톤",
        "family": "담백하지만 울림이 있는 톤",
    }

    # ------------------------------------------------------------------
    # Tone resolution
    # ------------------------------------------------------------------

    def _resolve_tone(self, post_data: dict[str, Any]) -> str:
        """토픽 클러스터 기반 톤 매핑 (YAML 기반, fallback 포함)."""
        # 1. 토픽 클러스터에서 YAML tone_mapping 조회
        profile = post_data.get("content_profile", {}) or {}
        topic_cluster = profile.get("topic_cluster", "")
        rules = _load_draft_rules()
        tone_map = rules.get("tone_mapping", {})
        if topic_cluster and topic_cluster in tone_map:
            return tone_map[topic_cluster]

        # 2. 기존 카테고리 기반 fallback
        category = post_data.get("category", "general")
        if category in self._CATEGORY_TONES:
            return self._CATEGORY_TONES[category]

        # 3. YAML 기타 톤 or 기본 톤
        return tone_map.get("기타", self.tone)

    # ------------------------------------------------------------------
    # Content essence extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _prompt_content(post_data: dict[str, Any], limit: int = 700) -> str:
        """Return content text capped for prompt budget without changing caller data."""
        content = str(post_data.get("content", ""))
        if len(content) > limit:
            logger.info("Content truncated from %s chars to %s for API prompt.", len(content), limit)
            return f"{content[:limit]}..."
        return content

    @staticmethod
    def _content_sentences(content: str, min_length: int = 10) -> list[str]:
        """Split content into prompt-worthy sentences."""
        return [sentence.strip() for sentence in re.split(r"[.!?\n]+", content) if len(sentence.strip()) > min_length]

    @staticmethod
    def _content_key_numbers(content: str, limit: int = 8, context_chars: int = 15) -> list[str]:
        """Extract numeric snippets with surrounding context."""
        key_numbers: list[str] = []
        for match in re.finditer(r"\d[\d,.]*\d?[만천백억원%명개월년일시위등배]?", content):
            start = max(0, match.start() - context_chars)
            end = min(len(content), match.end() + context_chars)
            snippet = content[start:end].strip()
            if snippet and snippet not in key_numbers:
                key_numbers.append(snippet)
        return key_numbers[:limit]

    @staticmethod
    def _content_quotes(content: str, limit: int = 5) -> list[str]:
        """Extract quoted phrases from content."""
        quotes: list[str] = re.findall(
            r"""['\"\u201c\u201d\u2018\u2019「」『』](.{5,80}?)['\"\u201c\u201d\u2018\u2019「」『』]""",
            content,
        )
        return quotes[:limit]

    @staticmethod
    def _content_emotional_peaks(
        sentences: list[str],
        emotion_keywords: list[str],
        limit: int = 3,
    ) -> list[str]:
        """Select sentences that match configured emotional keywords."""
        emotional_peaks: list[str] = []
        for sentence in sentences:
            if any(keyword in sentence for keyword in emotion_keywords):
                emotional_peaks.append(sentence)
                if len(emotional_peaks) >= limit:
                    break
        return emotional_peaks

    @staticmethod
    def _content_signal_examples(
        content: str,
        sentences: list[str],
        emotion_keywords: list[str],
    ) -> dict[str, list[str]]:
        """Extract numeric, quote, and emotional signal examples from content."""
        return {
            "key_numbers": DraftPromptsMixin._content_key_numbers(content),
            "quotes": DraftPromptsMixin._content_quotes(content),
            "emotional_peaks": DraftPromptsMixin._content_emotional_peaks(sentences, emotion_keywords),
        }

    @staticmethod
    def _content_bookends(sentences: list[str]) -> tuple[str, str]:
        """Return opening and closing sentences used as narrative bookends."""
        opening = sentences[0] if sentences else ""
        closing = sentences[-1] if len(sentences) > 1 else ""
        return opening, closing

    @staticmethod
    def _emotion_keywords(rules: dict[str, Any]) -> list[str]:
        """Flatten emotion-rule keywords from draft rules."""
        emotion_keywords: list[str] = []
        for rule in rules.get("emotion_rules", []):
            emotion_keywords.extend(rule.get("keywords", []))
        return emotion_keywords

    @staticmethod
    def _build_essence_block(essence: dict[str, Any]) -> str:
        """Build the optional source-essence block used by the prompt."""
        if not (essence.get("key_numbers") or essence.get("quotes") or essence.get("emotional_peaks")):
            return ""

        parts = []
        if essence["key_numbers"]:
            parts.append(f"핵심 수치: {' | '.join(essence['key_numbers'])}")
        if essence["quotes"]:
            parts.append(f"인용/발언: {' | '.join(essence['quotes'])}")
        if essence["emotional_peaks"]:
            parts.append(f"감정 고조점: {' / '.join(essence['emotional_peaks'])}")
        if essence.get("opening"):
            parts.append(f"원문 도입부: {essence['opening']}")
        if essence.get("closing") and essence["closing"] != essence.get("opening"):
            parts.append(f"원문 결론부: {essence['closing']}")
        return "\n[원문 핵심 추출 — 초안에 반드시 활용]\n" + "\n".join(parts)

    @staticmethod
    def _extract_content_essence(post_data: dict[str, Any]) -> dict[str, Any]:
        """원문에서 핵심 요소를 결정론적으로 추출 (LLM 호출 없음).

        Returns:
            {key_numbers, quotes, emotional_peaks, opening, closing}
        """
        content = str(post_data.get("content", ""))
        title = str(post_data.get("title", ""))

        rules = _load_draft_rules()
        emotion_keywords = DraftPromptsMixin._emotion_keywords(rules)

        sentences = DraftPromptsMixin._content_sentences(content)
        signals = DraftPromptsMixin._content_signal_examples(content, sentences, emotion_keywords)

        # 4. 내러티브 북엔드 (첫/끝 문장)
        opening, closing = DraftPromptsMixin._content_bookends(sentences)

        return {
            "title": title,
            "key_numbers": signals["key_numbers"],
            "quotes": signals["quotes"],
            "emotional_peaks": signals["emotional_peaks"],
            "opening": opening,
            "closing": closing,
        }

    # ------------------------------------------------------------------
    # Example formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _example_reference_values(index: int, example: dict[str, Any]) -> dict[str, Any]:
        """Return formatted values for one high-performing reference example."""
        return {
            "index": index,
            "grade": f" [등급: {example['grade']}]" if example.get("grade") else "",
            "views": example.get("views", 0),
            "topic_cluster": example.get("topic_cluster", "기타"),
            "hook_type": example.get("hook_type", "공감형"),
            "emotion_axis": example.get("emotion_axis", "공감"),
            "draft_style": example.get("draft_style", "공감형"),
            "text": str(example.get("text", "")).strip(),
        }

    @staticmethod
    def _format_example_reference_lines(index: int, example: dict[str, Any]) -> list[str]:
        """Format one high-performing example as prompt reference lines."""
        values = DraftPromptsMixin._example_reference_values(index, example)
        return [
            f"- 예시 {values['index']}{values['grade']}",
            f"  조회수: {values['views']}",
            f"  토픽: {values['topic_cluster']}",
            f"  훅: {values['hook_type']}",
            f"  감정: {values['emotion_axis']}",
            f"  추천 초안 타입: {values['draft_style']}",
            f"  본문: {values['text']}",
        ]

    @staticmethod
    def _golden_reference_example(topic_cluster: str, golden_example: dict[str, Any]) -> dict[str, Any]:
        """Map one YAML golden example into the shared reference-example shape."""
        hook_type = golden_example.get("hook_type", "공감형")
        return {
            "views": "(골든 예시)",
            "topic_cluster": topic_cluster,
            "hook_type": hook_type,
            "emotion_axis": "-",
            "draft_style": hook_type,
            "text": golden_example.get("text", ""),
            "grade": golden_example.get("grade", ""),
        }

    @staticmethod
    def _golden_reference_examples(
        rules: dict[str, Any],
        topic_cluster: str,
        example_seed: str,
    ) -> list[dict[str, Any]]:
        """Build prompt reference examples from YAML golden examples."""
        golden = rules.get("golden_examples", {})
        if not topic_cluster or topic_cluster not in golden:
            return []

        selected = DraftPromptsMixin._select_examples_deterministically(
            golden[topic_cluster],
            limit=2,
            seed_text=example_seed,
        )
        return [DraftPromptsMixin._golden_reference_example(topic_cluster, ge) for ge in selected]

    @staticmethod
    def _cost_db_reference_example(row: dict[str, Any]) -> dict[str, Any]:
        """Map one cost database row into the shared reference-example shape."""
        return {
            "views": row.get("yt_views", 0),
            "topic_cluster": row.get("topic_cluster", ""),
            "hook_type": row.get("hook_type", ""),
            "emotion_axis": row.get("emotion_axis", ""),
            "draft_style": row.get("draft_style", ""),
            "text": row.get("text", ""),
            "grade": "실적우수",
        }

    @staticmethod
    def _cost_db_reference_examples(topic_cluster: str) -> list[dict[str, Any]]:
        """Build prompt reference examples from the cost database when available."""
        try:
            from pipeline.cost_db import get_cost_db

            db = get_cost_db()
            top_from_db = db.get_top_performing_drafts(topic_cluster=topic_cluster, limit=2)
            return [DraftPromptsMixin._cost_db_reference_example(row) for row in top_from_db]
        except Exception:
            return []

    @staticmethod
    def _runtime_reference_examples(top_examples: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """Return runtime examples that should appear in prompt references."""
        return [example for example in (top_examples or []) if example.get("example_source") != "reviewer_memory"]

    @staticmethod
    def _reviewer_memory_examples(top_examples: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """Return runtime examples that represent reviewer-memory warnings."""
        return [example for example in (top_examples or []) if example.get("example_source") == "reviewer_memory"]

    @staticmethod
    def _reviewer_memory_line_values(item: dict[str, Any]) -> dict[str, str]:
        """Return normalized display fields for a reviewer-memory prompt line."""
        return {
            "label": str(item.get("memory_label") or "운영 메모").strip(),
            "text": str(item.get("text") or "").strip(),
            "reason": str(item.get("reason") or "").strip(),
        }

    @staticmethod
    def _format_reviewer_memory_item_lines(item: dict[str, Any]) -> list[str]:
        """Format one reviewer-memory warning for prompt output."""
        values = DraftPromptsMixin._reviewer_memory_line_values(item)
        if not values["text"]:
            return []

        lines = [f"- {values['label']}: {values['text']}"]
        if values["reason"]:
            lines.append(f"  이유: {values['reason']}")
        return lines

    @staticmethod
    def _merged_reference_examples(
        top_examples: list[dict[str, Any]] | None,
        topic_cluster: str,
        seed_text: str,
    ) -> list[dict[str, Any]]:
        """Merge configured, performance, and runtime examples for prompt references."""
        runtime_examples = DraftPromptsMixin._runtime_reference_examples(top_examples)
        example_seed = f"{topic_cluster}|{seed_text or 'default'}"
        rules = _load_draft_rules()

        merged: list[dict[str, Any]] = []
        merged.extend(DraftPromptsMixin._golden_reference_examples(rules, topic_cluster, example_seed))
        merged.extend(DraftPromptsMixin._cost_db_reference_examples(topic_cluster))
        if runtime_examples:
            merged.extend(runtime_examples)
        return merged

    @staticmethod
    def _format_examples(
        top_examples: list[dict[str, Any]] | None,
        topic_cluster: str = "",
        seed_text: str = "",
    ) -> str:
        """성과 우수 예시 포맷팅. YAML 골든 예시도 자동 병합 (랜덤 로테이션)."""
        merged = DraftPromptsMixin._merged_reference_examples(top_examples, topic_cluster, seed_text)
        if not merged:
            return ""

        lines = [
            "[성과 우수 레퍼런스]",
            "아래는 높은 성과를 기록한 예시입니다. 말투, 훅, 마무리 질문 방식을 참고하세요.",
        ]
        for index, example in enumerate(merged, start=1):
            lines.extend(DraftPromptsMixin._format_example_reference_lines(index, example))
        return "\n".join(lines)

    @staticmethod
    def _format_reviewer_memory(top_examples: list[dict[str, Any]] | None) -> str:
        reviewer_memory = DraftPromptsMixin._reviewer_memory_examples(top_examples)
        if not reviewer_memory:
            return ""

        lines = [
            "[운영 메모 - 최근 검토에서 자주 걸린 패턴]",
            "아래 패턴은 실제 운영 검토에서 반복적으로 멈춘 지점입니다. 이번 초안에서는 먼저 피하세요.",
        ]
        for item in reviewer_memory:
            lines.extend(DraftPromptsMixin._format_reviewer_memory_item_lines(item))

        return "\n".join(lines)

    @staticmethod
    def _build_reference_blocks(
        top_examples: list[dict[str, Any]] | None,
        topic_cluster: str,
        seed_text: str,
    ) -> dict[str, str]:
        """Build reference example and reviewer-memory prompt blocks."""
        return {
            "examples": DraftPromptsMixin._format_examples(
                top_examples,
                topic_cluster=topic_cluster,
                seed_text=seed_text,
            ),
            "reviewer_memory": DraftPromptsMixin._format_reviewer_memory(top_examples),
        }

    @staticmethod
    def _anthropic_user_output_block_values(output_blocks: dict[str, str]) -> dict[str, str]:
        """Select output blocks that are embedded into the Anthropic user prompt."""
        return {key: output_blocks[key] for key in _ANTHROPIC_USER_OUTPUT_BLOCK_KEYS}

    @staticmethod
    def _anthropic_user_reference_block_values(reference_blocks: dict[str, str]) -> dict[str, str]:
        """Select reference blocks that are embedded into the Anthropic user prompt."""
        return {key: reference_blocks[key] for key in _ANTHROPIC_USER_REFERENCE_BLOCK_KEYS}

    @staticmethod
    def _build_anthropic_user_blocks(
        *,
        essence_block: str,
        selection_brief_block: str,
        comment_trigger_block: str,
        research_block: str,
        topic_strategy_block: str,
        thinking_block: str,
        anti_examples_block: str,
        output_blocks: dict[str, str],
        reference_blocks: dict[str, str],
    ) -> dict[str, str]:
        """Assemble block mapping consumed by the Anthropic user prompt."""
        block_values = {
            "essence": essence_block,
            "selection_brief": selection_brief_block,
            "comment_trigger": comment_trigger_block,
            "research": research_block,
            "topic_strategy": topic_strategy_block,
            "thinking": thinking_block,
            "anti_examples": anti_examples_block,
            **DraftPromptsMixin._anthropic_user_output_block_values(output_blocks),
            **DraftPromptsMixin._anthropic_user_reference_block_values(reference_blocks),
        }
        return {key: block_values[key] for key in _ANTHROPIC_USER_BLOCK_KEYS}

    @staticmethod
    def _guidance_block_values(
        rules: dict[str, Any],
        templates: dict[str, Any],
        post_data: dict[str, Any],
        essence: dict[str, Any],
        profile: dict[str, Any],
        output_formats: list[str],
        topic_cluster: str,
    ) -> dict[str, str]:
        """Return guidance block values built from prompt inputs."""
        return {
            "voice": DraftPromptsMixin._build_voice_block(rules),
            "essence": DraftPromptsMixin._build_essence_block(essence),
            "research": DraftPromptsMixin._build_research_context_block(post_data),
            "thinking": DraftPromptsMixin._build_thinking_block(templates),
            "topic_strategy": DraftPromptsMixin._build_topic_strategy_block(rules, topic_cluster),
            "anti_examples": DraftPromptsMixin._build_anti_examples_block(rules, topic_cluster),
            "selection_brief": DraftPromptsMixin._build_selection_brief_block(profile, essence, output_formats),
            "comment_trigger": DraftPromptsMixin._build_comment_trigger_block(output_formats),
        }

    @staticmethod
    def _build_guidance_blocks(
        rules: dict[str, Any],
        templates: dict[str, Any],
        post_data: dict[str, Any],
        essence: dict[str, Any],
        profile: dict[str, Any],
        output_formats: list[str],
        topic_cluster: str,
    ) -> dict[str, str]:
        """Build non-output prompt guidance blocks."""
        return DraftPromptsMixin._guidance_block_values(
            rules,
            templates,
            post_data,
            essence,
            profile,
            output_formats,
            topic_cluster,
        )

    @staticmethod
    def _anthropic_system_prompt_parts(
        system_role: Any,
        voice_block: str,
        reviewer_memory_block: str,
    ) -> list[str]:
        """Return non-empty Anthropic system prompt parts."""
        return [
            part
            for part in (
                str(system_role).strip(),
                _ANTHROPIC_SYSTEM_INSTRUCTION,
                voice_block.strip(),
                reviewer_memory_block.strip(),
            )
            if part
        ]

    @staticmethod
    def _build_anthropic_system_prompt(system_role: Any, voice_block: str, reviewer_memory_block: str) -> str:
        """Build the Anthropic system prompt from optional prompt blocks."""
        return "\n\n".join(
            DraftPromptsMixin._anthropic_system_prompt_parts(system_role, voice_block, reviewer_memory_block)
        )

    @staticmethod
    def _post_info_section_values(post_data: dict[str, Any], content: str, source: str) -> dict[str, Any]:
        """Return source-post metadata values for the Anthropic user prompt."""
        return {
            "source": source,
            "title": post_data.get("title", ""),
            "content": content,
            "category": post_data.get("category", "general"),
            "likes": post_data.get("likes", 0),
            "comments": post_data.get("comments", 0),
        }

    @staticmethod
    def _post_info_section_lines(values: dict[str, Any], essence_block: str) -> list[str]:
        """Return source-post metadata lines for the Anthropic user prompt."""
        return [
            "[게시글 정보]",
            f"출처: {values['source']}",
            f"제목: {values['title']}",
            f"본문: {values['content']}",
            f"카테고리: {values['category']}",
            f"공감수: {values['likes']} | 댓글수: {values['comments']}",
            essence_block,
        ]

    @staticmethod
    def _format_post_info_section(values: dict[str, Any], essence_block: str) -> str:
        """Format the source-post metadata section for the Anthropic user prompt."""
        return "\n".join(DraftPromptsMixin._post_info_section_lines(values, essence_block))

    @staticmethod
    def _build_post_info_section(post_data: dict[str, Any], content: str, source: str, essence_block: str) -> str:
        """Build the source-post metadata section for the Anthropic user prompt."""
        values = DraftPromptsMixin._post_info_section_values(post_data, content, source)
        return DraftPromptsMixin._format_post_info_section(values, essence_block)

    @staticmethod
    def _content_profile_section_values(
        profile: dict[str, Any],
        topic_cluster: str,
        recommended_draft_type: str,
    ) -> dict[str, Any]:
        """Return values displayed in the Anthropic user prompt content profile section."""
        return {
            "topic_cluster": topic_cluster,
            "hook_type": profile.get("hook_type", "공감형"),
            "emotion_axis": profile.get("emotion_axis", "공감"),
            "audience_fit": profile.get("audience_fit", "범용"),
            "recommended_draft_type": recommended_draft_type,
            "publishability_score": profile.get("publishability_score", 0),
            "performance_score": profile.get("performance_score", 0),
        }

    @staticmethod
    def _content_profile_section_lines(values: dict[str, Any]) -> list[str]:
        """Return analyzed content profile lines for the Anthropic user prompt."""
        return [
            "[콘텐츠 프로필]",
            f"토픽 클러스터: {values['topic_cluster']}",
            f"훅 타입: {values['hook_type']}",
            f"감정 축: {values['emotion_axis']}",
            f"대상 독자: {values['audience_fit']}",
            f"추천 초안 타입: {values['recommended_draft_type']}",
            f"발행 적합도 점수: {values['publishability_score']}",
            f"성과 예측 점수: {values['performance_score']}",
        ]

    @staticmethod
    def _format_content_profile_section(values: dict[str, Any]) -> str:
        """Format the analyzed content profile section for the Anthropic user prompt."""
        return "\n".join(DraftPromptsMixin._content_profile_section_lines(values))

    @staticmethod
    def _build_content_profile_section(
        profile: dict[str, Any],
        topic_cluster: str,
        recommended_draft_type: str,
    ) -> str:
        """Build the analyzed content profile section for the Anthropic user prompt."""
        values = DraftPromptsMixin._content_profile_section_values(profile, topic_cluster, recommended_draft_type)
        return DraftPromptsMixin._format_content_profile_section(values)

    @staticmethod
    def _user_prompt_block_tail_parts(blocks: dict[str, str]) -> list[str]:
        """Return prepared prompt blocks in Anthropic user prompt order."""
        return [blocks[key] for key in _ANTHROPIC_USER_PROMPT_TAIL_KEYS]

    @staticmethod
    def _build_user_prompt_block_tail(blocks: dict[str, str]) -> str:
        """Build the ordered prepared-block section for the Anthropic user prompt."""
        return "\n".join(DraftPromptsMixin._user_prompt_block_tail_parts(blocks))

    @staticmethod
    def _anthropic_user_prompt_parts(
        post_info_section: str,
        content_profile_section: str,
        block_tail: str,
        tone: str,
    ) -> list[str]:
        """Return final Anthropic user prompt parts including separators."""
        return [
            post_info_section,
            "",
            content_profile_section,
            block_tail,
            "[톤 가이드]",
            tone,
            "",
        ]

    @staticmethod
    def _format_anthropic_user_prompt(
        post_info_section: str,
        content_profile_section: str,
        block_tail: str,
        tone: str,
    ) -> str:
        """Format the final Anthropic user prompt from prepared sections."""
        return "\n".join(
            DraftPromptsMixin._anthropic_user_prompt_parts(
                post_info_section,
                content_profile_section,
                block_tail,
                tone,
            )
        )

    @staticmethod
    def _anthropic_user_prompt_section_values(
        post_data: dict[str, Any],
        content: str,
        source: str,
        profile: dict[str, Any],
        topic_cluster: str,
        recommended_draft_type: str,
        blocks: dict[str, str],
    ) -> dict[str, str]:
        """Return prepared section values for the Anthropic user prompt."""
        return {
            "post_info": DraftPromptsMixin._build_post_info_section(post_data, content, source, blocks["essence"]),
            "content_profile": DraftPromptsMixin._build_content_profile_section(
                profile,
                topic_cluster,
                recommended_draft_type,
            ),
            "block_tail": DraftPromptsMixin._build_user_prompt_block_tail(blocks),
        }

    @staticmethod
    def _build_anthropic_user_prompt(
        post_data: dict[str, Any],
        content: str,
        source: str,
        tone: str,
        profile: dict[str, Any],
        topic_cluster: str,
        recommended_draft_type: str,
        blocks: dict[str, str],
    ) -> str:
        """Build the Anthropic user prompt from post metadata and prepared blocks."""
        sections = DraftPromptsMixin._anthropic_user_prompt_section_values(
            post_data,
            content,
            source,
            profile,
            topic_cluster,
            recommended_draft_type,
            blocks,
        )
        return DraftPromptsMixin._format_anthropic_user_prompt(
            sections["post_info"],
            sections["content_profile"],
            sections["block_tail"],
            tone,
        )

    @staticmethod
    def _example_selection_sort_key(seed: str, example: dict[str, Any]) -> tuple[str, str]:
        """Return deterministic sort key for seeded example selection."""
        text = str(example.get("text", "")).strip()
        return (hashlib.sha256(f"{seed}|{text}".encode("utf-8")).hexdigest(), text)

    @staticmethod
    def _example_selection_offset(seed: str, ordered_count: int) -> int:
        """Return deterministic rotation offset for selected examples."""
        return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % ordered_count

    @staticmethod
    def _select_examples_deterministically(
        examples: list[dict[str, Any]],
        limit: int,
        seed_text: str,
    ) -> list[dict[str, Any]]:
        if len(examples) <= limit:
            return list(examples)

        seed = seed_text or "default"
        ordered = sorted(
            examples,
            key=lambda example: DraftPromptsMixin._example_selection_sort_key(seed, example),
        )
        offset = DraftPromptsMixin._example_selection_offset(seed, len(ordered))
        rotated = ordered[offset:] + ordered[:offset]
        return rotated[:limit]

    # ------------------------------------------------------------------
    # Comment-trigger framework (Phase 2)
    # ------------------------------------------------------------------

    @staticmethod
    def _comment_trigger_prompt() -> str:
        """Return comment-trigger instructions for short social formats."""
        return _COMMENT_TRIGGER_PROMPT

    @staticmethod
    def _build_comment_trigger_block(output_formats: list[str]) -> str:
        """[독자가 댓글을 달고 싶어지는 4가지 트리거] 블록을 조립한다.

        twitter/threads 가 출력 포맷에 포함될 때만 활성화. 4 트리거(식별감/입장/
        오픈루프/구체 앵커)를 LLM 이 캡션 작성 단계부터 의식하도록 강제한다.

        Phase 2 의 핵심: 기존 게이트는 "나쁜 톤 제거" 였지만 이 블록은 "댓글이
        달리게 만드는 적극적 매력" 을 생성 단계에 주입한다.
        """
        # 댓글 트리거는 댓글이 핵심 KPI 인 짧은 포맷에서만 의미가 있다.
        if not any(fmt in output_formats for fmt in ("twitter", "threads")):
            return ""

        return DraftPromptsMixin._comment_trigger_prompt()

    @staticmethod
    def _topic_strategy_lines(topic_cluster: str, topic_strategy: dict[str, Any]) -> list[str]:
        """Return prompt lines for a topic-specific writing strategy."""
        parts = [f"[토픽별 작성 전략 — {topic_cluster}]"]
        if topic_strategy.get("emphasis"):
            parts.append(f"강조: {topic_strategy['emphasis']}")
        if topic_strategy.get("avoid"):
            parts.append(f"피하기: {topic_strategy['avoid']}")
        if topic_strategy.get("hook_template"):
            parts.append(f"훅 구조: {topic_strategy['hook_template']}")
        if topic_strategy.get("example_structure"):
            parts.append(f"글 구조: {topic_strategy['example_structure']}")
        return parts

    @staticmethod
    def _build_topic_strategy_block(rules: dict[str, Any], topic_cluster: str) -> str:
        """Build the optional topic-specific prompt strategy block."""
        topic_strategy = rules.get("topic_prompt_strategies", {}).get(topic_cluster, {})
        if not topic_strategy:
            return ""

        return "\n" + "\n".join(DraftPromptsMixin._topic_strategy_lines(topic_cluster, topic_strategy))

    @staticmethod
    def _selected_anti_examples(anti_examples: dict[str, Any], topic_cluster: str) -> list[dict[str, Any]]:
        """Return topic-first anti examples capped for prompt output."""
        generic_bad = anti_examples.get("generic_bad", [])
        topic_bad = anti_examples.get(topic_cluster, [])
        return (topic_bad + generic_bad)[:3]

    @staticmethod
    def _anti_example_lines(selected_examples: list[dict[str, Any]]) -> list[str]:
        """Return prompt lines for selected anti examples."""
        lines = ["\n[나쁜 예시 — 이렇게 쓰지 마세요]"]
        for idx, example in enumerate(selected_examples, 1):
            lines.append(f"- 나쁜 예시 {idx}: {example.get('text', '')}")
            if example.get("reason"):
                lines.append(f"  이유: {example['reason']}")
        return lines

    @staticmethod
    def _build_anti_examples_block(rules: dict[str, Any], topic_cluster: str) -> str:
        """Build the optional anti-example block for the current topic."""
        anti_examples = rules.get("anti_examples", {})
        selected_examples = DraftPromptsMixin._selected_anti_examples(anti_examples, topic_cluster)
        if not selected_examples:
            return ""

        return "\n".join(DraftPromptsMixin._anti_example_lines(selected_examples))

    @staticmethod
    def _selection_brief_values(profile: dict[str, Any], essence: dict[str, Any]) -> dict[str, str]:
        """Return values displayed in the X editorial brief."""
        return {
            "selection_summary": profile.get("selection_summary", "") or "직장인이 자기 일처럼 반응할 이유가 있는 글",
            "audience_need": profile.get("audience_need", "") or "직장인 현실 비교 욕구",
            "emotion_lane": profile.get("emotion_lane", "") or "공감과 웃음의 균형",
            "empathy_anchor": profile.get("empathy_anchor", "") or essence.get("opening", ""),
            "spinoff_angle": profile.get("spinoff_angle", "") or "현실 비교, 자기 경험",
        }

    @staticmethod
    def _selection_brief_lines(values: dict[str, str], output_formats: list[str]) -> list[str]:
        """Return prompt lines for the X editorial brief."""
        lines = [
            "[X 편집 브리프]",
            f"왜 고름: {values['selection_summary']}",
            f"독자 욕구: {values['audience_need']}",
            f"감정선: {values['emotion_lane']}",
            f"공감 앵커: {values['empathy_anchor']}",
            f"파생각: {values['spinoff_angle']}",
            "",
            "[반드시 지킬 것]",
            "1. 첫 문장은 장면, 대사, 숫자 중 하나로 시작할 것 (자극적 형용사 금지)",
            "2. 본문 안에 같이 웃거나 같이 한숨 쉬게 하는 포인트를 분명히 넣을 것",
            "3. 원문이 흥미로운 이유와 더 확장되는 이유를 분리해서 반영할 것",
            '4. 마지막은 여운이 남는 한 줄로 조용히 끝맺을 것. 질문·CTA·"여러분 ~?"·"댓글로 ~"·"저장해두세요" 모두 금지',
            '5. 인플루언서 어휘("시그널", "민낯", "끝판왕", "지뢰", "쓴맛", "기절할 뻔") 사용 금지',
            "6. 이모지는 기본 없음 — 정말 의미 있을 때만 1개 이하",
        ]
        if "twitter" in output_formats:
            lines.append("7. <twitter> 안에는 1개 안만 작성 (3안 묶음 금지)")
        return lines

    @staticmethod
    def _build_selection_brief_block(
        profile: dict[str, Any],
        essence: dict[str, Any],
        output_formats: list[str],
    ) -> str:
        """Build the X editorial brief block used by the user prompt."""
        values = DraftPromptsMixin._selection_brief_values(profile, essence)
        return "\n".join(DraftPromptsMixin._selection_brief_lines(values, output_formats))

    @staticmethod
    def _research_conflict_risk_note(research_context: dict[str, Any]) -> str:
        """Build the optional high-conflict warning note for auto-research context."""
        try:
            conflict_risk = float(research_context.get("conflict_risk") or 0.0)
        except (TypeError, ValueError):
            conflict_risk = 0.0

        if conflict_risk > 0.8:
            return "\n- 갈등 위험 높음: 성별/진영 대립으로 쓰지 말고 보편 가치로만 환원하세요."
        return ""

    @staticmethod
    def _research_context_block_values(research_context: dict[str, Any]) -> dict[str, Any]:
        """Return research context values with prompt defaults applied."""
        return {
            "source_frame": research_context.get("source_frame") or "N/A",
            "real_issue": research_context.get("real_issue") or "N/A",
            "universal_value": research_context.get("universal_value") or "N/A",
            "killer_sentence": research_context.get("killer_sentence") or "N/A",
            "closure": research_context.get("closure") or "open",
            "anchor": research_context.get("anchor") or "N/A",
        }

    @staticmethod
    def _research_context_from_post(post_data: dict[str, Any]) -> dict[str, Any]:
        """Return auto-research context only when the post stores it as a mapping."""
        research_context = post_data.get("research_context")
        return research_context if isinstance(research_context, dict) else {}

    @staticmethod
    def _format_research_context_block(values: dict[str, Any], risk_note: str) -> str:
        """Format the auto-research context prompt block."""
        return f"""
[오토리서치 컨텍스트 - 반드시 반영]
- 원문 프레임: {values["source_frame"]}
- 진짜 쟁점: {values["real_issue"]}
- 보편 가치: {values["universal_value"]}
- 반드시 포함할 킬러 문장: {values["killer_sentence"]}
- 결말 방식: {values["closure"]}
- 근거 앵커: {values["anchor"]}{risk_note}
작성 조건:
1. X 본문에는 위 킬러 문장을 그대로 1회 포함하세요.
2. 본문 중간에 "이건 ~가 아니라 ~입니다" 가치 선언을 반드시 넣으세요.
3. 개인 사례를 보편 원칙으로 환원하세요.
4. 결말 방식이 closed이면 단정형으로 닫고, open이면 정답이 하나가 아니라는 여지를 남기세요.
"""

    @staticmethod
    def _build_research_context_block(post_data: dict[str, Any]) -> str:
        """Build the optional auto-research context block."""
        research_context = DraftPromptsMixin._research_context_from_post(post_data)
        if not research_context:
            return ""

        risk_note = DraftPromptsMixin._research_conflict_risk_note(research_context)
        values = DraftPromptsMixin._research_context_block_values(research_context)
        return DraftPromptsMixin._format_research_context_block(values, risk_note)

    @staticmethod
    def _build_thinking_block(templates: dict[str, Any]) -> Any:
        """Build the thinking-instructions block, preferring configured templates."""
        thinking_template = templates.get("thinking_framework", "")
        if thinking_template:
            return thinking_template
        return _DEFAULT_THINKING_BLOCK

    @staticmethod
    def _brand_voice_bullet_lines(items: list[Any]) -> str:
        """Format brand voice list entries as indented bullets."""
        return "\n".join(f"  - {item}" for item in items)

    @staticmethod
    def _brand_voice_block_values(brand_voice: dict[str, Any]) -> dict[str, str]:
        """Return formatted brand voice values used by the prompt block."""
        examples = brand_voice.get("examples", {})
        return {
            "persona": brand_voice.get("persona", ""),
            "traits": DraftPromptsMixin._brand_voice_bullet_lines(brand_voice.get("voice_traits", [])),
            "forbidden": DraftPromptsMixin._brand_voice_bullet_lines(brand_voice.get("forbidden_expressions", [])),
            "good_example": examples.get("good", ""),
            "bad_example": examples.get("bad", ""),
        }

    @staticmethod
    def _format_brand_voice_block(values: dict[str, str]) -> str:
        """Format the brand voice prompt block."""
        return f"""
[보이스 가이드 — 반드시 준수]
페르소나: {values["persona"]}
말투 규칙:
{values["traits"]}
좋은 예: {values["good_example"]}
나쁜 예: {values["bad_example"]}

[절대 사용 금지 표현]
아래 표현은 AI스럽거나 상투적이므로 절대 사용하지 마세요:
{values["forbidden"]}
"""

    @staticmethod
    def _build_brand_voice_block(brand_voice: dict[str, Any]) -> str:
        """Build brand voice instructions when configured."""
        if not brand_voice:
            return ""

        values = DraftPromptsMixin._brand_voice_block_values(brand_voice)
        return DraftPromptsMixin._format_brand_voice_block(values)

    @staticmethod
    def _cliche_watchlist_lines(cliches: list[Any]) -> str:
        """Format the capped cliche watchlist entries."""
        return "\n".join(f'  - "{cliche}"' for cliche in cliches[:20])

    @staticmethod
    def _format_cliche_watchlist_block(cliche_lines: str) -> str:
        """Format the cliche watchlist prompt block."""
        return f"""
[절대 사용 금지 — 클리셰 목록]
아래 표현을 하나라도 사용하면 재생성 대상입니다:
{cliche_lines}
"""

    @staticmethod
    def _build_cliche_watchlist_block(cliches: list[Any]) -> str:
        """Build cliche watchlist instructions when configured."""
        if not cliches:
            return ""

        cliche_lines = DraftPromptsMixin._cliche_watchlist_lines(cliches)
        return DraftPromptsMixin._format_cliche_watchlist_block(cliche_lines)

    @staticmethod
    def _build_voice_block(rules: dict[str, Any]) -> str:
        """Build brand voice and cliche guardrail instructions."""
        voice_block = DraftPromptsMixin._build_brand_voice_block(rules.get("brand_voice", {}))
        return voice_block + DraftPromptsMixin._build_cliche_watchlist_block(rules.get("cliche_watchlist", []))

    @staticmethod
    def _build_image_prompt_block(templates: dict[str, Any]) -> Any:
        """Build image prompt instructions, preferring configured templates."""
        image_template = templates.get("image_prompt", "")
        if image_template:
            return image_template
        return _DEFAULT_IMAGE_PROMPT_BLOCK

    @staticmethod
    def _twitter_analysis_values(profile: dict[str, Any]) -> dict[str, Any]:
        """Return profile fields used by the default X/Twitter analysis block."""
        return {
            "audience_need": profile.get("audience_need", ""),
            "emotion_lane": profile.get("emotion_lane", ""),
            "empathy_anchor": profile.get("empathy_anchor", ""),
            "spinoff_angle": profile.get("spinoff_angle", ""),
        }

    @staticmethod
    def _twitter_analysis_lines(values: dict[str, Any]) -> list[str]:
        """Return content-analysis lines for the default X/Twitter prompt."""
        return [
            "[콘텐츠 분석 데이터]",
            f"- 타겟 니즈: {values['audience_need']}",
            f"- 감정선: {values['emotion_lane']}",
            f"- 킬링 포인트(Anchor): {values['empathy_anchor']}",
            f"- 확장 가능성(Spinoff): {values['spinoff_angle']}",
        ]

    @staticmethod
    def _format_twitter_analysis_block(values: dict[str, Any]) -> str:
        """Format the content-analysis context for the default X/Twitter prompt."""
        return "\n".join(DraftPromptsMixin._twitter_analysis_lines(values))

    @staticmethod
    def _build_twitter_analysis_block(profile: dict[str, Any]) -> str:
        """Build content-analysis context for the default X/Twitter prompt."""
        values = DraftPromptsMixin._twitter_analysis_values(profile)
        return DraftPromptsMixin._format_twitter_analysis_block(values)

    @staticmethod
    def _twitter_misc_lines(recommended_draft_type: str) -> list[str]:
        """Return miscellaneous constraint lines for the default X/Twitter prompt."""
        return [
            "[기타]",
            "- 본문에 링크나 해시태그는 넣지 마세요 (답글에 넣을 것).",
            f"- 1개의 안만 작성하세요. 추천 톤: '{recommended_draft_type}'.",
            "- 이모지는 기본 없음. 정말 의미 있을 때만 1개 이하.",
            "- 반드시 <twitter> 와 </twitter> 태그 안에만 작성.",
            "- 답글(원문 링크 포함)은 <reply> 와 </reply> 태그 안에 작성.",
        ]

    @staticmethod
    def _format_twitter_misc_block(recommended_draft_type: str) -> str:
        """Format miscellaneous constraints for the default X/Twitter prompt."""
        return "\n".join(DraftPromptsMixin._twitter_misc_lines(recommended_draft_type))

    @staticmethod
    def _build_twitter_misc_block(recommended_draft_type: str) -> str:
        """Build miscellaneous constraints for the default X/Twitter prompt."""
        return DraftPromptsMixin._format_twitter_misc_block(recommended_draft_type)

    @staticmethod
    def _twitter_fallback_values(
        source: str,
        profile: dict[str, Any],
        max_length: int,
        analysis_block: str,
        misc_block: str,
    ) -> dict[str, Any]:
        """Return values used by the default X/Twitter fallback block."""
        return {
            "source": source,
            "max_length": max_length,
            "analysis_block": analysis_block,
            "misc_block": misc_block,
            "empathy_anchor": profile.get("empathy_anchor", ""),
        }

    @staticmethod
    def _twitter_fallback_instruction_lines(values: dict[str, Any]) -> list[str]:
        """Return writing-instruction lines for the default X/Twitter fallback prompt."""
        return [
            "[작성 지침]",
            '1. 말투: 들려주듯 담담하게. AI 말투도, 인플루언서 톤("시그널/민낯/끝판왕/지뢰/쓴맛/기절할 뻔")도 모두 금지.',
            "2. 훅(Hook): 첫 문장은 장면·짧은 인용·구체적 숫자 중 하나로 시작하세요. 자극적 형용사는 피하세요.",
            f"3. 생략과 강조: 원문의 모든 내용을 담지 마세요. 가장 인상적인 지점 {values['empathy_anchor']} 하나에만 집중하세요.",
            '4. 마무리: 여운이 남는 한 줄로 조용히 끝내세요. 질문·CTA·"여러분 ~?"·"댓글로 ~" 모두 금지.',
            f"5. 형식: {values['max_length']}자 이내 (가능하면 200자 안으로). 출처 '{values['source']}' 표기는 선택 — 도입 강박 금지.",
        ]

    @staticmethod
    def _format_twitter_fallback_block(values: dict[str, Any]) -> str:
        """Format the default X/Twitter fallback prompt block."""
        instruction_block = "\n".join(DraftPromptsMixin._twitter_fallback_instruction_lines(values))
        return f"""\n[트위터(X) 초안 — 들려주듯 조용히]

당신은 옆에 앉은 사람에게 담담히 이야기를 풀어주는 직장인 콘텐츠 큐레이터입니다.
인플루언서 톤·자극적 명사화·과장은 모두 실패입니다.

{values["analysis_block"]}

{instruction_block}

{values["misc_block"]}
"""

    def _build_twitter_fallback_block(
        self,
        source: str,
        recommended_draft_type: str,
        profile: dict[str, Any],
    ) -> str:
        """Build the default X/Twitter prompt instructions."""
        analysis_block = self._build_twitter_analysis_block(profile)
        misc_block = self._build_twitter_misc_block(recommended_draft_type)
        values = self._twitter_fallback_values(source, profile, self.max_length, analysis_block, misc_block)
        return self._format_twitter_fallback_block(values)

    def _build_twitter_block(
        self,
        templates: dict[str, Any],
        output_formats: list[str],
        draft_format: str,
        source: str,
        recommended_draft_type: str,
        profile: dict[str, Any],
    ) -> str:
        """Build the X/Twitter output instruction block."""
        return self._build_twitter_block_from_request(
            self._build_output_block_request(
                templates,
                {},
                output_formats,
                draft_format,
                source,
                recommended_draft_type,
                profile,
                "",
                "",
                "",
            )
        )

    def _build_twitter_block_from_request(self, request: _OutputBlockRequest) -> str:
        """Build the X/Twitter output instruction block from an output request."""
        if "twitter" not in request.output_formats:
            return ""

        twitter_templates = request.templates.get("twitter", {})
        if request.draft_format == "thread" and "thread" in twitter_templates:
            return twitter_templates["thread"].format(
                source=request.source,
                recommended_draft_type=request.recommended_draft_type,
            )
        if "standard" in twitter_templates:
            return twitter_templates["standard"].format(
                max_length=self.max_length,
                source=request.source,
                recommended_draft_type=request.recommended_draft_type,
            )

        return self._build_twitter_fallback_block(request.source, request.recommended_draft_type, request.profile)

    @staticmethod
    def _newsletter_fallback_lines(empathy_anchor: str, spinoff_angle: str) -> list[str]:
        """Return lines for the default newsletter prompt block."""
        return [
            "",
            "[뉴스레터 초안 — 심층 큐레이션 및 인사이트]",
            "1. 목표: 바쁜 직장인에게 이 글이 왜 중요한지, 어떤 시사점이 있는지 '시니어 에디터'의 시각에서 정리합니다.",
            "2. 구조:",
            "   - 📢 헤드라인: 클릭을 유도하는 호기심 자극형 제목",
            "   - 📝 한 줄 요약: 핵심 내용 요약",
            f"   - 💡 에디터의 시선: {empathy_anchor}를 중심으로 한 심층 분석 및 {spinoff_angle} 제언",
            "   - ✅ 한 줄 결론/Action Item: 독자가 적용해볼 점",
            "3. 분량: 450자 이상 900자 이하.",
            "4. 말투: 신뢰감 있으면서도 친절한 전문 에디터 톤.",
            "5. 반드시 <newsletter> 와 </newsletter> 태그 안에만 작성하세요.",
            "",
        ]

    @staticmethod
    def _format_newsletter_fallback_block(empathy_anchor: str, spinoff_angle: str) -> str:
        """Format the default newsletter prompt block."""
        return "\n".join(DraftPromptsMixin._newsletter_fallback_lines(empathy_anchor, spinoff_angle))

    @staticmethod
    def _build_newsletter_block(
        templates: dict[str, Any],
        output_formats: list[str],
        empathy_anchor: str,
        spinoff_angle: str,
    ) -> str:
        """Build the newsletter output instruction block."""
        if "newsletter" not in output_formats:
            return ""

        nl_tmpl = templates.get("newsletter", "")
        return (
            nl_tmpl if nl_tmpl else DraftPromptsMixin._format_newsletter_fallback_block(empathy_anchor, spinoff_angle)
        )

    @staticmethod
    def _build_newsletter_block_from_request(request: _OutputBlockRequest) -> str:
        """Build the newsletter output instruction block from an output request."""
        return DraftPromptsMixin._build_newsletter_block(
            request.templates,
            request.output_formats,
            request.empathy_anchor,
            request.spinoff_angle,
        )

    @staticmethod
    def _resolved_topic_tone(
        rules: dict[str, Any],
        mapping_key: str,
        topic_cluster: str,
        default_tone: str,
    ) -> str:
        """Resolve topic-specific tone with generic and default fallbacks."""
        tone_map = rules.get(mapping_key, {})
        return tone_map.get(topic_cluster, tone_map.get("기타", default_tone))

    @staticmethod
    def _format_template_or_raw(template: str, **values: Any) -> str:
        """Format a configured template, or preserve it if placeholders drift."""
        try:
            return template.format(**values)
        except (KeyError, IndexError):
            return template

    @staticmethod
    def _threads_fallback_values(
        resolved_threads_tone: str,
        source: str,
        empathy_anchor: str,
        spinoff_angle: str,
        max_length: int,
        hashtags_count: int,
    ) -> dict[str, Any]:
        """Return values used by the default Threads fallback block."""
        return {
            "resolved_threads_tone": resolved_threads_tone,
            "source": source,
            "empathy_anchor": empathy_anchor,
            "spinoff_angle": spinoff_angle,
            "max_length": max_length,
            "hashtags_count": hashtags_count,
        }

    @staticmethod
    def _threads_fallback_lines(values: dict[str, Any]) -> list[str]:
        """Return lines for the default Threads fallback prompt block."""
        return [
            "",
            "[Threads 초안 — 친근한 스토리텔링 및 공감]",
            "1. 목표: 인스타그램/스레드 감성에 맞춰, 텍스트 위주지만 따뜻하고 친근하게 말을 겁니다.",
            "2. 전략:",
            f"   - {values['empathy_anchor']}를 내 이야기처럼 자연스럽게 풀어서 시작하세요.",
            "   - 트위터보다 조금 더 호흡이 길어도 좋으니 대화하듯 작성하세요.",
            f"   - {values['spinoff_angle']}을 활용해 독자의 개인적인 경험을 묻는 질문으로 마무리하세요.",
            "3. 형식:",
            f"   - {values['max_length']}자 이내.",
            f"   - 해시태그 {values['hashtags_count']}개 이내.",
            f"   - 출처 '{values['source']}'를 문맥에 맞게 언급.",
            f"4. 참고 톤: '{values['resolved_threads_tone']}'",
            "5. 반드시 <threads> 와 </threads> 태그 안에만 작성하세요.",
            "",
        ]

    @staticmethod
    def _format_threads_fallback_block(values: dict[str, Any]) -> str:
        """Format the default Threads fallback prompt block."""
        return "\n".join(DraftPromptsMixin._threads_fallback_lines(values))

    def _build_threads_fallback_block(
        self,
        resolved_threads_tone: str,
        source: str,
        empathy_anchor: str,
        spinoff_angle: str,
    ) -> str:
        """Build the default Threads prompt instructions."""
        values = self._threads_fallback_values(
            resolved_threads_tone,
            source,
            empathy_anchor,
            spinoff_angle,
            self.threads_max_length,
            self.threads_hashtags_count,
        )
        return self._format_threads_fallback_block(values)

    def _resolve_threads_tone(self, rules: dict[str, Any], topic_cluster: str) -> str:
        """Resolve the topic-aware Threads tone."""
        return self._resolved_topic_tone(rules, "tone_mapping_threads", topic_cluster, self.threads_tone)

    def _build_threads_block(
        self,
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        topic_cluster: str,
        source: str,
        recommended_draft_type: str,
        empathy_anchor: str,
        spinoff_angle: str,
    ) -> str:
        """Build the Threads output instruction block."""
        return self._build_threads_block_from_request(
            self._build_output_block_request(
                templates,
                rules,
                output_formats,
                "",
                source,
                recommended_draft_type,
                {},
                topic_cluster,
                empathy_anchor,
                spinoff_angle,
            )
        )

    def _build_threads_block_from_request(self, request: _OutputBlockRequest) -> str:
        """Build the Threads output instruction block from an output request."""
        if "threads" not in request.output_formats:
            return ""

        threads_tmpl = request.templates.get("threads", "")
        resolved_threads_tone = self._resolve_threads_tone(request.rules, request.topic_cluster)
        if threads_tmpl:
            return self._format_template_or_raw(
                threads_tmpl,
                threads_tone=resolved_threads_tone,
                source=request.source,
                recommended_draft_type=request.recommended_draft_type,
            )

        return self._build_threads_fallback_block(
            resolved_threads_tone,
            request.source,
            request.empathy_anchor,
            request.spinoff_angle,
        )

    @staticmethod
    def _naver_blog_fallback_values(
        resolved_blog_tone: str,
        source: str,
        min_length: int,
        max_length: int,
        seo_tags_count: int,
    ) -> dict[str, Any]:
        """Return values used by the default Naver Blog fallback block."""
        return {
            "resolved_blog_tone": resolved_blog_tone,
            "source": source,
            "min_length": min_length,
            "max_length": max_length,
            "seo_tags_count": seo_tags_count,
        }

    @staticmethod
    def _naver_blog_fallback_lines(values: dict[str, Any]) -> list[str]:
        """Return lines for the default Naver Blog fallback prompt block."""
        return [
            "",
            "[네이버 블로그 — 해설형 큐레이션 초안 작성 조건]",
            "★ 핵심 전환: 단일 게시물 확장이 아니라, 여러 소스의 유사 시그널을 묶어 해설하는 '패턴 리포트'를 작성하세요.",
            f"1. {values['min_length']}자 이상 {values['max_length']}자 이하로 작성하세요.",
            "2. 아래 구조를 따르세요:",
            "   ## 이번 주 직장인 커뮤니티에서 감지된 시그널",
            "   (도입부: 여러 커뮤니티에서 동시에 터진 주제가 무엇인지)",
            "   ## 무슨 일이 벌어지고 있나",
            "   (본문: 각 소스별 반응 요약 — 원문 복붙 금지, 패턴 요약만)",
            "   ## 왜 지금 이 주제가 뜨는가",
            "   (인사이트: 구조적 원인 해설)",
            "   ## 실무자가 알아야 할 것",
            "   (결론: 독자가 얻는 실용 포인트 + CTA)",
            "3. 검색 유입을 고려해 핵심 키워드를 자연스럽게 반복하세요.",
            f"4. SEO 해시태그를 {values['seo_tags_count']}개 글 끝에 추가하세요.",
            f"5. 정중하지만 위트 있는 해설자 톤을 유지하세요. 참고 톤: '{values['resolved_blog_tone']}'",
            "6. 반드시 <creator_take> 태그 안에 운영자의 핵심 해석 1문장을 작성하세요.",
            f"7. 원문 '{values['source']}'을 서두 또는 본문에서 간접적으로 언급하세요.",
            "8. 반드시 <naver_blog> 와 </naver_blog> 태그 안에만 작성하세요.",
            "",
        ]

    @staticmethod
    def _format_naver_blog_fallback_block(values: dict[str, Any]) -> str:
        """Format the default Naver Blog fallback prompt block."""
        return "\n".join(DraftPromptsMixin._naver_blog_fallback_lines(values))

    def _build_naver_blog_fallback_block(self, resolved_blog_tone: str, source: str) -> str:
        """Build the default Naver Blog prompt instructions."""
        values = self._naver_blog_fallback_values(
            resolved_blog_tone,
            source,
            self.blog_min_length,
            self.blog_max_length,
            self.blog_seo_tags_count,
        )
        return self._format_naver_blog_fallback_block(values)

    def _resolve_naver_blog_tone(self, rules: dict[str, Any], topic_cluster: str) -> str:
        """Resolve the topic-aware Naver Blog tone."""
        return self._resolved_topic_tone(rules, "tone_mapping_naver_blog", topic_cluster, self.blog_tone)

    def _build_naver_blog_block(
        self,
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        topic_cluster: str,
        source: str,
        recommended_draft_type: str,
    ) -> str:
        """Build the Naver Blog output instruction block."""
        return self._build_naver_blog_block_from_request(
            self._build_output_block_request(
                templates,
                rules,
                output_formats,
                "",
                source,
                recommended_draft_type,
                {},
                topic_cluster,
                "",
                "",
            )
        )

    def _build_naver_blog_block_from_request(self, request: _OutputBlockRequest) -> str:
        """Build the Naver Blog output instruction block from an output request."""
        if "naver_blog" not in request.output_formats:
            return ""

        blog_tmpl = request.templates.get("naver_blog", "")
        resolved_blog_tone = self._resolve_naver_blog_tone(request.rules, request.topic_cluster)
        if blog_tmpl:
            return self._format_template_or_raw(
                blog_tmpl,
                naver_blog_tone=resolved_blog_tone,
                source=request.source,
                recommended_draft_type=request.recommended_draft_type,
            )

        return self._build_naver_blog_fallback_block(resolved_blog_tone, request.source)

    def _build_shortform_output_blocks(
        self,
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        draft_format: str,
        source: str,
        recommended_draft_type: str,
        profile: dict[str, Any],
        topic_cluster: str,
        empathy_anchor: str,
        spinoff_angle: str,
    ) -> dict[str, str]:
        """Build output prompt blocks for short-form social platforms."""
        return self._build_shortform_output_blocks_from_request(
            self._build_output_block_request(
                templates,
                rules,
                output_formats,
                draft_format,
                source,
                recommended_draft_type,
                profile,
                topic_cluster,
                empathy_anchor,
                spinoff_angle,
            )
        )

    def _shortform_output_block_values(self, request: _OutputBlockRequest) -> dict[str, str]:
        """Return short-form platform output block values."""
        return {
            "twitter": self._build_twitter_block_from_request(request),
            "threads": self._build_threads_block_from_request(request),
        }

    def _build_shortform_output_blocks_from_request(self, request: _OutputBlockRequest) -> dict[str, str]:
        """Build short-form social output blocks from a named request object."""
        block_values = self._shortform_output_block_values(request)
        return {key: block_values[key] for key in _SHORTFORM_OUTPUT_BLOCK_KEYS}

    def _build_longform_output_blocks(
        self,
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        source: str,
        recommended_draft_type: str,
        topic_cluster: str,
        empathy_anchor: str,
        spinoff_angle: str,
    ) -> dict[str, str]:
        """Build output prompt blocks for longer-form publishing formats."""
        return self._build_longform_output_blocks_from_request(
            self._build_output_block_request(
                templates,
                rules,
                output_formats,
                "",
                source,
                recommended_draft_type,
                {},
                topic_cluster,
                empathy_anchor,
                spinoff_angle,
            )
        )

    def _longform_output_block_values(self, request: _OutputBlockRequest) -> dict[str, str]:
        """Return long-form platform output block values."""
        return {
            "newsletter": self._build_newsletter_block_from_request(request),
            "naver_blog": self._build_naver_blog_block_from_request(request),
        }

    def _build_longform_output_blocks_from_request(self, request: _OutputBlockRequest) -> dict[str, str]:
        """Build longer-form publishing output blocks from a named request object."""
        block_values = self._longform_output_block_values(request)
        return {key: block_values[key] for key in _LONGFORM_OUTPUT_BLOCK_KEYS}

    @staticmethod
    def _merge_platform_output_blocks(
        shortform_blocks: dict[str, str],
        longform_blocks: dict[str, str],
    ) -> dict[str, str]:
        """Merge platform blocks in the historical prompt order."""
        block_values = {
            "twitter": shortform_blocks["twitter"],
            "newsletter": longform_blocks["newsletter"],
            "threads": shortform_blocks["threads"],
            "naver_blog": longform_blocks["naver_blog"],
        }
        return {key: block_values[key] for key in _PLATFORM_OUTPUT_BLOCK_KEYS}

    @staticmethod
    def _build_output_block_request(
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        draft_format: str,
        source: str,
        recommended_draft_type: str,
        profile: dict[str, Any],
        topic_cluster: str,
        empathy_anchor: str,
        spinoff_angle: str,
    ) -> _OutputBlockRequest:
        """Pack output-format parameters into a named request object."""
        return _OutputBlockRequest(
            templates=templates,
            rules=rules,
            output_formats=output_formats,
            draft_format=draft_format,
            source=source,
            recommended_draft_type=recommended_draft_type,
            profile=profile,
            topic_cluster=topic_cluster,
            empathy_anchor=empathy_anchor,
            spinoff_angle=spinoff_angle,
        )

    def _build_platform_output_blocks_from_request(self, request: _OutputBlockRequest) -> dict[str, str]:
        """Build text platform output blocks from a named request object."""
        shortform_blocks = self._build_shortform_output_blocks_from_request(request)
        longform_blocks = self._build_longform_output_blocks_from_request(request)
        return self._merge_platform_output_blocks(shortform_blocks, longform_blocks)

    def _build_platform_output_blocks(
        self,
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        draft_format: str,
        source: str,
        recommended_draft_type: str,
        profile: dict[str, Any],
        topic_cluster: str,
        empathy_anchor: str,
        spinoff_angle: str,
    ) -> dict[str, str]:
        """Build output prompt blocks for text publishing platforms."""
        request = self._build_output_block_request(
            templates,
            rules,
            output_formats,
            draft_format,
            source,
            recommended_draft_type,
            profile,
            topic_cluster,
            empathy_anchor,
            spinoff_angle,
        )
        return self._build_platform_output_blocks_from_request(request)

    def _build_output_format_blocks(
        self,
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        draft_format: str,
        source: str,
        recommended_draft_type: str,
        profile: dict[str, Any],
        topic_cluster: str,
        empathy_anchor: str,
        spinoff_angle: str,
    ) -> dict[str, str]:
        """Build output-format prompt blocks used by the user prompt."""
        return self._build_output_format_blocks_from_request(
            self._build_output_block_request(
                templates,
                rules,
                output_formats,
                draft_format,
                source,
                recommended_draft_type,
                profile,
                topic_cluster,
                empathy_anchor,
                spinoff_angle,
            )
        )

    def _build_output_format_blocks_from_request(self, request: _OutputBlockRequest) -> dict[str, str]:
        """Build full output-format prompt blocks from a named request object."""
        groups = self._output_format_block_groups(request)
        return self._merge_output_format_blocks(groups.platform_blocks, groups.auxiliary_blocks)

    def _output_format_block_groups(self, request: _OutputBlockRequest) -> _OutputFormatBlockGroups:
        """Build platform and auxiliary block groups from an output request."""
        platform_blocks = self._build_platform_output_blocks_from_request(request)
        regulation_blocks = self._build_regulation_output_blocks(request.output_formats)
        auxiliary_blocks = self._build_auxiliary_output_blocks(request.templates, regulation_blocks)
        return _OutputFormatBlockGroups(
            platform_blocks=platform_blocks,
            auxiliary_blocks=auxiliary_blocks,
        )

    @staticmethod
    def _merge_output_format_blocks(
        platform_blocks: dict[str, str],
        auxiliary_blocks: dict[str, str],
    ) -> dict[str, str]:
        """Merge platform and auxiliary output blocks for final prompt assembly."""
        return {**platform_blocks, **auxiliary_blocks}

    def _auxiliary_output_block_values(
        self,
        templates: dict[str, Any],
        regulation_blocks: dict[str, str],
    ) -> dict[str, str]:
        """Return non-platform output block values."""
        return {
            "image": self._build_image_prompt_block(templates),
            "regulation_context": regulation_blocks["regulation_context"],
            "regulation_check": regulation_blocks["regulation_check"],
        }

    def _build_auxiliary_output_blocks(
        self,
        templates: dict[str, Any],
        regulation_blocks: dict[str, str],
    ) -> dict[str, str]:
        """Build non-platform output blocks appended after text outputs."""
        block_values = self._auxiliary_output_block_values(templates, regulation_blocks)
        return {key: block_values[key] for key in _AUXILIARY_OUTPUT_BLOCK_KEYS}

    @staticmethod
    def _output_request_context_values(context: dict[str, Any]) -> dict[str, Any]:
        """Return normalized context values used by output-block requests."""
        return {
            "source": context["source"],
            "recommended_draft_type": context["recommended_draft_type"],
            "profile": context["profile"],
            "topic_cluster": context["topic_cluster"],
            "empathy_anchor": context["empathy_anchor"],
            "spinoff_angle": context["spinoff_angle"],
        }

    def _build_output_block_request_from_context(
        self,
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        draft_format: str,
        context: dict[str, Any],
    ) -> _OutputBlockRequest:
        """Build output-block request parameters from normalized prompt context."""
        values = self._output_request_context_values(context)
        return self._build_output_block_request(
            templates,
            rules,
            output_formats,
            draft_format,
            values["source"],
            values["recommended_draft_type"],
            values["profile"],
            values["topic_cluster"],
            values["empathy_anchor"],
            values["spinoff_angle"],
        )

    def _build_output_format_blocks_from_context(
        self,
        templates: dict[str, Any],
        rules: dict[str, Any],
        output_formats: list[str],
        draft_format: str,
        context: dict[str, Any],
    ) -> dict[str, str]:
        """Build output-format prompt blocks from normalized prompt context."""
        return self._build_output_format_blocks_from_request(
            self._build_output_block_request_from_context(
                templates,
                rules,
                output_formats,
                draft_format,
                context,
            )
        )

    @staticmethod
    def _guidance_context_values(context: dict[str, Any]) -> dict[str, Any]:
        """Return normalized context fields used by prompt guidance blocks."""
        return {
            "essence": context["essence"],
            "profile": context["profile"],
            "topic_cluster": context["topic_cluster"],
        }

    @staticmethod
    def _build_guidance_blocks_from_context(
        rules: dict[str, Any],
        templates: dict[str, Any],
        post_data: dict[str, Any],
        output_formats: list[str],
        context: dict[str, Any],
    ) -> dict[str, str]:
        """Build non-output prompt guidance blocks from normalized prompt context."""
        values = DraftPromptsMixin._guidance_context_values(context)
        return DraftPromptsMixin._build_guidance_blocks(
            rules,
            templates,
            post_data,
            values["essence"],
            values["profile"],
            output_formats,
            values["topic_cluster"],
        )

    @staticmethod
    def _reference_seed_from_context(post_data: dict[str, Any], context: dict[str, Any]) -> str:
        """Build the deterministic reference-example seed from prompt context."""
        return f"{post_data.get('title', '')}|{context['profile'].get('selection_summary', '')}"

    @staticmethod
    def _build_reference_blocks_from_context(
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        context: dict[str, Any],
    ) -> dict[str, str]:
        """Build reference blocks using the normalized prompt context seed."""
        return DraftPromptsMixin._build_reference_blocks(
            top_examples,
            topic_cluster=context["topic_cluster"],
            seed_text=DraftPromptsMixin._reference_seed_from_context(post_data, context),
        )

    @staticmethod
    def _build_prompt_component_request(
        *,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str,
        context: dict[str, Any],
        rules: dict[str, Any],
        templates: dict[str, Any],
    ) -> _PromptComponentRequest:
        """Pack prompt component parameters into a named request object."""
        return _PromptComponentRequest(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format=draft_format,
            context=context,
            rules=rules,
            templates=templates,
        )

    def _build_prompt_component_blocks(
        self,
        *,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str,
        context: dict[str, Any],
        rules: dict[str, Any],
        templates: dict[str, Any],
    ) -> dict[str, dict[str, str]]:
        """Build output, guidance, and reference block groups for the final prompt."""
        return self._build_prompt_component_blocks_from_request(
            self._build_prompt_component_request(
                post_data=post_data,
                top_examples=top_examples,
                output_formats=output_formats,
                draft_format=draft_format,
                context=context,
                rules=rules,
                templates=templates,
            )
        )

    def _prompt_component_block_values(
        self,
        request: _PromptComponentRequest,
    ) -> dict[str, dict[str, str]]:
        """Return output, guidance, and reference block group values."""
        groups = self._prompt_component_block_groups(request)
        return {
            "output": groups.output_blocks,
            "guidance": groups.guidance_blocks,
            "reference": groups.reference_blocks,
        }

    def _prompt_component_block_groups(
        self,
        request: _PromptComponentRequest,
    ) -> _PromptComponentBlockGroups:
        """Build named output, guidance, and reference block groups."""
        return _PromptComponentBlockGroups(
            output_blocks=self._build_output_format_blocks_from_context(
                request.templates,
                request.rules,
                request.output_formats,
                request.draft_format,
                request.context,
            ),
            guidance_blocks=self._build_guidance_blocks_from_context(
                request.rules,
                request.templates,
                request.post_data,
                request.output_formats,
                request.context,
            ),
            reference_blocks=self._build_reference_blocks_from_context(
                request.post_data,
                request.top_examples,
                request.context,
            ),
        )

    def _build_prompt_component_blocks_from_request(
        self,
        request: _PromptComponentRequest,
    ) -> dict[str, dict[str, str]]:
        """Build output, guidance, and reference block groups from a named request object."""
        block_values = self._prompt_component_block_values(request)
        return {key: block_values[key] for key in _PROMPT_COMPONENT_BLOCK_KEYS}

    @staticmethod
    def _build_prompt_component_request_from_context(
        *,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str,
        context: dict[str, Any],
        rules: dict[str, Any],
        templates: dict[str, Any],
    ) -> _PromptComponentRequest:
        """Build a prompt component request from normalized prompt context and config."""
        return DraftPromptsMixin._build_prompt_component_request(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format=draft_format,
            context=context,
            rules=rules,
            templates=templates,
        )

    @staticmethod
    def _load_prompt_template_config() -> tuple[dict[str, Any], dict[str, Any], Any]:
        """Load draft rules, prompt templates, and the resolved system role."""
        rules = _load_draft_rules()
        templates = rules.get("prompt_templates", {})
        system_role = templates.get("system_role", _DEFAULT_SYSTEM_ROLE)
        return rules, templates, system_role

    @staticmethod
    def _regulation_check_lines() -> list[str]:
        """Return regulation self-check report prompt lines."""
        return [
            "",
            "[자체 규제 검증 리포트 작성 조건]",
            "1. 각 플랫폼 초안 작성 후, 아래 형식의 자체 검증 리포트를 반드시 작성하세요.",
            "2. 반드시 <regulation_check> 와 </regulation_check> 태그 안에만 작성하세요.",
            "3. 형식:",
            "   ✅ 또는 ⚠️ | 플랫폼명 | 검증 항목 | 결과 설명",
            "   예시:",
            "   ✅ X | 글자 수 | 267자 (280자 이내 준수)",
            "   ⚠️ Threads | 외부 링크 | 링크 1개 발견 — 댓글로 분리 권장",
            "",
        ]

    @staticmethod
    def _build_regulation_check_block(regulation_context: str) -> str:
        """Build the regulation self-check instructions when regulation context exists."""
        if not regulation_context:
            return ""
        return "\n".join(DraftPromptsMixin._regulation_check_lines())

    def _build_regulation_context(self, output_formats: list[str]) -> str:
        """Build regulation context for supported output platforms."""
        try:
            return self.regulation_checker.build_regulation_context(
                platforms=[fmt for fmt in output_formats if fmt in _REGULATION_SUPPORTED_OUTPUT_FORMATS]
            )
        except Exception as exc:
            logger.debug("Failed to build regulation context (ignored): %s", exc)
            return ""

    def _regulation_output_block_values(self, output_formats: list[str]) -> dict[str, str]:
        """Return paired regulation context and self-check block values."""
        regulation_context = self._build_regulation_context(output_formats)
        return {
            "regulation_context": regulation_context,
            "regulation_check": self._build_regulation_check_block(regulation_context),
        }

    def _build_regulation_output_blocks(self, output_formats: list[str]) -> dict[str, str]:
        """Build paired regulation context and self-check blocks."""
        block_values = self._regulation_output_block_values(output_formats)
        return {key: block_values[key] for key in _REGULATION_OUTPUT_BLOCK_KEYS}

    @staticmethod
    def _content_profile(post_data: dict[str, Any]) -> dict[str, Any]:
        """Return the normalized content profile mapping used by prompt context."""
        return post_data.get("content_profile", {}) or {}

    @staticmethod
    def _prompt_profile_values(profile: dict[str, Any]) -> dict[str, str]:
        """Return profile-derived values used by prompt context."""
        return {
            "topic_cluster": profile.get("topic_cluster", "기타"),
            "recommended_draft_type": profile.get("recommended_draft_type", "공감형"),
            "empathy_anchor": profile.get("empathy_anchor", ""),
            "spinoff_angle": profile.get("spinoff_angle", ""),
        }

    def _prompt_base_values(self, post_data: dict[str, Any]) -> dict[str, Any]:
        """Return post-derived base values used by prompt context."""
        return {
            "content": self._prompt_content(post_data),
            "source": post_data.get("source", "블라인드"),
            "tone": self._resolve_tone(post_data),
        }

    @staticmethod
    def _prompt_context_values(
        essence: dict[str, Any],
        profile: dict[str, Any],
        profile_values: dict[str, str],
        base_values: dict[str, Any],
    ) -> dict[str, Any]:
        """Return merged prompt context values before ordered projection."""
        return {
            "essence": essence,
            "content": base_values["content"],
            "source": base_values["source"],
            "tone": base_values["tone"],
            "profile": profile,
            "topic_cluster": profile_values["topic_cluster"],
            "recommended_draft_type": profile_values["recommended_draft_type"],
            "empathy_anchor": profile_values["empathy_anchor"],
            "spinoff_angle": profile_values["spinoff_angle"],
        }

    def _build_prompt_context(self, post_data: dict[str, Any]) -> dict[str, Any]:
        """Extract deterministic context used by the main prompt builder."""
        essence = self._extract_content_essence(post_data)
        profile = self._content_profile(post_data)
        profile_values = self._prompt_profile_values(profile)
        base_values = self._prompt_base_values(post_data)
        context_values = self._prompt_context_values(essence, profile, profile_values, base_values)
        return {key: context_values[key] for key in _PROMPT_CONTEXT_KEYS}

    @staticmethod
    def _build_anthropic_user_prompt_request(
        *,
        post_data: dict[str, Any],
        context: dict[str, Any],
        guidance_blocks: dict[str, str],
        output_blocks: dict[str, str],
        reference_blocks: dict[str, str],
    ) -> _AnthropicUserPromptRequest:
        """Build a named request object for Anthropic user prompt construction."""
        return _AnthropicUserPromptRequest(
            post_data=post_data,
            context=context,
            guidance_blocks=guidance_blocks,
            output_blocks=output_blocks,
            reference_blocks=reference_blocks,
        )

    def _build_anthropic_user_blocks_from_request(self, request: _AnthropicUserPromptRequest) -> dict[str, str]:
        """Build the Anthropic user prompt block map from a prompt request."""
        return self._build_anthropic_user_blocks(
            essence_block=request.guidance_blocks["essence"],
            selection_brief_block=request.guidance_blocks["selection_brief"],
            comment_trigger_block=request.guidance_blocks["comment_trigger"],
            research_block=request.guidance_blocks["research"],
            topic_strategy_block=request.guidance_blocks["topic_strategy"],
            thinking_block=request.guidance_blocks["thinking"],
            anti_examples_block=request.guidance_blocks["anti_examples"],
            output_blocks=request.output_blocks,
            reference_blocks=request.reference_blocks,
        )

    @staticmethod
    def _anthropic_user_prompt_values(context: dict[str, Any]) -> dict[str, Any]:
        """Return context fields used by the Anthropic user prompt."""
        return {
            "content": context["content"],
            "source": context["source"],
            "tone": context["tone"],
            "profile": context["profile"],
            "topic_cluster": context["topic_cluster"],
            "recommended_draft_type": context["recommended_draft_type"],
        }

    def _build_anthropic_user_prompt_from_request(self, request: _AnthropicUserPromptRequest) -> str:
        """Build the Anthropic user prompt from a named request object."""
        user_blocks = self._build_anthropic_user_blocks_from_request(request)
        values = self._anthropic_user_prompt_values(request.context)
        return self._build_anthropic_user_prompt(
            post_data=request.post_data,
            content=values["content"],
            source=values["source"],
            tone=values["tone"],
            profile=values["profile"],
            topic_cluster=values["topic_cluster"],
            recommended_draft_type=values["recommended_draft_type"],
            blocks=user_blocks,
        )

    def _build_anthropic_user_prompt_from_blocks(
        self,
        *,
        post_data: dict[str, Any],
        context: dict[str, Any],
        guidance_blocks: dict[str, str],
        output_blocks: dict[str, str],
        reference_blocks: dict[str, str],
    ) -> str:
        """Build the Anthropic user prompt after all component blocks are prepared."""
        return self._build_anthropic_user_prompt_from_request(
            self._build_anthropic_user_prompt_request(
                post_data=post_data,
                context=context,
                guidance_blocks=guidance_blocks,
                output_blocks=output_blocks,
                reference_blocks=reference_blocks,
            )
        )

    @staticmethod
    def _build_anthropic_prompt_result_request(
        *,
        post_data: dict[str, Any],
        context: dict[str, Any],
        system_role: Any,
        guidance_blocks: dict[str, str],
        output_blocks: dict[str, str],
        reference_blocks: dict[str, str],
    ) -> _AnthropicPromptResultRequest:
        """Build a named request object for the final split Anthropic prompt."""
        return _AnthropicPromptResultRequest(
            post_data=post_data,
            context=context,
            system_role=system_role,
            guidance_blocks=guidance_blocks,
            output_blocks=output_blocks,
            reference_blocks=reference_blocks,
        )

    def _build_anthropic_system_prompt_from_request(self, request: _AnthropicPromptResultRequest) -> str:
        """Build the split Anthropic system prompt from a result request."""
        return self._build_anthropic_system_prompt(
            request.system_role,
            request.guidance_blocks["voice"],
            request.reference_blocks["reviewer_memory"],
        )

    @staticmethod
    def _combined_anthropic_prompt_text(anthropic_system_prompt: str, anthropic_user_prompt: str) -> str:
        """Return the combined prompt text used for legacy DraftPrompt.content."""
        return f"{anthropic_system_prompt}\n\n{anthropic_user_prompt}".strip()

    def _build_anthropic_prompt_result_from_request(self, request: _AnthropicPromptResultRequest) -> DraftPrompt:
        """Build the final split Anthropic prompt result from a named request object."""
        anthropic_system_prompt = self._build_anthropic_system_prompt_from_request(request)
        anthropic_user_prompt = self._build_anthropic_user_prompt_from_request(
            self._build_anthropic_user_prompt_request(
                post_data=request.post_data,
                context=request.context,
                guidance_blocks=request.guidance_blocks,
                output_blocks=request.output_blocks,
                reference_blocks=request.reference_blocks,
            )
        )
        return DraftPrompt(
            self._combined_anthropic_prompt_text(anthropic_system_prompt, anthropic_user_prompt),
            anthropic_system_prompt=anthropic_system_prompt,
            anthropic_user_prompt=anthropic_user_prompt,
        )

    def _build_anthropic_prompt_result(
        self,
        *,
        post_data: dict[str, Any],
        context: dict[str, Any],
        system_role: Any,
        guidance_blocks: dict[str, str],
        output_blocks: dict[str, str],
        reference_blocks: dict[str, str],
    ) -> DraftPrompt:
        """Build the final split Anthropic prompt result from prepared blocks."""
        return self._build_anthropic_prompt_result_from_request(
            self._build_anthropic_prompt_result_request(
                post_data=post_data,
                context=context,
                system_role=system_role,
                guidance_blocks=guidance_blocks,
                output_blocks=output_blocks,
                reference_blocks=reference_blocks,
            )
        )

    @staticmethod
    def _build_anthropic_prompt_result_request_from_components(
        *,
        post_data: dict[str, Any],
        context: dict[str, Any],
        system_role: Any,
        component_blocks: dict[str, dict[str, str]],
    ) -> _AnthropicPromptResultRequest:
        """Build a final Anthropic result request from prepared component blocks."""
        return DraftPromptsMixin._build_anthropic_prompt_result_request(
            post_data=post_data,
            context=context,
            system_role=system_role,
            guidance_blocks=component_blocks["guidance"],
            output_blocks=component_blocks["output"],
            reference_blocks=component_blocks["reference"],
        )

    def _build_anthropic_prompt_result_from_components(
        self,
        *,
        post_data: dict[str, Any],
        context: dict[str, Any],
        system_role: Any,
        component_blocks: dict[str, dict[str, str]],
    ) -> DraftPrompt:
        """Build the final split Anthropic prompt from prepared component blocks."""
        return self._build_anthropic_prompt_result_from_request(
            self._build_anthropic_prompt_result_request_from_components(
                post_data=post_data,
                context=context,
                system_role=system_role,
                component_blocks=component_blocks,
            )
        )

    def _build_prompt_component_request_from_config(
        self,
        *,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str,
        context: dict[str, Any],
        rules: dict[str, Any],
        templates: dict[str, Any],
    ) -> _PromptComponentRequest:
        """Build the prompt component request after config and context are loaded."""
        return self._build_prompt_component_request_from_context(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format=draft_format,
            context=context,
            rules=rules,
            templates=templates,
        )

    def _prompt_preparation_values(self, post_data: dict[str, Any]) -> dict[str, Any]:
        """Return normalized prompt context and loaded template config values."""
        context = self._build_prompt_context(post_data)
        rules, templates, system_role = self._load_prompt_template_config()
        return {
            "context": context,
            "rules": rules,
            "templates": templates,
            "system_role": system_role,
        }

    def _build_prompt_preparation(self, post_data: dict[str, Any]) -> _PromptPreparation:
        """Prepare normalized prompt context and loaded template config."""
        values = self._prompt_preparation_values(post_data)
        return _PromptPreparation(
            context=values["context"],
            rules=values["rules"],
            templates=values["templates"],
            system_role=values["system_role"],
        )

    def _prompt_component_request_from_preparation(
        self,
        *,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str,
        preparation: _PromptPreparation,
    ) -> _PromptComponentRequest:
        """Build prompt component request values from prepared context and config."""
        return self._build_prompt_component_request_from_config(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format=draft_format,
            context=preparation.context,
            rules=preparation.rules,
            templates=preparation.templates,
        )

    def _build_prompt_component_blocks_from_config(
        self,
        *,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str,
        preparation: _PromptPreparation,
    ) -> dict[str, dict[str, str]]:
        """Build prompt component blocks from prepared context and config."""
        component_request = self._prompt_component_request_from_preparation(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format=draft_format,
            preparation=preparation,
        )
        return self._build_prompt_component_blocks_from_request(component_request)

    def _build_prompt_result_from_preparation(
        self,
        *,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str,
        preparation: _PromptPreparation,
    ) -> DraftPrompt:
        """Build the final prompt result from prepared context and config."""
        component_blocks = self._build_prompt_component_blocks_from_config(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format=draft_format,
            preparation=preparation,
        )
        return self._build_anthropic_prompt_result_from_components(
            post_data=post_data,
            context=preparation.context,
            system_role=preparation.system_role,
            component_blocks=component_blocks,
        )

    # ------------------------------------------------------------------
    # Main prompt builder
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str = "standard",
    ) -> str:
        """YAML 기반 프롬프트 조립. YAML 로드 실패 시 하드코딩 fallback."""
        preparation = self._build_prompt_preparation(post_data)
        return self._build_prompt_result_from_preparation(
            post_data=post_data,
            top_examples=top_examples,
            output_formats=output_formats,
            draft_format=draft_format,
            preparation=preparation,
        )

    # ------------------------------------------------------------------
    # Retry prompt
    # ------------------------------------------------------------------

    # P0-4: 품질 게이트 실패 유형별 구체적 수정 지침
    _FIX_INSTRUCTIONS: dict[str, str] = {
        "최소 글자 수": "글이 너무 짧습니다. 원문의 구체적인 사례, 숫자, 인용구를 추가하여 더 풍성하게 작성하세요.",
        "최소 길이": "글이 너무 짧습니다. 원문의 구체적인 사례, 숫자, 인용구를 추가하여 더 풍성하게 작성하세요.",
        "최대 글자 수": "글이 너무 깁니다. 불필요한 수식어와 반복을 제거하고 핵심만 남기세요.",
        "최대 길이": "글이 너무 깁니다. 불필요한 수식어와 반복을 제거하고 핵심만 남기세요.",
        "CTA": "CTA 문장(질문/유도)을 제거하고 여운이 남는 한 줄로 대체하세요. 독자가 스스로 생각하게 두세요.",
        "해시태그": "해시태그 수를 플랫폼 기준에 맞추세요. 핵심 키워드 중심으로 정리하세요.",
        "클리셰": "상투적 표현을 원문의 구체적인 디테일(숫자, 인용, 에피소드)로 대체하세요.",
        "한글 비율": "영어/특수문자 비율이 너무 높습니다. 한국어 문장을 자연스럽게 늘리세요.",
        "금지 패턴": "외부 링크 등 금지된 패턴이 포함되어 있습니다. 제거하세요.",
        "소제목": "소제목(##)을 3~4개 사용하여 글을 구조화하세요.",
        "SEO 태그": "글 끝에 검색 키워드 태그를 추가하세요.",
    }

    def _fix_instruction_for_issue(self, issue: Any) -> str:
        """Return a concrete retry instruction for a quality issue."""
        issue_text = str(issue)
        for key, instruction in self._FIX_INSTRUCTIONS.items():
            if key in issue_text:
                return instruction
        return ""

    def _retry_feedback_issue_lines(self, issue: Any) -> list[str]:
        """Return retry feedback lines for one quality issue."""
        lines = [f"  - {issue}"]
        instruction = self._fix_instruction_for_issue(issue)
        if instruction:
            lines.append(f"    → 수정 방법: {instruction}")
        return lines

    def _retry_feedback_group_lines(self, feedback: dict[str, Any]) -> list[str]:
        """Return retry feedback lines for one platform quality report."""
        platform = feedback.get("platform", "unknown")
        score = feedback.get("score", 0)
        issues = feedback.get("issues", [])
        lines = [f"\n❌ {platform} (점수: {score}/100):"]
        for issue in issues:
            lines.extend(self._retry_feedback_issue_lines(issue))
        return lines

    def _retry_feedback_lines(self, quality_feedback: list[dict[str, Any]]) -> list[str]:
        """Build retry feedback lines from quality-gate failures."""
        feedback_lines = [
            "",
            "━" * 40,
            "[이전 초안 품질 게이트 실패 — 아래 피드백을 반영하여 재작성하세요]",
        ]
        for feedback in quality_feedback:
            feedback_lines.extend(self._retry_feedback_group_lines(feedback))
        return feedback_lines

    @staticmethod
    def _retry_rewrite_instruction_lines() -> list[str]:
        """Return the fixed rewrite instructions appended to retry prompts."""
        return [
            "",
            "[재작성 지침]",
            "1. 위에서 지적된 문제점과 '수정 방법'을 반드시 반영하세요.",
            "2. 글자 수, CTA, 해시태그 등 플랫폼 규칙을 정확히 준수하세요.",
            "3. 기존 초안의 좋은 점은 유지하되, 문제점만 개선하세요.",
            "4. 원문에 없는 숫자나 사실을 날조하지 마세요.",
            "━" * 40,
        ]

    def _retry_prompt_feedback_lines(self, quality_feedback: list[dict[str, Any]]) -> list[str]:
        """Return all feedback and rewrite-instruction lines for a retry prompt."""
        feedback_lines = self._retry_feedback_lines(quality_feedback)
        feedback_lines.extend(self._retry_rewrite_instruction_lines())
        return feedback_lines

    def _build_retry_prompt(
        self,
        original_prompt: str,
        quality_feedback: list[dict[str, Any]],
    ) -> str:
        """품질 게이트 실패 피드백을 기반으로 재생성 프롬프트를 조립합니다.

        Args:
            original_prompt: 원래 사용된 프롬프트.
            quality_feedback: [{platform, issues, score}] 형태의 실패 정보.

        Returns:
            피드백이 포함된 재생성용 프롬프트.
        """
        return original_prompt + "\n".join(self._retry_prompt_feedback_lines(quality_feedback))
