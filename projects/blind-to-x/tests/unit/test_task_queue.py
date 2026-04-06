from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock

import pytest

from pipeline import task_queue


@pytest.fixture(autouse=True)
def reset_task_queue_singleton():
    task_queue._reset_singleton()
    yield
    task_queue._reset_singleton()


@pytest.mark.asyncio
async def test_local_semaphore_queue_preserves_input_order_and_reports_progress():
    queue = task_queue.LocalSemaphoreQueue()
    progress_updates: list[tuple[int, int]] = []
    state = {"running": 0, "peak": 0}

    async def worker(item: dict[str, int]) -> int:
        state["running"] += 1
        state["peak"] = max(state["peak"], state["running"])
        try:
            await asyncio.sleep(0.03 - (item["id"] * 0.01))
            return item["id"] * 10
        finally:
            state["running"] -= 1

    results = await queue.process_batch(
        [{"id": 1}, {"id": 2}, {"id": 3}],
        worker,
        max_parallel=2,
        on_progress=lambda done, total: progress_updates.append((done, total)),
    )

    assert results == [10, 20, 30]
    assert progress_updates == [(1, 3), (2, 3), (3, 3)]
    assert state["peak"] <= 2


@pytest.mark.asyncio
async def test_local_semaphore_queue_replaces_failures_with_none(caplog: pytest.LogCaptureFixture):
    queue = task_queue.LocalSemaphoreQueue()

    async def worker(item: dict[str, int]) -> int:
        if item["id"] == 2:
            raise RuntimeError("boom")
        return item["id"] * 10

    with caplog.at_level("WARNING"):
        results = await queue.process_batch(
            [{"id": 1}, {"id": 2}, {"id": 3}],
            worker,
            max_parallel=0,
        )

    assert results == [10, None, 30]
    assert "TaskQueue: item 2/3 failed: boom" in caplog.text


@pytest.mark.asyncio
async def test_celery_task_queue_falls_back_to_local_for_non_task_workers(monkeypatch: pytest.MonkeyPatch):
    celery_module = types.ModuleType("celery")
    celery_module.group = lambda *args, **kwargs: None
    celery_module.chord = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "celery", celery_module)

    queue = task_queue.CeleryTaskQueue.__new__(task_queue.CeleryTaskQueue)
    queue._celery = types.SimpleNamespace(signature=lambda *args, **kwargs: None)
    queue._task_timeout = 10

    local_process = AsyncMock(return_value=["local-result"])
    monkeypatch.setattr(task_queue.LocalSemaphoreQueue, "process_batch", local_process)

    async def worker(item: dict[str, str]) -> str:
        return item["value"]

    results = await queue.process_batch([{"value": "x"}], worker, max_parallel=4)

    assert results == ["local-result"]
    local_process.assert_awaited_once()


@pytest.mark.asyncio
async def test_celery_task_queue_times_out_stalled_groups_without_local_replay(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    class FakeResultGroup:
        def __init__(self) -> None:
            self.revoked = False
            self.forgotten = False

        def ready(self) -> bool:
            return False

        def completed_count(self) -> int:
            return 0

        def get(self, timeout: int, propagate: bool) -> list[str]:
            raise AssertionError("get() should not be called when polling times out")

        def revoke(self, terminate: bool = False) -> None:
            self.revoked = True

        def forget(self) -> None:
            self.forgotten = True

    class FakeJob:
        def __init__(self, result_group: FakeResultGroup) -> None:
            self._result_group = result_group

        def apply_async(self) -> FakeResultGroup:
            return self._result_group

    fake_result_group = FakeResultGroup()
    celery_module = types.ModuleType("celery")
    celery_module.group = lambda *args, **kwargs: FakeJob(fake_result_group)
    celery_module.chord = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "celery", celery_module)

    async def fake_wait_for(awaitable, timeout):
        awaitable.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(task_queue.asyncio, "wait_for", fake_wait_for)

    queue = task_queue.CeleryTaskQueue.__new__(task_queue.CeleryTaskQueue)
    queue._celery = types.SimpleNamespace(signature=lambda *args, **kwargs: None)
    queue._task_timeout = 10

    async def worker(item: dict[str, str]) -> str:
        return item["value"]

    worker.name = "pipeline.fake_task"

    local_process = AsyncMock(return_value=["should-not-run"])
    monkeypatch.setattr(task_queue.LocalSemaphoreQueue, "process_batch", local_process)

    with caplog.at_level("WARNING"):
        results = await queue.process_batch([{"value": "x"}, {"value": "y"}], worker, max_parallel=2)

    assert results == [None, None]
    assert fake_result_group.revoked is True
    assert fake_result_group.forgotten is True
    assert "Celery result polling timed out" in caplog.text
    local_process.assert_not_awaited()


def test_get_task_queue_falls_back_to_local_when_celery_init_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BTX_TASK_QUEUE", "celery")

    def raise_on_init(self) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(task_queue.CeleryTaskQueue, "__init__", raise_on_init)

    queue = task_queue.get_task_queue()

    assert isinstance(queue, task_queue.LocalSemaphoreQueue)
    assert task_queue.get_task_queue() is queue
