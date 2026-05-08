"""llm_metrics — LLM 호출 메트릭 수집 레이어.

모든 프로젝트의 LLM Client 호출에서 공통 메트릭을 수집하고
JSON Lines 형식으로 로깅합니다.

Langfuse 도입 전 선행 레이어로서:
  - 호출당 latency, token 수, 비용, 에러를 기록
  - 누적 통계를 thread-safe하게 관리
  - 향후 Langfuse @observe 데코레이터로 교체 가능하도록 설계

Usage:
    from execution.llm_metrics import MetricsCollector, record_llm_call

    # 데코레이터 방식
    collector = MetricsCollector()
    with collector.track("script_generation", provider="google", model="gemini-2.5-flash"):
        result = llm_client.generate_json(...)
    # → 자동으로 latency 기록

    # 직접 기록 방식
    record_llm_call(
        step="script_generation",
        provider="google",
        model="gemini-2.5-flash",
        input_tokens=500,
        output_tokens=200,
        latency_ms=1200,
        cost_usd=0.001,
    )
"""

from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
_METRICS_DIR = WORKSPACE_ROOT / ".tmp" / "llm_metrics"


@dataclass
class LLMCallMetric:
    """단일 LLM 호출 메트릭 레코드."""

    timestamp: str
    step: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    success: bool = True
    error: str = ""
    caller: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_line(self) -> str:
        """JSON Lines 형식 직렬화."""
        return json.dumps(asdict(self), ensure_ascii=False, default=str)


@dataclass
class AggregateStats:
    """누적 통계 요약."""

    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    error_count: int = 0
    provider_calls: dict[str, int] = field(default_factory=dict)

    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "avg_latency_ms": round(self.avg_latency_ms(), 1),
            "error_count": self.error_count,
            "error_rate": round(self.error_count / self.total_calls, 3) if self.total_calls else 0.0,
            "provider_calls": dict(self.provider_calls),
        }


class MetricsCollector:
    """Thread-safe LLM 메트릭 수집기.

    인스턴스별로 세션 내 누적 통계를 관리합니다.
    """

    def __init__(self, *, log_dir: Path | None = None, caller: str = ""):
        self._lock = threading.Lock()
        self._stats = AggregateStats()
        self._log_dir = log_dir or _METRICS_DIR
        self._caller = caller
        self._log_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def track(
        self,
        step: str,
        *,
        provider: str = "",
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Context manager로 LLM 호출 latency 자동 기록.

        Usage:
            ctx = {}
            with collector.track("step_name", provider="google") as ctx:
                result = llm.generate(...)
                ctx["input_tokens"] = result.input_tokens
                ctx["output_tokens"] = result.output_tokens
        """
        ctx: dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "cost_usd": 0.0,
        }
        start = time.monotonic()
        error_msg = ""
        success = True

        try:
            yield ctx
        except Exception as e:
            error_msg = str(e)[:200]
            success = False
            raise
        finally:
            latency_ms = (time.monotonic() - start) * 1000
            self.record(
                step=step,
                provider=provider,
                model=model,
                input_tokens=ctx.get("input_tokens", 0),
                output_tokens=ctx.get("output_tokens", 0),
                cache_creation_tokens=ctx.get("cache_creation_tokens", 0),
                cache_read_tokens=ctx.get("cache_read_tokens", 0),
                latency_ms=latency_ms,
                cost_usd=ctx.get("cost_usd", 0.0),
                success=success,
                error=error_msg,
                metadata=metadata,
            )

    def record(
        self,
        *,
        step: str,
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        latency_ms: float = 0.0,
        cost_usd: float = 0.0,
        success: bool = True,
        error: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> LLMCallMetric:
        """메트릭 레코드 기록."""
        metric = LLMCallMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            step=step,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            latency_ms=round(latency_ms, 1),
            cost_usd=cost_usd,
            success=success,
            error=error,
            caller=self._caller,
            metadata=metadata or {},
        )

        # 누적 통계 업데이트 (thread-safe)
        with self._lock:
            self._stats.total_calls += 1
            self._stats.total_input_tokens += input_tokens
            self._stats.total_output_tokens += output_tokens
            self._stats.total_cost_usd += cost_usd
            self._stats.total_latency_ms += latency_ms
            if not success:
                self._stats.error_count += 1
            self._stats.provider_calls[provider] = self._stats.provider_calls.get(provider, 0) + 1

        # JSON Lines 파일에 append
        self._write_log(metric)

        logger.debug(
            "[LLMMetrics] %s/%s latency=%.0fms tokens=%d+%d cost=$%.4f",
            provider,
            model,
            latency_ms,
            input_tokens,
            output_tokens,
            cost_usd,
        )

        return metric

    def get_stats(self) -> dict[str, Any]:
        """현재 세션 누적 통계 반환."""
        with self._lock:
            return self._stats.to_dict()

    def _write_log(self, metric: LLMCallMetric) -> None:
        """JSON Lines 파일에 메트릭 기록."""
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            log_file = self._log_dir / f"llm_calls_{today}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(metric.to_json_line() + "\n")
        except Exception:
            pass  # 로깅 실패는 무시


# ── 모듈 레벨 편의 함수 ──────────────────────────────────────────

_default_collector: MetricsCollector | None = None
_collector_lock = threading.Lock()


def get_default_collector(**kwargs: Any) -> MetricsCollector:
    """기본 MetricsCollector 싱글톤."""
    global _default_collector
    with _collector_lock:
        if _default_collector is None:
            _default_collector = MetricsCollector(**kwargs)
    return _default_collector


def record_llm_call(**kwargs: Any) -> LLMCallMetric:
    """간편 메트릭 기록 함수."""
    return get_default_collector().record(**kwargs)
