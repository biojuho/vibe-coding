# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for session-by-session detail and `DECISIONS.md` for settled architecture decisions.

## Latest Update

| Date | 2026-04-01 |
| Tool | Codex |
| Work | Completed `T-122` for `projects/hanwoo-dashboard`: auth enforcement now happens at the real server boundaries (`requireAuthenticatedSession()` on the dashboard page, diagnostics page, subscription page, payment APIs, and all exported server actions), the proxy now delegates to `Auth.js` session authorization instead of checking cookie presence, and the payment flow now uses a server-prepared order plus a transactional confirm step that upserts both `PaymentLog` and `Subscription`. Cleaned the broken subscription/diagnostics/success UI strings after the refactor. Local verification: `npm run lint` (warning-only existing font notice) and `npm run build` both pass. |

## Relay Update

| Date | 2026-04-01 |
| Tool | Antigravity (Gemini) |
| Work | **제3자 코드 리뷰 기반 Critical Fix 2건 완료.** ① `tests/test_lyria_bgm_generator.py` → `tests/test_lyria_utils.py` 리네임으로 pytest 수집 오류(이름 충돌) 해소 — `execution/tests/`의 모든 테스트가 실질적으로 수집되지 않던 버그 수정. ② `execution/content_db.py` 954줄 전체 DB 함수(17개)를 `conn = _conn() / conn.close()` 패턴에서 `with _conn() as conn:` context manager 패턴으로 전환 — 예외 발생 시 SQLite 파일 잠금 누수 방지, WAL journal mode 및 `check_same_thread=False` 추가. 전후 비교: 이전 20-23 failed → 현재 **1207 passed / 1 failed** (실패 1건은 `fastapi` 미설치 환경 이슈로 우리 변경과 무관). |

## Last Session

| Date | 2026-04-01 |
| Tool | Antigravity (Gemini) |
| Work | **blind-to-x 내부 로직 개편 QA/QC 완료 (T-117) ✅ APPROVED** — QA 2건 추가 수정: ① `runtime.py`의 `spec_from_file_location()` None 반환 방어 코드 추가 (AttributeError 예방). ② `draft_generator.py`의 모듈 수준 `@property` dead code(동작하지 않는 코드) → 단순 모듈 참조 별칭으로 교체. 회귀 검증 38 passed / 0 failed (exit code 0), ruff All checks passed. 리팩토링 최종 산출물: Phase 1 (`_sync_runtime_overrides` 제거 + `BLIND_DEBUG_DB_PATH` 환경변수 기반 로드), Phase 2 (`_ProxyModule` + `sys.modules` 교체 삭제), Phase 3 (`filter_profile_stage.py` 5개 함수 분해), Phase 4 (`generate_review_stage.py` warning 격상 + `components_loaded` 추적), tests/conftest.py monkeypatch 타겟 이전. |

### Previous Note

| Date | 2026-04-01 |
| Tool | Codex |
| Work | Ran the full shared `DEEP` QA/QC pass on the dirty workspace and got **`CONDITIONALLY_APPROVED`**: `blind-to-x 873 passed / 9 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 25 passed / 2 errors / 1 skipped`, total `2168 passed / 0 failed / 2 errors / 22 skipped`, `AST 20/20`, security `CLEAR (2 triaged issue(s))`, governance `CLEAR`, infra `6/6 Ready`, debt `TDR 39.1%`. Root was the only blocker: `workspace/tests/test_shorts_manager_helpers.py` mutates `sys.modules["path_contract"]` at import time without `REPO_ROOT`, which breaks collection for `test_topic_auto_generator.py` and `test_vibe_debt_auditor.py`. Logged follow-up `T-116`. |

### Previous Note

| Date | 2026-03-31 |
| Tool | Codex |
| Work | Completed **T-114** by adding dedicated coverage for `workspace/execution/pages/shorts_manager.py` (14 tests, **71%** file coverage), extracting shared `_format_issue_labels()` logic, and fixing `workspace/execution/vibe_debt_auditor.py` so `score_test_gap()` scans all parent `tests/` directories instead of stopping at the first nested match. Latest rerun: `shorts_manager.py` **43.9→32.9**, workspace TDR **37.31%→29.25%**, overall TDR **40.87%→38.9%**. |

## Current State

