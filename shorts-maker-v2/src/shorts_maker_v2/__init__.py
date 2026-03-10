from __future__ import annotations

__all__ = ["run_cli"]


def __getattr__(name: str):
    """Lazy-load heavy submodules (moviepy etc.) only when actually accessed."""
    if name == "run_cli":
        from shorts_maker_v2.cli import run_cli  # noqa: PLC0415
        return run_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

