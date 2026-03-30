"""
SAGE (Self-Aware Guided Efficient) 검증기.

LLM 응답의 confidence를 자기 평가하여 overthinking을 방지하고,
불필요한 추가 추론을 조기에 종료합니다.

주요 기능:
  - confidence 자기 평가: LLM에게 자신의 답변 확신도를 0~1로 평가 요청
  - self-critique: 반론을 생성한 뒤 원래 답변이 유지되면 강한 확신
  - 토큰 절약: 높은 confidence 시 조기 종료

Usage:
    from execution.confidence_verifier import ConfidenceVerifier
    from execution.llm_client import LLMClient

    verifier = ConfidenceVerifier(llm_client=LLMClient())
    result = verifier.verify(
        question="이 알고리즘의 시간복잡도는?",
        answer="O(n log n)입니다.",
    )
    print(result.confidence, result.is_reliable)
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger  # noqa: E402


DEFAULT_CONFIDENCE_THRESHOLD = 0.7


@dataclass
class VerificationResult:
    """검증 결과."""

    confidence: float  # 0.0 ~ 1.0
    is_reliable: bool  # confidence >= threshold
    final_answer: str  # 최종 답변 (수정될 수 있음)
    counter_argument: str  # 반론 (있는 경우)
    verification_method: str  # "self_eval" | "self_critique" | "skipped"
    tokens_saved: int  # 조기 종료로 절약된 예상 토큰 수


class ConfidenceVerifier:
    """SAGE 기반 자기 인식 검증기.

    LLM이 자신의 응답에 대한 confidence를 평가하고,
    필요한 경우에만 추가 검증을 수행하여 토큰/비용을 절약합니다.

    동작 흐름:
    1. LLM에게 자신의 답변 confidence를 0~1로 평가 요청
    2. confidence >= threshold → 조기 종료 (높은 확신)
    3. confidence < threshold → self-critique 추가 수행
    4. self-critique 후 원래 답변이 유지되면 confidence 상향
    """

    def __init__(
        self,
        llm_client: Any,
        *,
        threshold: float | None = None,
    ):
        env_threshold = os.getenv("CONFIDENCE_THRESHOLD", "").strip()
        self.threshold = (
            threshold
            if threshold is not None
            else (float(env_threshold) if env_threshold else DEFAULT_CONFIDENCE_THRESHOLD)
        )
        self.llm = llm_client

    def verify(
        self,
        question: str,
        answer: str,
    ) -> VerificationResult:
        """답변의 confidence를 자기 평가합니다.

        Args:
            question: 원래 질문
            answer: 검증할 답변

        Returns:
            VerificationResult
        """
        # 빈 답변은 바로 실패
        if not answer.strip():
            return VerificationResult(
                confidence=0.0,
                is_reliable=False,
                final_answer=answer,
                counter_argument="",
                verification_method="skipped",
                tokens_saved=0,
            )

        # Step 1: 자기 평가
        confidence = self._self_evaluate(question, answer)

        if confidence >= self.threshold:
            logger.info(
                "ConfidenceVerifier: 높은 확신 (%.2f >= %.2f), 조기 종료",
                confidence,
                self.threshold,
            )
            return VerificationResult(
                confidence=confidence,
                is_reliable=True,
                final_answer=answer,
                counter_argument="",
                verification_method="self_eval",
                tokens_saved=200,  # self-critique 스킵으로 절약
            )

        # Step 2: 낮은 confidence → self-critique
        logger.info(
            "ConfidenceVerifier: 낮은 확신 (%.2f < %.2f), self-critique 수행",
            confidence,
            self.threshold,
        )
        return self._self_critique(question, answer, initial_confidence=confidence)

    def verify_with_counter(
        self,
        question: str,
        answer: str,
    ) -> VerificationResult:
        """무조건 self-critique를 수행하는 강화 검증.

        높은 confidence라도 반론 생성 후에도 유지되는지 확인합니다.
        """
        if not answer.strip():
            return VerificationResult(
                confidence=0.0,
                is_reliable=False,
                final_answer=answer,
                counter_argument="",
                verification_method="skipped",
                tokens_saved=0,
            )

        confidence = self._self_evaluate(question, answer)
        return self._self_critique(question, answer, initial_confidence=confidence)

    def _self_evaluate(self, question: str, answer: str) -> float:
        """LLM에게 자신의 답변 confidence를 0~1로 평가 요청."""
        eval_prompt = (
            "다음 질문과 답변을 읽고, 답변의 정확도를 0.0에서 1.0 사이 소수로 평가하세요.\n\n"
            f"질문: {question}\n\n"
            f"답변: {answer[:2000]}\n\n"
            "규칙:\n"
            "- 0.0 = 완전히 틀림, 1.0 = 완벽히 정확\n"
            "- 숫자 하나만 출력하세요 (예: 0.85)\n"
            "- 다른 텍스트는 절대 포함하지 마세요"
        )

        try:
            raw = self.llm.generate_text(
                system_prompt="당신은 정확도 평가 전문가입니다. 숫자만 출력하세요.",
                user_prompt=eval_prompt,
                temperature=0.1,
            )
            return self._parse_confidence(raw)
        except Exception as e:
            logger.warning("ConfidenceVerifier: 자기 평가 실패 (%s), 기본값 0.5", e)
            return 0.5

    def _parse_confidence(self, raw: str) -> float:
        """LLM 응답에서 confidence 값 추출."""
        # 소수 패턴 추출
        matches = re.findall(r"(\d+\.\d+|\d+)", raw.strip())
        if matches:
            val = float(matches[0])
            return max(0.0, min(1.0, val))
        return 0.5  # 파싱 실패 시 기본값

    def _self_critique(
        self,
        question: str,
        answer: str,
        *,
        initial_confidence: float,
    ) -> VerificationResult:
        """반론 생성 후 원래 답변의 타당성 재평가."""
        # Step 1: 반론 생성
        critique_prompt = (
            "다음 질문에 대한 답변을 비판적으로 검토하세요.\n"
            "가능한 오류, 누락, 또는 대안적 해석을 제시하세요.\n\n"
            f"질문: {question}\n\n"
            f"답변: {answer[:2000]}\n\n"
            "형식:\n"
            "- 반론: [구체적인 반론 내용]\n"
            "- 수정 제안: [있다면 수정된 답변, 없으면 '수정 불필요']\n"
            "- 원래 답변 유지: [예/아니오]"
        )

        try:
            critique = self.llm.generate_text(
                system_prompt="당신은 엄격한 비판적 리뷰어입니다.",
                user_prompt=critique_prompt,
                temperature=0.3,
            )
        except Exception as e:
            logger.warning("ConfidenceVerifier: self-critique 실패 (%s)", e)
            return VerificationResult(
                confidence=initial_confidence,
                is_reliable=initial_confidence >= self.threshold,
                final_answer=answer,
                counter_argument=f"critique 실패: {e}",
                verification_method="self_critique",
                tokens_saved=0,
            )

        # 원래 답변이 유지되는지 확인
        critique_lower = critique.lower()
        answer_maintained = (
            "수정 불필요" in critique
            or "원래 답변 유지: 예" in critique
            or "유지: 예" in critique
            or "no revision" in critique_lower
            or "answer is correct" in critique_lower
        )

        if answer_maintained:
            # 반론을 견딤 → confidence 상향
            revised_confidence = min(1.0, initial_confidence + 0.2)
            final_answer = answer
            logger.info("ConfidenceVerifier: 반론 견딤, confidence %.2f → %.2f", initial_confidence, revised_confidence)
        else:
            # 반론에 타당성 있음 → 수정된 답변 사용, confidence 유지
            # 수정 제안 추출 시도
            revision_match = re.search(r"수정 제안:\s*(.+?)(?:\n|$)", critique, re.DOTALL)
            if revision_match and "수정 불필요" not in revision_match.group(1):
                final_answer = revision_match.group(1).strip()
            else:
                final_answer = answer
            revised_confidence = max(0.2, initial_confidence - 0.1)
            logger.info("ConfidenceVerifier: 반론 유효, confidence %.2f → %.2f", initial_confidence, revised_confidence)

        return VerificationResult(
            confidence=revised_confidence,
            is_reliable=revised_confidence >= self.threshold,
            final_answer=final_answer,
            counter_argument=critique,
            verification_method="self_critique",
            tokens_saved=0,
        )
