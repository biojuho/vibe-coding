from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.source_preflight_strategy_simulation import (  # noqa: E402
    _input_paths,
    _manual_ready_gate_result,
    build_strategy_simulation,
    main,
    parse_args,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _preflight_report(*, source: str, status: str, operator_action: str = "Inspect evidence.") -> dict:
    return {
        "summary": {
            "problem_count": 1,
            "problem_actions": [
                {
                    "source": source,
                    "status": status,
                    "action": operator_action,
                    "operator_action_required": True,
                    "operator_action": operator_action,
                    "evidence": {
                        "failure_report_path": f".tmp/failures/source_preflight/{source}-{status}.json",
                        "screenshot_path": f"screenshots/source_preflight/{source}.png",
                        "html_snapshot_path": f".tmp/failures/source_preflight/{source}.html",
                    },
                }
            ],
        }
    }


def test_manual_ready_gate_treats_string_false_as_blocked():
    payload = {
        "rollout_gate": {
            "ready_for_manual_strategy_review": "false",
            "status": "blocked",
            "operator_action": "Run the repair command first.",
        }
    }

    result = _manual_ready_gate_result(payload, required=True)

    assert result["passed"] is False
    assert result["status"] == "blocked"
    assert result["exit_code"] == 2
    assert result["reason"] == "Run the repair command first."


def _failure_report(*, source: str, status: str, operator_action: str = "Inspect evidence.") -> dict:
    return {
        "source": source,
        "classification": {"status": status},
        "failure_report": {
            "schema_version": 1,
            "tool": "source_browser_probe",
            "captured_at": "2026-06-10T00:00:00+00:00",
        },
        "operator": {
            "action_required": True,
            "action": operator_action,
            "evidence": {
                "failure_report_path": f".tmp/failures/source_preflight/{source}-{status}.json",
                "screenshot_path": f"screenshots/source_preflight/{source}.png",
                "html_snapshot_path": f".tmp/failures/source_preflight/{source}.html",
            },
        },
    }


def _write_complete_evidence(tmp_path: Path, *, source: str, status: str, report_name: str) -> Path:
    input_path = tmp_path / report_name
    _write_json(input_path, _preflight_report(source=source, status=status))
    _write_json(
        tmp_path / f".tmp/failures/source_preflight/{source}-{status}.json",
        _failure_report(source=source, status=status),
    )
    html = tmp_path / f".tmp/failures/source_preflight/{source}.html"
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text("<html>evidence</html>", encoding="utf-8")
    screenshot = tmp_path / f"screenshots/source_preflight/{source}.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")
    return input_path


def _write_operator_action_mismatch_evidence(tmp_path: Path) -> Path:
    source = "ppomppu"
    status = "timeout"
    report_name = "source_browser_preflight-mismatch.json"
    input_path = tmp_path / report_name
    _write_json(
        input_path,
        _preflight_report(
            source=source,
            status=status,
            operator_action="Inspect preflight summary evidence.",
        ),
    )
    _write_json(
        tmp_path / f".tmp/failures/source_preflight/{source}-{status}.json",
        _failure_report(
            source=source,
            status=status,
            operator_action="Inspect stale failure report evidence.",
        ),
    )
    html = tmp_path / f".tmp/failures/source_preflight/{source}.html"
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text("<html>evidence</html>", encoding="utf-8")
    screenshot = tmp_path / f"screenshots/source_preflight/{source}.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")
    return input_path


