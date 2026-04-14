# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Codex |
| Work | **T-209 완료**: `workspace/execution/health_check.py --json`로 시스템 스크리닝을 다시 수행해 유일한 fail 원인이 `workspace/execution/pr_self_review.py`의 INDEX 누락임을 확인했다. `workspace/directives/INDEX.md`의 "매핑 없는 Execution 스크립트" 섹션에 `pr_self_review.py`를 등록해 directive mapping drift를 복구했고, 이후 `python workspace/execution/health_check.py --category governance --json`는 `overall: ok`, 전체 헬스체크는 `fail: 0`, `overall: warn`로 회복됐다. |
| Next Priorities | 1. Optional env 경고(`GROQ_API_KEY`, `MOONSHOT_API_KEY`, `BRAVE_API_KEY`, Telegram/Bridge 계열) 정리 여부 사용자 확인. 2. T-199는 여전히 사용자 승인/플랜 결정 필요. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Gemini (Antigravity) |
| Work | **T-208 완료**: `hanwoo-dashboard` 내 `premium-input.js`, `premium-button.js` 등 하위 UI 컴포넌트들에 하드코딩되어 있던 `slate` 클래스들을 `globals.css` 테마 변수로 완벽히 동기화. 1~4차 UX/UI 개선 완전 완료. Lint 오류 없음. |
| Next Priorities | 1. User의 T-199 진행 상황 체크. 2. 대기. |
| Date | 2026-04-14 |
| Tool | Codex |
| Work | **T-207 완료**: `execution/github_branch_protection.py`를 추가하고 GitHub branch protection payload를 결정론적으로 고정했다. 현재 워크플로 기준 required checks를 `root-quality-gate` + `test-summary`로 설정하고, `--check-live`/`--apply` 경로에서 repo metadata 조회, live 보호 상태 조회, private + free 플랜의 GitHub 403 블로킹 감지를 자동화했다. `workspace/tests/test_github_branch_protection.py`로 payload, repo slug 파싱, 차단 경로, apply 성공 모의를 고정하고, 2026-04-14 기준 live 호출에서도 `gh api repos/biojuho/vibe-coding/branches/main/protection`의 완전한 HTTP 403 `"Upgrade to GitHub Pro or make this repository public"` 상태를 확인. |
| Date | 2026-04-14 |
| Tool | Claude Code (Opus 4.6 1M) |
| Work | **QC pass + T-199 플랜 블로커 확인**. 최근 4건 교차 검증: T-197 `component-imports.test.mjs` (eslint 0, npm test 51/51, 네거티브 테스트로 broken import 정확 검출), T-198 `pr_self_review.py` (py_compile/ruff/--help OK), T-202 `.amazonq/mcp.json` ↔ `.mcp.json` 완전 동기화(8서버), test_mcp_config.py 3/3 통과, 부수적으로 `execution/component_import_smoke_test.py` (Python판) `--strict` 146/146 resolved + ruff clean. **T-199**는 기술 블로커: `gh api repos/biojuho/vibe-coding/branches/main/protection` → HTTP 403 `"Upgrade to GitHub Pro or make this repository public"`. private + 무료 플랜 조합으로는 branch protection API 자체가 차단됨. |
| Next Priorities | 1. **T-199 unblock 결정**: GitHub Pro 업그레이드($4/월) vs public 전환 vs 로컬 게이트(T-195/T-206) 유지. 2. Google Gemini API 403 문제 별도 확인. |

## Notes

- **T-209 변경 파일 (2026-04-15)**: `workspace/directives/INDEX.md`
- **T-209 검증 (2026-04-15)**: `python workspace/execution/health_check.py --category governance --json` -> `overall: ok`, `python workspace/execution/health_check.py --json` -> `overall: warn`, `fail: 0`
- **T-207 변경 파일 (2026-04-14)**: `execution/github_branch_protection.py` [NEW], `workspace/tests/test_github_branch_protection.py` [NEW]
- **T-207 검증 (2026-04-14)**: `python -m pytest --no-cov workspace/tests/test_github_branch_protection.py -q` -> `5 passed`
- **T-207 라이브 확인 (2026-04-14)**: `python execution/github_branch_protection.py --check-live` -> `status: blocked`, repo `biojuho/vibe-coding`, branch `main`, message `Upgrade to GitHub Pro or make this repository public to enable this feature.`
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
