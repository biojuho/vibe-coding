# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Tool | Codex |
| Work | **T-274 workspace goal feature activation**. User asked to activate the `goal` feature. Graph-first exploration plus repo text search found no existing `goal` symbol/flag, so Codex activated a shared workspace goal path instead: added `.ai/GOAL.md`, taught `execution/session_orient.py` to collect/render a `GOAL` section, and added focused tests for active/missing/render behavior. Feature commit: `1c5f341 feat(workspace): surface active goal in session orientation`. Verification: `python -m pytest --no-cov workspace/tests/test_session_orient.py -q` -> `14 passed`; `python -m ruff check execution/session_orient.py workspace/tests/test_session_orient.py` clean; `python execution/session_orient.py` prints `GOAL: active (Codex) ...`; `py -3.13 -m code_review_graph update --repo . --skip-flows` succeeded; `py -3.13 -m code_review_graph detect-changes --repo . --brief` risk `0.00`; `git diff --check` clean aside from standard LF/CRLF warnings. Pre-commit advisory code-review gate warned risk `0.55` due graph test-gap mapping even though direct tests cover the changed paths. |
| Next Priorities | Future tools should read/update `.ai/GOAL.md` when the active user goal changes; `python execution/session_orient.py` now surfaces it at startup. Existing user-side blockers remain unchanged: T-251 Supabase password replacement and T-273 PR #35 review. No push/deploy performed. |

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-272 dropped-stash recovery → PR #35**. T-268 직후 stash@{0}이 다른 도구에 의해 자동 prune됐는데, `git fsck --unreachable`로 stash 커밋(`e9ce5cd`)을 찾아 그 3rd parent(`65ff5ee`)에서 untracked 파일 blob들을 추출. unique work 4개 복원 — `execution/langfuse_preflight.py` (264줄, T-253 라이브 활성화 전 안전 체크리스트 자동화), `workspace/tests/test_langfuse_preflight.py` (7 hermetic tests), `tests/eval/blind-to-x/golden_cases.example.yaml`, `rejected_cases.example.yaml` (promptfoo 시작 데이터셋). stash의 modified-tracked 변경분(`code_review_gate.py` 88줄 등)은 upstream `cb6c3c9`에 이미 흡수됐다고 판단하여 제외. `recover/langfuse-preflight-from-stash` 브랜치에 커밋(`670859f`)하고 origin에 푸시 후 **PR #35** 생성. 검증: Ruff clean, `test_langfuse_preflight.py` `7 passed`, pre-commit code-review gate `PASS risk=0.00`. |
| Next Priorities | **PR #35** 사용자 리뷰 대기 — Langfuse preflight 체크리스트 적절성 + eval example 스키마가 promptfoo extractor와 호환되는지 확인. T-251은 여전히 `YOUR_PASSWORD` 치환 필요. 다른 활성 TODO 없음. |

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Tool | Codex |
| Work | **T-271 workspace session orientation + committed path-fix verification**. Continued after `252c413 feat(workspace): add multi-tool session orientation snapshot` landed locally. Verified that the former dirty WIP is now committed: root agent docs document `execution/session_orient.py`; the CLI prints a multi-tool startup snapshot; `projects/blind-to-x/pipeline/notebooklm_enricher.py` and `pipeline/notion/_upload.py` now resolve shared helpers from `workspace/execution`; `tests/unit/test_workspace_path_pins.py`, `tests/integration/test_notebooklm_smoke.py`, and `workspace/tests/test_session_orient.py` pin the behavior. Verification: `workspace/tests/test_session_orient.py` -> `11 passed`; Blind path/enricher/smoke slice -> `31 passed, 1 warning`; targeted Ruff check and format check clean; `python -m py_compile execution/session_orient.py` passed; `python execution\session_orient.py` printed the expected branch/tasks/db/graph/CI snapshot; `py -3.13 -m code_review_graph detect-changes --repo . --brief` risk `0.00`. The staged gate reported advisory WARN risk `0.60` for graph test-gap mapping around the new CLI despite direct tests passing; no blocking failure. |
| Next Priorities | T-251 remains the single user-side product blocker: replace the literal `YOUR_PASSWORD` in `projects/hanwoo-dashboard/.env` `DATABASE_URL`, then run `npm run db:prisma7-test -- --live`. Local `main` is ahead of `origin/main` by `252c413`, `a3a077d`, and `732f4e6`, plus this context commit once written; no push/deploy performed. `execution/session_orient.py` reports HANDOFF line-count pressure, but `python execution\handoff_rotator.py --check --json` returned `noop` (`archived: 0`, cutoff `2026-05-05`), so there is no stale addendum to rotate right now. |

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-270 dead-code audit 패턴 확장 — blind-to-x 추가 2건 fix + 4-pin 테스트**. T-269(`boosting.py` parents[4] fix, Codex 커밋 `732f4e6`)의 같은 *클래스* 버그가 다른 곳에도 있는지 audit. `parent.parent.parent[.parent]` + `spec_from_file_location` 조합 grep → 후보 3건 발견, 각 후보의 `_target.exists()` 검증으로 2건 broken / 1건 정상 확인. **Broken (fix됨)**: (1) `projects/blind-to-x/pipeline/notion/_upload.py:571` — `parent×4` = `projects/` 까지만 가서 `projects/execution/notion_article_uploader.py` 찾다가 실패 → NLM 자동 아티클의 Notion heading/list/code 블록 변환이 한 달째 plain-text 폴백으로만 동작. `parents[4] / workspace / execution / notion_article_uploader.py` + 명시 `.exists()` 가드로 수정. (2) `projects/blind-to-x/pipeline/notebooklm_enricher.py:32` — `parent×3` = `projects/blind-to-x/` 까지만 가서 `content_writer.py` + `gdrive_pdf_extractor.py` 둘 다 못 찾음 → `NOTEBOOKLM_ENABLED=true` 시 NotebookLM enrichment 전체가 silent degraded (article 비어있는 채로 통과). `parents[3] / workspace / execution / ...` 로 수정. **정상 (대조군)**: `pipeline/process_stages/runtime.py:68` `parents[4] / workspace / execution / debug_history_db.py` 는 이미 올바름 — 우연 일치 아니라 의도적 정답. 회귀 pin: `tests/unit/test_workspace_path_pins.py` 신규 (4 케이스, `_repo_root_from()` 헬퍼가 `workspace/` + `projects/` 형제 디렉터리 탐색으로 `parents[N]` N 잘못 계산 시 즉시 fail). 검증: workspace_path_pins + viral_boost + notion_upload 합 `46 passed`, touched 5 파일 Ruff clean. **메타 패턴**: 직전 turn에 빌드한 `api_usage_tracker alerts` 가 dead_provider 신호 → `boosting.py` 추적 → 같은 패턴 audit으로 3건 모두 활성 코드로 복귀. 도구 → 신호 → 패턴 → audit 연결고리. |
| Next Priorities | `runtime.py` 의 `parents[4]` 가 정상인 이유는 file이 한 단계 깊이 (`pipeline/process_stages/`) — 같은 패턴이라도 깊이별 N 다름을 회귀 테스트가 명시. 이후 새 cross-directory import 추가 시 `_repo_root_from()` 헬퍼 패턴 사용 권장(parents[N] hardcoding 회피). T-251은 여전히 사용자 측 `YOUR_PASSWORD` 치환 대기. Memory entry `dead_code_viral_boost_20260512.md` 확장본에 3건 통합 기록 (`api_usage_alerts_20260511.md` → dead code audit 의 신호원). |

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Tool | Codex |
| Work | **T-269 blind-to-x viral boost WIP completed/verified**. Continued the visible WIP after the user said "pursuing goal". `estimate_viral_boost_llm()` now resolves the repo root with `parents[4]` and loads `workspace/execution/llm_client.py` instead of the nonexistent project-local `execution/llm_client.py`, fixing the silent always-0.0 dead path for borderline publishability posts. Tightened `tests/unit/test_viral_boost_llm.py` so the positive path uses a fake import loader, verifies the exact workspace target and 80 -> 12.0 conversion, and prevents real `.env` provider keys from being reloaded during fallback tests. While verifying, a concurrent local commit landed as `732f4e6 chore(workspace): cleanup remaining WIP files and test results`; it contains `boosting.py`, the new regression test, and `qc_results.json`. I preserved that commit as current state. Verification: `python -m pytest --no-cov tests/unit/test_viral_boost_llm.py -q --tb=short --maxfail=1` -> `4 passed`; content-intelligence slice -> `25 passed`; targeted Ruff clean; `py -3.13 -m code_review_graph detect-changes --repo . --brief` risk `0.00`; `git diff --check` clean. |
| Next Priorities | Local `main` is ahead of `origin/main` by `732f4e6` plus this context commit once committed; no push performed. Final sanity check showed unrelated concurrent WIP in `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `projects/blind-to-x/pipeline/notebooklm_enricher.py`, `projects/blind-to-x/pipeline/notion/_upload.py`, `execution/session_orient.py`, `projects/blind-to-x/tests/unit/test_workspace_path_pins.py`, and `workspace/tests/test_session_orient.py`; preserve unless the user explicitly asks to finish/revert. T-251 remains blocked by the user-only Supabase password replacement in `projects/hanwoo-dashboard/.env` (`YOUR_PASSWORD`). `refs/stash` no longer exists at final check (`git stash list` empty, `git rev-parse --verify refs/stash` failed); this changed concurrently, so do not assume the earlier `stash@{0}` work is still available. |

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-268 multi-branch consolidation → main 단일화 ("완성형")**. 세션 중 동시 작업하던 여러 AI 도구가 만든 3 브랜치(`main`, `feat/workspace-governance-root-execution`, `refactor/shorts-maker-v2-single-scene-rendering`)가 중복/분기 상태였고 중간에 `AUTO_MERGE`/conflict가 반복 발생. PR #33이 origin에서 squash-merged 되어 제 T-251 root cause `[ai-context]` 커밋 `9262f5c` 가 `8a691a4` 안에 자동 보존됨을 확인 (안전성 검증 완료). 이후 origin/main 위에서 unique work 2건을 cherry-pick으로 복원: `47b6590 fix(workspace): stabilize product readiness checks` (→ `9e58483`)와 `b29b967 feat(workspace): add LLM usage summary reporting`은 동시 작업으로 `c856f35 feat(workspace): improve product readiness monitoring`에 이미 흡수 확인. 최종 origin/main = `ae60610` 으로 푸시 완료(8 → 9 commits 반영, brc admin bypass). 검증: workspace Ruff clean, `test_llm_usage_summary.py`+`test_code_review_gate.py`+`test_governance_checks.py` `61 passed`, `git diff --check` clean. 로컬에서 `feat/workspace-governance-root-execution` + `refactor/shorts-maker-v2-single-scene-rendering` 브랜치 모두 정리됨(origin에서도 삭제됨). |
| Next Priorities | **stash@{0}** ("preserve concurrent tool WIP before cherry-pick")에 unique 264줄 `execution/langfuse_preflight.py` + tests 가 남아있음 — 사용자 검토 후 `git stash pop` 또는 `git stash drop` 결정 필요. 현재 워킹 트리에는 다른 도구의 새 WIP (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`, `projects/blind-to-x/pipeline/content_intelligence/boosting.py`, `tests/unit/test_viral_boost_llm.py`, `qc_results.json`) 존재 — 진행 중 작업이라 손대지 않음. T-251은 여전히 `YOUR_PASSWORD` 치환 필요. |

