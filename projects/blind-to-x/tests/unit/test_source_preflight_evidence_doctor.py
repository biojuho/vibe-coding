from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.source_preflight_evidence_doctor import (  # noqa: E402
    build_evidence_payload,
    exit_code_for_payload,
    main,
    _print_text_report,
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
                "failure_report_path": ".tmp/failures/source_preflight/ppomppu-timeout.json",
                "screenshot_path": "screenshots/source_preflight/ppomppu.png",
                "html_snapshot_path": ".tmp/failures/source_preflight/ppomppu.html",
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
    }
    assert payload["items"][0]["failure_report_status"] == "valid"
    assert exit_code_for_payload(payload) == 0


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
    assert payload["issues"][0]["code"] == "missing_failure_report_path"
    assert exit_code_for_payload(payload) == 0
    assert exit_code_for_payload(payload, fail_on_warning=True) == 1


def test_build_evidence_payload_fails_when_referenced_artifact_is_missing(tmp_path):
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
    assert payload["issues"][0]["code"] == "missing_screenshot_path"
    assert exit_code_for_payload(payload) == 2


def test_build_evidence_payload_validates_optional_trace_path(tmp_path):
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

    trace_path = tmp_path / ".tmp/traces/source-preflight-desktop.zip"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_bytes(b"trace")
    payload = build_evidence_payload(tmp_path / ".tmp/source_browser_preflight.json", base_dir=tmp_path)

    assert payload["status"] == "PASS"


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
