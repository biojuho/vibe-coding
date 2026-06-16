"""fact_checker 전용 단위 테스트 (BTX-FC 시리즈).

기존 test_quality_improvements.py의 TestFactChecker가 커버하지 못하는
엣지케이스를 추가 보강합니다:
  - 복합 한국어 숫자 파싱 (5천만, 1억5천만, 3천5백)
  - _is_common_number 시간/날짜 단위
  - _numbers_match ±1% 경계값 + ZeroDivision guard
  - verify_facts confidence 공식 검증
"""

from __future__ import annotations

import unittest

from pipeline.fact_checker import (
    _extract_numbers,
    _is_common_number,
    _normalize_number,
    _numbers_match,
    verify_facts,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. _normalize_number
# ═══════════════════════════════════════════════════════════════════════════════


class TestNormalizeNumber(unittest.TestCase):
    """_normalize_number 단위 및 복합 패턴 검증."""

    # ── 단순 단위 ────────────────────────────────────────────────────────────

    def test_만(self):
        self.assertEqual(_normalize_number("200만"), 2_000_000.0)

    def test_천(self):
        self.assertEqual(_normalize_number("5천"), 5_000.0)

    def test_억(self):
        self.assertEqual(_normalize_number("1억"), 100_000_000.0)

    def test_조(self):
        self.assertEqual(_normalize_number("1조"), 1_000_000_000_000.0)

    def test_백(self):
        self.assertEqual(_normalize_number("3백"), 300.0)

    # ── 복합 단위 ────────────────────────────────────────────────────────────

    def test_compound_5천만(self):
        """BTX-FC001: 5천만 → 50,000,000 (천 × 만 복합)."""
        self.assertEqual(_normalize_number("5천만"), 50_000_000.0)

    def test_compound_3천5백만(self):
        """BTX-FC002: 3천5백만 → 35,000,000."""
        self.assertEqual(_normalize_number("3천5백만"), 35_000_000.0)

    def test_compound_1억5천만(self):
        """BTX-FC003: 1억5천만 → 150,000,000."""
        self.assertEqual(_normalize_number("1억5천만"), 150_000_000.0)

    def test_compound_3천5백(self):
        """BTX-FC004: 3천5백 → 3,500."""
        self.assertEqual(_normalize_number("3천5백"), 3_500.0)

    def test_compound_2억5천(self):
        """BTX-FC005: 2억5천 → 200,005,000 — 억 → remaining '5천' 처리."""
        result = _normalize_number("2억5천")
        self.assertEqual(result, 200_005_000.0)

    # ── 접미사 제거 ──────────────────────────────────────────────────────────

    def test_suffix_원(self):
        """BTX-FC006: '원' 접미사 제거 후 정규화."""
        self.assertEqual(_normalize_number("5천만원"), 50_000_000.0)

    def test_suffix_명(self):
        self.assertEqual(_normalize_number("200명"), 200.0)

    def test_suffix_percent(self):
        self.assertAlmostEqual(_normalize_number("3.5%"), 3.5)

    def test_suffix_개(self):
        self.assertEqual(_normalize_number("100개"), 100.0)

    # ── 순수 숫자 ────────────────────────────────────────────────────────────

    def test_pure_integer(self):
        self.assertEqual(_normalize_number("1000"), 1_000.0)

    def test_pure_decimal(self):
        self.assertAlmostEqual(_normalize_number("3.5"), 3.5)

    def test_comma_separated(self):
        self.assertEqual(_normalize_number("1,000,000"), 1_000_000.0)

    # ── 엣지케이스 ───────────────────────────────────────────────────────────

    def test_empty_string_returns_none(self):
        """BTX-FC007: 빈 문자열 → None."""
        self.assertIsNone(_normalize_number(""))

    def test_only_suffix_returns_none(self):
        """BTX-FC008: 접미사만 있을 때 cleaned가 비어서 None."""
        self.assertIsNone(_normalize_number("원"))

    def test_zero_kr_unit_returns_none(self):
        """BTX-FC009: '0만' → total=0 → None (0을 의미있는 숫자로 안 취급)."""
        self.assertIsNone(_normalize_number("0만"))

    def test_invalid_string_returns_none(self):
        """BTX-FC010: 숫자 아닌 문자열 → None."""
        self.assertIsNone(_normalize_number("abc"))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. _is_common_number
# ═══════════════════════════════════════════════════════════════════════════════


class TestIsCommonNumber(unittest.TestCase):
    """공통 숫자 필터 검증."""

    # ── 연도 ─────────────────────────────────────────────────────────────────

    def test_year_1900_boundary(self):
        self.assertTrue(_is_common_number("1900"))

    def test_year_2024(self):
        self.assertTrue(_is_common_number("2024"))

    def test_year_2099_boundary(self):
        self.assertTrue(_is_common_number("2099"))

    def test_year_1800_out_of_range(self):
        """1800년대 → 패턴 밖 → False."""
        self.assertFalse(_is_common_number("1800"))

    def test_year_2100_out_of_range(self):
        """2100 → 패턴 밖 → False."""
        self.assertFalse(_is_common_number("2100"))

    # ── 뻔한 숫자 ────────────────────────────────────────────────────────────

    def test_common_1(self):
        self.assertTrue(_is_common_number("1"))

    def test_common_2(self):
        self.assertTrue(_is_common_number("2"))

    def test_common_3(self):
        self.assertTrue(_is_common_number("3"))

    def test_common_10(self):
        self.assertTrue(_is_common_number("10"))

    def test_common_100(self):
        self.assertTrue(_is_common_number("100"))

    def test_non_common_4(self):
        self.assertFalse(_is_common_number("4"))

    def test_non_common_50(self):
        self.assertFalse(_is_common_number("50"))

    def test_non_common_200(self):
        self.assertFalse(_is_common_number("200"))

    # ── 시간 단위 ────────────────────────────────────────────────────────────

    def test_time_시(self):
        """BTX-FC011: '12시' → 공통 (시간)."""
        self.assertTrue(_is_common_number("12시"))

    def test_time_분(self):
        """BTX-FC012: '30분' → 공통."""
        self.assertTrue(_is_common_number("30분"))

    def test_time_초(self):
        self.assertTrue(_is_common_number("59초"))

    # ── 날짜 단위 ────────────────────────────────────────────────────────────

    def test_date_월(self):
        """BTX-FC013: '3월' → 공통 (날짜)."""
        self.assertTrue(_is_common_number("3월"))

    def test_date_일(self):
        """BTX-FC014: '15일' → 공통."""
        self.assertTrue(_is_common_number("15일"))

    # ── 비공통 ───────────────────────────────────────────────────────────────

    def test_non_common_5천만(self):
        """BTX-FC015: '5천만' → 공통 아님."""
        self.assertFalse(_is_common_number("5천만"))

    def test_non_common_1억(self):
        self.assertFalse(_is_common_number("1억"))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. _numbers_match
# ═══════════════════════════════════════════════════════════════════════════════


class TestNumbersMatch(unittest.TestCase):
    """숫자 매칭 로직 — 문자열 / 정규화 / 허용 오차."""

    def test_exact_string_match(self):
        self.assertTrue(_numbers_match("5천만원", "5천만원"))

    def test_substring_containment_source_in_draft(self):
        """BTX-FC021: source가 draft에 포함 → 매치."""
        self.assertTrue(_numbers_match("200", "200명"))

    def test_substring_containment_draft_in_source(self):
        self.assertTrue(_numbers_match("200명", "200"))

    def test_normalized_equal_5000_eq_5천(self):
        """BTX-FC022: 5000 == 5천."""
        self.assertTrue(_numbers_match("5000", "5천"))

    def test_normalized_equal_1억_eq_100000000(self):
        self.assertTrue(_numbers_match("100000000", "1억"))

    def test_compound_match_1억5천만_eq_150000000(self):
        """BTX-FC023: '1억5천만' == '150000000'."""
        self.assertTrue(_numbers_match("1억5천만", "150000000"))

    def test_tolerance_within_1pct(self):
        """BTX-FC024: ±1% 이내 오차 허용 — 5000 vs 5049 (diff/5000 = 0.0098)."""
        self.assertTrue(_numbers_match("5000", "5049"))

    def test_tolerance_exceeds_1pct(self):
        """BTX-FC025: 1% 초과는 매치 안 됨 — 5000 vs 5100 (diff/5000 = 0.02)."""
        self.assertFalse(_numbers_match("5000", "5100"))

    def test_source_zero_no_zerodivision(self):
        """BTX-FC026: source=0 일 때 ZeroDivisionError 없어야 함 (norm_s != 0 guard)."""
        result = _numbers_match("0", "5")
        self.assertFalse(result)

    def test_both_unnormalizable_no_crash(self):
        """BTX-FC027: 두 값 모두 정규화 불가 → False, 크래시 없음."""
        self.assertFalse(_numbers_match("abc만", "def천"))

    def test_clearly_different(self):
        self.assertFalse(_numbers_match("5천만", "3천만"))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. _extract_numbers
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractNumbers(unittest.TestCase):
    """숫자 추출 패턴 검증."""

    def test_extracts_compound_천만원(self):
        """BTX-FC-EXT001: 복합 단위 '5천만원' 전체가 한 토큰으로 추출돼야 함 (과거엔 '5천'만 추출)."""
        nums = _extract_numbers("연봉 5천만원이다.")
        self.assertIn("5천만원", nums)

    def test_extracts_명(self):
        nums = _extract_numbers("직원 200명이 대상이다.")
        self.assertIn("200명", nums)

    def test_extracts_percent(self):
        nums = _extract_numbers("상위 3.5%에 해당한다.")
        self.assertIn("3.5%", nums)

    def test_deduplicates_same_token(self):
        """BTX-FC031: 동일 표현은 한 번만 포함."""
        nums = _extract_numbers("200명 중 200명이 동의했다.")
        self.assertEqual(nums.count("200명"), 1)

    def test_no_numbers_returns_empty(self):
        self.assertEqual(_extract_numbers("숫자 없는 텍스트."), [])

    def test_multiple_different_numbers(self):
        nums = _extract_numbers("연봉 5천만원, 직원 200명, 상위 30%")
        self.assertGreaterEqual(len(nums), 3)

    def test_pure_number_extracted(self):
        nums = _extract_numbers("10000명이 참여했다.")
        # "10000명" or "10000" should appear
        self.assertTrue(any("10000" in n for n in nums))


# ═══════════════════════════════════════════════════════════════════════════════
# 5. verify_facts — 종단간 검증
# ═══════════════════════════════════════════════════════════════════════════════


class TestVerifyFacts(unittest.TestCase):
    """verify_facts 엔드투엔드 시나리오."""

    def test_all_match_returns_passed_and_full_confidence(self):
        """BTX-FC041: 모든 숫자 매치 → passed=True, confidence=1.0."""
        result = verify_facts("연봉 5천만원, 직원 200명", "연봉 5천만원, 200명 대상")
        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.confidence, 1.0)

    def test_fabricated_number_sets_passed_false(self):
        """BTX-FC042: 원문에 없는 숫자 → passed=False."""
        result = verify_facts("연봉 5천만원이다.", "연봉 5천만원, 세후 350만원")
        self.assertFalse(result.passed)
        self.assertGreater(len(result.fabricated_items), 0)

    def test_confidence_formula_verified(self):
        """BTX-FC043: confidence = 1 - fabricated/total_draft 공식 검증."""
        source = "연봉 5천만원"
        draft = "연봉 5천만원이면 세후 350만원, 상위 30%에 해당"
        result = verify_facts(source, draft)
        expected = 1.0 - len(result.fabricated_items) / max(len(result.draft_numbers), 1)
        self.assertAlmostEqual(result.confidence, expected, places=5)

    def test_year_with_suffix_not_fabricated(self):
        """BTX-FC044: '2024년'은 연도 패턴으로 공통 숫자 인식 (과거엔 년 접미사 때문에 False)."""
        result = verify_facts("연봉 이야기", "2024년 기준 이야기")
        # 2024년 → _is_common_number 통과 → fabricated 없어야 함
        self.assertTrue(result.passed)
        self.assertEqual(result.fabricated_items, [])

    def test_empty_draft_always_passes(self):
        """BTX-FC045: 초안에 숫자 없음 → 즉시 passed=True."""
        result = verify_facts("연봉 5천만원이다.", "연봉이 꽤 높은 편이라고 한다")
        self.assertTrue(result.passed)
        self.assertEqual(result.fabricated_items, [])

    def test_source_numbers_populated(self):
        """BTX-FC046: source_numbers에 원문 숫자가 담겨야 함 (복합 단위 포함)."""
        result = verify_facts("연봉 5천만원, 직원 200명", "이야기")
        # 복합 단위 '5천만원' 전체가 한 토큰으로 추출돼야 함
        self.assertTrue(
            any("5천만원" in n or "5천만" in n for n in result.source_numbers),
            f"source_numbers={result.source_numbers} should contain '5천만원' or '5천만'",
        )
        self.assertIn("200명", result.source_numbers)

    def test_tolerance_allows_format_difference(self):
        """BTX-FC047: 5000 표기 vs 5천 표기 — 같은 값으로 매치."""
        result = verify_facts("연봉 5000만원", "연봉 5천만원")
        self.assertTrue(result.passed)

    def test_empty_source_causes_all_draft_numbers_fabricated(self):
        """BTX-FC048: 원문이 비어 있으면 초안 숫자는 전부 날조로 처리."""
        result = verify_facts("", "연봉 5천만원, 직원 200명")
        self.assertFalse(result.passed)
        # 공통 숫자가 아닌 항목은 모두 fabricated
        self.assertGreater(len(result.fabricated_items), 0)


if __name__ == "__main__":
    unittest.main()
