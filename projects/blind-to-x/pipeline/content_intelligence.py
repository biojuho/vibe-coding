"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

from pipeline.rules_loader import load_rules

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 분류 규칙 YAML 로더 (P2-A)
# ---------------------------------------------------------------------------
_loaded_rules: dict | None = None


def _load_rules() -> dict:
    """Load merged rule sections with in-module caching."""
    global _loaded_rules
    if _loaded_rules is not None:
        return _loaded_rules
    _loaded_rules = load_rules()
    return _loaded_rules


def _yaml_rules_to_tuples(key: str, fallback: list[tuple]) -> list[tuple[str, tuple[str, ...]]]:
    """YAML rules list → (label, keywords_tuple) 리스트 변환. 실패 시 fallback 반환."""
    rules = _load_rules().get(key, [])
    if not rules:
        return fallback
    result = []
    for entry in rules:
        label = entry.get("label", "")
        keywords = tuple(entry.get("keywords", []))
        if label and keywords:
            result.append((label, keywords))
    return result or fallback


@dataclass(frozen=True)
class ContentProfile:
    topic_cluster: str
    hook_type: str
    emotion_axis: str
    audience_fit: str
    recommended_draft_type: str
    scrape_quality_score: float
    publishability_score: float
    performance_score: float
    final_rank_score: float
    rationale: list[str]
    selection_summary: str = ""
    selection_reason_labels: list[str] = field(default_factory=list)
    audience_need: str = ""
    emotion_lane: str = ""
    empathy_anchor: str = ""
    spinoff_angle: str = ""
    # Phase 4-B: 6D quality scorecard (optional — zero when not computed)
    freshness_score: float = 0.0  # 15% — 게시글 신선도 (시간 기반)
    social_signal_score: float = 0.0  # 25% — 좋아요·댓글 소셜 신호
    hook_strength_score: float = 0.0  # 20% — 제목·훅 강도
    trend_relevance_score: float = 0.0  # 15% — 토픽 클러스터 트렌드 적합도
    audience_targeting_score: float = 0.0  # 15% — 독자 타게팅 정확도
    viral_potential_score: float = 0.0  # 10% — 감정 축 바이럴 잠재력
    rank_6d: float = 0.0  # 가중합 최종 점수 (0-100)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scrape_quality_score"] = round(self.scrape_quality_score, 2)
        payload["publishability_score"] = round(self.publishability_score, 2)
        payload["performance_score"] = round(self.performance_score, 2)
        payload["final_rank_score"] = round(self.final_rank_score, 2)
        payload["rank_6d"] = round(self.rank_6d, 2)
        return payload


# 코드 내장 fallback 규칙 (classification_rules.yaml 없을 때 사용)
_TOPIC_RULES_FALLBACK: list[tuple[str, tuple[str, ...]]] = [
    ("연봉", ("연봉", "월급", "성과급", "보너스", "급여", "임금", "인상")),
    ("이직", ("이직", "퇴사", "취업", "면접", "채용", "오퍼", "커리어")),
    ("회사문화", ("회사", "조직", "문화", "팀장", "상사", "팀원", "평가", "인사")),
    ("상사", ("상사", "부장", "팀장", "임원", "매니저", "관리자")),
    ("복지", ("복지", "재택", "휴가", "워라밸", "식대", "지원금", "사내")),
    ("연애", ("연애", "소개팅", "썸", "남친", "여친", "플러팅")),
    ("결혼", ("결혼", "신혼", "배우자", "남편", "아내", "이혼")),
    ("가족", ("가족", "부모", "엄마", "아빠", "자녀", "육아")),
    ("재테크", ("주식", "코인", "재테크", "부동산", "투자", "대출")),
    ("직장개그", ("웃김", "개웃", "현웃", "짤", "썰", "실화", "밈")),
]
_EMOTION_RULES_FALLBACK: list[tuple[str, tuple[str, ...]]] = [
    ("분노", ("빡", "열받", "화나", "분노", "짜증", "억까")),
    ("허탈", ("허탈", "허무", "현타", "공허", "멘붕")),
    ("공감", ("공감", "이해", "맞말", "다들", "나만", "저만")),
    ("웃김", ("웃김", "개웃", "현웃", "웃겨", "유머", "짤")),
    ("경악", ("충격", "미쳤", "실화", "레전드", "소름")),
    ("현타", ("현타", "퇴사 마렵", "현실", "지친", "번아웃")),
    ("통찰", ("인사이트", "배운", "느낀", "교훈", "정리")),
]
_AUDIENCE_RULES_FALLBACK: list[tuple[str, tuple[str, ...]]] = [
    ("초년생", ("신입", "주니어", "첫회사", "사회초년생")),
    ("이직준비층", ("이직", "오퍼", "면접", "취준", "구직")),
    ("관리자층", ("팀장", "리더", "매니저", "임원", "관리자")),
    ("전직장인", ("회사", "직장", "출근", "퇴근", "상사", "팀원")),
]


