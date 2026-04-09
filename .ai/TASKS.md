# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-161 | `hanwoo-dashboard` UX/UI polish pass owned by another tool. | Claude | 2026-04-07 | Leave unrelated UI work untouched unless the user explicitly redirects the session. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-181 | [`blind-to-x`] Fix test suite cache interference by replacing manual `_draft_rules_cache` mutations with `unittest.mock.patch` for `_load_draft_rules`. | Gemini (Antigravity) | 2026-04-10 |
| T-180 | [`blind-to-x`] Fix review-only generation failures so today's Notion queue backfills to five live cards. | Codex | 2026-04-09 |
| T-179 | [`blind-to-x`] Add a daily review queue floor so Notion gets at least five cards per day. | Codex | 2026-04-09 |
| T-178 | [`blind-to-x`] Make empty-draft Notion review cards actionable with explicit next-step copy. | Codex | 2026-04-09 |
| T-177 | [`blind-to-x`] Backfilled historical Notion review columns, added reviewer-memory prompt input, and applied the backfill to the live Notion DB. | Codex | 2026-04-09 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
