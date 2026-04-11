# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|
| T-184 | [`workspace`] Refresh or disable the invalid Moonshot credential so shared `health_check.py` stops failing on `401 Unauthorized`. | Codex | Medium | 2026-04-11 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-161 | `hanwoo-dashboard` UX/UI polish pass owned by another tool. | Claude | 2026-04-07 | Leave unrelated UI work untouched unless the user explicitly redirects the session. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-183 | [`workspace`] Resolve the stale `[TASK: T-100]` follow-up in `workspace/directives/system_audit_action_plan.md` so governance alignment passes again. | Codex | 2026-04-11 |
| T-182 | [`workspace`] Map the new harness execution scripts in `workspace/directives/INDEX.md` so governance checks stop flagging orphan files. | Codex | 2026-04-11 |
| T-181 | [`blind-to-x`] Fix test suite cache interference by replacing manual `_draft_rules_cache` mutations with `unittest.mock.patch` for `_load_draft_rules`. | Gemini (Antigravity) | 2026-04-10 |
| T-180 | [`blind-to-x`] Fix review-only generation failures so today's Notion queue backfills to five live cards. | Codex | 2026-04-09 |
| T-179 | [`blind-to-x`] Add a daily review queue floor so Notion gets at least five cards per day. | Codex | 2026-04-09 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
