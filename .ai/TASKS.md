# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO
| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|
| T-163 | Run a fresh post-fix SRE scan across the active projects and confirm whether any new reliability issues remain after the deep-debug sweep. | Codex | High | 2026-04-07 |

## IN_PROGRESS
| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-161 | `hanwoo-dashboard` UX/UI polish pass owned by another tool. | Claude | 2026-04-07 | Leave unrelated UI work untouched unless the user explicitly redirects the session. |

## DONE (Latest 5)
| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-162 | Harden the `hanwoo-dashboard` offline sync queue with retry caps/dead-letter handling and stabilize notification timestamps so alert cards do not drift on refresh. | Codex | 2026-04-07 |
| T-160 | Harden the remaining `hanwoo-dashboard` client-side refresh/read fetches so post-mutation summary updates and auxiliary dashboard reads fail softly on timeout or malformed payloads. | Codex | 2026-04-07 |
| T-159 | Harden the `hanwoo-dashboard` weather fetch path in `DashboardClient` so timeouts and shape drift degrade cleanly instead of silently breaking the widget. | Codex | 2026-04-07 |
| T-158 | Harden `projects/hanwoo-dashboard/src/lib/actions.js#getCattleHistory` so one malformed metadata JSON row cannot fail the entire history response, and add mixed-validity coverage. | Codex | 2026-04-07 |
| T-157 | Harden the `hanwoo-dashboard` market-price/KAPE fallback so synthetic data cannot masquerade as live production data, and add degraded/stale-state coverage. | Codex | 2026-04-07 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
