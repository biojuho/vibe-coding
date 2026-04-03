# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|
| T-100 | Raise `blind-to-x` coverage to `>=75%` (currently ~71%).                                                      | Codex  | Med      | 2026-03-31 |
| T-128 | `test_cost_tracker_uses_persisted_daily_totals` isolation bug: investigate and fix cross-test interference.    | Codex  | Med      | 2026-04-02 |
| T-121 | Resolve `KeyboardInterrupt` in `test_main.py` when run under certain terminal wrappers.                        | Codex  | Low      | 2026-04-01 |
| T-130 | Write unit tests for new modules (`cost_db_pg`, `task_queue`, etc.) to support T-100 goals.                   | Claude | Normal   | 2026-04-02 |
| T-120 | Fix `workspace/tests/test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` (`fastapi` missing in local env). | Codex | High | 2026-04-01 |

## IN_PROGRESS

| ID    | Task                                                                                                                                                                                                                                 | Owner | Started    | Notes |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|------------|-------|
| T-129 | Scale-harden `hanwoo-dashboard` for 100x traffic: cached read models, pagination, and client refactoring.                                                                                                                            | Codex | 2026-04-02 | Redis/BullMQ foundation ready. |

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-136 | Restore `blind-to-x` generic image prompt scene defaults and clear the last DEEP integration failure.                                                                                                                                | Codex        | 2026-04-03 |
| T-133 | Restore sync contract & repair `scheduler_engine.py` (verified).                                                                                                                                                                     | Antigravity  | 2026-04-03 |
| T-134 | Fix `blind-to-x` regressions (scraper compatibility and newsletter guard).                                                                                                                                                            | Antigravity  | 2026-04-03 |
| T-135 | Fix `qaqc_runner.py` discovery failure on Windows subdirs.                                                                                                                                                                            | Antigravity  | 2026-04-03 |
| T-132 | Review-driven cleanup for `projects/hanwoo-dashboard`: Next.js 16/Postgres alignment and security patches.                                                                                                                           | Codex        | 2026-04-02 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
