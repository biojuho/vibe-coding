from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_weekly_report import run  # noqa: E402
from scripts.review_experiment_dry_run import main as review_experiment_main  # noqa: E402
from scripts.source_preflight_evidence_doctor import main as evidence_doctor_main  # noqa: E402
from scripts.verify_weekly_smoke import (  # noqa: E402
    REVIEW_SUMMARY_TIMEOUT_SECONDS,
    verify_weekly_smoke,
)
from scripts.verify_weekly_smoke import (
    main as verify_main,
)
from scripts.write_weekly_smoke_inputs import (  # noqa: E402
    DEFAULT_REVIEW_RECORD_SAMPLE_NAME,
    DEFAULT_WEEKLY_REPORT_PAYLOAD_NAME,
    EXPECTED_REPORT_FRAGMENTS,
    EXPECTED_REVIEW_STDOUT_FRAGMENTS,
    EXPECTED_STRATEGY_STDOUT_FRAGMENTS,
    MANIFEST_SCHEMA_VERSION,
    SAFETY_CONTRACT,
    SMOKE_PROFILE,
    build_result_payload,
    build_self_check_payload,
    main,
    source_preflight_repair_input_paths,
    write_weekly_smoke_inputs,
)
from scripts.write_weekly_smoke_inputs import (
    _format_command as _format_weekly_command,
)


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _cmd(*parts: str | Path) -> str:
    return _format_weekly_command(list(parts))


def _write_and_build_manifest_smoke(tmp_path: Path, monkeypatch, capsys) -> tuple[Path, dict, dict[str, Path]]:
    monkeypatch.setattr("scripts.build_weekly_report._render_best_of_n_section", lambda days: "")
    manifest_path = tmp_path / "weekly_smoke_manifest.json"

    writer_exit_code = main(
        [
            "--output-dir",
            str(tmp_path),
            "--manifest-output",
            str(manifest_path),
            "--json",
        ]
    )

    writer_payload = json.loads(capsys.readouterr().out)
    assert writer_exit_code == 0
    assert writer_payload["manifest"] == manifest_path.as_posix()
    manifest = _read_json(manifest_path)
    paths = {name: Path(value) for name, value in manifest["paths"].items()}
    report_path = Path(manifest["expected_outputs"]["report"])

    build_exit_code = asyncio.run(
        run(
            days=7,
            config_path="config.example.yaml",
            output_path=str(report_path),
            payload_input=str(paths["weekly_report_payload"]),
            review_experiment_input=str(paths["review_experiment"]),
            source_preflight_trend_input=str(paths["source_preflight_trend"]),
            source_preflight_strategy_input=str(paths["source_preflight_strategy"]),
            recompute_contract_input=str(paths["recompute_contract"]),
        )
    )
    assert build_exit_code == 0
    capsys.readouterr()
    return manifest_path, manifest, paths


