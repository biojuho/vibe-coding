"""파이프라인 에러 타입 정의 — SiteAgent 패턴 차용.

SiteAgent의 InvokeErrorType에서 영감받아, 우리 파이프라인의 모든 에러를
9가지 구조화된 타입으로 분류합니다. 이를 통해:
  1. 로그에서 즉시 원인 파악
  2. 에러 타입별 차별화된 복구 전략 실행
  3. 모니터링 대시보드에서 에러 분포 시각화
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class PipelineErrorType(str, Enum):
    """파이프라인 에러 분류 체계.

    SiteAgent의 InvokeErrorType을 참고하여 우리 파이프라인에 맞게 재설계:

    - NETWORK_ERROR: 네트워크 연결 실패 (타임아웃, DNS 등)
    - RATE_LIMIT: API 속도 제한 (429 응답)
    - AUTH_ERROR: 인증 실패 (잘못된 API 키, 만료된 토큰)
    - SERVER_ERROR: 외부 서비스 서버 오류 (5xx)
    - INVALID_RESPONSE: LLM이 유효하지 않은 응답 반환 (JSON 파싱 실패 등)
    - CONTENT_FILTER: 콘텐츠 정책 위반 (DALL-E 안전 필터 등)
    - CONTEXT_LENGTH: 컨텍스트 창 초과
    - RESOURCE_ERROR: 로컬 리소스 문제 (디스크 공간, 메모리, 파일 없음)
    - UNKNOWN: 분류 불가 에러
    """

    NETWORK_ERROR = "network_error"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    INVALID_RESPONSE = "invalid_response"
    CONTENT_FILTER = "content_filter"
    CONTEXT_LENGTH = "context_length"
    RESOURCE_ERROR = "resource_error"
    UNKNOWN = "unknown"

    @property
    def is_retryable(self) -> bool:
        """이 에러 타입이 재시도 가능한지 여부."""
        return self in _RETRYABLE_TYPES

    @property
    def suggested_wait_sec(self) -> float:
        """에러 타입별 권장 대기 시간 (초)."""
        return _WAIT_TIMES.get(self, 2.0)

    @property
    def icon(self) -> str:
        """에러 타입별 로그 아이콘."""
        return _ICONS.get(self, "❓")


# 재시도 가능한 에러 타입
_RETRYABLE_TYPES = {
    PipelineErrorType.NETWORK_ERROR,
    PipelineErrorType.RATE_LIMIT,
    PipelineErrorType.SERVER_ERROR,
    PipelineErrorType.INVALID_RESPONSE,
}

# 에러 타입별 권장 대기 시간
_WAIT_TIMES = {
    PipelineErrorType.NETWORK_ERROR: 3.0,
    PipelineErrorType.RATE_LIMIT: 15.0,  # rate limit은 더 오래 기다림
    PipelineErrorType.SERVER_ERROR: 5.0,
    PipelineErrorType.INVALID_RESPONSE: 1.0,  # 즉시 재시도 가능
    PipelineErrorType.AUTH_ERROR: 0.0,  # 재시도 무의미
    PipelineErrorType.CONTENT_FILTER: 0.0,  # 프롬프트 수정 필요
    PipelineErrorType.CONTEXT_LENGTH: 0.0,  # 입력 축소 필요
    PipelineErrorType.RESOURCE_ERROR: 0.0,  # 시스템 점검 필요
}

# 로그 아이콘
_ICONS = {
    PipelineErrorType.NETWORK_ERROR: "🌐",
    PipelineErrorType.RATE_LIMIT: "⏱️",
    PipelineErrorType.AUTH_ERROR: "🔑",
    PipelineErrorType.SERVER_ERROR: "🖥️",
    PipelineErrorType.INVALID_RESPONSE: "📄",
    PipelineErrorType.CONTENT_FILTER: "🛡️",
    PipelineErrorType.CONTEXT_LENGTH: "📏",
    PipelineErrorType.RESOURCE_ERROR: "💾",
    PipelineErrorType.UNKNOWN: "❓",
}

# 에러 메시지 → 타입 매핑 키워드
_CLASSIFICATION_RULES: list[tuple[list[str], PipelineErrorType]] = [
    # AUTH_ERROR — 재시도 불가
    (
        [
            "invalid api key",
            "unauthorized",
            "permission denied",
            "insufficient_quota",
            "credit balance is too low",
            "billing",
            "invalid_api_key",
            "authentication",
            "api key not found",
        ],
        PipelineErrorType.AUTH_ERROR,
    ),
    # RATE_LIMIT
    (
        ["rate limit", "rate_limit", "429", "too many requests", "quota exceeded", "resource_exhausted", "throttl"],
        PipelineErrorType.RATE_LIMIT,
    ),
    # CONTENT_FILTER
    (
        [
            "content_policy",
            "content policy",
            "safety",
            "content_filter",
            "blocked",
            "moderation",
            "harmful",
            "inappropriate",
            "your request was rejected",
        ],
        PipelineErrorType.CONTENT_FILTER,
    ),
    # CONTEXT_LENGTH
    (
        [
            "context_length",
            "context length",
            "max_tokens",
            "maximum context",
            "token limit",
            "too long",
            "context window",
        ],
        PipelineErrorType.CONTEXT_LENGTH,
    ),
    # INVALID_RESPONSE
    (
        ["json", "parse error", "decode", "invalid response", "malformed", "expecting value", "unexpected token"],
        PipelineErrorType.INVALID_RESPONSE,
    ),
    # SERVER_ERROR
    (
        [
            "500",
            "502",
            "503",
            "504",
            "internal server error",
            "server error",
            "service unavailable",
            "bad gateway",
            "overloaded",
        ],
        PipelineErrorType.SERVER_ERROR,
    ),
    # NETWORK_ERROR
    (
        ["timeout", "timed out", "connection", "network", "dns", "unreachable", "reset by peer", "ssl", "eof"],
        PipelineErrorType.NETWORK_ERROR,
    ),
    # RESOURCE_ERROR
    (
        ["disk", "space", "memory", "no such file", "file not found", "permission", "errno", "oserror", "ioerror"],
        PipelineErrorType.RESOURCE_ERROR,
    ),
]


def classify_error(error: BaseException) -> PipelineErrorType:
    """에러를 PipelineErrorType으로 분류.

    에러 메시지를 소문자로 변환 후 키워드 매칭 규칙을 순차 적용합니다.
    매칭되는 규칙이 없으면 UNKNOWN을 반환합니다.

    Args:
        error: 분류할 예외 객체

    Returns:
        분류된 PipelineErrorType

    Examples:
        >>> classify_error(TimeoutError("Request timed out"))
        <PipelineErrorType.NETWORK_ERROR: 'network_error'>
        >>> classify_error(ValueError("JSON parse error"))
        <PipelineErrorType.INVALID_RESPONSE: 'invalid_response'>
    """
    text = str(error).lower()

    for keywords, error_type in _CLASSIFICATION_RULES:
        if any(kw in text for kw in keywords):
            return error_type

    return PipelineErrorType.UNKNOWN


class PipelineError(Exception):
    """구조화된 파이프라인 에러.

    에러 타입, 원인 에러, 실패한 스텝 이름, 프로바이더 정보를 포함합니다.
    """

    def __init__(
        self,
        message: str,
        error_type: PipelineErrorType,
        *,
        step: str = "",
        provider: str = "",
        cause: BaseException | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.step = step
        self.provider = provider
        self.cause = cause
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """직렬화 가능한 딕셔너리로 변환."""
        return {
            "message": str(self),
            "error_type": self.error_type.value,
            "step": self.step,
            "provider": self.provider,
            "is_retryable": self.error_type.is_retryable,
            "cause_type": type(self.cause).__name__ if self.cause else "",
            "context": self.context,
        }

    @classmethod
    def from_exception(
        cls,
        exc: BaseException,
        *,
        step: str = "",
        provider: str = "",
    ) -> PipelineError:
        """일반 예외를 PipelineError로 변환."""
        error_type = classify_error(exc)
        return cls(
            message=str(exc),
            error_type=error_type,
            step=step,
            provider=provider,
            cause=exc,
        )
