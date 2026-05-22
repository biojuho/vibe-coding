"""Tests for validate_safe_zone and gate_safe_zone."""

from __future__ import annotations

import pytest

from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.pipeline.qc_step import QCStep
from shorts_maker_v2.render.caption_pillow import (
    CaptionStyle,
    calculate_safe_position,
    validate_safe_zone,
)


def _plan(scene_id: int, narration: str, role: str = "body") -> ScenePlan:
    return ScenePlan(
        scene_id=scene_id,
        narration_ko=narration,
        visual_prompt_en="visual",
        target_sec=5.0,
        structure_role=role,
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


class TestGateSafeZone:
    """QCStep.gate_safe_zone — 자막이 YouTube Shorts UI 안전 영역에 들어가는지 검수."""

    def test_short_captions_pass(self):
        """짧은 나레이션 → 자막이 안전 영역에 들어가 PASS."""
        plans = [_plan(1, "짧은 자막입니다.", role="hook"), _plan(2, "본문 한 줄입니다.")]
        report = QCStep.gate_safe_zone(plans, [])
        assert report.verdict == "pass"
        assert report.issues == []
        assert all(report.checks.values())

    def test_overlong_caption_holds_with_scene_issue(self):
        """안전 영역에 다 담을 수 없을 만큼 긴 나레이션 → HOLD + 해당 씬 이슈."""
        plans = [_plan(1, "짧은 본문."), _plan(2, "가" * 600)]
        report = QCStep.gate_safe_zone(plans, [])
        assert report.verdict == "hold"
        assert len(report.issues) == 1
        assert "Scene 2" in report.issues[0]
        # 정상 씬은 통과, 오버플로우 씬만 실패로 기록된다
        assert report.checks["safe_zone_s1"] is True
        assert report.checks["safe_zone_s2"] is False

    def test_empty_scene_plans_pass(self):
        """씬이 없으면 검사할 자막도 없으므로 PASS (빈 이슈)."""
        report = QCStep.gate_safe_zone([], [])
        assert report.verdict == "pass"
        assert report.issues == []
