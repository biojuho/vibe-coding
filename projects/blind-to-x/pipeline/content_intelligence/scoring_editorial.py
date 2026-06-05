"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


from pipeline.content_intelligence.rules import _get_topic_editorial_rule
from pipeline.content_intelligence.utils import (
    _contains_any,
    _korean_ratio,
    _extract_empathy_anchor,
    _build_spinoff_angle,
    _round_score,
    _build_selection_summary,
    _engagement_signal,
)
from pipeline.content_intelligence.classifiers import (
    classify_topic_cluster,
    classify_emotion_axis,
    classify_audience_fit,
)


_DEFAULT_WORKPLACE_KEYWORDS = (
    "직장",
    "회사",
    "팀",
    "상사",
    "대표",
    "면접",
    "연봉",
    "월급",
    "성과급",
    "출근",
    "퇴근",
    "이직",
)
_COMPARISON_KEYWORDS = ("vs", "비교", "차이", "세전", "세후", "실수령", "회사별", "업계", "팀별")
_DEFAULT_SCENE_KEYWORDS = (
    "회의",
    "출근",
    "퇴근",
    "면담",
    "카톡",
    "전화",
    "메신저",
    "회식",
    "댓글",
    "복도",
    "회의실",
)
_DEFAULT_RAGE_PATTERNS = (
    "실화냐",
    "레전드",
    "충격",
    "미쳤다",
    "소름",
    "분노주의",
    "논란",
)
_DEFAULT_DULL_PATTERNS = (
    "중요한 이유",
    "생각해봅시다",
    "요즘 사람들",
    "현실적으로",
    "결론적으로",
)
_EMPATHY_EMOTION_AXES = {"공감", "웃김", "현타", "분노"}
_SHORTS_EMOTION_AXES = {"공감", "웃김", "현타"}
_WORKPLACE_AUDIENCE_FITS = {"전직장인", "이직준비층"}
_WORKPLACE_TOPIC_CLUSTERS = {"연봉", "이직", "회사문화", "상사", "직장개그", "건강", "IT", "재테크"}


@dataclass(frozen=True)
class _EditorialSignals:
    text: str
    normalized_title: str
    topic_cluster: str
    emotion_axis: str
    audience_fit: str
    topic_rule: dict[str, Any]
    has_number: bool
    has_quote: bool
    has_scene: bool
    has_workplace: bool
    has_comparison: bool
    rage_bait: bool
    dull_angle: bool
    garbled: bool
    korean_ratio: float


@dataclass(frozen=True)
class _EditorialKeywordSets:
    workplace: tuple[str, ...]
    comparison: tuple[str, ...]
    scene: tuple[str, ...]
    rage: tuple[str, ...]
    dull: tuple[str, ...]


def _build_editorial_keyword_sets(topic_rule: dict[str, Any]) -> _EditorialKeywordSets:
    return _EditorialKeywordSets(
        workplace=tuple(topic_rule.get("workplace_keywords", [])) or _DEFAULT_WORKPLACE_KEYWORDS,
        comparison=_COMPARISON_KEYWORDS,
        scene=tuple(topic_rule.get("must_have_anchors", [])) + _DEFAULT_SCENE_KEYWORDS,
        rage=tuple(topic_rule.get("rage_bait_patterns", [])) or _DEFAULT_RAGE_PATTERNS,
        dull=tuple(topic_rule.get("dull_angle_patterns", [])) or _DEFAULT_DULL_PATTERNS,
    )


