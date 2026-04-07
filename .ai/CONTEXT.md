# Vibe Coding Context

> Local-only multi-project workspace. Do not push, pull, or deploy unless the user explicitly asks.

## Workspace Summary

- Root runtime: Python `venv`, `pytest`, `ruff`, root `.env`
- Canonical path contract:
  - `workspace/...` for shared automation and docs
  - `projects/<name>/...` for product repos
  - `infrastructure/...` for services and MCP helpers

## Active Projects

| Project | Status | Stack | Canonical Path |
|---|---|---|---|
| `blind-to-x` | Active | Python pipeline, Notion, Cloudinary | `projects/blind-to-x` |
| `shorts-maker-v2` | Active | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | `projects/shorts-maker-v2` |
| `hanwoo-dashboard` | Active | Next.js, React, Prisma, Tailwind | `projects/hanwoo-dashboard` |
| `knowledge-dashboard` | Maintenance | Next.js, TypeScript, Tailwind | `projects/knowledge-dashboard` |
| `suika-game-v2` | Frozen | Vite, Vanilla JS, Matter.js | `projects/suika-game-v2` |
| `word-chain` | Frozen | React, Vite, Tailwind | `projects/word-chain` |

## Current Reliability Notes

- `projects/hanwoo-dashboard` is the main active deep-debug target.
- `DashboardClient` now reads cattle/sales through paginated dashboard APIs; full registries are loaded only on demand.
- `projects/hanwoo-dashboard/src/lib/actions.js#getNotifications()` now uses shared `buildNotifications(cattle)` and stable target-date timing from `src/lib/notification-timing.mjs`.
- `projects/hanwoo-dashboard/src/lib/syncManager.js` now caps offline queue retries and moves poison items to the `localStorage` key `joolife-offline-dead-letter`.
- `projects/hanwoo-dashboard/src/lib/offlineQueue.js` now persists retry metadata (`retryCount`, `lastAttemptAt`, `lastError`, `deadLetteredAt`) for offline mutations.
- `projects/knowledge-dashboard/src/app/page.tsx` now routes session POST/DELETE calls through a shared 10s timeout helper and only clears UI state after successful session deletion.
- `projects/blind-to-x/pipeline/daily_digest.py` now guards repeated Notion cursors and runaway page counts.
- `projects/blind-to-x/escalation_runner.py` now applies polling breaker/backoff logic for extended external outages.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` now reports degraded-step state via `manifest.degraded_steps` and `status="degraded"`.

## Recent Verification

- `npm run lint`, `npm test` (`43 passed`), and `npm run build` in `projects/hanwoo-dashboard` all passed on 2026-04-07 after `T-162`.
- Earlier on 2026-04-07: `npm run lint` in `projects/knowledge-dashboard`, `pytest --no-cov tests/unit/test_daily_digest_extended.py` in `projects/blind-to-x`, and `pytest --no-cov tests/unit/test_cli.py tests/unit/test_orchestrator_unit.py` in `projects/shorts-maker-v2` all passed.

## Minefield

- The worktree is dirty across multiple projects. Do not revert unrelated edits.
- `projects/hanwoo-dashboard` still has many user-facing Korean strings; keep edits surgical to avoid encoding churn.
- For `hanwoo-dashboard` Node-side unit tests, prefer `.mjs` helper/test files. The repo still does not set package-wide `"type": "module"`.
- `projects/blind-to-x` and `projects/shorts-maker-v2` enforce broad coverage defaults; use `python -m pytest --no-cov ...` for focused local verification unless a full coverage run is intended.
