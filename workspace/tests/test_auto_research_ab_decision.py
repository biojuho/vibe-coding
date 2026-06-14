"""Unit tests for the auto-research A/B decision helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "ab_decision.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ab_decision = _load_module("ab_decision_for_test", SCRIPT_PATH)


def _manifest() -> dict[str, object]:
    return {
        "baseline": {"metrics": {"resilience": 0}},
        "candidate": {"metrics": {"resilience": 1}, "gates": {"tests": True}},
        "directions": {"resilience": "higher"},
        "required_gates": ["tests"],
        "min_delta": 0.1,
    }


def test_load_json_accepts_utf8_bom_manifest(tmp_path: Path) -> None:
    path = tmp_path / "ab-manifest.json"
    path.write_text(json.dumps(_manifest()), encoding="utf-8-sig")

    result = ab_decision.decide(ab_decision._load_json(path))

    assert result["decision"] == "adopt_candidate"
    assert result["failed_gates"] == []


def test_load_json_accepts_powershell_utf16_manifest(tmp_path: Path) -> None:
    path = tmp_path / "ab-manifest.json"
    path.write_text(json.dumps(_manifest()), encoding="utf-16")

    result = ab_decision.decide(ab_decision._load_json(path))

    assert result["decision"] == "adopt_candidate"
    assert result["failed_gates"] == []


def test_load_json_reports_unreadable_manifest(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "ab-manifest.json"
    path.write_text(json.dumps(_manifest()), encoding="utf-8")
    original_read_bytes = ab_decision.Path.read_bytes

    def fake_read_bytes(read_path: Path, *args, **kwargs):
        if read_path == path:
            raise OSError("locked")
        return original_read_bytes(read_path, *args, **kwargs)

    monkeypatch.setattr(ab_decision.Path, "read_bytes", fake_read_bytes)

    with pytest.raises(SystemExit) as excinfo:
        ab_decision._load_json(path)

    assert str(excinfo.value).startswith(f"manifest unreadable: {path}:")
    assert "locked" in str(excinfo.value)


def test_metric_score_handles_direction_weights_and_zero_weight_warning() -> None:
    contributions, score_delta, warnings = ab_decision._metric_score(
        {"cost": 8.0, "noise": 5.0, "quality": 10.0},
        {"cost": 4.0, "noise": 7.0, "quality": 15.0},
        {"cost": "lower", "noise": "equal", "quality": "higher"},
        {"cost": 1.0, "noise": 0.0, "quality": 2.0},
    )

    assert score_delta == pytest.approx(0.5)
    assert warnings == ["noise has zero weight"]
    assert set(contributions) == {"cost", "quality"}
    assert contributions["cost"]["relative_delta"] == pytest.approx(0.5)
    assert contributions["quality"]["contribution"] == pytest.approx(1.0)


def test_gate_failures_separate_candidate_failures_from_baseline_warnings() -> None:
    failed_gates, warnings = ab_decision._gate_failures(
        ["tests", "lint"],
        {"tests": True},
        {"tests": False, "lint": False},
    )

    assert failed_gates == ["lint"]
    assert warnings == ["baseline failed gates: tests, lint"]


def test_decision_reason_prioritizes_failed_gate_over_positive_score() -> None:
    decision, reason = ab_decision._decision_reason(["tests"], 100.0, 0.1)

    assert decision == "reject_candidate"
    assert reason == "candidate failed required gates"


def test_cli_writes_ascii_json_artifact(tmp_path: Path, capsys) -> None:
    manifest = tmp_path / "ab-manifest.json"
    output = tmp_path / "ab-decision.json"
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")

    code = ab_decision.main([str(manifest), "--output", str(output), "--json"])
    stdout = json.loads(capsys.readouterr().out)
    persisted = json.loads(output.read_text(encoding="utf-8"))

    assert code == 0
    assert stdout["decision"] == "adopt_candidate"
    assert persisted["decision"] == "adopt_candidate"
    assert output.read_text(encoding="utf-8").isascii()


def test_cli_reports_output_write_failure_without_overwriting_existing_decision(tmp_path: Path, capsys) -> None:
    manifest = tmp_path / "ab-manifest.json"
    output = tmp_path / "ab-decision.json"
    output_tmp = output.with_name(f"{output.name}.refresh-tmp")
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")
    output.write_text('{"decision":"existing"}\n', encoding="utf-8")
    output_tmp.mkdir()

    code = ab_decision.main([str(manifest), "--output", str(output), "--json"])
    stdout = json.loads(capsys.readouterr().out)

    assert code == 4
    assert stdout["decision"] == "write_failed"
    assert stdout["write_error_path"] == output.as_posix()
    assert stdout["write_error"]
    assert output.read_text(encoding="utf-8") == '{"decision":"existing"}\n'


def test_cli_reports_output_parent_write_failure_without_traceback(tmp_path: Path, capsys) -> None:
    manifest = tmp_path / "ab-manifest.json"
    blocked_parent = tmp_path / ".tmp" / "blocked-parent"
    output = blocked_parent / "ab-decision.json"
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")
    blocked_parent.parent.mkdir(parents=True)
    blocked_parent.write_text("blocking file\n", encoding="utf-8")

    code = ab_decision.main([str(manifest), "--output", str(output), "--json"])
    stdout = json.loads(capsys.readouterr().out)

    assert code == 4
    assert stdout["decision"] == "write_failed"
    assert stdout["write_error_path"] == output.as_posix()
    assert "FileExistsError" in stdout["write_error"] or "NotADirectoryError" in stdout["write_error"]
    assert blocked_parent.read_text(encoding="utf-8") == "blocking file\n"
