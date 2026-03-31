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
        if source_content:
            self._check_source_fidelity(draft_text, source_content, result)

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
