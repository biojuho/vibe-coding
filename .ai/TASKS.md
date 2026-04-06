# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|
| T-157 | Harden `projects/hanwoo-dashboard` market-price/KAPE fallback so synthetic data cannot masquerade as live production data, and add degraded/stale-state coverage. | Codex | High | 2026-04-07 |

## IN_PROGRESS

| ID    | Task                                                                                                                                                                                                                                 | Owner | Started    | Notes |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|------------|-------|

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-156 | Harden `projects/hanwoo-dashboard/src/app/api/payments/confirm/route.js` against upstream timeout/non-JSON failure bodies and add focused regression tests. | Codex | 2026-04-07 |
| T-155 | Harden `hanwoo-dashboard` server mutation inputs with shared server-side validation and focused unit tests for malformed payloads. | Codex | 2026-04-06 |
| T-153 | Delete `.tmp/*.db.bak` files after verifying workspace.db migration is stable. | Gemini | 2026-04-06 |
| T-154 | Clean up unused imports (F401) across `execution/` and `tests/` and verify with QA/QC pipeline (APPROVED) | Gemini | 2026-04-06 |
| T-152 | Fix 3 pre-existing test failures in `blind-to-x`. 45 new harness tests + integration verification. | Gemini | 2026-04-06 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
