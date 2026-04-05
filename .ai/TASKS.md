# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|
| T-100 | Raise `blind-to-x` coverage to `>=75%` (currently ~71%).                                                      | Codex  | Med      | 2026-03-31 |
| T-121 | Resolve `KeyboardInterrupt` in `test_main.py` when run under certain terminal wrappers.                        | Codex  | Low      | 2026-04-01 |
| T-142 | Run `workspace/scripts/migrate_to_workspace_db.py` to actually move existing data into `workspace.db` and delete `.bak` files after verification. | Human | Med | 2026-04-04 |
| T-146 | Phase 2 PoC: Wrap `blind-to-x` research subtask with DeepAgents SDK in isolated sandbox and benchmark cost/quality. | Claude | Med | 2026-04-05 |
| T-148 | Phase 3: Implement context auto-compaction and Generator-Evaluator split using harness middleware patterns. | Claude | Med | 2026-04-05 |
| T-149 | Add `hanwoo-dashboard` `/api/dashboard/summary`, `/api/dashboard/cattle`, and `/api/dashboard/sales` routes with cache-backed reads and cursor pagination. | Codex | High | 2026-04-05 |

## IN_PROGRESS

| ID    | Task                                                                                                                                                                                                                                 | Owner | Started    | Notes |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|------------|-------|
| T-129 | Scale-harden `hanwoo-dashboard` for 100x traffic: cached read models, pagination, and client refactoring.                                                                                                                            | Codex | 2026-04-02 | Outbox worker + local-state invalidation + dynamic client split done. Next: T-149 dashboard routes + cursor pagination. |
| T-145 | Build Harness Engineering AI Phase 0-1: Tool Permission registry, HarnessSession middleware (observability/loop-detect/budget), agent_permissions.yaml. | Claude | 2026-04-05 | Phase 1 complete. |

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-147 | Create `hanwoo-dashboard` outbox worker script (`scripts/outbox-worker.mjs`) that consumes pending events and refreshes read-model snapshots. | Claude | 2026-04-05 |
| T-120 | Fix `test_auto_schedule_paths.py` FastAPI dependency by letting bridge helper imports work without FastAPI installed. | Codex | 2026-04-05 |
| T-144 | Wire `projects/shorts-maker-v2` `GrowthLoopEngine` to the shared YouTube analytics collectors and expose a project-local sync/decision command. | Codex | 2026-04-05 |
| T-143 | Design and scaffold the `projects/shorts-maker-v2` closed-loop growth engine for post-publish YouTube feedback, variant ranking, and next-batch recommendations. | Codex | 2026-04-04 |
| T-140 | Resolve the actionable SQL-injection-style QA/QC finding in `projects/blind-to-x/pipeline/escalation_queue.py` and clear the shared DEEP security gate. | Codex | 2026-04-04 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
