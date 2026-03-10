"""이미지 A/B 테스트 프레임워크 (P4-L4).

동일 콘텐츠에 대해 다양한 이미지 스타일 변형을 생성하고,
성과를 비교하여 최적의 이미지 스타일을 학습합니다.

사용법:
    tester = ImageABTester(config_mgr)
    variants = tester.generate_variants("연봉", "분노", "연봉 협상 실패 후기")
    report = tester.compare_results(results_a, results_b)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))


# ── 변형 스타일 정의 ─────────────────────────────────────────────────

# style / mood / colors 각 축에서 대안을 제공
_ALT_STYLES: dict[str, list[str]] = {
    "modern infographic": ["data visualization", "flat design infographic"],
    "dramatic illustration": ["cinematic scene", "editorial illustration"],
    "corporate meeting illustration": ["office environment 3D render", "watercolor office scene"],
    "conversation scene illustration": ["dialogue comic style", "minimalist two-person scene"],
    "cozy lifestyle illustration": ["warm interior design", "hygge lifestyle photo"],
    "warm family illustration": ["gentle watercolor family", "soft pastel family scene"],
    "finance chart illustration": ["money and coins 3D render", "stock market dashboard"],
    "comic-style office humor": ["kawaii office cartoon", "satirical editorial cartoon"],
    "tech-futuristic": ["cyberpunk tech scene", "clean minimalist tech"],
    "fitness illustration": ["health infographic", "calm wellness scene"],
    "newspaper editorial": ["protest scene illustration", "government building illustration"],
    "motivational poster": ["sunrise landscape", "journey path illustration"],
    "modern illustration": ["abstract geometric art", "watercolor scene"],
}

_ALT_MOODS: dict[str, list[str]] = {
    "professional, clean": ["bold and confident", "sleek and corporate"],
    "decisive, hopeful": ["adventurous, brave", "calm and certain"],
    "tense, frustrated": ["chaotic, overwhelming", "cold and distant"],
    "humorous, lighthearted": ["playful and silly", "witty and sarcastic"],
    "innovative, sleek": ["mysterious, cutting-edge", "warm and accessible tech"],
    "inspiring, ambitious": ["serene, peaceful", "energetic, dynamic"],
    "intense, frustrated": ["dark and moody", "explosive, angry"],
}


@dataclass
class ImageVariant:
    """이미지 변형 정보."""
    variant_id: str           # "A", "B", "C"
    variant_type: str         # "default", "alt_style", "alt_mood", "alt_colors"
    prompt: str               # 생성된 이미지 프롬프트
    style: str
    mood: str
    colors: str
    topic_cluster: str = ""
    emotion_axis: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "variant_type": self.variant_type,
            "prompt": self.prompt,
            "style": self.style,
            "mood": self.mood,
            "colors": self.colors,
            "topic_cluster": self.topic_cluster,
            "emotion_axis": self.emotion_axis,
        }


@dataclass
class ABTestResult:
    """A/B 테스트 결과."""
    test_id: str
    topic_cluster: str
    emotion_axis: str
    variants: list[ImageVariant]
    winner: str | None = None       # variant_id
    winner_reason: str = ""
    metrics: dict[str, dict[str, float]] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "topic_cluster": self.topic_cluster,
            "emotion_axis": self.emotion_axis,
            "variants": [v.to_dict() for v in self.variants],
            "winner": self.winner,
            "winner_reason": self.winner_reason,
            "metrics": self.metrics,
            "created_at": self.created_at,
        }


class ImageABTester:
    """이미지 A/B 테스트 관리자."""

    def __init__(self, config_mgr=None):
        self.config = config_mgr

    def generate_variants(
        self,
        topic_cluster: str,
        emotion_axis: str,
        title: str = "",
        max_variants: int = 3,
    ) -> list[ImageVariant]:
        """동일 콘텐츠에 대해 이미지 스타일 변형을 생성합니다.

        Args:
            topic_cluster: 토픽 클러스터.
            emotion_axis: 감정 축.
            title: 게시글 제목.
            max_variants: 최대 변형 수 (2-3).

        Returns:
            ImageVariant 리스트 (첫 번째 = default, 나머지 = 변형).
        """
        from pipeline.image_generator import (
            _TOPIC_IMAGE_STYLES,
            _DEFAULT_IMAGE_STYLE,
            _EMOTION_MOOD_OVERRIDE,
        )

        base_style_info = _TOPIC_IMAGE_STYLES.get(topic_cluster, _DEFAULT_IMAGE_STYLE)
        base_style = base_style_info["style"]
        base_mood = base_style_info["mood"]
        base_colors = base_style_info["colors"]

        # 감정 오버라이드 적용
        if emotion_axis in _EMOTION_MOOD_OVERRIDE:
            base_mood = _EMOTION_MOOD_OVERRIDE[emotion_axis]

        variants: list[ImageVariant] = []

        # Variant A: 기본 스타일
        default_prompt = self._build_prompt(title, base_style, base_mood, base_colors)
        variants.append(ImageVariant(
            variant_id="A",
            variant_type="default",
            prompt=default_prompt,
            style=base_style,
            mood=base_mood,
            colors=base_colors,
            topic_cluster=topic_cluster,
            emotion_axis=emotion_axis,
        ))

        # Variant B: 대안 스타일
        alt_styles = _ALT_STYLES.get(base_style, ["abstract art"])
        alt_style = random.choice(alt_styles)
        alt_prompt = self._build_prompt(title, alt_style, base_mood, base_colors)
        variants.append(ImageVariant(
            variant_id="B",
            variant_type="alt_style",
            prompt=alt_prompt,
            style=alt_style,
            mood=base_mood,
            colors=base_colors,
            topic_cluster=topic_cluster,
            emotion_axis=emotion_axis,
        ))

        # Variant C: 대안 무드 (max_variants >= 3일 때만)
        if max_variants >= 3:
            alt_moods = _ALT_MOODS.get(base_mood, ["atmospheric, evocative"])
            alt_mood = random.choice(alt_moods) if isinstance(alt_moods, list) else alt_moods
            alt_mood_prompt = self._build_prompt(title, base_style, alt_mood, base_colors)
            variants.append(ImageVariant(
                variant_id="C",
                variant_type="alt_mood",
                prompt=alt_mood_prompt,
                style=base_style,
                mood=alt_mood,
                colors=base_colors,
                topic_cluster=topic_cluster,
                emotion_axis=emotion_axis,
            ))

        return variants[:max_variants]

    def compare_results(
        self,
        variant_metrics: dict[str, dict[str, float]],
    ) -> ABTestResult:
        """변형별 성과를 비교하고 위너를 결정합니다.

        Args:
            variant_metrics: {
                "A": {"views": 500, "likes": 30, "retweets": 10},
                "B": {"views": 600, "likes": 45, "retweets": 15},
            }

        Returns:
            ABTestResult with winner determined.
        """
        if not variant_metrics:
            return ABTestResult(
                test_id="",
                topic_cluster="",
                emotion_axis="",
                variants=[],
                winner=None,
                winner_reason="데이터 없음",
            )

        # 참여율 기반 위너 결정
        # engagement_rate = (likes + retweets * 2) / views * 100
        scores: dict[str, float] = {}
        for vid, m in variant_metrics.items():
            views = float(m.get("views") or 0)
            likes = float(m.get("likes") or 0)
            retweets = float(m.get("retweets") or 0)
            if views > 0:
                scores[vid] = (likes + retweets * 2) / views * 100
            else:
                scores[vid] = 0.0

        # 통계적 유의성 판단 (간이)
        winner_id = max(scores, key=scores.get)  # type: ignore[arg-type]
        winner_score = scores[winner_id]

        # 2등과 5% 이상 차이 시 유의한 것으로 판단
        sorted_scores = sorted(scores.values(), reverse=True)
        margin = (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0] * 100 if len(sorted_scores) > 1 and sorted_scores[0] > 0 else 0

        if margin < 5:
            winner_reason = f"참여율 차이 미미 ({margin:.1f}%). 추가 데이터 필요."
            winner_id = None  # 유의하지 않음
        else:
            winner_reason = f"Variant {winner_id} 참여율 {winner_score:.2f}% (차이 {margin:.1f}%)"

        return ABTestResult(
            test_id=f"ab_{datetime.now(_KST).strftime('%Y%m%d_%H%M%S')}",
            topic_cluster="",
            emotion_axis="",
            variants=[],
            winner=winner_id,
            winner_reason=winner_reason,
            metrics=variant_metrics,
            created_at=datetime.now(_KST).isoformat(),
        )

    def generate_style_report(
        self,
        results: list[ABTestResult],
    ) -> dict[str, Any]:
        """복수 A/B 테스트 결과를 종합하여 스타일 추천 리포트 생성.

        Returns:
            {
                "total_tests": int,
                "decisive_tests": int,
                "style_wins": {"modern infographic": 3, ...},
                "recommended_updates": [{"topic": "연봉", "winning_style": "...", ...}],
            }
        """
        style_wins: dict[str, int] = {}
        decisive = 0

        for r in results:
            if r.winner is None:
                continue
            decisive += 1
            for v in r.variants:
                if v.variant_id == r.winner:
                    style_wins[v.style] = style_wins.get(v.style, 0) + 1

        # 토픽별 추천
        recommendations = []
        if style_wins:
            top_style = max(style_wins, key=style_wins.get)  # type: ignore[arg-type]
            recommendations.append({
                "winning_style": top_style,
                "wins": style_wins[top_style],
                "confidence": "high" if style_wins[top_style] >= 3 else "medium",
            })

        return {
            "total_tests": len(results),
            "decisive_tests": decisive,
            "style_wins": style_wins,
            "recommended_updates": recommendations,
        }

    @staticmethod
    def _build_prompt(title: str, style: str, mood: str, colors: str) -> str:
        """이미지 프롬프트 조합."""
        title_part = f", inspired by: {title[:60]}" if title else ""
        return (
            f"A {style} illustration, {mood} mood, "
            f"color palette: {colors}, "
            f"depicting a scene related to Korean workplace life"
            f"{title_part}. "
            f"No text, no watermarks, high quality, 16:9 aspect ratio."
        )
