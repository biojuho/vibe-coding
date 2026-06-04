# SESSION_LOG

> Recent 7-day AI session history. Older entries are preserved in Git history or `.ai/archive/`.

| Date | Tool | Summary | Changed Files |
|---|---|---|---|
| 2026-06-04 | Codex | **T-1208 workspace control-plane rotation hardening**. Rotated oversized `HANDOFF.md` with the existing handoff rotator (`archived=458`, `kept=73`), added deterministic `session_log_rotator.py` with focused tests, and rotated `.ai/SESSION_LOG.md` (`archived_table_rows=241`, `archived_detail_sections=218`, cutoff `2026-05-28`). Verification: `python -m pytest workspace/tests/test_session_log_rotator.py -q` passed 10/10, `python -m py_compile execution/session_log_rotator.py` passed, and post-rotation dry-runs returned noop. | `execution/session_log_rotator.py`; `workspace/tests/test_session_log_rotator.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/archive/HANDOFF_archive_2026-06-04.md`; `.ai/archive/SESSION_LOG_before_2026-05-28.md` |
| 2026-06-04 | Claude Opus 4.8 (1M context) | **T-1207 /goal "프로젝트 완성품화" → knowledge-dashboard 선택 → 출시 가능 v1.0.0**. 7개 프로젝트 평가 후 knowledge-dashboard 선정(사용자 확정, 완성 기준 "기능 완전+출시 가능"). 출시 차단 버그 3건+신뢰성 공백 해소: ① **mojibake** — `page.tsx`의 cp949 깨진 한국어 fallback 5건 UTF-8 교정(Edit가 깨진 바이트 매칭 실패 → 라인번호 기반 Python 교정 + codepoint 검증). ② **QA/QC 인증우회/staleness** — `sync_data.py`가 인증경로 `data/qaqc_result.json` 미러 작성(`/api/data/qaqc`가 읽는 위치, 검증: Apr1→Jun4 신선화) + `public/qaqc_result.json` 추적해제 + `.gitignore` `public/*.json`(public/은 무인증 노출=ADR-023 위반). 워크스페이스 공유 `qaqc_runner.py`는 병렬툴 충돌 회피 위해 미변경(프로젝트 한정 수정). ③ **a11y** — WAI-ARIA tablist/tab(roving+화살표/Home/End)+tabpanel, 검색 aria-label, html lang ko. ④ **테스트 3→16** — auth(HMAC/TTL/skew/변조/401·503) 10 + encoding-guard 1 + insights 엣지 2. ⑤ v1.0.0+favicon+README 배포섹션+SVG 5종 제거. 검증: QC test 16/16+lint+build OK(`/icon.svg` 확인), gate risk 0.0. commit `3c20d53e`. | `projects/knowledge-dashboard/src/app/page.tsx`; `.../layout.tsx`; `.../app/icon.svg`; `.../scripts/sync_data.py`; `.../src/lib/dashboard-auth.test.mts`; `.../src/encoding-guard.test.mts`; `.../src/lib/dashboard-insights.test.mts`; `.../package.json`; `.../README.md`; `.../.gitignore`; `public/*.svg`+`public/qaqc_result.json`(삭제); `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-06-04 | Claude Opus 4.8 (1M context) | **(1) hermes-agent 설치** (사용자 명시 요청, github.com/nousresearch/hermes-agent). PowerShell 5.1 코어모듈 autoload 결함(T-1203 버그)으로 공식 `install.ps1` 실패 → uv 선설치로 자식 powershell 제거 + venv/deps는 git-bash 직접 실행(stderr 트랩 회피) + finalize는 `-Stage` 런처. hermes v0.15.1 정상(`hermes doctor` green). 사용자 후속: `hermes setup`. **(2) T-1206 /goal "프로젝트 완성품화"→blind-to-x**: `image_generator._get_fallback_image_url`의 정적 폴백 URL 5개 중 3개(연봉/회사문화/연애) 실제 404 dead 버그 수정 + `config.image.fallback_images` 외부화 + 17개 토픽 taxonomy 전부 검증된(curl 200) Unsplash 커버 + 운영자 오버라이드/방어. 신규 테스트 8종(taxonomy 완전성·dead ID 회귀·오버라이드). 검증: image_generator 55/55, **full blind-to-x unit 1732/1732 pass 0 fail (5m15s)**, ruff clean. | `projects/blind-to-x/pipeline/image_generator.py`; `projects/blind-to-x/config.example.yaml`; `projects/blind-to-x/tests/unit/test_image_generator.py`; `.tmp/hermes_install.ps1`; `.tmp/run_hermes_install.ps1`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `%LOCALAPPDATA%\hermes\**` (outside workspace) |
| 2026-06-04 | Codex | **T-1205 Resolved Codex startup warnings**. Fixed invalid HeyGen skill descriptions by shortening `heygen-avatar` and `heygen-video` metadata below the 1024-byte loader limit, disabled the broken standalone Figma remote MCP config that lacked OAuth client credentials, and hardened the Notion MCP launcher for cmdlet-free PowerShell execution plus current `NOTION_TOKEN` env compatibility. Verified clean Codex prompt-input startup stderr and Notion MCP initialize response through the launcher. | `infrastructure/notion-mcp/start_notion_mcp.ps1`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `C:\Users\박주호\.codex\config.toml` (outside workspace); `C:\Users\박주호\.codex\plugins\cache\openai-curated\heygen\2abb1c44\skills\...\SKILL.md` (outside workspace); `C:\Users\박주호\.codex\.tmp\plugins\plugins\heygen\skills\...\SKILL.md` (outside workspace) |
| 2026-06-04 | Gemini 3.5 Flash (High) | **T-1204 Patched global npm .ps1 wrapper scripts** (`claude`, `codex`, `pnpm`, etc.) to use static .NET methods (`[System.IO.Path]::GetDirectoryName` and `[System.IO.File]::Exists`), bypassing all cmdlet loading failures. Verified flawless execution of both `claude` and `codex` command wrappers in PowerShell. | `C:\Users\박주호\AppData\Roaming\npm\*.ps1` (outside workspace); `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-06-04 | Gemini 3.5 Flash (High) | **T-1203 Resolved PowerShell core cmdlets not recognized issue** when running global npm wrappers like `codex.ps1`. Created global user profile script (`C:\Users\박주호\OneDrive\문서\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`) to explicitly import core modules (`Microsoft.PowerShell.Management`, `Microsoft.PowerShell.Utility`, `Microsoft.PowerShell.Diagnostics`, `Microsoft.PowerShell.Security`). Verified successful execution of `codex` command and cmdlet availability. | `C:\Users\박주호\OneDrive\문서\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` (outside workspace); `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-28 | Gemini 3.5 Flash | **T-1150..T-1202 full quality uplift, hardening sweep and task ID resolver**. Verified and committed 144 modified/new files. 498 Next.js unit tests passed, eslint completed cleanly, and the Next.js production build succeeded perfectly. The task ID helper tests (5/5) and YAML quality gate tests (5/5) passed. Commited and pushed to remote origin/main. | `execution/next_task_id.py`; `workspace/tests/test_next_task_id.py`; `projects/blind-to-x/tests/unit/test_quality_gate_yaml_externalization.py`; `projects/hanwoo-dashboard/...`; `.ai/GOAL.md`; `.ai/SESSION_LOG.md` |
| 2026-05-28 | Claude Opus 4.7 (1M context) | **T-1200 blind-to-x `cost_db.py` schema/migration 분리** (행동 변화 0). 1074줄 단일 모듈에 schema DDL + 마이그레이션 컨스턴트 + 검증자 + runtime queries가 다 섞여 있어 schema-only 테스트 불가능. 신규 `pipeline/cost_db_schema.py` (165줄)로 분리: `MIGRATION_COLUMNS`/`PRAGMA_TABLE_INFO_SQL`/`ALTER_TABLE_ADD_SQL`/`CREATE_TABLES_SCRIPT` 상수, `validate_allowed_name`/`validate_migration_column`/`ensure_column`/`init_db` 순수 함수. `cost_db.py`는 1074→954줄(-120) 슬림화하고 `_MIGRATION_COLUMNS`/`_validate_*` 등은 backwards-compat 별칭으로 재수출(`noqa: F401`). `CostDatabase._init_db`는 100여줄 inline SQL 대신 `_schema_init_db(conn)` 한 줄로 위임, `_ensure_column` static method도 `_schema_ensure_column` 위임. 신규 `tests/unit/test_cost_db_schema.py` (6 테스트) — in-memory SQLite에 `init_db(conn)`이 base table 6개 + MIGRATION_COLUMNS 전체 적용 / idempotency / validator rejection 직접 검증(0.16s). 외부 호출자(`test_cost_db_security.py`의 `CostDatabase._ensure_column(...)` 등) 변경 0. 검증: focused 27/27 pass, 풀 스위트 1777/1777 pass 0 fail (6m01s), ruff clean. | `projects/blind-to-x/pipeline/cost_db.py`; `projects/blind-to-x/pipeline/cost_db_schema.py`; `projects/blind-to-x/tests/unit/test_cost_db_schema.py`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md` |
| 2026-05-28 | Claude Opus 4.7 (1M context) | **T-1199 hanwoo AI Insight 라우트 structured metric 로그** (`ead4aa35`). T-1112 cacheBackend 동봉만으론 프로덕션 hit rate 회복 확인 불가. Langfuse SDK 추가 회피, lightweight 대안 — Vercel/CloudWatch 가 grep 해 대시보드화할 한 줄 structured JSON 로그. 신규 `emitInsightMetric(payload)` (try/catch fail-safe) + 6 return path 전부 emit (`unauthenticated`/`heuristic_no_api_key`/`cache_hit`/`gemini_success`/`gemini_parse_failure`/`gemini_timeout`/`gemini_error`). 모든 페이로드에 `durationMs`. PII 잠금(userId/summary 절대 미로그, source-grep contract 로 잠금). 1 신규 contract test, 전체 hanwoo `npm test` 498/498, lint clean, build exit 0. | `projects/hanwoo-dashboard/src/app/api/ai/insight/route.js`; `projects/hanwoo-dashboard/src/lib/ai-insight-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md` |
| 2026-05-28 | Codex | **최종 재점검 라운드:** `python execution/project_qc_runner.py --project hanwoo-dashboard --json`를 재실행해 `npm test` 497/497, `npm run lint`, `npm run build`를 통과했고, 이어서 `npm.cmd run db:prisma7-test -- --live` 재실행 결과 `Passed: 15`, `Failed: 1`로 동일한 `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`를 재확인했습니다. | `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `projects/hanwoo-dashboard/.env` |
| 2026-05-28 | Claude Opus 4.7 (1M context) | **T-1197 weekly report에 Best-of-N tuner 자동 임베드** (`a4951f9a`). T-1105 tuner CLI 가 수동 실행만 가능했던 걸 weekly report 빌드 파이프라인에 통합. `_render_best_of_n_section(days)` 신규 + `_render_report()` 끝에 append + markdown 코드 블록 래핑. `run()`은 `max(days, 30)` 윈도우로 sweep 표본 확보 유리. 실패는 swallow → fail-open. 10 신규 unit test, blind-to-x full 1713/1713, ruff clean. (참고: T-1198이 같은 작업의 검증·문서화로 병행 진행 — 멀티툴 race) | `projects/blind-to-x/scripts/build_weekly_report.py`; `projects/blind-to-x/tests/unit/test_build_weekly_report.py`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md` |
| 2026-05-28 | Claude Opus 4.7 (1M context) | **T-1198 /goal "Best-of-N weekly report embed" 검증 & 문서화**. /goal helper 가 멀티툴 race로 이전 세션의 T-1197 follow-up으로 변경된 채 active 상태. 코드 확인 결과 이미 완전 구현됨 — `scripts/build_weekly_report.py:15-39` `_render_best_of_n_section()`이 `tune_best_of_n_weight.build_report()`를 호출해 markdown 코드펜스로 임베드, try/except로 fail-open. 검증: focused tests 25/25 pass (`test_build_weekly_report.py` 10 + `test_tune_best_of_n_weight.py` 15, 0.39s), 실 DB end-to-end 호출 → 표본 부족(0<10) 케이스에서 "기본값 0.5 유지" 메시지 임베드 + 본문 무손상 확인. README/ops-runbook에 임베드 섹션 설명 0건 발견 → `README.md` "추천 주간 운영" 1번 항목 아래에 임베드 동작과 fail-open 1문단 추가. | `projects/blind-to-x/README.md`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md` |
| 2026-05-28 | Codex | **연속 상태 재확인:** `projects/hanwoo-dashboard`에서 `npm.cmd run db:prisma7-test -- --live`를 재실행해 live 검증이 `Passed: 15`, `Failed: 1`로 동일하게 실패함을 확인했습니다. 실패는 `P2010` + `XX000` + `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`였으며, `.env` URL/tenant/user는 기존 상태입니다. | `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `projects/hanwoo-dashboard/.env` |
| 2026-05-28 | Codex | **최종 보완 라운드 점검.** `python execution/project_qc_runner.py --json` 재실행으로 루트 전체 `blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, `knowledge-dashboard`의 test/lint/build 전부 통과를 재확인했으며, `python execution/code_review_gate.py --base HEAD~1 --json`도 `risk_score: 0.0` pass를 재확인했습니다. `projects/hanwoo-dashboard/.env`에서 `DATABASE_URL` 메타(`HOST=aws-0-ap-northeast-2.pooler.supabase.com:6543`, `USER=postgres.fuemeqmigptwfzqvrpjf`) 재확인 후 `T-251`의 외부 블로커 성격을 유지 보고했습니다. | `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md`; `projects/hanwoo-dashboard/.env` |
| 2026-05-28 | Codex | **연속 점검 및 최종 재확인.** `npm.cmd run db:prisma7-test -- --live`를 재실행해 live CRUD E2E가 `15 passed, 1 failed`로 유지되며 `P2010 / XX000 / ENOTFOUND tenant/user postgres.fuemeqmigptwfzqvrpjf not found` 재현을 추가 확인했습니다(외부 Supabase credential 동기화 블로커 유지). `.ai/HANDOFF.md`/`.ai/SESSION_LOG.md`/`.ai/TASKS.md` 상태는 그대로 반영되어 있습니다. | `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md` |
| 2026-05-28 | Codex | **연속 점검 및 T-251 재확인.** `session_orient`, `db:prisma7-test -- --live`, `code_review_gate --base HEAD~1 --json`, `handoff_rotator --check`를 재실행해 현재 상태를 갱신했습니다. `session_orient`/`goal`은 목표(active)와 T-251 단일 TODO를 유지하며, `code_review_gate`는 `risk_score: 0.0` pass, `db:prisma7-test -- --live`는 여전히 `tenant/user postgres.fuemeqmigptwfzqvrpjf` 관련 live CRUD 실패를 재확인했습니다. | `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `projects/hanwoo-dashboard/.env` |
| 2026-05-28 | Claude Opus 4.7 (1M context) | **T-1196 blind-to-x test pollution fix — `clear_runtime_state` promoted to `tests/conftest.py`**. T-1108 검증 중 한 풀 스위트 run에서 `test_cost_db_extended` + `test_cost_tracker_extended` 18건 transient fail 목격(개별/소그룹은 다 pass). 원인: unit conftest의 SQLite 격리 fixture가 `tests/unit/**` 만 보호. Integration test가 `pipeline.draft_generator`/`scoring_6d` 등을 통해 `get_cost_db()` 간접 호출하면 실 `.tmp/btx_costs.db` 가 오염되고 후속 unit test 가 빈 DB 기대하다 깨짐. 수정: `clear_runtime_state` (`_DEFAULT_DB_PATH` monkeypatch + `_db_singleton` reset + ml_scorer joblib cleanup)을 부모 `tests/conftest.py` 로 이동. Unit conftest엔 alias 코멘트만. Integration이 cost_db 직접 안 쓰는 것은 grep으로 확인. 검증: `py -3.14 -m pytest tests/unit tests/integration -q --no-cov --ignore=tests/integration/test_curl_cffi.py` 1767/1767 pass 0 fail (6m29s vs 사전 5m43s — +43s overhead는 integration test에도 fixture 적용된 비용으로 수용). | `projects/blind-to-x/tests/conftest.py`; `projects/blind-to-x/tests/unit/conftest.py`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md` |
| 2026-05-28 | Codex | **Session maintenance check.** Ran `python execution/session_orient.py --json` and `python execution/handoff_rotator.py --check`/`--keep-days 7`; confirmed dirty tree (`modified` 140, `untracked` 2), known user-owned blocker remains (`T-251`), and `.ai/HANDOFF.md`/`.ai/TASKS.md` contain the active handoff/task state for this task sequence. | `.ai/TASKS.md`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md` |
| 2026-05-28 | Codex | **hanwoo-dashboard T-1195 Profitability service DB row hardening**. `src/lib/dashboard/profitability-service.js` now normalizes malformed DB row collections before profitability math; `src/lib/profitability-copy.test.mjs` validates the row-normalization contract and `.ai/TASKS.md`, `.ai/HANDOFF.md`, `.ai/SESSION_LOG.md` were updated for this turn. | `projects/hanwoo-dashboard/src/lib/dashboard/profitability-service.js`; `projects/hanwoo-dashboard/src/lib/profitability-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md` |
| 2026-05-28 | Claude Opus 4.7 (1M context) | **T-1112 AI Insight 캐시 Redis 백킹** (`97447aca`). T-1104 in-memory Map 캐시는 서버리스/다중 인스턴스 cold start 마다 초기화돼 실 hit rate ~0%. 기존 `src/lib/redis.js`(isRedisConfigured/ensureRedisConnection) 재사용해 Redis 격상. 새 async API `loadCachedInsight/saveCachedInsight/dropCachedInsight` — REDIS_URL 시 `ai-insight:<key>` 24h TTL, 미설정 시 Map 폴백, 실패는 fail-open. 응답에 `cacheBackend` 동봉. 기존 sync API도 호환 유지. 5 신규 테스트(총 19), `npm test` 503/503, lint clean, build exit 0. | `projects/hanwoo-dashboard/src/app/api/ai/insight/route.js`; `projects/hanwoo-dashboard/src/lib/ai-insight-cache.mjs`; `projects/hanwoo-dashboard/src/lib/ai-insight-cache.test.mjs`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md` |
| 2026-05-28 | Codex | **hanwoo-dashboard T-1156 Sales tab prop, mutation-callback, and pagination-control hardening**. Added `normalizeSalesTabOptions()` and `normalizeSalesPaginationOptions()` in `SalesTab`. The tab now normalizes malformed top-level props before reading sales/cattle/expense payloads, market data, pagination state, quick-action intent, or `onCreateSale`; malformed sale-create callbacks fall back to a safe async no-op before submit handling, and malformed pagination/load-more callbacks fall back to a safe no-op before the load-more button can invoke them. Verification: focused sales/empty-state/pagination tests 71/71 passed, `npm.cmd test` 463/463 passed, `npm.cmd run lint` passed, `npm.cmd run build` passed with the known T-251 Supabase/Prisma `P2010 / XX000 / ENOTFOUND` health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. | `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`; `projects/hanwoo-dashboard/src/lib/sales-pagination-feedback.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-28 | Codex | **hanwoo-dashboard T-1155 Calving tab prop and mutation-callback hardening**. Added `normalizeCalvingTabOptions()` in `CalvingTab` and routed props through it before reading `cattle`, `buildings`, or `onRecordCalving`. Malformed calving-record callbacks now fall back to a safe async no-op before submit handling, preventing malformed direct/test/reuse callers from throwing during calving render or mutation setup while preserving payload normalization, pregnancy-date ordering, Korean calving form copy, async save locks, mounted-state cleanup, validation wiring, countdown labels, and existing dashboard behavior. Verification: focused calving test 6/6 passed, `npm.cmd test` 463/463 passed, `npm.cmd run lint` passed, `npm.cmd run build` passed with the known T-251 Supabase/Prisma `P2010 / XX000 / ENOTFOUND` health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. | `projects/hanwoo-dashboard/src/components/tabs/CalvingTab.js`; `projects/hanwoo-dashboard/src/lib/calving-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1145 Cattle detail helper prop option hardening.
- Changed `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`: added `normalizeDetailHelperOptions()` and routed `SectionTitle` and `InfoItem` props through it before reading heading icon/title/color or info label/value/highlight/delay fields.
- This prevents direct/test/reuse callers from throwing during modal helper render setup while preserving heading semantics, decorative icon hiding, highlight typography, animation delays, hover styling, Korean detail copy, and existing cattle form/detail focus behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs` coverage for safe helper option normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 18/18, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1146 Analysis KPI card prop option hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/AnalysisTab.js`: added `normalizeKpiCardOptions()` and routed `KpiCard` props through it before reading `title`, `value`, `icon`, or `accent`.
- This prevents direct/test/reuse callers from throwing during KPI card render setup while preserving KPI labels, money formatting, decorative icon semantics, accent styling, Korean analysis copy, and existing financial aggregation behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs` coverage for safe KPI card option normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1147 Feed helper prop and input option hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`: added `normalizeFeedHelperOptions()` and routed `FilterChip` and `Field` props through it before reading selected state, labels, callbacks, disabled state, suffix, errors, or input props.
- `FilterChip` now ignores malformed click handlers before wiring button interaction, and `Field` normalizes `inputProps` with a safe fallback field id before spreading input attributes.
- This prevents direct/test/reuse callers from throwing during feed filter or feed input render setup while preserving filter chip labels, busy/pressed semantics, feed validation wiring, Korean feed copy, and existing feed aggregation behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` coverage for safe Feed helper option normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/empty-state-wiring.test.mjs` passed 18/18, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1192 Cattle list server-action DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/cattle.js`: added cattle row/result normalization and routed `getCattleList()` and `getArchivedCattle()` Prisma results through it before returning.
- Malformed non-array DB/mock results now return `[]`, and malformed or array-shaped rows are filtered before direct/action/reuse callers receive active or archived cattle data.
- This preserves authenticated server action behavior, existing Korean cattle failure copy, archive semantics, dashboard cattle normalization, cattle pagination/export consumers, and active/archive ordering semantics.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe cattle list row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 8/8, `npm.cmd test` passed 496/496, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1188 Building server-action DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/building.js`: added building row/result normalization and routed `getBuildings()` Prisma results through it before returning.
- Malformed non-array DB/mock results now return `[]`, and malformed or array-shaped rows are filtered before direct/action/reuse callers receive building data.
- This preserves authenticated server action behavior, existing Korean building failure copy, building creation validation, delete guard behavior, dashboard building normalization, name ordering semantics, pen routing, setup progress, and settings building controls.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe building row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 6/6, `npm.cmd test` passed 494/494, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning once without the concurrent Next build lock.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1189 Schedule server-action DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/schedule.js`: added schedule row/result normalization and routed `getScheduleEvents()` Prisma results through it before returning.
- Malformed non-array DB/mock results now return `[]`, and malformed or array-shaped rows are filtered before direct/action/reuse callers receive schedule data.
- This preserves authenticated server action behavior, existing Korean schedule failure copy, schedule creation and completion-toggle behavior, dashboard schedule normalization, date ordering semantics, setup progress, today-focus schedule cards, and upcoming schedule countdown labels.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe schedule row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 7/7, `npm.cmd test` passed 495/495, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1191 Sales list server-action DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/sales.js`: added sales row/result normalization and routed `getSalesRecords()` Prisma results through it before returning.
- Malformed non-array DB/mock results now return `[]`, and malformed or array-shaped rows are filtered before direct/action/reuse callers receive sales data.
- This preserves authenticated server action behavior, existing Korean sales failure copy, sale creation validation, cattle history recording, dashboard sales normalization, profitability/analysis consumers, financial charting, sales list cache invalidation, and sale-date ordering semantics.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe sales row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 7/7, `npm.cmd test` passed 495/495, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1190 Expense list server-action DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/expense.js`: routed `getExpenseRecords()` Prisma results through the existing expense row normalizer before returning.
- Malformed non-array DB/mock results now return `[]`, and malformed or array-shaped rows are filtered before direct/action/reuse callers receive expense data.
- This preserves authenticated server action behavior, existing Korean expense failure copy, expense filter parsing, expense creation validation, expense aggregation normalization, date ordering semantics, dashboard expense filters, analysis, financial charting, and cost aggregation paths.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe expense list and aggregation row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 7/7, `npm.cmd test` passed 495/495, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1184 Expense aggregation row and amount hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/expense.js`: added `normalizeExpenseRows()` and `normalizeExpenseCategory()`, routed `getExpenseAggregation()` through them, filtered malformed/array-shaped expense rows, and coerced amounts with `toFiniteNumber()`.
- This prevents direct/action/reuse callers from crashing on malformed expense collections or corrupting category totals with array-attached fields, invalid categories, or non-finite/string amounts while preserving authenticated server action behavior and the existing safe `{}` catch fallback.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe expense aggregation row, category, and amount normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 3/3, `npm.cmd test` passed 490/490, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1185 AI chat farm-context DB row hardening.
- Changed `projects/hanwoo-dashboard/src/app/api/ai/chat/route.js`: added `isFarmContextRow()`, `normalizeFarmContextRows()`, `normalizeStatusCountLabel()`, and `normalizeStatusCountValue()`, then routed `statusCounts` and `recentSales` through safe row normalization before Gemini prompt context generation.
- Nested cattle data in recent sales is now normalized before reading cattle names or tag numbers, preventing array-shaped nested payloads from leaking into AI context while preserving Korean assistant instructions, farm-context fallback copy, sale-date fallback, and finite sale-price coercion.
- Strengthened `projects/hanwoo-dashboard/src/lib/ai-chat-api.test.mjs` coverage for safe AI chat farm-context row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-api.test.mjs` passed 11/11, `npm.cmd test` passed 491/491, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1186 Feed server-action DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/feed.js`: added `isFeedActionRow()` and `normalizeFeedActionRows()`, then routed `getFeedStandards()` and `getFeedHistory()` DB results through safe row normalization before returning to dashboard callers.
- This prevents malformed non-array DB/mock results or array-shaped rows from reaching feed rendering and aggregation paths while preserving authenticated server action behavior, feed record creation validation, Korean feed failure copy, and feed-history ordering/limit semantics.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe feed action row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 4/4, `npm.cmd test` passed 492/492, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1187 Inventory server-action DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/inventory.js`: added `isInventoryActionRow()` and `normalizeInventoryActionRows()`, then routed `getInventory()` DB results through safe row normalization before returning to dashboard callers.
- This prevents malformed non-array DB/mock results or array-shaped inventory rows from reaching inventory rendering and low-stock calculation paths while preserving authenticated server action behavior, item creation and quantity validation, Korean inventory failure copy, and category ordering semantics.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe inventory action row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 5/5, `npm.cmd test` passed 493/493, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1181 Payment API request-body hardening.
- Changed `projects/hanwoo-dashboard/src/app/api/payments/prepare/route.js`: added `normalizePaymentPrepareBody()` and routed `await req.json()` through it before reading amount, customer key, order name, customer name, or email fields.
- Changed `projects/hanwoo-dashboard/src/app/api/payments/confirm/route.js`: added `normalizePaymentConfirmBody()` and routed `await req.json()` through it before reading payment key, order id, or amount fields.
- This prevents null, primitive, and array-shaped JSON bodies from throwing or leaking array-attached fields into payment preparation/confirmation while preserving existing Korean validation/error paths, Toss payment flow, authentication handling, payment-log failure normalization, and subscription creation behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs` coverage for safe request-body normalization in both payment API routes.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/payment-ux-copy.test.mjs` passed 10/10, `npm.cmd test` passed 488/488, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1182 Notification builder cattle payload hardening.
- Changed `projects/hanwoo-dashboard/src/lib/notifications.js`: added `isNotificationCattleRow()` and `normalizeNotificationCattle()`, then routed `buildNotifications()` cattle input through the safe collection before estrus/calving alert generation.
- This prevents null, primitive, and array-shaped cattle payloads from throwing or leaking array-attached row fields into notification ids, messages, cattle metadata, timing, or alert sorting while preserving existing estrus/calving timing and dashboard notification behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs` coverage for safe notification-builder cattle payload normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/notification-system-copy.test.mjs` passed 10/10, `npm.cmd test` passed 489/489, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1183 Livestock weather alert utility forecast hardening.
- Changed `projects/hanwoo-dashboard/src/lib/utils.js`: added `isLivestockWeatherForecastDay()` and `normalizeLivestockWeatherForecast()`, then routed `getLivestockWeatherAlerts()` forecast input through the safe collection before heat/cold/rain alert generation.
- This prevents null, primitive, and array-shaped forecast payloads from throwing or leaking array-attached row fields into weather alert labels, thresholds, messages, or icons while preserving WeatherWidget's existing safe forecast flow, Korean weather copy, date formatting fallback, and livestock alert behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/utils-date.test.mjs` coverage for safe livestock weather forecast normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/utils-date.test.mjs` passed 1/1, `npm.cmd test` passed 489/489, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1178 Dashboard calculation utility array-row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.mjs`: setup completion counts now ignore malformed array rows instead of counting them as configured buildings, cattle, inventory, or schedule rows.
- Changed `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.mjs`: feed-category checks and feed-history consumption estimates now reject array rows before feed-depletion projections are calculated.
- Changed `projects/hanwoo-dashboard/src/lib/dashboard/farm-metrics.mjs`: feed-expense records, sales records, and object-based cattle lookup values now reject array rows before farm-specific feed-cost or weight-gain evidence is calculated.
- Strengthened `projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.test.mjs`, `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.test.mjs`, and `projects/hanwoo-dashboard/src/lib/dashboard/farm-metrics.test.mjs` coverage for array-row guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/setup-progress.test.mjs src/lib/dashboard/today-focus.test.mjs src/lib/dashboard/farm-metrics.test.mjs` passed 37/37, `npm.cmd test` passed 485/485, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1179 AI/market/history helper array-object hardening.
- Changed `projects/hanwoo-dashboard/src/lib/ai-chat-api.mjs`: chat history items now reject array objects before Gemini history normalization.
- Changed `projects/hanwoo-dashboard/src/lib/ai-insight.mjs`: profitability rows, notification rows, and parsed AI response items now require plain objects before insight summary/response output is derived.
- Changed `projects/hanwoo-dashboard/src/lib/market-price-state.mjs`: cached snapshots, live payloads, and bull/cow price sides now reject array objects before live/cache KAPE market price state is accepted.
- Changed `projects/hanwoo-dashboard/src/lib/cattle-history.mjs`: direct and JSON-parsed metadata arrays now become parse errors instead of flowing into cattle history metadata or weight-history extraction.
- Strengthened `projects/hanwoo-dashboard/src/lib/ai-chat-api.test.mjs`, `projects/hanwoo-dashboard/src/lib/ai-insight.test.mjs`, `projects/hanwoo-dashboard/src/lib/market-price-state.test.mjs`, and `projects/hanwoo-dashboard/src/lib/cattle-history.test.mjs` coverage for array-object guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-api.test.mjs src/lib/ai-insight.test.mjs src/lib/market-price-state.test.mjs src/lib/cattle-history.test.mjs` passed 46/46, `npm.cmd test` passed 487/487, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1180 AI chat request dependency hardening.
- Changed `projects/hanwoo-dashboard/src/lib/ai-chat-api.mjs`: added dependency normalization and required-callback validation for `handleAiChatRequest()` before destructuring and invoking chat-route dependencies.
- Malformed or partial dependency payloads now return the existing Korean JSON error envelope instead of throwing before authentication, API-key lookup, farm-context construction, or stream creation can be guarded.
- Strengthened `projects/hanwoo-dashboard/src/lib/ai-chat-api.test.mjs` coverage for malformed dependency input.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-api.test.mjs` passed 10/10, `npm.cmd test` passed 488/488, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1175 Collection row array hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/AnalysisTab.js`, `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`, `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`, and `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`: collection row normalizers now reject malformed array rows before tab rendering and aggregation.
- Changed `projects/hanwoo-dashboard/src/components/widgets/FinancialChartWidget.js`, `projects/hanwoo-dashboard/src/components/widgets/ProfitabilityWidget.js`, `projects/hanwoo-dashboard/src/components/widgets/NotificationWidget.js`, and `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`: widget/modal collection normalizers now ignore array rows before charts, recommendations, notification rows, and modal rendering.
- Changed `projects/hanwoo-dashboard/src/lib/dashboard/summary-service.js`, `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.mjs`, and `projects/hanwoo-dashboard/src/lib/cattle-csv-export.mjs`: dashboard summary, today-focus, and cattle CSV row helpers now reject array rows before summary cards, focus items, feed-depletion checks, or CSV export rows are derived.
- Strengthened `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs`, `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`, `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`, `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs`, and `projects/hanwoo-dashboard/src/lib/profitability-copy.test.mjs` source coverage for array-row guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs src/lib/profitability-copy.test.mjs src/lib/notification-system-copy.test.mjs src/lib/notification-modal-copy.test.mjs src/lib/dashboard/setup-progress.test.mjs src/lib/dashboard/today-focus.test.mjs src/lib/cattle-csv-export.test.mjs src/lib/empty-state-wiring.test.mjs src/lib/home-market-copy.test.mjs` passed 124/124, `npm.cmd test` passed 483/483, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1176 Dashboard and pagination array-row hardening.
- Changed `projects/hanwoo-dashboard/src/components/DashboardClient.js`: dashboard helper items, building rows, cattle/list rows, and notification rows now reject malformed arrays before home panels, building grids, cattle registries, notification fan-out, and full-list fetch accumulation use them.
- Changed `projects/hanwoo-dashboard/src/lib/hooks/useCattlePagination.js` and `projects/hanwoo-dashboard/src/lib/hooks/useSalesPagination.js`: page item normalizers now reject array rows before initial state, previous-state merging, and load-more accumulation.
- Changed `projects/hanwoo-dashboard/src/lib/hooks/useCursorPagination.js`: added shared item normalization for initial items and fetched page items, rejects array rows, and merges through normalized previous state.
- Strengthened `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`, `projects/hanwoo-dashboard/src/lib/cattle-pagination-feedback.test.mjs`, `projects/hanwoo-dashboard/src/lib/sales-pagination-feedback.test.mjs`, and `projects/hanwoo-dashboard/src/lib/cursor-pagination-feedback.test.mjs` source coverage for dashboard and pagination array-row guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs src/lib/cattle-pagination-feedback.test.mjs src/lib/sales-pagination-feedback.test.mjs src/lib/cursor-pagination-feedback.test.mjs` passed 57/57, `npm.cmd test` passed 483/483, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1177 Operational UI collection array-row hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/CalvingTab.js`, `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`, and `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`: operational tab collection normalizers now reject malformed array rows before pregnancy/calving lists, schedule lists, settings building rows, and widget registry controls render.
- Changed `projects/hanwoo-dashboard/src/components/forms/CattleForm.js` and `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`: building and fallback chart data normalizers now reject array rows before form selects, detail lookup, and fallback weight charts use them.
- Changed `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.js`, `projects/hanwoo-dashboard/src/components/widgets/AlertBanners.js`, `projects/hanwoo-dashboard/src/components/widgets/EarTagScannerModal.js`, `projects/hanwoo-dashboard/src/components/widgets/FieldModeView.js`, `projects/hanwoo-dashboard/src/components/ui/cards.js`, and `projects/hanwoo-dashboard/src/components/widgets/widgets.js`: notification, alert, scanner, field-mode, pen-card, and weather forecast row normalizers now reject array rows before user-facing rendering or target selection.
- Strengthened `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`, `projects/hanwoo-dashboard/src/lib/cards-accessibility.test.mjs`, `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`, `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs`, `projects/hanwoo-dashboard/src/lib/eartag-scanner-modal-accessibility.test.mjs`, `projects/hanwoo-dashboard/src/lib/field-mode-celebration.test.mjs`, `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`, `projects/hanwoo-dashboard/src/lib/tab-header-accessibility.test.mjs`, `projects/hanwoo-dashboard/src/lib/calving-tab-accessibility.test.mjs`, and `projects/hanwoo-dashboard/src/lib/alert-banners-accessibility.test.mjs` source coverage for array-row guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs src/lib/cards-accessibility.test.mjs src/lib/cattle-detail-modal-wiring.test.mjs src/lib/notification-system-copy.test.mjs src/lib/eartag-scanner-modal-accessibility.test.mjs src/lib/field-mode-celebration.test.mjs src/lib/settings-tab-accessibility.test.mjs src/lib/tab-header-accessibility.test.mjs src/lib/calving-tab-accessibility.test.mjs src/lib/alert-banners-accessibility.test.mjs` passed 139/139, `npm.cmd test` passed 483/483, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1172 Weather, fetch, queue, and offline utility array-option hardening.
- Changed `projects/hanwoo-dashboard/src/lib/weather-state.mjs`, `projects/hanwoo-dashboard/src/lib/fetchWithTimeout.js`, `projects/hanwoo-dashboard/src/lib/queue.js`, and `projects/hanwoo-dashboard/src/lib/offline-sync-state.mjs`: shared option/object normalizers now reject arrays before reading timeout, message, location, queue, retry, permanent-failure, or metadata fields.
- This prevents direct/test/reuse callers from leaking array-attached option fields into user-facing weather fallback copy, timeout behavior, queue option wiring, or offline retry/dead-letter state while preserving Open-Meteo normalization, guarded fetch timeout scheduling/cleanup, Redis configuration checks, offline retry accounting, Korean fallback copy, and existing dashboard behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/weather-state.test.mjs`, `projects/hanwoo-dashboard/src/lib/fetch-with-timeout.test.mjs`, `projects/hanwoo-dashboard/src/lib/offline-sync-state.test.mjs`, and `projects/hanwoo-dashboard/src/lib/queue.test.mjs` coverage for array-option and array-item guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/weather-state.test.mjs src/lib/fetch-with-timeout.test.mjs src/lib/offline-sync-state.test.mjs src/lib/queue.test.mjs` passed 25/25, `npm.cmd test` passed 479/479, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1173 Auth, dashboard cache/query/read-model, and notification timing array-option hardening.
- Changed `projects/hanwoo-dashboard/src/lib/auth-guard.js`, `projects/hanwoo-dashboard/src/lib/dashboard/cache.js`, `projects/hanwoo-dashboard/src/lib/dashboard/list-queries.js`, `projects/hanwoo-dashboard/src/lib/dashboard/read-models.js`, and `projects/hanwoo-dashboard/src/lib/notification-timing.mjs`: shared option/object normalizers now reject arrays before reading redirect, filter, pagination, cache-bypass, invalidation, or notification reference-time fields.
- This prevents direct/test/reuse callers from leaking array-attached option fields into authentication redirects, cache keys, list query cache bypasses, read-model cache decisions, cache invalidation, or estrus timing calculations while preserving existing Korean auth copy, dashboard cache segmentation, list pagination validation, read-model cache behavior, and notification timing fallbacks.
- Strengthened `projects/hanwoo-dashboard/src/lib/auth-guard-options.test.mjs`, `projects/hanwoo-dashboard/src/lib/dashboard-cache-options.test.mjs`, `projects/hanwoo-dashboard/src/lib/dashboard-list-query-input.test.mjs`, `projects/hanwoo-dashboard/src/lib/dashboard-read-models-date.test.mjs`, and `projects/hanwoo-dashboard/src/lib/notification-timing.test.mjs` coverage for array-option guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/auth-guard-options.test.mjs src/lib/dashboard-cache-options.test.mjs src/lib/dashboard-list-query-input.test.mjs src/lib/dashboard-read-models-date.test.mjs src/lib/notification-timing.test.mjs` passed 15/15, `npm.cmd test` passed 482/482, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1174 AI insight summary/request and action invalidation array-object hardening.
- Changed `projects/hanwoo-dashboard/src/lib/ai-insight.mjs`, `projects/hanwoo-dashboard/src/components/widgets/AIInsightWidget.js`, `projects/hanwoo-dashboard/src/app/api/ai/insight/route.js`, and `projects/hanwoo-dashboard/src/lib/actions/_helpers.js`: AI insight summary normalization, widget stable-summary normalization, API request-body normalization, and shared action cache invalidation option normalization now reject arrays before reading farm summary, weather, force-refresh, cache-key, or cache-invalidation fields.
- This prevents direct/test/reuse callers from leaking array-attached fields into heuristic insight generation, AI insight request caching/refresh behavior, widget fallback summaries, or dashboard cache invalidation while preserving existing Gemini fallback flow, Korean insight copy, same-day AI cache behavior, Next cache tag revalidation, and dashboard mutation cache invalidation.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-helper-options.test.mjs`, `projects/hanwoo-dashboard/src/lib/ai-insight.test.mjs`, and `projects/hanwoo-dashboard/src/lib/ai-insight-widget-copy.test.mjs` coverage for array-object guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-helper-options.test.mjs src/lib/ai-insight.test.mjs src/lib/ai-insight-widget-copy.test.mjs` passed 33/33, `npm.cmd test` passed 483/483, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1168 AI chat stream option and callback hardening.
- Changed `projects/hanwoo-dashboard/src/lib/ai-chat-api.mjs`: added `normalizeAiChatStreamOptions()` and routed `createAiChatSseStream()` through it before reading `chat`, `message`, or `encoder`.
- Changed `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`: added `normalizeStreamChatOptions()` and safe `handleChunk`, `handleDone`, and `handleError` callback fallbacks before fetch, chunk dispatch, completion, or error handling.
- This prevents direct/test/reuse callers from crashing AI chat streaming setup while preserving authenticated chat validation, Gemini history normalization, Korean configuration/error copy, abort handling, mounted-state guards, accessible launcher/dialog behavior, and existing offline fallback behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/ai-chat-api.test.mjs` and `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs` coverage for malformed stream options and callback guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-api.test.mjs src/lib/ai-chat-widget-copy.test.mjs` passed 11/11, `npm.cmd test` passed 474/474, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning once without a concurrent Next build lock.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1169 Dashboard summary service option and row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/dashboard/summary-service.js`: added `normalizeSummaryOptions()`, `normalizeSummaryRows()`, `resolveGeneratedAt()`, and `resolveFinancialSeriesMonthCount()`.
- The cached dashboard summary service now normalizes malformed top-level payload options before reading `farmId` or `client`, normalizes financial-series options before reading sales, expenses, month count, or generated date, filters malformed status/building/financial rows before reductions, maps, month aggregation, and occupancy calculations, and guards partial aggregate payloads with optional chaining plus numeric coercion.
- This prevents direct/test/reuse callers and partial Prisma result shapes from crashing summary payload generation while preserving cached query wiring, current-month rollups, six-month financial series, farm settings payloads, and existing dashboard summary API behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs` source coverage for safe summary option, row, month, generated-date, aggregate, and building normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 474/474, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1170 AI Gemini route helper option hardening.
- Changed `projects/hanwoo-dashboard/src/app/api/ai/insight/route.js`: added `normalizeGeminiInsightOptions()` and routed `callGeminiForInsights()` through it before reading `apiKey` or `prompt`.
- Changed `projects/hanwoo-dashboard/src/app/api/ai/chat/route.js`: added `normalizeGeminiChatStreamOptions()` and routed `createGeminiChatStream()` through it before reading `apiKey`, `message`, `history`, or `systemInstruction`.
- This prevents direct/test/reuse callers from crashing the AI provider setup through parameter destructuring while preserving authenticated route flow, Gemini model configuration, Korean insight timeout fallbacks, chat farm-context wiring, SSE stream delegation, AI cache behavior, and existing offline/configuration fallback behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs` and `projects/hanwoo-dashboard/src/lib/ai-insight-widget-copy.test.mjs` route source coverage for safe Gemini helper option normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-widget-copy.test.mjs src/lib/ai-insight-widget-copy.test.mjs` passed 17/17, `npm.cmd test` passed 475/475, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1171 Market price and payment helper option hardening.
- Changed `projects/hanwoo-dashboard/src/lib/market-price-state.mjs`: `normalizeOptions()` now rejects arrays, and `createAvailableMarketPrice()` normalizes top-level options before reading price sides, source metadata, freshness flags, or dates.
- Changed `projects/hanwoo-dashboard/src/app/api/payments/confirm/route.js`: added `normalizePaymentLogFailureOptions()` and routed `markPaymentLogFailed()` through it before reading `orderId`, `paymentKey`, or `amount`.
- This prevents direct/test/reuse callers from crashing helper setup or leaking malformed array option fields while preserving KAPE live/cache normalization, unavailable market fallback copy, Toss payment confirmation flow, Korean payment error copy, and existing persistence behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/market-price-state.test.mjs` and `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs` coverage for array-option and payment failure-log helper guards.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/market-price-state.test.mjs src/lib/payment-ux-copy.test.mjs` passed 20/20, `npm.cmd test` passed 476/476, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1164 Cattle detail modal prop, cattle-payload, callback, helper, and fallback chart hardening.
- Changed `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`: added `normalizeCattleDetailModalOptions()` and `normalizeDetailCattle()`, routed detail props through them, and introduced safe `handleClose`, `handleEdit`, `handleDelete`, and `handleUpdate` fallbacks.
- Malformed cattle payloads now render no modal instead of flowing into detail sections; malformed close/edit/delete/update callbacks fall back safely before Escape, header close, edit, archive, or breeding-record save actions invoke them.
- Also normalized malformed fallback `weightHistory` chart rows after direct array input or JSON parsing, and routed `SectionTitle` / `InfoItem` helper props through safe option normalization before destructuring.
- This prevents direct/test/reuse callers from throwing during detail render, close, edit, archive, Escape, breeding-record save setup, helper rendering, or fallback chart rendering while preserving building payload normalization, history fallback, async breeding save locks, archive busy locking, Korean detail copy, focus management, and dashboard cattle detail behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs` coverage for safe detail option, cattle, callback, helper, and fallback chart normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-detail-modal-wiring.test.mjs src/lib/cattle-form-date-submit.test.mjs src/lib/form-submit-pending-copy.test.mjs` passed 20/20, `npm.cmd test` passed 466/466, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1165 Dashboard client top-level prop option hardening.
- Changed `projects/hanwoo-dashboard/src/components/DashboardClient.js`: added `normalizeDashboardClientOptions()` and routed `DashboardClient` props through it before reading SSR cattle/sales pages, summary, notifications, feed standards, inventory, schedule, feed history, buildings, farm settings, expenses, market price, or profitability payloads.
- This prevents direct/test/reuse callers from throwing during dashboard render setup before existing pagination hooks, collection normalizers, Korean fallback copy, widget wiring, modal state, and mutation guards can run.
- Strengthened `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs` coverage for safe dashboard client option normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed 52/52, `npm.cmd test` passed 467/467, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1166 Farm metrics option hardening.
- Changed `projects/hanwoo-dashboard/src/lib/dashboard/farm-metrics.mjs`: added `normalizeFarmMetricOptions()` and routed `estimateMonthlyFeedCostPerHead()`, `estimateMonthlyWeightGainPerHead()`, and `computeFarmAdjustments()` through it before reading top-level calculation options.
- `computeFarmAdjustments()` now also normalizes malformed `defaults` before reading fallback feed-cost or weight-gain values.
- This prevents direct/test/reuse callers and profitability-service reuse from throwing on null, array, or primitive options while preserving existing feed-expense filtering, sales-window filtering, farm-specific adjustment evidence, and default fallback behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/dashboard/farm-metrics.test.mjs` coverage for malformed top-level options and malformed defaults.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/farm-metrics.test.mjs` passed 15/15, `npm.cmd test` passed 470/470, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1167 Dashboard setup and today-focus helper option hardening.
- Changed `projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.mjs`: added `normalizeSetupProgressOptions()` and routed `buildSetupProgressItems()` through it before reading farm setup inputs.
- Changed `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.mjs`: added `normalizeTodayFocusOptions()` and routed `estimateDailyFeedConsumptionKg()` and `buildTodayFocusItems()` through it before reading notification/schedule/inventory/feed collections, sales counts, online state, or reference dates.
- This prevents direct/test/reuse callers from throwing on null, array, or primitive options before setup progress, today-focus cards, or feed-depletion projections can fall back to safe empty/default dashboard guidance.
- Strengthened `projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.test.mjs` and `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.test.mjs` coverage for malformed top-level option payloads.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/setup-progress.test.mjs src/lib/dashboard/today-focus.test.mjs` passed 20/20, `npm.cmd test` passed 473/473, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1160 Cattle form prop and callback hardening.
- Changed `projects/hanwoo-dashboard/src/components/forms/CattleForm.js`: added `normalizeCattleFormOptions()` and routed `CattleForm` props through it before reading `cattle`, `buildings`, `onSubmit`, or `onCancel`.
- Malformed submit and cancel callbacks now fall back to safe async/no-op handlers before save, cancel-button, or Escape-key handling.
- Adjusted cattle form building normalization to avoid React Compiler memoization warnings while keeping reset behavior tied to the original `buildings` prop.
- This prevents direct/test/reuse callers from throwing during cattle form render, cancel, Escape, or submit setup while preserving building payload normalization, tag lookup guards, date conversion, async save locks, focus management, validation wiring, Korean form copy, and dashboard cattle create/edit behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs` coverage for safe cattle form option and callback normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-detail-modal-wiring.test.mjs src/lib/cattle-form-date-submit.test.mjs src/lib/form-submit-pending-copy.test.mjs` passed 20/20, `npm.cmd test` passed 464/464, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1161 Financial chart widget prop option hardening.
- Changed `projects/hanwoo-dashboard/src/components/widgets/FinancialChartWidget.js`: added `normalizeFinancialChartWidgetOptions()` and routed `FinancialChartWidget` props through it before reading `saleRecords`, `expenseRecords`, or `seriesData`.
- This prevents direct/test/reuse callers from throwing during financial chart render setup while preserving existing collection row filtering, strict month parsing, numeric coercion, fallback six-month aggregation, Korean chart labels, accessible chart summary, and dashboard financial widget behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs` coverage for safe financial chart option normalization and for blocking a regression to raw destructured component parameters.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 464/464, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1162 Ear tag scanner modal prop, list, and callback hardening.
- Changed `projects/hanwoo-dashboard/src/components/widgets/EarTagScannerModal.js`: added `normalizeEarTagScannerModalOptions()` and `normalizeScannerCattleList()`, routed props through them, and introduced safe `handleClose` / `handleSelect` callback fallbacks.
- Malformed cattle list payloads are now filtered before simulated target selection, manual choice rendering, retry, and lookup; malformed close/select callbacks fall back to no-ops before header close, footer close, or confirm actions invoke them.
- This prevents direct/test/reuse callers from throwing during scanner render, scan setup, manual selection, retry, close, or confirm handling while preserving scanner animation guards, Korean task labels, live result announcements, missing birth-date copy, tactile/audio feedback, and dashboard scanner behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/eartag-scanner-modal-accessibility.test.mjs` coverage for safe option, list, and callback normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 6/6, `npm.cmd test` passed 465/465, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1163 Field mode view prop, list, and callback hardening.
- Changed `projects/hanwoo-dashboard/src/components/widgets/FieldModeView.js`: added `normalizeFieldModeViewOptions()` and `normalizeFieldModeCattleList()`, routed props through them, and introduced safe `handleEnsureAllCattleLoaded`, `handleSelect`, and `handleCloseFieldMode` fallbacks.
- Malformed cattle list payloads are now filtered before search, critical-alert counters, total herd count, and the embedded ear-tag scanner; malformed loader/select/close callbacks fall back safely before background loading, search-result selection, scanner selection, or mode-close behavior.
- This prevents direct/test/reuse callers from throwing during field-mode render, search, stats, scanner handoff, close, or background loading while preserving checklist persistence, stale-load cleanup, celebration animation guards, Korean field-mode copy, loading announcements, and dashboard field-mode behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/field-mode-celebration.test.mjs` coverage for safe option, list, and callback normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/field-mode-celebration.test.mjs src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 20/20, `npm.cmd test` passed 466/466, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1158 Settings tab prop, widget-control, and mutation-callback hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`: added `normalizeSettingsTabOptions()`, `normalizeSettingsWidgetRegistry()`, and `normalizeSettingsWidgetVisible()`.
- `SettingsTab` now normalizes malformed top-level props before reading building payloads, farm settings, theme state, widget registry/visibility, quick-action intent, or settings/building/theme/widget callbacks.
- Malformed create-building, delete-building, farm-settings, theme-toggle, and widget-toggle callbacks now fall back to safe no-ops before submit/delete/switch handling.
- Malformed widget registry and visibility payloads are normalized before `.length`, `.map()`, and switch-state access.
- This prevents direct/test/reuse callers from throwing during settings render, widget interaction, farm save, building create, or building delete setup while preserving building payload normalization, Korean settings copy, async save/delete locks, mounted-state cleanup, validation wiring, diagnostics link, and existing dashboard settings behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs` and `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` coverage for safe settings option, widget, and callback normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/settings-tab-accessibility.test.mjs src/lib/empty-state-wiring.test.mjs` passed 33/33, `npm.cmd test` passed 464/464, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1159 Analysis tab prop option hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/AnalysisTab.js`: added `normalizeAnalysisTabOptions()` and routed `AnalysisTab` props through it before reading `saleRecords`, `feedHistory`, `cattleList`, or `expenseRecords`.
- This prevents direct/test/reuse callers from throwing during analysis render setup while preserving existing collection row normalization, KPI card option normalization, monthly revenue/cost/profit aggregation, feed-average calculation, chart labeling, Korean analysis copy, and existing dashboard analysis behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs` coverage for safe analysis tab option normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 464/464, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1148 Dashboard helper panel prop and collection hardening.
- Changed `projects/hanwoo-dashboard/src/components/DashboardClient.js`: added `normalizeDashboardHelperOptions()` and `normalizeDashboardHelperItems()`, then routed `TodayFocusPanel`, `QuickActionPanel`, `SetupProgressPanel`, and `PenCattleList` helper props and item/action/progress/cattle collections through them.
- Malformed callbacks now fall back to safe no-ops, setup progress numbers are finite/clamped before progressbar labels and width, quick actions fall back to a safe icon, and pen cattle filtering uses a normalized cattle collection.
- This prevents direct/test/reuse callers from throwing during home panel render or button handling while preserving today-focus labels, quick-action labels, setup progress semantics, pen cattle filtering, Korean empty-pen copy, and existing dashboard navigation behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs` coverage for safe dashboard helper normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1149 Legal document layout prop option hardening.
- Changed `projects/hanwoo-dashboard/src/components/layout/LegalDocumentLayout.js`: added `normalizeLegalDocumentLayoutOptions()` and routed `LegalDocumentLayout` props through it before reading `eyebrow`, `title`, `subtitle`, `lastUpdated`, or `children`.
- This prevents direct/test/reuse callers from throwing during legal page layout render setup while preserving privacy/terms support-channel copy, back-home link semantics, decorative back icon hiding, and existing legal page shell styling.
- Strengthened `projects/hanwoo-dashboard/src/lib/legal-pages-copy.test.mjs` coverage for safe layout option normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/legal-pages-copy.test.mjs` passed 1/1, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1150 App error boundary prop and reset hardening.
- Changed `projects/hanwoo-dashboard/src/app/error.js`: added `normalizeRouteErrorOptions()` and `normalizeRouteErrorReset()`, then routed `RouteError` props and retry handling through them before reading `error`/`reset` or invoking the retry action.
- Changed `projects/hanwoo-dashboard/src/app/global-error.js`: added `normalizeGlobalErrorOptions()` and `normalizeGlobalErrorReset()`, then routed `GlobalError` props and retry handling through them before reading `error`/`reset` or invoking the retry action.
- This prevents direct/test/reuse callers from throwing during app-level failure UI render or retry handling while preserving client-boundary requirements, Korean retry/home copy, route home action, global-error html/body contract, and existing error logging.
- Strengthened `projects/hanwoo-dashboard/src/lib/error-pages-wiring.test.mjs` coverage for safe error-boundary option and reset normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/error-pages-wiring.test.mjs` passed 10/10, `npm.cmd test -- --runTestsByPath src/lib/error-pages-wiring.test.mjs` ran the full suite and passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning once without the concurrent Next build lock.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1151 Root layout prop option hardening.
- Changed `projects/hanwoo-dashboard/src/app/layout.js`: added `normalizeRootLayoutOptions()` and routed `RootLayout` props through it before reading `children`.
- This prevents direct/test/reuse callers from throwing during root shell render setup while preserving the Korean metadata/PWA copy, font variable setup, FeedbackProvider wrapping, Suspense boundary, `lang="ko"`, and hydration-warning behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/app-metadata-copy.test.mjs` coverage for safe root-layout option normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/app-metadata-copy.test.mjs` passed 1/1, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1152 Subscription fallback prop option hardening.
- Changed `projects/hanwoo-dashboard/src/app/subscription/success/page.js`: added `normalizeSubscriptionFallbackOptions()` and routed `SubscriptionFallback` props through it before reading `message`.
- Changed `projects/hanwoo-dashboard/src/app/subscription/fail/page.js`: added `normalizeSubscriptionFallbackOptions()` and routed `SubscriptionFallback` props through it before reading `message`.
- This prevents direct/test/reuse callers from throwing during payment result loading-state render setup while preserving Korean loading/failure/success copy, polite busy status semantics, retry navigation fallbacks, guarded success timers, and existing payment confirmation behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs` coverage for safe subscription fallback option normalization on both result pages.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/payment-ux-copy.test.mjs` passed 10/10, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1153 Inventory tab prop and mutation-callback hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`: added `normalizeInventoryTabOptions()` and routed `InventoryTab` props through it before reading `inventory`, `onAddItem`, `onUpdateQuantity`, or `quickActionIntent`.
- Malformed `onAddItem` and `onUpdateQuantity` callbacks now fall back to safe async no-ops before create submit or inline quantity update handlers invoke them.
- This prevents direct/test/reuse callers from throwing during inventory render or mutation setup while preserving inventory row normalization, Korean empty-state/form copy, async save locks, mounted-state cleanup, validation wiring, and existing dashboard inventory behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` and `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs` coverage for safe inventory tab option and callback normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/empty-state-wiring.test.mjs src/lib/home-market-copy.test.mjs` passed 69/69, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build, and path-limited `git diff --check` passed with CRLF warnings only.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1154 Schedule tab prop and mutation-callback hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`: added `normalizeScheduleTabOptions()` and routed `ScheduleTab` props through it before reading `events`, `onCreateEvent`, `onToggleEvent`, or `quickActionIntent`.
- Malformed `onCreateEvent` and `onToggleEvent` callbacks now fall back to safe async no-ops before create submit or completion-toggle handlers invoke them.
- This prevents direct/test/reuse callers from throwing during schedule render or mutation setup while preserving event payload normalization, Korean calendar/form copy, async save locks, mounted-state cleanup, validation wiring, countdown labels, and existing dashboard schedule behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/tab-header-accessibility.test.mjs` and `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` coverage for safe schedule tab option and callback normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/tab-header-accessibility.test.mjs src/lib/empty-state-wiring.test.mjs` passed 26/26, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build, and path-limited `git diff --check` passed with CRLF warnings only.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1157 Feed tab prop and mutation-callback hardening.
- Changed `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`: added `normalizeFeedTabOptions()` and routed `FeedTab` props through it before reading `cattle`, `feedStandards`, `feedHistory`, `buildings`, or `onRecordFeed`.
- Malformed `onRecordFeed` callbacks now fall back to a safe async no-op before submit handling.
- This prevents direct/test/reuse callers from throwing during feed render or mutation setup while preserving existing cattle/feed/building payload normalization, feed aggregation, Korean feed copy, async save locks, mounted-state cleanup, validation wiring, chart labeling, and dashboard feed behavior.
- Strengthened `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` coverage for safe feed tab option and callback normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/empty-state-wiring.test.mjs` passed 18/18, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1193 Notification action cattle DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/notification.js`: added `isNotificationActionCattleRow()` and `normalizeNotificationActionCattleRows()`, then routed live `prisma.cattle.findMany()` results through the normalizer before `buildNotifications()`.
- This prevents direct/action/reuse callers from feeding non-array DB/mock results or array-shaped cattle rows into notification generation while preserving authenticated server action behavior, fresh read-model cache reuse, notification summary persistence, existing Korean fallback behavior, estrus/calving notification builder semantics, and dashboard notification consumers.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe notification cattle row normalization.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 9/9, `npm.cmd test` passed 497/497, `npm.cmd run lint` passed clean, `npm.cmd run build` passed, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- Continued active Hanwoo quality uplift with T-1194 Raw diagnostics server-action DB row hardening.
- Changed `projects/hanwoo-dashboard/src/lib/actions/system.js`: added `isRawDataActionRow()` and `normalizeRawDataActionRows()`, then routed dynamic model `prisma[modelName].findMany()` results through the normalizer before returning raw diagnostics data.
- This prevents direct/action/reuse callers from receiving non-array DB/mock results or array-shaped rows from `getRawData()` while preserving authenticated server action behavior, allowed-model enforcement, existing Korean diagnostics failure copy, the 50-row diagnostic limit, created-date ordering semantics, and diagnostics page safe rendering.
- Strengthened `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` coverage for safe raw diagnostics row normalization.
- Fixed a stale source assertion in `projects/hanwoo-dashboard/src/lib/ai-insight-widget-copy.test.mjs` so it now verifies the current Redis-aware async cache route contract (`loadCachedInsight`, `dropCachedInsight`, `saveCachedInsight`) instead of obsolete sync helper calls; this restored the full suite after it exposed the mismatch.
- Verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs src/lib/diagnostics-copy.test.mjs` passed 15/15, `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-insight-widget-copy.test.mjs` passed 14/14, `npm.cmd test` passed 503/503, `npm.cmd run lint` passed clean, `npm.cmd run build` passed after one transient Next build-lock retry, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build.
- Known build warning observed: Supabase Prisma `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, consistent with T-251 external credential/control-plane blocker.

## 2026-05-28 - Codex

- 추가로 T-251 외부 블로커 성격을 좁히기 위해 live 연결 문자열 대체 패턴을 테스트했습니다.
- `DATABASE_URL`을 `postgres:...@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres`로 바꿔 `npm.cmd run db:prisma7-test -- --live` 실행 시 `P2010` `XX000` `Message: (ENOIDENTIFIER) no tenant identifier provided (external_id or sni_hostname required)`가 발생했습니다.
- `db.fuemeqmigptwfzqvrpjf.supabase.co` 직접 호스트 DNS 조회는 실패했고, `db.fuemeqmigptwfzqvrpjf` 기반 풀커넥터 주소 자체가 현재 Supabase 호스팅에서 해석되지 않았습니다.
- 위 결과로 현재 `tenant/user postgres.fuemeqmigptwfzqvrpjf` 식별자가 잘못됐거나 제어면 동기화 불일치 상태임이 재확인되어, 사용자 소유 작업(T-251) 범주(비밀번호/DB URL 재동기화)로 결론이 유지됩니다.

## 2026-05-28 - Codex

- Added final continuation verification pass for the remaining active blocker. `npm.cmd run db:prisma7-test -- --live` in `projects/hanwoo-dashboard` re-ran as `15 passed, 1 failed`.
- Failure is unchanged: `PrismaClientKnownRequestError P2010` with `driverAdapterError` `Code: XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found` at `Connection health`.
- Verified `.env` still points to `postgresql://postgres.fuemeqmigptwfzqvrpjf:...@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres`; no local-side fix path exists until Supabase credentials are resynced by user.
- Ran `python execution/session_orient.py --json`; it still reports T-251 as the only TODO (`todo=1`) and no code-path tasks in progress.
- Ran `python execution/handoff_rotator.py --check`; it returned noop (`kept=518`, no archive needed yet).

