from __future__ import annotations

import importlib
import json
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
        self.sidebar = _DummyBlock(self)

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

    def bar_chart(self, data, **kwargs) -> None:
        self._record("bar_chart", data, **kwargs)

    def dataframe(self, data, **kwargs) -> None:
        self._record("dataframe", data, **kwargs)

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


def _install_result_tracker_db(monkeypatch: pytest.MonkeyPatch) -> None:
    db = types.ModuleType("execution.result_tracker_db")
    db.init_db = lambda: None
    db.get_all = lambda: [{"id": 1, "platform": "youtube"}]
    db.get_daily_trend = lambda days=30: []
    db.get_platform_summary = lambda: []
    monkeypatch.setitem(sys.modules, "execution.result_tracker_db", db)


def _install_api_usage_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    tracker = types.ModuleType("execution.api_usage_tracker")
    tracker.init_db = lambda: None
    tracker.get_usage_summary = lambda days=1: {"total_cost_usd": 0.25}
    tracker.get_daily_breakdown = lambda days=30: []
    tracker.get_provider_breakdown = lambda days=30: []
    monkeypatch.setitem(sys.modules, "execution.api_usage_tracker", tracker)


def _install_debug_history_db(monkeypatch: pytest.MonkeyPatch) -> None:
    db = types.ModuleType("execution.debug_history_db")
    db.init_db = lambda: None
    db.get_stats = lambda: {"total_entries": 3}
    monkeypatch.setitem(sys.modules, "execution.debug_history_db", db)


def _import_performance_overview(monkeypatch: pytest.MonkeyPatch):
    module_name = "execution.pages.performance_overview"
    sys.modules.pop(module_name, None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setitem(sys.modules, "pandas", types.ModuleType("pandas"))
    _install_result_tracker_db(monkeypatch)
    _install_api_usage_tracker(monkeypatch)
    _install_debug_history_db(monkeypatch)

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_performance_overview_inserts_workspace_root_once() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "performance_overview.py").read_text(encoding="utf-8")

    assert "WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "if str(WORKSPACE_ROOT) not in sys.path:" in source
    assert "Path(__file__).resolve().parent.parent.parent" not in source


def test_performance_overview_uses_current_streamlit_width_api(monkeypatch: pytest.MonkeyPatch) -> None:
    module, fake_streamlit = _import_performance_overview(monkeypatch)
    fake_streamlit.events.clear()

    module._render_line_chart("line")
    module._render_bar_chart("bar")
    module._render_dataframe("rows", hide_index=True)

    assert fake_streamlit.events == [
        ("line_chart", "line", {"width": "stretch"}),
        ("bar_chart", "bar", {"width": "stretch"}),
        ("dataframe", "rows", {"width": "stretch", "hide_index": True}),
    ]


def test_performance_overview_detects_chartable_row_ranges(monkeypatch: pytest.MonkeyPatch) -> None:
    module, _fake_streamlit = _import_performance_overview(monkeypatch)

    assert module._has_multiple_rows([{"day": "2026-06-05"}, {"day": "2026-06-06"}])
    assert not module._has_multiple_rows([{"day": "2026-06-06"}])
    assert not module._has_multiple_rows(object())


def test_performance_overview_watchdog_stats_reads_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module, _fake_streamlit = _import_performance_overview(monkeypatch)
    module.TMP_DIR = tmp_path
    (tmp_path / "watchdog_history.json").write_text(
        json.dumps(
            [
                {"timestamp": "2026-06-01T00:00:00", "status": "success"},
                {"timestamp": "2026-06-02T00:00:00", "status": "fail"},
                {"timestamp": "2026-06-03T00:00:00", "status": "pass"},
            ]
        ),
        encoding="utf-8",
    )

    stats = module._watchdog_stats()

    assert stats == {
        "success_rate": 66.7,
        "last_run": "2026-06-03T00:00:00",
        "total": 3,
        "success": 2,
    }


def test_performance_overview_source_avoids_deprecated_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "performance_overview.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'st.line_chart(data, width="stretch")' in source
    assert 'st.bar_chart(data, width="stretch")' in source
    assert 'st.dataframe(data, width="stretch", **kwargs)' in source
    assert "if _has_multiple_rows(df_trend):" in source
    assert "if _has_multiple_rows(df_daily):" in source
