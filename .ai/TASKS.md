# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-199 | `[workspace]` GitHub branch protection 설정 (main 브랜치 require CI pass) — **BLOCKED**: 2026-04-14 live check 기준 repo가 private + 무료 플랜이라 `gh api repos/biojuho/vibe-coding/branches/main/protection`가 HTTP 403. GitHub Pro 업그레이드 또는 public 전환 필요. 준비된 적용 명령: `python execution/github_branch_protection.py --apply` | User | P1 | 🔴 approval | 2026-04-14 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-212 | `[workspace]` health_check optional provider/venv 상태 재분류로 shared health check `overall: ok` 달성 | Codex | 2026-04-15 |
| T-211 | `[workspace]` health_check optional env completeness 정리 (`BRAVE/BRIDGE/GitHub/Telegram/Moonshot` 누락을 optional로 분류) + 회귀 테스트 2건 추가 | Codex | 2026-04-15 |
| T-210 | `[hanwoo-dashboard]` actions.js 리팩토링 (929줄 → 12개 도메인 파일 + barrel re-export 90줄). Lint 0 errors, 51/51 tests pass. DashboardClient는 분석 후 현행 유지 결정. | Gemini (Antigravity) | 2026-04-15 |
| T-209 | `[workspace]` shared health-check screening 후 directive mapping drift 복구 (`pr_self_review.py` INDEX 등록) | Codex | 2026-04-15 |
| T-208 | `[hanwoo-dashboard]` UX/UI 4차 개선 (premium 컴포넌트 하드코딩 제거 및 테마 동기화) | Gemini (Antigravity) | 2026-04-15 |
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite — Auto 컬럼 규칙

- `🟢 safe`: "해줘", "ㄱㄱ" 등 짧은 진행 명령만으로 자동 진행 가능. Boundary 조건 전부 충족 시에만 부여.
- `🔴 approval`: 반드시 사용자 확인 후 진행. 새 패키지 설치, DB 스키마 변경, 인증/보안 로직, 공개 API 계약 변경, 기술 스택 전환, 인프라/CI 변경 중 하나라도 해당하면 이 라벨.
- `🟢 safe` 자동 진행 상한: 변경 파일 7개 이하, 순수 추가 코드 ~250줄 이하, 같은 기능/모듈 경계 안.
- `🟢 safe` 항목이 비었고 `🔴 approval`만 남으면: "남은 작업은 모두 확인이 필요합니다" 안내 후 사용자 선택 대기.