def test_build_strategy_simulation_adopts_gate_directed_candidate_for_mixed_failures(tmp_path):
    timeout_report = _write_complete_evidence(
        tmp_path,
        source="ppomppu",
        status="timeout",
        report_name="source_browser_preflight-timeout.json",
    )
    blocked_report = _write_complete_evidence(
        tmp_path,
        source="blind",
        status="blocked",
        report_name="source_browser_preflight-blocked.json",
    )

    payload = build_strategy_simulation([timeout_report, blocked_report], base_dir=tmp_path)

    assert payload["dry_run"] is True
    assert payload["safety"] == {
        "read_only": True,
        "browser_launches": False,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }
    assert payload["objective_metrics"] == [
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
    ]
    assert payload["summary"]["evidence_gate_status_counts"] == {
        "strategy_review_ready": 1,
        "fallback_only": 1,
    }
    assert payload["summary"]["evidence_field_counts"] == {
        "failure_report_path": 2,
        "html_snapshot_path": 2,
        "screenshot_path": 2,
    }
    assert payload["summary"]["repair_command_count"] == 0
    assert payload["summary"]["repair_command_type_counts"] == {}
    assert payload["summary"]["top_repair_commands"] == []
    assert payload["summary"]["operator_action_counts"] == {"Inspect evidence.": 2}
    assert payload["summary"]["top_operator_actions"] == [
        {
            "operator_action": "Inspect evidence.",
            "count": 2,
            "sources": {"ppomppu": 1, "blind": 1},
        }
    ]
    assert payload["summary"]["metric_total"] == 10
    assert payload["summary"]["metric_missing"] == "current:2/10,candidate:2/10"
    assert payload["summary"]["missing_metric_counts"] == {"current": 2, "candidate": 2}
    assert payload["summary"]["missing_metric_names"] == {
        "current": ["latency_ms", "draft_quality_score"],
        "candidate": ["latency_ms", "draft_quality_score"],
    }
    assert payload["summary"]["measurement_scope"] == {
        "mode": "local_preflight_evidence",
        "external_llm_calls": False,
        "costed_generation": False,
        "not_measured_metrics": ["latency_ms", "draft_quality_score"],
        "deterministic_defaults": {
            "token_cost_estimate": 0.0,
            "duplicate_or_near_duplicate": False,
        },
    }
    assert payload["variants"]["current"]["signals"]["unsafe_strategy_change_count"] == 1
    assert payload["variants"]["current"]["signals"]["strategy_review_count"] == 1
    assert payload["variants"]["current"]["signals"]["repair_command_count"] == 0
    assert payload["variants"]["candidate"]["signals"]["unsafe_strategy_change_count"] == 0
    assert payload["variants"]["candidate"]["signals"]["strategy_review_count"] == 1
    assert payload["variants"]["candidate"]["signals"]["repair_command_count"] == 0
    assert payload["variants"]["candidate"]["signals"]["recommendation_action"] == "split_fallback_and_strategy_review"
    assert payload["comparison"]["recommendation"] == "adopt_candidate"
    assert payload["comparison"]["unsafe_strategy_change_delta"] == -1
    assert payload["comparison"]["strategy_review_delta"] == 0
    assert payload["rollout_gate"] == {
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
    }


def test_build_strategy_simulation_keeps_candidate_in_repair_mode_when_evidence_missing(tmp_path):
    input_path = tmp_path / "source_browser_preflight-warning.json"
    _write_json(
        input_path,
        {
            "summary": {
                "problem_count": 1,
                "problem_actions": [{"source": "blind", "status": "blocked", "evidence": {"error": "blocked"}}],
            }
        },
    )

    payload = build_strategy_simulation([input_path], base_dir=tmp_path)

    assert payload["trend_status"] == "WARN"
    assert payload["variants"]["candidate"]["signals"]["recommendation_action"] == "repair_evidence"
    assert payload["variants"]["candidate"]["signals"]["success"] is False
    assert payload["variants"]["candidate"]["signals"]["safety_risk_flags"] == [
        "evidence_repair_required",
        "incomplete_evidence",
        "repair_command_debt",
    ]
    assert payload["comparison"]["recommendation"] == "repair_evidence_first"
    assert payload["summary"]["repair_command_count"] == 2
    assert payload["summary"]["repair_command_queue_consistency"] == {
        "status": "ok",
        "repair_command_count": 2,
        "queue_count_total": 2,
        "queue_item_count": 2,
        "top_item_count": 2,
    }
    assert payload["summary"]["repair_command_type_counts"] == {
        "evidence_doctor": 1,
        "source_preflight_capture": 1,
    }
    assert {item["type"] for item in payload["summary"]["top_repair_commands"]} == {
        "evidence_doctor",
        "source_preflight_capture",
    }
    assert {tuple(item["buckets"].items()) for item in payload["summary"]["top_repair_commands"]} == {
        (("blind|blocked", 1),),
    }
    assert payload["rollout_gate"]["status"] == "blocked_repair_evidence"
    assert payload["rollout_gate"]["ready_for_manual_strategy_review"] is False
    assert payload["rollout_gate"]["auto_apply_allowed"] is False
    assert payload["rollout_gate"]["blocked_by"] == ["repair_evidence_first", "repair_command_debt"]


