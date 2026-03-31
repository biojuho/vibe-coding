# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for session-by-session detail and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Date | 2026-03-31 |
| Tool | Codex |
| Work | Ran the full shared QA/QC runner against the current dirty workspace after the new local worktree helper landed, recorded an `APPROVED` result (`3038 passed / 29 skipped`, `AST 20/20`, security and governance `CLEAR`), and refreshed the shared baseline in `projects/knowledge-dashboard/public/qaqc_result.json`. |

### Previous Note

| Date | 2026-03-31 |
| Tool | Codex |
| Work | Evaluated ACPX `examples/flows/pr-triage`, kept only the isolation layer that fits the local-first workspace, added `workspace/execution/pr_triage_worktree.py` plus `workspace/directives/pr_triage_worktree.md`, updated `workspace/directives/INDEX.md`, and verified the new helper with focused git-worktree tests. |

## Current State

- Shared workspace QC latest rerun on `2026-03-31` is **`APPROVED`**: `blind-to-x 700 passed / 16 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 1068 passed / 1 skipped`, total `3038 passed / 29 skipped`, `AST 20/20`, security `CLEAR (2 triaged issue(s))`, governance `CLEAR`, infrastructure `6/6 Ready`, disk `135.2 GB free`.
- `projects/blind-to-x` project-only coverage rerun on `2026-03-31` now reports **`595 passed / 16 skipped / 59.89% coverage`** after the active `T-100` uplift slices. The biggest completed hotspots in this session are `pipeline/cost_db.py` (**81%**), `pipeline/cost_tracker.py` (**83%**), `pipeline/notion/_query.py` (**84%**), `pipeline/image_cache.py` (**91%**), `pipeline/notification.py` (**93%**), and `pipeline/content_calendar.py` (**100%**).
- The 2 triaged security findings from the latest shared QC are both known false positives in `projects/blind-to-x/pipeline/cost_db.py` because the interpolated `table` names come only from the internal `_ARCHIVE_TABLES` allowlist.
- `workspace/execution/governance_checks.py` is now part of the shared control plane on `2026-03-31`: it validates required `.ai` context files, targeted relay claims against live code, directive/INDEX ownership drift, and tracked audit follow-up linkage to `.ai/TASKS.md`.
- `workspace/execution/health_check.py --category governance` now exposes that governance gate directly, and `workspace/execution/qaqc_runner.py` downgrades the final verdict away from `APPROVED` whenever governance returns `WARNING` or `FAIL`.
- `workspace/execution/repo_map.py` and `workspace/execution/context_selector.py` are now part of the shared control plane on `2026-03-31`: they build a deterministic repo map, rank relevant files within a char budget, and inject the selected repository context into `workspace/execution/graph_engine.py` before variant generation.
- `workspace/execution/repo_map.py` now also persists file summaries under `.tmp/repo_map_cache.db` on `2026-03-31`, keyed by relative path + file size + `mtime_ns`, so fresh builder instances can reuse parsed metadata without re-reading unchanged files.
- `workspace/execution/pr_triage_worktree.py` and `workspace/directives/pr_triage_worktree.md` are now part of the shared control plane on `2026-03-31`: they create disposable linked git worktrees under `.tmp/pr_triage_worktrees/`, record `manifest.json` plus `conflict-state.json`, and keep PR-style validation local-only with no implicit fetch/push/comment side effects.
- `workspace/execution/graph_engine.py` now merges selected repo context into the supervisor state and correctly reads `TaskNode.task_text` from `workspace/execution/thought_decomposer.py` instead of the broken `child.task` attribute.
- `.mcp.json` no longer registers the redundant `filesystem` MCP server on `2026-03-31`; local file work is expected to use the built-in Read/Write/Glob/Grep tool path instead.
- `workspace/scripts/mcp_toggle.ps1` now includes a `Guard` action that reports overlapping AI tool clients so multi-client MCP footprint drift is visible before deep sessions.
- `workspace/directives/INDEX.md` and `workspace/directives/local_inference.md` now explicitly cover the local inference + agentic coding stack, including `graph_engine.py`, `workers.py`, `code_evaluator.py`, and `governance_checks.py`.
- `workspace/execution/code_evaluator.py` remains a dedicated evaluator module with its own tests, but `workspace/execution/graph_engine.py` still uses its local weighted evaluation/reflection loop rather than a direct `CodeEvaluator` import. The relay now says that explicitly, and governance checks guard against the old stale claim recurring.
- The latest shared QC was run against a dirty worktree, not a pristine tree. Current non-committed control-plane WIP includes `workspace/execution/repo_map.py`, `workspace/execution/context_selector.py`, `workspace/execution/graph_engine.py`, `workspace/execution/pr_triage_worktree.py`, `workspace/tests/test_context_selector.py`, `workspace/tests/test_pr_triage_worktree.py`, and `workspace/directives/pr_triage_worktree.md`, alongside unrelated skill/infrastructure edits and untracked temp files (`o.txt`, `temp_test_out.txt`).
- The ACPX `pr-triage` example reviewed on `2026-03-31` does not literally use `git worktree`; its `prepareWorkspace()` step creates an isolated temp clone. Our adaptation deliberately uses linked worktrees instead because the local-first workspace already has the repos on disk and wants lower-overhead isolation.
- The Shorts golden render escape hatch is now pinned to a real 30-second verification path in `projects/shorts-maker-v2/tests/integration/test_golden_render.py`, and it validates both backends for resolution plus audio/video duration alignment.
- Open follow-ups in `workspace/directives/system_audit_action_plan.md` now carry `[TASK: T-XXX]` markers and are linked to the one remaining active audit task (`T-100`) instead of living only in a markdown checklist.
- `projects/blind-to-x/pipeline/process.py` remains the active slim orchestrator, with runtime behavior in `projects/blind-to-x/pipeline/process_stages/` and `projects/blind-to-x/pipeline/stages/` preserved as the compatibility bridge.
- `projects/blind-to-x/pipeline/cost_db.py` now exposes a backward-compatible `_connect()` alias again because older helpers still call it directly, and the provider circuit-breaker helpers now use correct skip-hour thresholds plus a valid UTC timestamp fallback on Python 3.14.
- `projects/blind-to-x` still has unrelated user merge/WIP state under `projects/blind-to-x`; keep control-plane work scoped away from that tree unless the user explicitly redirects the session there.

