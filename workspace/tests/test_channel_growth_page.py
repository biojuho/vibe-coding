from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

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

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def form(self, *args, **kwargs) -> _DummyBlock:
        return _DummyBlock(self)

    def form_submit_button(self, label, **kwargs) -> bool:
        self._record("form_submit_button", label, **kwargs)
        return False

    def button(self, label, **kwargs) -> bool:
        self._record("button", label, **kwargs)
        return False

    def plotly_chart(self, fig, **kwargs) -> None:
        self._record("plotly_chart", fig, **kwargs)

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)
            return ""

        return _method


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plotly = types.ModuleType("plotly")
    fake_go = types.ModuleType("plotly.graph_objects")
    fake_go.Figure = lambda *args, **kwargs: types.SimpleNamespace(
        add_trace=lambda trace: None,
        update_layout=lambda **layout: None,
    )
    fake_go.Bar = lambda **kwargs: {"kind": "bar", **kwargs}
    fake_go.Scatter = lambda **kwargs: {"kind": "scatter", **kwargs}
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_go)


def _install_channel_growth_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    tracker = types.ModuleType("execution.channel_growth_tracker")
    tracker.add_channel = lambda channel_id, name="": 1
    tracker.collect_channel_stats = lambda: {"updated": 0}
    tracker.get_channel_comparison = lambda: []
    tracker.get_channels = lambda: []
    tracker.get_growth_history = lambda channel_db_id, days=90: []
    tracker.init_db = lambda: None
    monkeypatch.setitem(sys.modules, "execution.channel_growth_tracker", tracker)


def _import_channel_growth(monkeypatch: pytest.MonkeyPatch):
    module_name = "execution.pages.channel_growth"
    sys.modules.pop(module_name, None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_plotly(monkeypatch)
    _install_channel_growth_tracker(monkeypatch)

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_channel_growth_inserts_workspace_root_for_execution_imports() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "channel_growth.py").read_text(encoding="utf-8")

    assert "WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "sys.path.insert(0, str(WORKSPACE_ROOT))" in source
    assert "Path(__file__).resolve().parent.parent)" not in source


def test_channel_growth_uses_current_plotly_width_api(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_channel_growth(monkeypatch)
    fake_streamlit.events.clear()

    module._render_plotly_chart("figure")

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


def test_channel_growth_source_avoids_deprecated_plotly_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "channel_growth.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)' in source


def test_channel_growth_hides_mobile_plotly_modebar() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "channel_growth.py").read_text(encoding="utf-8")

    assert '"displayModeBar": False' in source
    assert '"displaylogo": False' in source
    assert '"responsive": True' in source


def test_channel_growth_injects_mobile_touch_target_css(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_channel_growth(monkeypatch)
    fake_streamlit.events.clear()

    module._inject_channel_growth_mobile_css()

    markdowns = [payload for name, payload, _kwargs in fake_streamlit.events if name == "markdown"]
    assert markdowns
    css = str(markdowns[-1])
    assert "@media (max-width: 640px)" in css
    assert "min-height: 44px" in css
    assert "div[data-testid='stFormSubmitButton'] button" in css
    assert "button[data-testid='stBaseButton-headerNoPadding']" in css
    assert "button[data-testid='stMainMenuButton']" in css
    assert "width: 44px !important" in css
    assert "div[data-baseweb='input'] input" in css


def test_channel_growth_disables_heading_anchors() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "channel_growth.py").read_text(encoding="utf-8")
    heading_calls = [
        'st.title("📈 채널 성장 추적", anchor=False)',
        'st.subheader("채널 비교 (최신)", anchor=False)',
        'st.subheader("구독자 성장 추이", anchor=False)',
        'st.subheader("7일 성장률 비교", anchor=False)',
        'st.subheader("채널 관리", anchor=False)',
    ]

    for call in heading_calls:
        assert call in source


def test_channel_growth_uses_compact_korean_title(monkeypatch: pytest.MonkeyPatch) -> None:
    _module, fake_streamlit = _import_channel_growth(monkeypatch)

    page_configs = [payload for name, payload, _kwargs in fake_streamlit.events if name == "set_page_config"]
    titles = [payload for name, payload, _kwargs in fake_streamlit.events if name == "title"]
    captions = [payload for name, payload, _kwargs in fake_streamlit.events if name == "caption"]
    text_inputs = [payload for name, payload, _kwargs in fake_streamlit.events if name == "text_input"]
    source = (WORKSPACE_ROOT / "execution" / "pages" / "channel_growth.py").read_text(encoding="utf-8")

    assert page_configs and page_configs[0]["page_title"] == "채널 성장 - Joolife"
    assert "📈 채널 성장 추적" in titles
    assert any("YouTube 5채널 독립 성과 추적" in str(payload) for payload in captions)
    assert "YouTube 채널 ID" in text_inputs
    assert "YouTube Channel ID" not in source
    assert "Channel Growth 모듈" not in source