def get_topic_rules() -> list[tuple[str, tuple[str, ...]]]:
    return _yaml_rules_to_tuples("topic_rules", _TOPIC_RULES_FALLBACK)


def get_emotion_rules() -> list[tuple[str, tuple[str, ...]]]:
    return _yaml_rules_to_tuples("emotion_rules", _EMOTION_RULES_FALLBACK)


def get_audience_rules() -> list[tuple[str, tuple[str, ...]]]:
    return _yaml_rules_to_tuples("audience_rules", _AUDIENCE_RULES_FALLBACK)


# 모듈 수준 접근용 alias (기존 코드 호환)
TOPIC_RULES = property(get_topic_rules)
EMOTION_RULES = property(get_emotion_rules)
AUDIENCE_RULES = property(get_audience_rules)


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


def _load_x_editorial_rules() -> dict[str, Any]:
    return _load_rules().get("x_editorial_rules", {}) or {}


def _get_topic_editorial_rule(topic_cluster: str) -> dict[str, Any]:
    rules = _load_x_editorial_rules()
    defaults = dict(rules.get("defaults", {}) or {})
    topic_rule = dict((rules.get("topics", {}) or {}).get(topic_cluster, {}) or {})
    return {**defaults, **topic_rule}


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


def evaluate_candidate_editorial_fit(title: str, source: str = "", content: str = "") -> dict[str, Any]:
    text = f"{title}\n{content}".strip()
    normalized_title = (title or "").strip()
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


def get_time_context() -> dict[str, str]:
    """현재 KST 시간대에 맞는 프롬프트 접두어·톤 힌트 반환 (Phase 4-C).

    classification_rules.yaml의 prompt_variants.time_context 섹션을 참조.
    YAML 없거나 실패 시 하드코딩 fallback 사용.

    Returns:
        {"slot": "오전"|"점심"|"오후"|"저녁"|"심야",
         "prefix": "...", "tone_hint": "..."}
    """
    import datetime as _dt

    try:
        kst_hour = (_dt.datetime.now(_dt.timezone.utc).hour + 9) % 24
    except Exception:
        import time as _time

        kst_hour = (_time.gmtime().tm_hour + 9) % 24

    if 6 <= kst_hour < 12:
        slot = "오전"
    elif 12 <= kst_hour < 14:
        slot = "점심"
    elif 14 <= kst_hour < 18:
        slot = "오후"
    elif 18 <= kst_hour < 22:
        slot = "저녁"
    else:
        slot = "심야"

    _FALLBACK = {
        "오전": {"prefix": "출근 준비 중인 직장인들이 딱 공감할", "tone_hint": "핵심만, 에너지 넘치게"},
        "점심": {"prefix": "점심시간 직장인들이 폰으로 읽을", "tone_hint": "가볍고 재미있게"},
        "오후": {"prefix": "오후 업무 중 숨돌리는 직장인들의", "tone_hint": "공감 유발 강하게"},
        "저녁": {"prefix": "퇴근 후 소파에서 직장인들이 공감하는", "tone_hint": "솔직하고 따뜻하게"},
        "심야": {"prefix": "잠 못 드는 직장인들의 솔직한", "tone_hint": "감성적이고 진솔하게"},
    }

    rules = _load_rules().get("prompt_variants", {}).get("time_context", {})
    ctx = rules.get(slot, _FALLBACK[slot])
    return {
        "slot": slot,
        "prefix": ctx.get("prefix", _FALLBACK[slot]["prefix"]),
        "tone_hint": ctx.get("tone_hint", _FALLBACK[slot]["tone_hint"]),
    }


