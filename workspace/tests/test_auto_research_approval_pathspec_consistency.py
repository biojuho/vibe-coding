"""Unit tests for approval pathspec consistency evidence generation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "approval_pathspec_consistency.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("approval_pathspec_consistency", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["approval_pathspec_consistency"] = module
    spec.loader.exec_module(module)
    return module


approval_pathspec_consistency = _load_module()


def _write_handoff(path: Path, dirty_paths: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "dirty_signature": {
                    "input": {
                        "dirty_count": len(dirty_paths),
                        "staged": 0,
                        "dirty_paths": dirty_paths,
                    },
                },
            },
        ),
        encoding="utf-8",
    )


def test_build_report_marks_uncovered_current_dirty_paths(tmp_path: Path) -> None:
    evidence = tmp_path / ".tmp"
    evidence.mkdir()
    handoff = evidence / "handoff.json"
    _write_handoff(handoff, ["a.py", "b.py", ".ai/HANDOFF.md", "docs/runbook.md"])
    (evidence / "approve-a.pathspec").write_text("a.py\n.ai/HANDOFF.md\nclean.py\n", encoding="utf-8")

    report = approval_pathspec_consistency.build_report(
        root=tmp_path,
        handoff_json=handoff,
        pathspec_dir=evidence,
        generated_at="2026-06-11T00:00:00+00:00",
    )

    assert report["status"] == "needs_refresh"
    assert report["dirty_count"] == 4
    assert report["covered_dirty_count"] == 2
    assert report["uncovered_dirty_paths"] == ["b.py", "docs/runbook.md"]
    assert report["uncovered_non_evidence_source_count"] == 2
    assert report["extra_non_dirty_paths"] == ["clean.py"]
    assert report["pathspec_count"] == 1
    assert report["input_source"] == "dirty_handoff_signature"
    assert report["handoff_matches_live"] is None


def test_build_report_prefers_live_dirty_and_flags_stale_handoff(tmp_path: Path, monkeypatch) -> None:
    evidence = tmp_path / ".tmp"
    evidence.mkdir()
    handoff = evidence / "handoff.json"
    _write_handoff(handoff, ["a.py"])
    (evidence / "approve-current.pathspec").write_text("a.py\nb.py\n", encoding="utf-8")

    monkeypatch.setattr(approval_pathspec_consistency, "_live_dirty_paths", lambda root: ["a.py", "b.py"])
    monkeypatch.setattr(approval_pathspec_consistency, "_live_staged_paths", lambda root: [])

    report = approval_pathspec_consistency.build_report(
        root=tmp_path,
        handoff_json=handoff,
        pathspec_dir=evidence,
        generated_at="2026-06-11T00:00:00+00:00",
    )

    assert report["status"] == "stale_handoff"
    assert report["input_source"] == "live_git_dirty_paths"
    assert report["dirty_paths"] == ["a.py", "b.py"]
    assert report["dirty_count"] == 2
    assert report["covered_dirty_count"] == 2
    assert report["uncovered_dirty_count"] == 0
    assert report["handoff_dirty_count"] == 1
    assert report["live_dirty_count"] == 2
    assert report["handoff_matches_live"] is False
    assert report["handoff_only_dirty_paths"] == []
    assert report["live_only_dirty_paths"] == ["b.py"]


def test_build_report_treats_invalid_encoding_pathspec_as_empty(tmp_path: Path) -> None:
    evidence = tmp_path / ".tmp"
    evidence.mkdir()
    handoff = evidence / "handoff.json"
    _write_handoff(handoff, ["a.py"])
    (evidence / "approve-broken.pathspec").write_bytes(b"\xff")

    report = approval_pathspec_consistency.build_report(
        root=tmp_path,
        handoff_json=handoff,
        pathspec_dir=evidence,
        generated_at="2026-06-14T00:00:00+00:00",
    )

    assert report["status"] == "needs_refresh"
    assert report["pathspec_count"] == 1
    assert report["empty_pathspec_count"] == 1
    assert report["empty_pathspecs"] == ["approve-broken.pathspec"]
    assert report["uncovered_dirty_paths"] == ["a.py"]


def test_main_writes_coverage_and_combined_pathspec_without_bom(tmp_path: Path, capsys) -> None:
    evidence = tmp_path / ".tmp"
    evidence.mkdir()
    handoff = evidence / "handoff.json"
    output_json = evidence / "approval.json"
    output_md = evidence / "approval.md"
    coverage_json = evidence / "coverage.json"
    coverage_md = evidence / "coverage.md"
    combined = evidence / "combined.pathspec"
    _write_handoff(handoff, ["a.py", "b.py"])
    (evidence / "approve-a.pathspec").write_text("a.py\n", encoding="utf-8")

    code = approval_pathspec_consistency.main(
        [
            "--root",
            str(tmp_path),
            "--handoff-json",
            str(handoff),
            "--pathspec-dir",
            str(evidence),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--coverage-json",
            str(coverage_json),
            "--coverage-md",
            str(coverage_md),
            "--combined-pathspec",
            str(combined),
            "--json",
        ],
    )

    assert code == 0
    assert not output_json.read_bytes().startswith(b"\xef\xbb\xbf")
    report = json.loads(output_json.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_json.read_text(encoding="utf-8"))
    assert report["dirty_count"] == 2
    assert coverage["dirty_count"] == 2
    assert coverage["uncovered_dirty_paths"] == ["b.py"]
    assert combined.read_text(encoding="utf-8") == "a.py\n"
    assert "Dirty / covered / uncovered: `2` / `1` / `1`" in output_md.read_text(encoding="utf-8")
    assert "Dirty / covered / uncovered: `2` / `1` / `1`" in coverage_md.read_text(encoding="utf-8")
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "needs_refresh"


def test_main_reports_output_json_write_failure_without_overwriting(tmp_path: Path, capsys) -> None:
    evidence = tmp_path / ".tmp"
    evidence.mkdir()
    handoff = evidence / "handoff.json"
    output_json = evidence / "approval.json"
    output_md = evidence / "approval.md"
    coverage_json = evidence / "coverage.json"
    coverage_md = evidence / "coverage.md"
    combined = evidence / "combined.pathspec"
    _write_handoff(handoff, ["a.py", "b.py"])
    (evidence / "approve-a.pathspec").write_text("a.py\n", encoding="utf-8")
    output_json.write_text('{"status":"existing"}\n', encoding="utf-8")
    output_json.with_name(f"{output_json.name}.refresh-tmp").mkdir()

    code = approval_pathspec_consistency.main(
        [
            "--root",
            str(tmp_path),
            "--handoff-json",
            str(handoff),
            "--pathspec-dir",
            str(evidence),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--coverage-json",
            str(coverage_json),
            "--coverage-md",
            str(coverage_md),
            "--combined-pathspec",
            str(combined),
            "--json",
        ],
    )

    assert code == 4
    assert output_json.read_text(encoding="utf-8") == '{"status":"existing"}\n'
    assert not output_md.exists()
    assert not coverage_json.exists()
    assert not coverage_md.exists()
    assert not combined.exists()
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output_json.as_posix()
    assert stdout["write_error"]


def test_main_reports_blocked_output_parent_without_traceback(tmp_path: Path, capsys) -> None:
    evidence = tmp_path / ".tmp"
    evidence.mkdir()
    handoff = evidence / "handoff.json"
    blocked_parent = tmp_path / "blocked-parent"
    output_json = blocked_parent / "approval.json"
    output_md = evidence / "approval.md"
    coverage_json = evidence / "coverage.json"
    coverage_md = evidence / "coverage.md"
    combined = evidence / "combined.pathspec"
    _write_handoff(handoff, ["a.py"])
    (evidence / "approve-a.pathspec").write_text("a.py\n", encoding="utf-8")
    blocked_parent.write_text("not a directory\n", encoding="utf-8")

    code = approval_pathspec_consistency.main(
        [
            "--root",
            str(tmp_path),
            "--handoff-json",
            str(handoff),
            "--pathspec-dir",
            str(evidence),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--coverage-json",
            str(coverage_json),
            "--coverage-md",
            str(coverage_md),
            "--combined-pathspec",
            str(combined),
            "--json",
        ],
    )

    assert code == 4
    assert blocked_parent.read_text(encoding="utf-8") == "not a directory\n"
    assert not output_md.exists()
    assert not coverage_json.exists()
    assert not coverage_md.exists()
    assert not combined.exists()
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output_json.as_posix()
    assert stdout["write_error"]


def test_main_does_not_partially_write_when_late_output_parent_is_blocked(tmp_path: Path, capsys) -> None:
    evidence = tmp_path / ".tmp"
    evidence.mkdir()
    handoff = evidence / "handoff.json"
    output_json = evidence / "approval.json"
    output_md = evidence / "approval.md"
    coverage_json = evidence / "coverage.json"
    coverage_md = evidence / "coverage.md"
    blocked_parent = tmp_path / "blocked-combined"
    combined = blocked_parent / "combined.pathspec"
    _write_handoff(handoff, ["a.py"])
    (evidence / "approve-a.pathspec").write_text("a.py\n", encoding="utf-8")
    blocked_parent.write_text("not a directory\n", encoding="utf-8")

    code = approval_pathspec_consistency.main(
        [
            "--root",
            str(tmp_path),
            "--handoff-json",
            str(handoff),
            "--pathspec-dir",
            str(evidence),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--coverage-json",
            str(coverage_json),
            "--coverage-md",
            str(coverage_md),
            "--combined-pathspec",
            str(combined),
            "--json",
        ],
    )

    assert code == 4
    assert blocked_parent.read_text(encoding="utf-8") == "not a directory\n"
    assert not output_json.exists()
    assert not output_md.exists()
    assert not coverage_json.exists()
    assert not coverage_md.exists()
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == combined.as_posix()
    assert stdout["write_error"]
