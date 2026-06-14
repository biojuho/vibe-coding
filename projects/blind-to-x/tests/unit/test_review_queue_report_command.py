import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from pipeline.commands.review_queue_report import (
    SEVERITY_CRITICAL,
    SEVERITY_OK,
    SEVERITY_WARNING,
    STATUS_BLOCKED,
    STATUS_MISSING,
    STATUS_NEEDS_EDIT,
    STATUS_PUBLISHED,
    STATUS_READY,
    build_incident_response,
    build_operator_next_commands,
    build_operator_recovery_steps,
    build_review_queue_delta,
    build_review_queue_exit_codes,
    build_review_queue_report,
    build_review_queue_summary,
    classify_blocked_publish_error,
    evaluate_review_queue_severity,
    exit_code_for_review_queue_report,
    format_review_queue_report,
    normalize_x_publish_status,
    run_review_queue_report,
    write_review_queue_report_artifact,
)


def test_normalize_x_publish_status_handles_common_aliases():
    assert normalize_x_publish_status("Ready to Post") == STATUS_READY
    assert normalize_x_publish_status("ready") == STATUS_READY
    assert normalize_x_publish_status("Published") == STATUS_PUBLISHED
    assert normalize_x_publish_status("failed") == STATUS_BLOCKED
    assert normalize_x_publish_status("Needs Edit") == STATUS_NEEDS_EDIT
    assert normalize_x_publish_status("") == STATUS_MISSING


def test_classify_blocked_publish_error_maps_operator_incident_buckets():
    assert classify_blocked_publish_error("Missing tweet draft text") == "missing_draft"
    assert classify_blocked_publish_error("Twitter post failed") == "x_post_failed"
    assert classify_blocked_publish_error("Notion publish-state update failed after X post") == "notion_sync_failed"
    assert classify_blocked_publish_error("media upload failed") == "media_issue"
    assert classify_blocked_publish_error("Blocked X publish status") == "other"


def test_build_review_queue_report_prioritizes_blocked_and_stale_ready_items():
    records = [
        {
            "page_id": "page-ready-old",
            "title": "Old ready",
            "date": "2026-06-01T00:00:00+00:00",
            "x_publish_status": "Ready to Post",
        },
        {
            "page_id": "page-ready-fresh",
            "title": "Fresh ready",
            "date": "2026-06-08T00:00:00+00:00",
            "x_publish_status": "ready",
        },
        {
            "page_id": "page-blocked",
            "page_url": "https://notion.so/page-blocked",
            "title": "Blocked item",
            "date": "2026-06-07T00:00:00+00:00",
            "x_publish_status": "Blocked",
            "x_publish_error": "Twitter post failed",
        },
        {
            "page_id": "page-edit",
            "title": "Needs edit",
            "x_publish_status": "Needs Edit",
        },
        {
            "page_id": "page-published",
            "title": "Published item",
            "x_publish_status": "Published",
        },
        {
            "page_id": "page-missing",
            "title": "Missing status",
            "x_publish_status": "",
        },
    ]

    report = build_review_queue_report(
        records,
        stale_days=3,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )

    assert report["dry_run"] is True
    assert report["safety"] == {
        "read_only": True,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }
    assert report["report_options"] == {
        "stale_days": 3,
        "action_limit": 10,
        "ready_attention_limit": 3,
    }
    assert report["total_records"] == 6
    assert report["status_counts"][STATUS_READY] == 2
    assert report["status_counts"][STATUS_BLOCKED] == 1
    assert report["status_counts"][STATUS_PUBLISHED] == 1
    assert report["status_counts"][STATUS_NEEDS_EDIT] == 1
    assert report["status_counts"][STATUS_MISSING] == 1
    assert report["stale_ready_count"] == 1
    assert report["operator_action_count"] == 4
    assert report["operator_action_displayed_count"] == 4
    assert report["operator_action_hidden_count"] == 0
    assert report["operator_action_truncated"] is False
    assert report["operator_action_counts"]["fix_blocked_publish"] == 1
    assert report["operator_action_counts"]["publish_or_reschedule"] == 1
    assert report["operator_action_counts"]["fill_x_publish_status"] == 1
    assert report["operator_action_counts"]["review_draft_edits"] == 1
    assert report["ready_age_buckets"]["0_1_days"] == 1
    assert report["ready_age_buckets"]["8_plus_days"] == 1
    assert report["ready_missing_date_count"] == 0
    assert report["oldest_ready"]["age_days"] == 8
    assert report["oldest_ready"]["target_hint"] == "page_id:pageread"
    assert report["oldest_ready"]["title"] == "Old ready"
    assert report["summary"]["top_ready_age_bucket"] == {"name": "8_plus_days", "count": 1}
    assert report["summary"]["scheduled_due_count"] == 0
    assert report["summary"]["scheduled_ready_count"] == 0
    assert report["summary"]["oldest_ready_age_days"] == 8
    assert report["summary"]["oldest_ready_target"] == "page_id:pageread"
    assert report["summary"]["oldest_ready_title"] == "Old ready"
    assert report["ready_attention_count"] == 2
    assert report["ready_attention_displayed_count"] == 2
    assert report["ready_attention_total_count"] == 2
    assert report["ready_attention_hidden_count"] == 0
    assert report["ready_attention_truncated"] is False
    assert [item["title"] for item in report["ready_attention_items"]] == ["Old ready", "Fresh ready"]
    assert report["ready_attention_items"][0]["age_bucket"] == "8_plus_days"
    assert report["ready_attention_items"][0]["target_hint"] == "page_id:pageread"
    assert report["blocked_error_counts"]["x_post_failed"] == 1
    assert report["blocked_error_counts"]["missing_draft"] == 0
    assert report["blocked_error_examples"]["x_post_failed"] == "Twitter post failed"
    assert "Check X credentials" in report["blocked_error_recovery_hints"]["x_post_failed"]
    assert [item["action"] for item in report["operator_actions"]] == [
        "fix_blocked_publish",
        "publish_or_reschedule",
        "review_draft_edits",
        "fill_x_publish_status",
    ]
    assert [item["operator_action_rank"] for item in report["operator_actions"]] == [1, 2, 3, 4]
    assert report["operator_actions"][0]["page_id"] == "page-blocked"
    assert report["operator_actions"][0]["target_hint"] == "https://notion.so/page-blocked"
    assert report["operator_actions"][0]["operator_action_key"] == "page_id:page-blocked"
    assert report["operator_actions"][0]["reason"] == "Twitter post failed"
    assert report["operator_actions"][0]["error_bucket"] == "x_post_failed"
    assert report["operator_actions"][0]["priority"] == 10
    assert report["operator_actions"][0]["priority_label"] == "critical"
    assert report["operator_actions"][1]["priority"] == 30
    assert report["operator_actions"][1]["priority_label"] == "stale_ready"
    assert report["operator_actions"][2]["priority"] == 40
    assert report["operator_actions"][2]["priority_label"] == "needs_edit"
    assert report["operator_actions"][3]["priority"] == 50
    assert report["operator_actions"][3]["priority_label"] == "missing_status"
    assert report["operator_recovery_steps"][0]["action"] == "fix_blocked_publish"
    assert report["operator_recovery_steps"][0]["priority"] == 10
    assert report["operator_recovery_steps"][0]["priority_label"] == "critical"
    assert "--reprocess-approved" in report["operator_recovery_steps"][0]["next_step"]
    assert report["operator_recovery_steps"][0]["target_hint"] == "https://notion.so/page-blocked"
    assert report["incident_response"]["severity"] == SEVERITY_CRITICAL
    assert report["incident_response"]["operator_action_required"] is True
    assert report["incident_response"]["escalation_required"] is True
    assert report["incident_response"]["action"] == "fix_blocked_publish"
    assert report["incident_response"]["target_hint"] == "https://notion.so/page-blocked"
    assert report["incident_response"]["triage_bucket"] == "x_post_failed"
    assert report["incident_response"]["triage_hint"].startswith("Check X credentials")
    assert report["incident_response"]["error_bucket"] == "x_post_failed"
    assert report["incident_response"]["reason_bucket"] == ""
    assert "--reprocess-approved" in report["incident_response"]["next_step"]
    assert report["incident_response"]["read_only"] is True
    assert report["incident_response"]["x_posts"] is False
    assert report["incident_response"]["manual_publish_required"] is True
    next_commands = {command["name"]: command for command in report["operator_next_commands"]}
    assert list(next_commands) == ["refresh_report"]
    assert next_commands["refresh_report"]["read_only"] is True
    assert next_commands["refresh_report"]["x_posts"] is False
    assert next_commands["refresh_report"]["publish_command"] is False
    assert next_commands["refresh_report"]["purpose"] == "Rerun the same read-only review queue report."
    assert "--review-queue-report" in next_commands["refresh_report"]["command"]
    assert "--review-queue-stale-days 3" in next_commands["refresh_report"]["command"]
    assert "--review-queue-action-limit 10" in next_commands["refresh_report"]["command"]
    assert "--reprocess-approved" not in next_commands["refresh_report"]["command"]


