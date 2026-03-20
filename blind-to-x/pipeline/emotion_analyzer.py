"""KOTE 44차원 감정 분석기.

한국어 온라인 텍스트 감정(KOTE) 모델을 사용하여 텍스트의 감정을
44개 차원으로 분석합니다. 기존 키워드 기반 emotion_axis를 보강합니다.

모델: searle-j/kote_for_easygoing_people (KcELECTRA 기반, ~110M params)
라이선스: MIT
비용: $0 (로컬 CPU 추론, ~0.1초/건)

사용법:
    from pipeline.emotion_analyzer import analyze_emotions, get_emotion_profile
    emotions = analyze_emotions("연봉이 너무 적어서 화가 나요")
    profile = get_emotion_profile("분노가 치밀지만 이직할 용기가 없다")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_MODEL_NAME = "searle-j/kote_for_easygoing_people"
_classifier = None
_load_attempted = False

# KOTE 44감정 → 기존 emotion_axis 매핑
_KOTE_TO_AXIS: dict[str, str] = {
    "화남/분노": "분노",
    "짜증": "분노",
    "불평/불만": "분노",
    "슬픔": "허탈",
    "우울": "허탈",
    "외로움": "허탈",
    "허탈": "허탈",
    "안타까움/실망": "현타",
    "걱정/불안": "현타",
    "한심": "현타",
    "기쁨": "공감",
    "감동": "공감",
    "고마움": "공감",
    "편안/안심": "공감",
    "재미있음": "웃김",
    "유머": "웃김",
    "놀람": "경악",
    "충격": "경악",
    "경악": "경악",
    "깨달음": "통찰",
    "존경": "통찰",
}

# 콘텐츠 전략에 유용한 주요 감정 그룹
_EMOTION_GROUPS = {
    "부정_강": ["화남/분노", "짜증", "불평/불만", "환멸"],
    "부정_약": ["안타까움/실망", "걱정/불안", "슬픔", "우울"],
    "긍정_강": ["기쁨", "감동", "고마움", "자신감"],
    "긍정_약": ["편안/안심", "재미있음", "기대감"],
    "각성_고": ["놀람", "충격", "경악", "흥분"],
    "인지": ["깨달음", "존경", "호기심"],
}


@dataclass
class EmotionProfile:
    """감정 분석 결과."""

    top_emotions: list[dict[str, float]] = field(default_factory=list)
    emotion_axis: str = "공감"  # 기존 시스템 호환
    dominant_group: str = ""
    valence: float = 0.0  # -1(부정) ~ +1(긍정)
    arousal: float = 0.0  # 0(차분) ~ 1(강렬)
    confidence: float = 0.0


def _get_classifier():
    """KOTE 분류기 싱글톤. 로드 실패 시 None."""
    global _classifier, _load_attempted
    if _load_attempted:
        return _classifier
    _load_attempted = True
    try:
        from transformers import pipeline as hf_pipeline
        _classifier = hf_pipeline(
            "text-classification",
            model=_MODEL_NAME,
            top_k=10,
            device=-1,  # CPU
        )
        logger.info("KOTE emotion analyzer loaded: %s", _MODEL_NAME)
    except Exception as exc:
        logger.info("KOTE model not available (%s), emotion analysis disabled.", exc)
        _classifier = None
    return _classifier


def analyze_emotions(text: str, top_k: int = 5) -> list[dict[str, float]]:
    """텍스트의 감정을 분석하여 상위 k개 감정과 확률을 반환.

    Returns:
        [{"label": "화남/분노", "score": 0.92}, ...]
    """
    clf = _get_classifier()
    if clf is None or not text or not text.strip():
        return []

    try:
        # KOTE 모델은 긴 텍스트에서 느리므로 앞 512자만 사용
        truncated = text[:512]
        results = clf(truncated)
        if results and isinstance(results[0], list):
            return [{"label": r["label"], "score": round(r["score"], 3)} for r in results[0][:top_k]]
        return []
    except Exception as exc:
        logger.debug("Emotion analysis failed: %s", exc)
        return []


def get_emotion_profile(text: str) -> EmotionProfile:
    """텍스트의 감정 프로필을 구성합니다.

    기존 emotion_axis와 호환되는 라벨 + valence/arousal 차원을 추가로 제공.
    """
    emotions = analyze_emotions(text, top_k=10)
    if not emotions:
        return EmotionProfile()

    # emotion_axis 매핑 (최고 확률 감정 기준)
    axis = "공감"
    for emo in emotions:
        mapped = _KOTE_TO_AXIS.get(emo["label"])
        if mapped:
            axis = mapped
            break

    # 지배적 감정 그룹 판별
    group_scores: dict[str, float] = {}
    for group_name, group_labels in _EMOTION_GROUPS.items():
        score = sum(e["score"] for e in emotions if e["label"] in group_labels)
        group_scores[group_name] = score
    dominant = max(group_scores, key=group_scores.get) if group_scores else ""

    # Valence: 긍정 - 부정
    pos = group_scores.get("긍정_강", 0) + group_scores.get("긍정_약", 0)
    neg = group_scores.get("부정_강", 0) + group_scores.get("부정_약", 0)
    valence = (pos - neg) / max(pos + neg, 0.01)

    # Arousal: 강한 감정 비율
    strong = group_scores.get("부정_강", 0) + group_scores.get("긍정_강", 0) + group_scores.get("각성_고", 0)
    total = sum(group_scores.values()) or 1.0
    arousal = min(1.0, strong / total)

    return EmotionProfile(
        top_emotions=emotions[:5],
        emotion_axis=axis,
        dominant_group=dominant,
        valence=round(valence, 3),
        arousal=round(arousal, 3),
        confidence=emotions[0]["score"] if emotions else 0.0,
    )
