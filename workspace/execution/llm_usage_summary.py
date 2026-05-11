"""LLM 사용량 요약 리포터.

`llm_metrics.py` 가 쌓는 JSONL 파일들 (`workspace/.tmp/llm_metrics/llm_calls_*.jsonl`) 과
`api_usage_tracker` 의 SQLite `api_calls` 테이블을 통합 집계해서 단일 CLI 리포트로 제공.

Langfuse 셀프호스트가 활성화되지 않은 환경에서도 LLM 호출 가시성을 즉시 확보한다.

Usage:
    python workspace/execution/llm_usage_summary.py                   # 최근 7일 요약 (text)
    python workspace/execution/llm_usage_summary.py --days 30 --json  # 30일, JSON
    python workspace/execution/llm_usage_summary.py --provider anthropic
    python workspace/execution/llm_usage_summary.py --by-model
    python workspace/execution/llm_usage_summary.py --by-caller

집계 지표:
    total_calls / total_input_tokens / total_output_tokens / total_cost_usd
    cache_hit_ratio (cache_read_tokens / (input_tokens + cache_read_tokens), Anthropic only)
    fallback_rate (fallback_used 비율)
    error_rate (success=False 비율)
    avg_latency_ms / p95_latency_ms

순수 stdlib (json/sqlite3/argparse/pathlib/datetime). 외부 의존 없음.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_METRICS_DIR = WORKSPACE_ROOT / ".tmp" / "llm_metrics"
DEFAULT_DB_PATH = WORKSPACE_ROOT / ".tmp" / "workspace.db"


@dataclass
class CallRecord:
    """단일 LLM 호출의 정규화된 표현 — JSONL 과 SQLite 양쪽에서 공통 사용."""

    timestamp: datetime
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""
    caller: str = ""
    fallback_used: bool = False


@dataclass
class Aggregate:
    label: str
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cost_usd: float = 0.0
    error_count: int = 0
    fallback_count: int = 0
    latencies: list[float] = field(default_factory=list)

    def add(self, rec: CallRecord) -> None:
        self.total_calls += 1
        self.total_input_tokens += rec.input_tokens
        self.total_output_tokens += rec.output_tokens
        self.total_cache_creation_tokens += rec.cache_creation_tokens
        self.total_cache_read_tokens += rec.cache_read_tokens
        self.total_cost_usd += rec.cost_usd
        if not rec.success:
            self.error_count += 1
        if rec.fallback_used:
            self.fallback_count += 1
        if rec.latency_ms > 0:
            self.latencies.append(rec.latency_ms)

    def cache_hit_ratio(self) -> float:
        """cache_read_tokens / (input_tokens + cache_read_tokens) — 0.0 이면 캐싱 미사용."""
        denom = self.total_input_tokens + self.total_cache_read_tokens
        return (self.total_cache_read_tokens / denom) if denom > 0 else 0.0

    def avg_latency_ms(self) -> float:
        return (sum(self.latencies) / len(self.latencies)) if self.latencies else 0.0

    def p95_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_l = sorted(self.latencies)
        idx = max(0, min(len(sorted_l) - 1, int(round(len(sorted_l) * 0.95)) - 1))
        return sorted_l[idx]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cache_creation_tokens": self.total_cache_creation_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "cache_hit_ratio": round(self.cache_hit_ratio(), 4),
            "error_count": self.error_count,
            "error_rate": round(self.error_count / self.total_calls, 4) if self.total_calls else 0.0,
            "fallback_count": self.fallback_count,
            "fallback_rate": round(self.fallback_count / self.total_calls, 4) if self.total_calls else 0.0,
            "avg_latency_ms": round(self.avg_latency_ms(), 1),
            "p95_latency_ms": round(self.p95_latency_ms(), 1),
        }


# ── Data loaders ────────────────────────────────────────────────────────────


def _parse_timestamp(raw: str) -> datetime | None:
    """ISO-ish timestamp parser. Returns None on garbage."""
    if not raw:
        return None
    try:
        # Handle both '2026-05-08T01:40:07+00:00' and '2026-05-08 01:40:07'
        cleaned = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def load_jsonl_records(
    metrics_dir: Path,
    *,
    since: datetime | None = None,
) -> Iterable[CallRecord]:
    """Walk metrics_dir/*.jsonl, parse each line into a CallRecord."""
    if not metrics_dir.exists():
        return
    for path in sorted(metrics_dir.glob("llm_calls_*.jsonl")):
        try:
            with path.open("r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = _parse_timestamp(obj.get("timestamp", ""))
                    if ts is None:
                        continue
                    if since and ts < since:
                        continue
                    md = obj.get("metadata") or {}
                    yield CallRecord(
                        timestamp=ts,
                        provider=str(obj.get("provider", "") or "unknown"),
                        model=str(obj.get("model", "") or "unknown"),
                        input_tokens=int(obj.get("input_tokens", 0) or 0),
                        output_tokens=int(obj.get("output_tokens", 0) or 0),
                        cache_creation_tokens=int(obj.get("cache_creation_tokens", 0) or 0),
                        cache_read_tokens=int(obj.get("cache_read_tokens", 0) or 0),
                        cost_usd=float(obj.get("cost_usd", 0.0) or 0.0),
                        latency_ms=float(obj.get("latency_ms", 0.0) or 0.0),
                        success=bool(obj.get("success", True)),
                        error=str(obj.get("error", "") or ""),
                        caller=str(obj.get("caller", "") or ""),
                        fallback_used=bool(md.get("fallback_used", False)),
                    )
        except OSError:
            continue


def load_sqlite_records(
    db_path: Path,
    *,
    since: datetime | None = None,
) -> Iterable[CallRecord]:
    """Read api_calls table. cache_creation/read columns are optional (added in T-255)."""
    if not db_path.exists():
        return
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(api_calls)").fetchall()}
        has_cache = "cache_creation_tokens" in existing_cols and "cache_read_tokens" in existing_cols
    except sqlite3.DatabaseError:
        return
    try:
        rows = conn.execute("SELECT * FROM api_calls").fetchall()
    except sqlite3.DatabaseError:
        conn.close()
        return
    conn.close()

    for row in rows:
        # SQLite timestamp is local 'YYYY-MM-DD HH:MM:SS' (api_usage_tracker uses 'localtime')
        ts = _parse_timestamp(row["timestamp"])
        if ts is None:
            continue
        if since and ts < since:
            continue
        yield CallRecord(
            timestamp=ts,
            provider=str(row["provider"] or "unknown"),
            model=str(row["model"] or "unknown"),
            input_tokens=int(row["tokens_input"] or 0),
            output_tokens=int(row["tokens_output"] or 0),
            cache_creation_tokens=int(row["cache_creation_tokens"] or 0) if has_cache else 0,
            cache_read_tokens=int(row["cache_read_tokens"] or 0) if has_cache else 0,
            cost_usd=float(row["cost_usd"] or 0.0),
            latency_ms=0.0,  # api_calls has no latency
            success=True,  # api_calls only logs successful calls
            error="",
            caller=str(row["caller_script"] or ""),
            fallback_used=bool(int(row["fallback_used"] or 0)),
        )


def merge_dedup(
    *sources: Iterable[CallRecord],
) -> list[CallRecord]:
    """Combine multiple sources. Dedup by (timestamp, provider, model, tokens) tuple.

    JSONL is the richer source (has latency + error). SQLite api_calls overlaps but lacks
    those fields. We keep the JSONL entry when the same logical call exists in both.
    """
    seen: dict[tuple, CallRecord] = {}
    for src in sources:
        for rec in src:
            key = (
                rec.timestamp.replace(microsecond=0),  # 1s granularity
                rec.provider,
                rec.model,
                rec.input_tokens,
                rec.output_tokens,
            )
            existing = seen.get(key)
            if existing is None:
                seen[key] = rec
            elif existing.latency_ms == 0 and rec.latency_ms > 0:
                # Prefer the richer record
                seen[key] = rec
    return sorted(seen.values(), key=lambda r: r.timestamp)


# ── Aggregation ─────────────────────────────────────────────────────────────


def aggregate(
    records: Iterable[CallRecord],
    *,
    group_by: str = "overall",
) -> list[Aggregate]:
    """Bucket records by the given dimension and return per-bucket aggregates.

    group_by: "overall" / "provider" / "model" / "caller"
    """
    buckets: dict[str, Aggregate] = defaultdict(lambda: Aggregate(label=""))
    for rec in records:
        if group_by == "provider":
            key = rec.provider
        elif group_by == "model":
            key = f"{rec.provider}/{rec.model}"
        elif group_by == "caller":
            key = rec.caller or "(unknown)"
        else:
            key = "overall"
        agg = buckets[key]
        if not agg.label:
            agg.label = key
        agg.add(rec)
    return sorted(buckets.values(), key=lambda a: a.total_cost_usd, reverse=True)


# ── Rendering ───────────────────────────────────────────────────────────────


def _format_money(usd: float) -> str:
    if usd >= 1.0:
        return f"${usd:,.4f}"
    return f"${usd:.6f}"


def render_text(aggs: list[Aggregate], *, days: int, group_by: str) -> str:
    if not aggs:
        return f"LLM usage summary (last {days}d): no records found."
    lines: list[str] = [
        f"LLM usage summary — last {days}d, grouped by {group_by}",
        "=" * 80,
    ]
    for a in aggs:
        d = a.to_dict()
        lines.append(f"  {d['label']}")
        lines.append(
            f"    calls={d['total_calls']:>4}  "
            f"in={d['total_input_tokens']:>8,}  out={d['total_output_tokens']:>8,}  "
            f"cost={_format_money(d['total_cost_usd'])}"
        )
        cache_in = d["total_cache_creation_tokens"] + d["total_cache_read_tokens"]
        if cache_in > 0:
            lines.append(
                f"    cache_w={d['total_cache_creation_tokens']:>6,}  "
                f"cache_r={d['total_cache_read_tokens']:>6,}  "
                f"hit_ratio={d['cache_hit_ratio'] * 100:5.1f}%"
            )
        if d["error_count"] or d["fallback_count"]:
            lines.append(
                f"    errors={d['error_count']} ({d['error_rate'] * 100:.1f}%)  "
                f"fallbacks={d['fallback_count']} ({d['fallback_rate'] * 100:.1f}%)"
            )
        if d["avg_latency_ms"] > 0:
            lines.append(f"    latency: avg={d['avg_latency_ms']:.0f}ms  p95={d['p95_latency_ms']:.0f}ms")
        lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────────────────


def _ensure_utf8_stdout() -> None:
    """Windows cp949 콘솔에서도 한국어·em-dash 출력 가능하도록 stdout reconfigure."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="LLM 사용량 통합 요약")
    parser.add_argument("--days", type=int, default=7, help="며칠치 (default: 7)")
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=DEFAULT_METRICS_DIR,
        help=f"JSONL 디렉터리 (default: {DEFAULT_METRICS_DIR})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"workspace SQLite (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument("--provider", help="특정 provider 만 (예: anthropic)")
    parser.add_argument("--model", help="특정 model 만 (예: claude-sonnet-4-20250514)")
    parser.add_argument(
        "--by",
        choices=["overall", "provider", "model", "caller"],
        default="overall",
        help="집계 차원 (default: overall)",
    )
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args(argv)

    since = datetime.now(timezone.utc) - timedelta(days=args.days)

    jsonl_records = list(load_jsonl_records(args.metrics_dir, since=since))
    sqlite_records = list(load_sqlite_records(args.db, since=since))
    records = merge_dedup(jsonl_records, sqlite_records)

    if args.provider:
        records = [r for r in records if r.provider == args.provider]
    if args.model:
        records = [r for r in records if r.model == args.model]

    aggs = aggregate(records, group_by=args.by)

    if args.json:
        sys.stdout.write(
            json.dumps(
                {
                    "days": args.days,
                    "filter": {"provider": args.provider, "model": args.model},
                    "group_by": args.by,
                    "record_count": len(records),
                    "aggregates": [a.to_dict() for a in aggs],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    else:
        print(render_text(aggs, days=args.days, group_by=args.by))

    return 0


if __name__ == "__main__":
    sys.exit(main())
