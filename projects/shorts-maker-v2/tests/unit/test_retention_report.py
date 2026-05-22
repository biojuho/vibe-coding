"""Unit tests — retention_report.build_retention_report.

검증 범위:
  - 데이터 부재 시 예외 없이 안내 리포트를 반환한다.
  - 시뮬레이션 dict 가 있으면 요약/곡선/이탈/페르소나 섹션을 채운다.
  - autofix / hints 섹션은 데이터가 있을 때만 나타난다.
  - JobManifest 객체·속성 폴백 입력도 처리한다.
  - 비정상 값(None, 범위 초과, 비-dict 항목)에도 죽지 않는다.
"""

from __future__ import annotations

from shorts_maker_v2.models import JobManifest
from shorts_maker_v2.utils.retention_report import build_retention_report


def _sim_dict() -> dict:
    return {
        "predicted_retention": 0.62,
        "loop_probability": 0.41,
        "retention_curve": [
            {"scene_id": 1, "role": "hook", "viewers_remaining": 0.95, "drop_reason": "ok"},
            {"scene_id": 2, "role": "insight", "viewers_remaining": 0.7, "drop_reason": "slow"},
            {"scene_id": 3, "role": "closing", "viewers_remaining": 0.62, "drop_reason": "end"},
        ],
        "persona_breakdown": [
            {"name": "scroller", "swiped_at_scene": 2, "note": "left early"},
            {"name": "completionist", "swiped_at_scene": None, "note": "watched all"},
        ],
        "first_dropoff_scene_id": 2,
        "weakest_scene_id": 2,
        "rewrite_directive": "씬 2를 압축",
        "verdict": "degraded",
        "feedback": "중간이 늘어진다",
        "source": "llm",
    }


# ── 데이터 부재 ─────────────────────────────────────────────────────


class TestNoData:
    def test_no_simulation_returns_notice(self) -> None:
        md = build_retention_report({"title": "빈 영상"})
        assert "리텐션 리포트" in md
        assert "빈 영상" in md
        assert "데이터가 없습니다" in md

    def test_empty_dict_does_not_raise(self) -> None:
        md = build_retention_report({})
        assert "제목 없음" in md

    def test_topic_used_when_no_title(self) -> None:
        md = build_retention_report({"topic": "주제만 있음"})
        assert "주제만 있음" in md


# ── 시뮬레이션 섹션 ─────────────────────────────────────────────────


class TestSimulationSections:
    def test_full_report_has_all_core_sections(self) -> None:
        md = build_retention_report({"title": "T", "job_id": "J1", "retention_simulation": _sim_dict()})
        assert "## 예측 요약" in md
        assert "## 리텐션 곡선" in md
        assert "## 이탈 분석" in md
        assert "## 페르소나별 이탈" in md
        assert "J1" in md

    def test_summary_renders_percent_and_verdict(self) -> None:
        md = build_retention_report({"retention_simulation": _sim_dict()})
        assert "62%" in md  # predicted_retention
        assert "41%" in md  # loop_probability
        assert "degraded" in md
        assert "LLM 시뮬레이션" in md

    def test_curve_table_lists_every_scene(self) -> None:
        md = build_retention_report({"retention_simulation": _sim_dict()})
        for sid in (1, 2, 3):
            assert f"| {sid} |" in md
        assert "hook" in md and "insight" in md and "closing" in md

    def test_dropoff_section_shows_weakest_and_directive(self) -> None:
        md = build_retention_report({"retention_simulation": _sim_dict()})
        assert "씬 2를 압축" in md
        assert "가장 약한 씬" in md

    def test_persona_section_handles_none_swipe(self) -> None:
        md = build_retention_report({"retention_simulation": _sim_dict()})
        assert "끝까지 시청" in md
        assert "씬 2" in md

    def test_heuristic_source_label(self) -> None:
        sim = _sim_dict()
        sim["source"] = "heuristic"
        md = build_retention_report({"retention_simulation": sim})
        assert "휴리스틱" in md