def get_topic_hook(topic_cluster: str) -> dict[str, str]:
    """토픽 클러스터별 훅 오프너·CTA 반환 (Phase 4-C).

    Returns:
        {"opener": "...", "cta": "..."}
    """
    rules = _load_rules().get("prompt_variants", {}).get("topic_hooks", {})
    entry = rules.get(topic_cluster, {})
    return {
        "opener": entry.get("opener", ""),
        "cta": entry.get("cta", "댓글로 의견 나눠주세요 👇"),
    }


def get_source_hint(source: str) -> dict:
    """소스별 분류 힌트 반환 (P3).

    Args:
        source: 소스 이름 (blind, ppomppu, fmkorea, jobplanet).

    Returns:
        {"display_name", "description", "topic_bias", "emotion_bias", "quality_boost", ...}
    """
    hints = _load_rules().get("source_hints", {})
    default = {"display_name": source, "description": "", "topic_bias": [], "emotion_bias": [], "quality_boost": 1.0}
    return hints.get(source, default)


def get_season_boost(topic_cluster: str, month: int | None = None) -> float:
    """시즌 트렌드 가중치 반환 (P0-A2).

    classification_rules.yaml의 season_weights 섹션 참조.
    해당 월에 특정 토픽의 부스트 점수(0~15)를 반환합니다.
    YAML 없거나 해당 토픽이 없으면 0.0 반환.

    Args:
        topic_cluster: 토픽 클러스터 이름.
        month: 월 (1-12). None이면 현재 월 사용.

    Returns:
        0.0 ~ 15.0 사이의 부스트 점수.
    """
    if month is None:
        import datetime as _dt

        try:
            month = _dt.datetime.now(_dt.timezone.utc).month
        except Exception:
            import time as _time

            month = _time.gmtime().tm_mon

    rules = _load_rules()
    season_weights = rules.get("season_weights", {})
    month_weights = season_weights.get(month, season_weights.get(str(month), {}))
    boost = float(month_weights.get(topic_cluster, 0))
    return min(15.0, max(0.0, boost))


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


def calculate_performance_score(
    topic_cluster: str,
    hook_type: str,
    emotion_axis: str,
    recommended_draft_type: str,
    historical_examples: list[dict[str, Any]] | None = None,
) -> tuple[float, list[str]]:
    if not historical_examples:
        return 45.0, ["no_historical_examples"]

    total_weight = 0.0
    score = 35.0
    rationale: list[str] = []

    for example in historical_examples:
        weight = 1.0 + min(float(example.get("views", 0) or 0) / 10000.0, 2.0)
        total_weight += weight

        if example.get("topic_cluster") == topic_cluster:
            score += 18 * weight
            rationale.append("topic_match")
        if example.get("hook_type") == hook_type:
            score += 15 * weight
            rationale.append("hook_match")
        if example.get("emotion_axis") == emotion_axis:
            score += 12 * weight
            rationale.append("emotion_match")
        if example.get("draft_style") == recommended_draft_type:
            score += 10 * weight
            rationale.append("draft_style_match")

    if total_weight <= 0:
        return 50.0, ["no_weighted_examples"]

    normalized = score / total_weight
    return _round_score(normalized), sorted(set(rationale)) or ["weak_match"]


