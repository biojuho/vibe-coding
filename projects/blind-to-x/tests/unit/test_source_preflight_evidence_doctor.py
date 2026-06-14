from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.source_preflight_evidence_doctor import (  # noqa: E402
    _print_text_report,
    _trace_viewer_command,
    build_evidence_payload,
    exit_code_for_payload,
    main,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _valid_failure_report(source: str = "ppomppu", status: str = "timeout") -> dict:
    return {
        "source": source,
        "classification": {"status": status, "reason": "navigation timed out", "signals": ["timeout"]},
        "failure_report": {
            "schema_version": 1,
            "tool": "source_browser_probe",
            "captured_at": "2026-06-10T00:00:00+00:00",
        },
        "operator": {
            "action_required": True,
            "action": "Inspect captured evidence, then retry.",
            "evidence": {
                "failure_report_path": f".tmp/failures/source_preflight/{source}-{status}.json",
                "screenshot_path": f"screenshots/source_preflight/{source}.png",
                "html_snapshot_path": f".tmp/failures/source_preflight/{source}.html",
            },
        },
    }


def _preflight_report() -> dict:
    return {
        "summary": {
            "problem_count": 1,
            "problem_actions": [
                {
                    "source": "ppomppu",
                    "status": "timeout",
                    "action": "Inspect captured evidence, then retry.",
                    "operator_action_required": True,
                    "operator_action": "Inspect captured evidence, then retry.",
                    "evidence": {
                        "failure_report_path": ".tmp/failures/source_preflight/ppomppu-timeout.json",
                        "screenshot_path": "screenshots/source_preflight/ppomppu.png",
                        "html_snapshot_path": ".tmp/failures/source_preflight/ppomppu.html",
                    },
                }
            ],
        }
    }


def test_build_evidence_payload_passes_for_complete_failure_report(tmp_path):
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", _preflight_report())
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        _valid_failure_report(),
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["ok"] is True
    assert payload["summary"] == {
        "problem_action_count": 1,
        "failure_report_count": 1,
        "error_count": 0,
        "warning_count": 0,
        "strategy_change_ready_count": 1,
        "evidence_gate_status_counts": {"strategy_review_ready": 1},
        "repair_command_count": 0,
    }
    assert payload["items"][0]["failure_report_status"] == "valid"
    assert payload["items"][0]["operator_action_required"] is True
    assert payload["items"][0]["operator_action"] == "Inspect captured evidence, then retry."
    assert payload["items"][0]["evidence"] == {
        "failure_report_path": ".tmp/failures/source_preflight/ppomppu-timeout.json",
        "screenshot_path": "screenshots/source_preflight/ppomppu.png",
        "html_snapshot_path": ".tmp/failures/source_preflight/ppomppu.html",
    }
    assert payload["items"][0]["evidence_gate"] == {
        "status": "strategy_review_ready",
        "strategy_change_ready": True,
        "decision": "review_source_strategy",
        "reason": "Failure evidence is structurally complete enough to review selector, timeout, or source strategy.",
        "evidence_fields": ["failure_report_path", "html_snapshot_path", "screenshot_path"],
        "missing_required_evidence": [],
    }
    assert payload["items"][0]["repair_commands"] == []
    assert exit_code_for_payload(payload) == 0


def test_build_evidence_payload_accepts_string_true_failure_report_action_required(tmp_path):
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", _preflight_report())
    failure_report = _valid_failure_report()
    failure_report["operator"]["action_required"] = "true"
    _write_json(tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json", failure_report)
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["items"][0]["failure_report_status"] == "valid"
    assert payload["items"][0]["operator_action_required"] is True
    assert payload["issues"] == []


def test_build_evidence_payload_does_not_trust_invalid_failure_report_action_required_false(tmp_path):
    report = _preflight_report()
    action = report["summary"]["problem_actions"][0]
    del action["operator_action_required"]
    del action["operator_action"]
    del action["action"]
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", report)
    failure_report = _valid_failure_report()
    failure_report["operator"]["action_required"] = False
    _write_json(tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json", failure_report)
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["items"][0]["failure_report_status"] == "invalid"
    assert payload["items"][0]["operator_action_required"] is True
    assert payload["items"][0]["operator_action"] == "Inspect captured evidence, then retry."
    assert [issue["code"] for issue in payload["items"][0]["issues"]] == ["operator_action_not_required"]


def test_build_evidence_payload_respects_relative_input_already_under_relative_base_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base_dir = Path(".tmp/source-preflight")
    input_path = base_dir / "source_browser_preflight.json"
    _write_json(input_path, _preflight_report())
    _write_json(
        base_dir / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        _valid_failure_report(),
    )
    (base_dir / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = base_dir / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(input_path, base_dir=base_dir)

    assert payload["status"] == "PASS"
    assert payload["summary"]["error_count"] == 0
    assert payload["items"][0]["failure_report_status"] == "valid"


def test_build_evidence_payload_warns_when_problem_action_has_no_failure_report_path(tmp_path):
    report = {
        "summary": {
            "problem_count": 1,
            "problem_actions": [
                {
                    "source": "blind",
                    "status": "blocked",
                    "action": "Use fallback.",
                    "evidence": {"error": "blocked"},
                }
            ],
        }
    }
    _write_json(tmp_path / "preflight.json", report)

    payload = build_evidence_payload(tmp_path / "preflight.json", base_dir=tmp_path)

    assert payload["status"] == "WARN"
    assert payload["summary"]["warning_count"] == 1
    assert payload["summary"]["strategy_change_ready_count"] == 0
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert payload["issues"][0]["code"] == "missing_failure_report_path"
    assert payload["items"][0]["evidence_gate"]["status"] == "fix_evidence_first"
    assert payload["summary"]["repair_command_count"] == 2
    assert payload["items"][0]["repair_commands"][0].startswith("py -3 scripts/source_preflight_evidence_doctor.py")
    assert "--fail-on-warning" in payload["items"][0]["repair_commands"][0]
    assert "--source blind" in payload["items"][0]["repair_commands"][1]
    assert "--source-preflight-click-through" in payload["items"][0]["repair_commands"][1]
    assert exit_code_for_payload(payload) == 0
    assert exit_code_for_payload(payload, fail_on_warning=True) == 1


def test_build_evidence_payload_infers_operator_action_fields_for_legacy_reports(tmp_path):
    report = _preflight_report()
    action = report["summary"]["problem_actions"][0]
    del action["operator_action_required"]
    del action["operator_action"]
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", report)
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        _valid_failure_report(),
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["items"][0]["operator_action_required"] is True
    assert payload["items"][0]["operator_action"] == "Inspect captured evidence, then retry."


def test_build_evidence_payload_infers_operator_action_from_failure_report_when_summary_action_missing(tmp_path):
    report = _preflight_report()
    action = report["summary"]["problem_actions"][0]
    del action["operator_action_required"]
    del action["operator_action"]
    del action["action"]
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", report)
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        _valid_failure_report(),
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["items"][0]["operator_action_required"] is True
    assert payload["items"][0]["operator_action"] == "Inspect captured evidence, then retry."


def test_build_evidence_payload_respects_string_false_operator_action_required(tmp_path):
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

    payload = build_evidence_payload(input_path, base_dir=tmp_path)

    assert payload["status"] == "WARN"
    assert payload["items"][0]["operator_action_required"] is False
    assert payload["items"][0]["operator_action"] == "Inspect legacy action only."


def test_text_report_prints_operator_action_for_pass_items(tmp_path, capsys):
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", _preflight_report())
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        _valid_failure_report(),
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")
    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    _print_text_report(payload)

    text = capsys.readouterr().out
    assert "status: PASS" in text
    assert "operator_action item=0 source=ppomppu: required=true action=Inspect captured evidence, then retry." in text
    assert "repair_commands item=0" not in text


def test_build_evidence_payload_fails_when_referenced_artifact_is_missing(tmp_path, capsys):
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", _preflight_report())
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        _valid_failure_report(),
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["ok"] is False
    assert payload["summary"]["error_count"] == 1
    assert payload["summary"]["strategy_change_ready_count"] == 0
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert payload["issues"][0]["code"] == "missing_screenshot_path"
    assert payload["summary"]["repair_command_count"] == 2
    repair_commands = payload["items"][0]["repair_commands"]
    assert repair_commands[0].startswith("py -3 scripts/source_preflight_evidence_doctor.py")
    assert "--input" in repair_commands[0]
    assert "--base-dir" in repair_commands[0]
    assert "--fail-on-warning" in repair_commands[0]
    assert repair_commands[1].startswith("py -3 main.py")
    assert "--source ppomppu" in repair_commands[1]
    assert "--source-preflight-output" in repair_commands[1]
    assert "--source-preflight-screenshot-dir" in repair_commands[1]
    assert "--source-preflight-failure-dir" in repair_commands[1]
    assert exit_code_for_payload(payload) == 2

    _print_text_report(payload)
    text = capsys.readouterr().out
    assert "repair_commands: 2" in text
    assert "repair_commands item=0 source=ppomppu:" in text
    assert "py -3 main.py" in text


def test_build_evidence_payload_marks_blocked_source_as_fallback_only(tmp_path):
    report = _preflight_report()
    action = report["summary"]["problem_actions"][0]
    action["source"] = "blind"
    action["status"] = "blocked"
    action["evidence"]["failure_report_path"] = ".tmp/failures/source_preflight/blind-blocked.json"
    action["evidence"]["screenshot_path"] = "screenshots/source_preflight/blind.png"
    action["evidence"]["html_snapshot_path"] = ".tmp/failures/source_preflight/blind.html"
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", report)
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/blind-blocked.json",
        _valid_failure_report(source="blind", status="blocked"),
    )
    (tmp_path / ".tmp/failures/source_preflight/blind.html").write_text("<html>blocked</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/blind.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["summary"]["strategy_change_ready_count"] == 0
    assert payload["summary"]["evidence_gate_status_counts"] == {"fallback_only": 1}
    assert payload["items"][0]["evidence_gate"] == {
        "status": "fallback_only",
        "strategy_change_ready": False,
        "decision": "use_ready_fallback",
        "reason": "This status points to access control or browser environment repair, not selector/timeout tuning.",
        "evidence_fields": ["failure_report_path", "html_snapshot_path", "screenshot_path"],
        "missing_required_evidence": [],
    }


def test_build_evidence_payload_validates_optional_trace_path(tmp_path, capsys):
    report = _preflight_report()
    action_evidence = report["summary"]["problem_actions"][0]["evidence"]
    action_evidence["trace_path"] = ".tmp/traces/source-preflight-desktop.zip"
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", report)
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        _valid_failure_report(),
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["issues"][0]["code"] == "missing_trace_path"
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert "--source-preflight-trace-dir" in " ".join(payload["items"][0]["repair_commands"])

    trace_path = tmp_path / ".tmp/traces/source-preflight-desktop.zip"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_bytes(b"trace")
    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["summary"]["strategy_change_ready_count"] == 1
    assert (
        payload["items"][0]["trace_viewer_command"] == "playwright show-trace .tmp/traces/source-preflight-desktop.zip"
    )
    assert payload["items"][0]["trace_viewer_hint"] == (
        "Open the Playwright trace locally and inspect Actions, Console, Network, and DOM snapshots before changing "
        "selectors or timeouts."
    )

    _print_text_report(payload)
    text = capsys.readouterr().out
    assert "trace_viewer item=0 source=ppomppu: playwright show-trace .tmp/traces/source-preflight-desktop.zip" in text


def test_trace_viewer_command_quotes_powershell_metacharacter_path():
    assert (
        _trace_viewer_command(".tmp/traces/source&preflight.zip")
        == "playwright show-trace '.tmp/traces/source&preflight.zip'"
    )


def test_build_evidence_payload_fails_for_invalid_failure_report_metadata(tmp_path):
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", _preflight_report())
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        {
            "source": "ppomppu",
            "classification": {"status": "timeout"},
            "failure_report": {"schema_version": 2, "tool": "other"},
            "operator": {"action_required": False, "action": "", "evidence": []},
        },
    )

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    codes = {issue["code"] for issue in payload["issues"]}
    assert {
        "unexpected_schema_version",
        "unexpected_tool",
        "missing_captured_at",
        "operator_action_not_required",
        "missing_operator_action",
        "missing_operator_evidence",
    }.issubset(codes)


def test_build_evidence_payload_rejects_failure_report_without_self_reference(tmp_path):
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", _preflight_report())
    failure_report = _valid_failure_report()
    del failure_report["operator"]["evidence"]["failure_report_path"]
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        failure_report,
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert payload["issues"][0]["code"] == "operator_evidence_missing_failure_report_path"


def test_build_evidence_payload_rejects_mismatched_failure_report_self_reference(tmp_path):
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", _preflight_report())
    failure_report = _valid_failure_report()
    failure_report["operator"]["evidence"]["failure_report_path"] = ".tmp/failures/source_preflight/stale.json"
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        failure_report,
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert payload["issues"][0]["code"] == "operator_evidence_failure_report_path_mismatch"
    assert payload["issues"][0]["path"] == str(tmp_path / ".tmp/failures/source_preflight/stale.json")


def test_build_evidence_payload_rejects_mismatched_failure_report_operator_action(tmp_path):
    _write_json(tmp_path / ".tmp/source_browser_preflight.json", _preflight_report())
    failure_report = _valid_failure_report()
    failure_report["operator"]["action"] = "Use a ready fallback source for this run."
    _write_json(
        tmp_path / ".tmp/failures/source_preflight/ppomppu-timeout.json",
        failure_report,
    )
    (tmp_path / ".tmp/failures/source_preflight/ppomppu.html").write_text("<html>timeout</html>", encoding="utf-8")
    screenshot = tmp_path / "screenshots/source_preflight/ppomppu.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")

    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["summary"]["evidence_gate_status_counts"] == {"fix_evidence_first": 1}
    assert payload["issues"][0]["code"] == "operator_action_mismatch"


def test_text_report_prints_next_step(tmp_path, capsys):
    _write_json(tmp_path / "preflight.json", {"summary": {"problem_count": 0, "problem_actions": []}})
    payload = build_evidence_payload(tmp_path / "preflight.json", base_dir=tmp_path)

    _print_text_report(payload)

    text = capsys.readouterr().out
    assert "[SOURCE PREFLIGHT EVIDENCE DOCTOR]" in text
    assert "status: PASS" in text
    assert "next_step:" in text


def test_main_prints_json_payload(tmp_path, capsys):
    _write_json(tmp_path / "preflight.json", {"summary": {"problem_count": 0, "problem_actions": []}})

    exit_code = main(["--input", str(tmp_path / "preflight.json"), "--base-dir", str(tmp_path), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["summary"]["problem_action_count"] == 0


def test_build_evidence_payload_accepts_utf8_bom_json(tmp_path):
    path = tmp_path / "preflight-bom.json"
    path.write_text('\ufeff{"summary": {"problem_count": 0, "problem_actions": []}}', encoding="utf-8")

    payload = build_evidence_payload(path, base_dir=tmp_path)

    assert payload["status"] == "PASS"
    assert payload["summary"]["problem_action_count"] == 0
