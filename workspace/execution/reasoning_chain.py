"""
Test-Time Compute Scaling — 다중 샘플 추론 + 자기 합의.

o1-style 내부 긴 추론을 시뮬레이션합니다.
동일 프롬프트로 N회 독립 생성 후, 응답 간 유사도를 비교하여
가장 높은 합의를 얻은 답변을 선택합니다.

Usage:
    from execution.reasoning_chain import ReasoningChain
    from execution.llm_client import LLMClient

    chain = ReasoningChain(llm_client=LLMClient())
    result = chain.reason(
        system_prompt="코드 리뷰어",
        user_prompt="이 함수의 버그를 찾아주세요: ...",
    )
    print(result.answer, result.confidence)
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger  # noqa: E402


@dataclass
class ReasoningResult:
    """다중 추론 결과."""

    answer: str
    confidence: float  # 0.0 ~ 1.0
    n_samples_used: int  # 실제 생성된 샘플 수
    consensus_ratio: float  # 선택된 답변의 합의 비율
    reasoning_trace: list[str]  # 각 샘플의 핵심 요약
    all_responses: list[str] = field(default_factory=list, repr=False)


class ReasoningChain:
    """Test-Time Compute Scaling 추론 체인.

    동일 쿼리에 대해 N회 독립 추론을 수행하고,
    응답 간 구조적 유사도를 비교하여 가장 신뢰할 수 있는 답변을 선택합니다.

    조기 종료: 처음 ceil(n/2)+1 개 중 과반이 일치하면 나머지 스킵.
    """

    def __init__(
        self,
        llm_client: Any,
        *,
        n_samples: int = 3,
        consensus_threshold: float = 0.6,
        early_stop: bool = True,
    ):
        """
        Args:
            llm_client: LLMClient 또는 호환 객체
            n_samples: 독립 생성 횟수 (3~7 권장)
            consensus_threshold: 합의 임계값 (0.0~1.0)
            early_stop: 조기 종료 활성화 여부
        """
        self.llm = llm_client
        self.n_samples = max(2, min(n_samples, 10))
        self.consensus_threshold = consensus_threshold
        self.early_stop = early_stop

    @staticmethod
    def _fingerprint(text: str) -> str:
        """응답의 구조적 핑거프린트 생성.

        정확한 텍스트 매칭 대신, 핵심 구조를 추출하여 비교합니다:
        - 코드 블록 → 정규화된 해시
        - 일반 텍스트 → 핵심 키워드 집합
        """
        import re

        # 코드 블록 추출
        code_blocks = re.findall(r"```[\s\S]*?```", text)

        if code_blocks:
            # 코드 기반 핑거프린트: 공백/주석 제거 후 해시
            normalized = "\n".join(re.sub(r"\s+", " ", block.replace("```", "").strip()) for block in code_blocks)
            return hashlib.md5(normalized.encode()).hexdigest()[:12]

        # 텍스트 기반 핑거프린트: 핵심 단어 집합
        words = set(re.findall(r"\b\w{4,}\b", text.lower()))
        # 상위 20개 단어로 핑거프린트
        sorted_words = sorted(words)[:20]
        return hashlib.md5(" ".join(sorted_words).encode()).hexdigest()[:12]

    @staticmethod
    def _similarity(fp1: str, fp2: str) -> float:
        """두 핑거프린트의 유사도 (0.0~1.0)."""
        if fp1 == fp2:
            return 1.0
        # 간단한 문자 기반 유사도
        common = sum(c1 == c2 for c1, c2 in zip(fp1, fp2))
        return common / max(len(fp1), len(fp2))

    def reason(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> ReasoningResult:
        """N회 독립 추론 후 합의 기반 최선 답변 선택.

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 유저 프롬프트
            temperature: 생성 온도 (다양성을 위해 약간 높게)

        Returns:
            ReasoningResult
        """
        responses: list[str] = []
        fingerprints: list[str] = []
        traces: list[str] = []

        # 첫 번째 응답은 약간 낮은 온도
        temps = [max(0.3, temperature - 0.2)] + [temperature] * (self.n_samples - 1)

        for i in range(self.n_samples):
            try:
                content = self.llm.generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temps[i],
                )
                responses.append(content)
                fp = self._fingerprint(content)
                fingerprints.append(fp)
                traces.append(f"Sample {i + 1}: {content[:80]}...")

                logger.info("ReasoningChain sample %d/%d (fp=%s)", i + 1, self.n_samples, fp)

                # 조기 종료 체크
                if self.early_stop and len(responses) >= 2:
                    # 현재까지의 합의율 계산
                    current_consensus = self._compute_consensus(fingerprints)
                    if current_consensus >= self.consensus_threshold:
                        logger.info(
                            "ReasoningChain 조기 종료: %d/%d 샘플에서 합의율 %.2f",
                            len(responses),
                            self.n_samples,
                            current_consensus,
                        )
                        break

            except Exception as e:
                logger.warning("ReasoningChain sample %d 실패: %s", i + 1, e)
                traces.append(f"Sample {i + 1}: FAILED - {e}")

        if not responses:
            return ReasoningResult(
                answer="",
                confidence=0.0,
                n_samples_used=0,
                consensus_ratio=0.0,
                reasoning_trace=traces,
            )

        # 합의 기반 최선 답변 선택
        best_idx, consensus_ratio = self._select_best(fingerprints)
        confidence = min(1.0, consensus_ratio * (len(responses) / self.n_samples))

        return ReasoningResult(
            answer=responses[best_idx],
            confidence=confidence,
            n_samples_used=len(responses),
            consensus_ratio=consensus_ratio,
            reasoning_trace=traces,
            all_responses=responses,
        )

    def _compute_consensus(self, fingerprints: list[str]) -> float:
        """핑거프린트 목록에서 최대 합의율 계산."""
        if len(fingerprints) < 2:
            return 0.0

        # 각 핑거프린트가 다른 것들과 얼마나 유사한지 계산
        best_ratio = 0.0
        for i, fp_i in enumerate(fingerprints):
            similar_count = sum(
                1 for j, fp_j in enumerate(fingerprints) if i != j and self._similarity(fp_i, fp_j) > 0.5
            )
            ratio = (similar_count + 1) / len(fingerprints)  # +1 for self
            best_ratio = max(best_ratio, ratio)

        return best_ratio

    def _select_best(self, fingerprints: list[str]) -> tuple[int, float]:
        """가장 높은 합의를 가진 응답의 인덱스와 합의율 반환."""
        if len(fingerprints) == 1:
            return 0, 1.0

        scores = []
        for i, fp_i in enumerate(fingerprints):
            sim_sum = sum(self._similarity(fp_i, fp_j) for j, fp_j in enumerate(fingerprints) if i != j)
            scores.append(sim_sum / (len(fingerprints) - 1))

        best_idx = scores.index(max(scores))
        return best_idx, scores[best_idx]

    def reason_with_verification(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> ReasoningResult:
        """reason() + LLM 자체 검증 단계.

        1단계: 다중 샘플 추론으로 최선 답변 선택
        2단계: LLM에게 자신의 답변을 검증하도록 요청
        3단계: 검증 결과에 따라 confidence 조정
        """
        result = self.reason(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

        if not result.answer or result.confidence >= 0.9:
            return result  # 이미 높은 확신이면 스킵

        # 검증 단계
        verify_prompt = (
            f"다음은 이 질문에 대한 답변입니다:\n\n"
            f"질문: {user_prompt}\n\n"
            f"답변: {result.answer}\n\n"
            f"이 답변이 정확한지 검토하세요. "
            f"오류나 개선점이 있다면 수정된 답변을 제공하세요. "
            f"정확하다면 '검증 통과'라고 시작하세요."
        )

        try:
            verification = self.llm.generate_text(
                system_prompt="당신은 엄격한 코드 리뷰어입니다. 답변의 정확성만 검증하세요.",
                user_prompt=verify_prompt,
                temperature=0.2,
            )

            if "검증 통과" in verification or "correct" in verification.lower():
                result.confidence = min(1.0, result.confidence + 0.15)
                result.reasoning_trace.append("Verification: PASSED")
            else:
                # 검증에서 수정된 답변 사용
                result.answer = verification
                result.confidence = max(0.3, result.confidence - 0.1)
                result.reasoning_trace.append("Verification: REVISED")

        except Exception as e:
            result.reasoning_trace.append(f"Verification: FAILED - {e}")

        return result
