"""
단위 테스트: smart_router.py (SmartRouter)

복잡도 분류의 정확성과 프로바이더 선택 로직을 검증합니다.
LLM 호출 없이 결정론적으로 동작하므로 mock 불필요.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.smart_router import SmartRouter, ComplexityLevel


@pytest.fixture
def router():
    return SmartRouter()


# ── 복잡도 분류: SIMPLE ──────────────────────────────────────


class TestClassifySimple:
    def test_hello_world(self, router):
        result = router.classify("print('hello world')")
        assert result.complexity == ComplexityLevel.SIMPLE

    def test_for_loop(self, router):
        result = router.classify("Write a for loop that sums 1 to 10")
        assert result.complexity == ComplexityLevel.SIMPLE

    def test_import_statement(self, router):
        result = router.classify("How to import json in Python?")
        assert result.complexity == ComplexityLevel.SIMPLE

    def test_variable_naming(self, router):
        result = router.classify("변수 이름 변경해줘")
        assert result.complexity == ComplexityLevel.SIMPLE

    def test_crud(self, router):
        result = router.classify("Write a CRUD getter setter")
        assert result.complexity == ComplexityLevel.SIMPLE


# ── 복잡도 분류: MODERATE ────────────────────────────────────


class TestClassifyModerate:
    def test_implement_class(self, router):
        result = router.classify(
            "Implement an async Python class that handles WebSocket connections with retry logic and error handling"
        )
        assert result.complexity in (ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX)

    def test_write_unit_test(self, router):
        result = router.classify(
            "Write a unit test for the validate method in the User class that tests error handling and edge cases"
        )
        assert result.complexity in (ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX)

    def test_refactor_function(self, router):
        result = router.classify("리팩토링: 이 함수의 타입 힌트를 추가하고 데코레이터로 검증 로직을 분리하세요")
        assert result.complexity in (ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX)


# ── 복잡도 분류: COMPLEX ─────────────────────────────────────


class TestClassifyComplex:
    def test_architecture_design(self, router):
        result = router.classify(
            "Design a microservice architecture for our e-commerce platform. "
            "Consider trade-offs between event sourcing and CQRS pattern. "
            "Include security vulnerability assessment and performance optimization."
        )
        assert result.complexity == ComplexityLevel.COMPLEX

    def test_debugging_with_stack_trace(self, router):
        prompt = (
            "Debug this race condition in our system design.\n"
            "```\nTraceback:\n  File 'handler.py', line 42\n```\n"
            "```\nAnother trace\n```\n"
            "What's the root cause of this deadlock?"
        )
        result = router.classify(prompt)
        assert result.complexity == ComplexityLevel.COMPLEX

    def test_multi_file_migration(self, router):
        result = router.classify(
            "마이그레이션: 프로젝트 구조를 변경하여 여러 파일의 "
            "아키텍처를 리팩토링하고 비교 분석해주세요. "
            "장단점과 트레이드오프를 포함해주세요."
        )
        assert result.complexity == ComplexityLevel.COMPLEX

    def test_long_prompt_contributes(self, router):
        # 900+ 토큰 프롬프트
        long_desc = "word " * 900
        result = router.classify(long_desc)
        assert result.score > 0  # 길이가 score에 기여


# ── 프로바이더 선택 ──────────────────────────────────────────


class TestProviderSelection:
    def test_simple_uses_ollama(self, router):
        result = router.classify("print hello")
        assert "ollama" in result.providers

    def test_complex_uses_cloud_first(self, router):
        result = router.classify("Design a microservice architecture with security vulnerability analysis")
        assert result.providers[0] in ("google", "anthropic", "openai")

    def test_custom_routing_overrides(self):
        custom = SmartRouter(
            custom_routing={
                ComplexityLevel.SIMPLE: ["google", "ollama"],
            }
        )
        result = custom.classify("print hello")
        assert result.providers == ["google", "ollama"]


# ── 스코어링 ─────────────────────────────────────────────────


class TestScoring:
    def test_score_bounded_0_1(self, router):
        # 극단적 프롬프트들
        for prompt in [
            "hi",
            "a " * 2000 + "architecture debug microservice design pattern",
        ]:
            result = router.classify(prompt)
            assert 0.0 <= result.score <= 1.0

    def test_signals_populated(self, router):
        result = router.classify("debug this race condition in architecture")
        assert len(result.signals) > 0

    def test_code_blocks_increase_score(self, router):
        no_code = router.classify("build a thing for me please help")
        with_code = router.classify(
            "build a thing\n```python\nfor i in range(10):\n    pass\n```\n```js\nconsole.log()\n```"
        )
        # code blocks should add to score
        assert with_code.score >= no_code.score
