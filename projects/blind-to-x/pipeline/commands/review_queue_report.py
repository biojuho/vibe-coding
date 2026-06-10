"""Read-only Notion review queue report for X publish operations."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STATUS_READY = "Ready to Post"
STATUS_PUBLISHED = "Published"
STATUS_BLOCKED = "Blocked"
STATUS_NEEDS_EDIT = "Needs Edit"
STATUS_MISSING = "Missing"
STATUS_OTHER = "Other"
SEVERITY_OK = "ok"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

STATUS_ORDER = (
    STATUS_READY,
    STATUS_PUBLISHED,
    STATUS_BLOCKED,
    STATUS_NEEDS_EDIT,
    STATUS_MISSING,
    STATUS_OTHER,
)

STATUS_ALIASES = {
    "readytopost": STATUS_READY,
    "ready": STATUS_READY,
    "published": STATUS_PUBLISHED,
    "posted": STATUS_PUBLISHED,
    "blocked": STATUS_BLOCKED,
    "failed": STATUS_BLOCKED,
    "neededit": STATUS_NEEDS_EDIT,
    "needsedit": STATUS_NEEDS_EDIT,
    "edit": STATUS_NEEDS_EDIT,
}

DELTA_COUNT_KEYS = (
    "total_records",
    "blocked_count",
    "ready_to_post_count",
    "published_count",
    "needs_edit_count",
    "missing_status_count",
    "stale_ready_count",
    "operator_action_count",
    "operator_action_displayed_count",
    "operator_action_hidden_count",
    "scheduled_due_count",
    "scheduled_ready_count",
    "ready_attention_count",
    "ready_attention_displayed_count",
    "ready_attention_total_count",
    "ready_attention_hidden_count",
)

SEVERITY_ORDER = {
    SEVERITY_OK: 0,
    SEVERITY_WARNING: 1,
    SEVERITY_CRITICAL: 2,
}

RECOVERY_STEP_TEXT = {
    "fix_blocked_publish": (
        "Open the Notion page, fix X Publish Error or draft/media issue, then rerun --reprocess-approved."
    ),
    "publish_or_reschedule": (
        "Manually publish the approved draft or set X Scheduled At; rerun --review-queue-report after updating status."
    ),
    "review_draft_edits": (
        "Edit tweet_body or review notes in Notion, then move X Publish Status to Ready to Post when ready."
    ),
    "fill_x_publish_status": (
        "Set X Publish Status to Ready to Post, Needs Edit, Blocked, or Published before the next review."
    ),
}
RECOVERY_STEP_PRIORITY = {
    "fix_blocked_publish": (10, "critical"),
    "publish_or_reschedule": (30, "stale_ready"),
    "review_draft_edits": (40, "needs_edit"),
    "fill_x_publish_status": (50, "missing_status"),
}
RECOVERY_STEP_DEFAULT_PRIORITY = (90, "review")
OPERATOR_ACTION_ORDER = tuple(RECOVERY_STEP_TEXT)
BLOCKED_ERROR_BUCKET_ORDER = (
    "missing_draft",
    "x_post_failed",
    "notion_sync_failed",
    "media_issue",
    "other",
)
NEEDS_EDIT_REASON_BUCKET_ORDER = (
    "rejection_reasons",
    "risk_flags",
    "review_focus",
    "feedback_request",
    "memo",
    "unknown",
)
MISSING_STATUS_BUCKET_ORDER = (
    "draft_present",
    "draft_missing",
)
READY_AGE_BUCKET_ORDER = (
    "no_date",
    "0_1_days",
    "2_3_days",
    "4_7_days",
    "8_plus_days",
)
READY_ATTENTION_LIMIT = 3
REPORT_OPTION_ORDER = ("lookback_days", "limit", "stale_days", "action_limit", "ready_attention_limit")
QUERY_SCOPE_OPTIONS = frozenset({"lookback_days", "limit"})
REPORT_COMMAND_OPTION_FLAGS = (
    ("limit", "--limit"),
    ("lookback_days", "--review-queue-lookback-days"),
    ("stale_days", "--review-queue-stale-days"),
    ("action_limit", "--review-queue-action-limit"),
    ("ready_attention_limit", "--review-queue-ready-attention-limit"),
)
BLOCKED_ERROR_RECOVERY_HINTS = {
    "missing_draft": "Fill tweet_body or regenerate the draft before rerunning --reprocess-approved.",
    "x_post_failed": "Check X credentials/rate limits and retry manual reprocess after the account is ready.",
    "notion_sync_failed": "Verify Notion credentials/schema, then resync the publish state manually.",
    "media_issue": "Check screenshot/media upload output before retrying the approved post.",
    "other": "Inspect X Publish Error and update the Notion review state before retrying.",
}
NEEDS_EDIT_REASON_RECOVERY_HINTS = {
    "rejection_reasons": "Start from the rejection reason tags and edit only the failing draft dimension.",
    "risk_flags": "Resolve the named risk flags before moving the item back to Ready to Post.",
    "review_focus": "Use the review focus text as the single edit checklist for the draft.",
    "feedback_request": "Answer the feedback request in Notion, then update the draft/status.",
    "memo": "Inspect the review note and convert it into one concrete edit before approval.",
    "unknown": "Open the Notion page and add review notes or a rejection reason before rerouting.",
}
MISSING_STATUS_RECOVERY_HINTS = {
    "draft_present": "Set X Publish Status from the existing draft: Ready to Post, Needs Edit, Blocked, or Published.",
    "draft_missing": "Regenerate or write tweet_body first, then set X Publish Status for manual review.",
}


def _coerce_int(value: Any, default: int, *, minimum: int = 0) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        coerced = default
    return max(minimum, coerced)


def _safe_count(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_options(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _quote_command_arg(value: Any) -> str:
    text = str(value)
    if not text:
        return "''"
    if any(char.isspace() for char in text) or "'" in text or '"' in text:
        return "'" + text.replace("'", "''") + "'"
    return text


def _build_review_queue_command(report: dict[str, Any], **overrides: Any) -> str:
    report_options = _safe_options(report.get("report_options"))
    parts = ["python", "main.py", "--review-queue-report"]
    for option_name, flag in REPORT_COMMAND_OPTION_FLAGS:
        value = overrides.get(option_name, report_options.get(option_name))
        if value is not None:
            parts.extend([flag, _quote_command_arg(value)])
    artifact_path = report.get("artifact_path")
    if artifact_path:
        parts.extend(["--review-queue-report-output", _quote_command_arg(artifact_path)])
    return " ".join(parts)


def build_operator_next_commands(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return copy-ready read-only commands for follow-up queue inspection."""
    commands = [
        {
            "name": "refresh_report",
            "command": _build_review_queue_command(report),
            "purpose": "Rerun the same read-only review queue report.",
            "read_only": True,
            "notion_writes": False,
            "x_posts": False,
            "publish_command": False,
            "manual_publish_required": True,
        }
    ]
    if bool(report.get("operator_action_truncated")):
        total_actions = _safe_count(report.get("operator_action_count"))
        commands.append(
            {
                "name": "show_all_actions",
                "command": _build_review_queue_command(report, action_limit=total_actions),
                "purpose": f"Show all {total_actions} current operator actions without publishing.",
                "read_only": True,
                "notion_writes": False,
                "x_posts": False,
                "publish_command": False,
                "manual_publish_required": True,
            }
        )
    if bool(report.get("ready_attention_truncated")):
        total_attention = _safe_count(report.get("ready_attention_total_count"))
        commands.append(
            {
                "name": "show_all_ready_attention",
                "command": _build_review_queue_command(report, ready_attention_limit=total_attention),
                "purpose": f"Show all {total_attention} Ready to Post attention items without publishing.",
                "read_only": True,
                "notion_writes": False,
                "x_posts": False,
                "publish_command": False,
                "manual_publish_required": True,
            }
        )
    return commands


def _compact_text(value: Any, limit: int = 96) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _target_hint(action: dict[str, Any]) -> str:
    page_url = str(action.get("page_url") or "").strip()
    if page_url:
        return _compact_text(page_url, limit=120)
    page_id = str(action.get("page_id") or "").strip()
    if not page_id:
        return ""
    normalized = page_id.replace("-", "")
    short_id = normalized[:8] if normalized else page_id[:8]
    return f"page_id:{short_id}"


def _schedule_hint(item: dict[str, Any]) -> str:
    state = str(item.get("schedule_state") or "").strip()
    scheduled_at = str(item.get("scheduled_at") or "").strip()
    if state not in {"scheduled_due", "scheduled_future"}:
        return ""
    if scheduled_at:
        return f"schedule={state}@{scheduled_at}"
    return f"schedule={state}"


def _triage_bucket(item: dict[str, Any]) -> str:
    error_bucket = str(item.get("error_bucket") or "").strip()
    if error_bucket:
        return error_bucket
    reason_bucket = str(item.get("reason_bucket") or "").strip()
    if reason_bucket:
        return reason_bucket
    return str(item.get("triage_bucket") or "").strip()


def _triage_hint(item: dict[str, Any]) -> str:
    action_name = str(item.get("action") or "").strip()
    bucket = _triage_bucket(item)
    if not bucket:
        return ""
    if action_name == "fix_blocked_publish":
        return BLOCKED_ERROR_RECOVERY_HINTS.get(bucket, "")
    if action_name == "review_draft_edits":
        return NEEDS_EDIT_REASON_RECOVERY_HINTS.get(bucket, "")
    if action_name == "fill_x_publish_status":
        return MISSING_STATUS_RECOVERY_HINTS.get(bucket, "")
    return ""


def _operator_action_key(action: dict[str, Any]) -> str:
    page_id = str(action.get("page_id") or "").strip()
    if page_id:
        return f"page_id:{page_id}"
    page_url = str(action.get("page_url") or "").strip()
    if page_url:
        return f"page_url:{page_url}"
    target_hint = str(action.get("target_hint") or _target_hint(action)).strip()
    if target_hint:
        return f"target:{target_hint}"
    title = _compact_text(action.get("title"), limit=80)
    action_name = str(action.get("action") or "").strip()
    if title and action_name:
        return f"action_title:{action_name}:{title}"
    return ""


def _ready_attention_key(item: dict[str, Any]) -> str:
    page_id = str(item.get("page_id") or "").strip()
    if page_id:
        return f"page_id:{page_id}"
    page_url = str(item.get("page_url") or "").strip()
    if page_url:
        return f"page_url:{page_url}"
    target_hint = str(item.get("target_hint") or _target_hint(item)).strip()
    if target_hint:
        return f"target:{target_hint}"
    title = _compact_text(item.get("title"), limit=80)
    if title:
        return f"ready_title:{title}"
    return ""


def _join_compact_values(value: Any, *, limit: int = 96) -> str:
    if isinstance(value, (list, tuple, set)):
        text = ", ".join(str(item).strip() for item in value if str(item).strip())
    else:
        text = str(value or "").strip()
    return _compact_text(text, limit=limit)


