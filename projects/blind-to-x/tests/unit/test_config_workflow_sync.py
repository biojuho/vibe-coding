"""Validate the project-local pipeline workflow spec stays in sync with config.example.yaml.

The validated workflow file (projects/blind-to-x/.github/workflows/blind-to-x.yml)
is a kept-versioned specification, NOT an actively running GitHub workflow
(GitHub only discovers workflows in the repo-root .github/workflows/). The live
PR/push CI for blind-to-x is .github/workflows/full-test-matrix.yml's
"blind-to-x-tests" job at the repo root.
"""

from __future__ import annotations

import json
import re
import sys
import textwrap
from pathlib import Path

import pytest
import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXAMPLE_CONFIG = ROOT / "config.example.yaml"
CI_CONFIG = ROOT / "config.ci.yaml"
ENV_EXAMPLE = ROOT / ".env.example"
README = ROOT / "README.md"
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "blind-to-x.yml"
SOURCE_PREFLIGHT_REQUIRED_KEYS = {
    "timeout_ms",
    "output_path",
    "screenshot_dir",
    "failure_dir",
    "trace_dir",
    "click_through_default",
    "use_recommended_source_default",
    "safety",
}
SOURCE_PREFLIGHT_SAFETY_REQUIRED_KEYS = {
    "read_only",
    "notion_writes",
    "x_posts",
    "auto_apply_allowed",
    "manual_strategy_review_required",
}
ENV_PUBLISH_SAFETY_DEFAULTS = {
    "AUTO_PUBLISH": "false",
    "OPENAI_IMAGE_ENABLED": "false",
    "TWITTER_CONSUMER_KEY": "",
    "TWITTER_CONSUMER_SECRET": "",
    "TWITTER_ACCESS_TOKEN": "",
    "TWITTER_ACCESS_TOKEN_SECRET": "",
    "X_BEARER_TOKEN": "",
    "THREADS_ACCESS_TOKEN": "",
}
ENV_PUBLISH_UNSAFE_TRUE_KEYS = {
    "AUTO_PUBLISH",
    "OPENAI_IMAGE_ENABLED",
    "TWITTER_ENABLED",
    "X_AUTO_PUBLISH",
    "THREADS_AUTO_PUBLISH",
    "BLOG_AUTO_PUBLISH",
}

from config import ConfigManager  # noqa: E402
from pipeline.cli import (  # noqa: E402
    _mark_source_preflight_cli_overrides,
    build_parser,
    run_source_preflight_command,
)


def _extract_generated_config_yaml(workflow_text: str) -> str:
    # 1. 헤어독 패턴 (레거시 방식)
    match = re.search(
        r"cat << '?YAML_EOF'? > config\.yaml\r?\n(?P<body>.*?)\r?\n\s*YAML_EOF",
        workflow_text,
        flags=re.DOTALL,
    )
    if match:
        return textwrap.dedent(match.group("body"))

    # 2. envsubst 방식: config.ci.yaml을 템플릿으로 사용
    if "envsubst" in workflow_text and "config.ci.yaml" in workflow_text:
        ci_config = CI_CONFIG
        if ci_config.exists():
            return ci_config.read_text(encoding="utf-8")

    assert False, (
        "Workflow config generation step not found. "
        "Expected either a heredoc (cat << 'YAML_EOF' ... YAML_EOF) "
        "or envsubst < config.ci.yaml > config.yaml pattern."
    )


def _leaf_paths(obj: object, prefix: tuple[str, ...] = ()) -> set[str]:
    if isinstance(obj, dict):
        paths: set[str] = set()
        if not obj:
            paths.add(".".join(prefix))
            return paths
        for key, value in obj.items():
            paths |= _leaf_paths(value, prefix + (str(key),))
        return paths
    return {".".join(prefix)}


def _get_nested(obj: dict, path: str):
    cur = obj
    for part in path.split("."):
        assert isinstance(cur, dict), f"Expected dict while resolving {path}, got {type(cur)}"
        assert part in cur, f"Missing key: {path}"
        cur = cur[part]
    return cur


