# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|
| T-100 | Raise `blind-to-x` coverage to `>=75%` (currently ~71%).                                                      | Codex  | Med      | 2026-03-31 |
| T-128 | `test_cost_tracker_uses_persisted_daily_totals` isolation bug: investigate and fix cross-test interference.    | Codex  | Med      | 2026-04-02 |
| T-121 | Resolve `KeyboardInterrupt` in `test_main.py` when run under certain terminal wrappers.                        | Codex  | Low      | 2026-04-01 |
| T-120 | Fix `workspace/tests/test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` (`fastapi` missing in local env). | Codex | High | 2026-04-01 |

## IN_PROGRESS

| ID    | Task                                                                                                                                                                                                                                 | Owner | Started    | Notes |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|------------|-------|
| T-129 | Scale-harden `hanwoo-dashboard` for 100x traffic: cached read models, pagination, and client refactoring.                                                                                                                            | Codex | 2026-04-02 | Redis/BullMQ foundation ready. |

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-138 | Replace deprecated `asyncio.iscoroutinefunction` usage in `projects/blind-to-x/pipeline/observability.py` with `inspect.iscoroutinefunction`.                                                                                      | Codex        | 2026-04-04 |
| T-130 | Write unit tests for the remaining new `blind-to-x` modules (`observability`, `db_backend`, etc.) now that `cost_db_pg` and `task_queue` are covered.                                                                              | Codex        | 2026-04-04 |
| T-137 | Add focused `blind-to-x` unit coverage for `pipeline.task_queue` and `pipeline.cost_db_pg`.                                                                                                                                          | Codex        | 2026-04-04 |
| T-136 | Restore `blind-to-x` generic image prompt scene defaults and clear the last DEEP integration failure.                                                                                                                                | Codex        | 2026-04-03 |
| T-133 | Restore sync contract & repair `scheduler_engine.py` (verified).                                                                                                                                                                     | Antigravity  | 2026-04-03 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
