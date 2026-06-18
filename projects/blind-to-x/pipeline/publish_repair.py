"""Bounded self-repair for fixable X publish HOLD decisions.

Only *mechanical* problems are repaired deterministically here: over-length,
external links in the body, excess hashtags, and forbidden-tone phrases.

Content/structure-quality holds are deliberately NOT patched. Deterministic text
cannot make a draft jupak-compliant, and fabricating boilerplate — a templated
"이건 ~가 아니라 ~의 문제" value declaration plus a generic lingering close — is exactly
the abstraction anti-pattern the jupak X-body policy removed from the prompts (it
also produced identical tails across unrelated posts). Such holds get no change, so
the repair loop marks them exhausted and persists the real, human-reviewable draft
instead of a templated one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from config import as_bool as _as_bool
from pipeline.publish_decision import HOLD, PublishDecision
from pipeline.regulation_checker import x_weighted_character_count

X_MAX_CHARS = 280

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_HASHTAG_RE = re.compile(r"(?<!\S)#\S+")
_SPACE_RE = re.compile(r"\s+")

_FORBIDDEN_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\S+의 감각"), "그 기준"),
    (re.compile(r"\S+한 벽이 됩니다"), "문제가 됩니다"),
    (re.compile(r"\S+의 민낯"), "문제입니다"),
)

# Only mechanically-fixable reasons belong here. Content/structure-quality reasons
# (position / reduction / voice / ending / quality_score_below_threshold) are
# intentionally excluded — see the module docstring: they route to human review
# rather than deterministic boilerplate fabrication.
_FIXABLE_REASONS = {
    "x_weighted_length_exceeded",
    "forbidden_tone",
    "external_link_in_body",
    "hashtag_limit_exceeded",
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


def _trim_to_weighted_limit(text: str, max_chars: int) -> str:
    """Trim to the weighted char limit at a word boundary, preserving leading content."""
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


def repair_hold_draft(
    draft_text: str,
    decision: PublishDecision | dict[str, Any],
    research_context: dict[str, Any] | None = None,
    *,
    max_chars: int = X_MAX_CHARS,
    max_hashtags: int = 3,
) -> PublishRepairResult:
    """Repair a fixable HOLD draft once — mechanical edits only, no LLM, no fabrication.

    ``research_context`` is accepted for call-site compatibility but no longer used:
    deterministic content fabrication was removed (see module docstring). A
    content/structure-quality HOLD that has no mechanical issue returns ``changed=False``
    so the caller routes it to human review instead of templated boilerplate.
    """
    del research_context  # retained for API compatibility; intentionally unused
    original = _as_text(draft_text)
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

    repaired = _normalize_spaces(repaired)
    if "x_weighted_length_exceeded" in reasons or x_weighted_character_count(repaired) > max_chars:
        trimmed = _trim_to_weighted_limit(repaired, max_chars)
        if trimmed != repaired:
            repaired = trimmed
            applied.append("trim_to_x_weighted_limit")

    weighted_length = x_weighted_character_count(repaired) if repaired else 0
    return PublishRepairResult(
        text=repaired,
        changed=repaired != original,
        applied=applied,
        weighted_length=weighted_length,
    )