def calculate_6d_score(
    post_data: dict[str, Any],
    topic_cluster: str,
    hook_type: str,
    emotion_axis: str,
    audience_fit: str,
    source: str = "",
    trend_boost: float = 0.0,
) -> tuple[float, dict[str, float]]:
    """6차원 콘텐츠 품질 스코어카드 (Phase 4-B).

    Returns (rank_6d 0-100, dimensions dict).

    Dimensions & weights:
        freshness_score      15% — 게시글 신선도 (scraped_at 기반, 없으면 50점)
        social_signal_score  25% — 좋아요·댓글 소셜 신호
        hook_strength_score  20% — 제목·훅 타입 강도
        trend_relevance_score 15% — 토픽 클러스터 트렌드 적합도
        audience_targeting_score 15% — 독자 타게팅 정확도
        viral_potential_score  10% — 감정 축 바이럴 잠재력
    """
    import time

    title = str(post_data.get("title", "") or "")
    content = str(post_data.get("content", "") or "")
    likes = float(post_data.get("likes", 0) or 0)
    comments = float(post_data.get("comments", 0) or 0)

    # ── Freshness (15%) ─────────────────────────────────────────────
    freshness = 50.0  # default when no timestamp
    scraped_at = post_data.get("scraped_at") or post_data.get("created_at")
    if scraped_at:
        try:
            import datetime as _dt

            if isinstance(scraped_at, (int, float)):
                age_hours = (time.time() - scraped_at) / 3600
            else:
                ts = _dt.datetime.fromisoformat(str(scraped_at))
                age_hours = (_dt.datetime.now() - ts.replace(tzinfo=None)).total_seconds() / 3600
            # 0h→100, 6h→80, 24h→50, 72h→20, 168h+→5
            freshness = max(5.0, 100.0 * math.exp(-age_hours / 24.0))
        except Exception:
            pass

    # ── Social Signal (25%) ─────────────────────────────────────────
    raw_social = likes + comments * 2.0
    social = min(100.0, math.log1p(raw_social) / math.log1p(500) * 100) if raw_social > 0 else 5.0

    # ── Hook Strength (20%) ─────────────────────────────────────────
    title_len = len(title.strip())
    hook_base = {
        "논쟁형": 90.0,
        "공감형": 75.0,
        "정보형": 70.0,
        "한줄팩폭형": 85.0,
        "짤형": 65.0,
        "분석형": 88.0,
        "통찰형": 82.0,
    }.get(hook_type, 60.0)
    # title 길이 보너스 (8-35자 최적)
    if 8 <= title_len <= 35:
        hook_base = min(100.0, hook_base + 8.0)
    elif title_len < 4:
        hook_base = max(0.0, hook_base - 20.0)

    # ── Trend Relevance (15%) ───────────────────────────────────────
    # 고인기 토픽에 가중치 + 시즌 부스트 (P0-A2)
    _HIGH_TREND = {"연봉", "이직", "회사문화", "상사"}
    _MED_TREND = {"복지", "재테크", "직장개그", "부동산", "IT"}
    if topic_cluster in _HIGH_TREND:
        trend = 85.0
    elif topic_cluster in _MED_TREND:
        trend = 65.0
    elif topic_cluster == "기타":
        trend = 35.0
    else:
        trend = 50.0
    # 시즌 부스트 추가 (최대 15점)
    season_boost = get_season_boost(topic_cluster)
    if season_boost > 0:
        trend = min(100.0, trend + season_boost)
    # 실시간 트렌드 부스트 (trend_monitor.py에서 전달, 최대 30점)
    if trend_boost > 0:
        trend = min(100.0, trend + trend_boost)

    # ── Audience Targeting (15%) ────────────────────────────────────
    audience_scores = {
        "전직장인": 85.0,
        "이직준비층": 80.0,
        "초년생": 70.0,
        "관리자층": 60.0,
        "범용": 50.0,
    }
    audience = audience_scores.get(audience_fit, 50.0)
    # content 길이 보너스 (충분한 컨텍스트 = 타게팅 가능)
    if len(content.strip()) >= 150:
        audience = min(100.0, audience + 5.0)

    # ── Viral Potential (10%) ───────────────────────────────────────
    viral_scores = {
        "분노": 90.0,
        "경악": 85.0,
        "웃김": 80.0,
        "현타": 75.0,
        "허탈": 70.0,
        "공감": 65.0,
        "통찰": 55.0,
    }
    viral = viral_scores.get(emotion_axis, 50.0)

    # ── Weighted sum (보정 가중치 우선 사용) ──────────────────────────
    weights = {
        "freshness": 0.15,
        "social": 0.25,
        "hook": 0.20,
        "trend": 0.15,
        "audience": 0.15,
        "viral": 0.10,
    }
    try:
        from pipeline.cost_db import get_cost_db

        calibrated = get_cost_db().load_calibrated_weights(max_age_days=7)
        if calibrated and all(k in calibrated for k in weights):
            weights = calibrated
    except Exception:
        pass
    rank_6d = _round_score(
        freshness * weights["freshness"]
        + social * weights["social"]
        + hook_base * weights["hook"]
        + trend * weights["trend"]
        + audience * weights["audience"]
        + viral * weights["viral"]
    )

    # ── Source Quality Boost (P3 통합) ───────────────────────────────
    if source:
        source_hint = get_source_hint(source)
        quality_boost = float(source_hint.get("quality_boost", 1.0))
        rank_6d = _round_score(rank_6d * quality_boost)

    dims = {
        "freshness_score": _round_score(freshness),
        "social_signal_score": _round_score(social),
        "hook_strength_score": _round_score(hook_base),
        "trend_relevance_score": _round_score(trend),
        "audience_targeting_score": _round_score(audience),
        "viral_potential_score": _round_score(viral),
    }
    return rank_6d, dims


