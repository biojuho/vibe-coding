from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_source_preflight_repair_flow_runbook_is_linked_from_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/source-preflight-repair-flow.md" in readme
    assert "repair_command_debt blocks source strategy review" in readme
    assert "--source-preflight-print-options" in readme
    assert "without browser, Notion, X, or provider calls" in readme


def test_source_preflight_repair_flow_documents_manual_gate_and_safety():
    text = (ROOT / "docs/source-preflight-repair-flow.md").read_text(encoding="utf-8")

    required_fragments = [
        "manual_ready_gate.status=blocked",
        "comparison.recommendation=repair_evidence_first",
        "repair_command_debt",
        "`operator_action_mismatch`",
        "stale-evidence signal",
        "Repair or recapture evidence first",
        "Strategy simulation preserves `operator_action_mismatch_count`",
        "mismatch-driven stale evidence in `fix_evidence_first`",
        "strategy_review_ready",
        "--summary-only",
        "repair_remaining=N",
        "metric_missing=current:N/10,candidate:N/10",
        "operator_action_mismatch_count=N",
        "operator_action_mismatch_sources=SOURCE=N",
        "scope=local_preflight_evidence",
        "top_operator_action_count=N",
        "top_operator_action_sources=SOURCE=N",
        "top_operator_action=...",
        "summary.top_repair_commands",
        "source_preflight_evidence_doctor.py",
        "source_preflight_trend_report.py",
        "source_preflight_strategy_simulation.py",
        "--source-preflight-print-options",
        "browser_probe_will_run=false",
        "notion_writes=false",
        "x_posts=false",
        "read_only=true",
        "auto_apply_allowed=false",
        "manual_strategy_review_required=true",
        "does not launch Playwright",
        "auto-publish",
        "Do Not Apply: automatic publish",
        "Do not commit evidence files",
    ]
    for fragment in required_fragments:
        assert fragment in text
