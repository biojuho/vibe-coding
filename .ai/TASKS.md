# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-20 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed (`15 passed`) but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-320 | `[shorts-maker-v2]` 외부 OSS 도입(2026-05-19 리서치 완료). (2) OpenVoice v2 (MIT, 한국어 native, voice cloning, fallback chain `edge-tts → openvoice → openai` 로컬 적용) 도입 검토 및 설계. 로컬 CPU i7-12세대 구동 안정성 및 아키텍처 타당성 리서치 진행. | Any | Medium | approval | 2026-05-19 |
| T-372 | `[workspace]` 모노레포 마이그레이션 마무리(pnpm+turbo+biome+uv). (구 T-368 — DONE의 Codex T-368과 ID 충돌해 재번호) 현재 WIP(untracked): 루트 `package.json`/`pnpm-workspace.yaml`/`turbo.json`/`biome.json`/`.npmrc`/`pyproject.toml`/`uv.lock`, 수정된 `setup.bat`·`.github/workflows/full-test-matrix.yml`, 삭제된 knowledge-dashboard `package-lock.json`. **2026-05-20 진단(Claude)**: ① `pnpm install`이 이 로컬(Windows + 한글 홈 `박주호`)에서 linking 단계에 `exit 127`·에러 출력 없이 6회 연속 중단 — `--lockfile-only`(linking 없음)만 exit 0. 한글 경로 툴링 취약성(메모리 `windows_korean_path_encode_strict`) 의심. → **로컬 검증 불가**, CI(ubuntu-latest)는 정상일 가능성 높음. ② `pnpm-lock.yaml` 부재였으나 `pnpm install --lockfile-only`로 생성됨(루트, untracked, 336KB) — `.gitignore`엔 lockfile 제외 없음. ③ 미해결 결정: (a) `biome.json`이 `recommended` 규칙 + 전 코드베이스 대상 `biome check .` → `pnpm lint`가 기존 코드에서 대량 진단으로 적색 가능성(blast radius 미측정, 로컬 install 불가로 측정 못 함) — biome 채택 범위/advisory 여부 결정 필요. (b) hanwoo `package.json`에서 `postinstall: prisma generate` 제거됨 → CI fresh build 시 prisma client 미생성 위험, 복원하거나 turbo build/CI에 `prisma generate` 단계 추가 필요. ④ 잔존 정리: suika-game-v2·word-chain `package-lock.json` 미삭제(pnpm 모노레포에선 제거 대상), CI `actions/setup-node@v6→v4` 다운그레이드. **로컬 검증 불가 + 미해결 설계 결정 + infra/CI 범위라 신중 진행 필요 → approval.** | Any | Medium | approval | 2026-05-20 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-390 | `[hanwoo-dashboard]` Localized remaining notification/payment user-facing copy. Subscription success confirmation catch paths now log diagnostics and show stable Korean retry copy instead of rendering `error.message`, and `NotificationWidget` no longer shows the English `Priority Alerts` heading. Existing copy tests guard both contracts. Verification: focused payment/notification/component tests passed (`129 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 129, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise; commit hook WARN came from heuristic test-gap noise while direct tests covered the committed files. Commit `0d4a395`. | Codex | 2026-05-20 |
| T-389 | `[hanwoo-dashboard]` Surfaced sales pagination failures to operators. `useSalesPagination` now tracks safe Korean `loadError` copy for timeout, HTTP/API, pagination-safety, and unexpected failures, and `SalesTab` renders that message as a polite status region below the "load more" button instead of failing silently with console-only diagnostics. `sales-pagination-feedback.test.mjs` guards the contract. Verification: focused Hanwoo tests passed (`129 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 129, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise; commit hook WARN came from heuristic dirty-WIP/test-gap noise while direct tests covered the committed files. Commit `3554dae`. | Codex | 2026-05-20 |
| T-388 | `[hanwoo-dashboard]` Localized dashboard API and admin system fallback failures. `/api/dashboard/{summary,cattle,sales}` 500 paths now log diagnostics and return stable Korean fallback copy instead of arbitrary `error.message`, dashboard list validation errors now use Korean operator copy, and admin system/raw-data actions no longer return raw DB/runtime messages except the known unsupported-data-type copy. `home-market-copy.test.mjs` and `actions-copy.test.mjs` guard these contracts. Verification: focused action/home tests passed (`127 passed`), `npm.cmd run lint` passed, full Hanwoo QC passed (`test` 127, lint, build), path-limited `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate WARN was heuristic test-gap noise while direct tests covered the committed files. Commit `f1a4637`. | Codex | 2026-05-20 |
| T-320 | `[shorts-maker-v2]` 외부 OSS WhisperX 로컬 단어 단위 타임스탬프 동기화 및 OpenAI API 이중 안전 Fallback 도입 완료. CPU int8/medium 환경 최적화, alignment 장애 시 segment 파싱 fallback, 최종 에러 발생 시 OpenAI `whisper-1` API로 fallback하는 하이브리드 안전망 완성. 윈도우 한글 사용자 환경 권한 버그(PermissionError) 자가 수정을 통해 `project_qc_runner.py`를 개선하고 venv 테스트(12개 whisper_aligner + 14개 openai_client 패스) 및 ruff lint 통과 검증 완료. Commit `e4fe9c4`. | Gemini (Antigravity) | 2026-05-20 |
| T-387 | `[hanwoo-dashboard]` Localized Excel export failure feedback. `ExcelExportButton` now logs CSV/export exceptions and shows stable Korean retry copy instead of rendering arbitrary browser/runtime `error.message` text in the feedback toast. `excel-export-button-copy.test.mjs` guards the fallback copy and rejects the old raw-error description path. Verification: focused Excel export/CSV/component tests passed (`127 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 127, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise; commit hook WARN came from dirty-WIP/test-gap heuristic noise while direct tests covered the committed files. Commit `cf07c4e`. | Codex | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
