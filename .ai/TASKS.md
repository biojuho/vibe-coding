# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-20 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed (`15 passed`) but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-320 | `[shorts-maker-v2]` 외부 OSS 도입(2026-05-19 리서치 완료). (2) OpenVoice v2 (MIT, 한국어 native, voice cloning, fallback chain `edge-tts → openvoice → openai` 로컬 적용) 도입 검토 및 설계. 로컬 CPU i7-12세대 구동 안정성 및 아키텍처 타당성 리서치 진행. **2026-05-20(Claude)**: OpenVoice 구현 WIP(`openvoice_client.py` + `audio_mixin` openvoice 라우팅 분기 + `config.ProviderSettings.tts_openvoice_checkpoint_dir` 필드 + 단위 테스트 8건)가 커밋 `8ba2850`로 정착 — 그동안 미검증이라 QC를 막던 `test_openvoice_client.py`를 정상화(`--maxfail=1`에 가려진 4 fail 수정), shorts-maker-v2 full QC green(1467 passed). **잔여 활성화 작업**: shorts `pyproject.toml`에 `openvoice`/`melo` 의존성 선언, OpenVoice v2 체크포인트 모델 다운로드, 라이브 음성복제 end-to-end 검증. 미설치 시 `edge-tts` fallback으로 우아하게 degrade하므로 현재 파이프라인엔 무해. | Any | Medium | approval | 2026-05-19 |
| T-372 | `[workspace]` 모노레포 마이그레이션 마무리(pnpm+turbo+biome+uv). (구 T-368 — DONE의 Codex T-368과 ID 충돌해 재번호) 현재 WIP(untracked): 루트 `package.json`/`pnpm-workspace.yaml`/`turbo.json`/`biome.json`/`.npmrc`/`pyproject.toml`/`uv.lock`, 수정된 `setup.bat`·`.github/workflows/full-test-matrix.yml`, 삭제된 knowledge-dashboard `package-lock.json`. **2026-05-20 진단(Claude)**: ① `pnpm install`이 이 로컬(Windows + 한글 홈 `박주호`)에서 linking 단계에 `exit 127`·에러 출력 없이 6회 연속 중단 — `--lockfile-only`(linking 없음)만 exit 0. 한글 경로 툴링 취약성(메모리 `windows_korean_path_encode_strict`) 의심. → **로컬 검증 불가**, CI(ubuntu-latest)는 정상일 가능성 높음. ② `pnpm-lock.yaml` 부재였으나 `pnpm install --lockfile-only`로 생성됨(루트, untracked, 336KB) — `.gitignore`엔 lockfile 제외 없음. ③ 미해결 결정: (a) `biome.json`이 `recommended` 규칙 + 전 코드베이스 대상 `biome check .` → `pnpm lint`가 기존 코드에서 대량 진단으로 적색 가능성(blast radius 미측정, 로컬 install 불가로 측정 못 함) — biome 채택 범위/advisory 여부 결정 필요. (b) hanwoo `package.json`에서 `postinstall: prisma generate` 제거됨 → CI fresh build 시 prisma client 미생성 위험, 복원하거나 turbo build/CI에 `prisma generate` 단계 추가 필요. ④ 잔존 정리: suika-game-v2·word-chain `package-lock.json` 미삭제(pnpm 모노레포에선 제거 대상), CI `actions/setup-node@v6→v4` 다운그레이드. **로컬 검증 불가 + 미해결 설계 결정 + infra/CI 범위라 신중 진행 필요 → approval.** | Any | Medium | approval | 2026-05-20 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-404 | `[hanwoo-dashboard]` Kept inventory quantity edits open when async saves fail. `InventoryTab` now awaits `onUpdateQuantity` and only exits edit mode after a truthy result, preserving edited quantity input for retry while successful saves keep the existing close behavior. `empty-state-wiring.test.mjs` guards the contract. Verification: focused Hanwoo tests passed (`136 passed`), targeted ESLint passed, path-limited `git diff --check` passed, staged review gate JSON passed, and full Hanwoo QC passed (`test` 136, lint, build). Commit `1b90641`. | Codex | 2026-05-20 |
| T-403 | `[hanwoo-dashboard]` Made pen and cattle row cards keyboard reachable. `PenCard` and `CattleRow` now expose button semantics, tab focus, Korean accessible labels, and Enter/Space activation through a shared keyboard handler. `cards-accessibility.test.mjs` guards the contract. Verification: focused Hanwoo tests passed (`135 passed`), targeted ESLint passed, path-limited `git diff --check` passed, staged review gate JSON passed, and full Hanwoo QC passed (`test` 135, lint, build). Commit `89f2a29`. | Codex | 2026-05-20 |
| T-398 | `[workspace]` Dependabot 메이저 버전 PR 8건 정리 완료 — **오픈 PR 0건 달성**(21건 전량 머지). 트리아지: `#70`/`#72`는 제목이 `bump react`였으나 실제론 React `19.2.x` patch라 즉시 안전 머지. 빌드/테스트 툴링 메이저 `#63`(vite-plugin-react 6)·`#65`(pytest-asyncio 1.3)·`#68`(typescript 6)은 rebase 후 프로젝트 CI(build+test) 그린 확인 → 머지. `#60` anthropic 0.43→0.103: blind-to-x 사용처(`draft_providers.py`)가 stable core API(`messages.create` + prompt-cache 파라미터)만 사용함을 코드 확인, rebase 후 blind-to-x CI 그린 → 머지. `#71` recharts 2→3: hanwoo 5개 차트 컴포넌트가 전부 core 컴포넌트(`LineChart/BarChart/PieChart/Line/Bar/Pie/Cell/XAxis/YAxis/Tooltip/Legend/CartesianGrid`)만 사용·`'use client'`, rebase 후 hanwoo CI 그린 → 머지. `#64` lucide-react 0.563→1.16: v1이 `Github` brand icon 제거 → knowledge-dashboard `page.tsx`를 `FolderGit2`(non-brand, 0.563/1.x 양쪽 호환)로 교체하는 fix를 PR 브랜치에 직접 커밋(`707edf0`) → CI 그린 → 머지. 검증: 최종 머지 후 `main`(`11e9acb`) `active-project-matrix` 5잡 전부 success + `root-quality-gate` success. | Claude | 2026-05-20 |
| T-402 | `[hanwoo-dashboard]` Kept the feed-record form from resetting when async saves fail. `FeedTab` now awaits `onRecordFeed` and only resets after a truthy result, preserving entered feed data for retry while success/offline queue paths keep the existing reset behavior. `empty-state-wiring.test.mjs` guards the contract. Verification: focused Hanwoo tests passed (`135 passed`), targeted ESLint passed, path-limited `git diff --check` passed, graph risk `0.00`, and full Hanwoo QC passed (`test` 135, lint, build). Commit `774b5c0`. | Codex | 2026-05-20 |
| T-401 | `[hanwoo-dashboard]` Kept the cattle edit form open when async update mutations fail. The edit modal now passes `handleUpdateCattle` directly to `CattleForm`, so the async update handler owns close behavior: success/offline queue closes, failed mutations preserve the user's edits for retry. `empty-state-wiring.test.mjs` guards the contract. Verification: focused Hanwoo tests passed (`133 passed`), targeted ESLint passed, path-limited `git diff --check` passed, graph risk `0.00`, and full Hanwoo QC passed (`test` 133, lint, build). Commit `8d8a9dd`. | Codex | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
