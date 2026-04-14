# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Codex |
| Work | **T-211 완료**: shared health-check 경고를 다시 분류해 `workspace/execution/health_check.py`의 `.env` completeness 로직이 feature-specific optional 키까지 일괄 warn 하던 부분을 정리했다. `BRAVE_API_KEY`, `BRIDGE_*`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `MOONSHOT_API_KEY`, `TELEGRAM_*`를 optional completeness 항목으로 분리하고, `workspace/tests/test_health_check.py`에 회귀 테스트 2건을 추가했다. 재검증 기준 `python -m pytest --no-cov workspace/tests/test_health_check.py -q` -> `40 passed`, `python workspace/execution/health_check.py --json` -> `overall: warn`, `fail: 0`, 남은 warn은 실제 optional provider 미설정(`GROQ_API_KEY`, `MOONSHOT_API_KEY`)과 비활성 `venv`뿐이다. |
| Next Priorities | 1. 완전한 green을 원하면 `GROQ_API_KEY`/`MOONSHOT_API_KEY` 설정 여부와 root `venv` 활성화 정책 결정. 2. T-199는 여전히 사용자 승인 대기. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Gemini (Antigravity) |
| Work | **T-210 완료**: `hanwoo-dashboard/src/lib/actions.js` (929줄) 리팩토링. 12개 도메인별 파일(`actions/cattle.js`, `sales.js`, `feed.js`, `inventory.js`, `schedule.js`, `building.js`, `farm-settings.js`, `market.js`, `notification.js`, `expense.js`, `system.js`, `_helpers.js`)로 분리하고 `actions.js`를 barrel re-export (90줄)로 교체. 기존 `import { … } from '@/lib/actions'` 계약 100% 유지. Lint 0 errors, 51/51 tests pass (component-imports 포함). `DashboardClient.js`는 분석 결과 탭이 이미 분리되어 있고 30+ state/handler가 밀접 결합되어 추출 시 risk > benefit → 현행 유지 결정. |
| Next Priorities | 1. Phase 2: shorts-maker-v2 리팩토링 (media_step.py, test_render_step.py). 2. T-199 사용자 승인 대기. |
| Date | 2026-04-15 |
| Tool | Codex |
| Work | **T-209 완료**: `workspace/execution/health_check.py --json`로 시스템 스크리닝을 다시 수행해 유일한 fail 원인이 `workspace/execution/pr_self_review.py`의 INDEX 누락임을 확인했다. directive mapping drift 복구 후 `overall: warn`, `fail: 0`로 회복. |
| Next Priorities | 1. Optional env 경고 정리 여부 사용자 확인. 2. T-199는 여전히 사용자 승인/플랜 결정 필요. |
| Date | 2026-04-14 |
| Tool | Codex |
| Work | **T-207 완료**: `execution/github_branch_protection.py`를 추가하고 GitHub branch protection payload를 결정론적으로 고정했다. 현재 워크플로 기준 required checks를 `root-quality-gate` + `test-summary`로 설정하고, `--check-live`/`--apply` 경로에서 repo metadata 조회, live 보호 상태 조회, private + free 플랜의 GitHub 403 블로킹 감지를 자동화했다. `workspace/tests/test_github_branch_protection.py`로 payload, repo slug 파싱, 차단 경로, apply 성공 모의를 고정하고, 2026-04-14 기준 live 호출에서도 `gh api repos/biojuho/vibe-coding/branches/main/protection`의 완전한 HTTP 403 `"Upgrade to GitHub Pro or make this repository public"` 상태를 확인. |
| Date | 2026-04-14 |
| Tool | Claude Code (Opus 4.6 1M) |
| Work | **QC pass + T-199 플랜 블로커 확인**. 최근 4건 교차 검증: T-197 `component-imports.test.mjs` (eslint 0, npm test 51/51, 네거티브 테스트로 broken import 정확 검출), T-198 `pr_self_review.py` (py_compile/ruff/--help OK), T-202 `.amazonq/mcp.json` ↔ `.mcp.json` 완전 동기화(8서버), test_mcp_config.py 3/3 통과, 부수적으로 `execution/component_import_smoke_test.py` (Python판) `--strict` 146/146 resolved + ruff clean. **T-199**는 기술 블로커: `gh api repos/biojuho/vibe-coding/branches/main/protection` → HTTP 403 `"Upgrade to GitHub Pro or make this repository public"`. private + 무료 플랜 조합으로는 branch protection API 자체가 차단됨. |
| Next Priorities | 1. **T-199 unblock 결정**: GitHub Pro 업그레이드($4/월) vs public 전환 vs 로컬 게이트(T-195/T-206) 유지. 2. Google Gemini API 403 문제 별도 확인. |

## Notes

- **T-211 변경 파일 (2026-04-15)**: `workspace/execution/health_check.py`, `workspace/tests/test_health_check.py`
- **T-211 검증 (2026-04-15)**: `python -m pytest --no-cov workspace/tests/test_health_check.py -q` -> `40 passed`, `python workspace/execution/health_check.py --category env --json` -> `overall: warn`, `python workspace/execution/health_check.py --json` -> `overall: warn`, `fail: 0`
- **T-210 변경 파일 (2026-04-15)**: `projects/hanwoo-dashboard/src/lib/actions.js` [OVERWRITE→barrel], `projects/hanwoo-dashboard/src/lib/actions/_helpers.js` [NEW], `actions/cattle.js` [NEW], `actions/sales.js` [NEW], `actions/feed.js` [NEW], `actions/inventory.js` [NEW], `actions/schedule.js` [NEW], `actions/building.js` [NEW], `actions/farm-settings.js` [NEW], `actions/market.js` [NEW], `actions/notification.js` [NEW], `actions/expense.js` [NEW], `actions/system.js` [NEW]
- **T-210 검증 (2026-04-15)**: `npm run lint` → exit 0 (0 errors), `npm test` → 51/51 pass
- **T-210 DashboardClient 판단 (2026-04-15)**: 1,184줄이지만 탭 7개 이미 분리됨. 30+ state + pagination hooks가 밀접 결합 → 핸들러 추출 시 오히려 복잡도 증가. 현행 유지.
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
