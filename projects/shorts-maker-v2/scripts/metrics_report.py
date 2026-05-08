"""metrics_report — 파이프라인 성능 메트릭 리포트 생성.

workspace/.tmp/llm_metrics/ 하위의 JSONL 로그를 읽어
LLM 비용, 토큰 사용량, 레이턴시 통계를 출력한다.

Usage:
    python scripts/metrics_report.py                # 오늘 메트릭 요약
    python scripts/metrics_report.py --days 7       # 최근 7일
    python scripts/metrics_report.py --json          # JSON 출력
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _find_metrics_dir() -> Path:
    """workspace/.tmp/llm_metrics/ 디렉토리 탐색."""
    # 스크립트 기준 상위 탐색
    candidates = [
        Path(__file__).resolve().parent.parent / ".tmp" / "llm_metrics",
        Path.cwd() / ".tmp" / "llm_metrics",
        Path.cwd().parent / ".tmp" / "llm_metrics",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("llm_metrics 디렉토리를 찾을 수 없습니다. workspace/.tmp/llm_metrics/ 경로를 확인하세요.")


def _load_records(metrics_dir: Path, days: int = 1) -> list[dict]:
    """지정 일수 내의 JSONL 레코드 로드."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records: list[dict] = []

    for jsonl_file in sorted(metrics_dir.glob("*.jsonl")):
        # 파일명 형식: llm_2026-05-08.jsonl
        try:
            date_str = jsonl_file.stem.replace("llm_", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date < cutoff - timedelta(days=1):
                continue
        except ValueError:
            continue

        with jsonl_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue

    return records


def generate_report(records: list[dict]) -> dict:
    """메트릭 레코드로부터 요약 통계를 생성."""
    if not records:
        return {
            "total_calls": 0,
            "total_cost_usd": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "avg_latency_ms": 0.0,
            "by_model": {},
            "by_provider": {},
        }

    total_cost = 0.0
    total_input = 0
    total_output = 0
    latencies: list[float] = []
    by_model: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost": 0.0, "tokens": 0})
    by_provider: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost": 0.0, "tokens": 0})

    for r in records:
        cost = r.get("cost_usd", 0.0) or 0.0
        inp = r.get("input_tokens", 0) or 0
        out = r.get("output_tokens", 0) or 0
        lat = r.get("latency_ms", 0.0) or 0.0
        model = r.get("model", "unknown")
        provider = r.get("provider", "unknown")

        total_cost += cost
        total_input += inp
        total_output += out
        if lat > 0:
            latencies.append(lat)

        by_model[model]["calls"] += 1
        by_model[model]["cost"] += cost
        by_model[model]["tokens"] += inp + out

        by_provider[provider]["calls"] += 1
        by_provider[provider]["cost"] += cost
        by_provider[provider]["tokens"] += inp + out

    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    return {
        "total_calls": len(records),
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "avg_latency_ms": round(avg_lat, 1),
        "p95_latency_ms": round(
            sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0,
            1,
        ),
        "by_model": dict(by_model),
        "by_provider": dict(by_provider),
    }


def format_text_report(report: dict) -> str:
    """사람이 읽기 좋은 텍스트 리포트 포맷."""
    lines = [
        "=" * 60,
        "📊 Pipeline LLM Metrics Report",
        "=" * 60,
        "",
        f"  Total API Calls:     {report['total_calls']:,}",
        f"  Total Cost (USD):    ${report['total_cost_usd']:.4f}",
        f"  Total Tokens:        {report.get('total_tokens', 0):,}",
        f"    ├─ Input:          {report['total_input_tokens']:,}",
        f"    └─ Output:         {report['total_output_tokens']:,}",
        f"  Avg Latency:         {report['avg_latency_ms']:.0f}ms",
        f"  P95 Latency:         {report.get('p95_latency_ms', 0):.0f}ms",
        "",
    ]

    if report.get("by_model"):
        lines.append("  📦 By Model:")
        lines.append("  " + "-" * 50)
        for model, stats in sorted(
            report["by_model"].items(),
            key=lambda x: x[1]["cost"],
            reverse=True,
        ):
            lines.append(f"    {model:<30} {stats['calls']:>4} calls  ${stats['cost']:.4f}  {stats['tokens']:>8,} tok")
        lines.append("")

    if report.get("by_provider"):
        lines.append("  🏢 By Provider:")
        lines.append("  " + "-" * 50)
        for prov, stats in sorted(
            report["by_provider"].items(),
            key=lambda x: x[1]["cost"],
            reverse=True,
        ):
            lines.append(f"    {prov:<30} {stats['calls']:>4} calls  ${stats['cost']:.4f}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline LLM Metrics Report")
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="분석할 일수 (기본: 1일)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 형식으로 출력",
    )
    parser.add_argument(
        "--metrics-dir",
        type=str,
        default=None,
        help="메트릭 디렉토리 경로 (기본: 자동 탐색)",
    )
    args = parser.parse_args()

    try:
        metrics_dir = Path(args.metrics_dir) if args.metrics_dir else _find_metrics_dir()
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    records = _load_records(metrics_dir, days=args.days)
    report = generate_report(records)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_text_report(report))


if __name__ == "__main__":
    main()