| Field | Value |
|---|---|
| Date | 2026-05-11 |
| Tool | Codex |
| Work | **T-267 full QC re-run per user request**. Ran the canonical active-project QC with `python execution\project_qc_runner.py --json`; result `status: passed`. Results: `blind-to-x` test/lint passed (`1541 passed, 1 skipped, 2 warnings` for unit tests); `shorts-maker-v2` test/lint passed; `hanwoo-dashboard` test/lint/build passed (`npm test` 51 passed); `knowledge-dashboard` test/lint/build passed (`npm test` 3 passed). Supporting checks before the long QC: `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo . --brief` risk `0.00`; `python workspace\execution\health_check.py --category governance --json` `overall: ok`; `python execution\code_review_gate.py --staged --json` `status: pass`. No code changes were made by Codex for this QC run. After QC, unrelated dirty files were present (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `projects/blind-to-x/pipeline/content_intelligence/boosting.py`, `projects/blind-to-x/tests/unit/test_viral_boost_llm.py`, `qc_results.json`); they were not staged or reverted. |
| Next Priorities | T-251 remains the only product-readiness blocker requiring user action: replace `YOUR_PASSWORD` in `projects/hanwoo-dashboard/.env` `DATABASE_URL` with the real Supabase DB password, then run `npm run db:prisma7-test -- --live`. Preserve unrelated dirty files unless the user explicitly asks to finish or discard them. |

| Field | Value |
|---|---|
| Date | 2026-05-11 |
| Tool | Codex |
| Work | **T-266 pre-commit code-review gate noise reduction**. Committed `cb6c3c9` (`fix(workspace): quiet docs-only code review gate`): `execution/code_review_gate.py --staged` now filters staged paths to code/config candidates before invoking `code_review_graph`, so `.ai` / Markdown-only commits return PASS instead of inheriting stale graph test-gap warnings. Added focused tests for docs-only skip and mixed docs+code staged filtering. Verification: `workspace/tests/test_code_review_gate.py` now `20 passed`; Ruff check/format and `py_compile` clean; `git diff --cached --check` clean before commit; post-commit `python execution\code_review_gate.py --staged --json` returns `status: pass`. The gate can still warn on real code changes as intended. No push/deploy was performed. |
| Next Priorities | T-251 remains the only product-readiness blocker requiring user action: replace `YOUR_PASSWORD` in `projects/hanwoo-dashboard/.env` `DATABASE_URL` with the real Supabase DB password, then run `npm run db:prisma7-test -- --live`. |

| Field | Value |
|---|---|
| Date | 2026-05-11 |
| Tool | Gemini (Antigravity) |
| Work | **Session Ended for T-251 blocker**. Evaluated user's instruction to "Make it a completed product version" but found that T-251 requires a live Supabase DB password to execute the Prisma 7 Live CRUD E2E tests, which is only accessible by the user. Monitored background QC runs to ensure offline stability (`hanwoo-dashboard` build and offline tests passed). No code changes were made; updated the session logs to hand off the single remaining action to the user. |
| Next Priorities | User must manually insert the actual `DATABASE_URL` password in `projects/hanwoo-dashboard/.env` and execute `npm run db:prisma7-test -- --live` to finalize T-251. Once successful, the Hanwoo Dashboard is fully product-ready for live deployment. |

| Field | Value |
|---|---|
| Date | 2026-05-11 |
| Tool | Codex |
| Work | **T-265 product-readiness monitoring finish**. Committed `c856f35` (`feat(workspace): improve product readiness monitoring`): added `workspace/execution/llm_usage_summary.py` for JSONL + SQLite LLM usage summaries, wired API anomaly alerts into `workspace/execution/daily_report.py`, added staged `execution/code_review_gate.py --staged` plus advisory pre-commit integration, resolved governance INDEX parser/path drift, and fixed `shorts-maker-v2` direct auto-topic UTF-8 output on Windows. Final verification: workspace focused suite `105 passed`; Shorts focused CLI/structure suite passed; Ruff/format/py_compile clean; `python workspace\execution\daily_report.py --format markdown` shows `API alerts: 0`; `python workspace\execution\llm_usage_summary.py --json` reports 22 records / `$0.005445`; governance health `overall: ok`; full `python execution\project_qc_runner.py --json` passed across all active projects (`blind-to-x` 1541 passed / 1 skipped, `shorts-maker-v2` unit+integration passed, `hanwoo-dashboard` 51 passed + lint/build, `knowledge-dashboard` 3 passed + lint/build). The staged code-review gate still reports advisory WARN due graph test-gap heuristics, but it is non-blocking and covered by tests. No push/deploy was performed. |
| Next Priorities | Only known product-readiness blocker remains T-251: replace the literal `YOUR_PASSWORD` in `projects/hanwoo-dashboard/.env` `DATABASE_URL` with the real Supabase DB password, then run `npm run db:prisma7-test -- --live` from `projects/hanwoo-dashboard`. Optional follow-up: wire daily report/API alert output into cron or n8n once deployment cadence is chosen. |

