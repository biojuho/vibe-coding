"""T4-2: ROI Calculator 단위 테스트."""
from __future__ import annotations

from execution.roi_calculator import ROICalculator, ChannelROISummary


def test_estimate_content_cost_default() -> None:
    calc = ROICalculator()
    cost = calc.estimate_content_cost()
    # LLM(0.25) + TTS(0.0008*35) + Image(0.04*5) = 0.25 + 0.028 + 0.20 = 0.478
    assert cost > 0.4
    assert cost < 0.6


def test_estimate_content_cost_custom() -> None:
    calc = ROICalculator()
    cost = calc.estimate_content_cost(scene_count=3, duration_sec=20)
    assert cost > 0


def test_estimate_content_cost_direct() -> None:
    calc = ROICalculator()
    cost = calc.estimate_content_cost(cost_usd=0.15)
    assert cost == 0.15


def test_estimate_revenue() -> None:
    calc = ROICalculator(rpm=2.0)
    revenue = calc.estimate_revenue(10000)
    assert revenue == 20.0  # 10000/1000 * 2.0


def test_estimate_revenue_zero_views() -> None:
    calc = ROICalculator(rpm=2.0)
    assert calc.estimate_revenue(0) == 0.0


def test_calculate_roi_profit() -> None:
    calc = ROICalculator(rpm=2.0)
    result = calc.calculate_roi(cost=0.10, views=1000)
    # revenue = 1000/1000 * 2.0 = 2.0
    # ROI = (2.0 - 0.10) / 0.10 * 100 = 1900%
    assert result.roi_percent > 0
    assert result.estimated_revenue == 2.0


def test_calculate_roi_loss() -> None:
    calc = ROICalculator(rpm=0.5)
    result = calc.calculate_roi(cost=1.0, views=100)
    # revenue = 100/1000 * 0.5 = 0.05
    assert result.roi_percent < 0


def test_calculate_breakeven_views() -> None:
    calc = ROICalculator(rpm=2.0)
    bev = calc.calculate_breakeven_views(cost=0.10)
    # 0.10 / 2.0 * 1000 = 50
    assert bev == 50


def test_calculate_breakeven_views_zero_rpm() -> None:
    calc = ROICalculator(rpm=0)
    assert calc.calculate_breakeven_views(cost=0.10) == 0


def test_generate_channel_summary_empty() -> None:
    calc = ROICalculator()
    summary = calc.generate_channel_summary([])
    assert summary.total_content == 0
    assert summary.breakeven_status == "breakeven"


def test_generate_channel_summary_profit() -> None:
    calc = ROICalculator(rpm=5.0)
    contents = [
        {"title": "A", "channel": "test", "views": 10000, "cost_usd": 0.10},
        {"title": "B", "channel": "test", "views": 5000, "cost_usd": 0.10},
    ]
    summary = calc.generate_channel_summary(contents)
    assert summary.channel == "test"
    assert summary.total_content == 2
    assert summary.breakeven_status == "profit"
    assert summary.avg_roi_percent > 0


def test_generate_channel_summary_loss() -> None:
    calc = ROICalculator(rpm=0.01)
    contents = [
        {"title": "A", "channel": "loss_ch", "views": 10, "cost_usd": 5.0},
    ]
    summary = calc.generate_channel_summary(contents)
    assert summary.breakeven_status == "loss"
