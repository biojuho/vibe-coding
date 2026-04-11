from __future__ import annotations

import random
import time
from collections.abc import Callable
from concurrent.futures import Executor, Future
from threading import Lock, Timer
from typing import TypeVar

T = TypeVar("T")


def _validate_retry_args(
    max_attempts: int,
    base_delay_sec: float,
    max_delay_sec: float,
    jitter_ratio: float,
) -> None:
    if max_attempts <= 0:
        raise ValueError("max_attempts must be > 0.")
    if base_delay_sec < 0 or max_delay_sec < 0:
        raise ValueError("delay values must be >= 0.")
    if jitter_ratio < 0:
        raise ValueError("jitter_ratio must be >= 0.")


def _compute_backoff_delay(
    attempt: int,
    *,
    base_delay_sec: float,
    max_delay_sec: float,
    jitter_ratio: float,
) -> float:
    delay = min(max_delay_sec, base_delay_sec * (2 ** (attempt - 1)))
    jitter = delay * jitter_ratio * random.random()
    return delay + jitter


def retry_with_backoff(
    fn: Callable[[], T],
    max_attempts: int,
    base_delay_sec: float = 1.0,
    max_delay_sec: float = 12.0,
    jitter_ratio: float = 0.15,
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, float, BaseException], None] | None = None,
) -> T:
    _validate_retry_args(max_attempts, base_delay_sec, max_delay_sec, jitter_ratio)

    attempt = 1
    while True:
        try:
            return fn()
        except retry_exceptions as exc:
            if attempt >= max_attempts:
                raise
            sleep_sec = _compute_backoff_delay(
                attempt,
                base_delay_sec=base_delay_sec,
                max_delay_sec=max_delay_sec,
                jitter_ratio=jitter_ratio,
            )
            if on_retry is not None:
                on_retry(attempt, sleep_sec, exc)
            time.sleep(sleep_sec)
            attempt += 1


def submit_retry_with_backoff(
    executor: Executor,
    fn: Callable[[], T],
    max_attempts: int,
    base_delay_sec: float = 1.0,
    max_delay_sec: float = 12.0,
    jitter_ratio: float = 0.15,
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, float, BaseException], None] | None = None,
) -> Future[T]:
    """Submit retried work without parking an executor worker during backoff."""
    _validate_retry_args(max_attempts, base_delay_sec, max_delay_sec, jitter_ratio)

    result_future: Future[T] = Future()
    active_timers: set[Timer] = set()
    timers_lock = Lock()

    def _cancel_pending_timers(*, exclude: Timer | None = None) -> None:
        with timers_lock:
            timers = [timer for timer in active_timers if timer is not exclude]
            if exclude is None:
                active_timers.clear()
            else:
                active_timers.clear()
                active_timers.add(exclude)
        for timer in timers:
            timer.cancel()

    def _forget_timer(timer: Timer) -> None:
        with timers_lock:
            active_timers.discard(timer)

    def _set_result(value: T) -> None:
        if result_future.done():
            return
        result_future.set_result(value)
        _cancel_pending_timers()

    def _set_exception(exc: BaseException) -> None:
        if result_future.done():
            return
        if isinstance(exc, Exception):
            result_future.set_exception(exc)
        else:
            result_future.set_exception(RuntimeError(f"Unhandled base exception: {exc!r}"))
        _cancel_pending_timers()

    def _submit_attempt(attempt: int) -> None:
        if result_future.done():
            return
        try:
            attempt_future = executor.submit(fn)
        except Exception as exc:
            _set_exception(exc)
            return

        def _handle_attempt_done(inner_future: Future[T]) -> None:
            if result_future.done():
                return
            try:
                value = inner_future.result()
            except retry_exceptions as exc:
                if attempt >= max_attempts:
                    _set_exception(exc)
                    return
                sleep_sec = _compute_backoff_delay(
                    attempt,
                    base_delay_sec=base_delay_sec,
                    max_delay_sec=max_delay_sec,
                    jitter_ratio=jitter_ratio,
                )
                if on_retry is not None:
                    on_retry(attempt, sleep_sec, exc)

                retry_timer: Timer | None = None

                def _resubmit() -> None:
                    if retry_timer is not None:
                        _forget_timer(retry_timer)
                    _submit_attempt(attempt + 1)

                retry_timer = Timer(sleep_sec, _resubmit)
                retry_timer.daemon = True
                with timers_lock:
                    active_timers.add(retry_timer)
                retry_timer.start()
            except Exception as exc:
                _set_exception(exc)
            else:
                _set_result(value)

        attempt_future.add_done_callback(_handle_attempt_done)

    result_future.add_done_callback(lambda _future: _cancel_pending_timers())
    _submit_attempt(1)
    return result_future