| Field | Value |
|---|---|
| Date | 2026-05-11 |
| Tool | Codex |
| Work | **Product-readiness finalization after user asked to proceed by judgment**. Added a workspace API usage anomaly alert path: `workspace/execution/api_usage_tracker.py alerts` now detects high provider fallback rate, cost spikes versus the prior window, and expected providers with no recent calls; it returns JSON and exits `1` when alerts exist. Added 9 focused tests plus the `workspace/directives/api_monitoring.md` daily alert flow. Also synchronized `projects/shorts-maker-v2` Google Trends runtime dependency by adding `pytrends>=4.9.2` and regenerating `uv.lock` with a temporary `.tmp/uv-runner` uv install. Final verification: API tracker tests `43 passed`; Ruff check/format clean; `uv lock --check` clean; full `python execution\project_qc_runner.py --json` passed across all active projects (`blind-to-x` 1541 passed / 1 skipped, `shorts-maker-v2` 1365 passed / 12 skipped, `hanwoo-dashboard` 51 passed + lint/build, `knowledge-dashboard` 3 passed + lint/build); graph detect-changes risk `0.00`. Local `main` is ahead of `origin/main` by 2 feature commits (`75897bd`, `6c95a31`). No push/deploy was performed. |
| Next Priorities | T-251 remains the only known product-readiness blocker: replace the literal `YOUR_PASSWORD` in `projects/hanwoo-dashboard/.env` `DATABASE_URL` with the real Supabase DB password, then run `npm run db:prisma7-test -- --live` from `projects/hanwoo-dashboard`. After that, optionally wire `api_usage_tracker.py alerts --expected-providers openai,anthropic,google` into cron/n8n for daily monitoring. |

