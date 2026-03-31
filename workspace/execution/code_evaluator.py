"""
Code Evaluator 모듈 - 코드 생성을 평가하고 최적화 루프에 사용되는 Pydantic 기반 평가기
T-071 (Self-Reflection) 및 T-072 (Pydantic Structured Outputs & Security Score) 구현.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from execution._logging import logger


class EvaluationResult(BaseModel):
    """Pydantic schema for structured code evaluation output."""

    self_reflection: str = Field(
        ...,
        description=(
            "단계별 논리적 사고 및 코드 분석 과정 (Self-reflection). "
            "코드의 품질, 문제점, 예외 상황을 어떻게 처리하는지 스스로 질문하고 답변합니다."
        ),
    )
    score: float = Field(
        ...,
        description="전반적인 품질 점수 (0.0 ~ 1.0)",
    )
    security_score: float = Field(
        ...,
        description=(
            "보안 관점에서의 점수 (0.0 ~ 1.0). "
            "SQL Injection, XSS, Command Injection 등 취약점이 있다면 점수를 낮게 줍니다."
        ),
    )
    performance_score: float = Field(
        ...,
        description="성능 관점에서의 점수 (0.0 ~ 1.0). 불필요한 루프, 비효율적인 메모리 사용 시 점수를 낮춥니다.",
    )
    readability_score: float = Field(
        ...,
        description="가독성 및 모범 사례(Best Practices) 준수 점수 (0.0 ~ 1.0).",
    )
    is_approved: bool = Field(
        ...,
        description=(
            "코드가 요구사항을 완벽히 충족하며 품질(보안/성능/가독성)이 우수하여 즉시 병합(Merge)해도 된다면 true, "
            "실패/수정이 필요하면 false."
        ),
    )
    feedback: str = Field(
        ...,
        description=(
            "is_approved가 false일 경우, 수정할 부분을 구체적이고 실천 가능한(actionable) 형태로 제시합니다. "
            "true일 경우 칭찬이나 빈 문자열."
        ),
    )


class CodeEvaluator:
    """LLM을 래핑하여 Pydantic 모델 형태의 신뢰도 평가를 제공하는 에이전트."""

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def evaluate(self, requirements: str, code: str) -> EvaluationResult:
        """코드가 주어진 요구사항(바이브 입력)을 충족하는지 평가합니다."""
        logger.info("[CodeEvaluator] Pydantic 기반 코드 평가 시작...")

        # Pydantic JSON 스키마 추출
        schema_json = json.dumps(EvaluationResult.model_json_schema(), indent=2, ensure_ascii=False)

        system_prompt = (
            "당신은 최고 수준의 시니어 보안 전문가이자 수석 소프트웨어 엔지니어입니다.\n"
            "주어진 요구사항(Requirements)과 작성된 코드(Code)를 비교 분석하고, "
            "반드시 아래의 JSON Schema를 완벽하게 준수하는 JSON 객체만 반환하세요.\n"
            "마크다운 블록(```json)이나 다른 설명 없이 순수한 JSON 텍스트로 응답해야 합니다.\n\n"
            "### 요구되는 JSON Schema:\n"
            f"{schema_json}\n"
        )

        user_prompt = f"### 요구사항 (Requirements):\n{requirements}\n\n### 평가 대상 코드 (Code):\n{code}\n"

        try:
            # generate_json을 통해 JSON 응답 강제 (지원되는 LLM인 경우 json_mode=True 활성화됨)
            result_dict = self.llm.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # 낮은 온도로 일관된 평가 유도
            )

            # Pydantic으로 응답 검증
            eval_result = EvaluationResult.model_validate(result_dict)
            logger.info(
                "[CodeEvaluator] 평가 완료 - Approved: %s, Score: %.2f (Sec: %.2f, Perf: %.2f, Read: %.2f)",
                eval_result.is_approved,
                eval_result.score,
                eval_result.security_score,
                eval_result.performance_score,
                eval_result.readability_score,
            )
            return eval_result

        except Exception as e:
            logger.warning("[CodeEvaluator] 평가 중 오류 발생: %s", e)
            # 파싱 실패나 API 호출 오류 등에 대비한 기본 응답
            return EvaluationResult(
                self_reflection=f"LLM 호출 또는 JSON 파싱 중 오류 발생: {e}",
                score=0.0,
                security_score=0.0,
                performance_score=0.0,
                readability_score=0.0,
                is_approved=False,
                feedback=f"시스템 오류로 코드를 평가하지 못했습니다: {e}",
            )
