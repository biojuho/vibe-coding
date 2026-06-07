from __future__ import annotations

import importlib
import json
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

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def metric(self, label, value, **kwargs) -> None:
        self._record("metric", {"label": label, "value": value}, **kwargs)

    def line_chart(self, data, **kwargs) -> None:
        self._record("line_chart", data, **kwargs)

    def plotly_chart(self, fig, **kwargs) -> None:
        self._record("plotly_chart", fig, **kwargs)

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


def _install_fake_debt_history_db(monkeypatch: pytest.MonkeyPatch) -> None:
    db_module = types.ModuleType("execution.debt_history_db")

    class _DebtHistoryDB:
        def get_trend_data(self, days: int = 90) -> list[dict]:
            return []

        def get_project_trend(self, project_name: str, days: int = 90) -> list[dict]:
            return []

    db_module.DebtHistoryDB = _DebtHistoryDB
    monkeypatch.setitem(sys.modules, "execution.debt_history_db", db_module)


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plotly = types.ModuleType("plotly")
    fake_px = types.ModuleType("plotly.express")

    def _line(*args, **kwargs):
        return types.SimpleNamespace(kind="line", args=args, kwargs=kwargs, update_layout=lambda **_kwargs: None)

    fake_px.line = _line
    fake_plotly.express = fake_px
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", fake_px)


def _import_debt_dashboard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    module_name = "execution.pages.debt_dashboard"
    sys.modules.pop(module_name, None)

    (tmp_path / "debt_audit_result.json").write_text(
        json.dumps(
            {
                "overall_grade": "GREEN",
                "overall_tdr": 1.2,
                "total_principal_hours": 0.5,
                "total_interest_monthly_hours": 0.1,
                "projects": [],
                "file_scores": [],
                "timestamp": "2026-06-07T00:00:00",
                "total_files": 1,
                "scan_duration_seconds": 1.0,
            }
        ),
        encoding="utf-8",
    )

    fake_path_contract = types.ModuleType("path_contract")
    fake_path_contract.TMP_ROOT = tmp_path
    fake_streamlit = _FakeStreamlit()

    monkeypatch.setitem(sys.modules, "path_contract", fake_path_contract)
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_debt_history_db(monkeypatch)
    _install_fake_plotly(monkeypatch)

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_debt_dashboard_uses_current_plotly_chart_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, fake_streamlit = _import_debt_dashboard(monkeypatch, tmp_path)
    fake_streamlit.events.clear()

    pandas = pytest.importorskip("pandas")
    chart_data = pandas.DataFrame([{"overall_tdr": 32.3}], index=pandas.Index(["2026-06-07"], name="date"))

    module._render_line_chart(chart_data, y_axis_title="TDR %", series_labels={"overall_tdr": "전체 TDR"})

    assert fake_streamlit.events == [
        (
            "plotly_chart",
            fake_streamlit.events[0][1],
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
    figure = fake_streamlit.events[0][1]
    assert figure.kind == "line"
    assert figure.kwargs["x"] == "date"
    assert figure.kwargs["y"] == ["전체 TDR"]
    assert figure.kwargs["render_mode"] == "svg"


def test_debt_dashboard_skips_empty_line_charts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, fake_streamlit = _import_debt_dashboard(monkeypatch, tmp_path)
    fake_streamlit.events.clear()

    class _EmptyChartData:
        empty = True

    module._render_line_chart(_EmptyChartData())
    module._render_line_chart(None)

    assert fake_streamlit.events == []


def test_debt_dashboard_trend_chart_frame_filters_invalid_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, _fake_streamlit = _import_debt_dashboard(monkeypatch, tmp_path)
    pandas = pytest.importorskip("pandas")

    frame = module._build_trend_chart_frame(
        pandas.DataFrame(
            [
                {"timestamp": "2026-06-07T00:00:00", "overall_tdr": 32.3},
                {"timestamp": "not-a-date", "overall_tdr": 99.0},
                {"timestamp": "2026-06-08T00:00:00", "overall_tdr": None},
                {"timestamp": "2026-06-09T00:00:00", "overall_tdr": float("inf")},
            ]
        ),
        ["overall_tdr"],
    )

    assert frame is not None
    assert [value.isoformat() for value in frame.index.tolist()] == ["2026-06-07"]
    assert frame["overall_tdr"].tolist() == [32.3]


def test_debt_dashboard_source_avoids_deprecated_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "debt_dashboard.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)' in source
    assert '_build_trend_chart_frame(df, ["overall_tdr"])' in source
    assert '_build_trend_chart_frame(df, ["tdr_percent"])' in source
    assert '_build_trend_chart_frame(df, ["avg_score"])' in source
    assert 'series_labels={"overall_tdr": "전체 TDR"}' in source
    assert 'series_labels={"tdr_percent": "TDR"}' in source
    assert 'series_labels={"avg_score": "평균 부채 점수"}' in source


def test_debt_dashboard_uses_korean_operator_copy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _module, fake_streamlit = _import_debt_dashboard(monkeypatch, tmp_path)

    configs = [payload for name, payload, _kwargs in fake_streamlit.events if name == "set_page_config"]
    titles = [payload for name, payload, _kwargs in fake_streamlit.events if name == "title"]
    captions = [payload for name, payload, _kwargs in fake_streamlit.events if name == "caption"]
    metrics = [payload for name, payload, _kwargs in fake_streamlit.events if name == "metric"]

    assert any(config["page_title"] == "기술부채 현황 - Joolife" for config in configs)
    assert "📊 기술부채 현황" in titles
    assert any("프로젝트별 TDR" in str(payload) for payload in captions)
    assert {"label": "전체 TDR", "value": "1.2%"} in metrics
    assert {"label": "등급", "value": "안정"} in metrics


def test_debt_dashboard_mobile_css_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, fake_streamlit = _import_debt_dashboard(monkeypatch, tmp_path)
    fake_streamlit.events.clear()

    module._inject_debt_dashboard_mobile_css()

    css_payloads = [
        payload
        for name, payload, kwargs in fake_streamlit.events
        if name == "markdown" and kwargs.get("unsafe_allow_html")
    ]
    assert css_payloads
    css = css_payloads[-1]
    assert "max-width: 640px" in css
    assert 'div[data-testid="stSelectbox"] div[data-baseweb="select"]' in css
    assert 'div[data-testid="stSelectbox"] input[role="combobox"]' in css
    assert 'div[data-baseweb="slider"] {' in css
    assert 'div[data-baseweb="slider"] [role="slider"]' in css
    assert 'div[data-testid="stExpander"] details summary' in css
    assert "min-height: 44px !important" in css
    assert "min-width: 44px !important" in css


def test_debt_dashboard_source_removes_old_english_operator_copy() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "debt_dashboard.py").read_text(encoding="utf-8")

    for old_copy in [
        "VibeDebt Auditor",
        "Technical debt quantification",
        "Overall TDR",
        "Technical Debt Ratio",
        "Fix Cost (Principal)",
        "Monthly Interest",
        "Project Breakdown",
        "Avg Debt Score",
        "Top Debtor Files",
        "Filter by project",
        "Minimum debt score",
        "Project Trend Detail",
        "Select project",
        "Last scan",
    ]:
        assert old_copy not in source
