"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ContentProfile:
    topic_cluster: str
    hook_type: str
    emotion_axis: str
    audience_fit: str
    recommended_draft_type: str
    scrape_quality_score: float
    publishability_score: float
    performance_score: float
    final_rank_score: float
    rationale: list[str]
    selection_summary: str = ""
    selection_reason_labels: list[str] = field(default_factory=list)
    audience_need: str = ""
    emotion_lane: str = ""
    empathy_anchor: str = ""
    spinoff_angle: str = ""
    # Phase 4-B: 6D quality scorecard (optional — zero when not computed)
    freshness_score: float = 0.0  # 15% — 게시글 신선도 (시간 기반)
    social_signal_score: float = 0.0  # 25% — 좋아요·댓글 소셜 신호
    hook_strength_score: float = 0.0  # 20% — 제목·훅 강도
    trend_relevance_score: float = 0.0  # 15% — 토픽 클러스터 트렌드 적합도
    audience_targeting_score: float = 0.0  # 15% — 독자 타게팅 정확도
    viral_potential_score: float = 0.0  # 10% — 감정 축 바이럴 잠재력
    rank_6d: float = 0.0  # 가중합 최종 점수 (0-100)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scrape_quality_score"] = round(self.scrape_quality_score, 2)
        payload["publishability_score"] = round(self.publishability_score, 2)
        payload["performance_score"] = round(self.performance_score, 2)
        payload["final_rank_score"] = round(self.final_rank_score, 2)
        payload["rank_6d"] = round(self.rank_6d, 2)
        return payload
