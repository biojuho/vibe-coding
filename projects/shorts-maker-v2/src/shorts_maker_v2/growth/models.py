from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

VariantField = Literal[
    "caption_combo",
    "hook_pattern",
    "title_variant",
    "thumbnail_variant",
]

ActionKind = Literal[
    "double_down",
    "probe",
    "retire",
    "schedule_followup",
]


@dataclass(frozen=True)
class VideoPerformanceSnapshot:
    """Canonical post-publish metrics for a single Short."""

    video_id: str
    channel: str
    topic: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    average_view_duration_sec: float = 0.0
    average_view_percentage: float = 0.0
    engaged_views: int = 0
    subscribers_gained: int = 0
    impressions: int = 0
    impressions_ctr: float = 0.0
    shares: int = 0
    revenue_usd: float = 0.0
    published_at: datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def engagement_rate(self) -> float:
        if self.views <= 0:
            return 0.0
        return (self.likes + self.comments) / self.views

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.published_at is not None:
            payload["published_at"] = self.published_at.isoformat()
        return payload


@dataclass(frozen=True)
class VariantPerformance:
    """Aggregated performance for one experimental arm."""

    field: VariantField
    variant: str
    videos: int
    total_views: int
    total_likes: int
    total_comments: int
    average_view_percentage: float
    average_view_duration_sec: float
    score: float

    @property
    def engagement_rate(self) -> float:
        if self.total_views <= 0:
            return 0.0
        return (self.total_likes + self.total_comments) / self.total_views

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GrowthAction:
    """Single recommended next action from the feedback loop."""

    kind: ActionKind
    target: str
    rationale: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GrowthLoopReport:
    """Top-level artifact returned by the growth engine."""

    channel: str
    video_count: int
    analyzed_variant_field: VariantField
    ranked_variants: list[VariantPerformance]
    recommended_actions: list[GrowthAction]

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "video_count": self.video_count,
            "analyzed_variant_field": self.analyzed_variant_field,
            "ranked_variants": [item.to_dict() for item in self.ranked_variants],
            "recommended_actions": [item.to_dict() for item in self.recommended_actions],
        }
