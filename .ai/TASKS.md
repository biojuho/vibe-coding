# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-215 | `[workspace]` Public conversion follow-up: rotate/revoke the previously exposed Brave API key and NotebookLM session, then decide whether a history rewrite is still required before making the repo public. | User | P0 | 🔴 approval | 2026-04-15 |
| T-199 | `[workspace]` GitHub branch protection for `main` requiring CI pass. Blocked because the repo is private on a free plan and the live API check returned HTTP 403. | User | P1 | 🔴 approval | 2026-04-14 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-221 | `[hanwoo-dashboard]` Next 16 production build restored by switching the build script to `next build --webpack` after Turbopack failed on `next/font/google` in `src/app/layout.js`; `npm run build` and `npm test` passed. | Codex | 2026-04-17 |
| T-220 | `[shorts-maker-v2]` Phase 2 render test split finished: `test_render_step_*.py` import issue fixed via `conftest_render`, full split suite green. | Gemini (Antigravity) | 2026-04-17 |
| T-217 | `[blind-to-x]` `main.py` split confirmed complete with `pipeline/cli.py`, `runner.py`, and `bootstrap.py`; `test_main.py` 20/20 passed. | Gemini (Antigravity) | 2026-04-15 |
| T-219 | `[blind-to-x]` Pydantic V2 migration: `fetch_stage.py` `.dict()` calls replaced with `.model_dump()`, deprecation warning removed, focused tests passed. | Gemini (Antigravity) | 2026-04-15 |
| T-218 | `[blind-to-x]` `blind_scraper.py` import path fixed and `test_main.py` monkeypatch targets updated; full focused verification passed. | Gemini (Antigravity) | 2026-04-15 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short “continue/go” command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
