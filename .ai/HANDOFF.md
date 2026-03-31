# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for session-by-session detail and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Date | 2026-03-31 |
| Tool | Claude |
| Work | Completed **T-114** debt remediation round 2. Extracted `_execute_subprocess` + `_apply_failure_policy` from `run_task` in `scheduler_engine.py`, `_check_manifest_vs_db` + `_check_db_vs_manifests` from `get_manifest_sync_diffs` in `content_db.py`, and `_render_item_header` + `_render_item_buttons` from `_render_items` in `shorts_manager.py`. Added 33 new tests (7 scheduler, 6 content_db, 20 shorts_manager_helpers). Results: `shorts_manager.py` 48.1→32.9, `content_db.py`/`scheduler_engine.py` dropped off workspace top-10. **Overall TDR 40.9%→38.9%**. T-115 logged for next round. |

### Previous Note

| Date | 2026-03-31 |
| Tool | Codex |
| Work | Completed `T-112` by consolidating the shared operator flow into a canonical `FAST / STANDARD / DEEP / DIAGNOSTIC` ladder. Added `workspace/directives/operator_workflow.md`, rewrote `workspace/scripts/README.md`, clarified `doctor.py` / `quality_gate.py` / `qaqc_runner.py` help text, and hardened `health_check.py` for Windows real-run diagnostics with UTF-8 console reconfiguration plus ASCII-safe report output. |

## Current State

