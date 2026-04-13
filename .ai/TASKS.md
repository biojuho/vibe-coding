# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|
| T-189 | `hanwoo-dashboard` 브라우저 자동화 환경 복구 (Playwright `0xc0000005` Access Violation) | Any | Medium | 2026-04-13 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-161 | `hanwoo-dashboard` UX/UI polish pass + QC (PremiumCard clay, alert banners CSS 변수 전환, footer 접근성, dead code 제거) | Gemini | 2026-04-13 |
| T-188 | [`blind-to-x`] Clean up the remaining `tests/unit/test_process.py` lint issue after the timeout-targeting edits and re-verify the focused process tests. | Codex | 2026-04-11 |
| T-187 | [`workspace`] Patch the local `code-review-graph` Python 3.13 package for UTF-8-safe file and git subprocess handling so `detect-changes` no longer crashes on Windows `cp949`. | Codex | 2026-04-11 |
| T-186 | [`blind-to-x`] Resolve the live Notion status-query 400 path in `pipeline/notion/_query.py` by mapping logical status labels to actual select options and canonicalizing the returned labels. | Codex | 2026-04-11 |
| T-185 | [`blind-to-x`] Fix unit-test environment leakage so `.env` or earlier `load_env()` calls cannot override `NotionUploader` test fixtures via `NOTION_DATABASE_ID` / `NOTION_PROP_*`. | Codex | 2026-04-11 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
