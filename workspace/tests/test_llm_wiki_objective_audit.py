"""Tests for `execution/llm_wiki_objective_audit.py`."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "execution" / "llm_wiki_objective_audit.py"
COMPLETION_AUDIT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "completion_audit.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


objective_audit = _load_module("llm_wiki_objective_audit", SCRIPT_PATH)
completion_audit = _load_module("completion_audit_for_objective_test", COMPLETION_AUDIT_PATH)


def _write(root: Path, rel_path: str, text: str = "") -> Path:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def _fake_report(**overrides):
    summary = {
        "status": "pass",
        "source_inventory_count": 65,
        "source_page_count": 12,
        "code_fact_count": 3,
        "config_fact_count": 3,
        "manifest_check_accepted_warning_count": 2,
        "manifest_check_unexpected_warning_count": 0,
        "release_summary_contract_status": "pass",
    }
    summary.update(overrides)
    return {"summary": summary, "issues": []}


def test_manifest_item_counts_exclude_blocked_complete_items():
    items = [
        {"coverage": "complete", "blockers": []},
        {"coverage": "complete", "blockers": ["still running"]},
        {"coverage": "missing", "blockers": ["missing evidence"]},
    ]

    complete_count, blocked_count = objective_audit._manifest_item_counts(items)

    assert complete_count == 1
    assert blocked_count == 2


def test_active_loop_blockers_surface_selector_and_external_boundary():
    blockers = objective_audit._active_loop_blockers(
        "dirty_worktree_handoff_current",
        "Current relay includes T-251.",
    )

    assert blockers[0].startswith("Objective is an active autonomous loop")
    assert any("dirty_worktree_handoff_current" in blocker for blocker in blockers)
    assert any("T-251" in blocker for blocker in blockers)


def _write_complete_fixture(root: Path) -> None:
    _write(
        root,
        "docs/wiki/llm/README.md",
        "\n".join(
            [
                "# LLM Wiki",
                "",
                "| # | page | note |",
                "|---|---|---|",
                "| 01 | [Architecture](01-architecture.md) | overview |",
                "| 14 | [Maintenance](14-maintenance-verification.md) | audit |",
                "| 15 | [Sources](15-source-inventory.md) | source-inventory.json |",
                "| 18 | [Runtime](18-runtime-wiring-checks.md) | runtime wiring |",
                "| 19 | [Objective](19-objective-loop-audit.md) | loop audit |",
                "",
                "py -3.13 execution/llm_wiki_audit.py --write-source-inventory --json",
            ]
        ),
    )
    _write(root, "docs/wiki/llm/01-architecture.md", "# Architecture\n")
    _write(root, "docs/wiki/llm/08-security.md", "# Security\n\n## A/B\n")
    _write(root, "docs/wiki/llm/14-maintenance-verification.md", "# Maintenance\n\n## A/B\n")
    _write(root, "docs/wiki/llm/15-source-inventory.md", "# Sources\n")
    _write(root, "docs/wiki/llm/18-runtime-wiring-checks.md", "# Runtime\n\n## A/B Decision\n")
    _write(root, "docs/wiki/llm/19-objective-loop-audit.md", "# Objective\n")
    _write(root, "docs/wiki/llm/source-inventory.json", '{"sources": []}\n')
    _write(root, "docs/wiki/llm/code-facts.json", '{"facts": []}\n')
    _write(root, "docs/wiki/llm/config-facts.json", '{"facts": []}\n')

    _write(root, "execution/llm_wiki_audit.py", "# audit script\n")
    _write(root, "workspace/tests/test_llm_wiki_audit.py", "# audit tests\n")
    _write(root, ".agents/skills/auto-research/scripts/llm_wiki_release_summary.py", "# summary helper\n")

    _write(
        root,
        ".ai/HANDOFF.md",
        "Next LLM Wiki candidate. T-1606 LLM Wiki. T-1607 selector. T-1608 handoff. T-251.\n",
    )
    _write(root, ".ai/TASKS.md", "LLM Wiki candidate and dirty_worktree_handoff_current. T-251.\n")
    _write(root, ".ai/SESSION_LOG.md", "T-1573 T-1577 T-1578 T-1579 T-1606 LLM Wiki cycles.\n")
    _write(root, ".ai/GOAL.md", "Active loop until the user says stop.\n")
    _write(
        root,
        ".tmp/next-experiment.json",
        json.dumps(
            {
                "summary": {"selected_kind": "dirty_worktree_handoff_current"},
                "selected": {"kind": "dirty_worktree_handoff_current"},
            }
        ),
    )


def test_build_manifest_maps_objective_requirements(monkeypatch, tmp_path: Path):
    _write_complete_fixture(tmp_path)
    monkeypatch.setattr(objective_audit, "_llm_wiki_report", lambda repo_root, today: _fake_report())

    manifest = objective_audit.build_manifest(tmp_path, today=date(2026, 6, 8))

    requirement_text = "\n".join(item["requirement"] for item in manifest["items"])
    assert "0단계" in requirement_text
    assert "외부 조사" in requirement_text
    assert "A/B 비교" in requirement_text
    assert "최신 반영" in requirement_text
    assert "사이클 보고" in requirement_text
    assert "중복/드리프트 방지" in requirement_text
    assert "종료 조건" in requirement_text
    assert manifest["summary"]["status"] == "blocked"
    assert manifest["summary"]["complete_item_count"] == 8
    assert manifest["summary"]["blocked_item_count"] == 1


def test_missing_source_inventory_blocks_external_research(monkeypatch, tmp_path: Path):
    _write_complete_fixture(tmp_path)
    (tmp_path / "docs" / "wiki" / "llm" / "source-inventory.json").unlink()
    monkeypatch.setattr(
        objective_audit,
        "_llm_wiki_report",
        lambda repo_root, today: _fake_report(source_inventory_count=0, source_page_count=0),
    )

    manifest = objective_audit.build_manifest(tmp_path, today=date(2026, 6, 8))
    external_item = next(item for item in manifest["items"] if item["requirement"].startswith("외부 조사"))

    assert external_item["coverage"] == "missing"
    assert external_item["verified"] is False
    assert any("source inventory manifest exists" in blocker for blocker in external_item["blockers"])
    assert any("external source inventory is non-empty" in blocker for blocker in external_item["blockers"])


def test_cli_writes_completion_audit_compatible_manifest(monkeypatch, tmp_path: Path, capsys):
    _write_complete_fixture(tmp_path)
    monkeypatch.setattr(objective_audit, "_llm_wiki_report", lambda repo_root, today: _fake_report())
    output = tmp_path / ".tmp" / "objective.json"

    exit_code = objective_audit.main(
        [
            "--repo-root",
            str(tmp_path),
            "--today",
            "2026-06-08",
            "--output",
            str(output),
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert output.exists()
    assert '"schema_version": 1' in captured.out

    manifest = json.loads(output.read_text(encoding="utf-8"))
    result = completion_audit.audit_manifest(manifest)

    assert result["status"] == "incomplete"
    assert result["summary"]["blocked_count"] == 1
    assert result["summary"]["complete_count"] == 8
