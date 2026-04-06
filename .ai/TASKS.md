# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|

## IN_PROGRESS

| ID    | Task                                                                                                                                                                                                                                 | Owner | Started    | Notes |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|------------|-------|

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-153 | Delete `.tmp/*.db.bak` files after verifying workspace.db migration is stable. | Gemini | 2026-04-06 |
| T-154 | Clean up unused imports (F401) across `execution/` and `tests/` and verify with QA/QC pipeline (APPROVED) | Gemini | 2026-04-06 |
| T-151 | Wire `hanwoo-dashboard` cattle/sales interactive surfaces to the new paginated routes; eliminated full-array initial loads in page.js and DashboardClient.js. | Gemini | 2026-04-05 |
| T-129 | Scale-harden `hanwoo-dashboard` for 100x traffic: cached read models, pagination, and client refactoring. (Completed via T-149 + T-151) | Codex+Gemini | 2026-04-05 |
| T-152 | Fix 3 pre-existing test failures in `blind-to-x`. 45 new harness tests + integration verification. | Gemini | 2026-04-06 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
