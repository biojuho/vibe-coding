from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest
import tomllib

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


class _DummyBlock:
    def __init__(self, streamlit_module: "_FakeStreamlit") -> None:
        self._streamlit = streamlit_module

    def __enter__(self) -> "_DummyBlock":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def __getattr__(self, name: str):
        return getattr(self._streamlit, name)


class _FakeStreamlit(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.events: list[tuple[str, object, dict]] = []

    def _record(self, name: str, payload: object = None, **kwargs) -> None:
        self.events.append((name, payload, kwargs))

    def set_page_config(self, **kwargs) -> None:
        self._record("set_page_config", kwargs)

    def error(self, message: object) -> None:
        self._record("error", message)

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def tabs(self, labels):
        self._record("tabs", labels)
        return [_DummyBlock(self) for _ in labels]

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def container(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def expander(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def slider(self, label, min_value=None, max_value=None, value=None, **kwargs):
        self._record("slider", label, **kwargs)
        return value

    def dataframe(self, data, **kwargs) -> None:
        self._record("dataframe", data, **kwargs)

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


def _make_content_db_module() -> types.ModuleType:
    module = types.ModuleType("execution.content_db")
    module.init_db = lambda: None
    module.get_kpis = lambda: {
        "total": 0,
        "success_count": 0,
        "failed_count": 0,
        "pending_count": 0,
        "total_cost_usd": 0.0,
        "avg_cost_usd": 0.0,
    }
    module.get_daily_stats = lambda days=30: []
    module.get_channel_stats = lambda: []
    module.get_hourly_stats = lambda days=30: []
    module.get_youtube_stats = lambda: {"uploaded": 0, "failed": 0, "awaiting": 0}
    module.get_performance_stats = lambda: []
    module.get_channel_performance_summary = lambda: []
    module.get_hook_pattern_performance = lambda: []
    return module


@pytest.fixture()
def shorts_analytics(monkeypatch: pytest.MonkeyPatch):
    module_name = "execution.pages.shorts_analytics"
    sys.modules.pop(module_name, None)

    fake_streamlit = _FakeStreamlit()
    fake_plotly = types.ModuleType("plotly")
    fake_px = types.ModuleType("plotly.express")
    fake_go = types.ModuleType("plotly.graph_objects")

    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", fake_px)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_go)
    monkeypatch.setitem(sys.modules, "execution.content_db", _make_content_db_module())

    module = importlib.import_module(module_name)
    yield module
    sys.modules.pop(module_name, None)


def test_youtube_performance_summary_handles_empty_and_missing_values(shorts_analytics) -> None:
    summary = shorts_analytics._summarize_youtube_performance(
        [
            {"yt_views": 1000, "yt_likes": 50, "yt_comments": 10},
            {"yt_views": None, "yt_likes": None, "yt_comments": None},
        ]
    )

    assert summary == {
        "video_count": 2,
        "total_views": 1000,
        "total_likes": 50,
        "total_comments": 10,
        "avg_views": 500.0,
        "like_rate": 5.0,
        "engagement_rate": 6.0,
    }


def test_channel_performance_rows_label_cpv_as_dollars_per_1k(shorts_analytics) -> None:
    rows = shorts_analytics._build_channel_performance_rows(
        [
            {
                "channel": "AI/Tech",
                "video_count": 4,
                "total_views": 2000,
                "avg_views": 500.0,
                "total_cost": 3.0,
            },
            {
                "channel": "우주/천문학",
                "video_count": 1,
                "total_views": 0,
                "avg_views": 0.0,
                "total_cost": 0.25,
            },
        ]
    )

    assert rows[0]["CPV ($/1K views)"] == "$1.50/1K"
    assert rows[0]["채널"] == "AI/기술"
    assert rows[1]["CPV ($/1K views)"] == "-"
    assert "CPV (원/조회)" not in rows[0]


def test_channel_label_aliases_normalize_legacy_raw_channels(shorts_analytics) -> None:
    assert shorts_analytics._display_channel_label("AI/Tech") == "AI/기술"
    assert shorts_analytics._display_channel_label("space") == "우주/천문학"
    assert shorts_analytics._display_channel_label("  history  ") == "역사/고고학"
    assert shorts_analytics._display_channel_label("") == "-"


def test_channel_stats_grouping_merges_legacy_and_canonical_labels(shorts_analytics) -> None:
    rows = shorts_analytics._group_channel_stats_by_display_label(
        [
            {
                "channel": "space",
                "total": 2,
                "success": 1,
                "failed": 1,
                "pending": 0,
                "total_cost": 3.0,
                "avg_cost": 1.0,
                "avg_duration": 40.0,
            },
            {
                "channel": "우주/천문학",
                "total": 3,
                "success": 2,
                "failed": 0,
                "pending": 1,
                "total_cost": 4.0,
                "avg_cost": 2.0,
                "avg_duration": 50.0,
            },
        ]
    )

    assert rows == [
        {
            "channel": "우주/천문학",
            "total": 5,
            "success": 3,
            "failed": 1,
            "pending": 1,
            "total_cost": 7.0,
            "avg_cost": pytest.approx(5.0 / 3),
            "avg_duration": pytest.approx(140.0 / 3),
        }
    ]


def test_cpv_data_skips_zero_view_or_zero_cost_channels_and_sorts(shorts_analytics) -> None:
    rows = shorts_analytics._build_cpv_data(
        [
            {"channel": "slow", "video_count": 1, "total_views": 1000, "total_cost": 4.0},
            {"channel": "free", "video_count": 1, "total_views": 1000, "total_cost": 0.0},
            {"channel": "empty", "video_count": 1, "total_views": 0, "total_cost": 1.0},
            {"channel": "AI/Tech", "video_count": 2, "total_views": 4000, "total_cost": 2.0},
        ]
    )

    assert [row["channel"] for row in rows] == ["AI/기술", "slow"]
    assert rows[0]["cpv_1k"] == 0.5
    assert rows[1]["cpv_1k"] == 4.0


def test_channel_performance_grouping_merges_labels_and_recomputes_averages(shorts_analytics) -> None:
    rows = shorts_analytics._group_channel_performance_by_display_label(
        [
            {
                "channel": "AI/Tech",
                "video_count": 1,
                "total_views": 1000,
                "avg_views": 1000.0,
                "avg_ctr": 2.0,
                "avg_watch_sec": 20.0,
                "total_cost": 1.0,
            },
            {
                "channel": "AI/기술",
                "video_count": 3,
                "total_views": 9000,
                "avg_views": 3000.0,
                "avg_ctr": 4.0,
                "avg_watch_sec": 40.0,
                "total_cost": 2.0,
            },
        ]
    )

    assert rows == [
        {
            "channel": "AI/기술",
            "video_count": 4,
            "total_views": 10000,
            "avg_views": 2500.0,
            "avg_ctr": pytest.approx(3.5),
            "avg_watch_sec": pytest.approx(35.0),
            "total_cost": 3.0,
        }
    ]


def test_revenue_and_roi_helpers_use_shorts_rpm_range(shorts_analytics) -> None:
    est_low, est_high = shorts_analytics._estimate_shorts_revenue(2500)

    assert est_low == pytest.approx(0.10)
    assert est_high == pytest.approx(0.25)
    assert shorts_analytics._roi_percent(0.25, 1.0) == pytest.approx(-75.0)
    assert shorts_analytics._roi_percent(0.25, 0.0) == pytest.approx(2500.0)


def test_render_dataframe_uses_current_stretch_width_api(shorts_analytics) -> None:
    fake_streamlit = shorts_analytics.st
    fake_streamlit.events.clear()

    shorts_analytics._render_dataframe([{"채널": "AI/기술"}])

    assert fake_streamlit.events == [("dataframe", [{"채널": "AI/기술"}], {"width": "stretch", "hide_index": True})]


def test_render_plotly_chart_uses_current_stretch_width_api(shorts_analytics) -> None:
    fake_streamlit = shorts_analytics.st
    fake_streamlit.events.clear()

    shorts_analytics._render_plotly_chart("figure")

    assert fake_streamlit.events == [
        (
            "plotly_chart",
            "figure",
            {
                "width": "stretch",
                "config": {
                    "displayModeBar": False,
                    "displaylogo": False,
                    "responsive": True,
                },
            },
        )
    ]


def test_shorts_analytics_page_config_uses_korean_operator_title(shorts_analytics) -> None:
    fake_streamlit = shorts_analytics.st

    assert (
        "set_page_config",
        {"page_title": "쇼츠 성과 분석 - Joolife", "page_icon": "📊", "layout": "wide"},
        {},
    ) in fake_streamlit.events


def test_shorts_analytics_source_avoids_deprecated_plotly_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "shorts_analytics.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'st.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)' in source


def test_shorts_analytics_hides_plotly_modebar_and_keeps_charts_responsive() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "shorts_analytics.py").read_text(encoding="utf-8")

    assert '"displayModeBar": False' in source
    assert '"displaylogo": False' in source
    assert '"responsive": True' in source


def test_shorts_analytics_source_labels_shorts_revenue_as_rpm() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "shorts_analytics.py").read_text(encoding="utf-8")

    assert "채널별 Shorts 수익 잠재력 (RPM 추정)" in source
    assert "Shorts RPM(수익/1천회 engaged views)" in source
    assert "Shorts CPM" not in source


def test_shorts_analytics_injects_mobile_touch_targets(shorts_analytics) -> None:
    fake_streamlit = shorts_analytics.st
    fake_streamlit.events.clear()

    shorts_analytics._inject_mobile_touch_target_styles()

    assert len(fake_streamlit.events) == 1
    name, css, kwargs = fake_streamlit.events[0]
    assert name == "markdown"
    assert kwargs == {"unsafe_allow_html": True}
    assert 'button[data-testid="stBaseButton-header"]' in css
    assert 'button[data-testid="stMainMenuButton"]' in css
    assert 'a[href^="#"]' in css
    assert "div[role='tablist']" in css
    assert "button[role='tab']" in css
    assert "min-height: 44px !important" in css
    assert "min-width: 44px !important" in css


def test_workspace_dependencies_include_plotly_for_shorts_analytics_runtime() -> None:
    pyproject = tomllib.loads((WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.startswith("plotly>=") for dependency in dependencies)