# ── autofix / hints ────────────────────────────────────────────────


class TestOptionalSections:
    def test_autofix_section_present_when_data_exists(self) -> None:
        md = build_retention_report(
            {
                "retention_simulation": _sim_dict(),
                "retention_autofix": {
                    "verdict": "improved",
                    "before_retention": 0.4,
                    "after_retention": 0.66,
                    "feedback": "씬 2 재작성",
                    "rewrites": [{"scene_id": 2, "accepted": True, "before": "옛 나레이션", "after": "새 나레이션"}],
                },
            }
        )
        assert "자가 치유" in md
        assert "40% → 66%" in md
        assert "✅" in md

    def test_autofix_section_absent_without_data(self) -> None:
        md = build_retention_report({"retention_simulation": _sim_dict()})
        assert "자가 치유" not in md

    def test_autofix_applied_to_render_is_flagged(self) -> None:
        md = build_retention_report(
            {
                "retention_simulation": _sim_dict(),
                "retention_autofix": {
                    "verdict": "improved",
                    "before_retention": 0.3,
                    "after_retention": 0.6,
                    "applied_to_render": True,
                    "feedback": "반영됨",
                    "rewrites": [],
                },
            }
        )
        assert "실제 렌더 대본에 반영됨" in md

    def test_autofix_advisory_only_is_flagged(self) -> None:
        md = build_retention_report(
            {
                "retention_simulation": _sim_dict(),
                "retention_autofix": {
                    "verdict": "improved",
                    "before_retention": 0.3,
                    "after_retention": 0.6,
                    "applied_to_render": False,
                    "feedback": "advisory",
                    "rewrites": [],
                },
            }
        )
        assert "advisory 기록만" in md

    def test_hints_section_present_when_data_exists(self) -> None:
        md = build_retention_report(
            {
                "retention_simulation": _sim_dict(),
                "retention_hints": {
                    "estimated_retention_score": 0.8,
                    "loop_potential": 0.5,
                    "hints": [{"category": "pacing", "severity": "warning", "message": "단조로움"}],
                },
            }
        )
        assert "휴리스틱 힌트" in md
        assert "단조로움" in md

    def test_hints_render_even_without_simulation(self) -> None:
        md = build_retention_report({"retention_hints": {"estimated_retention_score": 0.7, "hints": []}})
        assert "데이터가 없습니다" in md
        assert "휴리스틱 힌트" in md


# ── 입력 형태 / 견고성 ──────────────────────────────────────────────


class TestInputHandling:
    def test_accepts_job_manifest_object(self) -> None:
        manifest = JobManifest(job_id="J9", topic="매니페스트 객체", status="ok")
        manifest.retention_simulation = _sim_dict()
        md = build_retention_report(manifest)
        assert "J9" in md
        assert "## 예측 요약" in md

    def test_accepts_object_without_to_dict(self) -> None:
        class _Bag:
            title = "속성 폴백"
            topic = "t"
            job_id = "JX"
            retention_simulation = None
            retention_autofix = None
            retention_hints = None

        md = build_retention_report(_Bag())
        assert "속성 폴백" in md

    def test_malformed_curve_items_are_skipped(self) -> None:
        sim = _sim_dict()
        sim["retention_curve"] = [
            {"scene_id": 1, "role": "hook", "viewers_remaining": 0.9, "drop_reason": "ok"},
            "not a dict",
            None,
        ]
        md = build_retention_report({"retention_simulation": sim})
        assert "| 1 |" in md  # 유효 항목은 살아남는다

    def test_none_and_out_of_range_values_do_not_crash(self) -> None:
        sim = {
            "predicted_retention": None,
            "loop_probability": 5.0,  # 범위 초과
            "retention_curve": [{"scene_id": 1, "viewers_remaining": -3.0}],
            "persona_breakdown": [],
            "verdict": "error",
            "source": "llm",
        }
        md = build_retention_report({"retention_simulation": sim})
        assert "리텐션 리포트" in md
        assert "100%" in md  # 5.0 은 100% 로 클램프
