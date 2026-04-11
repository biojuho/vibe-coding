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
- `projects/blind-to-x/escalation_runner.py` now injects `TweetDraftGenerator` into `ExpressDraftPipeline`, and `pipeline/express_draft.py` can reuse the generator's real provider chain instead of failing structurally when only `_enabled_providers()` / `_generate_once()` are available.
- `projects/blind-to-x/pipeline/daily_digest.py` now guards repeated Notion cursors/runaway page counts and enforces a summary-generation timeout with fallback if Gemini hangs.
- `projects/blind-to-x/tests/unit/conftest.py` now clears `NOTION_DATABASE_ID` and any `NOTION_PROP_*` env overrides before each test, preventing `.env`-loaded Notion values from leaking into `NotionUploader` unit expectations.
- `projects/blind-to-x/pipeline/notion/_query.py` now resolves logical status names like `승인됨` against the live Notion select options (for the current DB, `발행승인`) and canonicalizes the returned status values back to the shared logical labels so feedback/reprocess flows stay stable across schema wording changes.
- `projects/blind-to-x/tests/unit/test_process.py` is back to a clean local test-helper state after the timeout-targeting edits; the unused `asyncio` import was removed and the focused process tests plus Ruff now pass together.
- The local Python 3.13 `code-review-graph` package on this machine is patched for UTF-8-safe `.gitignore` writes/reads plus UTF-8 git subprocess decoding. This fixed the Windows `cp949` crash in `detect-changes`, but it is a local site-packages edit, not a repo-tracked source change.
- `projects/blind-to-x` Notion uploads are reviewer-first: new pages include operator-review columns and a top-of-page review brief section.
- `projects/blind-to-x/scripts/sync_notion_review_schema.py --config config.yaml --apply` was successfully run on 2026-04-09, so the reviewer-first columns exist in the live Notion DB.
- `projects/blind-to-x/scripts/backfill_notion_review_columns.py --config config.yaml --apply` was also successfully run on 2026-04-09, and a follow-up dry-run reported `candidates: 0`, so the historical Notion queue is backfilled too.
- `projects/blind-to-x/pipeline/feedback_loop.py` now emits reviewer-memory summaries from rejection and risk metadata, and `pipeline/draft_prompts.py` injects those summaries into future draft prompts as anti-pattern guidance.
- `projects/blind-to-x/pipeline/notion/_query.py#get_recent_pages()` now falls back to a database query when Notion search returns zero rows, which matters because the live DB can contain pages even when search does not surface them.
- `projects/blind-to-x` review docs and helper scripts now default to channel-neutral, manual publishing guidance rather than X-first wording.
- `projects/blind-to-x/pipeline/notion/_upload.py` now adds a reviewer-facing `지금 할 일` callout and rewrites review copy when no publishable draft exists, so empty draft cards are actionable.
- `projects/blind-to-x/pipeline/regulation_checker.py` now phrases missing-draft warnings as "regulation check skipped because no draft exists," which avoids implying a policy violation when generation failed or returned nothing.
- `projects/blind-to-x` review-only runs now enforce a daily Notion queue floor of 5 cards. While today's count is below target, `pipeline/daily_queue_floor.py` relaxes candidate collection thresholds plus low-quality, viral, and calendar skips, but still keeps spam and length guards intact.
- `projects/blind-to-x/pipeline/process_stages/generate_review_stage.py` now treats draft-generation failure as a soft failure in `review_only` mode, so Notion review cards are still uploaded even if LLM output is invalid or missing required tags.
- `projects/blind-to-x/pipeline/notion/_upload.py` now surfaces `draft_generation_error` in the reviewer memo, and `pipeline/process_stages/generate_review_stage.py` disables review-only quality-gate regeneration retries to avoid repeated 180s timeouts while backfilling the queue.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` reports degraded-step state via `manifest.degraded_steps` and `status="degraded"`.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` now passes `google_client` into `ThumbnailStep`, and `pipeline/thumbnail_step.py` now prefers the Imagen3-capable path for Gemini thumbnails.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/qc_step.py` now holds Gate 4 when `ffprobe` / `ffmpeg` inspection is unavailable instead of falsely passing on partial checks.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py` now skips parallel paid-visual generation until audio succeeds, reducing wasted spend when paid scenes fail early.

## Recent Verification