def test_format_review_queue_report_is_operator_readable():
    report = build_review_queue_report(
        [
            {
                "page_id": "page-blocked",
                "page_url": "https://notion.so/page-blocked",
                "title": "Blocked item",
                "x_publish_status": "Blocked",
                "x_publish_error": "Missing tweet draft text",
            }
        ]
    )

    text = format_review_queue_report(report)

    assert "Blind-to-X review queue report (read-only)" in text
    assert "severity: critical" in text
    assert "severity_reasons: blocked_count=1" in text
    assert (
        "incident_response: critical | action_required=true | next_step=Open the Notion page, "
        "fix X Publish Error or draft/media issue, then rerun --reprocess-approved. | "
        "target=https://notion.so/page-blocked | triage=missing_draft | "
        "triage_hint=Fill tweet_body or regenerate the draft before rerunning --reprocess-approved. | "
        "exit_if_enforced=2 | guard=manual_publish_required"
    ) in text
    assert "safety: read_only=true, notion_writes=false, x_posts=false, manual_publish_required=true" in text
    assert "exit_codes: default=0, fail_on_warning=2" in text
    assert "options: stale_days=3, action_limit=10, ready_attention_limit=3" in text
    assert "Blocked=1" in text
    assert "delta: no_previous_artifact" in text
    assert "action_counts: fix_blocked_publish=1" in text
    assert "action_display: displayed=1, total=1, hidden=0, truncated=false" in text
    assert "top_blocked_error=missing_draft(1)" in text
    assert "next_command 1 [refresh_report]: python main.py --review-queue-report" in text
    assert "purpose=Rerun the same read-only review queue report." in text
    assert (
        "read_only=true, notion_writes=false, x_posts=false, publish_command=false, manual_publish_required=true"
    ) in text
    assert "ready_age: " not in text
    assert "ready_attention: " not in text
    assert "blocked_error_buckets: missing_draft=1" in text
    assert "blocked_error_recovery: missing_draft=1 | Missing tweet draft text | Fill tweet_body" in text
    assert "recovery 1 [p10 critical]:" in text
    assert "https://notion.so/page-blocked" in text
    assert "--reprocess-approved" in text
    assert "fix_blocked_publish" in text
    assert "Missing tweet draft text" in text
    assert (
        "1. [p10 critical] fix_blocked_publish | Blocked | Missing tweet draft text | "
        "Blocked item | https://notion.so/page-blocked"
    ) in text


def test_format_review_queue_report_parses_string_false_artifact_flags():
    report = {
        "total_records": 0,
        "severity": SEVERITY_OK,
        "operator_action_count": 2,
        "operator_action_displayed_count": 2,
        "operator_action_hidden_count": 0,
        "operator_action_truncated": "false",
        "ready_attention_displayed_count": 1,
        "ready_attention_total_count": 1,
        "ready_attention_hidden_count": 0,
        "ready_attention_truncated": "false",
        "ready_attention_items": [
            {
                "title": "Ready item",
                "target_hint": "page_id:ready",
                "ready_attention_rank": 1,
                "age_days": 0,
            }
        ],
        "incident_response": {
            "severity": SEVERITY_OK,
            "operator_action_required": "false",
            "next_step": "none",
            "target_hint": "none",
            "fail_on_warning_exit_code": 0,
            "manual_publish_required": "false",
        },
        "safety": {
            "read_only": "true",
            "notion_writes": "false",
            "x_posts": "false",
            "manual_publish_required": "false",
        },
        "operator_next_commands": [
            {
                "name": "refresh_report",
                "command": "python main.py --review-queue-report",
                "read_only": "true",
                "notion_writes": "false",
                "x_posts": "false",
                "publish_command": "false",
                "manual_publish_required": "false",
            }
        ],
        "delta": {
            "has_previous": "false",
            "counts": {"operator_action_count": 1},
            "incident_response": {
                "previous_escalation_required": "false",
                "current_escalation_required": "false",
            },
        },
    }

    text = format_review_queue_report(report)

    assert "incident_response: ok | action_required=false" in text
    assert "guard=none" in text
    assert "safety: read_only=true, notion_writes=false, x_posts=false, manual_publish_required=false" in text
    assert (
        "next_command 1 [refresh_report]: python main.py --review-queue-report | "
        "read_only=true, notion_writes=false, x_posts=false, publish_command=false, manual_publish_required=false"
    ) in text
    assert "action_display: displayed=2, total=2, hidden=0, truncated=false" in text
    assert "ready_attention: displayed=1, total=1, hidden=0, limit=3, truncated=false" in text
    assert "delta: no_previous_artifact" in text
    assert "delta: blocked=" not in text
    assert "rerun_with=--review-queue-action-limit" not in text
    assert "rerun_with=--review-queue-ready-attention-limit" not in text
    summary = build_review_queue_summary(report)
    assert summary["has_previous"] is False
    assert summary["delta_comparable"] is None
    assert summary["notion_writes"] is False
    assert summary["x_posts"] is False


def test_operator_actions_sort_by_recovery_priority_before_title():
    report = build_review_queue_report(
        [
            {
                "page_id": "missing-alpha",
                "title": "A missing status",
                "x_publish_status": "",
            },
            {
                "page_id": "needs-edit-zulu",
                "title": "Z needs edit",
                "x_publish_status": "Needs Edit",
            },
        ]
    )

    assert [item["action"] for item in report["operator_actions"]] == [
        "review_draft_edits",
        "fill_x_publish_status",
    ]
    assert [item["priority"] for item in report["operator_actions"]] == [40, 50]
    assert [item["priority_label"] for item in report["operator_actions"]] == ["needs_edit", "missing_status"]
    assert [item["operator_action_rank"] for item in report["operator_actions"]] == [1, 2]