- **VibeDebt Auditor** is now part of the shared control plane on `2026-03-31`: `workspace/execution/vibe_debt_auditor.py` scans 6 debt dimensions (complexity, duplication, test_gap, debt_markers, modularity, doc_sync), computes per-file scores (0-100) and project-level TDR (Technical Debt Ratio), persists history to `.tmp/debt_history.db` via `workspace/execution/debt_history_db.py`, and renders a Streamlit dashboard at `workspace/execution/pages/debt_dashboard.py`. Directive: `workspace/directives/vibe_debt_audit.md`. Tests now include the original audit suite plus a regression for parent-directory `tests/` discovery.
- `workspace/execution/pages/shorts_manager.py` now has dedicated focused coverage in `workspace/tests/test_shorts_manager.py` (14 tests, **71%** file coverage), covering flash state, upload helpers, manifest sync, launch flow, auth rendering, readiness/failure/review panels, and manifest drift reporting.
- `workspace/execution/vibe_debt_auditor.py` now walks **all** parent `tests/` directories when estimating `test_gap`, which fixes a false-positive scoring path for modules under `workspace/execution/**` whose matching tests live in `workspace/tests/`.
- Latest VibeDebt rerun on `2026-03-31` after the test-gap fix: **overall TDR 38.9%**, **workspace TDR 29.25%**, and `workspace/execution/pages/shorts_manager.py` now scores **32.9** (`test_gap_score 15.0`). Part of the drop comes from correcting the heuristic, not only from the new tests.
- The shared operator ladder is now canonical on `2026-03-31`: `workspace/scripts/doctor.py` = `FAST` readiness, `workspace/scripts/quality_gate.py` = `STANDARD` local validation, `workspace/execution/qaqc_runner.py` = `DEEP` shared approval, and `workspace/execution/health_check.py` = `DIAGNOSTIC` drill-down. Canonical guide: `workspace/directives/operator_workflow.md`.
- `workspace/execution/health_check.py` now reconfigures stdout/stderr to UTF-8 on Windows before printing diagnostic output, which avoids the previous `UnicodeEncodeError` path on cp949 terminals and keeps the tool usable as a real drill-down command.
- `workspace/execution/qaqc_runner.py` now includes an optional `[DEBT]` stage (skippable with `--skip-debt`) that runs the VibeDebt audit and persists results. The debt audit does not affect the pass/fail verdict; it reports TDR and grade as informational metrics.
- First VibeDebt scan on `2026-03-31`: **452 files, overall TDR 41.4% (RED)**. Workspace TDR 37.9%, blind-to-x 48.8%, shorts-maker-v2 38.4%. Top debt factors: `test_gap` (33-64 avg) and `complexity` (30-38 avg). Top debtor files: `llm_client.py` (58.8), `blind-to-x/main.py` (59.2), `karaoke.py` (56.4).
- Shared workspace QC latest rerun on `2026-04-01` is **`CONDITIONALLY_APPROVED`**: `blind-to-x 873 passed / 9 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 25 passed / 2 errors / 1 skipped`, total `2168 passed / 0 failed / 2 errors / 22 skipped`, `AST 20/20`, security `CLEAR (2 triaged issue(s))`, governance `CLEAR`, infrastructure `6/6 Ready`, disk `137.0 GB free`.
- Targeted reruns on `2026-04-01` no longer reproduce the old `T-116` root blocker in the current dirty worktree: `workspace/tests/test_shorts_manager_helpers.py`, `workspace/tests/test_topic_auto_generator.py`, and `workspace/tests/test_vibe_debt_auditor.py` now pass together locally. The next full shared QC should confirm whether the blocker is fully gone or was already fixed by parallel worktree changes.
- `T-119` is now closed on `2026-04-01`: `projects/blind-to-x/pipeline/draft_cache.py` uses `busy_timeout` plus a best-effort WAL checkpoint, `test_cost_tracker_uses_persisted_daily_totals` passes, and the previously failing draft-cache regression plus the verified blind unit slices pass sequentially.
- A new local-only follow-up `T-121` was logged on `2026-04-01`: `projects/blind-to-x/tests/unit/test_main.py` still hits a `KeyboardInterrupt` / runner interruption under this terminal wrapper, even though nearby blind unit slices are green. Treat it as a verification-harness issue until proven otherwise.
- `projects/hanwoo-dashboard` now enforces server-side auth on `src/app/page.js`, `src/app/admin/diagnostics/page.js`, `src/app/subscription/page.js`, all exported server actions in `src/lib/actions.js`, and the payment APIs. `src/proxy.js` now re-exports `auth` as the Next.js 16 proxy surface so access decisions come from `Auth.js` sessions rather than raw cookie presence.
- `projects/hanwoo-dashboard` subscription checkout now uses a server-prepared order (`src/app/api/payments/prepare/route.js`) and a transactional confirm path (`src/app/api/payments/confirm/route.js`) that binds `orderId` ownership to the authenticated user via `customerKey`, validates the premium amount, verifies Toss confirmation, and upserts `PaymentLog` plus `Subscription`.
- Latest `hanwoo-dashboard` verification on `2026-04-01`: `npm run lint` passes with only the pre-existing `@next/next/no-page-custom-font` warning in `src/app/layout.js`, and `npm run build` passes after the auth/payment hardening.
- The former shared QC blocker from `2026-04-01` is still tracked as `T-116`, but the targeted rerun is green in the current dirty worktree. Treat the old collection/import-pollution diagnosis as historical context until the next full shared QC confirms whether any blocker remains.
- Latest VibeDebt rerun on `2026-04-01` nudged overall TDR to **39.08%** with project split `workspace 29.25% / blind-to-x 48.06% / shorts-maker-v2 38.24%`.
- `.github/workflows/full-test-matrix.yml` and `.github/workflows/root-quality-gate.yml` now match the live repo layout on `2026-04-01`: workspace validation runs from `workspace/`, Python project jobs run from `projects/blind-to-x` and `projects/shorts-maker-v2`, and frontend jobs target `projects/hanwoo-dashboard` plus `projects/knowledge-dashboard`.
- `projects/shorts-maker-v2` still has a dual package shape on `2026-04-01`: the repo-root `shorts_maker_v2/` package is a namespace bridge in front of `src/shorts_maker_v2/`. Tests import the bridge first, so package-level entrypoints such as `run_cli` must be mirrored there, not only in `src/`.
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
- `venv\Scripts\python.exe -m pytest workspace\tests\test_shorts_manager.py workspace\tests\test_vibe_debt_auditor.py -q -o addopts=` -> **44 passed**
- `venv\Scripts\python.exe -m coverage run --source=execution.pages.shorts_manager -m pytest workspace\tests\test_shorts_manager.py -q -o addopts=` + `coverage report -m --include="*shorts_manager.py"` -> `workspace/execution/pages/shorts_manager.py` **71%**
- `venv\Scripts\python.exe -m ruff check workspace\execution\pages\shorts_manager.py workspace\tests\test_shorts_manager.py workspace\execution\vibe_debt_auditor.py workspace\tests\test_vibe_debt_auditor.py` -> **All checks passed**
- `venv\Scripts\python.exe workspace\execution\vibe_debt_auditor.py --format json --top 10` -> latest rerun **overall 38.9% / workspace 29.25% / `shorts_manager.py` 32.9**
- Detached `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py -o .tmp\qaqc_system_check_2026-04-01.json` -> **`CONDITIONALLY_APPROVED`** / `2168 passed / 0 failed / 2 errors / 22 skipped`
- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests -q --tb=short --no-header -o addopts= --maxfail=50` -> **2 collection errors** in `workspace\tests\test_topic_auto_generator.py` and `workspace\tests\test_vibe_debt_auditor.py`, both caused by `ImportError: cannot import name 'REPO_ROOT' from 'path_contract'`
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py` -> **`APPROVED`** / `3066 passed / 0 failed / 0 errors / 29 skipped`, `blind-to-x 723 passed / 16 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 1073 passed / 1 skipped`
- `venv\Scripts\python.exe -m compileall workspace\execution\repo_map.py workspace\execution\context_selector.py workspace\execution\graph_engine.py` -> **pass**
- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests\test_governance_checks.py workspace\tests\test_health_check.py workspace\tests\test_qaqc_runner.py workspace\tests\test_qaqc_runner_extended.py -q -o addopts=` -> **74 passed**
- `..\..\venv\Scripts\python.exe -m pytest tests\integration\test_golden_render.py -q -o addopts=` (`projects/shorts-maker-v2`) -> **2 passed, 2 warnings** in about **2m17s**
- `venv\Scripts\python.exe -m ruff check workspace/scripts/check_mapping.py workspace/execution/governance_checks.py workspace/execution/health_check.py workspace/execution/qaqc_runner.py workspace/execution/qaqc_history_db.py workspace/tests/test_governance_checks.py workspace/tests/test_doctor.py workspace/tests/test_health_check.py workspace/tests/test_qaqc_runner.py workspace/tests/test_qaqc_runner_extended.py workspace/tests/test_mcp_config.py` -> **All checks passed**
- `venv\Scripts\python.exe -m pytest workspace/tests/test_governance_checks.py workspace/tests/test_doctor.py workspace/tests/test_health_check.py workspace/tests/test_qaqc_runner.py workspace/tests/test_qaqc_runner_extended.py workspace/tests/test_mcp_config.py -q -o addopts=` -> **79 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest workspace/tests/test_shorts_manager_helpers.py workspace/tests/test_topic_auto_generator.py workspace/tests/test_vibe_debt_auditor.py -q --tb=short -o addopts= --maxfail=10` -> **68 passed**
- `..\..\venv\Scripts\python.exe -m pytest tests/unit/test_audio_postprocess.py -q --tb=short --maxfail=1 -o addopts=` (`projects/shorts-maker-v2`) -> **41 passed**
- `venv\Scripts\python.exe -m pytest projects/shorts-maker-v2/tests/unit/test_audio_postprocess.py projects/shorts-maker-v2/tests/unit/test_package_entrypoints.py -q -o addopts=` -> **44 passed, 1 warning**
- Batched `..\..\venv\Scripts\python.exe -m pytest ... -q --tb=short --maxfail=1 -o addopts=` runs across the remaining `projects/shorts-maker-v2/tests/unit` and `tests/integration` files -> **all passing locally after the `audio_postprocess.py` and bridge-package fixes**
- `..\..\venv\Scripts\python.exe -X utf8 -m pytest tests/unit/test_cost_controls.py::test_cost_tracker_uses_persisted_daily_totals -q --tb=short -o addopts= --maxfail=1` (`projects/blind-to-x`) -> **1 passed**
- `..\..\venv\Scripts\python.exe -X utf8 -m pytest tests/unit/test_optimizations.py::TestDraftGeneratorCache::test_second_call_uses_cache -q --tb=short -o addopts= --maxfail=1` (`projects/blind-to-x`) -> **2 consecutive isolated passes**
- Verified sequential blind unit slices after the `draft_cache.py` fix:
  - `tests/unit` files `[0..15]` -> **163 passed, 1 skipped**
  - `tests/unit` files `[16..19]` -> **34 passed**
  - `tests/unit` files `[20..23]` -> **40 passed**
  - `tests/unit` files `[24..27]` -> **98 passed**
  - `tests/unit` files `[29..31]` -> **54 passed, 1 skipped**
  - `tests/unit` files `[32..47]` -> **247 passed, 6 skipped**
  - `tests/unit` files `[48..end]` -> **154 passed, 1 warning**
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

