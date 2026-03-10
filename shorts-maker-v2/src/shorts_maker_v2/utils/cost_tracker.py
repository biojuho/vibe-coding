"""일일/월간 비용 추적 모듈.

JSONL 파일 기반으로 모든 작업의 비용을 누적 기록하고,
일일/월간/전체 통계를 조회할 수 있습니다.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CostTracker:
    """JSONL 파일 기반 비용 추적기.

    사용법:
        tracker = CostTracker(logs_dir="logs")
        tracker.record(job_id="abc", cost_usd=0.17, topic="블랙홀", channel="science")
        print(tracker.summary())
    """

    def __init__(self, logs_dir: str | Path = "logs"):
        self.logs_dir = Path(logs_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.logs_dir / "costs.jsonl"
        self._lock = threading.Lock()

    def record(
        self,
        *,
        job_id: str,
        cost_usd: float,
        topic: str = "",
        channel: str = "",
        status: str = "success",
        duration_sec: float = 0.0,
    ) -> None:
        """비용 레코드 추가."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "cost_usd": round(cost_usd, 6),
            "topic": topic,
            "channel": channel,
            "status": status,
            "duration_sec": round(duration_sec, 1),
        }
        with self._lock:
            with self._file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_records(self) -> list[dict[str, Any]]:
        """전체 레코드 로드."""
        if not self._file.exists():
            return []
        records: list[dict[str, Any]] = []
        with self._file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def _filter_by_date(
        self, records: list[dict[str, Any]], year: int, month: int, day: int | None = None
    ) -> list[dict[str, Any]]:
        """날짜 기준 필터링."""
        result = []
        for r in records:
            ts = r.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts)
                if dt.year == year and dt.month == month:
                    if day is None or dt.day == day:
                        result.append(r)
            except (ValueError, TypeError):
                continue
        return result

    def daily_total(self, date: datetime | None = None) -> float:
        """당일(또는 지정일) 누적 비용."""
        dt = date or datetime.now(timezone.utc)
        records = self._load_records()
        filtered = self._filter_by_date(records, dt.year, dt.month, dt.day)
        return round(sum(r.get("cost_usd", 0) for r in filtered), 6)

    def monthly_total(self, date: datetime | None = None) -> float:
        """당월(또는 지정월) 누적 비용."""
        dt = date or datetime.now(timezone.utc)
        records = self._load_records()
        filtered = self._filter_by_date(records, dt.year, dt.month)
        return round(sum(r.get("cost_usd", 0) for r in filtered), 6)

    def summary(self) -> dict[str, Any]:
        """전체 통계 요약."""
        records = self._load_records()
        now = datetime.now(timezone.utc)
        daily = self._filter_by_date(records, now.year, now.month, now.day)
        monthly = self._filter_by_date(records, now.year, now.month)

        total_cost = sum(r.get("cost_usd", 0) for r in records)
        daily_cost = sum(r.get("cost_usd", 0) for r in daily)
        monthly_cost = sum(r.get("cost_usd", 0) for r in monthly)

        return {
            "date": now.strftime("%Y-%m-%d"),
            "daily_jobs": len(daily),
            "daily_cost_usd": round(daily_cost, 4),
            "monthly_jobs": len(monthly),
            "monthly_cost_usd": round(monthly_cost, 4),
            "total_jobs": len(records),
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_job": round(total_cost / len(records), 4) if records else 0.0,
        }

    def print_summary(self) -> None:
        """비용 요약 출력."""
        s = self.summary()
        print(f"\n{'=' * 50}")
        print(f"📊 비용 대시보드 ({s['date']})")
        print(f"{'=' * 50}")
        print(f"  📅 오늘:  {s['daily_jobs']}건 | ${s['daily_cost_usd']:.4f}")
        print(f"  📆 이번달: {s['monthly_jobs']}건 | ${s['monthly_cost_usd']:.4f}")
        print(f"  📈 전체:  {s['total_jobs']}건 | ${s['total_cost_usd']:.4f}")
        if s["total_jobs"] > 0:
            print(f"  💰 건당 평균: ${s['avg_cost_per_job']:.4f}")
        print(f"{'=' * 50}\n")
