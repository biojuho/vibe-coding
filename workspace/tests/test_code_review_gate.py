"""Unit tests for `execution/code_review_gate.py`.

The graph backend (`code_review_graph.tools`) is faked through the
`tools=` injection point on `evaluate(...)`, so these tests stay
deterministic and do not require a real graph build.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from execution.code_review_gate import (
    _allows_unqualified_test_source,
    _change_analysis,
    _changed_python_test_paths,
    _correct_risk_score,
    _detect_kwargs,
    _dynamic_module_aliases,
    _filter_test_gaps,
    _gate_status,
    _has_tested_source,
    _load_changed_test_mentions,
    _load_tested_sources,
    _looks_like_test_node,
    _looks_like_test_path,
    _parse_python_source,
    _tested_source_keys,
    _test_mentions_from_tree,
    _print_report,
    evaluate,
    filter_graph_relevant_files,
    get_staged_files,
    get_untracked_files,
    is_graph_relevant_file,
    render_text,
    status_to_exit_code,
)

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
    changed_functions: list[Any] | None = None,
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
            "changed_functions": changed_functions or [],
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


def test_detect_kwargs_uses_base_or_explicit_changed_files(tmp_path):
    assert _detect_kwargs(
        base="HEAD~1",
        repo_root=tmp_path,
        detail_level="standard",
        changed_files=None,
    ) == {"repo_root": str(tmp_path), "detail_level": "standard", "base": "HEAD~1"}

    assert _detect_kwargs(
        base="HEAD~1",
        repo_root=tmp_path,
        detail_level="brief",
        changed_files=["a.py"],
    ) == {"repo_root": str(tmp_path), "detail_level": "brief", "changed_files": ["a.py"]}


def test_change_analysis_normalizes_graph_result_summary(tmp_path):
    analysis = _change_analysis(
        {
            "risk_score": 0.4,
            "changed_files": [{"path": "a.py"}, "b.py", {"other": "ignored"}],
            "test_gaps": [{"name": "do_thing", "file": "a.py"}],
            "affected_flows": [{"name": "flow-a"}, "flow-b", {"name": ""}],
            "review_priorities": ["inspect a.py"],
        },
        repo_root=tmp_path,
    )

    assert analysis.risk_score == 0.4
    assert analysis.changed_files == ["a.py", "b.py"]
    assert analysis.affected_flows == ["flow-a", "flow-b"]
    assert analysis.test_gaps == ["do_thing :: a.py"]
    assert analysis.review_priorities == ["inspect a.py"]


def test_gate_status_combines_risk_gap_and_untracked_reasons():
    status, reasons = _gate_status(
        risk_score=0.8,
        warn_threshold=0.3,
        fail_threshold=0.7,
        test_gaps=["do_thing :: a.py"],
        untracked_graph_files=["execution/new_gate.py"],
    )

    assert status == "fail"
    assert "fail-threshold" in reasons[0]
    assert "test gap" in reasons[1]
    assert "untracked graph-relevant" in reasons[2]


def test_low_risk_clean_change_passes(tmp_path):
    tools, calls = _fake_tools(risk_score=0.05, changed_files=["a.py"])
    report = _evaluate(tmp_path, tools)
    assert report.status == "pass"
    assert report.risk_score == 0.05
    assert calls["impact"] == [], "impact_radius should not be called on pass"


def test_evaluate_direct_import_path_passes_clean_change(tmp_path):
    tools, _ = _fake_tools(risk_score=0.05, changed_files=["a.py"])
    report = evaluate(
        base="HEAD~1",
        repo_root=tmp_path,
        warn_threshold=0.3,
        fail_threshold=0.7,
        include_architecture=False,
        tools=tools,
    )
    assert report.status == "pass"


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


def test_outgoing_tested_by_edges_clear_false_gap_and_correct_risk(tmp_path):
    import sqlite3

    qname = str(tmp_path / "src" / "app.py") + "::do_thing"
    graph_dir = tmp_path / ".code-review-graph"
    graph_dir.mkdir()
    with sqlite3.connect(graph_dir / "graph.db") as conn:
        conn.execute("CREATE TABLE edges (kind TEXT, source_qualified TEXT, target_qualified TEXT)")
        conn.execute(
            "INSERT INTO edges VALUES ('TESTED_BY', ?, ?)",
            (qname, str(tmp_path / "tests" / "test_app.py") + "::test_do_thing"),
        )

    tested_sources = _load_tested_sources(tmp_path)
    assert qname in tested_sources
    raw_gap = {
        "name": "do_thing",
        "qualified_name": qname,
        "file": str(tmp_path / "src" / "app.py"),
    }
    assert _filter_test_gaps([raw_gap], tested_sources=tested_sources) == []
    assert (
        _correct_risk_score(
            {
                "changed_functions": [
                    {
                        "name": "do_thing",
                        "qualified_name": qname,
                        "file_path": str(tmp_path / "src" / "app.py"),
                        "risk_score": 0.35,
                    }
                ],
            },
            raw_gap_qnames={qname},
            tested_sources=tested_sources,
        )
        == 0.1
    )
    assert (
        _correct_risk_score(
            {
                "affected_flows": [],
                "changed_functions": [
                    {
                        "name": "do_thing",
                        "qualified_name": qname,
                        "file_path": str(tmp_path / "src" / "app.py"),
                        "risk_score": 0.35,
                    }
                ],
            },
            raw_gap_qnames={qname},
            tested_sources=tested_sources,
            filtered_gap_count=0,
        )
        == 0.05
    )

    tools, _ = _fake_tools(
        risk_score=0.35,
        changed_files=["src/app.py"],
        changed_functions=[
            {
                "name": "do_thing",
                "qualified_name": qname,
                "file_path": str(tmp_path / "src" / "app.py"),
                "risk_score": 0.35,
            }
        ],
        test_gaps=[raw_gap],
    )

    report = _evaluate(tmp_path, tools)

    assert report.status == "pass"
    assert report.risk_score == 0.05
    assert report.test_gaps == []


def test_unqualified_hidden_script_test_edges_clear_false_gap_and_correct_risk(tmp_path):
    import sqlite3

    path = tmp_path / ".agents" / "skills" / "auto-research" / "scripts" / "next_experiment_selector.py"
    qname = str(path) + "::_github_candidate"
    graph_dir = tmp_path / ".code-review-graph"
    graph_dir.mkdir()
    with sqlite3.connect(graph_dir / "graph.db") as conn:
        conn.execute("CREATE TABLE edges (kind TEXT, source_qualified TEXT, target_qualified TEXT)")
        conn.execute(
            "INSERT INTO edges VALUES ('TESTED_BY', ?, ?)",
            ("_github_candidate", str(tmp_path / "tests" / "test_selector.py") + "::test_candidate"),
        )

    tested_sources = _load_tested_sources(tmp_path)
    raw_gap = {"name": "_github_candidate", "qualified_name": qname, "file": str(path)}
    assert _allows_unqualified_test_source(str(path))
    assert "_github_candidate" in _tested_source_keys("_github_candidate", str(path), qname)
    assert _has_tested_source("_github_candidate", str(path), qname, tested_sources)
    assert _filter_test_gaps([raw_gap], tested_sources=tested_sources) == []
    assert (
        _correct_risk_score(
            {
                "changed_functions": [
                    {
                        "name": "_github_candidate",
                        "qualified_name": qname,
                        "file_path": str(path),
                        "risk_score": 0.35,
                    }
                ],
            },
            raw_gap_qnames={qname},
            tested_sources=tested_sources,
        )
        == 0.1
    )


def test_unqualified_non_hidden_script_test_edges_are_not_enough(tmp_path):
    path = tmp_path / "src" / "app.py"
    qname = str(path) + "::do_thing"
    tested_sources = {"do_thing"}
    raw_gap = {"name": "do_thing", "qualified_name": qname, "file": str(path)}

    assert not _allows_unqualified_test_source(str(path))
    assert "do_thing" not in _tested_source_keys("do_thing", str(path), qname)
    assert not _has_tested_source("do_thing", str(path), qname, tested_sources)
    assert _filter_test_gaps([raw_gap], tested_sources=tested_sources) == [raw_gap]


def test_unqualified_streamlit_page_test_edges_clear_false_gap(tmp_path):
    path = tmp_path / "workspace" / "execution" / "pages" / "github_dashboard.py"
    qname = str(path) + "::_render_release_boundary"
    tested_sources = {"_render_release_boundary"}
    raw_gap = {"name": "_render_release_boundary", "qualified_name": qname, "file": str(path)}

    assert _allows_unqualified_test_source(str(path))
    assert _has_tested_source("_render_release_boundary", str(path), qname, tested_sources)
    assert _filter_test_gaps([raw_gap], tested_sources=tested_sources) == []


def test_changed_test_attribute_mentions_clear_dynamic_script_false_gap(tmp_path):
    source_path = tmp_path / ".agents" / "skills" / "auto-research" / "scripts" / "debug_loop_inventory.py"
    test_path = tmp_path / "workspace" / "tests" / "test_auto_research_debug_loop_inventory.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text(
        "\n".join(
            [
                "def test_helper_contract(debug_loop_inventory):",
                "    assert debug_loop_inventory._has_input_error({'_input_error': {}})",
            ]
        ),
        encoding="utf-8",
    )

    changed_files = [
        ".agents/skills/auto-research/scripts/debug_loop_inventory.py",
        "workspace/tests/test_auto_research_debug_loop_inventory.py",
    ]
    qname = str(source_path) + "::_has_input_error"
    raw_gap = {
        "name": "_has_input_error",
        "qualified_name": qname,
        "file": str(source_path),
    }

    mentions = _load_changed_test_mentions(tmp_path, changed_files)
    assert "_has_input_error" in mentions
    assert _has_tested_source("_has_input_error", str(source_path), qname, mentions)
    assert _filter_test_gaps([raw_gap], tested_sources=mentions) == []

    tools, _ = _fake_tools(
        risk_score=0.55,
        changed_files=changed_files,
        test_gaps=[raw_gap],
    )
    report = _evaluate(tmp_path, tools)

    assert report.status == "pass"
    assert report.risk_score == 0.0
    assert report.test_gaps == []


def test_changed_test_import_mentions_use_original_private_name(tmp_path):
    test_path = tmp_path / "workspace" / "tests" / "test_gate.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text(
        "from execution.code_review_gate import _load_changed_test_mentions as subject\n",
        encoding="utf-8",
    )

    mentions = _load_changed_test_mentions(tmp_path, ["workspace/tests/test_gate.py"])

    assert "_load_changed_test_mentions" in mentions
    assert "subject" not in mentions


def test_changed_python_test_paths_filter_to_existing_python_tests(tmp_path):
    test_path = tmp_path / "workspace" / "tests" / "test_gate.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("def test_gate():\n    pass\n", encoding="utf-8")
    helper_path = tmp_path / "workspace" / "tests" / "helper.txt"
    helper_path.write_text("not python\n", encoding="utf-8")

    paths = _changed_python_test_paths(
        tmp_path,
        [
            "src/app.py",
            "workspace/tests/test_gate.py",
            "workspace/tests/helper.txt",
            "workspace/tests/missing_test.py",
        ],
    )

    assert paths == [test_path]


def test_parse_python_source_returns_none_for_invalid_test_file(tmp_path):
    test_path = tmp_path / "workspace" / "tests" / "test_gate.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("def broken(:\n", encoding="utf-8")

    assert _parse_python_source(test_path) is None


def test_changed_test_mentions_include_public_dynamic_script_helpers(tmp_path):
    source_path = tmp_path / ".agents" / "skills" / "auto-research" / "scripts" / "debug_loop_inventory.py"
    test_path = tmp_path / "workspace" / "tests" / "test_auto_research_debug_loop_inventory.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text(
        "\n".join(
            [
                "def _load_module():",
                "    return object()",
                "",
                "debug_loop_inventory = _load_module()",
                "",
                "def test_completion_gate():",
                "    assert debug_loop_inventory.completion_is_blocked({'summary': {}})",
            ]
        ),
        encoding="utf-8",
    )
    changed_files = [
        ".agents/skills/auto-research/scripts/debug_loop_inventory.py",
        "workspace/tests/test_auto_research_debug_loop_inventory.py",
    ]
    qname = str(source_path) + "::completion_is_blocked"
    raw_gap = {
        "name": "completion_is_blocked",
        "qualified_name": qname,
        "file": str(source_path),
    }

    mentions = _load_changed_test_mentions(tmp_path, changed_files)

    assert "completion_is_blocked" in mentions
    assert _has_tested_source("completion_is_blocked", str(source_path), qname, mentions)
    assert _filter_test_gaps([raw_gap], tested_sources=mentions) == []


def test_test_mentions_from_tree_combines_dynamic_alias_and_private_imports():
    tree = ast.parse(
        "\n".join(
            [
                "from execution.code_review_gate import _filter_test_gaps as subject",
                "",
                "debug_loop_inventory = _load_module()",
                "gate = _load_gate()",
                "",
                "def test_contract():",
                "    assert debug_loop_inventory.completion_is_blocked({})",
                "    assert gate.evaluate({})",
                "    assert subject",
            ]
        )
    )

    assert _dynamic_module_aliases(tree) == {"debug_loop_inventory", "gate"}
    assert _test_mentions_from_tree(tree) == {"completion_is_blocked", "evaluate", "_filter_test_gaps"}


def test_covered_non_gap_functions_are_damped_only_in_filtered_gap_runs(tmp_path):
    source_path = tmp_path / "execution" / "code_review_gate.py"
    qname = str(source_path) + "::_load_changed_test_mentions"
    raw_gap_qname = str(source_path) + "::_other_helper"
    changed = {
        "affected_flows": [],
        "changed_functions": [
            {
                "name": "_load_changed_test_mentions",
                "qualified_name": qname,
                "file_path": str(source_path),
                "risk_score": 0.4,
            }
        ],
    }

    assert (
        _correct_risk_score(
            changed,
            raw_gap_qnames={raw_gap_qname},
            tested_sources={qname},
            filtered_gap_count=0,
        )
        == 0.05
    )
    assert (
        _correct_risk_score(
            changed,
            raw_gap_qnames={raw_gap_qname},
            tested_sources={qname},
            filtered_gap_count=1,
        )
        == 0.4
    )
    assert (
        _correct_risk_score(
            changed,
            raw_gap_qnames={raw_gap_qname},
            tested_sources=set(),
            filtered_gap_count=0,
        )
        == 0.4
    )


def test_changed_test_mentions_do_not_clear_ordinary_source_false_gap(tmp_path):
    source_path = tmp_path / "src" / "app.py"
    test_path = tmp_path / "workspace" / "tests" / "test_app.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("def test_app(app):\n    app._helper()\n", encoding="utf-8")
    changed_files = ["src/app.py", "workspace/tests/test_app.py"]
    qname = str(source_path) + "::_helper"
    raw_gap = {"name": "_helper", "qualified_name": qname, "file": str(source_path)}

    mentions = _load_changed_test_mentions(tmp_path, changed_files)

    assert "_helper" in mentions
    assert not _has_tested_source("_helper", str(source_path), qname, mentions)
    assert _filter_test_gaps([raw_gap], tested_sources=mentions) == [raw_gap]


def test_test_nodes_are_not_reported_as_production_gaps(tmp_path):
    test_path = str(tmp_path / "tests" / "test_app.py")
    assert _looks_like_test_path(test_path)
    assert _looks_like_test_node("TestThing", test_path)

    tools, _ = _fake_tools(
        risk_score=0.3,
        changed_files=["tests/test_app.py"],
        changed_functions=[
            {
                "name": "TestThing",
                "qualified_name": test_path + "::TestThing",
                "file_path": test_path,
                "risk_score": 0.3,
            }
        ],
        test_gaps=[
            {
                "name": "TestThing",
                "qualified_name": test_path + "::TestThing",
                "file": test_path,
            }
        ],
    )

    report = _evaluate(tmp_path, tools)

    assert report.status == "pass"
    assert report.risk_score == 0.0
    assert report.test_gaps == []


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
    assert status_to_exit_code("pass", strict=False) == 0
    assert status_to_exit_code("pass", strict=True) == 0
    assert status_to_exit_code("warn", strict=False) == 0
    assert status_to_exit_code("warn", strict=True) == 1
    assert status_to_exit_code("fail", strict=False) == 2
    assert status_to_exit_code("fail", strict=True) == 2
    assert status_to_exit_code("error", strict=False) == 3


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
    text = render_text(report)
    assert "WARN" in text
    assert "risk=0.50" in text
    assert "+ 1 more" in text  # truncation suffix
    assert "test gaps: 1" in text


def test_trivial_pass_report_and_print_report(capsys):
    report = gate._trivial_pass_report(warn_threshold=0.3, fail_threshold=0.7, reasons=["docs-only"])
    assert report.status == "pass"
    assert report.reasons == ["docs-only"]

    _print_report(report, as_json=False, text_override="custom pass")
    assert capsys.readouterr().out == "custom pass\n"

    _print_report(report, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["reasons"] == ["docs-only"]


def test_to_dict_serializable(tmp_path):
    import json

    tools, _ = _fake_tools(risk_score=0.4, changed_files=["a.py"])
    report = _evaluate(tmp_path, tools)
    blob = json.dumps(report.to_dict())  # must not raise
    parsed = json.loads(blob)
    assert parsed["status"] == "warn"
    assert parsed["risk_score"] == 0.4


def test_evaluate_with_explicit_changed_files_bypasses_base(tmp_path):
    """When `changed_files` is provided, detect_changes is called with it (not `base`)."""
    tools, calls = _fake_tools(risk_score=0.0, changed_files=["a.py"])
    _evaluate(tmp_path, tools, changed_files=["a.py", "b.py"])
    assert len(calls["detect"]) == 1
    detect_kwargs = calls["detect"][0]
    assert detect_kwargs.get("changed_files") == ["a.py", "b.py"]
    assert "base" not in detect_kwargs, "base must not be passed when changed_files is provided"


def test_evaluate_without_changed_files_passes_base(tmp_path):
    """Default behavior still passes `base` (not `changed_files`) to detect_changes."""
    tools, calls = _fake_tools(risk_score=0.0)
    _evaluate(tmp_path, tools)
    detect_kwargs = calls["detect"][0]
    assert detect_kwargs.get("base") == "HEAD~1"
    assert "changed_files" not in detect_kwargs


def test_get_staged_files_returns_list(tmp_path, monkeypatch):
    """get_staged_files invokes git and returns clean lines."""
    import subprocess

    class FakeCompleted:
        returncode = 0
        stdout = "a.py\nb/c.py\n\n  \n"

    def fake_run(*args, **kwargs):
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["errors"] == "replace"
        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_staged_files(tmp_path)
    assert result == ["a.py", "b/c.py"]


def test_get_staged_files_returns_empty_on_git_failure(tmp_path, monkeypatch):
    """If git invocation fails or returns nonzero, return an empty list."""
    import subprocess

    class FakeCompleted:
        returncode = 128
        stdout = "fatal: not a git repository"

    def fake_run(*args, **kwargs):
        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert get_staged_files(tmp_path) == []


def test_get_staged_files_handles_missing_git_binary(tmp_path, monkeypatch):
    """When git is not installed, return an empty list instead of raising."""
    import subprocess

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("git not on PATH")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert get_staged_files(tmp_path) == []


def test_get_untracked_files_returns_list(tmp_path, monkeypatch):
    """get_untracked_files invokes git and returns clean lines."""
    import subprocess

    class FakeCompleted:
        returncode = 0
        stdout = "execution/new_gate.py\nREADME.md\n\n  \n"

    def fake_run(*args, **kwargs):
        assert args[0] == ["git", "ls-files", "--others", "--exclude-standard"]
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["errors"] == "replace"
        assert kwargs["cwd"] == str(tmp_path)
        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_untracked_files(tmp_path)
    assert result == ["execution/new_gate.py", "README.md"]


def test_get_untracked_files_returns_empty_on_git_failure(tmp_path, monkeypatch):
    """If git invocation fails or returns nonzero, return an empty list."""
    import subprocess

    class FakeCompleted:
        returncode = 128
        stdout = "fatal: not a git repository"

    def fake_run(*args, **kwargs):
        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert get_untracked_files(tmp_path) == []


def test_evaluate_warns_for_untracked_graph_relevant_files(tmp_path):
    tools, _ = _fake_tools(risk_score=0.0, changed_files=[])
    report = _evaluate(
        tmp_path,
        tools,
        untracked_files=["execution/new_gate.py", "README.md"],
    )

    assert report.status == "warn"
    assert report.risk_score == 0.0
    assert report.untracked_files == ["execution/new_gate.py"]
    assert any("untracked graph-relevant" in reason for reason in report.reasons)


def test_filter_graph_relevant_files_skips_docs_only_paths():
    assert is_graph_relevant_file("execution/code_review_gate.py")

    result = filter_graph_relevant_files(
        [
            ".ai/HANDOFF.md",
            "workspace/directives/api_monitoring.md",
            "execution/code_review_gate.py",
            "projects/app/package.json",
            ".githooks/pre-commit",
            "README.md",
        ]
    )
    assert result == [
        "execution/code_review_gate.py",
        "projects/app/package.json",
        ".githooks/pre-commit",
    ]


def test_main_staged_docs_only_skips_graph(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gate, "get_staged_files", lambda repo_root: [".ai/HANDOFF.md"])

    def fail_evaluate(**kwargs):
        raise AssertionError("docs-only staged changes must not call evaluate")

    monkeypatch.setattr(gate, "evaluate", fail_evaluate)

    exit_code = gate.main(["--staged", "--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert "no staged code files" in capsys.readouterr().out


def test_main_staged_filters_docs_before_evaluate(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        gate,
        "get_staged_files",
        lambda repo_root: [".ai/HANDOFF.md", "execution/code_review_gate.py"],
    )

    def fake_evaluate(**kwargs):
        seen.update(kwargs)
        return gate.GateReport(
            status="pass",
            risk_score=0.0,
            warn_threshold=kwargs["warn_threshold"],
            fail_threshold=kwargs["fail_threshold"],
            changed_files=kwargs["changed_files"],
            affected_flows=[],
            test_gaps=[],
            review_priorities=[],
        )

    monkeypatch.setattr(gate, "evaluate", fake_evaluate)

    assert gate.main(["--staged", "--repo-root", str(tmp_path)]) == 0
    assert seen["changed_files"] == ["execution/code_review_gate.py"]
    assert seen["untracked_files"] is None


def test_main_default_filters_untracked_files_before_evaluate(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        gate,
        "get_untracked_files",
        lambda repo_root: ["README.md", "execution/code_review_gate.py"],
    )

    def fake_evaluate(**kwargs):
        seen.update(kwargs)
        return gate.GateReport(
            status="pass",
            risk_score=0.0,
            warn_threshold=kwargs["warn_threshold"],
            fail_threshold=kwargs["fail_threshold"],
            changed_files=[],
            affected_flows=[],
            test_gaps=[],
            review_priorities=[],
            untracked_files=kwargs["untracked_files"],
        )

    monkeypatch.setattr(gate, "evaluate", fake_evaluate)

    assert gate.main(["--repo-root", str(tmp_path)]) == 0
    assert seen["untracked_files"] == ["execution/code_review_gate.py"]


def test_main_retries_import_error_with_py313_on_windows(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gate.sys, "platform", "win32")
    monkeypatch.delenv("CODE_REVIEW_GATE_PY313_FALLBACK", raising=False)
    monkeypatch.setattr(gate, "get_untracked_files", lambda repo_root: [])

    def fake_evaluate(**kwargs):
        return gate.GateReport(
            status="error",
            risk_score=0.0,
            warn_threshold=kwargs["warn_threshold"],
            fail_threshold=kwargs["fail_threshold"],
            changed_files=[],
            affected_flows=[],
            test_gaps=[],
            review_priorities=[],
            error="code_review_graph is not importable from this Python interpreter.",
        )

    seen = {}

    def fake_run_py313(argv):
        seen["argv"] = list(argv)
        print('{"status": "pass"}')
        return 0

    monkeypatch.setattr(gate, "evaluate", fake_evaluate)
    monkeypatch.setattr(gate, "_run_py313_fallback", fake_run_py313)

    exit_code = gate.main(["--repo-root", str(tmp_path), "--json"])

    assert exit_code == 0
    assert seen["argv"] == ["--repo-root", str(tmp_path), "--json"]
    assert capsys.readouterr().out == '{"status": "pass"}\n'
