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


def test_api_monitor_source_avoids_deprecated_plotly_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "api_monitor.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)' in source
    assert source.count("_render_plotly_chart(") >= 8


def test_api_monitor_hides_mobile_plotly_modebar() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "api_monitor.py").read_text(encoding="utf-8")

    assert '"displayModeBar": False' in source
    assert '"displaylogo": False' in source
    assert '"responsive": True' in source


def test_api_monitor_injects_mobile_touch_target_css(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module, fake_streamlit = _import_api_monitor(monkeypatch, tmp_path)
    fake_streamlit.events.clear()

    module._inject_api_monitor_mobile_css()

    markdowns = [payload for name, payload, _kwargs in fake_streamlit.events if name == "markdown"]
    assert markdowns
    css = str(markdowns[-1])
    assert "@media (max-width: 640px)" in css
    assert "min-height: 44px !important" in css
    assert "min-width: 44px !important" in css
    assert "div[data-testid='stSlider'] [role='slider']" in css
    assert "button[aria-label='Main menu']" in css


def test_api_monitor_uses_korean_operator_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _module, fake_streamlit = _import_api_monitor(monkeypatch, tmp_path)

    page_configs = [payload for name, payload, _kwargs in fake_streamlit.events if name == "set_page_config"]
    titles = [payload for name, payload, _kwargs in fake_streamlit.events if name == "title"]
    captions = [payload for name, payload, _kwargs in fake_streamlit.events if name == "caption"]
    subheaders = [payload for name, payload, _kwargs in fake_streamlit.events if name == "subheader"]
    metrics = [payload for name, payload, _kwargs in fake_streamlit.events if name == "metric"]

    assert any(config["page_title"] == "API 사용 모니터 - Joolife" for config in page_configs)
    assert "📡 API 사용 모니터" in titles
    assert any("워크스페이스 API 호출" in str(payload) for payload in captions)
    assert "API 키 상태" in subheaders
    assert "운영 KPI" in subheaders
    assert "일별 API 사용량" in subheaders
    assert "총 API 호출" in metrics


def test_api_monitor_source_removes_old_english_operator_copy() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "api_monitor.py").read_text(encoding="utf-8")

    for old_copy in [
        "API usage tracking & credit monitoring",
        "API Key Status",
        "Operational KPIs",
        "Daily API Usage",
        "Usage by Provider",
        "Token Usage Detail",
        "LLM Bridge Policy",
        "Provider Bridge Metrics",
        "Cost by Provider",
    ]:
        assert old_copy not in source


def test_api_monitor_loads_btx_cost_db_with_project_root_import_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pipeline_dir = tmp_path / "blind-to-x" / "pipeline"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "__init__.py").write_text("", encoding="utf-8")
    (pipeline_dir / "cost_db_schema.py").write_text("SCHEMA_MARKER = 'ok'\n", encoding="utf-8")
    (pipeline_dir / "cost_db.py").write_text(
        "\n".join(
            [
                "from pipeline.cost_db_schema import SCHEMA_MARKER",
                "",
                "class CostDatabase:",
                "    def __init__(self):",
                "        self.marker = SCHEMA_MARKER",
                "",
                "    def get_today_summary(self):",
                "        return {",
                "            'gemini_image_limit': 500,",
                "            'gemini_image_count': 0,",
                "            'gemini_rpd_pct': 0.0,",
                "            'total_usd': 0.0,",
                "            'text_usd': 0.0,",
                "            'image_usd': 0.0,",
                "        }",
                "",
                "    def get_daily_trend(self, days):",
                "        return []",
                "",
                "    def get_draft_style_performance(self, days):",
                "        return []",
            ]
        ),
        encoding="utf-8",
    )

    module, fake_streamlit = _import_api_monitor(monkeypatch, tmp_path)

    captions = [str(payload) for name, payload, _kwargs in fake_streamlit.events if name == "caption"]
    metrics = [payload for name, payload, _kwargs in fake_streamlit.events if name == "metric"]
    assert module._BTX_COST_DB is not None
    assert module._BTX_COST_DB_ERROR is None
    assert not any("BTX CostDB 로드 실패" in payload for payload in captions)
    assert "오늘 텍스트 비용" in metrics
