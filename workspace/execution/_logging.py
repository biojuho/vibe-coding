"""Central logging setup for execution scripts.

Prefers loguru when available, but falls back to stdlib logging so tests and
fresh environments do not fail during import.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

try:
    from loguru import logger as _loguru_logger
except ModuleNotFoundError:
    _loguru_logger = None

_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _ROOT / ".tmp" / "logs"
_CONFIGURED = False

if _loguru_logger is not None:
    logger: Any = _loguru_logger
else:
    logger = logging.getLogger("execution")


def _setup_stdlib_logging(*, console_level: str, file_level: str) -> None:
    """Configure a minimal stdlib fallback logger."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    console_handler.setFormatter(logging.Formatter("%(levelname)-8s | %(name)s:%(funcName)s | %(message)s"))

    file_handler = logging.FileHandler(
        _LOG_DIR / "execution_fallback.log",
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s")
    )

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    logger.propagate = True


def setup_logging(
    *,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    rotation: str = "1 day",
    retention: str = "7 days",
    max_size: str = "500 MB",
) -> None:
    """Configure logging once for execution scripts."""
    del max_size

    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    _CONFIGURED = True

    if _loguru_logger is None:
        _setup_stdlib_logging(console_level=console_level, file_level=file_level)
        logger.warning("loguru is not installed; using stdlib logging fallback")
        return

    logger.remove()

    logger.add(
        sys.stderr,
        level=console_level,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | {message}",
        colorize=True,
    )

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(_LOG_DIR / "execution_{time:YYYY-MM-DD}.jsonl"),
        level=file_level,
        format="{message}",
        serialize=True,
        rotation=rotation,
        retention=retention,
        compression="gz",
        encoding="utf-8",
    )

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


setup_logging()
