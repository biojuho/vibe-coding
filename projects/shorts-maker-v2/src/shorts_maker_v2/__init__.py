from __future__ import annotations

import importlib

__all__ = ["run_cli"]


def __getattr__(name: str):
    """Lazy-load heavy submodules (moviepy etc.) only when actually accessed."""
    if name == "run_cli":
        cli = importlib.import_module("shorts_maker_v2.cli")
        return cli.run_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
