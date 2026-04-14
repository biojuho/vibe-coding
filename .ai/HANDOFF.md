# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-14 |
| Tool | Claude Code (Opus 4.6 1M) |
| Work | **QC pass + T-199 플랜 블로커 확인**. 최근 4건 교차 검증: T-197 `component-imports.test.mjs` (eslint 0, npm test 51/51, 네거티브 테스트로 broken import 정확 검출), T-198 `pr_self_review.py` (py_compile/ruff/--help OK), T-202 `.amazonq/mcp.json` ↔ `.mcp.json` 완전 동기화(8서버), test_mcp_config.py 3/3 통과, 부수적으로 `execution/component_import_smoke_test.py` (Python판) `--strict` 146/146 resolved + ruff clean. **T-199**는 기술 블로커: `gh api repos/biojuho/vibe-coding/branches/main/protection` → HTTP 403 `"Upgrade to GitHub Pro or make this repository public"`. private + 무료 플랜 조합으로는 branch protection API 자체가 차단됨. |
| Next Priorities | 1. **T-199 unblock 결정**: GitHub Pro 업그레이드($4/월) vs public 전환 vs 로컬 게이트(T-195/T-206) 유지. 2. Google Gemini API 403 문제 별도 확인. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-14 |
| Tool | Codex |
| Work | **T-206 완료**: `[ai-context]` spillover 재발 방지 가드 추가. `execution/ai_context_guard.py`와 `.githooks/commit-msg`를 만들어 context-only 커밋에 비문맥 파일이 섞이면 커밋 자체를 차단하도록 했고, `workspace/tests/test_ai_context_guard.py`로 허용/차단/BOM/훅 배선 케이스를 고정했다. |
| Next Priorities | 1. **T-199** GitHub branch protection (Owner: User). 2. Google Gemini API 403 문제 별도 확인. |

## Notes

- **T-206 변경 파일 (2026-04-14)**: `execution/ai_context_guard.py` [NEW], `.githooks/commit-msg` [NEW], `workspace/tests/test_ai_context_guard.py` [NEW]
- **T-206 검증 (2026-04-14)**: `python -m pytest --no-cov workspace/tests/test_ai_context_guard.py -q` -> `5 passed`. 샘플 실행에서 `[ai-context]` + `projects/hanwoo-dashboard/package.json` 조합은 exit 1로 차단, 일반 커밋 메시지는 exit 0 통과 확인.
- **T-205 기록 메모 (2026-04-14)**: `execution/component_import_smoke_test.py`는 현재 unstaged 상태이며, 다음 context-only 커밋 spillover 방지 목적의 조치다.
- **T-205 남은 dirty 파일 (2026-04-14)**: `projects/hanwoo-dashboard/package.json`, `execution/component_import_smoke_test.py`, `.ai/archive/SESSION_LOG_before_2026-03-23.md`는 작업트리 변경이 남아 있다. 이번 기록 작업에서는 의도적으로 미정리.
- **T-204 변경 파일 (2026-04-14)**: `tests/unit/test_render_step.py` (sys.modules 주입 헬퍼 + 2개 테스트 수정), `tests/unit/test_render_step_phase5.py` (sys.modules 주입 헬퍼 + 2개 테스트 수정), `tests/unit/test_thumbnail_step_sweep.py` (load_default mock 추가)
- **T-203 변경 파일 (2026-04-14)**: `.ai/archive/SESSION_LOG_before_2026-03-23.md` [RESTORED]
- **T-203 판단 메모 (2026-04-14)**: `projects/hanwoo-dashboard/package.json`은 현재 HEAD 이후 추가 작업트리 수정이 남아 있어, accidental commit cleanup 과정에서도 의도적으로 건드리지 않음.
- **T-202 변경 파일 (2026-04-14)**: `.amazonq/mcp.json` [NEW], `workspace/tests/test_mcp_config.py`
- **T-202 검증 (2026-04-14)**: `workspace/tests/test_mcp_config.py` 3개 테스트 통과. Antigravity 로그 `20260414T202420/.../Amazon Q Logs.log` 에서 `.amazonq/mcp.json` 기반 MCP 서버 8개 로드 확인.
- **T-198 변경 파일 (2026-04-14)**: `workspace/execution/pr_self_review.py` [NEW]
- **T-194 변경 파일 (2026-04-14)**: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (Smart Continue Lite Boundary 규칙 삽입), `.agents/workflows/plan.md` (safe/approval 분기 추가)
- **T-201 검증 (2026-04-14)**: Amazon Q 로그 `serverInfo.version: 1.63.0`, auth connection valid.
- **Google Gemini API (2026-04-14)**: `GOOGLE_API_KEY` 사용 시 403 PERMISSION_DENIED 발생. 프로젝트 액세스 거부. LLMClient fallback으로 DeepSeek 등 다른 프로바이더에서 정상 동작.
- **T-190 세션 로그 검색 도구 (2026-04-13)**:
  - 스크립트: `execution/session_log_search.py` (stdlib only, FTS5)
  - 인덱스: `.tmp/session_log_search.db`
- The local Python 3.13 `code-review-graph` package on this machine now has an unversioned UTF-8 patch in `site-packages`.
- `projects/blind-to-x/tests/unit/conftest.py` now clears `NOTION_DATABASE_ID` and any `NOTION_PROP_*` overrides before each unit test.
- UTF-8 markdown files in `.ai/` and `workspace/directives/` are fine on disk; earlier garbling came from the Windows cp949 console path, not file corruption.
- Do not revert unrelated in-progress edits elsewhere in the worktree.
