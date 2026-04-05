# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|
| T-142 | Run `workspace/scripts/migrate_to_workspace_db.py` to actually move existing data into `workspace.db` and delete `.bak` files after verification. | Human | Med | 2026-04-04 |
| T-150 | TASKS.md 정리: T-145/T-146/T-148 완료 반영, Harness Phase 0-3 전체 DONE 이동. | Claude | Low | 2026-04-05 |
| T-151 | Wire `hanwoo-dashboard` cattle/sales interactive surfaces to the new `/api/dashboard/*` paginated routes so those screens stop depending on full-array initial loads. | Codex | High | 2026-04-05 |

## IN_PROGRESS

| ID    | Task                                                                                                                                                                                                                                 | Owner | Started    | Notes |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|------------|-------|
| T-129 | Scale-harden `hanwoo-dashboard` for 100x traffic: cached read models, pagination, and client refactoring.                                                                                                                            | Codex | 2026-04-02 | Outbox worker + local-state invalidation + dashboard routes done. Next: T-151 wire cattle/sales UI to paginated route reads. |
| T-146 | Phase 2-3: Generator-Evaluator harness, context auto-compaction, YAML session factory, tool-output offloading. | Claude | 2026-04-05 | Complete. 56 tests, 86% coverage. |

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-149 | Add `hanwoo-dashboard` `/api/dashboard/summary`, `/api/dashboard/cattle`, and `/api/dashboard/sales` routes with cache-backed reads and cursor pagination. | Codex | 2026-04-05 |
| T-100 | Raise `blind-to-x` coverage to >=75%. Achieved **82%** with 93 new tests across 5 modules (draft_prompts, daily_digest, draft_providers, sentiment_tracker, editorial_reviewer). | Claude | 2026-04-05 |
| T-121 | Fix `test_main.py` collection error: `sys.modules['main']` collision when run in full suite. Root cause: another project's main.py shadowed blind-to-x/main.py. | Claude | 2026-04-05 |
| T-147 | Create `hanwoo-dashboard` outbox worker script (`scripts/outbox-worker.mjs`) that consumes pending events and refreshes read-model snapshots. | Claude | 2026-04-05 |
| T-120 | Fix `test_auto_schedule_paths.py` FastAPI dependency by letting bridge helper imports work without FastAPI installed. | Codex | 2026-04-05 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
