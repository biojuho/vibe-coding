"""
ShortsFactory — 5채널 통합 숏츠 제작 파이프라인
================================================
채널 이름만 바꾸면 전체 스타일(색상, 폰트, 전환, 훅)이 자동 전환됩니다.

사용법:
    from ShortsFactory import ShortsFactory

    factory = ShortsFactory(channel="ai_tech")
    factory.create("ai_news", {
        "hook_text": "🚨 역대급 AI 발표",
        "news_title": "GPT-5 출시 임박",
        "points": [
            {"text": "성능 3배 향상", "keywords": ["3배"]},
        ],
    })
    factory.render("output.mp4")
"""

from ShortsFactory.pipeline import ShortsFactory

__all__ = ["ShortsFactory"]
__version__ = "1.0.0"
