from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import json
import logging
from pathlib import Path
import sys

BTX_ROOT = Path(__file__).resolve().parent.parent
if str(BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(BTX_ROOT))

ConfigManager = None
FeedbackLoop = None
NotionUploader = None

logger = logging.getLogger(__name__)


def _load_live_report_dependencies():
    global ConfigManager, FeedbackLoop, NotionUploader

    if ConfigManager is None:
        from config import ConfigManager as imported_config_manager

        ConfigManager = imported_config_manager
    if FeedbackLoop is None:
        from pipeline.feedback_loop import FeedbackLoop as imported_feedback_loop

        FeedbackLoop = imported_feedback_loop
    if NotionUploader is None:
        from pipeline.notion_upload import NotionUploader as imported_notion_uploader

        NotionUploader = imported_notion_uploader
    return ConfigManager, FeedbackLoop, NotionUploader


def _as_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value) -> str:
    number = _as_float(value)
    if number is None:
        return "-"
    if abs(number - round(number)) < 0.0001:
        return str(int(round(number)))
    return f"{number:.2f}"


def _format_percent(value) -> str:
    number = _as_float(value)
    if number is None:
        return "-"
    return f"{number * 100:.1f}%"


def _format_usd(value) -> str:
    number = _as_float(value)
    return "-" if number is None else f"${number:.4f}"


def _format_ms(value) -> str:
    number = _as_float(value)
    return "-" if number is None else f"{number:.1f}ms"


