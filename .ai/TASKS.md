# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-20 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed (`15 passed`) but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-305 | `[blind-to-x]` Migrate openai 1.59 ??2.x. PR #39 was closed because the bump is too risky for automation: although `pipeline/draft_providers.py` and `pipeline/image_generator.py` already use the v1+ `AsyncOpenAI` + `client.chat.completions.create` pattern, v2 has breaking changes (Python 3.7 drop, module-level globals removed, deprecated method removal, response shape tweaks) and 4 test fixtures will need mock refreshes. Plan: pin openai>=2.x in `pyproject.toml`, refresh mocks in `tests/unit/test_multi_platform.py`, `test_scrapers.py`, `test_env_runtime_fallbacks.py`, `test_image_generator.py`, run targeted pytest slice, then live smoke against the LLM fallback chain. Verify Anthropic prompt cache + workspace usage forwarder (`cost_tracker.py`) still flush. Budget ~쩍?? day. | Any | Low | approval | 2026-05-18 |
| T-318 | `[shorts-maker-v2]` Phase 3 잔여 품질 개선. Duration target/QC 분리는 T-321에서 완료됐고, hook_score<0.6 성공 출하 차단은 T-327에서 완료됐으며, 50.4MB 파일 크기 경계 hold는 T-331에서 완료됨. 남은 후보: (a) scene_qc 8/8 통과 패턴을 더 분석해 strict 기본값 유지 안전성 확인, (b) 채널별 TTS 속도/voice role 미세조정. | Any | Medium | safe | 2026-05-19 |
| T-320 | `[shorts-maker-v2]` 외부 OSS 도입(2026-05-19 리서치 완료, 메모리 `shorts_v2_oss_shortlist_20260519`). 사용자 환경 Intel Iris Xe iGPU(NVIDIA 없음) + RAM 15.75GB 확인. **로컬 적용 가능**: (1) WhisperX (BSD-2, `pip install whisperx`, CPU int8+medium, T-19 backlog 직접 해결, `pipeline/media/audio_mixin.py`의 OpenAI Whisper transcribe_audio() drop-in 교체) (2) OpenVoice v2 (MIT, 한국어 native, voice cloning, fallback chain `edge-tts → openvoice → openai`). **클라우드 GPU 필요**: (3) LTX-Video (Apache 2.0, Replicate ~$0.05/clip, hook/closing 씬만 영상화 cascade) (4) ACE-Step v1.5 (Apache 2.0, Replicate ~$0.10/track, BGM Lyria cascade에 추가). Fish Speech는 "FISH AUDIO RESEARCH LICENSE" 위반 시 조치 경고로 제외. 사용자 결정: Replicate 소액 테스트 OK($1~5/월). 우선순위: WhisperX → OpenVoice → LTX-Video → ACE-Step. | Any | Medium | approval | 2026-05-19 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-331 | `[shorts-maker-v2]` Fixed Gate 4 file-size boundary policy so otherwise valid Shorts renders just above 50MB no longer go to manual HOLD. `QCStep.gate4_final` now uses named final-size policy bounds `[2,60]MB`, matching the renderer's existing 8M/12M bitrate caps more closely while still holding oversized outputs. Added regression coverage for a 50.4MB pass and a 60.1MB hold. Verification: `test_qc_step.py` `60 passed`, targeted Ruff passed, full shorts-maker-v2 `tests/unit tests/integration` passed with repo-local basetemp, `project_qc_runner --project shorts-maker-v2 --check lint --json` passed, and graph risk `0.00`. | Codex | 2026-05-20 |
| T-330 | `[hanwoo-dashboard]` Replaced cattle-detail browser prompts for 발정 기록 / 수정 기록 with an in-app date form. `CattleDetailModal` now opens an inline breeding record form with date input, cancel/save controls, validation, pending state, lucide action icons, and existing `handleUpdateCattle` success/offline feedback instead of native `prompt()`. Added source wiring coverage to prevent prompt regressions. Verification: Hanwoo tests `86 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, direct Hanwoo graph risk `0.00`, staged code-review gate PASS before commit; commit hook emitted advisory WARN from stale graph heuristics/unrelated dirty WIP. Commit `b92249d`. | Codex | 2026-05-20 |
| T-328 | `[hanwoo-dashboard]` Connected the Farm Setup / 운영 준비도 building step to the actual add-building form. The setup-progress helper now emits `actionId: add-building` for missing 축사 구조, `DashboardClient` forwards the quick-action intent into Settings, and `SettingsTab` remounts from that intent so the 축사 registration form opens immediately instead of requiring a second click after navigation. Verification: focused Hanwoo tests `85 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, direct Hanwoo graph risk `0.00`; staged code-review gate emitted advisory WARN from broad graph heuristics/unrelated dirty WIP but did not block. Commit `cc32b52`. | Codex | 2026-05-20 |
| T-327 | `[shorts-maker-v2]` Tightened hook-score quality gating so weak hooks no longer ship as `success`. `PipelineOrchestrator` now records a retryable non-blocking `hook_score` degraded step when `score_hook(...).passed` is false, keeping rendered artifacts out of upload-ready success flow. Added regression coverage for weak hook degradation, added English contrast/tech specificity scoring so valid hooks like `Tiny chips, big savings` pass, and updated smoke/renderer fixtures to use quality-valid hook narration. Verification: focused hook/orchestrator/renderer/i18n tests passed, `ruff check` passed, graph risk `0.00`, and full shorts-maker-v2 `tests/unit tests/integration` passed with explicit repo-local basetemp. | Codex | 2026-05-20 |
| T-324 | `[blind-to-x]` `/goal "제품완성형으로 만들어봐"` — 대상 blind-to-x, 기준 테스트·CI 통과 + 문서·온보딩(AskUserQuestion). 완성도 감사: blind-to-x는 T-304에서 이미 release-ready였고 이번 세션은 검증 + 온보딩 갭 1건 보완. 검증 전부 green — 단위 `1562 passed, 1 skipped`, 통합 `64 passed`(test_curl_cffi 제외, CI와 동일), `ruff check .` 통과. CI `blind-to-x-tests` 잡은 동일 커맨드를 main push/PR마다 실행하며 워크스페이스 pnpm WIP과 무관(node-apps 잡만 수정). 갭 보완: `.env.example`에 README "관측성" 섹션이 문서화한 토글 3개(`OPENAI_IMAGE_ENABLED`/`LANGFUSE_ENABLED`/`BTX_USAGE_FORWARD`) 누락분 추가. | Claude Code (Opus 4.7 1M) | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