def test_build_strategy_simulation_flags_repair_command_queue_count_mismatch(tmp_path, monkeypatch):
    def fake_build_trend_payload(input_paths, *, base_dir=None, max_json_bytes=2_000_000):
        return {
            "status": "WARN",
            "summary": {
                "report_count": 1,
                "problem_action_count": 1,
                "error_count": 0,
                "warning_count": 1,
                "evidence_gate_status_counts": {"fix_evidence_first": 1},
                "repair_command_count": 2,
                "repair_command_type_counts": {"evidence_doctor": 2},
                "top_repair_commands": [
                    {
                        "command": "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source.json",
                        "type": "evidence_doctor",
                        "count": 1,
                        "sources": {"blind": 1},
                    }
                ],
                "repair_command_queue": [
                    {
                        "command": "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source.json",
                        "type": "evidence_doctor",
                        "count": 1,
                        "sources": {"blind": 1},
                    }
                ],
                "operator_recommendation": {"action": "repair_evidence"},
            },
        }

    monkeypatch.setattr(
        "scripts.source_preflight_strategy_simulation.build_trend_payload",
        fake_build_trend_payload,
    )

    payload = build_strategy_simulation([tmp_path / "source_browser_preflight.json"], base_dir=tmp_path)

    assert payload["summary"]["repair_command_queue_consistency"] == {
        "status": "mismatch",
        "repair_command_count": 2,
        "queue_count_total": 1,
        "queue_item_count": 1,
        "top_item_count": 1,
    }
    assert payload["rollout_gate"]["status"] == "blocked_repair_evidence"
    assert payload["comparison"]["recommendation"] == "repair_evidence_first"


def test_build_strategy_simulation_blocks_operator_action_mismatch_before_strategy_review(tmp_path):
    input_path = _write_operator_action_mismatch_evidence(tmp_path)

    payload = build_strategy_simulation([input_path], base_dir=tmp_path)

    assert payload["trend_status"] == "FAIL"
    assert payload["summary"]["operator_action_mismatch_count"] == 1
    assert payload["summary"]["operator_action_mismatch_source_counts"] == {"ppomppu": 1}
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert payload["summary"]["repair_command_count"] == 2
    assert payload["variants"]["candidate"]["signals"]["recommendation_action"] == "repair_evidence"
    assert payload["variants"]["candidate"]["signals"]["success"] is False
    assert payload["variants"]["candidate"]["signals"]["safety_risk_flags"] == [
        "evidence_repair_required",
        "invalid_evidence",
        "repair_command_debt",
    ]
    assert payload["comparison"]["recommendation"] == "repair_evidence_first"
    assert payload["rollout_gate"]["status"] == "blocked_repair_evidence"
    assert payload["rollout_gate"]["ready_for_manual_strategy_review"] is False
    assert payload["rollout_gate"]["auto_apply_allowed"] is False
    assert payload["rollout_gate"]["blocked_by"] == [
        "invalid_evidence",
        "repair_evidence_first",
        "repair_command_debt",
    ]


def test_input_paths_collects_recent_directory_matches(tmp_path):
    older = tmp_path / ".tmp/source_browser_preflight-old.json"
    newer = tmp_path / ".tmp/source_browser_preflight-new.json"
    _write_json(older, {"summary": {}})
    _write_json(newer, {"summary": {}})
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_700_000_100, 1_700_000_100))
    args = parse_args(["--input-dir", str(tmp_path / ".tmp"), "--max-files", "1"])

    paths = _input_paths(args, tmp_path)

    assert paths == [newer]


def test_input_paths_keeps_explicit_empty_directory_from_falling_back_to_default(tmp_path):
    default_path = tmp_path / ".tmp/source_browser_preflight.json"
    empty_dir = tmp_path / "empty"
    _write_json(default_path, {"summary": {}})
    empty_dir.mkdir()
    args = parse_args(["--input-dir", str(empty_dir)])

    paths = _input_paths(args, tmp_path)
    payload = build_strategy_simulation(paths, base_dir=tmp_path)

    assert paths == []
    assert payload["input_paths"] == []
    assert payload["summary"]["report_count"] == 0
    assert payload["rollout_gate"]["status"] == "no_problem_actions"


