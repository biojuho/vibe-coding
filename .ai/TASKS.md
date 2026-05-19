# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-18 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed, but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-305 | `[blind-to-x]` Migrate openai 1.59 ??2.x. PR #39 was closed because the bump is too risky for automation: although `pipeline/draft_providers.py` and `pipeline/image_generator.py` already use the v1+ `AsyncOpenAI` + `client.chat.completions.create` pattern, v2 has breaking changes (Python 3.7 drop, module-level globals removed, deprecated method removal, response shape tweaks) and 4 test fixtures will need mock refreshes. Plan: pin openai>=2.x in `pyproject.toml`, refresh mocks in `tests/unit/test_multi_platform.py`, `test_scrapers.py`, `test_env_runtime_fallbacks.py`, `test_image_generator.py`, run targeted pytest slice, then live smoke against the LLM fallback chain. Verify Anthropic prompt cache + workspace usage forwarder (`cost_tracker.py`) still flush. Budget ~쩍?? day. | Any | Low | approval | 2026-05-18 |
| T-318 | `[shorts-maker-v2]` Phase 3 품질 개선 후보. (a) gate3_media_qc duration 채널 target 너무 엄격(채널 35→ effective [35,35], 49.8s 오디오와 충돌) → target ±10초 마진 추가 또는 채널별 max_duration 설정. (b) scene_qc 디폴트 OFF인데 ai_tech run에서 자동 8/8 통과한 패턴 분석 → 명시적 ON이 안전한지 확인. (c) hook_score<0.6 시 재생성 강제 게이트 (현재는 score 산출만 하고 통과). (d) 채널별 TTS 속도/voice role 미세조정. Phase 1+2 검증 run 결과(`runs/20260519-014816-a37f7826`) 확인 후 우선순위 재조정. | Any | Medium | safe | 2026-05-19 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-319 | `[hanwoo-dashboard]` Added action-oriented empty states for the operational Sales, Schedule, and Inventory tabs. Introduced a shared `EmptyState` component with lucide icon support and a CTA button, then replaced passive "no data" messages with direct actions (`매출 기록`, `일정 추가`, `재고 등록`) so first-run/empty-account flows guide the operator into the next useful step. Added a lightweight source wiring test for the component and tab integrations. Verification: Hanwoo `npm.cmd test` `79 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, code-review graph risk `0.00`, and dev server `/login` returned `200`. | Codex | 2026-05-19 |
| T-317 | `[shorts-maker-v2]` Phase 1+2 YouTube-ready 품질 개선 (commit `2b09759`). 2회 실험 run으로 8개 갭 식별 후 6개 해소: (Phase 1) hook hard cap 15→40자 + 단어 경계 트림 / Gate 2 audience-desire 매칭에 한국어 조사 stem + core_message + visual_keywords 다중 신호 / 4개 image entry-point (DALL-E·Pollinations·Imagen3·Gemini)에 "No text/letters" negative 자동 부착(중복 방지); (Phase 2) TTS provider openai→edge-tts 전환 — 모든 채널 Azure-voice 호환 + 무료 + _words.json 자동 생성으로 카라오케 자막 자동 복구 / 5개 채널 topic 50개 사실 기반 재설계 / `_pending_audio_warnings` + `_pending_render_warnings` 버퍼 도입해 Whisper/karaoke/color/audio post silent-fail이 manifest.degraded_steps로 drain. 검증: 1447 unit tests pass(+20 신규), ruff clean, validation run에서 Gate 2 FAIL 0회·kc_*.png 25개·caption_fallback 0개·이미지 영어 텍스트 artifact 없음 확인. 새 갭 발견: gate3_media_qc duration 채널 target (35±0) 너무 엄격(49.8s 오디오와 충돌) → T-318. | Claude Code (Opus 4.7 1M) | 2026-05-19 |
| T-316 | `[blind-to-x]` GitHub-inspired Notion publishing ops uplift. Researched comparable GitHub/social workflows (`langchain-ai/social-media-agent` human-in-the-loop publishing and NotionToTwitter's Notion-based post date/status/error/URL tracking), then added X publishing operations metadata to the blind-to-x Notion flow: `X Publish Status`, `X Scheduled At`, `X Published At`, `X Post URL`, and `X Publish Error`. Future X-ready uploads default to `Ready to Post` and show a `게시 운영` checklist in the `X 업로드 카드`; schema sync can create/merge the select/date/url/rich_text properties. Applied the live Notion schema update, backfilled the latest 5 pages to `Ready to Post`, then verified schema NOOP and backfill candidates 0. Verification: Notion upload/backfill tests `44 passed`, targeted Ruff passed, graph risk `0.00`. | Codex | 2026-05-19 |
| T-315 | `[blind-to-x]` Live Notion X-ready backfill for the active thread goal. Verified Notion connection (`notion_doctor.py` PASS) and schema (`sync_notion_review_schema.py --config config.yaml` NOOP, 43 properties, `X` option already present). Added `--append-x-upload-card` to `scripts/backfill_notion_review_columns.py` so existing pages with `tweet_body` but no `X 업로드 카드` can be upgraded without LLM/API generation. Applied it to the newest 5 Notion pages: dry-run found `x_card_candidates: 5`, apply updated 5 pages and appended 5 cards. Read-only verification confirmed `verified_x_ready=5/5` with `platforms=['X']`, `has_x_card=True`, `has_x_body=True`, `has_reply=True`. Verification: Notion/backfill unit slice `44 passed`, targeted Ruff passed, graph risk `0.00`. | Codex | 2026-05-19 |
| T-314 | `[hanwoo-dashboard]` Fixed login-time PWA asset routing so `/manifest.json`, app icons, `sw.js`, and Workbox assets bypass the auth proxy. This removes the browser manifest JSON parse error seen on `/login` and keeps install/app metadata available before authentication. Verification: `npm.cmd test` `77 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, and `Invoke-WebRequest http://127.0.0.1:3001/manifest.json` returned `200 application/json`. | Codex | 2026-05-19 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