1. Confirm `T-116` with the next full shared QC: the targeted root rerun is green in the current dirty worktree, but the shared baseline still needs one fresh end-to-end confirmation.
2. Start `T-123`: move `projects/knowledge-dashboard` away from public `public/*.json` exposure and toward authenticated server/API delivery for dashboard + QA/QC data.
3. Start `T-124`: add frontend smoke coverage for `hanwoo-dashboard` and `knowledge-dashboard` so CI validates auth/payment/dashboard flows instead of only `lint` + `build`.
4. Fix `T-120` (`fastapi` missing): `test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` still breaks on `ModuleNotFoundError`.
5. Investigate `T-121`: determine whether the local `projects/blind-to-x/tests/unit/test_main.py` `KeyboardInterrupt` is a harness-only artifact or a real `main.py` problem.

## Notes

- The repo is currently mid-merge in `projects/blind-to-x` (`MERGE_HEAD` present with unresolved `AA` / `UU` files). Do not commit or try to clean that state as part of control-plane work unless the user explicitly redirects the session there.
- `coverage run` is the reliable measurement path for `shorts-maker-v2` on this Windows machine; `pytest-cov` can still trip over duplicate root/project paths.
- On Windows, prefer the updated `workspace/execution/health_check.py` entrypoint over older ad-hoc snippets for environment diagnosis; it now forces UTF-8 console output before printing detailed reports.
- `CostDatabase._connect()` is still a live compatibility surface used by `content_calendar.py`, `content_intelligence.py`, and calibration helpers. Do not remove it just because `_conn()` exists.
- During active BlindToX schedule windows, the infra snapshot can show `4/6 Ready` because the remaining two tasks are legitimately `Running`; confirm with `schtasks /query` before treating that as a regression.
- For `blind-to-x` rule edits, treat `projects/blind-to-x/rules/*.yaml` as the source of truth; the root `classification_rules.yaml` is a compatibility snapshot/fallback surface.
- When targeted `coverage report` looks wrong for a Windows path, prefer `coverage report -m --include="*module_name.py"`.
- Compare VibeDebt snapshots carefully across `2026-03-31` entries: part of the latest workspace TDR drop comes from the corrected `score_test_gap()` parent-directory scan, not just from new test additions.
- `ContextSelector` defaults to `workspace/` roots unless the prompt explicitly points to `projects/` or `infrastructure/`, which helps keep unrelated `blind-to-x` WIP files out of control-plane coding prompts.
- `.tmp/repo_map_cache.db` is a deterministic intermediate cache, not a deliverable. It can be deleted and rebuilt safely when debugging repo-map selection issues.
- `workspace/execution/pr_triage_worktree.py` is safe to run against dirty repos because it checks out a detached linked worktree, but it currently assumes the needed refs already exist locally and does not fetch remotes on your behalf.
- Node-backed triage profiles intentionally reuse the source repo's existing `node_modules`; if dependencies are missing, `pr_triage_orchestrator.py` marks the command as `SKIP` instead of installing packages in the isolated worktree.
- Long foreground `qaqc_runner.py` invocations can still get interrupted by the current terminal wrapper on this machine; the `2026-04-01` rerun succeeded only after launching the runner as a detached Python process and polling its log/output files.