def test_input_paths_treats_negative_max_files_as_zero(tmp_path):
    source_dir = tmp_path / ".tmp"
    _write_json(source_dir / "source_browser_preflight-old.json", {"summary": {}})
    _write_json(source_dir / "source_browser_preflight-new.json", {"summary": {}})
    args = parse_args(["--input-dir", str(source_dir), "--max-files", "-1"])

    paths = _input_paths(args, tmp_path)

    assert paths == []


def test_main_respects_relative_explicit_input_already_under_relative_base_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    base_dir = Path(".tmp/source-preflight")
    input_path = _write_complete_evidence(
        base_dir,
        source="ppomppu",
        status="timeout",
        report_name="source_browser_preflight.json",
    )
    output_path = base_dir / "strategy.json"

    exit_code = main(
        [
            "--input",
            input_path.as_posix(),
            "--base-dir",
            base_dir.as_posix(),
            "--output",
            output_path.as_posix(),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    disk_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload == disk_payload
    assert payload["trend_status"] == "PASS"
    assert payload["summary"]["report_count"] == 1
    assert payload["summary"]["error_count"] == 0


def test_main_writes_json_report_and_summary_only_suppresses_output_file(tmp_path, capsys):
    input_path = _write_complete_evidence(
        tmp_path,
        source="ppomppu",
        status="timeout",
        report_name="source_browser_preflight.json",
    )
    output_path = tmp_path / ".tmp/source_preflight_strategy_simulation.json"

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(output_path),
            "--json",
        ]
    )

    assert exit_code == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    disk_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_payload["comparison"]["recommendation"] == "insufficient_evidence"
    assert stdout_payload["rollout_gate"]["status"] == "strategy_review_ready"
    assert stdout_payload["rollout_gate"]["ready_for_manual_strategy_review"] is True
    assert stdout_payload["manual_ready_gate"] == {
        "required": False,
        "passed": True,
        "status": "not_required",
        "exit_code": 0,
        "reason": "Manual-ready gate was not requested.",
    }
    assert disk_payload["output"]["written"] is True

    summary_output = tmp_path / ".tmp/summary-only.json"
    exit_code = main(
        [
            "--input",
            str(input_path),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(summary_output),
            "--summary-only",
        ]
    )

    assert exit_code == 0
    summary = capsys.readouterr().out
    assert "source_preflight_strategy_simulation=(not written)" in summary
    assert "gate=strategy_review_ready" in summary
    assert "manual_ready_gate=not_required" in summary
    assert "repair_command_count=0" in summary
    assert "primary_repair_type=-" in summary
    assert "primary_repair_count=0" in summary
    assert "primary_repair_buckets=-" in summary
    assert "primary_repair_sources=-" in summary
    assert "repair_remaining=0" in summary
    assert "metric_missing=current:2/10,candidate:2/10" in summary
    assert "operator_action_mismatch_count=0" in summary
    assert "operator_action_mismatch_sources=-" in summary
    assert "evidence_fields=failure_report_path=1,html_snapshot_path=1,screenshot_path=1" in summary
    assert "scope=local_preflight_evidence" in summary
    assert "top_operator_action_count=1" in summary
    assert "top_operator_action_sources=ppomppu=1" in summary
    assert "top_operator_action=Inspect evidence." in summary
    assert not summary_output.exists()

    json_summary_output = tmp_path / ".tmp/summary-only-json.json"
    exit_code = main(
        [
            "--input",
            str(input_path),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(json_summary_output),
            "--summary-only",
            "--json",
        ]
    )

    assert exit_code == 0
    summary_json = json.loads(capsys.readouterr().out)
    assert summary_json["summary"]["metric_missing"] == "current:2/10,candidate:2/10"
    assert summary_json["summary"]["metric_total"] == 10
    assert summary_json["summary"]["measurement_scope"]["mode"] == "local_preflight_evidence"
    assert summary_json["summary"]["operator_action_mismatch_count"] == 0
    assert summary_json["summary"]["operator_action_mismatch_source_counts"] == {}
    assert summary_json["summary"]["evidence_field_counts"] == {
        "failure_report_path": 1,
        "html_snapshot_path": 1,
        "screenshot_path": 1,
    }
    assert summary_json["output"]["written"] is False
    assert summary_json["output"]["write_suppressed"] is True
    assert summary_json["output"]["suppression_flags"] == ["summary_only"]
    assert not json_summary_output.exists()