def test_workflow_generated_config_matches_example_keyset():
    example_cfg = yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    workflow_yaml = _extract_generated_config_yaml(WORKFLOW_FILE.read_text(encoding="utf-8"))
    workflow_cfg = yaml.safe_load(workflow_yaml)

    example_keys = _leaf_paths(example_cfg)
    workflow_keys = _leaf_paths(workflow_cfg)

    missing = sorted(example_keys - workflow_keys)
    extra = sorted(workflow_keys - example_keys)
    assert not missing and not extra, f"Keyset mismatch.\nmissing_in_workflow={missing}\nextra_in_workflow={extra}"


def test_workflow_generated_config_contains_notion_url_property():
    workflow_yaml = _extract_generated_config_yaml(WORKFLOW_FILE.read_text(encoding="utf-8"))
    workflow_cfg = yaml.safe_load(workflow_yaml)
    assert workflow_cfg["notion"]["properties"]["url"]


def test_workflow_generated_config_required_values_non_empty():
    workflow_yaml = _extract_generated_config_yaml(WORKFLOW_FILE.read_text(encoding="utf-8"))
    workflow_cfg = yaml.safe_load(workflow_yaml)

    required_paths = [
        "notion.properties.url",
        "notion.properties.title",
        "request.timeout_seconds",
        "scrape_quality.min_content_length",
    ]
    for path in required_paths:
        value = _get_nested(workflow_cfg, path)
        assert value not in ("", None), f"Required value is empty: {path}"


def test_example_config_source_preflight_defaults_match_cli_contract():
    example_cfg = yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    source_preflight = example_cfg["source_preflight"]
    args = build_parser().parse_args(["--require-source-ready"])

    assert source_preflight["timeout_ms"] == args.source_preflight_timeout_ms
    assert source_preflight["output_path"] == args.source_preflight_output.as_posix()
    assert source_preflight["screenshot_dir"] == args.source_preflight_screenshot_dir.as_posix()
    assert source_preflight["failure_dir"] == args.source_preflight_failure_dir.as_posix()
    assert source_preflight["trace_dir"] == ".tmp/traces/source_preflight"
    assert source_preflight["click_through_default"] is False
    assert source_preflight["use_recommended_source_default"] is False


def test_ci_config_source_preflight_block_matches_example():
    example_cfg = yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    ci_cfg = yaml.safe_load(CI_CONFIG.read_text(encoding="utf-8"))

    assert ci_cfg["source_preflight"] == example_cfg["source_preflight"]


def test_source_preflight_config_blocks_have_required_schema():
    config_paths = {
        "config.example.yaml": EXAMPLE_CONFIG,
        "config.ci.yaml": CI_CONFIG,
    }

    for label, path in config_paths.items():
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        block = config.get("source_preflight")
        assert isinstance(block, dict), f"{label}: source_preflight must be a mapping"

        missing = sorted(SOURCE_PREFLIGHT_REQUIRED_KEYS - block.keys())
        unexpected = sorted(block.keys() - SOURCE_PREFLIGHT_REQUIRED_KEYS)
        assert not missing, f"{label}: source_preflight missing keys: {missing}"
        assert not unexpected, f"{label}: source_preflight unexpected keys: {unexpected}"

        assert type(block["timeout_ms"]) is int, f"{label}: source_preflight.timeout_ms must be int"
        for key in ("output_path", "screenshot_dir", "failure_dir", "trace_dir"):
            assert isinstance(block[key], str) and block[key], f"{label}: source_preflight.{key} must be non-empty str"
        for key in ("click_through_default", "use_recommended_source_default"):
            assert type(block[key]) is bool, f"{label}: source_preflight.{key} must be bool"

        safety = block["safety"]
        assert isinstance(safety, dict), f"{label}: source_preflight.safety must be a mapping"
        missing_safety = sorted(SOURCE_PREFLIGHT_SAFETY_REQUIRED_KEYS - safety.keys())
        unexpected_safety = sorted(safety.keys() - SOURCE_PREFLIGHT_SAFETY_REQUIRED_KEYS)
        assert not missing_safety, f"{label}: source_preflight.safety missing keys: {missing_safety}"
        assert not unexpected_safety, f"{label}: source_preflight.safety unexpected keys: {unexpected_safety}"
        for key in SOURCE_PREFLIGHT_SAFETY_REQUIRED_KEYS:
            assert type(safety[key]) is bool, f"{label}: source_preflight.safety.{key} must be bool"


