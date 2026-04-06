"""OpenTelemetry instrumentation for blind-to-x pipeline — observability layer.

Provides structured tracing, metrics, and logging for production monitoring.
Activated via environment variable:
    BTX_OTEL_ENABLED=true

Configuration:
    BTX_OTEL_ENDPOINT:   OTLP exporter endpoint (default: http://localhost:4317)
    BTX_OTEL_SERVICE:    Service name (default: btx-pipeline)
    BTX_OTEL_EXPORTER:   Exporter type: "otlp" | "console" | "none" (default: otlp)

Requirements (install when deploying):
    pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

Usage:
    from pipeline.observability import tracer, metrics, track_pipeline_run

    # 자동 span 생성
    with tracer.start_as_current_span("scrape_blind") as span:
        span.set_attribute("source", "blind")
        ...

    # 메트릭 기록
    metrics.record_api_call("gemini", tokens=1500, latency_ms=320)
    metrics.record_pipeline_run(posts_processed=5, duration_s=45.2)

If OpenTelemetry is not installed, all instrumentation is no-op (zero overhead).
"""

from __future__ import annotations

import logging
import os
import inspect
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

_OTEL_ENABLED = os.environ.get("BTX_OTEL_ENABLED", "").lower() in ("true", "1", "yes")
_OTEL_ENDPOINT = os.environ.get("BTX_OTEL_ENDPOINT", "http://localhost:4317")
_OTEL_SERVICE = os.environ.get("BTX_OTEL_SERVICE", "btx-pipeline")
_OTEL_EXPORTER = os.environ.get("BTX_OTEL_EXPORTER", "otlp").lower()


# ── No-op fallback (zero overhead when OTEL disabled) ──────────────────


class _NoopSpan:
    """No-op span for when OpenTelemetry is not available."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exc: Exception) -> None:
        pass

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _NoopTracer:
    """No-op tracer — transparently replaces OTel tracer when disabled."""

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs):
        yield _NoopSpan()

    def start_span(self, name: str, **kwargs):
        return _NoopSpan()


class _NoopMeter:
    """No-op meter — transparently replaces OTel meter when disabled."""

    def create_counter(self, name: str, **kwargs):
        return _NoopInstrument()

    def create_histogram(self, name: str, **kwargs):
        return _NoopInstrument()

    def create_up_down_counter(self, name: str, **kwargs):
        return _NoopInstrument()


class _NoopInstrument:
    """No-op instrument for counters/histograms."""

    def add(self, value: float, attributes: dict | None = None) -> None:
        pass

    def record(self, value: float, attributes: dict | None = None) -> None:
        pass


# ── Real OTel initialization ───────────────────────────────────────────


def _init_otel_tracer():
    """Initialize OpenTelemetry tracer with OTLP exporter."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": _OTEL_SERVICE})
        provider = TracerProvider(resource=resource)

        if _OTEL_EXPORTER == "otlp":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter(endpoint=_OTEL_ENDPOINT)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        elif _OTEL_EXPORTER == "console":
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)
        return trace.get_tracer(_OTEL_SERVICE)

    except ImportError:
        logger.debug("OpenTelemetry SDK not installed, using no-op tracer")
        return _NoopTracer()
    except Exception as exc:
        logger.warning("OTEL tracer init failed: %s", exc)
        return _NoopTracer()


def _init_otel_meter():
    """Initialize OpenTelemetry meter with OTLP exporter."""
    try:
        from opentelemetry import metrics as otel_metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": _OTEL_SERVICE})
        provider = MeterProvider(resource=resource)

        if _OTEL_EXPORTER == "otlp":
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=_OTEL_ENDPOINT),
                export_interval_millis=30000,  # 30초
            )
            provider = MeterProvider(resource=resource, metric_readers=[reader])
        elif _OTEL_EXPORTER == "console":
            from opentelemetry.sdk.metrics.export import (
                ConsoleMetricExporter,
                PeriodicExportingMetricReader,
            )

            reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=10000,
            )
            provider = MeterProvider(resource=resource, metric_readers=[reader])

        otel_metrics.set_meter_provider(provider)
        return otel_metrics.get_meter(_OTEL_SERVICE)

    except ImportError:
        logger.debug("OpenTelemetry SDK not installed, using no-op meter")
        return _NoopMeter()
    except Exception as exc:
        logger.warning("OTEL meter init failed: %s", exc)
        return _NoopMeter()


# ── Metrics wrapper ────────────────────────────────────────────────────