def test_main_require_manual_ready_passes_only_when_gate_is_ready(tmp_path, capsys):
    input_path = _write_complete_evidence(
        tmp_path,
        source="ppomppu",
        status="timeout",
        report_name="source_browser_preflight.json",
    )
    output_path = tmp_path / ".tmp/source_preflight_strategy_simulation.json"

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(output_path),
            "--require-manual-ready",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["rollout_gate"]["status"] == "strategy_review_ready"
    assert payload["manual_ready_gate"] == {
        "required": True,
        "passed": True,
        "status": "pass",
        "exit_code": 0,
        "reason": "Manual strategy review is ready: strategy_review_ready.",
    }


def test_main_require_manual_ready_blocks_fallback_only_without_repair_commands(tmp_path, capsys):
    input_path = _write_complete_evidence(
        tmp_path,
        source="blind",
        status="blocked",
        report_name="source_browser_preflight-blocked.json",
    )
    output_path = tmp_path / ".tmp/source_preflight_strategy_simulation.json"

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(output_path),
            "--require-manual-ready",
            "--json",
        ]
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["repair_command_count"] == 0
    assert payload["summary"]["repair_command_queue"] == []
    assert payload["rollout_gate"]["status"] == "fallback_only"
    assert payload["manual_ready_gate"] == {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Use ready fallback sources for this run; do not change selector, timeout, or source strategy.",
        "primary_repair_command": "",
        "repair_command_count": 0,
        "repair_command_remaining_count": 0,
        "repair_commands": [],
    }
    disk_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert disk_payload["manual_ready_gate"]["repair_commands"] == []


def test_main_require_manual_ready_blocks_repair_evidence(tmp_path, capsys):
    input_path = tmp_path / "source_browser_preflight-warning.json"
    _write_json(
        input_path,
        {
            "summary": {
                "problem_count": 1,
                "problem_actions": [{"source": "blind", "status": "blocked", "evidence": {"error": "blocked"}}],
            }
        },
    )
    output_path = tmp_path / ".tmp/source_preflight_strategy_simulation.json"

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(output_path),
            "--require-manual-ready",
        ]
    )

    assert exit_code == 2
    summary = capsys.readouterr().out
    assert "gate=blocked_repair_evidence" in summary
    assert "manual_ready_gate=blocked" in summary
    assert "repair_command_count=2" in summary
    assert "repair_remaining=1" in summary
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["manual_ready_gate"]["passed"] is False
    assert payload["manual_ready_gate"]["exit_code"] == 2
    assert "Run the recommended repair commands" in payload["manual_ready_gate"]["reason"]
    commands = payload["manual_ready_gate"]["repair_commands"]
    assert payload["manual_ready_gate"]["primary_repair_command"] == commands[0]
    assert "source_preflight_evidence_doctor.py" in commands[0]
    assert payload["manual_ready_gate"]["repair_command_count"] == 2
    assert payload["manual_ready_gate"]["repair_command_remaining_count"] == 1
    assert any("source_preflight_evidence_doctor.py" in command for command in commands)
    assert any("--source blind" in command for command in commands)


def test_main_require_manual_ready_blocks_operator_action_mismatch(tmp_path, capsys):
    input_path = _write_operator_action_mismatch_evidence(tmp_path)
    output_path = tmp_path / ".tmp/source_preflight_strategy_simulation.json"

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(output_path),
            "--require-manual-ready",
            "--json",
        ]
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["operator_action_mismatch_count"] == 1
    assert payload["summary"]["operator_action_mismatch_source_counts"] == {"ppomppu": 1}
    assert payload["rollout_gate"]["status"] == "blocked_repair_evidence"
    assert payload["manual_ready_gate"]["status"] == "blocked"
    assert payload["manual_ready_gate"]["exit_code"] == 2
    assert payload["manual_ready_gate"]["repair_command_count"] == 2
    assert payload["manual_ready_gate"]["repair_command_remaining_count"] == 1
    assert "source_preflight_evidence_doctor.py" in payload["manual_ready_gate"]["primary_repair_command"]
    assert any(
        "source_preflight_evidence_doctor.py" in command for command in payload["manual_ready_gate"]["repair_commands"]
    )
    disk_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert disk_payload["manual_ready_gate"]["status"] == "blocked"


