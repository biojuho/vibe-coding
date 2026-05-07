# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-248 | `[workspace]` Review newly surfaced unrelated WIP after debug triage: `.github/workflows/full-test-matrix.yml`, `.github/workflows/root-quality-gate.yml`, `infrastructure/n8n/bridge_server.py`, `projects/hanwoo-dashboard/package.json`, `projects/hanwoo-dashboard/scripts/prisma7-runtime-test.mjs`, and `workspace/tests/test_auto_schedule_paths.py`. | User/AI | Medium | ?뵶 approval | 2026-05-07 |
| T-246 | `[workspace]` Review or finish remaining unrelated WIP: `projects/blind-to-x/scrapers/jobplanet.py`, `projects/hanwoo-dashboard/public/manifest.json`, `projects/shorts-maker-v2/src/shorts_maker_v2/render/karaoke.py`, and `projects/shorts-maker-v2/src/shorts_maker_v2/utils/channel_router.py`. | User/AI | Medium | 🔴 approval | 2026-05-07 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-247 | `[projects]` Project-by-project debug triage completed: full QC found only `shorts-maker-v2` Ruff `B007` in `render/karaoke.py`; fixed the unused `enumerate()` index and revalidated `shorts-maker-v2` test/lint plus graph/diff checks. | Codex | 2026-05-07 |
| T-245 | `[projects]` Surge queue and Hanwoo AI chat stabilized: `blind-to-x` queue persists `content_preview` with migration/tests, escalation runner passes previews into express drafts, Hanwoo chat streams `/api/ai/chat` with abort/offline fallback, and PWA config is opt-in so build stays green. | Codex | 2026-05-07 |
| T-244 | `[workspace]` Project verification docs aligned: project-level `CLAUDE.md` files and `.agents/workflows/start.md`/`verify.md` now reference canonical `execution/project_qc_runner.py` checks and current project stacks. | Codex | 2026-05-07 |
| T-243 | `[workspace]` Project-by-project QC runner added: deterministic `execution/project_qc_runner.py` now wraps canonical checks for `blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, and `knowledge-dashboard`, with unit tests and Windows command/UTF-8 handling. | Codex | 2026-05-07 |
| T-242 | `[workspace]` Full QC pass completed: graph risk `0.00`, `git diff --check` clean, shared health `overall: warn` with `fail: 0`, governance OK, branch protection configured, 0 open PRs, targeted secret scan clean, workspace Ruff/pytest passed, active project test/lint/build paths passed, and Playwright Chromium smoke passed. | Codex | 2026-05-07 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
