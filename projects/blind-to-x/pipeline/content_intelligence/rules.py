"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

from pipeline.rules_loader import load_rules

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
    """YAML rules list → (label, keywords_tuple) 리스트 변환. 실패 시 fallback 반환.

    YAML 엔트리가 dict가 아닌 경우(str/int/None 등) 안전하게 건너뜀.
    """
    rules = _load_rules().get(key, [])
    if not rules or not isinstance(rules, list):
        return fallback
    result = []
    for entry in rules:
        if not isinstance(entry, dict):
            logger.debug("_yaml_rules_to_tuples(%s): non-dict entry skipped: %r", key, entry)
            continue
        label = entry.get("label", "")
        keywords = tuple(entry.get("keywords", []))
        if label and keywords:
            result.append((label, keywords))
    return result or fallback

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

def _load_x_editorial_rules() -> dict[str, Any]:
    return _load_rules().get("x_editorial_rules", {}) or {}


def _get_topic_editorial_rule(topic_cluster: str) -> dict[str, Any]:
    rules = _load_x_editorial_rules()
    defaults = dict(rules.get("defaults", {}) or {})
    topic_rule = dict((rules.get("topics", {}) or {}).get(topic_cluster, {}) or {})
    return {**defaults, **topic_rule}

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
