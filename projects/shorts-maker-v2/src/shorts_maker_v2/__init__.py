from __future__ import annotations

import importlib
import importlib.util
import sys

__all__ = ["run_cli"]


def __getattr__(name: str):
    """Lazy-load heavy submodules (moviepy etc.) only when actually accessed."""
    if name == "run_cli":
        cli = importlib.import_module("shorts_maker_v2.cli")
        return cli.run_cli
    submodule_name = f"{__name__}.{name}"
    existing = sys.modules.get(submodule_name)
    if existing is not None:
        globals()[name] = existing
        return existing
    if importlib.util.find_spec(submodule_name) is not None:
        module = importlib.import_module(submodule_name)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