@pytest.mark.asyncio
async def test_example_config_matches_source_preflight_print_options_output(monkeypatch, capsys):
    example_cfg = yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    source_preflight = example_cfg["source_preflight"]

    async def fail_if_browser_probe_runs(**kwargs):
        raise AssertionError(f"source preflight browser probe should not run: {kwargs}")

    monkeypatch.setattr("pipeline.cli.run_source_preflight", fail_if_browser_probe_runs)

    argv = [
        "--config",
        str(EXAMPLE_CONFIG),
        "--source",
        "ppomppu",
        "--source-preflight-print-options",
    ]
    args = _mark_source_preflight_cli_overrides(build_parser().parse_args(argv), argv)

    result = await run_source_preflight_command(ConfigManager(args.config), args)

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sources"] == ["ppomppu"]
    assert payload["timeout_ms"] == source_preflight["timeout_ms"]
    assert payload["output_path"] == source_preflight["output_path"]
    assert payload["screenshot_dir"] == source_preflight["screenshot_dir"]
    assert payload["failure_dir"] == source_preflight["failure_dir"]
    assert payload["trace_dir"] == source_preflight["trace_dir"]
    assert payload["click_through"] == source_preflight["click_through_default"]
    assert payload["use_recommended_source"] == source_preflight["use_recommended_source_default"]
    assert payload["origins"] == {
        "timeout_ms": "config",
        "output_path": "config",
        "screenshot_dir": "config",
        "failure_dir": "config",
        "trace_dir": "config",
        "click_through": "config",
        "use_recommended_source": "config",
    }
    assert payload["config_defaults"] == [
        "click_through",
        "failure_dir",
        "output_path",
        "screenshot_dir",
        "timeout_ms",
        "trace_dir",
        "use_recommended_source",
    ]
    assert payload["cli_overrides"] == []
    assert payload["browser_probe_will_run"] is False
    assert payload["read_only"] == source_preflight["safety"]["read_only"]
    assert payload["notion_writes"] == source_preflight["safety"]["notion_writes"]
    assert payload["x_posts"] == source_preflight["safety"]["x_posts"]
    assert payload["auto_apply_allowed"] == source_preflight["safety"]["auto_apply_allowed"]
    assert payload["manual_strategy_review_required"] == source_preflight["safety"]["manual_strategy_review_required"]


def test_example_config_keeps_preflight_and_publish_safety_manual():
    example_cfg = yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8"))

    assert example_cfg["content_strategy"]["require_human_approval"] is True
    assert example_cfg["twitter"]["enabled"] is False
    assert example_cfg["source_preflight"]["safety"] == {
        "read_only": True,
        "notion_writes": False,
        "x_posts": False,
        "auto_apply_allowed": False,
        "manual_strategy_review_required": True,
    }


