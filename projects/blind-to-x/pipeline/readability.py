"""Korean Readability Scorer — 한국어 텍스트 가독성 평가.

한국어에 맞는 가독성 지표를 계산합니다:
- 평균 문장 길이 (40자 초과 시 감점)
- 수동태 비율 (~됩니다/~됐습니다 과다 시 감점)
- 문장 다양성 (모든 문장이 비슷한 길이면 감점)

사용법:
    result = calculate_readability("직장인 연봉 이야기...")
    print(result["readability_score"])  # 0-100
"""

from __future__ import annotations

import re


def calculate_readability(text: str) -> dict[str, float]:
    """한국어 텍스트의 가독성을 평가합니다.

    Returns:
        {
            "avg_sentence_length": float,  # 평균 문장 길이 (문자)
            "passive_ratio": float,         # 수동태 비율 (0.0-1.0)
            "sentence_count": int,
            "readability_score": float,     # 최종 점수 (0-100)
        }
    """
    if not text or not text.strip():
        return {
            "avg_sentence_length": 0.0,
            "passive_ratio": 0.0,
            "sentence_count": 0,
            "readability_score": 50.0,
        }

    # 문장 분리 (한국어 구두점 + 줄바꿈 기반)
    sentences = [
        s.strip()
        for s in re.split(r"[.!?。\n]+", text)
        if len(s.strip()) >= 5  # 최소 5자 이상만 문장으로 인정
    ]

    if not sentences:
        return {
            "avg_sentence_length": 0.0,
            "passive_ratio": 0.0,
            "sentence_count": 0,
            "readability_score": 50.0,
        }

    sentence_count = len(sentences)
    lengths = [len(s) for s in sentences]
    avg_length = sum(lengths) / sentence_count

    # 수동태 패턴 감지 (한국어 수동태/피동 표현)
    passive_patterns = re.compile(
        r"(됩니다|됐습니다|되었습니다|되어집니다|시켜집니다|받게 됩니다|"
        r"된다고|되었다고|라고 합니다|것으로 보입니다|것으로 알려져)"
    )
    passive_count = sum(1 for s in sentences if passive_patterns.search(s))
    passive_ratio = passive_count / sentence_count

    # ── 점수 계산 (100점 만점) ─────────────────────────────────────
    score = 100.0

    # 1. 평균 문장 길이 감점 (최적: 15~35자)
    if avg_length > 60:
        score -= 30  # 매우 긴 문장
    elif avg_length > 45:
        score -= 20
    elif avg_length > 35:
        score -= 10
    elif avg_length < 8:
        score -= 15  # 너무 짧은 문장 (내용 부족)

    # 2. 수동태 비율 감점 (0.5 이상이면 딱딱함)
    if passive_ratio > 0.6:
        score -= 25
    elif passive_ratio > 0.4:
        score -= 15
    elif passive_ratio > 0.3:
        score -= 8

    # 3. 문장 수가 너무 적으면 감점 (twitter 제외 — 1~2문장은 허용)
    if sentence_count == 1 and len(text) > 200:
        score -= 15  # 긴 텍스트인데 문장이 하나 = 구두점 없음

    score = max(0.0, min(100.0, score))

    return {
        "avg_sentence_length": round(avg_length, 1),
        "passive_ratio": round(passive_ratio, 3),
        "sentence_count": sentence_count,
        "readability_score": round(score, 1),
    }
