# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-224 | `[workspace]` Public-repo cleanup PR `#25`: stop tracking `.code-review-graph/graph.db` and unblock merge by fixing repo-wide CI drift exposed on `chore/public-repo-cleanup`. Latest remote head is `9c296a9`, while GitHub PR metadata is still showing the previous head `ebfaec9` (trigger lag under observation). | AI | 2026-04-17 | Local checks now pass for `knowledge-dashboard` (`npm run build`, `npm run smoke`), `hanwoo-dashboard` (`npm run smoke` with `DATABASE_URL`), and `blind-to-x` targeted `test_content_calendar_branches.py`; PR review is still required. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-223 | `[workspace]` Public flip rollout: dependabot PRs resolved, and sanitized `.tmp/public-history-rewrite` force-pushed to origin `main` and `codex/dashboard-refresh` before the repo was made public. | Gemini (Antigravity) | 2026-04-17 |
| T-199 | `[workspace]` GitHub branch protection for `main` requiring CI pass successfully applied using `execution/github_branch_protection.py --apply`. | Gemini (Antigravity) | 2026-04-17 |
| T-215 | `[workspace]` Public-history decision recorded: because rotated Brave / NotebookLM secrets still exist in past commits, any future public visibility change must use the sanitized `.tmp/public-history-rewrite` history rather than exposing the current unre-written repo history. | Codex | 2026-04-17 |
| T-222 | `[hanwoo-dashboard]` DashboardClient split completed with extracted hooks/UI modules and `npm test` kept green. | Gemini (Antigravity) | 2026-04-17 |
| T-221 | `[hanwoo-dashboard]` Next 16 production build restored by switching the build script to `next build --webpack`; `npm run build` and `npm test` passed. | Codex | 2026-04-17 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short continue/go command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