def _needs_edit_reason(record: dict[str, Any]) -> str:
    bucket, reason = _needs_edit_bucket_and_reason(record)
    return reason


def _needs_edit_bucket_and_reason(record: dict[str, Any]) -> tuple[str, str]:
    reason_fields = (
        ("rejection_reasons", "Rejection reasons"),
        ("risk_flags", "Risk flags"),
        ("review_focus", "Review focus"),
        ("feedback_request", "Feedback request"),
        ("memo", "Review note"),
    )
    for field_name, label in reason_fields:
        value = _join_compact_values(record.get(field_name))
        if value:
            return field_name, f"{label}: {value}"
    return "unknown", "Draft is marked Needs Edit"


def _missing_status_reason(record: dict[str, Any]) -> str:
    _, reason = _missing_status_bucket_and_reason(record)
    return reason


def _missing_status_bucket_and_reason(record: dict[str, Any]) -> tuple[str, str]:
    details = []
    notion_status = _join_compact_values(record.get("status"), limit=48)
    if notion_status:
        details.append(f"notion_status={notion_status}")
    tweet_body = _join_compact_values(record.get("tweet_body"), limit=8)
    if tweet_body:
        details.append("tweet_body=present")
        return "draft_present", "Missing X publish status; " + ", ".join(details)
    details.append("tweet_body=missing")
    return "draft_missing", "Missing X publish status; " + ", ".join(details)


def _recovery_priority(action_name: str) -> tuple[int, str]:
    return RECOVERY_STEP_PRIORITY.get(action_name, RECOVERY_STEP_DEFAULT_PRIORITY)


def _ordered_nonzero_blocked_error_buckets(error_counts: dict[str, Any]) -> list[str]:
    return sorted(
        [bucket for bucket, count in error_counts.items() if _safe_count(count) > 0],
        key=lambda bucket: (
            -_safe_count(error_counts.get(bucket)),
            BLOCKED_ERROR_BUCKET_ORDER.index(bucket) if bucket in BLOCKED_ERROR_BUCKET_ORDER else 999,
            bucket,
        ),
    )


def _ordered_nonzero_needs_edit_reason_buckets(reason_counts: dict[str, Any]) -> list[str]:
    return sorted(
        [bucket for bucket, count in reason_counts.items() if _safe_count(count) > 0],
        key=lambda bucket: (
            -_safe_count(reason_counts.get(bucket)),
            (NEEDS_EDIT_REASON_BUCKET_ORDER.index(bucket) if bucket in NEEDS_EDIT_REASON_BUCKET_ORDER else 999),
            bucket,
        ),
    )


def _ordered_nonzero_missing_status_buckets(bucket_counts: dict[str, Any]) -> list[str]:
    return sorted(
        [bucket for bucket, count in bucket_counts.items() if _safe_count(count) > 0],
        key=lambda bucket: (
            -_safe_count(bucket_counts.get(bucket)),
            MISSING_STATUS_BUCKET_ORDER.index(bucket) if bucket in MISSING_STATUS_BUCKET_ORDER else 999,
            bucket,
        ),
    )


def _top_count_item(counts: dict[str, Any], order: tuple[str, ...]) -> dict[str, Any]:
    buckets = sorted(
        [bucket for bucket, count in counts.items() if _safe_count(count) > 0],
        key=lambda bucket: (
            -_safe_count(counts.get(bucket)),
            order.index(bucket) if bucket in order else 999,
            bucket,
        ),
    )
    if not buckets:
        return {"name": "", "count": 0}
    name = buckets[0]
    return {"name": name, "count": _safe_count(counts.get(name))}


def _top_ready_attention_movement(changes: list[Any]) -> dict[str, Any]:
    for change in changes:
        if not isinstance(change, dict):
            continue
        target_hint = change.get("target_hint") or change.get("ready_attention_key") or ""
        return {
            "ready_attention_key": change.get("ready_attention_key") or "",
            "page_id": change.get("page_id"),
            "target_hint": target_hint,
            "title": _compact_text(change.get("title"), limit=48),
            "previous_rank": _safe_count(change.get("previous_rank")),
            "current_rank": _safe_count(change.get("current_rank")),
            "rank_delta": _safe_count(change.get("rank_delta")),
            "direction": change.get("direction") or "same",
            "previous_age_days": change.get("previous_age_days"),
            "current_age_days": change.get("current_age_days"),
        }
    return {
        "ready_attention_key": "",
        "page_id": None,
        "target_hint": "",
        "title": "",
        "previous_rank": 0,
        "current_rank": 0,
        "rank_delta": 0,
        "direction": "",
        "previous_age_days": None,
        "current_age_days": None,
    }


def _top_ready_age_bucket(ready_age_buckets: dict[str, Any]) -> dict[str, Any]:
    for bucket in reversed(READY_AGE_BUCKET_ORDER):
        count = _safe_count(ready_age_buckets.get(bucket))
        if count > 0:
            return {"name": bucket, "count": count}
    return {"name": "", "count": 0}


def _operator_action_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    actions = report.get("operator_actions") if isinstance(report.get("operator_actions"), list) else []
    index: dict[str, dict[str, Any]] = {}
    for action in actions:
        if not isinstance(action, dict):
            continue
        key = str(action.get("operator_action_key") or _operator_action_key(action)).strip()
        if key and key not in index:
            index[key] = action
    return index


def _build_operator_action_rank_changes(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> list[dict[str, Any]]:
    current_actions = _operator_action_index(current)
    previous_actions = _operator_action_index(previous)
    changes: list[dict[str, Any]] = []
    for key in sorted(set(current_actions) & set(previous_actions)):
        current_action = current_actions[key]
        previous_action = previous_actions[key]
        current_rank = _safe_count(current_action.get("operator_action_rank"))
        previous_rank = _safe_count(previous_action.get("operator_action_rank"))
        if not current_rank or not previous_rank:
            continue
        rank_delta = current_rank - previous_rank
        current_name = str(current_action.get("action") or "")
        previous_name = str(previous_action.get("action") or "")
        if rank_delta == 0 and current_name == previous_name:
            continue
        direction = "up" if rank_delta < 0 else ("down" if rank_delta > 0 else "same")
        changes.append(
            {
                "operator_action_key": key,
                "page_id": current_action.get("page_id") or previous_action.get("page_id"),
                "target_hint": current_action.get("target_hint")
                or previous_action.get("target_hint")
                or _target_hint(current_action),
                "title": current_action.get("title") or previous_action.get("title") or "",
                "previous_rank": previous_rank,
                "current_rank": current_rank,
                "rank_delta": rank_delta,
                "direction": direction,
                "previous_action": previous_name,
                "current_action": current_name,
            }
        )
    return sorted(
        changes,
        key=lambda item: (
            _safe_count(item.get("current_rank")),
            abs(_safe_count(item.get("rank_delta"))),
            str(item.get("title") or ""),
        ),
    )


def _ready_attention_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = report.get("ready_attention_items") if isinstance(report.get("ready_attention_items"), list) else []
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("ready_attention_key") or _ready_attention_key(item)).strip()
        if key and key not in index:
            index[key] = item
    return index


