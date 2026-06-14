from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

README = ROOT / "README.md"
OPS_RUNBOOK = ROOT / "docs" / "ops-runbook.md"
BOOTSTRAP = ROOT / "pipeline" / "bootstrap.py"

from scripts.verify_weekly_smoke import (  # noqa: E402
    DEFAULT_RECOMPUTE_CONTRACT_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_REVIEW_EXPERIMENT_PATH,
    DEFAULT_REVIEW_RECORDS_PATH,
    DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
    DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
    EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
    build_review_summary_verification_payload,
    validate_manifest_contract,
)
from scripts.verify_weekly_smoke import (
    build_result_payload as build_verification_payload,
)
from scripts.write_weekly_smoke_inputs import (  # noqa: E402
    build_result_payload as build_writer_manifest,
)
from scripts.write_weekly_smoke_inputs import (
    default_output_paths,
)


def _source_string_constants(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def _commands_starting_with(text: str, prefix: str, *, label: str) -> list[str]:
    commands = [line.strip() for line in text.splitlines() if line.strip().startswith(prefix)]
    if commands:
        return commands
    raise AssertionError(f"{label} is missing a command starting with {prefix!r}")


def _json_block_after(text: str, heading: str) -> str:
    heading_index = text.index(heading)
    fence_start = text.index("```json", heading_index)
    block_start = text.index("\n", fence_start) + 1
    block_end = text.index("```", block_start)
    return text[block_start:block_end].strip()


def _weekly_smoke_build_command(text: str) -> str:
    for command in _commands_starting_with(
        text,
        "py -3 scripts/build_weekly_report.py --payload-input ",
        label="weekly smoke docs",
    ):
        if "--review-experiment-input" in command and "--source-preflight-strategy-input" in command:
            return command
    raise AssertionError("weekly smoke docs are missing the payload-input report build command")


def _weekly_smoke_input_writer_command(text: str) -> str:
    return _commands_starting_with(
        text,
        "py -3 scripts/write_weekly_smoke_inputs.py ",
        label="weekly smoke docs",
    )[0]


def _weekly_smoke_verifier_commands(text: str) -> list[str]:
    return _commands_starting_with(
        text,
        "py -3 scripts/verify_weekly_smoke.py ",
        label="weekly smoke docs",
    )


def _weekly_smoke_verifier_command(text: str) -> str:
    for command in _weekly_smoke_verifier_commands(text):
        if " --json" not in command:
            return command
    raise AssertionError("ops runbook is missing the text weekly_smoke verifier command")


def _weekly_smoke_verifier_json_command(text: str) -> str:
    for command in _weekly_smoke_verifier_commands(text):
        if command.endswith(" --json") and " --manifest " not in command:
            return command
    raise AssertionError("ops runbook is missing the JSON weekly_smoke verifier command")


def _weekly_smoke_manifest_verifier_json_command(text: str) -> str:
    for command in _weekly_smoke_verifier_commands(text):
        if " --manifest " in command and command.endswith(" --json"):
            return command
    raise AssertionError("ops runbook is missing the manifest JSON weekly_smoke verifier command")


def _manifest_command_contract_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    manifest = build_writer_manifest(
        default_output_paths(Path(".tmp")),
        manifest_output=manifest_path,
        self_check=True,
    )
    manifest["commands"]["write_inputs"] = "py -3 scripts/write_weekly_smoke_inputs.py --output-dir .tmp --self-check"
    errors = validate_manifest_contract(manifest)
    assert errors == [
        "manifest_command_missing_fragment:write_inputs:--manifest-output .tmp/weekly_smoke_manifest.json"
    ]

    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
    )
    payload["manifest"] = manifest_path.as_posix()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _manifest_expected_repair_queue_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    errors = ["manifest_expected_repair_queue_mismatch:total=expected_7,actual_6"]
    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
        manifest_repair_queue_payload={
            "ok": False,
            "status": "fail",
            "expected_present": True,
            "expected_is_object": True,
            "checked": True,
            "actual_present": True,
            "expected_key_count": 10,
            "actual_key_count": 10,
            "matched_key_count": 9,
            "mismatch_count": 1,
            "mismatched_keys": ["total"],
            "source_preflight_strategy": DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH.as_posix(),
        },
    )
    payload["manifest"] = manifest_path.as_posix()
    payload["repair_queue"] = {
        "present": True,
        "total": 6,
        "listed": 6,
        "count_total": 6,
        "consistency": "ok",
        "full_queue_available": True,
        "queue_item_count": 6,
        "primary_repair_command_present": True,
        "primary_repair_target": {
            "present": True,
            "command": "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning",
            "type": "evidence_doctor",
            "count": 1,
            "buckets": {"blind|blocked": 1},
            "sources": {"blind": 1},
        },
        "source": "manual_ready_gate.repair_commands",
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _manifest_review_summary_stdout_drift_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    missing_fragment = "not-present-in-review-summary"
    errors = [f"missing_review_summary_stdout_fragment:{missing_fragment}"]
    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
        review_summary_payload=build_review_summary_verification_payload(
            review_records_path=DEFAULT_REVIEW_RECORDS_PATH,
            expected_fragments=[*EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS, missing_fragment],
            errors=errors,
            executed=True,
            returncode=0,
        ),
    )
    payload["manifest"] = manifest_path.as_posix()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _manifest_review_summary_missing_input_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    review_records_path = Path(".tmp/missing_review_queue_report_sample.json")
    errors = [f"review_summary_missing_input:{review_records_path.as_posix()}"]
    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
        review_summary_payload=build_review_summary_verification_payload(
            review_records_path=review_records_path,
            expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
            errors=errors,
            executed=False,
            returncode=None,
        ),
    )
    payload["manifest"] = manifest_path.as_posix()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _manifest_review_summary_manifest_contract_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    errors = ["manifest_invalid_expected_review_stdout_fragment:42"]
    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
        review_summary_payload=build_review_summary_verification_payload(
            review_records_path=DEFAULT_REVIEW_RECORDS_PATH,
            expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
            errors=errors,
            executed=False,
            returncode=None,
        ),
    )
    payload["manifest"] = manifest_path.as_posix()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _manifest_review_summary_timeout_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    errors = ["review_summary_timeout"]
    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
        review_summary_payload=build_review_summary_verification_payload(
            review_records_path=DEFAULT_REVIEW_RECORDS_PATH,
            expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
            errors=errors,
            executed=True,
            returncode=None,
            child_error_tail="Timeout tail: partial stderr before termination",
            child_error_tail_source="stderr",
            child_error_tail_truncated=False,
        ),
    )
    payload["manifest"] = manifest_path.as_posix()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _manifest_review_summary_run_failed_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    errors = ["review_summary_run_failed:OSError"]
    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
        review_summary_payload=build_review_summary_verification_payload(
            review_records_path=DEFAULT_REVIEW_RECORDS_PATH,
            expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
            errors=errors,
            executed=False,
            returncode=None,
            child_error_tail="OSError: CreateProcess failed for review summary",
            child_error_tail_source="exception",
            child_error_tail_truncated=False,
        ),
    )
    payload["manifest"] = manifest_path.as_posix()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _manifest_review_summary_nonzero_exit_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    errors = ["review_summary_exit_code:2"]
    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
        review_summary_payload=build_review_summary_verification_payload(
            review_records_path=DEFAULT_REVIEW_RECORDS_PATH,
            expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
            errors=errors,
            executed=True,
            returncode=2,
            child_error_tail="Traceback tail: RuntimeError: review summary child failed",
            child_error_tail_source="stderr",
            child_error_tail_truncated=False,
        ),
    )
    payload["manifest"] = manifest_path.as_posix()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _manifest_review_summary_mixed_nonzero_stdout_drift_failure_example() -> str:
    manifest_path = Path(".tmp/weekly_smoke_manifest.json")
    missing_fragment = "missing_metric_rate=0.7"
    errors = [
        "review_summary_exit_code:1",
        f"missing_review_summary_stdout_fragment:{missing_fragment}",
    ]
    payload = build_verification_payload(
        errors=errors,
        report_path=DEFAULT_REPORT_PATH,
        review_experiment_path=DEFAULT_REVIEW_EXPERIMENT_PATH,
        source_preflight_trend_path=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        source_preflight_strategy_path=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        recompute_contract_path=DEFAULT_RECOMPUTE_CONTRACT_PATH,
        review_summary_payload=build_review_summary_verification_payload(
            review_records_path=DEFAULT_REVIEW_RECORDS_PATH,
            expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
            errors=errors,
            executed=True,
            returncode=1,
            child_error_tail="Traceback tail: JSONDecodeError: invalid review records",
            child_error_tail_source="stderr",
            child_error_tail_truncated=False,
        ),
    )
    payload["manifest"] = manifest_path.as_posix()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def test_ops_runbook_documents_notion_doctor_failure_triage_order():
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    required_fragments = [
        "Notion doctor failure triage order:",
        "1. `credential_check`",
        "2. `publish_safety_check`",
        "3. `error_code` and `error_message`",
        "4. `notion_retry_summary`, `notion_failure_classification`, and `notion_operator_action`",
        "5. `accessible_objects`",
        "6. `actions`",
        "Bearer token validity",
        "database/data_source ID and collection mode",
        "403/404 sharing",
        "retry/backoff categories",
        "Notion integration Bearer token",
        "`collection_kind=data_source`",
        "`Notion-Version 2025-09-03`",
        "operator_action_required=false",
        "auto_publish_env_enabled=false",
        "image_generation_env_enabled=false",
        "twitter_config_enabled=false",
        "manual_publish_required=true",
        "side_effect_env_keys_enabled=(none)",
        "empty JSON list",
        "credential_values_redacted=true",
        "must not print credential values",
        "Do not commit JSON output, `.env`, logs, screenshots, or `.tmp/failures` evidence.",
        "Notion retry classification:",
        "`notion_failure_classification.category`",
        "`rate_limited`",
        "`service_overload`",
        "`transient_server_error`",
        "`credential_invalid`",
        "`permission_or_sharing`",
        "`object_not_found_or_not_shared`",
        "`schema_or_payload`",
        "`notion_failure_classification.retry_recommended`",
        "`wait_seconds`",
        "`notion_failure_classification.primary_repair`",
        "Automation mapping:",
        "`credential_invalid` -> use `notion_operator_action` to rotate or replace `NOTION_API_KEY`",
        "`permission_or_sharing` -> share the target database/data source with the Notion integration",
        "`object_not_found_or_not_shared` -> verify `NOTION_DATABASE_ID` and sharing",
        "`rate_limited`, `service_overload`, or `transient_server_error` -> honor `Retry-After`/backoff",
        "Redacted `notion_doctor --json` failure sample for automation:",
        '"token_masked": "ntn_...alue"',
        '"last_status": 403',
        '"category": "permission_or_sharing"',
        '"primary_repair": "share_database_with_integration"',
        '"notion_operator_action": "Share the target database/data source with the Notion integration before rerun."',
        "Automation should treat this sample as a field contract",
        "keep real JSON output, `.env`, logs, screenshots, and `.tmp/failures` evidence out of commits",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_ops_runbook_notion_doctor_json_sample_is_parseable_and_redacted():
    text = OPS_RUNBOOK.read_text(encoding="utf-8")
    sample_text = _json_block_after(text, "Redacted `notion_doctor --json` failure sample for automation:")

    payload = json.loads(sample_text)

    assert payload["token_masked"] == "ntn_...alue"
    assert payload["notion_retry_summary"] == {
        "last_status": 403,
        "retryable": False,
    }
    assert payload["notion_failure_classification"] == {
        "category": "permission_or_sharing",
        "retry_recommended": False,
        "primary_repair": "share_database_with_integration",
    }
    assert (
        payload["notion_operator_action"]
        == "Share the target database/data source with the Notion integration before rerun."
    )
    assert payload["actions"] == [
        "For 403 restricted_resource or 404 object_not_found, share the target database/data source with the integration"
    ]

    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden_fragments = [
        "ntn_test_secret_value",
        "json-secret-value",
        "TWITTER_ACCESS_TOKEN",
        "NOTION_API_KEY=",
        "NOTION_DATABASE_ID=",
        ".env",
        ".tmp",
        "screenshots/",
        "token.json",
        "credentials.json",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in serialized


def test_ops_runbook_documents_provider_key_check_interpretation():
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    required_fragments = [
        "Provider key check interpretation:",
        "`provider_key_check.operator_action_required`",
        "`provider_key_check.missing_enabled_providers`",
        "`provider_key_check.ready_enabled_provider_count`",
        "`provider_key_check.enabled_provider_count`",
        "`provider_key_check.credential_values_redacted`",
        "keep this `true`",
        "`provider_key_check.checks[].provider`",
        "`enabled`",
        "`ready`",
        "`severity`",
        "`env_keys`",
        "`env_state`",
        "`env_key_states`",
        "`config_key`",
        "`config_state`",
        "`operator_action`",
        "`llm.providers`",
        "`claude` to `anthropic`",
        "`grok` to `xai`",
        "`chatgpt` to `openai`",
        "must not print API key values",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_ops_runbook_documents_cost_persistence_fail_open_triage():
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    required_fragments = [
        "Cost Persistence Fail-Open Triage",
        "`CostTracker.get_cost_persistence_status()`",
        "`status=degraded`",
        "`fail_open=true`",
        "`event_count`",
        "`retained_event_count`",
        "`total_event_count`",
        "`operation_count`",
        "`operations`",
        "`last_operation`",
        "`last_error_type`",
        "`error_types`",
        "`operator_action`",
        "`Cost Persistence: degraded`",
        "`Cost Persistence Last Error`",
        "`Cost Persistence Action`",
        "`check_budget()`",
        (
            "`Cost persistence status: status=... fail_open=... event_count=... operation_count=... "
            "operations=... retained_event_count=... total_event_count=...`"
        ),
        "`Cost persistence operator action: ...`",
        "observational only",
        "must not trigger automatic publish, source strategy changes, or CostDB repair",
        "check `.tmp/btx_costs.db` permissions/locks",
        "continue with in-memory counters",
        "Do not commit `btx_costs.db`, archive DB files, `.tmp/workspace.db`, logs, or generated cost evidence.",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_recompute_runtime_contract_gate_is_documented_in_readme_and_runbook():
    required_fragments = [
        "First-class runtime-contract gate before scoring:",
        "py -3 scripts/recompute_scores.py --assert-runtime-contract --input .tmp/recompute_scores_fixture.json --json",
        "Use this first-class gate instead of maintaining the jq/Python one-liner; it exits 0 only when validation is ok and the runtime contract says validation loads no runtime dependencies or scoring.",
        "Optional field-level check for saved validation JSON:",
        "jq -e '.ok == true",
        ".runtime_contract.validation.loads_runtime_dependencies == false",
        ".runtime_contract.validation.scoring_runs == false",
        ".runtime_contract.scoring_dry_run.scoring_dependencies_may_initialize == true",
        ".tmp/recompute_scores_validate.json",
        "If `jq` is not installed, use the Python fallback:",
        'py -3 -c "import json,pathlib;',
        "encoding='utf-8-sig'",
        "raise SystemExit(0 if ok else 1)",
        "The first-class gate reads only the validation JSON path and does not run scoring, Notion reads, Notion writes, X posts, providers, or browser capture.",
    ]
    doc_specific_fragments = {
        README: (
            "py -3 scripts/recompute_scores.py --validate-input --input .tmp/recompute_scores_fixture.json --json > .tmp/recompute_scores_validate.json",
        ),
        OPS_RUNBOOK: (
            "py -3 scripts/recompute_scores.py --validate-input --input .tmp/recompute_scores_fixture.json --json | Set-Content -Encoding utf8 .tmp/recompute_scores_validate.json",
        ),
    }

    for path in (README, OPS_RUNBOOK):
        text = path.read_text(encoding="utf-8")
        for fragment in required_fragments:
            assert fragment in text, f"{path.name} missing {fragment!r}"
        for fragment in doc_specific_fragments[path]:
            assert fragment in text, f"{path.name} missing {fragment!r}"


def test_ops_runbook_documents_source_preflight_problem_action_fields():
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    required_fragments = [
        "Source Preflight Structured Operator Actions",
        "`summary.problem_actions[]` includes",
        "`operator_action_required=true`",
        "`operator_action` matching `action`",
        "same structured operator signal as `results[]` and failure reports",
        "`operator_action_mismatch`",
        "preflight summary and failure report disagree",
        "rerun the evidence doctor or recapture the source preflight",
        "`summary.operator_action_mismatch_count`",
        "`summary.operator_action_mismatch_source_counts`",
        "`summary.evidence_field_counts`",
        "`evidence_fields:`",
        "`failure_report_path`",
        "`screenshot_path`",
        "`html_snapshot_path`",
        "`trace_path`",
        "`trace_viewer_command`",
        "`trace_viewer_hint`",
        "`trace_viewer item=N source=SOURCE: playwright show-trace ...`",
        "`exception_type`",
        "`Operator action mismatches:`",
        "Trend CLI JSON exposes the same mismatch counts",
        "`operator_action_mismatches:`",
        "before weekly aggregation",
        "`source_preflight_evidence_doctor.py` text output prints",
        "`operator_action item=N source=SOURCE: required=true action=...`",
        "For trace-backed evidence",
        "stdout-only operators can see the required action",
        "`source_preflight_trend_report.py` preserves original operator actions",
        "`summary.operator_action_counts`",
        "`summary.top_operator_actions[]`",
        "weekly reports render those top actions",
        "source trend evidence coverage as `Evidence fields:`",
        "source trend evidence field coverage",
        "`Operator action mismatches:`",
        "mismatch source count",
        "`Strategy operator action mismatches:`",
        "strategy mismatch source count",
        "Strategy simulation summary preserves trend `summary.top_operator_actions[]`",
        "Strategy simulation summary preserves `operator_action_mismatch_count`",
        "mismatch-derived stale evidence stays in `fix_evidence_first`",
        "`manual_ready_gate.status=blocked`",
        "`manual_ready_gate.primary_repair_command` order `source_preflight_evidence_doctor.py` before source recapture",
        "Run the evidence doctor first so saved evidence is inspected or repaired before browser recapture",
        "`summary.repair_command_queue` preserves the full ordered repair queue",
        "`sum(summary.repair_command_queue[].count)` must match `manual_ready_gate.repair_command_count`",
        "`Repair queue: listed=N` remains the unique command string count",
        "`buckets=source|status=count`",
        "first source/status repair bucket",
        "`count_total=N`",
        "`consistency=ok|mismatch`",
        "`summary.repair_command_queue_consistency`",
        "`top_repair_commands` is display-only",
        "Weekly smoke manifests include `Repair queue:`, `Primary repair target:`, `count_total=6`, and `consistency=ok`",
        "`verify_weekly_smoke.py` checks blocked `manual_ready_gate.repair_commands` presence",
        "`summary.repair_command_queue` count coverage",
        "per-item bucket/source fragments for the primary repair target",
        "`summary.repair_command_queue_consistency` before accepting the report",
        "During weekly report review, if `repair_remaining>=1`, read `Primary repair target:` first",
        "primary repair target type/count/bucket/source text",
        "Generated manifests also include `expected_repair_queue`",
        "`expected_strategy_stdout_fragments`",
        "`primary_repair_buckets=blind|blocked=1`",
        "`primary_repair_sources=blind=1`",
        "`repair_remaining=5`",
        "`operator_action_mismatch_sources=ppomppu=1`",
        "`scope=local_preflight_evidence`",
        "mirrors the structured `repair_queue` JSON object",
        "`paths.source_preflight_strategy`",
        "Manifest mode and writer `--self-check` compare the expected object",
        "catch stale generated manifests before parsing report Markdown",
        "`manifest_repair_queue`",
        "`manifest_repair_queue.ok`",
        "`manifest_repair_queue.checked`",
        "`manifest_repair_queue.matched_key_count`",
        "`manifest_repair_queue.mismatch_count`",
        "`manifest_repair_queue.mismatched_keys`",
        "`manifest_expected_repair_queue_mismatch:*`",
        "`manifest_expected_repair_queue_not_object`",
        "`manifest_expected_repair_queue_missing_strategy_path`",
        "`manifest_expected_repair_queue_unavailable`",
        "Compact manifest expectation:",
        '"expected_repair_queue": {',
        '"present": true',
        '"primary_repair_target": {',
        '"buckets": {"blind|blocked": 1}',
        '"sources": {"blind": 1}',
        '"source": "manual_ready_gate.repair_commands"',
        "Stale expected repair queue example:",
        "`repair_queue=ok|mismatch`",
        "`primary_repair_type=TYPE`",
        "`primary_repair_count=N`",
        "`primary_repair_buckets=SOURCE|STATUS=N`",
        "`primary_repair_sources=SOURCE=N`",
        "`summary.repair_command_queue[].buckets`",
        "`verify_weekly_smoke.py --json` also emits a structured `repair_queue` object",
        "`repair_queue.total`",
        "`repair_queue.listed`",
        "`repair_queue.count_total`",
        "`repair_queue.consistency`",
        "`repair_queue.full_queue_available`",
        "`repair_queue.queue_item_count`",
        "`repair_queue.primary_repair_command_present`",
        "`repair_queue.primary_repair_target`",
        "instead of parsing the Markdown report line",
        "Compact expected shape:",
        '"repair_queue": {',
        '"total": 6',
        '"listed": 6',
        '"count_total": 6',
        '"consistency": "ok"',
        '"full_queue_available": true',
        '"queue_item_count": 6',
        '"primary_repair_command_present": true',
        "Mismatch shape:",
        '"total": 2',
        '"listed": 1',
        '"count_total": 1',
        '"consistency": "mismatch"',
        '"full_queue_available": false',
        '"queue_item_count": 1',
        "PowerShell extraction:",
        "$payload = py -3 scripts/verify_weekly_smoke.py --manifest .tmp/weekly_smoke_manifest.json",
        "--verify-review-summary --verify-strategy-summary --json | ConvertFrom-Json",
        "$payload.manifest_repair_queue | ConvertTo-Json -Compress",
        "$payload.repair_queue | ConvertTo-Json -Compress",
        "Generated manifests also verify `expected_strategy_stdout_fragments`",
        "`paths.source_preflight_strategy`",
        "Unlike the review-summary check",
        "does not run browser, Notion, providers, X, or the manifest command string",
        "`strategy_summary` block",
        "`strategy_summary`",
        "`strategy_summary.diagnosis`",
        "`strategy_summary.failure_reasons`",
        "`strategy_summary.missing_stdout_fragments`",
        "`strategy_summary.stdout_drift`",
        "`strategy_summary.format_failed`",
        "`strategy_summary.manifest_contract_error`",
        "`missing_strategy_stdout_fragment:*`",
        '`error_categories=["strategy_summary"]`',
        "`manifest_invalid_expected_strategy_stdout_fragment:*`",
        "weekly `Source Preflight Strategy A/B` output renders `Source operator actions`",
        "`Source trend operator actions:`",
        "Source operator actions:",
        "`operator_action_mismatch_count=N`",
        "`operator_action_mismatch_sources=SOURCE=N`",
        "`evidence_fields=FIELD=N`",
        "`summary.evidence_field_counts`",
        "`top_operator_action_count=N`",
        "`top_operator_action_sources=SOURCE=N`",
        "`top_operator_action=...`",
        "stdout-only operators can see the first repair bucket, stale evidence, and the original evidence-doctor action",
        "weekly_smoke=ok",
        "top_operator_actions",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_ops_runbook_documents_review_experiment_summary_operator_actions():
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    required_fragments = [
        "Review experiment summary-only stdout includes",
        "`missing_metric_rate=N`",
        "`top_missing_metric=METRIC`",
        "`top_missing_metric_count=N`",
        "`top_missing_owner=OWNER`",
        "`top_missing_owner_count=N`",
        "`top_missing_owner_metric=METRIC`",
        "`operator_actions_total=N`",
        "`avg_operator_actions=N`",
        "`high_noise_items=N`",
        "`safety_risk_items=N`",
        "`safety_risk_flags=FLAG=N`",
        "`provider_failure_categories=CATEGORY=N`",
        "`provider_failure_providers=PROVIDER=N`",
        "`primary_provider_failure_categories=CATEGORY=N`",
        "`primary_provider_failure_providers=PROVIDER=N`",
        "`top_operator_action=...`",
        "`top_operator_action_count=N`",
        "`top_operator_action_reason=...`",
        "`rollout_blocker_count=N`",
        "`rollout_blocker_codes=CODE[,CODE]`",
        "`top_rollout_blocker_action=...`",
        (
            "stdout-only operators can see objective-metric gaps, owner gaps, action noise, rollout blockers, "
            "provider failure causes, the first provider repair target, and safety risk before opening JSON"
        ),
        "Weekly report payload smoke renders review experiment top actions",
        "`Review top operator actions:`",
        "`Missing metric owners:`",
        "`Safety risk flags:`",
        "`Provider failures:`",
        "`Provider failure repair:`",
        "`Source trend operator actions:`",
        "`Recompute Scores Runtime Contract (dry-run)`",
        "`recompute_scores_runtime_contract_smoke.json`",
        "`--recompute-contract-input`",
        "`--recompute-contract`",
        "`summary.candidate_top_operator_actions[]`",
        "`summary.candidate_safety_risk_item_count`",
        "`summary.candidate_provider_failure_category_counts`",
        "`summary.candidate_provider_failure_provider_counts`",
        "`summary.candidate_primary_provider_failure_category_counts`",
        "`summary.candidate_primary_provider_failure_provider_counts`",
        "`summary.candidate_primary_provider_failure_actions[]`",
        "`primary_categories=`",
        "`primary_providers=`",
        "The `Provider failure repair:` line surfaces",
        "review provider repair action text",
        "the first repair target is visible without opening JSON",
        "Provider failure triage order:",
        "`provider_failure_summary.primary_failure`",
        "`primary_operator_action`",
        "`primary_failure.category`",
        "auth, quota/billing, and invalid-output categories are repair-first",
        "rate-limit, overload, server, timeout, and network categories are retry/backoff candidates",
        "`candidate_provider_failure_*` counts describe the total incident shape",
        "`candidate_primary_provider_failure_*` counts identify the first repair target",
        "Do not apply: do not change LLM fallback order only because the primary failure is retryable or transient.",
        "Risk: if provider status/rate-limit semantics drift",
        "`classify_provider_failure()`",
        "scripts/write_weekly_smoke_inputs.py --output-dir .tmp",
        "`schema_version`",
        "`safety_contract`",
        "`commands`",
        "`expected_report_fragments`",
        "`Repair queue:`",
        "`expected_review_stdout_fragments`",
        "`expected_strategy_stdout_fragments`",
        "`provider_failure_categories=auth=1,rate_limit=1`",
        "`provider_failure_providers=gemini=1,openai=1`",
        "`primary_provider_failure_categories=auth=1`",
        "`primary_provider_failure_providers=openai=1`",
        "primary repair-axis",
        "`expected_repair_queue`",
        "`self_check`",
        "`self_check=ok`",
        "`write_inputs`",
        "`commands.review_summary`",
        "`commands.build_report`",
        "`commands.verify_text`",
        "`commands.verify_json`",
        "`commands.verify_manifest`",
        "`--verify-review-summary`",
        "`--verify-strategy-summary`",
        "`manifest_schema_version_mismatch`",
        "`manifest_profile_mismatch`",
        "`manifest_safety_mismatch:*`",
        "`manifest_missing_expected_fragment:*`",
        "`manifest_missing_expected_review_stdout_fragment:*`",
        "`manifest_invalid_expected_strategy_stdout_fragment:*`",
        "`missing_strategy_stdout_fragment:*`",
        "`manifest_expected_repair_queue_mismatch:*`",
        "`review_summary_missing_input:*`",
        "`missing_review_summary_stdout_fragment:*`",
        '`error_categories=["strategy_summary"]`',
        '`error_categories=["review_summary"]`',
        "`review_summary` block",
        "`review_summary.diagnosis`",
        "`review_summary.failure_reasons`",
        "`review_summary.missing_stdout_fragments`",
        "`review_summary.missing_input`",
        "`review_summary.stdout_drift`",
        "`review_summary.timeout`",
        "`review_summary.nonzero_exit`",
        "`review_summary.run_failed`",
        "`review_summary.manifest_contract_error`",
        "runs that dry-run child process",
        "`review_summary.child_error_tail`",
        "`review_summary.child_error_tail_source`",
        "`review_summary.child_error_tail_truncated`",
        "The primary diagnosis is always the first prioritized `review_summary.failure_reasons` entry",
        "route on `review_summary.diagnosis` while still preserving secondary causes",
        '`error_categories=["manifest"]` appears with a `review_summary` block',
        "the review-summary child did not run (`executed=false`, `returncode=null`)",
        "fix the manifest/writer contract first",
        "bounded stderr/stdout tail",
        "inspect `review_summary.child_error_tail` when present",
        "If `review_summary.nonzero_exit=true`, inspect `review_summary.child_error_tail` when present",
        "Text mode keeps review-summary failures compact as `weekly_smoke=fail reason=...`",
        "child stderr/stdout tails stay JSON-only in `review_summary.child_error_tail`",
        "`review_summary_timeout`",
        "`review_summary_run_failed:*`",
        "`review_summary_missing_input:*`",
        "`review_summary_exit_code:*`",
        "`missing_review_summary_stdout_fragment:*`",
        "treat `matched_stdout_fragment_count` as partial evidence only",
        "the manifest/stdout contract should be checked again after the child exit is fixed",
        "failed before summary output",
        "summary started but its contract was incomplete",
        "Review-summary failure triage order:",
        "`missing_input` / `review_summary_missing_input:*`",
        "`manifest_contract` / `manifest_invalid_expected_review_stdout_fragment:*`",
        "`timeout` / `review_summary_timeout`",
        "`run_failed` / `review_summary_run_failed:*`",
        '`review_summary.child_error_tail_source="exception"`',
        "`nonzero_exit` / `review_summary_exit_code:*`",
        "`stdout_drift` / `missing_review_summary_stdout_fragment:*`",
        "only after higher-priority failures are clear",
        "Review-summary stdout drift example:",
        "Review-summary missing input example:",
        "Review-summary manifest contract example:",
        "Review-summary timeout example:",
        "Review-summary run failed example:",
        "Review-summary nonzero exit example:",
        "Review-summary mixed nonzero/stdout drift example:",
        "`review_records`",
        "`executed`",
        "`returncode`",
        "`expected_stdout_fragment_count`",
        "`matched_stdout_fragment_count`",
        "`missing_stdout_fragment_count`",
        "`timeout_seconds`",
        "`summary.candidate_top_missing_metric_owners[]`",
        "`missing_metric_rate_high`",
        "`Next manual action:` should preserve the owner-specific `operator_action`",
        "`cost_tracking: Include token_cost_estimate from the generation cost tracker.`",
        "`summary.candidate_rollout_blocker_actions[]`",
        "`Rollout blocker actions:`",
        "`code`, `source`, `operator_action`",
        "`owner`, `top_metric`",
        "`manifest_missing_commands`",
        "`manifest_missing_command:*`",
        "`manifest_command_missing_fragment:*`",
        "`review_summary`",
        "`--manifest-output .tmp/weekly_smoke_manifest.json`",
        "`--self-check`",
        "`--verify-strategy-summary`",
        "copy-ready",
        "`error_categories`",
        '`error_categories=["manifest"]`',
        "`weekly_smoke=fail category=manifest`",
        "`manifest_safety_mismatch:notion_writes=expected_false,actual_True`",
        "`.tmp/weekly_report_experiment_smoke.json`",
        "`.tmp/source_preflight_trend.json`",
        "`.tmp/recompute_scores_runtime_contract_smoke.json`",
        "top review action count/action/reason",
        "top source trend action text",
        "`weekly_smoke=fail reason=...`",
        "`--json`",
        "`ok`",
        "`status`",
        "`errors`",
        "`paths`",
        "weekly_smoke=ok",
    ]
    for fragment in required_fragments:
        assert fragment in text

    readme_text = README.read_text(encoding="utf-8")
    readme_required_fragments = [
        "`primary_provider_failure_categories=CATEGORY=N`",
        "`primary_provider_failure_providers=PROVIDER=N`",
        "`primary_categories=`",
        "`primary_providers=`",
        "`provider_failure_summary.primary_failure`",
        "`primary_operator_action`",
        "Do not change fallback order only because a primary failure is retryable.",
    ]
    for fragment in readme_required_fragments:
        assert fragment in readme_text


def test_weekly_smoke_manifest_command_contract_failure_example_matches_verifier():
    expected_example = _manifest_command_contract_failure_example()

    for path in [README, OPS_RUNBOOK]:
        text = path.read_text(encoding="utf-8")
        assert "Command-contract drift example:" in text
        assert expected_example in text


def test_weekly_smoke_manifest_expected_repair_queue_example_matches_verifier():
    expected_example = _manifest_expected_repair_queue_failure_example()
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    assert "Stale expected repair queue example:" in text
    assert expected_example in text


def test_weekly_smoke_manifest_review_summary_stdout_drift_example_matches_verifier():
    expected_example = _manifest_review_summary_stdout_drift_failure_example()
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    assert "Review-summary stdout drift example:" in text
    assert expected_example in text


def test_weekly_smoke_manifest_review_summary_missing_input_example_matches_verifier():
    expected_example = _manifest_review_summary_missing_input_failure_example()
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    assert "Review-summary missing input example:" in text
    assert expected_example in text


def test_weekly_smoke_manifest_review_summary_manifest_contract_example_matches_verifier():
    expected_example = _manifest_review_summary_manifest_contract_failure_example()
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    assert "Review-summary manifest contract example:" in text
    assert expected_example in text


def test_weekly_smoke_manifest_review_summary_timeout_example_matches_verifier():
    expected_example = _manifest_review_summary_timeout_failure_example()
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    assert "Review-summary timeout example:" in text
    assert expected_example in text


def test_weekly_smoke_manifest_review_summary_run_failed_example_matches_verifier():
    expected_example = _manifest_review_summary_run_failed_failure_example()
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    assert "Review-summary run failed example:" in text
    assert expected_example in text


def test_weekly_smoke_manifest_review_summary_nonzero_exit_example_matches_verifier():
    expected_example = _manifest_review_summary_nonzero_exit_failure_example()
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    assert "Review-summary nonzero exit example:" in text
    assert expected_example in text


def test_weekly_smoke_manifest_review_summary_mixed_nonzero_stdout_drift_example_matches_verifier():
    expected_example = _manifest_review_summary_mixed_nonzero_stdout_drift_failure_example()
    text = OPS_RUNBOOK.read_text(encoding="utf-8")

    assert "Review-summary mixed nonzero/stdout drift example:" in text
    assert expected_example in text


def test_ops_runbook_weekly_smoke_verifier_locks_required_inputs_and_assertions():
    command = _weekly_smoke_verifier_command(OPS_RUNBOOK.read_text(encoding="utf-8"))

    required_fragments = [
        "scripts/verify_weekly_smoke.py",
        "--report",
        ".tmp/weekly_report_smoke.md",
        "--review-experiment",
        ".tmp/weekly_report_experiment_smoke.json",
        "--source-preflight-trend",
        ".tmp/source_preflight_trend.json",
        "--source-preflight-strategy",
        ".tmp/source_preflight_strategy_simulation.json",
        "--recompute-contract",
        ".tmp/recompute_scores_runtime_contract_smoke.json",
    ]
    for fragment in required_fragments:
        assert fragment in command


def test_ops_runbook_weekly_smoke_verifier_json_command_is_copy_ready():
    command = _weekly_smoke_verifier_json_command(OPS_RUNBOOK.read_text(encoding="utf-8"))

    required_fragments = [
        "scripts/verify_weekly_smoke.py",
        "--report",
        ".tmp/weekly_report_smoke.md",
        "--review-experiment",
        ".tmp/weekly_report_experiment_smoke.json",
        "--source-preflight-trend",
        ".tmp/source_preflight_trend.json",
        "--source-preflight-strategy",
        ".tmp/source_preflight_strategy_simulation.json",
        "--recompute-contract",
        ".tmp/recompute_scores_runtime_contract_smoke.json",
        "--json",
    ]
    for fragment in required_fragments:
        assert fragment in command
    assert command.endswith(" --json")


@pytest.mark.parametrize(
    ("description", "command_getter"),
    [
        ("weekly smoke input writer", _weekly_smoke_input_writer_command),
        ("weekly report payload smoke build", _weekly_smoke_build_command),
        ("weekly smoke JSON verifier", _weekly_smoke_verifier_json_command),
        ("weekly smoke manifest JSON verifier", _weekly_smoke_manifest_verifier_json_command),
    ],
)
def test_readme_and_ops_runbook_weekly_smoke_commands_stay_in_sync(description, command_getter):
    readme_command = command_getter(README.read_text(encoding="utf-8"))
    ops_command = command_getter(OPS_RUNBOOK.read_text(encoding="utf-8"))

    assert readme_command == ops_command, f"{description} command drifted between README and ops runbook"


def test_cost_persistence_runtime_log_templates_stay_documented():
    constants = _source_string_constants(BOOTSTRAP)
    status_template = next(constant for constant in constants if constant.startswith("Cost persistence status:"))
    action_template = next(
        constant for constant in constants if constant.startswith("Cost persistence operator action:")
    )
    required_fragments = [
        f"`{status_template.replace('%s', '...')}`",
        f"`{action_template.replace('%s', '...')}`",
    ]

    for path in [README, OPS_RUNBOOK]:
        text = path.read_text(encoding="utf-8")
        for fragment in required_fragments:
            assert fragment in text, f"{path} is missing runtime log fragment: {fragment}"
