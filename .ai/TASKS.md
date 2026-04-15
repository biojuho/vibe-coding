# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-215 | `[workspace]` Public 전환 전 후속 보안 조치: 기존 git 이력에 있었던 Brave API key / NotebookLM 세션을 rotate 또는 revoke 하고, 공개 전환 전에 history rewrite 필요 여부를 결정 | User | P0 | 🔴 approval | 2026-04-15 |
| T-199 | `[workspace]` GitHub branch protection 설정 (main 브랜치 require CI pass) — **BLOCKED**: 2026-04-14 live check 기준 repo가 private + 무료 플랜이라 `gh api repos/biojuho/vibe-coding/branches/main/protection`가 HTTP 403. GitHub Pro 업그레이드 또는 public 전환 필요. 준비된 적용 명령: `python execution/github_branch_protection.py --apply` | User | P1 | 🔴 approval | 2026-04-14 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-213 | `[workspace]` Public 전환 전 tracked secret sanitation 완료: Brave / NotebookLM tracked secret 파일을 템플릿화하고, n8n 자격정보를 env 기반 placeholder로 치환, `knowledge-dashboard` 동기화는 `auth.local.json` 우선 사용으로 정리 | Codex | 2026-04-15 |
| T-214 | `[blind-to-x]` test_optimizations.py mock 경로 버그 수정(`pipeline.content_intelligence.rules`)으로 전체 테스트 복구 (13/13 passed) | Gemini (Antigravity) | 2026-04-15 |
| T-212 | `[workspace]` health_check optional provider/venv 상태 재분류로 shared health check `overall: ok` 달성 | Codex | 2026-04-15 |
| T-211 | `[workspace]` health_check optional env completeness 정리 (`BRAVE/BRIDGE/GitHub/Telegram/Moonshot` 누락을 optional로 분류) + 추가 테스트 2건 | Codex | 2026-04-15 |
| T-210 | `[hanwoo-dashboard]` actions.js 리팩터링 (929줄 → 12개 도메인 파일 + barrel re-export 90줄, lint/test 통과) | Gemini (Antigravity) | 2026-04-15 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto 컬럼 규칙

- `🟢 safe`: 짧은 진행 명령만으로 자동 진행 가능한 범위.
- `🔴 approval`: 사용자 확인 후 진행. 패키지 설치, DB 스키마 변경, 인증/보안 로직, 공개 API 계약 변경, 인프라/CI 변경은 항상 여기에 해당.
- `🟢 safe` 자동 진행 상한: 변경 파일 7개 이하, 순수 추가 코드 약 250줄 이하, 같은 기능/모듈 경계 내.
- `🟢 safe`가 비고 `🔴 approval`만 남으면 "남은 작업은 모두 확인이 필요합니다. 어떤 작업을 진행할까요?"로 안내.