def test_main_summary_only_prints_operator_action_mismatch_count(tmp_path, capsys):
    input_path = _write_operator_action_mismatch_evidence(tmp_path)
    output_path = tmp_path / ".tmp/source_preflight_strategy_summary.json"

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(output_path),
            "--require-manual-ready",
            "--summary-only",
        ]
    )

    assert exit_code == 2
    summary = capsys.readouterr().out
    assert "manual_ready_gate=blocked" in summary
    assert "repair_remaining=1" in summary
    assert "primary_repair_type=evidence_doctor" in summary
    assert "primary_repair_count=1" in summary
    assert "primary_repair_buckets=ppomppu|timeout=1" in summary
    assert "primary_repair_sources=ppomppu=1" in summary
    assert "operator_action_mismatch_count=1" in summary
    assert "operator_action_mismatch_sources=ppomppu=1" in summary
    assert "evidence_fields=failure_report_path=1,html_snapshot_path=1,screenshot_path=1" in summary
    assert not output_path.exists()


def test_main_require_manual_ready_counts_multiple_repair_commands(tmp_path, capsys):
    first = tmp_path / "source_browser_preflight-first.json"
    second = tmp_path / "source_browser_preflight-second.json"
    third = tmp_path / "source_browser_preflight-third.json"
    for path, source in ((first, "blind"), (second, "ppomppu"), (third, "dcinside")):
        _write_json(
            path,
            {
                "summary": {
                    "problem_count": 1,
                    "problem_actions": [{"source": source, "status": "blocked", "evidence": {"error": "blocked"}}],
                }
            },
        )
    output_path = tmp_path / ".tmp/source_preflight_strategy_simulation.json"

    exit_code = main(
        [
            "--input",
            str(first),
            "--input",
            str(second),
            "--input",
            str(third),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(output_path),
            "--require-manual-ready",
            "--json",
        ]
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    commands = payload["manual_ready_gate"]["repair_commands"]
    assert len(payload["summary"]["top_repair_commands"]) == 4
    assert len(payload["summary"]["repair_command_queue"]) == 6
    assert payload["manual_ready_gate"]["repair_command_count"] == 6
    assert payload["manual_ready_gate"]["repair_command_remaining_count"] == 5
    assert payload["manual_ready_gate"]["primary_repair_command"] == commands[0]
    assert "source_preflight_evidence_doctor.py" in commands[0]
    assert any("source_preflight_evidence_doctor.py" in command for command in commands)
    assert any("--source blind" in command for command in commands)
    assert any("--source ppomppu" in command for command in commands)
    assert any("--source dcinside" in command for command in commands)

    summary_output = tmp_path / ".tmp/source_preflight_strategy_summary.json"
    exit_code = main(
        [
            "--input",
            str(first),
            "--input",
            str(second),
            "--input",
            str(third),
            "--base-dir",
            str(tmp_path),
            "--output",
            str(summary_output),
            "--require-manual-ready",
            "--summary-only",
        ]
    )

    assert exit_code == 2
    summary = capsys.readouterr().out
    assert "manual_ready_gate=blocked" in summary
    assert "repair_command_count=6" in summary
    assert "repair_queue=ok" in summary
    assert "primary_repair_type=evidence_doctor" in summary
    assert "primary_repair_count=1" in summary
    assert "primary_repair_buckets=blind|blocked=1" in summary
    assert "primary_repair_sources=blind=1" in summary
    assert "repair_remaining=5" in summary
    assert "metric_missing=current:2/10,candidate:2/10" in summary
    assert "operator_action_mismatch_count=0" in summary
    assert "operator_action_mismatch_sources=-" in summary
    assert "evidence_fields=error=3" in summary
    assert "scope=local_preflight_evidence" in summary
    assert "top_operator_action_count=0" in summary
    assert "top_operator_action=-" in summary
    assert not summary_output.exists()
