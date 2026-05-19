# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-18 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed, but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-305 | `[blind-to-x]` Migrate openai 1.59 ??2.x. PR #39 was closed because the bump is too risky for automation: although `pipeline/draft_providers.py` and `pipeline/image_generator.py` already use the v1+ `AsyncOpenAI` + `client.chat.completions.create` pattern, v2 has breaking changes (Python 3.7 drop, module-level globals removed, deprecated method removal, response shape tweaks) and 4 test fixtures will need mock refreshes. Plan: pin openai>=2.x in `pyproject.toml`, refresh mocks in `tests/unit/test_multi_platform.py`, `test_scrapers.py`, `test_env_runtime_fallbacks.py`, `test_image_generator.py`, run targeted pytest slice, then live smoke against the LLM fallback chain. Verify Anthropic prompt cache + workspace usage forwarder (`cost_tracker.py`) still flush. Budget ~쩍?? day. | Any | Low | approval | 2026-05-18 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-316 | `[blind-to-x]` GitHub-inspired Notion publishing ops uplift. Researched comparable GitHub/social workflows (`langchain-ai/social-media-agent` human-in-the-loop publishing and NotionToTwitter's Notion-based post date/status/error/URL tracking), then added X publishing operations metadata to the blind-to-x Notion flow: `X Publish Status`, `X Scheduled At`, `X Published At`, `X Post URL`, and `X Publish Error`. Future X-ready uploads default to `Ready to Post` and show a `게시 운영` checklist in the `X 업로드 카드`; schema sync can create/merge the select/date/url/rich_text properties. Applied the live Notion schema update, backfilled the latest 5 pages to `Ready to Post`, then verified schema NOOP and backfill candidates 0. Verification: Notion upload/backfill tests `44 passed`, targeted Ruff passed, graph risk `0.00`. | Codex | 2026-05-19 |
| T-315 | `[blind-to-x]` Live Notion X-ready backfill for the active thread goal. Verified Notion connection (`notion_doctor.py` PASS) and schema (`sync_notion_review_schema.py --config config.yaml` NOOP, 43 properties, `X` option already present). Added `--append-x-upload-card` to `scripts/backfill_notion_review_columns.py` so existing pages with `tweet_body` but no `X 업로드 카드` can be upgraded without LLM/API generation. Applied it to the newest 5 Notion pages: dry-run found `x_card_candidates: 5`, apply updated 5 pages and appended 5 cards. Read-only verification confirmed `verified_x_ready=5/5` with `platforms=['X']`, `has_x_card=True`, `has_x_body=True`, `has_reply=True`. Verification: Notion/backfill unit slice `44 passed`, targeted Ruff passed, graph risk `0.00`. | Codex | 2026-05-19 |
| T-314 | `[hanwoo-dashboard]` Fixed login-time PWA asset routing so `/manifest.json`, app icons, `sw.js`, and Workbox assets bypass the auth proxy. This removes the browser manifest JSON parse error seen on `/login` and keeps install/app metadata available before authentication. Verification: `npm.cmd test` `77 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, and `Invoke-WebRequest http://127.0.0.1:3001/manifest.json` returned `200 application/json`. | Codex | 2026-05-19 |
| T-313 | `[hanwoo-dashboard]` Quick Action Panel ?꾩엯. 媛쒖껜 ?깅줉, 異쒗븯 湲곕줉, ?쇱젙 異붽?, ?ш퀬 ?낅젰 ?듭븸??踰꾪듉 援ы쁽 + ???곕룞(`quickActionIntent`). DashboardClient, SalesTab, ScheduleTab, InventoryTab ?섏젙. Verification: `npm test` 77 passed, lint & build OK. 而ㅻ컠 `e0c80d1`. | Gemini | 2026-05-19 |
| T-312 | `[shorts-maker-v2]` ?덉쭏 怨좊룄?? scene QC ?쒖꽦??strict 紐⑤뱶), ?곸긽 湲몄씠 ?꾪솕(`[38,52]`珥?, ?쒓뎅?????덉쭏 媛?대뱶?쇱씤 議곌굔遺 ?곸슜(`hook_rules_ko`), 媛먯젙 ?ㅼ썙??5?꾨찓???뺤옣(?곗＜/?щ━/??궗/嫄닿컯/AI). Verification: pytest ?꾩껜 ?듦낵, i18n ?뚯뒪???ы븿. 而ㅻ컠 `f119b30`. | Gemini | 2026-05-19 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
