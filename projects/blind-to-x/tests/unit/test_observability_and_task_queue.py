"""Tests for pipeline.observability and pipeline.task_queue (T-130).

Covers the no-op fallback paths that activate when optional dependencies
(opentelemetry, celery) are absent, plus the LocalSemaphoreQueue logic
and get_task_queue singleton factory.
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# pipeline.observability
# ---------------------------------------------------------------------------


import pipeline.observability as obs_mod


class TestNoopSpan:
    def test_set_attribute_noop(self):
        span = obs_mod._NoopSpan()
        span.set_attribute("key", "value")  # must not raise

    def test_set_status_noop(self):
        span = obs_mod._NoopSpan()
        span.set_status("ok")

    def test_record_exception_noop(self):
        span = obs_mod._NoopSpan()
        span.record_exception(ValueError("boom"))

    def test_add_event_noop(self):
        span = obs_mod._NoopSpan()
        span.add_event("my_event", {"k": "v"})
        span.add_event("bare_event")

    def test_context_manager(self):
        span = obs_mod._NoopSpan()
        with span as s:
            assert s is span


class TestNoopTracer:
    def test_start_as_current_span_context_manager(self):
        tracer = obs_mod._NoopTracer()
        with tracer.start_as_current_span("my_span") as span:
            assert isinstance(span, obs_mod._NoopSpan)

    def test_start_span_returns_noop(self):
        tracer = obs_mod._NoopTracer()
        span = tracer.start_span("some_span")
        assert isinstance(span, obs_mod._NoopSpan)

    def test_start_as_current_span_with_kwargs(self):
        tracer = obs_mod._NoopTracer()
        with tracer.start_as_current_span("x", kind="client") as span:
            span.set_attribute("url", "http://test")


class TestNoopInstrument:
    def test_add_noop(self):
        inst = obs_mod._NoopInstrument()
        inst.add(1, {"tag": "val"})
        inst.add(5)

    def test_record_noop(self):
        inst = obs_mod._NoopInstrument()
        inst.record(99.5, {"label": "x"})
        inst.record(0)


class TestNoopMeter:
    def test_create_counter(self):
        meter = obs_mod._NoopMeter()
        counter = meter.create_counter("my.counter", description="test")
        assert isinstance(counter, obs_mod._NoopInstrument)

    def test_create_histogram(self):
        meter = obs_mod._NoopMeter()
        hist = meter.create_histogram("my.hist")
        assert isinstance(hist, obs_mod._NoopInstrument)

    def test_create_up_down_counter(self):
        meter = obs_mod._NoopMeter()
        udc = meter.create_up_down_counter("my.udc")
        assert isinstance(udc, obs_mod._NoopInstrument)


class TestPipelineMetrics:
    def setup_method(self):
        self.metrics = obs_mod.PipelineMetrics(obs_mod._NoopMeter())

    def test_record_api_call_full(self):
        self.metrics.record_api_call("gemini", tokens=1000, latency_ms=200.5, cost_usd=0.01, success=True)

    def test_record_api_call_failure(self):
        self.metrics.record_api_call("openai", success=False)

    def test_record_api_call_defaults(self):
        self.metrics.record_api_call("groq")

    def test_record_image_generation(self):
        self.metrics.record_image_generation("gemini", count=3)

    def test_record_pipeline_run_full(self):
        self.metrics.record_pipeline_run(posts_processed=5, posts_published=3, duration_s=45.2, source="blind")

    def test_record_pipeline_run_defaults(self):
        self.metrics.record_pipeline_run()

    def test_record_post_time(self):
        self.metrics.record_post_time("blind", 1.23)


class TestIsAsync:
    def test_async_function(self):
        async def my_fn():
            pass

        assert obs_mod._is_async(my_fn) is True

    def test_sync_function(self):
        def my_fn():
            pass

        assert obs_mod._is_async(my_fn) is False


class TestTracedDecorator:
    def test_sync_function_decorated(self):
        @obs_mod.traced("test_span")
        def add(a, b):
            return a + b

        assert add(1, 2) == 3

    def test_sync_function_no_name(self):
        @obs_mod.traced()
        def multiply(a, b):
            return a * b

        assert multiply(3, 4) == 12

    def test_sync_exception_propagates(self):
        @obs_mod.traced("fail_span")
        def boom():
            raise ValueError("expected error")

        with pytest.raises(ValueError, match="expected error"):
            boom()

    def test_async_function_decorated(self):
        @obs_mod.traced("async_span")
        async def fetch(url):
            return f"got:{url}"

        result = asyncio.run(fetch("http://x"))
        assert result == "got:http://x"

    def test_async_exception_propagates(self):
        @obs_mod.traced("async_fail")
        async def async_boom():
            raise RuntimeError("async error")

        with pytest.raises(RuntimeError, match="async error"):
            asyncio.run(async_boom())


class TestTimedSpan:
    def test_timed_span_runs(self):
        with obs_mod.timed_span("test_op", {"env": "unit"}) as span:
            assert span is not None

    def test_timed_span_no_attributes(self):
        with obs_mod.timed_span("bare_op"):
            pass  # should not raise

    def test_timed_span_sets_duration(self):
        # _NoopSpan.set_attribute is a no-op; just ensure no error raised
        with obs_mod.timed_span("timed") as span:
            span.set_attribute("work_done", True)


class TestInitFunctions:
    def test_init_otel_tracer_import_error_returns_noop(self):
        with patch.dict(
            sys.modules,
            {
                "opentelemetry": None,
                "opentelemetry.trace": None,
            },
        ):
            result = obs_mod._init_otel_tracer()
        assert isinstance(result, obs_mod._NoopTracer)

    def test_init_otel_meter_import_error_returns_noop(self):
        with patch.dict(
            sys.modules,
            {
                "opentelemetry": None,
                "opentelemetry.metrics": None,
            },
        ):
            result = obs_mod._init_otel_meter()
        assert isinstance(result, obs_mod._NoopMeter)

    def test_module_level_tracer_accessible(self):
        assert obs_mod.tracer is not None

    def test_module_level_metrics_accessible(self):
        assert obs_mod.metrics is not None
        assert isinstance(obs_mod.metrics, obs_mod.PipelineMetrics)


# ---------------------------------------------------------------------------
# pipeline.task_queue
# ---------------------------------------------------------------------------


import pipeline.task_queue as tq_mod


@pytest.fixture(autouse=True)
def reset_task_queue_singleton():
    """각 테스트 후 싱글톤 초기화."""
    tq_mod._reset_singleton()
    yield
    tq_mod._reset_singleton()


class TestLocalSemaphoreQueue:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_empty_items_returns_empty(self):
        q = tq_mod.LocalSemaphoreQueue()
        result = self._run(q.process_batch([], worker_fn=None, max_parallel=3))
        assert result == []

    def test_normal_batch(self):
        q = tq_mod.LocalSemaphoreQueue()

        async def worker(item):
            return item["val"] * 2

        items = [{"val": i} for i in range(5)]
        results = self._run(q.process_batch(items, worker, max_parallel=2))
        assert results == [0, 2, 4, 6, 8]

    def test_exception_in_worker_returns_none(self):
        q = tq_mod.LocalSemaphoreQueue()

        async def failing_worker(item):
            if item["id"] == 2:
                raise ValueError("bad item")
            return item["id"]

        items = [{"id": i} for i in range(4)]
        results = self._run(q.process_batch(items, failing_worker, max_parallel=2))
        # Failed item becomes None, others return normally
        assert results[2] is None
        assert results[0] == 0
        assert results[1] == 1
        assert results[3] == 3

    def test_progress_callback_called(self):
        q = tq_mod.LocalSemaphoreQueue()
        calls = []

        async def worker(item):
            return item

        def on_progress(done, total):
            calls.append((done, total))

        items = [{"x": i} for i in range(3)]
        self._run(q.process_batch(items, worker, max_parallel=1, on_progress=on_progress))
        assert len(calls) == 3
        assert calls[-1] == (3, 3)

    def test_max_parallel_zero_clamped_to_one(self):
        q = tq_mod.LocalSemaphoreQueue()

        async def worker(item):
            return item["n"]

        results = self._run(q.process_batch([{"n": 42}], worker, max_parallel=0))
        assert results == [42]


class TestGetTaskQueue:
    def test_default_returns_local_semaphore(self, monkeypatch):
        monkeypatch.delenv("BTX_TASK_QUEUE", raising=False)
        queue = tq_mod.get_task_queue()
        assert isinstance(queue, tq_mod.LocalSemaphoreQueue)

    def test_singleton_same_instance(self, monkeypatch):
        monkeypatch.delenv("BTX_TASK_QUEUE", raising=False)
        first = tq_mod.get_task_queue()
        second = tq_mod.get_task_queue()
        assert first is second

    def test_celery_env_unavailable_falls_back_to_local(self, monkeypatch):
        monkeypatch.setenv("BTX_TASK_QUEUE", "celery")
        # celery not installed in CI → factory should catch ImportError and fall back
        with patch.dict(sys.modules, {"celery": None}):
            queue = tq_mod.get_task_queue()
        assert isinstance(queue, tq_mod.LocalSemaphoreQueue)

    def test_explicit_config_local(self):
        cfg = tq_mod.TaskQueueConfig(backend="local")
        queue = tq_mod.get_task_queue(config=cfg)
        assert isinstance(queue, tq_mod.LocalSemaphoreQueue)

    def test_reset_singleton_clears(self, monkeypatch):
        monkeypatch.delenv("BTX_TASK_QUEUE", raising=False)
        tq_mod.get_task_queue()
        tq_mod._reset_singleton()
        q2 = tq_mod.get_task_queue()
        # After reset, a new instance is created (may or may not be same type)
        assert isinstance(q2, tq_mod.LocalSemaphoreQueue)


class TestTaskQueueConfig:
    def test_defaults(self):
        cfg = tq_mod.TaskQueueConfig()
        assert cfg.backend == "local"
        assert cfg.max_parallel == 3
        assert cfg.task_timeout == 600

    def test_custom_values(self):
        cfg = tq_mod.TaskQueueConfig(backend="celery", max_parallel=10)
        assert cfg.backend == "celery"
        assert cfg.max_parallel == 10


class TestCeleryQueueFallback:
    """CeleryTaskQueue.process_batch falls back to local when celery is None."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_fallback_when_celery_none(self):
        q = tq_mod.CeleryTaskQueue.__new__(tq_mod.CeleryTaskQueue)
        q._celery = None  # simulate uninitialized celery
        q._task_timeout = 60

        async def worker(item):
            return item["v"]

        results = self._run(q.process_batch([{"v": 1}, {"v": 2}], worker, max_parallel=2))
        assert results == [1, 2]

    def test_fallback_when_worker_not_celery_task(self):
        """worker_fn without .name attr triggers local fallback."""
        q = tq_mod.CeleryTaskQueue.__new__(tq_mod.CeleryTaskQueue)
        # Provide a mock celery but worker_fn won't have .name
        mock_celery = MagicMock()
        q._celery = mock_celery
        q._task_timeout = 60

        async def worker(item):
            return item["v"] + 10

        results = self._run(q.process_batch([{"v": 5}], worker, max_parallel=1))
        assert results == [15]
