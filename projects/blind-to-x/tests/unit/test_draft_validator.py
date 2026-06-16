"""draft_validator 전용 단위 테스트 (BTX-DV 시리즈).

validate_and_fix_drafts / _build_retry_prompt 검증.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ── 도우미 ─────────────────────────────────────────────────────────────────────


def _run(coro):
    """코루틴 동기 실행 (Python 3.11+)."""
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. _build_retry_prompt — 순수 문자열 함수
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuildRetryPrompt(unittest.TestCase):
    def setUp(self):
        from pipeline.draft_validator import _build_retry_prompt

        self._build = _build_retry_prompt

    def test_contains_original_draft(self):
        """BTX-DV001: 재시도 프롬프트에 원본 초안이 포함돼야 함."""
        prompt = self._build("내 초안 텍스트", ["너무 짧음"], "threads", {"title": "제목", "content": "내용"})
        self.assertIn("내 초안 텍스트", prompt)

    def test_contains_fix_instructions(self):
        """BTX-DV002: 수정 지시가 프롬프트에 포함돼야 함."""
        instructions = ["너무 짧습니다. 분량을 늘려주세요.", "클리셰를 제거하세요."]
        prompt = self._build("초안", instructions, "threads", {})
        for inst in instructions:
            self.assertIn(inst, prompt)

    def test_contains_platform(self):
        """BTX-DV003: 플랫폼명이 프롬프트에 포함돼야 함."""
        prompt = self._build("초안", ["지시"], "naver_blog", {})
        self.assertIn("naver_blog", prompt)

    def test_contains_post_title(self):
        """BTX-DV004: post_data의 title이 포함돼야 함."""
        prompt = self._build("초안", ["지시"], "threads", {"title": "팀장 갑질 사연", "content": "내용"})
        self.assertIn("팀장 갑질 사연", prompt)

    def test_content_truncated_to_500(self):
        """BTX-DV005: content는 500자로 잘려야 함."""
        long_content = "가" * 1000
        prompt = self._build("초안", ["지시"], "threads", {"title": "T", "content": long_content})
        # 500자 초과 내용은 포함되지 않아야 함
        self.assertNotIn("가" * 501, prompt)
        self.assertIn("가" * 500, prompt)

    def test_empty_instructions_list(self):
        """BTX-DV006: instructions 빈 리스트도 크래시 없이 처리."""
        prompt = self._build("초안", [], "threads", {})
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)

    def test_missing_post_data_keys_no_crash(self):
        """BTX-DV007: post_data에 title/content 없어도 크래시 없음."""
        prompt = self._build("초안", ["지시"], "threads", {})
        self.assertIsInstance(prompt, str)

    def test_multiple_instructions_formatted_as_bullets(self):
        """BTX-DV008: 여러 지시는 '- ' 형식으로 포함돼야 함."""
        prompt = self._build("초안", ["지시1", "지시2"], "threads", {})
        self.assertIn("- 지시1", prompt)
        self.assertIn("- 지시2", prompt)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. validate_and_fix_drafts — 비동기 메인 로직
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidateAndFixDrafts(unittest.TestCase):
    """validate_and_fix_drafts 시나리오 테스트."""

    def _make_gate_result(self, passed: bool, score: float = 80.0, failures: list | None = None):
        result = MagicMock()
        result.passed = passed
        result.score = score
        result.failures = failures or []
        result.warnings = []
        return result

    def test_passing_drafts_returned_unchanged(self):
        """BTX-DV010: 품질 게이트 통과 초안은 변경 없이 반환."""
        drafts = {"threads": "좋은 초안 텍스트입니다"}
        post_data = {"content": "원문 내용"}

        gate_result = self._make_gate_result(passed=True, score=90.0)

        with patch("pipeline.quality_gate.QualityGate") as MockGate:
            MockGate.return_value.check.return_value = gate_result
            result = _run(
                __import__("pipeline.draft_validator", fromlist=["validate_and_fix_drafts"]).validate_and_fix_drafts(
                    drafts, post_data
                )
            )

        self.assertEqual(result["threads"], "좋은 초안 텍스트입니다")

    def test_quality_gate_result_stored_in_post_data(self):
        """BTX-DV011: 검증 결과가 post_data['quality_gate']에 저장됨."""
        drafts = {"threads": "초안"}
        post_data = {"content": "내용"}

        gate_result = self._make_gate_result(passed=True, score=85.0)

        with patch("pipeline.quality_gate.QualityGate") as MockGate:
            MockGate.return_value.check.return_value = gate_result
            _run(
                __import__("pipeline.draft_validator", fromlist=["validate_and_fix_drafts"]).validate_and_fix_drafts(
                    drafts, post_data
                )
            )

        self.assertIn("quality_gate", post_data)
        self.assertIn("threads", post_data["quality_gate"])
        self.assertTrue(post_data["quality_gate"]["threads"]["passed"])

    def test_failed_draft_without_generator_not_retried(self):
        """BTX-DV012: generator=None이면 실패해도 재시도 없이 원본 반환."""
        drafts = {"threads": "짧은 초안"}
        post_data = {"content": "내용"}

        gate_result = self._make_gate_result(passed=False, score=40.0, failures=["too_short"])

        with patch("pipeline.quality_gate.QualityGate") as MockGate:
            MockGate.return_value.check.return_value = gate_result
            result = _run(
                __import__("pipeline.draft_validator", fromlist=["validate_and_fix_drafts"]).validate_and_fix_drafts(
                    drafts, post_data, generator=None
                )
            )

        # 원본 초안 그대로 반환 (재시도 없음)
        self.assertEqual(result["threads"], "짧은 초안")

    def test_failed_draft_with_generator_retried_and_improved(self):
        """BTX-DV013: generator 있고 재시도가 개선되면 개선된 초안 반환."""
        drafts = {"threads": "짧은 초안"}
        post_data = {"content": "내용"}

        initial_gate = self._make_gate_result(passed=False, score=40.0, failures=["too_short"])
        improved_gate = self._make_gate_result(passed=True, score=85.0)

        mock_generator = MagicMock()
        mock_generator._call_llm_with_fallback = AsyncMock(return_value="개선된 긴 초안 텍스트입니다")

        with patch("pipeline.quality_gate.QualityGate") as MockGate:
            MockGate.return_value.check.side_effect = [initial_gate, improved_gate]
            result = _run(
                __import__("pipeline.draft_validator", fromlist=["validate_and_fix_drafts"]).validate_and_fix_drafts(
                    drafts, post_data, generator=mock_generator
                )
            )

        self.assertEqual(result["threads"], "개선된 긴 초안 텍스트입니다")

    def test_failed_draft_retry_not_improved_keeps_original(self):
        """BTX-DV014: 재시도해도 점수가 낮으면 원본 유지."""
        drafts = {"threads": "원본 초안"}
        post_data = {"content": "내용"}

        initial_gate = self._make_gate_result(passed=False, score=40.0, failures=["too_short"])
        worse_gate = self._make_gate_result(passed=False, score=30.0)

        mock_generator = MagicMock()
        mock_generator._call_llm_with_fallback = AsyncMock(return_value="더 나쁜 초안")

        with patch("pipeline.quality_gate.QualityGate") as MockGate:
            MockGate.return_value.check.side_effect = [initial_gate, worse_gate]
            result = _run(
                __import__("pipeline.draft_validator", fromlist=["validate_and_fix_drafts"]).validate_and_fix_drafts(
                    drafts, post_data, generator=mock_generator
                )
            )

        # 재시도 결과가 나빠서 원본 유지
        self.assertEqual(result["threads"], "원본 초안")

    def test_retry_exception_keeps_original_no_crash(self):
        """BTX-DV015: 재시도 중 예외 발생 시 크래시 없이 원본 유지."""
        drafts = {"threads": "원본 초안"}
        post_data = {"content": "내용"}

        gate_fail = self._make_gate_result(passed=False, score=40.0, failures=["too_short"])

        mock_generator = MagicMock()
        mock_generator._call_llm_with_fallback = AsyncMock(side_effect=RuntimeError("LLM down"))

        with patch("pipeline.quality_gate.QualityGate") as MockGate:
            MockGate.return_value.check.return_value = gate_fail
            result = _run(
                __import__("pipeline.draft_validator", fromlist=["validate_and_fix_drafts"]).validate_and_fix_drafts(
                    drafts, post_data, generator=mock_generator
                )
            )

        self.assertEqual(result["threads"], "원본 초안")

    def test_multiple_platforms_all_validated(self):
        """BTX-DV016: 여러 플랫폼 초안이 모두 검증됨."""
        drafts = {"threads": "스레드 초안", "naver_blog": "블로그 초안"}
        post_data = {"content": "내용"}

        gate_pass = self._make_gate_result(passed=True, score=80.0)

        with patch("pipeline.quality_gate.QualityGate") as MockGate:
            MockGate.return_value.check.return_value = gate_pass
            _run(
                __import__("pipeline.draft_validator", fromlist=["validate_and_fix_drafts"]).validate_and_fix_drafts(
                    drafts, post_data
                )
            )

        self.assertEqual(MockGate.return_value.check.call_count, 2)

    def test_unknown_failure_code_no_fix_instruction(self):
        """BTX-DV017: 매핑 없는 failure code는 fix instruction 없어 재시도 스킵."""
        drafts = {"threads": "초안"}
        post_data = {"content": "내용"}

        gate_fail = self._make_gate_result(passed=False, score=40.0, failures=["unknown_code"])
        mock_generator = MagicMock()
        mock_generator._call_llm_with_fallback = AsyncMock(return_value="새 초안")

        with patch("pipeline.quality_gate.QualityGate") as MockGate:
            MockGate.return_value.check.return_value = gate_fail
            result = _run(
                __import__("pipeline.draft_validator", fromlist=["validate_and_fix_drafts"]).validate_and_fix_drafts(
                    drafts, post_data, generator=mock_generator
                )
            )

        # fix_instructions 없어서 LLM 안 호출 → 원본 그대로
        mock_generator._call_llm_with_fallback.assert_not_called()
        self.assertEqual(result["threads"], "초안")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. _FIX_INSTRUCTIONS 매핑 완전성 검증
# ═══════════════════════════════════════════════════════════════════════════════


class TestFixInstructionsMapping(unittest.TestCase):
    def test_all_known_failure_codes_have_instructions(self):
        """BTX-DV020: 알려진 품질 게이트 failure code는 모두 매핑돼야 함."""
        from pipeline.draft_validator import _FIX_INSTRUCTIONS

        expected_codes = {
            "too_short",
            "too_long",
            "cliche_overuse",
            "forbidden_expression",
            "repetition",
            "toxic_or_pii",
            "potential_fabrication",
        }
        for code in expected_codes:
            self.assertIn(code, _FIX_INSTRUCTIONS, f"'{code}'에 fix instruction 없음")
            self.assertGreater(len(_FIX_INSTRUCTIONS[code]), 0, f"'{code}' fix instruction이 빈 문자열")

    def test_all_instructions_are_nonempty_strings(self):
        """BTX-DV021: 모든 지시문이 비어있지 않은 문자열."""
        from pipeline.draft_validator import _FIX_INSTRUCTIONS

        for code, instruction in _FIX_INSTRUCTIONS.items():
            self.assertIsInstance(instruction, str, f"'{code}' instruction이 str이 아님")
            self.assertGreater(len(instruction.strip()), 0, f"'{code}' instruction이 비어 있음")


if __name__ == "__main__":
    unittest.main()
