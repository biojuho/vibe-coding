# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|
| T-191 | `.ai/archive/SESSION_LOG_before_2026-03-23.md` 파일 인코딩 손상(em dash→`??`, 한글 double-encode). git 히스토리에서 원본 복원 또는 삭제 결정 필요. | Any | Low | 2026-04-13 |
| T-192 | `.claude/` gitignore 정책 재검토 — `/search-log` 등 슬래시 커맨드를 팀/멀티툴 공유하려면 `!.claude/commands/**` 예외 추가 검토. | Any | Low | 2026-04-13 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-190 | `[workspace]` claude-mem 도입 대안으로 `execution/session_log_search.py` (SQLite FTS5) 신규 + `/search-log` 슬래시 커맨드 + SessionStart 자동 reindex 훅. 듀얼 파서(테이블 + 헤딩 3종 구분자), `normalize_query` 자동 인용, 142 엔트리 인덱싱, py_compile/ruff/한글 쿼리 전부 통과. | Claude Code | 2026-04-13 |
| T-189 | `hanwoo-dashboard` 브라우저 자동화 환경 복구 (Playwright `0xc0000005` Access Violation) - Node 우회 스크립트로 해결 | Gemini | 2026-04-13 |
| T-161 | `hanwoo-dashboard` UX/UI polish pass + QC (PremiumCard clay, alert banners CSS 변수 전환, footer 접근성, dead code 제거) | Gemini | 2026-04-13 |
| T-188 | [`blind-to-x`] Clean up the remaining `tests/unit/test_process.py` lint issue after the timeout-targeting edits and re-verify the focused process tests. | Codex | 2026-04-11 |
| T-187 | [`workspace`] Patch the local `code-review-graph` Python 3.13 package for UTF-8-safe file and git subprocess handling so `detect-changes` no longer crashes on Windows `cp949`. | Codex | 2026-04-11 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
