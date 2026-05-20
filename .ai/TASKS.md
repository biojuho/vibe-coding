# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-20 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed (`15 passed`) but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-320 | `[shorts-maker-v2]` 외부 OSS 도입(2026-05-19 리서치 완료, 메모리 `shorts_v2_oss_shortlist_20260519`). 사용자 환경 Intel Iris Xe iGPU(NVIDIA 없음) + RAM 15.75GB 확인. **로컬 적용 가능**: (1) WhisperX (BSD-2, `pip install whisperx`, CPU int8+medium, T-19 backlog 직접 해결, `pipeline/media/audio_mixin.py`의 OpenAI Whisper transcribe_audio() drop-in 교체) (2) OpenVoice v2 (MIT, 한국어 native, voice cloning, fallback chain `edge-tts → openvoice → openai`). **클라우드 GPU 필요**: (3) LTX-Video (Apache 2.0, Replicate ~$0.05/clip, hook/closing 씬만 영상화 cascade) (4) ACE-Step v1.5 (Apache 2.0, Replicate ~$0.10/track, BGM Lyria cascade에 추가). Fish Speech는 "FISH AUDIO RESEARCH LICENSE" 위반 시 조치 경고로 제외. 사용자 결정: Replicate 소액 테스트 OK($1~5/월). 우선순위: WhisperX → OpenVoice → LTX-Video → ACE-Step. | Any | Medium | approval | 2026-05-19 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-360 | `[hanwoo-dashboard]` Localized remaining user-facing server action fallback errors. `getCattleList()` now throws `개체 목록을 불러오지 못했습니다.`, `getSalesRecords()` now throws `판매 기록을 불러오지 못했습니다.`, and admin raw-data validation now returns `지원하지 않는 데이터 유형입니다.` instead of `Failed to fetch cattle data.`, `Failed to fetch sales records.`, and `Invalid model name`. Added `actions-copy.test.mjs` to guard these server-action fallback strings. Verification: focused Hanwoo server-action copy tests passed (`112 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 112 passed, lint passed, build passed), `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. | Codex | 2026-05-20 |
| T-359 | `[hanwoo-dashboard]` Localized the financial analysis surface. `AnalysisTab` no longer renders English section labels (`Financial Analysis`, `Monthly Flow`, `Cost Mix`, `Top Sales`), and `FinancialChartWidget` no longer renders `Farm Financial Overview`, `Recent 6-month revenue, expense, and profit`, `Unit: KRW`, or English chart legend labels. Added `analysis-copy.test.mjs` to guard this financial-analysis copy. Verification: focused Hanwoo analysis-copy tests passed (`111 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 111 passed, lint passed, build passed), source scan passed, `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. | Codex | 2026-05-20 |
| T-358 | `[hanwoo-dashboard]` Localized the shared authentication fallback. `AuthenticationError` now defaults to `로그인이 필요합니다.` instead of `Authentication required.`, so authenticated API routes that pass through `requireAuthenticatedSession()` do not leak English auth copy when no route-specific override is provided. Verification: focused Hanwoo payment/auth source tests passed (`110 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 110 passed, lint passed, build passed), `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. | Codex | 2026-05-20 |
| T-357 | `[hanwoo-dashboard]` Localized payment API fallback responses. `/api/payments/prepare` now returns Korean operator-facing messages for customer-key mismatches, amount mismatches, generic preparation failures, and the customer-name fallback (`Joolife 사용자`). `/api/payments/confirm` now returns Korean messages for missing confirmation fields, wrong-user orders, amount mismatches, missing Toss configuration, timeout diagnostics, retryable gateway deferrals, and generic verification failures instead of leaking English fallback/API text. Extended `payment-ux-copy.test.mjs` to guard these route-level fallback strings. Verification: focused Hanwoo payment tests passed (`110 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 110 passed, lint passed, build passed), `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. | Codex | 2026-05-20 |
| T-356 | `[hanwoo-dashboard]` Polished the AI chat widget fallback surface. `AIChatWidget` now recognizes localized Gemini setup/configuration errors from `/api/ai/chat` as setup errors, keeping the guided fallback path aligned with the Korean API copy. The closed floating launcher now uses a lucide `Bot` icon with explicit `aria-label`/`title` instead of a bare `AI` text button. Added `ai-chat-widget-copy.test.mjs` to guard Korean setup-error patterns and accessible launcher wiring. Verification: focused Hanwoo AI chat/widget tests passed (`109 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 109 passed, lint passed, build passed), `git diff --check` passed, and UTF-8 graph risk `0.00`. | Codex | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