def estimate_viral_boost_llm(title: str, content: str, topic_cluster: str, emotion_axis: str) -> float:
    """LLM으로 바이럴 잠재력을 추가 추정, 0~15점 반환.

    규칙 기반 스코어링의 보조 신호로 사용됩니다.
    LLM 실패 시 0.0 반환 (graceful degradation).
    비용: Gemini/Groq 무료 tier 사용 시 $0.
    """
    try:
        # 루트 경로에서 LLMClient 접근 (blind-to-x는 루트 venv 사용)
        import importlib.util
        import pathlib

        _root = pathlib.Path(__file__).resolve().parent.parent.parent
        spec = importlib.util.spec_from_file_location("execution.llm_client", _root / "execution" / "llm_client.py")
        if spec is None or spec.loader is None:
            return 0.0
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        client = mod.LLMClient(
            providers=["google", "groq", "deepseek", "zhipuai"],
            track_usage=False,
        )
    except Exception as exc:
        logger.debug("LLM 바이럴 부스트 클라이언트 초기화 실패: %s", exc)
        return 0.0

    _system = (
        "You are a Korean SNS viral potential analyst. "
        "Given a post's title and content, score its viral potential on Korean Twitter/X from 0 to 100. "
        "Focus on: emotional resonance, relatability, controversy potential, shareability. "
        'Respond ONLY with valid JSON: {"score": <integer 0-100>, "reason": "<one sentence in Korean>"}'
    )
    _user = (
        f"Topic cluster: {topic_cluster}\nEmotion: {emotion_axis}\n\nTitle: {title[:200]}\n\nContent: {content[:500]}"
    )

    try:
        result = client.generate_json(
            system_prompt=_system,
            user_prompt=_user,
            temperature=0.3,
        )
        raw = float(result.get("score", 0))
        # 0~100 점수를 0~15 부스트로 변환 (최대 15점 가산)
        boost = round(max(0.0, min(15.0, raw * 0.15)), 2)
        logger.info("LLM 바이럴 부스트: %.1f/100 → +%.2f pts | %s", raw, boost, result.get("reason", ""))
        return boost
    except Exception as exc:
        logger.debug("LLM 바이럴 부스트 실패: %s", exc)
        return 0.0


