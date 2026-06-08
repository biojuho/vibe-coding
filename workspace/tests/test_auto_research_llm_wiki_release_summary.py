"""Unit tests for the LLM Wiki release summary helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "llm_wiki_release_summary.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_release_summary", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["llm_wiki_release_summary"] = module
    spec.loader.exec_module(module)
    return module


llm_wiki_release_summary = _load_module()


def _packet(*, evidence_status: str = "pass", head_matches: bool | None = True) -> dict[str, object]:
    return {
        "status": "blocked_dirty_worktree",
        "summary": {"branch": "main", "head_short": "abc12345"},
        "blockers": ["dirty worktree paths: 3", "external/user-owned blocker(s): T-251"],
        "llm_wiki_strict_evidence": {
            "available": evidence_status != "missing",
            "path": ".tmp/llm-wiki-strict-audit-current.json",
            "status": evidence_status,
            "head_matches_current": head_matches,
            "unexpected_manifest_warning_count": 0 if evidence_status == "pass" else 1,
            "accepted_manifest_warning_count": 2,
            "source_inventory_count": 65,
            "generated_at": "2026-06-08",
            "command": "py -3.13 execution/llm_wiki_audit.py --write-strict-release-evidence --json",
        },
    }


def test_summary_marks_ready_llm_wiki_evidence_and_uses_current_artifact_action(tmp_path: Path) -> None:
    output = tmp_path / ".tmp" / "summary.md"
    result = llm_wiki_release_summary.build_summary(_packet(), root=tmp_path, output_path=output)

    markdown = result["summary_markdown"]

    assert result["status"] == "pass"
    assert "- [x] strict release gate status is pass" in markdown
    assert "- [x] evidence HEAD matches the current packet HEAD" in markdown
    assert "actions/upload-artifact@v7" in markdown
    assert "path: release-evidence/llm-wiki" in markdown
    assert "include-hidden-files" not in markdown
    assert result["artifact_upload"]["hidden_path_risk"] is True


def test_cli_appends_github_step_summary_and_prepares_visible_artifact_dir(tmp_path: Path, capsys) -> None:
    packet_path = tmp_path / ".tmp" / "release-authorization-packet.json"
    evidence_path = tmp_path / ".tmp" / "llm-wiki-strict-audit-current.json"
    output = tmp_path / ".tmp" / "summary.md"
    step_summary = tmp_path / "step-summary.md"
    artifact_dir = tmp_path / "release-evidence" / "llm-wiki"
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    evidence_path.write_text('{"status": "pass"}\n', encoding="utf-8")

    code = llm_wiki_release_summary.main(
        [
            "--root",
            str(tmp_path),
            "--packet",
            ".tmp/release-authorization-packet.json",
            "--output",
            ".tmp/summary.md",
            "--github-step-summary",
            str(step_summary),
            "--artifact-dir",
            "release-evidence/llm-wiki",
            "--json",
            "--strict",
        ]
    )
    stdout = json.loads(capsys.readouterr().out)

    assert code == 0
    assert stdout["status"] == "pass"
    assert stdout["github_step_summary"]["appended"] is True
    assert step_summary.read_text(encoding="utf-8") == output.read_text(encoding="utf-8")
    assert (artifact_dir / "llm-wiki-release-summary.md").exists()
    assert (artifact_dir / "llm-wiki-strict-audit-current.json").exists()
    assert stdout["artifact_upload"]["hidden_path_risk"] is False
    assert stdout["artifact_upload"]["action"] == "actions/upload-artifact@v7"


def test_strict_cli_fails_when_evidence_is_not_ready(tmp_path: Path, capsys) -> None:
    packet_path = tmp_path / ".tmp" / "release-authorization-packet.json"
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text(json.dumps(_packet(evidence_status="fail", head_matches=False)), encoding="utf-8")

    code = llm_wiki_release_summary.main(
        [
            "--root",
            str(tmp_path),
            "--packet",
            ".tmp/release-authorization-packet.json",
            "--output",
            ".tmp/summary.md",
            "--json",
            "--strict",
        ]
    )
    stdout = json.loads(capsys.readouterr().out)
    summary = (tmp_path / ".tmp" / "summary.md").read_text(encoding="utf-8")

    assert code == 1
    assert stdout["status"] == "fail"
    assert "- [ ] strict release gate status is pass" in summary
    assert "- [ ] evidence HEAD matches the current packet HEAD" in summary