def test_write_weekly_smoke_inputs_uses_stable_default_filenames(tmp_path):
    paths = write_weekly_smoke_inputs(tmp_path)

    assert paths == {
        "weekly_report_payload": tmp_path / DEFAULT_WEEKLY_REPORT_PAYLOAD_NAME,
        "review_records": tmp_path / DEFAULT_REVIEW_RECORD_SAMPLE_NAME,
        "review_experiment": tmp_path / "weekly_report_experiment_smoke.json",
        "source_preflight_trend": tmp_path / "source_preflight_trend.json",
        "source_preflight_strategy": tmp_path / "source_preflight_strategy_simulation.json",
        "recompute_contract": tmp_path / "recompute_scores_runtime_contract_smoke.json",
    }
    for path in paths.values():
        assert path.exists()
        assert path.parent == tmp_path
        assert _read_json(path)

    assert _read_json(paths["review_experiment"])["safety"]["notion_writes"] is False
    assert _read_json(paths["review_records"])["operator_actions"][0]["page_id"] == "page-blocked"
    assert _read_json(paths["review_records"])["ready_attention_items"][0]["page_id"] == "page-ready"
    assert _read_json(paths["review_experiment"])["summary"]["candidate_safety_risk_item_count"] == 2
    assert _read_json(paths["review_experiment"])["summary"]["candidate_safety_risk_flag_counts"] == {
        "privacy": 2,
        "legal": 1,
    }
    assert _read_json(paths["review_experiment"])["summary"]["candidate_provider_failure_category_counts"] == {
        "auth": 1,
        "rate_limit": 1,
    }
    assert _read_json(paths["review_experiment"])["summary"]["candidate_provider_failure_provider_counts"] == {
        "gemini": 1,
        "openai": 1,
    }
    assert _read_json(paths["review_experiment"])["summary"]["candidate_primary_provider_failure_category_counts"] == {
        "auth": 1,
    }
    assert _read_json(paths["review_experiment"])["summary"]["candidate_primary_provider_failure_provider_counts"] == {
        "openai": 1,
    }
    assert _read_json(paths["review_experiment"])["summary"]["candidate_primary_provider_failure_actions"] == [
        {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "category": "auth",
            "operator_action": "Check provider API key",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "count": 1,
        }
    ]
    assert _read_json(paths["review_experiment"])["summary"]["candidate_missing_metric_owner_counts"] == {
        "cost_tracking": 2,
        "provider_telemetry": 1,
    }
    assert (
        _read_json(paths["review_experiment"])["summary"]["candidate_top_missing_metric_owners"][0]["owner"]
        == "cost_tracking"
    )
    assert _read_json(paths["review_experiment"])["summary"]["candidate_rollout_blocker_actions"][0] == {
        "code": "missing_metric_rate_high",
        "source": "confidence",
        "operator_action": "cost_tracking: Include token_cost_estimate from the generation cost tracker.",
        "owner": "cost_tracking",
        "owner_count": 2,
        "top_metric": "token_cost_estimate",
        "top_metric_count": 2,
        "owner_operator_action": "Include token_cost_estimate from the generation cost tracker.",
    }
    assert _read_json(paths["source_preflight_trend"])["safety"]["browser_launches"] is False
    assert _read_json(paths["source_preflight_trend"])["summary"]["operator_action_mismatch_count"] == 1
    assert _read_json(paths["source_preflight_trend"])["summary"]["operator_action_mismatch_source_counts"] == {
        "ppomppu": 1
    }
    assert _read_json(paths["source_preflight_trend"])["summary"]["evidence_field_counts"] == {
        "failure_report_path": 3,
        "html_snapshot_path": 3,
        "screenshot_path": 3,
        "trace_path": 1,
        "error": 1,
    }
    source_strategy = _read_json(paths["source_preflight_strategy"])
    assert source_strategy["safety"]["x_posts"] is False
    assert source_strategy["summary"]["operator_action_mismatch_count"] == 1
    assert source_strategy["summary"]["operator_action_mismatch_source_counts"] == {"ppomppu": 1}
    assert len(source_strategy["summary"]["top_repair_commands"]) == 4
    assert len(source_strategy["summary"]["repair_command_queue"]) == 6
    assert source_strategy["summary"]["repair_command_queue"][0]["command"] == _cmd(
        "py",
        "-3",
        "scripts/source_preflight_evidence_doctor.py",
        "--input",
        tmp_path / "source_browser_preflight-blind.json",
        "--fail-on-warning",
    )
    assert source_strategy["summary"]["repair_command_queue"][0]["buckets"] == {"blind|blocked": 1}
    assert source_strategy["summary"]["repair_command_queue_consistency"] == {
        "status": "ok",
        "repair_command_count": 6,
        "queue_count_total": 6,
        "queue_item_count": 6,
        "top_item_count": 4,
    }
    assert source_strategy["manual_ready_gate"]["repair_command_count"] == 6
    assert len(source_strategy["manual_ready_gate"]["repair_commands"]) == 6
    assert _read_json(paths["recompute_contract"])["ok"] is True
    assert _read_json(paths["recompute_contract"])["gate_errors"] == []
    assert _read_json(paths["recompute_contract"])["runtime_contract"]["validation"]["scoring_runs"] is False
    assert all(path.exists() for path in source_preflight_repair_input_paths(tmp_path).values())


