"""
단위 테스트: reasoning_chain.py (ReasoningChain)
+ confidence_verifier.py (ConfidenceVerifier)
+ thought_decomposer.py (ThoughtDecomposer)

모든 LLM 호출을 mock하여 비용 없이 테스트합니다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.reasoning_chain import ReasoningChain, ReasoningResult
from execution.confidence_verifier import ConfidenceVerifier
from execution.thought_decomposer import ThoughtDecomposer, TaskNode, CompositeResult


# ══════════════════════════════════════════════════════════════
# ReasoningChain 테스트
# ══════════════════════════════════════════════════════════════


@pytest.fixture
def mock_llm():
    """generate_text를 가진 mock LLMClient."""
    llm = MagicMock()
    llm.generate_text.return_value = "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)"
    return llm


@pytest.fixture
def chain(mock_llm):
    return ReasoningChain(mock_llm, n_samples=3)


class TestReasoningChainBasic:
    def test_returns_reasoning_result(self, chain):
        result = chain.reason(
            system_prompt="You are a coder.",
            user_prompt="Write fibonacci in Python.",
        )
        assert isinstance(result, ReasoningResult)
        assert result.answer != ""
        assert result.n_samples_used >= 2
        assert 0.0 <= result.confidence <= 1.0

    def test_consensus_ratio_for_identical_responses(self, chain):
        result = chain.reason(
            system_prompt="test",
            user_prompt="test",
        )
        # 모든 응답이 동일 → 높은 consensus
        assert result.consensus_ratio >= 0.5

    def test_all_responses_stored(self, chain):
        result = chain.reason(
            system_prompt="test",
            user_prompt="test",
        )
        assert len(result.all_responses) >= 2

    def test_reasoning_trace_populated(self, chain):
        result = chain.reason(
            system_prompt="test",
            user_prompt="test",
        )
        assert len(result.reasoning_trace) >= 2


class TestReasoningChainEarlyStop:
    def test_early_stop_reduces_samples(self):
        llm = MagicMock()
        llm.generate_text.return_value = "consistent answer"
        chain = ReasoningChain(llm, n_samples=5, early_stop=True)

        result = chain.reason(
            system_prompt="test",
            user_prompt="test",
        )
        # 일관된 응답 → 5개 미만에서 조기 종료
        assert result.n_samples_used < 5

    def test_no_early_stop_uses_all_samples(self):
        llm = MagicMock()
        llm.generate_text.return_value = "consistent answer"
        chain = ReasoningChain(llm, n_samples=3, early_stop=False)

        result = chain.reason(
            system_prompt="test",
            user_prompt="test",
        )
        assert result.n_samples_used == 3


class TestReasoningChainDivergent:
    def test_divergent_responses_lower_confidence(self):
        call_count = 0

        def divergent_generate(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "def sort(x): return sorted(x)"
            elif call_count == 2:
                return "import heapq; heapq.nlargest(n, items)"
            else:
                return "x.sort(); return x"

        llm = MagicMock()
        llm.generate_text.side_effect = divergent_generate

        chain = ReasoningChain(llm, n_samples=3, early_stop=False)
        result = chain.reason(
            system_prompt="test",
            user_prompt="sort this",
        )
        # 발산하는 응답 → 낮은 confidence
        assert result.confidence < 1.0


class TestReasoningChainErrorHandling:
    def test_sample_failure_continues(self):
        call_count = 0

        def failing_generate(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("API error")
            return "valid response"

        llm = MagicMock()
        llm.generate_text.side_effect = failing_generate

        chain = ReasoningChain(llm, n_samples=3, early_stop=False)
        result = chain.reason(
            system_prompt="test",
            user_prompt="test",
        )
        # 1개 실패해도 나머지로 결과 생성
        assert result.answer != ""
        assert "FAILED" in result.reasoning_trace[1]

    def test_all_failures_empty_result(self):
        llm = MagicMock()
        llm.generate_text.side_effect = RuntimeError("always fails")

        chain = ReasoningChain(llm, n_samples=3, early_stop=False)
        result = chain.reason(
            system_prompt="test",
            user_prompt="test",
        )
        assert result.answer == ""
        assert result.confidence == 0.0


class TestReasoningChainVerification:
    def test_verification_passes(self):
        call_count = 0

        def varied_generate(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 첫 번째: 정렬 관련 답변
                return "Use sorted() function with reverse parameter for descending order"
            elif call_count == 2:
                # 두 번째: 완전히 다른 어휘의 답변
                return "Apply quicksort algorithm implementing partition logic recursively"
            # verification 단계
            return "검증 통과: correct answer"

        llm = MagicMock()
        llm.generate_text.side_effect = varied_generate
        chain = ReasoningChain(llm, n_samples=2, early_stop=False)
        result = chain.reason_with_verification(
            system_prompt="test",
            user_prompt="test",
        )
        has_verification = any("Verification" in t for t in result.reasoning_trace)
        assert has_verification


# ══════════════════════════════════════════════════════════════
# ConfidenceVerifier 테스트
# ══════════════════════════════════════════════════════════════


@pytest.fixture
def verifier_llm():
    llm = MagicMock()
    return llm


@pytest.fixture
def verifier(verifier_llm):
    return ConfidenceVerifier(llm_client=verifier_llm, threshold=0.7)


class TestConfidenceVerifierBasic:
    def test_high_confidence_early_return(self, verifier, verifier_llm):
        verifier_llm.generate_text.return_value = "0.95"
        result = verifier.verify(
            question="1+1은?",
            answer="2입니다.",
        )
        assert result.is_reliable is True
        assert result.confidence >= 0.7
        assert result.verification_method == "self_eval"
        assert result.tokens_saved > 0

    def test_low_confidence_triggers_critique(self, verifier, verifier_llm):
        verifier_llm.generate_text.side_effect = [
            "0.3",  # 낮은 confidence
            "반론: 답변이 부정확합니다.\n수정 제안: 수정 불필요\n원래 답변 유지: 예",
        ]
        result = verifier.verify(
            question="테스트 질문",
            answer="테스트 답변",
        )
        assert result.verification_method == "self_critique"

    def test_empty_answer_returns_unreliable(self, verifier):
        result = verifier.verify(
            question="test",
            answer="",
        )
        assert result.is_reliable is False
        assert result.confidence == 0.0
        assert result.verification_method == "skipped"


class TestConfidenceVerifierCritique:
    def test_critique_maintains_answer(self, verifier, verifier_llm):
        verifier_llm.generate_text.side_effect = [
            "0.4",  # 낮은 confidence
            "반론: 특별한 문제 없음\n수정 제안: 수정 불필요\n원래 답변 유지: 예",
        ]
        result = verifier.verify(
            question="질문",
            answer="원래 답변",
        )
        assert result.final_answer == "원래 답변"
        assert result.confidence > 0.4  # 반론 견딤 → 상향

    def test_critique_revises_answer(self, verifier, verifier_llm):
        verifier_llm.generate_text.side_effect = [
            "0.3",
            "반론: 심각한 오류\n수정 제안: 수정된 정확한 답변\n원래 답변 유지: 아니오",
        ]
        result = verifier.verify(
            question="질문",
            answer="잘못된 답변",
        )
        assert result.final_answer == "수정된 정확한 답변"
        assert result.confidence < 0.4

    def test_critique_failure_falls_back(self, verifier, verifier_llm):
        verifier_llm.generate_text.side_effect = [
            "0.4",  # 낮은 confidence
            RuntimeError("API error"),
        ]
        result = verifier.verify(
            question="질문",
            answer="답변",
        )
        assert result.final_answer == "답변"
        assert "실패" in result.counter_argument


class TestConfidenceVerifierParsing:
    def test_parse_float(self, verifier, verifier_llm):
        verifier_llm.generate_text.return_value = "0.85"
        result = verifier.verify(question="q", answer="a")
        assert abs(result.confidence - 0.85) < 0.01

    def test_parse_with_text(self, verifier, verifier_llm):
        verifier_llm.generate_text.return_value = "The confidence is 0.72 out of 1.0"
        result = verifier.verify(question="q", answer="a")
        assert result.confidence >= 0.7

    def test_parse_integer(self, verifier, verifier_llm):
        verifier_llm.generate_text.return_value = "1"
        result = verifier.verify(question="q", answer="a")
        assert result.confidence == 1.0


# ══════════════════════════════════════════════════════════════
# ThoughtDecomposer 테스트
# ══════════════════════════════════════════════════════════════


@pytest.fixture
def decomposer_llm():
    llm = MagicMock()
    return llm


@pytest.fixture
def decomposer(decomposer_llm):
    return ThoughtDecomposer(llm_client=decomposer_llm, max_depth=2)


class TestThoughtDecomposerAtomic:
    def test_short_task_is_atomic(self, decomposer):
        tree = decomposer.decompose("print hello")
        assert len(tree.children) == 0

    def test_simple_verb_is_atomic(self, decomposer):
        tree = decomposer.decompose("import json")
        assert len(tree.children) == 0


class TestThoughtDecomposerDecompose:
    def test_complex_task_decomposes(self, decomposer, decomposer_llm):
        # 서브태스크가 20단어 이상이어야 atomic으로 처리되지 않음
        decomposer_llm.generate_json.return_value = [
            "인증 시스템을 구현하고 JWT 토큰 기반 인가 로직을 작성하여 보안성을 확보하세요 이것은 매우 중요한 서브태스크입니다",
            "데이터베이스 스키마를 설계하고 ORM 모델을 정의하여 마이그레이션을 수행하세요 테이블 간 관계도 정의해야 합니다",
            "에러 처리 미들웨어를 작성하고 로깅 시스템을 구축하여 운영 안정성을 확보하세요 모든 예외를 캐치해야 합니다",
        ]
        task = (
            "Python으로 REST API 서버를 구현하세요. "
            "인증, 데이터베이스, 에러 처리를 포함해야 합니다. "
            "보안 취약점 검사도 수행하세요. "
            "JWT 토큰 기반 인가 로직을 작성하여 보안성을 확보하고, "
            "ORM 모델을 정의하여 마이그레이션도 포함해주세요."
        )
        tree = decomposer.decompose(task)
        assert len(tree.children) >= 2  # 최소 2개 이상 분해됨

    def test_respects_max_depth(self, decomposer_llm):
        decomposer_llm.generate_json.return_value = ["sub1", "sub2"]
        deep_decomposer = ThoughtDecomposer(llm_client=decomposer_llm, max_depth=1)
        tree = deep_decomposer.decompose(
            "Very complex multi-step architecture redesign with "
            "numerous components and deeply nested subtask requirements"
        )
        # 깊이 1에서 분해, 깊이 2부터는 리프 (max_depth=1이면 깊이 0에서 분해)
        max_d = _max_tree_depth(tree)
        assert max_d <= 1


class TestThoughtDecomposerExecute:
    def test_leaf_node_execution(self, decomposer, decomposer_llm):
        decomposer_llm.generate_text.return_value = "실행 결과입니다."
        leaf = TaskNode(task_text="간단한 작업 수행", depth=0)
        decomposer.execute_tree(leaf)
        assert leaf.status == "completed"
        assert leaf.result == "실행 결과입니다."

    def test_parent_synthesizes_children(self, decomposer, decomposer_llm):
        decomposer_llm.generate_text.return_value = "종합 결과"
        parent = TaskNode(
            task_text="부모 작업",
            depth=0,
            children=[
                TaskNode(task_text="자식1", depth=1),
                TaskNode(task_text="자식2", depth=1),
            ],
        )
        decomposer.execute_tree(parent)
        assert parent.status == "completed"
        for child in parent.children:
            assert child.status == "completed"

    def test_execution_failure_marks_failed(self, decomposer, decomposer_llm):
        decomposer_llm.generate_text.side_effect = RuntimeError("API crash")
        leaf = TaskNode(task_text="실패할 작업", depth=0)
        decomposer.execute_tree(leaf)
        assert leaf.status == "failed"


class TestThoughtDecomposerSolve:
    def test_full_pipeline(self, decomposer, decomposer_llm):
        # 분해 → 실행 → 합성
        decomposer_llm.generate_json.return_value = ["단계1", "단계2"]
        decomposer_llm.generate_text.return_value = "완성된 결과"

        result = decomposer.solve(
            "REST API 서버를 구현하세요. 인증과 DB를 포함하세요. "
            "보안 검사도 해주세요. JWT 토큰 기반 인가 로직을 작성하여 "
            "보안성을 확보하고 ORM 모델을 정의하여 마이그레이션을 포함해주세요."
        )
        assert isinstance(result, CompositeResult)
        assert result.final_answer != ""
        assert result.completed_subtasks > 0


# ── 유틸리티 ─────────────────────────────────────────────────


def _max_tree_depth(node: TaskNode) -> int:
    if not node.children:
        return node.depth
    return max(_max_tree_depth(c) for c in node.children)
