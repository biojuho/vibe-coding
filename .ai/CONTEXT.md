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
- `projects/hanwoo-dashboard/src/lib/dashboard/pagination-guard.mjs` prevents repeated-cursor and runaway page-loop conditions in full-registry loaders and client pagination hooks.
- `projects/hanwoo-dashboard/src/app/subscription/success/page.js` and `src/components/payment/PaymentWidget.js` now safely parse malformed/non-JSON payment responses so checkout UI stays deterministic.
- `projects/hanwoo-dashboard/src/lib/hooks/useCattlePagination.js` and `src/lib/hooks/useSalesPagination.js` now abort on unmount, enforce a 15s client timeout, and avoid late state writes after disposal.
- `projects/hanwoo-dashboard/src/components/widgets/MarketPriceWidget.js` now swallows refresh failures after logging them so timer/button refreshes do not create unhandled promise rejections.
- `projects/hanwoo-dashboard/src/lib/actions.js#getNotifications()` uses shared `buildNotifications(cattle)` and stable target-date timing from `src/lib/notification-timing.mjs`.
- `projects/hanwoo-dashboard/src/lib/syncManager.js` caps offline queue retries and moves poison items to the `localStorage` key `joolife-offline-dead-letter`.
- `projects/blind-to-x/escalation_runner.py` now injects `TweetDraftGenerator` into `ExpressDraftPipeline`, and `pipeline/express_draft.py` can reuse the generator's real provider chain instead of failing structurally when only `_enabled_providers()` / `_generate_once()` are available.
- `projects/blind-to-x/pipeline/daily_digest.py` now guards repeated Notion cursors/runaway page counts and enforces a summary-generation timeout with fallback if Gemini hangs.
- `projects/blind-to-x/escalation_runner.py` also applies polling breaker/backoff logic for extended external outages.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` reports degraded-step state via `manifest.degraded_steps` and `status="degraded"`.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` now passes `google_client` into `ThumbnailStep`, and `pipeline/thumbnail_step.py` now prefers the Imagen3-capable path for Gemini thumbnails.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/qc_step.py` now holds Gate 4 when `ffprobe` / `ffmpeg` inspection is unavailable instead of falsely passing on partial checks.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py` now skips parallel paid-visual generation until audio succeeds, reducing wasted spend when paid scenes fail early.

## Recent Verification

- `python -m pytest --no-cov tests/unit/test_express_draft.py tests/unit/test_daily_digest_extended.py tests/unit/test_escalation_runner.py -x` and `python -m ruff check .` passed in `projects/blind-to-x` on 2026-04-09.
- `python -m pytest --no-cov tests/unit/test_qc_step.py tests/unit/test_thumbnail_step.py tests/unit/test_media_step_branches.py tests/unit/test_orchestrator_unit.py -x` passed in `projects/shorts-maker-v2` on 2026-04-09, and `python -m ruff check ...` passed for the changed files.
- `npm test` (`48 passed`) and `npm run lint` passed in `projects/hanwoo-dashboard` on 2026-04-09.
- Earlier on 2026-04-08: `npm run lint`, `npm test`, and `npm run build` passed in `projects/hanwoo-dashboard` after `T-163`.

## Minefield

- The worktree is dirty across multiple projects. Do not revert unrelated edits.
- `projects/hanwoo-dashboard` still has many user-facing Korean strings; keep edits surgical to avoid encoding churn.
- For `hanwoo-dashboard` Node-side unit tests, prefer `.mjs` helper/test files. The repo still does not set package-wide `"type": "module"`.
- `projects/blind-to-x` and `projects/shorts-maker-v2` enforce broad coverage defaults; use `python -m pytest --no-cov ...` for focused local verification unless a full coverage run is intended.
- `projects/shorts-maker-v2` still has pre-existing repo-wide Ruff debt outside the current patch set (`archive/tests_legacy_v1/*` plus a few import-order hotspots). Changed-file Ruff checks are currently the reliable verification path.
- Windows `cp949` consoles can choke on `thumbnail_step.py` `print()` paths if they contain typographic punctuation; keep those strings ASCII-safe.
- `[ADR-026]` Project-level `CLAUDE.md` files now exist for `blind-to-x`, `hanwoo-dashboard`, and `shorts-maker-v2`. Read the relevant project's minefield section before editing.
- `[ADR-026]` `/verify` workflow is now explicit: do not claim completion without running the appropriate checks.
- `[Explore -> Plan -> Code -> Verify]` All implementation work follows the 4-step workflow. Never patch blindly without prior inspection.
