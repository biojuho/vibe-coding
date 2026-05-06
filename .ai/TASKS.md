# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-234 | `[workspace]` Resolve open PR #31 (`ai-context/2026-04-30-cleanup`) and sync local `main` with `origin/main`. The PR is mergeable and all checks pass, but branch protection still requires review; local `main` is ahead 6 after the latest QC/context commits. | User | P1 | `approval` | 2026-05-06 |
| T-231 | `[blind-to-x]` Provision Playwright browser binaries in the runtime if screenshot/browser-only Blind scraping is still required. The code now falls back to HTML-only extraction when the executable is missing. | User | P1 | `approval` | 2026-04-21 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-238 | `[workspace]` Code review of local `main` vs `origin/main` completed; no blocking findings found in the current diff. | Codex | 2026-05-06 |
| T-237 | `[workspace]` Full system recheck passed with no hard failures across shared health/governance, active project test/lint/build paths, graph change detection, PR/branch inventory, and targeted secret scan. | Codex | 2026-05-06 |
| T-235 | `[workspace]` Broad workspace Ruff sweep is now canonical-clean for `workspace/execution` and `workspace/tests`; expected path-bootstrap E402 exceptions are documented in `workspace/pyproject.toml`. Feature commit: `d14e897`. | Codex | 2026-05-06 |
| T-236 | `[shorts-maker-v2]` Full QC failure fixed: growth-sync date fixture no longer expires, full Ruff is clean, and graph SQLite WAL files are ignored. Feature commit: `611d151`. | Codex | 2026-05-06 |
| T-233 | `[workspace]` Dependabot PRs #28 (actions/setup-node 4→6) and #29 (dependabot/fetch-metadata 2→3) merged. All CI green. | Gemini (Antigravity) | 2026-04-30 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
