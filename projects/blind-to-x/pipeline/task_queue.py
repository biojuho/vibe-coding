"""Task queue abstraction for blind-to-x pipeline — 100x scale.

Provides a pluggable task queue that replaces asyncio.Semaphore-based
concurrency control with distributed worker capabilities.

Architecture:
    BTX_TASK_QUEUE=local   → asyncio.Semaphore (기존, 기본값 — 단일 프로세스)
    BTX_TASK_QUEUE=celery  → Celery + Redis broker (분산 워커)

The pipeline code calls `enqueue_posts()` and the queue handles routing.
Celery mode requires:
    pip install celery[redis]
    BTX_REDIS_URL=redis://localhost:6379/0

Usage (in main.py or scheduler):
    from pipeline.task_queue import get_task_queue
    queue = get_task_queue()
    results = await queue.process_batch(items, worker_fn, max_parallel=3)
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Protocol, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class TaskQueue(Protocol):
    """Task queue interface for pipeline batch processing."""

    async def process_batch(
        self,
        items: list[dict[str, Any]],
        worker_fn: Callable[[dict[str, Any]], Coroutine[Any, Any, T]],
        max_parallel: int = 3,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[T]:
        """Process a batch of items with controlled concurrency.

        Args:
            items: List of work items (e.g., URLs to process).
            worker_fn: Async function that processes a single item.
            max_parallel: Maximum concurrent workers.
            on_progress: Optional callback(completed, total) for progress tracking.

        Returns:
            List of results in the same order as items.
        """
        ...


class LocalSemaphoreQueue:
    """In-process task queue using asyncio.Semaphore.

    This is the current behavior — direct replacement for the existing
    semaphore pattern in main.py, but extracted into a reusable abstraction.
    """

    async def process_batch(
        self,
        items: list[dict[str, Any]],
        worker_fn: Callable[[dict[str, Any]], Coroutine[Any, Any, Any]],
        max_parallel: int = 3,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list:
        if not items:
            return []

        semaphore = asyncio.Semaphore(max(1, max_parallel))
        counter = {"done": 0}
        counter_lock = asyncio.Lock()
        total = len(items)

        async def _bounded(item: dict) -> Any:
            async with semaphore:
                result = await worker_fn(item)
                async with counter_lock:
                    counter["done"] += 1
                    if on_progress:
                        on_progress(counter["done"], total)
                return result

        results = await asyncio.gather(
            *[_bounded(item) for item in items],
            return_exceptions=True,
        )

        # Log exceptions but don't crash
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.warning(
                    "TaskQueue: item %d/%d failed: %s",
                    i + 1,
                    total,
                    r,
                )
                results[i] = None

        return results


class CeleryTaskQueue:
    """Distributed task queue using Celery + Redis.

    When enabled, tasks are enqueued to a Celery broker and processed
    by distributed workers. This allows horizontal scaling beyond a
    single process's asyncio event loop.

    Configuration:
        BTX_REDIS_URL: Redis connection URL for the broker
        BTX_CELERY_RESULT_BACKEND: Result backend URL (defaults to same Redis)
        BTX_CELERY_TASK_TIMEOUT: Max seconds per task (default: 600)

    Note: The actual worker processes must be started separately:
        celery -A pipeline.celery_app worker --concurrency=4
    """

    def __init__(self):
        self._redis_url = os.environ.get("BTX_REDIS_URL", "redis://localhost:6379/0")
        self._task_timeout = int(os.environ.get("BTX_CELERY_TASK_TIMEOUT", "600"))
        self._celery = None
        self._init_celery()

    def _init_celery(self) -> None:
        """Lazily initialize Celery app."""
        try:
            from celery import Celery

            self._celery = Celery(
                "btx_pipeline",
                broker=self._redis_url,
                backend=os.environ.get("BTX_CELERY_RESULT_BACKEND", self._redis_url),
            )
            self._celery.conf.update(
                task_serializer="json",
                result_serializer="json",
                accept_content=["json"],
                task_soft_time_limit=self._task_timeout,
                task_time_limit=self._task_timeout + 60,
                worker_max_tasks_per_child=100,  # 메모리 누수 방지
                worker_prefetch_multiplier=1,  # 공정한 분배
                task_acks_late=True,  # 실패 시 재시도 가능
                task_reject_on_worker_lost=True,
            )
            logger.info(
                "CeleryTaskQueue initialized: broker=%s timeout=%ds",
                self._redis_url,
                self._task_timeout,
            )
        except ImportError:
            logger.error("Celery is not installed. Run: pip install celery[redis]")
            raise

    async def process_batch(
        self,
        items: list[dict[str, Any]],
        worker_fn: Callable[[dict[str, Any]], Coroutine[Any, Any, Any]],
        max_parallel: int = 3,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list:
        """Dispatch items to Celery workers and collect results.

        In Celery mode, the worker_fn is serialized as a task name and
        items are dispatched via group() for controlled parallelism.
        Results are collected asynchronously from the result backend.

        Note: For this to work, worker_fn must be a registered Celery task.
        If not, falls back to local semaphore execution with a warning.
        """
        if not items:
            return []

        if self._celery is None:
            logger.warning("Celery not initialized, falling back to local execution")
            local = LocalSemaphoreQueue()
            return await local.process_batch(items, worker_fn, max_parallel, on_progress)

        # 실제 Celery 분산 실행
        try:
            from celery import group

            # worker_fn의 task name을 검색
            task_name = getattr(worker_fn, "name", None)
            if not task_name:
                # worker_fn이 Celery 태스크가 아니면 로컬 실행으로 폴백
                logger.info(
                    "worker_fn is not a Celery task, using local semaphore "
                    "(register with @celery_app.task for distributed execution)"
                )
                local = LocalSemaphoreQueue()
                return await local.process_batch(items, worker_fn, max_parallel, on_progress)

            # Celery group으로 병렬 디스패치
            job = group(self._celery.signature(task_name, args=(item,)) for item in items)

            # Apply async and wait for results
            result_group = job.apply_async()

            # Polling loop for progress tracking
            asyncio.get_event_loop()
            total = len(items)

            async def _poll_results():
                """Poll Celery result backend until all tasks complete."""
                while not result_group.ready():
                    await asyncio.sleep(1.0)
                    if on_progress:
                        completed = result_group.completed_count()
                        on_progress(completed, total)
                return result_group.get(
                    timeout=self._task_timeout,
                    propagate=False,
                )

            try:
                results = await asyncio.wait_for(
                    _poll_results(),
                    timeout=self._task_timeout + 5,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Celery result polling timed out after %ds for %d tasks; "
                    "revoking outstanding tasks and marking the batch failed.",
                    self._task_timeout + 5,
                    total,
                )
                try:
                    result_group.revoke(terminate=False)
                except Exception as revoke_exc:
                    logger.debug("Celery revoke after polling timeout failed: %s", revoke_exc)
                try:
                    result_group.forget()
                except Exception as forget_exc:
                    logger.debug("Celery forget after polling timeout failed: %s", forget_exc)
                return [None] * total

            # Handle individual task failures
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.warning("CeleryQueue: task %d/%d failed: %s", i + 1, total, r)
                    results[i] = None

            return results

        except Exception as exc:
            logger.warning("Celery dispatch failed, falling back to local: %s", exc)
            local = LocalSemaphoreQueue()
            return await local.process_batch(items, worker_fn, max_parallel, on_progress)


@dataclass
class TaskQueueConfig:
    """Configuration for task queue selection."""

    backend: str = "local"  # "local" or "celery"
    redis_url: str = ""
    max_parallel: int = 3
    task_timeout: int = 600


_queue_singleton: TaskQueue | None = None


def get_task_queue(config: TaskQueueConfig | None = None) -> TaskQueue:
    """Factory: get the task queue singleton based on env/config.

    Env vars:
        BTX_TASK_QUEUE=local   → LocalSemaphoreQueue (기본값)
        BTX_TASK_QUEUE=celery  → CeleryTaskQueue
    """
    global _queue_singleton
    if _queue_singleton is not None:
        return _queue_singleton

    backend = os.environ.get("BTX_TASK_QUEUE", "local").lower()
    if config:
        backend = config.backend

    if backend == "celery":
        try:
            _queue_singleton = CeleryTaskQueue()
            logger.info("TaskQueue: Celery 분산 큐 활성화")
        except Exception as exc:
            logger.warning("TaskQueue: Celery 초기화 실패, 로컬 폴백: %s", exc)
            _queue_singleton = LocalSemaphoreQueue()
    else:
        _queue_singleton = LocalSemaphoreQueue()

    return _queue_singleton


def _reset_singleton() -> None:
    """테스트 격리를 위한 싱글톤 리셋. 프로덕션에서는 사용하지 마세요.

    # [QA 수정] A-7: 테스트에서 싱글톤 상태 격리 가능하도록 추가
    """
    global _queue_singleton
    _queue_singleton = None
