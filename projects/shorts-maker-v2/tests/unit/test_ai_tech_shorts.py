from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_ai_tech_module():
    module_path = Path(__file__).resolve().parents[2] / "tools" / "ai_tech_shorts.py"
    spec = importlib.util.spec_from_file_location("ai_tech_shorts_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (0.0, "intro"),
        (3.99, "intro"),
        (4.0, "points"),
        (26.99, "points"),
        (27.0, "verdict"),
        (34.0, "verdict"),
    ],
)
def test_tech_vs_phase_boundaries_match_demo(timestamp, expected):
    module = _load_ai_tech_module()
    generator = module.TechVSShortsGenerator(**module.DEMO_VS)

    assert generator._phase(timestamp) == expected


@pytest.mark.parametrize("timestamp", [0.0, 1.5, 5.0, 12.0, 28.0, 34.0])
def test_tech_vs_render_phases_return_nonblank_frames(timestamp):
    module = _load_ai_tech_module()
    generator = module.TechVSShortsGenerator(**module.DEMO_VS)

    frame = generator._render(timestamp)

    assert frame.shape == (generator.H, generator.W, 3)
    assert frame.dtype.name == "uint8"
    assert frame.max() > frame.min()