- **VibeDebt Auditor** is now part of the shared control plane on `2026-03-31`: `workspace/execution/vibe_debt_auditor.py` scans 6 debt dimensions (complexity, duplication, test_gap, debt_markers, modularity, doc_sync), computes per-file scores (0-100) and project-level TDR (Technical Debt Ratio), persists history to `.tmp/debt_history.db` via `workspace/execution/debt_history_db.py`, and renders a Streamlit dashboard at `workspace/execution/pages/debt_dashboard.py`. Directive: `workspace/directives/vibe_debt_audit.md`. Tests: `workspace/tests/test_vibe_debt_auditor.py` (29 passed, 82% coverage).
- The shared operator ladder is now canonical on `2026-03-31`: `workspace/scripts/doctor.py` = `FAST` readiness, `workspace/scripts/quality_gate.py` = `STANDARD` local validation, `workspace/execution/qaqc_runner.py` = `DEEP` shared approval, and `workspace/execution/health_check.py` = `DIAGNOSTIC` drill-down. Canonical guide: `workspace/directives/operator_workflow.md`.
- `workspace/execution/health_check.py` now reconfigures stdout/stderr to UTF-8 on Windows before printing diagnostic output, which avoids the previous `UnicodeEncodeError` path on cp949 terminals and keeps the tool usable as a real drill-down command.
- `workspace/execution/qaqc_runner.py` now includes an optional `[DEBT]` stage (skippable with `--skip-debt`) that runs the VibeDebt audit and persists results. The debt audit does not affect the pass/fail verdict; it reports TDR and grade as informational metrics.
- First VibeDebt scan on `2026-03-31`: **452 files, overall TDR 41.4% (RED)**. Workspace TDR 37.9%, blind-to-x 48.8%, shorts-maker-v2 38.4%. Top debt factors: `test_gap` (33-64 avg) and `complexity` (30-38 avg). Top debtor files: `llm_client.py` (58.8), `blind-to-x/main.py` (59.2), `karaoke.py` (56.4).
- Shared workspace QC latest rerun on `2026-03-31` is **`APPROVED`**: `blind-to-x 723 passed / 16 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 1073 passed / 1 skipped`, total `3066 passed / 29 skipped`, `AST 20/20`, security `CLEAR (2 triaged issue(s))`, governance `CLEAR`, infrastructure `6/6 Ready`, disk `138.3 GB free`.
- `projects/blind-to-x` project-only coverage rerun on `2026-03-31` now reports **`701 passed / 16 skipped / 71% coverage`** after the latest `T-100` uplift. New test files: `test_image_generator.py` (45 tests), `test_image_upload.py` (30 tests), `test_analytics_tracker.py` (20 tests), `test_draft_analytics.py` (7 tests). Module coverage: `draft_analytics.py` **100%**, `image_upload.py` **89%**, `image_generator.py` **77%**, `analytics_tracker.py` **59%**.
- The 2 triaged security findings from the latest shared QC are both known false positives in `projects/blind-to-x/pipeline/cost_db.py` because the interpolated `table` names come only from the internal `_ARCHIVE_TABLES` allowlist.
- `workspace/execution/governance_checks.py` is now part of the shared control plane on `2026-03-31`: it validates required `.ai` context files, targeted relay claims against live code, directive/INDEX ownership drift, and tracked audit follow-up linkage to `.ai/TASKS.md`.
- `workspace/execution/health_check.py --category governance` now exposes that governance gate directly, and `workspace/execution/qaqc_runner.py` downgrades the final verdict away from `APPROVED` whenever governance returns `WARNING` or `FAIL`.
- `workspace/execution/repo_map.py` and `workspace/execution/context_selector.py` are now part of the shared control plane on `2026-03-31`: they build a deterministic repo map, rank relevant files within a char budget, and inject the selected repository context into `workspace/execution/graph_engine.py` before variant generation.
- `workspace/execution/repo_map.py` now also persists file summaries under `.tmp/repo_map_cache.db` on `2026-03-31`, keyed by relative path + file size + `mtime_ns`, so fresh builder instances can reuse parsed metadata without re-reading unchanged files.
- `workspace/execution/pr_triage_worktree.py` and `workspace/directives/pr_triage_worktree.md` are now part of the shared control plane on `2026-03-31`: they create disposable linked git worktrees under `.tmp/pr_triage_worktrees/`, record `manifest.json` plus `conflict-state.json`, and keep PR-style validation local-only with no implicit fetch/push/comment side effects.
- `workspace/execution/pr_triage_orchestrator.py` and `workspace/directives/pr_triage_orchestrator.md` are now part of the shared control plane on `2026-03-31`: they sit above `pr_triage_worktree.py`, auto-select repo-specific validation profiles, persist `triage-report.json` plus `logs/*.log`, and default to removing only the linked worktree while keeping the session artifacts for review.
- `workspace/execution/pr_triage_worktree.py` now decodes git command output with UTF-8 plus locale fallback on `2026-03-31`, which keeps manifest/report paths readable on Windows machines whose home directory includes non-ASCII characters.
- `workspace/execution/graph_engine.py` now merges selected repo context into the supervisor state and correctly reads `TaskNode.task_text` from `workspace/execution/thought_decomposer.py` instead of the broken `child.task` attribute.
- `.mcp.json` no longer registers the redundant `filesystem` MCP server on `2026-03-31`; local file work is expected to use the built-in Read/Write/Glob/Grep tool path instead.
- `workspace/scripts/mcp_toggle.ps1` now includes a `Guard` action that reports overlapping AI tool clients so multi-client MCP footprint drift is visible before deep sessions.
- `workspace/directives/INDEX.md` and `workspace/directives/local_inference.md` now explicitly cover the local inference + agentic coding stack, including `graph_engine.py`, `workers.py`, `code_evaluator.py`, and `governance_checks.py`.
- `workspace/execution/code_evaluator.py` remains a dedicated evaluator module with its own tests, but `workspace/execution/graph_engine.py` still uses its local weighted evaluation/reflection loop rather than a direct `CodeEvaluator` import. The relay now says that explicitly, and governance checks guard against the old stale claim recurring.
- Productivity review on `2026-03-31` found the shared control plane now spans **32 directives**, **140 execution files**, **114 tests**, and **152 Python files / 38,784 lines** under `workspace/`; reliability is strong, but the main productivity tax had become operator choice and planning drift rather than missing coverage or broken gates.
- That operator overlap is now reduced into one documented path: `doctor.py` -> `quality_gate.py` -> `qaqc_runner.py`, with `health_check.py --category ...` reserved for targeted diagnostics instead of daily default use.
- The latest shared QC was run against a dirty worktree, not a pristine tree. Current non-committed control-plane WIP includes `workspace/execution/repo_map.py`, `workspace/execution/context_selector.py`, `workspace/execution/graph_engine.py`, `workspace/execution/pr_triage_worktree.py`, `workspace/execution/pr_triage_orchestrator.py`, `workspace/tests/test_context_selector.py`, `workspace/tests/test_pr_triage_worktree.py`, `workspace/tests/test_pr_triage_orchestrator.py`, `workspace/directives/pr_triage_worktree.md`, and `workspace/directives/pr_triage_orchestrator.md`, alongside unrelated skill/infrastructure edits and untracked temp files (`o.txt`, `temp_test_out.txt`).
- The ACPX `pr-triage` example reviewed on `2026-03-31` does not literally use `git worktree`; its `prepareWorkspace()` step creates an isolated temp clone. Our adaptation deliberately uses linked worktrees instead because the local-first workspace already has the repos on disk and wants lower-overhead isolation.
- The Shorts golden render escape hatch is now pinned to a real 30-second verification path in `projects/shorts-maker-v2/tests/integration/test_golden_render.py`, and it validates both backends for resolution plus audio/video duration alignment.
- Open follow-ups in `workspace/directives/system_audit_action_plan.md` now carry `[TASK: T-XXX]` markers and are linked to the one remaining active audit task (`T-100`) instead of living only in a markdown checklist.
- `projects/blind-to-x/pipeline/process.py` remains the active slim orchestrator, with runtime behavior in `projects/blind-to-x/pipeline/process_stages/` and `projects/blind-to-x/pipeline/stages/` preserved as the compatibility bridge.
- `projects/blind-to-x/pipeline/cost_db.py` now exposes a backward-compatible `_connect()` alias again because older helpers still call it directly, and the provider circuit-breaker helpers now use correct skip-hour thresholds plus a valid UTC timestamp fallback on Python 3.14.
- `projects/blind-to-x` still has unrelated user merge/WIP state under `projects/blind-to-x`; keep control-plane work scoped away from that tree unless the user explicitly redirects the session there.

