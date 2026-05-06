# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-234 | `[workspace]` Resolve open PR #31 (`ai-context/2026-04-30-cleanup`) and sync local `main` with `origin/main`. The PR is mergeable and all checks pass, but branch protection still requires review; local `main` is ahead 3 after the latest QC/context commits. | User | P1 | `approval` | 2026-05-06 |
| T-235 | `[workspace]` Decide whether broad Ruff sweeps should be canonical. Targeted checks are green, but `python -m ruff check workspace/execution workspace/tests` still reports existing E402 path-bootstrap/legacy issues in shared scripts and legacy/manual tests. | AI | P3 | `approval` | 2026-05-06 |
| T-231 | `[blind-to-x]` Provision Playwright browser binaries in the runtime if screenshot/browser-only Blind scraping is still required. The code now falls back to HTML-only extraction when the executable is missing. | User | P1 | `approval` | 2026-04-21 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-236 | `[shorts-maker-v2]` Full QC failure fixed: growth-sync date fixture no longer expires, full Ruff is clean, and graph SQLite WAL files are ignored. Feature commit: `611d151`. | Codex | 2026-05-06 |
| T-233 | `[workspace]` Dependabot PRs #28 (actions/setup-node 4→6) and #29 (dependabot/fetch-metadata 2→3) merged. All CI green. | Gemini (Antigravity) | 2026-04-30 |
| T-232 | `[workspace]` PR #30 CI 통과 후 merge 완료. Local main synced with origin. | Gemini (Antigravity) | 2026-04-30 |
| T-229 | `[workspace]` Published local recovery commits via PR #30 (`fix/blind-to-x-reliability-pass`). Direct push blocked by branch protection; 4 commits including CI stabilization + blind-to-x reliability pass. | Gemini (Antigravity) | 2026-04-21 |
| T-230 | `[blind-to-x]` Blind scraping now degrades to HTML-only when Playwright browsers are unavailable, and draft generation/review-only output handling was hardened for JSON/plaintext/partial provider responses. | Codex | 2026-04-21 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
