# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-20 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed (`15 passed`) but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-320 | `[shorts-maker-v2]` 외부 OSS 도입(2026-05-19 리서치 완료, 메모리 `shorts_v2_oss_shortlist_20260519`). 사용자 환경 Intel Iris Xe iGPU(NVIDIA 없음) + RAM 15.75GB 확인. **로컬 적용 가능**: (1) WhisperX (BSD-2, `pip install whisperx`, CPU int8+medium, T-19 backlog 직접 해결, `pipeline/media/audio_mixin.py`의 OpenAI Whisper transcribe_audio() drop-in 교체) (2) OpenVoice v2 (MIT, 한국어 native, voice cloning, fallback chain `edge-tts → openvoice → openai`). **클라우드 GPU 필요**: (3) LTX-Video (Apache 2.0, Replicate ~$0.05/clip, hook/closing 씬만 영상화 cascade) (4) ACE-Step v1.5 (Apache 2.0, Replicate ~$0.10/track, BGM Lyria cascade에 추가). Fish Speech는 "FISH AUDIO RESEARCH LICENSE" 위반 시 조치 경고로 제외. 사용자 결정: Replicate 소액 테스트 OK($1~5/월). 우선순위: WhisperX → OpenVoice → LTX-Video → ACE-Step. | Any | Medium | approval | 2026-05-19 |
| T-366 | `[hanwoo-dashboard]` 고아 위젯 연결. `ProfitabilityWidget`(컴포넌트) + `getProfitabilityData`(서버 액션) + `getProfitabilityEstimates`(서비스)가 모두 구현됐고 `WIDGET_REGISTRY`에 `{ id: 'profitability', defaultOn: true }`로 등록됐지만 어디에서도 `<ProfitabilityWidget />`을 렌더하지 않음(`git grep -i profitabilit` 결과 마운트 지점 0건). 기본 ON 위젯이 실제로는 표시되지 않는 미완 기능 — DashboardClient/탭 위젯 렌더 경로에 연결 필요. 신규 기능 표면이라 approval. | Any | Medium | approval | 2026-05-20 |
| T-367 | `[hanwoo-dashboard]` `src/lib/formSchemas.js` enum 값 영어. 스케줄 타입 `['General','Vaccination','Checkup','Breeding','Other']`(L67), 재고 카테고리 `['Feed','Medicine','Equipment','Other']`(L72). UI는 한글 라벨을 보여주지만 DB에 영어 문자열로 저장됨. 한글화하려면 기존 데이터 마이그레이션 필요(단순 카피 변경 아님 → DB 작업이라 approval). 영향: formSchemas.js, ScheduleTab.js, InventoryTab.js + Prisma 데이터. | Any | Low | approval | 2026-05-20 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-362 | `[hanwoo-dashboard]` Localized admin diagnostics database status values. `lib/actions/system.js` now returns `정상`, `연결 실패`, and `확인 불가` instead of `Online`, `Offline`, and `N/A`, and `diagnostics-copy.test.mjs` guards against those English status values returning. Verification: focused Hanwoo diagnostics/action/component tests passed (`115 passed`), targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock, source scan passed, `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. | Codex | 2026-05-20 |
| T-365 | `[hanwoo-dashboard]` Localized the profitability widget error copy. `getProfitabilityEstimates()` threw English errors (`No market price data available...`, `Price data parsing failed`) that flow through `error: err.message` into `ProfitabilityWidget`, which renders `{error}` as visible operator-facing UI text — now `수익성 시뮬레이션에 사용할 시세 데이터가 없습니다.` / `시세 데이터를 해석하지 못했습니다.`; the console diagnostic was localized too. Added `profitability-copy.test.mjs` regression guard. Verification: focused profitability-copy test passed (2/2), full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 115 passed, lint passed, build passed). Commit `172e998`. | Claude Code (Opus 4.7 1M) | 2026-05-20 |
| T-361 | `[hanwoo-dashboard]` Localized the shared dialog close label for screen-reader users. The Radix dialog close control in `components/ui/dialog.js` now exposes `닫기` instead of `Close`, and `dialog-copy.test.mjs` guards against the English sr-only label returning. Verification: focused Hanwoo dialog-copy tests passed (`113 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 113 passed, lint passed, build passed), accessibility-copy source scan passed, `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. | Codex | 2026-05-20 |
| T-360 | `[hanwoo-dashboard]` Localized remaining user-facing server action fallback errors. `getCattleList()` now throws `개체 목록을 불러오지 못했습니다.`, `getSalesRecords()` now throws `판매 기록을 불러오지 못했습니다.`, and admin raw-data validation now returns `지원하지 않는 데이터 유형입니다.` instead of `Failed to fetch cattle data.`, `Failed to fetch sales records.`, and `Invalid model name`. Added `actions-copy.test.mjs` to guard these server-action fallback strings. Verification: focused Hanwoo server-action copy tests passed (`112 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 112 passed, lint passed, build passed), `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. | Codex | 2026-05-20 |
| T-359 | `[hanwoo-dashboard]` Localized the financial analysis surface. `AnalysisTab` no longer renders English section labels (`Financial Analysis`, `Monthly Flow`, `Cost Mix`, `Top Sales`), and `FinancialChartWidget` no longer renders `Farm Financial Overview`, `Recent 6-month revenue, expense, and profit`, `Unit: KRW`, or English chart legend labels. Added `analysis-copy.test.mjs` to guard this financial-analysis copy. Verification: focused Hanwoo analysis-copy tests passed (`111 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 111 passed, lint passed, build passed), source scan passed, `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. | Codex | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
