"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)


def _round_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _contains_any(text: str, keywords: list[str] | tuple[str, ...]) -> bool:
    lowered = (text or "").lower()
    return any(str(keyword).lower() in lowered for keyword in keywords if keyword)


def _korean_ratio(text: str) -> float:
    if not text:
        return 0.0
    korean_chars = sum(1 for c in text if "\uac00" <= c <= "\ud7a3")
    visible_chars = sum(1 for c in text if not c.isspace())
    return korean_chars / visible_chars if visible_chars > 0 else 0.0


def _extract_first_sentence(text: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+|\n+", text or "") if s.strip()]
    return sentences[0] if sentences else (text or "").strip()


def _extract_empathy_anchor(title: str, content: str) -> str:
    text = f"{title}\n{content}".strip()
    quote_match = re.search(r"[\"'“”‘’]([^\"'“”‘’]{4,80})[\"'“”‘’]", text)
    if quote_match:
        return quote_match.group(1).strip()

    number_match = re.search(r"\d[\d,./]*\s*(만원|천|백|억|배|명|개|년|개월|시간|프로|%|원)?", text)
    if number_match:
        start = max(0, number_match.start() - 18)
        end = min(len(text), number_match.end() + 18)
        return text[start:end].strip(" \n-:,")

    first_sentence = _extract_first_sentence(content or title)
    if first_sentence:
        return first_sentence[:80]

    return title[:80]


def _build_spinoff_angle(topic_cluster: str, title: str, content: str, rule: dict[str, Any]) -> str:
    text = f"{title}\n{content}".strip()
    detected: list[str] = []
    for pattern in rule.get("spinoff_patterns", []) or []:
        if _contains_any(text, [pattern]):
            detected.append(pattern)

    if not detected:
        if re.search(r"\d", text):
            detected.append("숫자 체감 비교")
        if re.search(r"(세전|세후|실수령|연봉|월급|성과급|인센티브)", text):
            detected.append("체감 차이")
        if re.search(r"(회사|팀|업계|직군|상사|대표|면접)", text):
            detected.append("회사별 현실 비교")
        if re.search(r"(댓글|반응|공감|싸움|논쟁)", text):
            detected.append("댓글 반응")

    if not detected:
        detected = list((rule.get("spinoff_patterns", []) or [])[:2])

    return ", ".join(dict.fromkeys(detected[:3]))


def _build_selection_summary(
    topic_cluster: str,
    audience_need: str,
    emotion_lane: str,
    empathy_anchor: str,
    spinoff_angle: str,
) -> str:
    topic_text = topic_cluster if topic_cluster != "기타" else "직장인 공감"
    summary = f"{topic_text} 이슈로 {audience_need}를 건드리는 글"
    if empathy_anchor:
        summary += f". '{empathy_anchor[:30]}' 같은 장면을 살리면 반응이 난다"
    if emotion_lane:
        summary += f". 톤은 {emotion_lane}"
    if spinoff_angle:
        summary += f". 파생각은 {spinoff_angle}"
    return summary


def _humanize_performance_rationale(labels: list[str]) -> list[str]:
    mapping = {
        "topic_match": "비슷한 주제가 실제로 반응했던 이력",
        "hook_match": "비슷한 훅 구조가 성과를 낸 이력",
        "emotion_match": "비슷한 감정선이 먹힌 이력",
        "draft_style_match": "비슷한 초안 스타일이 먹힌 이력",
        "weak_match": "유사 성과 사례가 약함",
        "ml_model": "성과 예측 모델 점수 반영",
        "no_historical_examples": "성과 데이터가 아직 부족함",
        "no_weighted_examples": "가중 비교할 성과 사례가 아직 부족함",
        "llm_viral_boost": "바이럴 가능성 보정 반영",
    }
    humanized: list[str] = []
    for label in labels:
        if label.startswith("trained_on="):
            humanized.append(f"학습 표본: {label.split('=', 1)[1]}")
            continue
        humanized.append(mapping.get(label, label))
    return list(dict.fromkeys(humanized))


def _match_first(text: str, rules: list[tuple[str, tuple[str, ...]]], default: str) -> str:
    lowered = text.lower()
    for label, keywords in rules:
        if any(keyword.lower() in lowered for keyword in keywords):
            return label
    return default


def _engagement_signal(post_data: dict[str, Any]) -> float:
    likes = float(post_data.get("likes", 0) or 0)
    comments = float(post_data.get("comments", 0) or 0)
    raw = likes + comments * 1.5
    if raw <= 0:
        return 0.0
    return min(20.0, math.log1p(raw) * 4.8)
