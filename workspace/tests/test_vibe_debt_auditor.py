"""Tests for the VibeDebt Auditor engine."""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.vibe_debt_auditor import (
    FunctionInfo,
    analyze_python_file,
    detect_duplicate_blocks,
    find_debt_markers,
    run_audit,
    scan_file,
    score_complexity,
    score_debt_markers,
    score_duplication,
    score_modularity,
    score_test_gap,
    summarize_project,
)
from execution.debt_history_db import DebtHistoryDB


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_py(tmp_path: Path) -> Path:
    """A small, clean Python file."""
    f = tmp_path / "clean.py"
    f.write_text(
        textwrap.dedent("""\
        def add(a, b):
            return a + b

        def multiply(a, b):
            return a * b
    """)
    )
    return f


@pytest.fixture
def complex_py(tmp_path: Path) -> Path:
    """A Python file with high complexity."""
    lines = ["def process(data):"]
    for i in range(25):
        lines.append(f'    if data.get("k{i}"):')
        lines.append(f'        x{i} = data["k{i}"] * {i}')
    lines.append("    return data")
    f = tmp_path / "complex.py"
    f.write_text("\n".join(lines))
    return f


@pytest.fixture
def debt_marker_py(tmp_path: Path) -> Path:
    """A file with debt markers."""
    f = tmp_path / "marked.py"
    f.write_text(
        textwrap.dedent("""\
        # TODO: refactor this
        def old_func():
            pass  # FIXME: broken logic

        # HACK: temporary workaround
        x = 1
        # XXX: needs review
    """)
    )
    return f


@pytest.fixture
def duplicate_py(tmp_path: Path) -> Path:
    """A file with duplicate blocks."""
    block = textwrap.dedent("""\
        result = []
        for item in data:
            if item.get("active"):
                result.append(item["name"])
                result.append(item["value"])
                result.append(item["id"])
    """)
    f = tmp_path / "duped.py"
    f.write_text(
        f"def func_a(data):\n{textwrap.indent(block, '    ')}\n\ndef func_b(data):\n{textwrap.indent(block, '    ')}\n"
    )
    return f


@pytest.fixture
def history_db(tmp_path: Path) -> DebtHistoryDB:
    return DebtHistoryDB(db_path=tmp_path / "test_debt.db")


# ---------------------------------------------------------------------------
# AST analysis tests
# ---------------------------------------------------------------------------


class TestAstAnalysis:
    def test_analyze_clean_file(self, simple_py: Path):
        functions, total, code, imports = analyze_python_file(simple_py)
        assert len(functions) == 2
        assert total > 0
        assert code > 0
        assert all(f.complexity == 1 for f in functions)

    def test_analyze_complex_file(self, complex_py: Path):
        functions, total, code, imports = analyze_python_file(complex_py)
        assert len(functions) == 1
        assert functions[0].complexity > 10

    def test_analyze_nonexistent(self, tmp_path: Path):
        functions, total, code, imports = analyze_python_file(tmp_path / "nope.py")
        assert functions == []
        assert total == 0

    def test_analyze_syntax_error(self, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n    pass")
        functions, total, code, imports = analyze_python_file(f)
        assert functions == []
        assert total > 0  # lines still counted


# ---------------------------------------------------------------------------
# Debt marker tests
# ---------------------------------------------------------------------------


class TestDebtMarkers:
    def test_find_markers(self, debt_marker_py: Path):
        markers = find_debt_markers(debt_marker_py)
        assert len(markers) == 4
        types = {m["type"] for m in markers}
        assert types == {"TODO", "FIXME", "HACK", "XXX"}

    def test_no_markers_in_clean(self, simple_py: Path):
        markers = find_debt_markers(simple_py)
        assert len(markers) == 0


# ---------------------------------------------------------------------------
# Duplication tests
# ---------------------------------------------------------------------------


class TestDuplication:
    def test_detect_duplicates(self, duplicate_py: Path):
        count = detect_duplicate_blocks(duplicate_py)
        assert count > 0

    def test_no_duplicates_in_clean(self, simple_py: Path):
        count = detect_duplicate_blocks(simple_py)
        assert count == 0


# ---------------------------------------------------------------------------
# Scoring dimension tests
# ---------------------------------------------------------------------------


class TestScoring:
    def test_complexity_score_clean(self):
        funcs = [FunctionInfo("f", 1, 5, 2)]
        score = score_complexity(funcs, 10)
        assert 0 <= score <= 30  # low complexity

    def test_complexity_score_high(self):
        funcs = [FunctionInfo("f", 1, 200, 25)]
        score = score_complexity(funcs, 200)
        assert score >= 70  # high complexity

    def test_complexity_score_empty(self):
        assert score_complexity([], 0) == 0.0

    def test_duplication_score_zero(self):
        assert score_duplication(0, 100) == 0.0

    def test_duplication_score_high(self):
        score = score_duplication(20, 100)
        assert score > 50

    def test_debt_markers_score_zero(self):
        assert score_debt_markers(0, 100) == 0.0

    def test_debt_markers_score_high(self):
        score = score_debt_markers(10, 100)
        assert score > 50

    def test_modularity_score_small(self):
        score = score_modularity(50, 5)
        assert score < 30

    def test_modularity_score_large(self):
        score = score_modularity(1200, 35)
        assert score > 50

    def test_test_gap_finds_later_parent_test_directory(self, tmp_path: Path):
        target = tmp_path / "workspace" / "execution" / "pages" / "shorts_manager.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def render():\n    return 1\n", encoding="utf-8")

        nested_tests = tmp_path / "workspace" / "execution" / "tests"
        nested_tests.mkdir(parents=True, exist_ok=True)
        outer_test = tmp_path / "workspace" / "tests" / "test_shorts_manager.py"
        outer_test.parent.mkdir(parents=True, exist_ok=True)
        outer_test.write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")

        assert score_test_gap(target, "workspace") == 15.0


