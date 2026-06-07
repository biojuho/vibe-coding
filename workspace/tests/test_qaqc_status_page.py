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


class _FakeColumnConfig:
    def TextColumn(self, label, **kwargs):
        return {"kind": "text", "label": label, **kwargs}

    def NumberColumn(self, label, **kwargs):
        return {"kind": "number", "label": label, **kwargs}


class _FakeStreamlit(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.events: list[tuple[str, object, dict]] = []
        self.column_config = _FakeColumnConfig()

    def _record(self, name: str, payload: object = None, **kwargs) -> None:
        self.events.append((name, payload, kwargs))

    def set_page_config(self, **kwargs) -> None:
        self._record("set_page_config", kwargs)

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyBlock(self) for _ in range(count)]

    def expander(self, label, **kwargs) -> _DummyBlock:
        self._record("expander", label, **kwargs)
        return _DummyBlock(self)

    def dataframe(self, data, **kwargs) -> None:
        self._record("dataframe", data, **kwargs)

    def metric(self, label, value, **kwargs) -> None:
        self._record("metric", {"label": label, "value": value}, **kwargs)

    def plotly_chart(self, fig, **kwargs) -> None:
        self._record("plotly_chart", fig, **kwargs)

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


def _install_fake_path_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path_contract = types.ModuleType("path_contract")
    path_contract.resolve_project_dir = lambda *_args, **_kwargs: tmp_path
    monkeypatch.setitem(sys.modules, "path_contract", path_contract)


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plotly = types.ModuleType("plotly")
    fake_px = types.ModuleType("plotly.express")

    def _line(*args, **kwargs):
        return types.SimpleNamespace(kind="line", args=args, kwargs=kwargs, update_layout=lambda **_kwargs: None)

    fake_px.line = _line
    fake_plotly.express = fake_px
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.express", fake_px)


def _import_qaqc_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    module_name = "execution.pages.qaqc_status"
    sys.modules.pop(module_name, None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_path_contract(monkeypatch, tmp_path)
    _install_fake_plotly(monkeypatch)

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_qaqc_status_empty_state_points_to_shorts_qc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "WORKSPACE_ROOT", tmp_path / "workspace")

    module.main()

    titles = [payload for name, payload, _kwargs in fake_streamlit.events if name == "title"]
    warnings = [payload for name, payload, _kwargs in fake_streamlit.events if name == "warning"]
    codes = [payload for name, payload, _kwargs in fake_streamlit.events if name == "code"]
    code_events = [event for event in fake_streamlit.events if event[0] == "code"]
    captions = [payload for name, payload, _kwargs in fake_streamlit.events if name == "caption"]

    assert "✅ 검증 현황" in titles
    assert "아직 QA/QC 결과 파일이 없습니다." in warnings
    assert module._SHORTS_QC_COMMAND in codes
    assert module._FULL_QC_COMMAND in codes
    assert all(event[2]["wrap_lines"] is True for event in code_events)
    assert all(event[2]["width"] == "stretch" for event in code_events)
    assert any("Shorts Maker V2" in str(caption) for caption in captions)


def test_qaqc_status_project_rows_surface_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, _fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)

    rows = module._build_project_rows(
        {
            "shorts-maker-v2": {"status": "PASS", "passed": 1640, "failed": 0, "skipped": 12},
            "hanwoo-dashboard": {"status": "FAIL", "passed": 10, "failed": 1, "skipped": 0},
        }
    )

    assert rows[0] == {
        "프로젝트": "shorts-maker-v2",
        "상태": "통과",
        "통과": 1640,
        "실패": 0,
        "건너뜀": 12,
        "다음 조치": "쇼츠 생성·업로드 전 최신 QC 기준으로 사용 가능",
    }
    assert rows[1]["상태"] == "실패"
    assert "focused gate" in rows[1]["다음 조치"]
    hanwoo_action = module._project_next_action("hanwoo-dashboard", {"status": "PASS"})
    assert "T-251" in hanwoo_action


def test_qaqc_status_loads_authenticated_data_before_public_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, _fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "WORKSPACE_ROOT", tmp_path / "workspace")
    data_dir = tmp_path / "data"
    public_dir = tmp_path / "public"
    data_dir.mkdir()
    public_dir.mkdir()
    (data_dir / "qaqc_result.json").write_text(
        json.dumps({"verdict": "APPROVED", "source": "data"}),
        encoding="utf-8",
    )
    (public_dir / "qaqc_result.json").write_text(
        json.dumps({"verdict": "REJECTED", "source": "public"}),
        encoding="utf-8",
    )

    assert module.load_latest_result() == {"verdict": "APPROVED", "source": "data"}