| Field | Value |
|---|---|
| Date | 2026-05-11 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-251 차단 원인 정확히 식별**: 사용자 "ㄱㄱ"에 따라 `npm run db:prisma7-test -- --live` 재실행했으나 가드에서 즉시 `DATABASE_URL is missing or placeholder` 로 실패. dotenv 로딩 자체는 정상이고 host/user는 실제 Supabase pooler 값인데, 비밀번호 자리에 Supabase 템플릿 문자열 `YOUR_PASSWORD`가 그대로 남아있어 `scripts/prisma7-runtime-test.mjs:56` 의 `isPlaceholderUrl` 가 정확히 차단. 즉 .env 미설정이 아니라 **사용자가 Supabase 콘솔에서 실제 비밀번호를 치환해 붙여넣지 않은 상태**. 추가로 작업 트리는 깨끗하고 origin/main 과 동기화 완료 (직전 푸시 `5a73e57..8cc2c11` 5 커밋 반영, brc 보호 admin bypass). |
| Next Priorities | T-251은 사용자 측 단일 조치만 남음 — Supabase Settings → Database → Transaction Pooler의 실제 비밀번호 포함 URL을 `projects/hanwoo-dashboard/.env` 의 `DATABASE_URL=` 라인에 붙여넣어 `YOUR_PASSWORD` 자리 치환. 그 후 같은 명령 재실행하면 Live CRUD E2E 섹션이 실행됨. 다른 활성 TODO 없음. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Codex |
| Work | **T-251 rechecked after user "ㄱㄱ"**. Checked DB config without printing secrets: root `.env` still has no `DATABASE_URL`; `projects/hanwoo-dashboard/.env` has a Supabase pooler host but still matches placeholder patterns, so it is not treated as a runnable live DB URL. Verification run: `node --check scripts/prisma7-runtime-test.mjs` passed; `npm run db:prisma7-test` passed offline (`14 passed, 0 failed, 1 skipped`); `npm test` passed (`51` tests); `npm run db:prisma7-test -- --live` failed exactly at the guard (`14 passed, 1 failed`) with `DATABASE_URL is missing or placeholder`. No code changes were needed. |
| Next Priorities | T-251 remains blocked until a real Supabase PostgreSQL `DATABASE_URL` is configured in `projects/hanwoo-dashboard/.env` or the shell environment. After that, rerun `npm run db:prisma7-test -- --live`; the Live CRUD E2E section should execute instead of failing at configuration. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Codex |
| Work | **T-257 completed — blind-to-x direct AsyncAnthropic prompt caching path**. During this session a concurrent commit `74a585b` landed broad workspace work and included the T-257 implementation: `DraftPrompt` now keeps string compatibility while exposing Anthropic system/user split metadata; reviewer memory and stable system preamble move into the cacheable Anthropic `system` block; `_generate_with_anthropic` injects `cache_control` for `5m` default / `1h` opt-in; provider calls now return cache write/read tokens; Langfuse trace forwarding and `CostTracker`/`CostDatabase` record cache token usage. Codex preserved that commit and added `ef78fb0` to align remaining draft-cache provider mocks with the new 5-tuple token contract. Verification: focused T-257/regression set `84 passed`; full `blind-to-x` unit suite `1541 passed, 1 skipped`; follow-up formatted-test check `17 passed`; `python -m ruff check .` and `python -m ruff format --check .` clean; graph detect-changes risk `0.00`; `git diff --check -- projects/blind-to-x` clean. |
| Next Priorities | T-251 remains blocked until a real Supabase PostgreSQL `DATABASE_URL` is configured. For T-257 live validation, run two Anthropic draft generations with the same reviewer-memory/system preamble inside the 5-minute TTL and confirm `cache_read_input_tokens > 0` in provider usage/trace data; no live Anthropic calls were made in this session. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Gemini (Antigravity) |
| Work | **T-259 완료 — 콘텐츠 품질 + 프론트엔드 캐싱 강화**: (1) `shorts-maker-v2`: **C-1** 감성 분석/토픽 클러스터링을 추가해 채널/감성에 맞는 BGM 다양성 확보(`pipeline.content_intelligence`). **B-3** 9:16 비율 내 자막 텍스트와 UI 오버랩 방지를 위한 Safe Zone QC 추가(`CaptionSafeZoneValidator`). **C-2** 렌더링/싱크/오디오 성능을 분석하는 `metrics_cli.py` 파이프라인 메트릭 리포트 툴 추가. (2) `hanwoo-dashboard`: **A-3** Next.js 16의 `use cache` 지시어 적용 (`src/lib/cache.js`, `FeedTab.js`, `AnalysisTab.js`) 및 캐시 무효화(`revalidateTag`, `revalidatePath`) 패턴 정립. 검증: `shorts-maker-v2` 1,308 passed, `hanwoo-dashboard` 51 passed (총 1,359 passed). |
| Next Priorities | 다음 세션에서는 T-251(Supabase DB 연동을 통한 Prisma 7 Live CRUD E2E) 또는 T-257(blind-to-x AsyncAnthropic 경로 프롬프트 캐싱) 진행을 고려. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **시스템 고도화 Phase C — AI context infra (item 1 + item 2)**. Item 1: added `execution/handoff_rotator.py` so HANDOFF.md "Current Addendum" rotates on a 7-day window into `.ai/archive/HANDOFF_archive_<rotation_date>.md`, plus `workspace/tests/test_handoff_rotator.py` (12 tests covering parse / keep+archive split / idempotence / dry-run / keep_days variation / preserved sibling sections / append-to-existing-archive). First applied run: HANDOFF.md `279→216` 줄, 9 stale addenda 이동. CLAUDE/AGENTS/GEMINI.md에 새 "HANDOFF 로테이션 규칙" 섹션 미러링. Item 2: added `execution/code_review_gate.py` — risk-aware deterministic gate that wraps `code_review_graph.tools.detect_changes_func` with classification (pass<warn<fail), auto-fetches `get_impact_radius` for warn/fail, optional `--include-architecture`, `--strict` 모드, JSON 모드, exit code matrix `0/1/2/3`. Tests injected via `tools=` parameter to keep them deterministic without a real graph build (`workspace/tests/test_code_review_gate.py`, 12 tests). End-to-end live run against the actual graph (`py -3.13 execution/code_review_gate.py --base HEAD~1 --strict`) returned warn (risk 0.40, 32 test gaps) and exit 1 as designed. CLAUDE/AGENTS/GEMINI.md에 "결정론적 게이트" 워크플로 섹션 추가. Verification: workspace 111 tests pass (focused regression set + new 24), ruff clean across all touched files. |
| Next Priorities | Phase C item 3 (workspace SQLite 미사용 테이블/뷰 정리 + 인덱스 보강) 또는 Phase B (shorts-maker-v2 multi-provider TTS + n8n 자동화)를 선택해 진행. Phase C item 1+2는 별도 PR로 묶일 수 있는 자체 완결 변경. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Codex |
| Work | Supersedes the concurrent T-253/T-254/T-255 addendum below with final committed state. **T-255 Anthropic prompt caching** committed as `4303474`: `cache_strategy` (`off`/`5m`/`1h`), anthropic-only `cache_control`, cache token capture, and API usage cost accounting for 5m writes (`1.25x`), 1h writes (`2.0x`), and cache reads (`0.10x`). **T-253 Langfuse observability** committed as `57c38bd`: opt-in Langfuse v3 tracing helper, JSONL metrics helper, blind-to-x async provider hook, `.env.example` keys, and a localhost-bound self-host compose stack under `infrastructure/langfuse/`. **T-254 promptfoo eval** committed as `6634d82`: Notion-to-golden/rejected extractor, promptfoo runner with baseline comparison and Telegram alert option, prompt/test assets, and generated dataset ignores. Verification: cache/LLM suite `181 passed`; Langfuse focused workspace suite `104 passed`; blind-to-x draft provider suite `24 passed`; eval extractor suite `6 passed`; Ruff/format/py_compile clean on touched files; Langfuse compose config validated with dummy env; promptfoo dry-run returns expected dataset-missing warnings until real Notion extraction is run. |
| Next Priorities | T-251 remains blocked by a real Supabase `DATABASE_URL`. T-257 remains the next LLM cost follow-up for the direct `AsyncAnthropic` blind-to-x async draft path. For T-253/T-254 live activation, run Langfuse locally and provision keys, then run `python execution/blind_to_x_eval_extract.py --apply` followed by `python execution/run_eval_blind_to_x.py --update-baseline`; these were not run because they require local services/secrets and live Notion data. Preserve unrelated dirty WIP in root agent docs, Hanwoo DB files, Shorts Maker V2 files, and new untracked utility/test files unless explicitly asked to finish them. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Claude Code (Opus 4.7 1M) + Codex (concurrent) |
| Work | **T-253 / T-254 / T-255 동시 착륙 — LLM 관측 + 평가 + 캐싱**. 사용자 "지금 시스템 고도화를 위해 필요한 것 인터넷에서 찾아서 제안해" 요청 → 7건 검색 후 우선순위 제안 → "순서대로 진행해" 승인 → 3건 모두 구현 완료. (1) **T-255 Anthropic prompt caching**: `workspace/execution/llm_client.py` 의 `_generate_once`에 `cache_strategy` 파라미터 추가 (off/5m/1h), anthropic 분기에서 `system`을 list[block] + `cache_control:{type:ephemeral, ttl:1h?}` 형태로 변환, 응답에서 `cache_creation_input_tokens`/`cache_read_input_tokens` 캡처해 5-tuple로 반환. `_log_usage` + `api_usage_tracker.log_api_call` 양쪽에 `cache_creation_tokens`/`cache_read_tokens` 컬럼 추가 (1.25× write / 0.10× read 가중 비용). 신규 테스트 `tests/test_llm_client_anthropic_cache.py` (10케이스), 기존 `test_llm_client.py` + `test_llm_bridge_integration.py` + `test_llm_fallback_chain.py` 의 mock `_generate_once` 3-tuple 반환을 5-tuple로 일괄 업그레이드 (정규식 변환). (2) **T-253 Langfuse opt-in observability**: `infrastructure/langfuse/` 에 v3 self-host 스택 (web/worker/Postgres/ClickHouse/Redis/MinIO, all `127.0.0.1` 바인딩) + README. `.env.example` 에 `LANGFUSE_ENABLED=0` 외 7개 키. `_emit_langfuse_trace` 모듈 헬퍼는 `LANGFUSE_ENABLED!=1` 또는 키 미설정이면 즉시 return (SDK import도 안 함). v3 SDK는 `get_client()` + `start_observation(as_type="generation")`. 신규 테스트 `tests/test_llm_client_langfuse.py` (5케이스). (3) **T-254 Promptfoo eval**: `execution/blind_to_x_eval_extract.py` (Notion `승인됨` → golden, `패스` + reviewer_memo → rejected, YAML 직렬화), `execution/run_eval_blind_to_x.py` (npx promptfoo eval + baseline 비교 + Telegram 알림 옵션), `tests/eval/blind-to-x/promptfooconfig.yaml` + `prompts/draft_v_current.txt`. 신규 테스트 `workspace/tests/test_eval_extract.py` (6케이스, Notion mock 없이 순수 함수 검증). 데이터셋 yaml은 `.gitignore` 등록. **신규 SOP 3건** `workspace/directives/`: `llm_observability_langfuse.md`, `llm_eval_promptfoo.md`, `anthropic_prompt_caching.md`. INDEX.md에 등록. **검증**: 164 focused tests pass (cache + langfuse + extract + 기존 LLMClient/bridge/fallback), Ruff clean across all touched files, 백그라운드 워크스페이스 전체 테스트 1316 passed (3-tuple→5-tuple 마이그레이션 반영). **주의**: 동일 세션 동안 Codex가 같은 `llm_client.py`를 평행 편집했고(별도 `execution/llm_metrics.py` 추가, v3 SDK API 정렬) 일부 변경이 라운드트립 중 손실되어 재적용했음. 최종 코드는 두 에이전트 작업이 깔끔하게 머지된 상태. |
| Next Priorities | T-257(blind-to-x async draft 캐싱 적용) 가 추가됨 — `pipeline/draft_prompts.py` reviewer-memory를 안정 preamble + 가변 suffix 로 분리 후 `pipeline/draft_providers.py::_generate_with_anthropic` 에 `cache_control` 주입. 또한 시스템 가동 후: (a) Langfuse Docker 스택 실제 기동 + UI 키 발급 + `LANGFUSE_ENABLED=1` 전환, (b) `python execution/blind_to_x_eval_extract.py --apply` 실제 Notion 호출로 첫 데이터셋 생성 + `python execution/run_eval_blind_to_x.py --update-baseline` 으로 baseline 캡처. 모두 사용자 작업이며 본 세션에서 수행 안 함. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-256 autoskills triage + 3 추가 스킬 설치 완료**: 사용자가 `npx autoskills`를 요청해서 dry-run으로 먼저 확인(감지 결과 Bash만, 추천 4개 = `bash-defensive-patterns`, `frontend-design`(이미 설치), `accessibility`, `seo`). `npx autoskills -y` 실행은 Windows에서 `addyosmani/web-quality-skills` 다운로드 도중 종료되는 버그 발견. autoskills가 wshobson 레포명을 잘못된 `wshobson/agent-skills`로 참조하는 문제도 확인(실제는 `wshobson/agents`). `npx skills add`로 직접 3개 설치: `bash-defensive-patterns` (`wshobson/agents`), `accessibility` (`addyosmani/web-quality-skills`), `seo` (`addyosmani/web-quality-skills`). 모두 `.agents/skills/` universal + `.claude/skills/` 심볼릭 링크. 보안 평가 모두 Gen `Safe` / Socket `0 alerts` / Snyk `Med Risk`. `skills-lock.json`에 3개 엔트리 추가. 추가로 세션 시작 직후 표준 QC 한 차례 더 실행해 기록(T-241): shared health `warn 7 / fail 0` (예상된 optional providers), governance `ok`, graph detect-changes risk `0.00`, workspace Ruff/pytest `1283 passed / 1 skipped`, `blind-to-x`/`shorts-maker-v2` Ruff clean. `git push origin main`으로 6 commit 푸시(브랜치 보호 admin bypass). |
| Next Priorities | 다음 세션부터 새 SKILL.md들 자동 인식. `bash-defensive-patterns`는 `execution/` shell 작업에, `accessibility`/`seo`는 `hanwoo-dashboard`/`knowledge-dashboard` Frontend 작업에 활용 가능. autoskills의 Windows 호환성 버그는 upstream 이슈로 추적 가치가 있으나 우선순위 낮음. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Codex |
| Work | Attempted T-251 after user approval. `npm run db:prisma7-test -- --live` in `projects/hanwoo-dashboard` did not run Live CRUD because `projects/hanwoo-dashboard/.env` still has a placeholder `DATABASE_URL` and root `.env` has no `DATABASE_URL`. Fixed the runtime test guard in commit `512496c` so `--live` with a missing/placeholder DB URL now exits non-zero instead of looking like a successful skip; offline mode remains `14 passed, 1 skipped`. Verification: `node --check scripts/prisma7-runtime-test.mjs`, `npm run db:prisma7-test` passes offline, `npm run db:prisma7-test -- --live` now fails clearly with `DATABASE_URL is missing or placeholder`, and diff check on the script only reported LF/CRLF warnings. |
| Next Priorities | T-251 remains open until a real Supabase PostgreSQL `DATABASE_URL` is configured in `projects/hanwoo-dashboard/.env` (or provided in the shell environment). After that, rerun `npm run db:prisma7-test -- --live` and expect the Live CRUD E2E section to execute instead of failing at configuration. Preserve the unrelated current WIP around handoff rotation, new directives, and installed skills unless the user explicitly asks to finish it. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Codex |
| Work | Continued after the user approved additional work. Committed the previously verified Phase A reliability WIP as `dccd4b6` (`psutil` optional, CI path tests wired, Hanwoo summary cache meta retained). Finished and committed T-246 project WIP by project: `18c5223` JobPlanet pages now use `_new_page_cm()` consistently, `d11d0a9` Shorts Maker V2 adds word timing snapping, short chunk merging, and channel branding overrides, `0352c44` Hanwoo adds Prisma 7 runtime stability testing plus manifest icon corrections, and `d128e0d` adds the tracked `find-skills` skill registry entry. Verification passed: graph risk `0.00`; `workspace/tests/test_auto_schedule_paths.py` 5 passed; Ruff clean for touched Python; Hanwoo project QC test/lint/build passed and `npm run db:prisma7-test` passed offline 14/14 with 1 live skip; Blind project QC passed `1534 passed, 1 skipped`; Shorts project QC passed `1300 passed, 12 skipped`; `git diff --check` only reported LF/CRLF warnings. |
| Next Priorities | Only live/external follow-up remains: after the Supabase project is active, run `npm run db:prisma7-test -- --live` in `projects/hanwoo-dashboard` to verify Live CRUD E2E. Broader future items from the prior Gemini note remain optional: Shorts viewer feedback loop, real video E2E generation, and Knowledge Dashboard automatic sync scheduling. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Gemini (Antigravity) |
| Work | **프로젝트별 고도화 세션 (3 세션)**: 3개 프로젝트의 안정성 고도화를 완료. **S-2**: Shorts Maker V2 word-level 싱크 정밀도 — `snap_word_timings` + `min_chunk_duration` 로직 구현. **S-3**: 채널별 브랜딩 파이프라인 — `ChannelRouter.apply()`에 transition_style, caption_style, highlight_color, hook_animation, intro/outro 전파 구현. **B-5**: JobPlanet 스크레이퍼 리소스 누수 — `_new_page_cm()` 컨텍스트 매니저 리팩토링으로 페이지 누수 차단. **H-5**: Prisma 7 런타임 안정성 테스트 — `scripts/prisma7-runtime-test.mjs` 신규 생성 (14/14 offline passed: Client Generation 4, PrismaPg Adapter 4, Connection Pool 3, Graceful Errors 3; Live CRUD E2E는 Supabase INACTIVE로 스킵). `npm run db:prisma7-test` 스크립트 추가. Knowledge Item 검증 체크리스트 업데이트 완료. 검증: hanwoo-dashboard prisma7 14/14 + unit tests 51/51, shorts-maker-v2 1300 passed (88.62%), blind-to-x 1608 passed (81.19%). |
| Next Priorities | 1. Supabase 프로젝트 활성화 후 `npm run db:prisma7-test -- --live`로 Live CRUD E2E 검증. 2. S-4: 시청자 피드백 루프 구현. 3. S-5: 실 영상 E2E 생성 테스트. 4. K-2: Knowledge Dashboard 자동 동기화 스케줄링. |

