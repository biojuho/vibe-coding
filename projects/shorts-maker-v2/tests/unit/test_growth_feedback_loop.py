from __future__ import annotations

from pathlib import Path

from shorts_maker_v2.growth.feedback_loop import GrowthLoopEngine
from shorts_maker_v2.growth.models import VideoPerformanceSnapshot
from shorts_maker_v2.utils.style_tracker import StyleTracker


class _SeriesStub:
    def get_top_series_candidates(self, performance_data=None, top_n: int = 5):
        if not performance_data:
            return []
        return [
            type(
                "SeriesPlanStub",
                (),
                {
                    "suggested_title": f"{performance_data[0]['topic']} Part 2",
                    "performance_score": 88.0,
                    "to_dict": lambda self: {
                        "suggested_title": f"{performance_data[0]['topic']} Part 2",
                        "performance_score": 88.0,
                    },
                },
            )()
        ]


def _snapshot(
    *,
    video_id: str,
    topic: str,
    caption_combo: str,
    views: int,
    likes: int,
    comments: int,
    avg_pct: float,
) -> VideoPerformanceSnapshot:
    return VideoPerformanceSnapshot(
        video_id=video_id,
        channel="ai_tech",
        topic=topic,
        views=views,
        likes=likes,
        comments=comments,
        average_view_percentage=avg_pct,
        metadata={"caption_combo": caption_combo},
    )


def test_ingest_style_feedback_records_caption_combo(tmp_path: Path) -> None:
    tracker = StyleTracker(tmp_path, db_path=tmp_path / "style.db")
    engine = GrowthLoopEngine(output_dir=tmp_path, style_tracker=tracker)
    snapshots = [
        _snapshot(
            video_id="vid-1",
            topic="AI agents",
            caption_combo="bold_white",
            views=10_000,
            likes=500,
            comments=50,
            avg_pct=72.0,
        )
    ]

    recorded = engine.ingest_style_feedback(channel="ai_tech", snapshots=snapshots)

    assert recorded == 1
    stats = tracker.get_performance_stats("ai_tech")
    assert stats[0]["combo_name"] == "bold_white"
    assert stats[0]["views"] == 10_000


def test_analyze_variants_ranks_better_combo_first(tmp_path: Path) -> None:
    engine = GrowthLoopEngine(output_dir=tmp_path)
    snapshots = [
        _snapshot(
            video_id="vid-1",
            topic="AI agents",
            caption_combo="winner",
            views=12_000,
            likes=700,
            comments=120,
            avg_pct=74.0,
        ),
        _snapshot(
            video_id="vid-2",
            topic="AI agents",
            caption_combo="winner",
            views=9_000,
            likes=430,
            comments=90,
            avg_pct=69.0,
        ),
        _snapshot(
            video_id="vid-3",
            topic="AI agents",
            caption_combo="loser",
            views=9_000,
            likes=120,
            comments=12,
            avg_pct=41.0,
        ),
    ]

    rankings = engine.analyze_variants(snapshots=snapshots)

    assert rankings[0].variant == "winner"
    assert rankings[0].score > rankings[1].score


def test_generate_report_recommends_series_followup(tmp_path: Path) -> None:
    tracker = StyleTracker(tmp_path, db_path=tmp_path / "style.db")
    engine = GrowthLoopEngine(output_dir=tmp_path, style_tracker=tracker, series_engine=_SeriesStub())
    snapshots = [
        _snapshot(
            video_id="vid-1",
            topic="AI agents",
            caption_combo="bold_white",
            views=15_000,
            likes=900,
            comments=160,
            avg_pct=76.0,
        ),
        _snapshot(
            video_id="vid-2",
            topic="AI agents",
            caption_combo="bold_white",
            views=10_000,
            likes=620,
            comments=105,
            avg_pct=71.0,
        ),
    ]

    report = engine.generate_report(channel="ai_tech", snapshots=snapshots)

    assert report.video_count == 2
    assert report.ranked_variants[0].variant == "bold_white"
    assert any(action.kind == "schedule_followup" for action in report.recommended_actions)
