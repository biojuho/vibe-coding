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


def notion_retry_operator_action(report: dict[str, Any], *, retry_label: str = "the Notion operation") -> str:
    status = report.get("last_status")
    retryable = report.get("retryable") is True
    attempts = report.get("attempts")
    last_attempt = attempts[-1] if isinstance(attempts, list) and attempts else {}
    wait_seconds = next(
        (last_attempt[key] for key in ("retry_after_seconds", "delay_seconds") if last_attempt.get(key) is not None),
        None,
    )

    if retryable:
        if wait_seconds is not None:
            return f"Retry {retry_label} after at least {wait_seconds}s, then reduce request rate if it repeats."
        return f"Retry {retry_label} later, then reduce request rate if it repeats."
    if status in {401, 403, 404}:
        return "Check the Notion token, database ID, and DB/data-source sharing before rerun."
    if status == 400:
        return "Check Notion schema/property compatibility before rerun."
    return "Inspect error_code, error_message, and retry report before rerun."


def notion_retry_diagnostics(notion_uploader: object, *, retry_label: str = "the Notion operation") -> dict[str, Any]:
    report = getattr(notion_uploader, "last_notion_retry_report", None)
    if not isinstance(report, dict):
        return {}

    return {
        "notion_retry_summary": notion_retry_summary(report),
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
