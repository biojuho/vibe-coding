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
| T-394 | `[hanwoo-dashboard]` Made Today Focus and Setup Progress panel navigation use the shared preload path. Both panels now call `handleTabChange`, matching bottom navigation so target tabs can start full-list preloads instead of switching without the needed background load. `home-market-copy.test.mjs` guards the contract. Verification: full Hanwoo QC passed (`test` 130, lint, build); staged code-review gate WARN was heuristic and polluted by unrelated shorts WIP. Commit `3f35b2f`. | Codex | 2026-05-20 |
| T-393 | `[hanwoo-dashboard]` Fixed the Quick Action sales path. The `record-sale` home quick action now uses the same `preloadForTab` path as bottom-tab navigation, so Sales starts the full cattle registry load instead of opening into a passive preparing state. `home-market-copy.test.mjs` guards both normal tab navigation and quick-action preloading. Verification: focused Hanwoo tests passed (`130 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 130, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS. Commit `f38aed9`. | Codex | 2026-05-20 |
| T-392 | `[hanwoo-dashboard]` Localized the weather timeout degradation path. `DashboardClient` and `useWeather` now reuse Korean `WEATHER_STALE_MESSAGE` when Open-Meteo times out instead of showing the English `Showing the last available weather snapshot...` fallback, and `home-market-copy.test.mjs` guards both paths. Verification: focused Hanwoo tests passed (`130 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 130, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise; commit hook WARN came from heuristic test-gap noise while direct tests covered the committed files. Commit `e9030e0`. | Codex | 2026-05-20 |
| T-391 | `[hanwoo-dashboard]` Made full-list preload failures recoverable. Feed/calving/sales/analysis and building views that need the complete cattle registry or sales ledger now set Korean retry feedback, swallow background promise rejections, and render a `다시 불러오기` retry action instead of leaving users at a passive loading/ready placeholder. `home-market-copy.test.mjs` guards the contract. Verification: focused home/component tests passed (`130 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 130, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise; commit hook WARN came from heuristic test-gap noise while direct tests covered the committed files. Commit `4748282`. | Codex | 2026-05-20 |
| T-390 | `[hanwoo-dashboard]` Localized remaining notification/payment user-facing copy. Subscription success confirmation catch paths now log diagnostics and show stable Korean retry copy instead of rendering `error.message`, and `NotificationWidget` no longer shows the English `Priority Alerts` heading. Existing copy tests guard both contracts. Verification: focused payment/notification/component tests passed (`129 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 129, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise; commit hook WARN came from heuristic test-gap noise while direct tests covered the committed files. Commit `0d4a395`. | Codex | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