def test_ready_attention_items_prioritize_stale_missing_date_then_fresh_ready_items():
    report = build_review_queue_report(
        [
            {
                "page_id": "fresh-ready",
                "title": "Fresh ready",
                "date": "2026-06-08T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
            {
                "page_id": "missing-date-ready",
                "title": "Missing date ready",
                "x_publish_status": "Ready to Post",
            },
            {
                "page_id": "old-ready",
                "title": "Old ready",
                "date": "2026-06-01T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
            {
                "page_id": "older-ready",
                "title": "Older ready",
                "date": "2026-05-30T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
        ],
        stale_days=3,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )

    assert [item["title"] for item in report["ready_attention_items"]] == [
        "Older ready",
        "Old ready",
        "Missing date ready",
    ]
    assert [item["age_bucket"] for item in report["ready_attention_items"]] == [
        "8_plus_days",
        "8_plus_days",
        "no_date",
    ]
    assert report["ready_attention_items"][0]["age_days"] == 10
    assert report["ready_attention_items"][0]["ready_attention_rank"] == 1
    assert report["ready_attention_items"][0]["ready_attention_key"] == "page_id:older-ready"
    assert report["ready_attention_items"][2]["target_hint"] == "page_id:missingd"
    assert report["ready_attention_items"][2]["ready_attention_rank"] == 3
    assert report["ready_attention_count"] == 3
    assert report["ready_attention_displayed_count"] == 3
    assert report["ready_attention_total_count"] == 4
    assert report["ready_attention_hidden_count"] == 1
    assert report["ready_attention_truncated"] is True


def test_future_scheduled_ready_items_do_not_trigger_manual_publish_attention():
    report = build_review_queue_report(
        [
            {
                "page_id": "scheduled-future",
                "title": "Scheduled future",
                "date": "2026-06-01T00:00:00+00:00",
                "x_scheduled_at": "2026-06-11T09:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
            {
                "page_id": "unscheduled-stale",
                "title": "Unscheduled stale",
                "date": "2026-06-05T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
        ],
        stale_days=3,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )

    assert report["ready_to_post_count"] == 2
    assert report["scheduled_ready_count"] == 1
    assert report["stale_ready_count"] == 1
    assert report["operator_action_count"] == 1
    assert report["operator_actions"][0]["page_id"] == "unscheduled-stale"
    assert report["ready_age_buckets"]["4_7_days"] == 1
    assert report["ready_age_buckets"]["8_plus_days"] == 0
    assert report["ready_attention_total_count"] == 1
    assert [item["page_id"] for item in report["ready_attention_items"]] == ["unscheduled-stale"]
    severity, reasons = evaluate_review_queue_severity(report)
    assert severity == SEVERITY_WARNING
    assert reasons == ["stale_ready_count=1"]
    text = format_review_queue_report(report)
    assert (
        "actions: blocked=0, stale_ready=1, scheduled_due=0, scheduled_ready=1, needs_edit=0, missing_status=0"
    ) in text
    assert "Scheduled future" not in text


def test_due_scheduled_ready_items_trigger_operator_attention_immediately():
    scheduled_at = "2026-06-08T09:00:00+00:00"
    report = build_review_queue_report(
        [
            {
                "page_id": "scheduled-due",
                "title": "Scheduled due",
                "date": "2026-06-01T00:00:00+00:00",
                "x_scheduled_at": scheduled_at,
                "x_publish_status": "Ready to Post",
            }
        ],
        stale_days=3,
        now=datetime(2026, 6, 9, 10, tzinfo=UTC),
    )

    assert report["scheduled_due_count"] == 1
    assert report["scheduled_ready_count"] == 0
    assert report["stale_ready_count"] == 0
    assert report["operator_action_count"] == 1
    assert report["operator_actions"][0]["reason"] == "Ready scheduled time passed 1 days ago"
    assert report["operator_actions"][0]["schedule_state"] == "scheduled_due"
    assert report["operator_actions"][0]["scheduled_at"] == scheduled_at
    assert report["ready_age_buckets"]["0_1_days"] == 1
    assert report["ready_age_buckets"]["8_plus_days"] == 0
    assert report["ready_attention_items"][0]["age_days"] == 1
    assert report["ready_attention_items"][0]["schedule_state"] == "scheduled_due"
    assert report["ready_attention_items"][0]["scheduled_at"] == scheduled_at
    assert report["operator_recovery_steps"][0]["schedule_state"] == "scheduled_due"
    assert report["operator_recovery_steps"][0]["scheduled_at"] == scheduled_at
    severity, reasons = evaluate_review_queue_severity(report)
    assert severity == SEVERITY_WARNING
    assert reasons == ["scheduled_due_count=1"]
    assert report["summary"]["operator_priority_score"] == 30
    assert report["summary"]["operator_priority_reasons"] == ["scheduled_due_count=1"]
    assert report["summary"]["scheduled_due_count"] == 1
    assert report["summary"]["scheduled_ready_count"] == 0
    assert report["incident_response"]["schedule_state"] == "scheduled_due"
    assert report["incident_response"]["scheduled_at"] == scheduled_at
    assert report["incident_response"]["schedule_hint"] == f"schedule=scheduled_due@{scheduled_at}"
    assert report["incident_response"]["scheduled_due_count"] == 1
    assert report["incident_response"]["scheduled_ready_count"] == 0
    text = format_review_queue_report(report)
    assert (
        "actions: blocked=0, stale_ready=0, scheduled_due=1, scheduled_ready=0, needs_edit=0, missing_status=0"
    ) in text
    assert "publish_or_reschedule | Ready to Post | Ready scheduled time passed 1 days ago" in text
    assert "incident_response: warning | action_required=true | next_step=Manually publish" in text
    assert f"schedule=scheduled_due@{scheduled_at}" in text


def test_ready_schedule_delta_surfaces_future_to_due_transition():
    records = [
        {
            "page_id": "scheduled",
            "title": "Scheduled item",
            "date": "2026-06-01T00:00:00+00:00",
            "x_scheduled_at": "2026-06-10T09:00:00+00:00",
            "x_publish_status": "Ready to Post",
        }
    ]
    previous = build_review_queue_report(records, now=datetime(2026, 6, 9, 10, tzinfo=UTC))
    current = build_review_queue_report(records, now=datetime(2026, 6, 10, 10, tzinfo=UTC))

    delta = build_review_queue_delta(current, previous)

    assert delta["comparable"] is True
    assert delta["counts"]["scheduled_due_count"] == 1
    assert delta["counts"]["scheduled_ready_count"] == -1
    assert delta["counts"]["operator_action_count"] == 1
    assert delta["incident_response"]["previous_schedule_hint"] == ""
    assert delta["incident_response"]["current_schedule_hint"] == "schedule=scheduled_due@2026-06-10T09:00:00+00:00"
    assert delta["incident_response"]["schedule_changed"] is True
    report = {**current, "delta": delta}
    text = format_review_queue_report(report)
    assert "delta: blocked=+0, stale_ready=+0, scheduled_due=+1, scheduled_ready=-1" in text
    assert "ready_schedule_delta: scheduled_due=+1, scheduled_ready=-1" in text
    assert "schedule=none->schedule=scheduled_due@2026-06-10T09:00:00+00:00" in text
    assert "--reprocess-approved" not in text


def test_ready_attention_limit_is_configurable_without_changing_default():
    records = [
        {
            "page_id": f"ready-{index}",
            "title": f"Ready {index}",
            "date": "2026-06-01T00:00:00+00:00",
            "x_publish_status": "Ready to Post",
        }
        for index in range(5)
    ]

    default_report = build_review_queue_report(records, now=datetime(2026, 6, 9, tzinfo=UTC))
    expanded_report = build_review_queue_report(
        records,
        ready_attention_limit=5,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )

    assert default_report["report_options"]["ready_attention_limit"] == 3
    assert default_report["ready_attention_count"] == 3
    assert default_report["ready_attention_hidden_count"] == 2
    assert default_report["ready_attention_truncated"] is True
    assert expanded_report["report_options"]["ready_attention_limit"] == 5
    assert expanded_report["ready_attention_count"] == 5
    assert expanded_report["ready_attention_hidden_count"] == 0
    assert expanded_report["ready_attention_truncated"] is False
    text = format_review_queue_report(expanded_report)
    assert "options: stale_days=3, action_limit=10, ready_attention_limit=5" in text
    assert "ready_attention: displayed=5, total=5, hidden=0, limit=5, truncated=false" in text


def test_operator_priority_labels_large_ready_backlog_without_incident():
    report = build_review_queue_report(
        [
            {
                "page_id": f"ready-backlog-{index}",
                "title": f"Ready backlog {index}",
                "date": "2026-06-05T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            }
            for index in range(4)
        ],
        stale_days=3,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )

    severity, reasons = evaluate_review_queue_severity(report)
    assert severity == SEVERITY_WARNING
    assert reasons == ["stale_ready_count=4"]
    assert report["summary"]["operator_priority_score"] == 100
    assert report["summary"]["operator_priority_label"] == "backlog"
    assert report["summary"]["operator_priority_reasons"] == ["stale_ready_count=4"]
    assert report["summary"]["top_ready_age_bucket"] == {"name": "4_7_days", "count": 4}
    text = format_review_queue_report(report)
    assert "summary: priority=100/backlog" in text
    assert "top_ready_age=4_7_days(4)" in text


def test_needs_edit_actions_surface_notion_review_reason_fields():
    report = build_review_queue_report(
        [
            {
                "page_id": "needs-edit-rejected",
                "title": "Rejected edit",
                "x_publish_status": "Needs Edit",
                "rejection_reasons": ["팩트 경계", "클리셰"],
                "risk_flags": ["독자 핏 약함"],
            },
            {
                "page_id": "needs-edit-focus",
                "title": "Focus edit",
                "x_publish_status": "Needs Edit",
                "review_focus": "첫 문장 훅만 다시 보기",
            },
        ]
    )

    reasons = [item["reason"] for item in report["operator_actions"]]
    reason_buckets = [item["reason_bucket"] for item in report["operator_actions"]]

    assert "Rejection reasons: 팩트 경계, 클리셰" in reasons
    assert "Review focus: 첫 문장 훅만 다시 보기" in reasons
    assert "rejection_reasons" in reason_buckets
    assert "review_focus" in reason_buckets
    assert report["needs_edit_reason_counts"]["rejection_reasons"] == 1
    assert report["needs_edit_reason_counts"]["review_focus"] == 1
    assert report["needs_edit_reason_counts"]["unknown"] == 0
    assert report["needs_edit_reason_examples"]["rejection_reasons"] == "Rejection reasons: 팩트 경계, 클리셰"
    assert "Start from the rejection reason tags" in report["needs_edit_reason_recovery_hints"]["rejection_reasons"]
    assert report["summary"]["top_operator_action"] == {"name": "review_draft_edits", "count": 2}
    assert report["summary"]["operator_priority_score"] == 30
    assert report["summary"]["operator_priority_label"] == "attention"
    assert report["summary"]["operator_priority_reasons"] == ["needs_edit_count=2"]
    assert report["summary"]["top_needs_edit_reason_bucket"] == {
        "name": "rejection_reasons",
        "count": 1,
    }
    assert report["incident_response"]["triage_bucket"] == "review_focus"
    assert report["incident_response"]["triage_hint"].startswith("Use the review focus text")
    text = format_review_queue_report(report)
    assert (
        "summary: priority=30/attention, top_action=review_draft_edits(2), top_needs_edit=rejection_reasons(1)"
    ) in text
    assert "triage=review_focus | triage_hint=Use the review focus text" in text
    assert "needs_edit_reason_buckets: rejection_reasons=1" in text
    assert "needs_edit_reason_recovery: rejection_reasons=1 | Rejection reasons:" in text
    assert "review_draft_edits | Needs Edit | Rejection reasons: 팩트 경계, 클리셰" in text
    assert "page_id:needsedi" in text


def test_missing_status_actions_surface_review_state_and_draft_presence():
    report = build_review_queue_report(
        [
            {
                "page_id": "missing-with-draft",
                "title": "Missing with draft",
                "status": "승인됨",
                "tweet_body": "ready draft",
                "x_publish_status": "",
            },
            {
                "page_id": "missing-without-draft",
                "title": "Missing without draft",
                "status": "검토중",
                "tweet_body": "",
                "x_publish_status": "",
            },
        ]
    )

    reasons = [item["reason"] for item in report["operator_actions"]]
    reason_buckets = [item["reason_bucket"] for item in report["operator_actions"]]

    assert "Missing X publish status; notion_status=승인됨, tweet_body=present" in reasons
    assert "Missing X publish status; notion_status=검토중, tweet_body=missing" in reasons
    assert "draft_present" in reason_buckets
    assert "draft_missing" in reason_buckets
    assert report["missing_status_counts"]["draft_present"] == 1
    assert report["missing_status_counts"]["draft_missing"] == 1
    assert report["missing_status_examples"]["draft_present"] == (
        "Missing X publish status; notion_status=승인됨, tweet_body=present"
    )
    assert "Set X Publish Status from the existing draft" in report["missing_status_recovery_hints"]["draft_present"]
    assert report["summary"]["top_operator_action"] == {"name": "fill_x_publish_status", "count": 2}
    assert report["summary"]["operator_priority_score"] == 25
    assert report["summary"]["operator_priority_label"] == "attention"
    assert report["summary"]["operator_priority_reasons"] == [
        "missing_status_draft_missing=1",
        "missing_status_draft_present=1",
    ]
    assert report["summary"]["top_missing_status_bucket"] == {"name": "draft_present", "count": 1}
    assert report["incident_response"]["triage_bucket"] == "draft_present"
    assert report["incident_response"]["triage_hint"].startswith("Set X Publish Status from the existing draft")
    text = format_review_queue_report(report)
    assert "summary: priority=25/attention, top_action=fill_x_publish_status(2)" in text
    assert "triage=draft_present | triage_hint=Set X Publish Status from the existing draft" in text
    assert "missing_status_buckets: draft_present=1, draft_missing=1" in text
    assert "missing_status_recovery: draft_present=1 | Missing X publish status;" in text
    assert "fill_x_publish_status | Missing | Missing X publish status; notion_status=승인됨" in text
    assert "page_id:missingw" in text


def test_build_operator_recovery_steps_limits_and_maps_actions():
    actions = [
        {
            "action": "fix_blocked_publish",
            "page_id": "blocked",
            "page_url": "https://notion.so/blocked",
            "title": "Blocked title",
        },
        {"action": "publish_or_reschedule", "page_id": "ready", "title": "Ready title"},
        {"action": "review_draft_edits", "page_id": "edit", "title": "Edit title"},
        {"action": "fill_x_publish_status", "page_id": "missing", "title": "Missing title"},
    ]

    steps = build_operator_recovery_steps(actions, limit=3)

    assert len(steps) == 3
    assert steps[0]["page_id"] == "blocked"
    assert steps[0]["priority"] == 10
    assert steps[0]["priority_label"] == "critical"
    assert steps[0]["target_hint"] == "https://notion.so/blocked"
    assert "--reprocess-approved" in steps[0]["next_step"]
    assert steps[1]["priority"] == 30
    assert steps[1]["priority_label"] == "stale_ready"
    assert steps[1]["target_hint"] == "page_id:ready"
    assert "X Scheduled At" in steps[1]["next_step"]
    assert steps[2]["priority"] == 40
    assert steps[2]["priority_label"] == "needs_edit"
    assert "Ready to Post" in steps[2]["next_step"]


def test_build_operator_recovery_steps_marks_unknown_actions_as_manual_review():
    steps = build_operator_recovery_steps(
        [{"action": "manual_review", "page_id": "manual", "title": "Manual follow-up"}]
    )

    assert steps[0]["priority"] == 90
    assert steps[0]["priority_label"] == "review"
    assert "update X Publish Status" in steps[0]["next_step"]


def test_build_review_queue_delta_compares_previous_counts():
    previous = build_review_queue_report(
        [
            {"page_id": "old-ready", "x_publish_status": "Ready to Post"},
            {
                "page_id": "old-blocked",
                "x_publish_status": "Blocked",
                "x_publish_error": "Twitter post failed",
            },
        ]
    )
    current = build_review_queue_report(
        [
            {"page_id": "new-ready", "x_publish_status": "Ready to Post"},
            {"page_id": "new-published", "x_publish_status": "Published"},
            {
                "page_id": "new-blocked-1",
                "x_publish_status": "Blocked",
                "x_publish_error": "Twitter post failed",
            },
            {
                "page_id": "new-blocked-2",
                "x_publish_status": "Blocked",
                "x_publish_error": "Missing tweet draft text",
            },
        ]
    )

    delta = build_review_queue_delta(current, previous)

    assert delta["has_previous"] is True
    assert delta["counts"]["total_records"] == 2
    assert delta["counts"]["blocked_count"] == 1
    assert delta["counts"]["published_count"] == 1
    assert delta["counts"]["operator_action_displayed_count"] == 1
    assert delta["counts"]["operator_action_hidden_count"] == 0
    assert delta["counts"]["ready_attention_displayed_count"] == 0
    assert delta["counts"]["ready_attention_total_count"] == 0
    assert delta["counts"]["ready_attention_hidden_count"] == 0
    assert delta["operator_action_truncated"] == {
        "previous": False,
        "current": False,
        "changed": False,
    }
    assert delta["ready_attention_truncated"] == {
        "previous": False,
        "current": False,
        "changed": False,
    }
    assert delta["incident_response"]["previous_severity"] == SEVERITY_CRITICAL
    assert delta["incident_response"]["current_severity"] == SEVERITY_CRITICAL
    assert delta["incident_response"]["current_fail_on_warning_exit_code"] == 2
    assert delta["status_counts"][STATUS_BLOCKED] == 1
    assert delta["operator_action_counts"]["fix_blocked_publish"] == 1
    assert delta["operator_action_counts"]["publish_or_reschedule"] == 0
    assert delta["blocked_error_counts"]["x_post_failed"] == 0
    assert delta["blocked_error_counts"]["missing_draft"] == 1
    assert delta["ready_age_buckets"]["no_date"] == 0
    assert delta["comparable"] is True
    assert delta["option_changes"] == {}
    assert delta["comparison_scope"] == {
        "same_options": True,
        "changed_options": [],
        "stable_signals": ["all"],
        "config_sensitive_signals": [],
    }


def test_build_review_queue_delta_marks_option_changes_as_not_comparable():
    previous = build_review_queue_report(
        [{"page_id": "old-ready", "x_publish_status": "Ready to Post"}],
        stale_days=3,
        action_limit=10,
    )
    current = build_review_queue_report(
        [{"page_id": "new-ready", "x_publish_status": "Ready to Post"}],
        stale_days=1,
        action_limit=2,
    )

    delta = build_review_queue_delta(current, previous)

    assert delta["comparable"] is False
    assert delta["option_changes"] == {
        "action_limit": {"previous": 10, "current": 2},
        "stale_days": {"previous": 3, "current": 1},
    }
    assert delta["comparison_scope"] == {
        "same_options": False,
        "changed_options": ["stale_days", "action_limit"],
        "stable_signals": [
            "status_counts",
            "blocked_error_buckets",
            "needs_edit_reason_buckets",
            "missing_status_buckets",
        ],
        "config_sensitive_signals": [
            "stale_ready_count",
            "severity",
            "incident_response",
            "operator_actions",
            "ready_attention_order",
            "operator_action_display",
            "operator_action_rank",
        ],
    }
    report = {**current, "delta": delta}
    text = format_review_queue_report(report)
    assert "delta_options: changed stale_days=3->1, action_limit=10->2" in text
    assert (
        "delta_scope: comparable=false, changed_options=stale_days, action_limit, "
        "stable_signals=4, config_sensitive_signals=7"
    ) in text
    assert (
        "delta_scope_detail: "
        "stable=status_counts, blocked_error_buckets, needs_edit_reason_buckets, missing_status_buckets | "
        "config_sensitive=stale_ready_count, severity, incident_response, operator_actions, "
        "ready_attention_order, operator_action_display, operator_action_rank"
    ) in text


def test_build_review_queue_delta_surfaces_action_display_changes():
    records = [
        {"page_id": "blocked", "title": "Blocked", "x_publish_status": "Blocked"},
        {"page_id": "needs-edit", "title": "Needs edit", "x_publish_status": "Needs Edit"},
        {"page_id": "missing", "title": "Missing", "x_publish_status": ""},
    ]
    previous = build_review_queue_report(records, action_limit=3)
    current = build_review_queue_report(records, action_limit=1)

    delta = build_review_queue_delta(current, previous)

    assert delta["comparable"] is False
    assert delta["option_changes"] == {"action_limit": {"previous": 3, "current": 1}}
    assert delta["counts"]["operator_action_count"] == 0
    assert delta["counts"]["operator_action_displayed_count"] == -2
    assert delta["counts"]["operator_action_hidden_count"] == 2
    assert delta["operator_action_truncated"] == {
        "previous": False,
        "current": True,
        "changed": True,
    }
    report = {**current, "delta": delta}
    text = format_review_queue_report(report)
    assert "action_display_delta: displayed=-2, hidden=+2, truncated=false->true" in text


def test_build_review_queue_delta_surfaces_ready_attention_display_changes():
    records = [
        {
            "page_id": f"ready-{index}",
            "title": f"Ready {index}",
            "date": "2026-06-01T00:00:00+00:00",
            "x_publish_status": "Ready to Post",
        }
        for index in range(4)
    ]
    previous = build_review_queue_report(
        records,
        ready_attention_limit=4,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )
    current = build_review_queue_report(
        records,
        ready_attention_limit=2,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )
    next_commands = {command["name"]: command for command in current["operator_next_commands"]}
    assert set(next_commands) == {"refresh_report", "show_all_ready_attention"}
    assert next_commands["show_all_ready_attention"]["read_only"] is True
    assert next_commands["show_all_ready_attention"]["x_posts"] is False
    assert next_commands["show_all_ready_attention"]["publish_command"] is False
    assert next_commands["show_all_ready_attention"]["purpose"] == (
        "Show all 4 Ready to Post attention items without publishing."
    )
    assert "--review-queue-report" in next_commands["show_all_ready_attention"]["command"]
    assert "--review-queue-ready-attention-limit 4" in next_commands["show_all_ready_attention"]["command"]
    assert "--reprocess-approved" not in next_commands["show_all_ready_attention"]["command"]

    delta = build_review_queue_delta(current, previous)

    assert delta["comparable"] is False
    assert delta["option_changes"] == {"ready_attention_limit": {"previous": 4, "current": 2}}
    assert delta["comparison_scope"] == {
        "same_options": False,
        "changed_options": ["ready_attention_limit"],
        "stable_signals": [
            "status_counts",
            "blocked_error_buckets",
            "needs_edit_reason_buckets",
            "missing_status_buckets",
            "ready_age_buckets",
            "incident_response",
        ],
        "config_sensitive_signals": ["ready_attention_display", "ready_attention_rank"],
    }
    assert delta["counts"]["ready_attention_displayed_count"] == -2
    assert delta["counts"]["ready_attention_total_count"] == 0
    assert delta["counts"]["ready_attention_hidden_count"] == 2
    assert delta["ready_attention_truncated"] == {
        "previous": False,
        "current": True,
        "changed": True,
    }
    report = {**current, "delta": delta}
    text = format_review_queue_report(report)
    assert (
        "delta_scope: comparable=false, changed_options=ready_attention_limit, "
        "stable_signals=6, config_sensitive_signals=2"
    ) in text
    assert (
        "delta_scope_detail: "
        "stable=status_counts, blocked_error_buckets, needs_edit_reason_buckets, missing_status_buckets, "
        "ready_age_buckets, incident_response | "
        "config_sensitive=ready_attention_display, ready_attention_rank"
    ) in text
    assert "ready_attention_display_delta: displayed=-2, total=+0, hidden=+2, truncated=false->true" in text


def test_build_review_queue_delta_surfaces_incident_response_changes():
    previous = build_review_queue_report([{"page_id": "published", "x_publish_status": "Published"}])
    current = build_review_queue_report(
        [
            {
                "page_id": "blocked",
                "title": "Blocked",
                "x_publish_status": "Blocked",
                "x_publish_error": "Twitter post failed",
            }
        ]
    )

    delta = build_review_queue_delta(current, previous)

    assert delta["incident_response"]["previous_severity"] == SEVERITY_OK
    assert delta["incident_response"]["current_severity"] == SEVERITY_CRITICAL
    assert delta["incident_response"]["severity_changed"] is True
    assert delta["incident_response"]["previous_action"] == ""
    assert delta["incident_response"]["current_action"] == "fix_blocked_publish"
    assert delta["incident_response"]["previous_target_hint"] == ""
    assert delta["incident_response"]["current_target_hint"] == "page_id:blocked"
    assert delta["incident_response"]["previous_triage_bucket"] == ""
    assert delta["incident_response"]["current_triage_bucket"] == "x_post_failed"
    assert delta["incident_response"]["triage_changed"] is True
    assert delta["incident_response"]["fail_on_warning_exit_code_delta"] == 2
    assert delta["incident_response"]["previous_escalation_required"] is False
    assert delta["incident_response"]["current_escalation_required"] is True
    report = {**current, "delta": delta}
    text = format_review_queue_report(report)
    assert (
        "incident_delta: severity=ok->critical, action=none->fix_blocked_publish, "
        "target=none->page_id:blocked, triage=none->x_post_failed, schedule=none->none, "
        "exit_if_enforced=0->2, escalation=false->true"
    ) in text


def test_build_review_queue_delta_surfaces_same_page_rank_changes():
    previous = build_review_queue_report(
        [
            {"page_id": "page-alpha", "title": "Alpha item", "x_publish_status": ""},
            {"page_id": "page-beta", "title": "Beta item", "x_publish_status": "Needs Edit"},
        ],
        action_limit=10,
    )
    current = build_review_queue_report(
        [
            {
                "page_id": "page-alpha",
                "title": "Alpha item",
                "x_publish_status": "Blocked",
                "x_publish_error": "Twitter post failed",
            },
            {"page_id": "page-beta", "title": "Beta item", "x_publish_status": "Needs Edit"},
        ],
        action_limit=10,
    )

    delta = build_review_queue_delta(current, previous)

    assert delta["operator_action_rank_change_count"] == 2
    assert delta["operator_action_rank_changes"][0] == {
        "operator_action_key": "page_id:page-alpha",
        "page_id": "page-alpha",
        "target_hint": "page_id:pagealph",
        "title": "Alpha item",
        "previous_rank": 2,
        "current_rank": 1,
        "rank_delta": -1,
        "direction": "up",
        "previous_action": "fill_x_publish_status",
        "current_action": "fix_blocked_publish",
    }
    assert delta["operator_action_rank_changes"][1]["operator_action_key"] == "page_id:page-beta"
    assert delta["operator_action_rank_changes"][1]["previous_rank"] == 1
    assert delta["operator_action_rank_changes"][1]["current_rank"] == 2
    assert delta["operator_action_rank_changes"][1]["direction"] == "down"
    report = {**current, "delta": delta}
    text = format_review_queue_report(report)
    assert (
        "action_rank_delta: page_id:pagealph 2->1 "
        "(up 1, action=fill_x_publish_status->fix_blocked_publish); "
        "page_id:pagebeta 1->2 (down 1)"
    ) in text


def test_build_review_queue_delta_surfaces_ready_attention_rank_changes():
    previous = build_review_queue_report(
        [
            {
                "page_id": "ready-alpha",
                "title": "Alpha ready",
                "date": "2026-06-07T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
            {
                "page_id": "ready-beta",
                "title": "Beta ready",
                "date": "2026-06-01T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
        ],
        stale_days=3,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )
    current = build_review_queue_report(
        [
            {
                "page_id": "ready-alpha",
                "title": "Alpha ready",
                "date": "2026-05-30T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
            {
                "page_id": "ready-beta",
                "title": "Beta ready",
                "date": "2026-06-01T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            },
        ],
        stale_days=3,
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )

    delta = build_review_queue_delta(current, previous)

    assert delta["ready_attention_rank_change_count"] == 2
    assert delta["ready_attention_rank_changes"][0] == {
        "ready_attention_key": "page_id:ready-alpha",
        "page_id": "ready-alpha",
        "target_hint": "page_id:readyalp",
        "title": "Alpha ready",
        "previous_rank": 2,
        "current_rank": 1,
        "rank_delta": -1,
        "direction": "up",
        "previous_age_days": 2,
        "current_age_days": 10,
        "previous_age_bucket": "2_3_days",
        "current_age_bucket": "8_plus_days",
    }
    assert delta["ready_attention_rank_changes"][1]["ready_attention_key"] == "page_id:ready-beta"
    assert delta["ready_attention_rank_changes"][1]["previous_rank"] == 1
    assert delta["ready_attention_rank_changes"][1]["current_rank"] == 2
    assert delta["ready_attention_rank_changes"][1]["direction"] == "down"
    report = {**current, "delta": delta}
    report["summary"] = build_review_queue_summary(report)
    assert report["summary"]["top_ready_attention_movement"] == {
        "ready_attention_key": "page_id:ready-alpha",
        "page_id": "ready-alpha",
        "target_hint": "page_id:readyalp",
        "title": "Alpha ready",
        "previous_rank": 2,
        "current_rank": 1,
        "rank_delta": -1,
        "direction": "up",
        "previous_age_days": 2,
        "current_age_days": 10,
    }
    text = format_review_queue_report(report)
    assert "top_ready_move=page_id:readyalp 2->1(up, age_days=2->10)" in text
    assert (
        "ready_attention_delta: page_id:readyalp 2->1 "
        "(up 1, age_days=2->10); page_id:readybet 1->2 (down 1, age_days=8->8)"
    ) in text


def test_build_review_queue_delta_compares_needs_edit_reason_buckets():
    previous = build_review_queue_report(
        [
            {
                "page_id": "prev-edit",
                "x_publish_status": "Needs Edit",
                "review_focus": "첫 문장 훅",
            }
        ]
    )
    current = build_review_queue_report(
        [
            {
                "page_id": "current-edit-1",
                "x_publish_status": "Needs Edit",
                "review_focus": "첫 문장 훅",
            },
            {
                "page_id": "current-edit-2",
                "x_publish_status": "Needs Edit",
                "risk_flags": ["팩트 경계"],
            },
        ]
    )

    delta = build_review_queue_delta(current, previous)

    assert delta["needs_edit_reason_counts"]["review_focus"] == 0
    assert delta["needs_edit_reason_counts"]["risk_flags"] == 1
    report = {**current, "delta": delta}
    text = format_review_queue_report(report)
    assert "needs_edit_reason_delta: rejection_reasons=+0, risk_flags=+1, review_focus=+0" in text


def test_build_review_queue_delta_compares_missing_status_buckets():
    previous = build_review_queue_report(
        [
            {
                "page_id": "prev-missing",
                "x_publish_status": "",
                "tweet_body": "ready draft",
            }
        ]
    )
    current = build_review_queue_report(
        [
            {
                "page_id": "current-missing-ready",
                "x_publish_status": "",
                "tweet_body": "ready draft",
            },
            {
                "page_id": "current-missing-draft",
                "x_publish_status": "",
                "tweet_body": "",
            },
        ]
    )

    delta = build_review_queue_delta(current, previous)

    assert delta["missing_status_counts"]["draft_present"] == 0
    assert delta["missing_status_counts"]["draft_missing"] == 1
    report = {**current, "delta": delta}
    text = format_review_queue_report(report)
    assert "missing_status_delta: draft_present=+0, draft_missing=+1" in text


def test_evaluate_review_queue_severity_maps_actions_to_operator_risk():
    ok_report = build_review_queue_report([{"page_id": "published", "x_publish_status": "Published"}])
    ok_report["delta"] = {"has_previous": False}
    assert evaluate_review_queue_severity(ok_report) == (SEVERITY_OK, [])

    warning_report = build_review_queue_report([{"page_id": "needs-edit", "x_publish_status": "Needs Edit"}])
    warning_report["delta"] = {"has_previous": False}
    warning, warning_reasons = evaluate_review_queue_severity(warning_report)
    assert warning == SEVERITY_WARNING
    assert "needs_edit_count=1" in warning_reasons

    stale_age_report = build_review_queue_report(
        [
            {
                "page_id": "stale-ready",
                "date": "2026-06-01T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            }
        ],
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )
    stale_age_report["delta"] = {"has_previous": False}
    stale_age, stale_age_reasons = evaluate_review_queue_severity(stale_age_report)
    assert stale_age == SEVERITY_WARNING
    assert "ready_8_plus_count=1" in stale_age_reasons

    missing_date_report = build_review_queue_report(
        [
            {
                "page_id": "ready-without-date",
                "x_publish_status": "Ready to Post",
            }
        ]
    )
    missing_date_report["delta"] = {"has_previous": False}
    missing_date, missing_date_reasons = evaluate_review_queue_severity(missing_date_report)
    assert missing_date == SEVERITY_WARNING
    assert "ready_missing_date_count=1" in missing_date_reasons

    critical_report = build_review_queue_report([{"page_id": "blocked", "x_publish_status": "Blocked"}])
    critical_report["delta"] = {"has_previous": False}
    critical, critical_reasons = evaluate_review_queue_severity(critical_report)
    assert critical == SEVERITY_CRITICAL
    assert "blocked_count=1" in critical_reasons


def test_evaluate_review_queue_severity_reports_ready_8_plus_delta():
    previous = build_review_queue_report(
        [
            {
                "page_id": "fresh-ready",
                "date": "2026-06-08T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            }
        ],
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )
    current = build_review_queue_report(
        [
            {
                "page_id": "old-ready",
                "date": "2026-06-01T00:00:00+00:00",
                "x_publish_status": "Ready to Post",
            }
        ],
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )
    current["delta"] = build_review_queue_delta(current, previous)

    severity, reasons = evaluate_review_queue_severity(current)

    assert severity == SEVERITY_WARNING
    assert "ready_8_plus_delta=+1" in reasons


def test_build_incident_response_maps_ok_and_warning_states_to_manual_actions():
    ok_report = build_review_queue_report([{"page_id": "published", "x_publish_status": "Published"}])
    ok_response = build_incident_response(ok_report)

    assert ok_response["severity"] == SEVERITY_OK
    assert ok_response["operator_action_required"] is False
    assert ok_response["escalation_required"] is False
    assert ok_response["next_step"] == "No operator action required; keep the manual Notion review queue monitored."
    assert ok_response["manual_publish_required"] is True
    assert ok_response["x_posts"] is False

    warning_report = build_review_queue_report([{"page_id": "needs-edit", "x_publish_status": "Needs Edit"}])
    warning_response = build_incident_response(warning_report)

    assert warning_response["severity"] == SEVERITY_WARNING
    assert warning_response["operator_action_required"] is True
    assert warning_response["escalation_required"] is False
    assert warning_response["action"] == "review_draft_edits"
    assert warning_response["fail_on_warning_exit_code"] == 1
    assert warning_response["manual_publish_required"] is True
    assert warning_response["x_posts"] is False


def test_exit_code_for_review_queue_report_is_opt_in():
    warning_report = {"severity": SEVERITY_WARNING}
    critical_report = {"severity": SEVERITY_CRITICAL}

    assert exit_code_for_review_queue_report(warning_report, fail_on_warning=False) == 0
    assert exit_code_for_review_queue_report(warning_report, fail_on_warning=True) == 1
    assert exit_code_for_review_queue_report(critical_report, fail_on_warning=True) == 2
    assert build_review_queue_exit_codes(warning_report) == {"default": 0, "fail_on_warning": 1}


def test_write_review_queue_report_artifact_round_trips_json(tmp_path):
    report = build_review_queue_report([{"page_id": "page-1", "x_publish_status": "Published"}])
    output_path = tmp_path / "review_queue_report_latest.json"

    written = write_review_queue_report_artifact(report, output_path)

    assert written == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["published_count"] == 1
    assert payload["status_counts"][STATUS_PUBLISHED] == 1


def test_write_review_queue_report_artifact_is_ascii_safe_for_windows_shells(tmp_path):
    report = build_review_queue_report(
        [{"page_id": "page-1", "title": "한글 제목", "x_publish_status": "Ready to Post"}]
    )
    output_path = tmp_path / "review_queue_report_latest.json"

    write_review_queue_report_artifact(report, output_path)

    raw = output_path.read_text(encoding="utf-8")
    raw.encode("ascii")
    assert "\\ud55c\\uae00" in raw
    payload = json.loads(raw)
    assert payload["ready_attention_items"][0]["title"] == "한글 제목"


def test_operator_next_commands_quote_powershell_metacharacter_artifact_path():
    report = build_review_queue_report(
        [{"page_id": "page-1", "title": "Ready", "x_publish_status": "Ready to Post"}],
        now=datetime(2026, 6, 9, tzinfo=UTC),
    )
    report["artifact_path"] = ".tmp/review&queue-loop7.json"

    commands = build_operator_next_commands(report)

    assert commands[0]["command"].endswith("--review-queue-report-output '.tmp/review&queue-loop7.json'")


@pytest.mark.asyncio
async def test_run_review_queue_report_fetches_recent_records_without_writes():
    notion = AsyncMock()
    notion.fetch_recent_records.return_value = [
        {"page_id": "page-1", "title": "Ready", "x_publish_status": "Ready to Post"}
    ]

    report = await run_review_queue_report(notion, lookback_days=14, limit=20, stale_days=2)

    notion.fetch_recent_records.assert_awaited_once_with(lookback_days=14, limit=20)
    assert report["success"] is True
    assert report["ready_to_post_count"] == 1
    assert report["report_options"] == {
        "lookback_days": 14,
        "limit": 20,
        "stale_days": 2,
        "action_limit": 10,
        "ready_attention_limit": 3,
    }
    assert report["delta"] == {"has_previous": False}
    assert report["summary"]["severity"] == SEVERITY_WARNING
    assert report["summary"]["top_operator_action"] == {"name": "publish_or_reschedule", "count": 1}
    assert report["summary"]["operator_priority_score"] == 25
    assert report["summary"]["operator_priority_label"] == "attention"
    assert report["summary"]["operator_priority_reasons"] == ["stale_ready_count=1"]
    assert report["summary"]["delta_comparable"] is None
    assert report["summary"]["read_only"] is True
    assert report["summary"]["x_posts"] is False
    assert not hasattr(notion, "update_page_properties") or not notion.update_page_properties.called


@pytest.mark.asyncio
async def test_run_review_queue_report_writes_artifact_and_reports_delta(tmp_path):
    output_path = tmp_path / "review_queue_report_latest.json"
    previous = build_review_queue_report(
        [
            {"page_id": "prev-ready", "title": "Prev ready", "x_publish_status": "Ready to Post"},
        ]
    )
    write_review_queue_report_artifact(previous, output_path)
    notion = AsyncMock()
    notion.fetch_recent_records.return_value = [
        {"page_id": "current-ready", "title": "Current ready", "x_publish_status": "Ready to Post"},
        {"page_id": "current-blocked", "title": "Current blocked", "x_publish_status": "Blocked"},
    ]

    report = await run_review_queue_report(
        notion,
        lookback_days=14,
        limit=20,
        stale_days=2,
        output_path=output_path,
    )

    assert report["artifact_path"] == str(output_path)
    assert report["delta"]["has_previous"] is True
    assert report["delta"]["counts"]["blocked_count"] == 1
    assert report["severity"] == SEVERITY_CRITICAL
    text = format_review_queue_report(report)
    assert "severity: critical" in text
    assert "severity_reasons: blocked_count=1" in text
    assert "options: lookback_days=14, limit=20, stale_days=2, action_limit=10, ready_attention_limit=3" in text
    assert "exit_codes: default=0, fail_on_warning=2" in text
    assert "summary: priority=125/critical, top_action=fix_blocked_publish(1)" in text
    assert "top_blocked_error=other(1)" in text
    assert "top_ready_age=no_date(1), oldest_ready=page_id:currentr@no_date" in text
    assert "delta: blocked=+1" in text
    assert "delta_options: changed lookback_days=missing->14, limit=missing->20, stale_days=3->2" in text
    assert "action_delta: fix_blocked_publish=+1" in text
    assert "blocked_error_buckets: missing_draft=0, x_post_failed=0, notion_sync_failed=0" in text
    assert "blocked_error_delta: missing_draft=+0, x_post_failed=+0, notion_sync_failed=+0" in text
    assert "ready_age: no_date=1" in text
    assert "oldest_age_days=no_date" in text
    assert "oldest_target=page_id:currentr" in text
    assert (
        "ready_attention: displayed=1, total=1, hidden=0, limit=3, truncated=false | "
        "1) age_days=no_date | Current ready | page_id:currentr"
    ) in text
    assert "ready_age_delta: no_date=+0" in text
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["blocked_count"] == 1
    assert payload["severity"] == SEVERITY_CRITICAL
    assert payload["delta"]["comparable"] is False
    assert payload["delta"]["option_changes"]["lookback_days"] == {"previous": None, "current": 14}
    assert payload["delta"]["option_changes"]["stale_days"] == {"previous": 3, "current": 2}
    assert payload["exit_codes"] == {"default": 0, "fail_on_warning": 2}
    assert payload["summary"]["severity"] == SEVERITY_CRITICAL
    assert payload["summary"]["operator_action_displayed_count"] == 2
    assert payload["summary"]["operator_action_hidden_count"] == 0
    assert payload["summary"]["operator_action_truncated"] is False
    assert payload["summary"]["operator_priority_score"] == 125
    assert payload["summary"]["operator_priority_label"] == "critical"
    assert payload["summary"]["operator_priority_reasons"] == ["blocked_count=1", "stale_ready_count=1"]
    assert payload["summary"]["top_operator_action"] == {"name": "fix_blocked_publish", "count": 1}
    assert payload["summary"]["top_blocked_error_bucket"] == {"name": "other", "count": 1}
    assert payload["summary"]["top_ready_age_bucket"] == {"name": "no_date", "count": 1}
    assert payload["summary"]["top_ready_attention_movement"]["target_hint"] == ""
    assert payload["summary"]["oldest_ready_target"] == "page_id:currentr"
    assert payload["summary"]["has_previous"] is True
    assert payload["summary"]["delta_comparable"] is False
    assert payload["summary"]["manual_publish_required"] is True
    assert payload["summary"]["x_posts"] is False
    assert payload["incident_response"]["severity"] == SEVERITY_CRITICAL
    assert payload["incident_response"]["operator_action_required"] is True
    assert payload["incident_response"]["escalation_required"] is True
    assert payload["incident_response"]["target_hint"] == "page_id:currentb"
    assert payload["incident_response"]["fail_on_warning_exit_code"] == 2
    assert payload["incident_response"]["manual_publish_required"] is True
    assert payload["incident_response"]["x_posts"] is False
    assert payload["safety"]["auto_publish_default"] is False
    assert payload["safety"]["manual_publish_required"] is True
    assert payload["report_options"]["lookback_days"] == 14
    assert payload["report_options"]["ready_attention_limit"] == 3
    assert payload["operator_action_counts"]["fix_blocked_publish"] == 1
    assert payload["operator_action_displayed_count"] == 2
    assert payload["operator_action_hidden_count"] == 0
    assert payload["operator_action_truncated"] is False
    assert payload["ready_age_buckets"]["no_date"] == 1
    assert payload["oldest_ready"]["target_hint"] == "page_id:currentr"
    assert payload["ready_attention_count"] == 1
    assert payload["ready_attention_displayed_count"] == 1
    assert payload["ready_attention_total_count"] == 1
    assert payload["ready_attention_hidden_count"] == 0
    assert payload["ready_attention_truncated"] is False
    assert payload["ready_attention_items"][0]["target_hint"] == "page_id:currentr"
    assert payload["ready_attention_items"][0]["ready_attention_rank"] == 1
    assert payload["ready_attention_items"][0]["ready_attention_key"] == "page_id:current-ready"
    assert payload["ready_attention_items"][0]["age_bucket"] == "no_date"
    assert payload["blocked_error_counts"]["other"] == 1
    assert payload["blocked_error_examples"]["other"] == "Blocked X publish status"
    assert payload["operator_recovery_steps"][0]["action"] == "fix_blocked_publish"
    assert payload["operator_recovery_steps"][0]["priority"] == 10
    assert payload["operator_recovery_steps"][0]["priority_label"] == "critical"
    assert payload["operator_actions"][0]["target_hint"] == "page_id:currentb"
    assert payload["operator_actions"][0]["operator_action_rank"] == 1
    assert payload["operator_actions"][0]["operator_action_key"] == "page_id:current-blocked"
    assert payload["operator_actions"][0]["priority"] == 10
    assert payload["operator_actions"][0]["priority_label"] == "critical"


@pytest.mark.asyncio
async def test_run_review_queue_report_coerces_numeric_options():
    notion = AsyncMock()
    notion.fetch_recent_records.return_value = []

    report = await run_review_queue_report(notion, lookback_days="14", limit="20", stale_days="2")

    notion.fetch_recent_records.assert_awaited_once_with(lookback_days=14, limit=20)
    assert report["success"] is True
    assert report["total_records"] == 0


@pytest.mark.asyncio
async def test_run_review_queue_report_honors_action_limit_option():
    notion = AsyncMock()
    notion.fetch_recent_records.return_value = [
        {"page_id": "blocked", "title": "Blocked", "x_publish_status": "Blocked"},
        {"page_id": "missing", "title": "Missing", "x_publish_status": ""},
    ]

    report = await run_review_queue_report(notion, lookback_days=14, limit=20, stale_days=2, action_limit="1")

    assert report["operator_action_count"] == 2
    assert len(report["operator_actions"]) == 1
    assert report["report_options"]["action_limit"] == 1
    assert report["operator_action_displayed_count"] == 1
    assert report["operator_action_hidden_count"] == 1
    assert report["operator_action_truncated"] is True
    assert report["operator_actions"][0]["operator_action_rank"] == 1
    next_commands = {command["name"]: command for command in report["operator_next_commands"]}
    assert set(next_commands) == {"refresh_report", "show_all_actions"}
    assert next_commands["show_all_actions"]["read_only"] is True
    assert next_commands["show_all_actions"]["x_posts"] is False
    assert next_commands["show_all_actions"]["publish_command"] is False
    assert next_commands["show_all_actions"]["purpose"] == "Show all 2 current operator actions without publishing."
    assert "--review-queue-report" in next_commands["show_all_actions"]["command"]
    assert "--limit 20" in next_commands["show_all_actions"]["command"]
    assert "--review-queue-lookback-days 14" in next_commands["show_all_actions"]["command"]
    assert "--review-queue-action-limit 2" in next_commands["show_all_actions"]["command"]
    assert "--reprocess-approved" not in next_commands["show_all_actions"]["command"]
    text = format_review_queue_report(report)
    assert "next_command 2 [show_all_actions]:" in text
    assert "purpose=Show all 2 current operator actions without publishing." in text
    assert "--review-queue-action-limit 2" in text
    assert (
        "action_display: displayed=1, total=2, hidden=1, truncated=true, rerun_with=--review-queue-action-limit 2"
    ) in text
    assert report["summary"]["operator_action_displayed_count"] == 1
    assert report["summary"]["operator_action_hidden_count"] == 1
    assert report["summary"]["operator_action_truncated"] is True


@pytest.mark.asyncio
async def test_run_review_queue_report_honors_ready_attention_limit_option():
    notion = AsyncMock()
    notion.fetch_recent_records.return_value = [
        {
            "page_id": f"ready-{index}",
            "title": f"Ready {index}",
            "date": "2026-06-01T00:00:00+00:00",
            "x_publish_status": "Ready to Post",
        }
        for index in range(4)
    ]

    report = await run_review_queue_report(
        notion,
        lookback_days=14,
        limit=20,
        stale_days=2,
        ready_attention_limit="4",
    )

    assert report["report_options"]["ready_attention_limit"] == 4
    assert report["ready_attention_count"] == 4
    assert report["ready_attention_displayed_count"] == 4
    assert report["ready_attention_total_count"] == 4
    assert report["ready_attention_hidden_count"] == 0
    assert report["ready_attention_truncated"] is False
    assert len(report["ready_attention_items"]) == 4
    text = format_review_queue_report(report)
    assert "ready_attention: displayed=4, total=4, hidden=0, limit=4, truncated=false" in text
