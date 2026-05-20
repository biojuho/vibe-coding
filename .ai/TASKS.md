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
| T-305 | `[blind-to-x]` openai SDK 1.59.9 → 2.37.0 마이그레이션 (PR #39 재개). 탐색으로 PR #39 triage의 "4개 mock fixture 갱신 필요" 추정이 보수적이었음을 확인 — 코드는 `chat.completions.create`/`images.generate`/`AsyncOpenAI` 생성자 등 openai 2.x에서 변경 없는 안정 API만 사용(+`getattr` 방어 접근)하고, 테스트 mock은 클라이언트 생성자를 fake로 교체해 SDK 버전 무관. openai 2.0.0의 실 breaking change(Responses API tool-call output)는 blind-to-x 미사용. **코드/테스트 변경 0건, 버전 핀만 변경**: `pyproject.toml` + `projects/blind-to-x/uv.lock`(openai 항목만, transitive 변화 없음). 검증: openai 2.37.0 설치 후 단위+통합 `1626 passed, 1 skipped, 0 failed`, `ruff check .` 통과. 라이브 스모크는 유료 API라 미실행(mock 1626건으로 갈음). | Claude Code (Opus 4.7 1M) | 2026-05-20 |
| T-336 | `[shorts-maker-v2]` Completed the final safe T-318 Phase 3 item by preserving channel-specific TTS tuning through the media generation path. `MediaStep` now stores `AppConfig._channel_key` and passes it into direct Edge TTS calls, Chatterbox/CosyVoice premium calls, and Edge fallback calls so `EdgeTTSClient` can apply channel-specific prosody instead of silently using default jitter/pitch. Added regression coverage for direct Edge routing and premium fallback channel propagation, and updated branch coverage for the explicit empty-channel contract. Verification: focused TTS routing tests `5 passed`, full shorts-maker-v2 `tests/unit tests/integration` passed with repo-local basetemp, targeted Ruff/check/format passed, project QC lint passed, and graph risk `0.00`. T-318 is now closed; remaining shorts-maker-v2 work is approval-gated OSS T-320. | Codex | 2026-05-20 |
| T-335 | `[hanwoo-dashboard]` Localized app-level metadata and PWA install copy for product polish. `src/app/layout.js` and `public/manifest.json` now use Korean product-ready title/description/short name for browser title, install prompt, and metadata instead of `Joolife Dashboard` / `Premium Hanwoo Farm Management System`. Added source/manifest regression coverage. Verification: Hanwoo tests `90 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed after approved Google Fonts network fetch, direct Hanwoo graph risk `0.00`, staged code-review gate PASS before commit; commit hook emitted advisory WARN from graph heuristics/unrelated shorts-maker WIP. Commit `62020ec`. | Codex | 2026-05-20 |
| T-334 | `[shorts-maker-v2]` Fixed scene_qc strict retry routing so audio/timing failures regenerate audio instead of wasting retries on visual-only regeneration. `PipelineOrchestrator` now derives the retry component from failed QC checks: audio integrity/timing/volume issues route to `audio` or `both`, visual issues route to `visual`, and script-only issues skip media retry and remain surfaced as unresolved. Retry counts now reflect actual media regeneration attempts. Added run-level and helper regression coverage. Verification: focused orchestrator+QC tests `115 passed`, full shorts-maker-v2 `tests/unit tests/integration` passed with repo-local basetemp, project QC lint passed, targeted Ruff/format passed, and graph risk `0.00`. | Codex | 2026-05-20 |
| T-333 | `[hanwoo-dashboard]` Localized the admin diagnostics surface for product polish. `DiagnosticsPageClient` now uses Korean operations copy for loading, toast errors, status cards, database ledger, raw-data inspector, model selector labels, and dashboard return action instead of English placeholders. Added source wiring coverage to keep visible diagnostics copy Korean. Verification: Hanwoo tests `89 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, direct Hanwoo graph risk `0.00`, staged code-review gate PASS before commit; commit hook emitted advisory WARN from graph heuristics/unrelated shorts-maker WIP. Commit `c0113d9`. | Codex | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
