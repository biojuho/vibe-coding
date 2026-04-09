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

- `projects/hanwoo-dashboard` is still the main active deep-debug target outside the current Notion work.
- `projects/hanwoo-dashboard/src/lib/dashboard/pagination-guard.mjs` prevents repeated-cursor and runaway page-loop conditions in full-registry loaders and client pagination hooks.
- `projects/hanwoo-dashboard/src/app/subscription/success/page.js` and `src/components/payment/PaymentWidget.js` now safely parse malformed or non-JSON payment responses so checkout UI stays deterministic.
- `projects/hanwoo-dashboard/src/lib/hooks/useCattlePagination.js` and `src/lib/hooks/useSalesPagination.js` now abort on unmount, enforce a 15s client timeout, and avoid late state writes after disposal.
- `projects/hanwoo-dashboard/src/components/widgets/MarketPriceWidget.js` now swallows refresh failures after logging them so timer/button refreshes do not create unhandled promise rejections.
- `projects/blind-to-x/escalation_runner.py` now injects `TweetDraftGenerator` into `ExpressDraftPipeline`, and `pipeline/express_draft.py` can reuse the generator’s real provider chain instead of failing structurally when only `_enabled_providers()` / `_generate_once()` are available.
- `projects/blind-to-x/pipeline/daily_digest.py` now guards repeated Notion cursors/runaway page counts and enforces a summary-generation timeout with fallback if Gemini hangs.
- `projects/blind-to-x` Notion uploads are reviewer-first: new pages include `운영자 해석`, `검토 포인트`, `피드백 요청`, `근거 앵커`, `위험 신호`, `반려 사유`, and `발행 플랫폼`, plus a top-of-page `검토 브리프` section.
- `projects/blind-to-x/scripts/sync_notion_review_schema.py --config config.yaml --apply` was successfully run on 2026-04-09, so the reviewer-first columns exist in the live Notion DB.
- `projects/blind-to-x/scripts/backfill_notion_review_columns.py --config config.yaml --apply` was also successfully run on 2026-04-09, and a follow-up dry-run reported `candidates: 0`, so the historical Notion queue is backfilled too.
- `projects/blind-to-x/pipeline/feedback_loop.py` now emits reviewer-memory summaries from `반려 사유` and `위험 신호`, and `pipeline/draft_prompts.py` injects those summaries into future draft prompts as anti-pattern guidance.
- `projects/blind-to-x/pipeline/notion/_query.py#get_recent_pages()` now falls back to a database query when Notion search returns zero rows, which matters because the live DB can contain pages even when search does not surface them.
- `projects/blind-to-x` review docs and helper scripts now default to channel-neutral, manual publishing guidance rather than X-first wording.
- `projects/blind-to-x/pipeline/notion/_upload.py` now adds a reviewer-facing `지금 할 일` callout and rewrites `검토 포인트` / `피드백 요청` when no publishable draft exists, so empty draft cards are actionable.
- `projects/blind-to-x/pipeline/regulation_checker.py` now phrases missing-draft warnings as “regulation check skipped because no draft exists,” which avoids implying a policy violation when generation failed or returned nothing.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` reports degraded-step state via `manifest.degraded_steps` and `status="degraded"`.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` now passes `google_client` into `ThumbnailStep`, and `pipeline/thumbnail_step.py` now prefers the Imagen3-capable path for Gemini thumbnails.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/qc_step.py` now holds Gate 4 when `ffprobe` / `ffmpeg` inspection is unavailable instead of falsely passing on partial checks.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py` now skips parallel paid-visual generation until audio succeeds, reducing wasted spend when paid scenes fail early.

## Recent Verification

- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_query_mixin.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_backfill_notion_review_columns.py tests/unit/test_notion_upload.py -q` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_upload.py tests/unit/test_regulation_checker.py -q` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m ruff check pipeline/notion/_query.py pipeline/feedback_loop.py pipeline/draft_prompts.py scripts/backfill_notion_review_columns.py scripts/check_notion_views.py docs/operations_sop.md tests/unit/test_notion_query_mixin.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_backfill_notion_review_columns.py` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m ruff check pipeline/notion/_upload.py pipeline/regulation_checker.py tests/unit/test_notion_upload.py tests/unit/test_regulation_checker.py` passed on 2026-04-09.
- `projects/blind-to-x`: `py -3 scripts/check_notion_views.py` passed on 2026-04-09.
- `projects/blind-to-x`: `py -3 scripts/backfill_notion_review_columns.py --config config.yaml --apply` succeeded on 2026-04-09, and a second dry-run reported `candidates: 0`.
- Earlier on 2026-04-09: `py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply`, `python -m pytest --no-cov tests/unit/test_notion_upload.py -q`, `python -m pytest --no-cov tests/unit/test_process_stages.py -q`, and focused Ruff checks also passed in `projects/blind-to-x`.
- `projects/shorts-maker-v2`: targeted pytest and `python -m ruff check .` passed on 2026-04-09.
- `projects/hanwoo-dashboard`: `npm test` and `npm run lint` passed on 2026-04-09.

## Minefield

- The worktree is dirty across multiple projects. Do not revert unrelated edits.
- `projects/hanwoo-dashboard` still has many user-facing Korean strings; keep edits surgical to avoid encoding churn.
- For `hanwoo-dashboard` Node-side unit tests, prefer `.mjs` helper/test files. The repo still does not set package-wide `"type": "module"`.
- `projects/blind-to-x` and `projects/shorts-maker-v2` enforce broad coverage defaults; use `python -m pytest --no-cov ...` for focused local verification unless a full coverage run is intended.
- `projects/blind-to-x` can return empty database properties through `notion-client` on Windows/Python 3.14; the uploader now relies on an `httpx` fallback to recover schema, and the review-schema/backfill scripts use direct REST-backed paths.
- Windows `cp949` consoles can still garble Korean in command output even when the underlying files and Notion payloads are UTF-8 clean.
- `[ADR-026]` Project-level `CLAUDE.md` files now exist for `blind-to-x`, `hanwoo-dashboard`, and `shorts-maker-v2`. Read the relevant project’s minefield section before editing.
- `[ADR-026]` `/verify` workflow is explicit: do not claim completion without running the appropriate checks.
- `[Explore -> Plan -> Code -> Verify]` All implementation work follows the 4-step workflow. Never patch blindly without prior inspection.