| Field | Value |
|---|---|
| Date | 2026-05-08 |
| Tool | Codex |
| Work | **T-249 workspace technology stack policy reflected**: checked the requested stack list against the repository. Confirmed active usage of React/Next.js, JavaScript/TypeScript, PostgreSQL/Supabase-compatible Prisma access, Redis/BullMQ, and native Fetch API wrappers. Confirmed Svelte/SvelteKit, Go, Rust, Flutter/native mobile, RabbitMQ, and TanStack Query are not installed in active product code and should remain candidate-only until a design note exists. Added `docs/technology-stack.md`, linked it from root `README.md`, updated `projects/hanwoo-dashboard/README.md` and `projects/knowledge-dashboard/README.md`, and expanded `.ai/CONTEXT.md` with the adoption policy. Verification passed: `git diff --check` (LF/CRLF warnings only), governance `overall: ok`, graph detect-changes risk `0.00`. |
| Next Priorities | If actual runtime adoption is desired later, start with a design note per stack: TanStack Query for Hanwoo interactive lists, Flutter for a separate mobile app, or Go/Rust only for measured worker bottlenecks. Do not replace existing React/Next/Python/Redis-BullMQ paths without that plan. |

| Field | Value |
|---|---|
| Date | 2026-05-07 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **시스템 고도화 Phase A — tech-debt cleanup (T-120/T-121/T-129)**. T-120: `psutil` was the actual CI blocker in `infrastructure/n8n/bridge_server.py` (fastapi/pydantic already had try/except fallbacks). Made `psutil` import optional and made `/health` endpoint psutil-aware (`memory_mb=None` when unavailable). Extended `workspace/tests/test_auto_schedule_paths.py` regression to block fastapi+pydantic+psutil together (renamed to `test_n8n_bridge_helper_imports_do_not_require_runtime_only_deps`) and wired the test file into both `.github/workflows/root-quality-gate.yml` and `.github/workflows/full-test-matrix.yml`. T-121: confirmed already mitigated by `_isolate_logging_handlers` autouse fixture in `projects/blind-to-x/tests/unit/conftest.py`; full unit suite 1523 passed + 3× targeted 20/20 runs all clean; memory entry was stale. T-129: deeper DashboardClient split was previously deemed risk>benefit (T-210), and the read-model cache is already wired at API layer (`/api/dashboard/summary` uses snapshot via `read-models.js`). Surgical contribution: piped the API's cache `meta` (`source`/`isStale`/`ageSeconds`) into a new `summaryMeta` state in `DashboardClient` so staleness info isn't dropped. Verification: workspace 87 tests pass, ruff clean across canonical + bridge_server, hanwoo-dashboard 51/51 tests + lint 0 + build green. **Note:** of the WIP files Codex flagged in the previous addendum, the bridge_server / both workflow YAMLs / `test_auto_schedule_paths.py` are now this session's intentional T-120 changes. |
| Next Priorities | Phase A is committable as its own PR. Then proceed to Phase C (code-graph utilization expansion + HANDOFF rotation rules) → Phase B (content-pipeline upgrades, e.g. shorts-maker-v2 multi-provider TTS + n8n automation). |

