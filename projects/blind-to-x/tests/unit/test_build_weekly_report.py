"""build_weekly_report.py 단위 테스트.

`_render_report` 의 markdown 직렬화 + T-1197 tuner 섹션 임베드 + fail-open 동작을 검증.
주 진입점 `run()` 은 Notion/feedback_loop 의존이 커서 여기서는 다루지 않는다.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_BTX_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BTX_ROOT))

from scripts.build_weekly_report import _render_best_of_n_section, _render_report, run  # noqa: E402


def _basic_payload():
    return {
        "totals": {
            "total": 12,
            "review_queue": 3,
            "approved": 7,
            "published": 5,
        },
        "top_topics": [("career", 6), ("money", 4)],
        "top_hooks": [("question", 5), ("statistic", 3)],
        "top_emotions": [("empathy", 6), ("anger", 2)],
        "top_performers": [
            {
                "title": "Title A",
                "views": 1000,
                "likes": 50,
                "retweets": 10,
                "topic_cluster": "career",
                "hook_type": "question",
                "emotion_axis": "empathy",
            }
        ],
    }


def _review_experiment_payload():
    return {
        "input_source": ".tmp/review_queue_report_sample.json",
        "dry_run": True,
        "batch": True,
        "safety": {
            "read_only": True,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "summary": {
            "item_count": 3,
            "candidate_adoption_rate": 0.667,
            "average_current_review_efficiency_score": 18.0,
            "average_candidate_review_efficiency_score": 24.5,
            "average_score_delta": 6.5,
            "candidate_operator_action_total": 5,
            "average_operator_actions_per_item": 1.667,
            "max_operator_actions_per_item": 2,
            "average_operator_action_delta": 1.667,
            "candidate_missing_metric_rate": 0.1,
            "candidate_missing_metric_counts": {
                "provider": 0,
                "model": 0,
                "latency_ms": 1,
                "token_cost_estimate": 2,
            },
            "candidate_operator_error_bucket_counts": {"x_post_failed": 2},
            "candidate_operator_reason_bucket_counts": {"missing_draft": 1},
            "candidate_operator_triage_bucket_counts": {"blocked_publish": 1},
            "candidate_ready_for_rollout": False,
            "candidate_rollout_reason": "blocked: fill missing objective metrics before rollout",
            "candidate_experiment_confidence": {
                "issues": [
                    {
                        "code": "missing_metric_rate_high",
                        "operator_action": (
                            "Fill the top missing metrics before using this experiment as adoption evidence."
                        ),
                    }
                ],
            },
        },
        "items": [
            {
                "current": {"signals": {}, "operator_action_count": 0},
                "candidate": {
                    "signals": {
                        "provider": "gemini",
                        "model": "gemini-2.5-flash",
                        "latency_ms": 400,
                        "token_cost_estimate": 0.01,
                    },
                    "operator_action_count": 2,
                },
            },
            {
                "current": {"signals": {}, "operator_action_count": 0},
                "candidate": {
                    "signals": {
                        "provider": "openai",
                        "model": "gpt-5-mini",
                        "latency_ms": 500,
                        "token_cost_estimate": 0.02,
                    },
                    "operator_action_count": 1,
                },
            },
            {
                "current": {"signals": {}, "operator_action_count": 0},
                "candidate": {
                    "signals": {
                        "provider": "gemini",
                        "model": "gemini-2.5-flash",
                        "latency_ms": 600,
                        "token_cost_estimate": 0.03,
                    },
                    "operator_action_count": 2,
                },
            },
        ],
    }


def _source_preflight_trend_payload():
    return {
        "status": "WARN",
        "ok": True,
        "safety": {
            "read_only": True,
            "browser_launches": False,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "summary": {
            "report_count": 3,
            "problem_action_count": 4,
            "failure_report_count": 3,
            "operator_action_required_count": 4,
            "strategy_change_ready_count": 2,
            "error_count": 0,
            "warning_count": 1,
            "status_counts": {"timeout": 2, "blocked": 1, "browser_unavailable": 1},
            "source_counts": {"ppomppu": 2, "blind": 1, "fmkorea": 1},
            "failure_report_status_counts": {"valid": 3, "missing": 1},
            "evidence_gate_status_counts": {
                "strategy_review_ready": 2,
                "fallback_only": 1,
                "fix_evidence_first": 1,
            },
            "top_issue_codes": {"missing_failure_report_path": 1},
            "repair_command_count": 3,
            "repair_command_type_counts": {
                "evidence_doctor": 2,
                "source_preflight_capture": 1,
            },
            "top_repair_commands": [
                {
                    "command": "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight.json",
                    "type": "evidence_doctor",
                    "count": 2,
                    "sources": {"ppomppu": 2},
                },
                {
                    "command": (
                        "py -3 main.py --config config.yaml --source ppomppu --source-preflight "
                        "--source-preflight-click-through"
                    ),
                    "type": "source_preflight_capture",
                    "count": 1,
                    "sources": {"ppomppu": 1},
                },
            ],
            "top_source_action": {
                "source": "ppomppu",
                "status": "timeout",
                "count": 2,
                "operator_action": (
                    "Inspect ppomppu timeout evidence, then adjust timeout or source fallback only after evidence is valid."
                ),
            },
            "top_source_remediation": {
                "source": "ppomppu",
                "status": "timeout",
                "count": 2,
                "evidence_fields": [
                    "failure_report_path",
                    "screenshot_path",
                    "html_snapshot_path",
                    "trace_path",
                    "error",
                ],
                "checklist": [
                    (
                        "Open ppomppu evidence fields first: "
                        "failure_report_path, screenshot_path, html_snapshot_path, trace_path, error."
                    ),
                    (
                        "Use a ready fallback source for this run if available; do not increase ppomppu timeout until "
                        "evidence shows a reachable slow page."
                    ),
                    "Rerun ppomppu preflight with --failure-dir after any timeout or selector change.",
                ],
            },
            "operator_recommendation": {
                "action": "repair_evidence",
                "priority": "medium",
                "source": "ppomppu",
                "status": "timeout",
                "reason": "Evidence is missing, invalid, or warning-level incomplete.",
                "operator_action": (
                    "Run the evidence doctor for affected reports, restore missing artifacts, then rerun trend "
                    "reporting before changing selectors, timeouts, or source strategy."
                ),
                "gate_counts": {
                    "fix_evidence_first": 1,
                    "fallback_only": 1,
                    "strategy_review_ready": 2,
                },
            },
        },
        "next_step": "Review warning codes; rerun individual evidence doctor for any unclear report.",
    }


def _source_preflight_strategy_payload():
    return {
        "dry_run": True,
        "trend_status": "PASS",
        "objective_metrics": [
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
        ],
        "safety": {
            "read_only": True,
            "browser_launches": False,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "summary": {
            "report_count": 2,
            "problem_action_count": 2,
            "error_count": 0,
            "warning_count": 0,
            "evidence_gate_status_counts": {
                "strategy_review_ready": 1,
                "fallback_only": 1,
            },
            "missing_metric_counts": {"current": 2, "candidate": 2},
            "missing_metric_names": {
                "current": ["latency_ms", "draft_quality_score"],
                "candidate": ["latency_ms", "draft_quality_score"],
            },
            "measurement_scope": {
                "mode": "local_preflight_evidence",
                "external_llm_calls": False,
                "costed_generation": False,
                "not_measured_metrics": ["latency_ms", "draft_quality_score"],
                "deterministic_defaults": {
                    "token_cost_estimate": 0.0,
                    "duplicate_or_near_duplicate": False,
                },
            },
        },
        "variants": {
            "current": {
                "name": "current_top_source_action",
                "signals": {
                    "provider": "source_preflight",
                    "model": "current_top_source_action",
                    "token_cost_estimate": 0.0,
                    "latency_ms": None,
                    "draft_quality_score": None,
                    "duplicate_or_near_duplicate": False,
                    "final_rank_score": 44.0,
                    "strategy_review_count": 2,
                    "unsafe_strategy_change_count": 1,
                    "success": False,
                    "operator_action_required": True,
                    "safety_risk_flags": ["ungated_strategy_change"],
                },
            },
            "candidate": {
                "name": "candidate_gate_directed_operator_recommendation",
                "signals": {
                    "provider": "source_preflight",
                    "model": "gate_directed_operator_recommendation",
                    "token_cost_estimate": 0.0,
                    "latency_ms": None,
                    "draft_quality_score": None,
                    "duplicate_or_near_duplicate": False,
                    "final_rank_score": 68.0,
                    "strategy_review_count": 1,
                    "unsafe_strategy_change_count": 0,
                    "recommendation_action": "split_fallback_and_strategy_review",
                    "success": True,
                    "operator_action_required": True,
                    "safety_risk_flags": [],
                },
            },
        },
        "comparison": {
            "recommendation": "adopt_candidate",
            "score_delta": 24.0,
            "unsafe_strategy_change_delta": -1,
            "operator_action_required_delta": 0,
        },
        "rollout_gate": {
            "status": "split_manual_review",
            "ready_for_manual_strategy_review": True,
            "auto_apply_allowed": False,
            "manual_review_required": True,
            "blocked_by": ["fallback_only_sources_present"],
            "operator_action": (
                "Use ready fallback sources for fallback-only failures, then manually review only strategy-ready evidence."
            ),
            "safety_note": (
                "This dry-run never applies selector, timeout, source, Notion, or publish changes automatically."
            ),
        },
        "manual_ready_gate": {
            "required": True,
            "passed": True,
            "status": "pass",
            "exit_code": 0,
            "reason": "Manual strategy review is ready: split_manual_review.",
        },
    }


def test_render_report_includes_all_required_summary_sections():
    """기본 markdown 구조가 깨지지 않아야: 헤더 + 요약 + Topics/Hooks/Emotions/Performers."""
    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(_basic_payload())
    assert text.startswith("# Blind-to-X Weekly Report")
    assert "## Summary" in text
    assert "Total records: 12" in text
    assert "Review queue: 3" in text
    assert "## Top Topics" in text
    assert "- career: 6" in text
    assert "## Top Hooks" in text
    assert "## Top Emotions" in text
    assert "## Top Performers" in text
    assert "Title A | views=1000 likes=50 retweets=10" in text


def test_render_report_embeds_review_experiment_batch_summary():
    payload = _basic_payload()
    payload["review_experiment"] = _review_experiment_payload()

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert "## Review Experiment A/B Summary (dry-run)" in text
    assert "Source: .tmp/review_queue_report_sample.json" in text
    assert "candidate adoption=66.7%" in text
    assert "rollout_ready=false" in text
    assert "Score: current_avg=18; candidate_avg=24.50; delta=6.50" in text
    assert "Operator actions: total=5; avg/item=1.67; max/item=2; delta=1.67" in text
    assert "Missing metrics: rate=10.0%; top=token_cost_estimate=2, latency_ms=1, model=0, provider=0" in text
    assert "Operator buckets: errors=x_post_failed=2; reasons=missing_draft=1; triage=blocked_publish=1" in text
    assert "Provider evidence: current=-; candidate=gemini=2, openai=1" in text
    assert "Model evidence: current=-; candidate=gemini-2.5-flash=2, gpt-5-mini=1" in text
    assert "Latency avg: current=-; candidate=500.0ms" in text
    assert "Cost avg: current=-; candidate=$0.0200" in text
    assert "Safety: read_only=true; notion_writes=false; x_posts=false; manual_publish_required=true" in text
    assert "Rollout gate: blocked: fill missing objective metrics before rollout" in text
    assert "Next manual action: Fill the top missing metrics before using this experiment as adoption evidence." in text


def test_render_report_preserves_non_numeric_review_metric_counts():
    payload = _basic_payload()
    experiment = _review_experiment_payload()
    experiment["summary"]["candidate_missing_metric_counts"] = {
        "latency_ms": "n/a",
        "provider": 1,
    }
    payload["review_experiment"] = experiment

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert "Missing metrics: rate=10.0%; top=provider=1, latency_ms=n/a" in text


def test_render_report_embeds_ready_review_experiment_next_action():
    payload = _basic_payload()
    experiment = _review_experiment_payload()
    experiment["summary"]["candidate_ready_for_rollout"] = True
    experiment["summary"]["candidate_rollout_reason"] = "ready: confidence and safety gates passed"
    experiment["summary"]["candidate_experiment_confidence"] = {"issues": []}
    payload["review_experiment"] = experiment

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert "Rollout gate: ready: confidence and safety gates passed" in text
    assert "Next manual action: Review the candidate card manually, then keep publish approval manual." in text


def test_render_report_embeds_source_preflight_trend_summary():
    payload = _basic_payload()
    payload["source_preflight_trend"] = _source_preflight_trend_payload()

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert "## Source Preflight Trend (dry-run)" in text
    assert "Reports: 3; status=WARN; problem_actions=4; failure_reports=3" in text
    assert "Operator actions: required=4" in text
    assert "Status buckets: timeout=2, blocked=1, browser_unavailable=1" in text
    assert "Source buckets: ppomppu=2, blind=1, fmkorea=1" in text
    assert "Evidence: failure_report_statuses=valid=3, missing=1; errors=0; warnings=1" in text
    assert "top_issue_codes=missing_failure_report_path=1" in text
    assert "Evidence gates: strategy_change_ready=2" in text
    assert "statuses=strategy_review_ready=2, fallback_only=1, fix_evidence_first=1" in text
    assert "Repair commands: total=3; types=evidence_doctor=2, source_preflight_capture=1" in text
    assert "2x evidence_doctor sources=ppomppu=2 command=py -3 scripts/source_preflight_evidence_doctor.py" in text
    assert "1x source_preflight_capture sources=ppomppu=1 command=py -3 main.py --config config.yaml" in text
    assert "Top source action: source=ppomppu; status=timeout; count=2" in text
    assert (
        "Inspect ppomppu timeout evidence, then adjust timeout or source fallback only after evidence is valid." in text
    )
    assert "Operator recommendation: action=repair_evidence; priority=medium; source=ppomppu; status=timeout" in text
    assert "restore missing artifacts, then rerun trend reporting" in text
    assert "Top source checklist: Open ppomppu evidence fields first" in text
    assert "do not increase ppomppu timeout" in text
    assert "Rerun ppomppu preflight with --failure-dir" in text
    assert "Safety: read_only=true; browser_launches=false; notion_writes=false; x_posts=false" in text
    assert "manual_publish_required=true" in text
    assert "Next manual action: Review warning codes; rerun individual evidence doctor for any unclear report." in text


def test_render_report_embeds_source_preflight_strategy_simulation():
    payload = _basic_payload()
    payload["source_preflight_strategy"] = _source_preflight_strategy_payload()

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert "## Source Preflight Strategy A/B (dry-run)" in text
    assert "Reports: 2; trend_status=PASS; problem_actions=2" in text
    assert "Recommendation: adopt_candidate; score_delta=24; unsafe_strategy_change_delta=-1" in text
    assert "Current: score=44; strategy_reviews=2; unsafe_changes=1" in text
    assert "Candidate: score=68; strategy_reviews=1; unsafe_changes=0" in text
    assert "action=split_fallback_and_strategy_review" in text
    assert (
        "Outcome signals: current_success=false; candidate_success=true; "
        "current_operator_action_required=true; candidate_operator_action_required=true"
    ) in text
    assert (
        "Provider/model/cost: current=source_preflight/current_top_source_action/$0.0000; "
        "candidate=source_preflight/gate_directed_operator_recommendation/$0.0000"
    ) in text
    assert (
        "A/B metrics: latency_ms current=-; candidate=-; draft_quality_score current=-; candidate=-; "
        "duplicate_or_near_duplicate current=false; candidate=false"
    ) in text
    assert (
        "Metric coverage: current_missing=2/10; candidate_missing=2/10; "
        "metric_missing=current:2/10,candidate:2/10; "
        "scope=local_preflight_evidence; external_llm_calls=false; costed_generation=false; "
        "not_measured=latency_ms, draft_quality_score"
    ) in text
    assert "Safety risk flags: current=ungated_strategy_change; candidate=-" in text
    assert "Evidence gates: fallback_only=1, strategy_review_ready=1" in text
    assert (
        "Rollout gate: status=split_manual_review; ready_for_manual_strategy_review=true; "
        "auto_apply_allowed=false; blocked_by=fallback_only_sources_present"
    ) in text
    assert (
        "Blocked checklist: fallback_only_sources_present=1: use ready fallback sources; keep strategy manual" in text
    )
    assert "Gate action: Use ready fallback sources for fallback-only failures" in text
    assert (
        "Manual-ready gate: status=pass; required=true; passed=true; exit_code=0; "
        "repair_remaining=0; reason=Manual strategy review is ready: split_manual_review."
    ) in text
    assert "Remaining repair commands:" not in text
    assert "Safety: read_only=true; browser_launches=false; notion_writes=false; x_posts=false" in text


def test_render_report_infers_source_preflight_metric_coverage_for_legacy_strategy_json():
    payload = _basic_payload()
    strategy = _source_preflight_strategy_payload()
    strategy.pop("objective_metrics")
    strategy["summary"].pop("missing_metric_counts")
    strategy["summary"].pop("missing_metric_names")
    strategy["summary"].pop("measurement_scope")
    strategy["variants"]["current"]["missing_required_metrics"] = ["latency_ms", "draft_quality_score"]
    strategy["variants"]["candidate"]["missing_required_metrics"] = ["latency_ms", "draft_quality_score"]
    payload["source_preflight_strategy"] = strategy

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert (
        "Metric coverage: current_missing=2/10; candidate_missing=2/10; "
        "metric_missing=current:2/10,candidate:2/10; "
        "scope=local_preflight_evidence_legacy; external_llm_calls=false; costed_generation=false; "
        "not_measured=latency_ms, draft_quality_score"
    ) in text


def test_render_report_uses_compact_source_preflight_metric_alias():
    payload = _basic_payload()
    strategy = _source_preflight_strategy_payload()
    strategy.pop("objective_metrics")
    strategy["summary"].pop("missing_metric_counts")
    strategy["summary"].pop("missing_metric_names")
    strategy["summary"]["metric_total"] = 7
    strategy["summary"]["metric_missing"] = "current:1/7,candidate:3/7"
    strategy["variants"]["current"]["missing_required_metrics"] = []
    strategy["variants"]["candidate"]["missing_required_metrics"] = []
    payload["source_preflight_strategy"] = strategy

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert (
        "Metric coverage: current_missing=1/7; candidate_missing=3/7; "
        "metric_missing=current:1/7,candidate:3/7; "
        "scope=local_preflight_evidence; external_llm_calls=false; costed_generation=false"
    ) in text


def test_render_report_embeds_blocked_source_preflight_manual_ready_action():
    payload = _basic_payload()
    strategy = _source_preflight_strategy_payload()
    strategy["rollout_gate"] = {
        "status": "blocked_repair_evidence",
        "ready_for_manual_strategy_review": False,
        "auto_apply_allowed": False,
        "manual_review_required": True,
        "blocked_by": ["repair_evidence_first", "repair_command_debt"],
        "operator_action": (
            "Repair missing or invalid failure evidence before reviewing selector, timeout, or source strategy changes."
        ),
    }
    strategy["summary"]["evidence_gate_status_counts"] = {"fix_evidence_first": 2}
    strategy["summary"]["repair_command_count"] = 2
    strategy["variants"]["candidate"]["signals"]["success"] = False
    strategy["variants"]["candidate"]["signals"]["safety_risk_flags"] = ["evidence_repair_required"]
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": (
            "Repair missing or invalid failure evidence before reviewing selector, timeout, or source strategy changes."
        ),
        "primary_repair_command": (
            "py -3 scripts/source_preflight_evidence_doctor.py --input 'source_browser_preflight.json' "
            "--base-dir '.tmp/source_preflight_strategy_blocked_smoke' --json --fail-on-warning"
        ),
        "repair_command_count": 2,
        "repair_command_remaining_count": 1,
        "repair_commands": [
            (
                "py -3 scripts/source_preflight_evidence_doctor.py --input 'source_browser_preflight.json' "
                "--base-dir '.tmp/source_preflight_strategy_blocked_smoke' --json --fail-on-warning"
            ),
            (
                "py -3 scripts/source_preflight_evidence_doctor.py --input 'source_browser_preflight-extra.json' "
                "--base-dir '.tmp/source_preflight_strategy_blocked_smoke' --json --fail-on-warning"
            ),
        ],
    }
    payload["source_preflight_strategy"] = strategy

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert (
        "Rollout gate: status=blocked_repair_evidence; ready_for_manual_strategy_review=false; "
        "auto_apply_allowed=false; blocked_by=repair_evidence_first, repair_command_debt"
    ) in text
    assert (
        "Outcome signals: current_success=false; candidate_success=false; "
        "current_operator_action_required=true; candidate_operator_action_required=true"
    ) in text
    assert (
        "Metric coverage: current_missing=2/10; candidate_missing=2/10; "
        "metric_missing=current:2/10,candidate:2/10; scope=local_preflight_evidence"
    ) in text
    assert "Safety risk flags: current=ungated_strategy_change; candidate=evidence_repair_required" in text
    assert "Blocked checklist: repair_evidence_first=2: run evidence doctor before strategy review" in text
    assert "repair_command_debt=2: run top repair commands before strategy review" in text
    assert "Manual-ready gate: status=blocked; required=true; passed=false; exit_code=2; repair_remaining=1" in text
    assert (
        "Next manual action: Repair missing or invalid failure evidence before reviewing selector, timeout, "
        "or source strategy changes."
    ) in text
    assert "Repair commands: count=2; primary_shown=true; remaining=1" in text
    assert (
        "Repair command: `py -3 scripts/source_preflight_evidence_doctor.py --input "
        "'source_browser_preflight.json' --base-dir '.tmp/source_preflight_strategy_blocked_smoke' "
        "--json --fail-on-warning`"
    ) in text
    assert (
        "Remaining repair commands: see `manual_ready_gate.repair_commands` in the source strategy JSON "
        "after running the primary command."
    ) in text


def test_render_report_keeps_unknown_source_preflight_blocker_visible():
    payload = _basic_payload()
    strategy = _source_preflight_strategy_payload()
    strategy["rollout_gate"] = {
        "status": "blocked_new_gate",
        "ready_for_manual_strategy_review": False,
        "auto_apply_allowed": False,
        "manual_review_required": True,
        "blocked_by": ["new_provider_gate"],
        "operator_action": "Inspect the new provider gate before changing source strategy.",
    }
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Inspect the new provider gate before changing source strategy.",
    }
    payload["source_preflight_strategy"] = strategy

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert (
        "Rollout gate: status=blocked_new_gate; ready_for_manual_strategy_review=false; "
        "auto_apply_allowed=false; blocked_by=new_provider_gate"
    ) in text
    assert "Blocked checklist: new_provider_gate: inspect rollout_gate.operator_action" in text
    assert "Gate action: Inspect the new provider gate before changing source strategy." in text


def test_render_report_blocks_unsafe_source_preflight_trend_summary():
    payload = _basic_payload()
    trend = _source_preflight_trend_payload()
    trend["safety"]["browser_launches"] = True
    trend["next_step"] = ""
    payload["source_preflight_trend"] = trend

    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(payload)

    assert "Safety: read_only=true; browser_launches=true" in text
    assert "Next manual action: Generate source preflight trend reports from existing JSON only" in text


def test_run_renders_payload_input_without_notion_fetch(tmp_path):
    payload_path = tmp_path / "weekly_payload.json"
    experiment_path = tmp_path / "review_experiment.json"
    trend_path = tmp_path / "source_preflight_trend.json"
    strategy_path = tmp_path / "source_preflight_strategy.json"
    output_path = tmp_path / "weekly_report.md"
    payload_path.write_text(json.dumps(_basic_payload()), encoding="utf-8")
    experiment_path.write_text(json.dumps(_review_experiment_payload()), encoding="utf-8")
    trend_path.write_text(json.dumps(_source_preflight_trend_payload()), encoding="utf-8")
    strategy_path.write_text(json.dumps(_source_preflight_strategy_payload()), encoding="utf-8")

    with (
        patch("scripts.build_weekly_report.ConfigManager") as config_manager,
        patch("scripts.build_weekly_report.NotionUploader") as notion_uploader,
        patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""),
    ):
        exit_code = asyncio.run(
            run(
                days=7,
                config_path="config.yaml",
                output_path=str(output_path),
                review_experiment_input=str(experiment_path),
                source_preflight_trend_input=str(trend_path),
                source_preflight_strategy_input=str(strategy_path),
                payload_input=str(payload_path),
            )
        )

    assert exit_code == 0
    config_manager.assert_not_called()
    notion_uploader.assert_not_called()
    text = output_path.read_text(encoding="utf-8")
    assert "## Review Experiment A/B Summary (dry-run)" in text
    assert "## Source Preflight Trend (dry-run)" in text
    assert "## Source Preflight Strategy A/B (dry-run)" in text
    assert "Next manual action: Fill the top missing metrics before using this experiment as adoption evidence." in text


def test_run_rejects_non_object_payload_input(tmp_path):
    payload_path = tmp_path / "weekly_payload.json"
    output_path = tmp_path / "weekly_report.md"
    payload_path.write_text(json.dumps([_basic_payload()]), encoding="utf-8")

    with pytest.raises(ValueError, match="weekly report payload input must be a JSON object"):
        asyncio.run(
            run(
                days=7,
                config_path="config.yaml",
                output_path=str(output_path),
                payload_input=str(payload_path),
            )
        )

    assert not output_path.exists()


def test_direct_script_renders_payload_input_without_project_pythonpath(tmp_path):
    payload_path = tmp_path / "weekly_payload.json"
    trend_path = tmp_path / "source_preflight_trend.json"
    strategy_path = tmp_path / "source_preflight_strategy.json"
    output_path = tmp_path / "weekly_report.md"
    payload_path.write_text(json.dumps(_basic_payload()), encoding="utf-8")
    trend_path.write_text(json.dumps(_source_preflight_trend_payload()), encoding="utf-8")
    strategy_path.write_text(json.dumps(_source_preflight_strategy_payload()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(_BTX_ROOT / "scripts" / "build_weekly_report.py"),
            "--payload-input",
            str(payload_path),
            "--source-preflight-trend-input",
            str(trend_path),
            "--source-preflight-strategy-input",
            str(strategy_path),
            "--output",
            str(output_path),
        ],
        cwd=_BTX_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert "Smoke item" not in text
    assert "## Source Preflight Trend (dry-run)" in text
    assert "## Source Preflight Strategy A/B (dry-run)" in text
    assert "metric_missing=current:2/10,candidate:2/10" in text
    assert "Title A | views=1000 likes=50 retweets=10" in result.stdout


def test_render_report_embeds_tuner_section_when_available():
    """T-1197: tuner 결과가 정상이면 markdown 코드 블록으로 임베드되어야."""
    fake_section = (
        "\n## Best-of-N Comment-Weight Tuning (dry-run)\n\n```\n"
        "=== Best-of-N comment-weight tuning (dry-run) ===\n"
        "기간: 최근 30일 / published 샘플: 12건\n"
        "권장: 0.5\n```\n"
    )
    with patch(
        "scripts.build_weekly_report._render_best_of_n_section",
        return_value=fake_section,
    ):
        text = _render_report(_basic_payload(), best_of_n_days=30)
    assert "## Best-of-N Comment-Weight Tuning (dry-run)" in text
    assert "기간: 최근 30일 / published 샘플: 12건" in text
    assert "권장: 0.5" in text
    # 기존 본문이 잘려나가지 않아야.
    assert "## Top Performers" in text


def test_render_report_omits_tuner_section_on_empty_return():
    """tuner 가 빈 문자열 반환(예: 예외 swallow) 시 본문은 그대로, 섹션은 없어야."""
    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(_basic_payload())
    assert "## Best-of-N Comment-Weight Tuning" not in text
    assert "## Top Performers" in text  # 기존 본문 유지


def test_render_best_of_n_section_swallows_tuner_exceptions():
    """T-1197 fail-open: tuner import/실행 예외는 weekly report 본문을 깨면 안 된다."""
    # build_report 가 raise 하도록 패치
    with patch(
        "scripts.tune_best_of_n_weight.build_report",
        side_effect=RuntimeError("tuner exploded"),
    ):
        text = _render_best_of_n_section(days=30)
    assert text == ""


def test_render_best_of_n_section_swallows_db_load_failure():
    """load_recent_rows 가 raise 해도 마찬가지로 빈 문자열."""
    with patch(
        "scripts.tune_best_of_n_weight.load_recent_rows",
        side_effect=OSError("no db"),
    ):
        text = _render_best_of_n_section(days=30)
    assert text == ""


@pytest.mark.parametrize("days", [7, 14, 30, 90])
def test_render_best_of_n_section_passes_days_window_to_loader(days):
    """sweep 윈도우가 호출자 파라미터로 전달되는지 확인."""
    captured = {}

    def fake_loader(*, days):
        captured["days"] = days
        return []

    with (
        patch("scripts.tune_best_of_n_weight.load_recent_rows", side_effect=fake_loader),
        patch(
            "scripts.tune_best_of_n_weight.build_report",
            return_value=("ok-report", {"sample_count": 0, "recommendation": None}),
        ),
    ):
        text = _render_best_of_n_section(days=days)
    assert captured["days"] == days
    assert "ok-report" in text


def test_render_best_of_n_section_wraps_text_in_code_fence():
    """직렬화된 출력이 markdown ``` 코드 블록 안에 들어가야 (Korean formatting 보존)."""
    with (
        patch("scripts.tune_best_of_n_weight.load_recent_rows", return_value=[]),
        patch(
            "scripts.tune_best_of_n_weight.build_report",
            return_value=(
                "line1\nline2\n  - indented",
                {"sample_count": 0, "recommendation": None},
            ),
        ),
    ):
        text = _render_best_of_n_section(days=30)
    assert text.count("```") == 2
    assert "line1\nline2\n  - indented" in text
    assert "## Best-of-N Comment-Weight Tuning (dry-run)" in text
