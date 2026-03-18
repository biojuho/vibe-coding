"""
콘텐츠 시리즈화 엔진 — 고성과 토픽 자동 감지 및 후속편 제안.

개별 1회성 토픽 생산에서 시리즈 콘텐츠로 전환하여
시청자 유지율과 채널 성장을 극대화합니다.

Usage:
    from shorts_maker_v2.pipeline.series_engine import SeriesEngine
    engine = SeriesEngine(output_dir=Path("output"))
    suggestion = engine.suggest_next("AI가 바꾸는 미래")
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SeriesPlan:
    """시리즈 에피소드 계획."""
    series_id: str
    parent_topic: str
    episode: int
    suggested_title: str
    prev_summary: str = ""
    performance_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TopicPerformance:
    """토픽 성과 데이터."""
    topic: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    content_count: int = 0

    @property
    def engagement_rate(self) -> float:
        """참여율: (좋아요+댓글) / 조회수."""
        if self.views == 0:
            return 0.0
        return (self.likes + self.comments) / self.views

    @property
    def performance_score(self) -> float:
        """종합 성과 점수 (0~100)."""
        # 조회수 가중치 60%, 참여율 가중치 40%
        view_score = min(self.views / 1000, 50) * 1.2  # max 60
        engagement_score = min(self.engagement_rate * 1000, 40)  # max 40
        return round(view_score + engagement_score, 1)


# ── 시리즈 후속편 제목 템플릿 ─────────────────────────────
SERIES_TEMPLATES = [
    "{topic} Part {ep} — 더 충격적인 후속편",
    "{topic} 시즌 {ep} — 그 후 어떻게 됐을까?",
    "{topic} 완결편 — 최종 결론은?",
    "[속보] {topic} 업데이트 #{ep}",
    "{topic}의 반전 Part {ep}",
]


class SeriesEngine:
    """콘텐츠 시리즈화 엔진.

    고성과 토픽을 감지하고, 후속편 시리즈를 자동으로 제안합니다.

    Args:
        output_dir: 매니페스트가 저장된 output 디렉토리
        min_performance_score: 시리즈화 최소 성과 점수 (기본: 30)
        max_episodes: 시리즈 최대 에피소드 수 (기본: 5)
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        min_performance_score: float = 30.0,
        max_episodes: int = 5,
    ) -> None:
        self.output_dir = output_dir
        self.min_performance_score = min_performance_score
        self.max_episodes = max_episodes
        self._series_registry: dict[str, list[SeriesPlan]] = {}

    def analyze_topics(
        self,
        performance_data: list[dict[str, Any]] | None = None,
    ) -> list[TopicPerformance]:
        """토픽별 성과 분석.

        Args:
            performance_data: [{"topic": str, "views": int, "likes": int, "comments": int}, ...]
                             None이면 output_dir에서 매니페스트 스캔.

        Returns:
            성과 점수 내림차순 정렬된 TopicPerformance 리스트
        """
        if performance_data is None:
            performance_data = self._scan_manifests()

        # 토픽별 집계
        topic_map: dict[str, TopicPerformance] = {}
        for item in performance_data:
            topic = item.get("topic", "").strip()
            if not topic:
                continue

            if topic not in topic_map:
                topic_map[topic] = TopicPerformance(topic=topic)

            tp = topic_map[topic]
            tp.views += item.get("views", 0)
            tp.likes += item.get("likes", 0)
            tp.comments += item.get("comments", 0)
            tp.content_count += 1

        result = sorted(
            topic_map.values(),
            key=lambda t: t.performance_score,
            reverse=True,
        )
        return result

    def suggest_next(
        self,
        topic: str,
        performance_data: list[dict[str, Any]] | None = None,
    ) -> SeriesPlan | None:
        """특정 토픽의 시리즈 후속편 제안.

        Args:
            topic: 원본 토픽
            performance_data: 성과 데이터 (없으면 내부 분석)

        Returns:
            SeriesPlan 또는 성과 미달 시 None
        """
        topics = self.analyze_topics(performance_data)
        target = next((t for t in topics if t.topic == topic), None)

        if target is None:
            logger.info("[Series] 토픽 '%s' 성과 데이터 없음", topic)
            return None

        if target.performance_score < self.min_performance_score:
            logger.info(
                "[Series] '%s' 성과 점수 %.1f < 기준 %.1f → 시리즈화 부적합",
                topic,
                target.performance_score,
                self.min_performance_score,
            )
            return None

        # 기존 시리즈 찾기
        series_id = self._make_series_id(topic)
        existing = self._series_registry.get(series_id, [])
        next_ep = len(existing) + 2  # Part 1은 원본

        if next_ep > self.max_episodes:
            logger.info(
                "[Series] '%s' 최대 에피소드(%d) 초과 → 시리즈 종료",
                topic,
                self.max_episodes,
            )
            return None

        # 제목 템플릿 선택
        template_idx = (next_ep - 2) % len(SERIES_TEMPLATES)
        title = SERIES_TEMPLATES[template_idx].format(topic=topic, ep=next_ep)

        # 이전 편 요약 생성
        prev_summary = ""
        if existing:
            prev_summary = f"이전 편({existing[-1].suggested_title})에서 이어지는 내용입니다."
        else:
            prev_summary = f"이전 편('{topic}')에서 큰 반응을 얻은 후속편입니다."

        plan = SeriesPlan(
            series_id=series_id,
            parent_topic=topic,
            episode=next_ep,
            suggested_title=title,
            prev_summary=prev_summary,
            performance_score=target.performance_score,
        )

        # 레지스트리 등록
        if series_id not in self._series_registry:
            self._series_registry[series_id] = []
        self._series_registry[series_id].append(plan)

        logger.info(
            "[Series] 후속편 제안: '%s' (EP%d, 점수=%.1f)",
            title,
            next_ep,
            target.performance_score,
        )
        return plan

    def get_top_series_candidates(
        self,
        performance_data: list[dict[str, Any]] | None = None,
        top_n: int = 5,
    ) -> list[SeriesPlan]:
        """상위 N개 시리즈 후보 토픽의 후속편 제안.

        Returns:
            SeriesPlan 리스트 (최대 top_n개)
        """
        topics = self.analyze_topics(performance_data)
        candidates = []

        for tp in topics[:top_n * 2]:  # 필터링 여유분
            plan = self.suggest_next(tp.topic, performance_data)
            if plan is not None:
                candidates.append(plan)
            if len(candidates) >= top_n:
                break

        return candidates

    @staticmethod
    def _make_series_id(topic: str) -> str:
        """토픽에서 시리즈 ID 생성."""
        clean = topic.strip().lower().replace(" ", "_")[:40]
        return f"series_{clean}"

    def _scan_manifests(self) -> list[dict[str, Any]]:
        """output_dir에서 매니페스트 파일을 스캔하여 성과 데이터 추출."""
        if not self.output_dir or not self.output_dir.exists():
            return []

        results = []
        for f in self.output_dir.glob("*_manifest.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("status") == "success":
                    results.append({
                        "topic": data.get("topic", ""),
                        "views": 0,  # 매니페스트에는 조회수 없음
                        "likes": 0,
                        "comments": 0,
                    })
            except Exception:
                continue
        return results
