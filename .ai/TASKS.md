# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|
| T-160 | Harden the remaining `hanwoo-dashboard` client-side refresh/read fetches so post-mutation summary updates and auxiliary dashboard reads fail softly on timeout or malformed payloads. | Codex | High | 2026-04-07 |

## IN_PROGRESS

| ID    | Task                                                                                                                                                                                                                                 | Owner | Started    | Notes |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|------------|-------|

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-159 | Harden the `hanwoo-dashboard` weather fetch path in `DashboardClient` so timeouts and shape drift degrade cleanly instead of silently breaking the widget. | Codex | 2026-04-07 |
| T-158 | Harden `projects/hanwoo-dashboard/src/lib/actions.js#getCattleHistory` so one malformed `metadata` JSON row cannot fail the entire history response, and add mixed-validity coverage. | Codex | 2026-04-07 |
| T-157 | Harden `projects/hanwoo-dashboard` market-price/KAPE fallback so synthetic data cannot masquerade as live production data, and add degraded/stale-state coverage. | Codex | 2026-04-07 |
| T-156 | Harden `projects/hanwoo-dashboard/src/app/api/payments/confirm/route.js` against upstream timeout/non-JSON failure bodies and add focused regression tests. | Codex | 2026-04-07 |
| T-155 | Harden `hanwoo-dashboard` server mutation inputs with shared server-side validation and focused unit tests for malformed payloads. | Codex | 2026-04-06 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
