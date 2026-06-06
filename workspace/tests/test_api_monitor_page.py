from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


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

    def slider(self, label: object, **kwargs) -> object:
        self._record("slider", label, **kwargs)
        return kwargs.get("value")

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def plotly_chart(self, fig, **kwargs) -> None:
        self._record("plotly_chart", fig, **kwargs)

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


class _BridgePolicy:
    @classmethod
    def from_env(cls) -> "_BridgePolicy":
        return cls()

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": "test",
            "min_hangul_ratio": 0.0,
            "max_cjk_ratio": 1.0,
            "max_jamo_ratio": 1.0,
            "repair_attempts": 0,
            "fallback_providers": [],
            "strict_korean": False,
        }


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plotly = types.ModuleType("plotly")
    fake_px = types.ModuleType("plotly.express")
    fake_go = types.ModuleType("plotly.graph_objects")
    fake_go.Figure = lambda: object()
    fake_go.Bar = lambda **kwargs: {"kind": "bar", **kwargs}
    fake_go.Scatter = lambda **kwargs: {"kind": "scatter", **kwargs}
    fake_px.bar = lambda **kwargs: {"kind": "bar_chart", **kwargs}
    fake_px.pie = lambda **kwargs: {"kind": "pie", **kwargs}
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", fake_px)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_go)


def _install_api_monitor_dependencies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path_contract = types.ModuleType("path_contract")
    path_contract.TMP_ROOT = tmp_path / ".tmp"
    path_contract.resolve_project_dir = lambda name, **kwargs: tmp_path / name
    monkeypatch.setitem(sys.modules, "path_contract", path_contract)

    tracker = types.ModuleType("execution.api_usage_tracker")
    tracker.check_api_keys = lambda: {"openai": True}
    tracker.get_usage_summary = lambda days: {
        "total_calls": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
    }
    tracker.get_daily_breakdown = lambda days: []
    tracker.get_provider_breakdown = lambda days: []
    tracker.get_bridge_daily_breakdown = lambda days: []
    tracker.get_bridge_reason_breakdown = lambda days: []
    tracker.get_bridge_provider_breakdown = lambda days: []
    tracker.get_blind_to_x_summary = lambda days: {
        "total_calls": 0,
        "total_cost_usd": 0.0,
        "providers": [],
    }
    tracker.init_db = lambda: None
    monkeypatch.setitem(sys.modules, "execution.api_usage_tracker", tracker)

    language_bridge = types.ModuleType("execution.language_bridge")
    language_bridge.BridgePolicy = _BridgePolicy
    monkeypatch.setitem(sys.modules, "execution.language_bridge", language_bridge)

    scheduler_engine = types.ModuleType("execution.scheduler_engine")
    scheduler_engine.get_scheduler_kpis = lambda days: {
        "scheduler_success_rate": 100.0,
        "scheduler_backlog": 0,
    }
    monkeypatch.setitem(sys.modules, "execution.scheduler_engine", scheduler_engine)


def _import_api_monitor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    sys.modules.pop("execution.pages.api_monitor", None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_plotly(monkeypatch)
    _install_api_monitor_dependencies(monkeypatch, tmp_path)

    module = importlib.import_module("execution.pages.api_monitor")
    return module, fake_streamlit


def test_api_monitor_uses_current_plotly_width_api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module, fake_streamlit = _import_api_monitor(monkeypatch, tmp_path)
    fake_streamlit.events.clear()

    module._render_plotly_chart("figure")

    assert fake_streamlit.events == [("plotly_chart", "figure", {"width": "stretch"})]


def test_api_monitor_source_avoids_deprecated_plotly_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "api_monitor.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'st.plotly_chart(fig, width="stretch")' in source
    assert source.count("_render_plotly_chart(") >= 8
