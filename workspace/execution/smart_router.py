"""
Smart Complexity Router — 쿼리 복잡도 기반 모델 라우팅.

자연어 프롬프트의 복잡도를 분석하여 로컬 모델(무료)과
클라우드 API(정확)를 동적으로 선택합니다.

Usage:
    from execution.smart_router import SmartRouter
    router = SmartRouter()
    result = router.route(
        system_prompt="...",
        user_prompt="...",
    )
    # result.provider, result.content, result.complexity_level
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger  # noqa: E402


class ComplexityLevel(Enum):
    """쿼리 복잡도 수준."""

    SIMPLE = "simple"  # boilerplate, CRUD, 단순 편집, 짧은 질문
    MODERATE = "moderate"  # 함수 구현, 리팩토링, 중간 규모 작업
    COMPLEX = "complex"  # 아키텍처 설계, 디버깅, 멀티파일 변경, 장문 추론


# ── 복잡도 분류 키워드 (LLM 없이 결정론적) ───────────────────

_COMPLEX_KEYWORDS = [
    # 아키텍처/설계
    "architecture",
    "아키텍처",
    "설계",
    "design pattern",
    "디자인 패턴",
    "시스템 설계",
    "system design",
    "마이크로서비스",
    "microservice",
    # 디버깅/분석
    "debug",
    "디버그",
    "디버깅",
    "근본 원인",
    "root cause",
    "stack trace",
    "스택 트레이스",
    "메모리 릭",
    "memory leak",
    "race condition",
    "deadlock",
    # 멀티파일/대규모
    "multi-file",
    "멀티파일",
    "여러 파일",
    "across files",
    "프로젝트 구조",
    "migration",
    "마이그레이션",
    "리팩토링 전체",
    "전면 수정",
    "대규모",
    # 복잡한 추론
    "trade-off",
    "트레이드오프",
    "최적화 전략",
    "비교 분석",
    "장단점",
    "pros and cons",
    "보안 취약점",
    "security vulnerability",
    "성능 병목",
    "concurrency",
    "동시성",
    "비동기 아키텍처",
]

_MODERATE_KEYWORDS = [
    # 구현
    "implement",
    "구현",
    "refactor",
    "리팩토링",
    "class",
    "클래스",
    "async",
    "비동기",
    "테스트 작성",
    "write test",
    "unit test",
    "에러 처리",
    "error handling",
    "exception",
    "API 연동",
    "integration",
    "통합",
    # 중간 규모 작업
    "함수 작성",
    "method",
    "메서드",
    "데이터 변환",
    "transform",
    "파싱",
    "parsing",
    "validate",
    "검증",
    "middleware",
    "decorator",
    "데코레이터",
    "type hint",
    "타입",
    "interface",
]

_SIMPLE_KEYWORDS = [
    # 단순 코드
    "for loop",
    "import",
    "print",
    "hello world",
    "CRUD",
    "getter",
    "setter",
    "변수",
    "variable",
    "상수",
    "constant",
    "주석",
    "comment",
    "docstring",
    "이름 변경",
    "rename",
    # 간단한 질문
    "what is",
    "뭐야",
    "무엇",
    "어떻게",
    "정리",
    "format",
    "포맷",
    "린트",
    "lint",
    "indent",
    "들여쓰기",
]


@dataclass
class RoutingDecision:
    """라우팅 결정 결과."""

    complexity: ComplexityLevel
    providers: list[str]
    score: float  # 0.0 (simple) ~ 1.0 (complex)
    signals: list[str]  # 분류에 기여한 키워드/신호


@dataclass
class RoutedResult:
    """라우팅된 LLM 호출 결과."""

    content: str
    provider_used: str
    complexity: ComplexityLevel
    input_tokens: int
    output_tokens: int


class SmartRouter:
    """복잡도 기반 모델 라우터.

    프롬프트를 분석하여 복잡도를 SIMPLE/MODERATE/COMPLEX로 분류하고,
    각 수준에 적합한 프로바이더 순서를 선택합니다.

    - SIMPLE → Ollama 로컬 (무료, 빠름)
    - MODERATE → Ollama → Google → DeepSeek (균형)
    - COMPLEX → Google → Anthropic → OpenAI → Ollama (정확도 우선)
    """

    # 복잡도별 프로바이더 순서
    PROVIDER_ROUTING: dict[ComplexityLevel, list[str]] = {
        ComplexityLevel.SIMPLE: ["ollama"],
        ComplexityLevel.MODERATE: ["ollama", "google", "deepseek", "groq"],
        ComplexityLevel.COMPLEX: ["google", "anthropic", "openai", "ollama"],
    }

    def __init__(
        self,
        *,
        simple_threshold: int = 200,
        complex_threshold: int = 800,
        custom_routing: dict[ComplexityLevel, list[str]] | None = None,
    ):
        """
        Args:
            simple_threshold: 토큰 수 이하 시 SIMPLE 후보
            complex_threshold: 토큰 수 이상 시 COMPLEX 후보
            custom_routing: 기본 프로바이더 순서 오버라이드
        """
        self.simple_threshold = simple_threshold
        self.complex_threshold = complex_threshold
        if custom_routing:
            self.PROVIDER_ROUTING = {**self.PROVIDER_ROUTING, **custom_routing}

    def classify(self, prompt: str) -> RoutingDecision:
        """프롬프트 복잡도를 결정론적으로 분류합니다.

        LLM을 호출하지 않으며, 키워드 매칭 + 길이 휴리스틱을 사용합니다.

        Returns:
            RoutingDecision(complexity, providers, score, signals)
        """
        prompt_lower = prompt.lower()
        signals: list[str] = []

        # 토큰 수 근사 (공백 분할)
        token_count = len(prompt.split())

        # 키워드 기반 스코어링
        complex_hits = [kw for kw in _COMPLEX_KEYWORDS if kw.lower() in prompt_lower]
        moderate_hits = [kw for kw in _MODERATE_KEYWORDS if kw.lower() in prompt_lower]
        simple_hits = [kw for kw in _SIMPLE_KEYWORDS if kw.lower() in prompt_lower]

        # 구조적 복잡도 신호
        code_block_count = len(re.findall(r"```", prompt))
        line_count = prompt.count("\n") + 1
        has_multi_questions = len(re.findall(r"\?", prompt)) >= 3
        has_numbered_list = bool(re.search(r"\n\s*\d+\.\s", prompt))

        # 스코어 계산 (0.0 ~ 1.0)
        score = 0.0

        # 키워드 기반
        score += len(complex_hits) * 0.2
        score += len(moderate_hits) * 0.08
        score -= len(simple_hits) * 0.1

        # 길이 기반
        if token_count > self.complex_threshold:
            score += 0.25
            signals.append(f"long_prompt({token_count} tokens)")
        elif token_count < self.simple_threshold:
            score -= 0.15
            signals.append(f"short_prompt({token_count} tokens)")

        # 구조 기반
        if code_block_count >= 2:
            score += 0.15
            signals.append(f"code_blocks({code_block_count})")
        if has_multi_questions:
            score += 0.1
            signals.append("multi_questions")
        if has_numbered_list:
            score += 0.05
            signals.append("numbered_list")
        if line_count > 30:
            score += 0.1
            signals.append(f"many_lines({line_count})")

        # 신호 수집
        if complex_hits:
            signals.extend([f"complex:{kw}" for kw in complex_hits[:3]])
        if moderate_hits:
            signals.extend([f"moderate:{kw}" for kw in moderate_hits[:3]])
        if simple_hits:
            signals.extend([f"simple:{kw}" for kw in simple_hits[:3]])

        # 최종 분류
        score = max(0.0, min(1.0, score))

        if score >= 0.4:
            level = ComplexityLevel.COMPLEX
        elif score >= 0.15:
            level = ComplexityLevel.MODERATE
        else:
            level = ComplexityLevel.SIMPLE

        providers = list(self.PROVIDER_ROUTING[level])

        logger.info(
            "SmartRouter 분류: %s (score=%.2f, signals=%s)",
            level.value,
            score,
            signals[:5],
        )

        return RoutingDecision(
            complexity=level,
            providers=providers,
            score=score,
            signals=signals,
        )

    def route(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> RoutedResult:
        """복잡도 분류 + LLMClient 호출을 원스텝으로 실행합니다.

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 유저 프롬프트
            temperature: 생성 온도
            json_mode: JSON 응답 요청 여부

        Returns:
            RoutedResult with content, provider_used, complexity
        """
        from execution.llm_client import LLMClient

        decision = self.classify(user_prompt)

        client = LLMClient(providers=decision.providers)

        if json_mode:
            result = client.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
            # generate_json은 dict을 반환하므로 직렬화
            import json

            content = json.dumps(result, ensure_ascii=False)
        else:
            content = client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )

        # 어떤 프로바이더가 실제로 사용되었는지 추적
        provider_used = client.enabled_providers()[0] if client.enabled_providers() else "unknown"

        return RoutedResult(
            content=content,
            provider_used=provider_used,
            complexity=decision.complexity,
            input_tokens=0,  # 집계는 LLMClient 내부에서 처리
            output_tokens=0,
        )


# ── CLI ──────────────────────────────────────────────────────


def _cli_main() -> None:
    """데모: 다양한 프롬프트로 복잡도 분류 테스트."""
    router = SmartRouter()

    test_cases = [
        ("print('hello world')", "SIMPLE 예상"),
        ("Write a for loop that sums numbers from 1 to 100", "SIMPLE 예상"),
        (
            "Implement an async Python class that handles WebSocket connections with retry logic and error handling",
            "MODERATE 예상",
        ),
        (
            "Debug this race condition in our microservice architecture. "
            "The system design uses event sourcing with CQRS pattern but we're "
            "seeing data inconsistency across multiple files when concurrent "
            "requests hit the API. Here's the stack trace:\n"
            "```\nTraceback (most recent call last):\n  File 'handler.py', line 42\n```\n"
            "Compare the trade-offs between using locks vs channels for this concurrency issue.",
            "COMPLEX 예상",
        ),
    ]

    for prompt, expected in test_cases:
        decision = router.classify(prompt)
        status = "✅" if expected.startswith(decision.complexity.value.upper()) else "⚠️"
        print(f"\n{status} {expected}")
        print(f"   분류: {decision.complexity.value} (score={decision.score:.2f})")
        print(f"   프로바이더: {decision.providers}")
        print(f"   신호: {decision.signals[:5]}")


if __name__ == "__main__":
    _cli_main()