## 2026-06-04 - Codex

- Completed T-1209 Hermes command/path recovery and Grok OAuth prep.
- Added stable command shims outside the repo at `%APPDATA%\npm\hermes.cmd`, `%APPDATA%\npm\hermes-agent.cmd`, and `%APPDATA%\npm\hermes-acp.cmd` pointing to the Hermes venv executables.
- Updated the current PowerShell profile outside the repo at `%USERPROFILE%\OneDrive\문서\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` to prepend `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts` when present.
- Verified `hermes --version` resolves and reports Hermes Agent v0.15.1, and `hermes doctor` runs.
- Set Hermes config outside the repo at `%LOCALAPPDATA%\hermes\config.yaml` to `model.provider=xai-oauth`, `model.default=grok-4.3`, and `model.base_url=https://api.x.ai/v1`.
- Started a visible PowerShell OAuth flow with `hermes auth add xai-oauth --timeout 900; hermes auth status xai-oauth`, but current verification still reports `xai-oauth: logged out` until the user completes browser approval.
- Existing unrelated `projects/knowledge-dashboard` worktree changes were left untouched.

## 2026-06-04 - Codex

- Completed T-1210 auto-research skill creation for the user request to turn the Karpathy autoresearch/self-improvement loop into a reusable skill.
- Commit: `aae01277` (`feat(skills): T-1210 add auto-research loop skill`).
- Added `.agents/skills/auto-research/SKILL.md` with a bounded research -> implement -> verify -> A/B compare -> adopt/revert -> record workflow, including GitHub PR/dependency triage and browser/app-click QA gates.
- Added `.agents/skills/auto-research/references/karpathy-autoresearch.md` and `references/loop-contract.md` to separate the source concept, product adaptation, evidence manifest, adoption gate, UI smoke, and GitHub triage rules from the lean skill body.
- Added deterministic helpers: `.agents/skills/auto-research/scripts/ab_decision.py` for weighted baseline/candidate scoring and `.agents/skills/auto-research/scripts/github_project_inventory.py` for local project, workflow, Dependabot, and open PR inventory.
- Fixed `.agents/skills/skill-creator/scripts/quick_validate.py` to read `SKILL.md` using UTF-8 after default Windows CP949 decoding failed on Korean trigger text in the new skill.
- Verification: `python .agents/skills/skill-creator/scripts/quick_validate.py .agents/skills/auto-research` passed; `python -m py_compile` passed for both new scripts and the validator; inline `ab_decision.decide(...)` returned `adopt_candidate`; `python .agents/skills/auto-research/scripts/github_project_inventory.py --root . --include-prs` ran and found 7 local project surfaces plus 27 open PRs (18 BLOCKED, 26 Dependabot); scoped `git diff --check -- .agents/skills/auto-research .agents/skills/skill-creator/scripts/quick_validate.py` exited 0 with a CRLF warning only.
- Boundary: existing unrelated `projects/knowledge-dashboard` dirty-tree work was left untouched. `main` is still ahead of origin, so any push would publish pending ahead commits too.
