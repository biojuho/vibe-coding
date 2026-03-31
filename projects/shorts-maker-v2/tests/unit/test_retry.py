from __future__ import annotations

import pytest

from shorts_maker_v2.utils.retry import retry_with_backoff


def test_retry_succeeds_after_failures() -> None:
    state = {"count": 0}

    def flaky() -> int:
        state["count"] += 1
        if state["count"] < 3:
            raise RuntimeError("temporary")
        return 42

    result = retry_with_backoff(
        flaky,
        max_attempts=3,
        base_delay_sec=0,
        max_delay_sec=0,
        jitter_ratio=0,
    )
    assert result == 42
    assert state["count"] == 3


def test_retry_raises_after_max_attempts() -> None:
    def always_fail() -> int:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        retry_with_backoff(
            always_fail,
            max_attempts=2,
            base_delay_sec=0,
            max_delay_sec=0,
            jitter_ratio=0,
        )
