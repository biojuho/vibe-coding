"""content_intelligence — 대본 감성 분석 및 메타데이터 추출.

외부 LLM 의존 없이 키워드 기반으로 감성 태그를 빠르게 분류한다.
파이프라인에서 비차단(non-blocking)으로 호출되며,
결과는 JobManifest.sentiment 필드에 저장된다.

Taxonomy:
    - primary_emotion: 주요 감정 (awe, curiosity, fear, hope, humor, ...)
    - intensity: 1~5 (low → extreme)
    - tags: 세부 감성 태그 list
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── 감정 키워드 사전 ────────────────────────────────────────────────────────

_EMOTION_KEYWORDS: dict[str, list[str]] = {
    "awe": [
        "놀라운",
        "경이로운",
        "상상을 초월",
        "믿기 어려운",
        "amazing",
        "incredible",
        "mind-blowing",
        "unbelievable",
        "우주",
        "광활",
        "무한",
    ],
    "curiosity": [
        "왜",
        "어떻게",
        "비밀",
        "진실",
        "사실",
        "why",
        "how",
        "secret",
        "truth",
        "mystery",
        "숨겨진",
        "알려지지 않은",
        "의문",
    ],
    "fear": [
        "위험",
        "공포",
        "두려운",
        "무서운",
        "치명적",
        "danger",
        "fear",
        "terrifying",
        "deadly",
        "horror",
        "소름",
        "충격",
        "경고",
    ],
    "hope": [
        "희망",
        "가능성",
        "미래",
        "발전",
        "치료",
        "hope",
        "possible",
        "future",
        "cure",
        "breakthrough",
        "극복",
        "성공",
        "기적",
    ],
    "humor": [
        "재미있는",
        "웃긴",
        "황당한",
        "어이없는",
        "funny",
        "hilarious",
        "absurd",
        "ridiculous",
        "반전",
        "장난",
        "코믹",
    ],
    "nostalgia": [
        "추억",
        "그리운",
        "옛날",
        "과거",
        "전설",
        "nostalgic",
        "memory",
        "classic",
        "legendary",
        "역사",
        "고대",
        "전통",
    ],
    "empathy": [
        "마음이",
        "감동",
        "눈물",
        "공감",
        "따뜻한",
        "touching",
        "emotional",
        "heartwarming",
        "empathy",
        "아픔",
        "위로",
        "사연",
    ],
    "motivation": [
        "할 수 있",
        "도전",
        "성장",
        "변화",
        "시작",
        "motivation",
        "challenge",
        "growth",
        "change",
        "끈기",
        "포기하지",
        "열정",
    ],
}

# 강도 부스터: 이 단어가 포함되면 intensity +1
_INTENSITY_BOOSTERS: list[str] = [
    "절대",
    "최고",
    "역대",
    "충격",
    "극한",
    "전무후무",
    "absolutely",
    "extreme",
    "ultimate",
    "shocking",
    "!!",
    "??",
    "역사상",
    "인류",
]


@dataclass
class SentimentResult:
    """대본 감성 분석 결과."""

    primary_emotion: str
    intensity: int  # 1-5
    tags: list[str] = field(default_factory=list)
    emotion_scores: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "primary_emotion": self.primary_emotion,
            "intensity": self.intensity,
            "tags": self.tags,
            "emotion_scores": self.emotion_scores,
        }


def analyze_sentiment(narrations: list[str]) -> SentimentResult:
    """키워드 기반 감성 분석.

    Args:
        narrations: 씬별 나레이션 텍스트 리스트

    Returns:
        SentimentResult — 주요 감정, 강도, 태그
    """
    full_text = " ".join(narrations).lower()

    # 각 감정 카테고리별 매칭 수 집계
    scores: dict[str, int] = {}
    matched_tags: list[str] = []

    for emotion, keywords in _EMOTION_KEYWORDS.items():
        count = 0
        for kw in keywords:
            occurrences = len(re.findall(re.escape(kw.lower()), full_text))
            if occurrences > 0:
                count += occurrences
                if kw not in matched_tags:
                    matched_tags.append(kw)
        scores[emotion] = count

    # 주요 감정 결정
    if not any(scores.values()):
        return SentimentResult(
            primary_emotion="neutral",
            intensity=1,
            tags=[],
            emotion_scores=scores,
        )

    primary = max(scores, key=lambda k: scores[k])

    # 강도 계산 (기본 키워드 매칭 수 기반)
    base_intensity = min(4, max(1, scores[primary] // 2))

    # 부스터 확인
    boost = sum(1 for b in _INTENSITY_BOOSTERS if b.lower() in full_text)
    intensity = min(5, base_intensity + min(boost, 2))

    # 상위 3개 태그만 유지
    top_tags = matched_tags[:6]

    return SentimentResult(
        primary_emotion=primary,
        intensity=intensity,
        tags=top_tags,
        emotion_scores=scores,
    )
