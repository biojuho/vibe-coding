"""Helpers for separating publishable drafts from review metadata."""

from __future__ import annotations

from typing import Any

PUBLISHABLE_DRAFT_KEYS = frozenset(
    {
        "twitter",
        "twitter_thread",
        "threads",
        "newsletter",
        "naver_blog",
    }
)
AUXILIARY_DRAFT_KEYS = frozenset({"reply_text"})
REVIEW_META_DRAFT_KEYS = frozenset({"creator_take"})


def is_internal_draft_key(key: str) -> bool:
    return key.startswith("_")


def is_publishable_draft_key(key: str) -> bool:
    return key in PUBLISHABLE_DRAFT_KEYS


def is_auxiliary_draft_key(key: str) -> bool:
    return key in AUXILIARY_DRAFT_KEYS


def is_review_meta_draft_key(key: str) -> bool:
    return key in REVIEW_META_DRAFT_KEYS


def iter_publishable_drafts(drafts: dict[str, Any]):
    for key, value in drafts.items():
        if is_publishable_draft_key(key) and isinstance(value, str) and value.strip():
            yield key, value


def split_draft_bundle(drafts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = {
        "publishable": {},
        "auxiliary": {},
        "review_meta": {},
        "internal": {},
        "other": {},
    }

    for key, value in drafts.items():
        if is_internal_draft_key(key):
            sections["internal"][key] = value
        elif is_publishable_draft_key(key):
            sections["publishable"][key] = value
        elif is_auxiliary_draft_key(key):
            sections["auxiliary"][key] = value
        elif is_review_meta_draft_key(key):
            sections["review_meta"][key] = value
        else:
            sections["other"][key] = value

    return sections
