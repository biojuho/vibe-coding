from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from ShortsFactory.engines.layout_engine import LayoutEngine


def _engine() -> LayoutEngine:
    return LayoutEngine(
        {
            "palette": {"bg": "#0A0E1A", "primary": "#00D4FF", "accent": "#00FF88"},
            "font_title": "Pretendard-Bold",
            "font_body": "Pretendard-Regular",
        }
    )


def _is_nonblank(path: Path) -> bool:
    with Image.open(path) as img:
        extrema = img.convert("RGBA").getextrema()
    return any(low != high for low, high in extrema)


def test_resolve_output_path_creates_parent_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "layout.png"

    resolved = LayoutEngine._resolve_output_path(target)

    assert resolved == target
    assert target.parent.exists()


def test_wrap_lines_reuses_layout_measurement() -> None:
    font = ImageFont.load_default()
    lines = LayoutEngine._wrap_lines("alpha beta gamma delta", font, 60)

    assert lines == LayoutEngine._wrapped_lines_with_draw(
        "alpha beta gamma delta",
        font,
        60,
        ImageDraw.Draw(Image.new("RGB", (1, 1))),
    )
    assert all(lines)


@pytest.mark.parametrize(
    ("name", "render", "expected_size"),
    [
        (
            "split_screen",
            lambda engine, path: engine.split_screen(
                "Ship reliable experiments every day",
                "Skip verification and hope",
                left_label="DO",
                right_label="DONT",
                output_path=path,
            ),
            (1080, 1920),
        ),
        (
            "card_layout",
            lambda engine, path: engine.card_layout(
                [
                    {"title": "Evidence", "body": "Focused tests protect the layout."},
                    {"title": "Launch", "body": "Keep local gates green."},
                ],
                output_path=path,
            ),
            (1080, 1920),
        ),
        (
            "timeline_layout",
            lambda engine, path: engine.timeline_layout(
                [
                    {"date": "D1", "title": "Explore", "desc": "Map graph context."},
                    {"date": "D2", "title": "Verify", "desc": "Run image hashes."},
                ],
                output_path=path,
            ),
            (1080, 1920),
        ),
        (
            "vs_title_bar",
            lambda engine, path: engine.vs_title_bar("Option A", "Option B", output_path=path),
            (1080, 288),
        ),
        (
            "vs_split_cards",
            lambda engine, path: engine.vs_split_cards("Fast iteration", "Risky rewrites", output_path=path),
            (1080, 1056),
        ),
        (
            "vs_score_bar",
            lambda engine, path: engine.vs_score_bar("Reliability", 84, 63, output_path=path),
            (1080, 110),
        ),
        (
            "numbered_list_layout",
            lambda engine, path: engine.numbered_list_layout(
                ["Pick a target", "Add coverage", "Adopt on improvement"],
                title="Loop",
                output_path=path,
            ),
            (1080, 1920),
        ),
        (
            "image_text_overlay",
            lambda engine, path: engine.image_text_overlay(
                "Launch evidence stays readable",
                position="center",
                output_path=path,
            ),
            (1080, 1920),
        ),
        (
            "metric_dashboard",
            lambda engine, path: engine.metric_dashboard(
                [
                    {"label": "QC", "value": "100%", "change": "+2%"},
                    {"label": "Risk", "value": "Low", "change": "-1%"},
                    {"label": "Speed", "value": "Fast", "change": "+5%"},
                ],
                title="Readiness",
                output_path=path,
            ),
            (1080, 1920),
        ),
        (
            "step_by_step_layout",
            lambda engine, path: engine.step_by_step_layout(
                [
                    {"label": "STEP 1", "title": "Graph", "desc": "Confirm callers."},
                    {"label": "STEP 2", "title": "Patch", "desc": "Extract helpers."},
                    {"label": "STEP 3", "title": "Gate", "desc": "Run checks."},
                ],
                title="Process",
                output_path=path,
            ),
            (1080, 1920),
        ),
        (
            "quote_card",
            lambda engine, path: engine.quote_card(
                "Evidence beats optimism when preparing a launch.",
                author="Codex",
                output_path=path,
            ),
            (1080, 500),
        ),
        (
            "comparison_table",
            lambda engine, path: engine.comparison_table(
                ["Area", "Before", "After"],
                [["Coverage", "Archive", "Active"], ["Risk", "Medium", "Lower"]],
                output_path=path,
            ),
            (1080, 300),
        ),
    ],
)
def test_layout_renderers_create_nonblank_expected_size(
    tmp_path: Path,
    name: str,
    render: Callable[[LayoutEngine, Path], Path],
    expected_size: tuple[int, int],
) -> None:
    output_path = tmp_path / f"{name}.png"

    result = render(_engine(), output_path)

    assert result == output_path
    with Image.open(result) as img:
        assert img.size == expected_size
    assert _is_nonblank(result)
