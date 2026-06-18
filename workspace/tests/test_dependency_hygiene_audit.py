"""Unit tests for `execution/dependency_hygiene_audit.py`.

deptry itself is never invoked: the subprocess boundary is mocked so the suite
runs deterministically in CI without deptry installed and without scanning the
real monorepo.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "execution" / "dependency_hygiene_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("dependency_hygiene_audit", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["dependency_hygiene_audit"] = module
    spec.loader.exec_module(module)
    return module


dha = _load_module()


def _finding(code: str, module: str, file: str = "pkg/mod.py", line: int = 1) -> dict:
    return {"code": code, "module": module, "message": f"{module} {code}", "file": file, "line": line}


# ── summarize() ───────────────────────────────────────────────────────────────


def test_summarize_counts_by_code_and_module():
    results = [
        {"project": "a", "success": True, "findings": [_finding("DEP001", "redis"), _finding("DEP003", "numpy")]},
        {"project": "b", "success": True, "findings": [_finding("DEP001", "redis")]},
    ]
    summary = dha.summarize(results)
    assert summary["total_findings"] == 3
    assert summary["by_code"] == {"DEP001": 2, "DEP003": 1}
    assert summary["by_module"]["redis"] == 2
    assert summary["projects_scanned"] == 2
    assert summary["failed_projects"] == []


def test_summarize_tracks_failed_projects_separately():
    results = [
        {"project": "ok", "success": True, "findings": [_finding("DEP002", "ddgs")]},
        {"project": "broken", "success": False, "error": "boom", "findings": []},
    ]
    summary = dha.summarize(results)
    assert summary["total_findings"] == 1
    assert summary["failed_projects"] == ["broken"]
    assert summary["projects_scanned"] == 1


# ── severity / build_json() ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code,severity",
    [("DEP001", "high"), ("DEP002", "low"), ("DEP003", "medium"), ("DEP004", "low"), ("DEP999", "low")],
)
def test_severity_mapping(code, severity):
    assert dha._severity_for(code) == severity


def test_build_json_enriches_with_severity_and_label():
    results = [{"project": "a", "success": True, "findings": [_finding("DEP001", "redis")]}]
    summary = dha.summarize(results)
    payload = dha.build_json(results, summary)
    assert payload["schema"] == "dependency_hygiene_audit.v1"
    assert payload["tool"] == "deptry"
    finding = payload["projects"][0]["findings"][0]
    assert finding["severity"] == "high"
    assert finding["label"] == "missing"
    assert payload["projects"][0]["finding_count"] == 1


def test_build_json_failed_project_has_null_count():
    results = [{"project": "x", "success": False, "error": "deptry crashed", "findings": []}]
    payload = dha.build_json(results, dha.summarize(results))
    assert payload["projects"][0]["finding_count"] is None
    assert payload["projects"][0]["error"] == "deptry crashed"


# ── discover_projects() ───────────────────────────────────────────────────────


def test_discover_projects_only_returns_those_with_pyproject(tmp_path):
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "pyproject.toml").write_text("[project]\nname='ws'\n", encoding="utf-8")
    # blind-to-x dir exists but has NO pyproject -> skipped
    (tmp_path / "projects" / "blind-to-x").mkdir(parents=True)
    found = dha.discover_projects(tmp_path, selected=None)
    names = {n for n, _ in found}
    assert "workspace" in names
    assert "blind-to-x" not in names


def test_discover_projects_respects_selection(tmp_path):
    for rel in ("workspace", "projects/blind-to-x", "projects/shorts-maker-v2"):
        d = tmp_path / rel
        d.mkdir(parents=True)
        (d / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    found = dha.discover_projects(tmp_path, selected=["blind-to-x"])
    assert [n for n, _ in found] == ["blind-to-x"]


# ── run_deptry() with mocked subprocess ───────────────────────────────────────


class _FakeCompleted:
    def __init__(self, returncode=1, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _patch_subprocess_with_report(monkeypatch, raw_report, returncode=1):
    """Patch subprocess.run so it writes ``raw_report`` to deptry's --json-output."""

    def fake_run(cmd, **kwargs):
        idx = cmd.index("--json-output")
        out_path = cmd[idx + 1]
        Path(out_path).write_text(json.dumps(raw_report), encoding="utf-8")
        return _FakeCompleted(returncode=returncode)

    monkeypatch.setattr(dha.subprocess, "run", fake_run)


