# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-14 |
| Tool | Codex |
| Work | **T-203 완료**: 직전 `ai-context` 커밋 정리. 실수로 섞여 들어간 `.ai/archive/SESSION_LOG_before_2026-03-23.md` 삭제를 복구했다. 반면 `projects/hanwoo-dashboard/package.json`은 이미 HEAD 이후 추가 작업트리 수정이 있어 사용자 변경을 덮을 위험이 확인되어 이번 정리 대상에서 제외했다. |
| Next Priorities | 1. **T-199** GitHub branch protection (Owner: User -- 사용자 직접 설정). 2. Google Gemini API 403 문제 별도 확인. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-14 |
| Tool | Codex |
| Work | **T-202 완료**: Amazon Q IDE MCP 경로 문제 해결. 루트 `.mcp.json`을 Amazon Q가 실제로 읽는 워크스페이스 레거시 경로 `.amazonq/mcp.json`으로 미러링하고, `workspace/tests/test_mcp_config.py`에 동기화 회귀 테스트를 추가. 이어서 `~/.aws/amazonq/agents/default.json` 타임스탬프 갱신으로 라이브 재초기화를 유도했고, 최신 Antigravity 로그에서 `.amazonq/mcp.json`로부터 8개 MCP 서버를 로드하고 초기화하는 것까지 확인. |
| Next Priorities | 1. **T-199** GitHub branch protection (Owner: User -- 사용자 직접 설정). 2. Google Gemini API 403 문제 별도 확인. |

## Notes

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
