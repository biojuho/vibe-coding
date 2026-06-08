"""Unit tests for the dirty worktree handoff plan helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "dirty_worktree_handoff_plan.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("dirty_worktree_handoff_plan", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["dirty_worktree_handoff_plan"] = module
    spec.loader.exec_module(module)
    return module


dirty_plan = _load_module()


def _github_inventory(*, group_order: str = "default") -> dict[str, object]:
    groups = [
        {
            "key": "llm-wiki",
            "owner_hint": "Codex/current-auto-research",
            "path_count": 2,
            "paths": ["execution/llm_wiki_audit.py", "docs/wiki/llm/README.md"],
            "sample_truncated": False,
        },
        {
            "key": "auto-research",
            "owner_hint": "Codex/current-auto-research",
            "path_count": 1,
            "paths": [".agents/skills/auto-research/scripts/next_experiment_selector.py"],
            "sample_truncated": False,
        },
    ]
    if group_order == "reversed":
        groups = list(reversed(groups))
    return {
        "git": {
            "dirty_count": 3,
            "dirty_paths": [
                "docs/wiki/llm/README.md",
                ".agents/skills/auto-research/scripts/next_experiment_selector.py",
                "execution/llm_wiki_audit.py",
            ],
            "dirty_path_groups": groups,
        },
        "open_prs": {"available": True, "count": 0},
    }


def _session_orient() -> dict[str, object]:
    return {
        "git": {
            "branch": "main",
            "ahead": 833,
            "behind": 0,
            "worktree": {"staged": 0, "modified": 2, "untracked": 1},
        },
        "pull_requests": {"open_count": 0},
    }


def _readiness() -> dict[str, object]:
    return {
        "overall": {
            "score": 94,
            "state": "blocked",
            "local_blocker_count": 1,
            "publish_blocker_count": 1,
            "external_blocker_count": 1,
        }
    }


def _gate() -> dict[str, object]:
    return {
        "status": "warn",
        "risk_score": 0.55,
        "findings": [],
        "test_gaps": ["helper_without_coverage"],
        "untracked_files": ["workspace/tests/test_dirty_worktree_handoff_plan.py"],
        "reasons": ["1 test gap(s) detected"],
    }


def test_dirty_signature_is_stable_for_group_and_path_order() -> None:
    signature_a = dirty_plan.dirty_signature(_github_inventory(), _session_orient())
    signature_b = dirty_plan.dirty_signature(_github_inventory(group_order="reversed"), _session_orient())

    assert signature_a["value"] == signature_b["value"]
    assert signature_a["input"]["dirty_paths"] == sorted(signature_a["input"]["dirty_paths"])


def test_build_plan_records_group_order_boundaries_and_sources(tmp_path: Path) -> None:
    plan = dirty_plan.build_plan(
        root=tmp_path,
        github_inventory=_github_inventory(),
        session_orient=_session_orient(),
        readiness=_readiness(),
        code_review_gate=_gate(),
    )

    assert plan["status"] == "handoff_required"
    assert plan["decision"]["mode"] == "handoff_only"
    assert plan["decision"]["stage_commit_push_authorized"] is False
    assert [group["key"] for group in plan["group_order"]] == ["auto-research", "llm-wiki"]
    assert any("T-251 is user-owned" in item for item in plan["handoff_only_boundaries"])
    assert plan["inputs"]["code_review_gate"]["risk_score"] == 0.55
    assert plan["inputs"]["code_review_gate"]["test_gap_count"] == 1
    assert plan["inputs"]["code_review_gate"]["untracked_graph_relevant_file_count"] == 1
    assert plan["ab_comparison"][1]["decision"] == "adopt"
    assert {source["url"] for source in plan["sources"]} == {
        "https://git-scm.com/docs/git-status",
        "https://git-scm.com/docs/git-ls-files",
    }


def test_previous_plan_freshness_detects_current_and_stale(tmp_path: Path) -> None:
    first = dirty_plan.build_plan(
        root=tmp_path,
        github_inventory=_github_inventory(),
        session_orient=_session_orient(),
        readiness=_readiness(),
        code_review_gate=_gate(),
    )
    current = dirty_plan.build_plan(
        root=tmp_path,
        github_inventory=_github_inventory(),
        session_orient=_session_orient(),
        readiness=_readiness(),
        code_review_gate=_gate(),
        previous_plan=first,
    )
    changed = _github_inventory()
    changed["git"]["dirty_paths"] = [*changed["git"]["dirty_paths"], "workspace/tests/test_new.py"]  # type: ignore[index]
    stale = dirty_plan.build_plan(
        root=tmp_path,
        github_inventory=changed,
        session_orient=_session_orient(),
        readiness=_readiness(),
        code_review_gate=_gate(),
        previous_plan=first,
    )

    assert current["freshness"]["status"] == "current"
    assert stale["freshness"]["status"] == "stale"


def test_main_writes_json_and_markdown_from_existing_artifacts(tmp_path: Path) -> None:
    github_path = tmp_path / "github.json"
    session_path = tmp_path / "session.json"
    readiness_path = tmp_path / "readiness.json"
    gate_path = tmp_path / "gate.json"
    json_path = tmp_path / "plan.json"
    md_path = tmp_path / "plan.md"
    github_path.write_text(json.dumps(_github_inventory()), encoding="utf-8")
    session_path.write_text(json.dumps(_session_orient()), encoding="utf-8")
    readiness_path.write_text(json.dumps(_readiness()), encoding="utf-8")
    gate_path.write_text(json.dumps(_gate()), encoding="utf-8")

    code = dirty_plan.main(
        [
            "--root",
            str(tmp_path),
            "--github-inventory",
            str(github_path),
            "--session-orient",
            str(session_path),
            "--readiness",
            str(readiness_path),
            "--code-review-gate",
            str(gate_path),
            "--output-json",
            str(json_path),
            "--output-md",
            str(md_path),
            "--json",
        ]
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert code == 0
    assert payload["status"] == "handoff_required"
    assert payload["freshness"]["status"] == "missing_previous_json"
    assert "Deterministic JSON plus Markdown handoff" in markdown
    assert "Do not stage, commit, push, or revert automatically" in markdown
