"""Shared context and stage-state helpers for `process_single_post()`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProcessRunContext:
    """Shared mutable state across process stages."""

    url: str
    trace_id: str
    result: dict[str, Any]
    post_data: dict[str, Any] = field(default_factory=dict)
    content_text: str = ""
    quality: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)
    drafts: dict[str, Any] | str | None = None
    image_prompt: str | None = None
    screenshot_task: Any = None
    notion_url: str | None = None
    notion_page_id: str | None = None
    twitter_url: str | None = None
    errors: list[str] = field(default_factory=list)
    stage_status: dict[str, dict[str, Any]] = field(default_factory=dict)


def build_process_result(url: str, trace_id: str) -> dict[str, Any]:
    return {
        "url": url,
        "trace_id": trace_id,
        "success": False,
        "error": None,
        "error_code": None,
        "notion_url": None,
        "quality_score": None,
        "failure_stage": None,
        "failure_reason": None,
        "stage_status": {},
    }


def mark_stage(ctx: ProcessRunContext, stage: str, status: str, detail: str | None = None) -> None:
    record = {"status": status}
    if detail:
        record["detail"] = detail
    ctx.stage_status[stage] = record
    ctx.result["stage_status"] = dict(ctx.stage_status)
