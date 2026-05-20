# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-20 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed (`15 passed`) but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |
| T-320 | `[shorts-maker-v2]` 외부 OSS 도입(2026-05-19 리서치 완료). (2) OpenVoice v2 (MIT, 한국어 native, voice cloning, fallback chain `edge-tts → openvoice → openai` 로컬 적용) 도입 검토 및 설계. 로컬 CPU i7-12세대 구동 안정성 및 아키텍처 타당성 리서치 진행. **2026-05-20(Claude)**: OpenVoice 구현 WIP(`openvoice_client.py` + `audio_mixin` openvoice 라우팅 분기 + `config.ProviderSettings.tts_openvoice_checkpoint_dir` 필드 + 단위 테스트 8건)가 커밋 `8ba2850`로 정착 — 그동안 미검증이라 QC를 막던 `test_openvoice_client.py`를 정상화(`--maxfail=1`에 가려진 4 fail 수정), shorts-maker-v2 full QC green(1467 passed). **잔여 활성화 작업**: shorts `pyproject.toml`에 `openvoice`/`melo` 의존성 선언, OpenVoice v2 체크포인트 모델 다운로드, 라이브 음성복제 end-to-end 검증. 미설치 시 `edge-tts` fallback으로 우아하게 degrade하므로 현재 파이프라인엔 무해. | Any | Medium | approval | 2026-05-19 |
| T-372 | `[workspace]` 모노레포 마이그레이션 마무리(pnpm+turbo+biome+uv). (구 T-368 — DONE의 Codex T-368과 ID 충돌해 재번호) 현재 WIP(untracked): 루트 `package.json`/`pnpm-workspace.yaml`/`turbo.json`/`biome.json`/`.npmrc`/`pyproject.toml`/`uv.lock`, 수정된 `setup.bat`·`.github/workflows/full-test-matrix.yml`, 삭제된 knowledge-dashboard `package-lock.json`. **2026-05-20 진단(Claude)**: ① `pnpm install`이 이 로컬(Windows + 한글 홈 `박주호`)에서 linking 단계에 `exit 127`·에러 출력 없이 6회 연속 중단 — `--lockfile-only`(linking 없음)만 exit 0. 한글 경로 툴링 취약성(메모리 `windows_korean_path_encode_strict`) 의심. → **로컬 검증 불가**, CI(ubuntu-latest)는 정상일 가능성 높음. ② `pnpm-lock.yaml` 부재였으나 `pnpm install --lockfile-only`로 생성됨(루트, untracked, 336KB) — `.gitignore`엔 lockfile 제외 없음. ③ 미해결 결정: (a) `biome.json`이 `recommended` 규칙 + 전 코드베이스 대상 `biome check .` → `pnpm lint`가 기존 코드에서 대량 진단으로 적색 가능성(blast radius 미측정, 로컬 install 불가로 측정 못 함) — biome 채택 범위/advisory 여부 결정 필요. (b) hanwoo `package.json`에서 `postinstall: prisma generate` 제거됨 → CI fresh build 시 prisma client 미생성 위험, 복원하거나 turbo build/CI에 `prisma generate` 단계 추가 필요. ④ 잔존 정리: suika-game-v2·word-chain `package-lock.json` 미삭제(pnpm 모노레포에선 제거 대상), CI `actions/setup-node@v6→v4` 다운그레이드. **로컬 검증 불가 + 미해결 설계 결정 + infra/CI 범위라 신중 진행 필요 → approval.** | Any | Medium | approval | 2026-05-20 |
| T-398 | `[workspace]` Dependabot 메이저 버전 PR 8건 검토 — T-396에서 위험 분류로 보류한 잔여분. 각 항목은 자체 마이그레이션·런타임 검증이 필요(CI 그린이어도 런타임 안전 보장 안 됨): `#60` anthropic 0.43→0.103 (blind-to-x LLM SDK, 0.x 60버전 점프 — 코드 마이그레이션 필요), `#63` @vitejs/plugin-react 5→6 (word-chain), `#64` lucide-react 0.563→1.16 (knowledge-dashboard, **CI 빌드 실패 확인됨** — 아이콘 API 변경 추정), `#65` pytest-asyncio 0.24→1.3 (blind-to-x, asyncio_mode 설정 breaking), `#68` typescript 5.9→6.0 (hanwoo-dashboard), `#70` react major (knowledge-dashboard), `#71` recharts 2→3 (hanwoo-dashboard, 차트 API breaking), `#72` react major (word-chain). 한 번에 하나씩, 프로젝트별 테스트와 함께 진행 권장. | Any | Medium | approval | 2026-05-20 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-401 | `[hanwoo-dashboard]` Kept the cattle edit form open when async update mutations fail. The edit modal now passes `handleUpdateCattle` directly to `CattleForm`, so the async update handler owns close behavior: success/offline queue closes, failed mutations preserve the user's edits for retry. `empty-state-wiring.test.mjs` guards the contract. Verification: focused Hanwoo tests passed (`133 passed`), targeted ESLint passed, path-limited `git diff --check` passed, graph risk `0.00`, and full Hanwoo QC passed (`test` 133, lint, build). Commit `8d8a9dd`. | Codex | 2026-05-20 |
| T-400 | `[hanwoo-dashboard]` Hid decorative public-page icons from assistive technology. Login, route-error, and not-found status icons now use `aria-hidden="true"`, and password visibility toggle icons are hidden so Korean `aria-label` copy remains the accessible name. `error-pages-wiring.test.mjs` guards the contract. Verification: focused Hanwoo tests passed (`132 passed`), targeted ESLint passed, path-limited `git diff --check` passed, graph risk `0.00`, and full Hanwoo QC passed (`test` 132, lint, build). Commit `3da2221`. | Codex | 2026-05-20 |
| T-399 | `[hanwoo-dashboard]` Made home building navigation semantic and keyboard-accessible. The empty-building CTA is now a real button routed through `handleTabChange('settings')`, and building cards are real buttons that preserve the clay-card visual treatment while exposing native keyboard activation. `home-market-copy.test.mjs` guards the contract. Verification: focused Hanwoo tests passed (`132 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 132, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS. Commit `c8473ca`. | Codex | 2026-05-20 |
| T-396 | `[workspace]` Dependabot PR 백로그 21건 정리. 안전 13건(`#56 #57 #58 #59 #61 #62 #66 #67 #69 #73 #74 #75 #76` — patch/minor·range 확장)을 admin squash-merge로 드레인. dependabot이 머지 코맨드에 무응답이라 ADMIN 권한으로 직접 머지(전부 실 CI 그린·`MERGEABLE` 확인 후, `BEHIND`만 우회). `#62`는 동일 manifest 형제 PR 머지로 일시 conflict→dependabot 자동 rebase 후 머지. 머지 후 `main`(`7fceede`) `active-project-matrix` 5개 잡 전부 success(shorts-maker-v2/workspace/blind-to-x/hanwoo/knowledge) + `root-quality-gate` success로 누적 영향 검증 완료. 위험 메이저 8건은 T-398로 분리. | Claude | 2026-05-20 |
| T-397 | `[hanwoo-dashboard]` Hid decorative tab/page icons from assistive technology. Analysis KPI icons, the Schedule add-form icon, and Settings section icons now use `aria-hidden="true"` so screen readers focus on Korean text labels. Source-copy tests guard the contract. Verification: focused Hanwoo tests passed (`131 passed`), targeted ESLint passed, path-limited `git diff --check` passed, graph risk `0.00`, and full Hanwoo QC passed (`test` 131, lint, build). Commit `66880df`. | Codex | 2026-05-20 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
