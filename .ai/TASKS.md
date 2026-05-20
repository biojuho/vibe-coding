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
| T-340 | `[hanwoo-dashboard]` Localized remaining weather fallback copy in the home weather surface. `weather-state.mjs` now emits Korean unavailable, stale, partial-forecast messages and Korean source labels (`실시간 Open-Meteo`, `부분 예보`, `이전 날씨`, `확인 불가`), and `WeatherWidget` no longer renders English unavailable fallback text. Added source/state regression coverage to prevent `Weather Unavailable` / `Weather data is temporarily unavailable` / stale or partial English labels from returning. Verification: Hanwoo node tests `94 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, `git diff --check` passed, and UTF-8 graph risk `0.00`. | Codex | 2026-05-20 |
| T-339 | `[hanwoo-dashboard]` Localized remaining visible English copy on the home surface and market price widget. Home fallback farm name now reads `Joolife 한우 농장`; panel eyebrows now use Korean labels (`오늘 요약`, `빠른 기록`, `운영 준비`); and `MarketPriceWidget` now renders Korean loading, unavailable, source, heading, grade, updated, and KAPE source labels instead of English UI copy such as `Joolife Dashboard`, `Today Brief`, `Quick Record`, `Farm Setup`, `Loading market prices`, and `Hanwoo Market Prices`. Added source regression coverage. Verification on current HEAD after adjacent T-338: Hanwoo tests `92 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, `git diff --check` passed, and direct Hanwoo graph risk `0.00`. Commit `cd99fb8`. | Codex | 2026-05-20 |
| T-338 | `[hanwoo-dashboard]` Fixed remaining English fallback copy in the market-price state layer. `market-price-state.mjs` now returns Korean product copy for unavailable market prices, stale-cache notices, and live/cache/unavailable source labels, preventing `MarketPriceWidget` from surfacing English fallback text in degraded KAPE states. Added regression assertions for stale, live, and unavailable labels/messages. Verification: focused market-price tests passed, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 92 passed, lint passed, build passed), `git diff --check` passed, and graph risk `0.00`. | Codex | 2026-05-20 |
| T-337 | `[shorts-maker-v2]` 렌더 핫패스 컬러 그레이딩 2.7배 가속. 렌더는 파이프라인 wall time의 ~89%이고 인코딩은 h264_qsv 하드웨어 가속이라 빠름 — 990초는 MoviePy 프레임별 Python 합성 비용. 신규 `scripts/bench_render.py`(합성 에셋 결정론적 렌더 벤치마크/프로파일러, LLM 파이프라인 불필요)로 측정: 렌더의 ~40%가 `color_grade_clip`(A/B: 4초 영상 71초 vs 색보정 제외 43초). 컬러 그레이딩은 프레임마다 1080×1920 numpy elementwise 패스 ~10회(패스당 ~14ms). `_grade_inplace`를 패스 ~10→~5로 축소: 밝기+대비를 단일 affine `A*x+B`로 융합, 채도 3→2패스, 틴트 채널별 strided 3회→길이-3 브로드캐스트 1회, `color_grade_clip` 프레임 함수는 float32 유지로 프레임당 uint8↔float32 왕복 제거. 측정: `_grade_inplace` 163.5→61.0 ms/frame(2.7배), end-to-end 렌더 ~72→~65초(~10%). 출력은 naive 레퍼런스 대비 max abs diff ≤0.0001(수학적 동일). 검증: color_grading 테스트 29 pass(회귀 테스트 2건 신규), 렌더 관련 단위 테스트 210 pass, `ruff check` 통과. commit `0930e4a`+`504c709`. | Claude Code (Opus 4.7 1M) | 2026-05-20 |
| T-305 | `[blind-to-x]` openai SDK 1.59.9 → 2.37.0 마이그레이션 (PR #39 재개). 탐색으로 PR #39 triage의 "4개 mock fixture 갱신 필요" 추정이 보수적이었음을 확인 — 코드는 `chat.completions.create`/`images.generate`/`AsyncOpenAI` 생성자 등 openai 2.x에서 변경 없는 안정 API만 사용(+`getattr` 방어 접근)하고, 테스트 mock은 클라이언트 생성자를 fake로 교체해 SDK 버전 무관. openai 2.0.0의 실 breaking change(Responses API tool-call output)는 blind-to-x 미사용. **코드/테스트 변경 0건, 버전 핀만 변경**: `pyproject.toml` + `projects/blind-to-x/uv.lock`(openai 항목만, transitive 변화 없음). 검증: openai 2.37.0 설치 후 단위+통합 `1626 passed, 1 skipped, 0 failed`, `ruff check .` 통과. 라이브 스모크는 유료 API라 미실행(mock 1626건으로 갈음). | Claude Code (Opus 4.7 1M) | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