def build_content_profile(
    post_data: dict[str, Any],
    scrape_quality_score: float,
    historical_examples: list[dict[str, Any]] | None = None,
    ranking_weights: dict[str, float] | None = None,
    llm_viral_boost: bool = False,
    trend_boost: float = 0.0,
) -> ContentProfile:
    title = str(post_data.get("title", "") or "")
    content = str(post_data.get("content", "") or "")

    topic_cluster = classify_topic_cluster(title, content)
    emotion_axis = classify_emotion_axis(title, content)
    audience_fit = classify_audience_fit(title, content)
    hook_type = classify_hook_type(title, content, emotion_axis)
    recommended_draft_type = recommend_draft_type(hook_type, emotion_axis)

    publishability_score, publishability_rationale, editorial_brief = calculate_publishability_score(
        post_data,
        topic_cluster,
        hook_type,
        emotion_axis,
    )

    # LLM 바이럴 부스트: 보더라인 점수(50-70)인 경우에만 호출 → API 비용 절감
    if llm_viral_boost and 50 <= publishability_score <= 70:
        boost = estimate_viral_boost_llm(title, content, topic_cluster, emotion_axis)
        if boost > 0:
            boost = min(10.0, boost)  # 최대 10점으로 캡 (과도한 부스트 방지)
            publishability_score = _round_score(publishability_score + boost)
            publishability_rationale.append("바이럴 가능성 보정 반영")

    # ML 점수 (100건 이상 축적 시 자동 활성화, 미만 시 heuristic 폴백)
    ml_score, ml_meta = 0.0, {}
    try:
        from pipeline.ml_scorer import get_ml_scorer

        _ml = get_ml_scorer()
        if _ml.is_active():
            ml_score, ml_meta = _ml.predict_score(
                topic_cluster=topic_cluster,
                hook_type=hook_type,
                emotion_axis=emotion_axis,
                draft_style=recommended_draft_type,
            )
    except Exception as _ml_exc:
        logger.debug("ML scorer unavailable: %s", _ml_exc)

    if ml_meta.get("method") == "ml":
        # ML 모델이 활성화된 경우 performance_score를 ML 예측으로 대체
        performance_score = ml_score
        performance_rationale = ["ml_model", f"trained_on={ml_meta.get('trained_on', '?')}"]
        logger.debug("Performance score via ML: %.1f (proba=%.4f)", ml_score, ml_meta.get("publish_proba", 0))
    else:
        performance_score, performance_rationale = calculate_performance_score(
            topic_cluster,
            hook_type,
            emotion_axis,
            recommended_draft_type,
            historical_examples=historical_examples,
        )

    weights = ranking_weights or {
        "scrape_quality": 0.35,
        "publishability": 0.40,
        "performance": 0.25,
    }
    final_rank_score = _round_score(
        scrape_quality_score * float(weights.get("scrape_quality", 0.35))
        + publishability_score * float(weights.get("publishability", 0.40))
        + performance_score * float(weights.get("performance", 0.25))
    )

    # Phase 4-B: 6D scorecard
    rank_6d, dims_6d = calculate_6d_score(
        post_data,
        topic_cluster,
        hook_type,
        emotion_axis,
        audience_fit,
        source=str(post_data.get("source", "")),
        trend_boost=trend_boost,
    )

    rationale = list(dict.fromkeys(publishability_rationale + _humanize_performance_rationale(performance_rationale)))
    return ContentProfile(
        topic_cluster=topic_cluster,
        hook_type=hook_type,
        emotion_axis=emotion_axis,
        audience_fit=audience_fit,
        recommended_draft_type=recommended_draft_type,
        scrape_quality_score=_round_score(scrape_quality_score),
        publishability_score=publishability_score,
        performance_score=performance_score,
        final_rank_score=final_rank_score,
        rationale=rationale,
        selection_summary=str(editorial_brief.get("selection_summary", "")),
        selection_reason_labels=list(editorial_brief.get("selection_reason_labels", []) or []),
        audience_need=str(editorial_brief.get("audience_need", "")),
        emotion_lane=str(editorial_brief.get("emotion_lane", "")),
        empathy_anchor=str(editorial_brief.get("empathy_anchor", "")),
        spinoff_angle=str(editorial_brief.get("spinoff_angle", "")),
        freshness_score=dims_6d["freshness_score"],
        social_signal_score=dims_6d["social_signal_score"],
        hook_strength_score=dims_6d["hook_strength_score"],
        trend_relevance_score=dims_6d["trend_relevance_score"],
        audience_targeting_score=dims_6d["audience_targeting_score"],
        viral_potential_score=dims_6d["viral_potential_score"],
        rank_6d=rank_6d,
    )


