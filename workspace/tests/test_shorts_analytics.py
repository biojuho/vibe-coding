from __future__ import annotations

import importlib
import sys
import types

import pytest


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
                "channel": "AI/기술",
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
    assert rows[1]["CPV ($/1K views)"] == "-"
    assert "CPV (원/조회)" not in rows[0]


def test_cpv_data_skips_zero_view_or_zero_cost_channels_and_sorts(shorts_analytics) -> None:
    rows = shorts_analytics._build_cpv_data(
        [
            {"channel": "slow", "video_count": 1, "total_views": 1000, "total_cost": 4.0},
            {"channel": "free", "video_count": 1, "total_views": 1000, "total_cost": 0.0},
            {"channel": "empty", "video_count": 1, "total_views": 0, "total_cost": 1.0},
            {"channel": "fast", "video_count": 2, "total_views": 4000, "total_cost": 2.0},
        ]
    )

    assert [row["channel"] for row in rows] == ["fast", "slow"]
    assert rows[0]["cpv_1k"] == 0.5
    assert rows[1]["cpv_1k"] == 4.0


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