def test_run_deptry_parses_report(monkeypatch, tmp_path):
    raw = [
        {
            "error": {"code": "DEP001", "message": "'redis' missing"},
            "module": "redis",
            "location": {"file": "p\\db.py", "line": 12, "column": 4},
        },
        {
            "error": {"code": "DEP003", "message": "'numpy' transitive"},
            "module": "numpy",
            "location": {"file": "p\\img.py", "line": 7, "column": 1},
        },
    ]
    _patch_subprocess_with_report(monkeypatch, raw, returncode=1)
    res = dha.run_deptry(tmp_path, timeout=30)
    assert res["success"] is True
    assert {f["code"] for f in res["findings"]} == {"DEP001", "DEP003"}
    assert res["findings"][0]["module"] == "redis"
    assert res["findings"][0]["line"] == 12


def test_run_deptry_clean_report_is_success_with_no_findings(monkeypatch, tmp_path):
    _patch_subprocess_with_report(monkeypatch, [], returncode=0)
    res = dha.run_deptry(tmp_path, timeout=30)
    assert res["success"] is True
    assert res["findings"] == []


def test_run_deptry_missing_report_is_failure(monkeypatch, tmp_path):
    # subprocess "runs" but never writes the JSON report -> treated as a crash.
    def fake_run(cmd, **kwargs):
        idx = cmd.index("--json-output")
        out_path = cmd[idx + 1]
        if Path(out_path).exists():
            Path(out_path).unlink()
        return _FakeCompleted(returncode=2, stderr="deptry exploded")

    monkeypatch.setattr(dha.subprocess, "run", fake_run)
    res = dha.run_deptry(tmp_path, timeout=30)
    assert res["success"] is False
    assert "no JSON report" in res["error"]


def test_run_deptry_timeout_is_failure(monkeypatch, tmp_path):
    def fake_run(cmd, **kwargs):
        raise dha.subprocess.TimeoutExpired(cmd, 5)

    monkeypatch.setattr(dha.subprocess, "run", fake_run)
    res = dha.run_deptry(tmp_path, timeout=5)
    assert res["success"] is False
    assert "timed out" in res["error"]


# ── main() exit codes ─────────────────────────────────────────────────────────


def _stub_audit(monkeypatch, results):
    summary = dha.summarize(results)
    monkeypatch.setattr(dha, "run_audit", lambda *a, **k: (results, summary))
    monkeypatch.setattr(dha, "deptry_installed", lambda: True)


def test_main_clean_returns_zero(monkeypatch, capsys):
    _stub_audit(monkeypatch, [{"project": "a", "success": True, "findings": []}])
    assert dha.main(["--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["summary"]["total_findings"] == 0


def test_main_findings_returns_one(monkeypatch):
    _stub_audit(monkeypatch, [{"project": "a", "success": True, "findings": [_finding("DEP001", "redis")]}])
    assert dha.main(["--json"]) == 1


def test_main_failed_project_returns_two(monkeypatch):
    _stub_audit(monkeypatch, [{"project": "a", "success": False, "error": "x", "findings": []}])
    assert dha.main(["--json"]) == 2


def test_main_deptry_missing_is_soft_by_default(monkeypatch, capsys):
    monkeypatch.setattr(dha, "deptry_installed", lambda: False)
    assert dha.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["installed"] is False


def test_main_deptry_missing_is_hard_with_strict(monkeypatch):
    monkeypatch.setattr(dha, "deptry_installed", lambda: False)
    assert dha.main(["--strict"]) == 3


# ── encoding safety ───────────────────────────────────────────────────────────


def test_safe_print_handles_non_encodable(monkeypatch, capsys):
    # Should never raise even if the stream cannot encode the glyph.
    dha._safe_print("한글 🧹 emoji test")
    # no exception == pass; output capture just confirms it ran
    capsys.readouterr()