def _build_ready_attention_rank_changes(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> list[dict[str, Any]]:
    current_items = _ready_attention_index(current)
    previous_items = _ready_attention_index(previous)
    changes: list[dict[str, Any]] = []
    for key in sorted(set(current_items) & set(previous_items)):
        current_item = current_items[key]
        previous_item = previous_items[key]
        current_rank = _safe_count(current_item.get("ready_attention_rank"))
        previous_rank = _safe_count(previous_item.get("ready_attention_rank"))
        if not current_rank or not previous_rank:
            continue
        rank_delta = current_rank - previous_rank
        current_age = current_item.get("age_days")
        previous_age = previous_item.get("age_days")
        if rank_delta == 0 and current_age == previous_age:
            continue
        direction = "up" if rank_delta < 0 else ("down" if rank_delta > 0 else "same")
        changes.append(
            {
                "ready_attention_key": key,
                "page_id": current_item.get("page_id") or previous_item.get("page_id"),
                "target_hint": current_item.get("target_hint")
                or previous_item.get("target_hint")
                or _target_hint(current_item),
                "title": current_item.get("title") or previous_item.get("title") or "",
                "previous_rank": previous_rank,
                "current_rank": current_rank,
                "rank_delta": rank_delta,
                "direction": direction,
                "previous_age_days": previous_age,
                "current_age_days": current_age,
                "previous_age_bucket": previous_item.get("age_bucket"),
                "current_age_bucket": current_item.get("age_bucket"),
            }
        )
    return sorted(
        changes,
        key=lambda item: (
            _safe_count(item.get("current_rank")),
            abs(_safe_count(item.get("rank_delta"))),
            str(item.get("title") or ""),
        ),
    )


def _operator_priority(report: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    score = 0

    blocked_count = _safe_count(report.get("blocked_count"))
    if blocked_count:
        score += blocked_count * 100
        reasons.append(f"blocked_count={blocked_count}")

    ready_age_buckets = report.get("ready_age_buckets") if isinstance(report.get("ready_age_buckets"), dict) else {}
    ready_8_plus_count = _safe_count(ready_age_buckets.get("8_plus_days"))
    if ready_8_plus_count:
        score += ready_8_plus_count * 40
        reasons.append(f"ready_8_plus_count={ready_8_plus_count}")

    stale_ready_count = _safe_count(report.get("stale_ready_count"))
    if stale_ready_count:
        score += stale_ready_count * 25
        reasons.append(f"stale_ready_count={stale_ready_count}")

    scheduled_due_count = _safe_count(report.get("scheduled_due_count"))
    if scheduled_due_count:
        score += scheduled_due_count * 30
        reasons.append(f"scheduled_due_count={scheduled_due_count}")

    needs_edit_count = _safe_count(report.get("needs_edit_count"))
    if needs_edit_count:
        score += needs_edit_count * 15
        reasons.append(f"needs_edit_count={needs_edit_count}")

    missing_status_counts = (
        report.get("missing_status_counts") if isinstance(report.get("missing_status_counts"), dict) else {}
    )
    draft_missing_count = _safe_count(missing_status_counts.get("draft_missing"))
    if draft_missing_count:
        score += draft_missing_count * 15
        reasons.append(f"missing_status_draft_missing={draft_missing_count}")
    draft_present_count = _safe_count(missing_status_counts.get("draft_present"))
    if draft_present_count:
        score += draft_present_count * 10
        reasons.append(f"missing_status_draft_present={draft_present_count}")

    if blocked_count:
        label = "critical"
    elif score >= 100:
        label = "backlog"
    elif score > 0:
        label = "attention"
    else:
        label = "clear"

    return {
        "score": score,
        "label": label,
        "reasons": reasons,
    }


def _ready_age_bucket(age_days: int | None) -> str:
    if age_days is None:
        return "no_date"
    if age_days <= 1:
        return "0_1_days"
    if age_days <= 3:
        return "2_3_days"
    if age_days <= 7:
        return "4_7_days"
    return "8_plus_days"


def _build_ready_attention_items(
    ready_items: list[dict[str, Any]],
    *,
    stale_days: int,
    limit: int = READY_ATTENTION_LIMIT,
) -> list[dict[str, Any]]:
    """Return the Ready queue items an operator should inspect first."""
    max_items = _coerce_int(limit, READY_ATTENTION_LIMIT, minimum=0)

    def sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        age_days = item.get("age_days")
        if age_days is None:
            return (1, 0, str(item.get("title") or ""))
        age = int(age_days)
        return (0 if age >= stale_days else 2, -age, str(item.get("title") or ""))

    sorted_items = sorted(ready_items, key=sort_key)
    return [
        {
            "ready_attention_rank": rank,
            "ready_attention_key": _ready_attention_key(item),
            "age_days": item.get("age_days"),
            "age_bucket": _ready_age_bucket(item.get("age_days")),
            "page_id": item.get("page_id"),
            "page_url": item.get("page_url"),
            "target_hint": _target_hint(item),
            "title": _compact_text(item.get("title")),
            "schedule_state": item.get("schedule_state") or "",
            "scheduled_at": item.get("scheduled_at") or "",
        }
        for rank, item in enumerate(sorted_items[:max_items], start=1)
    ]


def classify_blocked_publish_error(value: Any) -> str:
    """Map a blocked X publish error into a stable operator incident bucket."""
    text = str(value or "").casefold()
    token = _tokenize(text)
    if not token:
        return "other"
    if "missing" in text and ("tweet" in text or "draft" in text):
        return "missing_draft"
    if "notion" in text and ("update" in text or "sync" in text or "schema" in text):
        return "notion_sync_failed"
    if "media" in text or "image" in text or "upload" in text:
        return "media_issue"
    if "twitter" in text or "xapi" in token or "postfailed" in token or "tweetfailed" in token:
        return "x_post_failed"
    return "other"


def _tokenize(value: Any) -> str:
    return "".join(ch for ch in str(value or "").casefold() if ch.isalnum())


def normalize_x_publish_status(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return STATUS_MISSING
    token = _tokenize(value)
    if token in STATUS_ALIASES:
        return STATUS_ALIASES[token]
    text = str(value).strip()
    return text if text in STATUS_ORDER else STATUS_OTHER


def _parse_isoish(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _record_timestamp(record: dict[str, Any]) -> datetime | None:
    return (
        _parse_isoish(record.get("date"))
        or _parse_isoish(record.get("x_scheduled_at"))
        or _parse_isoish(record.get("x_published_at"))
    )


def _age_days(record: dict[str, Any], now: datetime) -> int | None:
    timestamp = _record_timestamp(record)
    if timestamp is None:
        return None
    delta = now.astimezone(UTC) - timestamp
    return max(0, delta.days)


def _ready_schedule_state(record: dict[str, Any], now: datetime) -> str:
    scheduled_at = _parse_isoish(record.get("x_scheduled_at"))
    if scheduled_at is None:
        return "unscheduled"
    if scheduled_at > now.astimezone(UTC):
        return "scheduled_future"
    return "scheduled_due"


def _ready_age_days(record: dict[str, Any], now: datetime) -> int | None:
    scheduled_at = _parse_isoish(record.get("x_scheduled_at"))
    if scheduled_at is not None and scheduled_at <= now.astimezone(UTC):
        delta = now.astimezone(UTC) - scheduled_at
        return max(0, delta.days)
    return _age_days(record, now)


def _record_title(record: dict[str, Any]) -> str:
    return str(record.get("title") or record.get("url") or record.get("page_id") or "").strip()


def _action_for_record(
    record: dict[str, Any],
    status: str,
    age_days: int | None,
    stale_days: int,
    *,
    ready_schedule_state: str = "unscheduled",
) -> dict | None:
    if status == STATUS_BLOCKED:
        reason = str(record.get("x_publish_error") or "Blocked X publish status").strip()
        return {
            "action": "fix_blocked_publish",
            "reason": reason,
            "error_bucket": classify_blocked_publish_error(reason),
        }
    if status == STATUS_READY:
        if ready_schedule_state == "scheduled_future":
            return None
        if ready_schedule_state == "scheduled_due":
            if age_days is None or age_days == 0:
                reason = "Ready scheduled time is due"
            else:
                reason = f"Ready scheduled time passed {age_days} days ago"
            return {"action": "publish_or_reschedule", "reason": reason}
        if age_days is None or age_days >= stale_days:
            reason = "Ready item has no date" if age_days is None else f"Ready item has waited {age_days} days"
            return {"action": "publish_or_reschedule", "reason": reason}
    if status == STATUS_NEEDS_EDIT:
        reason_bucket, reason = _needs_edit_bucket_and_reason(record)
        return {"action": "review_draft_edits", "reason": reason, "reason_bucket": reason_bucket}
    if status == STATUS_MISSING:
        reason_bucket, reason = _missing_status_bucket_and_reason(record)
        return {"action": "fill_x_publish_status", "reason": reason, "reason_bucket": reason_bucket}
    return None


def build_operator_recovery_steps(actions: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    """Convert prioritized report actions into short operator recovery steps."""
    max_items = _coerce_int(limit, 3, minimum=0)
    steps: list[dict[str, Any]] = []
    for action in actions[:max_items]:
        action_name = str(action.get("action") or "").strip()
        priority, priority_label = _recovery_priority(action_name)
        next_step = RECOVERY_STEP_TEXT.get(
            action_name,
            "Review this Notion page and update X Publish Status before the next run.",
        )
        steps.append(
            {
                "action": action_name,
                "priority": priority,
                "priority_label": priority_label,
                "page_id": action.get("page_id"),
                "page_url": action.get("page_url"),
                "target_hint": _target_hint(action),
                "title": _compact_text(action.get("title")),
                "reason": _compact_text(action.get("reason")),
                "error_bucket": action.get("error_bucket") or "",
                "reason_bucket": action.get("reason_bucket") or "",
                "triage_bucket": _triage_bucket(action),
                "triage_hint": _triage_hint(action),
                "schedule_state": action.get("schedule_state") or "",
                "scheduled_at": action.get("scheduled_at") or "",
                "next_step": next_step,
            }
        )
    return steps


def build_review_queue_report(
    records: list[dict[str, Any]],
    *,
    stale_days: int = 3,
    action_limit: int = 10,
    ready_attention_limit: int = READY_ATTENTION_LIMIT,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build an operator-facing read-only summary for recent Notion review records."""
    now = now or datetime.now(UTC)
    now_utc = now.astimezone(UTC)
    stale_days = _coerce_int(stale_days, 3, minimum=0)
    action_limit = _coerce_int(action_limit, 10, minimum=0)
    ready_attention_limit = _coerce_int(ready_attention_limit, READY_ATTENTION_LIMIT, minimum=0)
    counts: Counter[str] = Counter()
    operator_actions: list[dict[str, Any]] = []
    ready_items: list[dict[str, Any]] = []

    for record in records:
        status = normalize_x_publish_status(record.get("x_publish_status"))
        counts[status] += 1
        age = _ready_age_days(record, now_utc) if status == STATUS_READY else _age_days(record, now)
        ready_schedule_state = _ready_schedule_state(record, now_utc) if status == STATUS_READY else ""
        scheduled_at = _parse_isoish(record.get("x_scheduled_at")) if status == STATUS_READY else None
        if status == STATUS_READY:
            ready_items.append(
                {
                    "page_id": record.get("page_id"),
                    "page_url": record.get("page_url"),
                    "title": _record_title(record),
                    "age_days": age,
                    "schedule_state": ready_schedule_state,
                    "scheduled_at": scheduled_at.isoformat() if scheduled_at else "",
                }
            )
        action = _action_for_record(record, status, age, stale_days, ready_schedule_state=ready_schedule_state)
        if action:
            action_priority, action_priority_label = _recovery_priority(str(action.get("action") or ""))
            operator_actions.append(
                {
                    "page_id": record.get("page_id"),
                    "page_url": record.get("page_url"),
                    "target_hint": _target_hint(record),
                    "title": _record_title(record),
                    "x_publish_status": status,
                    "age_days": age,
                    "schedule_state": ready_schedule_state,
                    "scheduled_at": scheduled_at.isoformat() if scheduled_at else "",
                    "priority": action_priority,
                    "priority_label": action_priority_label,
                    **action,
                }
            )

    status_counts = {status: counts.get(status, 0) for status in STATUS_ORDER}
    extra_statuses = sorted(status for status in counts if status not in status_counts)
    for status in extra_statuses:
        status_counts[status] = counts[status]

    operator_actions.sort(
        key=lambda item: (
            item.get("priority", RECOVERY_STEP_DEFAULT_PRIORITY[0]),
            -(item["age_days"] or 0),
            str(item.get("title") or ""),
        )
    )
    for rank, action in enumerate(operator_actions, start=1):
        action["operator_action_rank"] = rank
        action["operator_action_key"] = _operator_action_key(action)
    limited_actions = operator_actions[:action_limit]
    hidden_action_count = max(len(operator_actions) - len(limited_actions), 0)
    operator_action_counter = Counter(str(item.get("action") or "") for item in operator_actions if item.get("action"))
    operator_action_counts = {
        action_name: operator_action_counter.get(action_name, 0) for action_name in OPERATOR_ACTION_ORDER
    }
    for action_name in sorted(operator_action_counter):
        if action_name not in operator_action_counts:
            operator_action_counts[action_name] = operator_action_counter[action_name]
    blocked_error_counter = Counter(
        str(item.get("error_bucket") or "other")
        for item in operator_actions
        if item.get("x_publish_status") == STATUS_BLOCKED
    )
    blocked_error_counts = {bucket: blocked_error_counter.get(bucket, 0) for bucket in BLOCKED_ERROR_BUCKET_ORDER}
    for bucket in sorted(blocked_error_counter):
        if bucket not in blocked_error_counts:
            blocked_error_counts[bucket] = blocked_error_counter[bucket]
    blocked_error_examples: dict[str, str] = {}
    for item in operator_actions:
        if item.get("x_publish_status") != STATUS_BLOCKED:
            continue
        bucket = str(item.get("error_bucket") or "other")
        if bucket not in blocked_error_examples:
            blocked_error_examples[bucket] = _compact_text(item.get("reason"))
    needs_edit_reason_counter = Counter(
        str(item.get("reason_bucket") or "unknown")
        for item in operator_actions
        if item.get("x_publish_status") == STATUS_NEEDS_EDIT
    )
    needs_edit_reason_counts = {
        bucket: needs_edit_reason_counter.get(bucket, 0) for bucket in NEEDS_EDIT_REASON_BUCKET_ORDER
    }
    for bucket in sorted(needs_edit_reason_counter):
        if bucket not in needs_edit_reason_counts:
            needs_edit_reason_counts[bucket] = needs_edit_reason_counter[bucket]
    needs_edit_reason_examples: dict[str, str] = {}
    for item in operator_actions:
        if item.get("x_publish_status") != STATUS_NEEDS_EDIT:
            continue
        bucket = str(item.get("reason_bucket") or "unknown")
        if bucket not in needs_edit_reason_examples:
            needs_edit_reason_examples[bucket] = _compact_text(item.get("reason"))
    missing_status_counter = Counter(
        str(item.get("reason_bucket") or "draft_missing")
        for item in operator_actions
        if item.get("x_publish_status") == STATUS_MISSING
    )
    missing_status_counts = {bucket: missing_status_counter.get(bucket, 0) for bucket in MISSING_STATUS_BUCKET_ORDER}
    for bucket in sorted(missing_status_counter):
        if bucket not in missing_status_counts:
            missing_status_counts[bucket] = missing_status_counter[bucket]
    missing_status_examples: dict[str, str] = {}
    for item in operator_actions:
        if item.get("x_publish_status") != STATUS_MISSING:
            continue
        bucket = str(item.get("reason_bucket") or "draft_missing")
        if bucket not in missing_status_examples:
            missing_status_examples[bucket] = _compact_text(item.get("reason"))
    attention_ready_items = [
        item for item in ready_items if str(item.get("schedule_state") or "") != "scheduled_future"
    ]
    scheduled_due_count = len(
        [item for item in ready_items if str(item.get("schedule_state") or "") == "scheduled_due"]
    )
    scheduled_ready_count = len(ready_items) - len(attention_ready_items)
    ready_age_counter = Counter(_ready_age_bucket(item.get("age_days")) for item in attention_ready_items)
    ready_age_buckets = {bucket: ready_age_counter.get(bucket, 0) for bucket in READY_AGE_BUCKET_ORDER}
    dated_ready_items = [item for item in attention_ready_items if item.get("age_days") is not None]
    oldest_ready_item = (
        max(dated_ready_items, key=lambda item: int(item.get("age_days") or 0))
        if dated_ready_items
        else (attention_ready_items[0] if attention_ready_items else None)
    )
    oldest_ready = {
        "age_days": oldest_ready_item.get("age_days") if oldest_ready_item else None,
        "page_id": oldest_ready_item.get("page_id") if oldest_ready_item else None,
        "page_url": oldest_ready_item.get("page_url") if oldest_ready_item else None,
        "target_hint": _target_hint(oldest_ready_item) if oldest_ready_item else "",
        "title": _compact_text(oldest_ready_item.get("title")) if oldest_ready_item else "",
    }
    ready_attention_items = _build_ready_attention_items(
        attention_ready_items,
        stale_days=stale_days,
        limit=ready_attention_limit,
    )

    report = {
        "success": True,
        "dry_run": True,
        "safety": {
            "read_only": True,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "generated_at": now.astimezone(UTC).isoformat(),
        "report_options": {
            "stale_days": stale_days,
            "action_limit": action_limit,
            "ready_attention_limit": ready_attention_limit,
        },
        "total_records": len(records),
        "status_counts": status_counts,
        "blocked_count": status_counts[STATUS_BLOCKED],
        "ready_to_post_count": status_counts[STATUS_READY],
        "published_count": status_counts[STATUS_PUBLISHED],
        "needs_edit_count": status_counts[STATUS_NEEDS_EDIT],
        "missing_status_count": status_counts[STATUS_MISSING],
        "stale_ready_count": len(
            [
                item
                for item in operator_actions
                if item["x_publish_status"] == STATUS_READY
                and (item["age_days"] is None or item["age_days"] >= stale_days)
            ]
        ),
        "operator_action_count": len(operator_actions),
        "operator_action_displayed_count": len(limited_actions),
        "operator_action_hidden_count": hidden_action_count,
        "operator_action_truncated": hidden_action_count > 0,
        "operator_action_counts": operator_action_counts,
        "scheduled_due_count": scheduled_due_count,
        "scheduled_ready_count": scheduled_ready_count,
        "ready_age_buckets": ready_age_buckets,
        "ready_missing_date_count": ready_age_buckets["no_date"],
        "oldest_ready": oldest_ready,
        "ready_attention_count": len(ready_attention_items),
        "ready_attention_displayed_count": len(ready_attention_items),
        "ready_attention_total_count": len(attention_ready_items),
        "ready_attention_hidden_count": max(len(attention_ready_items) - len(ready_attention_items), 0),
        "ready_attention_truncated": len(attention_ready_items) > len(ready_attention_items),
        "ready_attention_items": ready_attention_items,
        "blocked_error_counts": blocked_error_counts,
        "blocked_error_examples": blocked_error_examples,
        "blocked_error_recovery_hints": BLOCKED_ERROR_RECOVERY_HINTS,
        "needs_edit_reason_counts": needs_edit_reason_counts,
        "needs_edit_reason_examples": needs_edit_reason_examples,
        "needs_edit_reason_recovery_hints": NEEDS_EDIT_REASON_RECOVERY_HINTS,
        "missing_status_counts": missing_status_counts,
        "missing_status_examples": missing_status_examples,
        "missing_status_recovery_hints": MISSING_STATUS_RECOVERY_HINTS,
        "operator_actions": limited_actions,
        "operator_recovery_steps": build_operator_recovery_steps(limited_actions),
    }
    report["summary"] = build_review_queue_summary(report)
    report["incident_response"] = build_incident_response(report)
    report["operator_next_commands"] = build_operator_next_commands(report)
    return report


def build_review_queue_delta(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(previous, dict):
        return {"has_previous": False}

    delta = {
        "has_previous": True,
        "previous_generated_at": previous.get("generated_at"),
        "counts": {},
        "status_counts": {},
    }
    current_options = _safe_options(current.get("report_options"))
    previous_options = _safe_options(previous.get("report_options"))
    option_changes = {}
    option_keys = sorted(set(current_options) | set(previous_options))
    for option_name in option_keys:
        current_value = current_options.get(option_name)
        previous_value = previous_options.get(option_name)
        if current_value != previous_value:
            option_changes[option_name] = {
                "previous": previous_value,
                "current": current_value,
            }
    delta["comparable"] = not option_changes
    delta["option_changes"] = option_changes
    delta["comparison_scope"] = _build_delta_comparison_scope(option_changes)
    for key in DELTA_COUNT_KEYS:
        delta["counts"][key] = _safe_count(current.get(key)) - _safe_count(previous.get(key))
    previous_truncated = bool(previous.get("operator_action_truncated"))
    current_truncated = bool(current.get("operator_action_truncated"))
    delta["operator_action_truncated"] = {
        "previous": previous_truncated,
        "current": current_truncated,
        "changed": previous_truncated != current_truncated,
    }
    previous_ready_attention_truncated = bool(previous.get("ready_attention_truncated"))
    current_ready_attention_truncated = bool(current.get("ready_attention_truncated"))
    delta["ready_attention_truncated"] = {
        "previous": previous_ready_attention_truncated,
        "current": current_ready_attention_truncated,
        "changed": previous_ready_attention_truncated != current_ready_attention_truncated,
    }
    delta["incident_response"] = _build_incident_response_delta(current, previous)
    rank_changes = _build_operator_action_rank_changes(current, previous)
    delta["operator_action_rank_change_count"] = len(rank_changes)
    delta["operator_action_rank_changes"] = rank_changes

    current_status_counts = current.get("status_counts") if isinstance(current.get("status_counts"), dict) else {}
    previous_status_counts = previous.get("status_counts") if isinstance(previous.get("status_counts"), dict) else {}
    status_keys = sorted(set(current_status_counts) | set(previous_status_counts))
    for status in status_keys:
        delta["status_counts"][status] = _safe_count(current_status_counts.get(status)) - _safe_count(
            previous_status_counts.get(status)
        )
    current_action_counts = (
        current.get("operator_action_counts") if isinstance(current.get("operator_action_counts"), dict) else {}
    )
    previous_action_counts = (
        previous.get("operator_action_counts") if isinstance(previous.get("operator_action_counts"), dict) else {}
    )
    action_keys = sorted(set(current_action_counts) | set(previous_action_counts))
    delta["operator_action_counts"] = {
        action_name: _safe_count(current_action_counts.get(action_name))
        - _safe_count(previous_action_counts.get(action_name))
        for action_name in action_keys
    }
    current_error_counts = (
        current.get("blocked_error_counts") if isinstance(current.get("blocked_error_counts"), dict) else {}
    )
    previous_error_counts = (
        previous.get("blocked_error_counts") if isinstance(previous.get("blocked_error_counts"), dict) else {}
    )
    error_keys = sorted(set(current_error_counts) | set(previous_error_counts))
    delta["blocked_error_counts"] = {
        bucket: _safe_count(current_error_counts.get(bucket)) - _safe_count(previous_error_counts.get(bucket))
        for bucket in error_keys
    }
    current_needs_edit_reasons = (
        current.get("needs_edit_reason_counts") if isinstance(current.get("needs_edit_reason_counts"), dict) else {}
    )
    previous_needs_edit_reasons = (
        previous.get("needs_edit_reason_counts") if isinstance(previous.get("needs_edit_reason_counts"), dict) else {}
    )
    needs_edit_reason_keys = sorted(set(current_needs_edit_reasons) | set(previous_needs_edit_reasons))
    delta["needs_edit_reason_counts"] = {
        bucket: _safe_count(current_needs_edit_reasons.get(bucket))
        - _safe_count(previous_needs_edit_reasons.get(bucket))
        for bucket in needs_edit_reason_keys
    }
    current_missing_status_counts = (
        current.get("missing_status_counts") if isinstance(current.get("missing_status_counts"), dict) else {}
    )
    previous_missing_status_counts = (
        previous.get("missing_status_counts") if isinstance(previous.get("missing_status_counts"), dict) else {}
    )
    missing_status_keys = sorted(set(current_missing_status_counts) | set(previous_missing_status_counts))
    delta["missing_status_counts"] = {
        bucket: _safe_count(current_missing_status_counts.get(bucket))
        - _safe_count(previous_missing_status_counts.get(bucket))
        for bucket in missing_status_keys
    }
    current_ready_age = current.get("ready_age_buckets") if isinstance(current.get("ready_age_buckets"), dict) else {}
    previous_ready_age = (
        previous.get("ready_age_buckets") if isinstance(previous.get("ready_age_buckets"), dict) else {}
    )
    ready_age_keys = sorted(set(current_ready_age) | set(previous_ready_age))
    delta["ready_age_buckets"] = {
        bucket: _safe_count(current_ready_age.get(bucket)) - _safe_count(previous_ready_age.get(bucket))
        for bucket in ready_age_keys
    }
    ready_attention_rank_changes = _build_ready_attention_rank_changes(current, previous)
    delta["ready_attention_rank_change_count"] = len(ready_attention_rank_changes)
    delta["ready_attention_rank_changes"] = ready_attention_rank_changes
    return delta


def evaluate_review_queue_severity(report: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    severity = SEVERITY_OK

    def raise_to(next_severity: str, reason: str) -> None:
        nonlocal severity
        if SEVERITY_ORDER[next_severity] > SEVERITY_ORDER[severity]:
            severity = next_severity
        reasons.append(reason)

    if _safe_count(report.get("blocked_count")) > 0:
        raise_to(SEVERITY_CRITICAL, f"blocked_count={report.get('blocked_count')}")
    if _safe_count(report.get("stale_ready_count")) > 0:
        raise_to(SEVERITY_WARNING, f"stale_ready_count={report.get('stale_ready_count')}")
    if _safe_count(report.get("scheduled_due_count")) > 0:
        raise_to(SEVERITY_WARNING, f"scheduled_due_count={report.get('scheduled_due_count')}")
    if _safe_count(report.get("needs_edit_count")) > 0:
        raise_to(SEVERITY_WARNING, f"needs_edit_count={report.get('needs_edit_count')}")
    if _safe_count(report.get("missing_status_count")) > 0:
        raise_to(SEVERITY_WARNING, f"missing_status_count={report.get('missing_status_count')}")
    ready_age_buckets = report.get("ready_age_buckets") if isinstance(report.get("ready_age_buckets"), dict) else {}
    ready_8_plus_count = _safe_count(ready_age_buckets.get("8_plus_days"))
    if ready_8_plus_count > 0:
        raise_to(SEVERITY_WARNING, f"ready_8_plus_count={ready_8_plus_count}")
    ready_missing_date_count = _safe_count(report.get("ready_missing_date_count"))
    if ready_missing_date_count > 0:
        raise_to(SEVERITY_WARNING, f"ready_missing_date_count={ready_missing_date_count}")

    delta = report.get("delta") if isinstance(report.get("delta"), dict) else {}
    delta_counts = delta.get("counts") if isinstance(delta.get("counts"), dict) else {}
    if delta.get("has_previous"):
        if _safe_count(delta_counts.get("blocked_count")) > 0:
            raise_to(SEVERITY_CRITICAL, f"blocked_delta=+{delta_counts.get('blocked_count')}")
        if _safe_count(delta_counts.get("stale_ready_count")) > 0:
            raise_to(SEVERITY_WARNING, f"stale_ready_delta=+{delta_counts.get('stale_ready_count')}")
        if _safe_count(delta_counts.get("operator_action_count")) > 0:
            raise_to(SEVERITY_WARNING, f"operator_action_delta=+{delta_counts.get('operator_action_count')}")
        delta_ready_age = delta.get("ready_age_buckets") if isinstance(delta.get("ready_age_buckets"), dict) else {}
        ready_8_plus_delta = _safe_count(delta_ready_age.get("8_plus_days"))
        if ready_8_plus_delta > 0:
            raise_to(SEVERITY_WARNING, f"ready_8_plus_delta=+{ready_8_plus_delta}")

    return severity, reasons


def exit_code_for_review_queue_report(report: dict[str, Any], *, fail_on_warning: bool = False) -> int:
    if not fail_on_warning:
        return 0
    severity = str(report.get("severity") or SEVERITY_OK)
    if severity == SEVERITY_CRITICAL:
        return 2
    if severity == SEVERITY_WARNING:
        return 1
    return 0


def build_review_queue_exit_codes(report: dict[str, Any]) -> dict[str, int]:
    return {
        "default": exit_code_for_review_queue_report(report, fail_on_warning=False),
        "fail_on_warning": exit_code_for_review_queue_report(report, fail_on_warning=True),
    }


def build_review_queue_summary(report: dict[str, Any]) -> dict[str, Any]:
    severity = str(report.get("severity") or evaluate_review_queue_severity(report)[0])
    priority = _operator_priority(report)
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    delta = report.get("delta") if isinstance(report.get("delta"), dict) else {}
    oldest_ready = report.get("oldest_ready") if isinstance(report.get("oldest_ready"), dict) else {}
    action_counts = (
        report.get("operator_action_counts") if isinstance(report.get("operator_action_counts"), dict) else {}
    )
    blocked_error_counts = (
        report.get("blocked_error_counts") if isinstance(report.get("blocked_error_counts"), dict) else {}
    )
    ready_age_buckets = report.get("ready_age_buckets") if isinstance(report.get("ready_age_buckets"), dict) else {}
    needs_edit_reason_counts = (
        report.get("needs_edit_reason_counts") if isinstance(report.get("needs_edit_reason_counts"), dict) else {}
    )
    missing_status_counts = (
        report.get("missing_status_counts") if isinstance(report.get("missing_status_counts"), dict) else {}
    )
    ready_attention_rank_changes = (
        delta.get("ready_attention_rank_changes") if isinstance(delta.get("ready_attention_rank_changes"), list) else []
    )
    return {
        "severity": severity,
        "total_records": _safe_count(report.get("total_records")),
        "operator_action_count": _safe_count(report.get("operator_action_count")),
        "operator_action_displayed_count": _safe_count(report.get("operator_action_displayed_count")),
        "operator_action_hidden_count": _safe_count(report.get("operator_action_hidden_count")),
        "operator_action_truncated": bool(report.get("operator_action_truncated")),
        "blocked_count": _safe_count(report.get("blocked_count")),
        "stale_ready_count": _safe_count(report.get("stale_ready_count")),
        "scheduled_due_count": _safe_count(report.get("scheduled_due_count")),
        "scheduled_ready_count": _safe_count(report.get("scheduled_ready_count")),
        "needs_edit_count": _safe_count(report.get("needs_edit_count")),
        "missing_status_count": _safe_count(report.get("missing_status_count")),
        "operator_priority_score": priority["score"],
        "operator_priority_label": priority["label"],
        "operator_priority_reasons": priority["reasons"],
        "top_operator_action": _top_count_item(action_counts, OPERATOR_ACTION_ORDER),
        "top_blocked_error_bucket": _top_count_item(blocked_error_counts, BLOCKED_ERROR_BUCKET_ORDER),
        "top_needs_edit_reason_bucket": _top_count_item(
            needs_edit_reason_counts,
            NEEDS_EDIT_REASON_BUCKET_ORDER,
        ),
        "top_missing_status_bucket": _top_count_item(missing_status_counts, MISSING_STATUS_BUCKET_ORDER),
        "top_ready_age_bucket": _top_ready_age_bucket(ready_age_buckets),
        "top_ready_attention_movement": _top_ready_attention_movement(ready_attention_rank_changes),
        "ready_attention_displayed_count": _safe_count(report.get("ready_attention_displayed_count")),
        "ready_attention_total_count": _safe_count(report.get("ready_attention_total_count")),
        "ready_attention_hidden_count": _safe_count(report.get("ready_attention_hidden_count")),
        "ready_attention_truncated": bool(report.get("ready_attention_truncated")),
        "oldest_ready_age_days": oldest_ready.get("age_days"),
        "oldest_ready_target": oldest_ready.get("target_hint") or "",
        "oldest_ready_title": _compact_text(oldest_ready.get("title"), limit=48),
        "has_previous": bool(delta.get("has_previous")),
        "delta_comparable": delta.get("comparable") if delta.get("has_previous") else None,
        "read_only": bool(safety.get("read_only")),
        "notion_writes": bool(safety.get("notion_writes")),
        "x_posts": bool(safety.get("x_posts")),
        "manual_publish_required": bool(safety.get("manual_publish_required")),
    }


def build_incident_response(report: dict[str, Any]) -> dict[str, Any]:
    """Build a single operator-facing incident response summary for dashboards."""
    severity = str(report.get("severity") or evaluate_review_queue_severity(report)[0])
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    exit_codes = report.get("exit_codes") if isinstance(report.get("exit_codes"), dict) else {}
    if not exit_codes:
        exit_codes = build_review_queue_exit_codes({"severity": severity})
    recovery_steps = (
        report.get("operator_recovery_steps") if isinstance(report.get("operator_recovery_steps"), list) else []
    )
    first_step = recovery_steps[0] if recovery_steps and isinstance(recovery_steps[0], dict) else {}
    if first_step:
        next_step = str(first_step.get("next_step") or "").strip()
    elif severity == SEVERITY_OK:
        next_step = "No operator action required; keep the manual Notion review queue monitored."
    elif severity == SEVERITY_CRITICAL:
        next_step = "Resolve blocked Notion review items before any manual reprocess run."
    else:
        next_step = "Triage stale Ready to Post, Needs Edit, or missing-status items in Notion."
    return {
        "severity": severity,
        "operator_action_required": severity != SEVERITY_OK,
        "escalation_required": severity == SEVERITY_CRITICAL,
        "next_step": next_step,
        "action": first_step.get("action") or "",
        "target_hint": first_step.get("target_hint") or "",
        "title": _compact_text(first_step.get("title"), limit=48),
        "reason": _compact_text(first_step.get("reason"), limit=72),
        "triage_bucket": _triage_bucket(first_step),
        "triage_hint": _compact_text(first_step.get("triage_hint") or _triage_hint(first_step), limit=120),
        "error_bucket": first_step.get("error_bucket") or "",
        "reason_bucket": first_step.get("reason_bucket") or "",
        "schedule_state": first_step.get("schedule_state") or "",
        "scheduled_at": first_step.get("scheduled_at") or "",
        "schedule_hint": _schedule_hint(first_step),
        "scheduled_due_count": _safe_count(report.get("scheduled_due_count")),
        "scheduled_ready_count": _safe_count(report.get("scheduled_ready_count")),
        "default_exit_code": _safe_count(exit_codes.get("default")),
        "fail_on_warning_exit_code": _safe_count(exit_codes.get("fail_on_warning")),
        "read_only": bool(safety.get("read_only")),
        "notion_writes": bool(safety.get("notion_writes")),
        "x_posts": bool(safety.get("x_posts")),
        "manual_publish_required": bool(safety.get("manual_publish_required")),
    }


def _format_option_value(value: Any) -> str:
    return "missing" if value is None else str(value)


def _format_delta_option_changes(option_changes: dict[str, Any]) -> str:
    option_names = [name for name in REPORT_OPTION_ORDER if name in option_changes]
    option_names.extend(sorted(name for name in option_changes if name not in option_names))
    parts = []
    for option_name in option_names:
        change = option_changes.get(option_name) if isinstance(option_changes.get(option_name), dict) else {}
        previous = _format_option_value(change.get("previous"))
        current = _format_option_value(change.get("current"))
        parts.append(f"{option_name}={previous}->{current}")
    return ", ".join(parts)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _build_delta_comparison_scope(option_changes: dict[str, Any]) -> dict[str, Any]:
    changed_options = [name for name in REPORT_OPTION_ORDER if name in option_changes]
    changed_options.extend(sorted(name for name in option_changes if name not in changed_options))
    if not changed_options:
        return {
            "same_options": True,
            "changed_options": [],
            "stable_signals": ["all"],
            "config_sensitive_signals": [],
        }

    stable_signals: list[str] = []
    config_sensitive_signals: list[str] = []
    query_scope_changed = any(option_name in QUERY_SCOPE_OPTIONS for option_name in changed_options)
    if query_scope_changed:
        stable_signals.append("safety")
        config_sensitive_signals.extend(
            [
                "record_set",
                "all_count_deltas",
                "all_rank_deltas",
                "incident_response",
            ]
        )
    else:
        stable_signals.extend(
            [
                "status_counts",
                "blocked_error_buckets",
                "needs_edit_reason_buckets",
                "missing_status_buckets",
            ]
        )
        if "stale_days" not in changed_options:
            stable_signals.append("ready_age_buckets")
        if "stale_days" not in changed_options and "action_limit" not in changed_options:
            stable_signals.append("incident_response")

    if "stale_days" in changed_options:
        config_sensitive_signals.extend(
            [
                "stale_ready_count",
                "severity",
                "incident_response",
                "operator_actions",
                "ready_attention_order",
            ]
        )
    if "action_limit" in changed_options:
        config_sensitive_signals.extend(
            [
                "operator_action_display",
                "operator_action_rank",
                "incident_response",
            ]
        )
    if "ready_attention_limit" in changed_options:
        config_sensitive_signals.extend(
            [
                "ready_attention_display",
                "ready_attention_rank",
            ]
        )
    return {
        "same_options": False,
        "changed_options": changed_options,
        "stable_signals": _dedupe_preserve_order(stable_signals),
        "config_sensitive_signals": _dedupe_preserve_order(config_sensitive_signals),
    }


def _incident_response_for_delta(report: dict[str, Any]) -> dict[str, Any]:
    incident = report.get("incident_response") if isinstance(report.get("incident_response"), dict) else {}
    return incident if incident else build_incident_response(report)


def _build_incident_response_delta(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    current_incident = _incident_response_for_delta(current)
    previous_incident = _incident_response_for_delta(previous)
    previous_exit = _safe_count(previous_incident.get("fail_on_warning_exit_code"))
    current_exit = _safe_count(current_incident.get("fail_on_warning_exit_code"))
    previous_severity = str(previous_incident.get("severity") or SEVERITY_OK)
    current_severity = str(current_incident.get("severity") or SEVERITY_OK)
    previous_action = str(previous_incident.get("action") or "")
    current_action = str(current_incident.get("action") or "")
    previous_target = str(previous_incident.get("target_hint") or "")
    current_target = str(current_incident.get("target_hint") or "")
    previous_triage = str(previous_incident.get("triage_bucket") or _triage_bucket(previous_incident))
    current_triage = str(current_incident.get("triage_bucket") or _triage_bucket(current_incident))
    previous_schedule = str(previous_incident.get("schedule_hint") or _schedule_hint(previous_incident))
    current_schedule = str(current_incident.get("schedule_hint") or _schedule_hint(current_incident))
    return {
        "previous_severity": previous_severity,
        "current_severity": current_severity,
        "severity_changed": previous_severity != current_severity,
        "previous_action": previous_action,
        "current_action": current_action,
        "action_changed": previous_action != current_action,
        "previous_target_hint": previous_target,
        "current_target_hint": current_target,
        "target_changed": previous_target != current_target,
        "previous_triage_bucket": previous_triage,
        "current_triage_bucket": current_triage,
        "triage_changed": previous_triage != current_triage,
        "previous_schedule_hint": previous_schedule,
        "current_schedule_hint": current_schedule,
        "schedule_changed": previous_schedule != current_schedule,
        "previous_fail_on_warning_exit_code": previous_exit,
        "current_fail_on_warning_exit_code": current_exit,
        "fail_on_warning_exit_code_delta": current_exit - previous_exit,
        "previous_operator_action_required": bool(previous_incident.get("operator_action_required")),
        "current_operator_action_required": bool(current_incident.get("operator_action_required")),
        "previous_escalation_required": bool(previous_incident.get("escalation_required")),
        "current_escalation_required": bool(current_incident.get("escalation_required")),
    }


def load_review_queue_report_artifact(output_path: Path | str | None) -> dict[str, Any] | None:
    if not output_path:
        return None
    path = Path(output_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read previous review queue report artifact %s: %s", path, exc)
        return None
    return payload if isinstance(payload, dict) else None


def write_review_queue_report_artifact(report: dict[str, Any], output_path: Path | str | None) -> Path | None:
    if not output_path:
        return None
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)
    return path


def format_review_queue_report(report: dict[str, Any]) -> str:
    counts = report.get("status_counts", {})
    severity = report.get("severity")
    severity_reasons = report.get("severity_reasons") if isinstance(report.get("severity_reasons"), list) else []
    if not severity:
        severity, severity_reasons = evaluate_review_queue_severity(report)
    lines = [
        "Blind-to-X review queue report (read-only)",
        f"total_records: {report.get('total_records', 0)}",
        f"severity: {severity}",
        "status_counts: "
        + ", ".join(f"{status}={counts.get(status, 0)}" for status in STATUS_ORDER if status in counts),
        (
            "actions: "
            f"blocked={report.get('blocked_count', 0)}, "
            f"stale_ready={report.get('stale_ready_count', 0)}, "
            f"scheduled_due={report.get('scheduled_due_count', 0)}, "
            f"scheduled_ready={report.get('scheduled_ready_count', 0)}, "
            f"needs_edit={report.get('needs_edit_count', 0)}, "
            f"missing_status={report.get('missing_status_count', 0)}"
        ),
    ]
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    if summary:
        top_action = summary.get("top_operator_action") if isinstance(summary.get("top_operator_action"), dict) else {}
        top_blocked_error = (
            summary.get("top_blocked_error_bucket") if isinstance(summary.get("top_blocked_error_bucket"), dict) else {}
        )
        top_needs_edit = (
            summary.get("top_needs_edit_reason_bucket")
            if isinstance(summary.get("top_needs_edit_reason_bucket"), dict)
            else {}
        )
        top_missing = (
            summary.get("top_missing_status_bucket")
            if isinstance(summary.get("top_missing_status_bucket"), dict)
            else {}
        )
        comparable = summary.get("delta_comparable")
        comparable_label = "none" if comparable is None else str(bool(comparable)).lower()
        top_ready_age = (
            summary.get("top_ready_age_bucket") if isinstance(summary.get("top_ready_age_bucket"), dict) else {}
        )
        top_ready_age_name = str(top_ready_age.get("name") or "")
        ready_age_suffix = ""
        if top_ready_age_name:
            oldest_age = summary.get("oldest_ready_age_days")
            oldest_age_label = f"{oldest_age}d" if oldest_age is not None else "no_date"
            oldest_target = summary.get("oldest_ready_target") or "none"
            ready_age_suffix = (
                f"top_ready_age={top_ready_age_name}({top_ready_age.get('count', 0)}), "
                f"oldest_ready={oldest_target}@{oldest_age_label}, "
            )
        top_ready_movement = (
            summary.get("top_ready_attention_movement")
            if isinstance(summary.get("top_ready_attention_movement"), dict)
            else {}
        )
        ready_movement_target = (
            top_ready_movement.get("target_hint") or top_ready_movement.get("ready_attention_key") or ""
        )
        ready_movement_suffix = ""
        if ready_movement_target:
            ready_movement_suffix = (
                f", top_ready_move={ready_movement_target} "
                f"{top_ready_movement.get('previous_rank')}->{top_ready_movement.get('current_rank')}"
                f"({top_ready_movement.get('direction') or 'same'}, "
                f"age_days={top_ready_movement.get('previous_age_days')}"
                f"->{top_ready_movement.get('current_age_days')})"
            )
        top_blocked_error_suffix = ""
        if _safe_count(top_blocked_error.get("count")):
            top_blocked_error_suffix = (
                f"top_blocked_error={top_blocked_error.get('name') or 'none'}({top_blocked_error.get('count', 0)}), "
            )
        lines.append(
            "summary: "
            f"priority={summary.get('operator_priority_score', 0)}"
            f"/{summary.get('operator_priority_label') or 'clear'}, "
            f"top_action={top_action.get('name') or 'none'}({top_action.get('count', 0)}), "
            f"top_needs_edit={top_needs_edit.get('name') or 'none'}({top_needs_edit.get('count', 0)}), "
            f"top_missing={top_missing.get('name') or 'none'}({top_missing.get('count', 0)}), "
            f"{top_blocked_error_suffix}"
            f"{ready_age_suffix}"
            f"delta_comparable={comparable_label}"
            f"{ready_movement_suffix}"
        )
    if severity_reasons:
        lines.append("severity_reasons: " + ", ".join(str(reason) for reason in severity_reasons))
    incident = report.get("incident_response") if isinstance(report.get("incident_response"), dict) else {}
    if incident:
        incident_schedule_hint = incident.get("schedule_hint") or _schedule_hint(incident)
        incident_schedule_suffix = f"{incident_schedule_hint} | " if incident_schedule_hint else ""
        incident_triage = incident.get("triage_bucket") or _triage_bucket(incident)
        incident_triage_suffix = f"triage={incident_triage} | " if incident_triage else ""
        incident_triage_hint = _compact_text(incident.get("triage_hint") or _triage_hint(incident), limit=88)
        incident_triage_hint_suffix = f"triage_hint={incident_triage_hint} | " if incident_triage_hint else ""
        lines.append(
            "incident_response: "
            f"{incident.get('severity') or severity} | "
            f"action_required={str(bool(incident.get('operator_action_required'))).lower()} | "
            f"next_step={incident.get('next_step') or 'none'} | "
            f"target={incident.get('target_hint') or 'none'} | "
            f"{incident_triage_suffix}"
            f"{incident_triage_hint_suffix}"
            f"{incident_schedule_suffix}"
            f"exit_if_enforced={incident.get('fail_on_warning_exit_code', 0)} | "
            f"guard={'manual_publish_required' if incident.get('manual_publish_required') else 'none'}"
        )
    delta = report.get("delta") if isinstance(report.get("delta"), dict) else {}
    incident_delta = delta.get("incident_response") if isinstance(delta.get("incident_response"), dict) else {}
    if delta.get("has_previous") and incident_delta:
        lines.append(
            "incident_delta: "
            f"severity={incident_delta.get('previous_severity')}->{incident_delta.get('current_severity')}, "
            f"action={incident_delta.get('previous_action') or 'none'}"
            f"->{incident_delta.get('current_action') or 'none'}, "
            f"target={incident_delta.get('previous_target_hint') or 'none'}"
            f"->{incident_delta.get('current_target_hint') or 'none'}, "
            f"triage={incident_delta.get('previous_triage_bucket') or 'none'}"
            f"->{incident_delta.get('current_triage_bucket') or 'none'}, "
            f"schedule={incident_delta.get('previous_schedule_hint') or 'none'}"
            f"->{incident_delta.get('current_schedule_hint') or 'none'}, "
            f"exit_if_enforced={incident_delta.get('previous_fail_on_warning_exit_code', 0)}"
            f"->{incident_delta.get('current_fail_on_warning_exit_code', 0)}, "
            f"escalation={str(bool(incident_delta.get('previous_escalation_required'))).lower()}"
            f"->{str(bool(incident_delta.get('current_escalation_required'))).lower()}"
        )
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    if safety:
        lines.append(
            "safety: "
            f"read_only={str(bool(safety.get('read_only'))).lower()}, "
            f"notion_writes={str(bool(safety.get('notion_writes'))).lower()}, "
            f"x_posts={str(bool(safety.get('x_posts'))).lower()}, "
            f"manual_publish_required={str(bool(safety.get('manual_publish_required'))).lower()}"
        )
    exit_codes = report.get("exit_codes") if isinstance(report.get("exit_codes"), dict) else {}
    if not exit_codes:
        exit_codes = build_review_queue_exit_codes({"severity": severity})
    lines.append(
        f"exit_codes: default={exit_codes.get('default', 0)}, fail_on_warning={exit_codes.get('fail_on_warning', 0)}"
    )
    report_options = report.get("report_options") if isinstance(report.get("report_options"), dict) else {}
    if report_options:
        lines.append(
            "options: "
            + ", ".join(
                f"{option_name}={report_options.get(option_name)}"
                for option_name in REPORT_OPTION_ORDER
                if option_name in report_options
            )
        )
    next_commands = (
        report.get("operator_next_commands") if isinstance(report.get("operator_next_commands"), list) else []
    )
    for index, command in enumerate(next_commands, start=1):
        if not isinstance(command, dict):
            continue
        command_text = str(command.get("command") or "").strip()
        purpose = _compact_text(command.get("purpose"), limit=120)
        purpose_text = f"purpose={purpose} | " if purpose else ""
        lines.append(
            f"next_command {index} [{command.get('name')}]: {command_text} | "
            f"{purpose_text}"
            f"read_only={str(bool(command.get('read_only'))).lower()}, "
            f"notion_writes={str(bool(command.get('notion_writes'))).lower()}, "
            f"x_posts={str(bool(command.get('x_posts'))).lower()}, "
            f"publish_command={str(bool(command.get('publish_command'))).lower()}, "
            f"manual_publish_required={str(bool(command.get('manual_publish_required'))).lower()}"
        )
    if delta.get("has_previous"):
        delta_counts = delta.get("counts", {})
        lines.append(
            "delta: "
            f"blocked={delta_counts.get('blocked_count', 0):+}, "
            f"stale_ready={delta_counts.get('stale_ready_count', 0):+}, "
            f"scheduled_due={delta_counts.get('scheduled_due_count', 0):+}, "
            f"scheduled_ready={delta_counts.get('scheduled_ready_count', 0):+}, "
            f"ready={delta_counts.get('ready_to_post_count', 0):+}, "
            f"published={delta_counts.get('published_count', 0):+}, "
            f"actions={delta_counts.get('operator_action_count', 0):+}"
        )
        lines.append(
            "ready_schedule_delta: "
            f"scheduled_due={delta_counts.get('scheduled_due_count', 0):+}, "
            f"scheduled_ready={delta_counts.get('scheduled_ready_count', 0):+}"
        )
        truncated_delta = (
            delta.get("operator_action_truncated") if isinstance(delta.get("operator_action_truncated"), dict) else {}
        )
        if truncated_delta:
            lines.append(
                "action_display_delta: "
                f"displayed={delta_counts.get('operator_action_displayed_count', 0):+}, "
                f"hidden={delta_counts.get('operator_action_hidden_count', 0):+}, "
                f"truncated={str(bool(truncated_delta.get('previous'))).lower()}"
                f"->{str(bool(truncated_delta.get('current'))).lower()}"
            )
        rank_changes = (
            delta.get("operator_action_rank_changes")
            if isinstance(delta.get("operator_action_rank_changes"), list)
            else []
        )
        if rank_changes:
            rank_parts = []
            for change in rank_changes[:3]:
                if not isinstance(change, dict):
                    continue
                direction = str(change.get("direction") or "same")
                movement = abs(_safe_count(change.get("rank_delta")))
                target = change.get("target_hint") or change.get("operator_action_key") or ""
                previous_action = str(change.get("previous_action") or "")
                current_action = str(change.get("current_action") or "")
                action_suffix = (
                    f", action={previous_action}->{current_action}" if previous_action != current_action else ""
                )
                rank_parts.append(
                    f"{target} {change.get('previous_rank')}->{change.get('current_rank')} "
                    f"({direction} {movement}{action_suffix})"
                )
            if rank_parts:
                lines.append("action_rank_delta: " + "; ".join(rank_parts))
        option_changes = delta.get("option_changes") if isinstance(delta.get("option_changes"), dict) else {}
        if option_changes:
            lines.append("delta_options: changed " + _format_delta_option_changes(option_changes))
        comparison_scope = delta.get("comparison_scope") if isinstance(delta.get("comparison_scope"), dict) else {}
        if comparison_scope:
            changed_options = comparison_scope.get("changed_options")
            stable_signals = comparison_scope.get("stable_signals")
            config_sensitive = comparison_scope.get("config_sensitive_signals")
            changed_option_list = changed_options if isinstance(changed_options, list) else []
            stable_signal_list = stable_signals if isinstance(stable_signals, list) else []
            config_sensitive_list = config_sensitive if isinstance(config_sensitive, list) else []
            same_options = bool(comparison_scope.get("same_options"))
            stable_count = "all" if same_options else str(len(stable_signal_list))
            lines.append(
                "delta_scope: "
                f"comparable={str(same_options).lower()}, "
                f"changed_options={', '.join(changed_option_list) if changed_option_list else 'none'}, "
                f"stable_signals={stable_count}, "
                f"config_sensitive_signals={len(config_sensitive_list)}"
            )
            if not same_options:
                lines.append(
                    "delta_scope_detail: "
                    f"stable={', '.join(stable_signal_list) if stable_signal_list else 'none'} | "
                    "config_sensitive="
                    f"{', '.join(config_sensitive_list) if config_sensitive_list else 'none'}"
                )
    else:
        lines.append("delta: no_previous_artifact")
    action_counts = (
        report.get("operator_action_counts") if isinstance(report.get("operator_action_counts"), dict) else {}
    )
    if action_counts:
        lines.append(
            "action_counts: "
            + ", ".join(
                f"{action_name}={action_counts.get(action_name, 0)}"
                for action_name in OPERATOR_ACTION_ORDER
                if action_name in action_counts
            )
        )
    total_actions = _safe_count(report.get("operator_action_count"))
    if total_actions:
        displayed_actions = _safe_count(report.get("operator_action_displayed_count"))
        hidden_actions = _safe_count(report.get("operator_action_hidden_count"))
        truncated = bool(report.get("operator_action_truncated"))
        rerun_hint = f", rerun_with=--review-queue-action-limit {total_actions}" if truncated else ""
        lines.append(
            "action_display: "
            f"displayed={displayed_actions}, total={total_actions}, hidden={hidden_actions}, "
            f"truncated={str(truncated).lower()}{rerun_hint}"
        )
    delta_action_counts = (
        delta.get("operator_action_counts") if isinstance(delta.get("operator_action_counts"), dict) else {}
    )
    if delta.get("has_previous") and delta_action_counts:
        lines.append(
            "action_delta: "
            + ", ".join(
                f"{action_name}={delta_action_counts.get(action_name, 0):+}"
                for action_name in OPERATOR_ACTION_ORDER
                if action_name in delta_action_counts
            )
        )
    blocked_error_counts = (
        report.get("blocked_error_counts") if isinstance(report.get("blocked_error_counts"), dict) else {}
    )
    if any(_safe_count(blocked_error_counts.get(bucket)) for bucket in blocked_error_counts):
        lines.append(
            "blocked_error_buckets: "
            + ", ".join(
                f"{bucket}={blocked_error_counts.get(bucket, 0)}"
                for bucket in BLOCKED_ERROR_BUCKET_ORDER
                if bucket in blocked_error_counts
            )
        )
        blocked_error_examples = (
            report.get("blocked_error_examples") if isinstance(report.get("blocked_error_examples"), dict) else {}
        )
        blocked_error_hints = (
            report.get("blocked_error_recovery_hints")
            if isinstance(report.get("blocked_error_recovery_hints"), dict)
            else BLOCKED_ERROR_RECOVERY_HINTS
        )
        recovery_parts = []
        for bucket in _ordered_nonzero_blocked_error_buckets(blocked_error_counts)[:3]:
            example = _compact_text(blocked_error_examples.get(bucket), limit=56)
            hint = _compact_text(blocked_error_hints.get(bucket), limit=104)
            recovery_parts.append(f"{bucket}={blocked_error_counts.get(bucket)} | {example} | {hint}")
        if recovery_parts:
            lines.append("blocked_error_recovery: " + "; ".join(recovery_parts))
    delta_error_counts = (
        delta.get("blocked_error_counts") if isinstance(delta.get("blocked_error_counts"), dict) else {}
    )
    if delta.get("has_previous") and delta_error_counts:
        lines.append(
            "blocked_error_delta: "
            + ", ".join(
                f"{bucket}={delta_error_counts.get(bucket, 0):+}"
                for bucket in BLOCKED_ERROR_BUCKET_ORDER
                if bucket in delta_error_counts
            )
        )
    needs_edit_reason_counts = (
        report.get("needs_edit_reason_counts") if isinstance(report.get("needs_edit_reason_counts"), dict) else {}
    )
    if any(_safe_count(needs_edit_reason_counts.get(bucket)) for bucket in needs_edit_reason_counts):
        lines.append(
            "needs_edit_reason_buckets: "
            + ", ".join(
                f"{bucket}={needs_edit_reason_counts.get(bucket, 0)}"
                for bucket in NEEDS_EDIT_REASON_BUCKET_ORDER
                if bucket in needs_edit_reason_counts
            )
        )
        needs_edit_reason_examples = (
            report.get("needs_edit_reason_examples")
            if isinstance(report.get("needs_edit_reason_examples"), dict)
            else {}
        )
        needs_edit_reason_hints = (
            report.get("needs_edit_reason_recovery_hints")
            if isinstance(report.get("needs_edit_reason_recovery_hints"), dict)
            else NEEDS_EDIT_REASON_RECOVERY_HINTS
        )
        recovery_parts = []
        for bucket in _ordered_nonzero_needs_edit_reason_buckets(needs_edit_reason_counts)[:3]:
            example = _compact_text(needs_edit_reason_examples.get(bucket), limit=56)
            hint = _compact_text(needs_edit_reason_hints.get(bucket), limit=104)
            recovery_parts.append(f"{bucket}={needs_edit_reason_counts.get(bucket)} | {example} | {hint}")
        if recovery_parts:
            lines.append("needs_edit_reason_recovery: " + "; ".join(recovery_parts))
    delta_needs_edit_reason_counts = (
        delta.get("needs_edit_reason_counts") if isinstance(delta.get("needs_edit_reason_counts"), dict) else {}
    )
    if delta.get("has_previous") and delta_needs_edit_reason_counts:
        lines.append(
            "needs_edit_reason_delta: "
            + ", ".join(
                f"{bucket}={delta_needs_edit_reason_counts.get(bucket, 0):+}"
                for bucket in NEEDS_EDIT_REASON_BUCKET_ORDER
                if bucket in delta_needs_edit_reason_counts
            )
        )
    missing_status_counts = (
        report.get("missing_status_counts") if isinstance(report.get("missing_status_counts"), dict) else {}
    )
    if any(_safe_count(missing_status_counts.get(bucket)) for bucket in missing_status_counts):
        lines.append(
            "missing_status_buckets: "
            + ", ".join(
                f"{bucket}={missing_status_counts.get(bucket, 0)}"
                for bucket in MISSING_STATUS_BUCKET_ORDER
                if bucket in missing_status_counts
            )
        )
        missing_status_examples = (
            report.get("missing_status_examples") if isinstance(report.get("missing_status_examples"), dict) else {}
        )
        missing_status_hints = (
            report.get("missing_status_recovery_hints")
            if isinstance(report.get("missing_status_recovery_hints"), dict)
            else MISSING_STATUS_RECOVERY_HINTS
        )
        recovery_parts = []
        for bucket in _ordered_nonzero_missing_status_buckets(missing_status_counts)[:3]:
            example = _compact_text(missing_status_examples.get(bucket), limit=56)
            hint = _compact_text(missing_status_hints.get(bucket), limit=104)
            recovery_parts.append(f"{bucket}={missing_status_counts.get(bucket)} | {example} | {hint}")
        if recovery_parts:
            lines.append("missing_status_recovery: " + "; ".join(recovery_parts))
    delta_missing_status_counts = (
        delta.get("missing_status_counts") if isinstance(delta.get("missing_status_counts"), dict) else {}
    )
    if delta.get("has_previous") and delta_missing_status_counts:
        lines.append(
            "missing_status_delta: "
            + ", ".join(
                f"{bucket}={delta_missing_status_counts.get(bucket, 0):+}"
                for bucket in MISSING_STATUS_BUCKET_ORDER
                if bucket in delta_missing_status_counts
            )
        )
    ready_age_buckets = report.get("ready_age_buckets") if isinstance(report.get("ready_age_buckets"), dict) else {}
    if any(_safe_count(ready_age_buckets.get(bucket)) for bucket in ready_age_buckets):
        oldest_ready = report.get("oldest_ready") if isinstance(report.get("oldest_ready"), dict) else {}
        oldest_age = oldest_ready.get("age_days")
        oldest_target = oldest_ready.get("target_hint") or "none"
        lines.append(
            "ready_age: "
            + ", ".join(
                f"{bucket}={ready_age_buckets.get(bucket, 0)}"
                for bucket in READY_AGE_BUCKET_ORDER
                if bucket in ready_age_buckets
            )
            + f" | oldest_age_days={oldest_age if oldest_age is not None else 'no_date'}"
            + f" | oldest_target={oldest_target}"
        )
    ready_attention_items = (
        report.get("ready_attention_items") if isinstance(report.get("ready_attention_items"), list) else []
    )
    if ready_attention_items:
        ready_attention_limit = report_options.get("ready_attention_limit", READY_ATTENTION_LIMIT)
        displayed_attention = _safe_count(report.get("ready_attention_displayed_count") or len(ready_attention_items))
        total_attention = _safe_count(report.get("ready_attention_total_count") or len(ready_attention_items))
        hidden_attention = _safe_count(report.get("ready_attention_hidden_count"))
        attention_truncated = bool(report.get("ready_attention_truncated"))
        rerun_hint = (
            f", rerun_with=--review-queue-ready-attention-limit {total_attention}" if attention_truncated else ""
        )
        attention_parts = []
        for index, item in enumerate(ready_attention_items, start=1):
            rank = item.get("ready_attention_rank") or index
            age_days = item.get("age_days")
            age_label = age_days if age_days is not None else "no_date"
            schedule_hint = _schedule_hint(item)
            schedule_suffix = f" | {schedule_hint}" if schedule_hint else ""
            title = _compact_text(item.get("title"), limit=48) or "untitled"
            target_hint = item.get("target_hint") or "none"
            attention_parts.append(f"{rank}) age_days={age_label}{schedule_suffix} | {title} | {target_hint}")
        lines.append(
            "ready_attention: "
            f"displayed={displayed_attention}, total={total_attention}, hidden={hidden_attention}, "
            f"limit={ready_attention_limit}, truncated={str(attention_truncated).lower()}{rerun_hint} | "
            + "; ".join(attention_parts)
        )
    ready_attention_truncated_delta = (
        delta.get("ready_attention_truncated") if isinstance(delta.get("ready_attention_truncated"), dict) else {}
    )
    delta_counts = delta.get("counts") if isinstance(delta.get("counts"), dict) else {}
    if delta.get("has_previous") and ready_attention_truncated_delta:
        lines.append(
            "ready_attention_display_delta: "
            f"displayed={delta_counts.get('ready_attention_displayed_count', 0):+}, "
            f"total={delta_counts.get('ready_attention_total_count', 0):+}, "
            f"hidden={delta_counts.get('ready_attention_hidden_count', 0):+}, "
            f"truncated={str(bool(ready_attention_truncated_delta.get('previous'))).lower()}"
            f"->{str(bool(ready_attention_truncated_delta.get('current'))).lower()}"
        )
    delta_ready_age = delta.get("ready_age_buckets") if isinstance(delta.get("ready_age_buckets"), dict) else {}
    if delta.get("has_previous") and delta_ready_age:
        lines.append(
            "ready_age_delta: "
            + ", ".join(
                f"{bucket}={delta_ready_age.get(bucket, 0):+}"
                for bucket in READY_AGE_BUCKET_ORDER
                if bucket in delta_ready_age
            )
        )
    ready_attention_rank_changes = (
        delta.get("ready_attention_rank_changes") if isinstance(delta.get("ready_attention_rank_changes"), list) else []
    )
    if delta.get("has_previous") and ready_attention_rank_changes:
        attention_delta_parts = []
        for change in ready_attention_rank_changes[:3]:
            if not isinstance(change, dict):
                continue
            direction = str(change.get("direction") or "same")
            movement = abs(_safe_count(change.get("rank_delta")))
            target = change.get("target_hint") or change.get("ready_attention_key") or ""
            previous_age = change.get("previous_age_days")
            current_age = change.get("current_age_days")
            attention_delta_parts.append(
                f"{target} {change.get('previous_rank')}->{change.get('current_rank')} "
                f"({direction} {movement}, age_days={previous_age}->{current_age})"
            )
        if attention_delta_parts:
            lines.append("ready_attention_delta: " + "; ".join(attention_delta_parts))
    artifact_path = report.get("artifact_path")
    if artifact_path:
        lines.append(f"artifact: {artifact_path}")
    for index, step in enumerate(report.get("operator_recovery_steps", []), start=1):
        target_hint = step.get("target_hint")
        target_suffix = f" | {target_hint}" if target_hint else ""
        schedule_hint = _schedule_hint(step)
        schedule_suffix = f" | {schedule_hint}" if schedule_hint else ""
        priority = step.get("priority")
        priority_label = step.get("priority_label")
        priority_text = f" [p{priority} {priority_label}]" if priority is not None and priority_label else ""
        lines.append(
            f"recovery {index}{priority_text}: {step.get('next_step')} | "
            f"{step.get('title')}{schedule_suffix}{target_suffix}"
        )
    for index, action in enumerate(report.get("operator_actions", []), start=1):
        action_rank = _safe_count(action.get("operator_action_rank")) or index
        target_hint = action.get("target_hint") or _target_hint(action)
        target_suffix = f" | {target_hint}" if target_hint else ""
        schedule_hint = _schedule_hint(action)
        schedule_suffix = f" | {schedule_hint}" if schedule_hint else ""
        priority = action.get("priority")
        priority_label = action.get("priority_label")
        priority_text = f" [p{priority} {priority_label}]" if priority is not None and priority_label else ""
        lines.append(
            f"{action_rank}.{priority_text} {action.get('action')} | {action.get('x_publish_status')} | "
            f"{action.get('reason')} | {action.get('title')}{schedule_suffix}{target_suffix}"
        )
    return "\n".join(lines)


async def run_review_queue_report(
    notion_uploader,
    *,
    lookback_days: int,
    limit: int,
    stale_days: int,
    action_limit: int = 10,
    ready_attention_limit: int = READY_ATTENTION_LIMIT,
    output_path: Path | str | None = None,
) -> dict:
    """Fetch recent Notion records and summarize X publish review state without writing."""
    lookback_days = _coerce_int(lookback_days, 30, minimum=1)
    limit = _coerce_int(limit, 50, minimum=1)
    stale_days = _coerce_int(stale_days, 3, minimum=0)
    action_limit = _coerce_int(action_limit, 10, minimum=0)
    ready_attention_limit = _coerce_int(ready_attention_limit, READY_ATTENTION_LIMIT, minimum=0)
    records = await notion_uploader.fetch_recent_records(lookback_days=lookback_days, limit=limit)
    report = build_review_queue_report(
        records,
        stale_days=stale_days,
        action_limit=action_limit,
        ready_attention_limit=ready_attention_limit,
    )
    report_options = report.get("report_options") if isinstance(report.get("report_options"), dict) else {}
    report["report_options"] = {
        "lookback_days": lookback_days,
        "limit": limit,
        **report_options,
    }
    previous_report = load_review_queue_report_artifact(output_path)
    report["delta"] = build_review_queue_delta(report, previous_report)
    report["severity"], report["severity_reasons"] = evaluate_review_queue_severity(report)
    report["exit_codes"] = build_review_queue_exit_codes(report)
    report["summary"] = build_review_queue_summary(report)
    report["incident_response"] = build_incident_response(report)
    if output_path:
        report["artifact_path"] = str(Path(output_path))
    report["operator_next_commands"] = build_operator_next_commands(report)
    written_path = write_review_queue_report_artifact(report, output_path)
    if written_path:
        report["artifact_path"] = str(written_path)
        report["operator_next_commands"] = build_operator_next_commands(report)
    logger.info(
        "Review queue report completed. total=%s blocked=%s stale_ready=%s needs_edit=%s",
        report["total_records"],
        report["blocked_count"],
        report["stale_ready_count"],
        report["needs_edit_count"],
    )
    return report