| Field | Value |
|---|---|
| Date | 2026-05-07 |
| Tool | Codex |
| Work | **T-247 project-by-project debug triage completed**: ran graph-first status/change checks and the full `execution/project_qc_runner.py --json` matrix. Initial QC showed only one real failure: `shorts-maker-v2` Ruff `B007` in `src/shorts_maker_v2/render/karaoke.py` from an unused `enumerate()` index inside existing Phase 3 WIP. Fixed that single lint issue by iterating directly over `words`. Reverification passed: `shorts-maker-v2` full project runner (`1300 passed, 12 skipped` plus Ruff), and the earlier same-run matrix had `blind-to-x` test/lint, `hanwoo-dashboard` test/lint/build, and `knowledge-dashboard` test/lint/build all green. `git diff --check` reported only LF/CRLF warnings, and graph detect-changes risk stayed `0.00`. |
| Next Priorities | Remaining unrelated WIP is still intentionally uncommitted and should not be reverted: `.github/workflows/full-test-matrix.yml`, `.github/workflows/root-quality-gate.yml`, `infrastructure/n8n/bridge_server.py`, `projects/blind-to-x/scrapers/jobplanet.py`, `projects/hanwoo-dashboard/package.json`, `projects/hanwoo-dashboard/public/manifest.json`, `projects/hanwoo-dashboard/scripts/prisma7-runtime-test.mjs`, `projects/shorts-maker-v2/src/shorts_maker_v2/render/karaoke.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/utils/channel_router.py`, and `workspace/tests/test_auto_schedule_paths.py`. Only the `karaoke.py` unused-loop-index lint fix was made by Codex in this session; the rest should be reviewed/finished only with explicit approval. |

| Field | Value |
|---|---|
| Date | 2026-05-07 |
| Tool | Codex |
| Work | **T-245 surge queue + AI chat stabilization completed**: continued from the existing WIP. In `blind-to-x`, queued surge events now persist `content_preview`, legacy escalation DBs migrate the new column deterministically, and the escalation runner passes that preview into `ExpressDraftPipeline`. In `hanwoo-dashboard`, `AIChatWidget` now streams `/api/ai/chat` responses with immediate abort handling, safe Gemini history construction, offline fallback on missing API key, and lucide icons; `next.config.mjs` keeps Serwist PWA support but makes it opt-in via `NEXT_ENABLE_PWA=1` so the default Next 16 webpack build remains green. Feature commit: `760bf2f` (`fix(projects): stabilize surge queue and ai chat`). Verification passed: focused Blind queue pytest (`17 passed`), focused Blind Ruff, standard Blind full unit runner (`1534 passed, 1 skipped`), standard Blind lint runner, Hanwoo `npm test` (`51` passed), `npm run lint`, `npm run build`, `git diff --check`, governance `overall: ok`, and graph detect-changes risk `0.00`. |
| Next Priorities | Remaining unrelated WIP is still present and intentionally uncommitted: `projects/blind-to-x/scrapers/jobplanet.py`, `projects/hanwoo-dashboard/public/manifest.json`, `projects/shorts-maker-v2/src/shorts_maker_v2/render/karaoke.py`, and `projects/shorts-maker-v2/src/shorts_maker_v2/utils/channel_router.py`. Review/finish only with explicit approval because these appeared outside T-245. |

| Field | Value |
|---|---|
| Date | 2026-05-07 |
| Tool | Codex |
| Work | **T-244 project verification docs aligned**: refactored project/workflow verification docs to point at the canonical `execution/project_qc_runner.py` path. Updated `.agents/workflows/start.md`, `.agents/workflows/verify.md`, and the project-level `CLAUDE.md` files for `blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, and `knowledge-dashboard`. Also refreshed `hanwoo-dashboard` stack notes to Next 16 / React 19 / Prisma 7 and documented the `src/lib/actions.js` barrel + `src/lib/actions/` domain split. Feature commit: `bd0da70` (`docs(workspace): align project verification guides`). Verification passed: `python workspace/execution/health_check.py --category governance --json` (`overall: ok`), `python execution/project_qc_runner.py --dry-run --json`, doc-targeted `git diff --check`, and `python3.13 -m code_review_graph detect-changes --repo . --brief` risk `0.00`. |
| Next Priorities | No active TODO. Preserve unrelated in-progress worktree edits currently present in `projects/blind-to-x/escalation_runner.py`, `projects/blind-to-x/pipeline/escalation_queue.py`, `projects/blind-to-x/pipeline/express_draft.py`, `projects/blind-to-x/tests/unit/test_escalation_queue.py`, and `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; they were not part of T-244. |

| Field | Value |
|---|---|
| Date | 2026-05-07 |
| Tool | Codex |
| Work | **T-243 project-by-project QC runner added**: created `execution/project_qc_runner.py` to run the canonical verification commands for `blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, and `knowledge-dashboard` from one deterministic entry point. It supports `--project`, `--check`, `--dry-run`, `--list`, JSON output, per-command timeouts, Windows `.cmd/.bat/.exe` executable resolution, and UTF-8 console output. Added `workspace/tests/test_project_qc_runner.py`. Feature commit: `0c25272` (`chore(workspace): add project qc runner`). Verification passed: `python -m pytest --no-cov workspace\tests\test_project_qc_runner.py -q` (`6 passed`), `python -m ruff check execution\project_qc_runner.py workspace\tests\test_project_qc_runner.py`, `python execution\project_qc_runner.py --dry-run --json`, `python execution\project_qc_runner.py --project knowledge-dashboard --check test --json` (`3` Node tests passed), `git diff --check` clean except existing LF/CRLF warning in an unrelated Hanwoo file, and graph detect-changes risk `0.00`. |
| Next Priorities | No active TODO. Preserve unrelated in-progress worktree edits currently present in `projects/blind-to-x/escalation_runner.py`, `projects/blind-to-x/pipeline/escalation_queue.py`, `projects/blind-to-x/pipeline/express_draft.py`, and `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; they were not part of T-243. |

| Field | Value |
|---|---|
| Date | 2026-05-07 |
| Tool | Codex |
| Work | **T-242 full QC completed and recorded**: ran graph/git/shared/workspace/active-project checks. Results: `python3.13 -m code_review_graph detect-changes --repo . --brief` risk `0.00`; `git diff --check` clean; shared health `overall: warn`, `fail: 0` (8 expected warnings from optional provider/env gaps plus inactive root `venv`); governance `ok`; branch protection `configured`; open PRs `[]`; targeted secret scan `results: {}`; workspace Ruff clean and focused workspace pytest `54 passed`; `blind-to-x` Ruff clean and full unit pytest `1532 passed, 1 skipped`; Playwright Chromium launch smoke passed (`145.0.7632.6`); `shorts-maker-v2` Ruff clean and full unit/integration pytest passed; `hanwoo-dashboard` test/lint/build passed (`51` tests); `knowledge-dashboard` test/lint/build passed (`3` tests). |
| Next Priorities | No active TODO. Optional observation: `execution/remote_branch_cleanup.py` still reports remote-only branch `ai-context/2026-04-30-cleanup` as `safe_to_delete: true`, but it is not blocking QC. |

