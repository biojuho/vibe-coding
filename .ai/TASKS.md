# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-199 | `[workspace]` GitHub branch protection 설정 (main 브랜치 require CI pass) — **BLOCKED**: repo가 private + 무료 플랜이라 `gh api repos/biojuho/vibe-coding/branches/main/protection` HTTP 403. GitHub Pro 업그레이드 또는 public 전환 필요. 로컬 pre-commit(T-195)이 현재 유일한 강제 게이트. | User | P1 | 🔴 approval | 2026-04-14 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-206 | `[workspace]` `[ai-context]` commit spillover guard 추가 — commit-msg hook + deterministic guard script + 회귀 테스트 | Codex | 2026-04-14 |
| T-205 | `[workspace]` spillover 상태 기록 — helper script unstage, 남은 dirty 경계 문서화 | Codex | 2026-04-14 |
| T-204 | `[shorts-maker-v2]` 5건 테스트 실패 수정 — ShortsFactory sys.modules 주입 + Pillow load_default mock 추가. 1,300 passed, 0 failed | Gemini (Antigravity) | 2026-04-14 |
| T-203 | `[workspace]` accidental `ai-context` spillover 정리 — archived session log 삭제 복구, 충돌 위험 파일은 보류 | Codex | 2026-04-14 |
| T-202 | `[workspace]` Amazon Q IDE MCP legacy workspace config 복구 — `.amazonq/mcp.json` 추가, 회귀 테스트 보강, 라이브 로그에서 MCP 서버 8개 로드 확인 | Codex | 2026-04-14 |

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
