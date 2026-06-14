from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.source_preflight_trend_report import (  # noqa: E402
    _input_paths,
    build_trend_payload,
    exit_code_for_trend,
    main,
    parse_args,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _preflight_report(
    *,
    source: str = "ppomppu",
    status: str = "timeout",
    failure_report_path: str = ".tmp/failures/source_preflight/ppomppu-timeout.json",
    operator_action: str = "Inspect evidence.",
) -> dict:
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
                        "failure_report_path": failure_report_path,
                        "screenshot_path": f"screenshots/source_preflight/{source}.png",
                        "html_snapshot_path": f".tmp/failures/source_preflight/{source}.html",
                    },
                }
            ],
        }
    }


def _failure_report(
    *, source: str = "ppomppu", status: str = "timeout", operator_action: str = "Inspect evidence."
) -> dict:
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


def _write_complete_evidence(tmp_path: Path, *, report_name: str, source: str, status: str) -> Path:
    failure_report_path = f".tmp/failures/source_preflight/{source}-{status}.json"
    input_path = tmp_path / report_name
    _write_json(input_path, _preflight_report(source=source, status=status, failure_report_path=failure_report_path))
    _write_json(tmp_path / failure_report_path, _failure_report(source=source, status=status))
    screenshot = tmp_path / f"screenshots/source_preflight/{source}.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")
    html = tmp_path / f".tmp/failures/source_preflight/{source}.html"
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text("<html>evidence</html>", encoding="utf-8")
    return input_path


def _write_operator_action_mismatch_evidence(tmp_path: Path) -> Path:
    failure_report_path = ".tmp/failures/source_preflight/ppomppu-timeout.json"
    input_path = tmp_path / "source_browser_preflight-mismatch.json"
    _write_json(
        input_path,
        _preflight_report(
            source="ppomppu",
            status="timeout",
            failure_report_path=failure_report_path,
            operator_action="Inspect preflight summary evidence.",
        ),
    )
    _write_json(
        tmp_path / failure_report_path,
        _failure_report(
            source="ppomppu",
            status="timeout",
            operator_action="Inspect stale failure report evidence.",
        ),
    )
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")
    html = tmp_path / ".tmp/failures/source_preflight/ppomppu.html"
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text("<html>evidence</html>", encoding="utf-8")
    return input_path


