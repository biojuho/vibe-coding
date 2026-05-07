# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-242 | `[workspace]` Full QC pass completed: graph risk `0.00`, `git diff --check` clean, shared health `overall: warn` with `fail: 0`, governance OK, branch protection configured, 0 open PRs, targeted secret scan clean, workspace Ruff/pytest passed, active project test/lint/build paths passed, and Playwright Chromium smoke passed. | Codex | 2026-05-07 |
| T-241 | `[workspace]` QC pass recorded: shared health `warn 7 / fail 0` (expected optional providers), governance `ok`, graph detect-changes risk `0.00`, workspace Ruff clean, workspace pytest `1283 passed / 1 skipped`, `blind-to-x` & `shorts-maker-v2` Ruff clean, `git diff --check` clean, 0 open PRs. | Claude Code (Opus 4.7 1M) | 2026-05-07 |
| T-231 | `[blind-to-x]` Playwright Chromium browser binary installed (`chromium-headless-shell v1208`, 108.8 MiB). Smoke test passed. Browser-only scraping now fully functional. | Gemini (Antigravity) | 2026-05-06 |
| T-234 | `[workspace]` PR #31 closed, PR #32 created with QC fixes + AI context sync, CI all-green, squash-merged. Local main synced with origin/main. Branch protection temporarily adjusted and restored. | Gemini (Antigravity) | 2026-05-06 |
| T-239 | `[workspace]` Project-by-project code review completed for local `main` vs `origin/main`; no blocking findings found. | Codex | 2026-05-06 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
