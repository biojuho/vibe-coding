# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|
| T-100 | Raise `blind-to-x` coverage to `>=75%` (currently ~71%).                                                      | Codex  | Med      | 2026-03-31 |
| T-121 | Resolve `KeyboardInterrupt` in `test_main.py` when run under certain terminal wrappers.                        | Codex  | Low      | 2026-04-01 |
| T-120 | Fix `workspace/tests/test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` (`fastapi` missing in local env). | Codex | High | 2026-04-01 |
| T-142 | Run `workspace/scripts/migrate_to_workspace_db.py` to actually move existing data into `workspace.db` and delete `.bak` files after verification. | Human | Med | 2026-04-04 |
| T-144 | Wire `projects/shorts-maker-v2` `GrowthLoopEngine` to the shared YouTube analytics collectors and expose a project-local sync/decision command. | Codex | High | 2026-04-04 |

## IN_PROGRESS

| ID    | Task                                                                                                                                                                                                                                 | Owner | Started    | Notes |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|------------|-------|
| T-129 | Scale-harden `hanwoo-dashboard` for 100x traffic: cached read models, pagination, and client refactoring.                                                                                                                            | Codex | 2026-04-02 | Redis/BullMQ foundation ready. |

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-143 | Design and scaffold the `projects/shorts-maker-v2` closed-loop growth engine for post-publish YouTube feedback, variant ranking, and next-batch recommendations. | Codex | 2026-04-04 |
| T-140 | Resolve the actionable SQL-injection-style QA/QC finding in `projects/blind-to-x/pipeline/escalation_queue.py` and clear the shared DEEP security gate. | Codex | 2026-04-04 |
| T-139 | Fix `workspace/scripts/migrate_to_workspace_db.py` so `workspace/scripts/quality_gate.py` passes lint and high-severity static analysis again. | Codex | 2026-04-04 |
| T-141 | Resolve QA/QC Phase 2 regression in Telegram Phase callback handler by catching initial malformed message ID payloads.                                                                                                                | Antigravity  | 2026-04-04 |
| T-138 | Replace deprecated `asyncio.iscoroutinefunction` usage in `projects/blind-to-x/pipeline/observability.py` with `inspect.iscoroutinefunction`.                                                                                      | Codex        | 2026-04-04 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