def test_build_trend_payload_counts_status_sources_and_safety(tmp_path):
    first = _write_complete_evidence(
        tmp_path, report_name="source_browser_preflight-1.json", source="ppomppu", status="timeout"
    )
    second = _write_complete_evidence(
        tmp_path, report_name="source_browser_preflight-2.json", source="blind", status="blocked"
    )

    payload = build_trend_payload([first, second], base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["ok"] is True
    assert payload["summary"]["report_count"] == 2
    assert payload["summary"]["problem_action_count"] == 2
    assert payload["summary"]["operator_action_required_count"] == 2
    assert payload["summary"]["operator_action_counts"] == {"Inspect evidence.": 2}
    assert payload["summary"]["top_operator_actions"] == [
        {
            "operator_action": "Inspect evidence.",
            "count": 2,
            "sources": {"ppomppu": 1, "blind": 1},
        }
    ]
    assert payload["summary"]["status_counts"] == {"timeout": 1, "blocked": 1}
    assert payload["summary"]["source_counts"] == {"ppomppu": 1, "blind": 1}
    assert payload["summary"]["failure_report_status_counts"] == {"valid": 2}
    assert payload["summary"]["strategy_change_ready_count"] == 1
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
    assert payload["summary"]["top_source_action"] == {
        "source": "blind",
        "status": "blocked",
        "count": 1,
        "operator_action": "Use a ready fallback source for this run, then recheck blind after access controls change.",
    }
    assert payload["summary"]["top_source_remediation"] == {
        "source": "blind",
        "status": "blocked",
        "count": 1,
        "evidence_fields": ["failure_report_path", "screenshot_path", "html_snapshot_path", "trace_path", "error"],
        "checklist": [
            "Open blind evidence fields first: failure_report_path, screenshot_path, html_snapshot_path, trace_path, error.",
            "Use a ready fallback source for this run; do not add aggressive access-bypass logic.",
            "Recheck blind only after access controls or source availability change.",
        ],
    }
    top_source_evidence = payload["summary"]["top_source_evidence"]
    assert top_source_evidence["source"] == "blind"
    assert top_source_evidence["status"] == "blocked"
    assert top_source_evidence["count"] == 1
    assert top_source_evidence["input_path"] == str(second)
    assert top_source_evidence["evidence_gate_status"] == "fallback_only"
    assert top_source_evidence["open_first_field"] == "failure_report_path"
    assert top_source_evidence["open_first"] == ".tmp/failures/source_preflight/blind-blocked.json"
    assert top_source_evidence["evidence"] == {
        "failure_report_path": ".tmp/failures/source_preflight/blind-blocked.json",
        "screenshot_path": "screenshots/source_preflight/blind.png",
        "html_snapshot_path": ".tmp/failures/source_preflight/blind.html",
    }
    assert payload["summary"]["operator_recommendation"] == {
        "action": "split_fallback_and_strategy_review",
        "priority": "medium",
        "source": "blind",
        "status": "blocked",
        "reason": "Some failures need fallback handling while others are ready for strategy review.",
        "operator_action": (
            "Use ready fallback sources for fallback-only failures, then inspect strategy-ready evidence before "
            "selector, timeout, or source-strategy changes."
        ),
        "gate_counts": {
            "fix_evidence_first": 0,
            "fallback_only": 1,
            "strategy_review_ready": 1,
        },
    }
    assert payload["safety"] == {
        "read_only": True,
        "browser_launches": False,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }
    assert exit_code_for_trend(payload) == 0


def test_build_trend_payload_respects_explicit_operator_action_required_false(tmp_path):
    input_path = tmp_path / "source_browser_preflight-warning.json"
    _write_json(
        input_path,
        {
            "summary": {
                "problem_count": 1,
                "problem_actions": [
                    {
                        "source": "blind",
                        "status": "blocked",
                        "action": "Inspect legacy action only.",
                        "operator_action_required": False,
                        "operator_action": "",
                        "evidence": {"error": "blocked"},
                    }
                ],
            }
        },
    )

    payload = build_trend_payload([input_path], base_dir=tmp_path)

    assert payload["status"] == "WARN"
    assert payload["summary"]["operator_action_required_count"] == 0
    assert payload["summary"]["operator_action_counts"] == {"Inspect legacy action only.": 1}
    assert payload["summary"]["top_operator_actions"] == [
        {
            "operator_action": "Inspect legacy action only.",
            "count": 1,
            "sources": {"blind": 1},
        }
    ]


def test_build_trend_payload_respects_string_false_operator_action_required(tmp_path):
    input_path = tmp_path / "source_browser_preflight-warning.json"
    _write_json(
        input_path,
        {
            "summary": {
                "problem_count": 1,
                "problem_actions": [
                    {
                        "source": "blind",
                        "status": "blocked",
                        "action": "Inspect legacy action only.",
                        "operator_action_required": "false",
                        "operator_action": "",
                        "evidence": {"error": "blocked"},
                    }
                ],
            }
        },
    )

    payload = build_trend_payload([input_path], base_dir=tmp_path)

    assert payload["status"] == "WARN"
    assert payload["summary"]["operator_action_required_count"] == 0
    assert payload["summary"]["operator_action_counts"] == {"Inspect legacy action only.": 1}


def test_build_trend_payload_counts_failure_report_operator_action_for_legacy_problem_action(tmp_path):
    input_path = _write_complete_evidence(
        tmp_path,
        report_name="source_browser_preflight-legacy.json",
        source="ppomppu",
        status="timeout",
    )
    report = json.loads(input_path.read_text(encoding="utf-8"))
    action = report["summary"]["problem_actions"][0]
    del action["operator_action_required"]
    del action["operator_action"]
    del action["action"]
    _write_json(input_path, report)

    payload = build_trend_payload([input_path], base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["summary"]["operator_action_required_count"] == 1
    assert payload["summary"]["operator_action_counts"] == {"Inspect evidence.": 1}
    assert payload["summary"]["top_operator_actions"] == [
        {
            "operator_action": "Inspect evidence.",
            "count": 1,
            "sources": {"ppomppu": 1},
        }
    ]


def test_build_trend_payload_accepts_string_true_failure_report_action_required(tmp_path):
    input_path = _write_complete_evidence(
        tmp_path,
        report_name="source_browser_preflight-string-true.json",
        source="ppomppu",
        status="timeout",
    )
    failure_report_path = tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json"
    failure_report = json.loads(failure_report_path.read_text(encoding="utf-8"))
    failure_report["operator"]["action_required"] = "true"
    _write_json(failure_report_path, failure_report)

    payload = build_trend_payload([input_path], base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["summary"]["failure_report_status_counts"] == {"valid": 1}
    assert payload["summary"]["top_issue_codes"] == {}
    assert payload["summary"]["operator_action_required_count"] == 1


def test_build_trend_payload_does_not_trust_invalid_failure_report_action_required_false(tmp_path):
    input_path = _write_complete_evidence(
        tmp_path,
        report_name="source_browser_preflight-action-required-false.json",
        source="ppomppu",
        status="timeout",
    )
    report = json.loads(input_path.read_text(encoding="utf-8"))
    action = report["summary"]["problem_actions"][0]
    del action["operator_action_required"]
    del action["operator_action"]
    del action["action"]
    _write_json(input_path, report)
    failure_report_path = tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json"
    failure_report = json.loads(failure_report_path.read_text(encoding="utf-8"))
    failure_report["operator"]["action_required"] = False
    _write_json(failure_report_path, failure_report)

    payload = build_trend_payload([input_path], base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["summary"]["failure_report_status_counts"] == {"invalid": 1}
    assert payload["summary"]["top_issue_codes"] == {"operator_action_not_required": 1}
    assert payload["summary"]["operator_action_required_count"] == 1
    assert payload["summary"]["operator_action_counts"] == {"Inspect evidence.": 1}


def test_build_trend_payload_surfaces_warnings(tmp_path):
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

    payload = build_trend_payload([input_path], base_dir=tmp_path)

    assert payload["status"] == "WARN"
    assert payload["summary"]["warning_count"] == 1
    assert payload["summary"]["strategy_change_ready_count"] == 0
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert payload["summary"]["evidence_field_counts"] == {"error": 1}
    assert payload["summary"]["top_issue_codes"] == {"missing_failure_report_path": 1}
    assert payload["summary"]["top_source_action"] == {
        "source": "blind",
        "status": "blocked",
        "count": 1,
        "operator_action": "Use a ready fallback source for this run, then recheck blind after access controls change.",
    }
    assert payload["summary"]["top_source_remediation"]["checklist"][1] == (
        "Use a ready fallback source for this run; do not add aggressive access-bypass logic."
    )
    assert payload["summary"]["operator_recommendation"]["action"] == "repair_evidence"
    assert payload["summary"]["operator_recommendation"]["priority"] == "high"
    assert payload["summary"]["operator_recommendation"]["gate_counts"] == {
        "fix_evidence_first": 1,
        "fallback_only": 0,
        "strategy_review_ready": 0,
    }
    assert payload["summary"]["repair_command_count"] == 2
    assert payload["summary"]["repair_command_type_counts"] == {
        "source_preflight_capture": 1,
        "evidence_doctor": 1,
    }
    top_repair_commands = payload["summary"]["top_repair_commands"]
    assert [item["type"] for item in top_repair_commands] == ["evidence_doctor", "source_preflight_capture"]
    assert top_repair_commands[0]["buckets"] == {"blind|blocked": 1}
    assert top_repair_commands[1]["buckets"] == {"blind|blocked": 1}
    assert any("--source blind" in item["command"] for item in top_repair_commands)
    assert any("source_preflight_evidence_doctor.py" in item["command"] for item in top_repair_commands)
    assert exit_code_for_trend(payload) == 0
    assert exit_code_for_trend(payload, fail_on_warning=True) == 1


def test_build_trend_payload_preserves_full_repair_command_queue_when_top_is_limited(tmp_path):
    input_paths = []
    sources = ["blind", "ppomppu", "dcinside"]
    for source in sources:
        input_path = tmp_path / f"source_browser_preflight-{source}.json"
        _write_json(
            input_path,
            {
                "summary": {
                    "problem_count": 1,
                    "problem_actions": [{"source": source, "status": "blocked", "evidence": {"error": "blocked"}}],
                }
            },
        )
        input_paths.append(input_path)

    payload = build_trend_payload(input_paths, base_dir=tmp_path)

    summary = payload["summary"]
    queue = summary["repair_command_queue"]
    assert summary["repair_command_count"] == 6
    assert len(summary["top_repair_commands"]) == 4
    assert len(queue) == 6
    assert [item["type"] for item in queue[:3]] == ["evidence_doctor", "evidence_doctor", "evidence_doctor"]
    assert [item["type"] for item in queue[3:]] == [
        "source_preflight_capture",
        "source_preflight_capture",
        "source_preflight_capture",
    ]
    for source in sources:
        assert any(source in item["command"] for item in queue)
        assert any(item.get("buckets") == {f"{source}|blocked": 1} for item in queue)


def test_build_trend_payload_surfaces_errors(tmp_path):
    input_path = tmp_path / "source_browser_preflight-error.json"
    _write_json(
        input_path,
        _preflight_report(
            source="ppomppu",
            status="timeout",
            failure_report_path=".tmp/failures/source_preflight/missing.json",
        ),
    )

    payload = build_trend_payload([input_path], base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["summary"]["error_count"] == 1
    assert payload["summary"]["strategy_change_ready_count"] == 0
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert payload["summary"]["top_issue_codes"] == {"missing_json": 1}
    assert payload["reports"][0]["failure_report_status_counts"] == {"invalid": 1}
    assert payload["summary"]["top_source_action"] == {
        "source": "ppomppu",
        "status": "timeout",
        "count": 1,
        "operator_action": (
            "Inspect ppomppu timeout evidence, then adjust timeout or source fallback only after evidence is valid."
        ),
    }
    assert payload["summary"]["top_source_remediation"] == {
        "source": "ppomppu",
        "status": "timeout",
        "count": 1,
        "evidence_fields": ["failure_report_path", "screenshot_path", "html_snapshot_path", "trace_path", "error"],
        "checklist": [
            "Open ppomppu evidence fields first: failure_report_path, screenshot_path, html_snapshot_path, trace_path, error.",
            (
                "Use a ready fallback source for this run if available; do not increase ppomppu timeout until "
                "evidence shows a reachable slow page."
            ),
            "Rerun ppomppu preflight with --failure-dir after any timeout or selector change.",
        ],
    }
    assert payload["summary"]["operator_recommendation"]["action"] == "repair_evidence"
    assert payload["summary"]["operator_recommendation"]["priority"] == "high"
    assert payload["summary"]["operator_recommendation"]["source"] == "ppomppu"
    assert payload["summary"]["operator_recommendation"]["status"] == "timeout"
    assert exit_code_for_trend(payload) == 2


def test_build_trend_payload_summarizes_operator_action_mismatches(tmp_path, capsys):
    input_path = _write_operator_action_mismatch_evidence(tmp_path)

    payload = build_trend_payload([input_path], base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["summary"]["top_issue_codes"] == {"operator_action_mismatch": 1}
    assert payload["summary"]["operator_action_mismatch_count"] == 1
    assert payload["summary"]["operator_action_mismatch_source_counts"] == {"ppomppu": 1}
    assert payload["reports"][0]["operator_action_mismatch_count"] == 1
    assert payload["reports"][0]["operator_action_mismatch_source_counts"] == {"ppomppu": 1}
    assert payload["summary"]["operator_recommendation"]["action"] == "repair_evidence"
    assert exit_code_for_trend(payload) == 2

    exit_code = main(["--input", str(input_path), "--base-dir", str(tmp_path)])

    assert exit_code == 2
    output = capsys.readouterr().out
    assert "operator_action_mismatches: count=1; sources=ppomppu=1" in output


def test_main_json_output_writes_operator_action_mismatch_counts(tmp_path, capsys):
    input_path = _write_operator_action_mismatch_evidence(tmp_path)
    output_path = tmp_path / ".tmp/source_preflight_trend.json"

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

    assert exit_code == 2
    stdout_payload = json.loads(capsys.readouterr().out)
    output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_payload == output_payload
    assert output_payload["summary"]["operator_action_mismatch_count"] == 1
    assert output_payload["summary"]["operator_action_mismatch_source_counts"] == {"ppomppu": 1}
    assert output_payload["summary"]["top_issue_codes"] == {"operator_action_mismatch": 1}
    assert output_payload["summary"]["operator_recommendation"]["action"] == "repair_evidence"


def test_top_source_action_uses_count_then_source_status_tiebreak(tmp_path):
    first = _write_complete_evidence(
        tmp_path, report_name="source_browser_preflight-1.json", source="ppomppu", status="timeout"
    )
    second = _write_complete_evidence(
        tmp_path, report_name="source_browser_preflight-2.json", source="blind", status="blocked"
    )
    third = _write_complete_evidence(
        tmp_path, report_name="source_browser_preflight-3.json", source="ppomppu", status="timeout"
    )

    payload = build_trend_payload([first, second, third], base_dir=tmp_path)

    assert payload["summary"]["top_source_action"] == {
        "source": "ppomppu",
        "status": "timeout",
        "count": 2,
        "operator_action": (
            "Inspect ppomppu timeout evidence, then adjust timeout or source fallback only after evidence is valid."
        ),
    }
    assert payload["summary"]["top_source_remediation"]["source"] == "ppomppu"
    assert payload["summary"]["top_source_remediation"]["status"] == "timeout"
    assert payload["summary"]["top_source_remediation"]["count"] == 2
    assert payload["summary"]["strategy_change_ready_count"] == 2
    assert payload["summary"]["evidence_gate_status_counts"] == {
        "strategy_review_ready": 2,
        "fallback_only": 1,
    }
    assert payload["summary"]["operator_recommendation"]["action"] == "split_fallback_and_strategy_review"
    assert payload["summary"]["operator_recommendation"]["gate_counts"] == {
        "fix_evidence_first": 0,
        "fallback_only": 1,
        "strategy_review_ready": 2,
    }
    assert payload["summary"]["top_source_evidence"]["source"] == "ppomppu"
    assert payload["summary"]["top_source_evidence"]["status"] == "timeout"
    assert payload["summary"]["top_source_evidence"]["count"] == 2
    assert payload["summary"]["top_source_evidence"]["open_first"] == (
        ".tmp/failures/source_preflight/ppomppu-timeout.json"
    )
    assert "do not increase ppomppu timeout" in payload["summary"]["top_source_remediation"]["checklist"][1]


def test_input_paths_collects_recent_directory_matches(tmp_path):
    older = tmp_path / ".tmp/source_browser_preflight-old.json"
    newer = tmp_path / ".tmp/source_browser_preflight-new.json"
    ignored = tmp_path / ".tmp/other.json"
    _write_json(older, {"summary": {}})
    _write_json(newer, {"summary": {}})
    _write_json(ignored, {"summary": {}})
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
    payload = build_trend_payload(paths, base_dir=tmp_path)

    assert paths == []
    assert payload["summary"]["report_count"] == 0


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
        base_dir, report_name="source_browser_preflight.json", source="ppomppu", status="timeout"
    )
    output_path = base_dir / "trend.json"

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

    stdout_payload = json.loads(capsys.readouterr().out)
    output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert stdout_payload == output_payload
    assert output_payload["status"] == "PASS"
    assert output_payload["summary"]["report_count"] == 1
    assert output_payload["summary"]["error_count"] == 0


def test_main_writes_output_and_json_stdout(tmp_path, capsys):
    input_path = _write_complete_evidence(
        tmp_path, report_name="source_browser_preflight.json", source="ppomppu", status="timeout"
    )
    output_path = tmp_path / ".tmp/source_preflight_trend.json"

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
    output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_payload["status"] == "PASS"
    assert output_payload["summary"]["status_counts"] == {"timeout": 1}
    assert output_payload["summary"]["strategy_change_ready_count"] == 1
    assert output_payload["summary"]["repair_command_count"] == 0
    assert output_payload["summary"]["operator_recommendation"]["action"] == "review_source_strategy"
    assert output_payload["summary"]["top_source_remediation"]["checklist"][0].startswith("Open ppomppu evidence")


def test_main_text_report_prints_top_source_checklist(tmp_path, capsys):
    input_path = _write_complete_evidence(
        tmp_path, report_name="source_browser_preflight.json", source="ppomppu", status="timeout"
    )

    exit_code = main(["--input", str(input_path), "--base-dir", str(tmp_path)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "top_source_checklist:" in output
    assert "top_source_evidence: source=ppomppu; status=timeout; open_first=failure_report_path=" in output
    assert "operator_recommendation: action=review_source_strategy" in output
    assert "strategy_change_ready: 1" in output
    assert "evidence_gates: strategy_review_ready=1" in output
    assert "evidence_fields: failure_report_path=1, html_snapshot_path=1, screenshot_path=1" in output
    assert "repair_commands: count=0; types=-" in output
    assert "top_operator_action: count=1; sources=ppomppu=1; action=Inspect evidence." in output
    assert "do not increase ppomppu timeout" in output


def test_main_text_report_prints_repair_command_counts_for_missing_evidence(tmp_path, capsys):
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

    exit_code = main(["--input", str(input_path), "--base-dir", str(tmp_path)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "repair_commands: count=2; types=evidence_doctor=1, source_preflight_capture=1" in output
    assert "evidence_fields: error=1" in output
    assert "top_repair_command: count=1; type=evidence_doctor; sources=blind=1" in output
    assert "top_repair_command: count=1; type=source_preflight_capture; sources=blind=1" in output
    assert output.index("type=evidence_doctor") < output.index("type=source_preflight_capture")
