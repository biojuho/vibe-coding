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

    def error(self, message: object) -> None:
        self._record("error", message)

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def slider(self, label, **kwargs):
        self._record("slider", label, **kwargs)
        return kwargs.get("value", 30)

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def plotly_chart(self, fig, **kwargs) -> None:
        self._record("plotly_chart", fig, **kwargs)

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plotly = types.ModuleType("plotly")
    fake_px = types.ModuleType("plotly.express")
    fake_go = types.ModuleType("plotly.graph_objects")
    fake_px.pie = lambda **kwargs: {"kind": "pie", **kwargs}
    fake_px.bar = lambda **kwargs: {"kind": "bar", **kwargs}
    fake_go.Figure = lambda: types.SimpleNamespace(
        add_trace=lambda trace: None,
        add_hline=lambda **kwargs: None,
        update_layout=lambda **kwargs: None,
    )
    fake_go.Bar = lambda **kwargs: {"kind": "bar", **kwargs}
    fake_go.Scatter = lambda **kwargs: {"kind": "scatter", **kwargs}
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", fake_px)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_go)


def _install_api_usage_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    tracker = types.ModuleType("execution.api_usage_tracker")
    tracker.MONTHLY_BUDGET_USD = 30
    tracker.init_db = lambda: None
    tracker.get_usage_summary = lambda days: {"total_cost_usd": 0, "total_calls": 0, "total_tokens": 0}
    tracker.get_daily_breakdown = lambda days: []
    tracker.get_provider_breakdown = lambda days: []
    tracker.get_model_breakdown = lambda days: []
    tracker.get_monthly_summary = lambda months=6: []
    tracker.get_task_breakdown = lambda days: []
    tracker.get_fallback_analysis = lambda days: {
        "total_calls": 0,
        "fallback_calls": 0,
        "fallback_rate": 0,
        "by_provider": [],
    }
    tracker.get_savings_estimate = lambda days: {
        "actual_cost_usd": 0,
        "premium_baseline_usd": 0,
        "savings_usd": 0,
        "savings_pct": 0,
    }
    monkeypatch.setitem(sys.modules, "execution.api_usage_tracker", tracker)


def _install_path_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_root = tmp_path / "shorts-maker-v2"
    (project_root / "logs").mkdir(parents=True)
    path_contract = types.ModuleType("path_contract")
    path_contract.resolve_project_dir = lambda *args, **kwargs: project_root
    monkeypatch.setitem(sys.modules, "path_contract", path_contract)


def _import_cost_dashboard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    sys.modules.pop("execution.pages.cost_dashboard", None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_plotly(monkeypatch)
    _install_api_usage_tracker(monkeypatch)
    _install_path_contract(monkeypatch, tmp_path)

    module = importlib.import_module("execution.pages.cost_dashboard")
    return module, fake_streamlit


def test_cost_dashboard_uses_current_plotly_width_api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module, fake_streamlit = _import_cost_dashboard(monkeypatch, tmp_path)
    fake_streamlit.events.clear()

    module._render_plotly_chart("figure")

    assert fake_streamlit.events == [("plotly_chart", "figure", {"width": "stretch"})]


def test_cost_dashboard_source_avoids_deprecated_plotly_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "cost_dashboard.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'st.plotly_chart(fig, width="stretch")' in source
