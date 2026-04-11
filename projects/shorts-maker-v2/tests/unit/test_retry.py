from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from shorts_maker_v2.utils.retry import retry_with_backoff, submit_retry_with_backoff


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


def test_submit_retry_with_backoff_succeeds_after_failures() -> None:
    state = {"count": 0}

    def flaky() -> int:
        state["count"] += 1
        if state["count"] < 3:
            raise RuntimeError("temporary")
        return 42

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = submit_retry_with_backoff(
            executor,
            flaky,
            max_attempts=3,
            base_delay_sec=0,
            max_delay_sec=0,
            jitter_ratio=0,
        )
        assert future.result(timeout=1) == 42

    assert state["count"] == 3


def test_submit_retry_with_backoff_releases_worker_between_retries() -> None:
    first_attempt_failed = Event()
    second_attempt_can_finish = Event()
    quick_task_started = Event()
    state = {"count": 0}

    def flaky() -> str:
        state["count"] += 1
        if state["count"] == 1:
            first_attempt_failed.set()
            raise RuntimeError("temporary")
        second_attempt_can_finish.wait(timeout=1)
        return "done"

    def quick_task() -> str:
        quick_task_started.set()
        return "side-task"

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = submit_retry_with_backoff(
            executor,
            flaky,
            max_attempts=2,
            base_delay_sec=0.25,
            max_delay_sec=0.25,
            jitter_ratio=0,
        )

        assert first_attempt_failed.wait(timeout=1)
        quick_future = executor.submit(quick_task)

        assert quick_task_started.wait(timeout=0.1)
        assert quick_future.result(timeout=1) == "side-task"

        second_attempt_can_finish.set()
        assert future.result(timeout=1) == "done"
