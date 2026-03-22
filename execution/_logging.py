"""중앙 로깅 설정 — loguru 기반.

모든 execution 스크립트에서 import하여 사용합니다.
stdlib logging과 호환되며, 파일 로테이션 + 콘솔 출력을 제공합니다.

사용법:
    from execution._logging import logger, setup_logging
    setup_logging()  # 최초 1회 호출 (선택, import 시 기본 설정 적용)
    logger.info("message")
    logger.error("error", extra_field=value)

기존 stdlib logging 코드와의 호환:
    import logging
    logging.basicConfig(...)  # 기존 코드 그대로 두면 됨
    # loguru가 stdlib 핸들러를 intercept하므로 양쪽 모두 동일 출력으로 수렴
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _ROOT / ".tmp" / "logs"
_CONFIGURED = False


def setup_logging(
    *,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    rotation: str = "1 day",
    retention: str = "7 days",
    max_size: str = "500 MB",
) -> None:
    """로깅을 설정합니다. 여러 번 호출해도 안전합니다."""
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    _CONFIGURED = True

    # 기존 핸들러 제거
    logger.remove()

    # 콘솔 출력 (색상 + 간결 포맷)
    logger.add(
        sys.stderr,
        level=console_level,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | {message}",
        colorize=True,
    )

    # 파일 출력 (JSONL + 로테이션)
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(_LOG_DIR / "execution_{time:YYYY-MM-DD}.jsonl"),
        level=file_level,
        format="{message}",
        serialize=True,  # JSON 형식
        rotation=rotation,
        retention=retention,
        compression="gz",
        encoding="utf-8",
    )

    # stdlib logging → loguru intercept
    import logging

    class _InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame, depth = sys._getframe(6), 6
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)


# 기본 설정 적용 (import 시)
setup_logging()
