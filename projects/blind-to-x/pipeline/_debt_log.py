"""Observable degradation helper for silent-failure fallbacks.

Tech debt review (2026-04-15) identified 13 sites in blind-to-x where
``except Exception: pass`` (or equivalent) swallowed errors with no log,
making production incidents unreproducible. This module provides a single
``swallowed`` helper that converts those sites into WARNING-level log
entries without changing control flow.

Usage:
    from pipeline._debt_log import swallowed

    try:
        return risky_operation()
    except Exception as exc:
        swallowed("component.op", exc, fallback="default_value")
        return "default_value"

All events land under the ``btx.silent_fallback`` logger so downstream
health checks and alerting can aggregate them as a single signal.
"""

from __future__ import annotations

import logging

_logger = logging.getLogger("btx.silent_fallback")


def swallowed(
    component: str,
    exc: BaseException,
    *,
    fallback: str = "",
    action: str = "",
) -> None:
    """Log a swallowed exception without re-raising.

    Args:
        component: Dotted identifier ``"module.function"`` or similar so
            log filters can target specific sites.
        exc: The caught exception. Only the type name and stringified
            message are logged — full traceback is attached via
            ``exc_info`` for DEBUG-level consumers.
        fallback: Short description of what value/path is returned
            instead. Helps operators spot degraded output.
        action: Optional supplementary note ("using cached value",
            "retry scheduled", ...). Empty by default.
    """
    _logger.warning(
        "silent-fallback component=%s err=%s:%s fallback=%s action=%s",
        component,
        type(exc).__name__,
        exc,
        fallback,
        action,
        exc_info=exc,
    )
