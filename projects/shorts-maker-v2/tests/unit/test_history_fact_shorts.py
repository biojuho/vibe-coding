from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_history_fact_module():
    module_path = Path(__file__).resolve().parents[2] / "tools" / "history_fact_shorts.py"
    spec = importlib.util.spec_from_file_location("history_fact_shorts_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_countdown_timing_segments_demo_countdown():
    module = _load_history_fact_module()
    generator = module.HistoryCountdownGenerator(**module.DEMO_COUNTDOWN)

    hook_end, item_dur, cta_start, item_count = generator._countdown_timing()

    assert hook_end == 4.0
    assert item_count == 5
    assert item_dur == pytest.approx(6.2)
    assert cta_start == 35.0


def test_countdown_background_gradient_is_cached_from_original_formula():
    module = _load_history_fact_module()
    generator = module.HistoryCountdownGenerator(**module.DEMO_COUNTDOWN)

    gradient = generator._bg_gradient

    assert gradient.shape == (generator.H, generator.W, 3)
    assert gradient[0, 0].tolist() == [26, 20, 8]
    assert gradient[-1, 0].tolist() == [33, 24, 10]


@pytest.mark.parametrize("timestamp", [1.0, 8.0, 36.0])
def test_countdown_render_phases_return_nonblank_frames(timestamp):
    module = _load_history_fact_module()
    generator = module.HistoryCountdownGenerator(**module.DEMO_COUNTDOWN)

    frame = generator._render(timestamp)

    assert frame.shape == (generator.H, generator.W, 3)
    assert frame.dtype.name == "uint8"
    assert frame.max() > frame.min()