## Verification Highlights

- `python -X utf8 workspace/scripts/check_mapping.py` -> **All mappings valid**
- `python -X utf8 workspace/execution/health_check.py --category governance --json` -> **overall `ok`** (`ai_context_files`, `relay_claim_consistency`, `directive_mapping`, `task_backlog_alignment`)
- `venv\Scripts\python.exe -m pytest workspace\tests\test_doctor.py workspace\tests\test_health_check.py workspace\tests\test_qaqc_runner.py workspace\tests\test_qaqc_runner_extended.py -q -o addopts=` -> **71 passed**
- `venv\Scripts\python.exe workspace\scripts\doctor.py` -> **pass** with new `FAST` guidance and escalation hint
- `venv\Scripts\python.exe workspace\execution\health_check.py --category governance` -> **pass** with ASCII-safe diagnostic report on Windows
- `venv\Scripts\python.exe workspace\execution\health_check.py --help` -> **pass** with operator-ladder epilog
- `venv\Scripts\python.exe workspace\execution\qaqc_runner.py --help` -> **pass** with operator-ladder epilog
- `venv\Scripts\python.exe -m pytest workspace\tests\test_context_selector.py workspace\tests\test_graph_engine.py -q -o addopts=` -> **41 passed**
- `venv\Scripts\python.exe -m ruff check workspace\execution\repo_map.py workspace\execution\context_selector.py workspace\execution\graph_engine.py workspace\tests\test_context_selector.py workspace\tests\test_graph_engine.py` -> **All checks passed**
- `venv\Scripts\python.exe -m pytest workspace\tests\test_pr_triage_worktree.py -q -o addopts=` -> **2 passed**
- `venv\Scripts\python.exe -m ruff check workspace\execution\pr_triage_worktree.py workspace\tests\test_pr_triage_worktree.py` -> **All checks passed**
- `venv\Scripts\python.exe -m pytest workspace\tests\test_pr_triage_orchestrator.py workspace\tests\test_pr_triage_worktree.py -q -o addopts=` -> **7 passed**
- `venv\Scripts\python.exe -m ruff check workspace\execution\pr_triage_orchestrator.py workspace\execution\pr_triage_worktree.py workspace\tests\test_pr_triage_orchestrator.py workspace\tests\test_pr_triage_worktree.py` -> **All checks passed**
- `venv\Scripts\python.exe -m compileall workspace\execution\pr_triage_orchestrator.py workspace\execution\pr_triage_worktree.py` -> **pass**
- `venv\Scripts\python.exe -X utf8 workspace\execution\pr_triage_orchestrator.py run --repo-path .tmp/pr_triage_orchestrator_smoke/demo-python --head-ref main --profile python-generic --label smoke` -> **`PASS`** on a temporary git repo; generated `triage-report.json` + per-command logs and cleaned the linked worktree afterward
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py` -> **`APPROVED`** / `3066 passed / 0 failed / 0 errors / 29 skipped`, `blind-to-x 723 passed / 16 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 1073 passed / 1 skipped`
- `venv\Scripts\python.exe -m compileall workspace\execution\repo_map.py workspace\execution\context_selector.py workspace\execution\graph_engine.py` -> **pass**
- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests\test_governance_checks.py workspace\tests\test_health_check.py workspace\tests\test_qaqc_runner.py workspace\tests\test_qaqc_runner_extended.py -q -o addopts=` -> **74 passed**
- `..\..\venv\Scripts\python.exe -m pytest tests\integration\test_golden_render.py -q -o addopts=` (`projects/shorts-maker-v2`) -> **2 passed, 2 warnings** in about **2m17s**
- `python -X utf8 -m pytest workspace\tests\test_mcp_config.py -q -o addopts=` -> **2 passed**
- `powershell -ExecutionPolicy Bypass -File workspace\scripts\mcp_toggle.ps1 -Action Status` -> guard now reports overlapping AI tool clients and Tier 3 MCP status in one view
- `venv\Scripts\python.exe workspace\execution\qaqc_runner.py -o .tmp/qaqc_system_check_2026-03-31.json` -> **`APPROVED`** / `2915 passed / 0 failed / 0 errors / 29 skipped`
- `..\..\venv\Scripts\python.exe -m pytest tests\unit\test_cost_db_extended.py tests\unit\test_cost_tracker_extended.py tests\unit\test_notion_query_mixin.py -q -o addopts=` (`projects/blind-to-x`) -> **20 passed**
- `..\..\venv\Scripts\python.exe -m coverage run --source=pipeline -m pytest tests\unit\test_cost_db_extended.py tests\unit\test_cost_tracker_extended.py -q -o addopts=` + `coverage report -m --include="*cost_db.py,*cost_tracker.py"` (`projects/blind-to-x`) -> `cost_db.py` **78%**, `cost_tracker.py` **77%** in the isolated slice
- `..\..\venv\Scripts\python.exe -m coverage run --source=pipeline -m pytest tests\unit\test_notion_query_mixin.py -q -o addopts=` + `coverage report -m --include="*_query.py"` (`projects/blind-to-x`) -> `pipeline/notion/_query.py` **84%**
- `..\..\venv\Scripts\python.exe -m pytest tests\unit\test_image_cache.py tests\unit\test_notification.py tests\unit\test_content_calendar_branches.py -q -o addopts=` (`projects/blind-to-x`) -> **14 passed**
- `..\..\venv\Scripts\python.exe -m coverage run --source=pipeline -m pytest tests\unit\test_image_cache.py tests\unit\test_notification.py tests\unit\test_content_calendar_branches.py -q -o addopts=` + `coverage report -m --include="*image_cache.py,*notification.py,*content_calendar.py"` (`projects/blind-to-x`) -> `image_cache.py` **91%**, `notification.py` **93%**, `content_calendar.py` **96%** in the isolated slice
- `..\..\venv\Scripts\python.exe -m pytest tests\unit tests\integration -q --maxfail=1` (`projects/blind-to-x`) -> **595 passed, 16 skipped, 1 warning**, total coverage **59.89%**

