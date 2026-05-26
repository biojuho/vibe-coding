# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-20 with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed (`15 passed`) but live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |


## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|


## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-410 | `[workspace]` Update and refresh all system/project-level agent skills. Manually updated 4 project-level locked skills (`accessibility`, `bash-defensive-patterns`, `find-skills`, `seo`) using raw node CLI execution to bypass Windows `spawnSync` shell-concat path space issues. Successfully updated `bash-defensive-patterns` to the latest upstream commit (hash updated in `skills-lock.json`). Cloned/copied all 9 latest `nature-*` academic, citation, polishing, and writing skills from the `nature-skills` submodule into `.agents/skills/` so they are natively available across all agent layers. | Gemini (Antigravity) | 2026-05-26 |
| T-409 | `[workspace]` 모노레포 전체 MCP 서버 통합 진단 및 헬스 체크 시스템 완료. 에이전트 환경의 Notion MCP 연동성 검사(Desk Joopark 계정 PASS), 윈도우 인코딩 오류(CP949) 방어력을 갖춘 `execution/mcp_diagnostic.py` 자동화 스크립트 신설 및 구문, 의존성 임포트, JSON-RPC Stdio Handshake를 통한 로컬 MCP 서버 6종(sqlite-multi, system-monitor, telegram, cloudinary, youtube-data, n8n-workflow)의 100% 정상 작동 검증 및 종합 진단 보고서(`docs/mcp_status_report.md`) 발급 완료. | Gemini (Antigravity) | 2026-05-26 |
| T-703 | `[hanwoo-dashboard]` Dashboard runtime resilience polish. Wired the existing premium `ErrorBoundary` around `DashboardClient` in `src/app/page.js` and added a regression test so client-render failures surface the recoverable fallback instead of blanking the dashboard. Verified 282/282 tests, eslint, and Next production build. | Codex | 2026-05-26 |
| T-702 | `[hanwoo-dashboard]` Field Mode accessibility polish. Added accessible labels for field-mode exit/search/clear controls, exposed checklist progress as ARIA progressbar, and added checklist toggle pressed/state labels without touching existing shorts-maker-v2 dirty files. | Codex | 2026-05-26 |
| T-408 | `[workspace/blind-to-x/shorts-maker-v2]` 모노레포 누적 5개 프로젝트 기술 부채(Technical Debt) 해결. .ai/ 문서들 다이어트 및 stale 로그 제거. llm_client.py 헬퍼 통합 중복 제거, shorts-maker-v2 text_engine 렌더 전략 분리 및 데모 프롬프트 JSON 외부화, blind-to-x Phase 2 품질 게이트(상투어 및 의미 중복 감지) 장착 및 best_of_n 연동. 모노레포 전체 유닛 테스트 100% 그린 패스 완료. | Gemini (Antigravity) | 2026-05-26 |

| T-372 | `[workspace]` Monorepo Migration Cleanup. Successfully resolved all pending monorepo alignment tasks: removed legacy lockfiles, restored Prisma postinstall client generation hooks, and ran Biome automatic lint auto-formatting sweeps (`biome check --write .`) in advisory mode at the root. Validated that all 1,598 project-wide unit tests are 100% green and Next.js static pages compile successfully. | Gemini (Antigravity) | 2026-05-22 |
