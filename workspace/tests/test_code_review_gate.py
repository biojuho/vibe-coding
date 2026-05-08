"""Unit tests for `execution/code_review_gate.py`.

The graph backend (`code_review_graph.tools`) is faked through the
`tools=` injection point on `evaluate(...)`, so these tests stay
deterministic and do not require a real graph build.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / "execution" / "code_review_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("code_review_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["code_review_gate"] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def _fake_tools(
    *,
    risk_score: float = 0.0,
    changed_files: list[str] | None = None,
    test_gaps: list[Any] | None = None,
    affected_flows: list[Any] | None = None,
    review_priorities: list[Any] | None = None,
    impact_payload: dict[str, Any] | None = None,
    architecture_payload: dict[str, Any] | None = None,
    detect_raises: Exception | None = None,
):
    detect_calls: list[dict[str, Any]] = []
    impact_calls: list[dict[str, Any]] = []
    architecture_calls: list[dict[str, Any]] = []

    def detect_changes_func(**kwargs):
        detect_calls.append(kwargs)
        if detect_raises is not None:
            raise detect_raises
        return {
            "risk_score": risk_score,
            "changed_files": [{"path": p} for p in (changed_files or [])],
            "test_gaps": test_gaps or [],
            "affected_flows": affected_flows or [],
            "review_priorities": review_priorities or [],
        }

    def get_impact_radius(**kwargs):
        impact_calls.append(kwargs)
        return impact_payload or {"radius": []}

    def get_architecture_overview_func(**kwargs):
        architecture_calls.append(kwargs)
        return architecture_payload or {"communities": []}

    return (
        (detect_changes_func, get_impact_radius, get_architecture_overview_func),
        {"detect": detect_calls, "impact": impact_calls, "arch": architecture_calls},
    )


def _evaluate(tmp_path: Path, tools, **kwargs):
    defaults = {
        "base": "HEAD~1",
        "repo_root": tmp_path,
        "warn_threshold": 0.3,
        "fail_threshold": 0.7,
        "include_architecture": False,
    }
    defaults.update(kwargs)
    return gate.evaluate(tools=tools, **defaults)


def test_low_risk_clean_change_passes(tmp_path):
    tools, calls = _fake_tools(risk_score=0.05, changed_files=["a.py"])
    report = _evaluate(tmp_path, tools)
    assert report.status == "pass"
    assert report.risk_score == 0.05
    assert calls["impact"] == [], "impact_radius should not be called on pass"


def test_warn_threshold_promotes_to_warn(tmp_path):
    tools, calls = _fake_tools(risk_score=0.4, changed_files=["a.py", "b.py"])
    report = _evaluate(tmp_path, tools)
    assert report.status == "warn"
    assert any("warn-threshold" in r for r in report.reasons)
    assert calls["impact"], "impact_radius should be called for warn/fail"


def test_fail_threshold_blocks(tmp_path):
    tools, _ = _fake_tools(risk_score=0.85, changed_files=["a.py"])
    report = _evaluate(tmp_path, tools)
    assert report.status == "fail"
    assert any("fail-threshold" in r for r in report.reasons)


def test_test_gaps_force_at_least_warn_even_at_low_risk(tmp_path):
    tools, _ = _fake_tools(
        risk_score=0.0,
        changed_files=["a.py"],
        test_gaps=[{"name": "do_thing", "file": "a.py"}],
    )
    report = _evaluate(tmp_path, tools)
    assert report.status == "warn"
    assert report.test_gaps == ["do_thing :: a.py"]
    assert any("test gap" in r for r in report.reasons)


def test_no_test_gaps_at_zero_risk_stays_pass(tmp_path):
    tools, _ = _fake_tools(risk_score=0.0, changed_files=["a.py"])
    report = _evaluate(tmp_path, tools)
    assert report.status == "pass"
    assert report.reasons == []


def test_architecture_overview_only_when_requested(tmp_path):
    tools, calls = _fake_tools(risk_score=0.0)
    report = _evaluate(tmp_path, tools, include_architecture=False)
    assert report.architecture_overview is None
    assert calls["arch"] == []

    tools, calls = _fake_tools(risk_score=0.0)
    report = _evaluate(tmp_path, tools, include_architecture=True)
    assert report.architecture_overview is not None
    assert calls["arch"], "architecture overview should run when requested"


def test_warn_must_be_le_fail(tmp_path):
    tools, _ = _fake_tools()
    with pytest.raises(ValueError):
        _evaluate(tmp_path, tools, warn_threshold=0.9, fail_threshold=0.5)


def test_status_to_exit_code_strict_promotes_warn():
    assert gate.status_to_exit_code("pass", strict=False) == 0
    assert gate.status_to_exit_code("pass", strict=True) == 0
    assert gate.status_to_exit_code("warn", strict=False) == 0
    assert gate.status_to_exit_code("warn", strict=True) == 1
    assert gate.status_to_exit_code("fail", strict=False) == 2
    assert gate.status_to_exit_code("fail", strict=True) == 2
    assert gate.status_to_exit_code("error", strict=False) == 3


def test_detect_changes_failure_returns_error_status(tmp_path):
    tools, _ = _fake_tools(detect_raises=RuntimeError("graph not built"))
    report = _evaluate(tmp_path, tools)
    assert report.status == "error"
    assert report.error and "graph not built" in report.error


def test_impact_radius_failure_does_not_escalate_status(tmp_path):
    detect_calls: list = []

    def detect_changes_func(**kwargs):
        detect_calls.append(kwargs)
        return {
            "risk_score": 0.5,
            "changed_files": [{"path": "a.py"}],
            "test_gaps": [],
            "affected_flows": [],
            "review_priorities": [],
        }

    def get_impact_radius(**kwargs):
        raise RuntimeError("backend offline")

    def get_architecture_overview_func(**kwargs):
        return {}

    tools = (detect_changes_func, get_impact_radius, get_architecture_overview_func)
    report = gate.evaluate(
        base="HEAD~1",
        repo_root=tmp_path,
        warn_threshold=0.3,
        fail_threshold=0.7,
        include_architecture=False,
        tools=tools,
    )
    # impact_radius failure must not push us from warn to error
    assert report.status == "warn"
    assert report.impact_radius is not None
    assert "backend offline" in (report.impact_radius.get("error") or "")


def test_render_text_includes_status_and_reasons(tmp_path):
    tools, _ = _fake_tools(
        risk_score=0.5,
        changed_files=["a.py", "b.py", "c.py", "d.py", "e.py", "f.py"],
        test_gaps=[{"name": "x", "file": "a.py"}],
    )
    report = _evaluate(tmp_path, tools)
    text = gate.render_text(report)
    assert "WARN" in text
    assert "risk=0.50" in text
    assert "+ 1 more" in text  # truncation suffix
    assert "test gaps: 1" in text


def test_to_dict_serializable(tmp_path):
    import json

    tools, _ = _fake_tools(risk_score=0.4, changed_files=["a.py"])
    report = _evaluate(tmp_path, tools)
    blob = json.dumps(report.to_dict())  # must not raise
    parsed = json.loads(blob)
    assert parsed["status"] == "warn"
    assert parsed["risk_score"] == 0.4
