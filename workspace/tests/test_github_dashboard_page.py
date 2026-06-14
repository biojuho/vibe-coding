import importlib
import sys
import types
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PAGE_SOURCE = WORKSPACE_ROOT / "execution" / "pages" / "github_dashboard.py"


def _source() -> str:
    return PAGE_SOURCE.read_text(encoding="utf-8")


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

    def selectbox(self, label, options, **kwargs):
        self._record("selectbox", {"label": label, "options": options}, **kwargs)
        return options[0]

    def slider(self, label, **kwargs):
        self._record("slider", label, **kwargs)
        return kwargs.get("value")

    def spinner(self, text):
        self._record("spinner", text)
        return _DummyBlock(self)

    def expander(self, label):
        self._record("expander", label)
        return _DummyBlock(self)

    def stop(self) -> None:
        self._record("stop")

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)
            return ""

        return _method


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plotly = types.ModuleType("plotly")
    fake_px = types.ModuleType("plotly.express")
    fake_go = types.ModuleType("plotly.graph_objects")
    fake_px.pie = lambda **kwargs: types.SimpleNamespace(kind="pie", kwargs=kwargs)
    fake_go.Bar = lambda **kwargs: types.SimpleNamespace(kind="bar", kwargs=kwargs)
    fake_go.Figure = lambda *args, **kwargs: types.SimpleNamespace(
        kind="figure",
        args=args,
        kwargs=kwargs,
        update_layout=lambda **_layout: None,
    )
    fake_plotly.express = fake_px
    fake_plotly.graph_objects = fake_go
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", fake_px)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_go)


def _install_fake_github_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    github_stats = types.ModuleType("execution.github_stats")
    github_stats.get_commit_heatmap_data = lambda **kwargs: {}
    github_stats.get_commits = lambda *args, **kwargs: []
    github_stats.get_language_stats = lambda: {}
    github_stats.get_pr_stats = lambda **kwargs: {"total": 0, "open": 0, "merged": 0, "closed": 0}
    github_stats.get_repos = lambda: []
    github_stats.get_user = lambda: None
    github_stats.is_configured = lambda: False
    monkeypatch.setitem(sys.modules, "execution.github_stats", github_stats)


def _import_github_dashboard(monkeypatch: pytest.MonkeyPatch):
    module_name = "execution.pages.github_dashboard"
    sys.modules.pop(module_name, None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_plotly(monkeypatch)
    _install_fake_github_stats(monkeypatch)

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_github_dashboard_page_inserts_workspace_root_for_execution_imports():
    source = _source()

    assert "WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "sys.path.insert(0, str(WORKSPACE_ROOT))" in source
    assert "Path(__file__).resolve().parent.parent" not in source


def test_github_dashboard_page_surfaces_release_boundary_before_remote_stats():
    source = _source()

    assert 'page_title="GitHub 운영 - Joolife"' in source
    assert 'st.title("GitHub 운영 현황", anchor=False)' in source
    assert 'st.subheader("릴리스 경계", anchor=False)' in source
    assert "root-quality-gate" in source
    assert "active-project-matrix" in source
    assert "명시적 승인 전 push하지 말고" in source
    assert "`GITHUB_PERSONAL_ACCESS_TOKEN`이 없어" in source
    assert "GitHub activity & repository stats" not in source
    assert 'st.title("GitHub Dashboard")' not in source


def test_github_dashboard_page_disables_first_screen_heading_anchor_links():
    source = _source()

    assert source.count("anchor=False") == 2
    assert 'st.title("GitHub 운영 현황", anchor=False)' in source
    assert 'st.subheader("릴리스 경계", anchor=False)' in source


def test_github_dashboard_release_boundary_renders_without_heading_anchor(monkeypatch: pytest.MonkeyPatch):
    module, fake_streamlit = _import_github_dashboard(monkeypatch)
    from execution.pages.github_dashboard import _render_release_boundary

    fake_streamlit.events.clear()
    monkeypatch.setattr(
        module,
        "_local_release_status",
        lambda: {"branch": "main", "head": "abc1234", "ahead": 3, "status_line": "## main...origin/main [ahead 3]"},
    )

    _render_release_boundary()

    assert ("subheader", "릴리스 경계", {"anchor": False}) in fake_streamlit.events
    assert ("metric", {"label": "현재 브랜치", "value": "main"}, {}) in fake_streamlit.events
    assert any(
        name == "warning" and "명시적 승인 전 push하지 말고" in str(payload)
        for name, payload, _ in fake_streamlit.events
    )


def test_github_dashboard_page_hides_plotly_modebar_and_uses_current_width_api():
    source = _source()

    assert 'PLOTLY_CHART_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}' in source
    assert 'st.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)' in source
    assert "use_container_width=True" not in source


def test_github_dashboard_page_has_mobile_touch_target_css():
    source = _source()

    assert "def _inject_mobile_touch_target_styles()" in source
    assert 'div[data-testid="stSelectbox"] [role="combobox"]' in source
    assert 'div[data-testid="stSlider"] [role="slider"]' in source
    assert 'div[data-testid="stExpander"] summary' in source
    assert "min-height: 44px !important" in source
    assert "min-width: 44px !important" in source
