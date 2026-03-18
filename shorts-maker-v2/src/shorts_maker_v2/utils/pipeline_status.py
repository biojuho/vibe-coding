"""파이프라인 상태 표시 시스템 — SiteAgent 인디케이터 패턴 차용.

SiteAgent의 실시간 상태 인디케이터(thinking/executing/completed/error/retry)에서
영감받아 파이프라인 스텝별 상태를 시각적으로 표시합니다.

사용처:
  - CLI 출력의 스텝별 상태 표시
  - JSONL 로그의 status_type 필드
  - 향후 대시보드 연동 시 컬러/애니메이션 매핑
"""

from __future__ import annotations

from enum import Enum
from typing import Any
import logging
import sys
import time

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """파이프라인 스텝 상태.

    SiteAgent의 상태 인디케이터를 파이프라인 맥락으로 재해석:
    - THINKING: LLM 호출 대기/처리 중
    - EXECUTING: 미디어 생성/렌더링 등 비-LLM 작업 수행 중
    - COMPLETED: 스텝 성공 완료
    - ERROR: 스텝 실패
    - RETRY: 폴백 또는 재시도 진행 중
    - SKIPPED: 사전 조건 미충족으로 스킵
    """

    THINKING = "thinking"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"
    RETRY = "retry"
    SKIPPED = "skipped"


# 상태별 컬러 코드 (ANSI 256-color + Hex for dashboards)
_STATUS_COLORS: dict[StepStatus, dict[str, str]] = {
    StepStatus.THINKING: {
        "hex": "#39B6FF",     # SiteAgent --color-1 (블루)
        "ansi": "\033[38;5;39m",  # 밝은 파랑
    },
    StepStatus.EXECUTING: {
        "hex": "#BD45FB",     # SiteAgent --color-2 (퍼플)
        "ansi": "\033[38;5;135m",  # 보라
    },
    StepStatus.COMPLETED: {
        "hex": "#22C55E",     # SiteAgent 완료 (그린)
        "ansi": "\033[38;5;34m",  # 초록
    },
    StepStatus.ERROR: {
        "hex": "#EF4444",     # SiteAgent --color-3 (레드)
        "ansi": "\033[38;5;196m",  # 빨강
    },
    StepStatus.RETRY: {
        "hex": "#FFD600",     # SiteAgent --color-4 (옐로우)
        "ansi": "\033[38;5;220m",  # 노랑
    },
    StepStatus.SKIPPED: {
        "hex": "#6B7280",     # 회색
        "ansi": "\033[38;5;245m",  # 회색
    },
}

_RESET = "\033[0m"

# 상태별 아이콘
_STATUS_ICONS: dict[StepStatus, str] = {
    StepStatus.THINKING: "🧠",
    StepStatus.EXECUTING: "⚙️",
    StepStatus.COMPLETED: "✅",
    StepStatus.ERROR: "❌",
    StepStatus.RETRY: "🔄",
    StepStatus.SKIPPED: "⏭️",
}


def get_status_color(status: StepStatus, fmt: str = "hex") -> str:
    """상태에 대한 색상 코드 반환.

    Args:
        status: 파이프라인 스텝 상태
        fmt: "hex" (대시보드용) 또는 "ansi" (터미널용)

    Returns:
        색상 코드 문자열
    """
    return _STATUS_COLORS.get(status, _STATUS_COLORS[StepStatus.SKIPPED]).get(fmt, "")


def get_status_icon(status: StepStatus) -> str:
    """상태에 대한 아이콘 반환."""
    return _STATUS_ICONS.get(status, "❓")


