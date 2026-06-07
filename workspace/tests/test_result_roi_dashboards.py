from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

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


class _FakeSidebar(_DummyBlock):
    pass


class _FakeStreamlit(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.events: list[tuple[str, object, dict]] = []
        self.sidebar = _FakeSidebar(self)

    def _record(self, name: str, payload: object = None, **kwargs) -> None:
        self.events.append((name, payload, kwargs))

    def set_page_config(self, **kwargs) -> None:
        self._record("set_page_config", kwargs)

    def title(self, label: object) -> None:
        self._record("title", label)

    def caption(self, label: object) -> None:
        self._record("caption", label)

    def subheader(self, label: object) -> None:
        self._record("subheader", label)

    def info(self, message: object) -> None:
        self._record("info", message)

    def error(self, message: object) -> None:
        self._record("error", message)

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def number_input(self, label, **kwargs):
        self._record("number_input", label, **kwargs)
        return kwargs.get("value", 0)

    def button(self, label, **kwargs) -> bool:
        self._record("button", label, **kwargs)
        return False

    def form_submit_button(self, label, **kwargs) -> bool:
        self._record("form_submit_button", label, **kwargs)
        return False

    def plotly_chart(self, fig, **kwargs) -> None:
        self._record("plotly_chart", fig, **kwargs)

    def dataframe(self, data, **kwargs) -> None:
        self._record("dataframe", data, **kwargs)

    def tabs(self, labels):
        self._record("tabs", labels)
        return [_DummyBlock(self) for _ in labels]

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def form(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def container(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def expander(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


class _FakeFigure:
    def __init__(self) -> None:
        self.traces: list[object] = []
        self.layout: dict[str, object] = {}

    def add_trace(self, trace: object) -> None:
        self.traces.append(trace)

    def update_layout(self, **kwargs) -> None:
        self.layout.update(kwargs)


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plotly = types.ModuleType("plotly")
    fake_px = types.ModuleType("plotly.express")
    fake_go = types.ModuleType("plotly.graph_objects")
    fake_go.Figure = _FakeFigure
    fake_go.Bar = lambda **kwargs: {"kind": "bar", **kwargs}
    fake_go.Scatter = lambda **kwargs: {"kind": "scatter", **kwargs}
    fake_px.pie = lambda **kwargs: {"kind": "pie", **kwargs}
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", fake_px)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_go)


def _install_result_tracker(monkeypatch: pytest.MonkeyPatch, *, with_data: bool) -> None:
    tracker = types.ModuleType("execution.result_tracker_db")
    tracker.PLATFORMS = {
        "youtube": {"display": "YouTube", "emoji": "YT", "auto_stats": True},
        "x": {"display": "X", "emoji": "X", "auto_stats": False},
    }
    rows = [
        {
            "id": 1,
            "platform": "youtube",
            "url": "https://youtu.be/abcdefghijk",
            "title": "ROI sample",
            "channel": "ai-tech",
            "views": 2000,
            "likes": 25,
            "comments": 3,
            "published_at": "2026-06-06",
            "stats_updated": "2026-06-06 10:00",
        }
    ]
    tracker.init_db = lambda: None
    tracker.add_content = lambda **kwargs: 1
    tracker.collect_youtube_stats = lambda: {"updated": 0}
    tracker.delete_content = lambda content_id: None
    tracker.update_manual_stats = lambda *args, **kwargs: None
    tracker.get_stats_history = lambda content_id: []
    tracker.get_daily_trend = lambda days=30: []
    tracker.get_top_content = lambda limit=10: rows[:limit] if with_data else []
    tracker.get_all = lambda platform=None, channel=None: rows if with_data and (channel in (None, "ai-tech")) else []
    tracker.get_platform_summary = lambda: (
        [{"platform": "youtube", "count": 1, "total_views": 2000}] if with_data else []
    )
    tracker.get_channel_summary = lambda: (
        [
            {
                "platform": "youtube",
                "channel": "ai-tech",
                "count": 1,
                "total_views": 2000,
                "avg_views": 2000,
                "total_likes": 25,
            }
        ]
        if with_data
        else []
    )
    monkeypatch.setitem(sys.modules, "execution.result_tracker_db", tracker)


def _install_roi_calculator(monkeypatch: pytest.MonkeyPatch) -> None:
    roi = types.ModuleType("execution.roi_calculator")

    class _Summary:
        channel = "ai-tech"
        total_content = 1
        total_cost = 0.10
        total_views = 2000
        total_estimated_revenue = 3.0
        avg_roi_percent = 2900.0
        avg_cost_per_content = 0.10
        breakeven_status = "profit"

    class _Calculator:
        def __init__(self, rpm: float = 1.5) -> None:
            self.rpm = rpm

        def generate_channel_summary(self, content_list):
            return _Summary()

        def calculate_breakeven_views(self, cost: float) -> int:
            return int((cost / self.rpm) * 1000)

    roi.ROICalculator = _Calculator
    monkeypatch.setitem(sys.modules, "execution.roi_calculator", roi)


def _import_page(monkeypatch: pytest.MonkeyPatch, module_name: str, *, with_data: bool = True):
    sys.modules.pop(module_name, None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_plotly(monkeypatch)
    _install_result_tracker(monkeypatch, with_data=with_data)
    _install_roi_calculator(monkeypatch)

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_roi_dashboard_inserts_workspace_root_for_execution_imports() -> None:
    source = Path("workspace/execution/pages/roi_dashboard.py").read_text(encoding="utf-8")

    assert "_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "sys.path.insert(0, str(_WORKSPACE_ROOT))" in source
    assert "Path(__file__).resolve().parent.parent)" not in source


def test_roi_dashboard_uses_current_plotly_width_api(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_page(
        monkeypatch,
        "execution.pages.roi_dashboard",
        with_data=True,
    )
    fake_streamlit.events.clear()

    module._render_plotly_chart("figure")

    assert fake_streamlit.events == [
        ("plotly_chart", "figure", {"width": "stretch", "config": {"displayModeBar": False}})
    ]


def test_roi_dashboard_injects_mobile_touch_target_css(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_page(
        monkeypatch,
        "execution.pages.roi_dashboard",
        with_data=False,
    )
    fake_streamlit.events.clear()

    module._inject_roi_dashboard_mobile_css()

    markdowns = [(payload, kwargs) for name, payload, kwargs in fake_streamlit.events if name == "markdown"]
    assert markdowns
    css, kwargs = markdowns[-1]
    assert kwargs == {"unsafe_allow_html": True}
    assert "@media (max-width: 640px)" in css
    assert "div[data-testid='stNumberInput']" in css
    assert "min-height: 44px" in css
    assert "min-width: 44px" in css


def test_roi_dashboard_uses_compact_korean_operator_copy() -> None:
    source = Path("workspace/execution/pages/roi_dashboard.py").read_text(encoding="utf-8")

    assert 'st.title("쇼츠 ROI")' in source
    assert "업로드 성과와 제작비를 연결해 채널별 수익성을 점검합니다." in source
    assert '"Shorts RPM 추정값 ($)"' in source
    assert "1,000 engaged views당 크리에이터 수익 지표" in source
    assert "Content ROI Dashboard" not in source
    assert "YouTube Shorts RPM ($)" not in source
    assert 'f"{bep_views:,} views"' not in source


def test_result_dashboard_uses_current_streamlit_width_api(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_page(
        monkeypatch,
        "execution.pages.result_dashboard",
        with_data=False,
    )
    fake_streamlit.events.clear()

    module._render_plotly_chart("figure")
    module._render_dataframe([{"channel": "ai-tech"}])

    assert fake_streamlit.events == [
        ("plotly_chart", "figure", {"width": "stretch"}),
        ("dataframe", [{"channel": "ai-tech"}], {"width": "stretch", "hide_index": True}),
    ]


def test_result_dashboard_stretch_button_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    module, _fake_streamlit = _import_page(
        monkeypatch,
        "execution.pages.result_dashboard",
        with_data=False,
    )

    assert module._stretch_button_kwargs() == {"width": "stretch"}


def test_result_dashboard_injects_mobile_touch_target_css(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_page(
        monkeypatch,
        "execution.pages.result_dashboard",
        with_data=False,
    )
    fake_streamlit.events.clear()

    module._inject_result_dashboard_mobile_css()

    markdowns = [(payload, kwargs) for name, payload, kwargs in fake_streamlit.events if name == "markdown"]
    assert markdowns
    css, kwargs = markdowns[-1]
    assert kwargs == {"unsafe_allow_html": True}
    assert "@media (max-width: 640px)" in css
    assert "div[role='tablist']" in css
    assert "button[role='tab']" in css
    assert "min-height: 44px" in css
    assert "min-width: 44px" in css
    assert "div[data-baseweb='select']" in css
    assert "div[data-baseweb='input'] input" in css
    assert "div[data-testid='stTextArea'] textarea" in css
    assert "div[data-testid='stDateInput'] input" in css


def test_result_dashboard_source_calls_mobile_touch_target_css() -> None:
    source = Path("workspace/execution/pages/result_dashboard.py").read_text(encoding="utf-8")

    assert "def _inject_result_dashboard_mobile_css() -> None:" in source
    assert "_inject_result_dashboard_mobile_css()\n\n\n# " in source
    assert "flex-wrap: wrap" in source
    assert "overflow-x: visible" in source