def _format_bool(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "-"


def _count_sort_value(value) -> float:
    number = _as_float(value)
    return number if number is not None else 0.0


def _format_counts(counts: dict | Counter, *, limit: int = 4) -> str:
    if not counts:
        return "-"
    if isinstance(counts, Counter):
        items = counts.most_common(limit)
    else:
        items = sorted(counts.items(), key=lambda item: (-_count_sort_value(item[1]), str(item[0])))[:limit]
    return ", ".join(f"{label}={count}" for label, count in items) if items else "-"


def _format_flags(flags) -> str:
    if not isinstance(flags, (list, tuple)):
        return "-"
    values = [str(flag).strip() for flag in flags if str(flag).strip()]
    return ", ".join(values) if values else "-"


def _repair_remaining_count(manual_ready_gate: dict) -> int:
    remaining = manual_ready_gate.get("repair_command_remaining_count")
    if isinstance(remaining, int) and not isinstance(remaining, bool):
        return max(0, remaining)
    count = manual_ready_gate.get("repair_command_count")
    if isinstance(count, int) and not isinstance(count, bool):
        return max(0, count - 1)
    commands = manual_ready_gate.get("repair_commands")
    if isinstance(commands, list):
        return max(0, len(commands) - 1)
    return 0


_SOURCE_STRATEGY_BLOCKER_ACTIONS = {
    "invalid_evidence": "inspect source strategy JSON before review",
    "repair_evidence_first": "run evidence doctor before strategy review",
    "repair_command_debt": "run top repair commands before strategy review",
    "fallback_only_sources_present": "use ready fallback sources; keep strategy manual",
    "no_problem_actions": "collect or inspect local preflight evidence",
}

_SOURCE_STRATEGY_BLOCKER_COUNT_KEYS = {
    "invalid_evidence": ("invalid_evidence", "error"),
    "repair_evidence_first": ("fix_evidence_first", "repair_evidence_first"),
    "repair_command_debt": ("repair_command_count",),
    "fallback_only_sources_present": ("fallback_only",),
}

_SOURCE_STRATEGY_OBJECTIVE_METRICS = (
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


def _source_strategy_blocked_checklist(blocked_by: list, gate_counts: dict) -> str:
    items = []
    seen = set()
    for value in blocked_by:
        blocker = str(value or "").strip()
        if not blocker or blocker in seen:
            continue
        seen.add(blocker)
        action = _SOURCE_STRATEGY_BLOCKER_ACTIONS.get(blocker, "inspect rollout_gate.operator_action")
        count = None
        for key in _SOURCE_STRATEGY_BLOCKER_COUNT_KEYS.get(blocker, ()):
            if key in gate_counts:
                count = gate_counts.get(key)
                break
        prefix = f"{blocker}={count}" if count not in (None, "") else blocker
        items.append(f"{prefix}: {action}")
    return " | ".join(items)


def _source_strategy_missing_metric_count(summary: dict, variant: dict, variant_name: str) -> int:
    counts = summary.get("missing_metric_counts")
    if isinstance(counts, dict):
        try:
            return max(0, int(counts.get(variant_name) or 0))
        except (TypeError, ValueError):
            pass
    compact_counts = _source_strategy_compact_metric_counts(summary)
    if variant_name in compact_counts:
        return compact_counts[variant_name]
    missing = variant.get("missing_required_metrics")
    return len(missing) if isinstance(missing, list) else 0


def _source_strategy_compact_metric_counts(summary: dict) -> dict[str, int]:
    value = summary.get("metric_missing")
    if not isinstance(value, str):
        return {}
    parsed: dict[str, int] = {}
    for item in value.split(","):
        name, separator, fraction = item.strip().partition(":")
        if not separator:
            continue
        count_text = fraction.partition("/")[0].strip()
        try:
            parsed[name.strip()] = max(0, int(count_text))
        except (TypeError, ValueError):
            continue
    return parsed


def _source_strategy_metric_total(simulation: dict) -> int:
    summary = simulation.get("summary") if isinstance(simulation.get("summary"), dict) else {}
    try:
        metric_total = int(summary.get("metric_total") or 0)
    except (TypeError, ValueError):
        metric_total = 0
    if metric_total > 0:
        return metric_total
    objective_metrics = simulation.get("objective_metrics")
    if isinstance(objective_metrics, list) and objective_metrics:
        return len(objective_metrics)
    return len(_SOURCE_STRATEGY_OBJECTIVE_METRICS)


def _source_strategy_measurement_scope(
    summary: dict,
    current: dict,
    candidate: dict,
    current_signals: dict,
    candidate_signals: dict,
) -> dict:
    scope = summary.get("measurement_scope")
    if isinstance(scope, dict):
        return scope

    providers = {str(current_signals.get("provider") or ""), str(candidate_signals.get("provider") or "")}
    if providers != {"source_preflight"}:
        return {}

    missing_names = []
    for metric in ("latency_ms", "draft_quality_score"):
        if any(metric in (variant.get("missing_required_metrics") or []) for variant in (current, candidate)):
            missing_names.append(metric)

    return {
        "mode": "local_preflight_evidence_legacy",
        "external_llm_calls": False,
        "costed_generation": False,
        "not_measured_metrics": missing_names,
    }


def _first_operator_action(items) -> str:
    if not isinstance(items, list):
        return ""
    for item in items:
        if not isinstance(item, dict):
            continue
        action = str(item.get("operator_action") or "").strip()
        if action:
            return action
    return ""


def _review_experiment_next_action(summary: dict | None, safety: dict) -> str:
    if safety.get("read_only") is False:
        return "Restore the dry-run read-only safety contract before using this evidence."
    if safety.get("notion_writes") or safety.get("x_posts"):
        return "Disable Notion writes and X posting for the review experiment dry-run."
    if safety.get("auto_publish_default"):
        return "Keep auto-publish disabled; require manual publish approval."
    if safety.get("manual_publish_required") is False:
        return "Require manual publish approval before rollout."
    if not isinstance(summary, dict):
        return ""

    confidence = summary.get("candidate_experiment_confidence")
    if isinstance(confidence, dict):
        action = _first_operator_action(confidence.get("issues"))
        if action:
            return action

    action = _first_operator_action(summary.get("candidate_top_missing_metric_hints"))
    if action:
        return action

    if summary.get("candidate_ready_for_rollout") is True:
        return "Review the candidate card manually, then keep publish approval manual."
    return ""


def _variant_signal_stats(experiment: dict, variant_name: str) -> dict:
    variants = []
    items = experiment.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and isinstance(item.get(variant_name), dict):
                variants.append(item[variant_name])
    elif isinstance(experiment.get("variants"), dict) and isinstance(experiment["variants"].get(variant_name), dict):
        variants.append(experiment["variants"][variant_name])

    providers: Counter[str] = Counter()
    models: Counter[str] = Counter()
    latencies: list[float] = []
    costs: list[float] = []
    operator_action_total = 0

    for variant in variants:
        signals = variant.get("signals") if isinstance(variant.get("signals"), dict) else {}
        provider = str(signals.get("provider") or "").strip()
        model = str(signals.get("model") or "").strip()
        latency = _as_float(signals.get("latency_ms"))
        cost = _as_float(signals.get("token_cost_estimate"))
        if provider:
            providers[provider] += 1
        if model:
            models[model] += 1
        if latency is not None:
            latencies.append(latency)
        if cost is not None:
            costs.append(cost)
        operator_action_total += int(_as_float(variant.get("operator_action_count")) or 0)

    return {
        "providers": providers,
        "models": models,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "avg_cost_usd": sum(costs) / len(costs) if costs else None,
        "operator_action_total": operator_action_total,
    }


def _render_review_experiment_section(experiment: dict | None) -> str:
    if not isinstance(experiment, dict):
        return ""

    summary = experiment.get("summary") if isinstance(experiment.get("summary"), dict) else None
    comparison = experiment.get("comparison") if isinstance(experiment.get("comparison"), dict) else None
    variants = experiment.get("variants") if isinstance(experiment.get("variants"), dict) else None
    if summary is None and comparison is None:
        return ""

    safety = experiment.get("safety") if isinstance(experiment.get("safety"), dict) else {}
    current = _variant_signal_stats(experiment, "current")
    candidate = _variant_signal_stats(experiment, "candidate")

    lines = [
        "",
        "## Review Experiment A/B Summary (dry-run)",
        "",
    ]
    input_source = str(experiment.get("input_source") or "").strip()
    if input_source:
        lines.append(f"- Source: {input_source}")

    if summary is not None:
        next_action = _review_experiment_next_action(summary, safety)
        lines.extend(
            [
                f"- Items: {summary.get('item_count', 0)}; "
                f"candidate adoption={_format_percent(summary.get('candidate_adoption_rate'))}; "
                f"rollout_ready={_format_bool(summary.get('candidate_ready_for_rollout'))}",
                f"- Score: current_avg={_format_number(summary.get('average_current_review_efficiency_score'))}; "
                f"candidate_avg={_format_number(summary.get('average_candidate_review_efficiency_score'))}; "
                f"delta={_format_number(summary.get('average_score_delta'))}",
                f"- Operator actions: total={summary.get('candidate_operator_action_total', 0)}; "
                f"avg/item={_format_number(summary.get('average_operator_actions_per_item'))}; "
                f"max/item={summary.get('max_operator_actions_per_item', 0)}; "
                f"delta={_format_number(summary.get('average_operator_action_delta'))}",
            ]
        )
        missing_counts = summary.get("candidate_missing_metric_counts")
        if isinstance(missing_counts, dict):
            lines.append(
                f"- Missing metrics: rate={_format_percent(summary.get('candidate_missing_metric_rate'))}; "
                f"top={_format_counts(missing_counts)}"
            )
        lines.append(
            f"- Operator buckets: errors={_format_counts(summary.get('candidate_operator_error_bucket_counts') or {})}; "
            f"reasons={_format_counts(summary.get('candidate_operator_reason_bucket_counts') or {})}; "
            f"triage={_format_counts(summary.get('candidate_operator_triage_bucket_counts') or {})}"
        )
        rollout_reason = str(summary.get("candidate_rollout_reason") or "").strip()
        if rollout_reason:
            lines.append(f"- Rollout gate: {rollout_reason}")
        if next_action:
            lines.append(f"- Next manual action: {next_action}")
    elif comparison is not None and variants is not None:
        current_variant = variants.get("current") if isinstance(variants.get("current"), dict) else {}
        candidate_variant = variants.get("candidate") if isinstance(variants.get("candidate"), dict) else {}
        lines.extend(
            [
                f"- Recommendation: {comparison.get('recommendation', '-')}",
                f"- Score: current={_format_number(current_variant.get('review_efficiency_score'))}; "
                f"candidate={_format_number(candidate_variant.get('review_efficiency_score'))}; "
                f"delta={_format_number(comparison.get('score_delta'))}",
                f"- Operator actions: current={current_variant.get('operator_action_count', 0)}; "
                f"candidate={candidate_variant.get('operator_action_count', 0)}; "
                f"delta={_format_number(comparison.get('operator_action_delta'))}",
            ]
        )

    lines.extend(
        [
            f"- Provider evidence: current={_format_counts(current['providers'])}; "
            f"candidate={_format_counts(candidate['providers'])}",
            f"- Model evidence: current={_format_counts(current['models'])}; "
            f"candidate={_format_counts(candidate['models'])}",
            f"- Latency avg: current={_format_ms(current['avg_latency_ms'])}; "
            f"candidate={_format_ms(candidate['avg_latency_ms'])}",
            f"- Cost avg: current={_format_usd(current['avg_cost_usd'])}; "
            f"candidate={_format_usd(candidate['avg_cost_usd'])}",
            f"- Safety: read_only={_format_bool(safety.get('read_only'))}; "
            f"notion_writes={_format_bool(safety.get('notion_writes'))}; "
            f"x_posts={_format_bool(safety.get('x_posts'))}; "
            f"manual_publish_required={_format_bool(safety.get('manual_publish_required'))}",
            "",
        ]
    )
    return "\n".join(lines)


def _source_preflight_trend_next_action(summary: dict | None, safety: dict, payload: dict) -> str:
    if safety.get("read_only") is False:
        return "Restore the read-only source preflight trend contract before using this evidence."
    if safety.get("browser_launches"):
        return "Generate source preflight trend reports from existing JSON only; do not launch browsers here."
    if safety.get("notion_writes") or safety.get("x_posts"):
        return "Disable writes/posts for source preflight trend reporting."
    if safety.get("auto_publish_default"):
        return "Keep auto-publish disabled; require manual publish approval."
    if safety.get("manual_publish_required") is False:
        return "Require manual publish approval before rollout."
    next_step = str(payload.get("next_step") or "").strip()
    if next_step:
        return next_step
    if not isinstance(summary, dict):
        return ""
    if int(_as_float(summary.get("error_count")) or 0) > 0:
        return "Fix invalid or missing source preflight evidence before changing source strategy."
    if int(_as_float(summary.get("warning_count")) or 0) > 0:
        return "Review source preflight warning buckets before changing selectors or timeouts."
    if int(_as_float(summary.get("problem_action_count")) or 0) > 0:
        return "Use the most frequent source/status buckets to choose the next preflight hardening slice."
    return "No source preflight failures in the selected local reports."


def _format_top_repair_commands(items, *, limit: int = 2) -> str:
    if not isinstance(items, list):
        return "-"
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command") or "").strip()
        if not command:
            continue
        count = item.get("count", 0)
        command_type = item.get("type") or "other"
        sources = item.get("sources") if isinstance(item.get("sources"), dict) else {}
        parts.append(f"{count}x {command_type} sources={_format_counts(sources)} command={command}")
        if len(parts) >= limit:
            break
    return " | ".join(parts) if parts else "-"


def _render_source_preflight_trend_section(trend: dict | None) -> str:
    if not isinstance(trend, dict):
        return ""
    summary = trend.get("summary") if isinstance(trend.get("summary"), dict) else None
    if summary is None:
        return ""

    safety = trend.get("safety") if isinstance(trend.get("safety"), dict) else {}
    top_source_action = summary.get("top_source_action") if isinstance(summary.get("top_source_action"), dict) else {}
    top_source_remediation = (
        summary.get("top_source_remediation") if isinstance(summary.get("top_source_remediation"), dict) else {}
    )
    operator_recommendation = (
        summary.get("operator_recommendation") if isinstance(summary.get("operator_recommendation"), dict) else {}
    )
    next_action = _source_preflight_trend_next_action(summary, safety, trend)
    lines = [
        "",
        "## Source Preflight Trend (dry-run)",
        "",
        f"- Reports: {summary.get('report_count', 0)}; status={trend.get('status', '-')}; "
        f"problem_actions={summary.get('problem_action_count', 0)}; "
        f"failure_reports={summary.get('failure_report_count', 0)}",
        f"- Operator actions: required={summary.get('operator_action_required_count', 0)}",
        f"- Status buckets: {_format_counts(summary.get('status_counts') or {})}",
        f"- Source buckets: {_format_counts(summary.get('source_counts') or {})}",
        f"- Evidence: failure_report_statuses={_format_counts(summary.get('failure_report_status_counts') or {})}; "
        f"errors={summary.get('error_count', 0)}; warnings={summary.get('warning_count', 0)}; "
        f"top_issue_codes={_format_counts(summary.get('top_issue_codes') or {})}",
        f"- Evidence gates: strategy_change_ready={summary.get('strategy_change_ready_count', 0)}; "
        f"statuses={_format_counts(summary.get('evidence_gate_status_counts') or {})}",
        f"- Repair commands: total={summary.get('repair_command_count', 0)}; "
        f"types={_format_counts(summary.get('repair_command_type_counts') or {})}; "
        f"top={_format_top_repair_commands(summary.get('top_repair_commands'))}",
        f"- Safety: read_only={_format_bool(safety.get('read_only'))}; "
        f"browser_launches={_format_bool(safety.get('browser_launches'))}; "
        f"notion_writes={_format_bool(safety.get('notion_writes'))}; "
        f"x_posts={_format_bool(safety.get('x_posts'))}; "
        f"manual_publish_required={_format_bool(safety.get('manual_publish_required'))}",
    ]
    if top_source_action:
        lines.append(
            f"- Top source action: source={top_source_action.get('source', '-')}; "
            f"status={top_source_action.get('status', '-')}; count={top_source_action.get('count', 0)}; "
            f"action={top_source_action.get('operator_action', '-')}"
        )
    if operator_recommendation:
        lines.append(
            f"- Operator recommendation: action={operator_recommendation.get('action', '-')}; "
            f"priority={operator_recommendation.get('priority', '-')}; "
            f"source={operator_recommendation.get('source') or '-'}; "
            f"status={operator_recommendation.get('status') or '-'}; "
            f"next={operator_recommendation.get('operator_action', '-')}"
        )
    checklist = (
        top_source_remediation.get("checklist") if isinstance(top_source_remediation.get("checklist"), list) else []
    )
    checklist_items = [str(item).strip() for item in checklist if str(item).strip()]
    if checklist_items:
        lines.append(f"- Top source checklist: {' | '.join(checklist_items)}")
    if next_action:
        lines.append(f"- Next manual action: {next_action}")
    lines.append("")
    return "\n".join(lines)


def _render_source_preflight_strategy_section(simulation: dict | None) -> str:
    if not isinstance(simulation, dict):
        return ""
    summary = simulation.get("summary") if isinstance(simulation.get("summary"), dict) else {}
    comparison = simulation.get("comparison") if isinstance(simulation.get("comparison"), dict) else {}
    variants = simulation.get("variants") if isinstance(simulation.get("variants"), dict) else {}
    current = variants.get("current") if isinstance(variants.get("current"), dict) else {}
    candidate = variants.get("candidate") if isinstance(variants.get("candidate"), dict) else {}
    current_signals = current.get("signals") if isinstance(current.get("signals"), dict) else {}
    candidate_signals = candidate.get("signals") if isinstance(candidate.get("signals"), dict) else {}
    safety = simulation.get("safety") if isinstance(simulation.get("safety"), dict) else {}
    rollout_gate = simulation.get("rollout_gate") if isinstance(simulation.get("rollout_gate"), dict) else {}
    manual_ready_gate = (
        simulation.get("manual_ready_gate") if isinstance(simulation.get("manual_ready_gate"), dict) else {}
    )
    blocked_by = rollout_gate.get("blocked_by") if isinstance(rollout_gate.get("blocked_by"), list) else []
    blocked_by_text = ", ".join(str(item) for item in blocked_by if str(item).strip()) or "-"
    gate_counts = summary.get("evidence_gate_status_counts") or {}
    blocker_counts = dict(gate_counts) if isinstance(gate_counts, dict) else {}
    blocker_counts["repair_command_count"] = summary.get("repair_command_count", 0)
    blocked_checklist = _source_strategy_blocked_checklist(blocked_by, blocker_counts)
    metric_total = _source_strategy_metric_total(simulation)
    measurement_scope = _source_strategy_measurement_scope(
        summary,
        current,
        candidate,
        current_signals,
        candidate_signals,
    )
    not_measured_metrics = measurement_scope.get("not_measured_metrics")
    current_missing_metric_count = _source_strategy_missing_metric_count(summary, current, "current")
    candidate_missing_metric_count = _source_strategy_missing_metric_count(summary, candidate, "candidate")
    if not comparison:
        return ""

    lines = [
        "",
        "## Source Preflight Strategy A/B (dry-run)",
        "",
        f"- Reports: {summary.get('report_count', 0)}; trend_status={simulation.get('trend_status', '-')}; "
        f"problem_actions={summary.get('problem_action_count', 0)}",
        f"- Recommendation: {comparison.get('recommendation', '-')}; "
        f"score_delta={_format_number(comparison.get('score_delta'))}; "
        f"unsafe_strategy_change_delta={comparison.get('unsafe_strategy_change_delta', '-')}; "
        f"operator_action_required_delta={comparison.get('operator_action_required_delta', '-')}",
        f"- Current: score={_format_number(current_signals.get('final_rank_score'))}; "
        f"strategy_reviews={current_signals.get('strategy_review_count', 0)}; "
        f"unsafe_changes={current_signals.get('unsafe_strategy_change_count', 0)}",
        f"- Candidate: score={_format_number(candidate_signals.get('final_rank_score'))}; "
        f"strategy_reviews={candidate_signals.get('strategy_review_count', 0)}; "
        f"unsafe_changes={candidate_signals.get('unsafe_strategy_change_count', 0)}; "
        f"action={candidate_signals.get('recommendation_action', '-')}",
        f"- Outcome signals: current_success={_format_bool(current_signals.get('success'))}; "
        f"candidate_success={_format_bool(candidate_signals.get('success'))}; "
        f"current_operator_action_required={_format_bool(current_signals.get('operator_action_required'))}; "
        f"candidate_operator_action_required={_format_bool(candidate_signals.get('operator_action_required'))}",
        f"- Provider/model/cost: current={current_signals.get('provider', '-')}/"
        f"{current_signals.get('model', '-')}/{_format_usd(current_signals.get('token_cost_estimate'))}; "
        f"candidate={candidate_signals.get('provider', '-')}/{candidate_signals.get('model', '-')}/"
        f"{_format_usd(candidate_signals.get('token_cost_estimate'))}",
        f"- A/B metrics: latency_ms current={_format_ms(current_signals.get('latency_ms'))}; "
        f"candidate={_format_ms(candidate_signals.get('latency_ms'))}; "
        f"draft_quality_score current={_format_number(current_signals.get('draft_quality_score'))}; "
        f"candidate={_format_number(candidate_signals.get('draft_quality_score'))}; "
        f"duplicate_or_near_duplicate current={_format_bool(current_signals.get('duplicate_or_near_duplicate'))}; "
        f"candidate={_format_bool(candidate_signals.get('duplicate_or_near_duplicate'))}",
        f"- Metric coverage: current_missing={current_missing_metric_count}/{metric_total}; "
        f"candidate_missing={candidate_missing_metric_count}/{metric_total}; "
        f"metric_missing=current:{current_missing_metric_count}/{metric_total},"
        f"candidate:{candidate_missing_metric_count}/{metric_total}; "
        f"scope={measurement_scope.get('mode', '-')}; "
        f"external_llm_calls={_format_bool(measurement_scope.get('external_llm_calls'))}; "
        f"costed_generation={_format_bool(measurement_scope.get('costed_generation'))}; "
        f"not_measured={_format_flags(not_measured_metrics)}",
        f"- Safety risk flags: current={_format_flags(current_signals.get('safety_risk_flags'))}; "
        f"candidate={_format_flags(candidate_signals.get('safety_risk_flags'))}",
        f"- Evidence gates: {_format_counts(gate_counts if isinstance(gate_counts, dict) else {})}",
        f"- Rollout gate: status={rollout_gate.get('status', '-')}; "
        f"ready_for_manual_strategy_review={_format_bool(rollout_gate.get('ready_for_manual_strategy_review'))}; "
        f"auto_apply_allowed={_format_bool(rollout_gate.get('auto_apply_allowed'))}; "
        f"blocked_by={blocked_by_text}",
    ]
    if blocked_checklist:
        lines.append(f"- Blocked checklist: {blocked_checklist}")
    lines.append(f"- Gate action: {rollout_gate.get('operator_action', '-')}")
    if manual_ready_gate:
        lines.append(
            f"- Manual-ready gate: status={manual_ready_gate.get('status', '-')}; "
            f"required={_format_bool(manual_ready_gate.get('required'))}; "
            f"passed={_format_bool(manual_ready_gate.get('passed'))}; "
            f"exit_code={manual_ready_gate.get('exit_code', '-')}; "
            f"repair_remaining={_repair_remaining_count(manual_ready_gate)}; "
            f"reason={manual_ready_gate.get('reason', '-')}"
        )
        if manual_ready_gate.get("status") == "blocked":
            lines.append(f"- Next manual action: {manual_ready_gate.get('reason', '-')}")
            repair_commands = (
                manual_ready_gate.get("repair_commands")
                if isinstance(manual_ready_gate.get("repair_commands"), list)
                else []
            )
            try:
                repair_command_count = int(manual_ready_gate.get("repair_command_count") or len(repair_commands))
            except (TypeError, ValueError):
                repair_command_count = len(repair_commands)
            repair_command = str(manual_ready_gate.get("primary_repair_command") or "").strip()
            remaining_repair_commands = _repair_remaining_count(manual_ready_gate)
            if repair_command_count:
                lines.append(
                    f"- Repair commands: count={repair_command_count}; "
                    f"primary_shown={_format_bool(bool(repair_command))}; remaining={remaining_repair_commands}"
                )
            if repair_command:
                lines.append(f"- Repair command: `{repair_command}`")
            if remaining_repair_commands > 0:
                lines.append(
                    "- Remaining repair commands: see `manual_ready_gate.repair_commands` "
                    "in the source strategy JSON after running the primary command."
                )
    lines.extend(
        [
            f"- Safety: read_only={_format_bool(safety.get('read_only'))}; "
            f"browser_launches={_format_bool(safety.get('browser_launches'))}; "
            f"notion_writes={_format_bool(safety.get('notion_writes'))}; "
            f"x_posts={_format_bool(safety.get('x_posts'))}; "
            f"manual_publish_required={_format_bool(safety.get('manual_publish_required'))}",
            "",
        ]
    )
    return "\n".join(lines)


def _load_review_experiment_report(input_path: str | None) -> dict:
    if not input_path:
        return {}
    try:
        path = Path(input_path)
        with path.open(encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        logger.warning("Review experiment section skipped: %s", exc)
        return {}


def _load_source_preflight_trend_report(input_path: str | None) -> dict:
    if not input_path:
        return {}
    try:
        path = Path(input_path)
        with path.open(encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        logger.warning("Source preflight trend section skipped: %s", exc)
        return {}


def _load_source_preflight_strategy_report(input_path: str | None) -> dict:
    if not input_path:
        return {}
    try:
        path = Path(input_path)
        with path.open(encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        logger.warning("Source preflight strategy section skipped: %s", exc)
        return {}


def _load_report_payload(input_path: str | None) -> dict:
    if not input_path:
        return {}
    path = Path(input_path)
    with path.open(encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("weekly report payload input must be a JSON object")
    return payload


def _render_best_of_n_section(days: int) -> str:
    """T-1197: tuner 의 dry-run 결과를 weekly report 에 임베드.

    tuner 실패(import 에러 / DB 미존재 / 표본 부족 예외)는 swallow 해서 빈 문자열 반환.
    weekly report 본문이 절대 깨지지 않도록 fail-open.
    """
    try:
        from scripts.tune_best_of_n_weight import build_report, load_recent_rows

        rows = load_recent_rows(days=days)
        text, _summary = build_report(rows, days=days, min_samples=10)
    except Exception as exc:  # pragma: no cover - 환경 의존적
        logger.warning("Best-of-N tuner section skipped: %s", exc)
        return ""

    lines = [
        "",
        "## Best-of-N Comment-Weight Tuning (dry-run)",
        "",
        "```",
        text,
        "```",
        "",
    ]
    return "\n".join(lines)


def _render_report(payload: dict, *, best_of_n_days: int = 30) -> str:
    totals = payload.get("totals", {})
    lines = [
        "# Blind-to-X Weekly Report",
        "",
        "## Summary",
        f"- Total records: {totals.get('total', 0)}",
        f"- Review queue: {totals.get('review_queue', 0)}",
        f"- Approved: {totals.get('approved', 0)}",
        f"- Published: {totals.get('published', 0)}",
        "",
        "## Top Topics",
    ]
    for label, count in payload.get("top_topics", []):
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Top Hooks"])
    for label, count in payload.get("top_hooks", []):
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Top Emotions"])
    for label, count in payload.get("top_emotions", []):
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Top Performers"])
    for item in payload.get("top_performers", []):
        lines.append(
            f"- {item['title']} | views={item['views']} likes={item['likes']} retweets={item['retweets']} | "
            f"{item['topic_cluster']} / {item['hook_type']} / {item['emotion_axis']}"
        )
    body = "\n".join(lines) + "\n"
    review_experiment_section = _render_review_experiment_section(payload.get("review_experiment"))
    if review_experiment_section:
        body += review_experiment_section
    source_preflight_section = _render_source_preflight_trend_section(payload.get("source_preflight_trend"))
    if source_preflight_section:
        body += source_preflight_section
    source_strategy_section = _render_source_preflight_strategy_section(payload.get("source_preflight_strategy"))
    if source_strategy_section:
        body += source_strategy_section
    tuner_section = _render_best_of_n_section(best_of_n_days)
    if tuner_section:
        body += tuner_section
    return body


async def run(
    days: int,
    config_path: str,
    output_path: str,
    review_experiment_input: str | None = None,
    source_preflight_trend_input: str | None = None,
    source_preflight_strategy_input: str | None = None,
    payload_input: str | None = None,
) -> int:
    payload = _load_report_payload(payload_input)
    if not payload:
        config_manager_cls, feedback_loop_cls, notion_uploader_cls = _load_live_report_dependencies()
        config_mgr = config_manager_cls(config_path)
        notion_uploader = notion_uploader_cls(config_mgr)
        feedback_loop = feedback_loop_cls(notion_uploader, config_mgr)
        payload = await feedback_loop.build_weekly_report_payload(days=days)
    review_experiment = _load_review_experiment_report(review_experiment_input)
    if review_experiment:
        payload["review_experiment"] = review_experiment
    source_preflight_trend = _load_source_preflight_trend_report(source_preflight_trend_input)
    if source_preflight_trend:
        payload["source_preflight_trend"] = source_preflight_trend
    source_preflight_strategy = _load_source_preflight_strategy_report(source_preflight_strategy_input)
    if source_preflight_strategy:
        payload["source_preflight_strategy"] = source_preflight_strategy
    # tuner sweep 은 더 긴 윈도우(30일)로 보는 게 표본 확보에 유리.
    report = _render_report(payload, best_of_n_days=max(days, 30))

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report, encoding="utf-8")
    print(report)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Build Blind-to-X weekly report.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", default=".tmp/weekly_report.md")
    parser.add_argument(
        "--payload-input",
        default="",
        help="Optional weekly report payload JSON to render locally without fetching Notion.",
    )
    parser.add_argument(
        "--review-experiment-input",
        default="",
        help="Optional review_experiment_dry_run JSON to embed as a read-only A/B summary.",
    )
    parser.add_argument(
        "--source-preflight-trend-input",
        default="",
        help="Optional source_preflight_trend_report JSON to embed as a read-only operations summary.",
    )
    parser.add_argument(
        "--source-preflight-strategy-input",
        default="",
        help="Optional source_preflight_strategy_simulation JSON to embed as a read-only A/B summary.",
    )
    args = parser.parse_args()

    from config import load_env, setup_logging

    load_env()
    setup_logging()
    raise SystemExit(
        asyncio.run(
            run(
                days=args.days,
                config_path=args.config,
                output_path=args.output,
                review_experiment_input=args.review_experiment_input,
                source_preflight_trend_input=args.source_preflight_trend_input,
                source_preflight_strategy_input=args.source_preflight_strategy_input,
                payload_input=args.payload_input,
            )
        )
    )


if __name__ == "__main__":
    main()