## Verification Highlights

- `python -X utf8 workspace/scripts/check_mapping.py` -> **All mappings valid**
- `python -X utf8 workspace/execution/health_check.py --category governance --json` -> **overall `ok`** (`ai_context_files`, `relay_claim_consistency`, `directive_mapping`, `task_backlog_alignment`)
- `venv\Scripts\python.exe -m pytest workspace\tests\test_context_selector.py workspace\tests\test_graph_engine.py -q -o addopts=` -> **41 passed**
- `venv\Scripts\python.exe -m ruff check workspace\execution\repo_map.py workspace\execution\context_selector.py workspace\execution\graph_engine.py workspace\tests\test_context_selector.py workspace\tests\test_graph_engine.py` -> **All checks passed**
- `venv\Scripts\python.exe -m pytest workspace\tests\test_pr_triage_worktree.py -q -o addopts=` -> **2 passed**
- `venv\Scripts\python.exe -m ruff check workspace\execution\pr_triage_worktree.py workspace\tests\test_pr_triage_worktree.py` -> **All checks passed**
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py` -> **`APPROVED`** / `3038 passed / 0 failed / 0 errors / 29 skipped`, `blind-to-x 700 passed / 16 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 1068 passed / 1 skipped`
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

1. Finish `T-100` by raising the remaining audit-owned coverage follow-up so both `shorts-maker-v2` and `blind-to-x` meet their documented floors without relying on stale baseline numbers.
2. For the next `blind-to-x` uplift slice, prefer another bounded deterministic cluster over scraper-heavy work first. Good candidates after this session are `pipeline/image_generator.py` + `pipeline/image_upload.py`, or one of the 0%-coverage analytics modules if its external dependencies can be fully mocked.
3. Keep the shared context backlog tidy now that `T-109` is done, but do not overwrite fresh relay/task edits from other agents without merging them carefully.
4. If the user wants a richer PR lane later, build it on top of `pr_triage_worktree.py` as a read-only/local-first orchestrator first; keep GitHub write actions as a separately approved extension rather than bundling them into the baseline helper.

## Notes

- The repo is currently mid-merge in `projects/blind-to-x` (`MERGE_HEAD` present with unresolved `AA` / `UU` files). Do not commit or try to clean that state as part of control-plane work unless the user explicitly redirects the session there.
- `coverage run` is the reliable measurement path for `shorts-maker-v2` on this Windows machine; `pytest-cov` can still trip over duplicate root/project paths.
- `CostDatabase._connect()` is still a live compatibility surface used by `content_calendar.py`, `content_intelligence.py`, and calibration helpers. Do not remove it just because `_conn()` exists.
- During active BlindToX schedule windows, the infra snapshot can show `4/6 Ready` because the remaining two tasks are legitimately `Running`; confirm with `schtasks /query` before treating that as a regression.
- For `blind-to-x` rule edits, treat `projects/blind-to-x/rules/*.yaml` as the source of truth; the root `classification_rules.yaml` is a compatibility snapshot/fallback surface.
- When targeted `coverage report` looks wrong for a Windows path, prefer `coverage report -m --include="*module_name.py"`.
- `ContextSelector` defaults to `workspace/` roots unless the prompt explicitly points to `projects/` or `infrastructure/`, which helps keep unrelated `blind-to-x` WIP files out of control-plane coding prompts.
- `.tmp/repo_map_cache.db` is a deterministic intermediate cache, not a deliverable. It can be deleted and rebuilt safely when debugging repo-map selection issues.
- `workspace/execution/pr_triage_worktree.py` is safe to run against dirty repos because it checks out a detached linked worktree, but it currently assumes the needed refs already exist locally and does not fetch remotes on your behalf.
