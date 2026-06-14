"""Helpers for exposing Notion retry diagnostics in operator-facing results."""

from __future__ import annotations

from typing import Any


def notion_retry_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_state": report.get("final_state"),
        "attempt_count": report.get("attempt_count"),
        "retry_count": report.get("retry_count"),
        "last_status": report.get("last_status"),
        "retryable": report.get("retryable"),
    }


def _latest_wait_seconds(report: dict[str, Any]) -> Any:
    attempts = report.get("attempts")
    last_attempt = attempts[-1] if isinstance(attempts, list) and attempts else {}
    return next(
        (last_attempt[key] for key in ("retry_after_seconds", "delay_seconds") if last_attempt.get(key) is not None),
        None,
    )


def notion_failure_classification(report: dict[str, Any]) -> dict[str, Any]:
    status = report.get("last_status")
    retryable = report.get("retryable") is True
    wait_seconds = _latest_wait_seconds(report)

    category = "unknown"
    primary_repair = "inspect_retry_report"
    if status == 429:
        category = "rate_limited"
        primary_repair = "respect_retry_after_or_backoff"
    elif status == 529:
        category = "service_overload"
        primary_repair = "respect_retry_after_or_backoff"
    elif isinstance(status, int) and status >= 500:
        category = "transient_server_error"
        primary_repair = "retry_later_or_backoff"
    elif status == 401:
        category = "credential_invalid"
        primary_repair = "fix_notion_token"
    elif status == 403:
        category = "permission_or_sharing"
        primary_repair = "share_database_with_integration"
    elif status == 404:
        category = "object_not_found_or_not_shared"
        primary_repair = "verify_database_id_and_sharing"
    elif status == 400:
        category = "schema_or_payload"
        primary_repair = "fix_schema_or_payload"
    elif retryable:
        category = "network_or_unknown_transient"
        primary_repair = "retry_later_or_backoff"

    return {
        "category": category,
        "status": status,
        "retryable": retryable,
        "retry_recommended": bool(retryable),
        "wait_seconds": wait_seconds,
        "primary_repair": primary_repair,
    }


def notion_retry_operator_action(report: dict[str, Any], *, retry_label: str = "the Notion operation") -> str:
    status = report.get("last_status")
    retryable = report.get("retryable") is True
    wait_seconds = _latest_wait_seconds(report)

    if retryable:
        if wait_seconds is not None:
            return f"Retry {retry_label} after at least {wait_seconds}s, then reduce request rate if it repeats."
        return f"Retry {retry_label} later, then reduce request rate if it repeats."
    if status == 401:
        return "Update NOTION_API_KEY with a valid Notion integration Bearer token before rerun."
    if status == 403:
        return "Share the target database/data source with the Notion integration before rerun."
    if status == 404:
        return "Verify NOTION_DATABASE_ID is the target database/data_source ID and shared before rerun."
    if status == 400:
        return "Check Notion schema/property compatibility before rerun."
    return "Inspect error_code, error_message, and retry report before rerun."


def notion_retry_diagnostics(notion_uploader: object, *, retry_label: str = "the Notion operation") -> dict[str, Any]:
    report = getattr(notion_uploader, "last_notion_retry_report", None)
    if not isinstance(report, dict):
        return {}

    return {
        "notion_retry_summary": notion_retry_summary(report),
        "notion_failure_classification": notion_failure_classification(report),
        "notion_retry_report": report,
        "notion_operator_action": notion_retry_operator_action(report, retry_label=retry_label),
    }


def attach_notion_retry_diagnostics(
    target: dict[str, Any],
    notion_uploader: object,
    *,
    retry_label: str = "the Notion operation",
) -> None:
    target.update(notion_retry_diagnostics(notion_uploader, retry_label=retry_label))
