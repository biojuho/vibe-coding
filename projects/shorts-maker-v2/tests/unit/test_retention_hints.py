"""Tests for retention_hints module."""

from __future__ import annotations

from shorts_maker_v2.utils.retention_hints import (
    SceneInfo,
    analyze_retention,
)


def _make_scenes(
    durations: list[float],
    roles: list[str] | None = None,
    narr_lengths: list[int] | None = None,
) -> list[SceneInfo]:
    """헬퍼: SceneInfo 리스트 생성."""
    n = len(durations)
    if roles is None:
        roles = ["hook"] + ["body"] * max(0, n - 2) + (["closing"] if n > 1 else [])
    if narr_lengths is None:
        narr_lengths = [int(d * 5) for d in durations]
    return [
        SceneInfo(
            scene_id=i + 1,
            duration_sec=durations[i],
            structure_role=roles[i],
            narration_length=narr_lengths[i],
        )
        for i in range(n)
    ]


class TestAnalyzeRetention:
    """Retention Hints 분석 단위 테스트."""

    def test_optimal_duration_high_score(self):
        """최적 구간(38~45초) 내 총 길이는 높은 점수."""
        scenes = _make_scenes([3, 7, 8, 7, 7, 6, 5])
        report = analyze_retention(scenes)
        assert report.estimated_retention_score >= 0.8

    def test_over_60sec_critical_hint(self):
        """60초 초과 시 critical 힌트 발생."""
        scenes = _make_scenes([10, 15, 15, 15, 10])
        report = analyze_retention(scenes)
        critical_hints = [h for h in report.hints if h.severity == "critical"]
        assert len(critical_hints) > 0
        assert any("60초" in h.message for h in critical_hints)

    def test_long_hook_warning(self):
        """Hook이 5초 초과 시 warning."""
        scenes = _make_scenes([8, 7, 7, 7], roles=["hook", "body", "body", "closing"])
        report = analyze_retention(scenes)
        hook_hints = [h for h in report.hints if h.category == "hook"]
        assert len(hook_hints) > 0

    def test_monotonous_pacing_warning(self):
        """씬 길이가 모두 동일하면 pacing warning."""
        scenes = _make_scenes([7, 7, 7, 7, 7])
        report = analyze_retention(scenes)
        pacing_hints = [h for h in report.hints if h.category == "pacing"]
        assert len(pacing_hints) > 0

    def test_varied_pacing_no_warning(self):
        """다양한 씬 길이면 pacing warning 없음."""
        scenes = _make_scenes([3, 8, 5, 10, 4, 6])
        report = analyze_retention(scenes)
        pacing_uniform = [h for h in report.hints if h.category == "pacing" and "분산" in h.message]
        assert len(pacing_uniform) == 0

    def test_short_scene_info_hint(self):
        """2.5초 미만 씬은 info 힌트."""
        scenes = _make_scenes([2, 7, 7, 7], roles=["hook", "body", "body", "closing"])
        report = analyze_retention(scenes)
        short_hints = [h for h in report.hints if h.category == "pacing" and h.scene_id == 1 and "짧" in h.message]
        assert len(short_hints) > 0

    def test_loop_potential_short_closing(self):
        """마지막 씬이 짧으면 루핑 잠재력 증가."""
        scenes = _make_scenes(
            [3, 7, 7, 3],
            roles=["hook", "body", "body", "closing"],
            narr_lengths=[12, 35, 35, 12],
        )
        report = analyze_retention(scenes)
        assert report.loop_potential >= 0.3

    def test_empty_scenes_no_crash(self):
        """빈 씬 리스트도 크래시 없이 처리."""
        report = analyze_retention([])
        assert report.estimated_retention_score >= 0.0
        assert report.loop_potential == 0.0

    def test_report_to_dict(self):
        """to_dict() 구조 확인."""
        scenes = _make_scenes([3, 7, 7, 7])
        report = analyze_retention(scenes)
        d = report.to_dict()
        assert "estimated_retention_score" in d
        assert "loop_potential" in d
        assert "hints" in d
        assert isinstance(d["hints"], list)

    def test_under_optimal_info(self):
        """최적 구간보다 짧으면 info 힌트."""
        scenes = _make_scenes([3, 5, 5, 5])
        report = analyze_retention(scenes)
        dur_hints = [h for h in report.hints if h.category == "duration"]
        assert any("짧음" in h.message for h in dur_hints)