- `workspace`: `python workspace/execution/health_check.py --category governance --json` passed on 2026-04-11 after `workspace/directives/INDEX.md` was updated with the missing harness scripts and `workspace/directives/system_audit_action_plan.md` closed the archived `T-100` checkbox.
- `workspace`: `python -m pytest --no-cov workspace/tests/test_health_check.py -q` and `python -m ruff check workspace/execution/health_check.py workspace/tests/test_health_check.py` both passed on 2026-04-11 after Moonshot optional-provider handling was added.
- `workspace`: `python workspace/execution/health_check.py --json` reports overall `warn` on 2026-04-11 with `fail: 0`; Moonshot is now treated as an optional fallback provider, and the latest probe saw `MOONSHOT_API_KEY` unset rather than invalid.
- `workspace`: `python3.13 -m code_review_graph status` ran on 2026-04-11 and reported `11095` nodes, `81218` edges, `819` files, and last graph update `2026-04-09T16:00:25` on commit `780b638fa8d2`.
- `workspace`: `python3.13 -m code_review_graph detect-changes --repo projects/blind-to-x --brief` passed on 2026-04-11 after the local package was patched to force UTF-8 for file I/O and git subprocess decoding on Windows.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_query_mixin.py -q` and `python -m ruff check pipeline/notion/_query.py tests/unit/test_notion_query_mixin.py` both passed on 2026-04-11 after logical-status alias handling was added to `_query.py`.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_process.py -q` and `python -m ruff check tests/unit/test_process.py tests/unit/conftest.py tests/unit/test_notion_query_mixin.py` both passed on 2026-04-11 after the lingering `test_process.py` lint cleanup.
- `projects/blind-to-x`: a live read-only probe on 2026-04-11 confirmed the current DB still rejects `select.equals="승인됨"` with HTTP 400, accepts `select.equals="발행승인"`, and now returns approved pages correctly through `get_pages_by_status("승인됨")`.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/ -q` passed on 2026-04-11 (`1484 passed, 1 skipped`) after the `_query.py` status alias fix.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/ -q` passed on 2026-04-11 (`1481 passed, 1 skipped`) after the unit-test env-isolation fixture was extended to clear `NOTION_DATABASE_ID` and `NOTION_PROP_*`.
- `projects/blind-to-x`: `python -m ruff check tests/unit/conftest.py` passed on 2026-04-11.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_query_mixin.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_backfill_notion_review_columns.py tests/unit/test_notion_upload.py -q` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_upload.py tests/unit/test_regulation_checker.py -q` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_feed_collector.py tests/unit/test_process_stages.py -q` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m ruff check pipeline/notion/_query.py pipeline/feedback_loop.py pipeline/draft_prompts.py scripts/backfill_notion_review_columns.py scripts/check_notion_views.py docs/operations_sop.md tests/unit/test_notion_query_mixin.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_backfill_notion_review_columns.py` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m ruff check pipeline/notion/_upload.py pipeline/regulation_checker.py tests/unit/test_notion_upload.py tests/unit/test_regulation_checker.py` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m ruff check main.py pipeline/daily_queue_floor.py pipeline/feed_collector.py pipeline/process.py pipeline/process_stages/filter_profile_stage.py tests/unit/test_feed_collector.py tests/unit/test_process_stages.py` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m ruff check pipeline/draft_generator.py pipeline/process.py pipeline/process_stages/generate_review_stage.py pipeline/notion/_upload.py tests/unit/test_process_stages.py tests/unit/test_pipeline_flow.py tests/unit/test_notion_upload.py` passed on 2026-04-09.
- `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_process_stages.py -q -x`, `python -m pytest --no-cov tests/unit/test_pipeline_flow.py::test_process_single_post_generation_failure_review_only_uploads_card tests/unit/test_pipeline_flow.py::test_process_single_post_generation_failure_non_review_stops_before_upload -q -x`, and `python -m pytest --no-cov tests/unit/test_notion_upload.py -q -x` passed on 2026-04-09.
- `projects/blind-to-x`: `py -3 scripts/check_notion_views.py` passed on 2026-04-09.
- `projects/blind-to-x`: `py -3 scripts/backfill_notion_review_columns.py --config config.yaml --apply` succeeded on 2026-04-09, and a second dry-run reported `candidates: 0`.
- `projects/blind-to-x`: live floor probe on 2026-04-09 returned `DailyQueueFloorState(target=5, current=0, remaining=5, active=True)`.
- `projects/blind-to-x`: two live `python main.py --source blind --popular --review-only ...` runs on 2026-04-09 recovered the live Notion queue from 0 to 5 same-day cards; the fifth card landed by 19:39 KST.
- Earlier on 2026-04-09: `py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply`, `python -m pytest --no-cov tests/unit/test_notion_upload.py -q`, `python -m pytest --no-cov tests/unit/test_process_stages.py -q`, and focused Ruff checks also passed in `projects/blind-to-x`.
- `projects/shorts-maker-v2`: targeted pytest and `python -m ruff check .` passed on 2026-04-09.
- `projects/hanwoo-dashboard`: `npm test` and `npm run lint` passed on 2026-04-09.

## Minefield

- The worktree is dirty across multiple projects. Do not revert unrelated edits.
- Bare `pytest` is not on `PATH` in the current root shell unless the venv is activated; prefer `python -m pytest`.
- `projects/hanwoo-dashboard` still has many user-facing Korean strings; keep edits surgical to avoid encoding churn.
- For `hanwoo-dashboard` Node-side unit tests, prefer `.mjs` helper/test files. The repo still does not set package-wide `"type": "module"`.
- `projects/blind-to-x` and `projects/shorts-maker-v2` enforce broad coverage defaults; use `python -m pytest --no-cov ...` for focused local verification unless a full coverage run is intended.
- `projects/blind-to-x` can return empty database properties through `notion-client` on Windows/Python 3.14; the uploader now relies on an `httpx` fallback to recover schema, and the review-schema/backfill scripts use direct REST-backed paths.
- The `code-review-graph` Windows `cp949` crash is fixed locally in site-packages, but that patch is not repo-tracked; reinstalling the package can silently reintroduce it.
- Windows `cp949` consoles can still garble Korean in command output even when the underlying files and Notion payloads are UTF-8 clean.
- Windows PowerShell `Get-Content` output can make UTF-8 markdown in `.ai/` and `workspace/directives/` look corrupted; confirm with Python/UTF-8-aware readers before treating it as file damage.
- Moonshot is now treated as an optional fallback provider in shared health checks; if `MOONSHOT_API_KEY` is missing or invalid, the system should degrade to `warn` rather than `fail`.
- `[ADR-026]` Project-level `CLAUDE.md` files now exist for `blind-to-x`, `hanwoo-dashboard`, and `shorts-maker-v2`. Read the relevant project's minefield section before editing.
- `[ADR-026]` `/verify` workflow is explicit: do not claim completion without running the appropriate checks.
- `[Explore -> Plan -> Code -> Verify]` All implementation work follows the 4-step workflow. Never patch blindly without prior inspection.
