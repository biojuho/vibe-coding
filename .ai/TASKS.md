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
| T-343 | `[hanwoo-dashboard]` Hardened cattle CSV export formatting after the Korean-header localization. The export helper now uses fully Korean headers (`개체 번호`, `축사 번호` instead of mixed `ID` labels), quotes CSV cells containing commas/quotes/newlines, and preserves normalized memo text. Added regression coverage for quoted cattle names such as `복"실,이`. Verification: focused CSV tests passed (`98 passed`), targeted ESLint passed, `project_qc_runner --project hanwoo-dashboard --json` passed for test/lint and build passed on retry after a transient concurrent Next build lock, `git diff --check` passed, and UTF-8 graph risk `0.00`. | Codex | 2026-05-20 |
| T-342 | `[hanwoo-dashboard]` Localized cattle CSV export output. The Excel/download flow now uses a pure `cattle-csv-export.mjs` helper with Korean CSV headers (`이름`, `이력번호`, `생년월일`, `성별`, `상태`, `축사 ID`, `칸 번호`, `메모`), keeps the UTF-8 BOM for spreadsheet compatibility, and normalizes memo commas/extra whitespace before export. `ExcelExportButton` now delegates CSV generation to the tested helper. Verification: focused export/import tests passed (`97 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 97 passed, lint passed, build passed), `git diff --check` passed, and UTF-8 graph risk `0.00`. | Codex | 2026-05-20 |
| T-341 | `[hanwoo-dashboard]` Localized payment confirmation fallback copy. `payment-confirmation.mjs` now returns Korean pending, failure, amount-mismatch, and malformed gateway-response messages while preserving explicit gateway-provided messages. Added direct behavior coverage and source-copy coverage so app-authored user-facing fallbacks do not regress to `Payment confirmation`, `Payment verification`, `Confirmed payment amount`, or `Gateway response:`. Verification: Hanwoo node tests `96 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, `git diff --check` passed, staged code-review gate PASS, and direct Hanwoo graph risk `0.00`. Commit `535839a`. | Codex | 2026-05-20 |
| T-340 | `[hanwoo-dashboard]` Localized remaining weather fallback copy in the home weather surface. `weather-state.mjs` now emits Korean unavailable, stale, partial-forecast messages and Korean source labels (`실시간 Open-Meteo`, `부분 예보`, `이전 날씨`, `확인 불가`), and `WeatherWidget` no longer renders English unavailable fallback text. Added source/state regression coverage to prevent `Weather Unavailable` / `Weather data is temporarily unavailable` / stale or partial English labels from returning. Verification: Hanwoo node tests `94 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, `git diff --check` passed, and UTF-8 graph risk `0.00`. | Codex | 2026-05-20 |
| T-339 | `[hanwoo-dashboard]` Localized remaining visible English copy on the home surface and market price widget. Home fallback farm name now reads `Joolife 한우 농장`; panel eyebrows now use Korean labels (`오늘 요약`, `빠른 기록`, `운영 준비`); and `MarketPriceWidget` now renders Korean loading, unavailable, source, heading, grade, updated, and KAPE source labels instead of English UI copy such as `Joolife Dashboard`, `Today Brief`, `Quick Record`, `Farm Setup`, `Loading market prices`, and `Hanwoo Market Prices`. Added source regression coverage. Verification on current HEAD after adjacent T-338: Hanwoo tests `92 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, `git diff --check` passed, and direct Hanwoo graph risk `0.00`. Commit `cd99fb8`. | Codex | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
