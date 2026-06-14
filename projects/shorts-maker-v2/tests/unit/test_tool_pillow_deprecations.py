from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TOOL_RENDER_CASES = [
    ("health_do_vs_dont", "HealthDoVsDontGenerator", "DEMO_DATA", "_render", 1.0),
    ("health_mental_message", "MentalHealthMessageGenerator", "DEMO_DATA", "_render", 1.0),
    ("health_medical_study", "MedicalStudyGenerator", "DEMO_DATA", "_render", 1.0),
    ("history_mystery", "HistoryMysteryGenerator", "DEMO_DATA", "_render", 1.0),
    ("history_timeline", "HistoryTimelineGenerator", "DEMO_DATA", "_render", 1.0),
    ("psychology_quiz", "PsychologyQuizGenerator", "DEMO_DATA", "_render", 1.0),
    ("psychology_shorts", "PsychologyShortsGenerator", "DEMO_DATA", "_render_frame", 1.0),
    ("space_fact_bomb", "SpaceFactBombGenerator", "DEMO_FACTS", "_render", 1.0),
]


def _load_tool_module(module_name: str):
    module_path = PROJECT_ROOT / "tools" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"{module_name}_pillow_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _assert_rgb_frame(frame, generator):
    assert frame.shape == (generator.H, generator.W, 3)
    assert frame.dtype.name == "uint8"
    assert frame.max() > frame.min()


@pytest.mark.parametrize(("module_name", "class_name", "demo_name", "render_name", "timestamp"), TOOL_RENDER_CASES)
def test_tool_demo_renderers_do_not_emit_pillow_mode_deprecations(
    module_name: str,
    class_name: str,
    demo_name: str,
    render_name: str,
    timestamp: float,
):
    module = _load_tool_module(module_name)
    generator = getattr(module, class_name)(**getattr(module, demo_name))

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        frame = getattr(generator, render_name)(timestamp)

    _assert_rgb_frame(frame, generator)


def test_space_scale_demo_renderer_does_not_emit_pillow_mode_deprecations():
    module = _load_tool_module("space_scale")
    generator = module.SpaceScaleGenerator(scales=module.DEMO_SCALES, duration=42.0)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        frame = generator._render(1.0)

    _assert_rgb_frame(frame, generator)
