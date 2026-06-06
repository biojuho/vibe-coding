from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_space_scale_module():
    module_path = Path(__file__).resolve().parents[2] / "tools" / "space_scale.py"
    spec = importlib.util.spec_from_file_location("space_scale_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_space_scale_timing_helpers_keep_demo_timeline():
    module = _load_space_scale_module()
    generator = module.SpaceScaleGenerator(module.DEMO_SCALES, duration=42.0)
    item_count = len(module.DEMO_SCALES)

    scale_end, outro_start, rewind_start = generator._phase_bounds()

    assert scale_end == pytest.approx(35.5)
    assert outro_start == pytest.approx(35.5)
    assert rewind_start == pytest.approx(39.5)

    idx, local_t = generator._scale_phase_step(generator.step_dur + 0.25, item_count)
    assert idx == 1
    assert local_t == pytest.approx(0.25)
    assert generator._warp_speed(1, 0.0, item_count) == pytest.approx(6.0)


def test_space_scale_transition_helpers_match_original_curves():
    module = _load_space_scale_module()
    generator = module.SpaceScaleGenerator(module.DEMO_SCALES, duration=42.0)
    item_count = len(module.DEMO_SCALES)

    previous = generator._previous_item_transition(1, 0.0)
    assert previous is not None
    prev_scale, prev_alpha = previous
    assert prev_scale == pytest.approx(1.0)
    assert prev_alpha == 255

    cur_scale, cur_alpha, text_t = generator._current_item_transition(1, 0.0, item_count)
    assert cur_scale == pytest.approx(0.1)
    assert cur_alpha == 0
    assert text_t == pytest.approx(0.0)

    exit_lt = generator.step_dur - generator.trans_dur / 2
    exit_prog = generator._eo((exit_lt - (generator.step_dur - generator.trans_dur)) / generator.trans_dur)
    cur_scale, cur_alpha, _ = generator._current_item_transition(0, exit_lt, item_count)
    assert cur_scale == pytest.approx(1.0 - exit_prog * 0.9)
    assert cur_alpha == int(255 * (1 - exit_prog))


def test_space_scale_render_phases_return_nonblank_frames():
    module = _load_space_scale_module()
    generator = module.SpaceScaleGenerator(module.DEMO_SCALES, duration=42.0)
    timestamps = [
        0.0,
        generator.step_dur + 0.25,
        generator.total_scale_dur + 1.0,
        generator.total_scale_dur + generator.outro_dur + 1.0,
    ]

    for timestamp in timestamps:
        frame = generator._render(timestamp)

        assert frame.shape == (generator.H, generator.W, 3)
        assert frame.dtype.name == "uint8"
        assert frame.max() > frame.min()