## Next Priorities

1. Continue `T-100`: `blind-to-x` is now at **71%** (from 59.89%). Next candidates: remaining low-coverage modules (`analytics_tracker.py` sync_metrics path, scraper modules) or pivot to `shorts-maker-v2` coverage uplift.
2. Tackle `T-113`: address the top debt hotspots from the new VibeDebt scan (`workspace/execution/llm_client.py`, `projects/blind-to-x/main.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/render/karaoke.py`) with a focus on test-gap and complexity reduction.
3. Continue trimming planning/backlog drift: large roadmap/audit directives should either map to active task IDs or stay clearly marked as reference-only so agents do not scan strategy docs as if they were execution queues.
4. For further `blind-to-x` uplift, the image/analytics modules are now covered. Next bounded cluster: `pipeline/dedup.py`, `pipeline/content_intelligence.py`, or `pipeline/style_bandit.py`.
5. If the user wants a richer PR lane later, build it on top of `pr_triage_orchestrator.py` as the read-only/local-first entrypoint; keep GitHub write actions as a separately approved extension rather than bundling them into the baseline helper.

## Notes

- The repo is currently mid-merge in `projects/blind-to-x` (`MERGE_HEAD` present with unresolved `AA` / `UU` files). Do not commit or try to clean that state as part of control-plane work unless the user explicitly redirects the session there.
- `coverage run` is the reliable measurement path for `shorts-maker-v2` on this Windows machine; `pytest-cov` can still trip over duplicate root/project paths.
- On Windows, prefer the updated `workspace/execution/health_check.py` entrypoint over older ad-hoc snippets for environment diagnosis; it now forces UTF-8 console output before printing detailed reports.
- `CostDatabase._connect()` is still a live compatibility surface used by `content_calendar.py`, `content_intelligence.py`, and calibration helpers. Do not remove it just because `_conn()` exists.
- During active BlindToX schedule windows, the infra snapshot can show `4/6 Ready` because the remaining two tasks are legitimately `Running`; confirm with `schtasks /query` before treating that as a regression.
- For `blind-to-x` rule edits, treat `projects/blind-to-x/rules/*.yaml` as the source of truth; the root `classification_rules.yaml` is a compatibility snapshot/fallback surface.
- When targeted `coverage report` looks wrong for a Windows path, prefer `coverage report -m --include="*module_name.py"`.
- `ContextSelector` defaults to `workspace/` roots unless the prompt explicitly points to `projects/` or `infrastructure/`, which helps keep unrelated `blind-to-x` WIP files out of control-plane coding prompts.
- `.tmp/repo_map_cache.db` is a deterministic intermediate cache, not a deliverable. It can be deleted and rebuilt safely when debugging repo-map selection issues.
- `workspace/execution/pr_triage_worktree.py` is safe to run against dirty repos because it checks out a detached linked worktree, but it currently assumes the needed refs already exist locally and does not fetch remotes on your behalf.
- Node-backed triage profiles intentionally reuse the source repo's existing `node_modules`; if dependencies are missing, `pr_triage_orchestrator.py` marks the command as `SKIP` instead of installing packages in the isolated worktree.
