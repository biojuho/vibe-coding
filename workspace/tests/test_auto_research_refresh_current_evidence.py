"""Unit tests for the auto-research current evidence refresh helper."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "refresh_current_evidence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("refresh_current_evidence", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["refresh_current_evidence"] = module
    spec.loader.exec_module(module)
    return module


refresh_current_evidence = _load_module()


def _json_bytes(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def test_refresh_current_evidence_writes_bom_free_current_json(monkeypatch, tmp_path):
    root = tmp_path
    (root / ".tmp").mkdir()
    (root / ".tmp" / "product-readiness-current.json").write_bytes(b"\xef\xbb\xbf{}")
    (root / ".tmp" / "scoped-dirty-worktree-handoff-plan-current.json").write_bytes(
        _json_bytes({"status": "handoff_required"}),
    )
    (root / ".tmp" / "next-scoped-authorization-menu-current.json").write_bytes(
        _json_bytes(
            {
                "recommended": {
                    "token": "APPROVE_AI_CONTEXT_RELAY_UPDATE",
                    "pathspec": ".tmp/approve-ai-context-relay-update.pathspec",
                    "files": [".ai/HANDOFF.md", ".ai/TASKS.md"],
                    "reason": ["Relay context only"],
                },
                "also_available": [
                    {
                        "token": "APPROVE_ROOT_NPMRC_STRICT_PEER_DEPS",
                        "pathspec": ".tmp/approve-root-npmrc-strict-peer-deps.pathspec",
                        "classification": "verified_existing_packet",
                    },
                    {
                        "token": "APPROVE_SESSION_LOG_ROTATOR",
                        "pathspec": ".tmp/approve-session-log-rotator.pathspec",
                        "classification": "verified_uncovered_workspace_tool_packet",
                        "reason": "Covers the session log rotator",
                    },
                ],
                "one_line_user_options": [
                    "APPROVE_AI_CONTEXT_RELAY_UPDATE",
                    "APPROVE_SESSION_LOG_ROTATOR",
                    "STOP",
                ],
            },
        ),
    )
    code_review_gate = root / ".tmp" / "code-review-gate-current.json"
    code_review_gate.write_bytes(
        b"\xef\xbb\xbf"
        + _json_bytes(
            {
                "status": "warn",
                "risk_score": 0.6,
                "affected_flows": [],
                "changed_files": [
                    ".ai/CONTEXT.md",
                    ".ai/HANDOFF.md",
                    ".ai/SESSION_LOG.md",
                    ".ai/TASKS.md",
                ],
                "test_gaps": [
                    "_manifest_context :: C:\\Users\\박주호\\Desktop\\Vibe coding\\execution\\llm_wiki_objective_audit.py",
                    "_initial_status :: C:\\Users\\박주호\\Desktop\\Vibe coding\\execution\\mcp_diagnostic.py",
                    "_missing_required_keys :: C:\\Users\\박주호\\Desktop\\Vibe coding\\execution\\mcp_diagnostic.py",
                ],
                "reasons": [
                    "risk_score 0.60 >= warn-threshold 0.30",
                    "315 test gap(s) detected",
                    "16 untracked graph-relevant file(s) require direct review coverage",
                    "extra reason hidden",
                ],
                "untracked_files": [
                    ".agents/skills/auto-research/scripts/scoped_authorization_menu.py",
                    "execution/locked_temp_cleanup.py",
                    "projects/blind-to-x/scripts/verify_weekly_smoke.py",
                    "workspace/tests/test_locked_temp_cleanup.py",
                ],
                "impact_radius": {
                    "changed_files": 4,
                    "changed_nodes": 12,
                    "impacted_nodes": [
                        {
                            "kind": "Function",
                            "name": "_gate_failures",
                            "file_path": r"C:\Users\박주호\Desktop\Vibe coding\.agents\skills\auto-research\scripts\ab_decision.py",
                        },
                        {
                            "kind": "Function",
                            "name": "_metric_score",
                            "file_path": ".agents/skills/auto-research/scripts/ab_decision.py",
                        },
                        "workspace/execution/content_db.py::list_ready_items",
                        "workspace/execution/smart_router.py::route",
                    ],
                    "total_impacted": 17,
                    "impacted_files": [
                        r"C:\Users\박주호\Desktop\Vibe coding\.agents\skills\auto-research\scripts\github_project_inventory.py",
                        r"C:\Users\박주호\Desktop\Vibe coding\projects\blind-to-x\scripts\backfill_notion_review_columns.py",
                        "workspace/execution/content_db.py",
                        "workspace/execution/smart_router.py",
                    ],
                    "edges": 21,
                    "truncated": True,
                },
                "review_priorities": [
                    "_supabase_password_env_checks",
                    "_dashboard_runtime_auth_env_checks",
                    "_source_preflight_requested",
                    "_credential_diagnostic_lines",
                ],
            },
        ),
    )

    session_orient_calls: list[str] = []

    def fake_run(argv, **kwargs):
        joined = " ".join(argv)
        cwd = Path(kwargs["cwd"])
        if argv[0] == "git":
            has_virtual_index = "env" in kwargs and "GIT_INDEX_FILE" in kwargs["env"]
            if argv[1:] == ["read-tree", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            if argv[1] == "add":
                return subprocess.CompletedProcess(argv, 0, b"", b"warning: CRLF normalization\n")
            if argv[1:] == ["diff", "--cached", "--name-only"]:
                stdout = b".ai/HANDOFF.md\n.ai/TASKS.md\n" if has_virtual_index else b""
                return subprocess.CompletedProcess(argv, 0, stdout, b"")
            if argv[1:] == ["diff", "--cached", "--shortstat"]:
                return subprocess.CompletedProcess(argv, 0, b" 2 files changed, 10 insertions(+)\n", b"")
            if argv[1:] == ["diff", "--cached", "--check"]:
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            raise AssertionError(f"unexpected git command: {joined}")
        if "product_readiness_score.py" in joined:
            return subprocess.CompletedProcess(
                argv,
                0,
                _json_bytes(
                    {
                        "overall": {
                            "score": 92,
                            "state": "blocked",
                            "blockers": {"workspace": 1, "local": 1, "publish": 0, "external": 0},
                        },
                        "projects": [
                            {
                                "name": "blind-to-x",
                                "score": 92,
                                "state": "ready",
                                "qc": {
                                    "available": True,
                                    "status": "PASS",
                                    "passed": 2506,
                                    "failed": 0,
                                    "skipped": 9,
                                    "stale": False,
                                    "head_stale": False,
                                    "missing_checks": [],
                                },
                                "dirty_paths": ["projects/blind-to-x/pipeline/draft_prompts.py"],
                                "tasks": [],
                            },
                            {
                                "name": "shorts-maker-v2",
                                "score": 92,
                                "state": "ready",
                                "qc": {
                                    "available": True,
                                    "status": "PASS",
                                    "passed": 1660,
                                    "failed": 0,
                                    "skipped": 12,
                                    "stale": False,
                                    "head_stale": False,
                                    "missing_checks": [],
                                },
                                "dirty_paths": ["projects/shorts-maker-v2/tools/ai_tech_shorts.py"],
                                "tasks": [],
                            },
                            {
                                "name": "hanwoo-dashboard",
                                "score": 82,
                                "state": "blocked",
                                "qc": {
                                    "available": True,
                                    "status": "PASS",
                                    "passed": 541,
                                    "failed": 0,
                                    "skipped": 0,
                                    "stale": False,
                                    "head_stale": False,
                                    "missing_checks": [],
                                },
                                "dirty_paths": ["projects/hanwoo-dashboard/package.json"],
                                "tasks": [{"id": "T-251"}],
                            },
                            {
                                "name": "knowledge-dashboard",
                                "score": 92,
                                "state": "ready",
                                "qc": {
                                    "available": True,
                                    "status": "PASS",
                                    "passed": 69,
                                    "failed": 0,
                                    "skipped": 0,
                                    "stale": False,
                                    "head_stale": False,
                                    "missing_checks": [],
                                },
                                "dirty_paths": [],
                                "tasks": [],
                            },
                        ],
                    },
                ),
                b"",
            )
        if "github_project_inventory.py" in joined:
            (cwd / ".tmp" / "github-project-inventory-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "projects": [{"path": "."}, {"path": "projects/blind-to-x"}],
                        "workflows": [".github/workflows/root-quality-gate.yml"],
                        "dependabot_files": [".github/dependabot.yml"],
                        "open_prs": {"count": 0},
                        "recommendations": ["Keep current-head release gates visible."],
                    },
                ),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        if "browser_qa_inventory.py" in joined:
            (cwd / ".tmp" / "browser-qa-inventory-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "summary": {
                            "browser_project_count": 4,
                            "covered_count": 4,
                            "missing_count": 0,
                            "fresh_nonblank_screenshot_project_count": 4,
                            "stale_screenshot_project_count": 0,
                        },
                        "projects": [
                            {
                                "path": "projects/hanwoo-dashboard",
                                "browser_app": True,
                                "status": "covered",
                                "log_evidence_count": 118,
                                "verified_log_evidence_count": 90,
                                "fresh_nonblank_screenshot_count": 2,
                                "current_screenshot_count": 2,
                                "freshest_screenshot_age_days": 4,
                                "freshest_screenshot_path": "output/playwright/browser-qa-t2060-hanwoo-dashboard.png",
                                "freshest_screenshot_width": 390,
                                "freshest_screenshot_height": 844,
                                "freshest_screenshot_nonblank": True,
                            },
                            {
                                "path": "projects/knowledge-dashboard",
                                "browser_app": True,
                                "status": "covered",
                                "log_evidence_count": 18,
                                "verified_log_evidence_count": 13,
                                "fresh_nonblank_screenshot_count": 1,
                                "current_screenshot_count": 1,
                                "freshest_screenshot_age_days": 4,
                                "freshest_screenshot_path": "output/playwright/browser-qa-t2060-knowledge-dashboard.png",
                                "freshest_screenshot_width": 390,
                                "freshest_screenshot_height": 844,
                                "freshest_screenshot_nonblank": True,
                            },
                            {
                                "path": "projects/suika-game-v2",
                                "browser_app": True,
                                "status": "covered",
                                "log_evidence_count": 14,
                                "verified_log_evidence_count": 14,
                                "fresh_nonblank_screenshot_count": 1,
                                "current_screenshot_count": 1,
                                "freshest_screenshot_age_days": 4,
                                "freshest_screenshot_path": "output/playwright/browser-qa-t2060-suika-game-v2.png",
                                "freshest_screenshot_width": 390,
                                "freshest_screenshot_height": 844,
                                "freshest_screenshot_nonblank": True,
                            },
                            {
                                "path": "projects/word-chain",
                                "browser_app": True,
                                "status": "covered",
                                "log_evidence_count": 13,
                                "verified_log_evidence_count": 13,
                                "fresh_nonblank_screenshot_count": 1,
                                "current_screenshot_count": 1,
                                "freshest_screenshot_age_days": 4,
                                "freshest_screenshot_path": "output/playwright/browser-qa-t2060-word-chain.png",
                                "freshest_screenshot_width": 390,
                                "freshest_screenshot_height": 844,
                                "freshest_screenshot_nonblank": True,
                            },
                        ],
                    },
                ),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        if "dependency_freshness_inventory.py" in joined:
            (cwd / ".tmp" / "dependency-freshness-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "summary": {
                            "package_project_count": 5,
                            "candidate_dependency_count": 0,
                            "outdated_dependency_count": 13,
                            "deferred_dependency_count": 2,
                            "peer_blocker_latest_blocked_count": 6,
                            "unavailable_project_count": 0,
                        },
                        "projects": [
                            {
                                "path": "projects/hanwoo-dashboard",
                                "dependencies": [
                                    {
                                        "name": "eslint",
                                        "peer_target_major": 10,
                                        "peer_blocker_latest_check": "partial_upstream_support",
                                        "peer_blocker_latest_supported_count": 1,
                                        "peer_blocker_latest_blocked_count": 3,
                                        "peer_blocker_latest_unavailable_count": 0,
                                        "peer_blockers": [
                                            {
                                                "package": "eslint-plugin-import",
                                                "latest_peer_check": "blocks_target_major",
                                            },
                                            {
                                                "package": "eslint-plugin-jsx-a11y",
                                                "latest_peer_check": "blocks_target_major",
                                            },
                                            {
                                                "package": "eslint-plugin-react",
                                                "latest_peer_check": "blocks_target_major",
                                            },
                                            {
                                                "package": "eslint-plugin-react-hooks",
                                                "latest_peer_check": "allows_target_major",
                                                "latest_peer_allows_target": True,
                                            },
                                        ],
                                    },
                                ],
                            },
                            {
                                "path": "projects/knowledge-dashboard",
                                "dependencies": [
                                    {
                                        "name": "eslint",
                                        "peer_target_major": 10,
                                        "peer_blocker_latest_check": "still_blocked",
                                        "peer_blocker_latest_supported_count": 0,
                                        "peer_blocker_latest_blocked_count": 3,
                                        "peer_blocker_latest_unavailable_count": 0,
                                        "peer_blockers": [
                                            {
                                                "package": "eslint-plugin-import",
                                                "latest_peer_check": "blocks_target_major",
                                            },
                                            {
                                                "package": "eslint-plugin-jsx-a11y",
                                                "latest_peer_check": "blocks_target_major",
                                            },
                                            {
                                                "package": "eslint-plugin-react",
                                                "latest_peer_check": "blocks_target_major",
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        if "direction_alignment_audit.py" in joined:
            (cwd / ".tmp" / "direction-alignment-audit-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "status": "aligned_blocked",
                        "summary": {"overall_score": 0.91},
                    },
                ),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "aligned_blocked"}), b"")
        if "launch_objective_audit.py" in joined:
            (cwd / ".tmp" / "launch-objective-audit-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "items": [
                            {
                                "requirement": "Research current dependency/code freshness.",
                                "evidence": [
                                    "code_review_gate status=warn, risk_score=0.6, changed_files=426, test_gaps=662.",
                                ],
                            },
                        ],
                    },
                ),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"items": []}), b"")
        if "completion_audit.py" in joined:
            return subprocess.CompletedProcess(
                argv,
                0,
                _json_bytes(
                    {
                        "status": "incomplete",
                        "summary": {"item_count": 1, "complete_count": 0, "issue_count": 1, "blocked_count": 1},
                        "items": [
                            {
                                "requirement": "Prove launch readiness.",
                                "artifacts": [".tmp/product-readiness-current.json"],
                                "evidence": ["product readiness remains blocked"],
                                "coverage": "partial",
                                "blockers": ["dirty handoff"],
                                "issues": ["blocked"],
                                "passed": False,
                            },
                        ],
                    },
                ),
                b"",
            )
        if "release_authorization_packet.py" in joined:
            (cwd / ".tmp" / "release-authorization-packet-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "status": "blocked_dirty_worktree",
                        "summary": {
                            "head_short": "abc1234",
                            "ahead_count": 2,
                            "dirty_count": 3,
                            "commit_omitted_count": 1,
                            "current_head_required_success_count": 0,
                            "llm_wiki_strict_evidence_status": "pass",
                            "llm_wiki_strict_evidence_head_matches_current": True,
                            "llm_wiki_strict_evidence_unexpected_count": 0,
                            "llm_wiki_strict_evidence_path": ".tmp/llm-wiki-strict-audit-current.json",
                        },
                        "git": {
                            "commits_ahead_preview": [
                                {"sha": "abc12345", "subject": "feat: improve launch evidence."},
                                {"sha": "def67890", "subject": "fix: keep release gate visible"},
                            ],
                        },
                        "current_head_actions": {
                            "available": False,
                            "head_sha": "abc1234fedcba",
                            "command": (
                                "gh run list --commit abc1234fedcba --limit 20 "
                                "--json databaseId,name,workflowName,status,conclusion,headSha,createdAt,url"
                            ),
                            "returncode": 0,
                            "limit": 20,
                            "run_count": 0,
                            "required_success_count": 0,
                            "required_count": 2,
                            "required_run_count": 0,
                            "runs_preview": [],
                            "missing_required_workflows": ["root-quality-gate", "active-project-matrix"],
                        },
                        "authorization": {
                            "push_required": True,
                            "allowed_without_explicit_user_authorization": False,
                            "post_push_gates": ["root-quality-gate", "active-project-matrix"],
                            "guardrails": [
                                "Do not push without explicit user authorization.",
                                "Wait for required workflows on the exact current HEAD.",
                            ],
                        },
                        "llm_wiki_strict_evidence": {
                            "available": True,
                            "status": "pass",
                            "head_matches_current": True,
                            "unexpected_manifest_warning_count": 0,
                            "path": ".tmp/llm-wiki-strict-audit-current.json",
                        },
                    },
                ),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "blocked_dirty_worktree"}), b"")
        if "session_orient.py" in joined:
            session_orient_calls.append(joined)
            task_id = "T-2568" if len(session_orient_calls) == 1 else "T-2569"
            return subprocess.CompletedProcess(
                argv,
                0,
                _json_bytes(
                    {
                        "repo_root": str(cwd),
                        "git": {
                            "branch": "main",
                            "ahead": 2,
                            "behind": 0,
                            "worktree": {
                                "modified": 2,
                                "untracked": 1,
                                "staged": 0,
                                "unmerged": 0,
                            },
                        },
                        "handoff": {
                            "latest_addendum_order_status": "ok",
                            "effective_latest_task_id": task_id,
                            "current_head": "abc1234",
                            "latest_next_priority_status": "ok",
                            "current_addendum_count": 4,
                            "rotation_suggested": False,
                            "archivable_addendum_count": 0,
                        },
                    },
                ),
                b"",
            )
        if "dirty_worktree_handoff_plan.py" in joined:
            assert "--previous-json" in argv
            previous_index = argv.index("--previous-json") + 1
            assert Path(argv[previous_index]).as_posix() == ".tmp/scoped-dirty-worktree-handoff-plan-current.json"
            (cwd / ".tmp" / "scoped-dirty-worktree-handoff-plan-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "status": "handoff_required",
                        "freshness": {"current": True},
                        "previous_plan_freshness": {"status": "current"},
                        "dirty_signature": {
                            "value": "abcdef123456",
                            "input": {
                                "dirty_count": 3,
                                "staged": 0,
                                "dirty_path_groups": [{"key": "ai-context"}, {"key": "auto-research"}],
                            },
                        },
                    },
                ),
            )
            (cwd / ".tmp" / "scoped-dirty-worktree-handoff-plan-refresh.md").write_text(
                "# Dirty handoff\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "handoff_required"}), b"")
        if "approval_pathspec_consistency.py" in joined:
            (cwd / ".tmp" / "authorization-coverage-current.json").write_bytes(
                _json_bytes({"dirty_count": 3, "covered_dirty_count": 3, "uncovered_dirty_count": 0}),
            )
            (cwd / ".tmp" / "approval-pathspec-consistency-current.md").write_text(
                "# Approval pathspec\n",
                encoding="utf-8",
            )
            (cwd / ".tmp" / "approval-pathspec-combined-current.pathspec").write_text(
                "a.py\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(
                argv,
                0,
                _json_bytes(
                    {
                        "status": "ok",
                        "dirty_count": 3,
                        "covered_dirty_count": 3,
                        "uncovered_dirty_count": 0,
                        "uncovered_non_evidence_source_count": 0,
                        "pathspec_count": 1,
                        "staged_count": 0,
                        "pathspec_results": [
                            {
                                "pathspec": "approve-ai-context-relay-update.pathspec",
                                "unique_path_count": 3,
                                "covered_dirty_count": 3,
                            },
                            {
                                "pathspec": "approve-root-npmrc-strict-peer-deps.pathspec",
                                "unique_path_count": 1,
                                "covered_dirty_count": 0,
                                "extra_non_dirty_count": 1,
                                "extra_non_dirty_paths": [".npmrc"],
                            },
                        ],
                    },
                ),
                b"",
            )
        if "scoped_authorization_menu.py" in joined and "--check" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                _json_bytes(
                    {
                        "status": "ok",
                        "rendered_matches": True,
                        "exact_rendered_matches": True,
                        "coverage_stale": False,
                    },
                ),
                b"",
            )
        if "scoped_authorization_menu.py" in joined:
            assert "--rewrite-menu-json" in argv
            (cwd / ".tmp" / "next-scoped-authorization-menu-current.md").write_text(
                "# Scoped menu\n",
                encoding="utf-8",
            )
            (cwd / ".tmp" / "approve-ai-context-relay-update.pathspec").write_text(
                ".ai/HANDOFF.md\n.ai/TASKS.md\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        if "next_experiment_selector.py" in joined:
            (cwd / ".tmp" / "next-experiment-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "status": "blocked",
                        "summary": {
                            "selected_kind": "dirty_worktree_handoff_current",
                            "adoptable_candidate_count": 0,
                            "blocked_candidate_count": 1,
                        },
                        "selected": {
                            "kind": "dirty_worktree_handoff_current",
                            "evidence": [
                                "dirty groups: ai-context=2, auto-research=1",
                            ],
                        },
                    },
                ),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "blocked"}), b"")
        if "debug_loop_inventory.py" in joined:
            (cwd / ".tmp" / "debug-loop-known-bugs-refresh.json").write_bytes(
                _json_bytes(
                    {
                        "summary": {
                            "completion_allowed": False,
                            "blocked_item_count": 5,
                            "completion_blockers": [
                                {
                                    "title": "Dirty Handoff Boundary Blocks New Product Edits",
                                    "next_action": "Wait for explicit scoped staging/commit authorization.",
                                },
                                {
                                    "title": "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker",
                                    "next_action": "User resets Supabase credentials.",
                                },
                                {
                                    "title": "Current-HEAD GitHub Actions Cannot Be Proven Locally",
                                    "next_action": "Explicit push authorization or user push.",
                                },
                                {
                                    "title": "Launch Completion Audit Remains Incomplete",
                                    "next_action": "Keep blocked evidence current.",
                                },
                            ],
                        },
                    },
                ),
            )
            (cwd / ".tmp" / "debug-loop-known-bugs-refresh.md").write_text(
                "# Debug inventory\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 1, _json_bytes({"status": "blocked"}), b"")
        raise AssertionError(f"unexpected command: {joined}")

    monkeypatch.setattr(refresh_current_evidence.subprocess, "run", fake_run)

    summary = refresh_current_evidence.refresh_current_evidence(root, timeout=5)

    assert summary["status"] == "ok"
    assert code_review_gate.read_bytes().startswith(b"{\n")
    assert json.loads(code_review_gate.read_text(encoding="utf-8"))["status"] == "warn"
    for relative in [
        ".tmp/product-readiness-current.json",
        ".tmp/github-project-inventory-current.json",
        ".tmp/browser-qa-inventory-current.json",
        ".tmp/dependency-freshness-current.json",
        ".tmp/direction-alignment-audit-current.json",
        ".tmp/launch-objective-audit-current.json",
        ".tmp/launch-objective-completion-audit-current.json",
        ".tmp/release-authorization-packet-current.json",
        ".tmp/session-orient-current.json",
        ".tmp/next-experiment-current.json",
        ".tmp/next-experiment-selection-current.json",
        ".tmp/next-experiment-continuation.json",
        ".tmp/approval-pathspec-consistency-current.json",
        ".tmp/approval-execution-matrix-current.json",
        ".tmp/launch-blocker-burndown-current.json",
        ".tmp/ai-context-aic1-scoped-authorization-current.json",
        ".tmp/session-log-rotator-authorization-current.json",
        ".tmp/authorization-coverage-current.json",
        ".tmp/next-scoped-authorization-menu-current.check.json",
        ".tmp/debug-loop-known-bugs-current.json",
        ".tmp/scoped-dirty-worktree-handoff-plan-current.json",
    ]:
        raw = (root / relative).read_bytes()
        assert raw[:1] == b"{"
        assert not raw.startswith(b"\xef\xbb\xbf")
        json.loads(raw.decode("utf-8"))

    selector_current = json.loads((root / ".tmp" / "next-experiment-current.json").read_text(encoding="utf-8"))
    selector_alias = json.loads(
        (root / ".tmp" / "next-experiment-selection-current.json").read_text(encoding="utf-8"),
    )
    selector_continuation = json.loads(
        (root / ".tmp" / "next-experiment-continuation.json").read_text(encoding="utf-8"),
    )
    assert selector_alias == selector_current
    assert selector_continuation == selector_current

    debug_step = next(step for step in summary["steps"] if step["name"] == "debug_loop_inventory")
    assert debug_step["returncode"] == 1
    assert debug_step["expected_returncode"] is True
    assert any(step["name"] == "debug_loop_completion_exit_contract" for step in summary["steps"])
    assert any(step["name"] == "release_authorization_packet" for step in summary["steps"])
    assert any(step["name"] == "github_project_inventory" for step in summary["steps"])
    assert any(step["name"] == "browser_qa_inventory" for step in summary["steps"])
    assert any(step["name"] == "dependency_freshness_inventory" for step in summary["steps"])
    assert any(step["name"] == "direction_alignment_audit" for step in summary["steps"])
    assert any(step["name"] == "approval_pathspec_consistency" for step in summary["steps"])
    assert any(step["name"] == "approval_execution_matrix_and_burndown" for step in summary["steps"])
    assert any(step["name"] == "scoped_authorization_menu" for step in summary["steps"])
    assert any(step["name"] == "ai_context_relay_packet" for step in summary["steps"])
    assert any(step["name"] == "session_log_rotator_pathspec" for step in summary["steps"])
    assert any(step["name"] == "session_log_rotator_packet" for step in summary["steps"])
    assert any(step["name"] == "session_log_rotator_menu_option" for step in summary["steps"])
    assert any(step["name"] == "session_orient_final" for step in summary["steps"])
    assert len(session_orient_calls) == 2
    assert (root / ".tmp" / "approve-session-log-rotator.pathspec").read_text(encoding="utf-8") == (
        "execution/session_log_rotator.py\nworkspace/tests/test_session_log_rotator.py\n"
    )
    menu = json.loads((root / ".tmp" / "next-scoped-authorization-menu-current.json").read_text(encoding="utf-8"))
    assert any(item["token"] == "APPROVE_SESSION_LOG_ROTATOR" for item in menu["also_available"])
    assert any(step["name"] == "launch_prompt_artifact_checklist" for step in summary["steps"])
    check_step = next(step for step in summary["steps"] if step["name"] == "scoped_authorization_menu_check")
    assert check_step["returncode"] == 0
    assert check_step["expected_returncode"] is True
    packet = json.loads(
        (root / ".tmp" / "ai-context-aic1-scoped-authorization-current.json").read_text(encoding="utf-8"),
    )
    assert packet["scope"] == [".ai/HANDOFF.md", ".ai/TASKS.md"]
    assert packet["current_scope_validation"]["scope_dirty_path_count"] == 2
    assert packet["current_scope_validation"]["all_scope_paths_currently_dirty"] is True
    assert packet["virtual_index"]["path_count"] == 2
    assert packet["virtual_index"]["real_staged_count_after"] == 0
    assert (
        (root / ".tmp" / "ai-context-aic1-scoped-authorization-current.md")
        .read_text(encoding="utf-8")
        .startswith(
            "# AI Context Relay Update Authorization Packet",
        )
    )
    checklist = (root / ".tmp" / "launch-objective-prompt-artifact-checklist-current.md").read_text(
        encoding="utf-8",
    )
    assert checklist.startswith("# Launch Objective Prompt-to-Artifact Checklist")
    assert "coverage 3/3" in checklist
    assert "Completion coverage: partial 1; passed 0/1, blocked 1." in checklist
    assert "Completion blockers: Prove launch readiness." in checklist
    assert (
        "Completion blocker actions: Prove launch readiness -> "
        "clear local/workspace blockers and keep direct readiness evidence current."
    ) in checklist
    assert "Completion blockers omitted:" not in checklist
    assert "Authorization options:" in checklist
    assert "APPROVE_SESSION_LOG_ROTATOR" in checklist
    assert "Authorization option pathspecs:" in checklist
    assert "APPROVE_AI_CONTEXT_RELAY_UPDATE->approve-ai-context-relay-update.pathspec" in checklist
    assert "Authorization option classes:" in checklist
    assert "APPROVE_AI_CONTEXT_RELAY_UPDATE->recommended" in checklist
    assert "Authorization options omitted:" not in checklist
    assert (
        "Authorization option coverage: APPROVE_AI_CONTEXT_RELAY_UPDATE=3/3; APPROVE_SESSION_LOG_ROTATOR=n/a."
    ) in checklist
    assert (
        "One-line user options: APPROVE_AI_CONTEXT_RELAY_UPDATE, APPROVE_SESSION_LOG_ROTATOR, STOP (shown 3/3)."
        in checklist
    )
    assert (
        "One-line user option details: shown 3/3: "
        "APPROVE_AI_CONTEXT_RELAY_UPDATE->recommended/approve-ai-context-relay-update.pathspec/"
        "Relay context only; APPROVE_SESSION_LOG_ROTATOR->verified_uncovered_workspace_tool_packet/"
        "approve-session-log-rotator.pathspec/Covers the newly surfaced session log rotator source/test pair "
        "with virtual index and diff-check proof without authorizing staging.; "
        "STOP->control/n/a/stop the loop without staging, committing, pushing, cleanup, or live retries."
    ) in checklist
    assert (
        "Authorization omissions: current-zero-dirty APPROVE_ROOT_NPMRC_STRICT_PEER_DEPS "
        "(tokens 1, dirty coverage 0, extra non-dirty paths 1, details "
        "APPROVE_ROOT_NPMRC_STRICT_PEER_DEPS -> approve-root-npmrc-strict-peer-deps.pathspec: .npmrc)."
    ) in checklist
    assert "Dirty groups: ai-context=2, auto-research=1." in checklist
    assert (
        "Handoff orientation: order ok, effective T-2569, head abc1234, priorities ok, "
        "addenda 4, rotation no, archivable 0."
    ) in checklist
    assert "Git worktree: branch main, ahead 2, behind 0, modified 2, untracked 1, staged 0, unmerged 0." in checklist
    assert (
        "Dirty handoff plan: status handoff_required, freshness true/current, signature abcdef12, "
        "dirty 3, staged 0, groups 2."
    ) in checklist
    assert "Approval phases: phase0_context_relay=3 dirty/1 tokens; coverage 3/3, phase refs 3." in checklist
    assert "Approval phase references: phase0_context_relay=3; unique coverage 3/3, overlap refs 0." in checklist
    assert "Approval phase tokens: phase0_context_relay: APPROVE_AI_CONTEXT_RELAY_UPDATE." in checklist
    assert (
        "Debug blockers: 5 blocked, completion_allowed false, top Dirty Handoff Boundary Blocks New Product Edits."
    ) in checklist
    assert (
        "Debug blocker titles: Dirty Handoff Boundary Blocks New Product Edits; "
        "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker; "
        "Current-HEAD GitHub Actions Cannot Be Proven Locally; "
        "Launch Completion Audit Remains Incomplete."
    ) in checklist
    assert (
        "Debug blocker next actions: Dirty Handoff Boundary Blocks New Product Edits -> "
        "Wait for explicit scoped staging/commit authorization; "
        "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker -> User resets Supabase credentials; "
        "Current-HEAD GitHub Actions Cannot Be Proven Locally -> Explicit push authorization or user push; "
        "Launch Completion Audit Remains Incomplete -> Keep blocked evidence current."
    ) in checklist
    assert (
        "GitHub inventory: 2 projects, 1 workflows, 1 dependabot files, open PRs 0, recommendations 1."
    ) in checklist
    assert "GitHub recommendations: Keep current-head release gates visible." in checklist
    assert "Browser QA: 4/4 covered, fresh nonblank screenshots 4/4, stale 0, missing 0." in checklist
    assert (
        "Browser QA projects: hanwoo-dashboard=covered/fresh-nonblank2/shots2/age4d; "
        "knowledge-dashboard=covered/fresh-nonblank1/shots1/age4d; "
        "suika-game-v2=covered/fresh-nonblank1/shots1/age4d; "
        "word-chain=covered/fresh-nonblank1/shots1/age4d."
    ) in checklist
    assert (
        "Browser QA artifacts: "
        "hanwoo-dashboard=output/playwright/browser-qa-t2060-hanwoo-dashboard.png/390x844/nonblank true; "
        "knowledge-dashboard=output/playwright/browser-qa-t2060-knowledge-dashboard.png/390x844/nonblank true; "
        "suika-game-v2=output/playwright/browser-qa-t2060-suika-game-v2.png/390x844/nonblank true; "
        "word-chain=output/playwright/browser-qa-t2060-word-chain.png/390x844/nonblank true."
    ) in checklist
    assert (
        "Browser QA log evidence: hanwoo-dashboard=verified-logs90/118; "
        "knowledge-dashboard=verified-logs13/18; "
        "suika-game-v2=verified-logs14/14; "
        "word-chain=verified-logs13/13."
    ) in checklist
    assert (
        "Dependency freshness: 5 package projects, candidates 0, outdated 13, deferred 2, "
        "peer-blocked 6, unavailable 0."
    ) in checklist
    assert (
        "Dependency blockers: projects/hanwoo-dashboard eslint@10: eslint-plugin-import, "
        "eslint-plugin-jsx-a11y, eslint-plugin-react; projects/knowledge-dashboard eslint@10: "
        "eslint-plugin-import, eslint-plugin-jsx-a11y, eslint-plugin-react."
    ) in checklist
    assert (
        "Dependency blocker actions: projects/hanwoo-dashboard eslint@10 -> "
        "defer major migration until upstream peer support "
        "(latest-supported 1, still-blocked 3, unavailable 0); "
        "projects/knowledge-dashboard eslint@10 -> defer major migration until upstream peer support "
        "(latest-supported 0, still-blocked 3, unavailable 0)."
    ) in checklist
    assert "Code review gate: status=warn, risk_score=0.6, changed_files=426, test_gaps=662." in checklist
    assert (
        "Code review gate detail: affected flows 0; changed top shown 4/4: .ai/CONTEXT.md, "
        ".ai/HANDOFF.md, .ai/SESSION_LOG.md, .ai/TASKS.md; gap files shown 2/2: "
        "execution/llm_wiki_objective_audit.py, execution/mcp_diagnostic.py."
    ) in checklist
    assert (
        "Code review gate count sources: launch audit counts changed/test gaps 426/662; "
        "detail artifact rows changed/test gaps/unique gap files 4/3/2."
    ) in checklist
    assert (
        "Code review gate reasons: shown 3/4: risk_score 0.60 >= warn-threshold 0.30; "
        "315 test gap(s) detected; 16 untracked graph-relevant file(s) require direct review coverage; "
        "omitted 1 more."
    ) in checklist
    assert (
        "Code review gate untracked: shown 4/4: "
        ".agents/skills/auto-research/scripts/scoped_authorization_menu.py, "
        "execution/locked_temp_cleanup.py, projects/blind-to-x/scripts/verify_weekly_smoke.py, "
        "workspace/tests/test_locked_temp_cleanup.py."
    ) in checklist
    assert (
        "Code review gate impact: changed files 4, changed nodes 12, impacted nodes shown/total 4/17, "
        "impacted files 4, edges 21, truncated true; impacted file preview shown 4/4: "
        ".agents/skills/auto-research/scripts/github_project_inventory.py, "
        "projects/blind-to-x/scripts/backfill_notion_review_columns.py, "
        "workspace/execution/content_db.py, workspace/execution/smart_router.py; "
        "impacted node preview shown 4/4: "
        "_gate_failures (.agents/skills/auto-research/scripts/ab_decision.py), "
        "_metric_score (.agents/skills/auto-research/scripts/ab_decision.py), "
        "workspace/execution/content_db.py::list_ready_items, "
        "workspace/execution/smart_router.py::route."
    ) in checklist
    assert (
        "Code review gate priorities: shown 4/4: _supabase_password_env_checks, "
        "_dashboard_runtime_auth_env_checks, _source_preflight_requested, "
        "_credential_diagnostic_lines."
    ) in checklist
    assert "Code review gate artifact: utf8_bom false, first bytes 7B 0A 20 20." in checklist
    assert (
        "Recommended next scope: APPROVE_AI_CONTEXT_RELAY_UPDATE / phase0_context_relay - "
        "Context relay first. (3 dirty paths, 1 tokens)."
    ) in checklist
    assert (
        "Recommended authorization artifact: APPROVE_AI_CONTEXT_RELAY_UPDATE -> packet unknown, "
        "pathspec .tmp/approve-ai-context-relay-update.pathspec, files 2."
    ) in checklist
    assert "Recommended authorization files: shown 2/2: .ai/HANDOFF.md, .ai/TASKS.md." in checklist
    assert "Next A/B task id: T-1" in checklist
    assert "A/B manifest collisions: none." in checklist
    assert "A/B collision hidden task ids:" not in checklist
    assert "A/B collision task ids omitted:" not in checklist
    assert "Authorization check: status ok, rendered_matches true" in checklist
    assert "exact_rendered_matches true, coverage_stale false" in checklist
    assert (
        "Release packet: blocked_dirty_worktree, head abc1234, ahead 2, dirty 3, "
        "current-head Actions 0/2, missing root-quality-gate, active-project-matrix."
    ) in checklist
    assert (
        "Release packet blockers: dirty worktree paths 3; "
        "current-head Actions unavailable until explicit push/user push."
    ) in checklist
    assert (
        "LLM Wiki strict release evidence: available true, status pass, "
        "head_matches_current true, unexpected 0, path .tmp/llm-wiki-strict-audit-current.json."
    ) in checklist
    assert (
        "Release commits: shown 2/3; abc12345 feat: improve launch evidence; "
        "def67890 fix: keep release gate visible; omitted 1 more."
    ) in checklist
    assert "Release commit encoding: subjects 2, non-ascii 0, replacement chars 0, mojibake markers 0." in checklist
    assert (
        "Release actions: available false, runs 0, required runs 0/2, success 0/2, "
        "successful none, missing root-quality-gate, active-project-matrix, "
        "current-head boundary ahead 2/dirty 3."
    ) in checklist
    assert (
        "Release actions probe: head abc1234f, returncode 0, runs_preview 0/20, run_count 0, "
        "command gh run list --commit abc1234fedcba --limit 20."
    ) in checklist
    assert (
        "Release authorization guardrails: push_required true, "
        "allowed_without_explicit_user_authorization false, "
        "post-push gates root-quality-gate, active-project-matrix, guardrails 2, "
        "shown 2/2: Do not push without explicit user authorization.; "
        "Wait for required workflows on the exact current HEAD."
    ) in checklist
    assert (
        "Target readiness: blind-to-x=92/ready/dirty1/tasks0; "
        "shorts-maker-v2=92/ready/dirty1/tasks0; "
        "hanwoo-dashboard=82/blocked/dirty1/tasks1; "
        "knowledge-dashboard=92/ready/dirty0/tasks0."
    ) in checklist
    assert (
        "Target blockers: blind-to-x: score 92, dirty 1; "
        "shorts-maker-v2: score 92, dirty 1; "
        "hanwoo-dashboard: score 82, state blocked, tasks T-251, dirty 1; "
        "knowledge-dashboard: score 92."
    ) in checklist
    assert (
        "Target blocker actions: blind-to-x -> clear target dirty paths and keep project QC/readiness evidence current; "
        "shorts-maker-v2 -> clear target dirty paths and keep project QC/readiness evidence current; "
        "hanwoo-dashboard -> wait for Supabase credential reset before live Prisma CRUD retry; "
        "knowledge-dashboard -> refresh target readiness evidence and resolve score/state blockers."
    ) in checklist
    assert (
        "Project QC: 4/4 PASS, checks passed 4776, failed 0, skipped 21, stale 0, head-stale 0, missing checks 0."
    ) in checklist
    assert (
        "Blocker actions: dirty_worktree_handoff_current -> user_or_operator / APPROVE_AI_CONTEXT_RELAY_UPDATE"
    ) in checklist
    assert "current_head_release_checks_unproven -> user_or_operator / explicit_push_or_user_push" in checklist
    assert "hanwoo_t251_external_supabase_credentials -> user / external_credential_reset" in checklist
    assert "Prove launch readiness." in checklist
    assert "do not call `update_goal`" in checklist


def test_completion_blocker_summary_lists_current_blockers_without_residual_omission():
    completion = {
        "items": [
            {"requirement": "First blocker.", "passed": False, "blockers": ["blocked"]},
            {"requirement": "Second blocker", "passed": False, "blockers": ["blocked"]},
            {"requirement": "Third blocker", "passed": False, "blockers": ["blocked"]},
            {"requirement": "Fourth blocker", "passed": False, "blockers": ["blocked"]},
            {"requirement": "Fifth blocker", "passed": False, "blockers": ["blocked"]},
            {"requirement": "Sixth blocker", "passed": False, "blockers": ["blocked"]},
            {"requirement": "Seventh blocker", "passed": False, "blockers": ["blocked"]},
            {"requirement": "Already passed", "passed": True, "blockers": []},
        ],
    }

    assert (
        refresh_current_evidence._completion_blocker_summary(completion)
        == "First blocker; Second blocker; Third blocker; Fourth blocker; Fifth blocker; Sixth blocker; Seventh blocker."
    )
    assert refresh_current_evidence._completion_blocker_omission_summary(completion) == ""


def test_completion_blocker_action_summary_maps_boundaries_with_limit():
    completion = {
        "items": [
            {
                "requirement": "Find GitHub-related projects and PR/workflow surfaces before choosing improvements.",
                "passed": False,
                "blockers": ["dirty worktree"],
            },
            {
                "requirement": "Generate a no-push release authorization packet before any clean-ahead publish.",
                "passed": False,
                "blockers": ["dirty worktree"],
            },
            {
                "requirement": "Separate externally blocked live checks from local product-polish completion.",
                "passed": False,
                "blockers": ["T-251"],
            },
            {
                "requirement": "Prove blind-to-x target product launch readiness with direct project evidence.",
                "passed": False,
                "blockers": ["dirty paths"],
            },
        ],
    }

    assert (
        refresh_current_evidence._completion_blocker_action_summary(completion, limit=3)
        == "Find GitHub-related projects and PR/workflow surfaces before choosing improvements -> "
        "resolve dirty worktree boundary or keep GitHub inventory evidence current; "
        "Generate a no-push release authorization packet before any clean-ahead publish -> "
        "keep no-push packet current until explicit stage/commit/push authorization; "
        "Separate externally blocked live checks from local product-polish completion -> "
        "user resets Supabase credentials, then rerun the live Prisma check once; omitted 1: "
        "Prove blind-to-x target product launch readiness with direct project evidence -> "
        "clear target dirty paths and keep project QC/readiness evidence current."
    )


def test_completion_blocker_action_summary_lists_current_full_scale_by_default():
    requirements = [
        "Find GitHub-related projects and PR/workflow surfaces before choosing improvements.",
        "Verify local product-readiness gates before claiming launch readiness.",
        "Generate a no-push release authorization packet before any clean-ahead publish.",
        "Run the deterministic next-experiment selector and confirm no local auto-research candidate remains.",
        "Separate externally blocked live checks from local product-polish completion.",
        "Prove hanwoo-dashboard target product launch readiness with direct project evidence.",
        "Prove blind-to-x target product launch readiness with direct project evidence.",
        "Prove shorts-maker-v2 target product launch readiness with direct project evidence.",
        "Prove knowledge-dashboard target product launch readiness with direct project evidence.",
    ]
    completion = {
        "items": [
            {"requirement": requirement, "passed": False, "blockers": ["blocked"]} for requirement in requirements
        ],
    }

    summary = refresh_current_evidence._completion_blocker_action_summary(completion)

    assert summary.startswith(
        "Find GitHub-related projects and PR/workflow surfaces before choosing improvements -> "
        "resolve dirty worktree boundary or keep GitHub inventory evidence current; "
    )
    assert (
        "Prove knowledge-dashboard target product launch readiness with direct project evidence -> "
        "clear target dirty paths and keep project QC/readiness evidence current."
    ) in summary
    assert "omitted" not in summary


def test_completion_blocker_action_summary_limits_omitted_preview():
    completion = {
        "items": [
            {"requirement": f"Generic blocker {index}", "passed": False, "blockers": ["blocked"]}
            for index in range(1, 8)
        ],
    }

    assert (
        refresh_current_evidence._completion_blocker_action_summary(completion, limit=2)
        == "Generic blocker 1 -> keep blocker evidence current until the owning boundary is cleared; "
        "Generic blocker 2 -> keep blocker evidence current until the owning boundary is cleared; "
        "omitted 5: Generic blocker 3 -> keep blocker evidence current until the owning boundary is cleared; "
        "Generic blocker 4 -> keep blocker evidence current until the owning boundary is cleared; omitted-more 3."
    )


def test_completion_coverage_summary_reports_coverage_and_pass_counts():
    completion = {
        "items": [
            {"coverage": "complete", "passed": True, "blockers": []},
            {"coverage": "complete", "passed": False, "blockers": ["blocked"]},
            {"coverage": "partial", "passed": False, "blockers": ["blocked"]},
            {"coverage": "", "passed": False, "blockers": []},
        ],
    }

    assert (
        refresh_current_evidence._completion_coverage_summary(completion)
        == "complete 2, partial 1, unknown 1; passed 1/4, blocked 3."
    )


def test_completion_coverage_summary_omits_missing_items():
    assert refresh_current_evidence._completion_coverage_summary({"items": []}) == ""
    assert refresh_current_evidence._completion_coverage_summary({}) == ""


def test_code_review_gate_detail_summary_shows_visible_and_total_counts():
    summary = refresh_current_evidence._code_review_gate_detail_summary(
        {
            "affected_flows": [],
            "changed_files": [
                ".ai/CONTEXT.md",
                ".ai/HANDOFF.md",
                ".ai/SESSION_LOG.md",
                ".ai/TASKS.md",
            ],
            "test_gaps": [
                "_manifest_context :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\llm_wiki_objective_audit.py",
                "_initial_status :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\mcp_diagnostic.py",
                "_missing_required_keys :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\mcp_diagnostic.py",
            ],
        },
    )

    assert (
        summary == "affected flows 0; changed top shown 4/4: .ai/CONTEXT.md, .ai/HANDOFF.md, "
        ".ai/SESSION_LOG.md, .ai/TASKS.md; gap files shown 2/2: "
        "execution/llm_wiki_objective_audit.py, execution/mcp_diagnostic.py."
    )


def test_code_review_gate_detail_summary_uses_current_wider_default_preview():
    changed_files = [
        ".ai/CONTEXT.md",
        ".ai/HANDOFF.md",
        ".ai/SESSION_LOG.md",
        ".ai/TASKS.md",
        ".ai/archive/HANDOFF_archive_2026-06-11.md",
        ".cache/dbf3428f6ecb6967.png",
        ".gitignore",
        "execution/llm_wiki_objective_audit.py",
        "execution/mcp_diagnostic.py",
        "execution/product_readiness_score.py",
        "execution/project_qc_runner.py",
        "execution/session_orient.py",
    ]
    gap_files = [
        "execution/llm_wiki_objective_audit.py",
        "execution/mcp_diagnostic.py",
        "execution/product_readiness_score.py",
        "execution/project_qc_runner.py",
        "execution/session_orient.py",
        "execution/skill_lint.py",
        "projects/blind-to-x/pipeline/bootstrap.py",
        "projects/blind-to-x/pipeline/cli.py",
        "projects/blind-to-x/pipeline/cost_tracker.py",
        "projects/blind-to-x/pipeline/draft_generator.py",
        "projects/blind-to-x/pipeline/draft_providers.py",
    ]

    summary = refresh_current_evidence._code_review_gate_detail_summary(
        {
            "affected_flows": [],
            "changed_files": changed_files,
            "test_gaps": [f"gap :: C:\\Users\\owner\\Desktop\\Vibe coding\\{path}" for path in gap_files],
        },
    )

    assert summary.startswith(
        "affected flows 0; changed top shown 10/12: "
        ".ai/CONTEXT.md, .ai/HANDOFF.md, .ai/SESSION_LOG.md, .ai/TASKS.md, "
        ".ai/archive/HANDOFF_archive_2026-06-11.md, .cache/dbf3428f6ecb6967.png, "
        ".gitignore, execution/llm_wiki_objective_audit.py, execution/mcp_diagnostic.py, "
        "execution/product_readiness_score.py, omitted 2: "
    )
    assert "gap files shown 10/11: " in summary
    assert "projects/blind-to-x/pipeline/draft_generator.py, omitted 1: " in summary


def test_code_review_gate_detail_summary_limits_omitted_previews():
    summary = refresh_current_evidence._code_review_gate_detail_summary(
        {
            "affected_flows": ["a", "b"],
            "changed_files": [
                ".ai/HANDOFF.md",
                ".ai/TASKS.md",
                "hidden-a.py",
                "hidden-b.py",
                "hidden-c.py",
                "hidden-d.py",
            ],
            "test_gaps": [
                f"gap{i} :: C:\\Users\\owner\\Desktop\\Vibe coding\\workspace\\gap_{i}.py" for i in range(1, 7)
            ],
        },
        limit=2,
        omitted_limit=2,
    )

    assert (
        summary == "affected flows 2; changed top shown 2/6: .ai/HANDOFF.md, .ai/TASKS.md, "
        "omitted 4: hidden-a.py, hidden-b.py, omitted-more 2; gap files shown 2/6: "
        "workspace/gap_1.py, workspace/gap_2.py, omitted 4: workspace/gap_3.py, workspace/gap_4.py, "
        "omitted-more 2."
    )


def test_code_review_gate_detail_summary_default_expands_omitted_preview():
    summary = refresh_current_evidence._code_review_gate_detail_summary(
        {
            "affected_flows": [],
            "changed_files": [f"changed_{index}.py" for index in range(1, 46)],
            "test_gaps": [
                f"missing :: C:/Users/test/Desktop/Vibe coding/workspace/gap_{index}.py" for index in range(1, 45)
            ],
        },
    )

    assert "changed top shown 10/45: changed_1.py" in summary
    assert "omitted 35: changed_11.py" in summary
    assert "changed_40.py" in summary
    assert "changed_41.py" not in summary
    assert "omitted-more 5" in summary
    assert "gap files shown 10/44: workspace/gap_1.py" in summary
    assert "omitted 34: workspace/gap_11.py" in summary
    assert "workspace/gap_40.py" in summary
    assert "workspace/gap_41.py" not in summary
    assert summary.endswith("omitted-more 4.")


def test_code_review_gate_count_alignment_summary_reports_source_mismatch():
    summary = refresh_current_evidence._code_review_gate_count_alignment_summary(
        "status=warn, risk_score=0.6, changed_files=426, test_gaps=662.",
        {
            "changed_files": [".ai/CONTEXT.md", ".ai/HANDOFF.md"],
            "test_gaps": [
                "_manifest_context :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\llm_wiki_objective_audit.py",
                "_initial_status :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\mcp_diagnostic.py",
                "_missing_required_keys :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\mcp_diagnostic.py",
            ],
        },
    )

    assert (
        summary == "launch audit counts changed/test gaps 426/662; "
        "detail artifact rows changed/test gaps/unique gap files 2/3/2."
    )


def test_code_review_gate_count_alignment_summary_omits_matching_counts():
    assert (
        refresh_current_evidence._code_review_gate_count_alignment_summary(
            "status=warn, risk_score=0.6, changed_files=2, test_gaps=3.",
            {
                "changed_files": [".ai/CONTEXT.md", ".ai/HANDOFF.md"],
                "test_gaps": [
                    "_manifest_context :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\llm_wiki_objective_audit.py",
                    "_initial_status :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\mcp_diagnostic.py",
                    "_missing_required_keys :: C:\\Users\\owner\\Desktop\\Vibe coding\\execution\\mcp_diagnostic.py",
                ],
            },
        )
        == ""
    )


def test_code_review_gate_reason_summary_lists_reasons_with_omission_count():
    summary = refresh_current_evidence._code_review_gate_reason_summary(
        {
            "reasons": [
                "risk_score 0.60 >= warn-threshold 0.30.",
                "315 test gap(s) detected",
                "",
                "16 untracked graph-relevant file(s) require direct review coverage",
                "extra reason hidden",
            ],
        },
    )

    assert (
        summary == "shown 3/4: risk_score 0.60 >= warn-threshold 0.30; 315 test gap(s) detected; "
        "16 untracked graph-relevant file(s) require direct review coverage; omitted 1 more."
    )


def test_code_review_gate_reason_summary_omits_missing_reasons():
    assert refresh_current_evidence._code_review_gate_reason_summary({"reasons": []}) == ""
    assert refresh_current_evidence._code_review_gate_reason_summary({}) == ""


def test_handoff_orientation_summary_reports_ab_manifest_alignment():
    summary = refresh_current_evidence._handoff_orientation_summary(
        {
            "handoff": {
                "latest_addendum_order_status": "ok",
                "effective_latest_task_id": "T-2624",
                "current_head": "3823a80f6c49",
                "latest_next_priority_status": "ok",
                "current_addendum_count": 26,
                "rotation_suggested": False,
                "archivable_addendum_count": 0,
            },
        },
        ab_task_id_advisory={"highest_task_id": 2624},
    )

    assert summary == (
        "order ok, effective T-2624, head 3823a80f, priorities ok, addenda 26, rotation no, "
        "archivable 0, aligned with latest A/B manifest."
    )


def test_handoff_orientation_summary_reports_newer_ab_manifest():
    summary = refresh_current_evidence._handoff_orientation_summary(
        {
            "handoff": {
                "latest_addendum_order_status": "ok",
                "effective_latest_task_id": "T-2623",
                "current_head": "3823a80f6c49",
                "latest_next_priority_status": "ok",
                "current_addendum_count": 26,
                "rotation_suggested": False,
                "archivable_addendum_count": 0,
            },
        },
        ab_task_id_advisory={"highest_task_id": 2624},
    )

    assert summary == (
        "order ok, effective T-2623, head 3823a80f, priorities ok, addenda 26, rotation no, "
        "archivable 0, latest A/B manifest T-2624 newer than effective handoff."
    )


def test_code_review_gate_untracked_summary_lists_paths_default_full_scale():
    summary = refresh_current_evidence._code_review_gate_untracked_summary(
        {
            "untracked_files": [
                ".agents/skills/auto-research/scripts/scoped_authorization_menu.py",
                "execution\\locked_temp_cleanup.py",
                "projects/blind-to-x/scripts/verify_weekly_smoke.py",
                "workspace/tests/test_locked_temp_cleanup.py",
            ],
        },
    )

    assert (
        summary == "shown 4/4: .agents/skills/auto-research/scripts/scoped_authorization_menu.py, "
        "execution/locked_temp_cleanup.py, projects/blind-to-x/scripts/verify_weekly_smoke.py, "
        "workspace/tests/test_locked_temp_cleanup.py."
    )


def test_code_review_gate_untracked_summary_limits_omitted_preview():
    summary = refresh_current_evidence._code_review_gate_untracked_summary(
        {
            "untracked_files": [
                "shown-a.py",
                "shown-b.py",
                "hidden-a.py",
                "hidden-b.py",
                "hidden-c.py",
                "hidden-d.py",
            ],
        },
        limit=2,
    )

    assert summary == "shown 2/6: shown-a.py, shown-b.py, omitted 4: hidden-a.py, hidden-b.py, omitted-more 2."


def test_code_review_gate_untracked_summary_omits_missing_paths():
    assert refresh_current_evidence._code_review_gate_untracked_summary({"untracked_files": []}) == ""
    assert refresh_current_evidence._code_review_gate_untracked_summary({}) == ""


def test_code_review_gate_impact_summary_reports_blast_radius_counts():
    summary = refresh_current_evidence._code_review_gate_impact_summary(
        {
            "impact_radius": {
                "changed_files": 113,
                "changed_nodes": 2876,
                "impacted_nodes": 500,
                "total_impacted": 2487,
                "impacted_files": 166,
                "edges": 7723,
                "truncated": True,
            },
        },
    )

    assert (
        summary == "changed files 113, changed nodes 2876, impacted nodes shown/total 500/2487, "
        "impacted files 166, edges 7723, truncated true."
    )


def test_code_review_gate_impact_summary_uses_list_fallbacks_and_omits_missing_data():
    summary = refresh_current_evidence._code_review_gate_impact_summary(
        {
            "changed_files": ["a.py", "b.py"],
            "impact_radius": {
                "changed_nodes": ["a", "b", "c"],
                "impacted_nodes": ["d", "e"],
                "impacted_files": ["a.py"],
                "edges": ["a->d", "b->e"],
                "truncated": False,
            },
        },
    )

    assert (
        summary == "changed files 2, changed nodes 3, impacted nodes shown/total 2/2, "
        "impacted files 1, edges 2, truncated false; impacted file preview shown 1/1: a.py; "
        "impacted node preview shown 2/2: d, e."
    )
    assert refresh_current_evidence._code_review_gate_impact_summary({"impact_radius": {}}) == ""
    assert refresh_current_evidence._code_review_gate_impact_summary({}) == ""


def test_code_review_gate_impact_summary_limits_impacted_file_preview():
    summary = refresh_current_evidence._code_review_gate_impact_summary(
        {
            "impact_radius": {
                "changed_files": 9,
                "changed_nodes": 10,
                "impacted_nodes": [
                    {
                        "kind": "File",
                        "name": r"C:\Users\박주호\Desktop\Vibe coding\a.py",
                        "file_path": r"C:\Users\박주호\Desktop\Vibe coding\a.py",
                    },
                    {"name": "node-a", "file_path": r"C:\Users\박주호\Desktop\Vibe coding\a.py"},
                    {"name": "node-b", "file_path": "b.py"},
                    {"name": "node-c", "file_path": "c.py"},
                    {"name": "node-d", "file_path": "d.py"},
                    {"name": "node-e", "file_path": "e.py"},
                    {"name": "node-f", "file_path": "f.py"},
                    {"name": "node-g", "file_path": "g.py"},
                ],
                "total_impacted": 12,
                "impacted_files": [
                    r"C:\Users\박주호\Desktop\Vibe coding\a.py",
                    "b.py",
                    "c.py",
                    "d.py",
                    "e.py",
                    "f.py",
                    "g.py",
                ],
                "edges": 13,
                "truncated": True,
            },
        },
        limit=3,
        omitted_limit=3,
    )

    assert "impacted file preview shown 3/7: a.py, b.py, c.py" in summary
    assert "omitted 4: d.py, e.py, f.py" in summary
    assert "impacted node preview shown 3/8: a.py, node-a (a.py), node-b (b.py)" in summary
    assert "omitted 5: node-c (c.py), node-d (d.py), node-e (e.py)" in summary
    assert "omitted-more 2." in summary


def test_code_review_gate_impact_summary_uses_current_wider_default_preview():
    impacted_files = [
        ".agents/skills/auto-research/scripts/github_project_inventory.py",
        "infrastructure/cloudinary-mcp/server.py",
        "projects/blind-to-x/scripts/backfill_notion_review_columns.py",
        "infrastructure/telegram-mcp/server.py",
        ".agents/skills/nature-figure/assets/figures4papers/figure_CellSpliceNet/plot_comparison.py",
        "projects/blind-to-x/pipeline/cross_source_insight.py",
        "projects/blind-to-x/pipeline/notion_upload.py",
        "projects/blind-to-x/pipeline/process_stages/generate_review_stage.py",
        "projects/blind-to-x/scripts/build_weekly_report.py",
        "projects/blind-to-x/scripts/notion_doctor.py",
        "projects/blind-to-x/pipeline/editorial_reviewer.py",
    ]
    impacted_nodes = [
        {
            "name": ".agents/skills/api-design-principles/assets/rest-api-template.py",
            "file_path": ".agents/skills/api-design-principles/assets/rest-api-template.py",
        },
        {"name": "_gate_failures", "file_path": ".agents/skills/auto-research/scripts/ab_decision.py"},
        {"name": "_metric_direction", "file_path": ".agents/skills/auto-research/scripts/ab_decision.py"},
        {"name": "_metric_score", "file_path": ".agents/skills/auto-research/scripts/ab_decision.py"},
        {"name": "decide", "file_path": ".agents/skills/auto-research/scripts/ab_decision.py"},
        {"name": "_age_days", "file_path": ".agents/skills/auto-research/scripts/browser_qa_inventory.py"},
        {"name": "_freshness_status", "file_path": ".agents/skills/auto-research/scripts/browser_qa_inventory.py"},
        {"name": "_format_path", "file_path": ".agents/skills/auto-research/scripts/browser_qa_inventory.py"},
        {"name": "_iter_screenshots", "file_path": ".agents/skills/auto-research/scripts/browser_qa_inventory.py"},
        {"name": "_scan_project", "file_path": ".agents/skills/auto-research/scripts/browser_qa_inventory.py"},
        {"name": "_summarize", "file_path": ".agents/skills/auto-research/scripts/browser_qa_inventory.py"},
    ]

    summary = refresh_current_evidence._code_review_gate_impact_summary(
        {
            "impact_radius": {
                "changed_files": 113,
                "changed_nodes": 2876,
                "impacted_nodes": impacted_nodes,
                "total_impacted": 2487,
                "impacted_files": impacted_files,
                "edges": 7723,
                "truncated": True,
            },
        },
    )

    assert "impacted file preview shown 10/11: " in summary
    assert "projects/blind-to-x/scripts/notion_doctor.py" in summary
    assert "omitted 1: projects/blind-to-x/pipeline/editorial_reviewer.py" in summary
    assert "impacted node preview shown 10/11: " in summary
    assert "_scan_project (.agents/skills/auto-research/scripts/browser_qa_inventory.py)" in summary
    assert "omitted 1: _summarize (.agents/skills/auto-research/scripts/browser_qa_inventory.py)" in summary


def test_code_review_gate_impact_summary_default_expands_omitted_preview():
    summary = refresh_current_evidence._code_review_gate_impact_summary(
        {
            "impact_radius": {
                "changed_files": 40,
                "changed_nodes": 80,
                "impacted_nodes": [
                    {"name": f"node-{index}", "file_path": f"node_{index}.py"} for index in range(1, 36)
                ],
                "total_impacted": 70,
                "impacted_files": [f"file_{index}.py" for index in range(1, 37)],
                "edges": 120,
                "truncated": True,
            }
        },
    )

    assert "impacted file preview shown 10/36: file_1.py" in summary
    assert "omitted 26: file_11.py" in summary
    assert "file_30.py" in summary
    assert "file_31.py" not in summary
    assert "omitted-more 6" in summary
    assert "impacted node preview shown 10/35: node-1 (node_1.py)" in summary
    assert "omitted 25: node-11 (node_11.py)" in summary
    assert "node-30 (node_30.py)" in summary
    assert "node-31" not in summary
    assert summary.endswith("omitted-more 5.")


def test_code_review_gate_priority_summary_lists_review_priorities_default_full_scale():
    summary = refresh_current_evidence._code_review_gate_priority_summary(
        {
            "review_priorities": [
                "_supabase_password_env_checks",
                "_dashboard_runtime_auth_env_checks",
                "",
                "_source_preflight_requested",
                "_credential_diagnostic_lines",
            ],
        },
    )

    assert (
        summary == "shown 4/4: _supabase_password_env_checks, _dashboard_runtime_auth_env_checks, "
        "_source_preflight_requested, _credential_diagnostic_lines."
    )


def test_code_review_gate_untracked_summary_lists_current_full_scale():
    files = [
        ".agents/skills/auto-research/scripts/scoped_authorization_menu.py",
        "execution/locked_temp_cleanup.py",
        "projects/blind-to-x/scripts/verify_weekly_smoke.py",
        "projects/blind-to-x/scripts/write_weekly_smoke_inputs.py",
        "projects/blind-to-x/tests/unit/test_bootstrap_cost_status.py",
        "projects/blind-to-x/tests/unit/test_ops_runbook_docs.py",
        "projects/blind-to-x/tests/unit/test_recompute_scores.py",
        "projects/blind-to-x/tests/unit/test_source_preflight_repair_flow_docs.py",
        "projects/blind-to-x/tests/unit/test_verify_weekly_smoke.py",
        "projects/blind-to-x/tests/unit/test_write_weekly_smoke_inputs.py",
        "workspace/tests/test_auto_research_scoped_authorization_menu.py",
        "workspace/tests/test_backup_restore_test.py",
        "workspace/tests/test_bgm_downloader.py",
        "workspace/tests/test_locked_temp_cleanup.py",
        "workspace/tests/test_mcp_diagnostic.py",
        "workspace/tests/test_notebooklm_integration.py",
    ]

    summary = refresh_current_evidence._code_review_gate_untracked_summary(
        {"untracked_files": files},
    )

    assert summary == "shown 16/16: " + ", ".join(files) + "."
    assert "omitted" not in summary


def test_code_review_gate_priority_summary_limits_omitted_preview():
    summary = refresh_current_evidence._code_review_gate_priority_summary(
        {
            "review_priorities": [
                "shown-a",
                "shown-b",
                "hidden-a",
                "hidden-b",
                "hidden-c",
                "hidden-d",
            ],
        },
        limit=2,
    )

    assert summary == "shown 2/6: shown-a, shown-b, omitted 4: hidden-a, hidden-b, omitted-more 2."


def test_code_review_gate_priority_summary_omits_missing_priorities():
    assert refresh_current_evidence._code_review_gate_priority_summary({"review_priorities": []}) == ""
    assert refresh_current_evidence._code_review_gate_priority_summary({}) == ""


def test_code_review_gate_artifact_summary_reports_bom_and_first_bytes():
    assert (
        refresh_current_evidence._code_review_gate_artifact_summary(
            {
                "_artifact_first_bytes": "EF BB BF 7B",
                "_artifact_has_utf8_bom": True,
            },
        )
        == "utf8_bom true, first bytes EF BB BF 7B."
    )
    assert (
        refresh_current_evidence._code_review_gate_artifact_summary(
            {
                "_artifact_first_bytes": "7B 0A 20 20",
                "_artifact_has_utf8_bom": False,
            },
        )
        == "utf8_bom false, first bytes 7B 0A 20 20."
    )


def test_code_review_gate_artifact_summary_omits_missing_metadata():
    assert refresh_current_evidence._code_review_gate_artifact_summary({"status": "warn"}) == ""
    assert refresh_current_evidence._code_review_gate_artifact_summary({}) == ""


def test_normalize_utf8_bom_json_artifact_rewrites_bom_free(tmp_path):
    artifact = tmp_path / "code-review-gate-current.json"
    payload = {"status": "warn", "risk_score": 0.4}
    artifact.write_bytes(b"\xef\xbb\xbf" + _json_bytes(payload))

    result = refresh_current_evidence._normalize_utf8_bom_json_artifact(
        artifact,
        payload,
        name="code_review_gate_artifact_bom_normalize",
    )

    assert result is not None
    assert result.status == "ok"
    assert result.first_bytes == "7B 0A 20 20"
    assert artifact.read_bytes().startswith(b"{\n")
    assert json.loads(artifact.read_text(encoding="utf-8")) == payload


def test_browser_qa_artifact_summary_lists_retained_screenshot_paths():
    summary = refresh_current_evidence._browser_qa_artifact_summary(
        {
            "projects": [
                {
                    "path": "projects/hanwoo-dashboard",
                    "browser_app": True,
                    "freshest_screenshot_path": "output\\playwright\\browser-qa-hanwoo.png",
                    "freshest_screenshot_width": 390,
                    "freshest_screenshot_height": 844,
                    "freshest_screenshot_nonblank": True,
                },
                {
                    "path": "projects/knowledge-dashboard",
                    "browser_app": True,
                    "freshest_screenshot_path": "output/playwright/browser-qa-knowledge.png",
                    "freshest_screenshot_width": 390,
                    "freshest_screenshot_height": 844,
                    "freshest_screenshot_nonblank": True,
                },
                {
                    "path": "projects/hidden-browser",
                    "browser_app": True,
                    "freshest_screenshot_path": "output/playwright/browser-qa-hidden.png",
                },
            ],
        },
        limit=2,
    )

    assert (
        summary == "hanwoo-dashboard=output/playwright/browser-qa-hanwoo.png/390x844/nonblank true; "
        "knowledge-dashboard=output/playwright/browser-qa-knowledge.png/390x844/nonblank true; omitted 1"
    )


def test_browser_qa_artifact_summary_omits_missing_artifacts():
    assert refresh_current_evidence._browser_qa_artifact_summary({"projects": []}) == ""
    assert (
        refresh_current_evidence._browser_qa_artifact_summary(
            {"projects": [{"path": "projects/hanwoo-dashboard", "browser_app": True}]},
        )
        == ""
    )
    assert refresh_current_evidence._browser_qa_artifact_summary({}) == ""


def test_target_blocker_detail_summary_lists_scores_tasks_and_dirty_paths():
    readiness = {
        "projects": [
            {
                "name": "ready-clean",
                "score": 100,
                "state": "ready",
                "tasks": [],
                "dirty_paths": [],
            },
            {
                "name": "blocked-project",
                "score": 82,
                "state": "blocked",
                "tasks": [{"id": "T-251"}, {"id": "T-999"}, {"id": "T-1000"}],
                "dirty_paths": ["a", "b"],
            },
            {
                "name": "dirty-ready",
                "score": 92,
                "state": "ready",
                "tasks": [],
                "dirty_paths": ["c"],
            },
        ],
    }

    assert (
        refresh_current_evidence._target_blocker_detail_summary(readiness)
        == "blocked-project: score 82, state blocked, tasks T-251,T-999,+1, dirty 2; "
        "dirty-ready: score 92, dirty 1"
    )


def test_target_blocker_action_summary_maps_external_dirty_and_readiness_actions():
    readiness = {
        "projects": [
            {
                "name": "ready-clean",
                "score": 100,
                "state": "ready",
                "tasks": [],
                "dirty_paths": [],
            },
            {
                "name": "hanwoo-dashboard",
                "score": 82,
                "state": "blocked",
                "tasks": [{"id": "T-251"}],
                "dirty_paths": ["a"],
            },
            {
                "name": "blind-to-x",
                "score": 92,
                "state": "ready",
                "tasks": [],
                "dirty_paths": ["b"],
            },
            {
                "name": "knowledge-dashboard",
                "score": 92,
                "state": "ready",
                "tasks": [],
                "dirty_paths": [],
            },
        ],
    }

    assert (
        refresh_current_evidence._target_blocker_action_summary(readiness)
        == "hanwoo-dashboard -> wait for Supabase credential reset before live Prisma CRUD retry; "
        "blind-to-x -> clear target dirty paths and keep project QC/readiness evidence current; "
        "knowledge-dashboard -> refresh target readiness evidence and resolve score/state blockers"
    )


def test_browser_qa_project_summary_lists_project_screenshot_evidence():
    browser_qa = {
        "projects": [
            {
                "path": "projects/hanwoo-dashboard",
                "browser_app": True,
                "status": "covered",
                "fresh_nonblank_screenshot_count": 2,
                "current_screenshot_count": 3,
                "freshest_screenshot_age_days": 4,
            },
            {
                "path": "projects/api-only",
                "browser_app": False,
                "status": "missing",
            },
            {
                "path": "projects/word-chain",
                "browser_app": True,
                "status": "covered",
                "fresh_nonblank_screenshot_count": 1,
                "current_screenshot_count": 1,
                "freshest_screenshot_age_days": 0,
            },
        ],
    }

    assert (
        refresh_current_evidence._browser_qa_project_summary(browser_qa)
        == "hanwoo-dashboard=covered/fresh-nonblank2/shots3/age4d; "
        "word-chain=covered/fresh-nonblank1/shots1/age0d"
    )


def test_browser_qa_log_evidence_summary_lists_verified_log_counts():
    browser_qa = {
        "projects": [
            {
                "path": "projects/hanwoo-dashboard",
                "browser_app": True,
                "log_evidence_count": 118,
                "verified_log_evidence_count": 90,
            },
            {
                "path": "projects/api-only",
                "browser_app": False,
                "log_evidence_count": 8,
                "verified_log_evidence_count": 8,
            },
            {
                "path": "projects/word-chain",
                "browser_app": True,
                "log_evidence_count": 13,
                "verified_log_evidence_count": 13,
            },
            {
                "path": "projects/no-log",
                "browser_app": True,
                "log_evidence_count": 0,
                "verified_log_evidence_count": 0,
            },
        ],
    }

    assert (
        refresh_current_evidence._browser_qa_log_evidence_summary(browser_qa)
        == "hanwoo-dashboard=verified-logs90/118; word-chain=verified-logs13/13; omitted 1"
    )


def test_github_recommendation_summary_lists_actionable_inventory_recommendations():
    inventory = {
        "recommendations": [
            "Worktree is dirty; stage and commit only files owned by the current experiment.",
            "",
            "Keep current-head release gates visible.",
            "Refresh workflow evidence after push.",
        ],
    }

    assert (
        refresh_current_evidence._github_recommendation_summary(inventory)
        == "Worktree is dirty; stage and commit only files owned by the current experiment; "
        "Keep current-head release gates visible; omitted 1 more."
    )


def test_github_recommendation_summary_rewrites_stale_dirty_group_clause():
    inventory = {
        "recommendations": [
            (
                "Worktree is dirty; stage and commit only files owned by the current experiment. "
                "Dirty groups: project:blind-to-x=182, workspace-dashboard=72, root=58, "
                "workspace=46, auto-research=30."
            ),
        ],
    }

    summary = refresh_current_evidence._github_recommendation_summary(
        inventory,
        dirty_groups_summary=(
            "auto-research=30, workspace-code-review-gate=1, llm-wiki=5, workspace-dashboard=72, "
            "project:blind-to-x=182, project:hanwoo-dashboard=2, ai-context=11, execution=18, "
            "project:knowledge-dashboard=4, project:shorts-maker-v2=28, root=58, workspace=46"
        ),
    )

    assert "workspace-code-review-gate=1" in summary
    assert "project:shorts-maker-v2=28" in summary
    assert "project:hanwoo-dashboard=2" in summary
    assert "Dirty groups: project:blind-to-x=182, workspace-dashboard=72, root=58" not in summary


def test_dirty_groups_evidence_rewrites_stale_github_detail_clause():
    entries = [
        (
            "Worktree is dirty; stage and commit only files owned by the current experiment. "
            "Dirty groups: project:blind-to-x=182, workspace-dashboard=72, root=58, "
            "workspace=46, auto-research=30."
        ),
    ]

    rewritten = refresh_current_evidence._rewrite_dirty_groups_evidence(
        entries,
        (
            "auto-research=30, workspace-code-review-gate=1, llm-wiki=5, workspace-dashboard=72, "
            "project:blind-to-x=182, project:hanwoo-dashboard=2, ai-context=11, execution=18, "
            "project:knowledge-dashboard=4, project:shorts-maker-v2=28, root=58, workspace=46"
        ),
    )

    assert "workspace-code-review-gate=1" in rewritten[0]
    assert "project:shorts-maker-v2=28" in rewritten[0]
    assert "project:hanwoo-dashboard=2" in rewritten[0]
    assert "Dirty groups: project:blind-to-x=182, workspace-dashboard=72, root=58" not in rewritten[0]


def test_prompt_detail_blocker_rewrites_stale_dirty_group_clause():
    completion = {
        "status": "incomplete",
        "summary": {"item_count": 1, "complete_count": 0, "issue_count": 1, "blocked_count": 1},
        "items": [
            {
                "requirement": "Find GitHub-related projects.",
                "coverage": "partial",
                "blockers": [
                    (
                        "Worktree is dirty; stage and commit only files owned by the current experiment. "
                        "Dirty groups: project:blind-to-x=182, workspace-dashboard=72, root=58, "
                        "workspace=46, auto-research=30."
                    ),
                ],
                "passed": False,
            },
        ],
    }
    dirty_handoff_plan = {
        "group_order": [
            {"key": "auto-research", "path_count": 1},
            {"key": "project:blind-to-x", "path_count": 1},
            {"key": "project:shorts-maker-v2", "path_count": 1},
        ],
    }

    checklist = refresh_current_evidence._render_prompt_artifact_checklist(
        launch={},
        completion=completion,
        readiness={},
        selector={},
        browser_qa={},
        github_inventory={},
        dependency_freshness={},
        code_review_gate={},
        coverage={},
        menu={},
        menu_check={},
        approval={},
        release={},
        session_orient={},
        burndown={},
        dirty_handoff_plan=dirty_handoff_plan,
        debug_loop={},
        ab_task_id_advisory={},
        generated_at="2026-06-14T00:00:00Z",
    )

    assert "Dirty groups: auto-research=1, project:blind-to-x=1, project:shorts-maker-v2=1" in checklist
    assert "Dirty groups: project:blind-to-x=182, workspace-dashboard=72, root=58" not in checklist


def test_debug_blocker_title_summary_lists_blocker_titles_with_limit():
    debug_loop = {
        "summary": {
            "completion_blockers": [
                {"title": "Dirty Handoff Boundary Blocks New Product Edits."},
                {"title": "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker"},
                {"title": ""},
                {"title": "Current-HEAD GitHub Actions Cannot Be Proven Locally"},
                {"title": "Launch Completion Audit Remains Incomplete"},
            ],
        },
    }

    assert (
        refresh_current_evidence._debug_blocker_title_summary(debug_loop)
        == "Dirty Handoff Boundary Blocks New Product Edits; "
        "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker; "
        "Current-HEAD GitHub Actions Cannot Be Proven Locally; "
        "Launch Completion Audit Remains Incomplete."
    )


def test_debug_blocker_next_action_summary_lists_actions_with_limit():
    debug_loop = {
        "items": [
            {
                "title": "Dirty Handoff Boundary Blocks New Product Edits",
                "next_action": "Wait for explicit scoped staging/commit authorization.",
            },
            {
                "title": "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker",
                "next_action": "User resets Supabase credentials.",
            },
            {
                "title": "Current-HEAD GitHub Actions Cannot Be Proven Locally",
                "next_action": "Explicit push authorization or user push.",
            },
            {
                "title": "Launch Completion Audit Remains Incomplete",
                "next_action": "Keep blocked evidence current.",
            },
        ],
    }

    assert (
        refresh_current_evidence._debug_blocker_next_action_summary(debug_loop)
        == "Dirty Handoff Boundary Blocks New Product Edits -> "
        "Wait for explicit scoped staging/commit authorization; "
        "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker -> User resets Supabase credentials; "
        "Current-HEAD GitHub Actions Cannot Be Proven Locally -> Explicit push authorization or user push; "
        "Launch Completion Audit Remains Incomplete -> Keep blocked evidence current."
    )


def test_debug_blocker_next_action_summary_preserves_explicit_omission_limit():
    debug_loop = {
        "items": [
            {
                "title": "Dirty Handoff Boundary Blocks New Product Edits",
                "next_action": "Wait for explicit scoped staging/commit authorization.",
            },
            {
                "title": "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker",
                "next_action": "User resets Supabase credentials.",
            },
            {
                "title": "Current-HEAD GitHub Actions Cannot Be Proven Locally",
                "next_action": "Explicit push authorization or user push.",
            },
            {
                "title": "Launch Completion Audit Remains Incomplete",
                "next_action": "Keep blocked evidence current.",
            },
        ],
    }

    assert (
        refresh_current_evidence._debug_blocker_next_action_summary(debug_loop, limit=3)
        == "Dirty Handoff Boundary Blocks New Product Edits -> "
        "Wait for explicit scoped staging/commit authorization; "
        "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker -> User resets Supabase credentials; "
        "Current-HEAD GitHub Actions Cannot Be Proven Locally -> Explicit push authorization or user push; "
        "omitted 1 more."
    )


def test_debug_blocker_next_action_summary_omits_missing_actions():
    assert refresh_current_evidence._debug_blocker_next_action_summary({"items": [{"title": "Blocked"}]}) == ""


def test_dependency_peer_blocker_action_summary_lists_defer_counts():
    dependency_freshness = {
        "projects": [
            {
                "path": "projects/hanwoo-dashboard",
                "dependencies": [
                    {
                        "name": "eslint",
                        "peer_target_major": 10,
                        "peer_blocker_latest_check": "partial_upstream_support",
                        "peer_blocker_latest_supported_count": 1,
                        "peer_blocker_latest_blocked_count": 3,
                        "peer_blocker_latest_unavailable_count": 0,
                    },
                ],
            },
            {
                "path": "projects/knowledge-dashboard",
                "dependencies": [
                    {
                        "name": "eslint",
                        "peer_target_major": 10,
                        "peer_blocker_latest_check": "still_blocked",
                        "peer_blocker_latest_supported_count": 0,
                        "peer_blocker_latest_blocked_count": 3,
                        "peer_blocker_latest_unavailable_count": 0,
                    },
                ],
            },
        ],
    }

    assert (
        refresh_current_evidence._dependency_peer_blocker_action_summary(dependency_freshness)
        == "projects/hanwoo-dashboard eslint@10 -> defer major migration until upstream peer support "
        "(latest-supported 1, still-blocked 3, unavailable 0); "
        "projects/knowledge-dashboard eslint@10 -> defer major migration until upstream peer support "
        "(latest-supported 0, still-blocked 3, unavailable 0)"
    )


def test_release_commit_preview_summary_lists_ahead_commit_subjects():
    release = {
        "summary": {"commit_count": 4, "commit_omitted_count": 2},
        "git": {
            "commits_ahead_preview": [
                {"sha": "abc123456789", "subject": "feat: improve release checklist."},
                {"sha": "def67890", "subject": "fix: keep current-head gates visible"},
                {"sha": "", "subject": ""},
                {"sha": "99999999", "subject": "docs: update launch notes"},
            ],
        },
    }

    assert (
        refresh_current_evidence._release_commit_preview_summary(release, limit=2)
        == "shown 2/4; abc12345 feat: improve release checklist; "
        "def67890 fix: keep current-head gates visible; "
        "omitted 2 more."
    )


def test_release_llm_wiki_strict_evidence_summary_prefers_detail_section():
    release = {
        "summary": {
            "llm_wiki_strict_evidence_status": "fail",
            "llm_wiki_strict_evidence_head_matches_current": False,
            "llm_wiki_strict_evidence_unexpected_count": 3,
            "llm_wiki_strict_evidence_path": ".tmp/stale.json",
        },
        "llm_wiki_strict_evidence": {
            "available": True,
            "status": "pass",
            "head_matches_current": True,
            "unexpected_manifest_warning_count": 0,
            "path": ".tmp/llm-wiki-strict-audit-current.json",
        },
    }

    assert (
        refresh_current_evidence._release_llm_wiki_strict_evidence_summary(release)
        == "available true, status pass, head_matches_current true, unexpected 0, "
        "path .tmp/llm-wiki-strict-audit-current.json."
    )


def test_release_llm_wiki_strict_evidence_summary_uses_summary_fallback():
    release = {
        "summary": {
            "llm_wiki_strict_evidence_status": "pass",
            "llm_wiki_strict_evidence_head_matches_current": True,
            "llm_wiki_strict_evidence_unexpected_count": 0,
            "llm_wiki_strict_evidence_path": ".tmp/llm-wiki-strict-audit-current.json",
        },
    }

    assert (
        refresh_current_evidence._release_llm_wiki_strict_evidence_summary(release)
        == "status pass, head_matches_current true, unexpected 0, "
        "path .tmp/llm-wiki-strict-audit-current.json."
    )


def test_release_packet_blocker_summary_combines_dirty_actions_and_external_boundaries():
    release_summary = {
        "dirty_count": 457,
        "current_head_run_count": 0,
        "current_head_required_success_count": 0,
        "unproven_workflow_count": 2,
        "external_blocker_ids": ["T-251"],
    }

    assert (
        refresh_current_evidence._release_packet_blocker_summary(release_summary, {})
        == "dirty worktree paths 457; current-head Actions unavailable until explicit push/user push; "
        "external/user-owned blocker(s) T-251."
    )


def test_release_packet_blocker_summary_omits_when_no_blockers():
    release_summary = {
        "dirty_count": 0,
        "current_head_run_count": 2,
        "current_head_required_success_count": 2,
        "unproven_workflow_count": 2,
        "external_blocker_ids": [],
    }

    assert refresh_current_evidence._release_packet_blocker_summary(release_summary, {}) == ""


def test_release_actions_summary_shows_unpushed_dirty_boundary_when_no_runs():
    release_actions = {
        "available": True,
        "run_count": 0,
        "required_count": 2,
        "required_run_count": 0,
        "required_success_count": 0,
        "missing_required_workflows": ["root-quality-gate", "active-project-matrix"],
        "successful_required_workflows": [],
    }
    release_summary = {"ahead_count": 924, "dirty_count": 457}

    assert (
        refresh_current_evidence._release_actions_summary(release_actions, release_summary)
        == "available true, runs 0, required runs 0/2, success 0/2, successful none, "
        "missing root-quality-gate, active-project-matrix, current-head boundary ahead 924/dirty 457."
    )


def test_release_actions_summary_omits_boundary_when_runs_exist():
    release_actions = {
        "available": True,
        "run_count": 2,
        "required_count": 2,
        "required_run_count": 2,
        "required_success_count": 2,
        "missing_required_workflows": [],
        "successful_required_workflows": ["root-quality-gate", "active-project-matrix"],
    }
    release_summary = {"ahead_count": 924, "dirty_count": 457}

    assert (
        refresh_current_evidence._release_actions_summary(release_actions, release_summary)
        == "available true, runs 2, required runs 2/2, success 2/2, "
        "successful root-quality-gate, active-project-matrix, missing none."
    )


def test_release_actions_probe_summary_shows_current_head_probe_boundary():
    release_actions = {
        "head_sha": "3823a80f6c494cf46b3855a31ec871e49730e8b6",
        "command": (
            "gh run list --commit 3823a80f6c494cf46b3855a31ec871e49730e8b6 --limit 20 "
            "--json databaseId,name,workflowName,status,conclusion,headSha,createdAt,url"
        ),
        "returncode": 0,
        "limit": 20,
        "run_count": 0,
        "runs_preview": [],
    }

    assert (
        refresh_current_evidence._release_actions_probe_summary(release_actions)
        == "head 3823a80f, returncode 0, runs_preview 0/20, run_count 0, "
        "command gh run list --commit 3823a80f6c494cf46b3855a31ec871e49730e8b6 --limit 20."
    )


def test_release_actions_probe_summary_omits_when_no_probe_evidence():
    assert refresh_current_evidence._release_actions_probe_summary({}) == ""


def test_release_authorization_guardrail_summary_previews_guardrail_text():
    summary = refresh_current_evidence._release_authorization_guardrail_summary(
        {
            "push_required": True,
            "allowed_without_explicit_user_authorization": False,
            "post_push_gates": ["root-quality-gate", "active-project-matrix"],
            "guardrails": [
                "Do not push without explicit user authorization.",
                "Wait for required workflows on the exact current HEAD.",
                "Do not retry external T-251 until credentials are reset.",
            ],
        }
    )

    assert summary == (
        "push_required true, allowed_without_explicit_user_authorization false, "
        "post-push gates root-quality-gate, active-project-matrix, guardrails 3, "
        "shown 3/3: Do not push without explicit user authorization.; "
        "Wait for required workflows on the exact current HEAD.; "
        "Do not retry external T-251 until credentials are reset."
    )


def test_release_authorization_guardrail_summary_preserves_explicit_omission_limit():
    summary = refresh_current_evidence._release_authorization_guardrail_summary(
        {
            "push_required": True,
            "allowed_without_explicit_user_authorization": False,
            "post_push_gates": ["root-quality-gate", "active-project-matrix"],
            "guardrails": [
                "Do not push without explicit user authorization.",
                "Wait for required workflows on the exact current HEAD.",
                "Do not retry external T-251 until credentials are reset.",
            ],
        },
        limit=2,
    )

    assert summary == (
        "push_required true, allowed_without_explicit_user_authorization false, "
        "post-push gates root-quality-gate, active-project-matrix, guardrails 3, "
        "shown 2/3: Do not push without explicit user authorization.; "
        "Wait for required workflows on the exact current HEAD., omitted 1."
    )


def test_release_authorization_guardrail_summary_omits_missing_guardrail_text():
    assert refresh_current_evidence._release_authorization_guardrail_summary({}) == ""


def test_release_commit_preview_summary_preserves_korean_commit_subjects():
    release = {
        "summary": {"commit_count": 2},
        "git": {
            "commits_ahead_preview": [
                {"sha": "3823a80f", "subject": "[ai-context] 세션 로그 업데이트"},
                {
                    "sha": "7001b83b",
                    "subject": "[shorts-maker-v2] T-2423 CTA 정책 단일화 + 렌더 전 조기 kill 게이트",
                },
            ],
        },
    }

    summary = refresh_current_evidence._release_commit_preview_summary(release)

    assert "세션 로그 업데이트" in summary
    assert "정책 단일화" in summary
    assert "?몄뀡" not in summary
    assert "濡쒓렇" not in summary


def test_release_commit_encoding_summary_reports_unicode_health():
    release = {
        "git": {
            "commits_ahead_preview": [
                {"sha": "3823a80f", "subject": "[ai-context] 세션 로그 업데이트"},
                {"sha": "7001b83b", "subject": "[shorts-maker-v2] T-2423 CTA 정책 단일화"},
                {"sha": "24830b9f", "subject": "T-2264 extract reasoning JSON parser stages"},
            ],
        },
    }

    assert refresh_current_evidence._release_commit_encoding_summary(release) == (
        "subjects 3, non-ascii 2, replacement chars 0, mojibake markers 0; "
        "non-ascii examples 3823a80f [ai-context] 세션 로그 업데이트, "
        "7001b83b [shorts-maker-v2] T-2423 CTA 정책 단일화."
    )


def test_release_commit_encoding_summary_reports_mojibake_markers():
    release = {
        "git": {
            "commits_ahead_preview": [
                {"sha": "3823a80f", "subject": "[ai-context] �몄뀡 濡쒓렇"},
                {"sha": "7001b83b", "subject": "[shorts-maker-v2] T-2423 CTA 뺤콉"},
            ],
        },
    }

    summary = refresh_current_evidence._release_commit_encoding_summary(release)

    assert summary.startswith("subjects 2, non-ascii 2, replacement chars 1, mojibake markers 2; ")
    assert "non-ascii examples 3823a80f [ai-context]" in summary
    assert "7001b83b [shorts-maker-v2] T-2423 CTA" in summary


def test_release_commit_encoding_summary_reports_omitted_non_ascii_examples():
    release = {
        "git": {
            "commits_ahead_preview": [
                {"sha": "00000001", "subject": "release alpha \uac00"},
                {"sha": "00000002", "subject": "release beta \ub098"},
                {"sha": "00000003", "subject": "release gamma \ub2e4"},
            ],
        },
    }

    summary = refresh_current_evidence._release_commit_encoding_summary(release, example_limit=1)

    assert "subjects 3, non-ascii 3" in summary
    assert "non-ascii examples 00000001 release alpha \uac00, omitted 2 non-ascii examples." in summary
    assert "00000002 release beta \ub098" not in summary


def test_release_commit_encoding_summary_limits_non_ascii_examples():
    release = {
        "git": {
            "commits_ahead_preview": [
                {"sha": f"{index:08x}", "subject": f"릴리스 증거 {index}"} for index in range(1, 8)
            ],
        },
    }

    summary = refresh_current_evidence._release_commit_encoding_summary(release, example_limit=3)

    assert "subjects 7, non-ascii 7" in summary
    assert "00000001 릴리스 증거 1" in summary
    assert "00000003 릴리스 증거 3" in summary
    assert "00000004 릴리스 증거 4" not in summary


def test_approval_phase_summary_reports_omitted_phase_totals():
    approval = {
        "status": "ok",
        "pathspec_results": [
            {
                "pathspec": ".tmp/approve-ai-context-relay-update.pathspec",
                "unique_path_count": 3,
                "covered_dirty_count": 3,
            },
            {
                "pathspec": ".tmp/approve-auto-research-scoped-authorization-menu.pathspec",
                "unique_path_count": 7,
                "covered_dirty_count": 7,
            },
            {
                "pathspec": ".tmp/approve-blind-to-x-draft-prompts.pathspec",
                "unique_path_count": 11,
                "covered_dirty_count": 11,
            },
            {
                "pathspec": ".tmp/approve-shorts-maker-v2-content-tools.pathspec",
                "unique_path_count": 13,
                "covered_dirty_count": 13,
            },
        ],
    }

    summary = refresh_current_evidence._approval_phase_summary(approval, "2026-06-14T00:00:00Z", limit=2)

    assert summary == (
        "phase0_context_relay=3 dirty/1 tokens; "
        "phase1_loop_tooling=7 dirty/1 tokens; "
        "omitted 2 phases/24 dirty/2 tokens"
    )


def test_approval_phase_summary_reports_coverage_and_phase_reference_totals():
    approval = {
        "status": "ok",
        "dirty_count": 20,
        "covered_dirty_count": 20,
        "pathspec_results": [
            {
                "pathspec": ".tmp/approve-ai-context-relay-update.pathspec",
                "unique_path_count": 3,
                "covered_dirty_count": 3,
            },
            {
                "pathspec": ".tmp/approve-auto-research-scoped-authorization-menu.pathspec",
                "unique_path_count": 7,
                "covered_dirty_count": 7,
            },
            {
                "pathspec": ".tmp/approve-blind-to-x-draft-prompts.pathspec",
                "unique_path_count": 11,
                "covered_dirty_count": 11,
            },
            {
                "pathspec": ".tmp/approve-shorts-maker-v2-content-tools.pathspec",
                "unique_path_count": 13,
                "covered_dirty_count": 13,
            },
        ],
    }

    summary = refresh_current_evidence._approval_phase_summary(approval, "2026-06-14T00:00:00Z", limit=2)

    assert summary.endswith("coverage 20/20, phase refs 34")


def test_approval_phase_reference_summary_lists_phase_refs_and_overlap():
    approval = {
        "status": "ok",
        "dirty_count": 20,
        "covered_dirty_count": 20,
        "pathspec_results": [
            {
                "pathspec": ".tmp/approve-ai-context-relay-update.pathspec",
                "unique_path_count": 3,
                "covered_dirty_count": 3,
            },
            {
                "pathspec": ".tmp/approve-auto-research-scoped-authorization-menu.pathspec",
                "unique_path_count": 7,
                "covered_dirty_count": 7,
            },
            {
                "pathspec": ".tmp/approve-blind-to-x-draft-prompts.pathspec",
                "unique_path_count": 11,
                "covered_dirty_count": 11,
            },
            {
                "pathspec": ".tmp/approve-shorts-maker-v2-content-tools.pathspec",
                "unique_path_count": 13,
                "covered_dirty_count": 13,
            },
        ],
    }

    summary = refresh_current_evidence._approval_phase_reference_summary(
        approval,
        "2026-06-14T00:00:00Z",
    )

    assert summary == (
        "phase0_context_relay=3; phase1_loop_tooling=7; "
        "phase2_blind_to_x_dirty_product_paths=11; phase3_shorts_maker_v2_dirty_product_paths=13; "
        "unique coverage 20/20, overlap refs 14"
    )


def test_approval_phase_reference_summary_preserves_explicit_omission_limit():
    approval = {
        "status": "ok",
        "dirty_count": 20,
        "covered_dirty_count": 20,
        "pathspec_results": [
            {
                "pathspec": ".tmp/approve-ai-context-relay-update.pathspec",
                "unique_path_count": 3,
                "covered_dirty_count": 3,
            },
            {
                "pathspec": ".tmp/approve-auto-research-scoped-authorization-menu.pathspec",
                "unique_path_count": 7,
                "covered_dirty_count": 7,
            },
            {
                "pathspec": ".tmp/approve-blind-to-x-draft-prompts.pathspec",
                "unique_path_count": 11,
                "covered_dirty_count": 11,
            },
            {
                "pathspec": ".tmp/approve-shorts-maker-v2-content-tools.pathspec",
                "unique_path_count": 13,
                "covered_dirty_count": 13,
            },
        ],
    }

    summary = refresh_current_evidence._approval_phase_reference_summary(
        approval,
        "2026-06-14T00:00:00Z",
        limit=2,
    )

    assert summary == (
        "phase0_context_relay=3; phase1_loop_tooling=7; omitted 2 phases/24 refs; "
        "unique coverage 20/20, overlap refs 14"
    )


def test_approval_phase_token_summary_lists_visible_phase_tokens():
    approval = {
        "status": "ok",
        "pathspec_results": [
            {
                "pathspec": ".tmp/approve-ai-context-relay-update.pathspec",
                "unique_path_count": 3,
                "covered_dirty_count": 3,
            },
            {
                "pathspec": ".tmp/approve-auto-research-scoped-authorization-menu.pathspec",
                "unique_path_count": 7,
                "covered_dirty_count": 7,
            },
            {
                "pathspec": ".tmp/approve-blind-to-x-draft-prompts.pathspec",
                "unique_path_count": 11,
                "covered_dirty_count": 11,
            },
            {
                "pathspec": ".tmp/approve-blind-to-x-draft-generator-failure-summary.pathspec",
                "unique_path_count": 5,
                "covered_dirty_count": 5,
            },
            {
                "pathspec": ".tmp/approve-shorts-maker-v2-content-tools.pathspec",
                "unique_path_count": 13,
                "covered_dirty_count": 13,
            },
        ],
    }

    summary = refresh_current_evidence._approval_phase_token_summary(
        approval,
        "2026-06-14T00:00:00Z",
        phase_limit=2,
        token_limit=1,
    )

    assert summary == (
        "phase0_context_relay: APPROVE_AI_CONTEXT_RELAY_UPDATE; "
        "phase1_loop_tooling: APPROVE_AUTO_RESEARCH_SCOPED_AUTHORIZATION_MENU; "
        "omitted 2 phases"
    )


def test_release_commit_preview_summary_default_uses_packet_preview_depth():
    release = {
        "summary": {"commit_count": 36, "commit_omitted_count": 1},
        "git": {
            "commits_ahead_preview": [
                {"sha": f"{index:08x}", "subject": f"feat: release evidence {index}"} for index in range(1, 37)
            ],
        },
    }

    summary = refresh_current_evidence._release_commit_preview_summary(release)

    assert "00000001 feat: release evidence 1" in summary
    assert "00000023 feat: release evidence 35" in summary
    assert "00000024 feat: release evidence 36" not in summary
    assert summary.startswith("shown 35/36; ")
    assert summary.endswith("omitted 1 more.")


def test_selector_dirty_groups_summary_default_covers_current_handoff_scale():
    selector_selected = {
        "evidence": [
            (
                "dirty groups: project:blind-to-x=182, workspace-dashboard=72, root=58, "
                "workspace=46, auto-research=30, execution=18, ai-context=11, llm-wiki=5, "
                "project:knowledge-dashboard=4, project:shorts-maker-v2=28, "
                "project:hanwoo-dashboard=2, workspace-code-review-gate=1, extra=1"
            ),
        ],
    }

    summary = refresh_current_evidence._selector_dirty_groups_summary(selector_selected)

    assert "project:blind-to-x=182" in summary
    assert "project:shorts-maker-v2=28" in summary
    assert "workspace-code-review-gate=1" in summary
    assert "extra=1" not in summary
    assert summary.endswith("omitted 1 more")


def test_dirty_handoff_groups_summary_uses_plan_counts_before_selector_fallback():
    dirty_handoff_plan = {
        "group_order": [
            {"key": "auto-research", "path_count": 30},
            {"key": "workspace-code-review-gate", "path_count": 1},
            {"key": "llm-wiki", "path_count": 5},
            {"key": "workspace-dashboard", "path_count": 72},
            {"key": "project:blind-to-x", "path_count": 182},
            {"key": "project:hanwoo-dashboard", "path_count": 2},
            {"key": "ai-context", "path_count": 11},
            {"key": "execution", "path_count": 18},
            {"key": "project:knowledge-dashboard", "path_count": 4},
            {"key": "project:shorts-maker-v2", "path_count": 28},
            {"key": "root", "path_count": 58},
            {"key": "workspace", "path_count": 46},
            {"key": "extra", "path_count": 1},
        ],
    }

    summary = refresh_current_evidence._dirty_handoff_groups_summary(dirty_handoff_plan)

    assert summary.startswith("auto-research=30, workspace-code-review-gate=1")
    assert "project:shorts-maker-v2=28" in summary
    assert "workspace=46" in summary
    assert "extra=1" not in summary
    assert summary.endswith("omitted 1 more")


def test_release_commit_preview_summary_derives_total_from_omitted_count():
    release = {
        "summary": {"commit_omitted_count": 3},
        "git": {
            "commits_ahead_preview": [
                {"sha": "abc12345", "subject": "feat: visible release commit"},
                {"sha": "def67890", "subject": "fix: another visible commit"},
            ],
        },
    }

    assert (
        refresh_current_evidence._release_commit_preview_summary(release)
        == "shown 2/5; abc12345 feat: visible release commit; "
        "def67890 fix: another visible commit; omitted 3 more."
    )


def test_ab_manifest_task_id_advisory_reports_next_id_and_collisions(tmp_path):
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir()
    for name in [
        "ab-manifest-t2538-first.json",
        "ab-manifest-t2538-second.json",
        "ab-manifest-t2539-latest.json",
        "ab-decision-t2540-result.json",
        "ab-manifest-helper-direct.json",
    ]:
        (tmp_dir / name).write_text("{}\n", encoding="utf-8")

    advisory = refresh_current_evidence._ab_manifest_task_id_advisory(tmp_path)

    assert advisory == {
        "highest_task_id": 2539,
        "next_task_id": 2540,
        "manifest_count": 3,
        "scanned_manifest_count": 4,
        "collision_group_count": 1,
        "collision_task_ids": [2538],
        "collision_examples": [
            {
                "task_id": 2538,
                "path_count": 2,
                "paths": [
                    (tmp_dir / "ab-manifest-t2538-first.json").as_posix(),
                    (tmp_dir / "ab-manifest-t2538-second.json").as_posix(),
                ],
            }
        ],
        "collision_omitted_examples": [],
        "latest_manifest_paths": [(tmp_dir / "ab-manifest-t2539-latest.json").as_posix()],
        "latest_manifest_count": 1,
        "latest_decision_path": "",
        "latest_decision": {},
        "latest_decision_count": 0,
    }


def test_ab_manifest_collision_summary_reports_latest_examples(tmp_path):
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir()
    for name in [
        "ab-manifest-t2537-first.json",
        "ab-manifest-t2537-second.json",
        "ab-manifest-t2538-first.json",
        "ab-manifest-t2538-second.json",
        "ab-manifest-t2539-first.json",
        "ab-manifest-t2539-second.json",
        "ab-manifest-t2540-first.json",
        "ab-manifest-t2540-second.json",
        "ab-manifest-t2541-latest.json",
    ]:
        (tmp_dir / name).write_text("{}\n", encoding="utf-8")

    summary = refresh_current_evidence._ab_manifest_collision_summary(
        refresh_current_evidence._ab_manifest_task_id_advisory(tmp_path),
    )

    assert "T-2540 (2 files: ab-manifest-t2540-first.json, ab-manifest-t2540-second.json)" in summary
    assert "T-2539 (2 files: ab-manifest-t2539-first.json, ab-manifest-t2539-second.json)" in summary
    assert "T-2538 (2 files: ab-manifest-t2538-first.json, ab-manifest-t2538-second.json)" in summary
    assert summary.startswith("shown 4/4; ")
    assert "T-2537 (2 files: ab-manifest-t2537-first.json, ab-manifest-t2537-second.json)" in summary
    assert "omitted" not in summary


def test_ab_manifest_collision_summary_uses_current_wider_default_preview(tmp_path):
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir()
    for task_id in range(2601, 2613):
        (tmp_dir / f"ab-manifest-t{task_id}-first.json").write_text("{}\n", encoding="utf-8")
        (tmp_dir / f"ab-manifest-t{task_id}-second.json").write_text("{}\n", encoding="utf-8")

    summary = refresh_current_evidence._ab_manifest_collision_summary(
        refresh_current_evidence._ab_manifest_task_id_advisory(tmp_path),
    )

    assert summary.startswith("shown 10/12; ")
    assert "T-2612 (2 files: ab-manifest-t2612-first.json, ab-manifest-t2612-second.json)" in summary
    assert "T-2603 (2 files: ab-manifest-t2603-first.json, ab-manifest-t2603-second.json)" in summary
    assert "omitted 2: T-2602 (2 files: ab-manifest-t2602-first.json, ab-manifest-t2602-second.json)" in summary
    assert "T-2601 (2 files: ab-manifest-t2601-first.json, ab-manifest-t2601-second.json)" in summary


def test_ab_manifest_collision_summary_limits_hidden_group_preview(tmp_path):
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir()
    for task_id in range(2530, 2542):
        (tmp_dir / f"ab-manifest-t{task_id}-first.json").write_text("{}\n", encoding="utf-8")
        (tmp_dir / f"ab-manifest-t{task_id}-second.json").write_text("{}\n", encoding="utf-8")

    summary = refresh_current_evidence._ab_manifest_collision_summary(
        refresh_current_evidence._ab_manifest_task_id_advisory(tmp_path, example_limit=3, omitted_limit=5),
    )

    assert "shown 3/12" in summary
    assert "omitted 9: T-2538 (2 files: ab-manifest-t2538-first.json, ab-manifest-t2538-second.json)" in summary
    assert "T-2534 (2 files: ab-manifest-t2534-first.json, ab-manifest-t2534-second.json)" in summary
    assert "T-2533" not in summary
    assert "omitted-more 4." in summary


def test_ab_manifest_collision_summary_default_expands_omitted_group_preview(tmp_path):
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir()
    for task_id in range(2500, 2542):
        (tmp_dir / f"ab-manifest-t{task_id}-first.json").write_text("{}\n", encoding="utf-8")
        (tmp_dir / f"ab-manifest-t{task_id}-second.json").write_text("{}\n", encoding="utf-8")

    summary = refresh_current_evidence._ab_manifest_collision_summary(
        refresh_current_evidence._ab_manifest_task_id_advisory(tmp_path),
    )

    assert "shown 10/42" in summary
    assert "omitted 32: T-2531 (2 files: ab-manifest-t2531-first.json, ab-manifest-t2531-second.json)" in summary
    assert "T-2512 (2 files: ab-manifest-t2512-first.json, ab-manifest-t2512-second.json)" in summary
    assert "T-2511" not in summary
    assert "omitted-more 12." in summary


def test_ab_manifest_collision_omission_summary_lists_hidden_task_ids(tmp_path):
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir()
    for task_id in range(2529, 2542):
        (tmp_dir / f"ab-manifest-t{task_id}-first.json").write_text("{}\n", encoding="utf-8")
        (tmp_dir / f"ab-manifest-t{task_id}-second.json").write_text("{}\n", encoding="utf-8")

    summary = refresh_current_evidence._ab_manifest_collision_omission_summary(
        refresh_current_evidence._ab_manifest_task_id_advisory(tmp_path),
        shown_limit=3,
        limit=4,
    )

    assert summary == "T-2538, T-2537, T-2536, T-2535; omitted 6 more."


def test_ab_manifest_collision_omission_summary_default_covers_current_scale(tmp_path):
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir()
    for task_id in range(2478, 2542):
        (tmp_dir / f"ab-manifest-t{task_id}-first.json").write_text("{}\n", encoding="utf-8")
        (tmp_dir / f"ab-manifest-t{task_id}-second.json").write_text("{}\n", encoding="utf-8")

    summary = refresh_current_evidence._ab_manifest_collision_omission_summary(
        refresh_current_evidence._ab_manifest_task_id_advisory(tmp_path),
        shown_limit=3,
    )

    assert "T-2538" in summary
    assert "T-2478" in summary
    assert "omitted" not in summary


def test_prompt_checklist_labels_ab_collision_hidden_task_ids():
    checklist = refresh_current_evidence._render_prompt_artifact_checklist(
        launch={},
        completion={},
        readiness={},
        selector={},
        session_orient={},
        dirty_handoff_plan={},
        github_inventory={},
        browser_qa={},
        dependency_freshness={},
        code_review_gate={},
        coverage={},
        menu={},
        menu_check={},
        release={},
        approval={},
        burndown={},
        debug_loop={},
        ab_task_id_advisory={
            "highest_task_id": 2541,
            "next_task_id": 2542,
            "manifest_count": 12,
            "scanned_manifest_count": 12,
            "collision_group_count": 6,
            "collision_task_ids": [2541, 2540, 2539, 2538, 2537, 2536],
            "collision_examples": [],
            "collision_omitted_examples": [],
        },
        generated_at="2026-06-14T00:00:00Z",
    )

    assert "A/B collision hidden task ids: T-2538, T-2537, T-2536." in checklist
    assert "A/B collision task ids omitted:" not in checklist


def test_ab_latest_task_collision_summary_reports_selected_collision_files():
    advisory = {
        "highest_task_id": 2612,
        "collision_task_ids": [2612, 2526],
        "collision_examples": [
            {
                "task_id": 2612,
                "path_count": 2,
                "paths": [
                    ".tmp/ab-manifest-t2612-ab-collision-omitted-more-label.json",
                    ".tmp/ab-manifest-t2612-release-commit-korean-subject-regression.json",
                ],
            },
        ],
    }

    assert (
        refresh_current_evidence._ab_latest_task_collision_summary(advisory) == "T-2612 has 2 manifest files: "
        "ab-manifest-t2612-ab-collision-omitted-more-label.json, "
        "ab-manifest-t2612-release-commit-korean-subject-regression.json."
    )


def test_ab_latest_task_collision_summary_omits_non_colliding_latest_task():
    advisory = {
        "highest_task_id": 2613,
        "collision_task_ids": [2612, 2526],
        "collision_examples": [{"task_id": 2612, "path_count": 2, "paths": ["first", "second"]}],
    }

    assert refresh_current_evidence._ab_latest_task_collision_summary(advisory) == ""


def test_ab_latest_decision_summary_reports_decision_gate_counts(tmp_path):
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir()
    (tmp_dir / "ab-manifest-t2632-latest-decision-summary.json").write_text("{}\n", encoding="utf-8")
    (tmp_dir / "ab-decision-t2632-latest-decision-summary.json").write_text(
        json.dumps(
            {
                "decision": "adopt_candidate",
                "reason": "candidate improved weighted score",
                "score_delta": 0.28,
                "failed_gates": [],
                "warnings": ["non blocking note"],
            },
        )
        + "\n",
        encoding="utf-8",
    )

    advisory = refresh_current_evidence._ab_manifest_task_id_advisory(tmp_path)
    summary = refresh_current_evidence._ab_latest_decision_summary(advisory)

    assert summary == (
        "T-2632 adopt_candidate, score_delta 0.28, failed_gates 0, warnings 1, "
        "reason candidate improved weighted score, artifact ab-decision-t2632-latest-decision-summary.json."
    )
    assert refresh_current_evidence._ab_latest_manifest_summary(advisory) == (
        "T-2632 artifact ab-manifest-t2632-latest-decision-summary.json, manifest files 1."
    )


def test_ab_latest_decision_summary_omits_missing_decision():
    assert refresh_current_evidence._ab_latest_decision_summary({"highest_task_id": 2632}) == ""


def test_ab_latest_manifest_summary_reports_latest_manifest_path():
    summary = refresh_current_evidence._ab_latest_manifest_summary(
        {
            "highest_task_id": 2677,
            "latest_manifest_paths": [".tmp/ab-manifest-t2677-release-packet-blocker-summary.json"],
            "latest_manifest_count": 1,
        },
    )

    assert summary == "T-2677 artifact ab-manifest-t2677-release-packet-blocker-summary.json, manifest files 1."


def test_ab_latest_manifest_summary_reports_latest_collision_files():
    summary = refresh_current_evidence._ab_latest_manifest_summary(
        {
            "highest_task_id": 2676,
            "latest_manifest_paths": [
                ".tmp/ab-manifest-t2676-browser-qa-log-evidence-summary.json",
                ".tmp/ab-manifest-t2676-release-packet-blocker-summary.json",
            ],
            "latest_manifest_count": 2,
        },
    )

    assert summary == (
        "T-2676 artifact ab-manifest-t2676-browser-qa-log-evidence-summary.json, "
        "ab-manifest-t2676-release-packet-blocker-summary.json, manifest files 2."
    )


def test_ab_latest_manifest_summary_omits_missing_manifest():
    assert refresh_current_evidence._ab_latest_manifest_summary({"highest_task_id": 2677}) == ""


def test_ab_manifest_collision_omission_evidence_expands_hidden_task_ids():
    entries = [
        "A/B manifest task id collision detected for T-2600: first, second.",
        "A/B manifest task id collision summary omitted 2 older collision group(s).",
        "Latest A/B manifest selection used task id T-2601.",
    ]
    advisory = {"collision_task_ids": [2600, 2599, 2598, 2597, 2596, 2595, 2594]}

    expanded = refresh_current_evidence._expand_ab_collision_omission_evidence(entries, advisory)

    assert expanded == [
        "A/B manifest task id collision detected for T-2600: first, second.",
        "A/B manifest task id collision hidden task ids: T-2595, T-2594.",
        "Latest A/B manifest selection used task id T-2601.",
    ]


def test_ab_manifest_collision_omission_evidence_rewrites_stale_detail_ids():
    entries = [
        "A/B manifest task id collision detected for T-2526: first, second.",
        "A/B manifest task id collision omitted task ids: T-2505, T-2498.",
        "Latest A/B manifest selection used task id T-2609.",
    ]
    advisory = {
        "collision_task_ids": [
            2526,
            2523,
            2519,
            2517,
            2515,
            2505,
            2498,
            2215,
            2145,
        ],
    }

    expanded = refresh_current_evidence._expand_ab_collision_omission_evidence(entries, advisory)

    assert expanded == [
        "A/B manifest task id collision detected for T-2526: first, second.",
        "A/B manifest task id collision hidden task ids: T-2505, T-2498, T-2215, T-2145.",
        "Latest A/B manifest selection used task id T-2609.",
    ]


def test_ab_manifest_collision_omission_evidence_rewrites_hidden_detail_ids():
    entries = [
        "A/B manifest task id collision detected for T-2526: first, second.",
        "A/B manifest task id collision hidden task ids: T-2505, T-2498.",
        "Latest A/B manifest selection used task id T-2609.",
    ]
    advisory = {
        "collision_task_ids": [
            2526,
            2523,
            2519,
            2517,
            2515,
            2505,
            2498,
            2215,
            2145,
        ],
    }

    expanded = refresh_current_evidence._expand_ab_collision_omission_evidence(entries, advisory)

    assert expanded == [
        "A/B manifest task id collision detected for T-2526: first, second.",
        "A/B manifest task id collision hidden task ids: T-2505, T-2498, T-2215, T-2145.",
        "Latest A/B manifest selection used task id T-2609.",
    ]


def test_recommended_authorization_files_summary_lists_default_full_scale():
    summary = refresh_current_evidence._recommended_authorization_files_summary(
        {
            "files": [
                ".ai/CONTEXT.md",
                ".ai/HANDOFF.md",
                ".ai/TASKS.md",
                ".ai/SESSION_LOG.md",
            ],
        },
    )

    assert summary == "shown 4/4: .ai/CONTEXT.md, .ai/HANDOFF.md, .ai/TASKS.md, .ai/SESSION_LOG.md."


def test_recommended_authorization_files_summary_limits_omitted_preview():
    summary = refresh_current_evidence._recommended_authorization_files_summary(
        {
            "files": [
                ".ai/CONTEXT.md",
                ".ai/HANDOFF.md",
                ".ai/TASKS.md",
                ".ai/SESSION_LOG.md",
                ".ai/PROJECTS.md",
                ".ai/DECISIONS.md",
                ".ai/TOOL_MATRIX.md",
            ],
        },
        limit=3,
    )

    assert (
        summary == "shown 3/7: .ai/CONTEXT.md, .ai/HANDOFF.md, .ai/TASKS.md, omitted 4: "
        ".ai/SESSION_LOG.md, .ai/PROJECTS.md, .ai/DECISIONS.md, omitted-more 1."
    )


def test_recommended_authorization_files_summary_omits_missing_files():
    assert refresh_current_evidence._recommended_authorization_files_summary({"files": []}) == ""
    assert refresh_current_evidence._recommended_authorization_files_summary({}) == ""


def test_authorization_options_skip_zero_dirty_staging_tokens():
    menu = {
        "recommended": {"token": "APPROVE_AI_CONTEXT_RELAY_UPDATE", "pathspec": ".tmp/approve-ai-context.pathspec"},
        "one_line_user_options": [
            "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            "APPROVE_ZERO_DIRTY_SCOPE",
            "APPROVE_POSITIVE_DIRTY_SCOPE",
            "APPROVE_TMP_STALE_PYTEST_CLEANUP",
            "STOP",
        ],
        "also_available": [
            {
                "token": "APPROVE_ZERO_DIRTY_SCOPE",
                "pathspec": ".tmp/approve-zero-dirty-scope.pathspec",
                "classification": "verified_existing_packet",
            },
            {
                "token": "APPROVE_POSITIVE_DIRTY_SCOPE",
                "pathspec": ".tmp/approve-positive-dirty-scope.pathspec",
                "classification": "verified_existing_packet",
            },
        ],
    }
    approval = {
        "pathspec_results": [
            {"pathspec": "approve-ai-context.pathspec", "covered_dirty_count": 2},
            {"pathspec": "approve-zero-dirty-scope.pathspec", "covered_dirty_count": 0},
            {"pathspec": "approve-positive-dirty-scope.pathspec", "covered_dirty_count": 3},
        ],
    }

    tokens, total = refresh_current_evidence._authorization_option_tokens(menu, approval=approval)

    assert "APPROVE_ZERO_DIRTY_SCOPE" not in tokens
    assert tokens == [
        "APPROVE_AI_CONTEXT_RELAY_UPDATE",
        "APPROVE_POSITIVE_DIRTY_SCOPE",
        "APPROVE_TMP_STALE_PYTEST_CLEANUP",
    ]
    assert total == 3


def test_authorization_option_coverage_summary_lists_all_current_tokens():
    menu = {
        "recommended": {"token": "APPROVE_AI_CONTEXT_RELAY_UPDATE", "pathspec": ".tmp/approve-ai-context.pathspec"},
        "also_available": [
            {"token": "APPROVE_OPTION_A", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_B", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_C", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_D", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_E", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_F", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_G", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_H", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_I", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_J", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_K", "classification": "cleanup_packet"},
            {
                "token": "APPROVE_ZERO_DIRTY_SCOPE",
                "pathspec": ".tmp/approve-zero-dirty-scope.pathspec",
                "classification": "verified_existing_packet",
            },
        ],
    }
    approval = {
        "pathspec_results": [
            {"pathspec": "approve-ai-context.pathspec", "covered_dirty_count": 2},
            {"pathspec": "approve-zero-dirty-scope.pathspec", "covered_dirty_count": 0},
        ],
    }

    summary = refresh_current_evidence._authorization_option_coverage_summary(menu, approval)

    assert summary == (
        "APPROVE_AI_CONTEXT_RELAY_UPDATE=2/0; APPROVE_OPTION_A=n/a; APPROVE_OPTION_B=n/a; "
        "APPROVE_OPTION_C=n/a; APPROVE_OPTION_D=n/a; "
        "APPROVE_OPTION_E=n/a; APPROVE_OPTION_F=n/a; APPROVE_OPTION_G=n/a; APPROVE_OPTION_H=n/a; "
        "APPROVE_OPTION_I=n/a; APPROVE_OPTION_J=n/a; APPROVE_OPTION_K=n/a"
    )
    assert refresh_current_evidence._authorization_option_coverage_omission_summary(menu, approval) == ""


def test_authorization_option_pathspec_summary_lists_visible_option_pathspecs():
    menu = {
        "recommended": {"token": "APPROVE_AI_CONTEXT_RELAY_UPDATE", "pathspec": ".tmp/approve-ai-context.pathspec"},
        "one_line_user_options": [
            "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            "APPROVE_OPTION_A",
            "APPROVE_ZERO_DIRTY_SCOPE",
        ],
        "also_available": [
            {
                "token": "APPROVE_OPTION_A",
                "pathspec": ".tmp/approve-option-a.pathspec",
                "classification": "cleanup_packet",
            },
            {
                "token": "APPROVE_OPTION_B",
                "pathspec": ".tmp/approve-option-b.pathspec",
                "classification": "cleanup_packet",
            },
            {
                "token": "APPROVE_ZERO_DIRTY_SCOPE",
                "pathspec": ".tmp/approve-zero-dirty-scope.pathspec",
                "classification": "verified_existing_packet",
            },
        ],
    }
    approval = {
        "pathspec_results": [
            {"pathspec": "approve-ai-context.pathspec", "covered_dirty_count": 2},
            {"pathspec": "approve-zero-dirty-scope.pathspec", "covered_dirty_count": 0},
        ],
    }

    summary = refresh_current_evidence._authorization_option_pathspec_summary(menu, approval, limit=2)

    assert summary == (
        "shown 2/3: APPROVE_AI_CONTEXT_RELAY_UPDATE->approve-ai-context.pathspec; "
        "APPROVE_OPTION_A->approve-option-a.pathspec, omitted 1: "
        "APPROVE_OPTION_B->approve-option-b.pathspec."
    )


def test_authorization_option_pathspec_summary_limits_omitted_preview():
    menu = {
        "recommended": {"token": "APPROVE_AI_CONTEXT_RELAY_UPDATE", "pathspec": ".tmp/approve-ai-context.pathspec"},
        "one_line_user_options": [
            "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            "APPROVE_OPTION_A",
            "APPROVE_OPTION_B",
            "APPROVE_OPTION_C",
            "APPROVE_OPTION_D",
        ],
        "also_available": [
            {"token": "APPROVE_OPTION_A", "pathspec": ".tmp/approve-option-a.pathspec"},
            {"token": "APPROVE_OPTION_B", "pathspec": ".tmp/approve-option-b.pathspec"},
            {"token": "APPROVE_OPTION_C", "pathspec": ".tmp/approve-option-c.pathspec"},
            {"token": "APPROVE_OPTION_D", "pathspec": ".tmp/approve-option-d.pathspec"},
        ],
    }

    summary = refresh_current_evidence._authorization_option_pathspec_summary(menu, {}, limit=2)

    assert summary == (
        "shown 2/5: APPROVE_AI_CONTEXT_RELAY_UPDATE->approve-ai-context.pathspec; "
        "APPROVE_OPTION_A->approve-option-a.pathspec, omitted 3: "
        "APPROVE_OPTION_B->approve-option-b.pathspec; APPROVE_OPTION_C->approve-option-c.pathspec, omitted-more 1."
    )


def test_authorization_option_pathspec_summary_default_covers_current_option_scale():
    also_available = [
        {"token": f"APPROVE_OPTION_{index}", "pathspec": f".tmp/approve-option-{index}.pathspec"}
        for index in range(1, 12)
    ]
    menu = {
        "recommended": {
            "token": "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            "pathspec": ".tmp/approve-ai-context.pathspec",
        },
        "one_line_user_options": [
            "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            *[item["token"] for item in also_available],
        ],
        "also_available": also_available,
    }

    summary = refresh_current_evidence._authorization_option_pathspec_summary(menu, {})

    assert summary.startswith(
        "shown 12/12: APPROVE_AI_CONTEXT_RELAY_UPDATE->approve-ai-context.pathspec; "
        "APPROVE_OPTION_1->approve-option-1.pathspec",
    )
    assert "APPROVE_OPTION_11->approve-option-11.pathspec" in summary
    assert "omitted" not in summary


def test_authorization_option_pathspec_summary_omits_without_visible_options():
    assert refresh_current_evidence._authorization_option_pathspec_summary({}, {}) == ""


def test_authorization_option_classification_summary_lists_visible_option_classes():
    menu = {
        "recommended": {"token": "APPROVE_AI_CONTEXT_RELAY_UPDATE", "pathspec": ".tmp/approve-ai-context.pathspec"},
        "one_line_user_options": [
            "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            "APPROVE_OPTION_A",
            "APPROVE_ZERO_DIRTY_SCOPE",
        ],
        "also_available": [
            {
                "token": "APPROVE_OPTION_A",
                "classification": "cleanup_packet",
            },
            {
                "token": "APPROVE_OPTION_B",
                "classification": "verified_existing_packet",
            },
            {
                "token": "APPROVE_ZERO_DIRTY_SCOPE",
                "pathspec": ".tmp/approve-zero-dirty-scope.pathspec",
                "classification": "verified_existing_packet",
            },
        ],
    }
    approval = {
        "pathspec_results": [
            {"pathspec": "approve-ai-context.pathspec", "covered_dirty_count": 2},
            {"pathspec": "approve-zero-dirty-scope.pathspec", "covered_dirty_count": 0},
        ],
    }

    summary = refresh_current_evidence._authorization_option_classification_summary(menu, approval, limit=2)

    assert summary == (
        "shown 2/3: APPROVE_AI_CONTEXT_RELAY_UPDATE->recommended; "
        "APPROVE_OPTION_A->cleanup_packet, omitted 1: "
        "APPROVE_OPTION_B->verified_existing_packet."
    )


def test_authorization_option_classification_summary_default_covers_current_option_scale():
    also_available = [
        {"token": f"APPROVE_OPTION_{index}", "classification": f"class_{index}"} for index in range(1, 12)
    ]
    menu = {
        "recommended": {
            "token": "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            "pathspec": ".tmp/approve-ai-context.pathspec",
        },
        "one_line_user_options": [
            "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            *[item["token"] for item in also_available],
        ],
        "also_available": also_available,
    }

    summary = refresh_current_evidence._authorization_option_classification_summary(menu, {})

    assert summary.startswith(
        "shown 12/12: APPROVE_AI_CONTEXT_RELAY_UPDATE->recommended; APPROVE_OPTION_1->class_1",
    )
    assert "APPROVE_OPTION_11->class_11" in summary
    assert "omitted" not in summary


def test_authorization_option_classification_summary_omits_without_visible_options():
    assert refresh_current_evidence._authorization_option_classification_summary({}, {}) == ""


def test_authorization_option_tokens_list_all_current_tokens_before_omitting():
    menu = {
        "recommended": {"token": "APPROVE_AI_CONTEXT_RELAY_UPDATE", "pathspec": ".tmp/approve-ai-context.pathspec"},
        "one_line_user_options": [
            "APPROVE_AI_CONTEXT_RELAY_UPDATE",
            "APPROVE_OPTION_A",
            "APPROVE_OPTION_B",
            "APPROVE_OPTION_C",
            "STOP",
        ],
        "also_available": [
            {"token": "APPROVE_OPTION_D", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_E", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_F", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_G", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_H", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_I", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_J", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_K", "classification": "cleanup_packet"},
            {"token": "APPROVE_OPTION_L", "classification": "cleanup_packet"},
            {
                "token": "APPROVE_ZERO_DIRTY_SCOPE",
                "pathspec": ".tmp/approve-zero-dirty-scope.pathspec",
                "classification": "verified_existing_packet",
            },
        ],
    }
    approval = {
        "pathspec_results": [
            {"pathspec": "approve-ai-context.pathspec", "covered_dirty_count": 2},
            {"pathspec": "approve-zero-dirty-scope.pathspec", "covered_dirty_count": 0},
        ],
    }

    tokens, total = refresh_current_evidence._authorization_option_tokens(menu, approval=approval)

    assert tokens == [
        "APPROVE_AI_CONTEXT_RELAY_UPDATE",
        "APPROVE_OPTION_A",
        "APPROVE_OPTION_B",
        "APPROVE_OPTION_C",
        "APPROVE_OPTION_D",
        "APPROVE_OPTION_E",
        "APPROVE_OPTION_F",
        "APPROVE_OPTION_G",
        "APPROVE_OPTION_H",
        "APPROVE_OPTION_I",
        "APPROVE_OPTION_J",
        "APPROVE_OPTION_K",
        "APPROVE_OPTION_L",
    ]
    assert total == 13
    assert refresh_current_evidence._authorization_option_omission_summary(menu, approval) == ""


def test_authorization_option_omissions_report_zero_dirty_tokens():
    menu = {
        "recommended": {"token": "APPROVE_AI_CONTEXT_RELAY_UPDATE", "pathspec": ".tmp/approve-ai-context.pathspec"},
        "also_available": [
            {
                "token": "APPROVE_ZERO_DIRTY_SCOPE",
                "pathspec": ".tmp/approve-zero-dirty-scope.pathspec",
                "classification": "verified_existing_packet",
            },
            {
                "token": "APPROVE_POSITIVE_DIRTY_SCOPE",
                "pathspec": ".tmp/approve-positive-dirty-scope.pathspec",
                "classification": "verified_existing_packet",
            },
            {
                "token": "APPROVE_NO_COVERAGE_DETAIL",
                "pathspec": ".tmp/approve-no-coverage-detail.pathspec",
                "classification": "verified_existing_packet",
            },
            {
                "token": "APPROVE_RELAY_ONLY_ZERO_DIRTY",
                "pathspec": ".tmp/approve-relay-only-zero-dirty.pathspec",
                "classification": "relay_only_packet",
            },
        ],
    }
    approval = {
        "pathspec_results": [
            {"pathspec": "approve-ai-context.pathspec", "covered_dirty_count": 2},
            {
                "pathspec": "approve-zero-dirty-scope.pathspec",
                "covered_dirty_count": 0,
                "extra_non_dirty_count": 2,
                "extra_non_dirty_paths": ["config/.npmrc", "docs/readme.md"],
            },
            {"pathspec": "approve-positive-dirty-scope.pathspec", "covered_dirty_count": 3},
            {"pathspec": "approve-relay-only-zero-dirty.pathspec", "covered_dirty_count": 0},
        ],
    }

    omissions = refresh_current_evidence._authorization_option_zero_dirty_omissions(menu, approval)

    assert omissions == ["APPROVE_ZERO_DIRTY_SCOPE"]
    assert refresh_current_evidence._authorization_option_zero_dirty_omission_summary(menu, approval) == (
        "APPROVE_ZERO_DIRTY_SCOPE (tokens 1, dirty coverage 0, extra non-dirty paths 2, details "
        "APPROVE_ZERO_DIRTY_SCOPE -> approve-zero-dirty-scope.pathspec: config/.npmrc, docs/readme.md)"
    )


def test_replace_after_validation_rejects_bom_refresh_without_replacing_current(tmp_path):
    current_launch = tmp_path / "launch-objective-audit-current.json"
    refresh_launch = tmp_path / "launch-objective-audit-refresh.json"
    current_launch.write_bytes(_json_bytes({"previous": True}))
    refresh_launch.write_bytes(b"\xef\xbb\xbf" + _json_bytes({"items": []}))

    result = refresh_current_evidence._replace_after_validation(refresh_launch, current_launch)

    assert result.status == "failed"
    assert json.loads(current_launch.read_text(encoding="utf-8")) == {"previous": True}
    assert "BOM" in result.detail


def test_replace_after_validation_reports_unreadable_first_bytes(tmp_path):
    current_launch = tmp_path / "launch-objective-audit-current.json"
    refresh_launch = tmp_path / "launch-objective-audit-refresh.json"
    current_launch.write_bytes(_json_bytes({"previous": True}))
    refresh_launch.mkdir()

    result = refresh_current_evidence._replace_after_validation(refresh_launch, current_launch)

    assert result.status == "failed"
    assert result.first_bytes == "unreadable"
    assert json.loads(current_launch.read_text(encoding="utf-8")) == {"previous": True}
    assert "unreadable JSON" in result.detail


def test_debug_loop_completion_exit_contract_rejects_blocked_exit_zero(tmp_path):
    debug_json = tmp_path / "debug-loop-known-bugs-current.json"
    debug_json.write_bytes(_json_bytes({"summary": {"completion_allowed": False}}))

    result = refresh_current_evidence._validate_debug_loop_completion_exit(debug_json, observed_returncode=0)

    assert result.status == "failed"
    assert result.expected_returncode is False
    assert "expected returncode 1" in result.detail


def test_debug_loop_completion_exit_contract_accepts_blocked_exit_one(tmp_path):
    debug_json = tmp_path / "debug-loop-known-bugs-current.json"
    debug_json.write_bytes(_json_bytes({"summary": {"completion_allowed": False}}))

    result = refresh_current_evidence._validate_debug_loop_completion_exit(debug_json, observed_returncode=1)

    assert result.status == "ok"
    assert result.expected_returncode is True


def test_stdout_json_step_does_not_reuse_stale_refresh(monkeypatch, tmp_path):
    root = tmp_path
    target = tmp_path / "product-readiness-current.json"
    refresh = tmp_path / "product-readiness-current.json.refresh"
    target.write_bytes(_json_bytes({"previous": True}))
    refresh.write_bytes(_json_bytes({"stale_refresh": True}))

    def fake_run(_root, argv, **kwargs):
        assert not refresh.exists()
        return subprocess.CompletedProcess(argv, 0, _json_bytes({"fresh": True}), b"")

    monkeypatch.setattr(refresh_current_evidence, "_run", fake_run)

    result = refresh_current_evidence._run_stdout_json_step(
        root,
        name="product_readiness",
        argv=["python", "execution/product_readiness_score.py", "--json"],
        target=target,
        timeout=5,
    )

    assert result.status == "ok"
    assert json.loads(target.read_text(encoding="utf-8")) == {"fresh": True}
    assert not refresh.exists()


def test_stdout_json_step_fails_when_stale_refresh_cannot_be_removed(monkeypatch, tmp_path):
    root = tmp_path
    target = tmp_path / "product-readiness-current.json"
    refresh = tmp_path / "product-readiness-current.json.refresh"
    target.write_bytes(_json_bytes({"previous": True}))
    refresh.mkdir()

    def fake_run(_root, argv, **kwargs):
        raise AssertionError(f"unexpected command after unremovable refresh: {' '.join(argv)}")

    monkeypatch.setattr(refresh_current_evidence, "_run", fake_run)

    result = refresh_current_evidence._run_stdout_json_step(
        root,
        name="product_readiness",
        argv=["python", "execution/product_readiness_score.py", "--json"],
        target=target,
        timeout=5,
    )

    assert result.status == "failed"
    assert result.returncode == 2
    assert "could not remove stale refresh file" in result.detail
    assert result.first_bytes == "unreadable"
    assert json.loads(target.read_text(encoding="utf-8")) == {"previous": True}


def test_stdout_json_step_fails_when_atomic_refresh_write_fails(monkeypatch, tmp_path):
    root = tmp_path
    target = tmp_path / "product-readiness-current.json"
    refresh_tmp = tmp_path / "product-readiness-current.json.refresh.refresh-tmp"
    target.write_bytes(_json_bytes({"previous": True}))
    refresh_tmp.mkdir()

    def fake_run(_root, argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, _json_bytes({"fresh": True}), b"")

    monkeypatch.setattr(refresh_current_evidence, "_run", fake_run)

    result = refresh_current_evidence._run_stdout_json_step(
        root,
        name="product_readiness",
        argv=["python", "execution/product_readiness_score.py", "--json"],
        target=target,
        timeout=5,
    )

    assert result.status == "failed"
    assert result.returncode == 2
    assert "could not write refresh evidence atomically" in result.detail
    assert json.loads(target.read_text(encoding="utf-8")) == {"previous": True}


def test_atomic_write_bytes_retries_transient_replace_permission_error(monkeypatch, tmp_path):
    target = tmp_path / "current.json"
    original_replace = Path.replace
    calls = 0

    def flaky_replace(self: Path, destination: Path):
        nonlocal calls
        if self.name == "current.json.refresh-tmp" and destination == target:
            calls += 1
            if calls == 1:
                raise PermissionError("target temporarily locked")
        return original_replace(self, destination)

    monkeypatch.setattr(refresh_current_evidence.time, "sleep", lambda delay: None)
    monkeypatch.setattr(Path, "replace", flaky_replace)

    refresh_current_evidence._atomic_write_bytes(target, _json_bytes({"fresh": True}))

    assert calls == 2
    assert json.loads(target.read_text(encoding="utf-8")) == {"fresh": True}
    assert not target.with_name("current.json.refresh-tmp").exists()


def test_replace_after_validation_retries_transient_replace_permission_error(monkeypatch, tmp_path):
    source = tmp_path / "current.json.refresh"
    target = tmp_path / "current.json"
    source.write_bytes(_json_bytes({"fresh": True}))
    target.write_bytes(_json_bytes({"previous": True}))
    original_replace = Path.replace
    calls = 0

    def flaky_replace(self: Path, destination: Path):
        nonlocal calls
        if self == source and destination == target:
            calls += 1
            if calls == 1:
                raise PermissionError("target temporarily locked")
        return original_replace(self, destination)

    monkeypatch.setattr(refresh_current_evidence.time, "sleep", lambda delay: None)
    monkeypatch.setattr(Path, "replace", flaky_replace)

    result = refresh_current_evidence._replace_after_validation(source, target)

    assert calls == 2
    assert result.status == "ok"
    assert result.returncode == 0
    assert json.loads(target.read_text(encoding="utf-8")) == {"fresh": True}
    assert not source.exists()


def test_replace_after_validation_reports_locked_target_without_overwriting_current(monkeypatch, tmp_path):
    source = tmp_path / "current.json.refresh"
    target = tmp_path / "current.json"
    source.write_bytes(_json_bytes({"fresh": True}))
    target.write_bytes(_json_bytes({"previous": True}))
    calls = 0

    def locked_replace(self: Path, destination: Path):
        nonlocal calls
        if self == source and destination == target:
            calls += 1
            raise PermissionError("target locked")
        raise AssertionError(f"unexpected replace: {self} -> {destination}")

    monkeypatch.setattr(refresh_current_evidence.time, "sleep", lambda delay: None)
    monkeypatch.setattr(Path, "replace", locked_replace)

    result = refresh_current_evidence._replace_after_validation(source, target)

    assert calls == 3
    assert result.status == "failed"
    assert result.returncode == 2
    assert result.output == source
    assert "could not replace refresh evidence after validation" in result.detail
    assert json.loads(target.read_text(encoding="utf-8")) == {"previous": True}
    assert json.loads(source.read_text(encoding="utf-8")) == {"fresh": True}


def test_replace_after_validation_reports_blocked_target_parent_without_traceback(tmp_path):
    source = tmp_path / "current.json.refresh"
    blocked_parent = tmp_path / "blocked-parent"
    target = blocked_parent / "current.json"
    source.write_bytes(_json_bytes({"fresh": True}))
    blocked_parent.write_text("not a directory\n", encoding="utf-8")

    result = refresh_current_evidence._replace_after_validation(source, target)

    assert result.status == "failed"
    assert result.returncode == 2
    assert result.output == source
    assert result.first_bytes == "7B 0A 20 20"
    assert "could not create target evidence directory" in result.detail
    assert json.loads(source.read_text(encoding="utf-8")) == {"fresh": True}


def test_replace_markdown_reports_invalid_encoding_without_overwriting_current(tmp_path):
    source = tmp_path / "debug-loop-known-bugs-refresh.md"
    target = tmp_path / "debug-loop-known-bugs-current.md"
    source.write_bytes("새 증거\n".encode("utf-16"))
    target.write_text("# Previous debug inventory\n", encoding="utf-8")

    result = refresh_current_evidence._replace_markdown(source, target)

    assert result.status == "failed"
    assert result.returncode == 2
    assert result.output == source
    assert "unreadable Markdown" in result.detail
    assert target.read_text(encoding="utf-8") == "# Previous debug inventory\n"


def test_replace_markdown_reports_blocked_target_parent_without_traceback(tmp_path):
    source = tmp_path / "debug-loop-known-bugs-refresh.md"
    blocked_parent = tmp_path / "blocked-parent"
    target = blocked_parent / "debug-loop-known-bugs-current.md"
    source.write_text("# Fresh debug inventory\n", encoding="utf-8")
    blocked_parent.write_text("not a directory\n", encoding="utf-8")

    result = refresh_current_evidence._replace_markdown(source, target)

    assert result.status == "failed"
    assert result.returncode == 2
    assert result.output == target
    assert "could not write refresh evidence atomically" in result.detail
    assert source.read_text(encoding="utf-8") == "# Fresh debug inventory\n"


def test_copy_json_after_validation_reports_atomic_write_failure(tmp_path):
    source = tmp_path / "next-experiment-current.json"
    target = tmp_path / "next-experiment-continuation.json"
    temp_target = tmp_path / "next-experiment-continuation.json.refresh-tmp"
    source.write_bytes(_json_bytes({"status": "blocked"}))
    target.write_bytes(_json_bytes({"previous": True}))
    temp_target.mkdir()

    result = refresh_current_evidence._copy_json_after_validation(source, target)

    assert result.status == "failed"
    assert result.returncode == 2
    assert "could not write refresh evidence atomically" in result.detail
    assert json.loads(target.read_text(encoding="utf-8")) == {"previous": True}


def test_copy_json_after_validation_reports_validated_source_read_failure(monkeypatch, tmp_path):
    source = tmp_path / "next-experiment-current.json"
    target = tmp_path / "next-experiment-continuation.json"
    source.write_bytes(_json_bytes({"status": "blocked"}))
    target.write_bytes(_json_bytes({"previous": True}))
    original_read_bytes = Path.read_bytes
    source_read_count = 0

    def unreadable_after_validation(self: Path) -> bytes:
        nonlocal source_read_count
        if self == source:
            source_read_count += 1
            if source_read_count == 1:
                return original_read_bytes(self)
            raise PermissionError("source locked after validation")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", unreadable_after_validation)

    result = refresh_current_evidence._copy_json_after_validation(source, target)

    assert result.status == "failed"
    assert result.returncode == 2
    assert result.output == source
    assert source_read_count == 3
    assert "could not read validated JSON for sync" in result.detail
    assert json.loads(target.read_text(encoding="utf-8")) == {"previous": True}


def test_approval_matrix_write_reports_atomic_write_failure(tmp_path):
    approval = tmp_path / "approval-pathspec-consistency-current.json"
    readiness = tmp_path / "product-readiness-current.json"
    completion = tmp_path / "launch-objective-completion-audit-current.json"
    selector = tmp_path / "next-experiment-current.json"
    matrix_json = tmp_path / "approval-execution-matrix-current.json"
    matrix_md = tmp_path / "approval-execution-matrix-current.md"
    burndown_json = tmp_path / "launch-blocker-burndown-current.json"
    burndown_md = tmp_path / "launch-blocker-burndown-current.md"
    approval.write_bytes(
        _json_bytes(
            {
                "status": "ok",
                "dirty_count": 3,
                "covered_dirty_count": 3,
                "pathspec_count": 1,
                "pathspec_results": [
                    {
                        "pathspec": "approve-ai-context-relay-update.pathspec",
                        "unique_path_count": 2,
                        "covered_dirty_count": 2,
                    },
                ],
            },
        ),
    )
    readiness.write_bytes(_json_bytes({"overall": {"score": 90, "state": "blocked"}}))
    completion.write_bytes(_json_bytes({"summary": {"item_count": 15, "complete_count": 6, "blocked_count": 9}}))
    selector.write_bytes(
        _json_bytes({"status": "blocked", "summary": {"selected_kind": "dirty_worktree_handoff_current"}}),
    )
    matrix_json.write_bytes(_json_bytes({"previous": True}))
    (tmp_path / "approval-execution-matrix-current.json.refresh-tmp").mkdir()

    result = refresh_current_evidence._write_approval_matrix_and_burndown(
        approval=approval,
        readiness=readiness,
        completion=completion,
        selector=selector,
        matrix_json=matrix_json,
        matrix_md=matrix_md,
        burndown_json=burndown_json,
        burndown_md=burndown_md,
    )

    assert result.status == "failed"
    assert result.returncode == 2
    assert result.name == "approval_execution_matrix_and_burndown"
    assert "could not write refresh evidence atomically" in result.detail
    assert json.loads(matrix_json.read_text(encoding="utf-8")) == {"previous": True}
    assert not matrix_md.exists()
    assert not burndown_json.exists()
    assert not burndown_md.exists()


def test_approval_matrix_and_burndown_markdown_include_uncovered_source_paths(tmp_path):
    approval = tmp_path / "approval-pathspec-consistency-current.json"
    readiness = tmp_path / "product-readiness-current.json"
    completion = tmp_path / "launch-objective-completion-audit-current.json"
    selector = tmp_path / "next-experiment-current.json"
    matrix_json = tmp_path / "approval-execution-matrix-current.json"
    matrix_md = tmp_path / "approval-execution-matrix-current.md"
    burndown_json = tmp_path / "launch-blocker-burndown-current.json"
    burndown_md = tmp_path / "launch-blocker-burndown-current.md"
    uncovered_paths = ["execution/session_log_rotator.py", "workspace/tests/test_session_log_rotator.py"]
    approval.write_bytes(
        _json_bytes(
            {
                "status": "needs_refresh",
                "dirty_count": 3,
                "covered_dirty_count": 1,
                "uncovered_dirty_count": 2,
                "uncovered_dirty_paths": uncovered_paths,
                "uncovered_non_evidence_source_count": 2,
                "uncovered_non_evidence_source_paths": uncovered_paths,
                "pathspec_count": 1,
                "staged_count": 0,
                "pathspec_results": [
                    {
                        "pathspec": "approve-ai-context-relay-update.pathspec",
                        "unique_path_count": 1,
                        "covered_dirty_count": 1,
                    },
                ],
            },
        ),
    )
    readiness.write_bytes(_json_bytes({"overall": {"score": 90, "state": "blocked"}}))
    completion.write_bytes(_json_bytes({"summary": {"item_count": 15, "complete_count": 6, "blocked_count": 9}}))
    selector.write_bytes(
        _json_bytes({"status": "blocked", "summary": {"selected_kind": "dirty_worktree_handoff_current"}}),
    )

    result = refresh_current_evidence._write_approval_matrix_and_burndown(
        approval=approval,
        readiness=readiness,
        completion=completion,
        selector=selector,
        matrix_json=matrix_json,
        matrix_md=matrix_md,
        burndown_json=burndown_json,
        burndown_md=burndown_md,
    )

    assert result.status == "ok"
    matrix = json.loads(matrix_json.read_text(encoding="utf-8"))
    burndown = json.loads(burndown_json.read_text(encoding="utf-8"))
    assert matrix["uncovered_non_evidence_source_paths"] == uncovered_paths
    assert matrix["phases"][0]["tokens"][0]["token"] == "APPROVE_AI_CONTEXT_RELAY_UPDATE"
    assert burndown["uncovered_non_evidence_source_paths"] == uncovered_paths
    assert burndown["recommended_first_token"] == "APPROVE_AI_CONTEXT_RELAY_UPDATE"
    assert burndown["recommended_first_pathspec"] == "approve-ai-context-relay-update.pathspec"
    assert burndown["recommended_first_pathspec_path_count"] == 1
    assert burndown["recommended_first_pathspec_dirty_count"] == 1
    assert burndown["recommended_first_phase"] == {
        "phase": "phase0_context_relay",
        "label": "Context relay first.",
        "dirty_path_count": 1,
        "token_count": 1,
    }
    assert burndown["blocker_actions"][0] == {
        "blocker": "dirty_worktree_handoff_current",
        "owner": "user_or_operator",
        "next_action": "Approve one scoped pathspec token before staging or committing.",
        "authorization": "APPROVE_AI_CONTEXT_RELAY_UPDATE",
    }
    matrix_text = matrix_md.read_text(encoding="utf-8")
    burndown_text = burndown_md.read_text(encoding="utf-8")
    assert "## Uncovered Source Paths" in matrix_text
    assert "#### Token pathspecs" in matrix_text
    assert (
        "- `APPROVE_AI_CONTEXT_RELAY_UPDATE` -> `approve-ai-context-relay-update.pathspec` (1/1 dirty paths)"
        in matrix_text
    )
    assert "## Uncovered Source Paths" in burndown_text
    assert "## Recommended Next Scope" in burndown_text
    assert "- First token: `APPROVE_AI_CONTEXT_RELAY_UPDATE`" in burndown_text
    assert (
        "- First pathspec: `approve-ai-context-relay-update.pathspec` (1 dirty paths, 1 total paths)" in burndown_text
    )
    assert "- First phase: `phase0_context_relay` - Context relay first. (1 dirty paths, 1 tokens)" in burndown_text
    assert "## Blocker Owners And Actions" in burndown_text
    assert (
        "- `dirty_worktree_handoff_current`: owner `user_or_operator`, "
        "next `Approve one scoped pathspec token before staging or committing.`, "
        "authorization `APPROVE_AI_CONTEXT_RELAY_UPDATE`"
    ) in burndown_text
    assert (
        "- `hanwoo_t251_external_supabase_credentials`: owner `user`, "
        "next `Reset or resync Supabase credentials before live Prisma CRUD E2E retry.`, "
        "authorization `external_credential_reset`"
    ) in burndown_text
    for path in uncovered_paths:
        assert f"`{path}`" in matrix_text
        assert f"`{path}`" in burndown_text


def test_ai_context_relay_packet_write_reports_atomic_write_failure(monkeypatch, tmp_path):
    root = tmp_path
    (root / ".tmp").mkdir()
    menu_json = root / ".tmp" / "next-scoped-authorization-menu-current.json"
    coverage_json = root / ".tmp" / "authorization-coverage-current.json"
    selector_json = root / ".tmp" / "next-experiment-current.json"
    packet_json = root / ".tmp" / "ai-context-aic1-scoped-authorization-current.json"
    packet_md = root / ".tmp" / "ai-context-aic1-scoped-authorization-current.md"
    menu_json.write_bytes(
        _json_bytes(
            {
                "recommended": {
                    "token": "APPROVE_AI_CONTEXT_RELAY_UPDATE",
                    "pathspec": ".tmp/approve-ai-context-relay-update.pathspec",
                    "files": [".ai/HANDOFF.md"],
                },
            },
        ),
    )
    coverage_json.write_bytes(_json_bytes({"status": "ok", "dirty_count": 1, "covered_dirty_count": 1}))
    selector_json.write_bytes(
        _json_bytes({"status": "blocked", "summary": {"selected_kind": "dirty_worktree_handoff_current"}}),
    )
    packet_json.write_bytes(_json_bytes({"previous": True}))
    (root / ".tmp" / "ai-context-aic1-scoped-authorization-current.json.refresh-tmp").mkdir()

    def fake_git_with_index(_root, _index_path, argv, **_kwargs):
        if argv[1:] == ["diff", "--cached", "--name-only"]:
            return subprocess.CompletedProcess(argv, 0, b".ai/HANDOFF.md\n", b"")
        if argv[1:] == ["diff", "--cached", "--shortstat"]:
            return subprocess.CompletedProcess(argv, 0, b" 1 file changed, 1 insertion(+)\n", b"")
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    def fake_git_without_index(_root, argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(refresh_current_evidence, "_git_with_index", fake_git_with_index)
    monkeypatch.setattr(refresh_current_evidence, "_git_without_index", fake_git_without_index)

    result = refresh_current_evidence._write_ai_context_relay_packet(
        root=root,
        menu_json=menu_json,
        coverage_json=coverage_json,
        selector_json=selector_json,
        packet_json=packet_json,
        packet_md=packet_md,
        timeout=5,
    )

    assert result.status == "failed"
    assert result.returncode == 2
    assert result.name == "ai_context_relay_packet"
    assert "could not write refresh evidence atomically" in result.detail
    assert json.loads(packet_json.read_text(encoding="utf-8")) == {"previous": True}
    assert not packet_md.exists()


def test_session_log_rotator_packet_writes_pathspec_and_virtual_index_proof(monkeypatch, tmp_path):
    root = tmp_path
    (root / ".tmp").mkdir()
    coverage_json = root / ".tmp" / "authorization-coverage-current.json"
    selector_json = root / ".tmp" / "next-experiment-current.json"
    pathspec = root / ".tmp" / "approve-session-log-rotator.pathspec"
    packet_json = root / ".tmp" / "session-log-rotator-authorization-current.json"
    packet_md = root / ".tmp" / "session-log-rotator-authorization-current.md"
    coverage_json.write_bytes(
        _json_bytes(
            {
                "status": "ok",
                "dirty_count": 2,
                "covered_dirty_count": 2,
                "uncovered_dirty_count": 0,
                "uncovered_non_evidence_source_count": 0,
                "pathspec_count": 90,
                "staged_count": 0,
            },
        ),
    )
    selector_json.write_bytes(
        _json_bytes(
            {
                "status": "blocked",
                "summary": {"selected_kind": "dirty_worktree_handoff_current", "adoptable_candidate_count": 0},
            },
        ),
    )

    def fake_git_with_index(_root, _index_path, argv, **_kwargs):
        if argv[1:] == ["diff", "--cached", "--name-only"]:
            return subprocess.CompletedProcess(
                argv,
                0,
                b"execution/session_log_rotator.py\nworkspace/tests/test_session_log_rotator.py\n",
                b"",
            )
        if argv[1:] == ["diff", "--cached", "--shortstat"]:
            return subprocess.CompletedProcess(argv, 0, b" 2 files changed, 12 insertions(+)\n", b"")
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    def fake_git_without_index(_root, argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(refresh_current_evidence, "_git_with_index", fake_git_with_index)
    monkeypatch.setattr(refresh_current_evidence, "_git_without_index", fake_git_without_index)

    result = refresh_current_evidence._write_session_log_rotator_packet(
        root=root,
        coverage_json=coverage_json,
        selector_json=selector_json,
        pathspec=pathspec,
        packet_json=packet_json,
        packet_md=packet_md,
        timeout=5,
    )

    assert result.status == "ok"
    assert pathspec.read_text(encoding="utf-8") == (
        "execution/session_log_rotator.py\nworkspace/tests/test_session_log_rotator.py\n"
    )
    packet = json.loads(packet_json.read_text(encoding="utf-8"))
    assert packet["token"] == "APPROVE_SESSION_LOG_ROTATOR"
    assert packet["authorized_by_this_artifact"] is False
    assert packet["current_scope_validation"]["all_scope_paths_currently_dirty"] is True
    assert packet["current_scope_validation"]["real_staged_count"] == 0
    assert packet["virtual_index"]["cached_diff_check_exit"] == 0
    markdown = packet_md.read_text(encoding="utf-8")
    assert "APPROVE_SESSION_LOG_ROTATOR" in markdown
    assert "Authorized by this artifact: false" in markdown


def test_session_log_rotator_menu_option_upserts_without_duplicates(tmp_path):
    menu_json = tmp_path / "menu.json"
    menu_json.write_bytes(
        _json_bytes(
            {
                "recommended": {"token": "APPROVE_AI_CONTEXT_RELAY_UPDATE"},
                "also_available": [
                    {"token": "APPROVE_OTHER", "reason": "Keep existing option."},
                    {"token": "APPROVE_SESSION_LOG_ROTATOR", "reason": "stale"},
                ],
            },
        ),
    )

    result = refresh_current_evidence._upsert_session_log_rotator_menu_option(menu_json)

    assert result.status == "ok"
    menu = json.loads(menu_json.read_text(encoding="utf-8"))
    matches = [item for item in menu["also_available"] if item["token"] == "APPROVE_SESSION_LOG_ROTATOR"]
    assert len(matches) == 1
    assert matches[0]["packet"] == ".tmp/session-log-rotator-authorization-current.md"
    assert matches[0]["pathspec"] == ".tmp/approve-session-log-rotator.pathspec"
    assert "virtual index" in matches[0]["reason"]
    assert any(item["token"] == "APPROVE_OTHER" for item in menu["also_available"])


def test_output_file_inventory_refresh_failure_preserves_existing_current(monkeypatch, tmp_path):
    root = tmp_path
    (root / ".tmp").mkdir()
    current_inventory = root / ".tmp" / "github-project-inventory-current.json"
    refresh_inventory = root / ".tmp" / "github-project-inventory-refresh.json"
    current_inventory.write_bytes(_json_bytes({"previous": True}))
    refresh_inventory.write_bytes(_json_bytes({"stale_refresh": True}))

    def fake_run(argv, **kwargs):
        joined = " ".join(argv)
        cwd = Path(kwargs["cwd"])
        if argv[0] == "git":
            has_virtual_index = "env" in kwargs and "GIT_INDEX_FILE" in kwargs["env"]
            if argv[1:] == ["read-tree", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            if argv[1] == "add":
                return subprocess.CompletedProcess(argv, 0, b"", b"warning: CRLF normalization\n")
            if argv[1:] == ["diff", "--cached", "--name-only"]:
                stdout = (
                    b"execution/session_log_rotator.py\nworkspace/tests/test_session_log_rotator.py\n"
                    if has_virtual_index
                    else b""
                )
                return subprocess.CompletedProcess(argv, 0, stdout, b"")
            if argv[1:] == ["diff", "--cached", "--shortstat"]:
                return subprocess.CompletedProcess(argv, 0, b" 2 files changed, 10 insertions(+)\n", b"")
            if argv[1:] == ["diff", "--cached", "--check"]:
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            raise AssertionError(f"unexpected git command: {joined}")
        if "product_readiness_score.py" in joined:
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"overall": {"score": 92}}), b"")
        if "github_project_inventory.py" in joined:
            (cwd / ".tmp" / "github-project-inventory-refresh.json").write_bytes(
                b"\xef\xbb\xbf" + _json_bytes({"summary": {"project_count": 7}}),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        raise AssertionError(f"unexpected command after failed inventory refresh: {joined}")

    monkeypatch.setattr(refresh_current_evidence.subprocess, "run", fake_run)

    summary = refresh_current_evidence.refresh_current_evidence(root, timeout=5)

    assert summary["status"] == "failed"
    assert summary["steps"][-1]["name"] == "github_project_inventory"
    assert summary["steps"][-1]["status"] == "failed"
    assert "BOM" in summary["steps"][-1]["detail"]
    assert json.loads(current_inventory.read_text(encoding="utf-8")) == {"previous": True}
    assert refresh_inventory.read_bytes().startswith(b"\xef\xbb\xbf")


def test_output_file_inventory_refresh_does_not_reuse_stale_refresh(monkeypatch, tmp_path):
    root = tmp_path
    (root / ".tmp").mkdir()
    current_inventory = root / ".tmp" / "github-project-inventory-current.json"
    refresh_inventory = root / ".tmp" / "github-project-inventory-refresh.json"
    current_inventory.write_bytes(_json_bytes({"previous": True}))
    refresh_inventory.write_bytes(_json_bytes({"stale_refresh": True}))

    def fake_run(argv, **kwargs):
        joined = " ".join(argv)
        if "product_readiness_score.py" in joined:
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"overall": {"score": 92}}), b"")
        if "github_project_inventory.py" in joined:
            assert not refresh_inventory.exists()
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        raise AssertionError(f"unexpected command after missing inventory refresh: {joined}")

    monkeypatch.setattr(refresh_current_evidence.subprocess, "run", fake_run)

    summary = refresh_current_evidence.refresh_current_evidence(root, timeout=5)

    assert summary["status"] == "failed"
    assert summary["steps"][-1]["name"] == "github_project_inventory"
    assert summary["steps"][-1]["status"] == "failed"
    assert "unreadable JSON" in summary["steps"][-1]["detail"]
    assert json.loads(current_inventory.read_text(encoding="utf-8")) == {"previous": True}
    assert not refresh_inventory.exists()


def test_output_file_inventory_unremovable_refresh_preserves_existing_current(monkeypatch, tmp_path):
    root = tmp_path
    (root / ".tmp").mkdir()
    current_inventory = root / ".tmp" / "github-project-inventory-current.json"
    refresh_inventory = root / ".tmp" / "github-project-inventory-refresh.json"
    current_inventory.write_bytes(_json_bytes({"previous": True}))
    refresh_inventory.mkdir()

    def fake_run(argv, **kwargs):
        joined = " ".join(argv)
        if "product_readiness_score.py" in joined:
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"overall": {"score": 92}}), b"")
        raise AssertionError(f"unexpected command after unremovable inventory refresh: {joined}")

    monkeypatch.setattr(refresh_current_evidence.subprocess, "run", fake_run)

    summary = refresh_current_evidence.refresh_current_evidence(root, timeout=5)

    assert summary["status"] == "failed"
    assert summary["steps"][-1]["name"] == "github_project_inventory"
    assert summary["steps"][-1]["status"] == "failed"
    assert summary["steps"][-1]["returncode"] == 2
    assert "could not remove stale refresh file" in summary["steps"][-1]["detail"]
    assert summary["steps"][-1]["first_bytes"] == "unreadable"
    assert json.loads(current_inventory.read_text(encoding="utf-8")) == {"previous": True}


def test_output_file_inventory_timeout_preserves_existing_current(monkeypatch, tmp_path):
    root = tmp_path
    (root / ".tmp").mkdir()
    current_inventory = root / ".tmp" / "github-project-inventory-current.json"
    refresh_inventory = root / ".tmp" / "github-project-inventory-refresh.json"
    current_inventory.write_bytes(_json_bytes({"previous": True}))
    refresh_inventory.write_bytes(_json_bytes({"stale_refresh": True}))

    def fake_run(argv, **kwargs):
        joined = " ".join(argv)
        if "product_readiness_score.py" in joined:
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"overall": {"score": 92}}), b"")
        if "github_project_inventory.py" in joined:
            assert not refresh_inventory.exists()
            raise subprocess.TimeoutExpired(argv, timeout=5, output=b"", stderr=b"partial stderr")
        raise AssertionError(f"unexpected command after timed-out inventory refresh: {joined}")

    monkeypatch.setattr(refresh_current_evidence.subprocess, "run", fake_run)

    summary = refresh_current_evidence.refresh_current_evidence(root, timeout=5)

    assert summary["status"] == "failed"
    assert summary["steps"][-1]["name"] == "github_project_inventory"
    assert summary["steps"][-1]["returncode"] == 124
    assert summary["steps"][-1]["status"] == "failed"
    assert "timed out after 5 seconds" in summary["steps"][-1]["detail"]
    assert json.loads(current_inventory.read_text(encoding="utf-8")) == {"previous": True}
    assert not refresh_inventory.exists()


def test_refresh_current_evidence_fails_when_scoped_menu_check_drifts(monkeypatch, tmp_path):
    root = tmp_path
    (root / ".tmp").mkdir()
    (root / ".tmp" / "next-scoped-authorization-menu-current.json").write_bytes(
        _json_bytes(
            {
                "recommended": {
                    "token": "APPROVE_AI_CONTEXT_RELAY_UPDATE",
                    "pathspec": ".tmp/approve-ai-context-relay-update.pathspec",
                    "files": [".ai/HANDOFF.md"],
                },
                "also_available": [],
            },
        ),
    )

    def fake_run(argv, **kwargs):
        joined = " ".join(argv)
        cwd = Path(kwargs["cwd"])
        if argv[0] == "git":
            has_virtual_index = "env" in kwargs and "GIT_INDEX_FILE" in kwargs["env"]
            if argv[1:] == ["read-tree", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            if argv[1] == "add":
                return subprocess.CompletedProcess(argv, 0, b"", b"warning: CRLF normalization\n")
            if argv[1:] == ["diff", "--cached", "--name-only"]:
                stdout = b"execution/session_log_rotator.py\nworkspace/tests/test_session_log_rotator.py\n"
                if not has_virtual_index:
                    stdout = b""
                return subprocess.CompletedProcess(argv, 0, stdout, b"")
            if argv[1:] == ["diff", "--cached", "--shortstat"]:
                return subprocess.CompletedProcess(argv, 0, b" 2 files changed, 10 insertions(+)\n", b"")
            if argv[1:] == ["diff", "--cached", "--check"]:
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            raise AssertionError(f"unexpected git command: {joined}")
        if "product_readiness_score.py" in joined:
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"overall": {"score": 92}}), b"")
        if "github_project_inventory.py" in joined:
            (cwd / ".tmp" / "github-project-inventory-refresh.json").write_bytes(
                _json_bytes({"summary": {"project_count": 7}}),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        if "browser_qa_inventory.py" in joined:
            (cwd / ".tmp" / "browser-qa-inventory-refresh.json").write_bytes(
                _json_bytes({"summary": {"coverage": "4/4"}}),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        if "dependency_freshness_inventory.py" in joined:
            (cwd / ".tmp" / "dependency-freshness-refresh.json").write_bytes(
                _json_bytes({"summary": {"candidate_dependency_count": 0}}),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        if "direction_alignment_audit.py" in joined:
            (cwd / ".tmp" / "direction-alignment-audit-refresh.json").write_bytes(
                _json_bytes({"status": "aligned_blocked"}),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "aligned_blocked"}), b"")
        if "dirty_worktree_handoff_plan.py" in joined:
            (cwd / ".tmp" / "scoped-dirty-worktree-handoff-plan-refresh.json").write_bytes(
                _json_bytes({"status": "handoff_required"}),
            )
            (cwd / ".tmp" / "scoped-dirty-worktree-handoff-plan-refresh.md").write_text(
                "# Dirty handoff\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "handoff_required"}), b"")
        if "approval_pathspec_consistency.py" in joined:
            (cwd / ".tmp" / "authorization-coverage-current.json").write_bytes(
                _json_bytes({"dirty_count": 3, "covered_dirty_count": 3, "uncovered_dirty_count": 0}),
            )
            return subprocess.CompletedProcess(
                argv,
                0,
                _json_bytes(
                    {
                        "status": "ok",
                        "dirty_count": 3,
                        "covered_dirty_count": 3,
                        "uncovered_dirty_count": 0,
                        "uncovered_non_evidence_source_count": 0,
                        "pathspec_count": 1,
                        "staged_count": 0,
                        "pathspec_results": [
                            {
                                "pathspec": "approve-ai-context-relay-update.pathspec",
                                "unique_path_count": 3,
                                "covered_dirty_count": 3,
                            },
                        ],
                    },
                ),
                b"",
            )
        if "launch_objective_audit.py" in joined:
            (cwd / ".tmp" / "launch-objective-audit-refresh.json").write_bytes(_json_bytes({"items": []}))
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"items": []}), b"")
        if "completion_audit.py" in joined:
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "incomplete"}), b"")
        if "release_authorization_packet.py" in joined:
            (cwd / ".tmp" / "release-authorization-packet-refresh.json").write_bytes(
                _json_bytes({"status": "blocked_dirty_worktree"}),
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "blocked_dirty_worktree"}), b"")
        if "session_orient.py" in joined:
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"repo_root": str(cwd)}), b"")
        if "next_experiment_selector.py" in joined:
            (cwd / ".tmp" / "next-experiment-refresh.json").write_bytes(_json_bytes({"status": "blocked"}))
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "blocked"}), b"")
        if "debug_loop_inventory.py" in joined:
            (cwd / ".tmp" / "debug-loop-known-bugs-refresh.json").write_bytes(
                _json_bytes({"summary": {"completion_allowed": False}}),
            )
            (cwd / ".tmp" / "debug-loop-known-bugs-refresh.md").write_text(
                "# Debug inventory\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 1, _json_bytes({"status": "blocked"}), b"")
        if "scoped_authorization_menu.py" in joined and "--check" in argv:
            return subprocess.CompletedProcess(
                argv,
                2,
                _json_bytes({"status": "drift", "rendered_matches": False}),
                b"",
            )
        if "scoped_authorization_menu.py" in joined:
            assert "--rewrite-menu-json" in argv
            (cwd / ".tmp" / "next-scoped-authorization-menu-current.md").write_text(
                "# Scoped menu\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, _json_bytes({"status": "ok"}), b"")
        raise AssertionError(f"unexpected command: {joined}")

    monkeypatch.setattr(refresh_current_evidence.subprocess, "run", fake_run)

    summary = refresh_current_evidence.refresh_current_evidence(root, timeout=5)

    assert summary["status"] == "failed"
    check_step = summary["steps"][-1]
    assert check_step["name"] == "scoped_authorization_menu_check"
    assert check_step["returncode"] == 2
    assert check_step["expected_returncode"] is False