def _build_editorial_signals(
    title: str,
    source: str,
    content: str,
    topic_cluster: str,
    emotion_axis: str,
    audience_fit: str,
    topic_rule: dict[str, Any],
) -> _EditorialSignals:
    text = f"{title}\n{content}".strip()
    normalized_title = title.strip()
    keywords = _build_editorial_keyword_sets(topic_rule)

    return _EditorialSignals(
        text=text,
        normalized_title=normalized_title,
        topic_cluster=topic_cluster,
        emotion_axis=emotion_axis,
        audience_fit=audience_fit,
        topic_rule=topic_rule,
        has_number=bool(re.search(r"\d", text)),
        has_quote=bool(re.search(r"[\"'“”‘’]|라고|라는데|라는 말", text)),
        has_scene=_contains_any(text, keywords.scene),
        has_workplace=_contains_any(text, keywords.workplace) or str(source).lower() in {"blind", "jobplanet"},
        has_comparison=_contains_any(text, keywords.comparison),
        rage_bait=_contains_any(normalized_title, keywords.rage),
        dull_angle=_contains_any(text, keywords.dull),
        garbled="\ufffd" in text or bool(re.search(r"[ÃÂ�]{2,}", text)),
        korean_ratio=_korean_ratio(text),
    )


def _score_reader_desire(signals: _EditorialSignals) -> float:
    reader_desire = 25.0
    if signals.topic_cluster != "기타":
        reader_desire += 25.0
    if signals.has_workplace:
        reader_desire += 25.0
    if signals.has_comparison or signals.has_number:
        reader_desire += 15.0
    if signals.audience_fit in _WORKPLACE_AUDIENCE_FITS:
        reader_desire += 10.0
    return _round_score(reader_desire)


def _score_empathy_fun(signals: _EditorialSignals) -> float:
    empathy_fun = 20.0
    if signals.emotion_axis in _EMPATHY_EMOTION_AXES:
        empathy_fun += 30.0
    if signals.has_quote or signals.has_scene:
        empathy_fun += 25.0
    if re.search(r"(ㅋㅋ|ㅠㅠ|ㅎㅎ|한숨|현타|웃기|씁쓸)", signals.text):
        empathy_fun += 15.0
    return _round_score(empathy_fun)


def _score_spinoff(signals: _EditorialSignals) -> float:
    spinoff = 15.0
    if signals.has_comparison:
        spinoff += 30.0
    if signals.has_number:
        spinoff += 20.0
    if signals.has_workplace:
        spinoff += 15.0
    if re.search(r"(댓글|반응|후기|체감|실수령|세전|세후|업계)", signals.text):
        spinoff += 20.0
    return _round_score(spinoff)


def _score_specificity(signals: _EditorialSignals, content: str) -> float:
    specificity = 15.0
    if signals.has_number:
        specificity += 30.0
    if signals.has_quote:
        specificity += 25.0
    if signals.has_scene:
        specificity += 20.0
    if len((content or signals.normalized_title).strip()) >= 45:
        specificity += 10.0
    if signals.dull_angle:
        specificity -= 20.0
    return _round_score(specificity)


def _score_workplace_fit(signals: _EditorialSignals) -> float:
    workplace_fit = 10.0
    if signals.has_workplace:
        workplace_fit += 70.0
    elif signals.topic_cluster in _WORKPLACE_TOPIC_CLUSTERS:
        workplace_fit += 45.0
    elif signals.audience_fit != "범용":
        workplace_fit += 20.0
    return _round_score(workplace_fit)


def _score_editorial_dimensions(signals: _EditorialSignals, content: str) -> dict[str, float]:
    return {
        "reader_desire": _score_reader_desire(signals),
        "empathy_fun": _score_empathy_fun(signals),
        "spinoff": _score_spinoff(signals),
        "specificity": _score_specificity(signals, content),
        "workplace_fit": _score_workplace_fit(signals),
    }


def _weighted_editorial_score(dimensions: dict[str, float]) -> float:
    return _round_score(
        dimensions["reader_desire"] * 0.30
        + dimensions["empathy_fun"] * 0.25
        + dimensions["spinoff"] * 0.20
        + dimensions["specificity"] * 0.15
        + dimensions["workplace_fit"] * 0.10
    )


def _is_text_garbled(signals: _EditorialSignals) -> bool:
    return signals.garbled or (len(signals.text) >= 10 and signals.korean_ratio < 0.15)


