# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-18 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed, but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-305 | `[blind-to-x]` Migrate openai 1.59 → 2.x. PR #39 was closed because the bump is too risky for automation: although `pipeline/draft_providers.py` and `pipeline/image_generator.py` already use the v1+ `AsyncOpenAI` + `client.chat.completions.create` pattern, v2 has breaking changes (Python 3.7 drop, module-level globals removed, deprecated method removal, response shape tweaks) and 4 test fixtures will need mock refreshes. Plan: pin openai>=2.x in `pyproject.toml`, refresh mocks in `tests/unit/test_multi_platform.py`, `test_scrapers.py`, `test_env_runtime_fallbacks.py`, `test_image_generator.py`, run targeted pytest slice, then live smoke against the LLM fallback chain. Verify Anthropic prompt cache + workspace usage forwarder (`cost_tracker.py`) still flush. Budget ~½–1 day. | Any | Low | approval | 2026-05-18 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-313 | `[hanwoo-dashboard]` Quick Action Panel 도입. 개체 등록, 출하 기록, 일정 추가, 재고 입력 퀵액션 버튼 구현 + 탭 연동(`quickActionIntent`). DashboardClient, SalesTab, ScheduleTab, InventoryTab 수정. Verification: `npm test` 77 passed, lint & build OK. 커밋 `e0c80d1`. | Gemini | 2026-05-19 |
| T-312 | `[shorts-maker-v2]` 품질 고도화: scene QC 활성화(strict 모드), 영상 길이 완화(`[38,52]`초), 한국어 훅 품질 가이드라인 조건부 적용(`hook_rules_ko`), 감정 키워드 5도메인 확장(우주/심리/역사/건강/AI). Verification: pytest 전체 통과, i18n 테스트 포함. 커밋 `f119b30`. | Gemini | 2026-05-19 |
| T-311 | `[hanwoo-dashboard]` Second UX/UI optimization pass for the active quality goal. Reworked `/login` into an operator-first flow with labelled username/password fields, lucide icons, password visibility toggle, disabled/pending submit states, clearer error feedback, mobile-safe layout, status chips, and favicon fallback. Replaced bottom tab emoji navigation with lucide icons and `aria-current` for steadier cross-platform scanning. Verification: Hanwoo `npm.cmd test` `77 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, Playwright CLI `/login` mobile/desktop visual checks passed, console errors `0`. Commit `94d043e`. | Codex | 2026-05-19 |
| T-310 | `[blind-to-x]` Made Notion review output more suitable for direct X upload. `pipeline/notion/_upload.py` now labels Twitter drafts as `X`, adds a top-level `X 업로드 카드` with copy-ready `X 본문`, optional `첫 답글 / 출처 메모`, 280-character count, link/hashtag separation guidance, and upload order. Updated backfill/schema helpers. Verification: Notion/backfill focused tests `42 passed`; Ruff passed; risk `0.00`. | Codex | 2026-05-19 |
| T-309 | `[blind-to-x]` Quality gate fail 원인 진단 + 5계층 동시 정비 — require_cta False, system_role "조용한 해설자", 1안만 출력, cliche_watchlist 13개 추가, golden_examples 재작성. 검증: pytest 1560 passed, dry-run Quality Score 0→85. 커밋 `4628bb8`. | Claude Code | 2026-05-19 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
