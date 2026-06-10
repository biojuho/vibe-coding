"""Unit tests for the auto-research direction alignment scorecard."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "direction_alignment_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("direction_alignment_audit", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["direction_alignment_audit"] = module
    spec.loader.exec_module(module)
    return module


direction_alignment_audit = _load_module()


def _write_workspace(root: Path) -> None:
    ai = root / ".ai"
    ai.mkdir(parents=True)
    (ai / "HANDOFF.md").write_text(
        "handoff session_orient.py project_qc_runner.py readiness do not retry T-251 Supabase credential reset",
        encoding="utf-8",
    )
    (ai / "TASKS.md").write_text("T-251 Supabase credential reset user-owned external blocker", encoding="utf-8")
    (ai / "CONTEXT.md").write_text("Local-only workspace handoff readiness project_qc_runner.py", encoding="utf-8")
    (ai / "GOAL.md").write_text("active auto-research local output quality loop", encoding="utf-8")

    execution = root / "execution"
    execution.mkdir()
    for name in ("session_orient.py", "product_readiness_score.py", "project_qc_runner.py"):
        (execution / name).write_text("# helper\n", encoding="utf-8")

    skill_root = root / ".agents" / "skills" / "auto-research"
    scripts = skill_root / "scripts"
    scripts.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text(
        "A/B official docs current external research completion audit browser QA direction_alignment_audit.py",
        encoding="utf-8",
    )
    for name in (
        "ab_decision.py",
        "browser_qa_inventory.py",
        "completion_audit.py",
        "dirty_worktree_handoff_plan.py",
        "next_experiment_selector.py",
        "release_authorization_packet.py",
    ):
        (scripts / name).write_text("# helper\n", encoding="utf-8")

    tmp = root / ".tmp"
    tmp.mkdir()
    (tmp / "scoped-dirty-worktree-handoff-plan-current.json").write_text(
        json.dumps(
            {
                "status": "handoff_required",
                "freshness": {"status": "current", "current": True},
                "decision": {"mode": "handoff_only", "stage_commit_push_authorized": False},
            }
        ),
        encoding="utf-8",
    )
    (tmp / "next-experiment-continuation.json").write_text(
        json.dumps(
            {
                "status": "blocked",
                "selected": {
                    "kind": "dirty_worktree_handoff_current",
                    "guardrails": [
                        "Do not push without explicit user authorization.",
                        "Do not retry T-251 until Supabase credentials are reset.",
                    ],
                },
                "summary": {"selected_kind": "dirty_worktree_handoff_current"},
            }
        ),
        encoding="utf-8",
    )


def test_build_audit_reports_aligned_but_blocked_boundary(tmp_path: Path) -> None:
    _write_workspace(tmp_path)

    audit = direction_alignment_audit.build_audit(tmp_path)

    assert audit["status"] == "aligned_blocked"
    assert audit["summary"]["overall_score"] >= 0.8
    assert audit["summary"]["reference_count"] == 3
    assert audit["summary"]["selector_kind"] == "dirty_worktree_handoff_current"
    assert any("explicit scoped staging/commit authorization" in item for item in audit["critical_blockers"])
    assert any(item["reference"] == "OpenAI Codex Web" for item in audit["external_comparison"])
    assert any(item["reference"] == "Cursor Plan Mode" for item in audit["external_comparison"])
    assert not any(item["reference"] == "Claude Code" for item in audit["external_comparison"])
    assert any("editable plan" in item["vibe_counter_position"] for item in audit["external_comparison"])


def test_build_audit_surfaces_missing_loop_evidence(tmp_path: Path) -> None:
    _write_workspace(tmp_path)
    (tmp_path / ".agents" / "skills" / "auto-research" / "scripts" / "ab_decision.py").unlink()

    audit = direction_alignment_audit.build_audit(tmp_path)
    loop_pillar = next(pillar for pillar in audit["pillars"] if pillar["key"] == "evidence_backed_loop")

    assert audit["status"] in {"partial", "aligned_blocked"}
    assert any("ab_decision.py" in blocker for blocker in loop_pillar["blockers"])


def test_cli_output_file_is_ascii_safe(tmp_path: Path, capsys) -> None:
    root = tmp_path / "\ubc15\uc8fc\ud638"
    root.mkdir()
    _write_workspace(root)
    output = tmp_path / "direction-alignment.json"

    code = direction_alignment_audit.main(["--root", str(root), "--output", str(output), "--json"])

    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "aligned_blocked"
    raw = output.read_bytes()
    assert all(byte < 128 for byte in raw)
    assert "\\ubc15\\uc8fc\\ud638" in raw.decode("ascii")
