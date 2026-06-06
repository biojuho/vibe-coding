from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_quote_module():
    module_path = Path(__file__).resolve().parents[2] / "tools" / "psychology_quote.py"
    spec = importlib.util.spec_from_file_location("psychology_quote_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_psychology_quote_timeline_matches_demo():
    module = _load_quote_module()
    generator = module.QuoteShortsGenerator(**module.DEMO_DATA)

    bg_fade_end, quote_start, quote_interval, author_start, fade_out_start = generator._timeline()

    assert bg_fade_end == pytest.approx(2.0)
    assert quote_start == pytest.approx(2.0)
    assert quote_interval == pytest.approx(0.5)
    assert author_start == pytest.approx(12.0)
    assert fade_out_start == pytest.approx(17.0)


def test_psychology_quote_frame_alpha_helpers_preserve_curves():
    module = _load_quote_module()
    generator = module.QuoteShortsGenerator(**module.DEMO_DATA)

    bg_alpha, global_alpha = generator._frame_alphas(1.0, 2.0, 17.0)
    assert bg_alpha == pytest.approx(0.875)
    assert global_alpha == pytest.approx(1.0)

    bg_alpha, global_alpha = generator._frame_alphas(18.5, 2.0, 17.0)
    assert bg_alpha == pytest.approx(1.0)
    assert global_alpha == pytest.approx(0.125)


@pytest.mark.parametrize(
    ("timestamp", "expect_nonblank"),
    [
        (0.0, False),
        (2.25, True),
        (12.5, True),
        (18.5, True),
    ],
)
def test_psychology_quote_render_phases_return_expected_frames(timestamp, expect_nonblank):
    module = _load_quote_module()
    generator = module.QuoteShortsGenerator(**module.DEMO_DATA)

    frame = generator._render(timestamp)

    assert frame.shape == (generator.H, generator.W, 3)
    assert frame.dtype.name == "uint8"
    if expect_nonblank:
        assert frame.max() > frame.min()
    else:
        assert frame.max() == frame.min()