def test_qaqc_status_loads_latest_workspace_qc_before_dashboard_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, _fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "WORKSPACE_ROOT", tmp_path / "workspace")
    latest_dir = tmp_path / ".tmp"
    data_dir = tmp_path / "data"
    latest_dir.mkdir()
    data_dir.mkdir()
    (latest_dir / "project_qc_runner_latest.json").write_text(
        json.dumps({"status": "passed", "source": "latest"}),
        encoding="utf-8",
    )
    (data_dir / "qaqc_result.json").write_text(
        json.dumps({"verdict": "APPROVED", "source": "data"}),
        encoding="utf-8",
    )

    assert module.load_latest_result() == {"status": "passed", "source": "latest"}


def test_qaqc_status_warns_on_stale_or_incomplete_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, _fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)

    warnings = module._quality_warnings(
        {"timestamp": "2026-04-02T00:00:00.000Z", "projects": {}},
        now=module.datetime(2026, 6, 8, tzinfo=module.timezone.utc),
    )

    assert any("67일 전" in warning for warning in warnings)
    assert any("프로젝트별 결과가 비어" in warning for warning in warnings)


def test_qaqc_status_summary_metric_uses_runner_status_verdict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)

    module._render_summary_metrics({"status": "passed", "projects": {"shorts-maker-v2": {"passed": 1640}}})

    metrics = [payload for name, payload, _kwargs in fake_streamlit.events if name == "metric"]
    assert {"label": "판정", "value": "사용 가능"} in metrics
    assert {"label": "통과", "value": 1640} in metrics


def test_qaqc_status_load_history_uses_history_db(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, _fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)
    history_db = types.ModuleType("execution.qaqc_history_db")

    class FakeHistoryDB:
        def get_trend_data(self, days: int):
            return [{"date": "2026-06-08", "passed": days, "failed": 0}]

    history_db.QaQcHistoryDB = FakeHistoryDB
    monkeypatch.setitem(sys.modules, "execution.qaqc_history_db", history_db)

    assert module.load_history() == [{"date": "2026-06-08", "passed": 30, "failed": 0}]


def test_qaqc_status_uses_current_dataframe_and_plotly_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)

    module._render_project_results(
        {"projects": {"shorts-maker-v2": {"status": "PASS", "passed": 1640, "failed": 0, "skipped": 12}}}
    )
    module._render_trend([{"date": "2026-06-07", "passed": 10, "failed": 0}])

    dataframe_events = [event for event in fake_streamlit.events if event[0] == "dataframe"]
    assert dataframe_events
    assert dataframe_events[0][2]["width"] == "stretch"
    assert dataframe_events[0][2]["hide_index"] is True
    assert "다음 조치" in dataframe_events[0][2]["column_config"]
    visible_actions = [payload for name, payload, _kwargs in fake_streamlit.events if name == "markdown"]
    assert any("프로젝트별 다음 조치" in str(payload) for payload in visible_actions)
    assert any("shorts-maker-v2" in str(payload) for payload in visible_actions)

    plotly_events = [event for event in fake_streamlit.events if event[0] == "plotly_chart"]
    assert plotly_events == [
        (
            "plotly_chart",
            plotly_events[0][1],
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


def test_qaqc_status_infrastructure_section_has_empty_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module, fake_streamlit = _import_qaqc_status(monkeypatch, tmp_path)

    module._render_infrastructure({})

    subheaders = [payload for name, payload, _kwargs in fake_streamlit.events if name == "subheader"]
    infos = [payload for name, payload, _kwargs in fake_streamlit.events if name == "info"]

    assert "인프라 상태" in subheaders
    assert "인프라 점검 결과가 없습니다." in infos


def test_qaqc_status_source_contracts() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "qaqc_status.py").read_text(encoding="utf-8")

    assert "QA/QC Status Dashboard" not in source
    assert "Unified test, AST, security, and infrastructure status" not in source
    assert "No QA/QC result found yet" not in source
    assert "use_container_width=True" not in source
    assert 'st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)' in source
    assert 'st.code(command, language="powershell", wrap_lines=True, width="stretch")' in source
    assert "st.dataframe(" in source
    assert 'width="stretch"' in source
    assert "hide_index=True" in source
    assert "min-height: 44px" in source
    assert 'div[data-testid="stToolbar"] button' in source
    assert 'a[aria-label="Link to heading"]' in source
    assert "project_qc_runner.py --project shorts-maker-v2" in source
    assert ".tmp/project_qc_runner_latest.json" in source
    assert "projects/knowledge-dashboard/data/qaqc_result.json" in source
    assert "projects/knowledge-dashboard/public/qaqc_result.json" in source
    assert "게시·공유 전 재검증" in source
    assert "프로젝트별 다음 조치" in source
    assert "검증 현황" in source
