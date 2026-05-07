# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-246 | `[workspace]` Review or finish remaining unrelated WIP: `projects/blind-to-x/scrapers/jobplanet.py`, `projects/hanwoo-dashboard/public/manifest.json`, `projects/shorts-maker-v2/src/shorts_maker_v2/render/karaoke.py`, and `projects/shorts-maker-v2/src/shorts_maker_v2/utils/channel_router.py`. | User/AI | Medium | 🔴 approval | 2026-05-07 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-249 | `[workspace]` Reflected requested stack policy: current defaults are React/Next.js, JS/TS, PostgreSQL/Supabase-compatible Prisma access, Redis/BullMQ, and Fetch API wrappers; Svelte, Go, Rust, Flutter/native, RabbitMQ, and TanStack Query are candidate-only until a design note exists. | Codex | 2026-05-08 |
| T-120 | `[infrastructure/n8n]` Made `psutil` optional in `bridge_server.py` (real CI blocker — fastapi/pydantic already had fallbacks); extended `test_auto_schedule_paths.py` regression to block fastapi+pydantic+psutil together; wired the test file into `root-quality-gate.yml` and `full-test-matrix.yml`. | Claude Code (Opus 4.7 1M) | 2026-05-07 |
| T-121 | `[blind-to-x]` Confirmed `test_main.py` KeyboardInterrupt already mitigated by `_isolate_logging_handlers` autouse fixture in `tests/unit/conftest.py`; full unit suite (1523 passed, 12 skipped) and 3 back-to-back targeted runs (20/20 each) all clean. Memory entry was stale. | Claude Code (Opus 4.7 1M) | 2026-05-07 |
| T-129 | `[hanwoo-dashboard]` Wired the read-model cache `meta` (source/isStale/ageSeconds) from `/api/dashboard/summary` through to a new `summaryMeta` state in `DashboardClient`. Deeper DashboardClient split previously deemed risk>benefit (T-210). | Claude Code (Opus 4.7 1M) | 2026-05-07 |
| T-247 | `[projects]` Project-by-project debug triage completed: full QC found only `shorts-maker-v2` Ruff `B007` in `render/karaoke.py`; fixed the unused `enumerate()` index and revalidated `shorts-maker-v2` test/lint plus graph/diff checks. | Codex | 2026-05-07 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
