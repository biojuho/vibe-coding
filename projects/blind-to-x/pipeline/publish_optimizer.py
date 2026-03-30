"""Optimal publish time recommendation based on historical performance (P1-B3).

Analyses past tweet performance by time-of-day slot and recommends the best
publishing windows. Works with the existing KST time-slot system from
analytics_tracker.py.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# KST 시간대 슬롯 정의 (analytics_tracker._kst_time_slot과 동일)
TIME_SLOTS = {
    "오전": {"hours": "06-12", "description": "아침 출근길"},
    "점심": {"hours": "12-14", "description": "점심시간"},
    "오후": {"hours": "14-18", "description": "오후 근무시간"},
    "저녁": {"hours": "18-22", "description": "퇴근 후"},
    "심야": {"hours": "22-06", "description": "심야 시간대"},
}

# 글로벌 기본 우선 추천 시간대 (데이터 부족 시 fallback)
_DEFAULT_OPTIMAL_SLOTS = ["점심", "저녁", "오전"]


class PublishOptimizer:
    """과거 성과 데이터 기반 발행 시간 최적화."""

    def __init__(self, notion_uploader=None, config: dict | None = None):
        self.notion_uploader = notion_uploader
        self.config = config or {}

    @staticmethod
    def get_hourly_performance(
        records: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """시간대 슬롯별 평균 성과 통계 산출.

        Args:
            records: Notion에서 가져온 페이지 레코드 리스트.
                     각 레코드에 'published_at', 'views', 'likes', 'retweets' 포함.

        Returns:
            {
                "오전": {"count": N, "avg_views": X, "avg_likes": Y, "avg_retweets": Z, "engagement_rate": E},
                ...
            }
        """
        slot_data: dict[str, list[dict[str, float]]] = defaultdict(list)

        for r in records:
            slot = _extract_time_slot(r)
            if not slot:
                continue
            views = float(r.get("views", 0) or 0)
            likes = float(r.get("likes", 0) or 0)
            retweets = float(r.get("retweets", 0) or 0)
            if views <= 0:
                continue
            slot_data[slot].append(
                {
                    "views": views,
                    "likes": likes,
                    "retweets": retweets,
                }
            )

        result = {}
        for slot in TIME_SLOTS:
            entries = slot_data.get(slot, [])
            if not entries:
                result[slot] = {"count": 0, "avg_views": 0, "avg_likes": 0, "avg_retweets": 0, "engagement_rate": 0}
                continue
            n = len(entries)
            avg_v = sum(e["views"] for e in entries) / n
            avg_l = sum(e["likes"] for e in entries) / n
            avg_r = sum(e["retweets"] for e in entries) / n
            # engagement_rate: (likes + retweets*2) / views * 100
            total_views = sum(e["views"] for e in entries)
            total_engagement = sum(e["likes"] + e["retweets"] * 2 for e in entries)
            eng_rate = (total_engagement / total_views * 100) if total_views > 0 else 0

            result[slot] = {
                "count": n,
                "avg_views": round(avg_v, 1),
                "avg_likes": round(avg_l, 1),
                "avg_retweets": round(avg_r, 1),
                "engagement_rate": round(eng_rate, 3),
            }
        return result

    @staticmethod
    def get_optimal_publish_time(
        records: list[dict[str, Any]],
        metric: str = "engagement_rate",
        min_data_points: int = 5,
    ) -> list[dict[str, Any]]:
        """최적 발행 시간대 추천.

        Args:
            records: 과거 발행 레코드.
            metric: 정렬 기준 ('engagement_rate', 'avg_views', 'avg_likes').
            min_data_points: 추천에 필요한 최소 데이터 수.

        Returns:
            [{"slot": "점심", "score": 2.5, "reason": "...", "stats": {...}}, ...]
            점수 내림차순 정렬.
        """
        hourly = PublishOptimizer.get_hourly_performance(records)

        # 데이터 충분한 슬롯만 추천 대상
        candidates = []
        for slot, stats in hourly.items():
            if stats["count"] >= min_data_points:
                score = stats.get(metric, 0)
                candidates.append(
                    {
                        "slot": slot,
                        "score": score,
                        "stats": stats,
                        "confidence": "high" if stats["count"] >= 10 else "medium",
                    }
                )

        if not candidates:
            # 데이터 부족: 기본 추천
            logger.info(
                "발행 시간 최적화: 데이터 부족(%d건). 기본 추천 사용.", sum(s["count"] for s in hourly.values())
            )
            return [
                {
                    "slot": slot,
                    "score": 0,
                    "stats": hourly.get(slot, {}),
                    "confidence": "default",
                    "reason": f"{TIME_SLOTS[slot]['description']} — 일반적으로 효과적인 시간대",
                }
                for slot in _DEFAULT_OPTIMAL_SLOTS
            ]

        # 점수 내림차순 정렬
        candidates.sort(key=lambda c: c["score"], reverse=True)

        # 추천 이유 생성
        for i, c in enumerate(candidates):
            s = c["stats"]
            if i == 0:
                c["reason"] = (
                    f"🏆 최고 성과 시간대 — {TIME_SLOTS[c['slot']]['description']}, "
                    f"평균 {s['avg_views']:.0f}조회, 참여율 {s['engagement_rate']:.2f}%"
                )
            else:
                c["reason"] = (
                    f"{TIME_SLOTS[c['slot']]['description']}, "
                    f"평균 {s['avg_views']:.0f}조회, 참여율 {s['engagement_rate']:.2f}%"
                )

        return candidates


def _extract_time_slot(record: dict[str, Any]) -> str | None:
    """레코드에서 발행 시간대 슬롯 추출.

    published_at (ISO format) 또는 performance_grade 존재 시 추정.
    """
    published_at = record.get("published_at", "")
    if not published_at:
        return None

    try:
        # ISO format: "2025-03-01T14:30:00+09:00" or similar
        if "T" in str(published_at):
            time_part = str(published_at).split("T")[1]
            hour = int(time_part[:2])
        else:
            return None

        if 6 <= hour < 12:
            return "오전"
        elif 12 <= hour < 14:
            return "점심"
        elif 14 <= hour < 18:
            return "오후"
        elif 18 <= hour < 22:
            return "저녁"
        return "심야"
    except (ValueError, IndexError):
        return None
