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
| T-187 | [`workspace`] Patch the local `code-review-graph` Python 3.13 package for UTF-8-safe file and git subprocess handling so `detect-changes` no longer crashes on Windows `cp949`. | Codex | 2026-04-11 |
| T-186 | [`blind-to-x`] Resolve the live Notion status-query 400 path in `pipeline/notion/_query.py` by mapping logical status labels to actual select options and canonicalizing the returned labels. | Codex | 2026-04-11 |
| T-185 | [`blind-to-x`] Fix unit-test environment leakage so `.env` or earlier `load_env()` calls cannot override `NotionUploader` test fixtures via `NOTION_DATABASE_ID` / `NOTION_PROP_*`. | Codex | 2026-04-11 |
| T-184 | [`workspace`] Treat Moonshot as an optional degraded provider so shared `health_check.py` no longer hard-fails when that fallback is disabled or invalid. | Codex | 2026-04-11 |
| T-183 | [`workspace`] Resolve the stale `[TASK: T-100]` follow-up in `workspace/directives/system_audit_action_plan.md` so governance alignment passes again. | Codex | 2026-04-11 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
