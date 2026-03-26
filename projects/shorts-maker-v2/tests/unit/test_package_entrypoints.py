from __future__ import annotations

import importlib
import io
import runpy
import sys
from types import ModuleType

import pytest


def test_package_getattr_returns_lazy_run_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    package = importlib.import_module("shorts_maker_v2")
    fake_cli = ModuleType("shorts_maker_v2.cli")

    def fake_run_cli() -> int:
        return 123

    fake_cli.run_cli = fake_run_cli
    monkeypatch.setitem(sys.modules, "shorts_maker_v2.cli", fake_cli)

    assert package.run_cli is fake_run_cli


def test_package_getattr_raises_for_unknown_attribute() -> None:
    package = importlib.import_module("shorts_maker_v2")

    with pytest.raises(AttributeError, match="missing"):
        _ = package.missing


def test_package_main_rewraps_cp949_streams_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_cli = ModuleType("shorts_maker_v2.cli")

    def fake_run_cli() -> int:
        return 7

    fake_cli.run_cli = fake_run_cli
    monkeypatch.setitem(sys.modules, "shorts_maker_v2.cli", fake_cli)
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="cp949"), raising=False)
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="cp949"), raising=False)

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("shorts_maker_v2.__main__", run_name="__main__")

    assert excinfo.value.code == 7
    assert sys.stdout.encoding.lower() == "utf-8"
    assert sys.stderr.encoding.lower() == "utf-8"