def test_env_example_keeps_auto_publish_disabled_by_default():
    env_text = ENV_EXAMPLE.read_text(encoding="utf-8")
    env_values = dotenv_values(ENV_EXAMPLE)
    readme = README.read_text(encoding="utf-8")

    assert re.search(r"(?m)^AUTO_PUBLISH=false$", env_text)
    for key, expected_value in ENV_PUBLISH_SAFETY_DEFAULTS.items():
        assert key in env_values, f".env.example missing publish-safety key: {key}"
        assert env_values[key] == expected_value, f".env.example {key} must default to {expected_value!r}"

    unsafe_enabled = {
        key: value
        for key, value in env_values.items()
        if key in ENV_PUBLISH_UNSAFE_TRUE_KEYS and str(value or "").strip().lower() in {"1", "true", "yes", "on"}
    }
    assert not unsafe_enabled, f".env.example must not enable publish/cost side effects by default: {unsafe_enabled}"
    assert "`.env.example` is a safe template" in readme
    assert "publish/API token placeholders" in readme
    assert "Unit tests parse this file with `python-dotenv`" in readme
    assert "real credentials only in your local `.env`" in readme
    assert "`notion_doctor` output includes `publish_safety_check`" in readme
    assert "operator_action_required=false" in readme
    assert "auto_publish_env_enabled=false" in readme
    assert "image_generation_env_enabled=false" in readme
    assert "twitter_config_enabled=false" in readme
    assert "manual_publish_required=true" in readme
    assert "side_effect_env_keys_enabled=(none)" in readme
    assert "empty JSON list" in readme
    assert "credential_values_redacted=true" in readme
    assert "secret values must stay redacted" in readme
    assert "`provider_key_check`" in readme
    assert "`missing_enabled_providers`" in readme
    assert "`env_key_states`" in readme
    assert "must not print API key values" in readme
    assert "`notion_failure_classification.category`" in readme
    assert "`retry_recommended`" in readme
    assert "`wait_seconds`" in readme
    assert "`primary_repair`" in readme
    assert "`rate_limited`" in readme
    assert "`schema_or_payload`" in readme
    assert "Automation should route `notion_operator_action` by category" in readme
    assert "`credential_invalid` means rotate or replace `NOTION_API_KEY`" in readme
    assert "`permission_or_sharing` means share the target database/data source with the integration" in readme
    assert "`object_not_found_or_not_shared` means verify `NOTION_DATABASE_ID` and sharing" in readme
    assert "retry categories mean honor `Retry-After`/backoff before schema changes" in readme
    assert "redacted `notion_doctor --json` failure sample in `docs/ops-runbook.md`" in readme
    assert "`notion_retry_summary.last_status`" in readme
    assert "`notion_failure_classification.primary_repair`" in readme
    assert "not on raw error text" in readme
    assert "Failure `actions` separate setup, permission, and transient repairs" in readme
    assert "Notion integration Bearer token" in readme
    assert "`Notion-Version 2025-09-03`" in readme
    assert "share the resource for 403/404 failures" in readme
    assert "retry/backoff for transient categories before changing schema" in readme


def test_readme_documents_cost_db_fail_open_status_fields():
    readme = README.read_text(encoding="utf-8")

    required_fragments = [
        "`CostTracker.get_cost_persistence_status()`",
        "`status=degraded`",
        "`fail_open=true`",
        "`event_count`",
        "`retained_event_count`",
        "`total_event_count`",
        "`operation_count`",
        "`last_operation`",
        "`last_error_type`",
        "`error_types`",
        "`operations`",
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
        "must not enable automatic publish, source strategy changes, or CostDB repair",
        "in-memory counters",
        "`btx_costs.db`, archive DB, `.tmp/workspace.db`",
    ]
    for fragment in required_fragments:
        assert fragment in readme