def _is_too_abstract(signals: _EditorialSignals, dimensions: dict[str, float]) -> bool:
    missing_specific_anchor = not (signals.has_number or signals.has_quote or signals.has_scene)
    return dimensions["specificity"] < 35 or (signals.dull_angle and missing_specific_anchor)


def _hard_reject_checks(signals: _EditorialSignals, dimensions: dict[str, float]) -> tuple[tuple[bool, str], ...]:
    return (
        (_is_text_garbled(signals), "문자 깨짐 또는 비한글 비율 과다"),
        (_is_too_abstract(signals, dimensions), "너무 추상적"),
        (dimensions["spinoff"] < 35, "파생각 부족"),
        (dimensions["workplace_fit"] < 45, "직장인 맥락 약함"),
        (signals.rage_bait and dimensions["empathy_fun"] < 60, "갈등 낚시 과다"),
    )


def _build_hard_reject_reasons(signals: _EditorialSignals, dimensions: dict[str, float]) -> list[str]:
    return [reason for should_reject, reason in _hard_reject_checks(signals, dimensions) if should_reject]


def _build_editorial_reason_labels(dimensions: dict[str, float], score: float) -> list[str]:
    reason_labels: list[str] = []
    if dimensions["reader_desire"] >= 70:
        reason_labels.append("직장인이 바로 눌러볼 만한 주제")
    if dimensions["empathy_fun"] >= 70:
        reason_labels.append("공감하거나 웃을 장면이 분명함")
    if dimensions["spinoff"] >= 65:
        reason_labels.append("댓글과 파생 대화로 이어질 각이 있음")
    if dimensions["specificity"] >= 65:
        reason_labels.append("숫자·대사·상황이 구체적임")
    if dimensions["workplace_fit"] >= 70:
        reason_labels.append("직장인 독자 맥락에 정확히 맞음")

    if not reason_labels and score >= 55:
        reason_labels.append("반응 포인트는 있으나 편집 보강이 필요함")
    return reason_labels


def _text_field(post_data: dict[str, Any], key: str) -> str:
    return str(post_data.get(key, "") or "")


def _editorial_text_or_fallback(editorial_fit: dict[str, Any], key: str, fallback: str) -> str:
    return str(editorial_fit.get(key) or fallback)


def evaluate_candidate_editorial_fit(title: str, source: str = "", content: str = "") -> dict[str, Any]:
    # None/비문자열 입력 방어 — 외부 스크래퍼 데이터에서 None이 들어올 수 있음
    title = str(title or "")
    content = str(content or "")
    source = str(source or "")
    topic_cluster = classify_topic_cluster(title, content)
    emotion_axis = classify_emotion_axis(title, content)
    audience_fit = classify_audience_fit(title, content)
    topic_rule = _get_topic_editorial_rule(topic_cluster)
    signals = _build_editorial_signals(
        title=title,
        source=source,
        content=content,
        topic_cluster=topic_cluster,
        emotion_axis=emotion_axis,
        audience_fit=audience_fit,
        topic_rule=topic_rule,
    )
    dimensions = _score_editorial_dimensions(signals, content)
    score = _weighted_editorial_score(dimensions)
    hard_reject_reasons = _build_hard_reject_reasons(signals, dimensions)
    reason_labels = _build_editorial_reason_labels(dimensions, score)

    return {
        "topic_cluster": topic_cluster,
        "emotion_axis": emotion_axis,
        "audience_fit": audience_fit,
        "score": score,
        "dimensions": dimensions,
        "hard_reject": bool(hard_reject_reasons),
        "hard_reject_reasons": hard_reject_reasons,
        "reason_labels": reason_labels,
        "empathy_anchor": _extract_empathy_anchor(title, content),
        "spinoff_angle": _build_spinoff_angle(topic_cluster, title, content, topic_rule),
        "audience_need": str(topic_rule.get("reader_desire", "직장인이 자기 얘기로 받아들일 만한 현실감")),
        "emotion_lane": str(topic_rule.get("emotion_lane", "공감과 웃음이 함께 남는 톤")),
    }


