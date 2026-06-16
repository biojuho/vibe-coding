"""Single publish decision gate for X automation."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from config import as_bool as _as_bool
from pipeline.regulation_checker import x_weighted_character_count

PUBLISH = "PUBLISH"
HOLD = "HOLD"
DROP = "DROP"

X_MAX_CHARS = 280
DEFAULT_QUALITY_THRESHOLD = 85.0

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_HASHTAG_RE = re.compile(r"(?<!\S)#\S+")
_FRAME_RE = re.compile(r"이건\s+.{1,40}?(?:가|이)\s+아니라\s+.{1,60}?입니다")
_FORBIDDEN_TONE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("~의 감각", re.compile(r"\S+의 감각")),
    ("~한 벽이 됩니다", re.compile(r"\S+한 벽이 됩니다")),
    ("~의 민낯", re.compile(r"\S+의 민낯")),
    # 인플루언서 슬랭 — draft_prompts/rules/prompts.yaml 금지 어휘와 동기화
    ("끝판왕", re.compile(r"끝판왕")),
    ("기절할 뻔", re.compile(r"기절할\s*뻔")),
    ("~만이 살 길", re.compile(r"\S+만이 살 길")),
    # prompts.yaml 금지 목록에 있으나 기존 목록에 없던 과장 반응 어휘
    ("어처구니없어서", re.compile(r"어처구니없어서")),
    ("어질어질", re.compile(r"어질어질")),
    # editorial.yaml influencer_vocab 동기화 — 순수 은어, 합법적 맥락 없음
    ("팩폭", re.compile(r"팩폭")),
    ("현실 자각 타임", re.compile(r"현실\s*자각\s*타임")),
    ("정신 차리고 봐", re.compile(r"정신\s*차리고\s*봐")),
    # draft_quality_gate.py CTA 패턴과 동기화 (influencer 교훈형 CTA)
    ("한 수 알려", re.compile(r"한\s*수\s*알려")),
)


@dataclass(frozen=True)
class PublishDecision:
    action: str
    reason: str
    x_publish_status: str
    quality_score: float
    quality_ceiling: float
    hard_gate: bool = False
    fixable: bool = False
    reasons: list[str] = field(default_factory=list)
    rubric: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "x_publish_status": self.x_publish_status,
            "quality_score": self.quality_score,
            "quality_ceiling": self.quality_ceiling,
            "hard_gate": self.hard_gate,
            "fixable": self.fixable,
            "reasons": list(self.reasons),
            "rubric": dict(self.rubric),
            "metrics": dict(self.metrics),
        }


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_score(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(score):
        return None
    if 0 <= score <= 10:
        score *= 10
    return max(0.0, min(100.0, score))


def _quality_score(scores: Any) -> float | None:
    if isinstance(scores, dict):
        values = [_coerce_score(value) for value in scores.values()]
        numeric = [value for value in values if value is not None]
        if numeric:
            return sum(numeric) / len(numeric)
    return _coerce_score(scores)


def _has_forbidden_tone(text: str) -> list[str]:
    return [label for label, pattern in _FORBIDDEN_TONE_PATTERNS if pattern.search(text)]


def _has_value_frame(text: str, research_context: dict[str, Any]) -> bool:
    killer = _as_text(research_context.get("killer_sentence"))
    if killer and killer in text:
        return True
    return bool(_FRAME_RE.search(text))


def _has_universal_reduction(text: str, research_context: dict[str, Any]) -> bool:
    value = _as_text(research_context.get("universal_value"))
    if value and value in text:
        return True
    return any(token in text for token in ("원칙", "기준", "공정", "존중", "책임", "배려", "경계"))


def _has_operator_voice(text: str) -> bool:
    polite = bool(re.search(r"(요|습니다|합니다|입니다)", text))
    conversational = bool(re.search(r"(참|결국|근데|거든요|것 같아요)", text))
    return polite and conversational


def _ending_matches(text: str, research_context: dict[str, Any]) -> bool:
    closure = _as_text(research_context.get("closure")) or "open"
    stripped = text.rstrip()
    if closure == "closed":
        return not stripped.endswith("?") and any(
            token in text for token in ("문제입니다", "기준입니다", "해야", "안 됩니다")
        )
    return any(token in text for token in ("다를 수", "달라질", "정답은", "남습니다", "생각해볼"))


def evaluate_position_rubric(draft_text: str, research_context: dict[str, Any]) -> dict[str, Any]:
    text = _as_text(draft_text)
    forbidden = _has_forbidden_tone(text)
    items = {
        "position": 100 if _has_value_frame(text, research_context) else 0,
        "reduction": 100 if _has_universal_reduction(text, research_context) else 0,
        "tone": 0 if forbidden else 100,
        "voice": 100 if _has_operator_voice(text) else 0,
        "ending": 100 if _ending_matches(text, research_context) else 0,
    }
    zero_items = [name for name, score in items.items() if score == 0]
    if "tone" in zero_items:
        ceiling = 0.0
    elif zero_items:
        ceiling = 84.0
    else:
        ceiling = 100.0
    return {
        "items": items,
        "zero_items": zero_items,
        "forbidden_tone": forbidden,
        "quality_ceiling": ceiling,
        "score": sum(items.values()) / len(items),
    }


def _regulation_failures(regulation: Any) -> list[str]:
    if not regulation:
        return []
    if isinstance(regulation, str):
        if "경고" in regulation or "FAILED" in regulation or "실패" in regulation:
            return ["regulation_report_not_passed"]
        return []
    if not isinstance(regulation, dict):
        return []

    failures: list[str] = []
    for platform, report in regulation.items():
        passed = getattr(report, "passed", None)
        if passed is None and isinstance(report, dict):
            passed = report.get("passed")
        if passed is False:
            failures.append(f"{platform}:regulation_failed")
    return failures


def _research_failed(research_context: Any) -> bool:
    if not isinstance(research_context, dict) or not research_context:
        return True
    return _as_bool(research_context.get("value_reduction_failed")) or not research_context.get("universal_value")


def decide_publish(
    scores: Any,
    regulation: Any,
    research_context: dict[str, Any] | None,
    draft_text: str,
    *,
    quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
    max_chars: int = X_MAX_CHARS,
    max_hashtags: int = 3,
) -> PublishDecision:
    """Return PUBLISH/HOLD/DROP from the single authoritative gate."""
    text = _as_text(draft_text)
    research = research_context or {}
    if _research_failed(research):
        return PublishDecision(
            action=DROP,
            reason="research_context value reduction failed",
            x_publish_status="Blocked",
            quality_score=0.0,
            quality_ceiling=0.0,
            hard_gate=True,
            reasons=["research_value_reduction_failed"],
            metrics={"weighted_length": x_weighted_character_count(text) if text else 0},
        )

    rubric = evaluate_position_rubric(text, research)
    base_quality = _quality_score(scores)
    if base_quality is None:
        base_quality = float(rubric["score"])
    quality_score = min(float(base_quality), float(rubric["quality_ceiling"]))

    weighted_length = x_weighted_character_count(text)
    hashtag_count = len(_HASHTAG_RE.findall(text))
    hard_hold_reasons: list[str] = []
    if weighted_length > max_chars:
        hard_hold_reasons.append("x_weighted_length_exceeded")
    if rubric["forbidden_tone"]:
        hard_hold_reasons.append("forbidden_tone")
    if _URL_RE.search(text):
        hard_hold_reasons.append("external_link_in_body")
    if hashtag_count > max_hashtags:
        hard_hold_reasons.append("hashtag_limit_exceeded")
    hard_hold_reasons.extend(_regulation_failures(regulation))

    conflict_risk = float(research.get("conflict_risk") or 0.0)
    value_reduced = _has_value_frame(text, research) and _has_universal_reduction(text, research)
    if conflict_risk > 0.8 and not value_reduced:
        return PublishDecision(
            action=DROP,
            reason="high conflict risk without universal value reduction",
            x_publish_status="Blocked",
            quality_score=quality_score,
            quality_ceiling=float(rubric["quality_ceiling"]),
            hard_gate=True,
            reasons=["high_conflict_without_value_reduction"],
            rubric=rubric,
            metrics={
                "weighted_length": weighted_length,
                "hashtags": hashtag_count,
                "conflict_risk": conflict_risk,
            },
        )

    if hard_hold_reasons:
        return PublishDecision(
            action=HOLD,
            reason=hard_hold_reasons[0],
            x_publish_status="Needs Edit",
            quality_score=quality_score,
            quality_ceiling=float(rubric["quality_ceiling"]),
            hard_gate=True,
            fixable=True,
            reasons=hard_hold_reasons,
            rubric=rubric,
            metrics={
                "weighted_length": weighted_length,
                "hashtags": hashtag_count,
                "conflict_risk": conflict_risk,
            },
        )

    if quality_score < quality_threshold:
        return PublishDecision(
            action=HOLD,
            reason=f"quality_score_below_threshold:{quality_score:.1f}<{quality_threshold:.1f}",
            x_publish_status="Needs Edit",
            quality_score=quality_score,
            quality_ceiling=float(rubric["quality_ceiling"]),
            fixable=True,
            reasons=["quality_score_below_threshold", *rubric["zero_items"]],
            rubric=rubric,
            metrics={
                "weighted_length": weighted_length,
                "hashtags": hashtag_count,
                "conflict_risk": conflict_risk,
            },
        )

    return PublishDecision(
        action=PUBLISH,
        reason="all gates passed",
        x_publish_status="Ready to Post",
        quality_score=quality_score,
        quality_ceiling=float(rubric["quality_ceiling"]),
        rubric=rubric,
        metrics={
            "weighted_length": weighted_length,
            "hashtags": hashtag_count,
            "conflict_risk": conflict_risk,
        },
    )


def decision_card_lines(decision: dict[str, Any] | PublishDecision | None) -> list[str]:
    if isinstance(decision, PublishDecision):
        payload = decision.to_dict()
    elif isinstance(decision, dict):
        payload = decision
    else:
        payload = {
            "action": HOLD,
            "reason": "publish decision missing",
            "quality_score": 0,
            "metrics": {},
            "reasons": ["publish_decision_missing"],
        }

    action = _as_text(payload.get("action")) or HOLD
    reason = _as_text(payload.get("reason")) or "reason missing"
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    score = payload.get("quality_score")
    lines = [f"결정: {action} - {reason}"]
    if score not in (None, ""):
        lines.append(f"결정 점수: {_as_text(score)}")
    if metrics:
        detail = ", ".join(f"{key}={value}" for key, value in metrics.items() if value not in (None, ""))
        if detail:
            lines.append(f"결정 근거: {detail}")
    reasons = payload.get("reasons")
    if isinstance(reasons, list) and reasons:
        lines.append("세부 사유: " + ", ".join(str(item) for item in reasons[:5]))
    return lines
