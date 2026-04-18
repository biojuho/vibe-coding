# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-229 | `[workspace]` Publish the local `main` recovery commits (`96e6daf`, `7c56a15`) by either pushing `main` or opening a new PR. PR `#27` is closed/unmerged and its remote head branch is gone. | User | P0 | 🔴 approval | 2026-04-18 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-228 | `[workspace]` Local CI stabilization recovery completed on `main`: `blind-to-x`, `shorts-maker-v2`, and `hanwoo-dashboard` failing checks were fixed locally and revalidated green. Feature commit: `7c56a15`. | Codex | 2026-04-18 |
| T-227 | `[blind-to-x]` Scraper short-content failure handling and unit coverage were stabilized across Blind / FMKorea / Jobplanet, and the focused scraper + escalation checks were revalidated green. | Codex | 2026-04-18 |
| T-224 | `[workspace]` GitHub Action Quality Gate 에러(매핑 누락, 모듈 충돌) 해결 및 QC 테스트 완료. | Gemini (Antigravity) | 2026-04-18 |
| T-223 | `[workspace]` Public flip rollout completed: sanitized `.tmp/public-history-rewrite` was force-pushed to `origin/main`, the repo became public, and the old private-plan blocker was removed. | Gemini (Antigravity) | 2026-04-17 |
| T-199 | `[workspace]` GitHub branch protection for `main` was applied successfully; the latest live check now reports `status: configured` with required checks `root-quality-gate` and `test-summary`. | Gemini (Antigravity) | 2026-04-17 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short “continue/go” command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