def test_readme_documents_source_preflight_problem_action_fields():
    readme = README.read_text(encoding="utf-8")

    required_fragments = [
        "problem_actions[].operator_action_required",
        "problem_actions[].operator_action",
        "mirror the structured",
        "action fields in results[] and failure reports",
        "operator_action_mismatch means the preflight summary and failure report disagree",
        "rerun the evidence doctor/capture before selector or timeout changes",
        "source_preflight_evidence_doctor.py text output prints",
        "operator_action item=N source=SOURCE: required=true action=...",
        "source_preflight_trend_report.py summary.top_operator_actions preserves original operator_action text",
        "source_preflight_trend_report.py summarizes operator_action_mismatch_count and operator_action_mismatch_source_counts",
        "summary.evidence_field_counts",
        "text evidence_fields show which local failure artifacts",
        "failure_report_path",
        "screenshot_path",
        "html_snapshot_path",
        "trace_path",
        "Trace-backed problem actions and failure reports expose trace_viewer_command and trace_viewer_hint",
        "source_preflight_evidence_doctor.py text output prints trace_viewer item=N source=SOURCE: playwright show-trace ...",
        "Its text output prints operator_action_mismatches before weekly aggregation",
        "Its summary preserves trend summary.top_operator_actions for A/B review output",
        "Its summary preserves operator_action_mismatch_count so stale evidence blocks manual strategy review",
        "operator_action_mismatch_count=N",
        "operator_action_mismatch_sources=SOURCE=N",
        "top_operator_action so stdout-only operators can see repair, metric, mismatch, and action coverage",
        "summary.operator_action_mismatch_count",
        "weekly_smoke=ok",
        "Operator action mismatches:",
        "Strategy operator action mismatches:",
        "scripts/write_weekly_smoke_inputs.py --output-dir .tmp",
        (
            "Automation can add `--json` to the writer and read `schema_version`, `safety_contract`, "
            "`commands`, `commands.review_summary`, `commands.verify_manifest`, `expected_report_fragments`, "
            "`expected_review_stdout_fragments`, `expected_strategy_stdout_fragments`, "
            "`expected_repair_queue`, `self_check`, and `paths`"
        ),
        "commands.review_summary",
        "expected_review_stdout_fragments",
        "expected_strategy_stdout_fragments",
        "expected_repair_queue",
        "`self_check=ok`",
        "commands.verify_manifest",
        "--verify-review-summary",
        "--verify-strategy-summary",
        "scripts/verify_weekly_smoke.py",
        "scripts/verify_weekly_smoke.py --manifest .tmp/weekly_smoke_manifest.json --verify-review-summary --verify-strategy-summary --json",
        "and read `ok`, `errors`, `error_categories`, `paths`, `repair_queue`, `repair_queue.primary_repair_target`, `manifest_repair_queue`, and `strategy_summary`",
        "`manifest_repair_queue`",
        "`strategy_summary`",
        "`manifest_schema_version_mismatch`",
        "`manifest_profile_mismatch`",
        "`manifest_safety_mismatch:*`",
        "`manifest_missing_expected_fragment:*`",
        "`manifest_missing_expected_review_stdout_fragment:*`",
        "`manifest_invalid_expected_strategy_stdout_fragment:*`",
        "`missing_strategy_stdout_fragment:*`",
        "`manifest_expected_repair_queue_mismatch:*`",
        "Stale expected repair queue example",
        "`manifest_expected_repair_queue_mismatch:total=expected_7,actual_6`",
        "preserving the actual `repair_queue` object and adding `manifest_repair_queue` mismatch metadata",
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
        '`diagnosis="manifest_contract"`',
        "`manifest_invalid_expected_review_stdout_fragment:*`",
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
        "Text mode keeps review-summary failures compact as `weekly_smoke=fail reason=...`",
        "child stderr/stdout tails stay JSON-only in `review_summary.child_error_tail`",
        "`review_summary_timeout`",
        "`review_summary_run_failed:*`",
        "`review_summary_missing_input:*`",
        "`review_summary_exit_code:*`",
        "`missing_review_summary_stdout_fragment:*`",
        "fix the child process failure first",
        "treat `matched_stdout_fragment_count` as partial evidence only",
        "subprocess failed before summary output",
        "summary started but its stdout contract was incomplete",
        "`review_records`",
        "`executed`",
        "`returncode`",
        "`expected_stdout_fragment_count`",
        "`matched_stdout_fragment_count`",
        "`missing_stdout_fragment_count`",
        "`timeout_seconds`",
        "Review-summary stdout drift example",
        "Review-summary missing input example",
        "Review-summary manifest contract example",
        "Review-summary timeout example",
        "Review-summary run failed example",
        "Review-summary nonzero exit example",
        "Review-summary mixed nonzero/stdout drift example",
        '`diagnosis="stdout_drift"`',
        '`diagnosis="missing_input"`',
        '`diagnosis="timeout"`',
        '`diagnosis="run_failed"`',
        '`diagnosis="nonzero_exit"`',
        "the missing stdout fragment list",
        "the missing local sample path",
        "the child process return code",
        "the bounded child error tail",
        "the child process launch exception",
        "combined nonzero child exit with secondary stdout drift",
        "`manifest_missing_commands`",
        "`manifest_missing_command:*`",
        "`manifest_command_missing_fragment:*`",
        "review_summary",
        "`--manifest-output .tmp/weekly_smoke_manifest.json`",
        "`--self-check`",
        "copy-ready",
        "`manifest_safety_mismatch:notion_writes=expected_false,actual_True`",
        '`error_categories=["manifest"]`',
        "`weekly_smoke=fail category=manifest`",
        (
            "scripts/verify_weekly_smoke.py --report .tmp/weekly_report_smoke.md "
            "--review-experiment .tmp/weekly_report_experiment_smoke.json "
            "--source-preflight-trend .tmp/source_preflight_trend.json "
            "--source-preflight-strategy .tmp/source_preflight_strategy_simulation.json "
            "--recompute-contract .tmp/recompute_scores_runtime_contract_smoke.json --json"
        ),
        "Recompute Scores Runtime Contract (dry-run)",
        "recompute_scores_runtime_contract_smoke.json",
        "--recompute-contract-input",
        "--recompute-contract",
        "review_experiment_dry_run.py --summary-only",
        "missing_metric_rate=N",
        "top_missing_metric=METRIC",
        "top_missing_metric_count=N",
        "top_missing_owner=OWNER",
        "top_missing_owner_count=N",
        "top_missing_owner_metric=METRIC",
        "operator_actions_total=N",
        "safety_risk_items=N",
        "safety_risk_flags=FLAG=N",
        "provider_failure_categories=CATEGORY=N",
        "provider_failure_providers=PROVIDER=N",
        "top_operator_action_reason=...",
        "rollout_blocker_count=N",
        "rollout_blocker_codes=CODE[,CODE]",
        "top_rollout_blocker_action=...",
        "Review top operator actions:",
        "Missing metric owners:",
        "missing_metric_rate_high",
        "cost_tracking: Include token_cost_estimate from the generation cost tracker.",
        "summary.candidate_rollout_blocker_actions[]",
        "Rollout blocker actions:",
        "Safety risk flags:",
        "Provider failures:",
        "Source trend operator actions:",
    ]
    for fragment in required_fragments:
        assert fragment in readme