# ---------------------------------------------------------------------------
# Full file scan tests
# ---------------------------------------------------------------------------


class TestScanFile:
    def test_scan_clean_file(self, simple_py: Path):
        result = scan_file(simple_py, "test", set())
        assert result.total_score < 40
        assert result.principal_minutes >= 0
        assert result.function_count == 2

    def test_scan_complex_file(self, complex_py: Path):
        result = scan_file(complex_py, "test", set())
        assert result.total_score > result.complexity_score * 0.2
        assert result.max_complexity > 10

    def test_scan_mapped_file_lower_doc_score(self, simple_py: Path):
        mapped = scan_file(simple_py, "test", {"clean.py"})
        unmapped = scan_file(simple_py, "test", set())
        assert mapped.doc_sync_score <= unmapped.doc_sync_score


# ---------------------------------------------------------------------------
# Project summary tests
# ---------------------------------------------------------------------------


class TestProjectSummary:
    def test_summary_basic(self, simple_py: Path):
        scores = [scan_file(simple_py, "test", set())]
        summary = summarize_project("test", scores)
        assert summary.name == "test"
        assert summary.file_count == 1
        assert summary.tdr_grade in ("GREEN", "YELLOW", "RED")

    def test_summary_empty(self):
        summary = summarize_project("empty", [])
        assert summary.file_count == 0
        assert summary.avg_score == 0.0


# ---------------------------------------------------------------------------
# Integration: full audit on workspace
# ---------------------------------------------------------------------------


class TestFullAudit:
    def test_run_audit_workspace(self):
        result = run_audit(project_filter="workspace")
        assert result.total_files > 0
        assert result.overall_tdr >= 0
        assert result.overall_grade in ("GREEN", "YELLOW", "RED")
        assert len(result.projects) == 1
        assert result.projects[0].name == "workspace"

    def test_audit_result_serializable(self):
        from dataclasses import asdict

        result = run_audit(project_filter="workspace")
        data = asdict(result)
        json_str = json.dumps(data, ensure_ascii=False)
        assert len(json_str) > 100


# ---------------------------------------------------------------------------
# History DB tests
# ---------------------------------------------------------------------------


class TestDebtHistoryDB:
    def test_record_and_retrieve(self, history_db: DebtHistoryDB):
        result = run_audit(project_filter="workspace")
        audit_id = history_db.record_audit(result)
        assert audit_id >= 1

        trend = history_db.get_trend_data(days=1)
        assert len(trend) >= 1
        assert trend[0]["overall_tdr"] == result.overall_tdr

    def test_project_trend(self, history_db: DebtHistoryDB):
        result = run_audit(project_filter="workspace")
        history_db.record_audit(result)

        trend = history_db.get_project_trend("workspace", days=1)
        assert len(trend) >= 1

    def test_top_debtors(self, history_db: DebtHistoryDB):
        result = run_audit(project_filter="workspace")
        history_db.record_audit(result)

        debtors = history_db.get_latest_top_debtors()
        assert isinstance(debtors, list)

    def test_consecutive_increases_not_enough_data(self, history_db: DebtHistoryDB):
        assert history_db.get_consecutive_increases() is False

    def test_consecutive_increases_detection(self, history_db: DebtHistoryDB):
        result = run_audit(project_filter="workspace")
        # Record multiple times (same data, but tests the detection logic)
        for _ in range(5):
            history_db.record_audit(result)
        # Same TDR each time = not increasing
        assert history_db.get_consecutive_increases() is False