def calculate_publishability_score(
    post_data: dict[str, Any], topic_cluster: str, hook_type: str, emotion_axis: str
) -> tuple[float, list[str], dict[str, Any]]:
    title = _text_field(post_data, "title")
    content = _text_field(post_data, "content")
    editorial_fit = evaluate_candidate_editorial_fit(
        title=title,
        source=_text_field(post_data, "source"),
        content=content,
    )
    topic_rule = _get_topic_editorial_rule(topic_cluster)

    audience_need = _editorial_text_or_fallback(
        editorial_fit,
        "audience_need",
        str(topic_rule.get("reader_desire", "직장인이 자기 얘기로 느낄 만한 현실감")),
    )
    emotion_lane = _editorial_text_or_fallback(
        editorial_fit,
        "emotion_lane",
        str(topic_rule.get("emotion_lane", "공감과 웃음이 함께 남는 톤")),
    )
    empathy_anchor = _editorial_text_or_fallback(
        editorial_fit,
        "empathy_anchor",
        _extract_empathy_anchor(title, content),
    )
    spinoff_angle = _editorial_text_or_fallback(
        editorial_fit,
        "spinoff_angle",
        _build_spinoff_angle(topic_cluster, title, content, topic_rule),
    )

    reason_labels = _build_publishability_reason_labels(editorial_fit, hook_type, emotion_axis)

    publishability_score = float(editorial_fit["score"])
    engagement = _engagement_signal(post_data)
    if engagement > 0:
        publishability_score = _round_score(publishability_score + min(8.0, engagement * 0.25))
        reason_labels.append("초기 반응 지표도 나쁘지 않음")

    rationale = list(dict.fromkeys(reason_labels))
    brief = _build_publishability_brief(
        topic_cluster=topic_cluster,
        audience_need=audience_need,
        emotion_lane=emotion_lane,
        empathy_anchor=empathy_anchor,
        spinoff_angle=spinoff_angle,
        editorial_fit=editorial_fit,
        rationale=rationale,
    )
    return publishability_score, rationale, brief


def _build_publishability_reason_labels(editorial_fit: dict[str, Any], hook_type: str, emotion_axis: str) -> list[str]:
    reason_labels = list(editorial_fit.get("reason_labels") or [])
    if not reason_labels and editorial_fit.get("hard_reject_reasons"):
        reason_labels = [f"보강 필요: {reason}" for reason in editorial_fit["hard_reject_reasons"]]

    if hook_type == "정보형":
        reason_labels.append("정보 포인트를 공감형 문장으로 번역하기 좋음")
    elif hook_type in {"공감형", "논쟁형"}:
        reason_labels.append("스크롤을 멈추게 할 훅이 분명함")
    if emotion_axis in _SHORTS_EMOTION_AXES:
        reason_labels.append("같이 웃거나 같이 한숨 쉬게 할 감정선이 있음")
    return reason_labels


def _build_publishability_brief(
    *,
    topic_cluster: str,
    audience_need: str,
    emotion_lane: str,
    empathy_anchor: str,
    spinoff_angle: str,
    editorial_fit: dict[str, Any],
    rationale: list[str],
) -> dict[str, Any]:
    selection_summary = _build_selection_summary(
        topic_cluster=topic_cluster,
        audience_need=audience_need,
        emotion_lane=emotion_lane,
        empathy_anchor=empathy_anchor,
        spinoff_angle=spinoff_angle,
    )
    return {
        "selection_summary": selection_summary,
        "selection_reason_labels": rationale,
        "audience_need": audience_need,
        "emotion_lane": emotion_lane,
        "empathy_anchor": empathy_anchor,
        "spinoff_angle": spinoff_angle,
        "editorial_dimensions": editorial_fit.get("dimensions", {}),
        "hard_reject_reasons": editorial_fit.get("hard_reject_reasons", []),
    }
