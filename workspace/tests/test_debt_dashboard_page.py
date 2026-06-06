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

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_debt_dashboard_uses_current_streamlit_line_chart_width_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, fake_streamlit = _import_debt_dashboard(monkeypatch, tmp_path)
    fake_streamlit.events.clear()

    class _ChartData:
        empty = False

    chart_data = _ChartData()
    module._render_line_chart(chart_data)

    assert fake_streamlit.events == [("line_chart", chart_data, {"width": "stretch"})]


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
    assert 'st.line_chart(data, width="stretch")' in source
    assert '_build_trend_chart_frame(df, ["overall_tdr"])' in source
    assert '_build_trend_chart_frame(df, ["tdr_percent"])' in source
    assert '_build_trend_chart_frame(df, ["avg_score"])' in source
    assert "_render_line_chart(chart_df)" in source
    assert "_render_line_chart(tdr_chart)" in source
    assert "_render_line_chart(score_chart)" in source
