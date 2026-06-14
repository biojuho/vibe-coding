"""T4-3: Series Engine 단위 테스트."""

from __future__ import annotations

from shorts_maker_v2.pipeline.series_engine import (
    SeriesEngine,
    SeriesPlan,
    TopicPerformance,
)


def test_topic_performance_score_zero_views() -> None:
    tp = TopicPerformance(topic="test", views=0)
    assert tp.performance_score == 0.0
    assert tp.engagement_rate == 0.0


def test_topic_performance_score_with_data() -> None:
    tp = TopicPerformance(topic="hot", views=5000, likes=200, comments=50)
    score = tp.performance_score
    assert score > 0
    assert tp.engagement_rate > 0


def test_topic_performance_engagement() -> None:
    tp = TopicPerformance(topic="t", views=1000, likes=100, comments=50)
    assert tp.engagement_rate == 0.15  # (100+50)/1000


def test_analyze_topics_empty() -> None:
    engine = SeriesEngine()
    result = engine.analyze_topics(performance_data=[])
    assert result == []


def test_analyze_topics_aggregation() -> None:
    engine = SeriesEngine()
    data = [
        {"topic": "AI", "views": 1000, "likes": 50, "comments": 10},
        {"topic": "AI", "views": 2000, "likes": 100, "comments": 20},
        {"topic": "Crypto", "views": 500, "likes": 10, "comments": 5},
    ]
    topics = engine.analyze_topics(data)
    assert len(topics) == 2

    ai = next(t for t in topics if t.topic == "AI")
    assert ai.views == 3000
    assert ai.likes == 150
    assert ai.content_count == 2


def test_analyze_topics_sorted_by_score() -> None:
    engine = SeriesEngine()
    data = [
        {"topic": "Low", "views": 10, "likes": 0, "comments": 0},
        {"topic": "High", "views": 5000, "likes": 200, "comments": 50},
    ]
    topics = engine.analyze_topics(data)
    assert topics[0].topic == "High"
    assert topics[1].topic == "Low"


def test_suggest_next_no_data() -> None:
    engine = SeriesEngine()
    result = engine.suggest_next("없는토픽", performance_data=[])
    assert result is None


def test_suggest_next_low_score() -> None:
    engine = SeriesEngine(min_performance_score=50.0)
    data = [{"topic": "Low", "views": 10, "likes": 0, "comments": 0}]
    result = engine.suggest_next("Low", performance_data=data)
    assert result is None


def test_suggest_next_success() -> None:
    engine = SeriesEngine(min_performance_score=10.0)
    data = [
        {"topic": "Hot Topic", "views": 5000, "likes": 200, "comments": 50},
    ]
    result = engine.suggest_next("Hot Topic", performance_data=data)
    assert result is not None
    assert isinstance(result, SeriesPlan)
    assert result.parent_topic == "Hot Topic"
    assert result.episode == 2
    assert "Hot Topic" in result.suggested_title


def test_suggest_next_increments_episodes() -> None:
    engine = SeriesEngine(min_performance_score=10.0)
    data = [
        {"topic": "Series", "views": 3000, "likes": 100, "comments": 30},
    ]
    ep2 = engine.suggest_next("Series", performance_data=data)
    ep3 = engine.suggest_next("Series", performance_data=data)
    assert ep2 is not None
    assert ep3 is not None
    assert ep2.episode == 2
    assert ep3.episode == 3


def test_suggest_next_max_episodes() -> None:
    engine = SeriesEngine(min_performance_score=1.0, max_episodes=3)
    data = [{"topic": "T", "views": 3000, "likes": 100, "comments": 30}]
    engine.suggest_next("T", performance_data=data)  # ep2
    engine.suggest_next("T", performance_data=data)  # ep3
    result = engine.suggest_next("T", performance_data=data)  # ep4 → should be None
    assert result is None


def test_get_top_series_candidates() -> None:
    engine = SeriesEngine(min_performance_score=10.0)
    data = [
        {"topic": "A", "views": 5000, "likes": 200, "comments": 50},
        {"topic": "B", "views": 3000, "likes": 100, "comments": 20},
        {"topic": "C", "views": 10, "likes": 0, "comments": 0},
    ]
    candidates = engine.get_top_series_candidates(data, top_n=2)
    assert len(candidates) <= 2
    topics = {c.parent_topic for c in candidates}
    assert "A" in topics


def test_series_plan_to_dict() -> None:
    plan = SeriesPlan(
        series_id="series_test",
        parent_topic="Test",
        episode=2,
        suggested_title="Test Part 2",
    )
    d = plan.to_dict()
    assert d["series_id"] == "series_test"
    assert d["episode"] == 2


def test_make_series_id() -> None:
    sid = SeriesEngine._make_series_id("AI가 바꾸는 미래")
    assert sid.startswith("series_")
    assert " " not in sid


class TestScanManifests:
    """_scan_manifests: corrupt JSON은 스킵, success 매니페스트만 반환."""

    def test_returns_empty_when_no_output_dir(self) -> None:
        engine = SeriesEngine()
        assert engine._scan_manifests() == []

    def test_returns_empty_when_dir_missing(self, tmp_path) -> None:
        engine = SeriesEngine(output_dir=tmp_path / "missing")
        assert engine._scan_manifests() == []

    def test_skips_non_success_manifests(self, tmp_path) -> None:
        (tmp_path / "ep1_manifest.json").write_text('{"status": "degraded", "topic": "AI"}', encoding="utf-8")
        engine = SeriesEngine(output_dir=tmp_path)
        assert engine._scan_manifests() == []

    def test_returns_success_manifest(self, tmp_path) -> None:
        (tmp_path / "ep1_manifest.json").write_text('{"status": "success", "topic": "AI 미래"}', encoding="utf-8")
        engine = SeriesEngine(output_dir=tmp_path)
        results = engine._scan_manifests()
        assert len(results) == 1
        assert results[0]["topic"] == "AI 미래"
        assert results[0]["views"] == 0

    def test_skips_corrupt_json_without_raising(self, tmp_path) -> None:
        (tmp_path / "bad_manifest.json").write_text("not-valid-json{{{", encoding="utf-8")
        (tmp_path / "good_manifest.json").write_text('{"status": "success", "topic": "우주"}', encoding="utf-8")
        engine = SeriesEngine(output_dir=tmp_path)
        results = engine._scan_manifests()
        assert len(results) == 1
        assert results[0]["topic"] == "우주"

    def test_multiple_success_manifests(self, tmp_path) -> None:
        for i, topic in enumerate(["AI", "역사", "심리학"]):
            (tmp_path / f"ep{i}_manifest.json").write_text(
                f'{{"status": "success", "topic": "{topic}"}}', encoding="utf-8"
            )
        engine = SeriesEngine(output_dir=tmp_path)
        results = engine._scan_manifests()
        assert len(results) == 3
        topics = {r["topic"] for r in results}
        assert topics == {"AI", "역사", "심리학"}
