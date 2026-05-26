"""다축 품질 게이트 — 초안의 발행 적합성을 다차원으로 검증.

DeepEval/Guardrails의 핵심 개념을 Gemini Flash(무료)로 경량 구현.
LLM 호출 없이 결정론적으로 검사하는 "하드 게이트"와,
선택적 LLM 기반 "소프트 게이트"로 구성됩니다.

사용법:
    from pipeline.quality_gate import QualityGate
    gate = QualityGate()
    result = gate.check(draft_text, source_content, platform="twitter")
    if not result.passed:
        print(result.failures)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from pipeline.rules_loader import get_rule_section, load_rules

logger = logging.getLogger(__name__)

# ── 하드 게이트 기본값 ───────────────────────────────────────────────
_PLATFORM_LIMITS = {
    "twitter": {"min_len": 20, "max_len": 280},
    "twitter_thread": {"min_len": 50, "max_len": 2000},
    "newsletter": {"min_len": 100, "max_len": 5000},
    "default": {"min_len": 20, "max_len": 3000},
}

# 절대 통과 불가 패턴 (toxic, 개인정보 등)
_TOXIC_PATTERNS = [
    re.compile(r"\b(씨발|좆|병신|지랄)\b"),
    re.compile(r"(?<!\d)0\d{1,2}-\d{3,4}-\d{4}(?!\d)"),  # 전화번호 (0으로 시작: 010, 02 등)
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # 이메일
]


@dataclass
class GateResult:
    """품질 게이트 검증 결과."""

    passed: bool = True
    score: float = 100.0
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


_rules_cache: dict | None = None


def _load_rules_once() -> dict:
    """Load merged rule sections with a module cache."""
    global _rules_cache
    if _rules_cache is not None:
        return _rules_cache
    _rules_cache = load_rules()
    return _rules_cache


def _load_cliches() -> list[str]:
    """Load the cliche watchlist."""
    return list(get_rule_section("cliche_watchlist", []))


def _load_forbidden() -> list[str]:
    """Load forbidden expressions from brand voice."""
    brand_voice = get_rule_section("brand_voice", {})
    return list(brand_voice.get("forbidden_expressions", []))


class QualityGate:
    """다축 품질 게이트.

    하드 게이트 (결정론적, 비용 $0):
    - 길이 제한 (플랫폼별)
    - 독성/개인정보 필터
    - 클리셰/금지 표현 감지
    - 원문 충실도 (핵심 숫자 보존)
    - 반복 감지 (동일 문장/구)

    소프트 게이트 (LLM, 선택적):
    - 브랜드 보이스 일치도
    - 논리적 일관성
    """

    def __init__(self):
        self._cliches = _load_cliches()
        self._forbidden = _load_forbidden()

    def check(
        self,
        draft_text: str,
        source_content: str = "",
        platform: str = "default",
        post_data: dict[str, Any] | None = None,
    ) -> GateResult:
        """초안에 대해 모든 하드 게이트를 실행합니다."""
        result = GateResult()

        if not draft_text or not draft_text.strip():
            result.passed = False
            result.score = 0.0
            result.failures.append("empty_draft")
            return result

        # 개별 게이트 실행
        self._check_length(draft_text, platform, result)
        self._check_toxic(draft_text, result)
        self._check_cliches(draft_text, result)
        self._check_forbidden(draft_text, result)
        self._check_repetition(draft_text, result)
        self._check_bland_creator_take(draft_text, result)
        self._check_semantic_similarity(draft_text, platform, result)
        if source_content:
            self._check_source_fidelity(draft_text, source_content, result)
            self._check_originality(draft_text, source_content, result)

        # 종합 점수 산출 (failures: -20점, warnings: -5점)
        penalty = len(result.failures) * 20 + len(result.warnings) * 5
        result.score = max(0.0, 100.0 - penalty)
        result.passed = len(result.failures) == 0

        return result

    def _check_length(self, text: str, platform: str, result: GateResult) -> None:
        """플랫폼별 길이 제한 검사."""
        limits = _PLATFORM_LIMITS.get(platform, _PLATFORM_LIMITS["default"])
        text_len = len(text)
        result.metrics["text_length"] = float(text_len)

        if text_len < limits["min_len"]:
            result.failures.append(f"too_short: {text_len}자 < 최소 {limits['min_len']}자 ({platform})")
        elif text_len > limits["max_len"]:
            result.failures.append(f"too_long: {text_len}자 > 최대 {limits['max_len']}자 ({platform})")

    def _check_toxic(self, text: str, result: GateResult) -> None:
        """독성/개인정보 필터."""
        for pattern in _TOXIC_PATTERNS:
            match = pattern.search(text)
            if match:
                result.failures.append(f"toxic_or_pii: '{match.group()[:10]}...'")
                return

    def _check_cliches(self, text: str, result: GateResult) -> None:
        """클리셰 사용 감지."""
        found = [c for c in self._cliches if c in text]
        if found:
            result.metrics["cliche_count"] = float(len(found))
            if len(found) >= 3:
                result.failures.append(f"cliche_overuse: {len(found)}개 ({', '.join(found[:3])})")
            else:
                result.warnings.append(f"cliche_detected: {', '.join(found)}")

    def _check_forbidden(self, text: str, result: GateResult) -> None:
        """금지 표현 사용 감지."""
        found = [f for f in self._forbidden if f in text]
        if found:
            result.failures.append(f"forbidden_expression: {', '.join(found[:3])}")

    def _check_repetition(self, text: str, result: GateResult) -> None:
        """반복 문장/구 감지."""
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if len(s.strip()) > 5]
        if len(sentences) < 2:
            return

        seen: set[str] = set()
        duplicates = 0
        for s in sentences:
            normalized = re.sub(r"\s+", "", s)
            if normalized in seen:
                duplicates += 1
            seen.add(normalized)

        if duplicates > 0:
            result.metrics["repeated_sentences"] = float(duplicates)
            if duplicates >= 2:
                result.failures.append(f"repetition: {duplicates}개 문장 반복")
            else:
                result.warnings.append("minor_repetition: 1개 문장 반복")

    def _check_source_fidelity(self, draft: str, source: str, result: GateResult) -> None:
        """원문 핵심 숫자가 초안에 보존되었는지 검사."""
        from pipeline.fact_checker import verify_facts

        fc = verify_facts(source, draft)
        result.metrics["fact_confidence"] = fc.confidence
        if not fc.passed and len(fc.fabricated_items) >= 2:
            result.warnings.append(
                f"potential_fabrication: {len(fc.fabricated_items)}개 수치 미검증 ({', '.join(fc.fabricated_items[:3])})"
            )

    def _check_originality(
        self,
        draft: str,
        source: str,
        result: GateResult,
        min_run: int = 12,
        warn_threshold: int = 2,
        fail_threshold: int = 4,
    ) -> None:
        """원문 베끼기 (paraphrase 부족) 감지.

        원문과 ``min_run`` 자 이상 연속 일치하는 chunk 수를 센다. 인용("...")
        구간은 제외 — 인용은 원문 표현 그대로 가져오는 게 올바른 사용법이다.
        ``warn_threshold`` 이상이면 warning, ``fail_threshold`` 이상이면 failure.

        결정론적·LLM 호출 없음. 한국어 공백 무시 슬라이딩 윈도우.
        """
        if not draft or not source:
            return
        # 인용부 제거 (큰따옴표, 작은따옴표, 한국어 인용부호)
        quote_stripped = re.sub(
            r"""[\"'“”‘’「」『』][^\"'“”‘’「」『』]+["""
            r"""\"'“”‘’「」『』]""",
            "",
            draft,
        )
        # 공백을 무시한 정규화 (출처 표기/줄바꿈 차이 보정)
        norm_draft = re.sub(r"\s+", "", quote_stripped)
        norm_source = re.sub(r"\s+", "", source)
        if len(norm_draft) < min_run or len(norm_source) < min_run:
            return

        # 슬라이딩 윈도우로 일치 시작점들을 모은 뒤, 인접 매치들을 한 chunk 로 병합
        matches: list[tuple[int, int]] = []  # (draft_pos, length)
        i = 0
        while i <= len(norm_draft) - min_run:
            window = norm_draft[i : i + min_run]
            if window in norm_source:
                # 가능한 한 길게 확장
                length = min_run
                while i + length < len(norm_draft) and norm_draft[i : i + length + 1] in norm_source:
                    length += 1
                matches.append((i, length))
                i += length  # 겹치지 않게 점프
            else:
                i += 1

        hit_count = len(matches)
        if hit_count == 0:
            return
        result.metrics["copy_chunks"] = float(hit_count)
        result.metrics["copy_chars"] = float(sum(length for _, length in matches))
        if hit_count >= fail_threshold:
            sample = [norm_draft[pos : pos + length] for pos, length in matches[:3]]
            result.failures.append(
                f"copy_overlap: 원문과 연속 {min_run}자 이상 일치 {hit_count}곳 "
                f"(예: {', '.join(repr(s) for s in sample)})"
            )
        elif hit_count >= warn_threshold:
            result.warnings.append(
                f"copy_overlap_partial: 원문과 연속 {min_run}자 이상 일치 {hit_count}곳 — paraphrase 보완 권장"
            )

    def _check_bland_creator_take(self, text: str, result: GateResult) -> None:
        """LLM 응답이 generic/bland한 'creator take'인지 감지하는 결정론적 heuristic.

        숫자가 전혀 없고 뻔한 상투적 소셜 표현이 발견되는 경우 실패(failures) 또는 경고(warnings) 처리합니다.
        """
        # 숫자나 구체성 지표 존재 여부 확인
        has_digits = bool(re.search(r"\d+", text))

        # 뻔한 buzzwords 감지
        bland_buzzwords = [
            "정말 중요",
            "꼭 기억",
            "핵심은",
            "엄청난",
            "놀라운",
            "대단한",
            "흥미로운",
            "다들 어떻게",
            "생각해보면",
            "도움이 되셨",
            "알아보겠",
            "아주 유익",
            "유용한 정보",
        ]
        found_buzzwords = [w for w in bland_buzzwords if w in text]

        result.metrics["bland_buzzword_count"] = float(len(found_buzzwords))
        result.metrics["has_digits"] = 1.0 if has_digits else 0.0

        # 숫자가 아예 없고 뻔한 단어가 2개 이상 포함된 경우 실패
        if not has_digits and len(found_buzzwords) >= 2:
            result.failures.append(
                f"bland_creator_take: 구체적 수치(숫자) 없음 & 상투적 표현 {len(found_buzzwords)}개 감지 "
                f"({', '.join(found_buzzwords[:3])})"
            )
        elif len(found_buzzwords) >= 3:
            result.warnings.append(
                f"bland_creator_take_warning: 상투적 표현 다수 감지 ({', '.join(found_buzzwords[:3])})"
            )

    def _check_semantic_similarity(self, text: str, platform: str, result: GateResult) -> None:
        """최근 N개 캡션과의 Jaccard 3-gram 유사도 비교. 임계값(0.85) 초과 시 warning/error."""
        if not text:
            return

        # 인라인 임포트로 순환 참조 방지
        try:
            from pipeline.draft_cache import DraftCache

            cache = DraftCache()
            recent_drafts = cache.get_recent_drafts(5)
        except Exception as exc:
            logger.debug("Failed to load DraftCache in _check_semantic_similarity: %s", exc)
            return

        if not recent_drafts:
            return

        # 3-gram 집합 생성 헬퍼
        def get_3grams(t: str) -> set[str]:
            normalized = re.sub(r"\s+", "", t).lower()
            if len(normalized) < 3:
                return {normalized} if normalized else set()
            return {normalized[i : i + 3] for i in range(len(normalized) - 2)}

        # Jaccard 유사도 계산
        def jaccard_similarity(t1: str, t2: str) -> float:
            s1 = get_3grams(t1)
            s2 = get_3grams(t2)
            if not s1 or not s2:
                return 0.0
            return len(s1.intersection(s2)) / len(s1.union(s2))

        max_sim = 0.0
        similar_text = ""

        for past_dict in recent_drafts:
            # 해당 플랫폼의 과거 캡션 추출
            past_text = past_dict.get(platform, "")
            if not past_text:
                continue

            sim = jaccard_similarity(text, past_text)
            if sim > max_sim:
                max_sim = sim
                similar_text = past_text

        result.metrics["max_semantic_similarity"] = max_sim

        if max_sim >= 0.85:
            result.failures.append(
                f"semantic_similarity_limit: 최근 초안과 너무 높은 유사도({max_sim:.2f} >= 0.85) "
                f"구간: '{similar_text[:20]}...'"
            )
        elif max_sim >= 0.70:
            result.warnings.append(
                f"semantic_similarity_warning: 최근 초안과 유사함({max_sim:.2f} >= 0.70) 구간: '{similar_text[:20]}...'"
            )
