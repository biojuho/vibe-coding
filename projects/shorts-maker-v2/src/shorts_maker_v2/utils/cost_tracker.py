"""일일/월간 비용 추적 모듈.

JSONL 파일 기반으로 모든 작업의 비용을 누적 기록하고,
일일/월간/전체 통계를 조회할 수 있습니다.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CostTracker:
    """JSONL 파일 기반 비용 추적기.

    사용법:
        tracker = CostTracker(logs_dir="logs")
        tracker.record(job_id="abc", cost_usd=0.17, topic="블랙홀", channel="space")
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
        with self._lock, self._file.open("a", encoding="utf-8") as f:
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
                if dt.year == year and dt.month == month and (day is None or dt.day == day):
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
        sep = "=" * 50
        logger.info(sep)
        logger.info("비용 대시보드 (%s)", s["date"])
        logger.info(sep)
        logger.info("  오늘:   %d건 | $%.4f", s["daily_jobs"], s["daily_cost_usd"])
        logger.info("  이번달: %d건 | $%.4f", s["monthly_jobs"], s["monthly_cost_usd"])
        logger.info("  전체:   %d건 | $%.4f", s["total_jobs"], s["total_cost_usd"])
        if s["total_jobs"] > 0:
            logger.info("  건당 평균: $%.4f", s["avg_cost_per_job"])
        logger.info(sep)
