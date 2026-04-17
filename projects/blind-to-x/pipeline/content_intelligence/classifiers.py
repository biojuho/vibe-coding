"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

logger = logging.getLogger(__name__)


from pipeline.content_intelligence.rules import (
    get_topic_rules, get_emotion_rules, get_audience_rules, _load_rules
)
from pipeline.content_intelligence.utils import _match_first

def classify_topic_cluster(title: str, content: str) -> str:
    return _match_first(f"{title} {content}", get_topic_rules(), "기타")


def classify_emotion_axis(title: str, content: str) -> str:
    """감정 축 분류 — KOTE 44차원 모델 우선, 키워드 폴백."""
    # KOTE 모델 시도 (로드 실패 시 자동 폴백)
    try:
        from pipeline.emotion_analyzer import get_emotion_profile

        profile = get_emotion_profile(f"{title} {content}")
        if profile.confidence >= 0.5:
            logger.debug(
                "KOTE emotion: %s (confidence=%.2f, valence=%.2f)",
                profile.emotion_axis,
                profile.confidence,
                profile.valence,
            )
            return profile.emotion_axis
    except Exception:
        pass
    # 키워드 기반 폴백
    return _match_first(f"{title} {content}", get_emotion_rules(), "공감")


def classify_audience_fit(title: str, content: str) -> str:
    return _match_first(f"{title} {content}", get_audience_rules(), "범용")


def classify_hook_type(title: str, content: str, emotion_axis: str) -> str:
    text = f"{title} {content}".lower()
    hook_rules = _load_rules().get("hook_rules", {})

    논쟁형_kw = hook_rules.get("논쟁형", {}).get("keywords", ["왜", "vs", "맞아?", "어떰", "어떻게 생각", "논란", "?"])
    정보형_kw = hook_rules.get("정보형", {}).get("keywords", ["정리", "팁", "방법", "요약", "가이드", "체크리스트"])
    짤형_kw = hook_rules.get("짤형", {}).get("keywords", ["짤", "웃김", "현웃", "개웃", "밈"])
    분석형_kw = hook_rules.get("분석형", {}).get(
        "keywords", ["분석", "트렌드", "비교", "종합", "모아봤", "정리해봤", "동시에", "커뮤니티"]
    )
    통찰형_kw = hook_rules.get("통찰형", {}).get(
        "keywords", ["배운", "깨달", "인사이트", "알게 된", "정리하면", "느낀 점", "교훈", "결론"]
    )
    한줄팩폭형_kw = hook_rules.get("한줄팩폭형", {}).get(
        "keywords", ["ㅋㅋ", "레전드", "개웃", "이건 진짜", "실화냐", "미쳤", "헐"]
    )

    if any(token in text for token in 분석형_kw):
        return "분석형"
    if any(token in text for token in 통찰형_kw):
        return "통찰형"
    if any(token in text for token in 논쟁형_kw):
        return "논쟁형"
    if any(token in text for token in 정보형_kw):
        return "정보형"
    if any(token in text for token in 짤형_kw):
        return "짤형"
    if any(token in text for token in 한줄팩폭형_kw):
        return "한줄팩폭형"
    if emotion_axis in {"분노", "허탈", "현타"} and len(content.strip()) < 180:
        return "한줄팩폭형"
    return "공감형"


def recommend_draft_type(hook_type: str, emotion_axis: str) -> str:
    if hook_type == "분석형":
        return "분석형"
    if hook_type == "정보형":
        return "정보전달형"
    if hook_type == "논쟁형" or emotion_axis in {"분노", "경악"}:
        return "논쟁형"
    if hook_type == "한줄팩폭형":
        return "공감형" if emotion_axis in {"공감", "허탈", "현타"} else "논쟁형"
    return "공감형"
