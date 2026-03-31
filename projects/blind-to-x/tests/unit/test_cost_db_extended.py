from __future__ import annotations

from datetime import date, datetime, timedelta
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.cost_db import CostDatabase  # noqa: E402


def _make_db(tmp_path) -> CostDatabase:
    return CostDatabase(tmp_path / "costs.db")


def _insert_draft(
    db: CostDatabase,
    *,
    day: str,
    content_url: str,
    notion_page_id: str = "",
    topic_cluster: str = "career",
    hook_type: str = "hook",
    emotion_axis: str = "emotion",
    draft_style: str = "style-a",
    final_rank_score: float = 0.0,
    published: int = 1,
    published_at: str = "",
    yt_views: int = 0,
    engagement_rate: float = 0.0,
    impression_count: int = 0,
) -> None:
    with db._conn() as conn:
        conn.execute(
            """
            INSERT INTO draft_analytics (
                date,
                content_url,
                notion_page_id,
                source,
                topic_cluster,
                hook_type,
                emotion_axis,
                draft_style,
                provider_used,
                final_rank_score,
                published,
                published_at,
                yt_views,
                engagement_rate,
                impression_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                day,
                content_url,
                notion_page_id,
                "blind",
                topic_cluster,
                hook_type,
                emotion_axis,
                draft_style,
                "gemini",
                final_rank_score,
                published,
                published_at,
                yt_views,
                engagement_rate,
                impression_count,
            ),
        )


def test_provider_failure_state_tracks_skip_windows_and_reset(tmp_path) -> None:
    db = _make_db(tmp_path)

    assert db.get_skipped_providers() == set()
    assert db.get_circuit_skip_hours("gemini") == 0.0

    db.record_provider_failure("gemini", skip_hours=0.5)
    db.record_provider_failure("gemini", skip_hours=1.0)
    db.record_provider_failure("gemini", skip_hours=2.0)

    with db._connect() as conn:
        row = conn.execute(
            "SELECT fail_count, skip_until FROM provider_failures WHERE provider = ?",
            ("gemini",),
        ).fetchone()

    assert row["fail_count"] == 3
    assert row["skip_until"]
    assert "gemini" in db.get_skipped_providers()
    assert db.get_circuit_skip_hours("gemini") == 12.0

    db.record_provider_success("gemini")

    with db._connect() as conn:
        cleared = conn.execute(
            "SELECT fail_count, skip_until FROM provider_failures WHERE provider = ?",
            ("gemini",),
        ).fetchone()

    assert cleared["fail_count"] == 0
    assert cleared["skip_until"] is None
    assert db.get_skipped_providers() == set()
    assert db.get_circuit_skip_hours("gemini") == 0.0


def test_update_draft_scores_and_view_stats_fallback_to_notion_page_id(tmp_path) -> None:
    db = _make_db(tmp_path)
    db.record_draft(
        source="blind",
        topic_cluster="career",
        hook_type="hook",
        emotion_axis="emotion",
        draft_style="style-a",
        provider_used="gemini",
        final_rank_score=71.0,
        notion_page_id="page-1",
    )

    db.update_draft_scores(
        notion_page_id="page-1",
        hook_score=7.2,
        virality_score=8.3,
        fit_score=9.4,
    )
    db.update_draft_view_stats(
        notion_page_id="page-1",
        yt_views=1234,
        engagement_rate=4.6,
        impression_count=4567,
    )

    with db._conn() as conn:
        row = conn.execute(
            """
            SELECT hook_score, virality_score, fit_score, yt_views, engagement_rate, impression_count
            FROM draft_analytics
            WHERE notion_page_id = ?
            """,
            ("page-1",),
        ).fetchone()

    assert row["hook_score"] == 7.2
    assert row["virality_score"] == 8.3
    assert row["fit_score"] == 9.4
    assert row["yt_views"] == 1234
    assert row["engagement_rate"] == 4.6
    assert row["impression_count"] == 4567


def test_daily_trend_combines_text_and_image_costs(tmp_path) -> None:
    db = _make_db(tmp_path)
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    with db._conn() as conn:
        conn.execute(
            """
            INSERT INTO daily_text_costs (date, provider, tokens_input, tokens_output, usd_estimated)
            VALUES (?, ?, ?, ?, ?)
            """,
            (yesterday, "openai", 100, 50, 0.25),
        )
        conn.execute(
            """
            INSERT INTO daily_text_costs (date, provider, tokens_input, tokens_output, usd_estimated)
            VALUES (?, ?, ?, ?, ?)
            """,
            (today, "gemini", 200, 75, 1.5),
        )
        conn.execute(
            """
            INSERT INTO daily_image_costs (date, provider, image_count, usd_estimated)
            VALUES (?, ?, ?, ?)
            """,
            (today, "dalle", 2, 0.4),
        )

    trend = db.get_daily_trend(days=2)

    assert len(trend) == 2
    assert trend[0]["date"] == yesterday
    assert trend[0]["total_usd"] == 0.25
    assert trend[0]["images"] == 0
    assert trend[1]["date"] == today
    assert trend[1]["text_usd"] == 1.5
    assert trend[1]["image_usd"] == 0.4
    assert trend[1]["total_usd"] == 1.9
    assert trend[1]["images"] == 2


def test_style_performance_and_best_style_lookup(tmp_path) -> None:
    db = _make_db(tmp_path)
    today = date.today().isoformat()

    for idx, score in enumerate([70, 71, 72], start=1):
        _insert_draft(
            db,
            day=today,
            content_url=f"https://example.com/a-{idx}",
            topic_cluster="career",
            draft_style="style-a",
            final_rank_score=score,
        )

    for idx, score in enumerate([88, 90, 92], start=1):
        _insert_draft(
            db,
            day=today,
            content_url=f"https://example.com/b-{idx}",
            topic_cluster="career",
            draft_style="style-b",
            final_rank_score=score,
        )

    performance = db.get_draft_style_performance(days=1)
    performance_by_style = {row["draft_style"]: row for row in performance}

    assert performance_by_style["style-a"]["total"] == 3
    assert performance_by_style["style-b"]["total"] == 3
    assert performance_by_style["style-b"]["avg_score"] == 90.0
    assert db.get_best_draft_style_for_cluster("career", min_samples=3, days=1) == "style-b"
    assert db.get_best_draft_style_for_cluster("career", min_samples=4, days=1) is None


def test_recent_insights_and_spikes_return_latest_rows(tmp_path) -> None:
    db = _make_db(tmp_path)

    db.record_cross_source_insight(
        topic_cluster="career",
        sources=["blind", "fmkorea"],
        post_count=3,
        notion_page_id="page-1",
    )
    with db._conn() as conn:
        conn.execute(
            "UPDATE cross_source_insights SET published = 1 WHERE notion_page_id = ?",
            ("page-1",),
        )

    db.record_trend_spike(keyword="layoff", source="blind", score=9.5, matched_topic="career", triggered=True)
    db.record_trend_spike(keyword="office", source="fmkorea", score=4.0, matched_topic="career", triggered=False)

    insights = db.get_recent_insights(days=1)
    spikes = db.get_recent_spikes(days=1)

    assert len(insights) == 1
    assert insights[0]["topic_cluster"] == "career"
    assert '"blind"' in insights[0]["sources"]
    assert insights[0]["published"] == 1
    assert [row["keyword"] for row in spikes] == ["layoff", "office"]
    assert spikes[0]["triggered"] == 1


def test_cost_per_post_and_archive_old_data(tmp_path) -> None:
    db = _make_db(tmp_path)
    old_day = (date.today() - timedelta(days=120)).isoformat()
    today = date.today().isoformat()

    with db._conn() as conn:
        conn.execute(
            """
            INSERT INTO daily_text_costs (date, provider, tokens_input, tokens_output, usd_estimated)
            VALUES (?, ?, ?, ?, ?)
            """,
            (old_day, "openai", 100, 50, 2.0),
        )
        conn.execute(
            """
            INSERT INTO daily_image_costs (date, provider, image_count, usd_estimated)
            VALUES (?, ?, ?, ?)
            """,
            (old_day, "dalle", 1, 1.0),
        )
        conn.execute(
            """
            INSERT INTO cross_source_insights (date, topic_cluster, sources, post_count, notion_page_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (old_day, "career", "[]", 2, "page-old"),
        )
        conn.execute(
            """
            INSERT INTO trend_spikes (date, keyword, source, score, matched_topic, triggered)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (old_day, "layoff", "blind", 7.0, "career", 1),
        )

    _insert_draft(db, day=old_day, content_url="https://example.com/old-1", final_rank_score=70)
    _insert_draft(db, day=old_day, content_url="https://example.com/old-2", final_rank_score=75)
    _insert_draft(db, day=today, content_url="https://example.com/new-1", final_rank_score=90)

    cpp = db.get_cost_per_post(days=365)
    assert cpp == {"avg_cost_per_post": 1.0, "total_cost": 3.0, "total_posts": 3}

    archived = db.archive_old_data(days=90)

    assert archived["daily_text_costs"] == 1
    assert archived["daily_image_costs"] == 1
    assert archived["draft_analytics"] == 2
    assert archived["cross_source_insights"] == 1
    assert archived["trend_spikes"] == 1

    archive_files = list(tmp_path.glob("btx_costs_archive_*.db"))
    assert len(archive_files) == 1

    with db._conn() as conn:
        remaining_drafts = conn.execute("SELECT COUNT(*) AS cnt FROM draft_analytics").fetchone()
        remaining_text = conn.execute("SELECT COUNT(*) AS cnt FROM daily_text_costs").fetchone()

    assert remaining_drafts["cnt"] == 1
    assert remaining_text["cnt"] == 0

    archive_conn = sqlite3.connect(str(archive_files[0]))
    try:
        archived_drafts = archive_conn.execute("SELECT COUNT(*) FROM draft_analytics").fetchone()[0]
        archived_text = archive_conn.execute("SELECT COUNT(*) FROM daily_text_costs").fetchone()[0]
    finally:
        archive_conn.close()

    assert archived_drafts == 2
    assert archived_text == 1


def test_top_performing_drafts_and_calibrated_weights_roundtrip(tmp_path) -> None:
    db = _make_db(tmp_path)

    db.record_draft(
        source="blind",
        topic_cluster="career",
        hook_type="story",
        emotion_axis="curious",
        draft_style="style-a",
        provider_used="gemini",
        final_rank_score=88.0,
        published=True,
        content_url="https://example.com/top",
        notion_page_id="page-top",
    )
    db.record_draft(
        source="blind",
        topic_cluster="career",
        hook_type="question",
        emotion_axis="serious",
        draft_style="style-b",
        provider_used="gemini",
        final_rank_score=65.0,
        published=True,
        content_url="https://example.com/other",
        notion_page_id="page-other",
    )
    db.update_draft_view_stats(
        content_url="https://example.com/top",
        yt_views=5000,
        engagement_rate=8.4,
        impression_count=12000,
    )
    db.update_draft_view_stats(
        content_url="https://example.com/other",
        yt_views=1500,
        engagement_rate=2.0,
        impression_count=8000,
    )

    top = db.get_top_performing_drafts(topic_cluster="career", min_engagement=1.0, limit=1)
    assert top == [
        {
            "topic_cluster": "career",
            "hook_type": "story",
            "emotion_axis": "curious",
            "draft_style": "style-a",
            "text": "https://example.com/top",
            "yt_views": 5000,
            "engagement_rate": 8.4,
        }
    ]

    weights = {"freshness": 0.1, "social": 0.1, "hook": 0.2, "trend": 0.2, "audience": 0.2, "viral": 0.2}
    db.save_calibrated_weights(weights)
    assert db.load_calibrated_weights(max_age_days=7) == weights

    stale_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
    with db._conn() as conn:
        conn.execute("UPDATE calibrated_weights SET calibrated_at = ?", (stale_timestamp,))

    assert db.load_calibrated_weights(max_age_days=7) is None
