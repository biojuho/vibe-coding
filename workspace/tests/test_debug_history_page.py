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

    def metric(self, label, value, **kwargs) -> None:
        self._record("metric", {"label": label, "value": value}, **kwargs)

    def plotly_chart(self, fig, **kwargs) -> None:
        self._record("plotly_chart", fig, **kwargs)

    def selectbox(self, label, options, **kwargs):
        self._record("selectbox", {"label": label, "options": options}, **kwargs)
        return options[0]

    def text_input(self, label, **kwargs) -> str:
        self._record("text_input", label, **kwargs)
        return ""

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)
            return ""

        return _method


def _install_fake_plotly_express(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plotly = types.ModuleType("plotly")
    fake_px = types.ModuleType("plotly.express")
    fake_px.colors = types.SimpleNamespace(sequential=types.SimpleNamespace(RdBu=["red", "blue"], Teal=["teal"]))
    fake_px.pie = lambda **kwargs: types.SimpleNamespace(kind="pie", kwargs=kwargs)
    fake_plotly.express = fake_px
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", fake_px)


def _install_debug_history_db(monkeypatch: pytest.MonkeyPatch) -> None:
    db = types.ModuleType("execution.debug_history_db")
    db.get_stats = lambda: {
        "total_entries": 2,
        "by_severity": {"P1": 1, "P2": 1},
        "by_layer": {"execution": 2},
        "directive_update_rate": 50.0,
        "test_addition_rate": 50.0,
        "top_modules": {"module_a": 2},
    }
    db.list_entries = lambda **kwargs: []
    db.list_patterns = lambda: []
    db.lookup_pattern = lambda error_msg: []
    db.search_entries = lambda keyword: []
    monkeypatch.setitem(sys.modules, "execution.debug_history_db", db)


def _import_debug_history(monkeypatch: pytest.MonkeyPatch):
    module_name = "execution.pages.debug_history"
    sys.modules.pop(module_name, None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_plotly_express(monkeypatch)
    _install_debug_history_db(monkeypatch)

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_debug_history_inserts_workspace_root_for_execution_imports() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "debug_history.py").read_text(encoding="utf-8")

    assert "WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "sys.path.insert(0, str(WORKSPACE_ROOT))" in source
    assert "Path(__file__).resolve().parent.parent)" not in source


def test_debug_history_uses_current_plotly_width_api(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_debug_history(monkeypatch)
    fake_streamlit.events.clear()

    module._render_plotly_chart("figure")

    assert fake_streamlit.events == [
        ("plotly_chart", "figure", {"width": "stretch", "config": module.PLOTLY_CHART_CONFIG})
    ]
    assert module.PLOTLY_CHART_CONFIG == {
        "displayModeBar": False,
        "displaylogo": False,
        "responsive": True,
    }


def test_debug_history_source_avoids_deprecated_plotly_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "debug_history.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'st.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)' in source
    assert '"displayModeBar": False' in source


def test_debug_history_disables_streamlit_heading_anchor_links() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "debug_history.py").read_text(encoding="utf-8")

    assert source.count("anchor=False") == 5
    assert 'st.title("디버그 이력", anchor=False)' in source
    assert 'st.subheader("최근 디버그 이력", anchor=False)' in source
    assert 'st.subheader("키워드 검색", anchor=False)' in source
    assert 'st.subheader("등록된 오류 패턴", anchor=False)' in source
    assert 'st.subheader("오류 메시지 패턴 검색", anchor=False)' in source


def test_debug_history_uses_korean_operator_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    _, fake_streamlit = _import_debug_history(monkeypatch)

    assert ("set_page_config", {"page_title": "디버그 이력 - Joolife", "page_icon": "🔎", "layout": "wide"}, {}) in (
        fake_streamlit.events
    )
    assert ("title", "디버그 이력", {"anchor": False}) in fake_streamlit.events
    assert ("caption", "반복 오류와 해결 패턴을 확인하고 다음 조치를 정합니다.", {}) in fake_streamlit.events

    metric_labels = [
        payload["label"]
        for name, payload, _kwargs in fake_streamlit.events
        if name == "metric" and isinstance(payload, dict)
    ]
    assert metric_labels == ["총 이력", "P0/P1 긴급", "지침 업데이트율", "테스트 추가율", "최다 오류 모듈"]

    select_labels = [
        payload["label"]
        for name, payload, _kwargs in fake_streamlit.events
        if name == "selectbox" and isinstance(payload, dict)
    ]
    assert select_labels == ["심각도", "계층"]

    text_inputs = [payload for name, payload, _kwargs in fake_streamlit.events if name == "text_input"]
    assert text_inputs == ["모듈 검색", "키워드 입력", "오류 메시지 입력"]


def test_debug_history_source_rejects_old_english_first_screen_copy() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "debug_history.py").read_text(encoding="utf-8")

    assert 'page_title="Debug History - Joolife"' not in source
    assert 'st.title("🪲 Debug History")' not in source
    assert "seen {p['times_seen']}x" not in source
    assert "검색 결과 없음" not in source


def test_debug_history_injects_mobile_touch_target_css(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_debug_history(monkeypatch)

    css_events = [payload for name, payload, kwargs in fake_streamlit.events if name == "markdown" and kwargs]
    assert module.MOBILE_TOUCH_TARGET_CSS in css_events
    assert "@media (max-width: 640px)" in module.MOBILE_TOUCH_TARGET_CSS
    assert "min-height: 44px !important" in module.MOBILE_TOUCH_TARGET_CSS
    assert 'div[data-testid="stHeader"] button' in module.MOBILE_TOUCH_TARGET_CSS
    assert 'div[data-testid="stToolbar"] button' in module.MOBILE_TOUCH_TARGET_CSS
    assert 'div[data-testid="stHeaderActionElements"] a' in module.MOBILE_TOUCH_TARGET_CSS
    assert 'div[data-baseweb="select"]' in module.MOBILE_TOUCH_TARGET_CSS
    assert 'a[href^="#"]' in module.MOBILE_TOUCH_TARGET_CSS
    assert ".modebar-container" in module.MOBILE_TOUCH_TARGET_CSS
