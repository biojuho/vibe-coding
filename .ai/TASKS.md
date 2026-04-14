# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-199 | `[workspace]` GitHub branch protection 설정 (main 브랜치 require CI pass) | User | P1 | 🔴 approval | 2026-04-14 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-202 | `[workspace]` Amazon Q IDE MCP legacy workspace config 복구 — `.amazonq/mcp.json` 추가, 회귀 테스트 보강, 라이브 로그에서 MCP 서버 8개 로드 확인 | Codex | 2026-04-14 |
| T-198 | `[workspace]` PR 셀프 리뷰 자동화 스크립트 — `execution/pr_self_review.py` (LLMClient 재사용, quick/standard/deep 3단계) | Gemini (Antigravity) | 2026-04-14 |
| T-201 | `[workspace]` Antigravity Amazon Q 재시작 후 `1.63.0` 적용 확인 — 로그에서 `serverInfo.version: 1.63.0` 확인 완료 | Gemini (Antigravity) | 2026-04-14 |
| T-194 | `[workspace]` Smart Continue Lite 도입 — TASKS.md Auto 컬럼, CLAUDE/AGENTS/GEMINI.md Boundary 규칙, plan.md 분기 추가 완료 | Gemini (Antigravity) | 2026-04-14 |
| T-200 | `[workspace]` Antigravity Amazon Q triage: downloaded LSP `1.64.0` delist workaround 적용으로 다음 선택 버전을 `1.63.0`으로 롤백 | Codex | 2026-04-14 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite — Auto 컬럼 규칙

- `🟢 safe`: "해줘", "ㄱㄱ" 등 짧은 진행 명령만으로 자동 진행 가능. Boundary 조건 전부 충족 시에만 부여.
- `🔴 approval`: 반드시 사용자 확인 후 진행. 새 패키지 설치, DB 스키마 변경, 인증/보안 로직, 공개 API 계약 변경, 기술 스택 전환, 인프라/CI 변경 중 하나라도 해당하면 이 라벨.
- `🟢 safe` 자동 진행 상한: 변경 파일 7개 이하, 순수 추가 코드 ~250줄 이하, 같은 기능/모듈 경계 안.
- `🟢 safe` 항목이 비었고 `🔴 approval`만 남으면: "남은 작업은 모두 확인이 필요합니다" 안내 후 사용자 선택 대기.
