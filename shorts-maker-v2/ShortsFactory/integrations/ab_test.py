"""ab_test.py — A/B 테스트 프레임워크.

같은 주제로 다른 스타일/훅/템포의 영상을 자동 생성 + 성과 비교

Usage:
    from ShortsFactory.integrations.ab_test import ABTestRunner
    
    runner = ABTestRunner(channel="space")
    runner.add_variant("A", template="space_fact_bomb", overrides={"hook_text": "충격 통계형"})
    runner.add_variant("B", template="space_scale",     overrides={"hook_text": "질문형"})
    results = runner.run(topic="블랙홀의 비밀", data={...})
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ShortsFactory.ab_test")

_PROJECT = Path(__file__).resolve().parent.parent.parent


@dataclass
class Variant:
    """A/B 테스트 변형."""
    name: str
    template: str
    overrides: dict[str, Any] = field(default_factory=dict)
    output_path: str = ""
    video_id: str = ""     # YouTube 업로드 후 ID
    status: str = "pending"
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """A/B 테스트 결과."""
    test_id: str
    topic: str
    channel: str
    created_at: str
    variants: list[Variant]
    winner: str = ""
    confidence: float = 0.0


class ABTestRunner:
    """A/B 테스트 실행기."""

    def __init__(self, channel: str):
        self.channel = channel
        self.variants: list[Variant] = []
        self._results_dir = _PROJECT / "ab_results"
        self._results_dir.mkdir(exist_ok=True)

    def add_variant(
        self, name: str, template: str, overrides: dict | None = None,
    ) -> "ABTestRunner":
        """변형 추가."""
        self.variants.append(Variant(
            name=name, template=template,
            overrides=overrides or {},
        ))
        return self

    def run(self, topic: str, data: dict[str, Any]) -> ABTestResult:
        """모든 변형을 렌더링하고 결과 저장."""
        from ShortsFactory.pipeline import ShortsFactory

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_id = f"ab_{self.channel}_{ts}"

        for variant in self.variants:
            merged = {**data, **variant.overrides}
            out_path = f"output/ab/{test_id}/{variant.name}_{variant.template}.mp4"

            try:
                factory = ShortsFactory(channel=self.channel)
                factory.create(variant.template, merged)
                result = factory.render(out_path)
                variant.output_path = result
                variant.status = "rendered"
                logger.info(f"  Variant {variant.name}: rendered -> {result}")
            except Exception as e:
                variant.status = f"error: {e}"
                logger.error(f"  Variant {variant.name}: failed -> {e}")

        result = ABTestResult(
            test_id=test_id,
            topic=topic,
            channel=self.channel,
            created_at=ts,
            variants=self.variants,
        )

        self._save_result(result)
        return result

    def _save_result(self, result: ABTestResult):
        """결과를 JSON으로 저장."""
        path = self._results_dir / f"{result.test_id}.json"
        data = {
            "test_id": result.test_id,
            "topic": result.topic,
            "channel": result.channel,
            "created_at": result.created_at,
            "variants": [
                {
                    "name": v.name,
                    "template": v.template,
                    "overrides": v.overrides,
                    "output_path": v.output_path,
                    "video_id": v.video_id,
                    "status": v.status,
                    "metrics": v.metrics,
                }
                for v in result.variants
            ],
            "winner": result.winner,
            "confidence": result.confidence,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"A/B test saved: {path}")


class ABTestAnalyzer:
    """A/B 테스트 결과 분석기.

    YouTube Analytics와 연동하여 각 Variant의 성과를 비교합니다.
    """

    # YouTube Analytics 지표
    METRICS = {
        "views": "조회수",
        "watch_time_sec": "총 시청 시간 (초)",
        "avg_view_duration": "평균 시청 시간",
        "avg_view_percentage": "평균 시청률 (%)",
        "likes": "좋아요",
        "comments": "댓글",
        "shares": "공유",
        "subscribers_gained": "구독 전환",
        "ctr": "클릭률 (CTR, %)",
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")

    def fetch_metrics(self, video_id: str) -> dict[str, float]:
        """YouTube Analytics API에서 지표 가져오기."""
        if not self.api_key:
            logger.warning("YOUTUBE_API_KEY not set. Returning mock metrics.")
            return self._mock_metrics()

        try:
            import requests
        except ImportError:
            return self._mock_metrics()

        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "statistics,contentDetails",
            "id": video_id,
            "key": self.api_key,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            logger.error(f"YouTube API error: {resp.status_code}")
            return {}

        items = resp.json().get("items", [])
        if not items:
            return {}

        stats = items[0].get("statistics", {})
        return {
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        }

    def analyze(self, test_result: ABTestResult) -> dict[str, Any]:
        """A/B 테스트 결과 분석."""
        for variant in test_result.variants:
            if variant.video_id:
                variant.metrics = self.fetch_metrics(variant.video_id)

        # 승자 결정 (단순: CTR + 시청률 가중 평균)
        scored = []
        for v in test_result.variants:
            if v.metrics:
                score = (
                    v.metrics.get("ctr", 0) * 0.4 +
                    v.metrics.get("avg_view_percentage", 0) * 0.3 +
                    v.metrics.get("likes", 0) / max(v.metrics.get("views", 1), 1) * 100 * 0.3
                )
                scored.append((v.name, score))

        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            test_result.winner = scored[0][0]
            if len(scored) > 1 and scored[1][1] > 0:
                test_result.confidence = (scored[0][1] - scored[1][1]) / scored[1][1] * 100

        return {
            "winner": test_result.winner,
            "confidence": f"{test_result.confidence:.1f}%",
            "scores": scored,
            "variants": {
                v.name: v.metrics for v in test_result.variants
            },
        }

    @staticmethod
    def _mock_metrics() -> dict[str, float]:
        """테스트용 목업 지표."""
        import random
        return {
            "views": random.randint(100, 5000),
            "likes": random.randint(5, 200),
            "comments": random.randint(0, 30),
            "ctr": round(random.uniform(3.0, 15.0), 1),
            "avg_view_percentage": round(random.uniform(40.0, 90.0), 1),
        }
