"""Bounded self-repair for fixable X publish HOLD decisions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pipeline.publish_decision import HOLD, PublishDecision
from pipeline.regulation_checker import x_weighted_character_count
from config import as_bool as _as_bool

X_MAX_CHARS = 280

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_HASHTAG_RE = re.compile(r"(?<!\S)#\S+")
_SPACE_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")

_FORBIDDEN_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\S+의 감각"), "그 기준"),
    (re.compile(r"\S+한 벽이 됩니다"), "문제가 됩니다"),
    (re.compile(r"\S+의 민낯"), "문제입니다"),
)

_FIXABLE_REASONS = {
    "x_weighted_length_exceeded",
    "forbidden_tone",
    "external_link_in_body",
    "hashtag_limit_exceeded",
    "quality_score_below_threshold",
    "position",
    "reduction",
    "voice",
    "ending",
}


@dataclass(frozen=True)
class PublishRepairResult:
    text: str
    changed: bool
    applied: list[str] = field(default_factory=list)
    weighted_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed": self.changed,
            "applied": list(self.applied),
            "weighted_length": self.weighted_length,
        }


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _decision_reasons(decision: PublishDecision | dict[str, Any]) -> list[str]:
    if isinstance(decision, PublishDecision):
        raw = decision.reasons
    elif isinstance(decision, dict):
        raw = decision.get("reasons")
    else:
        raw = []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item).strip()]


def _is_fixable_hold(decision: PublishDecision | dict[str, Any]) -> bool:
    if isinstance(decision, PublishDecision):
        action = decision.action
        fixable = decision.fixable
    elif isinstance(decision, dict):
        action = decision.get("action")
        fixable = _as_bool(decision.get("fixable"))
    else:
        return False
    if action != HOLD or not fixable:
        return False
    return any(reason in _FIXABLE_REASONS for reason in _decision_reasons(decision))


def _normalize_spaces(text: str) -> str:
    return _SPACE_RE.sub(" ", text).strip()


def _strip_urls(text: str) -> tuple[str, bool]:
    repaired = _URL_RE.sub("", text)
    return repaired, repaired != text


def _limit_hashtags(text: str, max_hashtags: int) -> tuple[str, bool]:
    matches = list(_HASHTAG_RE.finditer(text))
    if len(matches) <= max_hashtags:
        return text, False

    keep = 0
    chunks: list[str] = []
    last = 0
    for match in matches:
        if keep < max_hashtags:
            keep += 1
            continue
        chunks.append(text[last : match.start()])
        last = match.end()
    chunks.append(text[last:])
    return "".join(chunks), True


def _replace_forbidden_tone(text: str) -> tuple[str, bool]:
    repaired = text
    for pattern, replacement in _FORBIDDEN_REPLACEMENTS:
        repaired = pattern.sub(replacement, repaired)
    return repaired, repaired != text


def _extract_hook(text: str) -> str:
    quote_match = re.search(r'"[^"]{4,80}"', text)
    if quote_match:
        return quote_match.group(0)
    first_sentence = _SENTENCE_SPLIT_RE.split(text, maxsplit=1)[0].strip()
    if not first_sentence:
        return ""
    return _trim_to_weighted_limit(first_sentence, 70)


def _frame_sentences(research_context: dict[str, Any]) -> list[str]:
    killer = _as_text(research_context.get("killer_sentence"))
    value = _as_text(research_context.get("universal_value")) or "기준"
    closure = _as_text(research_context.get("closure")) or "open"

    sentences: list[str] = []
    if killer:
        sentences.append(killer.rstrip(".") + ".")
    sentences.append(f"참 개인 감정으로 끝낼 일이 아니라 {value}의 문제거든요.")
    if closure == "closed":
        sentences.append("그래서 이건 그냥 넘기면 안 되는 문제입니다.")
    else:
        sentences.append("정답은 상황마다 다를 수 있어도 기준은 남습니다.")
    return sentences


def _ensure_value_frame(text: str, research_context: dict[str, Any], reasons: list[str]) -> tuple[str, bool]:
    if not ({"position", "reduction", "voice", "ending", "quality_score_below_threshold"} & set(reasons)):
        return text, False

    existing = text
    additions = []
    for sentence in _frame_sentences(research_context):
        sentence_body = sentence.rstrip(".")
        if sentence_body and sentence_body not in existing:
            additions.append(sentence)
    if not additions:
        return text, False
    return _normalize_spaces(text + " " + " ".join(additions)), True


def _trim_to_weighted_limit(text: str, max_chars: int) -> str:
    text = _normalize_spaces(text)
    if x_weighted_character_count(text) <= max_chars:
        return text

    kept: list[str] = []
    for token in text.split():
        candidate = " ".join([*kept, token]).strip()
        if candidate and x_weighted_character_count(candidate) <= max_chars:
            kept.append(token)
        else:
            break
    return " ".join(kept).strip()


def _compress_with_frame(text: str, research_context: dict[str, Any], max_chars: int) -> str:
    hook = _extract_hook(text)
    parts = [part for part in [hook, *_frame_sentences(research_context)] if part]
    candidate = _normalize_spaces(" ".join(parts))
    if x_weighted_character_count(candidate) <= max_chars:
        return candidate
    return _trim_to_weighted_limit(candidate, max_chars)


def repair_hold_draft(
    draft_text: str,
    decision: PublishDecision | dict[str, Any],
    research_context: dict[str, Any] | None,
    *,
    max_chars: int = X_MAX_CHARS,
    max_hashtags: int = 3,
) -> PublishRepairResult:
    """Repair a fixable HOLD draft once without LLM calls or unbounded loops."""
    original = _as_text(draft_text)
    research = research_context or {}
    if not original or not _is_fixable_hold(decision):
        return PublishRepairResult(
            text=original,
            changed=False,
            weighted_length=x_weighted_character_count(original) if original else 0,
        )

    reasons = _decision_reasons(decision)
    applied: list[str] = []
    repaired = original

    if "external_link_in_body" in reasons:
        repaired, changed = _strip_urls(repaired)
        if changed:
            applied.append("strip_url")

    if "hashtag_limit_exceeded" in reasons:
        repaired, changed = _limit_hashtags(repaired, max_hashtags=max_hashtags)
        if changed:
            applied.append("limit_hashtags")

    if "forbidden_tone" in reasons:
        repaired, changed = _replace_forbidden_tone(repaired)
        if changed:
            applied.append("replace_forbidden_tone")

    repaired, changed = _ensure_value_frame(repaired, research, reasons)
    if changed:
        applied.append("ensure_value_frame")

    repaired = _normalize_spaces(repaired)
    if "x_weighted_length_exceeded" in reasons or x_weighted_character_count(repaired) > max_chars:
        repaired = _compress_with_frame(repaired, research, max_chars)
        applied.append("compress_to_x_weighted_limit")

    weighted_length = x_weighted_character_count(repaired) if repaired else 0
    return PublishRepairResult(
        text=repaired,
        changed=repaired != original,
        applied=applied,
        weighted_length=weighted_length,
    )
