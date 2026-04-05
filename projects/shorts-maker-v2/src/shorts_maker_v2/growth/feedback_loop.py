"""Closed-loop growth primitives for post-publish learning.

Step 1 intentionally keeps the engine lightweight:

- accept normalized metrics from any source
- update the existing StyleTracker
- rank experimental variants
- recommend the next series follow-up

Recommended follow-up runtime packages for the real metrics adapter:
- google-api-python-client
- google-auth-oauthlib
- google-auth-httplib2
- requests
- duckdb (optional)
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any, Protocol

from shorts_maker_v2.growth.models import (
    GrowthAction,
    GrowthLoopReport,
    VariantField,
    VariantPerformance,
    VideoPerformanceSnapshot,
)
from shorts_maker_v2.utils.style_tracker import StyleTracker


class MetricsSource(Protocol):
    """Adapter contract for YouTube/warehouse metric providers."""

    def fetch_video_snapshots(
        self,
        *,
        video_ids: Sequence[str],
        channel: str = "",
        since: datetime | None = None,
    ) -> list[VideoPerformanceSnapshot]:
        """Return normalized performance snapshots for the requested videos."""


class SeriesPlanner(Protocol):
    """Minimal contract for optional series recommendation engines."""

    def get_top_series_candidates(
        self,
        performance_data: list[dict[str, Any]] | None = None,
        top_n: int = 5,
    ) -> list[Any]:
        """Return top follow-up candidates ordered by desirability."""


class GrowthLoopEngine:
    """Post-publish optimizer that learns from live audience response."""

    def __init__(
        self,
        output_dir: Path,
        *,
        style_tracker: StyleTracker | None = None,
        series_engine: SeriesPlanner | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.style_tracker = style_tracker or StyleTracker(self.output_dir)
        self.series_engine = series_engine

    def ingest_style_feedback(
        self,
        *,
        channel: str,
        snapshots: Sequence[VideoPerformanceSnapshot],
        variant_field: VariantField = "caption_combo",
    ) -> int:
        """Push live performance back into the existing StyleTracker.

        Returns the number of snapshots that successfully updated the tracker.
        """

        recorded = 0
        for snapshot in snapshots:
            variant_value = snapshot.metadata.get(variant_field, "").strip()
            if not variant_value:
                continue
            self.style_tracker.record_performance(
                channel,
                variant_value,
                views=snapshot.views,
                likes=snapshot.likes,
            )
            recorded += 1
        return recorded

    def analyze_variants(
        self,
        *,
        snapshots: Sequence[VideoPerformanceSnapshot],
        variant_field: VariantField = "caption_combo",
    ) -> list[VariantPerformance]:
        """Aggregate variant arms into ranked performance records."""

        grouped: dict[str, list[VideoPerformanceSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            key = snapshot.metadata.get(variant_field, "").strip()
            if key:
                grouped[key].append(snapshot)

        rankings: list[VariantPerformance] = []
        for variant, items in grouped.items():
            avg_watch_pct = fmean(item.average_view_percentage for item in items) if items else 0.0
            avg_watch_dur = fmean(item.average_view_duration_sec for item in items) if items else 0.0
            total_views = sum(item.views for item in items)
            total_likes = sum(item.likes for item in items)
            total_comments = sum(item.comments for item in items)
            score = self._score_variant(
                total_views=total_views,
                total_likes=total_likes,
                total_comments=total_comments,
                average_view_percentage=avg_watch_pct,
            )
            rankings.append(
                VariantPerformance(
                    field=variant_field,
                    variant=variant,
                    videos=len(items),
                    total_views=total_views,
                    total_likes=total_likes,
                    total_comments=total_comments,
                    average_view_percentage=round(avg_watch_pct, 2),
                    average_view_duration_sec=round(avg_watch_dur, 2),
                    score=round(score, 4),
                )
            )

        rankings.sort(key=lambda item: item.score, reverse=True)
        return rankings

    def recommend_series_followup(
        self,
        snapshots: Sequence[VideoPerformanceSnapshot],
    ) -> Any | None:
        """Convert live topic metrics into a next-episode recommendation."""

        if self.series_engine is None:
            return None

        performance_data = [
            {
                "topic": snapshot.topic,
                "views": snapshot.views,
                "likes": snapshot.likes,
                "comments": snapshot.comments,
            }
            for snapshot in snapshots
        ]
        candidates = self.series_engine.get_top_series_candidates(performance_data, top_n=1)
        return candidates[0] if candidates else None

    def generate_report(
        self,
        *,
        channel: str,
        snapshots: Sequence[VideoPerformanceSnapshot],
        variant_field: VariantField = "caption_combo",
    ) -> GrowthLoopReport:
        """Analyze recent performance and emit ranked next actions."""

        self.ingest_style_feedback(channel=channel, snapshots=snapshots, variant_field=variant_field)
        ranked_variants = self.analyze_variants(snapshots=snapshots, variant_field=variant_field)
        actions: list[GrowthAction] = []

        if ranked_variants:
            top_variant = ranked_variants[0]
            actions.append(
                GrowthAction(
                    kind="double_down",
                    target=top_variant.variant,
                    rationale=(
                        f"{variant_field} '{top_variant.variant}' scored highest "
                        f"with engagement {top_variant.engagement_rate:.2%}."
                    ),
                    score=top_variant.score,
                    metadata={"variant_field": variant_field},
                )
            )

        next_combo = self.style_tracker.get_weighted_combo(channel)
        if next_combo:
            actions.append(
                GrowthAction(
                    kind="probe",
                    target=next_combo,
                    rationale="Reuse the highest-upside caption combo suggested by Thompson sampling.",
                    score=0.5,
                    metadata={"variant_field": "caption_combo"},
                )
            )

        series_plan = self.recommend_series_followup(snapshots)
        if series_plan is not None:
            actions.append(
                GrowthAction(
                    kind="schedule_followup",
                    target=series_plan.suggested_title,
                    rationale="A previous topic is showing enough audience response to justify a follow-up episode.",
                    score=series_plan.performance_score,
                    metadata=series_plan.to_dict(),
                )
            )

        return GrowthLoopReport(
            channel=channel,
            video_count=len(snapshots),
            analyzed_variant_field=variant_field,
            ranked_variants=ranked_variants,
            recommended_actions=actions,
        )

    @staticmethod
    def _score_variant(
        *,
        total_views: int,
        total_likes: int,
        total_comments: int,
        average_view_percentage: float,
    ) -> float:
        """Compact heuristic for step 1 ranking.

        The first version favors:
        - observable audience response
        - watch quality
        - enough sample size to avoid overreacting to tiny tests
        """

        if total_views <= 0:
            return 0.0

        engagement_rate = (total_likes + total_comments) / total_views
        watch_quality = max(0.0, min(average_view_percentage / 100.0, 1.0))
        sample_bonus = min(total_views / 5000.0, 1.0)
        return (engagement_rate * 0.45) + (watch_quality * 0.35) + (sample_bonus * 0.20)