# ── 6D 가중치 자동 보정 (Phase 3-A) ──────────────────────────────────


def calibrate_weights(days: int = 30, min_rows: int = 30) -> dict[str, float] | None:
    """draft_analytics의 실제 성과 데이터로 6D 가중치를 자동 보정합니다.

    engagement_rate가 있는 포스트들의 각 6D 차원과 engagement의
    상관계수를 계산하여 가중치를 재배분합니다.

    Args:
        days: 분석할 최근 일수.
        min_rows: 최소 필요 데이터 수. 미달 시 None 반환.

    Returns:
        보정된 가중치 dict. 데이터 부족 시 None.
    """
    try:
        from pipeline.cost_db import get_cost_db

        db = get_cost_db()

        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        with db._connect() as conn:
            rows = conn.execute(
                """SELECT hook_score, virality_score, fit_score,
                          engagement_rate, yt_views
                   FROM draft_analytics
                   WHERE date >= ? AND published = 1
                     AND engagement_rate > 0""",
                (cutoff,),
            ).fetchall()

        if len(rows) < min_rows:
            logger.debug("calibrate_weights: not enough data (%d < %d)", len(rows), min_rows)
            return None

        # 간단한 Pearson 상관계수 계산 (numpy 없이)
        n = len(rows)
        engagement_vals = [r[3] + math.log1p(r[4]) * 0.1 for r in rows]  # combined metric

        # 6D 차원별 proxy 값 (현재 저장된 점수 활용)
        dim_names = ["freshness", "social", "hook", "trend", "audience", "viral"]
        # hook_score → hook, virality_score → viral, fit_score → audience
        # freshness/social/trend는 직접 저장 안 되므로 proxy 사용
        dim_proxies = {
            "hook": [float(r[0] or 5) for r in rows],
            "viral": [float(r[1] or 5) for r in rows],
            "audience": [float(r[2] or 5) for r in rows],
        }

        def _pearson(x: list[float], y: list[float]) -> float:
            mx = sum(x) / n
            my = sum(y) / n
            cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
            sx = math.sqrt(sum((xi - mx) ** 2 for xi in x)) or 1e-10
            sy = math.sqrt(sum((yi - my) ** 2 for yi in y)) or 1e-10
            return cov / (sx * sy)

        correlations = {}
        for dim in dim_names:
            if dim in dim_proxies:
                correlations[dim] = max(0.05, abs(_pearson(dim_proxies[dim], engagement_vals)))
            else:
                correlations[dim] = 0.15  # proxy 없는 차원은 기본값

        # 상관계수 비례로 가중치 재배분 (합=1.0, 각 0.05~0.40)
        total_corr = sum(correlations.values())
        weights = {}
        for dim in dim_names:
            raw = correlations[dim] / total_corr
            weights[dim] = max(0.05, min(0.40, raw))

        # 합 정규화
        w_sum = sum(weights.values())
        weights = {k: round(v / w_sum, 4) for k, v in weights.items()}

        # 저장
        db.save_calibrated_weights(weights)
        logger.info("calibrate_weights: new weights = %s (from %d rows)", weights, n)
        return weights

    except Exception as exc:
        logger.debug("calibrate_weights failed: %s", exc)
        return None