class PipelineMetrics:
    """High-level metrics API for the blind-to-x pipeline.

    Wraps OpenTelemetry counters/histograms into domain-specific methods.
    """

    def __init__(self, meter):
        self._meter = meter

        # Counters
        self.api_calls = meter.create_counter(
            "btx.api.calls.total",
            description="Total API calls by provider",
        )
        self.api_errors = meter.create_counter(
            "btx.api.errors.total",
            description="Total API errors by provider",
        )
        self.posts_processed = meter.create_counter(
            "btx.posts.processed.total",
            description="Total posts processed",
        )
        self.posts_published = meter.create_counter(
            "btx.posts.published.total",
            description="Total posts published to Notion",
        )
        self.tokens_used = meter.create_counter(
            "btx.tokens.total",
            description="Total LLM tokens consumed",
        )
        self.images_generated = meter.create_counter(
            "btx.images.generated.total",
            description="Total images generated",
        )

        # Histograms
        self.api_latency = meter.create_histogram(
            "btx.api.latency_ms",
            description="API call latency in milliseconds",
        )
        self.pipeline_duration = meter.create_histogram(
            "btx.pipeline.duration_s",
            description="Pipeline run duration in seconds",
        )
        self.post_processing_time = meter.create_histogram(
            "btx.post.processing_time_s",
            description="Per-post processing time in seconds",
        )
        self.cost_usd = meter.create_histogram(
            "btx.cost.usd",
            description="Cost in USD per API call",
        )

    def record_api_call(
        self,
        provider: str,
        tokens: int = 0,
        latency_ms: float = 0,
        cost_usd: float = 0,
        success: bool = True,
    ) -> None:
        attrs = {"provider": provider}
        self.api_calls.add(1, attrs)
        if tokens > 0:
            self.tokens_used.add(tokens, attrs)
        if latency_ms > 0:
            self.api_latency.record(latency_ms, attrs)
        if cost_usd > 0:
            self.cost_usd.record(cost_usd, attrs)
        if not success:
            self.api_errors.add(1, attrs)

    def record_image_generation(self, provider: str, count: int = 1) -> None:
        self.images_generated.add(count, {"provider": provider})

    def record_pipeline_run(
        self,
        posts_processed: int = 0,
        posts_published: int = 0,
        duration_s: float = 0,
        source: str = "unknown",
    ) -> None:
        attrs = {"source": source}
        if posts_processed > 0:
            self.posts_processed.add(posts_processed, attrs)
        if posts_published > 0:
            self.posts_published.add(posts_published, attrs)
        if duration_s > 0:
            self.pipeline_duration.record(duration_s, attrs)

    def record_post_time(self, source: str, duration_s: float) -> None:
        self.post_processing_time.record(duration_s, {"source": source})


# ── Convenience decorators ──────────────────────────────────────────────


def traced(name: str | None = None):
    """Decorator to add a span around an async function.

    Usage:
        @traced("scrape_blind")
        async def scrape(url: str):
            ...
    """

    def decorator(fn):
        span_name = name or f"{fn.__module__}.{fn.__qualname__}"

        if _is_async(fn):  # [QA 수정] A-8: 불필요한 walrus 연산자 제거
            import functools

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        result = await fn(*args, **kwargs)
                        return result
                    except Exception as exc:
                        span.record_exception(exc)
                        raise

            return async_wrapper
        else:
            import functools

            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        result = fn(*args, **kwargs)
                        return result
                    except Exception as exc:
                        span.record_exception(exc)
                        raise

            return sync_wrapper

    return decorator


def _is_async(fn) -> bool:
    """Check if fn is an async function."""
    return inspect.iscoroutinefunction(fn)


@contextmanager
def timed_span(name: str, attributes: dict | None = None):
    """Context manager for a timed span with automatic duration recording.

    Usage:
        with timed_span("process_post", {"source": "blind"}):
            ...
    """
    start = time.perf_counter()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
        try:
            yield span
        finally:
            elapsed = time.perf_counter() - start
            span.set_attribute("duration_s", round(elapsed, 3))


# ── Module-level singletons ────────────────────────────────────────────

if _OTEL_ENABLED:
    tracer = _init_otel_tracer()
    _meter = _init_otel_meter()
    metrics = PipelineMetrics(_meter)
    logger.info(
        "OpenTelemetry enabled: service=%s endpoint=%s exporter=%s",
        _OTEL_SERVICE,
        _OTEL_ENDPOINT,
        _OTEL_EXPORTER,
    )
else:
    tracer = _NoopTracer()
    metrics = PipelineMetrics(_NoopMeter())
