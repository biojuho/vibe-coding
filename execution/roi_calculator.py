"""
콘텐츠 ROI 계산기 — 비용 대비 수익 분석.

콘텐츠당 비용(LLM+TTS+이미지)을 산출하고, YouTube AdSense RPM 기반
예상 수익을 계산하여 채널별 ROI를 제공합니다.

Usage:
    from execution.roi_calculator import ROICalculator
    calc = ROICalculator()
    report = calc.generate_report(channel="ai_tech")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ContentCost:
    """단일 콘텐츠의 비용 내역."""
    content_id: int
    title: str
    channel: str
    llm_cost: float = 0.0
    tts_cost: float = 0.0
    image_cost: float = 0.0
    infra_cost: float = 0.0
    total_cost: float = 0.0

    def __post_init__(self) -> None:
        self.total_cost = self.llm_cost + self.tts_cost + self.image_cost + self.infra_cost


@dataclass
class ROIResult:
    """ROI 분석 결과."""
    content_id: int
    title: str
    channel: str
    total_cost: float
    views: int
    estimated_revenue: float
    roi_percent: float  # (revenue - cost) / cost * 100
    breakeven_views: int  # 손익분기점 조회수


@dataclass
class ChannelROISummary:
    """채널별 ROI 요약."""
    channel: str
    total_content: int
    total_cost: float
    total_views: int
    total_estimated_revenue: float
    avg_roi_percent: float
    avg_cost_per_content: float
    avg_views_per_content: float
    breakeven_status: str  # "profit" | "loss" | "breakeven"


# ── 기본 비용 상수 (AppConfig costs 기반) ──────────────────
DEFAULT_COSTS = {
    "llm_per_job": 0.25,        # 대본 생성 1건
    "tts_per_second": 0.0008,   # EdgeTTS (실제 무료, 폴백용 OpenAI 기준)
    "image_per_scene": 0.04,    # DALL-E 3 기준
    "stock_per_scene": 0.0,     # Pexels = 무료
    "avg_scenes": 5,            # 평균 씬 수
    "avg_duration_sec": 35,     # 평균 영상 길이
}


class ROICalculator:
    """콘텐츠 ROI 계산기.

    Args:
        rpm: YouTube AdSense RPM (Revenue Per Mille, 1000 조회당 수익 $)
             기본값: $1.5 (한국 Shorts 평균 RPM 추정)
        costs: 비용 상수 딕셔너리
    """

    def __init__(
        self,
        rpm: float = 1.5,
        costs: dict[str, float] | None = None,
    ) -> None:
        self.rpm = rpm
        self.costs = {**DEFAULT_COSTS, **(costs or {})}

    def estimate_content_cost(
        self,
        scene_count: int | None = None,
        duration_sec: float | None = None,
        cost_usd: float | None = None,
    ) -> float:
        """콘텐츠 1건의 예상 비용 산출.

        Args:
            scene_count: 씬 수 (없으면 기본값 사용)
            duration_sec: 영상 길이 (없으면 기본값 사용)
            cost_usd: 이미 계산된 비용이 있으면 직접 사용

        Returns:
            예상 비용 ($)
        """
        if cost_usd is not None:
            return cost_usd

        scenes = scene_count or int(self.costs["avg_scenes"])
        dur = duration_sec or self.costs["avg_duration_sec"]

        llm = self.costs["llm_per_job"]
        tts = self.costs["tts_per_second"] * dur
        img = self.costs["image_per_scene"] * scenes

        return round(llm + tts + img, 4)

    def estimate_revenue(self, views: int) -> float:
        """조회수 기반 예상 수익 산출.

        Returns:
            예상 수익 ($)
        """
        return round((views / 1000) * self.rpm, 4)

    def calculate_roi(
        self,
        cost: float,
        views: int,
    ) -> ROIResult:
        """단일 콘텐츠의 ROI 계산.

        Returns:
            ROIResult 객체
        """
        revenue = self.estimate_revenue(views)
        roi_pct = ((revenue - cost) / max(cost, 0.001)) * 100
        breakeven = int((cost / max(self.rpm, 0.001)) * 1000) if self.rpm > 0 else 0

        return ROIResult(
            content_id=0,
            title="",
            channel="",
            total_cost=cost,
            views=views,
            estimated_revenue=revenue,
            roi_percent=round(roi_pct, 1),
            breakeven_views=breakeven,
        )

    def calculate_breakeven_views(self, cost: float) -> int:
        """손익분기점 조회수 계산."""
        if self.rpm <= 0:
            return 0
        return int((cost / self.rpm) * 1000)

    def generate_channel_summary(
        self,
        contents: list[dict[str, Any]],
    ) -> ChannelROISummary:
        """채널의 전체 콘텐츠 ROI 요약.

        Args:
            contents: [{"title": str, "channel": str, "views": int, "cost_usd": float}, ...]

        Returns:
            ChannelROISummary
        """
        if not contents:
            return ChannelROISummary(
                channel="",
                total_content=0,
                total_cost=0,
                total_views=0,
                total_estimated_revenue=0,
                avg_roi_percent=0,
                avg_cost_per_content=0,
                avg_views_per_content=0,
                breakeven_status="breakeven",
            )

        channel = contents[0].get("channel", "unknown")
        total_cost = 0.0
        total_views = 0
        total_revenue = 0.0
        roi_percents: list[float] = []

        for c in contents:
            cost = self.estimate_content_cost(cost_usd=c.get("cost_usd"))
            views = c.get("views", 0)
            revenue = self.estimate_revenue(views)

            total_cost += cost
            total_views += views
            total_revenue += revenue

            roi = ((revenue - cost) / max(cost, 0.001)) * 100
            roi_percents.append(roi)

        avg_roi = sum(roi_percents) / len(roi_percents) if roi_percents else 0
        n = len(contents)

        if total_revenue > total_cost * 1.05:
            status = "profit"
        elif total_revenue < total_cost * 0.95:
            status = "loss"
        else:
            status = "breakeven"

        return ChannelROISummary(
            channel=channel,
            total_content=n,
            total_cost=round(total_cost, 4),
            total_views=total_views,
            total_estimated_revenue=round(total_revenue, 4),
            avg_roi_percent=round(avg_roi, 1),
            avg_cost_per_content=round(total_cost / max(n, 1), 4),
            avg_views_per_content=round(total_views / max(n, 1), 1),
            breakeven_status=status,
        )
