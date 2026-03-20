"""팩트 검증 게이트 (Fact Checker).

초안에 포함된 숫자/수치가 원문에 실제로 존재하는지 결정론적으로 검증합니다.
LLM 호출 없이 순수 Python으로 동작하므로 비용이 $0입니다.

사용법:
    from pipeline.fact_checker import verify_facts
    result = verify_facts(source_content, draft_text)
    if not result.passed:
        print(f"잠재 날조 항목: {result.fabricated_items}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── 한국어 숫자 단위 변환 맵 ──────────────────────────────────────────
_KR_UNIT_MAP: dict[str, int] = {
    "만": 10_000,
    "천": 1_000,
    "백": 100,
    "억": 100_000_000,
    "조": 1_000_000_000_000,
}

# ── 무시할 공통 숫자 패턴 (연도, 뻔한 숫자) ───────────────────────────
_COMMON_NUMBER_PATTERNS = re.compile(
    r"^(19|20)\d{2}$"          # 연도 (1900~2099)
    r"|^(1|2|3|10|100)$"       # 흔한 숫자
    r"|^\d{1,2}(시|분|초)$"    # 시간
    r"|^\d{1,2}(월|일)$"       # 날짜
)


@dataclass
class FactCheckResult:
    """팩트 검증 결과."""

    passed: bool = True
    fabricated_items: list[str] = field(default_factory=list)
    source_numbers: list[str] = field(default_factory=list)
    draft_numbers: list[str] = field(default_factory=list)
    confidence: float = 1.0


def _extract_numbers(text: str) -> list[str]:
    """텍스트에서 숫자/수치 표현을 추출합니다.

    Examples:
        "연봉 5천만원" → ["5천만원"]
        "3.5%" → ["3.5%"]
        "200명" → ["200명"]
    """
    # 한국어 단위 포함 숫자
    pattern = r"\d[\d,.]*\d?[만천백억조원%명개월년일시위등배호차건]?"
    matches = re.findall(pattern, text)
    # 중복 제거 + 정렬
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        m = m.strip().rstrip(".")
        if m and m not in seen:
            seen.add(m)
            result.append(m)
    return result


def _normalize_number(num_str: str) -> float | None:
    """한국어 숫자 표현을 float로 정규화. 실패 시 None.

    Examples:
        "5천" → 5000.0
        "3.5%" → 3.5
        "200만원" → 2000000.0
        "1억5천" → 150000000.0
        "5천만원" → 50000000.0
    """
    # 단위 접미사 제거
    cleaned = re.sub(r"[원%명개월년일시위등배호차건]$", "", num_str)
    if not cleaned:
        return None

    # 한국어 단위가 하나도 없으면 순수 숫자
    has_kr_unit = any(u in cleaned for u in _KR_UNIT_MAP)
    if not has_kr_unit:
        try:
            return float(cleaned.replace(",", ""))
        except ValueError:
            return None

    # "5천만", "1억5천", "3천5백" 같은 복합 패턴 처리
    # 큰 단위부터 순서대로 파싱: 조 > 억 > 만 > 천 > 백
    total = 0.0
    remaining = cleaned

    for unit_str, unit_val in sorted(_KR_UNIT_MAP.items(), key=lambda x: -x[1]):
        if unit_str not in remaining:
            continue
        parts = remaining.split(unit_str, 1)
        left = parts[0].replace(",", "").strip()
        # 좌측에 하위 단위가 포함된 경우 재귀 처리 (e.g., "5천" in "5천만")
        if left:
            sub_has_unit = any(u in left for u in _KR_UNIT_MAP)
            if sub_has_unit:
                sub_val = _normalize_number(left)
                coeff = sub_val if sub_val is not None else 1.0
            else:
                try:
                    coeff = float(left)
                except ValueError:
                    coeff = 1.0
        else:
            coeff = 1.0
        total += coeff * unit_val
        remaining = parts[1] if len(parts) > 1 else ""

    # 남은 숫자 처리
    if remaining:
        remaining = remaining.replace(",", "").strip()
        if remaining:
            try:
                total += float(remaining)
            except ValueError:
                pass

    return total if total > 0 else None


def _is_common_number(num_str: str) -> bool:
    """무시해도 되는 공통 숫자인지 판단."""
    cleaned = re.sub(r"[,.]", "", num_str)
    return bool(_COMMON_NUMBER_PATTERNS.match(cleaned))


def _numbers_match(source_num: str, draft_num: str) -> bool:
    """두 숫자 표현이 같은 값을 나타내는지 비교.

    문자열 완전 일치 또는 정규화된 수치 비교.
    """
    # 1. 문자열 완전 일치
    if source_num == draft_num:
        return True

    # 2. 한쪽이 다른 쪽에 포함
    if source_num in draft_num or draft_num in source_num:
        return True

    # 3. 정규화 비교 (5천 == 5000)
    norm_s = _normalize_number(source_num)
    norm_d = _normalize_number(draft_num)
    if norm_s is not None and norm_d is not None:
        # 같은 값이거나 ±1% 오차 허용
        if norm_s == norm_d:
            return True
        if norm_s != 0 and abs(norm_s - norm_d) / abs(norm_s) < 0.01:
            return True

    return False


def verify_facts(source_content: str, draft_text: str) -> FactCheckResult:
    """원문 대비 초안의 숫자/수치 사실 검증.

    Args:
        source_content: 원문 텍스트.
        draft_text: 생성된 초안 텍스트.

    Returns:
        FactCheckResult: 검증 결과 (passed, fabricated_items 등).
    """
    source_numbers = _extract_numbers(source_content)
    draft_numbers = _extract_numbers(draft_text)

    if not draft_numbers:
        return FactCheckResult(
            passed=True,
            source_numbers=source_numbers,
            draft_numbers=draft_numbers,
        )

    fabricated: list[str] = []
    for d_num in draft_numbers:
        # 공통 숫자 무시
        if _is_common_number(d_num):
            continue
        # 원문에서 매칭되는 숫자 찾기
        matched = any(_numbers_match(s_num, d_num) for s_num in source_numbers)
        if not matched:
            fabricated.append(d_num)

    confidence = 1.0 - len(fabricated) / max(len(draft_numbers), 1)

    return FactCheckResult(
        passed=len(fabricated) == 0,
        fabricated_items=fabricated,
        source_numbers=source_numbers,
        draft_numbers=draft_numbers,
        confidence=confidence,
    )
