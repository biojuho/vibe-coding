# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-226 | `[workspace]` Post-merge cleanup stabilization follow-up: PR `#27` carries the missed cleanup stabilization delta, but it is now behind `main` and its old CI run is red. | Codex | 2026-04-18 | Local targeted checks are green on the current dirty worktree of `fix/pr25-post-merge-stabilization`: `blind-to-x` `test_content_calendar_branches.py` (`6 passed`), `shorts-maker-v2` `test_trend_discovery_step.py` (`37 passed`), and `hanwoo-dashboard` `node scripts/smoke.mjs` (exit `0`). Final `git status --short --branch` shows the branch is now `behind 3` versus `origin/fix/pr25-post-merge-stabilization` with additional local edits and untracked files, so the worktree must be reconciled before the old red CI can be trusted or refreshed. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-227 | `[blind-to-x]` Scraper short-content failure handling and unit coverage were stabilized across Blind / FMKorea / Jobplanet, and the focused scraper + escalation checks were revalidated green. | Codex | 2026-04-18 |
| T-223 | `[workspace]` Public flip rollout completed: sanitized `.tmp/public-history-rewrite` was force-pushed to `origin/main`, the repo became public, and the old private-plan blocker was removed. | Gemini (Antigravity) | 2026-04-17 |
| T-199 | `[workspace]` GitHub branch protection for `main` was applied successfully; the latest live check now reports `status: configured` with required checks `root-quality-gate` and `test-summary`. | Gemini (Antigravity) | 2026-04-17 |
| T-215 | `[workspace]` Public-history decision recorded: because rotated Brave / NotebookLM secrets still exist in past commits, any future public visibility change must use the sanitized `.tmp/public-history-rewrite` history rather than exposing the current unre-written repo history. | Codex | 2026-04-17 |
| T-222 | `[hanwoo-dashboard]` DashboardClient 훅 분리 (useWeather, useOfflineSyncQueue 등) 및 위젯/분석 탭 UI 폴리싱 (PremiumCard, 다국어 처리) 적용. `npm test` 51/51 통과. | Gemini (Antigravity) | 2026-04-17 |
| T-221 | `[hanwoo-dashboard]` Next 16 production build restored by switching the build script to `next build --webpack` after Turbopack failed on `next/font/google` in `src/app/layout.js`; `npm run build` and `npm test` passed. | Codex | 2026-04-17 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short “continue/go” command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