def test_write_weekly_smoke_inputs_json_cli_reports_written_paths(tmp_path, capsys):
    exit_code = main(["--output-dir", str(tmp_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    paths = {name: Path(value) for name, value in payload["paths"].items()}
    assert exit_code == 0
    assert payload == build_result_payload(paths)
    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert payload["profile"] == SMOKE_PROFILE
    assert payload["safety_contract"] == SAFETY_CONTRACT
    assert payload["expected_report_fragments"] == EXPECTED_REPORT_FRAGMENTS
    assert "Repair queue:" in payload["expected_report_fragments"]
    assert "Primary repair target:" in payload["expected_report_fragments"]
    assert payload["expected_review_stdout_fragments"] == EXPECTED_REVIEW_STDOUT_FRAGMENTS
    assert "primary_provider_failure_categories=auth=1" in payload["expected_review_stdout_fragments"]
    assert "primary_provider_failure_providers=openai=1" in payload["expected_review_stdout_fragments"]
    assert payload["expected_strategy_stdout_fragments"] == EXPECTED_STRATEGY_STDOUT_FRAGMENTS
    assert "primary_repair_buckets=blind|blocked=1" in payload["expected_strategy_stdout_fragments"]
    assert "operator_action_mismatch_sources=ppomppu=1" in payload["expected_strategy_stdout_fragments"]
    assert payload["expected_repair_queue"] == build_result_payload(paths)["expected_repair_queue"]
    assert payload["expected_repair_queue"]["primary_repair_target"]["command"] == _cmd(
        "py",
        "-3",
        "scripts/source_preflight_evidence_doctor.py",
        "--input",
        tmp_path / "source_browser_preflight-blind.json",
        "--fail-on-warning",
    )
    assert payload["expected_outputs"]["report"] == (tmp_path / "weekly_report_smoke.md").as_posix()
    assert paths["weekly_report_payload"].name == DEFAULT_WEEKLY_REPORT_PAYLOAD_NAME
    assert all(path.exists() for path in paths.values())


def test_write_weekly_smoke_inputs_manifest_output_writes_copy_ready_manifest(tmp_path, capsys):
    manifest_path = tmp_path / "weekly_smoke_manifest.json"

    exit_code = main(["--output-dir", str(tmp_path), "--manifest-output", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    manifest = _read_json(manifest_path)
    assert exit_code == 0
    assert payload == manifest
    assert payload["manifest"] == manifest_path.as_posix()
    assert (
        payload["expected_repair_queue"]
        == build_result_payload(
            {name: Path(value) for name, value in payload["paths"].items()},
            manifest_output=manifest_path,
        )["expected_repair_queue"]
    )
    assert payload["expected_strategy_stdout_fragments"] == EXPECTED_STRATEGY_STDOUT_FRAGMENTS
    assert payload["commands"]["write_inputs"] == _cmd(
        "py",
        "-3",
        "scripts/write_weekly_smoke_inputs.py",
        "--output-dir",
        tmp_path,
        "--manifest-output",
        manifest_path,
    )
    assert payload["commands"]["review_summary"] == _cmd(
        "py",
        "-3",
        "scripts/review_experiment_dry_run.py",
        "--input-mode",
        "review-records",
        "--input",
        tmp_path / DEFAULT_REVIEW_RECORD_SAMPLE_NAME,
        "--min-items",
        "1",
        "--max-missing-rate",
        "0.25",
        "--summary-only",
    )
    assert payload["commands"]["verify_manifest"] == _cmd(
        "py",
        "-3",
        "scripts/verify_weekly_smoke.py",
        "--manifest",
        manifest_path,
        "--verify-review-summary",
        "--verify-strategy-summary",
    )


def test_write_weekly_smoke_inputs_writes_repair_inputs_that_doctor_accepts(tmp_path, capsys):
    paths = write_weekly_smoke_inputs(tmp_path)
    source_strategy = _read_json(paths["source_preflight_strategy"])

    doctor_inputs = [
        source_preflight_repair_input_paths(tmp_path)["blind"],
        source_preflight_repair_input_paths(tmp_path)["ppomppu"],
        source_preflight_repair_input_paths(tmp_path)["dcinside"],
    ]
    assert source_strategy["manual_ready_gate"]["repair_commands"][:3] == [
        _cmd(
            "py",
            "-3",
            "scripts/source_preflight_evidence_doctor.py",
            "--input",
            doctor_input,
            "--fail-on-warning",
        )
        for doctor_input in doctor_inputs
    ]

    for doctor_input in doctor_inputs:
        exit_code = evidence_doctor_main(["--input", str(doctor_input), "--fail-on-warning", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert exit_code == 0
        assert payload["status"] == "PASS"
        assert payload["summary"]["error_count"] == 0
        assert payload["summary"]["warning_count"] == 0


def test_write_weekly_smoke_inputs_self_check_json_reports_ok(tmp_path, capsys):
    manifest_path = tmp_path / "weekly_smoke_manifest.json"

    exit_code = main(
        [
            "--output-dir",
            str(tmp_path),
            "--manifest-output",
            str(manifest_path),
            "--self-check",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["self_check"] == {"errors": [], "ok": True, "status": "ok"}
    manifest = _read_json(manifest_path)
    assert manifest["manifest"] == manifest_path.as_posix()
    assert manifest["self_check"] == payload["self_check"]
    assert (
        payload["commands"]["write_inputs"]
        == manifest["commands"]["write_inputs"]
        == _cmd(
            "py",
            "-3",
            "scripts/write_weekly_smoke_inputs.py",
            "--output-dir",
            tmp_path,
            "--manifest-output",
            manifest_path,
            "--self-check",
        )
    )


def test_write_weekly_smoke_inputs_self_check_text_reports_ok(tmp_path, capsys):
    manifest_path = tmp_path / "weekly_smoke_manifest.json"

    exit_code = main(["--output-dir", str(tmp_path), "--manifest-output", str(manifest_path), "--self-check"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert "weekly_smoke_inputs=written" in output
    assert "self_check=ok" in output
    assert f"manifest={manifest_path.as_posix()}" in output
    assert _read_json(manifest_path)["self_check"] == {"errors": [], "ok": True, "status": "ok"}


def test_write_weekly_smoke_inputs_self_check_reports_contract_failures(tmp_path):
    paths = write_weekly_smoke_inputs(tmp_path)
    payload = build_result_payload(paths)
    payload["schema_version"] = 0

    self_check = build_self_check_payload(paths=paths, manifest_payload=payload)

    assert self_check["ok"] is False
    assert self_check["status"] == "fail"
    assert self_check["errors"] == ["manifest_schema_version_mismatch:expected=1,actual=0"]


def test_write_weekly_smoke_inputs_json_manifest_includes_copy_ready_commands(tmp_path, capsys):
    exit_code = main(["--output-dir", str(tmp_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    commands = payload["commands"]
    assert exit_code == 0
    assert commands["write_inputs"] == _cmd(
        "py",
        "-3",
        "scripts/write_weekly_smoke_inputs.py",
        "--output-dir",
        tmp_path,
    )
    assert commands["review_summary"] == _cmd(
        "py",
        "-3",
        "scripts/review_experiment_dry_run.py",
        "--input-mode",
        "review-records",
        "--input",
        tmp_path / "review_queue_report_sample.json",
        "--min-items",
        "1",
        "--max-missing-rate",
        "0.25",
        "--summary-only",
    )
    assert commands["build_report"] == _cmd(
        "py",
        "-3",
        "scripts/build_weekly_report.py",
        "--payload-input",
        tmp_path / "weekly_report_payload_smoke.json",
        "--review-experiment-input",
        tmp_path / "weekly_report_experiment_smoke.json",
        "--source-preflight-trend-input",
        tmp_path / "source_preflight_trend.json",
        "--source-preflight-strategy-input",
        tmp_path / "source_preflight_strategy_simulation.json",
        "--recompute-contract-input",
        tmp_path / "recompute_scores_runtime_contract_smoke.json",
        "--output",
        tmp_path / "weekly_report_smoke.md",
    )
    assert commands["verify_text"] == _cmd(
        "py",
        "-3",
        "scripts/verify_weekly_smoke.py",
        "--report",
        tmp_path / "weekly_report_smoke.md",
        "--review-experiment",
        tmp_path / "weekly_report_experiment_smoke.json",
        "--source-preflight-trend",
        tmp_path / "source_preflight_trend.json",
        "--source-preflight-strategy",
        tmp_path / "source_preflight_strategy_simulation.json",
        "--recompute-contract",
        tmp_path / "recompute_scores_runtime_contract_smoke.json",
    )
    assert commands["verify_json"] == f"{commands['verify_text']} --json"


def test_write_weekly_smoke_inputs_quotes_copy_ready_commands_for_space_paths(tmp_path):
    output_dir = tmp_path / "weekly smoke"
    manifest_path = output_dir / "weekly smoke manifest.json"

    paths = write_weekly_smoke_inputs(output_dir)
    payload = build_result_payload(paths, manifest_output=manifest_path, self_check=True)
    commands = payload["commands"]
    source_strategy = _read_json(paths["source_preflight_strategy"])
    doctor_input = output_dir / "source_browser_preflight-blind.json"

    assert f"--output-dir '{output_dir.as_posix()}'" in commands["write_inputs"]
    assert f"--manifest-output '{manifest_path.as_posix()}'" in commands["write_inputs"]
    assert f"--input '{(output_dir / DEFAULT_REVIEW_RECORD_SAMPLE_NAME).as_posix()}'" in commands["review_summary"]
    assert f"--payload-input '{paths['weekly_report_payload'].as_posix()}'" in commands["build_report"]
    assert f"--report '{(output_dir / 'weekly_report_smoke.md').as_posix()}'" in commands["verify_text"]
    assert commands["verify_json"].endswith(" --json")
    assert f"--manifest '{manifest_path.as_posix()}'" in commands["verify_manifest"]
    expected_doctor_command = _cmd(
        "py",
        "-3",
        "scripts/source_preflight_evidence_doctor.py",
        "--input",
        doctor_input,
        "--fail-on-warning",
    )
    assert payload["expected_repair_queue"]["primary_repair_target"]["command"] == expected_doctor_command
    assert source_strategy["manual_ready_gate"]["primary_repair_command"] == expected_doctor_command


def test_write_weekly_smoke_inputs_quotes_copy_ready_commands_for_powershell_metacharacter_paths(tmp_path):
    output_dir = tmp_path / "weekly&smoke"
    manifest_path = output_dir / "weekly&smoke-manifest.json"

    paths = write_weekly_smoke_inputs(output_dir)
    payload = build_result_payload(paths, manifest_output=manifest_path, self_check=True)
    commands = payload["commands"]
    source_strategy = _read_json(paths["source_preflight_strategy"])
    doctor_input = output_dir / "source_browser_preflight-blind.json"

    assert f"--output-dir '{output_dir.as_posix()}'" in commands["write_inputs"]
    assert f"--manifest-output '{manifest_path.as_posix()}'" in commands["write_inputs"]
    assert f"--input '{(output_dir / DEFAULT_REVIEW_RECORD_SAMPLE_NAME).as_posix()}'" in commands["review_summary"]
    assert f"--payload-input '{paths['weekly_report_payload'].as_posix()}'" in commands["build_report"]
    assert f"--report '{(output_dir / 'weekly_report_smoke.md').as_posix()}'" in commands["verify_text"]
    assert f"--manifest '{manifest_path.as_posix()}'" in commands["verify_manifest"]
    expected_doctor_command = _cmd(
        "py",
        "-3",
        "scripts/source_preflight_evidence_doctor.py",
        "--input",
        doctor_input,
        "--fail-on-warning",
    )
    assert payload["expected_repair_queue"]["primary_repair_target"]["command"] == expected_doctor_command
    assert source_strategy["manual_ready_gate"]["primary_repair_command"] == expected_doctor_command


def test_written_weekly_smoke_inputs_feed_review_summary_stdout_contract(tmp_path, capsys):
    paths = write_weekly_smoke_inputs(tmp_path)

    exit_code = review_experiment_main(
        [
            "--input-mode",
            "review-records",
            "--input",
            str(paths["review_records"]),
            "--min-items",
            "1",
            "--max-missing-rate",
            "0.25",
            "--summary-only",
        ]
    )

    stdout = capsys.readouterr().out
    assert exit_code == 0
    for fragment in EXPECTED_REVIEW_STDOUT_FRAGMENTS:
        assert fragment in stdout


def test_written_weekly_smoke_manifest_verifier_reports_review_summary_metadata(tmp_path, monkeypatch, capsys):
    manifest_path, _manifest, paths = _write_and_build_manifest_smoke(tmp_path, monkeypatch, capsys)

    verify_exit_code = verify_main(["--manifest", str(manifest_path), "--verify-review-summary", "--json"])

    verifier_payload = json.loads(capsys.readouterr().out)
    assert verify_exit_code == 0
    assert verifier_payload["ok"] is True
    assert verifier_payload["errors"] == []
    assert verifier_payload["review_summary"] == {
        "ok": True,
        "status": "ok",
        "diagnosis": "ok",
        "failure_reasons": [],
        "executed": True,
        "review_records": paths["review_records"].as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": len(EXPECTED_REVIEW_STDOUT_FRAGMENTS),
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "timeout": False,
        "nonzero_exit": False,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": 0,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }
    assert verifier_payload["strategy_summary"] == {
        "ok": True,
        "status": "ok",
        "diagnosis": "ok",
        "failure_reasons": [],
        "executed": True,
        "source_preflight_strategy": paths["source_preflight_strategy"].as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_STRATEGY_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": len(EXPECTED_STRATEGY_STDOUT_FRAGMENTS),
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "format_failed": False,
        "manifest_contract_error": False,
    }


def test_written_weekly_smoke_manifest_verifier_reports_stale_review_summary_fragment(tmp_path, monkeypatch, capsys):
    manifest_path, manifest, paths = _write_and_build_manifest_smoke(tmp_path, monkeypatch, capsys)

    manifest["expected_review_stdout_fragments"] = [
        *manifest["expected_review_stdout_fragments"],
        "not-present-in-review-summary",
    ]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    verify_exit_code = verify_main(["--manifest", str(manifest_path), "--verify-review-summary", "--json"])

    verifier_payload = json.loads(capsys.readouterr().out)
    assert verify_exit_code == 1
    assert verifier_payload["ok"] is False
    assert verifier_payload["error_categories"] == ["review_summary"]
    assert verifier_payload["errors"] == ["missing_review_summary_stdout_fragment:not-present-in-review-summary"]
    assert verifier_payload["review_summary"] == {
        "ok": False,
        "status": "fail",
        "diagnosis": "stdout_drift",
        "failure_reasons": ["stdout_drift"],
        "executed": True,
        "review_records": paths["review_records"].as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_REVIEW_STDOUT_FRAGMENTS) + 1,
        "matched_stdout_fragment_count": len(EXPECTED_REVIEW_STDOUT_FRAGMENTS),
        "missing_stdout_fragment_count": 1,
        "missing_stdout_fragments": ["not-present-in-review-summary"],
        "missing_input": False,
        "stdout_drift": True,
        "timeout": False,
        "nonzero_exit": False,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": 0,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }
    assert verifier_payload["strategy_summary"]["ok"] is True
    assert verifier_payload["strategy_summary"]["missing_stdout_fragments"] == []


def test_written_weekly_smoke_manifest_verifier_reports_stale_strategy_summary_fragment(tmp_path, monkeypatch, capsys):
    manifest_path, manifest, paths = _write_and_build_manifest_smoke(tmp_path, monkeypatch, capsys)

    manifest["expected_strategy_stdout_fragments"] = [
        *manifest["expected_strategy_stdout_fragments"],
        "not-present-in-strategy-summary",
    ]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    verify_exit_code = verify_main(["--manifest", str(manifest_path), "--verify-review-summary", "--json"])

    verifier_payload = json.loads(capsys.readouterr().out)
    assert verify_exit_code == 1
    assert verifier_payload["ok"] is False
    assert verifier_payload["error_categories"] == ["strategy_summary"]
    assert verifier_payload["errors"] == ["missing_strategy_stdout_fragment:not-present-in-strategy-summary"]
    assert verifier_payload["strategy_summary"] == {
        "ok": False,
        "status": "fail",
        "diagnosis": "stdout_drift",
        "failure_reasons": ["stdout_drift"],
        "executed": True,
        "source_preflight_strategy": paths["source_preflight_strategy"].as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_STRATEGY_STDOUT_FRAGMENTS) + 1,
        "matched_stdout_fragment_count": len(EXPECTED_STRATEGY_STDOUT_FRAGMENTS),
        "missing_stdout_fragment_count": 1,
        "missing_stdout_fragments": ["not-present-in-strategy-summary"],
        "missing_input": False,
        "stdout_drift": True,
        "format_failed": False,
        "manifest_contract_error": False,
    }
    assert verifier_payload["review_summary"]["ok"] is True


def test_written_weekly_smoke_inputs_feed_report_builder_and_verifier(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.build_weekly_report._render_best_of_n_section", lambda days: "")
    paths = write_weekly_smoke_inputs(tmp_path)
    report_path = tmp_path / "weekly_report_smoke.md"

    exit_code = asyncio.run(
        run(
            days=7,
            config_path="config.example.yaml",
            output_path=str(report_path),
            payload_input=str(paths["weekly_report_payload"]),
            review_experiment_input=str(paths["review_experiment"]),
            source_preflight_trend_input=str(paths["source_preflight_trend"]),
            source_preflight_strategy_input=str(paths["source_preflight_strategy"]),
            recompute_contract_input=str(paths["recompute_contract"]),
        )
    )

    assert exit_code == 0
    assert (
        verify_weekly_smoke(
            report_path=report_path,
            review_experiment_path=paths["review_experiment"],
            source_preflight_trend_path=paths["source_preflight_trend"],
            source_preflight_strategy_path=paths["source_preflight_strategy"],
            recompute_contract_path=paths["recompute_contract"],
        )
        == []
    )
    report = report_path.read_text(encoding="utf-8")
    assert "Review top operator actions:" in report
    assert "Missing metric owners: 2x cost_tracking top_metric=token_cost_estimate" in report
    assert "Rollout blocker actions: missing_metric_rate_high source=confidence owner=cost_tracking" in report
    assert "Next manual action: cost_tracking: Include token_cost_estimate from the generation cost tracker." in report
    assert "Safety risk flags: items=2; flags=privacy=2, legal=1" in report
    assert (
        "Provider failures: categories=auth=1, rate_limit=1; providers=gemini=1, openai=1; "
        "primary_categories=auth=1; primary_providers=openai=1" in report
    )
    assert "Source trend operator actions:" in report
    assert "Evidence fields: failure_report_path=3, html_snapshot_path=3, screenshot_path=3" in report
    assert (
        "Top source evidence: source=ppomppu; status=timeout; count=2; "
        "open_first=failure_report_path=.tmp/failures/source_preflight/ppomppu-timeout.json" in report
    )
    assert "trace_path=1" in report
    assert "Operator action mismatches: count=1; sources=ppomppu=1" in report
    assert "Strategy operator action mismatches: count=1; sources=ppomppu=1" in report
    assert "Source operator actions:" in report
    assert "Repair commands: count=6; primary_shown=true; remaining=5" in report
    assert (
        "Repair queue: total=6; listed=6; count_total=6; consistency=ok; full_queue_available=true; "
        "source=manual_ready_gate.repair_commands"
    ) in report
    assert "Primary repair target: type=evidence_doctor; count=1; buckets=blind|blocked=1; sources=blind=1" in report
    assert "metric_missing=current:2/10,candidate:2/10" in report
    assert "Recompute Scores Runtime Contract (dry-run)" in report
    assert "Gate: status=ok; ok=true; validation_ok=true; gate_errors=0" in report
    assert "validation_scoring_runs=false" in report
    assert "Recompute command:" in report
