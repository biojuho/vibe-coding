"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

logger = logging.getLogger(__name__)


from pipeline.content_intelligence.rules import _get_topic_editorial_rule
from pipeline.content_intelligence.utils import (
    _contains_any, _korean_ratio, _extract_empathy_anchor, _build_spinoff_angle,
    _round_score, _build_selection_summary, _engagement_signal
)
from pipeline.content_intelligence.classifiers import (
    classify_topic_cluster, classify_emotion_axis, classify_audience_fit
)

def evaluate_candidate_editorial_fit(title: str, source: str = "", content: str = "") -> dict[str, Any]:
    # None/비문자열 입력 방어 — 외부 스크래퍼 데이터에서 None이 들어올 수 있음
    title = str(title or "")
    content = str(content or "")
    source = str(source or "")
    text = f"{title}\n{content}".strip()
    normalized_title = title.strip()
    topic_cluster = classify_topic_cluster(title, content)
    emotion_axis = classify_emotion_axis(title, content)
    audience_fit = classify_audience_fit(title, content)
    topic_rule = _get_topic_editorial_rule(topic_cluster)

    workplace_keywords = tuple(topic_rule.get("workplace_keywords", [])) or (
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
    comparison_keywords = ("vs", "비교", "차이", "세전", "세후", "실수령", "회사별", "업계", "팀별")
    scene_keywords = tuple(topic_rule.get("must_have_anchors", [])) + (
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
    rage_patterns = tuple(topic_rule.get("rage_bait_patterns", [])) or (
        "실화냐",
        "레전드",
        "충격",
        "미쳤다",
        "소름",
        "분노주의",
        "논란",
    )
    dull_patterns = tuple(topic_rule.get("dull_angle_patterns", [])) or (
        "중요한 이유",
        "생각해봅시다",
        "요즘 사람들",
        "현실적으로",
        "결론적으로",
    )

    has_number = bool(re.search(r"\d", text))
    has_quote = bool(re.search(r"[\"'“”‘’]|라고|라는데|라는 말", text))
    has_scene = _contains_any(text, scene_keywords)
    has_workplace = _contains_any(text, workplace_keywords) or str(source).lower() in {"blind", "jobplanet"}
    has_comparison = _contains_any(text, comparison_keywords)
    rage_bait = _contains_any(normalized_title, rage_patterns)
    dull_angle = _contains_any(text, dull_patterns)
    garbled = "\ufffd" in text or bool(re.search(r"[ÃÂ�]{2,}", text))
    korean_ratio = _korean_ratio(text)

    reader_desire = 25.0
    if topic_cluster != "기타":
        reader_desire += 25.0
    if has_workplace:
        reader_desire += 25.0
    if has_comparison or has_number:
        reader_desire += 15.0
    if audience_fit in {"전직장인", "이직준비층"}:
        reader_desire += 10.0

    empathy_fun = 20.0
    if emotion_axis in {"공감", "웃김", "현타", "분노"}:
        empathy_fun += 30.0
    if has_quote or has_scene:
        empathy_fun += 25.0
    if re.search(r"(ㅋㅋ|ㅠㅠ|ㅎㅎ|한숨|현타|웃기|씁쓸)", text):
        empathy_fun += 15.0

    spinoff = 15.0
    if has_comparison:
        spinoff += 30.0
    if has_number:
        spinoff += 20.0
    if has_workplace:
        spinoff += 15.0
    if re.search(r"(댓글|반응|후기|체감|실수령|세전|세후|업계)", text):
        spinoff += 20.0

    specificity = 15.0
    if has_number:
        specificity += 30.0
    if has_quote:
        specificity += 25.0
    if has_scene:
        specificity += 20.0
    if len((content or normalized_title).strip()) >= 45:
        specificity += 10.0
    if dull_angle:
        specificity -= 20.0

    workplace_fit = 10.0
    if has_workplace:
        workplace_fit += 70.0
    elif topic_cluster in {"연봉", "이직", "회사문화", "상사", "직장개그", "건강", "IT", "재테크"}:
        workplace_fit += 45.0
    elif audience_fit != "범용":
        workplace_fit += 20.0

    dimensions = {
        "reader_desire": _round_score(reader_desire),
        "empathy_fun": _round_score(empathy_fun),
        "spinoff": _round_score(spinoff),
        "specificity": _round_score(specificity),
        "workplace_fit": _round_score(workplace_fit),
    }
    score = _round_score(
        dimensions["reader_desire"] * 0.30
        + dimensions["empathy_fun"] * 0.25
        + dimensions["spinoff"] * 0.20
        + dimensions["specificity"] * 0.15
        + dimensions["workplace_fit"] * 0.10
    )

    hard_reject_reasons: list[str] = []
    if garbled or (len(text) >= 10 and korean_ratio < 0.15):
        hard_reject_reasons.append("문자 깨짐 또는 비한글 비율 과다")
    if dimensions["specificity"] < 35 or (dull_angle and not (has_number or has_quote or has_scene)):
        hard_reject_reasons.append("너무 추상적")
    if dimensions["spinoff"] < 35:
        hard_reject_reasons.append("파생각 부족")
    if dimensions["workplace_fit"] < 45:
        hard_reject_reasons.append("직장인 맥락 약함")
    if rage_bait and dimensions["empathy_fun"] < 60:
        hard_reject_reasons.append("갈등 낚시 과다")

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
    title = str(post_data.get("title", "") or "")
    content = str(post_data.get("content", "") or "")
    editorial_fit = evaluate_candidate_editorial_fit(
        title=title,
        source=str(post_data.get("source", "") or ""),
        content=content,
    )
    topic_rule = _get_topic_editorial_rule(topic_cluster)

    audience_need = editorial_fit.get("audience_need") or str(
        topic_rule.get("reader_desire", "직장인이 자기 얘기로 느낄 만한 현실감")
    )
    emotion_lane = editorial_fit.get("emotion_lane") or str(
        topic_rule.get("emotion_lane", "공감과 웃음이 함께 남는 톤")
    )
    empathy_anchor = str(editorial_fit.get("empathy_anchor") or _extract_empathy_anchor(title, content))
    spinoff_angle = str(
        editorial_fit.get("spinoff_angle") or _build_spinoff_angle(topic_cluster, title, content, topic_rule)
    )

    reason_labels = list(editorial_fit.get("reason_labels") or [])
    if not reason_labels and editorial_fit.get("hard_reject_reasons"):
        reason_labels = [f"보강 필요: {reason}" for reason in editorial_fit["hard_reject_reasons"]]

    if hook_type == "정보형":
        reason_labels.append("정보 포인트를 공감형 문장으로 번역하기 좋음")
    elif hook_type in {"공감형", "논쟁형"}:
        reason_labels.append("스크롤을 멈추게 할 훅이 분명함")
    if emotion_axis in {"공감", "웃김", "현타"}:
        reason_labels.append("같이 웃거나 같이 한숨 쉬게 할 감정선이 있음")

    publishability_score = float(editorial_fit["score"])
    engagement = _engagement_signal(post_data)
    if engagement > 0:
        publishability_score = _round_score(publishability_score + min(8.0, engagement * 0.25))
        reason_labels.append("초기 반응 지표도 나쁘지 않음")

    selection_summary = _build_selection_summary(
        topic_cluster=topic_cluster,
        audience_need=audience_need,
        emotion_lane=emotion_lane,
        empathy_anchor=empathy_anchor,
        spinoff_angle=spinoff_angle,
    )

    rationale = list(dict.fromkeys(reason_labels))
    brief = {
        "selection_summary": selection_summary,
        "selection_reason_labels": rationale,
        "audience_need": audience_need,
        "emotion_lane": emotion_lane,
        "empathy_anchor": empathy_anchor,
        "spinoff_angle": spinoff_angle,
        "editorial_dimensions": editorial_fit.get("dimensions", {}),
        "hard_reject_reasons": editorial_fit.get("hard_reject_reasons", []),
    }
    return publishability_score, rationale, brief