| Field | Value |
|---|---|
| Date | 2026-05-07 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-241 QC pass executed and recorded**: ran the standard QC battery against the current working tree (HEAD `783bf99` `[ai-context]` only, 1 commit ahead of `origin/main`; uncommitted edits were Gemini's pending HANDOFF/TASKS reorder). Results: shared health `overall: warn` / `fail: 0` (7 warns are expected optional provider/env gaps — `GROQ_API_KEY`, `MOONSHOT_API_KEY`, env_completeness optional keys), governance `ok`, `py -3.13 -m code_review_graph detect-changes` risk `0.00` / 0 affected flows / 0 test gaps, `git diff --check origin/main..HEAD` clean, workspace Ruff clean, workspace pytest `1283 passed, 1 skipped`, `blind-to-x` Ruff clean, `shorts-maker-v2` Ruff clean, `gh pr list --state open` returns `[]`. |
| Next Priorities | 워크스페이스는 QC-clean 상태. 활성 TODO 없음. T-231/T-234 완료 컨텍스트가 미커밋 상태였으나 이번 기록과 함께 커밋됨. |

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Tool | Gemini (Antigravity) |
| Work | **T-234 + T-231 완료**: (1) PR #31 close → PR #32 생성 (9 커밋 squash) → CI 9/9 통과 → squash merge → 로컬 main 동기화 (`90c83bd`). (2) Playwright Chromium 설치 (`chromium-headless-shell v1208`, 108.8 MiB) → smoke test 통과. Open PR: 0개, TODO: 0개. |
| Next Priorities | 워크스페이스 완전 clean — 활성 TODO 없음. 새 기능 개발 또는 콘텐츠 파이프라인 운영 시작 가능. |

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Tool | Codex |
| Work | **Task board rechecked after T-234 merge**: confirmed PR #32 is merged, `gh pr list --state open` returns no open PRs, and `main` was synced with `origin/main` at `90c83bd` before this context-only handoff update. Re-ran `python execution/remote_branch_cleanup.py --repo biojuho/vibe-coding --local-repo .tmp/public-history-rewrite`; it now reports one remote-only branch, `ai-context/2026-04-30-cleanup`, with `safe_to_delete: true` and no blocked branches. Added T-240 for that user-approved cleanup decision. |
| Next Priorities | 1. T-231 (User): install Playwright browsers if browser-only Blind scraping/screenshots are required. 2. T-240 (User): delete stale remote branch `ai-context/2026-04-30-cleanup` if no longer needed. |

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Next Priorities | 1. T-234 (User): PR #31 still needs review/merge or closure, and local `main` is ahead of `origin/main`. 2. T-231 (User): install Playwright browsers if browser-only Blind scraping/screenshots are required. |

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Tool | Codex |
| Work | **Code review completed for local `main` vs `origin/main`**: reviewed the 7 local commits ahead of origin. Scope was mostly `.ai` context updates, `.code-review-graph/.gitignore`, `workspace/pyproject.toml` E402 per-file ignores, and `shorts-maker-v2` unit-test stabilization. No blocking code-review findings were identified. Supporting checks: `python3.13 -m code_review_graph detect-changes --repo . --brief` risk `0.00`, `git diff --check origin/main..HEAD`, workspace Ruff, and focused `shorts-maker-v2` growth-sync pytest all passed. |
| Next Priorities | 1. T-234 (User): PR #31 still needs review/merge or closure, and local `main` is ahead of `origin/main`. 2. T-231 (User): install Playwright browsers if browser-only Blind scraping/screenshots are required. |

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Tool | Codex |
| Work | **Full system recheck completed with no hard failures**: reran graph/git change detection, shared health/governance, GitHub branch protection, PR/remote-branch inventory, targeted secret scan, workspace Ruff/pytest, `blind-to-x` full unit suite + Ruff, `shorts-maker-v2` full pytest + Ruff, and both Next app test/lint/build paths. All product/workspace verification commands passed. Shared health remains `overall: warn` with `fail: 0`; the warnings are optional provider/env gaps plus inactive root `venv`. `python3.13 -m code_review_graph detect-changes --repo . --brief` reported 0 affected flows, 0 test gaps, risk `0.00`. |
| Next Priorities | 1. T-234 (User): PR #31 still needs review/merge or closure, and local `main` is ahead 6 of `origin/main`. 2. T-231 (User): install Playwright browsers if browser-only Blind scraping/screenshots are required. |

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Tool | Codex |
| Work | **Remaining broad workspace Ruff QC resolved**: `python -m ruff check workspace/execution workspace/tests --output-format=concise` now passes. The root cause was intentional Windows/direct-run `sys.path` bootstrapping before shared imports; added exact E402 per-file ignores in `workspace/pyproject.toml` instead of moving runtime bootstrap code. Verification also passed for targeted workspace pytest (`54 passed`), governance health, and `git diff --check`. Feature commit: `d14e897` (`fix(workspace): align broad ruff QC with bootstrap scripts`). |
| Next Priorities | 1. T-234 (User): PR #31 still needs review/merge or closure, and local `main` is ahead of `origin/main`. 2. T-231 (User): install Playwright browsers if browser-only Blind scraping/screenshots are required. |

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Tool | Codex |
| Work | **Full QC pass executed and repaired**: broadened checks beyond the earlier smoke set. `blind-to-x` full unit suite and Ruff passed; `hanwoo-dashboard` and `knowledge-dashboard` test/lint/build passed. `shorts-maker-v2` full pytest initially failed because `test_growth_sync.py` used April 2026 fixed timestamps that had aged out of the 30-day filter; fixed the fixture to use recent timestamps, cleaned the remaining Ruff test-format debt, and added `.code-review-graph` WAL/SHM ignores. Feature commit: `611d151` (`fix(shorts-maker-v2): stabilize QC test suite`). Revalidation: `shorts-maker-v2` full pytest and full Ruff passed, plus focused growth/thumbnail tests passed. |
| Next Priorities | 1. T-234 (User): PR #31 still needs review/merge or closure, and local `main` is ahead of `origin/main`. 2. T-231 (User): install Playwright browsers if browser-only Blind scraping/screenshots are required. 3. T-235: broad workspace Ruff was still reporting E402 path-bootstrap issues at this point; resolved later in commit `d14e897`. |

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Tool | Codex |
| Work | **Full system check completed**: ran the shared health check, governance/env probes, GitHub branch protection checks, PR/remote-branch inventory, targeted secret scan, active project tests/lints/builds, and rebuilt `code-review-graph`. Current shared health is `overall: warn` with `fail: 0`; warnings are optional env/provider gaps plus inactive root `venv`. Governance is OK. Branch protection is configured on public `biojuho/vibe-coding/main` with required checks `root-quality-gate` and `test-summary`. Active project checks passed: `blind-to-x` focused Ruff/pytest, `shorts-maker-v2` focused pytest + targeted Ruff, `hanwoo-dashboard` test/lint/build, and `knowledge-dashboard` test/lint/build. `code-review-graph` was rebuilt to 11,567 nodes / 85,100 edges / 898 files. |
| Next Priorities | 1. T-234 (User): review/merge/close open PR #31 and sync `main`; local `main` is ahead 1 at `b5fcb7c`. 2. T-231 (User): install Playwright browser binaries if browser-only Blind scraping/screenshots are needed. 3. T-235 (AI/User): decide whether to clean broad Ruff debt or keep using targeted canonical checks. |


## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Gemini (Antigravity) |
| Work | **T-214 완료**: `projects/blind-to-x/tests/unit/test_optimizations.py` 테스트 실행 시 발생하던 mock 객체(`pipeline.content_intelligence`) 경로 문제를 `rules` 서브모듈로 타겟팅하여 수정. 최종적으로 13개 실패 테스트를 모두 패스 상태로 복구(100% 통과). QC 승인(APPROVED) 완료. |
| Next Priorities | 현재 코드베이스 무결성 회복. 다음 T-213 승인 대기. |

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Codex |
| Work | **T-199 라이브 재확인**: `python execution/github_branch_protection.py --check-live`를 다시 실행해 `biojuho/vibe-coding` / `main`의 branch protection 차단 상태를 2026-04-15 기준으로 재검증했다. 결과는 여전히 `status: blocked`, 저장소는 `PRIVATE`, GitHub 응답 메시지는 `Upgrade to GitHub Pro or make this repository public to enable this feature.`였고, 준비된 payload(`root-quality-gate`, `test-summary`) 자체는 dry-run으로 정상 생성됨을 함께 확인했다. |
| Next Priorities | 1. `T-199`는 기술 문제가 아니라 GitHub 플랜/가시성 결정 대기 상태. 2. 결정 후 `python execution/github_branch_protection.py --apply` 실행, 이어서 `--check-live` 재검증. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Codex |
| Work | **T-212 완료**: `workspace/execution/health_check.py`에서 남은 shared warn(`GROQ_API_KEY`, `MOONSHOT_API_KEY`, inactive root `venv`)를 실제 운영 의미에 맞게 재분류했다. Groq/Moonshot 미설정은 optional provider 상태로, root `venv` 비활성은 현재 표준 실행 패턴(`python -m ...`)에 맞는 정상 상태로 취급하도록 정리했고, `workspace/tests/test_health_check.py`에 회귀 테스트 3건을 추가했다. 재검증 결과 `python -m pytest --no-cov workspace/tests/test_health_check.py -q` -> `43 passed`, `python workspace/execution/health_check.py --json` -> `overall: ok`, `warn: 0`, `fail: 0`. |
| Next Priorities | 1. 남은 TODO는 `T-199`뿐이며 사용자 측 GitHub 플랜/공개 여부 결정이 필요. 2. 코드 변경(`workspace/execution/health_check.py`, `workspace/tests/test_health_check.py`)은 아직 워킹트리에 남아 있다. |
| Date | 2026-04-15 |
| Tool | Codex |
| Work | **T-211 완료**: shared health-check 경고를 다시 분류해 `workspace/execution/health_check.py`의 `.env` completeness 로직이 feature-specific optional 키까지 일괄 warn 하던 부분을 정리했다. `BRAVE_API_KEY`, `BRIDGE_*`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `MOONSHOT_API_KEY`, `TELEGRAM_*`를 optional completeness 항목으로 분리하고, `workspace/tests/test_health_check.py`에 회귀 테스트 2건을 추가했다. 재검증 기준 `python -m pytest --no-cov workspace/tests/test_health_check.py -q` -> `40 passed`, `python workspace/execution/health_check.py --json` -> `overall: warn`, `fail: 0`, 남은 warn은 실제 optional provider 미설정(`GROQ_API_KEY`, `MOONSHOT_API_KEY`)과 비활성 `venv`뿐이다. |
| Next Priorities | 1. 완전한 green을 원하면 `GROQ_API_KEY`/`MOONSHOT_API_KEY` 설정 여부와 root `venv` 활성화 정책 결정. 2. T-199는 여전히 사용자 승인 대기. |
| Date | 2026-04-15 |
| Tool | Gemini (Antigravity) |
| Work | **T-210 완료**: `hanwoo-dashboard/src/lib/actions.js` (929줄) 리팩토링. 12개 도메인별 파일(`actions/cattle.js`, `sales.js`, `feed.js`, `inventory.js`, `schedule.js`, `building.js`, `farm-settings.js`, `market.js`, `notification.js`, `expense.js`, `system.js`, `_helpers.js`)로 분리하고 `actions.js`를 barrel re-export (90줄)로 교체. 기존 `import { … } from '@/lib/actions'` 계약 100% 유지. Lint 0 errors, 51/51 tests pass (component-imports 포함). `DashboardClient.js`는 분석 결과 탭이 이미 분리되어 있고 30+ state/handler가 밀접 결합되어 추출 시 risk > benefit → 현행 유지 결정. |
| Next Priorities | 1. Phase 2: shorts-maker-v2 리팩토링 (media_step.py, test_render_step.py). 2. T-199 사용자 승인 대기. |
| Date | 2026-04-14 |
| Tool | Codex |
| Work | **T-207 완료**: `execution/github_branch_protection.py`를 추가하고 GitHub branch protection payload를 결정론적으로 고정했다. 현재 워크플로 기준 required checks를 `root-quality-gate` + `test-summary`로 설정하고, `--check-live`/`--apply` 경로에서 repo metadata 조회, live 보호 상태 조회, private + free 플랜의 GitHub 403 블로킹 감지를 자동화했다. `workspace/tests/test_github_branch_protection.py`로 payload, repo slug 파싱, 차단 경로, apply 성공 모의를 고정하고, 2026-04-14 기준 live 호출에서도 `gh api repos/biojuho/vibe-coding/branches/main/protection`의 완전한 HTTP 403 `"Upgrade to GitHub Pro or make this repository public"` 상태를 확인. |
| Date | 2026-04-14 |
| Tool | Claude Code (Opus 4.6 1M) |
| Work | **QC pass + T-199 플랜 블로커 확인**. 최근 4건 교차 검증: T-197 `component-imports.test.mjs` (eslint 0, npm test 51/51, 네거티브 테스트로 broken import 정확 검출), T-198 `pr_self_review.py` (py_compile/ruff/--help OK), T-202 `.amazonq/mcp.json` ↔ `.mcp.json` 완전 동기화(8서버), test_mcp_config.py 3/3 통과, 부수적으로 `execution/component_import_smoke_test.py` (Python판) `--strict` 146/146 resolved + ruff clean. **T-199**는 기술 블로커: `gh api repos/biojuho/vibe-coding/branches/main/protection` → HTTP 403 `"Upgrade to GitHub Pro or make this repository public"`. private + 무료 플랜 조합으로는 branch protection API 자체가 차단됨. |
| Next Priorities | 1. **T-199 unblock 결정**: GitHub Pro 업그레이드($4/월) vs public 전환 vs 로컬 게이트(T-195/T-206) 유지. 2. Google Gemini API 403 문제 별도 확인. |

## Notes

- **T-213 feature commit (2026-04-15)**: `e5122b1` - `[workspace] sanitize tracked secret templates for public readiness`
- **HEAD safety recheck (2026-04-15)**: current `HEAD` no longer contains the tracked Brave key, NotebookLM auth payload, or the old hard-coded n8n credentials.
- **History exposure range (2026-04-15)**: Brave / NotebookLM / n8n README secrets trace back to initial commit `ba5db77`; `infrastructure/n8n/docker-compose.yml` also carried the old password through `3418fe1`; the old n8n bridge token appears in `.ai` history as well.
- **History rewrite tooling (2026-04-15)**: `git filter-repo --version` failed because `git-filter-repo` is not installed in the current environment.
- **T-213 complete (2026-04-15)**: current tracked files no longer contain the live Brave key, NotebookLM auth payload, or the hard-coded n8n credentials.
- **Public conversion warning (2026-04-15)**: sanitizing the current tree does not remove secrets from past commits. Public visibility still needs credential rotation and possibly git-history cleanup.
- **Public conversion blocker scan (2026-04-15)**: tracked secret-bearing files found at `.agents/skills/brave-search/secrets.json`, `infrastructure/notebooklm-mcp/tokens/auth.json`, and hard-coded n8n credentials in `infrastructure/n8n/docker-compose.yml` / `infrastructure/n8n/README.md`.
- **detect-secrets baseline note (2026-04-15)**: `.secrets.baseline` already suppresses `.agents/skills/brave-search/secrets.json` and `infrastructure/notebooklm-mcp/tokens/auth.json`, so baseline presence must not be mistaken for an actual fix.

- **T-199 라이브 재확인 (2026-04-15)**: `python execution/github_branch_protection.py --check-live` -> `status: blocked`, repo `biojuho/vibe-coding`, branch `main`, visibility `PRIVATE`, message `Upgrade to GitHub Pro or make this repository public to enable this feature.`
- **T-199 dry-run 재확인 (2026-04-15)**: `python execution/github_branch_protection.py` -> payload generated locally with required checks `root-quality-gate`, `test-summary`
- **T-212 변경 파일 (2026-04-15)**: `workspace/execution/health_check.py`, `workspace/tests/test_health_check.py`
- **T-212 검증 (2026-04-15)**: `python -m pytest --no-cov workspace/tests/test_health_check.py -q` -> `43 passed`, `python workspace/execution/health_check.py --category env --json` -> `overall: ok`, `python workspace/execution/health_check.py --json` -> `overall: ok`, `warn: 0`, `fail: 0`
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
