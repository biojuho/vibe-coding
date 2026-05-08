"""Tests for validate_safe_zone and gate_safe_zone."""

from __future__ import annotations

import pytest

from shorts_maker_v2.render.caption_pillow import (
    CaptionStyle,
    calculate_safe_position,
    validate_safe_zone,
)


class TestValidateSafeZone:
    """validate_safe_zone 함수 테스트."""

    def test_caption_in_safe_zone(self):
        """안전 영역 중앙의 캡션 → in_safe_zone=True."""
        result = validate_safe_zone(
            y_position=500,
            caption_height=100,
            canvas_height=1920,
        )
        assert result["in_safe_zone"] is True
        assert result["top_overflow_px"] == 0
        assert result["bottom_overflow_px"] == 0

    def test_caption_above_safe_zone(self):
        """상단 안전 영역 위로 넘어가는 캡션."""
        top_safe = int(1920 * 0.15)  # 288
        result = validate_safe_zone(
            y_position=100,  # 288보다 위
            caption_height=50,
            canvas_height=1920,
        )
        assert result["in_safe_zone"] is False
        assert result["top_overflow_px"] == top_safe - 100  # 188px

    def test_caption_below_safe_zone(self):
        """하단 안전 영역 아래로 넘어가는 캡션."""
        safe_bottom = 1920 - int(1920 * 0.20)  # 1536
        result = validate_safe_zone(
            y_position=1500,
            caption_height=100,  # bottom = 1600 > 1536
            canvas_height=1920,
        )
        assert result["in_safe_zone"] is False
        assert result["bottom_overflow_px"] == (1500 + 100) - safe_bottom

    def test_exactly_at_boundaries(self):
        """정확히 안전 영역 경계에 위치한 캡션."""
        top_safe = int(1920 * 0.15)  # 288
        safe_bottom = 1920 - int(1920 * 0.20)  # 1536
        caption_h = safe_bottom - top_safe
        result = validate_safe_zone(
            y_position=top_safe,
            caption_height=caption_h,
            canvas_height=1920,
        )
        assert result["in_safe_zone"] is True

    def test_custom_canvas_height(self):
        """1080px 캔버스에서의 안전 영역 검증."""
        result = validate_safe_zone(
            y_position=200,
            caption_height=50,
            canvas_height=1080,
        )
        top_safe = int(1080 * 0.15)  # 162
        assert result["safe_area_top"] == top_safe
        assert result["in_safe_zone"] is True

    def test_zero_height_caption(self):
        """0px 높이 캡션 (edge case)."""
        result = validate_safe_zone(
            y_position=500,
            caption_height=0,
            canvas_height=1920,
        )
        assert result["in_safe_zone"] is True


class TestCalculateSafePositionIntegration:
    """calculate_safe_position 결과가 항상 safe zone 내에 있는지 검증."""

    @pytest.fixture
    def default_style(self):
        return CaptionStyle(
            font_size=76,
            margin_x=40,
            bottom_offset=200,
            text_color="#FFFFFF",
            stroke_color="#000000",
            stroke_width=4,
            line_spacing=12,
            font_candidates=(),
        )

    @pytest.mark.parametrize("caption_height", [50, 100, 200, 400])
    def test_body_always_in_safe_zone(self, default_style, caption_height):
        """body 역할 캡션은 항상 안전 영역 내."""
        y = calculate_safe_position(1920, caption_height, default_style, role="body")
        result = validate_safe_zone(y, caption_height, 1920)
        assert result["in_safe_zone"] is True

    @pytest.mark.parametrize("caption_height", [50, 100, 200])
    def test_hook_always_in_safe_zone(self, default_style, caption_height):
        """hook 역할 캡션도 항상 안전 영역 내."""
        y = calculate_safe_position(1920, caption_height, default_style, role="hook")
        result = validate_safe_zone(y, caption_height, 1920)
        assert result["in_safe_zone"] is True
