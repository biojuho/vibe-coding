# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
|---|---|---|---|---|---|
| T-215 | `[workspace]` Public 전환 전 후속 보안 조치: 기존 git 이력에 있었던 Brave API key / NotebookLM 세션을 rotate 또는 revoke 하고, 공개 전환 전에 history 편집 필요 여부를 결정 | User | P0 | 🔴 approval | 2026-04-15 |
| T-199 | `[workspace]` GitHub branch protection 설정 (main 브랜치 require CI pass) — **BLOCKED**: 2026-04-14 live check 기준 repo가 private + 무료 플랜이라 HTTP 403. | User | P1 | 🔴 approval | 2026-04-14 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-217 | `[blind-to-x]` `main.py` 분리 리팩터링 완료 확인: `pipeline/cli.py`, `runner.py`, `bootstrap.py`로 역할 분리 + `test_main.py` 20/20 passed | Gemini (Antigravity) | 2026-04-15 |
| T-219 | `[blind-to-x]` Pydantic V2 마이그레이션: `fetch_stage.py`의 `.dict()` → `.model_dump()` 전환, deprecation warning 제거 (61 tests passed) | Gemini (Antigravity) | 2026-04-15 |
| T-218 | `[blind-to-x]` `blind_scraper.py` import 에러 수정 + `test_main.py` monkeypatch 경로 갱신 (1484 tests passed) | Gemini (Antigravity) | 2026-04-15 |
| T-216 | `[hanwoo-dashboard]` 기술 부채 해결 (Phase 1): `useCursorPagination` 추상화를 통한 `useCattle/useSales` 중복 로직 90% 제거 | Gemini (Antigravity) | 2026-04-15 |
| T-213 | `[workspace]` Public 전환 전 tracked secret sanitation 완료 | Codex | 2026-04-15 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto 컬럼 규칙

- `🟢 safe`: 짧은 진행 명령만으로 자동 진행 가능한 범위.
- `🔴 approval`: 사용자 확인 후 진행. 패키지 설치, DB 스키마 변경, 인증/보안 로직, 공개 API 계약 변경, 인프라/CI 변경은 항상 여기에 해당.
- `🟢 safe` 자동 진행 상한: 변경 파일 7개 이하, 순수 추가 코드 약 250줄 이하, 같은 기능/모듈 경계 내.
- `🟢 safe`가 비고 `🔴 approval`만 남으면 "남은 작업은 모두 확인이 필요합니다. 어떤 작업을 진행할까요?"로 안내.
