# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-201 | `[workspace]` Antigravity Amazon Q 재시작 후 `1.63.0` 적용 여부 확인 및 재발 시 manifest overwrite 재조사 | Any | P2 | 🟢 safe | 2026-04-14 |
| T-198 | `[workspace]` PR 셀프 리뷰 자동화 스크립트 (`git diff` -> AI 분석) | Any | P3 | 🔴 approval | 2026-04-14 |
| T-199 | `[workspace]` GitHub branch protection 설정 (main 브랜치 require CI pass) | User | P1 | 🔴 approval | 2026-04-14 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-194 | `[workspace]` Smart Continue Lite 도입 — TASKS.md 확장, AGENTS.md/GEMINI.md Boundary 규칙 삽입, plan.md 분기 추가, ADR-026 예외 조항 | Gemini | 2026-04-14 | Phase 1~3 |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-200 | `[workspace]` Antigravity Amazon Q triage: downloaded LSP `1.64.0` delist workaround 적용으로 다음 선택 버전을 `1.63.0`으로 롤백 | Codex | 2026-04-14 |
| T-197 | `hanwoo-dashboard` 컴포넌트 import smoke test — 146개 @/ import 전수 검증 + pre-commit hook 등록 | Gemini | 2026-04-14 |
| T-196 | `[workspace]` `execution/commit_scope_guard.py` — AI 과잉 수정 차단 (파일 수, 금지 영역, 위험 점수) + pre-commit hook | Gemini | 2026-04-14 |
| T-195 | `[workspace]` QC 체계 도입 — 루트 `.pre-commit-config.yaml` (ruff + file hygiene + detect-secrets), `.githooks/pre-commit` 프레임워크 통합, Dependabot auto-merge 워크플로우, 3개 프로젝트 CLAUDE.md 세션 행동 규칙 주입 | Gemini | 2026-04-14 |
| T-193 | `hanwoo-dashboard` 출하 수익성 예측(Profitability Estimator) 백엔드 로직 작성, 프론트엔드 액션 연동 및 `ProfitabilityWidget` UI 구현 완료. | Gemini | 2026-04-14 |

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
