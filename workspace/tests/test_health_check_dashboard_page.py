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

    def selectbox(self, label, options, **kwargs):
        self._record("selectbox", {"label": label, "options": options}, **kwargs)
        return options[0]

    def button(self, label, **kwargs) -> bool:
        self._record("button", label, **kwargs)
        return False

    def stop(self) -> None:
        raise RuntimeError("streamlit stop called")

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self._record(name, args[0] if args else None, **kwargs)

        return _method


def _install_fake_health_check(monkeypatch: pytest.MonkeyPatch) -> None:
    health_check = types.ModuleType("execution.health_check")
    health_check.STATUS_OK = "ok"
    health_check.STATUS_WARN = "warn"
    health_check.STATUS_FAIL = "fail"
    health_check.STATUS_SKIP = "skip"
    health_check.run_all_checks = lambda category=None: []
    health_check.get_summary = lambda results: {
        "overall": "ok",
        "counts": {"ok": 0, "warn": 0, "fail": 0, "skip": 0},
        "total": 0,
    }
    monkeypatch.setitem(sys.modules, "execution.health_check", health_check)


def _import_health_check_dashboard(monkeypatch: pytest.MonkeyPatch):
    module_name = "execution.pages.health_check_dashboard"
    sys.modules.pop(module_name, None)
    fake_streamlit = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    _install_fake_health_check(monkeypatch)

    module = importlib.import_module(module_name)
    return module, fake_streamlit


def test_health_check_dashboard_inserts_workspace_root_once() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "health_check_dashboard.py").read_text(encoding="utf-8")

    assert "WORKSPACE_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "if str(WORKSPACE_ROOT) not in sys.path:" in source
    assert "sys.path.insert(0, str(WORKSPACE_ROOT))" in source
    assert "Path(__file__).resolve().parent.parent" not in source


def test_health_check_dashboard_uses_current_button_width_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, fake_streamlit = _import_health_check_dashboard(monkeypatch)

    assert module._stretch_button_kwargs() == {"width": "stretch"}
    button_events = [event for event in fake_streamlit.events if event[0] == "button"]
    assert button_events == [
        (
            "button",
            "🔍 점검 실행",
            {"type": "primary", "width": "stretch"},
        )
    ]


def test_health_check_dashboard_source_avoids_deprecated_width_api() -> None:
    source = (WORKSPACE_ROOT / "execution" / "pages" / "health_check_dashboard.py").read_text(encoding="utf-8")

    assert "use_container_width=True" not in source
    assert 'return {"width": "stretch"}' in source
    assert "**_stretch_button_kwargs()" in source
