from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_with_backoff(
    fn: Callable[[], T],
    max_attempts: int,
    base_delay_sec: float = 1.0,
    max_delay_sec: float = 12.0,
    jitter_ratio: float = 0.15,
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, float, BaseException], None] | None = None,
) -> T:
    if max_attempts <= 0:
        raise ValueError("max_attempts must be > 0.")
    if base_delay_sec < 0 or max_delay_sec < 0:
        raise ValueError("delay values must be >= 0.")
    if jitter_ratio < 0:
        raise ValueError("jitter_ratio must be >= 0.")

    attempt = 1
    while True:
        try:
            return fn()
        except retry_exceptions as exc:
            if attempt >= max_attempts:
                raise
            delay = min(max_delay_sec, base_delay_sec * (2 ** (attempt - 1)))
            jitter = delay * jitter_ratio * random.random()
            sleep_sec = delay + jitter
            if on_retry is not None:
                on_retry(attempt, sleep_sec, exc)
            time.sleep(sleep_sec)
            attempt += 1