def format_status_line(
    step_name: str,
    status: StepStatus,
    *,
    detail: str = "",
    elapsed_sec: float | None = None,
    use_color: bool = True,
) -> str:
    """상태 표시 라인 포맷.

    Args:
        step_name: 스텝 이름 (예: "script", "media", "render")
        status: 현재 상태
        detail: 추가 상세 정보
        elapsed_sec: 소요 시간 (초)
        use_color: ANSI 색상 사용 여부

    Returns:
        포맷팅된 상태 라인

    Examples:
        >>> format_status_line("script", StepStatus.THINKING, detail="gemini-3.1-flash")
        '🧠 [script] thinking — gemini-3.1-flash'
    """
    icon = get_status_icon(status)
    ansi = get_status_color(status, "ansi") if use_color else ""
    reset = _RESET if use_color else ""

    parts = [f"{icon} {ansi}[{step_name}]{reset} {status.value}"]
    if detail:
        parts.append(f"— {detail}")
    if elapsed_sec is not None:
        parts.append(f"({elapsed_sec:.1f}s)")

    return " ".join(parts)


class PipelineStatusTracker:
    """파이프라인 전체 상태 추적기.

    각 스텝의 상태를 기록하고 CLI/로그로 출력합니다.

    Usage:
        tracker = PipelineStatusTracker(job_id="20261231-120000-abc123")
        tracker.update("research", StepStatus.THINKING, detail="Gemini Search Grounding")
        tracker.update("research", StepStatus.COMPLETED, elapsed_sec=3.2)
        tracker.update("script", StepStatus.THINKING, detail="gemini-3.1-flash")
    """

    def __init__(self, job_id: str = "", *, quiet: bool = False):
        self.job_id = job_id
        self.quiet = quiet
        self._steps: dict[str, dict[str, Any]] = {}
        self._start_times: dict[str, float] = {}

    def start(self, step_name: str, detail: str = "") -> None:
        """스텝 시작 기록."""
        self._start_times[step_name] = time.time()
        self.update(step_name, StepStatus.THINKING, detail=detail)

    def update(
        self,
        step_name: str,
        status: StepStatus,
        *,
        detail: str = "",
        elapsed_sec: float | None = None,
    ) -> None:
        """스텝 상태 업데이트 및 출력."""
        # 자동 elapsed 계산
        if elapsed_sec is None and step_name in self._start_times:
            if status in (StepStatus.COMPLETED, StepStatus.ERROR, StepStatus.SKIPPED):
                elapsed_sec = round(time.time() - self._start_times[step_name], 1)

        self._steps[step_name] = {
            "status": status.value,
            "status_color": get_status_color(status, "hex"),
            "detail": detail,
            "elapsed_sec": elapsed_sec,
            "timestamp": time.time(),
        }

        if not self.quiet:
            use_color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
            line = format_status_line(
                step_name, status,
                detail=detail, elapsed_sec=elapsed_sec,
                use_color=use_color,
            )
            print(line)

        logger.info(
            "pipeline_status",
            extra={
                "step": step_name,
                "status": status.value,
                "detail": detail,
                "elapsed_sec": elapsed_sec,
                "job_id": self.job_id,
            },
        )

    def complete(self, step_name: str, detail: str = "") -> None:
        """스텝 완료 기록 (편의 메서드)."""
        self.update(step_name, StepStatus.COMPLETED, detail=detail)

    def fail(self, step_name: str, detail: str = "") -> None:
        """스텝 실패 기록 (편의 메서드)."""
        self.update(step_name, StepStatus.ERROR, detail=detail)

    def retry(self, step_name: str, detail: str = "") -> None:
        """재시도 기록 (편의 메서드)."""
        self.update(step_name, StepStatus.RETRY, detail=detail)

    def summary(self) -> dict[str, dict[str, Any]]:
        """전체 스텝 상태 요약."""
        return dict(self._steps)

    def to_log_record(self) -> dict[str, Any]:
        """JSONL 로그용 딕셔너리."""
        return {
            "job_id": self.job_id,
            "steps": self.summary(),
            "total_steps": len(self._steps),
            "completed": sum(
                1 for s in self._steps.values()
                if s["status"] == StepStatus.COMPLETED.value
            ),
            "failed": sum(
                1 for s in self._steps.values()
                if s["status"] == StepStatus.ERROR.value
            ),
        }
