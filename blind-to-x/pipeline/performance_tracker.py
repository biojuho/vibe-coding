"""
P6: 콘텐츠 성과 피드백 루프 (Performance Feedback Loop)

Threads/네이버 블로그 발행 후 성과 데이터를 기록하고,
시간 경과에 따른 토픽/플랫폼별 성과 추이를 분석합니다.

사용법:
    tracker = PerformanceTracker(config)
    tracker.record_performance("page_id", "threads", {"likes": 42, "comments": 5, "saves": 12})
    report = tracker.generate_report(days=7)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── 성과 지표 타입 정의 ────────────────────────────────────────────
PLATFORM_METRICS = {
    "twitter": ["likes", "retweets", "impressions", "replies", "bookmarks"],
    "threads": ["likes", "comments", "saves", "shares", "reach"],
    "naver_blog": ["views", "likes", "comments", "shares", "blog_rank"],
    "newsletter": ["opens", "clicks", "unsubscribes", "forwards"],
}

# 각 지표의 가중치 (engagement score 계산용)
ENGAGEMENT_WEIGHTS = {
    "twitter": {"likes": 1, "retweets": 3, "impressions": 0.01, "replies": 5, "bookmarks": 2},
    "threads": {"likes": 1, "comments": 5, "saves": 3, "shares": 4, "reach": 0.01},
    "naver_blog": {"views": 0.1, "likes": 1, "comments": 5, "shares": 4, "blog_rank": -2},
    "newsletter": {"opens": 1, "clicks": 3, "unsubscribes": -5, "forwards": 4},
}

# 성과 등급 기준 (engagement_score 기준)
GRADE_THRESHOLDS = {
    "S": 80,  # 바이럴 성공
    "A": 50,  # 좋은 성과
    "B": 25,  # 평균적 성과
    "C": 0,   # 개선 필요
}


class PerformanceRecord:
    """단일 콘텐츠의 성과 데이터."""

    def __init__(
        self,
        notion_page_id: str,
        platform: str,
        metrics: dict[str, float],
        topic_cluster: str = "",
        emotion_axis: str = "",
        recorded_at: str | None = None,
    ):
        self.notion_page_id = notion_page_id
        self.platform = platform
        self.metrics = metrics
        self.topic_cluster = topic_cluster
        self.emotion_axis = emotion_axis
        self.recorded_at = recorded_at or datetime.now().isoformat()
        self.engagement_score = self._calculate_engagement()
        self.grade = self._assign_grade()

    def _calculate_engagement(self) -> float:
        weights = ENGAGEMENT_WEIGHTS.get(self.platform, {})
        score = 0.0
        for metric, value in self.metrics.items():
            w = weights.get(metric, 0)
            score += value * w
        return round(score, 2)

    def _assign_grade(self) -> str:
        for grade, threshold in sorted(GRADE_THRESHOLDS.items(), key=lambda x: -x[1]):
            if self.engagement_score >= threshold:
                return grade
        return "C"

    def to_dict(self) -> dict:
        return {
            "notion_page_id": self.notion_page_id,
            "platform": self.platform,
            "metrics": self.metrics,
            "topic_cluster": self.topic_cluster,
            "emotion_axis": self.emotion_axis,
            "engagement_score": self.engagement_score,
            "grade": self.grade,
            "recorded_at": self.recorded_at,
        }


class PerformanceTracker:
    """콘텐츠 성과를 추적하고 분석합니다."""

    def __init__(self, config=None, data_dir: str | Path | None = None):
        self.config = config or {}
        self.data_dir = Path(data_dir or os.environ.get(
            "PERFORMANCE_DATA_DIR",
            Path(__file__).parent.parent / ".tmp" / "performance",
        ))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.records_file = self.data_dir / "performance_records.jsonl"
        self._records_cache: list[PerformanceRecord] | None = None

    # ── 기록 ───────────────────────────────────────────────────────
    def record_performance(
        self,
        notion_page_id: str,
        platform: str,
        metrics: dict[str, float],
        topic_cluster: str = "",
        emotion_axis: str = "",
    ) -> PerformanceRecord:
        """성과 데이터를 기록합니다."""
        # [QA 수정] 입력값 유효성 검사
        if not notion_page_id or not notion_page_id.strip():
            raise ValueError("notion_page_id는 비어 있을 수 없습니다.")
        if platform not in PLATFORM_METRICS:
            logger.warning("알 수 없는 플랫폼: %s (허용: %s)", platform, list(PLATFORM_METRICS.keys()))

        record = PerformanceRecord(
            notion_page_id=notion_page_id,
            platform=platform,
            metrics=metrics,
            topic_cluster=topic_cluster,
            emotion_axis=emotion_axis,
        )

        # [QA 수정] JSONL 파일에 추가 — flush 보장
        with open(self.records_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            f.flush()

        # 캐시 무효화
        self._records_cache = None

        logger.info(
            "성과 기록: %s/%s → %s등급 (score=%.1f)",
            platform, topic_cluster or "?", record.grade, record.engagement_score,
        )
        return record

    # ── 조회 ───────────────────────────────────────────────────────
    def _load_records(self) -> list[PerformanceRecord]:
        """JSONL 파일에서 모든 기록을 로드합니다."""
        if self._records_cache is not None:
            return self._records_cache

        records = []
        if self.records_file.exists():
            with open(self.records_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        records.append(PerformanceRecord(
                            notion_page_id=data["notion_page_id"],
                            platform=data["platform"],
                            metrics=data["metrics"],
                            topic_cluster=data.get("topic_cluster", ""),
                            emotion_axis=data.get("emotion_axis", ""),
                            recorded_at=data.get("recorded_at"),
                        ))
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning("성과 기록 파싱 실패: %s", e)

        self._records_cache = records
        return records

    def get_records(
        self,
        platform: str | None = None,
        topic: str | None = None,
        days: int | None = None,
    ) -> list[PerformanceRecord]:
        """필터링된 성과 기록을 반환합니다."""
        records = self._load_records()

        if platform:
            records = [r for r in records if r.platform == platform]
        if topic:
            records = [r for r in records if r.topic_cluster == topic]
        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            records = [r for r in records if r.recorded_at >= cutoff]

        return records

    # ── 분석 ───────────────────────────────────────────────────────
    def generate_report(self, days: int = 7) -> dict[str, Any]:
        """기간별 성과 보고서를 생성합니다."""
        records = self.get_records(days=days)

        if not records:
            return {
                "period_days": days,
                "total_posts": 0,
                "message": "해당 기간에 기록된 성과가 없습니다.",
            }

        # 플랫폼별 집계
        platform_stats: dict[str, dict[str, Any]] = {}
        for rec in records:
            p = rec.platform
            if p not in platform_stats:
                platform_stats[p] = {
                    "count": 0,
                    "total_engagement": 0.0,
                    "grades": {"S": 0, "A": 0, "B": 0, "C": 0},
                    "top_topics": {},
                }
            stats = platform_stats[p]
            stats["count"] += 1
            stats["total_engagement"] += rec.engagement_score
            stats["grades"][rec.grade] = stats["grades"].get(rec.grade, 0) + 1

            topic = rec.topic_cluster or "기타"
            if topic not in stats["top_topics"]:
                stats["top_topics"][topic] = {"count": 0, "total_score": 0.0}
            stats["top_topics"][topic]["count"] += 1
            stats["top_topics"][topic]["total_score"] += rec.engagement_score

        # 플랫폼별 평균 계산 + 토픽 정렬
        for p, stats in platform_stats.items():
            stats["avg_engagement"] = round(stats["total_engagement"] / stats["count"], 2)
            # 토픽별 평균으로 정렬
            sorted_topics = sorted(
                stats["top_topics"].items(),
                key=lambda x: x[1]["total_score"] / x[1]["count"],
                reverse=True,
            )
            stats["top_topics_ranked"] = [
                {
                    "topic": t,
                    "count": d["count"],
                    "avg_score": round(d["total_score"] / d["count"], 2),
                }
                for t, d in sorted_topics[:5]
            ]

        # 전체 Best/Worst 콘텐츠
        sorted_all = sorted(records, key=lambda r: r.engagement_score, reverse=True)
        best = sorted_all[:3] if len(sorted_all) >= 3 else sorted_all
        worst = sorted_all[-3:] if len(sorted_all) >= 3 else []

        return {
            "period_days": days,
            "total_posts": len(records),
            "platform_stats": {
                p: {
                    "count": s["count"],
                    "avg_engagement": s["avg_engagement"],
                    "grades": s["grades"],
                    "top_topics": s["top_topics_ranked"],
                }
                for p, s in platform_stats.items()
            },
            "best_performing": [r.to_dict() for r in best],
            "worst_performing": [r.to_dict() for r in worst],
        }

    def get_topic_recommendations(self, platform: str, days: int = 30) -> list[dict]:
        """플랫폼별 토픽 추천 (성과 기반)."""
        records = self.get_records(platform=platform, days=days)
        if not records:
            return []

        topic_scores: dict[str, dict[str, float]] = {}
        for rec in records:
            topic = rec.topic_cluster or "기타"
            if topic not in topic_scores:
                topic_scores[topic] = {"total": 0.0, "count": 0}
            topic_scores[topic]["total"] += rec.engagement_score
            topic_scores[topic]["count"] += 1

        recommendations = []
        for topic, data in topic_scores.items():
            avg = data["total"] / data["count"]
            recommendations.append({
                "topic": topic,
                "avg_engagement": round(avg, 2),
                "sample_count": int(data["count"]),
                "recommendation": "강력 추천" if avg >= 50 else "추천" if avg >= 25 else "보통" if avg >= 10 else "개선 필요",
            })

        return sorted(recommendations, key=lambda x: -x["avg_engagement"])


# ── Notion 성과 업데이트 유틸 ──────────────────────────────────────
async def update_notion_performance(
    notion_uploader,
    notion_page_id: str,
    platform: str,
    metrics: dict[str, float],
) -> bool:
    """Notion 페이지에 성과 데이터를 업데이트합니다."""
    # [QA 수정] 빈 page_id 방어
    if not notion_page_id or not notion_page_id.strip():
        logger.warning("Notion 성과 업데이트 스킵: page_id가 비어 있습니다.")
        return False

    try:
        props_update: dict[str, Any] = {}

        # [QA 수정] 플랫폼별 성과 지표 매핑 — url_key 미사용 변수 제거
        if platform == "twitter":
            if "likes" in metrics:
                props_update["24h 좋아요"] = {"number": metrics["likes"]}
            if "retweets" in metrics:
                props_update["24h 리트윗"] = {"number": metrics["retweets"]}
            if "impressions" in metrics:
                props_update["24h 조회수"] = {"number": metrics["impressions"]}
        # TODO: threads, naver_blog 성과 속성은 Notion DB에 추가 후 매핑

        if props_update and notion_uploader:
            if hasattr(notion_uploader, "client") and notion_uploader.client:
                await notion_uploader.client.pages.update(
                    page_id=notion_page_id,
                    properties=props_update,
                )
                logger.info("Notion 성과 업데이트 완료: %s (%s)", notion_page_id[:8], platform)
                return True

    except Exception as exc:
        logger.warning("Notion 성과 업데이트 실패: %s — %s", notion_page_id[:8], exc)

    return False
