"""YouTube Shorts upload metadata helpers."""

from __future__ import annotations

from typing import Any

MAX_DESCRIPTION_BYTES = 5000
MAX_TAG_CHARS = 500


def _clean_text(value: Any) -> str:
    text = " ".join(str(value or "").replace("<", "").replace(">", "").split())
    return text.strip()


def _truncate_utf8(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip()


def _duration_label(value: Any) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return ""
    if seconds <= 0:
        return ""
    return f"{round(seconds)}초"


def _hashtag(value: Any, *, fallback: str = "") -> str:
    text = _clean_text(value).lstrip("#")
    token = "".join(ch for ch in text if ch.isalnum() or ch == "_")
    if not token:
        token = fallback
    return f"#{token}" if token else ""


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _tag_api_char_count(tags: list[str]) -> int:
    total = 0
    for index, tag in enumerate(tags):
        total += len(tag)
        if " " in tag:
            total += 2
        if index:
            total += 1
    return total


def _limit_tags(tags: list[str], max_chars: int = MAX_TAG_CHARS) -> list[str]:
    limited: list[str] = []
    for tag in _dedupe(tags):
        candidate = [*limited, tag]
        if _tag_api_char_count(candidate) > max_chars:
            break
        limited.append(tag)
    return limited


def build_shorts_upload_metadata(item: dict[str, Any]) -> tuple[str, list[str]]:
    """Build copy-ready YouTube Shorts description and API tags from queue item data."""

    topic = _clean_text(item.get("topic"))
    title = _clean_text(item.get("title")) or topic
    channel = _clean_text(item.get("channel"))
    hook_pattern = _clean_text(item.get("hook_pattern"))
    duration = _duration_label(item.get("duration_sec"))

    context_subject = title or topic or "Shorts"
    lines = [context_subject, ""]
    if topic:
        lines.append(f"핵심 요약: {topic}")

    point_parts: list[str] = []
    if hook_pattern:
        point_parts.append(f"{hook_pattern} 훅")
    if duration:
        point_parts.append(f"{duration} 분량")
    if point_parts:
        lines.append(f"시청 포인트: {', '.join(point_parts)}을 담은 쇼츠입니다.")

    if channel:
        lines.append(f"채널: {channel}")

    hashtags = _dedupe(
        [
            "#Shorts",
            _hashtag(channel),
            _hashtag(topic, fallback="Shorts"),
        ]
    )[:3]
    if hashtags:
        lines.extend(["", " ".join(hashtags)])

    description = _truncate_utf8("\n".join(lines).strip(), MAX_DESCRIPTION_BYTES)
    tags = _limit_tags([channel, topic, title, hook_pattern, "Shorts", "YouTube Shorts"])
    return description, tags
