# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-120 | Fix `test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` failing due to `ModuleNotFoundError: No module named 'fastapi'` — apply `pytest.importorskip('fastapi')` to skip gracefully OR add `fastapi` to workspace dev dependencies. | Antigravity | Medium | 2026-04-01 |
| T-119 | Fix the latent `blind-to-x` unit regressions exposed by the restored active-project CI: `tests/unit/test_cost_controls.py::test_cost_tracker_uses_persisted_daily_totals` and `tests/unit/test_optimizations.py::TestDraftGeneratorCache::test_second_call_uses_cache`. | Codex | High | 2026-04-01 |
| T-116 | Fix the root QC blocker in `workspace/tests`: `test_shorts_manager_helpers.py` mutates `sys.modules["path_contract"]` at import time without `REPO_ROOT`/`TMP_ROOT`, which breaks collection for `test_topic_auto_generator.py` and `test_vibe_debt_auditor.py` during shared QA/QC. | Codex | High | 2026-04-01 |
| T-115 | Continue workspace TDR reduction after the corrected test-gap heuristic: next workspace hotspots are `code_improver.py` (46.2), `workers.py` (37.7), and `result_tracker_db.py` (37.4) | Claude | Low | 2026-03-31 |


## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|
| T-100 | Raise the remaining project coverage follow-up from the system audit so `shorts-maker-v2` and `blind-to-x` reach their documented target floors | Claude | 2026-03-31 | `shorts-maker-v2` coverage pending. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-critical | Resolved 2 Critical Issues from 3rd-party code review: (1) pytest collection error from file name collision `test_lyria_bgm_generator.py` — renamed to `test_lyria_utils.py`. (2) SQLite connection leaks in `execution/content_db.py` (17 functions) — migrated all from `conn = _conn() / conn.close()` to `with _conn() as conn:` context manager + WAL mode. Result: **1207 passed / 1 failed** vs previous 20-23 failures. | Antigravity | 2026-04-01 |
| T-118 | Restored active-project CI coverage for the live repo layout by rewriting `.github/workflows/full-test-matrix.yml` and `.github/workflows/root-quality-gate.yml`, narrowing the workspace lint gate to the real control-plane files, fixing `shorts-maker-v2` lazy pydub/test import behavior, and mirroring the `run_cli` lazy export in the root bridge package. | Codex | 2026-04-01 |
| T-117 | **blind-to-x 내부 로직 개편 + QA/QC ✅ APPROVED** — Phase 1: `_sync_runtime_overrides` 제거 + `BLIND_DEBUG_DB_PATH` 환경변수 기반 로드. Phase 2: `_ProxyModule` + `sys.modules` 교체 삭제. Phase 3: `filter_profile_stage.py` 5개 함수 분해. Phase 4: `generate_review_stage.py` warning 격상 + `components_loaded` 추적. QA 수정: `spec_from_file_location` None 체크 + `@property` dead code 제거. 417 passed / 0 failed. ruff All checks passed. | Antigravity | 2026-04-01 |
| T-114 | Added dedicated tests for `workspace/execution/pages/shorts_manager.py` (14 tests, 71% file coverage), extracted repeated issue-label formatting, and fixed `vibe_debt_auditor.py` so test-gap discovery scans all parent `tests/` directories instead of stopping at the first nested match. Latest rerun: `shorts_manager.py` score **43.9 -> 32.9**, workspace TDR **37.31% -> 29.25%**, overall TDR **40.87% -> 38.9%**. | Codex | 2026-03-31 |
| T-113 | Reduced debt in top 3 hotspots: `llm_client.py` 58.8→41.9 (bridged pattern extraction), `blind-to-x/main.py` 59.2→top10 탈락 (main() split + 20 tests), `karaoke.py` 56.4→top10 탈락 (_scale_style + _measure_words). TDR 41.4%→40.9%. | Claude | 2026-03-31 |
| T-111 | Wired the local-only PR triage worktree helper into `workspace/execution/pr_triage_orchestrator.py`, added repo-specific validation profiles + `triage-report.json` artifacts, documented the new directive, and hardened Windows git-output decoding for non-ASCII paths. | Codex | 2026-03-31 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
