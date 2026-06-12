"""Dry-run A/B report for Notion review-card signal changes.

The script compares the current review-card signal set with a candidate
recovery-aware signal set. It performs no Notion writes and no X publishing.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BTX_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = BTX_ROOT / ".tmp" / "review_experiment_dry_run.json"

REVIEW_RECORD_COLLECTION_KEYS = (
    "records",
    "review_records",
    "operator_actions",
    "ready_attention_items",
)
OPERATOR_ACTION_NOISE_THRESHOLD = 3
MIN_CONFIDENT_EXPERIMENT_ITEMS = 3
MAX_CONFIDENT_MISSING_METRIC_RATE = 0.25
PROVIDER_FAILURE_PRIORITY = {
    "auth": 10,
    "quota_or_billing": 20,
    "invalid_output": 30,
    "rate_limit": 40,
    "overloaded": 50,
    "server_error": 60,
    "timeout": 70,
    "network_error": 80,
    "provider_error": 90,
}

OBJECTIVE_METRICS = (
    "success",
    "latency_ms",
    "provider",
    "model",
    "token_cost_estimate",
    "final_rank_score",
    "draft_quality_score",
    "safety_risk_flags",
    "duplicate_or_near_duplicate",
    "operator_action_required",
)

MISSING_METRIC_HINTS = {
    "success": {
        "reason": "No publishable draft was exported for the review item.",
        "operator_action": "Regenerate or repair the draft before review approval.",
        "owner": "draft_generation",
    },
    "latency_ms": {
        "reason": "Provider timing telemetry was not exported.",
        "operator_action": "Include latency_ms from generation telemetry in review records.",
        "owner": "provider_telemetry",
    },
    "provider": {
        "reason": "The draft provider name was not exported.",
        "operator_action": "Include the provider used for the selected draft or fallback attempt.",
        "owner": "provider_telemetry",
    },
    "model": {
        "reason": "The model name was not exported.",
        "operator_action": "Include the model used for the selected draft or fallback attempt.",
        "owner": "provider_telemetry",
    },
    "token_cost_estimate": {
        "reason": "The estimated token cost was not exported.",
        "operator_action": "Include token_cost_estimate from the generation cost tracker.",
        "owner": "cost_tracking",
    },
    "final_rank_score": {
        "reason": "The source selection rank score was not exported.",
        "operator_action": "Include final_rank_score from the ranking stage.",
        "owner": "source_ranking",
    },
    "draft_quality_score": {
        "reason": "The draft quality gate score was not exported.",
        "operator_action": "Include draft_quality_score from the quality gate stage.",
        "owner": "quality_gate",
    },
    "safety_risk_flags": {
        "reason": "The safety review result was not exported.",
        "operator_action": "Export safety_risk_flags or an explicit reviewed-no-risk marker.",
        "owner": "safety_review",
    },
    "duplicate_or_near_duplicate": {
        "reason": "The duplicate detection result was not exported.",
        "operator_action": "Include duplicate_or_near_duplicate from similarity checks.",
        "owner": "deduplication",
    },
    "operator_action_required": {
        "reason": "The operator action requirement was not exported.",
        "operator_action": "Include operator_action_required from review queue triage.",
        "owner": "review_queue",
    },
}

ROLLOUT_BLOCKER_REASONS = {
    "sample_size_too_small": "run the dry-run with at least 3 review items",
    "missing_metric_rate_high": "fill missing objective metrics before rollout",
    "operator_action_noise_high": "reduce noisy operator actions before rollout",
    "not_read_only": "restore the read-only dry-run safety contract",
    "notion_writes_enabled": "disable Notion writes for the dry-run",
    "x_posts_enabled": "disable X posting for the dry-run",
    "auto_publish_enabled": "keep auto-publish disabled by default",
    "manual_publish_not_required": "require manual publish approval",
}

CURRENT_SIGNALS = (
    "title",
    "url",
    "success",
    "draft_generation_error",
    "final_rank_score",
    "draft_quality_score",
    "safety_risk_flags",
    "duplicate_or_near_duplicate",
)

CANDIDATE_SIGNALS = (
    *CURRENT_SIGNALS,
    "provider",
    "model",
    "latency_ms",
    "token_cost_estimate",
    "x_publish_status",
    "operator_action_required",
    "operator_actions",
    "provider_failure_summary",
)

DEFAULT_FIXTURE: dict[str, Any] = {
    "post_data": {
        "title": "Review-only draft with provider fallback",
        "url": "https://example.com/posts/1",
        "draft_generation_failed": True,
        "draft_generation_error": "All providers failed",
        "draft_provider_failure_summary": {
            "providers_attempted": ["gemini", "openai"],
            "categories": {"auth": 1, "rate_limit": 1},
            "operator_action_required": True,
            "primary_operator_action": "Check provider API key and quota before retrying",
        },
        "draft_provider_failures": [
            {
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "latency_ms": 830,
                "category": "rate_limit",
                "operator_action_required": True,
                "operator_action": "Wait for quota reset or switch provider",
            },
            {
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "latency_ms": 410,
                "category": "auth",
                "operator_action_required": True,
                "operator_action": "Check provider API key",
            },
        ],
        "token_cost_estimate": 0.038,
        "x_publish_status": "Needs Edit",
        "risk_flags": ["draft_generation_failed"],
    },
    "drafts": {
        "_generation_failed": True,
        "_provider_used": "gemini",
        "_model_used": "gemini-2.5-flash",
        "_quality_gate_score": 4.2,
        "_max_semantic_similarity": 0.16,
    },
    "analysis": {
        "selection_summary": "Review-only item needs provider recovery before publishing.",
        "final_rank_score": 74,
    },
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
        return default
    return bool(value)


def _average_numeric(values: Any) -> float | None:
    if isinstance(values, dict):
        numbers = [_as_float(value) for value in values.values()]
    elif isinstance(values, list | tuple):
        numbers = [_as_float(value) for value in values]
    else:
        return _as_float(values)

    valid = [number for number in numbers if number is not None]
    if not valid:
        return None
    return round(sum(valid) / len(valid), 3)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _first_record_value(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _first_nonempty_text(mapping: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _provider_failures(post_data: dict[str, Any], drafts: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for source in (post_data.get("draft_provider_failures"), drafts.get("_provider_failures")):
        if isinstance(source, list):
            failures.extend(item for item in source if isinstance(item, dict))
    return failures


def _unique_nonempty_texts(values: Any) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in _as_list(values):
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            results.append(text)
    return results


def _provider_names_from_failures(failures: list[dict[str, Any]]) -> list[str]:
    values = [_first_present(failure.get("provider"), failure.get("provider_name")) for failure in failures]
    return _unique_nonempty_texts(values)


def _provider_failure_category_counts(value: Any) -> dict[str, int]:
    counts: Counter[str] = Counter()
    if isinstance(value, dict):
        for category, count in value.items():
            key = str(category).strip()
            parsed = _as_float(count)
            int_count = int(parsed) if parsed is not None else 0
            if key and int_count > 0:
                counts[key] += int_count
    else:
        for category in _as_list(value):
            key = str(category).strip()
            if key:
                counts[key] += 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _provider_failure_category_counts_from_failures(failures: list[dict[str, Any]]) -> dict[str, int]:
    values = [
        _first_present(failure.get("category"), failure.get("error_category"), failure.get("failure_category"))
        for failure in failures
    ]
    return _provider_failure_category_counts(values)


def _provider_failure_category(failure: dict[str, Any]) -> str:
    return (
        str(
            _first_present(
                failure.get("category"),
                failure.get("error_category"),
                failure.get("failure_category"),
                "provider_error",
            )
        ).strip()
        or "provider_error"
    )


def _provider_failure_brief(failure: dict[str, Any]) -> dict[str, Any]:
    category = _provider_failure_category(failure)
    provider = str(_first_present(failure.get("provider"), failure.get("provider_name"), "") or "").strip()
    model = str(failure.get("model") or "").strip()
    circuit_breaker = _as_bool(failure.get("circuit_breaker_candidate")) or category in {"auth", "quota_or_billing"}
    return {
        "provider": provider,
        "model": model,
        "category": category,
        "retryable": _as_bool(failure.get("retryable")),
        "circuit_breaker_candidate": circuit_breaker,
        "error_preview": str(failure.get("error_preview") or failure.get("error") or "").strip(),
        "operator_action": str(failure.get("operator_action") or "").strip(),
    }


def _provider_failure_priority(failure: dict[str, Any], index: int) -> tuple[int, int]:
    category = _provider_failure_category(failure)
    priority = PROVIDER_FAILURE_PRIORITY.get(category, PROVIDER_FAILURE_PRIORITY["provider_error"])
    if _as_bool(failure.get("circuit_breaker_candidate")) or category in {"auth", "quota_or_billing"}:
        priority = max(0, priority - 5)
    return priority, index


def _primary_provider_failure_from_failures(failures: list[dict[str, Any]]) -> dict[str, Any]:
    if not failures:
        return {}
    indexed = list(enumerate(failures))
    _, primary = sorted(indexed, key=lambda item: _provider_failure_priority(item[1], item[0]))[0]
    return _provider_failure_brief(primary)


def _primary_provider_failure(summary: dict[str, Any], failures: list[dict[str, Any]]) -> dict[str, Any]:
    primary = _as_dict(summary.get("primary_failure"))
    if primary:
        brief = _provider_failure_brief(primary)
        if brief["provider"] or brief["category"] != "provider_error" or brief["operator_action"]:
            return brief
    return _primary_provider_failure_from_failures(failures)


def _merge_provider_failure_counts(primary: dict[str, int], fallback: dict[str, int]) -> dict[str, int]:
    merged = dict(primary)
    for key, count in fallback.items():
        if key not in merged:
            merged[key] = count
    return dict(sorted(merged.items(), key=lambda pair: (-pair[1], pair[0])))


def _provider_failure_summary(post_data: dict[str, Any], drafts: dict[str, Any]) -> dict[str, Any]:
    failures = _provider_failures(post_data, drafts)
    summary = _as_dict(
        _first_present(
            post_data.get("draft_provider_failure_summary"),
            drafts.get("_provider_failure_summary"),
        )
    )
    if not summary and not failures:
        return {}

    providers_attempted = _unique_nonempty_texts(summary.get("providers_attempted"))
    for provider in _provider_names_from_failures(failures):
        if provider not in providers_attempted:
            providers_attempted.append(provider)

    categories = _merge_provider_failure_counts(
        _provider_failure_category_counts(summary.get("categories")),
        _provider_failure_category_counts_from_failures(failures),
    )
    primary_failure = _primary_provider_failure(summary, failures)
    return {
        "providers_attempted": providers_attempted,
        "categories": categories,
        "operator_action_required": _as_bool(summary.get("operator_action_required"))
        or any(_as_bool(failure.get("operator_action_required")) for failure in failures),
        "primary_operator_action": str(summary.get("primary_operator_action") or "").strip()
        or str(primary_failure.get("operator_action") or "").strip(),
        "primary_failure": primary_failure,
    }


def _first_provider_failure(failures: list[dict[str, Any]]) -> dict[str, Any]:
    return failures[0] if failures else {}


def _draft_generation_failed(post_data: dict[str, Any], drafts: dict[str, Any]) -> bool:
    return _as_bool(_first_present(post_data.get("draft_generation_failed"), drafts.get("_generation_failed")))


def _draft_success(post_data: dict[str, Any], drafts: dict[str, Any]) -> bool:
    generation_failed = _draft_generation_failed(post_data, drafts)
    draft_text = _first_nonempty_text(drafts, ("twitter", "threads", "naver_blog", "newsletter"))
    return bool(draft_text) and not generation_failed


def _x_publish_status_requires_action(value: Any) -> bool:
    return str(value or "").strip().lower() in {"", "needs edit", "blocked", "failed"}


def _priority_value(value: Any, default: int = 999) -> int:
    priority = _as_float(value)
    return int(priority if priority is not None else default)


def _duplicate_or_near_duplicate(post_data: dict[str, Any], drafts: dict[str, Any]) -> bool:
    explicit = _first_present(
        post_data.get("duplicate_or_near_duplicate"),
        post_data.get("is_duplicate"),
        drafts.get("_duplicate_or_near_duplicate"),
    )
    if explicit is not None:
        return _as_bool(explicit)

    similarity = _as_float(
        _first_present(post_data.get("max_semantic_similarity"), drafts.get("_max_semantic_similarity"))
    )
    return bool(similarity is not None and similarity >= 0.85)


def _draft_quality_score(post_data: dict[str, Any], drafts: dict[str, Any]) -> float | None:
    primary_score = _as_float(
        _first_present(
            drafts.get("_quality_gate_score"),
            post_data.get("draft_quality_score"),
            post_data.get("quality_gate_score"),
        )
    )
    if primary_score is not None:
        return primary_score
    return _average_numeric(post_data.get("quality_gate_scores"))


def _safety_risk_flags_result(*mappings: dict[str, Any]) -> list[Any] | None:
    for mapping in mappings:
        for key in ("risk_flags", "safety_risk_flags"):
            if key not in mapping:
                continue
            value = mapping.get(key)
            if value in (None, "", {}):
                continue
            return _as_list(value)
    return None


def _objective_metric_snapshot(fixture: dict[str, Any]) -> dict[str, Any]:
    post_data = _as_dict(fixture.get("post_data"))
    drafts = _as_dict(fixture.get("drafts"))
    analysis = _as_dict(fixture.get("analysis"))
    failures = _provider_failures(post_data, drafts)
    first_failure = _first_provider_failure(failures)

    risk_flags = _safety_risk_flags_result(post_data, analysis)
    summary = _provider_failure_summary(post_data, drafts)
    x_status = str(post_data.get("x_publish_status") or "").strip()
    review_queue_operator_action = str(post_data.get("review_queue_operator_action") or "").strip()
    success = _draft_success(post_data, drafts)
    generation_failed = _draft_generation_failed(post_data, drafts)
    operator_action_required = bool(
        summary.get("operator_action_required")
        or any(_as_bool(failure.get("operator_action_required")) for failure in failures)
        or review_queue_operator_action
        or generation_failed
        or _x_publish_status_requires_action(x_status)
        or not success
    )

    return {
        "success": success,
        "latency_ms": _as_float(
            _first_present(post_data.get("latency_ms"), drafts.get("_latency_ms"), first_failure.get("latency_ms"))
        ),
        "provider": _first_present(
            drafts.get("_provider_used"), post_data.get("provider_used"), first_failure.get("provider")
        ),
        "model": _first_present(drafts.get("_model_used"), post_data.get("model_used"), first_failure.get("model")),
        "token_cost_estimate": _as_float(
            _first_present(
                post_data.get("token_cost_estimate"),
                post_data.get("estimated_cost_usd"),
                drafts.get("_token_cost_estimate"),
            )
        ),
        "final_rank_score": _as_float(
            _first_present(analysis.get("final_rank_score"), post_data.get("final_rank_score"))
        ),
        "draft_quality_score": _draft_quality_score(post_data, drafts),
        "safety_risk_flags": risk_flags,
        "duplicate_or_near_duplicate": _duplicate_or_near_duplicate(post_data, drafts),
        "operator_action_required": operator_action_required,
    }


def _missing_required_signals(signals: dict[str, Any]) -> list[str]:
    missing = []
    for metric in OBJECTIVE_METRICS:
        value = signals.get(metric)
        if metric == "safety_risk_flags" and value == []:
            continue
        if value in (None, "", [], {}):
            missing.append(metric)
    return missing


def _present_signal_count(signals: dict[str, Any]) -> int:
    count = 0
    for metric, value in signals.items():
        if metric == "safety_risk_flags" and value == []:
            count += 1
        elif value not in (None, "", [], {}):
            count += 1
    return count


def _operator_actions(metrics: dict[str, Any], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    post_data = _as_dict(fixture.get("post_data"))
    drafts = _as_dict(fixture.get("drafts"))
    summary = _provider_failure_summary(post_data, drafts)
    failures = _provider_failures(post_data, drafts)
    actions: list[dict[str, Any]] = []

    review_queue_action = str(post_data.get("review_queue_operator_action") or "").strip()
    review_queue_reason = str(post_data.get("review_queue_operator_reason") or "").strip()
    if review_queue_action:
        priority = _as_float(post_data.get("review_queue_priority"))
        action = {
            "action": "review_queue_action",
            "reason": f"{review_queue_action}: {review_queue_reason}" if review_queue_reason else review_queue_action,
            "priority": int(priority if priority is not None else 15),
        }
        for bucket_key in ("error_bucket", "reason_bucket", "triage_bucket"):
            value = str(post_data.get(f"review_queue_{bucket_key}") or "").strip()
            if value:
                action[bucket_key] = value
        actions.append(action)

    primary_action = summary.get("primary_operator_action")
    if primary_action:
        actions.append(
            {
                "action": "repair_provider_access",
                "reason": primary_action,
                "priority": 10,
            }
        )

    for failure in failures:
        failure_action = str(failure.get("operator_action") or "").strip()
        if not failure_action:
            continue
        actions.append(
            {
                "action": "repair_provider_access",
                "provider": failure.get("provider"),
                "reason": failure_action,
                "priority": 20,
            }
        )

    if metrics["operator_action_required"] and not metrics["success"]:
        actions.append(
            {
                "action": "regenerate_draft_after_recovery",
                "reason": "No publishable draft is available for review.",
                "priority": 30,
            }
        )

    x_status = str(post_data.get("x_publish_status") or "").strip()
    if _x_publish_status_requires_action(x_status):
        actions.append(
            {
                "action": "resolve_x_publish_status",
                "reason": x_status or "Missing X publish status",
                "priority": 40,
            }
        )

    if metrics["duplicate_or_near_duplicate"]:
        actions.append(
            {
                "action": "rewrite_duplicate_draft",
                "reason": "Similarity is above the near-duplicate threshold.",
                "priority": 50,
            }
        )

    if metrics["safety_risk_flags"]:
        actions.append(
            {
                "action": "review_risk_flags",
                "reason": ", ".join(str(flag) for flag in metrics["safety_risk_flags"][:3]),
                "priority": 60,
            }
        )

    deduped: dict[tuple[Any, Any], dict[str, Any]] = {}
    for action in actions:
        key = (action.get("action"), action.get("reason"))
        deduped.setdefault(key, action)
    return sorted(deduped.values(), key=lambda item: _priority_value(item.get("priority")))


def _score_variant(signals: dict[str, Any], operator_action_count: int) -> float:
    missing = _missing_required_signals(signals)
    score = _present_signal_count(signals) * 1.5
    score += max(0, 12 - len(missing) * 2)
    if signals.get("operator_action_required"):
        score += 6 if operator_action_count else -6
    if signals.get("safety_risk_flags"):
        score += 2
    if signals.get("duplicate_or_near_duplicate"):
        score += 2
    return round(score, 2)


def _build_variant(name: str, fixture: dict[str, Any], signal_names: tuple[str, ...]) -> dict[str, Any]:
    post_data = _as_dict(fixture.get("post_data"))
    metrics = _objective_metric_snapshot(fixture)
    base_signals = {
        "title": _first_present(post_data.get("title"), post_data.get("source_title")),
        "url": _first_present(post_data.get("url"), post_data.get("source_url")),
        "draft_generation_error": post_data.get("draft_generation_error"),
        "x_publish_status": post_data.get("x_publish_status"),
        **metrics,
    }

    signals = {key: base_signals.get(key) for key in signal_names}
    if "provider_failure_summary" in signal_names:
        signals["provider_failure_summary"] = _provider_failure_summary(post_data, _as_dict(fixture.get("drafts")))

    actions = _operator_actions(metrics, fixture) if "operator_actions" in signal_names else []
    if "operator_actions" in signal_names:
        signals["operator_actions"] = actions

    missing = _missing_required_signals(signals)
    return {
        "name": name,
        "signals": signals,
        "signal_count": _present_signal_count(signals),
        "missing_required_signals": missing,
        "operator_action_count": len(actions),
        "review_efficiency_score": _score_variant(signals, len(actions)),
    }


def _compare_variants(current: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    score_delta = round(candidate["review_efficiency_score"] - current["review_efficiency_score"], 2)
    missing_signal_delta = len(current["missing_required_signals"]) - len(candidate["missing_required_signals"])
    operator_action_delta = candidate["operator_action_count"] - current["operator_action_count"]

    if score_delta >= 4 and missing_signal_delta >= 0:
        recommendation = "adopt_candidate"
    elif score_delta <= -4:
        recommendation = "keep_current"
    else:
        recommendation = "insufficient_evidence"

    return {
        "recommendation": recommendation,
        "score_delta": score_delta,
        "missing_signal_delta": missing_signal_delta,
        "operator_action_delta": operator_action_delta,
    }


def _safety_contract() -> dict[str, bool]:
    return {
        "read_only": True,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }


def build_review_experiment(fixture: dict[str, Any], *, input_source: str = "default_fixture") -> dict[str, Any]:
    """Build a deterministic dry-run comparison report."""
    current = _build_variant("current_review_card", fixture, CURRENT_SIGNALS)
    candidate = _build_variant("candidate_recovery_card", fixture, CANDIDATE_SIGNALS)
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "input_source": input_source,
        "dry_run": True,
        "safety": _safety_contract(),
        "objective_metrics": list(OBJECTIVE_METRICS),
        "variants": {
            "current": current,
            "candidate": candidate,
        },
        "comparison": _compare_variants(current, candidate),
    }


def _review_item_identity(fixture: dict[str, Any], index: int) -> dict[str, Any]:
    post_data = _as_dict(fixture.get("post_data"))
    return {
        "index": index,
        "title": _first_present(post_data.get("title"), post_data.get("source_title"), f"fixture_{index}"),
        "url": _first_present(post_data.get("url"), post_data.get("source_url")),
    }


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def _recommendation_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "adopt_candidate": 0,
        "keep_current": 0,
        "insufficient_evidence": 0,
    }
    for item in items:
        recommendation = item["comparison"]["recommendation"]
        counts[recommendation] = counts.get(recommendation, 0) + 1
    return counts


def _high_noise_items(
    items: list[dict[str, Any]],
    *,
    max_operator_actions_per_item: int = OPERATOR_ACTION_NOISE_THRESHOLD,
) -> list[dict[str, Any]]:
    noisy_items = []
    for item in items:
        action_count = int(item["candidate"]["operator_action_count"])
        if action_count <= max_operator_actions_per_item:
            continue
        noisy_items.append(
            {
                "index": item.get("index"),
                "title": item.get("title"),
                "url": item.get("url"),
                "operator_action_count": action_count,
                "missing_required_signal_count": len(item["candidate"]["missing_required_signals"]),
                "score_delta": item["comparison"]["score_delta"],
            }
        )
    return sorted(
        noisy_items,
        key=lambda item: (
            -int(item["operator_action_count"]),
            -int(item["missing_required_signal_count"]),
            str(item.get("title") or ""),
        ),
    )


def _candidate_missing_metric_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {metric: 0 for metric in OBJECTIVE_METRICS}
    for item in items:
        for metric in item["candidate"]["missing_required_signals"]:
            counts[metric] = counts.get(metric, 0) + 1
    return counts


def _candidate_missing_metric_rates(counts: dict[str, int], item_count: int) -> dict[str, float]:
    if not item_count:
        return {metric: 0.0 for metric in OBJECTIVE_METRICS}
    return {metric: round(counts.get(metric, 0) / item_count, 3) for metric in OBJECTIVE_METRICS}


def _candidate_operator_bucket_counts(items: list[dict[str, Any]], bucket_key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        actions = item["candidate"]["signals"].get("operator_actions")
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            bucket = str(action.get(bucket_key) or "").strip()
            if bucket:
                counts[bucket] += 1
    return dict(sorted(counts.items()))


def _candidate_safety_risk_flag_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        flags = item["candidate"]["signals"].get("safety_risk_flags")
        if not isinstance(flags, list):
            continue
        for flag in flags:
            value = str(flag).strip()
            if value:
                counts[value] += 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _candidate_safety_risk_item_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if _candidate_has_safety_risk_flags(item))


def _candidate_provider_failure_category_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        summary = item["candidate"]["signals"].get("provider_failure_summary")
        if not isinstance(summary, dict):
            continue
        categories = summary.get("categories")
        if not isinstance(categories, dict):
            continue
        for category, count in categories.items():
            key = str(category).strip()
            value = int(_as_float(count) or 0)
            if key and value > 0:
                counts[key] += value
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _candidate_provider_failure_provider_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        summary = item["candidate"]["signals"].get("provider_failure_summary")
        if not isinstance(summary, dict):
            continue
        for provider in _as_list(summary.get("providers_attempted")):
            key = str(provider).strip()
            if key:
                counts[key] += 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _candidate_primary_provider_failure_category_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        summary = item["candidate"]["signals"].get("provider_failure_summary")
        if not isinstance(summary, dict):
            continue
        primary = summary.get("primary_failure")
        if not isinstance(primary, dict):
            continue
        category = str(primary.get("category") or "").strip()
        if category:
            counts[category] += 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _candidate_primary_provider_failure_provider_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        summary = item["candidate"]["signals"].get("provider_failure_summary")
        if not isinstance(summary, dict):
            continue
        primary = summary.get("primary_failure")
        if not isinstance(primary, dict):
            continue
        provider = str(primary.get("provider") or "").strip()
        if provider:
            counts[provider] += 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _candidate_primary_provider_failure_actions(items: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str, str, str, bool, bool]] = Counter()
    for item in items:
        summary = item["candidate"]["signals"].get("provider_failure_summary")
        if not isinstance(summary, dict):
            continue
        primary = summary.get("primary_failure")
        if not isinstance(primary, dict):
            continue
        provider = str(primary.get("provider") or "").strip()
        model = str(primary.get("model") or "").strip()
        category = str(primary.get("category") or "").strip()
        operator_action = (
            str(summary.get("primary_operator_action") or "").strip()
            or str(primary.get("operator_action") or "").strip()
        )
        if not (provider or model or category or operator_action):
            continue
        counts[
            (
                provider or "-",
                model or "-",
                category or "provider_error",
                operator_action or "-",
                _as_bool(primary.get("retryable")),
                _as_bool(primary.get("circuit_breaker_candidate")),
            )
        ] += 1

    actions: list[dict[str, Any]] = []
    for (provider, model, category, operator_action, retryable, circuit_breaker), count in sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0][0], item[0][2], item[0][3]),
    )[:limit]:
        actions.append(
            {
                "provider": provider,
                "model": model,
                "category": category,
                "operator_action": operator_action,
                "retryable": retryable,
                "circuit_breaker_candidate": circuit_breaker,
                "count": count,
            }
        )
    return actions


def _candidate_has_safety_risk_flags(item: dict[str, Any]) -> bool:
    flags = item["candidate"]["signals"].get("safety_risk_flags")
    return isinstance(flags, list) and any(str(flag).strip() for flag in flags)


def _candidate_top_operator_actions(items: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    priorities: dict[str, int] = {}
    reasons: dict[str, Counter[str]] = {}
    for item in items:
        actions = item["candidate"]["signals"].get("operator_actions")
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            action_name = str(action.get("action") or "").strip()
            if not action_name:
                continue
            counts[action_name] += 1
            priority = _priority_value(action.get("priority"))
            priorities[action_name] = min(priority, priorities.get(action_name, priority))
            reason = str(action.get("reason") or "").strip()
            if reason:
                reasons.setdefault(action_name, Counter())[reason] += 1

    top_actions = sorted(counts.items(), key=lambda item: (-item[1], priorities.get(item[0], 999), item[0]))[:limit]
    results: list[dict[str, Any]] = []
    for action_name, count in top_actions:
        reason_counts = reasons.get(action_name) or Counter()
        top_reason = ""
        if reason_counts:
            top_reason = sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        results.append(
            {
                "action": action_name,
                "count": count,
                "priority": priorities.get(action_name, 999),
                "reason": top_reason,
            }
        )
    return results


def _top_missing_metrics(counts: dict[str, int], item_count: int) -> list[dict[str, Any]]:
    metric_order = {metric: index for index, metric in enumerate(OBJECTIVE_METRICS)}
    metrics = [metric for metric, count in counts.items() if count > 0]
    metrics.sort(key=lambda metric: (-counts[metric], metric_order.get(metric, 999), metric))
    return [
        {
            "metric": metric,
            "count": counts[metric],
            "rate": round(counts[metric] / item_count, 3) if item_count else 0.0,
        }
        for metric in metrics[:5]
    ]


def _missing_metric_hint(metric: str, count: int, item_count: int) -> dict[str, Any]:
    hint = MISSING_METRIC_HINTS.get(
        metric,
        {
            "reason": "The objective metric was not exported.",
            "operator_action": f"Include {metric} in review records.",
            "owner": "unknown",
        },
    )
    return {
        "metric": metric,
        "count": count,
        "rate": round(count / item_count, 3) if item_count else 0.0,
        **hint,
    }


def _candidate_missing_metric_hints(counts: dict[str, int], item_count: int) -> dict[str, dict[str, Any]]:
    return {metric: _missing_metric_hint(metric, counts.get(metric, 0), item_count) for metric in OBJECTIVE_METRICS}


def _top_missing_metric_hints(counts: dict[str, int], item_count: int) -> list[dict[str, Any]]:
    return [
        _missing_metric_hint(str(metric["metric"]), int(metric["count"]), item_count)
        for metric in _top_missing_metrics(counts, item_count)
    ]


def _missing_metric_owner_counts(counts: dict[str, int]) -> dict[str, int]:
    owner_counts: Counter[str] = Counter()
    for metric, count in counts.items():
        amount = int(_as_float(count) or 0)
        if amount <= 0:
            continue
        hint = MISSING_METRIC_HINTS.get(metric, {})
        owner = str(hint.get("owner") or "unknown").strip() or "unknown"
        owner_counts[owner] += amount
    return dict(sorted(owner_counts.items(), key=lambda item: (-item[1], item[0])))


def _top_missing_metric_owners(
    counts: dict[str, int],
    item_count: int,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    owner_metrics: dict[str, Counter[str]] = {}
    metric_order = {metric: index for index, metric in enumerate(OBJECTIVE_METRICS)}
    for metric, count in counts.items():
        amount = int(_as_float(count) or 0)
        if amount <= 0:
            continue
        hint = MISSING_METRIC_HINTS.get(metric, {"owner": "unknown"})
        owner = str(hint.get("owner") or "unknown").strip() or "unknown"
        owner_metrics.setdefault(owner, Counter())[metric] += amount

    owner_counts = _missing_metric_owner_counts(counts)
    total_missing_count = sum(owner_counts.values())
    results: list[dict[str, Any]] = []
    for owner, count in list(owner_counts.items())[:limit]:
        metric_counts = owner_metrics.get(owner, Counter())
        metric_name, metric_count = sorted(
            metric_counts.items(),
            key=lambda item: (-item[1], metric_order.get(item[0], 999), item[0]),
        )[0]
        hint = _missing_metric_hint(metric_name, metric_count, item_count)
        results.append(
            {
                "owner": owner,
                "count": count,
                "share": round(count / total_missing_count, 3) if total_missing_count else 0.0,
                "top_metric": metric_name,
                "top_metric_count": metric_count,
                "operator_action": hint["operator_action"],
            }
        )
    return results


def _candidate_experiment_confidence(
    *,
    item_count: int,
    min_item_count: int,
    max_missing_metric_rate: float,
    max_operator_actions_per_item: int,
    adoption_rate: float,
    missing_metric_rate: float,
    average_operator_actions_per_item: float,
    high_noise_item_count: int,
    top_missing_metric_owners: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    issues = []
    if item_count < min_item_count:
        issues.append(
            {
                "code": "sample_size_too_small",
                "reason": "The batch has too few items to trust the candidate adoption rate.",
                "operator_action": f"Run the dry-run with at least {min_item_count} review items.",
            }
        )
    if missing_metric_rate > max_missing_metric_rate:
        owner_issue = _missing_metric_owner_issue(top_missing_metric_owners)
        issues.append(
            {
                "code": "missing_metric_rate_high",
                "reason": "Too many objective metric slots are missing from the candidate evidence.",
                **owner_issue,
            }
        )
    if average_operator_actions_per_item > max_operator_actions_per_item or high_noise_item_count:
        issues.append(
            {
                "code": "operator_action_noise_high",
                "reason": "The candidate card is producing a noisy operator action queue.",
                "operator_action": "Reduce or group candidate operator actions before rollout.",
            }
        )

    return {
        "level": "needs_more_evidence" if issues else "actionable",
        "operator_action_required": bool(issues),
        "min_item_count": min_item_count,
        "max_missing_metric_rate": max_missing_metric_rate,
        "max_average_operator_actions_per_item": max_operator_actions_per_item,
        "observed_item_count": item_count,
        "observed_adoption_rate": adoption_rate,
        "observed_missing_metric_rate": missing_metric_rate,
        "observed_average_operator_actions_per_item": average_operator_actions_per_item,
        "issues": issues,
    }


def _missing_metric_owner_issue(top_missing_metric_owners: list[dict[str, Any]] | None) -> dict[str, Any]:
    generic_action = "Fill the top missing metrics before using this experiment as adoption evidence."
    if not top_missing_metric_owners:
        return {"operator_action": generic_action}

    top_owner = top_missing_metric_owners[0]
    if not isinstance(top_owner, dict):
        return {"operator_action": generic_action}

    owner = str(top_owner.get("owner") or "").strip()
    top_metric = str(top_owner.get("top_metric") or "").strip()
    owner_action = str(top_owner.get("operator_action") or "").strip()
    if not owner or not owner_action:
        return {"operator_action": generic_action}

    return {
        "operator_action": f"{owner}: {owner_action}",
        "owner": owner,
        "owner_count": int(_as_float(top_owner.get("count")) or 0),
        "top_metric": top_metric or "-",
        "top_metric_count": int(_as_float(top_owner.get("top_metric_count")) or 0),
        "owner_operator_action": owner_action,
    }


def _candidate_rollout_gate(confidence: dict[str, Any], safety: dict[str, bool]) -> dict[str, Any]:
    blockers = [str(issue.get("code")) for issue in confidence.get("issues", []) if issue.get("code")]
    safety_blockers = [
        code
        for code, blocked in (
            ("not_read_only", not safety.get("read_only")),
            ("notion_writes_enabled", safety.get("notion_writes")),
            ("x_posts_enabled", safety.get("x_posts")),
            ("auto_publish_enabled", safety.get("auto_publish_default")),
            ("manual_publish_not_required", not safety.get("manual_publish_required")),
        )
        if blocked
    ]
    blockers.extend(safety_blockers)
    return {
        "candidate_ready_for_rollout": not blockers,
        "candidate_rollout_blockers": blockers,
        "candidate_rollout_blocker_actions": _candidate_rollout_blocker_actions(confidence, safety),
        "candidate_rollout_reason": _candidate_rollout_reason(blockers, confidence),
    }


def _candidate_rollout_blocker_actions(confidence: dict[str, Any], safety: dict[str, bool]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for issue in confidence.get("issues", []):
        if not isinstance(issue, dict):
            continue
        code = str(issue.get("code") or "").strip()
        if not code:
            continue
        action = str(issue.get("operator_action") or "").strip()
        item: dict[str, Any] = {
            "code": code,
            "source": "confidence",
            "operator_action": action or ROLLOUT_BLOCKER_REASONS.get(code, f"resolve {code} before rollout"),
        }
        reason = str(issue.get("reason") or "").strip()
        if reason:
            item["reason"] = reason
        for key in ("owner", "owner_count", "top_metric", "top_metric_count", "owner_operator_action"):
            if key in issue:
                item[key] = issue[key]
        actions.append(item)

    safety_blockers = (
        ("not_read_only", not safety.get("read_only")),
        ("notion_writes_enabled", safety.get("notion_writes")),
        ("x_posts_enabled", safety.get("x_posts")),
        ("auto_publish_enabled", safety.get("auto_publish_default")),
        ("manual_publish_not_required", not safety.get("manual_publish_required")),
    )
    for code, blocked in safety_blockers:
        if not blocked:
            continue
        actions.append(
            {
                "code": code,
                "source": "safety",
                "operator_action": ROLLOUT_BLOCKER_REASONS.get(code, f"resolve {code} before rollout"),
            }
        )
    return actions


def _candidate_rollout_reason(blockers: list[str], confidence: dict[str, Any]) -> str:
    if not blockers:
        return "ready: confidence and safety gates passed"

    primary = blockers[0]
    reason = ROLLOUT_BLOCKER_REASONS.get(primary, f"resolve {primary} before rollout")
    if primary == "sample_size_too_small":
        reason = f"run the dry-run with at least {confidence.get('min_item_count')} review items"
    if len(blockers) == 1:
        return f"blocked: {reason}"
    return f"blocked: {reason}; additional blockers: {len(blockers) - 1}"


def _summarize_batch_items(
    items: list[dict[str, Any]],
    *,
    min_item_count: int = MIN_CONFIDENT_EXPERIMENT_ITEMS,
    max_missing_metric_rate: float = MAX_CONFIDENT_MISSING_METRIC_RATE,
    max_operator_actions_per_item: int = OPERATOR_ACTION_NOISE_THRESHOLD,
) -> dict[str, Any]:
    recommendation_counts = _recommendation_counts(items)
    score_deltas = [float(item["comparison"]["score_delta"]) for item in items]
    missing_signal_deltas = [float(item["comparison"]["missing_signal_delta"]) for item in items]
    operator_action_deltas = [float(item["comparison"]["operator_action_delta"]) for item in items]
    current_scores = [float(item["current"]["review_efficiency_score"]) for item in items]
    candidate_scores = [float(item["candidate"]["review_efficiency_score"]) for item in items]
    candidate_operator_actions = [float(item["candidate"]["operator_action_count"]) for item in items]
    candidate_missing_metric_count = sum(len(item["candidate"]["missing_required_signals"]) for item in items)

    item_count = len(items)
    adoption_count = recommendation_counts.get("adopt_candidate", 0)
    total_metric_slots = item_count * len(OBJECTIVE_METRICS)
    high_noise_items = _high_noise_items(items, max_operator_actions_per_item=max_operator_actions_per_item)
    missing_metric_counts = _candidate_missing_metric_counts(items)
    missing_metric_owner_counts = _missing_metric_owner_counts(missing_metric_counts)
    top_missing_metric_owners = _top_missing_metric_owners(missing_metric_counts, item_count)
    safety_risk_flag_counts = _candidate_safety_risk_flag_counts(items)
    provider_failure_category_counts = _candidate_provider_failure_category_counts(items)
    provider_failure_provider_counts = _candidate_provider_failure_provider_counts(items)
    primary_provider_failure_category_counts = _candidate_primary_provider_failure_category_counts(items)
    primary_provider_failure_provider_counts = _candidate_primary_provider_failure_provider_counts(items)
    primary_provider_failure_actions = _candidate_primary_provider_failure_actions(items)
    adoption_rate = round(adoption_count / item_count, 3) if item_count else 0.0
    average_operator_actions_per_item = _average(candidate_operator_actions)
    missing_metric_rate = round(candidate_missing_metric_count / total_metric_slots, 3) if total_metric_slots else 0.0
    confidence = _candidate_experiment_confidence(
        item_count=item_count,
        min_item_count=min_item_count,
        max_missing_metric_rate=max_missing_metric_rate,
        max_operator_actions_per_item=max_operator_actions_per_item,
        adoption_rate=adoption_rate,
        missing_metric_rate=missing_metric_rate,
        average_operator_actions_per_item=average_operator_actions_per_item,
        high_noise_item_count=len(high_noise_items),
        top_missing_metric_owners=top_missing_metric_owners,
    )
    return {
        "item_count": item_count,
        "recommendation_counts": recommendation_counts,
        "candidate_adoption_rate": adoption_rate,
        "average_score_delta": _average(score_deltas),
        "average_missing_signal_delta": _average(missing_signal_deltas),
        "average_operator_action_delta": _average(operator_action_deltas),
        "average_current_review_efficiency_score": _average(current_scores),
        "average_candidate_review_efficiency_score": _average(candidate_scores),
        "candidate_operator_action_total": int(sum(candidate_operator_actions)),
        "average_operator_actions_per_item": average_operator_actions_per_item,
        "max_operator_actions_per_item": int(max(candidate_operator_actions, default=0)),
        "operator_action_noise_threshold": max_operator_actions_per_item,
        "high_noise_item_count": len(high_noise_items),
        "high_noise_items": high_noise_items[:5],
        "candidate_missing_metric_count": candidate_missing_metric_count,
        "candidate_total_metric_slots": total_metric_slots,
        "candidate_missing_metric_rate": missing_metric_rate,
        "candidate_missing_metric_counts": missing_metric_counts,
        "candidate_missing_metric_rates": _candidate_missing_metric_rates(missing_metric_counts, item_count),
        "candidate_missing_metric_owner_counts": missing_metric_owner_counts,
        "candidate_top_missing_metric_owners": top_missing_metric_owners,
        "candidate_operator_error_bucket_counts": _candidate_operator_bucket_counts(items, "error_bucket"),
        "candidate_operator_reason_bucket_counts": _candidate_operator_bucket_counts(items, "reason_bucket"),
        "candidate_operator_triage_bucket_counts": _candidate_operator_bucket_counts(items, "triage_bucket"),
        "candidate_safety_risk_item_count": _candidate_safety_risk_item_count(items),
        "candidate_safety_risk_flag_counts": safety_risk_flag_counts,
        "candidate_provider_failure_category_counts": provider_failure_category_counts,
        "candidate_provider_failure_provider_counts": provider_failure_provider_counts,
        "candidate_primary_provider_failure_category_counts": primary_provider_failure_category_counts,
        "candidate_primary_provider_failure_provider_counts": primary_provider_failure_provider_counts,
        "candidate_primary_provider_failure_actions": primary_provider_failure_actions,
        "candidate_top_operator_actions": _candidate_top_operator_actions(items),
        "candidate_top_missing_metrics": _top_missing_metrics(missing_metric_counts, item_count),
        "candidate_missing_metric_hints": _candidate_missing_metric_hints(missing_metric_counts, item_count),
        "candidate_top_missing_metric_hints": _top_missing_metric_hints(missing_metric_counts, item_count),
        "candidate_experiment_confidence": confidence,
        **_candidate_rollout_gate(confidence, _safety_contract()),
    }


def build_review_experiment_batch(
    fixtures: list[dict[str, Any]],
    *,
    input_source: str = "default_fixture",
    min_item_count: int = MIN_CONFIDENT_EXPERIMENT_ITEMS,
    max_missing_metric_rate: float = MAX_CONFIDENT_MISSING_METRIC_RATE,
    max_operator_actions_per_item: int = OPERATOR_ACTION_NOISE_THRESHOLD,
) -> dict[str, Any]:
    """Build a deterministic multi-item dry-run comparison report."""
    items: list[dict[str, Any]] = []
    for index, fixture in enumerate(fixtures, start=1):
        report = build_review_experiment(fixture, input_source=f"{input_source}#{index}")
        items.append(
            {
                **_review_item_identity(fixture, index),
                "current": report["variants"]["current"],
                "candidate": report["variants"]["candidate"],
                "comparison": report["comparison"],
            }
        )

    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "input_source": input_source,
        "dry_run": True,
        "batch": True,
        "safety": _safety_contract(),
        "objective_metrics": list(OBJECTIVE_METRICS),
        "summary": _summarize_batch_items(
            items,
            min_item_count=min_item_count,
            max_missing_metric_rate=max_missing_metric_rate,
            max_operator_actions_per_item=max_operator_actions_per_item,
        ),
        "items": items,
    }


def _load_json_file(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def _review_record_key(record: dict[str, Any], index: int) -> str:
    key = _first_record_value(record, ("page_id", "id", "page_url", "url", "source_url", "target_hint"))
    if key:
        return str(key)
    title = str(_first_record_value(record, ("title", "source_title")) or "").strip()
    status = str(record.get("x_publish_status") or "").strip()
    action = str(record.get("action") or "").strip()
    return f"record:{title}:{status}:{action}:{index}"


def _merge_review_record(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if value in (None, "", [], {}):
            continue
        current = merged.get(key)
        if current in (None, "", [], {}):
            merged[key] = value
        elif key in {"risk_flags", "rejection_reasons"}:
            merged[key] = _as_list(current) + [item for item in _as_list(value) if item not in _as_list(current)]
    return merged


def _review_records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        raw_records = payload
    elif isinstance(payload, dict):
        raw_records = []
        for key in REVIEW_RECORD_COLLECTION_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                raw_records.extend(value)
    else:
        raise ValueError("review record input must be a JSON object or array")

    records: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(raw_records, start=1):
        if not isinstance(record, dict):
            continue
        key = _review_record_key(record, index)
        records[key] = _merge_review_record(records[key], record) if key in records else dict(record)
    return list(records.values())


def review_records_to_fixtures(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for record in records:
        title = _first_record_value(record, ("title", "source_title"))
        url = _first_record_value(record, ("url", "source_url", "page_url", "target_hint"))
        tweet_body = _first_record_value(record, ("tweet_body", "twitter", "x_body", "draft_text"))
        x_error = _first_record_value(record, ("x_publish_error", "draft_generation_error", "error"))
        final_rank_score = _first_record_value(record, ("final_rank_score", "rank_score"))
        quality_score = _first_record_value(record, ("draft_quality_score", "quality_gate_score"))
        duplicate_flag = _first_record_value(record, ("duplicate_or_near_duplicate", "is_duplicate"))
        similarity = _first_record_value(record, ("max_semantic_similarity", "semantic_similarity"))
        risk_flags = _safety_risk_flags_result(record)
        provider_failure_summary = _first_record_value(
            record,
            ("draft_provider_failure_summary", "provider_failure_summary", "_provider_failure_summary"),
        )
        provider_failures = _first_record_value(
            record,
            ("draft_provider_failures", "provider_failures", "_provider_failures"),
        )

        post_data = {
            "title": title,
            "url": url,
            "page_id": _first_record_value(record, ("page_id", "id")),
            "x_publish_status": record.get("x_publish_status"),
            "draft_generation_error": x_error,
            "provider_used": _first_record_value(record, ("provider", "provider_used")),
            "model_used": _first_record_value(record, ("model", "model_used")),
            "latency_ms": record.get("latency_ms"),
            "token_cost_estimate": _first_record_value(record, ("token_cost_estimate", "estimated_cost_usd")),
            "final_rank_score": final_rank_score,
            "draft_quality_score": quality_score,
            "risk_flags": risk_flags,
            "rejection_reasons": record.get("rejection_reasons"),
            "review_focus": record.get("review_focus"),
            "feedback_request": record.get("feedback_request"),
            "memo": record.get("memo"),
            "review_queue_operator_action": record.get("action"),
            "review_queue_operator_reason": _first_record_value(record, ("reason", "triage_hint")),
            "review_queue_priority": record.get("priority"),
            "review_queue_error_bucket": record.get("error_bucket"),
            "review_queue_reason_bucket": record.get("reason_bucket"),
            "review_queue_triage_bucket": record.get("triage_bucket"),
            "duplicate_or_near_duplicate": duplicate_flag,
            "max_semantic_similarity": similarity,
        }
        if isinstance(provider_failure_summary, dict):
            post_data["draft_provider_failure_summary"] = provider_failure_summary
        if isinstance(provider_failures, list):
            post_data["draft_provider_failures"] = provider_failures
        drafts = {
            "twitter": tweet_body,
            "_provider_used": _first_record_value(record, ("provider", "provider_used")),
            "_model_used": _first_record_value(record, ("model", "model_used")),
            "_quality_gate_score": quality_score,
            "_max_semantic_similarity": similarity,
        }
        analysis = {
            "selection_summary": record.get("selection_summary"),
            "final_rank_score": final_rank_score,
            "risk_flags": risk_flags,
        }
        fixtures.append({"post_data": post_data, "drafts": drafts, "analysis": analysis})
    return fixtures


def load_review_record_fixtures(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None:
        raise ValueError("--input is required when --input-mode=review-records")
    payload = _load_json_file(path)
    records = _review_records_from_payload(payload)
    return review_records_to_fixtures(records), str(path)


def load_fixture(path: Path | None) -> tuple[dict[str, Any], str]:
    if path is None:
        return json.loads(json.dumps(DEFAULT_FIXTURE)), "default_fixture"
    payload = _load_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError("review experiment input must be a JSON object")
    return payload, str(path)


def load_fixtures(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None:
        return [json.loads(json.dumps(DEFAULT_FIXTURE))], "default_fixture"
    payload = _load_json_file(path)

    if isinstance(payload, list):
        fixtures = payload
    elif isinstance(payload, dict):
        candidate = _first_present(payload.get("fixtures"), payload.get("records"), payload.get("items"))
        fixtures = candidate if isinstance(candidate, list) else [payload]
    else:
        raise ValueError("review experiment batch input must be a JSON object or array")

    if not all(isinstance(item, dict) for item in fixtures):
        raise ValueError("review experiment batch items must be JSON objects")
    return fixtures, str(path)


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _format_batch_console_summary(report: dict[str, Any], destination: str) -> str:
    summary = report["summary"]
    top_action = _console_top_operator_action(summary.get("candidate_top_operator_actions"))
    safety_flags = _format_compact_counts(summary.get("candidate_safety_risk_flag_counts"))
    provider_failure_categories = _format_compact_counts(summary.get("candidate_provider_failure_category_counts"))
    provider_failure_providers = _format_compact_counts(summary.get("candidate_provider_failure_provider_counts"))
    primary_failure_categories = _format_compact_counts(
        summary.get("candidate_primary_provider_failure_category_counts")
    )
    primary_failure_providers = _format_compact_counts(
        summary.get("candidate_primary_provider_failure_provider_counts")
    )
    top_missing_metric = _console_top_missing_metric(summary.get("candidate_top_missing_metrics"))
    top_missing_owner = _console_top_missing_metric_owner(summary.get("candidate_top_missing_metric_owners"))
    rollout_blockers = _console_rollout_blocker_actions(summary.get("candidate_rollout_blocker_actions"))
    top_rollout_blocker = rollout_blockers["top"]
    return (
        "review_experiment_dry_run="
        f"{destination} batch_items={summary['item_count']} "
        f"adoption_rate={summary['candidate_adoption_rate']} "
        f"avg_score_delta={summary['average_score_delta']} "
        f"missing_metric_rate={summary.get('candidate_missing_metric_rate', 0.0)} "
        f"top_missing_metric={top_missing_metric['metric']} "
        f"top_missing_metric_count={top_missing_metric['count']} "
        f"top_missing_owner={top_missing_owner['owner']} "
        f"top_missing_owner_count={top_missing_owner['count']} "
        f"top_missing_owner_metric={top_missing_owner['top_metric']} "
        f"top_missing_owner_action={top_missing_owner['operator_action']} "
        f"operator_actions_total={summary['candidate_operator_action_total']} "
        f"avg_operator_actions={summary['average_operator_actions_per_item']} "
        f"high_noise_items={summary['high_noise_item_count']} "
        f"safety_risk_items={summary.get('candidate_safety_risk_item_count', 0)} "
        f"safety_risk_flags={safety_flags} "
        f"provider_failure_categories={provider_failure_categories} "
        f"provider_failure_providers={provider_failure_providers} "
        f"primary_provider_failure_categories={primary_failure_categories} "
        f"primary_provider_failure_providers={primary_failure_providers} "
        f"top_operator_action={top_action['action']} "
        f"top_operator_action_count={top_action['count']} "
        f"top_operator_action_reason={top_action['reason']} "
        f"rollout_blocker_count={rollout_blockers['count']} "
        f"rollout_blocker_codes={rollout_blockers['codes']} "
        f"top_rollout_blocker_code={top_rollout_blocker['code']} "
        f"top_rollout_blocker_source={top_rollout_blocker['source']} "
        f"top_rollout_blocker_owner={top_rollout_blocker['owner']} "
        f"top_rollout_blocker_metric={top_rollout_blocker['top_metric']} "
        f"top_rollout_blocker_action={top_rollout_blocker['operator_action']} "
        f"ready_for_rollout={summary['candidate_ready_for_rollout']} "
        f"rollout_reason={summary['candidate_rollout_reason']}"
    )


def _format_single_console_summary(report: dict[str, Any], destination: str) -> str:
    recommendation = report["comparison"]["recommendation"]
    score_delta = report["comparison"]["score_delta"]
    candidate = report["variants"]["candidate"]
    top_action = _console_top_operator_action(candidate["signals"].get("operator_actions"))
    return (
        f"review_experiment_dry_run={destination} "
        f"recommendation={recommendation} score_delta={score_delta} "
        f"operator_action_count={candidate['operator_action_count']} "
        f"top_operator_action={top_action['action']} "
        f"top_operator_action_count={top_action['count']} "
        f"top_operator_action_reason={top_action['reason']} "
        "ready_for_rollout=False "
        "rollout_reason=blocked: run batch dry-run for rollout confidence"
    )


def _console_top_operator_action(actions: Any) -> dict[str, Any]:
    if not isinstance(actions, list):
        return {"action": "-", "count": 0, "reason": "-"}
    if actions and isinstance(actions[0], dict) and "count" in actions[0]:
        item = actions[0]
        return {
            "action": str(item.get("action") or "-"),
            "count": item.get("count", 0),
            "reason": str(item.get("reason") or "-"),
        }
    counts: Counter[str] = Counter()
    reasons: dict[str, Counter[str]] = {}
    priorities: dict[str, int] = {}
    for item in actions:
        if not isinstance(item, dict):
            continue
        action_name = str(item.get("action") or "").strip()
        if not action_name:
            continue
        counts[action_name] += 1
        priority = _priority_value(item.get("priority"))
        priorities[action_name] = min(priority, priorities.get(action_name, priority))
        reason = str(item.get("reason") or "").strip()
        if reason:
            reasons.setdefault(action_name, Counter())[reason] += 1
    if not counts:
        return {"action": "-", "count": 0, "reason": "-"}
    action_name, count = sorted(counts.items(), key=lambda item: (-item[1], priorities.get(item[0], 999), item[0]))[0]
    reason_counts = reasons.get(action_name) or Counter()
    reason = "-"
    if reason_counts:
        reason = sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {"action": action_name, "count": count, "reason": reason}


def _console_top_missing_metric(metrics: Any) -> dict[str, Any]:
    if not isinstance(metrics, list):
        return {"metric": "-", "count": 0}
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        name = str(metric.get("metric") or "").strip()
        if name:
            return {"metric": name, "count": metric.get("count", 0)}
    return {"metric": "-", "count": 0}


def _console_top_missing_metric_owner(owners: Any) -> dict[str, Any]:
    if not isinstance(owners, list):
        return {"owner": "-", "count": 0, "top_metric": "-", "operator_action": "-"}
    for owner in owners:
        if not isinstance(owner, dict):
            continue
        name = str(owner.get("owner") or "").strip()
        if name:
            return {
                "owner": name,
                "count": owner.get("count", 0),
                "top_metric": str(owner.get("top_metric") or "-"),
                "operator_action": str(owner.get("operator_action") or "-"),
            }
    return {"owner": "-", "count": 0, "top_metric": "-", "operator_action": "-"}


def _console_rollout_blocker_actions(actions: Any) -> dict[str, Any]:
    top = _empty_console_rollout_blocker_action()
    if not isinstance(actions, list):
        return {"count": 0, "codes": "-", "top": top}
    codes = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        code = str(action.get("code") or "").strip()
        if not code:
            continue
        codes.append(code)
        if top["code"] == "-":
            top = _console_rollout_blocker_action(action, code)
    return {
        "count": len(codes),
        "codes": ",".join(codes) if codes else "-",
        "top": top,
    }


def _empty_console_rollout_blocker_action() -> dict[str, Any]:
    return {"code": "-", "source": "-", "owner": "-", "top_metric": "-", "operator_action": "-"}


def _console_rollout_blocker_action(action: dict[str, Any], code: str) -> dict[str, Any]:
    return {
        "code": code,
        "source": str(action.get("source") or "-"),
        "owner": str(action.get("owner") or "-"),
        "top_metric": str(action.get("top_metric") or "-"),
        "operator_action": str(action.get("operator_action") or "-"),
    }


def _format_compact_counts(counts: Any) -> str:
    if not isinstance(counts, dict):
        return "-"
    parts = [f"{key}={value}" for key, value in sorted(counts.items(), key=lambda item: str(item[0]))]
    return ",".join(parts) if parts else "-"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return parsed


def _rate_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0 or parsed > 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run A/B report for Notion review-card signal changes")
    parser.add_argument("--input", type=Path, help="Optional JSON fixture with post_data, drafts, and analysis")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSON output path")
    parser.add_argument(
        "--input-mode",
        choices=("fixture", "review-records"),
        default="fixture",
        help="Input JSON shape: normalized fixtures or review queue records/report export",
    )
    parser.add_argument("--batch", action="store_true", help="Treat input as a list of review fixtures and aggregate")
    parser.add_argument(
        "--min-items",
        type=_positive_int,
        default=MIN_CONFIDENT_EXPERIMENT_ITEMS,
        help="Minimum batch item count required before rollout confidence can be actionable",
    )
    parser.add_argument(
        "--max-missing-rate",
        type=_rate_float,
        default=MAX_CONFIDENT_MISSING_METRIC_RATE,
        help="Maximum objective metric missing rate allowed before rollout confidence is blocked",
    )
    parser.add_argument(
        "--max-operator-actions",
        type=_non_negative_int,
        default=OPERATOR_ACTION_NOISE_THRESHOLD,
        help="Maximum average and per-item candidate operator action count allowed before rollout confidence is blocked",
    )
    parser.add_argument("--json", action="store_true", help="Print the report JSON to stdout")
    parser.add_argument("--no-write", action="store_true", help="Build the report without writing an output file")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print the console summary without writing the JSON report",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.input_mode == "review-records":
        fixtures, input_source = load_review_record_fixtures(args.input)
        report = build_review_experiment_batch(
            fixtures,
            input_source=input_source,
            min_item_count=args.min_items,
            max_missing_metric_rate=args.max_missing_rate,
            max_operator_actions_per_item=args.max_operator_actions,
        )
    elif args.batch:
        fixtures, input_source = load_fixtures(args.input)
        report = build_review_experiment_batch(
            fixtures,
            input_source=input_source,
            min_item_count=args.min_items,
            max_missing_metric_rate=args.max_missing_rate,
            max_operator_actions_per_item=args.max_operator_actions,
        )
    else:
        fixture, input_source = load_fixture(args.input)
        report = build_review_experiment(fixture, input_source=input_source)

    skip_write = args.no_write or args.summary_only
    suppression_flags = []
    if args.no_write:
        suppression_flags.append("no_write")
    if args.summary_only:
        suppression_flags.append("summary_only")
    report["output"] = {
        "path": str(args.output),
        "written": not skip_write,
        "write_suppressed": skip_write,
        "suppression_flags": suppression_flags,
    }

    if not skip_write:
        write_report(report, args.output)

    if args.json:
        print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    else:
        destination = "(not written)" if skip_write else str(args.output)
        if report.get("batch"):
            print(_format_batch_console_summary(report, destination))
        else:
            print(_format_single_console_summary(report, destination))

    return 0


if __name__ == "__main__":
    sys.exit(main())
