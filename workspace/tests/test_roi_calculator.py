"""ROICalculator 단위 테스트."""

from execution.roi_calculator import (
    ChannelROISummary,
    ContentCost,
    ROICalculator,
    ROIResult,
)


class TestContentCost:
    def test_total_cost_auto_calculated(self):
        c = ContentCost(
            content_id=1,
            title="t",
            channel="ai_tech",
            llm_cost=0.25,
            tts_cost=0.03,
            image_cost=0.2,
            infra_cost=0.01,
        )
        assert c.total_cost == 0.25 + 0.03 + 0.2 + 0.01

    def test_total_cost_defaults_to_zero(self):
        c = ContentCost(content_id=1, title="t", channel="ch")
        assert c.total_cost == 0.0


class TestROICalculator:
    def test_defaults(self):
        calc = ROICalculator()
        assert calc.rpm == 1.5
        assert calc.costs["llm_per_job"] == 0.25

    def test_custom_rpm(self):
        calc = ROICalculator(rpm=3.0)
        assert calc.rpm == 3.0

    def test_custom_costs_merge(self):
        calc = ROICalculator(costs={"llm_per_job": 0.01})
        assert calc.costs["llm_per_job"] == 0.01
        assert calc.costs["tts_per_second"] == 0.0008  # default preserved

    def test_estimate_content_cost_defaults(self):
        calc = ROICalculator()
        cost = calc.estimate_content_cost()
        # llm=0.25 + tts=0.0008*35 + img=0.04*5 = 0.25 + 0.028 + 0.2 = 0.478
        assert cost == 0.478

    def test_estimate_content_cost_custom_scenes(self):
        calc = ROICalculator()
        cost = calc.estimate_content_cost(scene_count=3, duration_sec=20)
        # llm=0.25 + tts=0.0008*20 + img=0.04*3 = 0.25 + 0.016 + 0.12 = 0.386
        assert cost == 0.386

    def test_estimate_content_cost_direct(self):
        calc = ROICalculator()
        cost = calc.estimate_content_cost(cost_usd=1.23)
        assert cost == 1.23

    def test_estimate_revenue(self):
        calc = ROICalculator(rpm=2.0)
        rev = calc.estimate_revenue(10000)
        assert rev == 20.0

    def test_estimate_revenue_zero_views(self):
        calc = ROICalculator()
        assert calc.estimate_revenue(0) == 0.0

    def test_calculate_roi_profit(self):
        calc = ROICalculator(rpm=2.0)
        result = calc.calculate_roi(cost=0.5, views=10000)
        assert isinstance(result, ROIResult)
        assert result.estimated_revenue == 20.0
        assert result.roi_percent > 0
        assert result.breakeven_views == 250

    def test_calculate_roi_loss(self):
        calc = ROICalculator(rpm=1.0)
        result = calc.calculate_roi(cost=5.0, views=100)
        assert result.roi_percent < 0

    def test_calculate_breakeven_views(self):
        calc = ROICalculator(rpm=2.0)
        assert calc.calculate_breakeven_views(1.0) == 500

    def test_calculate_breakeven_views_zero_rpm(self):
        calc = ROICalculator(rpm=0)
        assert calc.calculate_breakeven_views(1.0) == 0

    def test_generate_channel_summary_empty(self):
        calc = ROICalculator()
        summary = calc.generate_channel_summary([])
        assert isinstance(summary, ChannelROISummary)
        assert summary.total_content == 0
        assert summary.breakeven_status == "breakeven"

    def test_generate_channel_summary_profit(self):
        calc = ROICalculator(rpm=10.0)
        contents = [
            {"title": "A", "channel": "ai_tech", "views": 5000, "cost_usd": 0.5},
            {"title": "B", "channel": "ai_tech", "views": 8000, "cost_usd": 0.5},
        ]
        summary = calc.generate_channel_summary(contents)
        assert summary.channel == "ai_tech"
        assert summary.total_content == 2
        assert summary.breakeven_status == "profit"
        assert summary.avg_views_per_content == 6500.0

    def test_generate_channel_summary_loss(self):
        calc = ROICalculator(rpm=0.01)
        contents = [
            {"title": "X", "channel": "space", "views": 10, "cost_usd": 10.0},
        ]
        summary = calc.generate_channel_summary(contents)
        assert summary.breakeven_status == "loss"

    def test_generate_channel_summary_breakeven(self):
        calc = ROICalculator(rpm=1.0)
        contents = [
            {"title": "Y", "channel": "health", "views": 500, "cost_usd": 0.5},
        ]
        summary = calc.generate_channel_summary(contents)
        assert summary.breakeven_status == "breakeven"