def test_workflow_runs_tests_before_pipeline():
    """데이터 정확도 테스트가 파이프라인 스텝보다 먼저 실행돼야 합니다."""
    workflow_cfg = yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))
    steps = workflow_cfg["jobs"]["run-pipeline"]["steps"]
    names = [step.get("name", "") for step in steps]

    test_idx = names.index("Run data accuracy tests")
    # "Run pipeline"으로 시작하는 첫 번째 파이프라인 스텝의 인덱스
    pipeline_idx = next(i for i, name in enumerate(names) if name.startswith("Run pipeline"))
    assert test_idx < pipeline_idx, "Run data accuracy tests must be before Run pipeline"


def test_workflow_pipeline_uses_valid_feed_mode():
    """각 파이프라인 스텝이 --trending 또는 --popular 중 하나를 반드시 사용해야 합니다."""
    workflow_cfg = yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))
    steps = workflow_cfg["jobs"]["run-pipeline"]["steps"]
    pipeline_steps = [s for s in steps if s.get("name", "").startswith("Run pipeline")]
    assert pipeline_steps, "파이프라인 실행 스텝이 없습니다."
    for step in pipeline_steps:
        run_cmd = step.get("run", "")
        assert "--trending" in run_cmd or "--popular" in run_cmd, (
            f"스텝 '{step.get('name')}': --trending 또는 --popular 중 하나가 필요합니다."
        )
