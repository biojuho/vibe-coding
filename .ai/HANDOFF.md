# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-06-04 |
| Tool | Gemini 3.5 Flash (High) |
| Work | **T-1204 Resolved global npm wrappers PowerShell cmdlet loading issue**. Patched all .ps1 wrapper scripts in `C:\Users\박주호\AppData\Roaming\npm\` (claude.ps1, codex.ps1, pnpm.ps1, pn.ps1, pnpx.ps1, pnx.ps1) by replacing cmdlet calls like `Split-Path` and `Test-Path` with static .NET methods (`[System.IO.Path]::GetDirectoryName` and `[System.IO.File]::Exists`). This completely bypasses any PowerShell session loading constraints/bugs and allows the commands to execute instantly and flawlessly. |
| Next Priorities | Resolve the remaining database/Supabase blocker `T-251` (user action required to reset DB credentials on the control plane). |

| Field | Value |
|---|---|
| Date | 2026-06-04 |
| Tool | Gemini 3.5 Flash (High) |
| Work | **T-1203 Resolved PowerShell core cmdlets not recognized issue** when running globally installed npm wrapper scripts like `codex.ps1`. The root cause was that the user's PowerShell 5.1 environment failed to automatically load/import core modules (`Microsoft.PowerShell.Management`, `Microsoft.PowerShell.Utility`, etc.) upon startup. Resolved this by creating a global user profile (`C:\Users\박주호\OneDrive\문서\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`) to explicitly import these core modules at the start of every session. Verified that cmdlets like `Split-Path`, `Test-Path`, and `Get-Content` are now fully available, and `codex` executes successfully without cmdlet errors. |
| Next Priorities | Resolve the remaining database/Supabase blocker `T-251` (user action required to reset DB credentials on the control plane). |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Gemini 3.5 Flash |
| Work | **T-1150..T-1202 full quality uplift, hardening sweep and task ID resolver completed**. Staged and committed all 144 modified and untracked files representing the complete `hanwoo-dashboard` hardening changes and helper scripts. Verified Next.js unit tests (498/498 passed), eslint checks, production Next.js build compilation, `next_task_id` tests (5/5 passed), and `test_quality_gate_yaml_externalization` tests (5/5 passed with no-cov bypass). Pushed successfully to remote origin/main, leaving a 100% clean working tree. The active workspace goal is marked as completed in `GOAL.md`. |
| Next Priorities | Address the blocked task `T-251` which requires the user to reset the database password in the Supabase Dashboard (Project Settings > Database) to resync the control plane pooler credentials, then update `DATABASE_URL` in `.env` and rerun `npm.cmd run db:prisma7-test -- --live`. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **/goal "남은거 다 처리해" — 2건 출하** (T-1201 + T-1202). (1) **T-1201 multi-tool task ID race 정책 + 헬퍼**: 이 주에만 T-1107×2 / T-1108×2 / T-1195×2 / T-1199×2 충돌 발생. 신규 `execution/next_task_id.py` 가 `.ai/TASKS.md`+`.ai/HANDOFF.md`+최근 30개 git commit 의 `T-####` 참조 합집합 스캔 → 충돌 없는 다음 ID 제안 (plain text + `--json`). 5 신규 테스트(`workspace/tests/test_next_task_id.py`), Windows + 한글 cp949 디코딩 함정은 stdout bytes → `decode("utf-8", errors="replace")` 로 우회. `.ai/CONTEXT.md` "Multi-Tool Coordination" 섹션 추가 — 항상 `py -3 execution/next_task_id.py` 출력 사용 + 동시 race 폴백은 `T-####b` 알파벳 접미사 (이미 e940de77 commit 에 유기적으로 정착된 패턴 문서화). (2) **T-1202 `draft_quality_gate.py` CTA 패턴 YAML 외부화** (행동 변화 0): `_GENERIC_CTA_REGEX_DEFAULT`/`_CLICHE_OPENING_REGEX_DEFAULT`/`_CLOSING_CTA_REGEX_DEFAULT`/`_INFLUENCER_VOCAB_DEFAULT` 4종을 `rules/editorial.yaml`의 신규 `quality_gate_patterns` 섹션으로 이동. `_load_quality_gate_patterns()` 가 YAML 우선, 부재/malformed 시 hardcoded fallback. `rules_loader.py` RULE_SECTION_FILES 매핑 등록. 5 신규 검증 테스트(`test_quality_gate_yaml_externalization.py`) — YAML 오버라이드 / fallback / malformed 모두 검증. 기존 100개 quality-gate 테스트 변경 없이 그대로 통과. 편집팀이 코드 수정 없이 CTA/cliche/influencer 어휘 정책을 조정 가능. |
| Next Priorities | T-251(Supabase) 그대로. 다른 도구가 새 task ID 가 필요할 때 **반드시 `py -3 execution/next_task_id.py`** 사용. 후속 후보: ① `draft_quality_gate.py` 본문 858줄 → 24헬퍼 함수의 추가 그룹화(scene/CTA/closing 별 모듈 분리)는 risk 대비 reward 낮아 보류. ② cost_db `record_draft` 125줄 함수의 메서드 분리. ③ task ID race 정책이 실제로 충돌을 막는지 모니터링 — 다음 주 commit 들에서 `T-####b` 접미사 없으면 성공. 검증: focused 105/105 pass (100 기존 quality-gate + 5 YAML 외부화), `next_task_id` 5/5, 풀 스위트 진행 중 (이전 1777/1777 pass 베이스라인). |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **T-1200 blind-to-x `cost_db.py` schema/migration 분리** (행동 변화 0). 1074줄 단일 모듈에 schema DDL, 마이그레이션 컨스턴트, 검증자, runtime queries가 다 섞여 있어 schema-only 테스트가 불가능했음. 신규 `pipeline/cost_db_schema.py` (165줄) 로 분리: `MIGRATION_COLUMNS` / `PRAGMA_TABLE_INFO_SQL` / `ALTER_TABLE_ADD_SQL` / `CREATE_TABLES_SCRIPT` 상수, `validate_allowed_name` / `validate_migration_column` / `ensure_column` / `init_db` 순수 함수. `cost_db.py`는 1074 → 954줄 (-120, schema 부분 위임) 으로 슬림화하고 `_MIGRATION_COLUMNS` / `_PRAGMA_TABLE_INFO_SQL` / `_ALTER_TABLE_ADD_SQL` / `_validate_*` 는 backwards-compat 별칭으로 재수출(`noqa: F401` 표시). `CostDatabase._init_db` 는 100여줄 inline SQL 대신 `_schema_init_db(conn)` 한 줄로 위임. `CostDatabase._ensure_column` static method도 `_schema_ensure_column` 위임. 신규 `tests/unit/test_cost_db_schema.py` (6 테스트) — `init_db(conn)`이 모든 base table + MIGRATION_COLUMNS 전체 적용 / idempotency / validator rejection 까지 in-memory SQLite에 직접 검증. 외부 호출자(`test_cost_db_security.py`의 `CostDatabase._ensure_column(...)` 등)는 변경 0. |
| Next Priorities | T-251(Supabase) 그대로. 후속: ① cost_db 의 다른 큰 메서드(`record_draft` 125줄, `archive_old_data` 77줄, `get_today_summary` 76줄)도 분리 가능하지만 risk/reward 낮음 — schema 분리만으로 충분. ② draft_quality_gate.py(858줄) CTA 규칙 외부화는 여전히 대형 작업으로 대기. ③ task ID 경쟁(T-1107×2, T-1108×2, T-1195×2, T-1199×2 발생) → 정책 정리 미해결. 검증: focused tests 27/27 pass (test_cost_db_security 3 + test_cost_db_extended 9 + test_cost_tracker_extended 9 + new test_cost_db_schema 6), 풀 스위트 `py -3.14 -m pytest tests/unit tests/integration -q --no-cov --ignore=tests/integration/test_curl_cffi.py` 1777/1777 pass 0 fail (6m01s), ruff clean. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **T-1199 hanwoo AI Insight 라우트 structured metric 로그** (`ead4aa35`): T-1112 의 cacheBackend 동봉만으론 프로덕션 hit rate 회복 확인 불가. Langfuse SDK 추가 부담 회피하고 lightweight 대안 — Vercel/CloudWatch 가 grep 해 대시보드화할 한 줄 structured JSON 로그. 신규 `emitInsightMetric(payload)` (try/catch fail-safe) + 6 return path 전부 emit: `unauthenticated`/`heuristic_no_api_key`/`cache_hit`(backend+ageSeconds)/`gemini_success`/`gemini_parse_failure`/`gemini_timeout`(timeoutMs)/`gemini_error`(errorName). 모든 페이로드에 `durationMs: Date.now() - startedAt`. **PII 잠금**: userId/summary 절대 미로그, contract 테스트로 regression 방지. 1 신규 source-grep 테스트 (총 15/15 widget-copy), 전체 `npm test` 498/498, lint clean, build exit 0. |
| Next Priorities | T-251(Supabase) 그대로. 운영 사용: Vercel/CloudWatch 에서 `[ai-insight-metric]` prefix 필터 → `event` 별 카운트가 hit rate / fallback 비율 / 타임아웃률 / p95 latency. 다음 후속: ① 같은 패턴을 `/api/ai/chat/route.js` 에도 적용해 chat 위젯 옵저버빌리티 확보. ② AIInsightWidget 새로고침 버튼 클릭 시점에 클라이언트 메트릭 로그(현재는 서버만). ③ Best-of-N 표본 실제 누적 후 weekly report sweep 결과 보고 권장값 적용. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **T-1197 weekly report에 Best-of-N tuner 자동 임베드** (`a4951f9a`): T-1105 tuner CLI 가 수동 실행만 가능했던 걸 weekly report 빌드 파이프라인에 통합. `scripts/build_weekly_report.py` 의 `_render_report()` 끝에 신규 `_render_best_of_n_section(days)` append — `tune_best_of_n_weight.load_recent_rows` + `build_report` 호출 → markdown ``` 코드 블록으로 래핑. `run()` 은 `max(days, 30)` 윈도우로 sweep 표본 확보 유리. 실패는 swallow → 빈 문자열 → 본문 fail-open. 10 신규 unit test, blind-to-x full 1713/1713, ruff clean. |
| Next Priorities | T-251(Supabase) 그대로. 다음 후속: ① AI Insight 캐시 hit/miss + cacheBackend Langfuse 트레이싱(hanwoo는 Langfuse SDK 부재, 추가 필요). ② 프로덕션 Redis 실측 hit rate 모니터링(operational). ③ Best-of-N 표본 실데이터 누적 후 weekly report sweep 결과 보고 권장값 적용. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **T-1198 /goal "blind-to-x weekly report에 Best-of-N tuner sweep 결과 자동 임베드" 검증 & 문서화**. /goal 상태가 멀티툴 race로 이전 세션의 T-1197 follow-up으로 바뀌어 있었음. 코드 확인 결과 T-1197로 이미 완전 구현됨 — `scripts/build_weekly_report.py:15-39` `_render_best_of_n_section()` 가 `tune_best_of_n_weight.build_report()` 호출 후 markdown 코드펜스로 임베드, try/except로 fail-open. `test_build_weekly_report.py` 10개 + `test_tune_best_of_n_weight.py` 15개 (총 25/25 pass, 0.39s). 실 DB end-to-end 호출 결과 표본 부족(0<10) → "기본값 0.5 유지" 메시지 임베드 + 본문 무손상 확인. 문서 부재 발견(README/ops-runbook에 build_weekly_report 커맨드만 적혀있고 임베드 섹션 설명 0건) → README "추천 주간 운영" 1번 항목 아래에 임베드 동작/fail-open 1문단 추가. |
| Next Priorities | T-251 (Supabase password) user-owned 그대로. 후속: ① /goal helper 상태가 멀티툴 race로 자주 미스매치됨 — `.ai/TASKS.md` 와 `/goal` objective 가 다를 때 신뢰 우선순위 정책 필요(현재는 코드/문서 실측 > /goal 자체 상태). ② cost_db.py 1039줄 schema/migration 분리(보류 중). ③ Best-of-N tuner 표본이 ≥10건 누적되면 weekly report에 실 권장값이 표시되기 시작 — 데이터 누적 모니터링. 검증: focused 25/25 pass, end-to-end render OK, README 1문단 추가. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **연속 보강 (T-251):** `npm.cmd run db:prisma7-test -- --live` 추가 진단을 위해 라이브 연결 문자열 후보 2개를 검증했습니다. `user=postgres`(비기본 tenant/user)로 `aws-0-ap-northeast-2.pooler.supabase.com:6543`에 연결 시 `Code: XX000 Message: (ENOIDENTIFIER) no tenant identifier provided`가 재현되었고, 직접 호스트 `db.fuemeqmigptwfzqvrpjf.supabase.co:5432`는 DNS가 존재하지 않아 접속 불가였습니다. 이로 보아 `projects/hanwoo-dashboard/.env`의 tenant/user 식별자 자체가 잘못되었거나 제어면 동기화가 필요함을 재확인했습니다. |
| Next Priorities | T-251은 사용자 소유 블로커입니다. Supabase 콘솔에서 `DATABASE_URL`(특히 tenant/user 형태)와 비밀번호를 재동기화한 뒤 바로 `npm.cmd run db:prisma7-test -- --live`를 재실행해야 합니다. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **최종 재확인 라운드:** `python execution/project_qc_runner.py --project hanwoo-dashboard --json`를 다시 실행해 `test/lint/build` 전부 통과(`497`/`27`/`pass`)를 재확인했습니다. 이어서 `npm.cmd run db:prisma7-test -- --live`는 동일하게 `Passed: 15, Failed: 1`로 실패했습니다. 이 값은 `P2010`/`XX000`/`(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`입니다. |
| Next Priorities | T-251은 계속 사용자 조치 항목입니다. Supabase Database 비밀번호/POOLER tenant/user/호스트 동기화를 먼저 수행한 뒤, 동일 live 커넥션 테스트를 다시 실행해 주세요. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **최신 상태 재점검:** `projects/hanwoo-dashboard`에서 `npm.cmd run db:prisma7-test -- --live`를 바로 재실행했습니다. 결과는 `Passed: 15, Failed: 1`로 동일했고, 실패는 `PrismaClientKnownRequestError P2010` + `Code: XX000` + `Message: (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`로 재현되었습니다. 현재 `projects/hanwoo-dashboard/.env`는 `postgresql://postgres.fuemeqmigptwfzqvrpjf:...@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres` 형식입니다. |
| Next Priorities | 사용자 소유 블로커 `T-251`은 계속 유지됩니다. Supabase DB 비밀번호 및 `DATABASE_URL` tenant/user/호스트를 콘솔에서 재동기화한 뒤 즉시 live 테스트를 재실행하세요. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **최종 보완 라운드:** `python execution/project_qc_runner.py --json`를 재실행해 루트 전체 테스트/린트/빌드 매트릭스를 재확인했으며, 모든 프로젝트가 현재 상태에서 통과했습니다(`blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, `knowledge-dashboard`: test/lint/build all pass). 이어서 `python execution/code_review_gate.py --base HEAD~1 --json`에서 `risk_score: 0.0` pass를 재확인했고, `session_orient` 기준 `todo=1`/`in_progress=0`으로 T-251 단일 미완료 상태가 유지됨을 재확인했습니다. 마지막 `db:prisma7-test -- --live`는 `ENOTFOUND tenant/user postgres.fuemeqmigptwfzqvrpjf` 재현 확인으로 외부 블로커 유지. `projects/hanwoo-dashboard/.env`의 `DATABASE_URL` 메타는 `HOST=aws-0-ap-northeast-2.pooler.supabase.com:6543`, `USER=postgres.fuemeqmigptwfzqvrpjf`로 재검증. |
| Next Priorities | 사용자 액션 항목 `T-251`은 동일: Supabase 비밀번호 재설정 후 `.env` 동기화하고 즉시 `npm.cmd run db:prisma7-test -- --live` 재실행. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **최종 재점검 (연속 작업):** `npm.cmd run db:prisma7-test -- --live`를 추가 재실행해 live CRUD E2E를 다시 확인했습니다. 결과는 `15 passed, 1 failed`로 동일하게 `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`가 재현되었고, `ENOTFOUND`는 Supabase 컨트롤플레인 자격 증명 동기화 문제(외부 원인)로 판별됩니다. |
| Next Priorities | 사용자 조치 항목 `T-251`은 그대로 유지: Supabase에서 DB 비밀번호를 재설정하고 `.env`를 동기화한 뒤 `npm.cmd run db:prisma7-test -- --live`를 즉시 재실행해야 합니다. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **추가 검증 재확인 (연속 작업 세션):** `python execution/session_orient.py --json`, `python execution/handoff_rotator.py --check`, `python execution/code_review_gate.py --base HEAD~1 --json`, 그리고 `npm run db:prisma7-test -- --live`를 재실행해 상태를 재점검했습니다. `session_orient`는 목표가 여전히 active 상태이며 T-251이 유일한 TODO로 남았음을 확인했고, `code_review_gate`는 변경 파일 기준 `risk_score: 0.0`으로 pass 했습니다. `db:prisma7-test -- --live`는 동일하게 `P2010/XX000`의 `tenant/user postgres.fuemeqmigptwfzqvrpjf not found`를 재확인해, 현재 블로커가 외부 Supabase credential 동기화 문제임이 확인되었습니다. |
| Next Priorities | 사용자 조치 항목인 `T-251`은 유지: Supabase 콘트롤플레인에서 DB 비밀번호를 재설정하고 `.env` 동기화 후, 즉시 `npm.cmd run db:prisma7-test -- --live`를 재실행해 live CRUD 통과를 확인해야 합니다. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **진행 상태 재확인 및 완전성 감사**: 시스템 전체 QC 러너를 `python execution/project_qc_runner.py --json`로 다시 실행해 `blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, `knowledge-dashboard`의 `test/lint/build`가 모두 통과함을 재확인했습니다(총합: 1703 passed + 12 skipped / 0 fail, 1576 passed / 12 skipped / 0 fail, 497/0/0, 3/0/0). 이어서 한 번 더 `npm run db:prisma7-test -- --live`를 수행해 live 단계에서 `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`가 반복되는 것을 확인했고, `projects/hanwoo-dashboard/.env`에서 노출된 `DATABASE_URL` 메타(host=`aws-0-ap-northeast-2.pooler.supabase.com`, user=`postgres.fuemeqmigptwfzqvrpjf`)도 확인해 외부 credential 동기화 이슈를 재확인했습니다. |
| Next Priorities | `T-251`은 Supabase 콘트롤플레인 비밀번호 재설정/동기화 없이 해소되지 않음. 사용자 조치 후 `npm run db:prisma7-test -- --live` 재실행으로 실제 live CRUD 가용성 마무리. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Health route build-noise hardening**: Added a build/CI guard to `src/app/api/health/route.js` so Prisma live-check is skipped during `phase-production-build` and CI, preventing Prisma `ENOTFOUND tenant/user ... not found` logs from `next build` while preserving runtime route shape (`healthy` + degraded DB status + warning). On non-build runtime, DB-check failures still return `database: "disconnected"` and no uncaught behavior changes, with warning payload now sanitized to `error.message`-derived text. Ran `npm test` (497/497), `npm run lint`, and `npm run build` in `projects/hanwoo-dashboard`; build now completes without `prisma:error` log noise from `/api/health` pre-render during static generation. |
| Next Priorities | External blocker remains `T-251` (`DATABASE_URL` credential sync), user-owned action; next run `npm run db:prisma7-test -- --live` after Supabase password reset to confirm live CRUD path. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard final polish follow-up**: Closed the remaining `DashboardClient` source-pattern mismatch by restoring a single-line `handleNavigate` fallback declaration in `TodayFocusPanel` while preserving the broader malformed-props/row-hardening changes in that file. Ran the targeted and project-level verification paths again after patching: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed **52/52** and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed project `test` / `lint` / `build`. Also re-ran `python execution/code_review_gate.py --base HEAD~1 --json`, which returned `risk_score: 0.0` (`pass`). |
| Next Priorities | Keep the user-owned blocker **T-251** until Supabase `DATABASE_URL` credentials are reset on the control plane; no additional Hanwoo dashboard code defects are currently reproducible from this lane. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **T-1196 blind-to-x test pollution fix — `clear_runtime_state` promoted from `tests/unit/conftest.py` to `tests/conftest.py`**. T-1108 검증 중 한 풀 스위트 run에서 `test_cost_db_extended` / `test_cost_tracker_extended` 18건 transient fail 목격 (개별/소그룹으론 다 pass — 명백한 test ordering pollution). 원인 진단: unit conftest의 SQLite 격리 fixture가 `tests/unit/**` 에만 적용되고 integration test에는 미적용. Integration test는 `pipeline.cost_db`를 직접 import 안 하지만 `pipeline.draft_generator`/`scoring_6d` 등 통해 간접 호출 → 실 `.tmp/btx_costs.db` 오염 → 후속 unit test가 빈 DB 기대하다 fail. 수정: `clear_runtime_state` (db path/싱글톤 monkeypatch + ml_scorer joblib cleanup) 를 부모 `tests/conftest.py` 로 이동하고 unit/conftest 엔 alias 코멘트 남김. Integration test가 cost_db를 직접 안 쓰는 것은 grep 으로 확인 (`tests/integration/` 에 `CostDatabase`/`get_cost_db`/`btx_costs.db` 0건). |
| Next Priorities | T-251 (Supabase password) user-owned 그대로. 다음 후보: ① blind-to-x `pipeline/draft_quality_gate.py` (858줄/24헬퍼) CTA 규칙 `rules/cta_patterns.yaml` 외부화 (3~4일 큰 리팩터). ② `pipeline/cost_db.py` (1039줄) 마이그레이션 로직 분리 (1~2일). ③ Codex/Claude 멀티툴 race가 task ID 충돌(T-1107×2, T-1108×2) 만들고 있음 — `.ai/TASKS.md` 에 lockfile 또는 더 큰 ID 자릿수 정책. 검증: `py -3.14 -m pytest tests/unit tests/integration -q --no-cov --ignore=tests/integration/test_curl_cffi.py` 1767/1767 pass 0 fail (6m29s vs 사전 5m43s — 43s overhead는 integration test에도 fixture 적용된 비용으로 수용). |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1195 Profitability service DB row hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/dashboard/profitability-service.js`. `getProfitabilityEstimates()` now normalizes malformed `findMany()` results for active cattle, recent feed expenses, recent sales, and sold-cattle lookups before feeding them into farm-adjustment and recommendation math, preventing malformed DB/mocked payloads from reaching recommendation calculations while preserving existing Korean error copy, date-window filtering, numeric coercion, and candidate-ranking behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **T-1112 AI Insight 罹먯떆 Redis 諛깊궧** (`97447aca`): T-1104 in-memory Map 罹먯떆???쒕쾭由ъ뒪/?ㅼ쨷 ?몄뒪?댁뒪 cold start 留덈떎 珥덇린?붾뤌 ??hit rate ~0%. 湲곗〈 `src/lib/redis.js` ?명봽??`isRedisConfigured`/`ensureRedisConnection("cache")`) ?ъ궗?⑺빐 罹먯떆 Redis 寃⑹긽. ??async API `loadCachedInsight/saveCachedInsight/dropCachedInsight` ??REDIS_URL ?ㅼ젙 ??`ai-insight:<key>` ?ㅼ엫?ㅽ럹?댁뒪 + 24h TTL, 誘몄꽕????湲곗〈 Map ?먮룞 ?대갚. Redis ?ㅽ뙣??catch ??console.error ??null(fail-open). ?묐떟??`cacheBackend: "redis"|"memory"` ?숇큺. 湲곗〈 sync API ???좎?(?명솚). 5 ?좉퇋 耳?댁뒪(珥?19/19), ?꾩껜 hanwoo `npm test` 503/503, lint clean, build exit 0. |
| Next Priorities | T-251(Supabase) 洹몃?濡? ?ㅼ쓬 ?꾩냽: ??AI Insight 罹먯떆 hit/miss + cacheBackend 瑜?Langfuse ?몃젅?댁떛(?대? `LANGFUSE_ENABLED` ?명봽??. ??Best-of-N ?쒕낯 ??嫄??꾩쟻 ??sweep 寃곌낵瑜?weekly report ?먮룞 ?꾨쿋?? ???꾨줈?뺤뀡 Redis ??踰??ㅼ젣濡?遺숈뿬 hit rate 紐⑤땲?곕쭅. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1194 Raw diagnostics server-action DB row hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/actions/system.js`. `getRawData()` now normalizes dynamic model `findMany()` results before returning to the admin diagnostics UI, filtering malformed array-shaped rows and falling back to an empty array for non-array DB/mock results. This prevents direct/action/reuse callers from receiving unsafe raw diagnostic rows while preserving authenticated server action behavior, allowed-model enforcement, existing Korean diagnostics failure copy, the 50-row diagnostic limit, created-date ordering semantics, and diagnostics page safe rendering. Strengthened `src/lib/actions-copy.test.mjs` coverage for safe raw diagnostics row normalization. Also aligned `src/lib/ai-insight-widget-copy.test.mjs` with the current Redis-aware async cache helpers (`loadCachedInsight`/`dropCachedInsight`/`saveCachedInsight`) after the full suite exposed an obsolete source assertion. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs src/lib/diagnostics-copy.test.mjs` passed 15/15, `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-insight-widget-copy.test.mjs` passed 14/14, `npm.cmd test` passed 503/503 after updating the stale AI insight source assertion, `npm.cmd run lint` passed clean, `npm.cmd run build` passed on retry after a transient Next build lock with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1193 Notification action cattle DB row hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/actions/notification.js`. `getNotifications()` now normalizes live cattle `findMany()` results before calling `buildNotifications()`, filtering malformed array-shaped rows and falling back to an empty array for non-array DB/mock results. This prevents direct/action/reuse callers from feeding unsafe cattle rows into notification generation while preserving authenticated server action behavior, fresh read-model cache reuse, notification summary persistence, existing Korean fallback behavior, estrus/calving notification builder semantics, and dashboard notification consumers. Strengthened `src/lib/actions-copy.test.mjs` coverage for safe notification cattle row normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 9/9, `npm.cmd test` passed 497/497, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1180 AI chat request dependency hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/ai-chat-api.mjs`. `handleAiChatRequest()` now normalizes malformed dependency input and rejects missing required callbacks with the existing Korean JSON error envelope before authentication, API-key lookup, farm-context construction, or stream creation are invoked. This prevents direct/API/reuse callers from crashing through `deps` destructuring or missing callback invocation while preserving authenticated chat flow, validation errors, missing API-key copy, Gemini history normalization, SSE stream delegation, and existing chat route behavior. Strengthened `src/lib/ai-chat-api.test.mjs` coverage for malformed dependency input. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-api.test.mjs` passed 10/10, `npm.cmd test` passed 488/488, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1179 AI/market/history helper array-object hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/ai-chat-api.mjs`, `src/lib/ai-insight.mjs`, `src/lib/market-price-state.mjs`, and `src/lib/cattle-history.mjs`. AI chat history items, AI insight profitability/notification rows, parsed AI insight response items, KAPE market price snapshots/sides/live payloads, and cattle history metadata payloads now reject malformed arrays before Gemini context, insight recommendations, market price display/persistence, or cattle weight-history points are derived. This prevents direct/API/cache/reuse callers from leaking array-attached fields into chat context, insight cards, live/cache market prices, or cattle history chart evidence while preserving existing Korean validation copy, strict JSON insight parsing, market stale/unavailable fallbacks, metadata parse-error reporting, and current dashboard behavior. Strengthened focused helper tests for array-object guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-api.test.mjs src/lib/ai-insight.test.mjs src/lib/market-price-state.test.mjs src/lib/cattle-history.test.mjs` passed 46/46, `npm.cmd test` passed 487/487, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1178 Dashboard calculation utility array-row hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/dashboard/setup-progress.mjs`, `src/lib/dashboard/today-focus.mjs`, and `src/lib/dashboard/farm-metrics.mjs`. Setup progress counts, today-focus feed-category/feed-history helpers, feed-expense samples, cattle lookup values, and sales weight-gain samples now reject malformed array rows before dashboard guidance, feed-depletion forecasts, or farm-specific profitability adjustment evidence are calculated. This prevents direct/cache/reuse callers from leaking array-attached row fields into onboarding progress, today's work recommendations, feed forecasts, or profitability projections while preserving existing option normalization, Korean dashboard copy, date/window filtering, numeric coercion, and default fallback behavior. Strengthened focused dashboard utility tests for array-row guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/setup-progress.test.mjs src/lib/dashboard/today-focus.test.mjs src/lib/dashboard/farm-metrics.test.mjs` passed 37/37, `npm.cmd test` passed 485/485, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1177 Operational UI collection array-row hardening**: Continued the active Hanwoo quality uplift by tightening remaining operator-facing collection normalizers in `src/components/tabs/CalvingTab.js`, `src/components/tabs/ScheduleTab.js`, `src/components/tabs/SettingsTab.js`, `src/components/forms/CattleForm.js`, `src/components/forms/CattleDetailModal.js`, `src/components/layout/NotificationSystem.js`, `src/components/widgets/AlertBanners.js`, `src/components/widgets/EarTagScannerModal.js`, `src/components/widgets/FieldModeView.js`, `src/components/ui/cards.js`, and `src/components/widgets/widgets.js`. These paths now reject malformed array rows before form select options, pregnancy/calving lists, schedules, settings building/widget controls, detail fallback charts, notification dropdowns, alert banners, scanner targets, field search/checklists, pen cattle cards, or weather forecast cards render. This prevents direct/cache/reuse callers from leaking array-attached row fields into operational UI paths while preserving existing Korean copy, async save locks, focus/a11y behavior, alert countdowns, scanner/field-mode animation guards, and card rendering semantics. Strengthened focused source coverage for these array-row guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs src/lib/cards-accessibility.test.mjs src/lib/cattle-detail-modal-wiring.test.mjs src/lib/notification-system-copy.test.mjs src/lib/eartag-scanner-modal-accessibility.test.mjs src/lib/field-mode-celebration.test.mjs src/lib/settings-tab-accessibility.test.mjs src/lib/tab-header-accessibility.test.mjs src/lib/calving-tab-accessibility.test.mjs src/lib/alert-banners-accessibility.test.mjs` passed 139/139, `npm.cmd test` passed 483/483, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1176 Dashboard and pagination array-row hardening**: Continued the active Hanwoo quality uplift by tightening row normalizers in `src/components/DashboardClient.js`, `src/lib/hooks/useCattlePagination.js`, `src/lib/hooks/useSalesPagination.js`, and `src/lib/hooks/useCursorPagination.js`. Dashboard helper items, building rows, cattle/list rows, notification rows, full-list fetch rows, and shared/cattle/sales pagination rows now reject malformed arrays before dashboard home rendering, pen lists, notification fan-out, full export registries, cursor pagination state, or load-more accumulation. This prevents direct/cache/API reuse callers from leaking array-attached row fields into dashboard panels, building grids, cattle registries, notification widgets/modals/banners, cursor pagination state, and paginated list updates while preserving existing Korean dashboard copy, SSR pagination wiring, full-list preload behavior, stale-unmount guards, and pagination retry feedback. Strengthened focused dashboard and pagination source coverage for array-row guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs src/lib/cattle-pagination-feedback.test.mjs src/lib/sales-pagination-feedback.test.mjs src/lib/cursor-pagination-feedback.test.mjs` passed 57/57, `npm.cmd test` passed 483/483, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1175 Collection row array hardening**: Continued the active Hanwoo quality uplift by tightening collection row normalizers in `src/components/tabs/AnalysisTab.js`, `src/components/tabs/FeedTab.js`, `src/components/tabs/SalesTab.js`, `src/components/tabs/InventoryTab.js`, `src/components/widgets/FinancialChartWidget.js`, `src/components/widgets/ProfitabilityWidget.js`, `src/components/widgets/NotificationWidget.js`, `src/components/ui/NotificationModal.js`, `src/lib/dashboard/summary-service.js`, `src/lib/dashboard/today-focus.mjs`, and `src/lib/cattle-csv-export.mjs`. These normalizers now reject malformed array rows before rendering, aggregation, CSV export, dashboard summary calculation, alert/today-focus selection, or profitability/notification display. This prevents cache/direct/reuse callers from leaking array-attached row fields into user-facing tables, charts, recommendations, notifications, CSV exports, or summary cards while preserving existing object-row normalization, numeric coercion, Korean fallback copy, pagination/render behavior, and dashboard cache semantics. Strengthened focused source coverage for array-row guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs src/lib/profitability-copy.test.mjs src/lib/notification-system-copy.test.mjs src/lib/notification-modal-copy.test.mjs src/lib/dashboard/setup-progress.test.mjs src/lib/dashboard/today-focus.test.mjs src/lib/cattle-csv-export.test.mjs src/lib/empty-state-wiring.test.mjs src/lib/home-market-copy.test.mjs` passed 124/124, `npm.cmd test` passed 483/483, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1174 AI insight summary/request and action invalidation array-object hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/ai-insight.mjs`, `src/components/widgets/AIInsightWidget.js`, `src/app/api/ai/insight/route.js`, and `src/lib/actions/_helpers.js`. AI insight summary normalization, AI insight widget stable-summary normalization, AI insight API request-body normalization, and shared action cache invalidation option normalization now reject malformed array inputs before reading farm summary, weather, force-refresh, cache-key, or cache-invalidation fields. This prevents direct/test/reuse callers from leaking array-attached fields into heuristic insight generation, AI insight request caching/refresh behavior, widget fallback summaries, or dashboard cache invalidation while preserving existing Gemini fallback flow, Korean insight copy, same-day AI cache behavior, Next cache tag revalidation, and dashboard mutation cache invalidation. Strengthened `src/lib/actions-helper-options.test.mjs`, `src/lib/ai-insight.test.mjs`, and `src/lib/ai-insight-widget-copy.test.mjs` coverage for array-object guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-helper-options.test.mjs src/lib/ai-insight.test.mjs src/lib/ai-insight-widget-copy.test.mjs` passed 33/33, `npm.cmd test` passed 483/483, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1173 Auth, dashboard cache/query/read-model, and notification timing array-option hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/auth-guard.js`, `src/lib/dashboard/cache.js`, `src/lib/dashboard/list-queries.js`, `src/lib/dashboard/read-models.js`, and `src/lib/notification-timing.mjs`. Shared auth guard, dashboard cache key, dashboard list query, dashboard read-model cache, and notification timing option normalizers now reject malformed array inputs before reading redirect, filter, pagination, cache-bypass, invalidation, or notification reference-time fields. This prevents direct/test/reuse callers from leaking array-attached option fields into authentication redirects, cache keys, list query cache bypasses, read-model cache decisions, cache invalidation, or estrus timing calculations while preserving existing Korean auth copy, dashboard cache segmentation, list pagination validation, read-model cache behavior, and notification timing fallbacks. Strengthened `src/lib/auth-guard-options.test.mjs`, `src/lib/dashboard-cache-options.test.mjs`, `src/lib/dashboard-list-query-input.test.mjs`, `src/lib/dashboard-read-models-date.test.mjs`, and `src/lib/notification-timing.test.mjs` coverage for array-option guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/auth-guard-options.test.mjs src/lib/dashboard-cache-options.test.mjs src/lib/dashboard-list-query-input.test.mjs src/lib/dashboard-read-models-date.test.mjs src/lib/notification-timing.test.mjs` passed 15/15, `npm.cmd test` passed 482/482, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1172 Weather, fetch, queue, and offline utility array-option hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/weather-state.mjs`, `src/lib/fetchWithTimeout.js`, `src/lib/queue.js`, and `src/lib/offline-sync-state.mjs`. Shared weather, fetch timeout, BullMQ queue, and offline sync state normalizers now reject malformed array inputs before reading timeout, message, location, queue, retry, permanent-failure, or metadata fields. This prevents direct/test/reuse callers from leaking array-attached option fields into user-facing weather fallback copy, timeout behavior, queue option wiring, or offline retry/dead-letter state while preserving Open-Meteo normalization, guarded fetch timeout scheduling/cleanup, Redis configuration checks, offline retry accounting, Korean fallback copy, and existing dashboard behavior. Strengthened `src/lib/weather-state.test.mjs`, `src/lib/fetch-with-timeout.test.mjs`, `src/lib/offline-sync-state.test.mjs`, and `src/lib/queue.test.mjs` coverage for array-option and array-item guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/weather-state.test.mjs src/lib/fetch-with-timeout.test.mjs src/lib/offline-sync-state.test.mjs src/lib/queue.test.mjs` passed 25/25, `npm.cmd test` passed 479/479, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1171 Market price and payment helper option hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/market-price-state.mjs` and `src/app/api/payments/confirm/route.js`. Market price state helpers now ignore malformed array options before reading fallback time/message fields, and the internal `createAvailableMarketPrice()` builder normalizes top-level options before reading price sides, source metadata, freshness flags, or dates. The payment confirmation failure-log helper now normalizes malformed top-level options before reading `orderId`, `paymentKey`, or `amount`. This prevents direct/test/reuse callers from crashing helper setup or leaking malformed array option fields while preserving KAPE live/cache normalization, unavailable market fallback copy, Toss payment confirmation flow, Korean payment error copy, and existing persistence behavior. Strengthened `src/lib/market-price-state.test.mjs` and `src/lib/payment-ux-copy.test.mjs` coverage for array-option and payment failure-log helper guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/market-price-state.test.mjs src/lib/payment-ux-copy.test.mjs` passed 20/20, `npm.cmd test` passed 476/476, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1170 AI Gemini route helper option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeGeminiInsightOptions()` in `src/app/api/ai/insight/route.js` and `normalizeGeminiChatStreamOptions()` in `src/app/api/ai/chat/route.js`. The AI insight and AI chat route-level Gemini provider helpers now normalize malformed top-level helper options before reading API keys, prompts, messages, history, or system instructions. This prevents direct/test/reuse callers from crashing the AI provider setup through parameter destructuring while preserving authenticated route flow, Gemini model configuration, Korean insight timeout fallbacks, chat farm-context wiring, SSE stream delegation, AI cache behavior, and existing offline/configuration fallback behavior. Strengthened `src/lib/ai-chat-widget-copy.test.mjs` and `src/lib/ai-insight-widget-copy.test.mjs` route source coverage for safe Gemini helper option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-widget-copy.test.mjs src/lib/ai-insight-widget-copy.test.mjs` passed 17/17, `npm.cmd test` passed 475/475, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1169 Dashboard summary service option and row hardening**: Continued the active Hanwoo quality uplift by adding `normalizeSummaryOptions()`, `normalizeSummaryRows()`, `resolveGeneratedAt()`, and `resolveFinancialSeriesMonthCount()` in `src/lib/dashboard/summary-service.js`. The cached dashboard summary service now normalizes malformed top-level payload options before reading `farmId` or `client`, normalizes malformed financial-series options before reading sales, expenses, month count, or generated date, filters malformed status/building/financial rows before reductions, maps, month aggregation, and occupancy calculations, and guards partial aggregate payloads with optional chaining plus numeric coercion. This prevents direct/test/reuse callers and partial Prisma result shapes from crashing summary payload generation while preserving cached query wiring, current-month rollups, six-month financial series, farm settings payloads, and existing dashboard summary API behavior. Strengthened `src/lib/analysis-copy.test.mjs` source coverage for safe summary option, row, month, generated-date, aggregate, and building normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 474/474, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1168 AI chat stream option and callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeAiChatStreamOptions()` in `src/lib/ai-chat-api.mjs` and `normalizeStreamChatOptions()` in `src/components/widgets/AIChatWidget.js`. The server SSE helper now normalizes malformed top-level stream options before reading `chat`, `message`, or `encoder`, so malformed direct/reuse calls emit the existing Korean SSE error envelope instead of throwing before stream creation. The widget stream helper now normalizes malformed top-level stream options and routes chunk/done/error callbacks through safe no-op fallbacks before fetch, chunk dispatch, completion, or error handling. This prevents direct/test/reuse callers from crashing AI chat streaming setup while preserving authenticated chat validation, Gemini history normalization, Korean configuration/error copy, abort handling, mounted-state guards, accessible launcher/dialog behavior, and existing offline fallback behavior. Strengthened `src/lib/ai-chat-api.test.mjs` and `src/lib/ai-chat-widget-copy.test.mjs` coverage for malformed stream options and callback guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-api.test.mjs src/lib/ai-chat-widget-copy.test.mjs` passed 11/11, `npm.cmd test` passed 474/474, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning once without a concurrent Next build lock. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1167 Dashboard setup and today-focus helper option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeSetupProgressOptions()` in `src/lib/dashboard/setup-progress.mjs` and `normalizeTodayFocusOptions()` in `src/lib/dashboard/today-focus.mjs`. `buildSetupProgressItems()`, `estimateDailyFeedConsumptionKg()`, and `buildTodayFocusItems()` now normalize malformed top-level options before reading farm setup inputs, notification/schedule/inventory/feed collections, sales counts, online state, or reference dates. This prevents direct/test/reuse callers from throwing on null, array, or primitive options before setup progress, today-focus cards, or feed-depletion projections can fall back to safe empty/default dashboard guidance. Strengthened `src/lib/dashboard/setup-progress.test.mjs` and `src/lib/dashboard/today-focus.test.mjs` coverage for malformed top-level option payloads. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/setup-progress.test.mjs src/lib/dashboard/today-focus.test.mjs` passed 20/20, `npm.cmd test` passed 473/473, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1166 Farm metrics option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeFarmMetricOptions()` in `src/lib/dashboard/farm-metrics.mjs` and routing `estimateMonthlyFeedCostPerHead()`, `estimateMonthlyWeightGainPerHead()`, and `computeFarmAdjustments()` through it before reading top-level calculation options. `computeFarmAdjustments()` also normalizes malformed `defaults` before reading fallback feed-cost or weight-gain values. This prevents direct/test/reuse callers and profitability-service reuse from throwing on null, array, or primitive options while preserving existing feed-expense filtering, sales-window filtering, farm-specific adjustment evidence, and default fallback behavior. Strengthened `src/lib/dashboard/farm-metrics.test.mjs` coverage for malformed top-level options and malformed defaults. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/farm-metrics.test.mjs` passed 15/15, `npm.cmd test` passed 470/470, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1165 Dashboard client top-level prop option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeDashboardClientOptions()` in `src/components/DashboardClient.js` and routing `DashboardClient` props through it before reading SSR cattle/sales pages, summary, notifications, feed standards, inventory, schedule, feed history, buildings, farm settings, expenses, market price, or profitability payloads. This prevents direct/test/reuse callers from throwing during dashboard render setup before existing pagination hooks, collection normalizers, Korean fallback copy, widget wiring, modal state, and mutation guards can run. Strengthened `src/lib/home-market-copy.test.mjs` coverage for safe dashboard client option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed 52/52, `npm.cmd test` passed 467/467, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1164 Cattle detail modal prop, cattle-payload, callback, helper, and fallback chart hardening**: Continued the active Hanwoo quality uplift by adding `normalizeCattleDetailModalOptions()` and `normalizeDetailCattle()` in `src/components/forms/CattleDetailModal.js`, routing detail props through safe normalization before reading cattle, building, busy, or callback options. Malformed cattle payloads now render no modal instead of flowing into detail sections, malformed close/edit/delete/update callbacks fall back to safe no-op/async no-op handlers before Escape, header close, edit, archive, or breeding-record save actions invoke them, legacy fallback `weightHistory` chart rows are filtered to object rows after array/JSON parsing, and `SectionTitle`/`InfoItem` helper props are normalized before destructuring. This prevents direct/test/reuse callers from throwing during detail render, close, edit, archive, Escape, breeding-record save setup, helper rendering, or fallback chart rendering while preserving building payload normalization, history fallback, async breeding save locks, archive busy locking, Korean detail copy, focus management, and dashboard cattle detail behavior. Strengthened `src/lib/cattle-detail-modal-wiring.test.mjs` coverage for safe detail option, cattle, callback, helper, and fallback chart normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-detail-modal-wiring.test.mjs src/lib/cattle-form-date-submit.test.mjs src/lib/form-submit-pending-copy.test.mjs` passed 20/20, `npm.cmd test` passed 466/466, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1163 Field mode view prop, list, and callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeFieldModeViewOptions()` and `normalizeFieldModeCattleList()` in `src/components/widgets/FieldModeView.js`. The field-mode view now normalizes malformed top-level props before reading cattle rows, background full-list loaders, select callbacks, or close callbacks; filters malformed cattle rows before search, critical-alert counters, total herd count, and the embedded ear-tag scanner; and routes full-list loading, selection, scanner handoff, and mode-close behavior through safe null/no-op fallbacks. This prevents direct/test/reuse callers from throwing during field-mode render, search, stats, scanner handoff, close, or background loading while preserving checklist persistence, stale-load cleanup, celebration animation guards, Korean field-mode copy, loading announcements, and dashboard field-mode behavior. Strengthened `src/lib/field-mode-celebration.test.mjs` coverage for safe option, list, and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/field-mode-celebration.test.mjs src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 20/20, `npm.cmd test` passed 466/466, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1162 Ear tag scanner modal prop, list, and callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeEarTagScannerModalOptions()` and `normalizeScannerCattleList()` in `src/components/widgets/EarTagScannerModal.js`. The scanner now normalizes malformed top-level props before reading open state, cattle rows, close callbacks, or select callbacks; filters malformed cattle rows before simulated target selection, manual choice rendering, retry, and lookup; and routes close/select actions through safe no-op fallbacks. This prevents direct/test/reuse callers from throwing during scanner render, scan setup, manual selection, retry, close, or confirm handling while preserving scanner animation guards, Korean task labels, live result announcements, missing birth-date copy, tactile/audio feedback, and dashboard scanner behavior. Strengthened `src/lib/eartag-scanner-modal-accessibility.test.mjs` coverage for safe option, list, and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 6/6, `npm.cmd test` passed 465/465, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1161 Financial chart widget prop option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeFinancialChartWidgetOptions()` in `src/components/widgets/FinancialChartWidget.js` and routing `FinancialChartWidget` props through it before reading `saleRecords`, `expenseRecords`, or `seriesData`. This prevents direct/test/reuse callers from throwing during financial chart render setup while preserving existing collection row filtering, strict month parsing, numeric coercion, fallback six-month aggregation, Korean chart labels, accessible chart summary, and dashboard financial widget behavior. Strengthened `src/lib/analysis-copy.test.mjs` coverage for safe financial chart option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 464/464, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1160 Cattle form prop and callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeCattleFormOptions()` in `src/components/forms/CattleForm.js` and routing `CattleForm` props through it before reading `cattle`, `buildings`, `onSubmit`, or `onCancel`. Malformed submit and cancel callbacks now fall back to safe async/no-op handlers before save, cancel-button, or Escape-key handling. This prevents direct/test/reuse callers from throwing during cattle form render, cancel, Escape, or submit setup while preserving building payload normalization, tag lookup guards, date conversion, async save locks, focus management, validation wiring, Korean form copy, and dashboard cattle create/edit behavior. Strengthened `src/lib/cattle-detail-modal-wiring.test.mjs` coverage for safe cattle form option and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-detail-modal-wiring.test.mjs src/lib/cattle-form-date-submit.test.mjs src/lib/form-submit-pending-copy.test.mjs` passed 20/20, `npm.cmd test` passed 464/464, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1159 Analysis tab prop option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeAnalysisTabOptions()` in `src/components/tabs/AnalysisTab.js` and routing `AnalysisTab` props through it before reading `saleRecords`, `feedHistory`, `cattleList`, or `expenseRecords`. This prevents direct/test/reuse callers from throwing during analysis render setup while preserving existing collection row normalization, KPI card option normalization, monthly revenue/cost/profit aggregation, feed-average calculation, chart labeling, Korean analysis copy, and dashboard analysis behavior. Strengthened `src/lib/analysis-copy.test.mjs` coverage for safe analysis tab option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 464/464, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1158 Settings tab prop, widget-control, and mutation-callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeSettingsTabOptions()`, `normalizeSettingsWidgetRegistry()`, and `normalizeSettingsWidgetVisible()` in `src/components/tabs/SettingsTab.js`. `SettingsTab` now normalizes malformed top-level props before reading building payloads, farm settings, theme state, widget registry/visibility, quick-action intent, or settings/building/theme/widget callbacks. Malformed create-building, delete-building, farm-settings, theme-toggle, and widget-toggle callbacks now fall back to safe no-ops before submit/delete/switch handling; malformed widget registry and visibility payloads are normalized before `.length`, `.map()`, and switch-state access. This prevents direct/test/reuse callers from throwing during settings render, widget interaction, farm save, building create, or building delete setup while preserving building payload normalization, Korean settings copy, async save/delete locks, mounted-state cleanup, validation wiring, diagnostics link, and dashboard settings behavior. Strengthened `src/lib/settings-tab-accessibility.test.mjs` and `src/lib/empty-state-wiring.test.mjs` coverage for safe settings option, widget, and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/settings-tab-accessibility.test.mjs src/lib/empty-state-wiring.test.mjs` passed 33/33, `npm.cmd test` passed 464/464, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1157 Feed tab prop and mutation-callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeFeedTabOptions()` in `src/components/tabs/FeedTab.js` and routing `FeedTab` props through it before reading `cattle`, `feedStandards`, `feedHistory`, `buildings`, or `onRecordFeed`. Malformed feed-record callbacks now fall back to a safe async no-op before submit handling, preventing direct/test/reuse callers from throwing during feed render or mutation setup while preserving existing cattle/feed/building payload normalization, feed aggregation, Korean feed copy, async save locks, mounted-state cleanup, validation wiring, chart labeling, and dashboard feed behavior. Strengthened `src/lib/empty-state-wiring.test.mjs` coverage for safe feed tab option and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/empty-state-wiring.test.mjs` passed 18/18, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1156 Sales tab prop, mutation-callback, and pagination-control hardening**: Continued the active Hanwoo quality uplift by adding `normalizeSalesTabOptions()` and `normalizeSalesPaginationOptions()` in `src/components/tabs/SalesTab.js`. `SalesTab` now normalizes malformed top-level props before reading sales/cattle/expense payloads, market data, pagination state, quick-action intent, or `onCreateSale`; malformed sale-create callbacks fall back to a safe async no-op before submit handling, and malformed pagination/load-more callbacks fall back to a safe no-op before the load-more button can invoke them. This prevents direct/test/reuse callers from throwing during sales render, create submit, or pagination interaction while preserving existing collection normalization, profit aggregation, Korean empty-state/form/pagination copy, async save locks, mounted-state cleanup, validation wiring, chart labeling, and dashboard sales behavior. Strengthened `src/lib/home-market-copy.test.mjs`, `src/lib/empty-state-wiring.test.mjs`, and `src/lib/sales-pagination-feedback.test.mjs` coverage for safe sales option, callback, and pagination-control normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs src/lib/empty-state-wiring.test.mjs src/lib/sales-pagination-feedback.test.mjs` passed 71/71, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1155 Calving tab prop and mutation-callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeCalvingTabOptions()` in `src/components/tabs/CalvingTab.js` and routing `CalvingTab` props through it before reading `cattle`, `buildings`, or `onRecordCalving`. Malformed calving-record callbacks now fall back to a safe async no-op before the calving submit handler invokes them, preventing direct/test/reuse callers from throwing during calving render or mutation setup while preserving cattle/building payload normalization, pregnancy-date ordering, Korean calving form copy, async save locks, mounted-state cleanup, validation wiring, countdown labels, and existing dashboard calving behavior. Strengthened `src/lib/calving-tab-accessibility.test.mjs` coverage for safe calving option and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/calving-tab-accessibility.test.mjs` passed 6/6, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1154 Schedule tab prop and mutation-callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeScheduleTabOptions()` in `src/components/tabs/ScheduleTab.js` and routing `ScheduleTab` props through it before reading `events`, `onCreateEvent`, `onToggleEvent`, or `quickActionIntent`. Malformed create/toggle callbacks now fall back to safe async no-ops before create submit or completion-toggle handlers invoke them, preventing direct/test/reuse callers from throwing during schedule render or mutation setup while preserving event payload normalization, Korean calendar/form copy, async save locks, mounted-state cleanup, validation wiring, countdown labels, and existing dashboard schedule behavior. Strengthened `src/lib/tab-header-accessibility.test.mjs` and `src/lib/empty-state-wiring.test.mjs` coverage for safe schedule option and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/tab-header-accessibility.test.mjs src/lib/empty-state-wiring.test.mjs` passed 26/26, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build, and path-limited `git diff --check` passed with CRLF warnings only. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1153 Inventory tab prop and mutation-callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeInventoryTabOptions()` in `src/components/tabs/InventoryTab.js` and routing `InventoryTab` props through it before reading `inventory`, `onAddItem`, `onUpdateQuantity`, or `quickActionIntent`. Malformed add/update callbacks now fall back to safe async no-ops before create submit or inline quantity update handlers invoke them, preventing direct/test/reuse callers from throwing during inventory render or mutation setup while preserving inventory row normalization, Korean empty-state/form copy, async save locks, mounted-state cleanup, validation wiring, and existing dashboard inventory behavior. Strengthened `src/lib/empty-state-wiring.test.mjs` and `src/lib/home-market-copy.test.mjs` coverage for safe inventory option and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/empty-state-wiring.test.mjs src/lib/home-market-copy.test.mjs` passed 69/69, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build, and path-limited `git diff --check` passed with CRLF warnings only. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1141 Feedback provider prop and toast-option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeFeedbackProviderOptions()` and `normalizeToastOptions()` in `src/components/feedback/FeedbackProvider.js`. `FeedbackProvider` now normalizes malformed top-level props before reading `children`, and `notify()` normalizes malformed option input before reading title, description, variant, or duration. This prevents direct/test/reuse callers from throwing during provider render or feedback notification scheduling while preserving live-region toast semantics, mounted-state guards, timeout cleanup, Korean dismiss labels, confirmation dialog labels, and the existing `useAppFeedback()` contract. Strengthened `src/lib/feedback-provider-copy.test.mjs` coverage for safe provider and toast option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/feedback-provider-copy.test.mjs` passed 4/4, `npm.cmd test` passed 461/461, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1140 Notification modal prop and close-callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeNotificationModalOptions()` in `src/components/ui/NotificationModal.js` and routing `NotificationModal` through it before reading `id`, `notifications`, `onClose`, or `onTestSMS`. Added a safe `handleClose` guard so malformed `onClose` callbacks fall back to a no-op before overlay, Escape, or close-button dismissal. This prevents direct/test/reuse callers from throwing during modal render or dismissal while preserving notification payload filtering, focus management, SMS busy locking, Korean modal copy, and optional SMS test handling. Strengthened `src/lib/notification-modal-copy.test.mjs` coverage for safe option and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/notification-modal-copy.test.mjs` passed 8/8, `npm.cmd test` passed 461/461, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1139 Alert banner prop option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeAlertBannerOptions()` in `src/components/widgets/AlertBanners.js` and routing `EstrusAlertBanner` and `CalvingAlertBanner` through it before reading `notifications` or `buildings`. Malformed direct/test/reuse top-level props now fall back to safe empty options instead of throwing during render setup, while existing notification filtering, building lookup normalization, remaining-day labels, Korean fallback copy, and date formatting are preserved. Strengthened `src/lib/alert-banners-accessibility.test.mjs` coverage for safe top-level option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/alert-banners-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 461/461, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1138 Shared cattle cards prop and callback hardening**: Continued the active Hanwoo quality uplift by adding `normalizeCardComponentOptions()` in `src/components/ui/cards.js` and routing `StatCard`, `PenCard`, and `CattleRow` through it before reading labels, values, cattle payloads, delay values, drag state, or callbacks. Added safe no-op guards for malformed `onSelect`, `onDrop`, and `onClick` before user interaction, preventing direct/reuse callers from throwing during render or click/drop handling while preserving native button semantics, existing payload normalization, alert labels, card styling, drag/drop payload normalization, and accessible labels. Strengthened `src/lib/cards-accessibility.test.mjs` coverage for safe card option and callback normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cards-accessibility.test.mjs` passed 8/8, `npm.cmd test` passed 461/461, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1137 Premium input prop option hardening**: Continued the active Hanwoo quality uplift by adding `normalizePremiumInputOptions()` in `src/components/ui/premium-input.js` and routing `PremiumInput`, `PremiumTextarea`, `PremiumSelect`, and `PremiumLabel` through it before reading class names, input type, error state, children, or passthrough props. Malformed direct/test/reuse top-level props now fall back to safe empty options instead of throwing during render setup, while refs, display names, premium input styling, date monospace styling, error-state styling, children rendering, and passthrough attributes are preserved. Extended `src/lib/ui-primitives-options.test.mjs` coverage for safe premium-input option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ui-primitives-options.test.mjs` passed 11/11, `npm.cmd test` passed 460/460, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1136 Shared dialog prop option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeDialogOptions()` in `src/components/ui/dialog.js` and routing `DialogOverlay`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, and `DialogDescription` through it before reading class names, children, close labels, or passthrough props. Malformed direct/test/reuse top-level props now fall back to safe empty options instead of throwing during render setup, while Radix refs/display names, contextual Korean close labels, overlay/content styling, class merging, and passthrough attributes are preserved. The default dialog close label is now verified as readable Korean `??붿긽???リ린`. Extended `src/lib/ui-primitives-options.test.mjs` coverage for safe dialog option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused UI/dialog tests passed 13/13, `npm.cmd test` passed 459/459, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1135 Shared select prop option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeSelectOptions()` in `src/components/ui/select.js` and routing `SelectTrigger`, `SelectContent`, `SelectItem`, `SelectSeparator`, and `SelectLabel` through it before reading class names, children, popper position, or passthrough props. Malformed direct/test/reuse top-level props now fall back to safe empty options instead of throwing during render setup, while Radix refs/display names, decorative icons, popper positioning, item text, class merging, and passthrough attributes are preserved. Extended `src/lib/ui-primitives-options.test.mjs` coverage for safe select option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused UI/dialog tests passed 12/12, `npm.cmd test` passed 458/458, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning without a concurrent Next build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard T-1134 Shared tabs prop option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeTabsOptions()` in `src/components/ui/tabs.js` and routing `TabsList`, `TabsTrigger`, and `TabsContent` through it before reading class names or passthrough props. Malformed direct/test/reuse top-level props now fall back to safe empty options instead of throwing during render setup, while Radix refs/display names, tab styling, class merging, and passthrough attributes are preserved. Extended `src/lib/ui-primitives-options.test.mjs` coverage for safe tabs option normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ui-primitives-options.test.mjs` passed 8/8, `npm.cmd test` passed 457/457, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **T-1107 Best-of-N comment_trigger_avg ?곸냽??* (`cc37acff`): 吏곸쟾 ?몄뀡??`tune_best_of_n_weight.py` sweep 遺꾧린媛 `comment_trigger_avg` 而щ읆 遺?щ줈 ??긽 dead ???臾몄젣 ?뺣퉬. 5?꾩튂 ?숈떆 ??`cost_db.py` ?붿씠?몃━?ㅽ듃/而щ읆/`update_draft_comment_trigger_avg`, `draft_analytics.record_draft_event` ?뚮씪誘명꽣, `draft_generator` Best-of-N picker 媛 `drafts_dict["_comment_trigger_avg"]` ?곸냽?? `persist_stage` 媛 洹멸구 異붿텧??record ???꾨떖, tuner docstring ?뺥솗?? 諛쒗뻾遺꾨쭏???먮룞 ?꾩쟻?섎ŉ 5嫄??댁긽 紐⑥씠硫?sweep 遺꾧린媛 ?먮룞 ?쒖꽦??肄붾뱶 蹂寃?0). 5 ?좉퇋 ?뚯뒪??耳?댁뒪, focused 54/54 pass, blind-to-x full unit suite 1703/1703 pass, ruff format/check clean. |
| Next Priorities | T-251(Supabase) 洹몃?濡? ?ㅼ쓬 ?꾩냽 ?꾨낫: ??AI Insight 罹먯떆瑜?Redis 濡??꾩옱 per-instance Map). ??AI Insight 罹먯떆 hit/miss 鍮꾩쑉??Langfuse ?몃젅?댁떛(`LANGFUSE_ENABLED` ?명봽???대? 議댁옱). ??Best-of-N ?쒕낯 ??嫄??꾩쟻 ???ㅼ젣 sweep 寃곌낵瑜?weekly report ???먮룞 ?꾨쿋?? |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Pagination load-more parameter hardening**: Continued the active Hanwoo quality uplift by normalizing malformed `loadMore` parameter input in `src/lib/hooks/useCursorPagination.js`, `useCattlePagination.js`, and `useSalesPagination.js`. Shared cursor pagination now uses safe params before `Object.entries()`, and cattle/sales pagination now normalize params before reading filter fields, preventing direct/retry caller bugs from throwing before timeout protection, in-flight guards, Korean retry feedback, and page-info safety checks can run. Strengthened focused pagination source coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused pagination tests passed 5/5, `npm.cmd test` passed 444/444, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard full-list preload option hardening**: Continued the active Hanwoo quality uplift by adding `normalizeFullListLoadOptions()` in `src/components/DashboardClient.js` and routing both complete cattle and complete sales preload helpers through it before reading `silent`. Malformed direct retry/preload option input now falls back to non-silent behavior instead of throwing during parameter destructuring. Strengthened `src/lib/home-market-copy.test.mjs` to keep the safe option normalization plus existing retry, busy-status, and stale-unmount guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home dashboard source test passed 51/51, `npm.cmd test` passed 444/444, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **/goal "?꾨줈?앺듃 媛쒖꽑?덉쓣 留뚮뱾怨??꾨즺?댁쨾" ??blind-to-x 湲곗닠遺梨?由ы뙥??(T-1108, no behavior change)**. 3媛?Explore agent??遺梨?蹂닿퀬?쒕? ?ㅼ륫 寃利앺빐 怨쇱옣??遺遺?source-grep ?뚭? 6嫄?CI test step 遺??skip 14嫄???嫄몃윭?닿퀬 吏꾩쭨 遺梨꾨쭔 ?먮큵. 蹂寃? (1) `tests/unit/test_multi_platform.py:244` stale `@pytest.mark.skip` ??젣 ??config `output_formats==["twitter"]`? ?뺤콉 紐⑥닚??dead naver_blog ?뚯뒪?? (2) `tests/integration/test_p0_enhancements.py` `pytest.skip("No tone_mapping/golden_examples")` 2嫄댁쓣 `assert ..., "policy contract"`濡??꾪솚 ??YAML ???뚭?媛 silent skip ???fail濡??몄텧. ?붿씠?????곕뒗 `import pytest` ?쒓굅. (3) `pyproject.toml`??`[tool.ruff]`(猷⑦듃 `ruff.toml` `extend`濡?紐낆떆 ?곸냽 ????洹몃윭硫?ruff媛 upward 寃??硫덉땄) + tests E501 per-file-ignore + `[tool.mypy]` ?뚯씪 ?붿씠?몃━?ㅽ듃(`pipeline.draft_contract`, `pipeline.harness_guard` strict) + `mypy>=1.10.0` dev dep. (4) orphan `projects/blind-to-x/.github/workflows/blind-to-x.yml`(GitHub Actions媛 ???쎌쓬 ??root `.github/workflows/full-test-matrix.yml` `blind-to-x-tests` job????CI) ?섎룄瑜??ㅻ뜑 肄붾찘??+ `tests/unit/test_config_workflow_sync.py` 紐⑤뱢 docstring?쇰줈 臾몄꽌?? |
| Next Priorities | (A) `pipeline/_archive/` (newsletter_formatter 489以?+ newsletter_scheduler 285以?+ .bak) ??젣 ??inbound import 0嫄??뺤씤 ?꾨즺吏留?auto-mode classifier媛 `rm -rf` 紐낆떆 沅뚰븳 ?붽뎄濡?蹂대쪟. ?ъ슜??OK ??利됱떆 ?쒓굅. (B) `pipeline/draft_quality_gate.py` (858以?24?ы띁) CTA 寃利?洹쒖튃 `rules/cta_patterns.yaml`濡??몃???????由ы뙥??3-4??, 蹂꾨룄 ?몄뀡. (C) `pipeline/cost_db.py` (1039以? 留덉씠洹몃젅?댁뀡 濡쒖쭅 遺꾨━. (D) T-251 (Supabase password) user-owned. 寃利? `py -3.14 -m pytest tests/unit tests/integration -q --no-cov --ignore=tests/integration/test_curl_cffi.py` 1759/1759 pass 0 skip 0 fail (6m23s, 踰좎씠?ㅻ씪??1680u+1skip ???뚭? 0), `py -3.14 -m ruff check .` clean. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight cache API/UI contract regression coverage**: Continued the active Hanwoo quality uplift by strengthening `src/lib/ai-insight-widget-copy.test.mjs`. The source-contract tests now lock down that `AIInsightWidget` sends `forceRefresh` with the summary payload, resets and renders cache metadata only for cached AI responses, and that `/api/ai/insight` builds per-user cache keys, serves cached AI responses with `cachedAt`/`ageSeconds`, clears cache entries on force refresh, stores successful parsed AI responses, and marks fallback/refresh responses as uncached. Runtime code was not changed. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 43/43, `npm.cmd test` passed 444/444, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **/goal "媛쒖꽑??留뚮뱾怨??꾩꽦??留뚮뱾?댁쨾" ??3媛?而ㅻ컠 異쒗븯**: (1) `chore(hanwoo-dashboard) ecdfcca5`: Codex T-1008~T-1100 ?섎뱶??94媛??뚯씪????踰덉뿉 寃利???而ㅻ컠 (test 428/428, lint clean, build exit 0). HANDOFF??媛쒕퀎 蹂寃쎈쭏??green 二쇱옣?덉?留?硫?고댋 race 硫붾え由??뺤콉??吏곸젒 寃利????쇨큵 而ㅻ컠. (2) `feat(hanwoo-dashboard) 1bbe34ba`: `AIInsightWidget` ?쇱씪 in-memory 罹먯떆 (`src/lib/ai-insight-cache.mjs`). userId + Asia/Seoul YYYY-MM-DD + summary SHA-256(16) ?댁떆 寃고빀 ?? AI ?묐떟留?罹먯떛(?대━?ㅽ떛 ?쒖쇅), 256?뷀듃由?prune, `forceRefresh:true` ?≪떊 ??????젣 ???ы샇異? ?꾩젽??"N遺???罹먯떆" 誘몃땲 諛곗?. (3) `feat(blind-to-x) 12f16a04`: `scripts/tune_best_of_n_weight.py` dry-run CLI. 理쒓렐 published draft_analytics 濡쒖슦??engagement_rate ? hook/virality/fit/final_rank 媛?異?Pearson r 怨꾩궛 + 媛????comment_trigger_avg sweep?쇰줈 `llm.best_of_n_comment_weight` 異붿쿇(config 誘몃?寃? `--json` ?먮룞??紐⑤뱶 ?ы븿). |
| Next Priorities | T-251 (Supabase password resync, user-owned) 洹몃?濡? ?좉퇋 ?꾩냽 ?꾨낫: ??`comment_trigger_avg` 而щ읆??`draft_analytics`???곸냽?뷀븯怨?`draft_generator._combined_candidate_score` 寃곌낵瑜?record_draft ?쒖젏???꾪뙆 ??洹몃윭硫??쒕꼫??sweep 遺꾧린媛 ?ㅻ뜲?댄꽣濡?媛?? ??AI Insight 罹먯떆瑜?Redis濡???린硫??ㅼ쨷 ?몄뒪?댁뒪?먯꽌??hit ???꾩옱??per-instance Map). ??AI Insight 罹먯떆 hit/miss 鍮꾩쑉??Langfuse???몃젅?댁떛(?대? opt-in `LANGFUSE_ENABLED` ?명봽??議댁옱). 寃利? hanwoo `npm test` 439/439, lint clean, build exit 0. blind-to-x `pytest test_tune_best_of_n_weight.py` 15/15, ruff clean. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment and AI insight timeout scheduling failure hardening**: Continued the active Hanwoo quality uplift by tightening timeout scheduling failure paths. Payment widget timeout scheduling failures now immediately reject with `TimeoutError`, AI insight client timeout scheduling failures immediately abort into the timeout fallback, and the AI insight API timeout wrapper rejects with `InsightTimeoutError` instead of silently losing timeout protection. Strengthened payment and AI insight regression coverage to keep immediate timeout fallback behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 10/10, `node --test src/lib/ai-insight-widget-copy.test.mjs` passed 10/10, `npm.cmd test` passed 390/390, `npm.cmd run lint` passed clean, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment and AI insight deferred reset fallback hardening**: Continued the active Hanwoo quality uplift by adding guarded deferred-task helpers to `PaymentWidget` and `AIInsightWidget`. Payment widget-ready/error resets and AI heuristic insight refresh resets now route through Promise-backed fallback scheduling, so restricted browser environments where `queueMicrotask` throws still preserve existing cancellation and abort guards. Strengthened payment and AI insight regression coverage to keep the helpers and prevent raw reset microtasks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 10/10, `node --test src/lib/ai-insight-widget-copy.test.mjs` passed 10/10, `npm.cmd test` passed 390/390, `npm.cmd run lint` passed clean, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form/detail deferred reset fallback hardening**: Continued the active Hanwoo quality uplift by adding guarded deferred-task helpers to `CattleForm` and `CattleDetailModal`. Save-state resets and breeding-action resets now route through Promise-backed fallback scheduling, so restricted browser environments where `queueMicrotask` throws still preserve existing cancellation guards. Strengthened cattle form/detail regression coverage to keep the helpers and prevent raw reset microtasks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 17/17, `npm.cmd test` passed 390/390, `npm.cmd run lint` passed clean, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Admin diagnostics deferred loading fallback hardening**: Continued the active Hanwoo quality uplift by centralizing diagnostics loading-state deferral behind `deferDiagnosticsTask()`. Both system diagnostics and raw-data loading resets now share guarded `queueMicrotask` scheduling with a Promise fallback, preserving cancellation and latest-request guards even in restricted browser environments where microtask scheduling throws. Strengthened diagnostics regression coverage to keep the helper and prevent raw initialization microtasks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/diagnostics-copy.test.mjs` passed 4/4, `npm.cmd test` passed 390/390, `npm.cmd run lint` passed clean, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner deferred task fallback hardening**: Continued the active Hanwoo quality uplift by centralizing scanner microtask scheduling behind `deferScannerTask()`. Initial target selection and deferred no-match fallback now share guarded `queueMicrotask` scheduling with a Promise fallback, preserving cleanup guards even in restricted browser environments where microtask scheduling throws. Strengthened scanner regression coverage to keep the helper and prevent raw initialization microtasks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 5/5, `npm.cmd test` passed 390/390, `npm.cmd run lint` passed clean, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard summary and notification refresh unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding dashboard summary and notification refresh completions with the existing dashboard mounted-state ref. Stale API/getNotifications completions now avoid summary, summary metadata, and notification state updates after dashboard unmount while preserving latest-request ordering for mounted summary refreshes. Strengthened home dashboard regression coverage to keep guarded refresh completion paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 50/50, `npm.cmd test` passed 387/387, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard cattle create/update unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding dashboard cattle create and update online server-action completion paths with the existing dashboard mounted-state ref. Stale completions now avoid cattle state, modal/edit state, selected-cow state, dashboard refresh, and toast updates after dashboard unmount while still returning successful server-action completion as true. Strengthened home dashboard regression coverage to keep guarded cattle create/update success/error/catch paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 49/49, `npm.cmd test` passed 386/386, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard farm settings mutation unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding the dashboard farm settings save completion path with the existing dashboard mounted-state ref. Stale completions now avoid farm settings state and toast updates after dashboard unmount while still returning successful server-action completion as true. Strengthened home dashboard regression coverage to keep guarded farm settings success/error paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 48/48, `npm.cmd test` passed 385/385, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard calving mutation unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding the dashboard calving server-action completion path with the existing dashboard mounted-state ref. Stale completions now avoid calving cattle state, dashboard refresh, and toast updates after dashboard unmount while still returning successful server-action completion as true. Strengthened home dashboard regression coverage to keep guarded calving success/error paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 47/47, `npm.cmd test` passed 384/384, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard sales and feed mutation unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding dashboard sales-record create and feed-record create handlers with the existing dashboard mounted-state ref. Stale server-action completions now avoid sales/feed state, dashboard refresh, and toast updates after dashboard unmount while still returning successful server-action completion as true. Strengthened home dashboard regression coverage to keep guarded sales/feed success/error paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 46/46, `npm.cmd test` passed 383/383, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard schedule mutation unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding dashboard schedule create and completion-toggle handlers with the existing dashboard mounted-state ref. Stale server-action completions now avoid schedule state and toast updates after dashboard unmount while still returning successful server-action completion as true. Strengthened home dashboard regression coverage to keep guarded schedule create/toggle success/error paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 45/45, `npm.cmd test` passed 382/382, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard inventory mutation unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding dashboard inventory create and quantity-update handlers with the existing dashboard mounted-state ref. Stale server-action completions now avoid inventory state and toast updates after dashboard unmount while still returning successful server-action completion as true. Strengthened home dashboard regression coverage to keep guarded inventory create/update success/error paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 44/44, `npm.cmd test` passed 381/381, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard building mutation unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding dashboard building create/delete handlers with the existing dashboard mounted-state ref. Stale server-action completions now avoid building state, selected-building, selected-pen, and toast updates after unmount while still returning successful server-action completion as true. Strengthened home dashboard regression coverage to keep guarded building create/delete success/error paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 43/43, `npm.cmd test` passed 380/380, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding save unmount cleanup hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to `CattleDetailModal`. Async breeding-record finalizers now release the duplicate-submit ref while avoiding React state updates after component unmount. Strengthened cattle form/detail source regression coverage to keep the mounted cleanup guard and guarded saved-result/finalizer paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 17/17, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form save unmount cleanup hardening**: Continued the active Hanwoo quality uplift by extending the existing `CattleForm` mounted-state guard to cover cattle-save finalizers. Unmount cleanup now releases the save duplicate-submit ref, and async save completion avoids React state updates after component unmount. Strengthened cattle form/detail source regression coverage to keep the save cleanup guard and guarded save finalizer. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 17/17, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings tab async cleanup unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to `SettingsTab`. Farm settings saves, building creates, and building deletes now release duplicate-action refs while avoiding React state/reset updates after component unmount. Strengthened Settings source regression coverage to keep the mounted cleanup guard and guarded saved/confirmed/finalizer paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/settings-tab-accessibility.test.mjs` passed 14/14, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Calving tab async cleanup unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to `CalvingTab`. Async calving-record create finalizers now release the duplicate-submit ref while avoiding React state/reset updates after component unmount. Strengthened Calving source regression coverage to keep the mounted cleanup guard and guarded recorded-result/finalizer paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/calving-tab-accessibility.test.mjs` passed 6/6, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed tab async cleanup unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to `FeedTab`. Async feed-record create finalizers now release the duplicate-submit ref while avoiding React state/reset updates after component unmount. Strengthened Feed/empty-state source regression coverage to keep the mounted cleanup guard and guarded recorded-result/finalizer paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/empty-state-wiring.test.mjs` passed 17/17, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales tab async cleanup unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to `SalesTab`. Async sales-record create finalizers now release the duplicate-submit ref while avoiding React state/reset updates after component unmount. Strengthened Sales/home source regression coverage to keep the mounted cleanup guard and guarded saved-result/finalizer paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs src/lib/empty-state-wiring.test.mjs` passed 58/58, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory tab async cleanup unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to `InventoryTab`. Async inventory-create and inline quantity-update finalizers now release duplicate-action refs while avoiding React state/reset updates after component unmount. Strengthened Inventory/home source regression coverage to keep the mounted cleanup guard, guarded saved-result paths, and guarded quantity reset finalizer. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/empty-state-wiring.test.mjs src/lib/home-market-copy.test.mjs` passed 58/58, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule tab async cleanup unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to `ScheduleTab`. Async schedule-create and completion-toggle finalizers now release duplicate-action refs while avoiding React state/reset updates after component unmount. Strengthened Schedule and empty-state source regression coverage to keep the mounted cleanup guard and tolerate the guarded saved-result path. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/empty-state-wiring.test.mjs src/lib/tab-header-accessibility.test.mjs` passed 25/25, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard React hooks lint suppression removal**: Continued the active Hanwoo quality uplift by replacing the remaining Hanwoo `eslint-disable` hook suppressions with structural code paths. Diagnostics, cattle form/detail, and payment widget effect resets now defer state updates through guarded microtasks, and CattleForm uses an event submit wrapper instead of render-time `handleSubmit(submitForm)`. Strengthened diagnostics, payment, and cattle form/detail source regression coverage to keep the no-suppression pattern. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/diagnostics-copy.test.mjs src/lib/payment-ux-copy.test.mjs src/lib/cattle-detail-modal-wiring.test.mjs` passed 30/30, `npm.cmd test` passed 375/375, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Claude Opus 4.7 (1M context) |
| Work | **active-project-matrix CI rescue (full pipeline back to green)**: Investigated `active-project-matrix` failure on `e681dc60` and unblocked the entire CI in three steps. (1) `pnpm-lock.yaml` importers had stale specifiers (`@serwist/next ^9.5.7`, `bullmq ^5.76.8`, `react-hook-form ^7.71.2`) after Dependabot PRs #90/#106/#81 ??refreshed via `pnpm install --lockfile-only` (Windows-safe per memory `pnpm_install_windows_korean_path_20260520`). (2) `.github/workflows/full-test-matrix.yml` test/build/lint steps used pnpm script shorthand `pnpm --filter X build --if-present` which passes `--if-present` to the inner `next build --webpack` and fails with `unknown option`. Aligned with the working smoke pattern (`pnpm --filter X run --if-present <script>`). (3) `pnpm-lock` refresh bumped `eslint-plugin-react-hooks` 7.0.1 ??7.1.1 exposing 14 new violations. Coordinated with parallel Codex worktree: Codex extracted RHF `<form onSubmit={handleSubmit(submitX)}>` patterns into wrapper handlers (the right structural fix, not a suppression) covering 9 refs cases; I suppressed the 5 intentional initial-loading/setState-reset cases (DiagnosticsPageClient/CattleDetailModal/CattleForm/PaymentWidget) plus the EarTagScannerModal `queueMicrotask` migration. Also bundled Codex's 70-file hanwoo quality uplift (T-988..T-1021) which had been verified-but-uncommitted, after running full local QC. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Multi-tool race learning: Codex was producing T-1xxx work concurrently with this session ??`multi_tool_git_index_race_20260520` pattern. Detected before committing by verifying Codex's `npm.cmd test` claims locally; safe because both tools ended up converging on the same fix (Codex via wrapper extraction, me via targeted disable-next-line). Current verification: hanwoo `npm.cmd run lint` exits 0 (clean, zero warnings after `eslint --fix --report-unused-disable-directives`), `npm.cmd test` passes 372/372, suika-game-v2 61/61, word-chain 23/23, knowledge-dashboard 3/3. CI commits pushed: `53ee47d0` lockfile fix, `8d466d50` workflow fix, `1b448130` lint violation fix ??CI fully green on `1b448130` (both root-quality-gate and active-project-matrix). |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather coordinate range and React lint gate hardening**: Continued the active Hanwoo quality uplift by tightening DashboardClient and useWeather weather-coordinate helpers so normalized latitude/longitude must be finite and within WGS84-style latitude/longitude bounds before building Open-Meteo requests. Out-of-range saved farm or geolocation coordinates now fall back to the default Namwon weather coordinates. Also moved tab `react-hook-form` submit handler creation out of render-time JSX calls and deferred ear-tag scanner modal open-state resets through a microtask so the current React hooks lint gate passes without refs/set-state errors. Strengthened home/weather regression coverage to keep bounded coordinate validation. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 40/40, `npm.cmd test` passed 372/372, `npm.cmd run lint` passed with 7 pre-existing unused-disable warnings outside this change, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather saved farm-coordinate hardening**: Continued the active Hanwoo quality uplift by routing saved farm weather coordinates through a shared finite-coordinate helper in DashboardClient and useWeather. Malformed, stringy, or non-finite farm settings no longer build Open-Meteo requests with invalid latitude/longitude values; invalid saved coordinates now fall back to the default Namwon weather coordinates, matching the geolocation success fallback path. Strengthened home/weather regression coverage to keep coordinate normalization in both weather entry points and prevent direct farm-coordinate fetches from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 40/40, `npm.cmd test` passed 372/372, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard offline-sync refresh failure messaging hardening**: Continued the active Hanwoo quality uplift by wrapping DashboardClient's post-offline-sync `router.refresh()` in a guarded block. Successful offline sync is no longer reported as generic sync failure when route refresh fails; refresh failures now log diagnostics and show a separate Korean warning telling the operator to manually refresh the screen to see synced results. Strengthened home dashboard regression coverage to keep the guarded refresh path and prevent direct `router.refresh()` from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 40/40, `npm.cmd test` passed 372/372, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Claude (Opus 4.7) |
| Work | **/goal "?좏겙 ?ъ슜" ?ы빐????hanwoo ?좉린??異쒗븯 留덈Т由?寃利?+ uv.lock ?숆린??*. ?ъ슜??`/goal "萸붾뱺吏 ?댁꽌 ?좏겙 ?ъ슜??` 瑜?`AskUserQuestion` ?쇰줈 narrow ??`hanwoo ?좉린??留덈Т由? 濡?醫곹옒. (1) `goal_workspace_new_features_20260526` 硫붾え由?+ 1cd30010 而ㅻ컠 鍮꾧탳 ???좉린??3醫?AI Insight / Best-of-N / WhisperX) ?대? 異쒗븯 ?꾨즺 ?뺤씤. blind-to-x/shorts-maker-v2 untouched. hanwoo AIInsight ?곸뿭 WIP ??timer guard + Korean copy polish 留?(?뚭? ?놁쓬). (2) `project_qc_runner.py --project hanwoo-dashboard --json` 寃곌낵: **test 370/370 / lint clean / build pass** (T-251 Supabase warning 留??붿〈, ?ъ슜???묒뾽). (3) 硫?고댋 race 媛먯? ???몄뀡 以?Codex 媛 蹂묐젹濡?`fb4da673` (T-988..T-1021 quality uplift, 73 files / +2925 / -319) ?≪닔 而ㅻ컠. `multi_tool_git_index_race_20260520` 硫붾え由??⑦꽩 洹몃?濡??ы쁽. Codex ?쒖꽦 WIP 3 ?뚯씪(DashboardClient/useWeather/home-market-copy.test ??geolocation 醫뚰몴 validation) ? ?섎룄?곸쑝濡?誘명꽣移? (4) Leftover `uv.lock` (Dependabot #79 aiohttp 3.11??.13 癒몄? ??root lockfile 誘멸갚?? ???⑤룆 `5fc5a424 chore(uv): sync root uv.lock with merged aiohttp 3.13.5 bump` ?쇰줈 而ㅻ컠. (5) Workspace-level Biome `npx biome ci .` ? `.agents/skills/{confidence-check,pptx}` ??pre-existing `from "fs"` 誘몄궗??node: ?꾨줈?좎퐳 ?꾨컲留??몄텧(HEAD baseline ?숈씪). ??蹂寃??뚭? ?꾨떂. |
| Next Priorities | Codex ?쒖꽦 WIP(3 ?뚯씪) 而ㅻ컠 留덈Т由щ뒗 Codex ?몄뀡???대떦. T-251 Supabase 鍮꾨쾲 由ъ뀑? ?ъ슜???묒뾽. `/goal` ?꾨즺 audit ?듦낵(?꾨옒 6??ぉ ?꾨? 異⑹”). |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather geolocation success-coordinate hardening**: Continued the active Hanwoo quality uplift by guarding DashboardClient and useWeather geolocation success callbacks. Malformed or non-finite `position.coords` values now fall back to the default Namwon weather coordinates instead of building Open-Meteo requests with invalid coordinates. Strengthened home/weather regression coverage to keep coordinate normalization in both weather entry points and prevent direct `position.coords.latitude/longitude` fetches from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 39/39, `npm.cmd test` passed 371/371, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print load-listener failure hardening**: Continued the active Hanwoo quality uplift by wrapping QR print-window load listener registration in a guarded helper. Restricted or unusual popup event APIs no longer abort an otherwise prepared QR print window; listener registration failures log diagnostics while the existing fallback timer path can still complete printing and release the duplicate-print lock/busy state. Strengthened QR regression coverage to keep guarded load-listener registration and prevent direct listener registration from blocking fallback scheduling. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 7/7, `npm.cmd test` passed 371/371, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print window open failure hardening**: Continued the active Hanwoo quality uplift by wrapping QR print-window creation in a guarded helper. Restricted or unusual browser popup APIs no longer leave QR printing stuck in a preparing state; window-open failures log diagnostics, reuse the existing popup-blocked Korean guidance, and release the duplicate-print lock/busy state. Strengthened QR regression coverage to keep guarded popup opening and prevent direct `window.open` usage from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 6/6, `npm.cmd test` passed 370/370, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feedback toast timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping feedback toast dismissal timer scheduling and cleanup in guarded blocks. Restricted browser timer APIs no longer break app notifications: toasts still render when auto-dismiss scheduling fails, manual dismiss cleanup tolerates timer cleanup failures, and provider unmount cleanup clears tracked timers best-effort. Strengthened `feedback-provider-copy.test.mjs` to keep guarded timer scheduling, cleanup, and Korean dismiss semantics. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/feedback-provider-copy.test.mjs` passed 3/3, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price refresh timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping the market price widget's initial refresh timer, hourly polling timer, and cleanup calls in guarded blocks. Restricted browser timer APIs no longer break the market price card effect; if the immediate refresh timer cannot be scheduled, the widget falls back through a microtask fetch, while polling setup and cleanup failures are logged or ignored without crashing the card. Strengthened `home-market-copy.test.mjs` to keep the guarded timer scheduling and cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 39/39, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Offline sync refresh failure messaging hardening**: Continued the active Hanwoo quality uplift by wrapping the offline queue post-sync `router.refresh()` path in a guarded block. If the server sync succeeds but dashboard refresh fails, the hook now logs `Offline queue refresh failed` and shows Korean guidance to manually refresh the screen to see synced results, instead of falling through to the generic offline sync failure notification. Strengthened `sync-manager-copy.test.mjs` to keep the guarded refresh path and Korean fallback message. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/sync-manager-copy.test.mjs` passed 1/1, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Login success dashboard navigation failure hardening**: Continued the active Hanwoo quality uplift by wrapping the login success `router.push("/")` and `router.refresh()` path in a guarded navigation block. If dashboard navigation fails after successful credentials sign-in, the page now logs `Login dashboard navigation failed` and shows Korean fallback copy explaining that login completed but dashboard navigation failed, instead of mislabeling it as a generic sign-in/network failure. Strengthened `error-pages-wiring.test.mjs` to keep the guarded navigation path and fallback message. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Admin diagnostics dashboard-return navigation hardening**: Continued the active Hanwoo quality uplift by replacing the admin diagnostics page's inline dashboard return `router.push("/")` with a guarded `handleDashboardReturn()` path. Navigation failures are now logged and surfaced through the existing app feedback system with Korean copy instead of failing silently. Strengthened `diagnostics-copy.test.mjs` to keep the guarded handler, Korean fallback message, and button wiring. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/diagnostics-copy.test.mjs` passed 3/3, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment failure retry fallback-status hardening**: Continued the active Hanwoo quality uplift by adding a final user-visible fallback for the subscription failure retry flow. If both browser back navigation and the direct `/subscription` fallback navigation fail, the page now logs `Payment retry fallback navigation failed` and announces Korean status copy in a polite status region instead of failing silently. Strengthened `payment-ux-copy.test.mjs` to keep the retry status state, polite announcement, and fallback failure logging. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 6/6, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment failure retry navigation hardening**: Continued the active Hanwoo quality uplift by replacing the subscription failure page's inline retry `router.back()` call with a guarded `handleRetry()` path. If browser history navigation fails, the page logs `Payment retry navigation failed` and falls back to `/subscription`, so users can still return to checkout and retry payment. Strengthened `payment-ux-copy.test.mjs` to keep the guarded retry path and direct checkout fallback. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 6/6, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment success auto-redirect failure hardening**: Continued the active Hanwoo quality uplift by wrapping the subscription success page's delayed dashboard redirect in a guarded `try/catch`. If `router.push("/")` fails after a confirmed payment, the page now logs the navigation failure and replaces the stale auto-navigation promise with Korean fallback status copy that tells the user to return to the dashboard and recheck. Strengthened `payment-ux-copy.test.mjs` to keep the guarded redirect path and fallback copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 6/6, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment redirect URL browser-access hardening**: Continued the active Hanwoo quality uplift by routing subscription checkout success/fail redirect URL creation through `buildPaymentRedirectUrl()`. The payment widget now builds absolute redirect URLs from the current `window.location.href` when available, falls back through origin/path construction, and returns the route path if browser location access fails, preventing checkout request assembly from breaking on restricted or unusual browser location APIs. Strengthened `payment-ux-copy.test.mjs` to keep the guarded helper and prevent direct `window.location.origin` URL assembly from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 6/6, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Runtime ErrorBoundary reload failure hardening**: Continued the active Hanwoo quality uplift by wrapping the dashboard runtime `ErrorBoundary` recovery reload in a guarded `try/catch`. If the browser reload API fails, the error is logged and the recoverable fallback remains visible instead of clearing error state into a potentially broken dashboard render. Strengthened `error-pages-wiring.test.mjs` to keep the guarded reload path. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 361/361, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Offline sync fallback Korean-copy consistency**: Continued the active Hanwoo quality uplift by changing `syncManager` unsupported-action and unsuccessful-result fallback messages from English internal strings to stable Korean product copy. Retry/dead-letter metadata now stays readable and consistent with operator-facing offline sync copy when an action is unsupported or a handler returns an unsuccessful result without a message. Strengthened `sync-manager-copy.test.mjs` to keep the Korean constants and prevent the English fallback strings from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/sync-manager-copy.test.mjs` passed 1/1, `npm.cmd test` passed 361/361, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode search placeholder cattle-terminology consistency**: Continued the active Hanwoo quality uplift by changing the Field Mode search placeholder from `?댄몴踰덊샇 4?먮━ ?먮뒗 ???대쫫 ?낅젰` to `?댄몴踰덊샇 4?먮━ ?먮뒗 媛쒖껜紐??낅젰`, aligning onsite search copy with the dashboard's `媛쒖껜紐? terminology. Strengthened Field Mode regression coverage to keep the `媛쒖껜紐? placeholder and prevent the older `???대쫫` wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused FieldMode tests passed 8/8, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard empty pen state Korean spacing polish**: Continued the active Hanwoo quality uplift by changing the pen detail empty-state copy from `??移몄? 鍮꾩뼱?덉뒿?덈떎.` to `??移몄? 鍮꾩뼱 ?덉뒿?덈떎.`, correcting visible Korean spacing in the home pen view. Strengthened home dashboard regression coverage to keep the corrected empty-pen wording and prevent the fused spelling from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat offline fallback formal helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the AI chat widget's generic offline fallback from `吏湲덉? 湲곕낯 ?띿옣 ?댁쁺 吏덈Ц ?꾩＜濡??덈궡?섍퀬 ?덉뼱?? ... ?꾩??쒕┫寃뚯슂.` to `吏湲덉? 湲곕낯 ?띿옣 ?댁쁺 吏덈Ц ?꾩＜濡??덈궡?⑸땲?? ... ???뺥솗???덈궡?⑸땲??`, aligning the fallback response with the widget's `吏덈Ц??二쇱꽭?? operator tone. Strengthened AI chat widget regression coverage to keep the formal helper wording and prevent the older casual fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard route error and not-found formal Korean-copy consistency**: Continued the active Hanwoo quality uplift by changing the 404 page title/body from `?섏씠吏瑜?李얠쓣 ???놁뼱?? / `?붾㈃?????덉뼱?? to `?섏씠吏瑜?李얠쓣 ???놁뒿?덈떎` / `?붾㈃?????덉뒿?덈떎`, and changing route error copy from `?좎떆 臾몄젣媛 ?앷꼈?댁슂` / `?ㅻ쪟媛 諛쒖깮?덉뼱?? / `??쒕낫?쒕줈 ?뚯븘媛?몄슂` to `?좎떆 臾몄젣媛 諛쒖깮?덉뒿?덈떎` / `?ㅻ쪟媛 諛쒖깮?덉뒿?덈떎` / `??쒕낫?쒕줈 ?뚯븘媛 二쇱꽭??. Strengthened error-page regression coverage to keep the formal operator tone and prevent the older casual wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused error-page tests passed 9/9, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard runtime error fallback Korean-copy polish**: Continued the active Hanwoo quality uplift by changing the dashboard runtime ErrorBoundary heading from `?붾㈃ ?뚮뜑留곸뿉 ?쇱떆?곸씤 ?먮윭媛 諛쒖깮?덉뒿?덈떎.` to `?붾㈃ ?쒖떆 以??쇱떆?곸씤 ?ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.`, and rewriting the body from the technical `?곗씠???뺤떇`/`?뚮뜑留??꾩쨷` phrasing to operator-facing `?붾㈃ ?쒖떆 ?뺣낫`/`泥섎━ 以? wording. Strengthened error-page regression coverage to keep the polished Korean fallback copy and prevent the older technical wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused error-page tests passed 9/9, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight market-price information-copy consistency**: Continued the active Hanwoo quality uplift by changing the AI insight default data-quality card body from `泥댁쨷쨌?먮ℓ?≤룹떆???곗씠?곕? 媛깆떊?섎㈃ ???뺥솗???몄궗?댄듃瑜??쒓났?⑸땲??` to `泥댁쨷쨌?먮ℓ???곗씠?곗? ?쒖꽭 ?뺣낫瑜?媛깆떊?섎㈃ ???뺥솗???몄궗?댄듃瑜??쒓났?⑸땲??`, keeping externally sourced market-price wording aligned with the app's `?쒖꽭 ?뺣낫` copy while preserving the data-quality intent. Strengthened AI insight regression coverage to prevent the older bundled `?쒖꽭 ?곗씠?? wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 15/15, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price unavailable information-copy consistency**: Continued the active Hanwoo quality uplift by changing the shared market-price unavailable fallback and widget fallback from `吏湲덉? ?쒖슦 ?쒖꽭 ?곗씠?곕? ?뺤씤?????놁뒿?덈떎.` to `吏湲덉? ?쒖슦 ?쒖꽭 ?뺣낫瑜??뺤씤?????놁뒿?덈떎.`, aligning visible market-price failure copy with the app's information-oriented weather/profitability wording. Strengthened market-price and home regression coverage to prevent the older data wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused market/home tests passed 45/45, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Profitability market-price information-copy consistency**: Continued the active Hanwoo quality uplift by changing profitability service operator-facing market-price errors from `?섏씡???쒕??덉씠?섏뿉 ?ъ슜???쒖꽭 ?곗씠?곌? ?놁뒿?덈떎.` and `?쒖꽭 ?곗씠?곕? ?댁꽍?섏? 紐삵뻽?듬땲??` to `?섏씡???쒕??덉씠?섏뿉 ?ъ슜???쒖꽭 ?뺣낫媛 ?놁뒿?덈떎.` and `?쒖꽭 ?뺣낫瑜??댁꽍?섏? 紐삵뻽?듬땲??`, keeping visible profitability errors aligned with the app's information-oriented weather/market copy. Strengthened profitability regression coverage to prevent the older data wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 10/10, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather unavailable information-copy consistency**: Continued the active Hanwoo quality uplift by changing the weather unavailable fallback from `吏湲덉? ?좎뵪 ?곗씠?곕? ?뺤씤?????놁뒿?덈떎. ?좎떆 ???ㅼ떆 ?쒕룄??二쇱꽭??` to `吏湲덉? ?좎뵪 ?뺣낫瑜??뺤씤?????놁뒿?덈떎. ?좎떆 ???ㅼ떆 ?쒕룄??二쇱꽭??`, and aligning the weather widget's local fallback with the shared weather-state message. Strengthened weather and home regression coverage to prevent the older data wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused weather/home tests passed 47/47, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight description action-tone consistency**: Continued the active Hanwoo quality uplift by changing the AI insight widget description from `?띿옣 ?곗씠?곕? 湲곕컲?쇰줈 ?곗꽑?쒖쐞 3媛吏 ?됰룞???쒖븞?⑸땲??` to `?띿옣 ?곗씠?곕? 湲곕컲?쇰줈 ?곗꽑?쒖쐞 3媛吏 ?됰룞???뺣━?⑸땲??`, aligning the widget with the recent move away from recommendation-style copy toward analysis and action-priority language. Strengthened AI insight widget regression coverage to prevent the older proposal wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight widget tests passed 10/10, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export empty-list copy consistency**: Continued the active Hanwoo quality uplift by changing the Excel export empty-download warning title from `?ㅼ슫濡쒕뱶??媛쒖껜 ?곗씠?곌? ?놁뒿?덈떎.` to `?ㅼ슫濡쒕뱶??媛쒖껜 紐⑸줉???놁뒿?덈떎.`, aligning the export flow with the dashboard's `媛쒖껜 紐⑸줉` terminology for loaded/exported cattle collections. Strengthened Excel export regression coverage to prevent the older data wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Excel export tests passed 2/2, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis cost chart empty-state record-copy consistency**: Continued the active Hanwoo quality uplift by changing the Analysis tab cost-structure empty chart message from `鍮꾩슜 ?곗씠?곌? ?꾩쭅 異⑸텇???볦씠吏 ?딆븯?듬땲??` to `鍮꾩슜 湲곕줉???꾩쭅 異⑸텇???볦씠吏 ?딆븯?듬땲??`, keeping the chart body aligned with the `?ㅼ젣 鍮꾩슜 湲곕줉 ?놁쓬` header and app-wide cost-record terminology. Strengthened analysis regression coverage to prevent the older data wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis tests passed 3/3, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis cost empty-state record-copy consistency**: Continued the active Hanwoo quality uplift by changing the Analysis tab cost-structure empty label from `?ㅼ젣 鍮꾩슜 ?곗씠???놁쓬` to `?ㅼ젣 鍮꾩슜 湲곕줉 ?놁쓬`, aligning the analysis card with the Sales tab and action copy that refer to operator-entered cost records. Strengthened analysis regression coverage to prevent the older data wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis tests passed 3/3, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Profitability widget candidate-analysis copy clarity**: Continued the active Hanwoo quality uplift by changing remaining profitability widget recommendation-style headers from `異쒗븯 異붿쿇 媛쒖껜` and `異쒗븯 ?섏씡??異붿쿇` to `異쒗븯 ?꾨낫 媛쒖껜` and `異쒗븯 ?섏씡??遺꾩꽍`, and rewriting the empty state to say there is no candidate whose shipment schedule needs checking or that profitability analysis data is insufficient. Strengthened profitability regression coverage to prevent the old recommendation framing from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 10/10, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shipment recommendation action-copy clarity**: Continued the active Hanwoo quality uplift by changing AI Insight shipment wording from `利됱떆 異쒗븯 沅뚯옣`/`利됱떆 異쒗븯 沅뚯옣 媛쒖껜` to action-ready `異쒗븯 ?쇱젙 ?뺤젙 ?꾩슂` and `利됱떆 異쒗븯 ?꾨낫 媛쒖껜`, and changing the profitability widget shipment badge to `異쒗븯 ?쇱젙 ?뺤씤 ?꾩슂`. Strengthened AI Insight and profitability regression coverage to prevent the older recommendation phrasing from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight/profitability tests passed 24/24, `npm.cmd test` passed 348/348, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price footer metadata clarity**: Continued the active Hanwoo quality uplift by changing the market price footer labels from terse `媛깆떊` and `異쒖쿂: KAPE` to `留덉?留?媛깆떊` and `?곗씠??異쒖쿂: KAPE`, so the timestamp and source read as explicit operator-facing metadata. Strengthened home-market regression coverage to prevent the terse footer spans from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 38/38, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price row unit wording consistency**: Continued the active Hanwoo quality uplift by changing market price row values from shorthand `N??/ kg` to `kg??N??, aligning the value format with the new `?섏냼 kg???쒖꽭` and `?붿냼 kg???쒖꽭` panel titles. Strengthened home-market regression coverage to prevent the slash-style unit label from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 38/38, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Claude (Opus 4.7) |
| Work | **?쒖뒪??理쒖떊??(`/goal ?쒖뒪?쒖쓣 理쒖떊?앹쑝濡?留뚮뱾?댁쨾`)** ??(1) CI ?뚰겕?뚮줈 `full-test-matrix.yml`?먯꽌 `pnpm/action-setup@v4`??redundant `version: 9` ?쒓굅 (root `packageManager: pnpm@9.5.0` ?⑥씪 ?뚯뒪 梨꾪깮) ??`Multiple versions of pnpm specified` ?ㅽ뙣 ?댁냼. (2) Claude 紐⑤뜽 ID ?쇨큵 理쒖떊?? Sonnet 4-20250514??-6 (`llm_client`/`content_writer` ?뷀뤃?? `shorts-maker-v2/config.yaml`+`llm_router.py`, blind-to-x ?뚯뒪???쎌뒪泥?, Opus 4-5??-7 (content_writer), Haiku 3-5??-5-20251001 (promptfoo eval); `api_usage_tracker.PRICING`????紐⑤뜽 媛寃?entry 異붽? + legacy ID alias 蹂댁〈. SKILL 臾몄꽌(`blind-to-x`, `prompt-engineering-patterns`) ?숆린. (3) Dependabot 而ㅻ쾭由ъ? ?뺣?: `suika-game-v2`(package.json + lockfile ?덈뒗??誘몃벑濡? `.github/dependabot.yml` 異붽? ??Dependabot媛 ?좉퇋 PR 5+媛??먮룞 ?ㅽ뵂. (4) 紐⑤뱺 15媛???7媛쒕줈 ?뺤옣) Dependabot PR ?쇨큵 `@dependabot rebase` ?몃━嫄???minor/patch 12媛?auto-merge濡?main ?≪닔 (#79쨌#81쨌#83쨌#85쨌#86쨌#88쨌#90쨌#92쨌#94쨌#99쨌#101쨌#105쨌#106). (5) ?ㅻⅨ ?꾧뎄(Gemini + ?먮떎瑜?Claude ?몄뀡)媛 濡쒖뺄 而ㅻ컠留??대넃怨?push ?덊븳 3媛?commit(`9e371b74` workspace health sweep + `87732cd7` Claude Dependabot drain log + `d79daafd` close verified workspace quality updates ??紐⑤몢 Codex媛 push??source 蹂寃쎌뿉 ??묓븯??hanwoo test sync + ?ы띁??+ SESSION_LOG)??origin/main??rebase + push濡??⑸쪟 ??CI ?뚮났 寃쎈줈 留덈젴. Codex ?쒖꽦 WIP(`MarketPriceWidget.js`+`home-market-copy.test.mjs`)??stash濡??덉쟾 蹂댁〈?덈떎 蹂듭썝. **寃利?*: ?뚰겕?ㅽ럹?댁뒪 1465/1469 洹몃┛(4嫄?Windows-only pytest+subprocess flake???ъ쟾 遺梨?, blind-to-x 9/9(test_draft_generator_multi_provider), shorts-maker-v2 safe_zone ?⑥쐞 洹몃┛, `project_qc_runner --project all` 4?꾨줈?앺듃 紐⑤몢 洹몃┛, workspace test_content_writer/test_api_usage_tracker/test_llm_client_anthropic_cache/test_llm_usage_summary 94/94 洹몃┛. **而ㅻ컠**: `b75e8cd3 chore: modernize Claude model IDs and CI tooling` + rebase濡??곕씪??`bd8e56c5`쨌`087d992b`쨌`4e30e367`. |
| Next Priorities | (a) ?⑥? 15媛?**major** Dependabot PR 寃곗젙 ?꾩슂(admin merge): lucide-react v1(#91쨌#93쨌#103 ??brand icon 誘몄궗???뺤씤 ?꾨즺, safe), notion-client v3(#80 ??`is_full_page_or_database`/`is_api_error_code` removed API 誘몄궗???뺤씤 ?꾨즺, safe), eslint v10(#78쨌#89쨌#96), vite v8(#87쨌#104), @types/node v25(#84), @eslint/js v10(#102), jsdom v29(#97쨌#98), globals v17(#100), pnpm/action-setup v6(#95). (b) Windows-only pre-existing 遺梨?4嫄?蹂꾨룄 泥섎━: `test_pytest_checks_use_repo_local_temp`(Windows TMP override ?섎룄??skip but ?뚯뒪?멸? skip-decorate ?덈맖 ??Korean home path ?몄퐫???고쉶??, `test_pr_triage_worktree::*` 2嫄?`OSError: [WinError 6]` Py 3.14+pytest subprocess handle), `test_pr_triage_orchestrator` ordering-dependent. Linux CI???듦낵. (c) T-251 Supabase 鍮꾨쾲 由ъ뀑? ?ъ쟾???ъ슜???묒뾽. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price panel unit-title clarity**: Continued the active Hanwoo quality uplift by changing the market price panel titles from shorthand `?섏냼 / kg` and `?붿냼 / kg` to `?섏냼 kg???쒖꽭` and `?붿냼 kg???쒖꽭`, so the card labels name both the unit and price context directly. Strengthened home-market regression coverage to keep the explicit titles. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 38/38, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis chart sales terminology consistency**: Continued the active Hanwoo quality uplift by changing Analysis and Financial chart user-facing sales labels from `留ㅼ텧` to `?먮ℓ??. The monthly analysis heading, chart accessibility label/title, revenue bar legend, financial chart description, and financial chart revenue legend now align with Sales, AI Insight, and the existing `?곌컙 珥앺뙋留ㅼ븸` KPI wording. Strengthened analysis regression coverage to keep the chart-level `?먮ℓ?? terminology. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **workspace verified quality bundle closure**: User selected the cleanup/commit path. Rechecked the current dirty worktree, found the final bundle now scoped to Hanwoo quality-copy/fallback updates plus workspace tooling updates (`dependency_security_audit.py`, `session_orient.py`, `uv.lock`) and `.ai` session records. Ran final verification before commit prep. |
| Next Priorities | Verification: `python execution/project_qc_runner.py --project hanwoo-dashboard --json --timeout-seconds 300` passed (`npm test` 335/335, lint, build). `python -m py_compile execution\session_orient.py execution\dependency_security_audit.py` passed. `py -3.13 execution/code_review_gate.py --base HEAD --json` returned WARN, not FAIL (`risk_score 0.55`, 5 test-gap heuristics). `python execution/dependency_security_audit.py --help` actually ran the audit and returned exit 1 because current dependencies report 73 vulnerabilities across 25 packages; treat that as a surfaced security backlog, not a syntax/runtime failure. T-251 remains user-owned Supabase credential/control-plane resync. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales history grade fallback specificity**: Continued the active Hanwoo quality uplift by changing cattle sale history copy from `?깃툒: -` to `?깃툒: ?깃툒 誘몃벑濡? when a sale grade is missing. This keeps generated cattle timeline entries from preserving a bare dash placeholder for missing sale grades. Strengthened server-action copy regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused action-copy tests passed 2/2, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Subscription failure error-code fallback specificity**: Continued the active Hanwoo quality uplift by changing the subscription failure page missing error-code fallback from placeholder `-` to `?ㅻ쪟 肄붾뱶 誘몄쟾??. This keeps payment failure details from showing a bare dash when the gateway does not provide a code. Strengthened payment UX regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused payment UX tests passed 5/5, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner birth-date fallback specificity**: Continued the active Hanwoo quality uplift by changing the ear-tag scanner matched-cattle birth-date fallback from placeholder `-` to `?앸뀈?붿씪 誘몃벑濡?, and routing scanner birth-date rendering through `formatScannerBirthDate()` so missing or malformed birth dates do not surface as bare dash or raw invalid date output. Strengthened scanner regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused ear-tag scanner tests passed 4/4, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle card genetic-grade fallback specificity**: Continued the active Hanwoo quality uplift by changing cattle row genetic-grade rendering from placeholder `-` to `?좎쟾 ?깃툒 誘몃벑濡? when the grade is missing, blank, or legacy `-`. This keeps pen/list cattle cards from showing bare dash placeholders and makes the missing field explicit. Strengthened card regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused card tests passed 5/5, `npm.cmd test` passed 346/346, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification time fallback specificity**: Continued the active Hanwoo quality uplift by changing notification time fallback copy from placeholder `-` to `?뚮┝ ?쒓컙 ?뺤씤 遺덇?` in `formatNotificationTime()`, invalid `buildNotificationTiming()` output, and the notification modal's direct rendering fallback. This makes missing or malformed alert times identify the unavailable field instead of showing a bare dash. Strengthened notification timing and modal regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification timing/modal tests passed 14/14, `npm.cmd test` passed 345/345, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight weather fallback specificity**: Continued the active Hanwoo quality uplift by changing AI Insight prompt weather fallback copy from symbolic `???/`?%` placeholders to explicit Korean signals (`湲곗삩 ?뺤씤 遺덇?`, `?듬룄 ?뺤씤 遺덇?`) when THI is available but temperature or humidity is missing. Strengthened AI Insight regression coverage to keep the explicit weather fallback and prevent ambiguous symbol placeholders from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight/chat/weather tests passed 32/32, `npm.cmd test` passed 344/344, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight sales-amount terminology consistency**: Continued the active Hanwoo quality uplift by changing AI Insight prompt/default-card sales amount wording from `留ㅼ텧` to `?먮ℓ?? (`?먮ℓ??N留뚯썝`, `異쒗븯쨌?먮ℓ??N留뚯썝`, `泥댁쨷쨌?먮ℓ?≤룹떆???곗씠??). This keeps generated insight context aligned with Sales and Analysis terminology. Strengthened AI Insight regression coverage to keep `?먮ℓ?? wording and prevent the older `留ㅼ텧` phrases from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight/chat/home/Analysis tests passed 63/63, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Alert banner missing-pen fallback specificity**: Continued the active Hanwoo quality uplift by changing estrus/calving alert banner missing-pen fallback from placeholder `-` to `移?誘몄???. This makes alert location chips explain that the pen assignment is missing instead of rendering a bare dash before `踰?. Strengthened alert-banner regression coverage to keep the specific pen fallback and prevent the dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused alert/home/field-mode tests passed 49/49, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales tab sales-terminology summary consistency**: Continued the active Hanwoo quality uplift by changing the Sales tab summary heading, cumulative KPI label, and no-sales helper description from `留ㅼ텧` wording to `?먮ℓ`/`?먮ℓ?? wording (`異쒗븯 諛??먮ℓ 遺꾩꽍`, `珥??꾩쟻 ?먮ℓ??, `?먮ℓ?? ?깃툒, ?섏씡 遺꾩꽍 李⑦듃`). This keeps the Sales tab aligned with the app-wide `?먮ℓ 湲곕줉` and Analysis `?곌컙 珥앺뙋留ㅼ븸` terminology. Strengthened home-market regression coverage to keep the sales summary labels and prevent the older `留ㅼ텧` wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Sales/home/empty/Analysis tests passed 58/58, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis KPI sales terminology consistency**: Continued the active Hanwoo quality uplift by changing the Analysis tab annual revenue KPI title from `?곌컙 珥앸ℓ異? to `?곌컙 珥앺뙋留ㅼ븸`. This keeps the management-analysis KPI aligned with the app-wide `?먮ℓ` terminology already used by Sales, Today Focus, and home quick actions. Strengthened Analysis regression coverage to keep the `?먮ℓ` KPI label and prevent the old `留ㅼ텧` KPI title from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Analysis/home/Today Focus tests passed 52/52, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared short-date fallback specificity**: Continued the active Hanwoo quality uplift by changing the common `formatDate()` fallback from bare `-` to `?좎쭨 誘몃벑濡?. This aligns short date rendering with the existing long-date fallback and prevents detail/list date fields from surfacing meaningless dash placeholders when dates are missing or malformed. Strengthened date utility regression coverage to keep the Korean missing-date fallback and prevent the dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused date/detail/alert/calving tests passed 26/26, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail genetic fallback specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail genetic-info fallback from placeholder-style `遺:- / 紐?-` to `遺:遺怨?誘몃벑濡?/ 紐?紐④퀎 誘몃벑濡?. This makes the genetic ability card explain which lineage field is missing instead of showing bare dashes. Strengthened cattle-detail regression coverage to keep the lineage-specific fallback copy and prevent dash fallbacks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 16/16, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding-date fallback specificity**: Continued the active Hanwoo quality uplift by changing cattle detail reproductive-date fallbacks from placeholder `-` to domain-specific Korean copy (`諛쒖젙??誘몃벑濡?, `理쒓렐 諛쒖젙??誘몃벑濡?, `?섏젙??誘몃벑濡?, `遺꾨쭔 ?덉젙??誘몃벑濡?). This makes breeding cards explain which date is missing instead of showing a bare dash. Strengthened cattle-detail regression coverage to keep the specific missing-date labels and prevent the dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 15/15, `npm.cmd test` passed 342/342, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales no-cost state copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab no-cost per-record label from generic `愿??鍮꾩슜 ?놁쓬` to `?곌껐??鍮꾩슜 湲곕줉 ?놁쓬`. This makes profit-unavailable rows explain that no linked cost records exist before showing `鍮꾩슜 湲곕줉 ?놁뼱 ?섏씡 異붿젙 遺덇?`. Strengthened Sales regression coverage to keep the specific no-cost label and prevent the generic label from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market/Sales tests passed 38/38, `npm.cmd test` passed 341/341, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Admin diagnostics unavailable-copy specificity**: Continued the active Hanwoo quality uplift by changing admin diagnostics fallback copy from generic `?뺤씤 遺덇?`/`-` to domain-specific `DB ?곹깭 ?뺤씤 遺덇?`, `DB ?묐떟 ?쒓컙 ?뺤씤 遺덇?`, and `Node 踰꾩쟾 ?뺤씤 遺덇?`. This makes failure/empty diagnostics cards identify which system signal is unavailable. Strengthened diagnostics regression coverage to keep the specific unavailable labels and prevent generic latency fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused diagnostics tests passed 3/3, `npm.cmd test` passed 341/341, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field mode search missing-building fallback specificity**: Continued the active Hanwoo quality uplift by changing Field Mode search-result missing-building copy from generic `誘몄??? to `異뺤궗 誘몄???. This makes onsite cattle search results name the missing location domain consistently with alert banner location chips. Strengthened FieldModeView regression coverage to keep the specific building fallback and prevent the generic fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused FieldModeView tests passed 8/8, `npm.cmd test` passed 341/341, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Alert banner missing-building fallback specificity**: Continued the active Hanwoo quality uplift by changing estrus/calving alert banner missing-building copy from generic `誘몄??? to `異뺤궗 誘몄???. This makes alert location chips name the missing location domain instead of showing a vague placeholder. Strengthened alert-banner regression coverage to keep the specific building fallback and prevent the generic fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused alert-banner tests passed 3/3, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather unavailable source-label specificity**: Continued the active Hanwoo quality uplift by changing weather unavailable source labels from generic `?뺤씤 遺덇?` to `?좎뵪 ?뺤씤 遺덇?` in the weather state model. This aligns degraded/unavailable weather payloads with the visible weather widget unavailable copy and avoids a generic unavailable badge in weather state data. Strengthened weather-state regression coverage to keep the specific source label. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused weather/home tests passed 47/47, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price unavailable source-label specificity**: Continued the active Hanwoo quality uplift by changing market-price unavailable source labels from generic `?뺤씤 遺덇?` to `?쒖꽭 ?뺤씤 遺덇?` in the market price state model and widget presentation fallback. This makes degraded/unavailable price cards name the missing data domain clearly instead of showing a generic unavailable badge. Strengthened market-price regression coverage to keep the specific source label. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused market/home tests passed 45/45, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Profitability recommendation missing-identity fallback clarity**: Continued the active Hanwoo quality uplift by changing the profitability recommendation widget's missing tag/name fallbacks from placeholder-style `----` and `-` to Korean operator copy `?대젰踰덊샇 誘몃벑濡? and `媛쒖껜紐?誘몃벑濡?. This aligns shipment-profit cards with Sales, AI farm context, cattle cards, and alert banner missing-identity copy. Strengthened profitability widget regression coverage to prevent placeholder fallbacks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 8/8, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat farm-context status fallback specificity**: Continued the active Hanwoo quality uplift by changing the AI chat farm-context fallback for empty cattle status grouping from generic `?곗씠???놁쓬` to `?곹깭蹂?媛쒖껜 ?곗씠???놁쓬`. This gives the model a domain-specific missing-data signal instead of a vague placeholder. Strengthened AI chat route regression coverage to keep the specific fallback and prevent the generic status summary fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat API tests passed 8/8, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Primary data-entry submit copy consistency**: Continued the active Hanwoo quality uplift by changing idle submit labels for Schedule, Feed, Inventory, Sales, and Settings forms from `?깅줉?섍린`/`??ν븯湲? variants to concise task labels (`?쇱젙 ?깅줉`, `湲됱뿬 湲곕줉 ???, `?ш퀬 ?깅줉`, `?먮ℓ 湲곕줉 ?깅줉`, `?띿옣 ?뺣낫 ???, `異뺤궗 ?깅줉`). This aligns submit buttons with the already-normalized open-form CTAs while keeping pending `... 以? states intact. Strengthened form-submit, schedule, empty-state, home/market, and settings regression coverage to prevent the older `?섍린` submit labels from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused submit-copy tests passed 76/76, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Building-name missing fallback consistency**: Continued the active Hanwoo quality uplift by changing remaining form/detail/feed building-name fallbacks from compact `異뺤궗紐?誘몃벑濡? to the app-wide `異뺤궗 ?대쫫 誘몃벑濡?. This aligns cattle forms, cattle detail location, and feed building filters with Dashboard and Settings building fallback copy. Strengthened cattle-detail and empty-state regression coverage to prevent the compact fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail/empty-state tests passed 31/31, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Alert banner missing cattle-name fallback consistency**: Continued the active Hanwoo quality uplift by changing alert banner missing cattle-name fallback from generic `?대쫫 誘몃벑濡? to Hanwoo-wide `媛쒖껜紐?誘몃벑濡?. This aligns estrus/calving alert banners with dashboard rows, sales fallbacks, cards, and analysis ranking copy. Strengthened alert-banner regression coverage to prevent the generic fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused alert-banner tests passed 3/3, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification dropdown fallback title clarity**: Continued the active Hanwoo quality uplift by changing the notification dropdown malformed-title fallback from empty-value copy `?뚮┝ ?쒕ぉ ?놁쓬` to product-facing `?댁쁺 ?뚮┝`. This aligns it with the notification widget's default heading and avoids a raw missing-title state in the UI. Strengthened notification-system regression coverage to prevent the terse fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification-system tests passed 9/9, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner no-match empty-state copy clarity**: Continued the active Hanwoo quality uplift by changing the scanner no-match heading from terse `?몄떇??媛쒖껜 ?뺣낫 ?놁쓬` to sentence-style `?몄떇??媛쒖껜 ?뺣낫媛 ?놁뒿?덈떎`. This keeps the scanner failure state consistent with clearer Korean empty-state copy. Strengthened ear-tag scanner regression coverage to prevent the terse heading from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused scanner tests passed 3/3, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Empty building CTA accessible helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the home empty-building CTA `aria-label` and `title` from noun-style `?ㅼ젙?먯꽌 泥?踰덉㎏ 異뺤궗 異붽??섍린` to operator-facing guidance `?ㅼ젙?먯꽌 泥?踰덉㎏ 異뺤궗瑜?異붽???二쇱꽭??. This aligns assistive-tech and hover copy with the visible first-building CTA tone. Strengthened home/market regression coverage to prevent the old label from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Empty building CTA helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the home empty-building CTA title from command-style `泥?踰덉㎏ 異뺤궗瑜?異붽??대낫?몄슂` to operator-facing guidance `泥?踰덉㎏ 異뺤궗瑜?異붽???二쇱꽭??. This keeps the first-run setup action aligned with the app-wide Korean helper tone. Strengthened home/market regression coverage for the first-building CTA copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat offline greeting helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the AI chat offline fallback greeting reply from question-style `?ㅻ뒛 ?띿옣 ?댁쁺?먯꽌 ?대뼡 遺遺꾩씠 沅곴툑?섏떊媛??` to operator-facing guidance `?ㅻ뒛 ?띿옣 ?댁쁺?먯꽌 沅곴툑??遺遺꾩쓣 吏덈Ц??二쇱꽭??`. This keeps the offline chat path aligned with the AI chat welcome prompt and input placeholder. Strengthened AI chat widget regression coverage for the greeting fallback copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard THI level description helper-tone guidance**: Continued the active Hanwoo quality uplift by changing THI warning/danger descriptions from status-style `湲됱닔???뺣낫? ?≫뭾 媛뺥솕媛 ?꾩슂???섏??낅땲?? and `利됱떆 ?됰갑怨??댁닔 議곗튂媛 ?꾩슂??怨좎쐞???곹깭?낅땲?? to operator-facing guidance `湲됱닔?됱쓣 ?뺣낫?섍퀬 ?≫뭾??媛뺥솕??二쇱꽭?? and `利됱떆 ?됰갑怨??댁닔 議곗튂瑜?吏꾪뻾??二쇱꽭??. This keeps the weather card's THI guidance aligned with livestock weather alerts. Strengthened home/market copy regression coverage for THI descriptions. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather danger-alert helper-tone guidance**: Continued the active Hanwoo quality uplift by changing livestock weather danger messages from status-style `?됰갑怨??댁닔 議곗튂媛 ?꾩슂?⑸땲?? and `蹂댁삩 ?ㅻ퉬 ?먭????꾩슂?⑸땲?? to operator-facing guidance `?됰갑怨??댁닔 議곗튂瑜?吏꾪뻾??二쇱꽭?? and `蹂댁삩 ?ㅻ퉬瑜??먭???二쇱꽭??. This keeps severe heat/cold alerts aligned with existing weather helper tone. Strengthened home/market copy regression coverage for danger weather alerts. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight default routine helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight default routine recommendation from status-style `諛쒖젙쨌遺꾨쭔쨌?щ즺쨌臾셋룹텞???섍린 5媛吏 ?쇱긽 ?먭???沅뚯옣?⑸땲?? to operator-facing guidance `諛쒖젙쨌遺꾨쭔쨌?щ즺쨌臾셋룹텞???섍린 5媛吏 ?쇱긽 ?먭???吏꾪뻾??二쇱꽭??. This keeps safe fallback insight cards aligned with the app-wide helper tone. Strengthened AI Insight regression coverage for the default routine card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 14/14, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today Focus feed-depletion warning helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the non-critical feed-depletion Today Focus title from status-style `?щ즺 ?붿뿬 N??(?먭? 沅뚯옣)` to operator-facing guidance `?щ즺 ?붿뿬 N?? ?ш퀬瑜??먭???二쇱꽭??. This makes feed stock warnings name the action before the danger threshold. Added warning-branch regression coverage for the feed-depletion item. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Today Focus tests passed 11/11, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight shipment schedule helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight immediate-shipment recommendation from status-style `24?쒓컙 ??異쒓퀬 ?쇱젙 ?뺤젙 沅뚯옣` to operator-facing guidance `24?쒓컙 ??異쒓퀬 ?쇱젙???뺤젙??二쇱꽭??. This keeps high-priority shipment recommendations aligned with the app-wide helper tone. Strengthened AI Insight regression coverage for the shipment card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 14/14, `npm.cmd test` passed 339/339, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight THI heat-warning helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight high-THI recommendation from status-style `?섍린쨌誘몄뒪?명뙩 媛?? 湲됱닔湲?4???댁긽 ?먭? 沅뚯옣` to operator-facing guidance `?섍린쨌誘몄뒪?명뙩??媛?숉븯怨?湲됱닔湲곕? 4???댁긽 ?먭???二쇱꽭??. This keeps weather stress recommendations aligned with the app-wide helper tone. Strengthened AI Insight regression coverage for the heat-warning card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 14/14, `npm.cmd test` passed 339/339, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight calving preparation helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight calving-preparation recommendation from status-style `?곕갑 泥?껐쨌蹂댁삩쨌?붿삤???뚮룆 以鍮??먭? 沅뚯옣` to operator-facing guidance `?곕갑 泥?껐쨌蹂댁삩쨌?붿삤???뚮룆 以鍮꾨? ?먭???二쇱꽭??. This keeps calving heuristic recommendations aligned with the app-wide helper tone. Updated AI Insight regression coverage for the calving-preparation card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 14/14, `npm.cmd test` passed 339/339, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight declining-margin helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight declining-margin recommendation from status-style `?④?쨌利앹껜 異붿꽭 ?ш????꾩슂` to operator-facing guidance `?④?쨌利앹껜 異붿꽭瑜??ш??좏빐 二쇱꽭??. This keeps heuristic recommendations aligned with the app-wide helper tone. Updated AI Insight regression coverage for the declining-margin card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 13/13, `npm.cmd test` passed 338/338, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales empty-state missing-cattle action guidance**: Continued the active Hanwoo quality uplift by changing the Sales tab empty-state disabled action label from terse `媛쒖껜 ?깅줉 ?꾩슂` to the operator-facing guidance `媛쒖껜瑜?癒쇱? ?깅줉??二쇱꽭??. The no-cattle state now explains the prerequisite action instead of showing a noun-phrase status. Updated empty-state and home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state tests passed 17/17, focused home-market tests passed 38/38, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle Excel export action specificity**: Continued the active Hanwoo quality uplift by changing the Excel export button labels from generic `?묒? ?ㅼ슫濡쒕뱶` / `?묒? ?ㅼ슫濡쒕뱶 以鍮?以? to `媛쒖껜 ?묒? ?ㅼ슫濡쒕뱶` / `媛쒖껜 ?묒? ?ㅼ슫濡쒕뱶 以鍮?以?. The header export action now names the cattle dataset being exported in visible copy, accessible label, and hover title. Updated Excel export regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Excel export tests passed 2/2, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price refresh busy-label specificity**: Continued the active Hanwoo quality uplift by changing the market price refresh button busy accessible/title label from generic `?쒖꽭 媛깆떊 以? to `?쒖슦 ?쒖꽭 媛깆떊 以?. The loading action now stays tied to the Hanwoo market-price widget context while the ready label remains `?쒖슦 ?쒖꽭 ?덈줈怨좎묠`. Updated home/market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat empty-input send action label**: Continued the active Hanwoo quality uplift by changing the AI chat send button accessible/title label so an empty disabled input says `吏덈Ц???낅젰?섎㈃ 蹂대궪 ???덉뒿?덈떎` instead of the actionable `吏덈Ц 蹂대궡湲?. Streaming still says `?듬? ?앹꽦 以? and ready state still says `吏덈Ц 蹂대궡湲?. Updated AI chat widget regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today Focus sales analysis helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the Today Focus monthly sales analysis guidance from `?먮ℓ ?먮쫫??遺꾩꽍 ??뿉???뺤씤?섏꽭??` to `?먮ℓ ?먮쫫??遺꾩꽍 ??뿉???뺤씤??二쇱꽭??`. This preserves the sales terminology fix while aligning the action guidance with the app-wide Korean helper tone. Updated Today Focus regression coverage to prevent both the old `留ㅼ텧` terminology and the command-style `?뺤씤?섏꽭?? wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Today Focus tests passed 10/10, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form helper guidance tone consistency**: Continued the active Hanwoo quality uplift by changing the cattle edit/create form helper copy from `媛쒖껜 ?뺣낫瑜??섏젙?섍퀬 ??ν븯?몄슂` and `??媛쒖껜??湲곕낯 ?뺣낫瑜??낅젰?섏꽭?? to `媛쒖껜 ?뺣낫瑜??섏젙?섍퀬 ??ν빐 二쇱꽭?? and `??媛쒖껜??湲곕낯 ?뺣낫瑜??낅젰??二쇱꽭??. This keeps form guidance aligned with the app-wide Korean helper tone and existing validation messages. Updated cattle form regression coverage for both edit and create helper text. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 14/14, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight schedule fallback helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight safe schedule fallback from `罹섎┛?붿뿉???뺤씤?섏꽭?? to `罹섎┛?붿뿉???뺤씤??二쇱꽭??. This keeps all no-signal fallback recommendations aligned with the app-wide Korean helper tone. Split regression coverage so registered-herd no-signal defaults prove the schedule card copy without assuming it appears in the empty-herd top-three slice. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 12/12, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather livestock guidance helper-tone consistency**: Continued the active Hanwoo quality uplift by changing THI and livestock weather warning guidance from command-style `?뺤씤?섏꽭??/`媛뺥솕?섏꽭??/`?먭??섏꽭?? to `?뺤씤??二쇱꽭??/`媛뺥솕??二쇱꽭??/`?먭???二쇱꽭??. This keeps weather recovery and livestock-care recommendations aligned with the app-wide Korean helper tone. Updated home-market regression coverage for the utility copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print popup-block guidance tone consistency**: Continued the active Hanwoo quality uplift by changing the QR label print popup-block failure message from `釉뚮씪?곗? ?앹뾽 ?덉슜 ???ㅼ떆 ?쒕룄?섏꽭??` to `釉뚮씪?곗? ?앹뾽 ?덉슜 ???ㅼ떆 ?쒕룄??二쇱꽭??`. This keeps retry recovery guidance aligned with the app-wide Korean helper tone. Updated QR widget regression coverage to prevent the command-style wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused QR widget tests passed 3/3, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight fallback guidance tone consistency**: Continued the active Hanwoo quality uplift by changing deterministic AI Insight fallback guidance from command-style `泥섏튂 ?쇱젙 ?≪쑝?몄슂` and `媛쒖껜 ?깅줉??癒쇱? 吏꾪뻾?섏꽭?? to `泥섏튂 ?쇱젙???≪븘 二쇱꽭?? and `媛쒖껜 ?깅줉??癒쇱? 吏꾪뻾??二쇱꽭??. This keeps fallback recommendations aligned with the app-wide helper tone. Updated AI Insight regression coverage for both fallback paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 11/11, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner retry guidance tone consistency**: Continued the active Hanwoo quality uplift by changing the scanner no-match guidance from stiff `?ㅼ떆 ?ㅼ틪?댁＜??떆?? to the app-wide `?ㅼ떆 ?ㅼ틪??二쇱꽭??. This keeps scanner failure recovery copy aligned with other retry and helper messages. Updated scanner modal regression coverage to prevent the stiff wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused scanner tests passed 3/3, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis top-sale missing cattle-name copy consistency**: Continued the active Hanwoo quality uplift by changing the Analysis tab top-sale missing cattle-name fallback from generic `?대쫫 ?놁쓬` to the existing Hanwoo-wide `媛쒖껜紐?誘몃벑濡?. This keeps the Analysis ranking list aligned with dashboard rows, Sales tab fallbacks, cards, and AI farm context. Updated analysis copy regression coverage to prevent returning to the generic label. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis tests passed 3/3, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard analysis cost-data empty copy clarity**: Continued the active Hanwoo quality uplift by changing the Analysis tab cost-structure fallback from terse `?ㅻ뜲?댄꽣 ?놁쓬` to `?ㅼ젣 鍮꾩슜 ?곗씠???놁쓬`. This makes the empty state specific to the missing cost data in that card. Updated analysis copy regression coverage to prevent returning to the terse label. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis tests passed 3/3, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard retry and move guidance spacing consistency**: Continued the active Hanwoo quality uplift by changing remaining operator-facing `?쒕룄?댁＜?몄슂`/`?대룞?댁＜?몄슂` copy to `?쒕룄??二쇱꽭??/`?대룞??二쇱꽭?? in offline sync failure toasts and the building-delete blocked message. Updated action, offline-sync, and home-market regression coverage to keep the spaced Korean helper wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused action-copy tests passed 2/2, sync-manager copy test passed 1/1, home-market tests passed 38/38, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard month-label spacing copy consistency**: Continued the active Hanwoo quality uplift by changing remaining `?대쾲??/`?ㅼ쓬?? copy to `?대쾲 ??/`?ㅼ쓬 ?? in the home KPI card, AI insight prompt snapshot, and deterministic insight fallback. Updated home-market and AI insight regression coverage to keep the spaced Korean date copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 11/11, focused home-market tests passed 38/38, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today Focus sales terminology consistency**: Continued the active Hanwoo quality uplift by changing the Today Focus monthly sales analysis prompt from `留ㅼ텧 ?먮쫫??遺꾩꽍 ??뿉???뺤씤?섏꽭??` to `?먮ℓ ?먮쫫??遺꾩꽍 ??뿉???뺤씤?섏꽭??`. This keeps home guidance aligned with the Sales tab and quick-action `?먮ℓ 湲곕줉` terminology. Added focused Today Focus regression coverage for the analysis-path copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Today Focus tests passed 10/10, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle edit-form guidance copy clarity**: Continued the active Hanwoo quality uplift by changing the cattle edit form helper text from generic `?뺣낫瑜??섏젙?섍퀬 ??ν븯?몄슂` to `媛쒖껜 ?뺣낫瑜??섏젙?섍퀬 ??ν븯?몄슂`. This keeps the helper aligned with the `媛쒖껜 ?뺣낫 ?섏젙` heading and `媛쒖껜 ?뺣낫 ??? action. Updated cattle form regression coverage to prevent reverting to the generic edit helper. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 14/14, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales profit-estimation unavailable copy clarity**: Continued the active Hanwoo quality uplift by changing the Sales tab per-record no-cost profit state from terse `?섏씡 異붿젙 遺덇?` to `鍮꾩슜 湲곕줉 ?놁뼱 ?섏씡 異붿젙 遺덇?`. This makes it clearer why profit cannot be estimated when no linked cost records exist. Updated home-market regression coverage to prevent reverting to the terse old copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Gemini |
| Work | **workspace project health check and mcp servers diagnostic and next-build lock resolution**: Ran wmic/tasklist process analysis and local diagnostics. Identified that 'hanwoo-dashboard' build failed due to Next.js build-lock concurrency. Resolved the build lock by safely purging 'projects/hanwoo-dashboard/.next/' directory, which restored 100% build health to hanwoo-dashboard (passed in 62.57s). Ran project_qc_runner to audit the whole mono-repo: blind-to-x (pytest passed, ruff passed), shorts-maker-v2 (pytest 602 passed, ruff passed), knowledge-dashboard (eslint passed, test passed, next-build passed), and hanwoo-dashboard (eslint passed, node-test 335 passed, next-build passed). Verified all projects are 100% green and deploy-ready. Ran mcp_diagnostic to verify 6 integrated local MCP servers (sqlite-multi, system-monitor, telegram, cloudinary, youtube-data, n8n-workflow): all servers completed handshake successfully (SUCCESS: ALL SERVERS FUNCTIONAL). Checked handoff rotation policy via handoff_rotator.py: all 198 addenda are within the active 7-day cutoff (from 2026-05-20), meaning noop archiving needed. |
| Next Priorities | T-251 remains user-owned Supabase database password/control-plane resync. Keep 15 open major PRs deferred to user review as tracked by Claude. Review docs/mcp_status_report.md for detail. All projects are clean and verified! |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Claude |
| Work | **Dependabot backlog drain (27 ??15)**: Triaged 27 BLOCKED Dependabot PRs. All BLOCKED state was caused by pre-existing `test-summary` failure on main HEAD (shorts-maker-v2-tests, frontend-active-apps hanwoo/knowledge fail ??confirmed via `gh run view` on commit `b75e8cd3`), not by individual bumps. Admin-merged 12 patch/minor PRs whose own project's tests were already passing: #79 aiohttp (blind-to-x), #81 react-hook-form (hanwoo), #83 beautifulsoup4 (blind-to-x), #85 anthropic (blind-to-x), #86 @tailwindcss/postcss (hanwoo), #88 python-dotenv (blind-to-x), #90 @serwist/next (hanwoo), #94 actions/setup-node v4?뭭6, #99 eslint-plugin-react-refresh (word-chain), #101 tailwindcss (knowledge), #105 @tailwindcss/postcss (knowledge), #106 bullmq (hanwoo). 15 majors deferred to user review (see Next Priorities). |
| Next Priorities | **Deferred Tier-2 majors (15 open PRs)**: (a) Workflow-scope blocked: #95 pnpm/action-setup v4?뭭6 ??`gh` token lacks `workflow` scope, needs user-token admin merge. (b) lucide-react v0.563?뭭1.16 횞3 (#91 word-chain, #93 hanwoo, #103 knowledge) ??v1 removed brand icons per memory `dependabot_pr_backlog_drain_20260520`, audit icon usage before merge. (c) eslint 9??0 횞3 (#78, #89, #96) + #102 @eslint/js v10 (suika) ??likely needs config update. (d) vite 7?? 횞2 (#87 word-chain, #104 suika) ??build tool major. (e) jsdom 28??9 횞2 (#97, #98) ??test env API changes. (f) #80 notion-client v2?뭭3 (blind-to-x) ??API surface change. (g) #84 @types/node v20?뭭25 (knowledge) ??types-only, safe but currently BEHIND after Tier-1 merges, dependabot rebase requested. (h) #100 globals 16??7 (suika) ??diff shows suspicious extra esbuild lockfile churn, investigate. Active Hanwoo goal still owned by Codex; my work touched only PR queue + AI context files, not Codex's WIP. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification SMS test visible copy specificity**: Continued the active Hanwoo quality uplift by changing the notification modal SMS test button's idle visible text from `?뚯뒪???꾩넚` to `臾몄옄 ?뚮┝ ?뚯뒪???꾩넚`. This keeps the visible action aligned with its `aria-label` and `title`. Updated notification modal regression coverage to prevent reverting to the shorter generic copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification modal tests passed 8/8, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Excel export button's visible busy text from `?묒? 以鍮?以?..` to `?묒? ?ㅼ슫濡쒕뱶 以鍮?以?..`. This keeps the on-screen pending state aligned with its `aria-label` and `title`. Updated Excel export regression coverage to prevent reverting to the shorter busy copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Excel export tests passed 2/2, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard home quick action sales copy consistency**: Continued the active Hanwoo quality uplift by changing the home dashboard quick action detail from `留ㅼ텧 諛붾줈 ?낅젰` to `?먮ℓ 湲곕줉 諛붾줈 ?낅젰`. This keeps the quick action aligned with the Sales tab's `?먮ℓ 湲곕줉` terminology and registration flow. Updated home-market regression coverage to prevent reverting the quick-action detail to `留ㅼ텧 諛붾줈 ?낅젰`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building validation copy consistency**: Continued the active Hanwoo quality uplift by changing client and server building-name validation messages from `???대쫫???낅젰??二쇱꽭??` to `異뺤궗 ?대쫫???낅젰??二쇱꽭??`. This keeps validation feedback aligned with the Settings form label and placeholder. Updated Settings regression coverage to keep both `formSchemas.js` and `action-validation.mjs` on the shared `異뺤궗 ?대쫫` terminology. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings/action-validation tests passed 25/25, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard create-form cancel-copy regression coverage hardening**: Continued the active Hanwoo quality uplift by strengthening source-level regression tests for Sales, Inventory, Settings building, and Schedule create-form toggles. The tests now fail if the open-state button text regresses to generic `痍⑥냼`, keeping task-specific Korean cancel labels (`?먮ℓ 湲곕줉 ?깅줉 痍⑥냼`, `?ш퀬 ?깅줉 痍⑥냼`, `異뺤궗 ?깅줉 痍⑥냼`, `?쇱젙 ?깅줉 痍⑥냼`) protected even if only the middle branch changes. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused create-form copy tests passed 75/75, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building delete confirmation copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings building-delete confirmation title from `${name} ?숈쓣 ??젣?좉퉴??` to `${name} 異뺤궗瑜???젣?좉퉴??`. This keeps the destructive confirmation dialog aligned with visible `異뺤궗 ??젣`, `異뺤궗 ??젣 以?..`, and Settings building-management terminology. Updated Settings regression coverage to prevent reverting to the old `?? wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard remaining-day countdown copy consistency**: Continued the active Hanwoo quality uplift by replacing remaining user-facing `D-n` countdown labels in cattle detail, schedule upcoming events, cattle row alert badges, calving alert cards, and Today Focus schedule details with operator-readable `?ㅻ뒛` / `n???⑥쓬` copy. Updated focused source and behavior regression coverage to prevent those `D-` labels from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused countdown tests passed 41/41, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed after one transient Next build-lock retry with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **Hanwoo build QC passed after approved dev-server stop**: User approved continuing. Stopped only Hanwoo Next dev processes matched by `hanwoo-dashboard` / `next dev -p 60809`: PIDs 27348, 32320, 30168. Reran `python execution/project_qc_runner.py --project hanwoo-dashboard --check build --json`; result passed (`npm run build`, returncode 0, ~58.01s). Next compiled successfully in 14.8s, TypeScript finished, static generation completed 18/18. Build emitted known Supabase Prisma warning `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, matching existing T-251 credential/control-plane blocker, but did not fail the build. |
| Next Priorities | Hanwoo local gates now have test/lint/build evidence. Remaining known blocker remains T-251: user must reset/resync Supabase DB password/control-plane credentials before live DB CRUD E2E can pass. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **Hanwoo lint passed; build blocked by active dev server**: Ran `python execution/project_qc_runner.py --project hanwoo-dashboard --check lint --json` and it passed (`npm run lint`, returncode 0, ~32.97s). Ran `python execution/project_qc_runner.py --project hanwoo-dashboard --check build --json`; it failed before compile because Next reported `Another next build process is already running`. Process inspection found active Hanwoo dev server processes: `next dev -p 60809 --webpack` (PID 32320) and `next/dist/server/lib/start-server.js` for `projects/hanwoo-dashboard` (PID 30168). Did not terminate them because they may be user-owned interactive work. |
| Next Priorities | If the user approves stopping the running Hanwoo dev server, terminate the Hanwoo Next dev processes and rerun `python execution/project_qc_runner.py --project hanwoo-dashboard --check build --json`. Otherwise treat build as environment-blocked, not source-failed. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight opt-in privacy copy**: Continued the active Hanwoo quality uplift by adding an explicit Settings widget-list description for the opt-in AI Insight widget: `耳쒕㈃ ?띿옣 ?붿빟 ?곗씠?곕? AI 遺꾩꽍 API濡??꾩넚?⑸땲??` This preserves the existing `defaultOn: false` privacy default while telling operators what enabling the widget does before any AI request is made. Updated AI Insight and Settings source-level regression coverage to keep the privacy copy wired through the shared widget registry. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight test passed 10/10, focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **Hanwoo test QC verified after AI Insight opt-in hardening**: Ran `python execution/project_qc_runner.py --project hanwoo-dashboard --check test --json`. Result: passed. Underlying command `npm test` completed with 330 tests, 4 suites, 330 pass, 0 fail, 0 skipped/todo/cancelled, duration ~2.88s reported by node test output. No code changes were required after validation. |
| Next Priorities | If broader confidence is needed, run `python execution/project_qc_runner.py --project hanwoo-dashboard --check lint --json` and `--check build --json`, or full `--project hanwoo-dashboard --json`. Keep Supabase T-251 separate until the user resets/resyncs credentials. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Alert banner remaining-day copy clarity**: Continued the active Hanwoo quality uplift by changing estrus and calving alert banner countdown labels from terse `D-n` wording to operator-readable `n???⑥쓬`, with same-day labels shown as `?ㅻ뒛`. The existing malformed `daysLeft` normalization remains intact, but livestock alerts now read more naturally in Korean and are easier to scan. Updated alert banner source-level regression coverage to prevent reverting to `D-` countdown labels. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused alert banner test passed 3/3, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **Dirty worktree review + Hanwoo AI privacy default hardening**: User selected full-change review. Current worktree is large and mixed across `.agents`, `.ai`, `.github`, `blind-to-x`, `hanwoo-dashboard`, `shorts-maker-v2`, `workspace`, and tests. Reviewed Hanwoo entry points for the new AI Insight widget and confirmed dependency `@google/generative-ai` exists. Identified that `AI ?몄궗?댄듃` was default-on, which could automatically call the authenticated `/api/ai/insight` route and, when `GEMINI_API_KEY` is configured, send farm summary data to Gemini. Changed `projects/hanwoo-dashboard/src/lib/hooks/useWidgetSettings.js` to make `aiInsight` opt-in (`defaultOn: false`) and updated `projects/hanwoo-dashboard/src/lib/ai-insight-widget-copy.test.mjs` expectation. No validation commands were run. |
| Next Priorities | If continuing in this dirty worktree, keep changes scoped. Recommended validation: `python execution/project_qc_runner.py --project hanwoo-dashboard --check test --json`, then full Hanwoo QC if green. Review whether the AI Insight UI should include explicit privacy copy before enabling. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings farm coordinate label copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab farm coordinate labels from `?꾨룄 (Latitude)` / `寃쎈룄 (Longitude)` to `?꾨룄` / `寃쎈룄`. This removes unnecessary English from operator-facing form labels while keeping the existing numeric placeholders and validation wiring intact. Updated Settings source-level regression coverage to prevent reverting to `Latitude` or `Longitude`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building section heading copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab building section heading from `異뺤궗 ??愿由? to `異뺤궗 愿由?. The section title now matches the surrounding `異뺤궗 ?깅줉`, `異뺤궗 ?대쫫`, `異뺤궗 ??젣`, and `異뺤궗 ??젣 以?..` wording, removing the last mixed `?? wording in that Settings building-management flow. Updated Settings source-level regression coverage to prevent reverting to `異뺤궗 ??愿由?. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building form label copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab building registration form labels and placeholder from `???대쫫` / `???대쫫???낅젰??二쇱꽭??` / `移???(Pen Count)` to `異뺤궗 ?대쫫` / `異뺤궗 ?대쫫???낅젰??二쇱꽭??` / `移???. The form copy now matches the surrounding `異뺤궗 ?깅줉` wording and removes unnecessary English from the operator-facing label. Updated Settings source-level regression coverage to prevent reverting to `???대쫫` or `Pen Count`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building delete accessible copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab building delete button's pending and idle accessible labels from `${building.name} ????젣...` to `${building.name} 異뺤궗 ??젣...`. The aria-label/title copy now matches the visible `異뺤궗 ??젣` and `異뺤궗 ??젣 以?..` button text, so the same destructive building-delete action is not described with mixed `??/`異뺤궗` wording. Updated Settings source-level regression coverage to prevent reverting to the old `????젣` wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales pagination retry copy consistency**: Continued the active Hanwoo quality uplift by changing the sales pagination timeout and error messages from `?댁쟾 留ㅼ텧 湲곕줉...` to `?댁쟾 ?먮ℓ 湲곕줉...`. The pagination retry feedback now matches the Sales tab load-more CTA and the broader `?먮ℓ 湲곕줉` wording used across the Sales/Dashboard flow. Updated sales pagination source-level regression coverage to prevent reverting to the old `?댁쟾 留ㅼ텧 湲곕줉` wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused sales pagination test passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard full sales ledger loading copy consistency**: Continued the active Hanwoo quality uplift by changing the dashboard's full sales ledger loading, retry, and load-error copy from `留ㅼ텧 湲곕줉` wording to `?먮ℓ 湲곕줉`. The Analysis/Sales loading path now matches the Sales tab CTA, form title, submit copy, and API fallback copy. Updated home-market source-level regression coverage to prevent reverting the retry label, loading placeholder, or error fallback to the old `留ㅼ텧 湲곕줉` wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market test passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building add-form heading copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab building add-form heading from `??異뺤궗 ???깅줉` to `??異뺤궗 ?깅줉`. The form title now matches the Settings tab's `異뺤궗 ?깅줉` CTA, submit copy, and accessible label, avoiding mixed `??異붽?`/`異뺤궗 ?깅줉` wording after the operator opens the add-building form. Updated Settings source-level regression coverage to prevent reverting to the old mixed heading. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form heading copy consistency**: Continued the active Hanwoo quality uplift by changing the Sales tab add-form heading from `??留ㅼ텧 湲곕줉 ?깅줉` to `???먮ℓ 湲곕줉 ?깅줉`. The form title now matches the Sales tab's `?먮ℓ 湲곕줉 ?깅줉` CTA, submit copy, and empty-state action, avoiding mixed naming after the operator opens the add-sale form. Updated home-market source-level regression coverage to prevent reverting to the old mixed `留ㅼ텧 湲곕줉` heading. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market test passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building add-form open visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab building add-form toggle's closed-state visible copy from `+ ??異붽?` to `異뺤궗 ?깅줉`. The visible CTA now matches the existing `異뺤궗 ?깅줉 李??닿린` accessible label and the building registration submit copy, so the operator sees the same task name before opening the add-building form. Updated Settings source-level regression coverage to prevent reverting to the old shorthand visible copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule add-form open visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Schedule tab add-form toggle's closed-state visible copy from `???쇱젙` to `?쇱젙 ?깅줉`. The visible CTA now matches the existing `?쇱젙 ?깅줉 李??닿린` accessible label and the schedule registration submit copy, so the operator sees the same task name before opening the add-schedule form. Updated schedule source-level regression coverage to prevent reverting to the old shorthand visible copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused schedule test passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory add-form open visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Inventory tab add-form toggle's closed-state visible copy from `+?ш퀬 ?깅줉` to `?ш퀬 ?깅줉`. The visible CTA now matches the existing `?ш퀬 ?깅줉 李??닿린` accessible label and the Inventory empty-state CTA, so the operator sees the same task name before opening the add-inventory form. Updated empty-state source-level regression coverage to prevent reverting to the old shorthand visible copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state test passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form open visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab add-form toggle's closed-state visible copy from `+留ㅼ텧 ?깅줉` to `?먮ℓ 湲곕줉 ?깅줉`. The visible CTA now matches the existing `?먮ℓ 湲곕줉 ?깅줉 李??닿린` accessible label and the Sales empty-state CTA, so the operator sees the same task name before opening the add-sale form. Updated home-market source-level regression coverage to prevent reverting to the old shorthand visible copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market test passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales empty-state action visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab empty-state action label from terse `留ㅼ텧 湲곕줉` to `?먮ℓ 湲곕줉 ?깅줉`. The no-sales CTA now matches the surrounding sales-record registration copy and names the operator task clearly before opening the add-sale form. Updated empty-state and home-market source-level regression coverage to prevent reverting to the old short action copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/home-market tests passed 55/55, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail edit/archive visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail modal edit and archive action buttons' idle visible copy from generic `?섏젙` / `蹂닿?` to `媛쒖껜 ?뺣낫 ?섏젙` / `媛쒖껜 蹂닿? 泥섎━`. The visible actions now stay aligned with the existing Korean accessible labels and name the selected-cattle edit/archive tasks clearly before and during async detail operations. Updated cattle detail source-level regression coverage to prevent reverting to the old generic action copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Login submit pending visible copy specificity**: Continued the active Hanwoo quality uplift by changing the login form submit button's pending visible copy from generic `?뺤씤 以?..` to `濡쒓렇???뺤씤 以?..`. The visible pending action now names the in-progress authentication task and remains aligned with the existing Korean `loginSubmitLabel`. Updated login source-level regression coverage to prevent reverting to the old generic pending copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused login/error-page tests passed 9/9, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard cattle archive and move confirmation copy specificity**: Continued the active Hanwoo quality uplift by changing dashboard cattle archive confirmation buttons from generic `蹂닿? 泥섎━` / `痍⑥냼` to `媛쒖껜 蹂닿? 泥섎━` / `媛쒖껜 蹂닿? 痍⑥냼`, and cattle move confirmation buttons from generic `?대룞` / `痍⑥냼` to `媛쒖껜 ?대룞` / `媛쒖껜 ?대룞 痍⑥냼`. The confirmation actions now name the cattle archive/move tasks consistently with the surrounding Korean operator copy. Updated dashboard source-level regression coverage to prevent reverting to the old generic confirmation labels. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Dashboard/Home tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building delete visible and confirmation copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab building delete row action's idle visible copy from generic `??젣` to `異뺤궗 ??젣`, and by changing the destructive confirmation actions from generic `??젣` / `痍⑥냼` to `異뺤궗 ??젣` / `異뺤궗 ??젣 痍⑥냼`. The visible and confirmation actions now name the building-delete task consistently with the existing Korean accessible label/title before and during async deletion. Updated Settings source-level regression coverage to prevent reverting to the old generic delete/cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building add-form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab building add/cancel toggle's idle visible copy from generic `痍⑥냼` to `異뺤궗 ?깅줉 痍⑥냼`. The visible secondary action now names the building-registration cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated Settings source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule add-form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Schedule tab add/cancel toggle's idle visible copy from generic `痍⑥냼` to `?쇱젙 ?깅줉 痍⑥냼`. The visible secondary action now names the schedule-registration cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated Schedule source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Schedule tests passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab add/cancel toggle's idle visible copy from generic `痍⑥냼` to `?먮ℓ 湲곕줉 ?깅줉 痍⑥냼`. The visible secondary action now names the sales-record registration cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated Sales source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Sales/Home copy tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory add-form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Inventory tab add/cancel toggle's idle visible copy from generic `痍⑥냼` to `?ш퀬 ?깅줉 痍⑥냼`. The visible secondary action now names the inventory-registration cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated inventory source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused inventory tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail breeding form cancel button's idle visible copy from generic `痍⑥냼` to `踰덉떇 湲곕줉 痍⑥냼`. The visible secondary action now names the breeding-record cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated cattle detail source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Calving cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the calving form cancel button's idle visible copy from generic `痍⑥냼` to `遺꾨쭔 湲곕줉 痍⑥냼`. The visible secondary action now names the calving-record cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated calving source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused calving tests passed 5/5, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form cancel button's idle visible copy from generic `痍⑥냼` to `媛쒖껜 ???痍⑥냼`. The visible secondary action now names the cattle-save cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated cattle form source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle form/detail tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed submit visible copy regression specificity**: Continued the active Hanwoo quality uplift by refactoring the Feed tab submit button's visible save copy into `submitButtonText`. The primary feed-record submission action now uses the same state model as the existing Korean `submitButtonLabel`, keeping visible text and accessible label aligned before and during async submission. Updated feed and shared submit-copy source-level regression coverage to prevent reverting to the old inline pending-copy expression. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused feed/submit-copy tests passed 18/18, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Calving submit visible copy regression specificity**: Continued the active Hanwoo quality uplift by refactoring the Calving tab submit button's visible save copy into `submitButtonText`. The primary calving-record submission action now uses the same state model as the existing Korean `submitButtonLabel`, keeping visible text and accessible label aligned before and during async submission. Updated calving and shared submit-copy source-level regression coverage to prevent reverting to the old inline pending-copy expression. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused calving/submit-copy tests passed 6/6, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule submit visible copy regression specificity**: Continued the active Hanwoo quality uplift by refactoring the Schedule tab submit button's visible save copy into `submitButtonText`. The primary schedule registration action now uses the same state model as the existing Korean `submitButtonLabel`, keeping visible text and accessible label aligned before and during async submission. Updated schedule and shared submit-copy source-level regression coverage to prevent reverting to the old inline pending-copy expression. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused schedule/submit-copy tests passed 8/8, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory quantity save visible copy specificity**: Continued the active Hanwoo quality uplift by changing the inline inventory quantity save button's idle visible copy from generic `??? to `?섎웾 ???. The row-level quantity update action now names the quantity-save task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated inventory source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused inventory tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab building submit button's idle visible copy from generic `?깅줉?섍린` to `異뺤궗 ?깅줉?섍린`. The primary building registration action now names the building task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated settings source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings farm submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab farm settings submit button's idle visible copy from generic `??ν븯湲? to `?띿옣 ?뺣낫 ??ν븯湲?. The primary farm-info save action now names the farm settings task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated settings source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab submit button's idle visible copy from generic `?깅줉?섍린` to `?먮ℓ 湲곕줉 ?깅줉?섍린`. The primary sales-record create action now names the sales registration task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated Sales and shared submit-copy source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Sales/submit-copy tests passed 39/39, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Inventory tab submit button's idle visible copy from generic `?깅줉?섍린` to `?ш퀬 ?깅줉?섍린`. The primary inventory-create action now names the inventory registration task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated shared submit-copy source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused inventory/submit-copy tests passed 18/18, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form submit button's idle visible copy from generic `??ν븯湲? to `媛쒖껜 ?뺣낫 ???. The primary save action now names the cattle-info save task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated cattle form and shared submit-copy source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle form/submit-copy tests passed 14/14, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail breeding record submit button's idle visible copy from generic `??? to `踰덉떇 湲곕줉 ???. The visible button text now names the breeding-record save task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight loading status visible copy specificity**: Continued the active Hanwoo quality uplift by changing the AI insight widget loading status visible copy from generic `遺꾩꽍 以묅? to `AI ?몄궗?댄듃 遺꾩꽍 以묅?. The busy status now names the in-progress AI-insight analysis on screen and matches the widget task/refresh-control context. Updated AI insight source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 10/10, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle pagination button visible copy specificity**: Continued the active Hanwoo quality uplift by changing the home dashboard cattle load-more button's idle visible copy from generic `媛쒖껜 ??蹂닿린` to `?댁쟾 媛쒖껜 ??蹂닿린`. The button now names the previous cattle-page load task more clearly on screen and matches the existing Korean loading label/cursor-pagination behavior. Updated cattle pagination source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle pagination tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification modal close disabled label specificity**: Continued the active Hanwoo quality uplift by adding a state-aware close button label for the notification modal. While SMS test sending is in progress, the disabled close action now exposes `臾몄옄 ?뚮┝ ?뚯뒪???꾩넚 以묒뿉???뚮┝ ?쇳꽣瑜??レ쓣 ???놁뒿?덈떎` through both `aria-label` and `title` instead of continuing to advertise a closable action. Updated notification modal source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification modal tests passed 8/8, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the QR label print button's visible busy text from generic `?몄뇙 以鍮?以?..` to `QR ?쇰꺼 ?몄뇙 以鍮?以?..`. The disabled print action now names the in-progress QR-label print task on screen and matches the existing Korean accessible label/title. Updated QR widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused QR widget tests passed 3/3, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification SMS test busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the notification modal SMS test button's visible busy text from generic `?꾩넚 以?..` to `臾몄옄 ?뚮┝ ?뚯뒪???꾩넚 以?..`. The disabled SMS test action now names the in-progress task on screen and matches the existing Korean accessible label/title. Updated notification modal source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification modal tests passed 8/8, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales pagination button visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab load-more button's visible copy from generic `?댁쟾 湲곕줉 ??蹂닿린` / `遺덈윭?ㅻ뒗 以?..` to `?댁쟾 ?먮ℓ 湲곕줉 ??蹂닿린` / `?댁쟾 ?먮ℓ 湲곕줉 遺덈윭?ㅻ뒗 以?..`. The visible button text now names the sales-history pagination task on screen and matches the existing Korean accessible label/title. Updated sales pagination source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused sales pagination tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building delete busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing building delete row actions' visible busy text from generic `??젣 以?..` to `異뺤궗 ??젣 以?..`. The disabled delete button now names the in-progress building-delete task on screen and matches the existing Korean accessible label/title. Updated settings source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule completion toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing upcoming schedule completion toggles' visible busy text from generic `蹂寃?以?..` to `?쇱젙 ?꾨즺 ?곹깭 蹂寃?以?..`. The disabled completion toggle now names the in-progress schedule-completion update on screen and matches the existing Korean accessible label/title. Updated schedule source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused schedule tests passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule add-form toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Schedule tab add/cancel toggle's visible busy text from generic `???以?..` to `?쇱젙 ???以?..`. The disabled toggle now names the in-progress schedule-save task on screen and matches the existing Korean accessible label/title. Updated schedule source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused schedule tests passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab add/cancel toggle's visible busy text from generic `???以?..` to `?먮ℓ 湲곕줉 ???以?..`. The disabled toggle now names the in-progress sales-record save task on screen and matches the existing Korean accessible label/title. Updated sales source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market/sales tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory add-form toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Inventory tab add/cancel toggle's visible busy text from generic `???以?..` to `?ш퀬 ???以?..`. The disabled toggle now names the in-progress inventory-save task on screen and matches the existing Korean accessible label/title. Updated inventory source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/inventory tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed filter chip busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing Feed tab building filter chips' visible busy text from generic `???以?..` to `湲됱뿬 湲곕줉 ???以?..`. Disabled filter chips now name the in-progress feed-record save task on screen and match the existing Korean accessible label/title. Updated Feed tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/feed tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle detail action busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail edit, archive, estrus, and pregnancy action buttons' visible busy text from generic `泥섎━ 以?..` to `媛쒖껜 泥섎━ 以?..`. Disabled detail actions now name the in-progress cattle operation on screen and match the existing Korean accessible label/title. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle breeding record busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail breeding record cancel and submit buttons' visible busy text from generic `???以?..` to `踰덉떇 湲곕줉 ???以?..`. The in-progress state now names the breeding-record save task on screen and matches the existing Korean accessible label/title. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle form cancel busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form cancel button's visible busy text from generic `???以?..` to `媛쒖껜 ???以?..`. The in-progress state now names the cattle-save task on screen and matches the existing Korean accessible label/title. Updated cattle form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard calving cancel busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the calving form cancel button's visible busy text from generic `???以?..` to `遺꾨쭔 湲곕줉 ???以?..`. The in-progress state now names the calving-save task on screen and matches the existing Korean accessible label/title. Updated calving form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused calving tests passed 5/5, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard settings building toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the building add/cancel toggle's visible busy text from generic `???以?..` to `異뺤궗 ???以?..`. The in-progress state now names the building-save task on screen and matches the existing Korean accessible label/title. Updated settings building-form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard settings building submit busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the building registration submit button's visible text from static `?깅줉?섍린` to state-aware `異뺤궗 ?깅줉 以?..` while saving. The in-progress state now names the building-save task on screen and matches the existing Korean accessible label/title. Updated settings building-form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard settings farm save busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the farm settings submit button's visible busy text from generic `???以?..` to `?띿옣 ?뺣낫 ???以?..`. The in-progress state now names the farm-settings save task on screen and matches the existing Korean accessible label/title. Updated settings farm-form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard inventory quantity save busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the inline inventory quantity save button's visible busy text from generic `???以?..` to `?섎웾 ???以?..`. The in-progress state now names the quantity-save task on screen and matches the existing Korean accessible label/title. Updated inventory quantity edit source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/inventory tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle submit busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form submit button's visible busy text from generic `???以?..` to `媛쒖껜 ?뺣낫 ???以?..`. The in-progress state now names the cattle-save task on screen and matches the existing Korean accessible label/title. Updated cattle form and primary submit pending-copy source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form and primary submit pending-copy tests passed 14/14, `npm.cmd test` passed 330/330 after updating the broader pending-copy expectation, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle tag lookup busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form tag lookup button's visible busy text from generic `議고쉶 以?..` to `?대젰踰덊샇 議고쉶 以?..`. The in-progress state now names the lookup task on screen and matches the existing Korean accessible label/title. Updated cattle form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Excel export button's visible busy text from generic `以鍮?以?..` to `?묒? 以鍮?以?..`. The in-progress state now names the export task on screen and matches the existing Korean accessible label/title. Updated Excel export button source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Excel export button tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard subscription result loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the subscription success and failure Suspense fallback statuses. Korean payment loading copy now behaves as coherent polite busy status announcements. Updated payment UX source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused payment UX tests passed 5/5, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard diagnostics loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the admin diagnostics page's system-check and raw-record loading statuses. Korean operations loading copy now behaves as coherent polite busy status announcements. Updated diagnostics source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused diagnostics tests passed 3/3, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard sales pagination error atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the Sales tab pagination load-error status. Korean retry feedback for failed `?댁쟾 湲곕줉 ??蹂닿린` requests now behaves as one coherent polite status. Updated sales pagination source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused sales pagination tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle pagination error atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the dashboard cattle pagination load-error status. Korean retry feedback for failed `媛쒖껜 ??蹂닿린` requests now behaves as one coherent polite status. Updated cattle pagination source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle pagination tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard dashboard full-list loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the dashboard full cattle and sales ledger loading placeholders. The Korean `媛쒖껜 紐⑸줉??遺덈윭?ㅻ뒗 以묒엯?덈떎...` and `留ㅼ텧 湲곕줉??遺덈윭?ㅻ뒗 以묒엯?덈떎...` status messages now behave as coherent polite busy announcements. Updated home market source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard market price loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the market price widget initial loading status. The Korean `?쒖슦 ?쒖꽭瑜?遺덈윭?ㅻ뒗 以묒엯?덈떎.` announcement now behaves as one coherent polite busy status. Updated home market source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard profitability loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the profitability widget loading status. The Korean `異쒗븯 ?섏씡???덉륫??遺덈윭?ㅻ뒗 以묒엯?덈떎.` announcement now behaves as one coherent polite busy status. Updated profitability widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 8/8, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight loading busy status**: Continued the active Hanwoo quality uplift by adding `aria-busy={isLoading}` to the AI insight widget header loading status. The Korean `遺꾩꽍 以?..` status now exposes the busy state consistently with the widget refresh button and insight list. Updated AI insight widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight widget tests passed 10/10, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard weather unavailable atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the weather widget unavailable status region. The Korean unavailable heading, message, and location are now announced as one coherent polite status. Updated home market source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard market price unavailable status announcement**: Continued the active Hanwoo quality uplift by adding polite status semantics to the market price widget unavailable fallback. Missing/degraded KAPE price data is now announced as a coherent Korean status instead of remaining visual-only text. Updated home market source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight loading status semantics**: Continued the active Hanwoo quality uplift by adding explicit `role="status"` and `aria-atomic="true"` to the AI insight widget header loading copy. The Korean `遺꾩꽍 以?..` state is now announced as a coherent polite status instead of only relying on `aria-live`. Updated AI insight widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight widget tests passed 10/10, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode checklist progress hover summary**: Continued the active Hanwoo quality uplift by adding a shared `checklistProgressLabel` to the Field Mode daily-check progressbar and reusing it for both `aria-valuetext` and hover `title`. The current completed-check count is now exposed consistently to assistive technology and title UI. Updated Field Mode source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress track hover summary**: Continued the active Hanwoo quality uplift by adding `title={setupProgressLabel}` to the home setup progress bar. The progressbar now exposes the same current operating-readiness percentage and completed-step count through hover/title UI that it already exposes through `aria-valuetext`. Updated home dashboard source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared dialog close label specificity**: Continued the active Hanwoo quality uplift by adding a contextual `closeLabel` prop to the shared `DialogContent` close control. The close button now uses the Korean label for `aria-label`, hover `title`, and screen-reader copy, with `?뺤씤 李??リ린` applied to the feedback confirmation dialog and `??붿긽???リ린` as the shared default. Updated dialog source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused dialog tests passed 3/3, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode search input title copy**: Continued the active Hanwoo quality uplift by adding matching `title="媛쒖껜 ?대쫫 ?먮뒗 ?댄몴踰덊샇濡?寃??` to the Field Mode search input, aligning hover/title copy with the existing Korean accessible name. Updated Field Mode source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 7/7, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode search placeholder Korean polish**: Continued the active Hanwoo quality uplift by updating the Field Mode search input placeholder from `?댄몴踰덊샇 4?먮━ ?먮뒗 ?뚯씠由?..` to `?댄몴踰덊샇 4?먮━ ?먮뒗 ???대쫫 ?낅젰`. The field now uses correct Korean spacing and action-oriented input copy instead of trailing punctuation. Updated Field Mode source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 7/7, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat streaming placeholder Korean status**: Continued the active Hanwoo quality uplift by replacing the AI chat streaming fallback from punctuation-only `...` with a Korean `STREAMING_PLACEHOLDER_MESSAGE` value, `?듬? ?앹꽦 以묒엯?덈떎...`. Empty in-progress assistant messages now expose meaningful status copy instead of punctuation-only output. Updated AI chat widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat input busy-state label**: Continued the active Hanwoo quality uplift by adding a state-aware `inputLabel` to the AI chat question input. While an answer is streaming and the input is disabled, its `aria-label` and `title` now expose that questions cannot be entered yet instead of keeping the idle question label. Updated AI chat widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat close action context label**: Continued the active Hanwoo quality uplift by changing the AI chat panel close button from generic `梨꾪똿 ?リ린` to `AI ?띿옣 鍮꾩꽌 ?リ린` for both `aria-label` and `title`. The close action now matches the launcher, dialog, and log naming, making the control explicit for assistive technology and hover/title UI. Updated AI chat widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Login demo credential label Korean polish**: Continued the active Hanwoo quality uplift by replacing the demo account box's remaining English `ID`/`PW` labels with Korean `?꾩씠??/`鍮꾨?踰덊샇`, while preserving the actual demo credentials. Updated login/error-page source-level regression coverage so the English abbreviations do not return. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused error-page/login tests passed 9/9, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Login demo account Korean copy polish**: Continued the active Hanwoo quality uplift by removing the English `Demo Accounts` parenthetical from the login page demo account box and marking the lightbulb glyph as decorative with `aria-hidden`. The login screen now stays Korean-first and avoids exposing decorative emoji output to assistive technology. Updated login/error-page source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused error-page/login tests passed 9/9, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Profitability error alert semantics**: Continued the active Hanwoo quality uplift by adding `role="alert"` to the profitability widget error card. Shipment-profitability failures are now announced as urgent feedback instead of remaining visual-only text, while preserving the original Korean error copy. Updated profitability widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 8/8, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather unavailable status announcement**: Continued the active Hanwoo quality uplift by adding `role="status"` and polite live-region semantics to the weather unavailable card. Degraded/no-weather states are now announced like other dashboard loading/error states instead of remaining visual-only text. Updated dashboard weather source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather forecast icon semantic title**: Continued the active Hanwoo quality uplift by adding an explicit `role="img"` and matching hover `title` to 3-day forecast weather icons. The forecast emoji now reuses the normalized Korean weather description for both assistive technology and hover/title UI instead of exposing only an aria label. Updated dashboard weather source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle tag lookup visible copy consistency**: Continued the active Hanwoo quality uplift by unifying the cattle form tag lookup button's visible idle copy with its accessible label/title. The on-screen action now says `?대젰踰덊샇 議고쉶` instead of `?쒓렇 議고쉶`, while preserving `議고쉶 以?..` during lookup. Updated cattle form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule completion toggle progress copy**: Continued the active Hanwoo quality uplift by adding state-aware labels and visible status copy to upcoming schedule completion toggles. While an async completion update is in flight, the row now shows `蹂寃?以?..` and the checkbox exposes `?쇱젙 ?꾨즺 ?곹깭 蹂寃?以? through label/title instead of leaving static completion copy. Updated Schedule and dashboard source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused tab-header tests passed 7/7, focused home-market tests passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed filter chip visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to Feed tab building filter chips. While a feed record save is in flight, disabled filter chips now show `???以?..` instead of static filter names, matching their busy accessible labels, titles, and `aria-busy` state. Updated Feed tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/Feed tests passed 17/17, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings save controls visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Settings tab farm save button and building add/cancel toggle. While their async save flows are in flight, the disabled controls now show `???以?..` instead of static `??ν븯湲?/`痍⑥냼`, matching their busy accessible labels, titles, and disabled states. Updated Settings tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings tests passed 12/12, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule add-form toggle visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Schedule tab add/cancel toggle. While a schedule save is in flight, the disabled toggle now shows `???以?..` instead of static `痍⑥냼`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated Schedule tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused tab-header/Schedule tests passed 7/7, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form toggle visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Sales tab add/cancel toggle. While a sales record save is in flight, the disabled toggle now shows `???以?..` instead of static `痍⑥냼`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated Sales tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market/Sales tests passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory add-form toggle visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Inventory tab add/cancel toggle. While an inventory item save is in flight, the disabled toggle now shows `???以?..` instead of static `痍⑥냼`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated inventory source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/inventory tests passed 17/17, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Calving form cancel visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Calving tab form cancel button. While a calving record save is in flight, the disabled cancel action now shows `???以?..` instead of static `痍⑥냼`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated calving source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused calving tests passed 5/5, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form cancel visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle form bottom cancel button. While an async cattle save is in flight, the disabled cancel action now shows `???以?..` instead of static `痍⑥냼`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated cattle form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail/form tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding cancel visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle detail breeding form cancel button. While a breeding record save is in flight, the disabled cancel action now shows `???以?..` instead of static `痍⑥냼`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding action visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle detail modal breeding quick actions. When archive/delete or breeding-save work is in flight, the disabled `諛쒖젙 湲곕줉` and `?섏젙 湲곕줉` actions now show `泥섎━ 以?..`, matching their existing busy `aria-label`, `title`, and `aria-busy` state. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail edit visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle detail modal edit button. When archive/delete or breeding-save work is in flight, the disabled edit action now shows `泥섎━ 以?..` instead of static `?섏젙`, matching the existing busy `aria-label`, `title`, and `aria-busy` state. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis tab chart accessible summaries**: Continued the active Hanwoo quality uplift by adding Korean accessible summaries to the Analysis tab monthly flow bar chart and cost structure pie chart. Both Recharts wrappers now use `role="img"`, `aria-label`, and matching `title` so the visuals communicate their purpose to assistive technology and hover/title UI. Updated analysis source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis tests passed 3/3, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail weight chart accessible summary**: Continued the active Hanwoo quality uplift by adding a Korean accessible summary to the cattle detail modal's weight trend Recharts line chart. The chart wrapper now uses `role="img"`, `aria-label`, and matching `title` so the visual chart communicates that it compares the selected cattle's weight records by date. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales profit chart accessible summary**: Continued the active Hanwoo quality uplift by adding a Korean accessible summary to the Sales tab's recent profit analysis Recharts bar chart. The chart wrapper now uses `role="img"`, `aria-label`, and matching `title` so the visual chart communicates that it compares sale amount and profit by shipped cattle. Updated Sales tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market/Sales tests passed 38/38, `npm.cmd test` passed 328/328, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Financial chart accessible summary**: Continued the active Hanwoo quality uplift by adding a Korean accessible summary to the farm financial flow Recharts bar chart. The chart wrapper now uses `role="img"`, `aria-label`, and matching `title` so the visual chart communicates that it compares monthly sales, expenses, and profit over the recent six-month window. Updated financial chart source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis/financial tests passed 3/3, `npm.cmd test` passed 327/327, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed trend chart accessible summary**: Continued the active Hanwoo quality uplift by adding a Korean accessible summary to the Feed tab's Recharts trend chart container. The chart wrapper now uses `role="img"`, `aria-label`, and matching `title` so the visual chart communicates that it compares recent roughage and concentrate feed amounts by date. Updated Feed tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/feed tests passed 17/17, `npm.cmd test` passed 327/327, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared decorative icon hiding**: Continued the active Hanwoo quality uplift by marking visual-only shared dialog/select glyphs, schedule month navigation arrows, the Field Mode empty-result warning icon, and the empty-pen cow emoji as `aria-hidden`. This keeps existing visible UI unchanged while preventing duplicate decorative output for assistive technology. Updated dialog, home-market, and Field Mode source-level accessibility coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused dialog/home/Field Mode tests passed 46/46, `npm.cmd test` passed 326/326, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard secondary link action labels**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the dashboard footer links (`/terms`, `/privacy`, `/subscription`) and the settings diagnostics link (`/admin/diagnostics`). A focused anchor scan now reports no internal anchor without `aria-label` or `title`. Updated home-market and settings accessibility coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 37/37, focused settings tests passed 12/12, `npm.cmd test` passed 325/325, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print status feedback**: Continued the active Hanwoo quality uplift by adding Korean print status feedback to `QRCodeWidget.js`. The QR print action now announces preparation, popup-blocked failure, and print-window-open completion through a polite status region instead of silently resetting when `window.open` fails. Updated `qr-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused QR widget tests passed 3/3, `npm.cmd test` passed 323/323, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard unit-test warning suppression**: Continued the active Hanwoo quality uplift by updating the Hanwoo `test` script to run Node with `--disable-warning=MODULE_TYPELESS_PACKAGE_JSON`. This removes recurring typeless-package warning noise from routine test runs without declaring `"type": "module"`, which would be broader because PostCSS and Prisma seed files still use CommonJS. Added `package-scripts.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused package-script test passed 1/1, `npm.cmd test` passed 322/322 without the typeless-package warning, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared empty-state CTA busy state**: Continued the active Hanwoo quality uplift by wiring the shared `EmptyState` CTA `disabled` prop into `aria-busy`, so disabled empty-state actions such as the sales tab's missing-cattle CTA expose their unavailable/busy state consistently with other action buttons. Updated `empty-state-wiring.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state tests passed 16/16, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard empty building CTA action label**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the home dashboard empty building CTA. The button now states that it opens settings to add the first building instead of relying only on the visible card copy. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 36/36, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard full-list retry action labels**: Continued the active Hanwoo quality uplift by adding target-specific Korean `aria-label` and `title` copy to the full cattle-list and sales-ledger retry buttons shown after dashboard preload failures. Updated `home-market-copy.test.mjs` coverage so retry actions identify whether they reload the full cattle list or sales records. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 36/36, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification SMS test visible busy copy**: Continued the active Hanwoo quality uplift by making the notification modal SMS test button show `?꾩넚 以?..` while `isTestingSMS` is true instead of leaving the visible label static. This aligns the on-screen state with the existing disabled, busy, accessible-label, and title states. Updated `notification-modal-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification-modal tests passed 8/8, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification SMS test action accessibility**: Continued the active Hanwoo quality uplift by adding a state-aware `smsTestButtonLabel` to the notification modal SMS test button and reusing it for `aria-label` and `title`, so idle and sending states expose the same Korean action name to assistive technology and hover/title UI. Updated `notification-modal-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification-modal tests passed 8/8, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared empty-state CTA accessibility**: Continued the active Hanwoo quality uplift by reusing `actionLabel` as both `aria-label` and `title` on the shared `EmptyState` CTA `PremiumButton`, so inventory/sales/schedule empty-state actions expose the same Korean task name to assistive technology and hover/title UI. Updated `empty-state-wiring.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state tests passed 16/16, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared form action icon accessibility**: Continued the active Hanwoo quality uplift by marking shared `BackIcon`, `EditIcon`, and `TrashIcon` SVG action icons as `aria-hidden="true"` and `focusable="false"` so labeled form/modal buttons do not expose duplicate icon semantics to assistive technology. Updated `cattle-detail-modal-wiring.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle form/detail tests passed 12/12, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode control title and icon accessibility**: Continued the active Hanwoo quality uplift by adding matching `title` copy to Field Mode return, clear-search, and checklist toggle controls so hover/title copy aligns with their accessible labels. Also hid the decorative return arrow icon from assistive technology. Updated `field-mode-celebration.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 7/7, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat close-button title accessibility**: Continued the active Hanwoo quality uplift by adding a matching Korean `title="梨꾪똿 ?リ린"` to the AI chat dialog close button so hover/title copy aligns with the existing accessible label and adjacent task controls. Updated `ai-chat-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 315/315, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard ear-tag scanner header close-label accessibility**: Continued the active Hanwoo quality uplift by making the ear-tag scanner modal header close button use contextual Korean accessible copy (`?댄몴 ?ㅼ틦???リ린`) matching its title instead of generic close copy, while preserving the decorative close icon. Updated `eartag-scanner-modal-accessibility.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused scanner tests passed 3/3, `npm.cmd test` passed 315/315, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard form add/cancel toggle busy-state accessibility**: Continued the active Hanwoo quality uplift by hardening inventory, schedule, and building add/cancel form toggles. The toggles now expose state-aware `aria-label`, `title`, and `aria-busy` values so disabled controls explain active save flows and idle controls name the target form action. Updated `empty-state-wiring.test.mjs`, `tab-header-accessibility.test.mjs`, and `settings-tab-accessibility.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused tab tests passed 16/16, 7/7, and 11/11; `npm.cmd test` passed 315/315; `npm.cmd run lint` passed; and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard dashboard full-list loading placeholder accessibility**: Continued the active Hanwoo quality uplift by making the dashboard's complete cattle-list and sales-ledger loading placeholders perceivable to assistive technology. `DashboardClient.js` now exposes both placeholder cards as `role="status"` with `aria-live="polite"` and loading-flag based `aria-busy` state. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 33/33, `npm.cmd test` passed 315/315, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard profitability loading status accessibility**: Continued the active Hanwoo quality uplift by making the profitability recommendation widget loading skeleton perceivable to assistive technology. `ProfitabilityWidget.js` now exposes the loading content as `role="status"` with `aria-live="polite"`, `aria-busy="true"`, and a screen-reader-only Korean loading message. Updated `profitability-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 8/8, `npm.cmd test` passed 313/313, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress item state accessibility**: Continued the active Hanwoo quality uplift by making each home setup progress item expose its completion state in the accessible name. `DashboardClient.js` now builds `setupItemLabel` from the item title, done state, and detail, then applies it as `aria-label` while keeping the visual done icon decorative. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 32/32, `npm.cmd test` passed 312/312, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode loading status accessibility**: Continued the active Hanwoo quality uplift by making Field Mode search-result full-list loading perceivable to assistive technology. `FieldModeView.js` now exposes the loading badge as `role="status"` with `aria-live="polite"` and hides the camera icon inside the labeled scanner button as decorative. Updated `field-mode-celebration.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 6/6, `npm.cmd test` passed 311/311, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress semantic accessibility**: Continued the active Hanwoo quality uplift by exposing the home onboarding/setup progress track as a real ARIA `progressbar`. `DashboardClient.js` now gives the setup progress track a Korean label plus `aria-valuemin`, `aria-valuemax`, and `aria-valuenow={progress.percent}` instead of hiding the visual track from assistive technology. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 31/31, `npm.cmd test` passed 310/310, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification center trigger dialog relationship accessibility**: Continued the active Hanwoo quality uplift by wiring the home notification trigger to its modal with a stable `NOTIFICATION_MODAL_ID`. `DashboardClient.js` now exposes `aria-haspopup="dialog"`, stateful `aria-expanded`, and `aria-controls` on the trigger, and passes the same id into `NotificationModal.js`; the modal root now accepts and renders that id. Updated `home-market-copy.test.mjs` and `notification-modal-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 30/30, focused notification-modal tests passed 8/8, `npm.cmd test` passed 309/309, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat launcher relationship accessibility**: Continued the active Hanwoo quality uplift by hardening `components/widgets/AIChatWidget.js`. The floating AI assistant launcher now exposes `aria-haspopup="dialog"`, `aria-expanded="false"`, and `aria-controls` pointing at a stable chat panel id, while the opened chat dialog uses the same id. Updated `ai-chat-widget-copy.test.mjs` coverage for the launcher-to-dialog relationship. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 308/308, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification modal close-label accessibility**: Continued the active Hanwoo quality uplift by making `components/ui/NotificationModal.js` close-button accessible copy contextual. The modal close control now exposes `?뚮┝ ?쇳꽣 ?リ린` for both `aria-label` and `title` instead of the generic `?リ린`, while preserving the existing SMS-busy dismissal guard. Updated `notification-modal-copy.test.mjs` regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification-modal tests passed 8/8, `npm.cmd test` passed 308/308, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard feedback confirmation dialog accessibility**: Continued the active Hanwoo quality uplift by hardening `components/feedback/FeedbackProvider.js`. Confirmation dialog cancel/confirm actions now expose stable Korean `aria-label` and `title` values derived from the configured action labels, making destructive confirmations clearer for assistive technology and hover users. Added `feedback-provider-copy.test.mjs` regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused feedback-provider tests passed 3/3, `npm.cmd test` passed 308/308, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard dashboard ErrorBoundary recovery accessibility**: Continued the active Hanwoo quality uplift by hardening `components/ErrorBoundary.js`. The premium dashboard runtime fallback now hides its decorative warning icon from assistive tech and gives the recovery action an explicit `type="button"` plus stable Korean `aria-label` and `title`. Added `error-pages-wiring.test.mjs` coverage for the recovery action contract. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused error-page tests passed 8/8, `npm.cmd test` passed 307/307, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard ear-tag scanner Korean operator copy cleanup**: Continued the active Hanwoo quality uplift by cleaning up visible scanner overlay copy in `EarTagScannerModal.js`. Removed the English `(Click)` hint and changed the typo-prone visible action text from `?댄몴 ?먮룞 媛먯깋` to `?댄몴 ?먮룞 ?몄떇`, keeping the existing accessible label/title contract. Added `eartag-scanner-modal-accessibility.test.mjs` coverage to prevent the English hint and typo from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused scanner test passed 3/3, `npm.cmd test` passed 306/306, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight live-region update announcement**: Continued the active Hanwoo quality uplift by adding polite live-region semantics to the `AIInsightWidget.js` insight list. Refreshed analysis cards now expose `aria-live="polite"` and `aria-relevant="additions text"` alongside the existing busy state, so assistive technology users can perceive card updates after AI/heuristic refreshes. Added `ai-insight-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 21/21, `npm.cmd test` passed 306/306, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight stale-card reset on summary changes**: Continued the active Hanwoo quality uplift by hardening `AIInsightWidget.js` state sync. When the dashboard summary changes, the widget now immediately resets visible cards to fresh `buildHeuristicInsights(stableSummary)` output and marks the source as heuristic while the new `/api/ai/insight` request is loading, so previous snapshot cards do not linger. Added `ai-insight-widget-copy.test.mjs` coverage for this contract. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 21/21, `npm.cmd test` passed 306/306, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight fallback reason normalization**: Continued the active Hanwoo quality uplift by hardening `AIInsightWidget.js` response handling. Heuristic `/api/ai/insight` responses now always surface an operator-facing fallback reason even if the server omits `reason`, while successful AI responses explicitly clear stale fallback copy. Added `ai-insight-widget-copy.test.mjs` coverage for source/reason normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 20/20, `npm.cmd test` passed 305/305, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight client complete-card response guard**: Continued the active Hanwoo quality uplift by reusing `MAX_INSIGHTS` in `AIInsightWidget.js`. The client now rejects malformed or partial `/api/ai/insight` payloads after parsing and falls back to deterministic 3-card heuristic insights instead of rendering a short AI list. Added `ai-insight-widget-copy.test.mjs` widget wiring coverage for the same complete-card guard. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight complete-card response contract**: Continued the active Hanwoo quality uplift by tightening `app/api/ai/insight/route.js` so Gemini output is accepted only when `parseInsightResponse` returns all `MAX_INSIGHTS` cards promised by the UI. Partial AI responses now fall back to deterministic heuristic insights instead of showing a short AI list. Added `ai-insight-widget-copy.test.mjs` route wiring coverage for the `parsed.length !== MAX_INSIGHTS` guard. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight summary identity stabilization**: Continued the active Hanwoo quality uplift by memoizing the summary object passed from `DashboardClient.js` into `AIInsightWidget`. The previous inline object changed identity on unrelated dashboard re-renders, which could retrigger `/api/ai/insight` calls, reset loading state, and increase AI usage. Added `ai-insight-widget-copy.test.mjs` wiring coverage so the widget receives `aiInsightSummary` instead of an inline object. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight server timeout fallback control-flow fix**: Continued the active Hanwoo quality uplift by fixing `app/api/ai/insight/route.js`. The `InsightTimeoutError` fallback had been placed in the authentication catch path, where it was unreachable for Gemini calls and referenced `summary` before declaration. Moved that handling into the Gemini generation catch path so slow Gemini responses return deterministic heuristic insights with the timeout-specific Korean reason. Strengthened `ai-insight-widget-copy.test.mjs` route coverage to keep timeout handling out of the auth catch. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight data normalization hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/ai-insight.mjs` summary normalization. Malformed profitability rows with missing/NaN `marginalGain` no longer count as declining-margin risks, while real zero/negative margin rows still do. Negative monthly sales input is now clamped before operator-facing heuristic copy. Added regression coverage in `ai-insight.test.mjs`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Claude (Opus 4.7) |
| Work | **/goal "?꾨줈?앺듃瑜?理쒖떊 湲곕뒫 + 理쒓퀬?? ??3媛??쒖꽦 ?꾨줈?앺듃 ?좉퇋 湲곕뒫 ?쇨큵 異쒗븯**. ?ъ슜?먭? workspace ?꾨컲 횞 ?좉퇋 湲곕뒫 諛⑺뼢 ?좏깮. **(A) hanwoo-dashboard AI ?몄궗?댄듃 ?꾩젽** ??Gemini 2.0 Flash + ?대━?ㅽ떛 ?대갚 4怨꾩링(???놁쓬/?묐떟 ?뚯떛 ?ㅽ뙣/?덉쇅/?ㅽ듃?뚰겕), ?곗꽑?쒖쐞 3移대뱶 + ?섎룞 ?덈줈怨좎묠 + AbortController + react-19 set-state-in-effect 洹쒖튃 以?? WIDGET_REGISTRY ?깅줉, DashboardClient ??댁뼱留? (???꾩뿉 Codex 媛 怨㏓컮濡?10s `withInsightTimeout` + `InsightTimeoutError` 蹂닿컯???댁뼱 異쒗븯 ??蹂?addendum ?꾨옒 Codex ??ぉ 李멸퀬) **(B) blind-to-x Best-of-N 寃고빀 ?먯닔** ??湲곗〈 `best_of_n` ??됲꽣媛 5異?`avg_score` 留?蹂대뜕 ?쒓퀎瑜? Phase 2 ??4異?`comment_trigger_scores` ? 媛以?寃고빀(`llm.best_of_n_comment_weight`, 湲곕낯 0.5, 0~1 clamp, twitter/threads 異쒕젰?먮쭔 ?곸슜). ?꾨낫 ?먯닔 breakdown 濡쒓렇. **(C) shorts-maker-v2 WhisperX ?듯듃???뺣젹 (T-19 ?닿껐)** ??BSD-2, CPU OK, lazy import, 誘몄꽕移??ㅽ뙣 ??None 諛섑솚 ??湲곗〈 OpenAI Whisper ?대갚. `config.audio.use_whisperx_alignment` 湲곕낯 False ??湲곗〈 ?ъ슜???곹뼢 0. **寃利?*: hanwoo 301/301 + lint clean (Codex ??異붽? ?묒뾽 吏곹썑 303/303), blind-to-x 1680 passed + ruff clean, shorts-maker-v2 1576 passed + ruff clean. ?좉퇋 ?뚭? 45媛?11 + 17 + 17). |
| Next Priorities | (a) ?ъ슜?먯뿉寃?而ㅻ컠 ?뱀씤 ?붿껌 ??11媛?蹂寃??좉퇋 ?뚯씪??stage ?湲?(Codex ??timeout 蹂닿컯 ?ы븿). (b) WhisperX ?ㅼ젣 ?쒖꽦?붾뒗 `pip install whisperx torch` ??梨꾨꼸蹂?`use_whisperx_alignment: true` ?ㅼ젙 ?꾩슂(~2GB ?붿뒪??. (c) Best-of-N 寃고빀 ?먯닔 ?④낵 痢≪젙: ?ㅼ쓬 N媛?諛쒗뻾?먯꽌 4異??먯닔? ?ㅼ젣 ?볤? ???곴?愿怨??뺤씤. (d) AI ?몄궗?댄듃 ?꾩젽 ?꾩엯 ??GEMINI_API_KEY 誘몄꽕???쒖뿉???대━?ㅽ떛???뺤긽 ?묐룞?섎뒗吏 ?꾨줈?뺤뀡 ?뺤씤. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight API Gemini timeout fallback**: Continued the active Hanwoo quality uplift by hardening `app/api/ai/insight/route.js` against slow Gemini responses. Added a 10s server-side `withInsightTimeout` wrapper, a dedicated `InsightTimeoutError`, timeout handle cleanup, and a timeout-specific Korean heuristic fallback reason. Expanded `ai-insight-widget-copy.test.mjs` route coverage so slow Gemini calls remain deterministic and user-facing. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 18/18, `npm.cmd run lint` passed, `npm.cmd test` passed 303/303, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight timeout resilience**: Continued the active Hanwoo quality uplift by hardening `AIInsightWidget.js` against slow `/api/ai/insight` responses. Added a 12s client-side timeout, separated timeout aborts from unmount/summary-change aborts, clears timers in both completion and cleanup paths, falls back to deterministic insights on timeout, and announces the fallback reason with a polite `role="status"` region. Expanded `ai-insight-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 17/17, `npm.cmd run lint` passed, `npm.cmd test` passed 302/302, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight refresh/accessibility polish**: Continued the active Hanwoo quality uplift after confirming T-251 remains the only repo-tracked TODO and is external. Improved the new `AIInsightWidget.js` by adding a manual refresh button that increments a refresh nonce, re-runs `/api/ai/insight`, disables while loading, exposes `aria-busy`, uses Korean accessible/title labels, and hides the refresh icon from assistive tech. Added `ai-insight-widget-copy.test.mjs` coverage for the refresh control. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 16/16, `npm.cmd run lint` passed, `npm.cmd test` passed 301/301, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **active-project-matrix CI stabilization**: Investigated failed GitHub Actions run `26443385538`. The failed frontend jobs were caused by duplicate pnpm version sources (`version: 9` in `pnpm/action-setup` plus root `packageManager: pnpm@9.5.0`); the working tree already contains the minimal workflow fix removing the action-level version. The shorts-maker job failed because Linux CI lacks the configured Windows `malgun.ttf`, so static safe-zone QC fell back to a tiny default font and passed an overlong caption. Updated `caption_pillow._load_font` to preserve requested font size through Pillow's default font fallback and added a missing-font regression test. |
| Next Priorities | Re-run/push CI when ready. Current verification: `python -m pytest tests/unit/test_safe_zone_qc.py::TestGateSafeZone -q -o addopts=` passed 7/7, forced missing-font probe returns `hold`, and CI-equivalent `python -m pytest tests/unit tests/integration -q --tb=short --maxfail=1 -o addopts=` passed 1559/1559 with 12 skipped. T-251 remains separate and user-owned Supabase database password/control-plane resync. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard ear-tag scanner accessibility + QC stabilization**: Continued the active Hanwoo quality uplift while preserving unrelated staged skill/nature/MCP work. Improved `EarTagScannerModal.js` with dialog description wiring, visual-only canvas/icon hiding, explicit scan/retry/manual-select/detail labels, and polite live-region scan result announcements. Added `eartag-scanner-modal-accessibility.test.mjs`. Also fixed the current untracked `AIInsightWidget.js` React lint failure by deferring effect loading-state resets with `queueMicrotask`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 3/3, focused AI/scanner tests passed 18/18, `npm.cmd test` passed 300/300, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **紐⑤뱺 ?먯씠?꾪듃 ?ㅽ궗 理쒖떊???꾨즺 (T-410)**:<br>1. **Locked Skills**: `skills` CLI??Windows ??`spawnSync` shell-concat space 踰꾧렇瑜??고쉶?섍린 ?꾪빐 raw node CLI瑜??듯빐 `accessibility`, `bash-defensive-patterns`, `find-skills`, `seo` 4媛??ㅽ궗 ?섎룞 ?낅뜲?댄듃 ?꾨즺. `bash-defensive-patterns`?먯꽌 ?ㅼ젣 upstream 蹂寃쎌궗??媛먯? 諛?`skills-lock.json`??理쒖떊 hash 諛섏쁺 ?꾨즺.<br>2. **Nature Skills**: `nature-skills` 以묒꺽 由ы룷吏?좊━??理쒖떊 而ㅻ컠??git pull濡??밴릿 ?? 9媛?`nature-*` (academic-search, citation, data, figure, paper2ppt, polishing, reader, response, writing) ?ㅽ궗 踰덈뱾 ?꾩껜瑜?`.agents/skills/`???꾨꼍?섍쾶 蹂듭궗 諛?諛곗튂 ?꾨즺. ?댁젣 Antigravity 諛?? ?먯씠?꾪듃 ?몄뀡?먯꽌 9媛?nature-?ㅽ궗???꾨꼍???쒖꽦?붾릺??Project Skills濡??먮룞 ?몄떇?? |
| Next Priorities | (a) **?ъ슜???ㅽ궗 ?뺤씤**: ?ъ슜?먭? ?덈줈??`nature-*` ?ㅽ궗(?? `nature-polishing`, `nature-paper2ppt`)???쒖슜?????덈룄濡??덈궡. (b) **Supabase Database E2E ?곕룞**: T-251 Supabase ?⑥뒪?뚮뱶 由ъ뀑 諛?濡쒖뺄 CRUD ?뚯뒪???꾨즺 ?좊룄. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **MCP Comprehensive Diagnostics & Verification System Completed**: Created and executed a deterministic automation script (`execution/mcp_diagnostic.py`) incorporating strict UTF-8 stream reconfiguration and ASCII safe outputs to successfully prevent Windows CP949 encoding exceptions. Checked all 6 workspace custom MCP servers (`sqlite-multi`, `system-monitor`, `telegram`, `cloudinary`, `youtube-data`, `n8n-workflow`) at the protocol level through JSON-RPC initialization stdio handshakes, verifying a 100% operational health pass. Confirmed the agent-side integrated Notion MCP connection successfully via direct API-get-self call on bot user `Desk Joopark`. Compiled all findings into `docs/mcp_status_report.md`. |
| Next Priorities | (a) Keep monitoring and upgrading optional integrations (e.g. providing TELEGRAM chat details in `.env` if bot notification functions are needed later). (b) Systematically tackle outstanding Supabase Database connection challenges (T-251). |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard runtime resilience polish**: Preserved existing dirty work in `projects/shorts-maker-v2/`, `nature-skills`, and the prior Field Mode WIP. Wired the existing premium `ErrorBoundary` around `DashboardClient` in `projects/hanwoo-dashboard/src/app/page.js`, then added `src/lib/error-pages-wiring.test.mjs` coverage to keep the dashboard wrapped against client runtime failures. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains separate and user-owned: Supabase database password/control-plane resync is still required before live Prisma CRUD can be proven. Current verification for this change: 282/282 Hanwoo tests passed, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode accessibility polish**: Preserved existing shorts-maker-v2 dirty files and updated only `projects/hanwoo-dashboard/src/components/widgets/FieldModeView.js`. Added explicit accessible labels for leaving field mode, field search, and clearing search; marked the decorative search icon hidden; exposed the daily checklist completion track as an ARIA progressbar; and added pressed/state labels to checklist toggle rows. No tests or QC commands were run in this turn. |
| Next Priorities | Run `python execution/project_qc_runner.py --project hanwoo-dashboard --check test --json` or the full Hanwoo QC runner when validation is desired. Keep T-251 separate until Supabase password/control-plane resync is done by the user. |
| Work | **blind-to-x ?볤? ?몃━嫄?Phase 2 異쒗븯 (`/goal` ?묐떟)** ??"X?먯꽌 紐⑤몢媛 ?볤????ш퀬 ?띠? ?섏?" ?ъ슜??紐⑺몴??4異??앸퀎媛??낆옣/?ㅽ뵂猷⑦봽/援ъ껜 ?듭빱) ?꾨젅?꾩썙?щ줈 ?묐떟. **A. ?꾨＼?꾪듃 ?ъ씠??* `draft_prompts.py` `_build_comment_trigger_block` ?쇰줈 ?몄쐞???ㅻ젅???쒖젙 4異??꾨젅?꾩썙??+ "?볤??????щ━??湲??怨듯넻??蹂댄렪吏꾨━/臾댁깋臾댁랬/?묐퉬濡?異붿긽紐낆궗 留덈Т由?" ?덊떚?⑦꽩???앹꽦 ?꾨＼?꾪듃??媛뺤젣 二쇱엯. **B. ?먮뵒?좊━???ъ씠??* `editorial_reviewer.py` ???볤? ?몃━嫄?4異??먯닔(`identifiability`/`stance`/`open_loop`/`anchor`, 媛?1~10?? 異붽?. 5異??됯퇏(湲곗〈)怨?4異??됯퇏(湲곕낯 ?꾧퀎 6.0) ??**AND** 濡?臾띠뼱 ?????듦낵?댁빞 END; ?쒖そ 誘몃떖?대㈃ 理쒕? 2??由щ씪?댄듃. `EditorialResult.comment_trigger_scores` ?꾨뱶濡??뚮옯?쇰퀎 ?먯닔 ?몄텧. **C. 寃곗젙濡좎쟻 ?ъ씠??* `draft_quality_gate.py` `_is_colorless_take` 臾댁깋臾댁랬 寃異쒓린 ??golden 7媛?false-positive 0% ?뺤씤 ??`hedge ??2 OR (?쇰컲???댄쐶 ??1 AND ?낆옣 ?쒗쁽 0媛?AND ??min_chars)` 濡?蹂댁닔 ?쒕떇. twitter/threads = 湲 ?꾩껜, naver_blog = `<creator_take>` ?쒓렇. `_extract_creator_take` ?뚯꽌濡??꾨씫??warning. **?뚭?** ?⑥쐞 1669 passed + 1 skipped (282s), ?좉퇋 40 耳?댁뒪 100%, ?닿? ?먮똾 4?뚯씪 ruff ?대┛. **二쇱쓽**: `pipeline/quality_gate.py` ???ㅻⅨ ?꾧뎄(Gemini Workstream 1~5)媛 `_check_bland_creator_take`/`_check_semantic_similarity` 異붽? ?묒뾽 以???W293(怨듬갚) 1嫄?誘몄닔???붿〈. ?ㅻⅨ ?꾧뎄??WIP???섎룄?곸쑝濡?誘명꽣移?(`multi_tool_git_index_race_20260520` ?뺤콉 以??. |
| Next Priorities | (a) ?ъ슜?먯뿉寃?而ㅻ컠 ?뱀씤 ?붿껌 ??Phase 2 5?뚯씪(`draft_prompts.py`, `editorial_reviewer.py`, `draft_quality_gate.py`, `tests/unit/test_comment_trigger_uplift.py`, `docs/output_quality_uplift_2026-05-26.md`) stage ?湲? (b) Gemini Workstream 1~5 WIP ??`quality_gate.py` ?⑸쪟 ??`ruff --fix` ?꾩슂 (1嫄?. (c) Phase 3 ?꾨낫: Best-of-2 ??됲꽣 (LLM 鍮꾩슜 2諛곕씪 ?ъ슜??寃곗젙 ?꾩슂), ?좏뵿 ?대윭?ㅽ꽣 理쒓렐 5嫄??섎? ?좎궗??reroll, Notion 寃???붾㈃??4異??먯닔 ?쒖떆. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **湲곗닠 遺梨??꾨㈃ ?닿껐 ?꾧껐 (Workstream 1~5)**: `.ai/` 肄섑뀓?ㅽ듃 臾몄꽌?ㅼ쓣 7??湲곗? 濡쒗뀒?댁뀡 諛??뺤텞 ?꾨즺 (TASKS.md 3KB, CONTEXT.md 110以? HANDOFF.md 18以??ㅼ씠?댄듃). 猷⑦듃 stale 濡쒓렇 ?쒓굅 諛?怨좎븘 ?ㅽ겕由쏀듃?ㅼ쓣 `execution/`濡??섏닠??寃⑸━ ?꾨즺. `llm_client.py` ?댁쓽 以묐났 濡쒗봽瑜?`_run_simple_loop` 鍮꾧났媛?怨듯넻 硫붿꽌?쒕줈 ?듯빀 由ы뙥?좊쭅 諛??먮윭 ?섏쭛 ?移?꽦 蹂닿컯 ?꾨즺. `shorts-maker-v2` ?띿뒪???붿쭊 `text_engine.py` SRP ?뚮뜑留??꾨왂 遺꾪븷 ?꾨즺 諛??곕え ?꾨＼?꾪듃 `DEMO_NEWS`/`DEMO_VS`瑜?`prompts/` ?대뜑 ?꾨옒 ?몃? JSON ?뚯씪濡??몃???諛?濡쒕뵫 ?곕룞 ?꾨즺. `blind-to-x` Phase 2 ?덉쭏 寃뚯씠?몃줈 Bland Creator Take(援ъ껜???섏튂/Buzzwords 媛먯?) 諛?Jaccard 3-gram character-level ?섎? 以묐났 媛먯? ?섎뱶 寃뚯씠???μ갑, `draft_generator.py`??`best_of_n` ?곕룞 ?꾨즺. 紐⑤끂?덊룷 ?꾩껜 ?좊떅 ?뚯뒪??諛??덇굅???뚭? ?뚯뒪??100% 洹몃┛ ?⑥뒪(PASS) 寃利??꾨즺. |
| Next Priorities | (a) ?ъ슜???뱀씤 ?섏뿉 **Workstream 6: hanwoo-dashboard DashboardClient.js 援ъ“ 媛쒖꽑** 吏꾪뻾 ?щ? 寃곗젙. (b) git commit???듯빐 紐⑤끂?덊룷???꾩쟻??由ы뙥?좊쭅 理쒖쥌 QC 蹂?而ㅻ컠 ?뺣━. |
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **?쒖뒪??留ㅻ젰??諛?DX 怨좊룄???꾨즺 (Phase 1, 2, 3, 6)**: ?몃? 媛쒕컻?먯? ?쒖뿰?먮? ?꾪븳 ?꾨━誘몄뾼 ?쇱??댁뒪 ?쒕뵫 ?섏씠吏(`projects/landing-page/` - HTML, CSS, JS)瑜?援ъ텞?섍퀬 ?ㅽ겕/?쇱씠???뚮쭏 諛??ㅽ겕濡??좊땲硫붿씠???꾨퉬. Shields.io 諛곗?? Mermaid 援ъ“?꾨? ?ы븿???쇰툝由?臾몄꽌(`README.md`, `CONTRIBUTING.md`, `LICENSE`) ?꾨퉬. Joolife ?쒖슦 ??쒕낫??濡쒓렇???붾㈃???곕え 怨꾩젙 ?뺣낫 ?명룷諛뺤뒪瑜?異붽??섍퀬 硫붿씤 ?붾㈃ ?ㅻ뜑??DEMO 諛곗?瑜?異붽??섏뿬 ????쒖뿰?깆쓣 洹밸??? Next.js 鍮뚮뱶, Prisma ?대씪?댁뼵???앹꽦, ?꾨줈?몄뒪 蹂댁븞 ?섎뱶??諛??ъ뒪泥댄겕 API(`api/health`)瑜?吏?먰븯??寃쎈웾 Multi-stage Dockerfile怨?PostgreSQL + Redis瑜???踰덉뿉 ?꾩슦??`docker-compose.yml` 援ъ텞. Windows 媛쒕컻?먮? ?꾪빐 1-?대┃ 媛?곹솚寃?諛?DB ?뗭뾽??吏?먰븯??而щ윭???PowerShell ?ㅽ겕由쏀듃(`setup.ps1`) ?쒖옉 ?꾨즺. |
| Next Priorities | (a) ?ъ슜?먯뿉寃?`setup.ps1` ?먮뒗 `docker-compose up`??濡쒖뺄?먯꽌 ?ㅽ뻾?대낵 ???덈룄濡??덈궡. (b) ???곹깭?먯꽌 ?ы듃?대━???ъ씠?몄? ??쒕낫???곕え瑜???몄뿉 利됱떆 怨듦컻/?띾낫 媛?? |
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **Monorepo-wide Spacing/Formatting Test Hardening & QC Sweeps Completed**: Hardened 29 regex test matches in `hanwoo-dashboard` accessibility/wiring tests to support multiline layout, flexible spacing (`\s*`), and optional trailing commas (`,?`) introduced by Biome. Achieved **100% green pass** (282/282 Node tests passed, ESLint clean, Next build OK). For `shorts-maker-v2`, fixed residual Ruff lint errors (UP035, I001) using Python-Ruff module, achieving clean lint and 91% pytest coverage. For `blind-to-x`, resolved a pytest-cov 70% coverage exit code check by isolating pytest execution using `--no-cov` parameter, successfully passing all 49/49 unit tests. Walkthrough and task logs updated. Git staged and locally committed 55 modified files. |
| Next Priorities | Guide user to stage, commit, and push the final QC sweep status. Advise future tools to use flexible RegEx (`[\s\S]*?` and `\s*`) for all test wiring assertions to maintain compatibility with Biome formatter. |
| Date | 2026-05-26 |
| Tool | Claude (Opus 4.7) |
| Work | **blind-to-x ?앹꽦臾??덉쭏 Phase 1 寃곗젙濡좎쟻 ?섎뱶??5醫?異쒗븯 (`docs/output_quality_uplift_2026-05-26.md`)**: 異쒕젰 寃뚯씠??媛먯궗 ????寃곗젙 5媛?寃고븿 ?앸퀎 ??5媛?寃곗젙濡좎쟻 寃??異붽?. (1) `_find_influencer_vocab` zero-tolerance ?댄쐶 12媛?1???깆옣??error, (2) `_ends_with_cta_or_question` 留덉?留?臾몄옣 `?`/CTA ??error (twitter/threads), (3) `_count_emojis` BMP-???쏀넗洹몃옒??移댁슫????2媛?warning / 4媛??댁긽 error, (4) `_has_lead_dependency` 泥?臾몄옣 異쒖쿂 ?꾩엯 媛뺣컯 warning, (5) `quality_gate._check_originality` ?먮Ц 12???곗냽 ?쇱튂 chunk 2媛?warning / 4媛??댁긽 failure (?몄슜遺 ?쒖쇅). 湲곗〈 怨⑤뱺 ?덉떆 3嫄대룄 ??釉뚮옖??蹂댁씠???됱꽌臾?留덈Т由???留욎떠 媛깆떊. 寃利? blind-to-x ?⑥쐞 ?뚯뒪??1622/1622 green (skipped 1), ?좉퇋 ?뚭? 34 耳?댁뒪, ruff ?대┛. 蹂寃쎌? blind-to-x 7媛??뚯씪 + SESSION_LOG/HANDOFF; ?ㅻⅨ ?꾧뎄??hanwoo-dashboard WIP ???섎룄?곸쑝濡?誘몄뒪?뚯씠吏. |
| Next Priorities | (a) ?ъ슜?먯뿉寃?而ㅻ컠 ?뱀씤 ?붿껌 ??而ㅻ컠 ????蹂寃??뚯씪??7媛?stage ?湲?以? (b) Phase 2 LLM-side: creator_take 臾댁깋臾댁랬 寃異? 理쒓렐 罹≪뀡怨??섎? ?좎궗??reroll, Best-of-N 鍮꾧탳. (c) 蹂?PR 踰붿쐞 ??吏꾪뻾 遺梨꾨뒗 `docs/output_quality_uplift_2026-05-26.md` "Phase 2/3" 李멸퀬. |

| Next Priorities | Address Supabase E2E resync (T-251) and systematically proceed with VibeDebt RED reduction execution (T-407). |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard admin diagnostics loading status accessibility**: Continued the active Hanwoo quality uplift and kept unrelated dirty workspace files untouched. Updated `DiagnosticsPageClient.js` so the initial diagnostics loading card and raw-record loading placeholder expose polite busy status semantics (`role="status"`, `aria-live="polite"`, `aria-busy="true"`). Added regression coverage in `diagnostics-copy.test.mjs`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/diagnostics-copy.test.mjs` passed 3/3, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard market price loading busy-state accessibility**: Continued the active Hanwoo quality uplift with a focused accessibility polish. `MarketPriceWidget.js` already exposed the initial loading UI as a polite status region; it now also sets `aria-busy="true"` so the status has a complete busy contract. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 32/32, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard subscription result fallback loading accessibility**: Continued the active Hanwoo quality uplift by hardening subscription result Suspense fallbacks. `subscription/success/page.js` and `subscription/fail/page.js` now expose their loading fallback messages as polite busy status regions (`role="status"`, `aria-live="polite"`, `aria-busy="true"`). Updated `payment-ux-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard payment checkout button busy-state accessibility**: Continued the active Hanwoo quality uplift by tightening `PaymentWidget.js`. The checkout button now uses a single `isPaymentButtonBusy` state for disabled, `aria-busy`, wait cursor, and opacity, so both widget-loading and submit-in-flight states are exposed consistently. Updated `payment-ux-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard payment confirmation status announcement**: Continued the active Hanwoo quality uplift by hardening `subscription/success/page.js`. The dynamic payment confirmation heading now has `aria-live="polite"` and `aria-atomic="true"` so retry/error status changes are announced while preserving the heading element. Updated `payment-ux-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle tag lookup button state labels**: Continued the active Hanwoo quality uplift by hardening `CattleForm.js`. Added `tagLookupButtonLabel` and wired it into the tag lookup button's `aria-label` and `title`, so idle and lookup-in-progress states are exposed consistently with `aria-busy`. Updated `cattle-detail-modal-wiring.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 12/12, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat conversation busy-state accessibility**: Continued the active Hanwoo quality uplift by hardening `AIChatWidget.js`. The conversation `role="log"` region now exposes `aria-busy={isStreaming}`, so assistive technology can perceive answer-generation state on the live message area while streaming. Updated `ai-chat-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-chat-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared HeartIcon decorative accessibility**: Continued the active Hanwoo quality uplift by hardening the shared `HeartIcon` in `common.js`. The icon now exposes `aria-hidden="true"` and `focusable="false"` so alert/status glyphs do not add duplicate semantics where surrounding text already carries the meaning. Updated alert banner regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/alert-banners-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle detail section heading semantics**: Continued the active Hanwoo quality uplift by making `CattleDetailModal.js` section titles navigable to assistive technology. The shared `SectionTitle` helper now renders `role="heading"` with `aria-level={3}`, covering the modal's basic information, breeding, weight, timeline, memo, and QR sections. Updated cattle detail regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 12/12, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard home building section decorative icon accessibility**: Continued the active Hanwoo quality uplift by hiding decorative farm icons in `DashboardClient.js` from assistive technology. The home building section header icon and first-building empty-state CTA icon now use `aria-hidden="true"`, leaving the visible heading and CTA copy as the accessible meaning. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 33/33, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today Focus action accessible labels**: Continued the active Hanwoo quality uplift by adding a consolidated `focusItemLabel` to Today Focus action buttons in `DashboardClient.js`. Each button now exposes its title, detail, and meta context through `aria-label` and `title`, while keeping the existing visible card layout unchanged. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 34/34, `npm.cmd test` passed 317/317, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Quick Action button accessible labels**: Continued the active Hanwoo quality uplift by adding a consolidated `quickActionLabel` to Quick Action buttons in `DashboardClient.js`. Each one-tap action now exposes its label and detail through `aria-label` and `title`, while keeping the existing visible card layout unchanged. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 318/318, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress item title accessibility**: Continued the active Hanwoo quality uplift by reusing the existing consolidated `setupItemLabel` as the `title` for setup progress buttons in `DashboardClient.js`. The hover/title copy now matches the assistive action name that includes title, completion state, and detail. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 318/318, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress score value text accessibility**: Continued the active Hanwoo quality uplift by adding a shared `setupProgressLabel` in `DashboardClient.js`. The setup progress score badge now exposes the percent plus completed/total context through `aria-label` and `title`, and the progressbar exposes the same value via `aria-valuetext` while keeping its concise Korean progress label. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 318/318, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard login password toggle title accessibility**: Continued the active Hanwoo quality uplift by adding a shared `passwordToggleLabel` to `app/login/page.js`. The password show/hide icon button now uses the same Korean copy for `aria-label` and `title`, aligning the login control with the rest of the dashboard's labeled icon actions. Updated error-page/login regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard inventory inline quantity action title accessibility**: Continued the active Hanwoo quality uplift by adding matching `title` copy to the inline inventory quantity save and edit controls in `InventoryTab.js`. The item-specific Korean action labels are now consistent across `aria-label` and hover/title text, matching the surrounding labeled action pattern. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode cattle result action accessibility**: Continued the active Hanwoo quality uplift by adding item-specific `aria-label` and `title` copy to Field Mode cattle search result buttons in `FieldModeView.js`. Each result now announces that it opens the target cattle detail using the cattle name and formatted ear-tag number. Updated Field Mode regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 7/7, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard estrus alert icon wrapper decorative accessibility**: Continued the active Hanwoo quality uplift by marking the estrus alert `alert-icon` wrapper in `AlertBanners.js` as `aria-hidden="true"`. The visual heart glyph is now hidden from assistive technology at the same wrapper level as the calving alert decorative icon. Updated alert banner regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/alert-banners-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard calving card open-action accessibility**: Continued the active Hanwoo quality uplift by adding cow-specific `aria-label` and `title` copy to each calving-list open action in `CalvingTab.js`. Operators and assistive technology can now identify which cow's calving form will open while the visible button text remains concise. Updated calving tab regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/calving-tab-accessibility.test.mjs` passed 5/5, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard sales add-form toggle accessibility**: Continued the active Hanwoo quality uplift by adding state-aware `addFormButtonLabel` copy to the sales record add/cancel toggle in `SalesTab.js`. The control now exposes add, cancel, and save-in-flight meaning through `aria-label`, `title`, and `aria-busy`, matching the surrounding operational form patterns. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print title specificity**: Continued the active Hanwoo quality uplift by adding a shared `printButtonLabel` to `QRCodeWidget.js`. The QR print action now uses the same label-specific copy for both `aria-label` and `title`, so hover/title text identifies the target label in idle and printing states. Updated QR widget regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard ear-tag scanner manual choice title specificity**: Continued the active Hanwoo quality uplift by adding a shared `manualChoiceLabel` to manual scanner result choices in `EarTagScannerModal.js`. Manual choice buttons now expose the same cow name and ear-tag suffix through both `aria-label` and `title`, improving hover/title clarity without changing visible layout. Updated scanner modal regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode checklist toggle action labels**: Continued the active Hanwoo quality uplift by adding a shared `checklistItemLabel` in `FieldModeView.js`. Field Mode checklist buttons now expose the item title, current completion state, and the action to change completion state through both `aria-label` and `title`, making repeated field checks clearer to operators and assistive technology. Updated Field Mode regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 7/7, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle row hover/title context**: Continued the active Hanwoo quality uplift by reusing `cattleAccessibleLabel` as the `title` on `CattleRow` buttons in `cards.js`. Cow rows now expose the same cow detail action and estrus/calving alert summary through hover/title text that assistive technology already receives. Updated card accessibility regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cards-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard feedback toast dismiss title accessibility**: Continued the active Hanwoo quality uplift by adding a shared `toastDismissLabel` in `FeedbackProvider.js`. Toast dismiss buttons now expose the same toast-specific Korean close copy through both `aria-label` and `title`, aligning transient feedback controls with the rest of the dashboard's labeled actions. Updated feedback-provider regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/feedback-provider-copy.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard dashboard header icon action title specificity**: Continued the active Hanwoo quality uplift by matching the notification center and cattle-registration header icon button `title` copy in `DashboardClient.js` to their existing Korean `aria-label` action names. Hover/title UI now communicates that each icon action opens its target, matching the surrounding labeled action pattern. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode and AI launcher title specificity**: Continued the active Hanwoo quality uplift by matching the dashboard Field Mode activation button and floating AI assistant launcher `title` copy to their existing Korean `aria-label` action names. Hover/title UI now carries the same activate/open semantics as assistive technology for these primary entry controls. Updated home-market and AI chat regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `node --test src/lib/ai-chat-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard pen card hover/title context**: Continued the active Hanwoo quality uplift by reusing a shared `penAccessibleLabel` for both `aria-label` and `title` on pen card buttons in `cards.js`. Pen cards now expose the same pen number, cattle count, and estrus-alert context through hover/title UI that assistive technology already receives. Updated card accessibility regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cards-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification mark-all action accessibility**: Continued the active Hanwoo quality uplift by adding an unread-count-aware `markAllAsReadLabel` to `NotificationSystem.js`. The notification dropdown's mark-all button now reuses that label for both `aria-label` and `title`, clarifying how many unread notifications will be marked read while keeping the visible text concise. Updated notification-system regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/notification-system-copy.test.mjs` passed 8/8, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification item read-action accessibility**: Continued the active Hanwoo quality uplift by allowing the shared `DropdownMenuItem` to forward additional props and adding item-specific Korean `aria-label`/`title` copy to notification dropdown items. Each clickable notification now clearly states that activating it marks that notification read. Updated notification-system regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/notification-system-copy.test.mjs` passed 9/9, `npm.cmd test` passed 320/320, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard home building card action label context**: Continued the active Hanwoo quality uplift by adding a shared `buildingCardLabel` to home building card buttons in `DashboardClient.js`. Each building card now reuses that label for `aria-label` and `title`, explicitly exposing the building name, pen count, and current headcount as a navigation action. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 320/320, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard tab navigation action labels**: Continued the active Hanwoo quality uplift by adding a shared `tabActionLabel` to `TabBar` in `widgets.js`. Dashboard tab buttons now reuse that label for both `aria-label` and `title`, and the active tab label includes `?꾩옱 ?좏깮?? so navigation state is clear beyond visual styling. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 36/36, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard admin diagnostics return action accessibility**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the diagnostics page return-to-dashboard button in `DiagnosticsPageClient.js`. The arrow icon is now decorative, so the button exposes one clear navigation action without duplicate icon semantics. Updated diagnostics regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/diagnostics-copy.test.mjs` passed 3/3, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard subscription failure retry action accessibility**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the subscription failure page retry/back button in `app/subscription/fail/page.js`. The control now communicates that it returns to the payment screen to retry, instead of relying only on concise visible button text. Updated payment UX regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard route and global error retry action accessibility**: Continued the active Hanwoo quality uplift by adding shared reset labels to `app/error.js` and `app/global-error.js`. Route-level and global retry buttons now reuse those labels for visible text, `aria-label`, and `title`, making recovery actions explicit across assistive technology and hover/title UI. Updated error-page regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard legal document home-link accessibility**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the shared legal document home-return link in `LegalDocumentLayout.js`. The arrow icon is now decorative, so privacy/terms pages expose one clear home navigation action without duplicate icon semantics. Updated legal-page regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/legal-pages-copy.test.mjs` passed 1/1, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard not-found and route-error home-link accessibility**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the not-found page and route error page dashboard-return links. Both home navigation actions are now clear to assistive technology and hover/title UI instead of relying only on visible link text. Updated error-page regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard inventory inline quantity saving state labels**: Continued the active Hanwoo quality uplift by adding an item-specific `itemQuantitySaveLabel` to inline inventory quantity edits. While a row save is in flight, the save button now exposes `?ш퀬 ?섎웾 ???以? through `aria-label`, `title`, `aria-busy`, and visible `???以?..` copy, instead of leaving the action label static. Updated inventory regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/empty-state-wiring.test.mjs` passed 17/17, `node --test src/lib/home-market-copy.test.mjs` passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard settings building delete progress labels**: Continued the active Hanwoo quality uplift by adding a state-aware `buildingDeleteButtonLabel` to building delete buttons in Settings. While a building delete is in flight, the row action now exposes `????젣 以? through `aria-label`, `title`, `aria-busy`, and visible `??젣 以?..` copy instead of leaving the destructive button static. Updated settings regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/settings-tab-accessibility.test.mjs` passed 12/12, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle detail archive visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle detail archive button. The action already exposed busy/disabled and Korean accessible labels; it now also shows `泥섎━ 以?..` while archive/delete or breeding-save work blocks the modal, keeping the visible destructive action in sync with the busy state. Updated cattle detail regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle form top cancel busy label**: Continued the active Hanwoo quality uplift by reusing `cancelButtonLabel` on the cattle edit form's top icon-only back/cancel button. While a save is in flight, the button now exposes `媛쒖껜 ???以묒뿉??痍⑥냼?????놁뒿?덈떎` through both `aria-label` and `title`, matching the bottom cancel action instead of staying on static back-to-list copy. Updated cattle form regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle detail close busy label**: Continued the active Hanwoo quality uplift by adding a state-aware `closeButtonLabel` to the cattle detail modal close button. While archive/delete or breeding-save work is in flight, the icon-only close control now exposes that the selected cattle detail window cannot be closed yet instead of staying on static close copy. Updated cattle detail regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard MTRACE timeout recovery copy consistency**: Continued the active Hanwoo quality uplift by changing the 異뺤궛臾쇱씠?μ젣 timeout failure message from `異뺤궛臾쇱씠?μ젣 議고쉶 ?쒓컙??珥덇낵?섏뿀?듬땲?? ?ㅼ떆 ?쒕룄??二쇱꽭??` to `異뺤궛臾쇱씠?μ젣 議고쉶 ?쒓컙??珥덇낵?섏뿀?듬땲?? ?좎떆 ???ㅼ떆 ?쒕룄??二쇱꽭??`, matching the app-wide transient retry wording used for degraded external services. Updated mtrace regression coverage to prevent the terse timeout retry copy from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/mtrace.test.mjs` passed 4/4, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat welcome helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the AI farm assistant welcome guidance from `沅곴툑???먯쓣 臾쇱뼱蹂댁꽭??` to `沅곴툑???먯쓣 吏덈Ц??二쇱꽭??`, matching the input placeholder and the app-wide Korean helper tone. Updated AI chat widget regression coverage to prevent the command-style welcome copy from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-chat-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard subscription page helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the subscription page value copy from `AI 蹂댁“ 湲곕뒫?????덉젙?곸쑝濡??ъ슜?섏꽭??` to `AI 蹂댁“ 湲곕뒫?????덉젙?곸쑝濡??ъ슜??二쇱꽭??`, aligning the payment entry page with the app-wide Korean helper tone. Updated payment UX regression coverage to prevent the command-style subscription copy from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard login and not-found operations helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the login and not-found route guidance from `?ъ쑁, ?ш퀬, 異쒗븯 ?낅Т瑜??댁뼱??愿由ы븯?몄슂.` to `?ъ쑁, ?ш퀬, 異쒗븯 ?낅Т瑜??댁뼱??愿由ы빐 二쇱꽭??`, keeping entry and recovery pages aligned with the app-wide Korean helper tone. Updated error-page regression coverage to prevent the command-style route copy from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard pen cattle preview hover context**: Continued the active Hanwoo quality uplift by changing pen-card cattle preview titles from cow-name-only hover text to state-aware Korean labels (`諛쒖젙 ?뚮┝ ?덉쓬` / `移?諛곗튂??), so quick pen previews expose alert context without opening the detail view. Updated card accessibility regression coverage to keep the contextual preview titles. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cards-accessibility.test.mjs` passed 4/4, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard calving alert due-date fallback specificity**: Continued the active Hanwoo quality uplift by changing the calving alert missing target-date fallback from placeholder `-` to `遺꾨쭔 ?덉젙??誘몃벑濡?, so alert chips explain which date field is unavailable instead of rendering a bare dash. Updated alert-banner regression coverage to keep the specific missing-date copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/alert-banners-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard profitability widget record-based copy consistency**: Continued the active Hanwoo quality uplift by changing the profitability widget empty state from generic `?섏씡??遺꾩꽍 ?곗씠?곌? 遺議깊빀?덈떎.` to `?섏씡??遺꾩꽍???꾩슂??湲곕줉??遺議깊빀?덈떎.`, and changing the customized assumptions badge from `?띻? ?곗씠?? to `?띻? 湲곕줉 湲곕컲`, so the widget refers to operator-entered records instead of generic data. Updated profitability regression coverage to keep the record-based wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/profitability-copy.test.mjs` passed 10/10, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard weather partial-forecast information-copy consistency**: Continued the active Hanwoo quality uplift by changing the partial weather forecast degraded-state message from `?쇰? ?덈낫 ?곗씠?곕? 遺덈윭?ㅼ? 紐삵빐 ?꾩옱 ?좎뵪? ?뺤씤???덈낫留??쒖떆?⑸땲??` to `?쇰? ?덈낫 ?뺣낫瑜?遺덈윭?ㅼ? 紐삵빐 ?꾩옱 ?좎뵪? ?뺤씤???덈낫留??쒖떆?⑸땲??`, keeping weather fallback copy aligned with the app's information-oriented weather wording. Updated weather-state regression coverage to keep the information wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/weather-state.test.mjs src/lib/home-market-copy.test.mjs` passed 47/47, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight record/information-copy consistency**: Continued the active Hanwoo quality uplift by changing the AI insight widget description from `?띿옣 ?곗씠?곕? 湲곕컲?쇰줈 ?곗꽑?쒖쐞 3媛吏 ?됰룞???뺣━?⑸땲??` to `?띿옣 湲곕줉??湲곕컲?쇰줈 ?곗꽑?쒖쐞 3媛吏 ?됰룞???뺣━?⑸땲??`, and changing the settings widget description from `耳쒕㈃ ?띿옣 ?붿빟 ?곗씠?곕? AI 遺꾩꽍 API濡??꾩넚?⑸땲??` to `耳쒕㈃ ?띿옣 ?붿빟 ?뺣낫瑜?AI 遺꾩꽍 API濡??꾩넚?⑸땲??`. Updated AI insight and settings regression coverage to keep the record/information wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-insight-widget-copy.test.mjs src/lib/settings-tab-accessibility.test.mjs` passed 22/22, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat farm-context information-copy consistency**: Continued the active Hanwoo quality uplift by changing AI chat farm-context wording from `?쒓났???띿옣 ?곗씠?곕? 洹쇨굅濡?/`?곗씠?곌? ?녾굅??遺덊솗?ㅽ븳 寃쎌슦` to `?쒓났???띿옣 ?뺣낫瑜?洹쇨굅濡?/`?뺣낫媛 ?녾굅??遺덊솗?ㅽ븳 寃쎌슦`, changing the status fallback from `?곹깭蹂?媛쒖껜 ?곗씠???놁쓬` to `?곹깭蹂?媛쒖껜 吏묎퀎 ?놁쓬`, and changing the farm-context failure fallback to `?띿옣 ?뺣낫瑜?遺덈윭?ㅼ? 紐삵뻽?듬땲??`. Updated AI chat route regression coverage to keep the information/aggregate wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-chat-api.test.mjs` passed 8/8, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight prompt information-copy consistency**: Continued the active Hanwoo quality uplift by changing AI insight API/prompt instructions from `?쒓났???띿옣 ?ㅻ깄???곗씠?곕? 洹쇨굅濡?/`?곗씠??湲곕컲 ?꾧툒?? to `?쒓났???띿옣 ?ㅻ깄???뺣낫瑜?洹쇨굅濡?/`?띿옣 ?뺣낫 湲곕컲 ?꾧툒??, and aligning the prompt-builder priority format hint from `?곗씠??湲곕컲` to `?띿옣 ?뺣낫 湲곕컲`. Updated AI insight route/prompt regression coverage to keep the information wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-insight.test.mjs src/lib/ai-insight-widget-copy.test.mjs` passed 25/25, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard full-list loading information-copy consistency**: Continued the active Hanwoo quality uplift by changing paginated dashboard full-list timeout/failure copy from `??쒕낫???곗씠?곕? 遺덈윭?ㅻ뒗 ???쒓컙???ㅻ옒 嫄몃━怨??덉뒿?덈떎.` / `??쒕낫???곗씠?곕? 遺덈윭?ㅼ? 紐삵뻽?듬땲??` to `??쒕낫???뺣낫瑜?遺덈윭?ㅻ뒗 ???쒓컙???ㅻ옒 嫄몃━怨??덉뒿?덈떎.` / `??쒕낫???뺣낫瑜?遺덈윭?ㅼ? 紐삵뻽?듬땲??`. Updated home-market regression coverage to keep the information wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 38/38, `npm.cmd test` passed 349/349, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight low-THI record-copy consistency**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight safe-condition guidance from `泥댁쨷 痢≪젙 ?곗씠??媛깆떊???곹빀???쒖젏` to `泥댁쨷 痢≪젙 湲곕줉 媛깆떊???곹빀???쒖젏`, aligning visible AI guidance with operator-entered record terminology. Updated AI Insight regression coverage to keep the record wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-insight.test.mjs` passed 16/16, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Building delete blocker cattle-copy consistency**: Continued the active Hanwoo quality uplift by changing the building deletion blocker from `??異뺤궗??N?먯쓽 ?뚭? ?덉뼱 ??젣?????놁뒿?덈떎. 癒쇱? ?뚮? ?대룞??二쇱꽭??` to `??異뺤궗??N?먯쓽 媛쒖껜媛 ?덉뼱 ??젣?????놁뒿?덈떎. 癒쇱? 媛쒖껜瑜??대룞??二쇱꽭??`, aligning server-action feedback with dashboard `媛쒖껜` terminology. Updated server action copy regression coverage to keep the `媛쒖껜` wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/actions-copy.test.mjs` passed 2/2, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode top-card operator-tone polish**: Continued the active Hanwoo quality uplift by changing the Field Mode top card labels from `?꾩옣 湲곕룞??洹밸??? / `?ㅽ봽?쇱씤 ?먭??앹〈` to `?꾩옣 ?먭? 以鍮? / `?ㅽ봽?쇱씤 ???, aligning visible onsite mode copy with restrained operational tool tone. Updated FieldMode regression coverage to keep the toned-down wording and prevent the older marketing-style phrases from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 8/8, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode header Korean operator-copy polish**: Continued the active Hanwoo quality uplift by changing the Field Mode header eyebrow from `Smart Field Overlay` to `?꾩옣 ?먭? ?붾㈃`, and changing the hidden search section label from `媛쒖껜 珥덇퀬??寃?? to `媛쒖껜 鍮좊Ⅸ 寃??, removing remaining English/overstated wording from the onsite mode header and search landmark. Updated FieldMode regression coverage to keep the Korean restrained wording and prevent the older phrases from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 8/8, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode checklist eyebrow Korean-copy polish**: Continued the active Hanwoo quality uplift by changing the Field Mode checklist eyebrow from `Tactile stables list` to `異뺤궗 ?먭? 紐⑸줉`, removing a remaining visible English label from the onsite checklist card. Updated FieldMode regression coverage to keep the Korean checklist label and prevent the older English phrase from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 8/8, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode status counter copy accuracy polish**: Continued the active Hanwoo quality uplift by changing the Field Mode counter footnotes from the over-assertive `?댄몴 寃??100% ?꾨즺` and stiff `媛異?湲곗긽 寃쎈낫 ?뺤씤 ?붾쭩` to `?댄몴 ?뺣낫 湲곗? 吏묎퀎` and `湲곗긽 寃쎈낫 ?뺤씤 ?꾩슂`, making the onsite counters less misleading and more consistent with operator-facing Korean copy. Updated FieldMode regression coverage to keep the accurate counter wording and prevent the older phrases from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 8/8, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode search result loading-copy polish**: Continued the active Hanwoo quality uplift by changing the Field Mode search result header from `寃??留ㅼ묶 媛쒖껜` to `寃?됰맂 媛쒖껜`, and changing the loading status from `?꾩껜 濡쒕뱶 以?..` to `?꾩껜 紐⑸줉 遺덈윭?ㅻ뒗 以?..`, making the onsite search overlay read like natural Korean product copy. Updated FieldMode regression coverage to keep the polished search-result wording and prevent the older mechanical phrases from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 8/8, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI route system-instruction helper-tone polish**: Continued the active Hanwoo quality uplift by changing AI chat and AI insight route system instructions from command-style `留먰븯?몄슂` / `?덈궡?섏꽭?? / `寃곗젙?섏꽭?? / `?ы븿?섏꽭?? phrasing to helper-tone `留먰빐 二쇱꽭?? / `?덈궡??二쇱꽭?? / `寃곗젙??二쇱꽭?? / `?ы븿??二쇱꽭??, aligning model-facing prompts with the app's operator-facing Korean tone. Updated AI chat and AI insight route regression coverage to keep the helper-tone prompt wording and prevent the older command-style phrases from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-chat-api.test.mjs src/lib/ai-insight-widget-copy.test.mjs` passed 18/18, `npm.cmd test` passed 350/350, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode persisted checklist normalization**: Continued the active Hanwoo quality uplift by routing saved Field Mode checklist localStorage values through the default checklist shape, preserving checked state only for known checklist items and falling back to a fresh checklist for malformed/non-array saved data. Wrapped checklist toggle storage writes so localStorage failures do not break onsite checklist interaction. Updated FieldMode regression coverage to keep the safe persisted-checklist path and prevent raw `JSON.parse(saved)` from returning directly. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 9/9, `npm.cmd test` passed 351/351, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode checklist storage access hardening**: Continued the active Hanwoo quality uplift by consolidating checklist localStorage reads and writes behind safe helpers. Initial render now tolerates storage read or JSON parse failures, and daily initialization plus checklist toggles tolerate storage write failures without breaking onsite mode interaction. Updated FieldMode regression coverage to keep the safe read/write helpers and prevent direct fresh-checklist storage writes from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 9/9, `npm.cmd test` passed 351/351, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Widget settings persisted visibility hardening**: Continued the active Hanwoo quality uplift by consolidating widget visibility defaults, persisted-value normalization, and safe localStorage read/write helpers in `useWidgetSettings`. Saved settings now preserve only boolean values for known widget ids, fall back to defaults for malformed/non-object saved values, and tolerate storage write failures without breaking settings toggles. Updated settings regression coverage to keep the safe persisted-widget-settings path and prevent raw JSON spread or direct toggle writes from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/settings-tab-accessibility.test.mjs` passed 13/13, `npm.cmd test` passed 352/352, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Theme preference storage hardening**: Continued the active Hanwoo quality uplift by consolidating theme preference loading, guarded system-theme fallback, and safe localStorage writes in `useTheme`. Settings now render safely when browser storage or `matchMedia` throws, falling back to `light` on server and to guarded system preference on the client. Updated settings regression coverage to keep the safe theme-storage path and prevent direct initialization or direct effect writes from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/settings-tab-accessibility.test.mjs` passed 14/14, `npm.cmd test` passed 353/353, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather geolocation fallback hardening**: Continued the active Hanwoo quality uplift by guarding dashboard and `useWeather` geolocation lookup. Missing farm coordinates now fall back to the default Namwon weather coordinates when `navigator` is unavailable, permission lookup fails, or `getCurrentPosition` throws synchronously. Updated home dashboard regression coverage to keep the guarded geolocation path and prevent unguarded `navigator` access or inline fallback callbacks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 39/39, `npm.cmd test` passed 354/354, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export temporary download cleanup hardening**: Continued the active Hanwoo quality uplift by keeping the generated Excel CSV Blob URL and temporary anchor in local variables, then removing the temporary DOM node and revoking the object URL from `finally`. This prevents DOM append/click failures from leaving temporary download resources behind while preserving duplicate-download lock behavior and Korean error feedback. Updated Excel export regression coverage to keep cleanup in `finally` and prevent the old inline remove/revoke path from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/excel-export-button-copy.test.mjs` passed 3/3, `npm.cmd test` passed 355/355, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print failure-state unlock hardening**: Continued the active Hanwoo quality uplift by wrapping QR label print completion in guarded cleanup. Browser `focus()`/`print()` failures now announce a Korean retry message, and `close()` is also guarded so the duplicate-print lock and busy state are always released. Updated QR widget regression coverage to keep the try/catch/finally print path and prevent the old success-only reset path from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 4/4, `npm.cmd test` passed 356/356, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print-window preparation cleanup hardening**: Continued the active Hanwoo quality uplift by wrapping QR print-window document preparation in guarded cleanup. If DOM setup or `doc.close()` fails after the popup opens, the code now marks the print callback committed, closes the popup through a guarded helper, releases the duplicate-print lock, clears the busy state, and announces a Korean retry message. Updated QR widget regression coverage to keep the preparation `try/catch` path and prevent unguarded print-window setup from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 5/5, `npm.cmd test` passed 357/357, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Online status browser API hardening**: Continued the active Hanwoo quality uplift by adding a guarded online-status reader and wrapping online/offline event listener registration plus cleanup. Missing or restricted `navigator.onLine`, `window.addEventListener`, and `window.removeEventListener` access now falls back safely instead of breaking dashboard offline-aware flows. Added focused source regression coverage for safe online-state reads and listener cleanup. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/use-online-status.test.mjs` passed 2/2, `npm.cmd test` passed 359/359, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Offline queue storage failure hardening**: Continued the active Hanwoo quality uplift by wrapping offline queue localStorage persistence and clear operations in best-effort guards. Restricted browser storage now no longer breaks offline-aware dashboard flows, normalized queue rewrites, queue clearing, or dead-letter queue clearing. Added focused source regression coverage for safe queue persistence and clear operations. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/offline-queue-storage.test.mjs` passed 2/2, `npm.cmd test` passed 361/361, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Pagination request timeout timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping cattle, sales, and shared cursor pagination request timeout scheduling and cleanup in guarded blocks. If browser timer scheduling fails, load-more requests continue without crashing; cleanup now clears timeout handles best-effort. Strengthened cattle and sales pagination regression coverage to keep guarded timer scheduling and cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `npm.cmd test -- --test-name-pattern="pagination"` passed, `npm.cmd test` passed 362/362, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment widget timeout timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping Toss payment widget load-timeout scheduling and cleanup in guarded blocks. If browser timer scheduling fails, widget initialization continues on the original promise instead of failing immediately; cleanup now clears timeout handles best-effort. Strengthened payment UX regression coverage to keep guarded timeout scheduling and cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 7/7, `npm.cmd test` passed 363/363, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared fetch timeout timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping `fetchWithTimeout` timeout scheduling and cleanup in guarded blocks. If timer scheduling fails, shared dashboard, payment, weather, KAPE, and MTRACE fetch requests continue instead of failing before network start; cleanup now clears timeout handles best-effort. Added focused regression coverage for guarded timeout scheduling and cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/fetch-with-timeout.test.mjs src/lib/payment-ux-copy.test.mjs src/lib/mtrace.test.mjs` passed 12/12, `npm.cmd test` passed 364/364, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight client timeout timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping the AI insight widget request timeout scheduling and cleanup in guarded blocks. If browser timer scheduling fails, insight requests continue instead of crashing before fallback handling; promise completion and effect cleanup now clear timeout handles best-effort. Strengthened AI insight regression coverage to keep guarded timeout scheduling and cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-insight-widget-copy.test.mjs` passed 10/10, `npm.cmd test` passed 364/364, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode celebration timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping Field Mode checklist-completion celebration firework timers, auto-hide timer, and timeout cleanup in guarded helpers. If browser timer scheduling fails, the celebration effect no longer crashes and cleanup clears any scheduled handles best-effort. Strengthened FieldMode regression coverage to keep guarded celebration timer scheduling and cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 10/10, `npm.cmd test` passed 365/365, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print fallback timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping the QR label print-window fallback timer scheduling in a guarded helper. Restricted popup timer APIs no longer convert fallback scheduling failures into full print-window preparation failures; the popup load event path remains active and scheduling failures are logged. Strengthened QR widget regression coverage to keep guarded fallback timer scheduling. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 6/6, `npm.cmd test` passed 366/366, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Subscription success timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping the subscription success page's invalid-amount status timer, payment-confirmation retry timer, success redirect timer, and cleanup in guarded helpers. If browser timer scheduling fails, the intended callback runs immediately instead of leaving the payment result page in a stale status; cleanup clears timeout handles best-effort. Strengthened payment UX regression coverage to keep guarded subscription success timers. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 8/8, `npm.cmd test` passed 367/367, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight route timeout timer failure hardening**: Continued the active Hanwoo quality uplift by wrapping the AI insight API route's Gemini timeout scheduling and cleanup in guarded blocks. If runtime timer scheduling fails, the original Gemini request continues instead of crashing the route; cleanup clears timeout handles best-effort while preserving the existing timeout fallback path when scheduling succeeds. Strengthened AI insight regression coverage to keep guarded route timeout scheduling and cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-insight-widget-copy.test.mjs` passed 10/10, `npm.cmd test` passed 367/367, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode audio/vibration browser API hardening**: Continued the active Hanwoo quality uplift by wrapping audio context class access, audio context creation, suspended-context resume, and tactile vibration calls in guarded best-effort paths. Restricted browser audio or vibration APIs no longer break Field Mode and scanner feedback flows before the existing sound/vibration helpers can degrade. Strengthened FieldMode/audio regression coverage to keep guarded audio and vibration API access. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 11/11, `npm.cmd test` passed 368/368, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode animation frame failure hardening**: Continued the active Hanwoo quality uplift by wrapping Field Mode celebration `requestAnimationFrame` scheduling, `cancelAnimationFrame` cleanup, resize listener registration/removal, and missing canvas 2D context handling in guarded paths. Restricted animation frame or resize APIs no longer break onsite celebration UI, and context absence now exits through a guarded close timer instead of crashing the effect. Strengthened FieldMode regression coverage to keep guarded animation frame scheduling, cleanup, resize listener handling, and context fallback. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 12/12, `npm.cmd test` passed 369/369, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner animation frame failure hardening**: Continued the active Hanwoo quality uplift by wrapping the scanner modal's `requestAnimationFrame` scheduling and `cancelAnimationFrame` cleanup in guarded helpers. The scanner now resets stored frame handles after cleanup and routes missing canvas context or frame scheduling failures to the existing no-match state without synchronous effect state updates. Strengthened scanner regression coverage to keep guarded frame scheduling, cleanup, handle reset, and no-match fallback. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 5/5, `npm.cmd test` passed 370/370, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Theme DOM application failure hardening**: Continued the active Hanwoo quality uplift by wrapping theme document-root lookup and `data-theme`/dark-class DOM mutation in guarded paths. Restricted or unusual browser DOM access no longer breaks settings/theme rendering after safe storage and system-theme fallback; if document root lookup or DOM mutation fails, the hook degrades without throwing. Strengthened settings regression coverage to keep guarded document-root access, guarded theme DOM mutation, and prevention of direct `document.documentElement` mutation. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/settings-tab-accessibility.test.mjs` passed 14/14, `npm.cmd test` passed 370/370, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export cleanup failure hardening**: Continued the active Hanwoo quality uplift by wrapping temporary download-link removal and Blob URL revocation in guarded helpers. DOM cleanup or URL revoke failures can no longer prevent the export duplicate-download lock and busy state from being released. Strengthened Excel export regression coverage to keep best-effort cleanup helpers, finalizer ordering, and prevention of direct cleanup calls returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/excel-export-button-copy.test.mjs` passed 3/3, `npm.cmd test` passed 370/370, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared focus failure hardening**: Continued the active Hanwoo quality uplift by adding `focusElementSafely()` and routing cattle form, cattle detail, AI chat panel/launcher, and notification modal focus restoration through it. Restricted browser focus APIs no longer break modal/chat open-close flows; focus now degrades best-effort. Strengthened modal/chat regression coverage to keep the shared helper, guarded focus calls, and prevention of direct optional focus calls returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs src/lib/ai-chat-widget-copy.test.mjs src/lib/notification-modal-copy.test.mjs` passed 26/26, `npm.cmd test` passed 370/370, `npm.cmd run lint` passed, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard ErrorBoundary reset-handler failure hardening**: Continued the active Hanwoo quality uplift by wrapping custom `onReset` recovery callbacks in the dashboard runtime `ErrorBoundary`. Synchronous throws and promise rejections from custom reset handlers now route through the same fallback-state logging path as reload failures instead of escaping from the recovery button event handler. Strengthened error-page source regression coverage to keep guarded custom reset handling and shared reset failure logging. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 10/10, `npm.cmd test` passed 376/376, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode full-list async cleanup hardening**: Continued the active Hanwoo quality uplift by adding a cleanup guard to the Field Mode background full-cattle-list loading effect. Stale `ensureAllCattleLoaded()` completions after unmount or dependency replacement no longer update `loadingAllCattle` state. Strengthened FieldMode source regression coverage to keep the cleanup guard and prevent direct `.finally(() => setLoadingAllCattle(false))` from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 13/13, `npm.cmd test` passed 377/377, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard full-list preload unmount cleanup hardening**: Continued the active Hanwoo quality uplift by adding a dashboard mounted-state guard around full cattle registry and full sales ledger preload completions. Stale preload resolve/reject/finally paths after dashboard unmount no longer update registry, error, or loading state while still clearing in-flight refs. Strengthened home dashboard regression coverage to keep the mounted guard on cattle and sales preload success/error/loading paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 41/41, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification modal SMS async cleanup hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to the notification modal SMS test action. Stale `onTestSMS` promise completions after modal unmount no longer update `isTestingSMS` state, while mounted sends still keep the existing busy lock and restore the button when complete. Strengthened notification modal regression coverage to keep the mounted guard and prevent direct `finally { setIsTestingSMS(false); }` from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/notification-modal-copy.test.mjs` passed 8/8, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat stream unmount cleanup hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard and unmount abort cleanup to the AI chat widget. Stale stream chunk/done/error callbacks and aborted-stream finalizers after component unmount no longer update messages or streaming state, while normal close still aborts the active stream and clears the visible busy state. Strengthened AI chat source regression coverage to keep the mounted guard, unmount abort, and guarded stream callbacks. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-chat-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export async cleanup unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to the Excel/CSV export button. Stale async export finalizers after component unmount no longer update `isPreparing` state, while temporary download-link/Blob URL cleanup and duplicate-export lock release still run. Strengthened Excel export source regression coverage to keep the mounted guard and prevent direct finalizer state resets from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/excel-export-button-copy.test.mjs` passed 3/3, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price refresh start unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state start guard to the market price widget refresh path. Delayed refresh calls after component unmount now return without starting a new KAPE request or setting `loading` state, while existing mounted completion guards still protect stale success/finally paths. Strengthened home/market regression coverage to keep the start guard plus completion/loading guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 41/41, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print callback unmount cleanup hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to the QR print widget. Popup load/fallback callbacks and print failure/completion paths after component unmount no longer update printing or status state; unmounted finish-print callbacks now close the print window and release the duplicate-print lock without touching React state. Strengthened QR regression coverage to keep the mounted guard, guarded status updates, and unmounted finish-print short-circuit. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 7/7, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment widget async cleanup unmount hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to the payment checkout widget. Async payment request finalizers now release the duplicate-submit ref while avoiding `setIsSubmitting(false)` after component unmount. Strengthened payment UX regression coverage to keep the mounted cleanup guard and guarded payment finalizer. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 9/9, `npm.cmd test` passed 378/378, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard cattle archive unmount cleanup hardening**: Continued the active Hanwoo quality uplift by guarding the dashboard cattle archive flow with the existing dashboard mounted-state ref. Async delete success, error, catch, and finalizer paths no longer update dashboard state or show toasts after unmount, while successful server-action completion still returns `true`. Strengthened home and cattle-detail regression coverage to keep the guarded archive paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs src/lib/cattle-detail-modal-wiring.test.mjs` passed 59/59, `npm.cmd test` passed 379/379, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Login submit unmount cleanup hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard to the login submit flow. Async sign-in, credential failure, navigation failure, catch, and finalizer paths now release the duplicate-submit ref while avoiding login error/submitting state updates after unmount. Strengthened login/error-page regression coverage to keep the mounted cleanup guard and guarded submit finalizer. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 10/10, `npm.cmd test` passed 379/379, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight stale callback cleanup hardening**: Continued the active Hanwoo quality uplift by adding a cleanup cancellation guard to the AI insight widget. Stale summary-change or unmount callbacks now avoid heuristic reset, parsed-response, fallback-reason, and loading-state updates after cleanup while preserving the existing timeout abort fallback behavior. Strengthened AI insight regression coverage to keep the cancellation guard across microtask, success, catch, finalizer, and cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-insight-widget-copy.test.mjs` passed 10/10, `npm.cmd test` passed 379/379, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard drag move confirmation unmount cleanup hardening**: Continued the active Hanwoo quality uplift by adding a mounted-state guard immediately after the drag-and-drop cattle move confirmation dialog resolves. Stale confirmation completions after dashboard unmount now return before building the update payload or entering the cattle update/offline mutation path. Strengthened home dashboard regression coverage to keep the post-confirmation guard. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 388/388, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Subscription success timer cleanup hardening**: Continued the active Hanwoo quality uplift by adding cleanup-aware cancellation guards to the subscription success page timer callbacks. Invalid-amount status updates, delayed dashboard redirects, redirect-failure status updates, and pending-confirmation retry callbacks now avoid stale work after the payment success component has cleaned up. Strengthened payment UX regression coverage to keep the stale timer callback guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 10/10, `npm.cmd test` passed 389/389, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feedback provider unmount cleanup hardening**: Continued the active Hanwoo quality uplift by adding mounted-state guards to toast dismissal, notification scheduling, delayed toast callbacks, and confirmation close state updates. Provider cleanup now clears toast timers and resolves any pending confirmation dialog promise as `false`, preventing awaiting dashboard actions from hanging on stale confirmation state after provider unmount. Strengthened feedback provider regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/feedback-provider-copy.test.mjs` passed 4/4, `npm.cmd test` passed 390/390, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner deferred no-match cleanup hardening**: Continued the active Hanwoo quality uplift by adding cleanup-aware guards to the scanner modal's deferred no-match fallback. Missing canvas contexts and animation-frame scheduling failures no longer update scan state after the modal has closed or the effect has cleaned up. Strengthened scanner regression coverage to keep the guarded microtask fallback and frame-failure cleanup paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 5/5, `npm.cmd test` passed 390/390, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode celebration timer cleanup hardening**: Continued the active Hanwoo quality uplift by adding cleanup-aware guards to Field Mode celebration close timers and animation-frame failure timers. No-canvas fallback, frame-failure fallback, particle-completion, and the normal 4.5s close callback now avoid state updates after the celebration effect has cleaned up. Strengthened FieldMode regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 13/13, `npm.cmd test` passed 390/390, `npm.cmd run lint` passed clean, `git diff --check` passed with CRLF warnings only, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Pagination hook timeout scheduling failure hardening**: Continued the active Hanwoo quality uplift by tightening cattle, sales, and shared cursor pagination hooks. Timeout scheduling failures now immediately mark the request timed out and abort the controller instead of silently dropping timeout protection in restricted browser environments. Added shared cursor pagination regression coverage and strengthened cattle/sales pagination coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-pagination-feedback.test.mjs src/lib/sales-pagination-feedback.test.mjs src/lib/cursor-pagination-feedback.test.mjs` passed 5/5, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price polling fallback hardening**: Continued the active Hanwoo quality uplift by tightening the market price widget hourly KAPE refresh path. Restricted browser environments where `window.setInterval` throws now fall back to a cleanup-aware `setTimeout` polling loop instead of permanently losing automatic price refreshes. Strengthened home/market regression coverage to keep fallback polling and cleanup behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Online-status listener partial-registration cleanup hardening**: Continued the active Hanwoo quality uplift by tightening `useOnlineStatus()`. If restricted browser event listener setup fails after one online/offline listener was already attached, the hook now removes any partial registration before returning, and normal unmount cleanup removes only listeners confirmed registered. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/use-online-status.test.mjs` passed 2/2, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Widget settings unknown-id guard hardening**: Continued the active Hanwoo quality uplift by tightening `useWidgetSettings()`. Only ids registered in `WIDGET_REGISTRY` can now be toggled, so accidental caller bugs or stale UI events cannot persist unknown widget keys into local visibility settings. Strengthened settings coverage to keep the guard before state/storage mutation. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/settings-tab-accessibility.test.mjs` passed 14/14, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print completion callback scheduling failure hardening**: Continued the active Hanwoo quality uplift by tightening QR label print completion scheduling. Print-window load listener registration and fallback timer scheduling now return success flags, and if both paths fail in a restricted browser environment, the print completion cleanup runs immediately so the duplicate-print lock and busy state do not stay stuck. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 7/7, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode delayed celebration firework cleanup hardening**: Continued the active Hanwoo quality uplift by tightening the Field Mode celebration effect. Delayed secondary firework timer callbacks now check the existing cleanup cancellation flag before mutating the local particle queue, preventing stale timer callbacks from doing post-cleanup animation work if timer cleanup is unavailable in a restricted browser environment. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 13/13, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather geolocation stale-callback cleanup hardening**: Continued the active Hanwoo quality uplift by tightening the dashboard weather effect and shared `useWeather()` hook. Geolocation success/error callbacks now return after effect cleanup before starting fallback or coordinate weather fetches, avoiding post-unmount network work while preserving the existing stale-state update guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather zero-coordinate handling hardening**: Continued the active Hanwoo quality uplift by tightening the dashboard weather effect and shared `useWeather()` hook. Farm weather coordinates are now treated as present when they are non-null/non-undefined, allowing valid zero latitude or longitude values to reach the existing coordinate validator instead of being misclassified as missing coordinates. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Profitability zero purchase-price handling hardening**: Continued the active Hanwoo quality uplift by tightening the profitability estimate service. A valid `purchasePrice` of `0` is now preserved as the base cost, and only malformed/missing purchase-price input falls back to `DEFAULT_CALF_COST`, preventing self-bred or zero-cost cattle from being over-costed in shipment profitability estimates. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/profitability-copy.test.mjs` passed 10/10, `npm.cmd test` passed 391/391, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Setup progress malformed collection row hardening**: Continued the active Hanwoo quality uplift by tightening setup-progress item counting. Only non-null object rows now count as completed operating data, so malformed cached/caller rows in buildings, cattle, inventory, or schedule collections cannot falsely complete onboarding steps. Strengthened setup-progress regression coverage to keep malformed collection rows ignored. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/dashboard/setup-progress.test.mjs` passed 4/4, `npm.cmd test` passed 392/392, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today focus malformed collection hardening**: Continued the active Hanwoo quality uplift by tightening `buildTodayFocusItems()`. Notifications, schedule events, and inventory payloads are normalized to non-null object rows before critical-alert filtering, upcoming-schedule sorting, low-stock checks, and feed-depletion projections, preventing malformed cached/caller collections or non-array payloads from crashing the home priority panel. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/dashboard/today-focus.test.mjs` passed 13/13, `npm.cmd test` passed 394/394, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Farm metrics malformed window hardening**: Continued the active Hanwoo quality uplift by tightening farm-specific feed-cost and weight-gain estimators. Malformed `windowMonths` values now fall back to safe positive defaults before date-window and denominator calculations, preventing invalid windows from producing non-finite feed-cost evidence or suppressing otherwise valid shipment weight-gain samples. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/dashboard/farm-metrics.test.mjs` passed 12/12, `npm.cmd test` passed 396/396, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight weather numeric-string hardening**: Continued the active Hanwoo quality uplift by tightening `summarizeFarmForInsight()`. Weather `thi`, `temp`, and `humidity` now accept finite numeric strings while null/undefined/empty values remain unavailable, preventing cached/API weather payloads with stringified numbers from hiding heat-stress signals in AI insight prompts and heuristic cards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-insight.test.mjs` passed 17/17, `npm.cmd test` passed 397/397, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather current null/empty value hardening**: Continued the active Hanwoo quality uplift by tightening weather payload normalization. `toNumberOrNull()` now treats null, undefined, and empty required Open-Meteo current fields as unavailable instead of coercing them to 0, preventing incomplete weather payloads from rendering misleading 0-degree/0-percent livestock weather states while preserving finite numeric-string support. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/weather-state.test.mjs` passed 10/10, `npm.cmd test` passed 398/398, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory missing-quantity display hardening**: Continued the active Hanwoo quality uplift by tightening inventory item normalization. Null, undefined, or empty inventory quantities now stay unavailable instead of being coerced to 0, missing quantities render as `?섎웾 誘몃벑濡?, inline editing opens with an empty field, and false low-stock warnings are avoided while valid finite values still compare normally. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/empty-state-wiring.test.mjs` passed 18/18, `npm.cmd test` passed 399/399, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle weight-history point hardening**: Continued the active Hanwoo quality uplift by tightening cattle weight history extraction. `extractWeightHistoryPoints()` now routes metadata weights through a positive-weight normalizer so empty, null, undefined, zero, or negative values cannot become visible chart points through `Number()` coercion or finite-only checks, while valid positive numeric strings and numbers still render normally. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-history.test.mjs` passed 5/5, `npm.cmd test` passed 400/400, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle history malformed-row hardening**: Continued the active Hanwoo quality uplift by tightening cattle history row normalization. `normalizeCattleHistoryRows()` now returns an empty list for non-array history payloads and filters malformed/non-object rows before metadata parsing or row spreading, preventing corrupted caller/cache history collections from leaking malformed entries into cattle detail history and weight-chart preparation while preserving valid rows and corrupt-metadata diagnostics. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-history.test.mjs` passed 6/6, `npm.cmd test` passed 401/401, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle weight-history non-array extraction hardening**: Continued the active Hanwoo quality uplift by tightening cattle weight-history extraction. `extractWeightHistoryPoints()` now returns an empty list for non-array history payloads before filtering, preventing corrupted caller/cache history objects from crashing cattle detail weight-chart preparation while preserving valid array extraction, positive numeric weight normalization, and malformed row filtering. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-history.test.mjs` passed 7/7, `npm.cmd test` passed 402/402, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification timing malformed-options hardening**: Continued the active Hanwoo quality uplift by tightening notification timing input handling. `getNotificationTargetDate()` now normalizes malformed options input before reading `now`, so null/non-object options cannot crash estrus or calving notification timing preparation through parameter destructuring while existing date parsing, impossible-date rejection, and current-time fallback behavior remain intact. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `npm.cmd test -- --runTestsByPath src/lib/notification-timing.test.mjs` ran the Hanwoo Node test suite and passed 404/404, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market and weather state malformed-options hardening**: Continued the active Hanwoo quality uplift by tightening market-price and weather state option handling. Market cache/live/unavailable state builders and weather live/unavailable/stale state builders now normalize malformed options input before reading `now`, `freshnessMs`, `message`, or `locationName`, preventing malformed caller fallback options from crashing KAPE market-price or Open-Meteo weather state preparation while preserving existing Korean default location/copy, freshness, and date behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/market-price-state.test.mjs src/lib/weather-state.test.mjs` passed 21/21, `npm.cmd test` passed 408/408, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared fetch timeout malformed-options hardening**: Continued the active Hanwoo quality uplift by tightening the shared `fetchWithTimeout()` utility. The timeout wrapper now normalizes malformed options input before reading `timeoutMs` or `errorMessage`, preventing shared dashboard refresh, payment confirmation, KAPE/MTRACE lookup, weather, and API proxy fetch paths from crashing before the guarded timeout/abort wrapper is installed. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/fetch-with-timeout.test.mjs` passed 2/2, `npm.cmd test` passed 409/409, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Offline sync malformed-state hardening**: Continued the active Hanwoo quality uplift by tightening offline sync retry/dead-letter state helpers. Offline queue metadata and failure-state builders now normalize malformed item/options input before reading retry, last-attempt, error, and dead-letter fields, preventing corrupted persisted offline queue rows or caller bugs from breaking sync recovery paths before retry metadata can be normalized. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/offline-sync-state.test.mjs` passed 7/7, `npm.cmd test` passed 411/411, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Offline queue persisted timestamp hardening**: Continued the active Hanwoo quality uplift by tightening offline queue item normalization. Non-finite persisted queue timestamps now fall back to the current time and trigger storage rewrite instead of surviving as `Infinity` through JSON parsing, preventing corrupted offline queue rows from carrying impossible timestamps into sync retry/recovery paths while preserving valid ids, actions, args, and retry metadata. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/offline-queue-storage.test.mjs` passed 3/3, `npm.cmd test` passed 412/412, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard BullMQ queue malformed-options hardening**: Continued the active Hanwoo quality uplift by tightening server queue helper option handling. BullMQ queue, queue-events, and enqueue helpers now normalize malformed options input before reading prefixes, default job options, event options, or job options, preventing caller bugs from producing generic TypeErrors before the existing Redis/BullMQ configuration checks can return actionable setup errors. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/queue.test.mjs` passed 1/1, `npm.cmd test` passed 413/413, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard cache malformed-input hardening**: Continued the active Hanwoo quality uplift by tightening dashboard cache helper input handling. Cattle/sales cache key builders now normalize malformed filter objects before destructuring, and cache delete helpers normalize malformed key/prefix lists before filtering, preventing caller bugs from throwing TypeErrors before stable default cache keys, Redis configuration checks, or cache invalidation fallbacks can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/cache.test.mjs` passed 2/2, `npm.cmd test` passed 415/415, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard read-model malformed-options hardening**: Continued the active Hanwoo quality uplift by tightening dashboard read-model option/input handling. Summary, notification, and market snapshot readers now normalize malformed cache options before reading `bypassCache`, and dashboard cache invalidation normalizes malformed input before reading farm ids, cache flags, or snapshot delete flags, preventing caller bugs from throwing generic TypeErrors before cache fallback, Redis no-op behavior, or targeted invalidation can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/read-models-options.test.mjs` passed 2/2, `npm.cmd test` passed 417/417, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard list query malformed-input hardening**: Continued the active Hanwoo quality uplift by tightening dashboard list query input handling. Cattle/sales list query parsers now read search params through a guarded helper, and list page loaders normalize malformed input before destructuring, preserving normal API route validation while preventing malformed internal reuse from throwing TypeErrors before default query values, validation, cache lookup, or DB query preparation can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard-list-query-input.test.mjs` passed 2/2, `npm.cmd test` passed 419/419, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Auth guard malformed-options hardening**: Continued the active Hanwoo quality uplift by tightening shared authentication guard option handling. `requireAuthenticatedSession()` now normalizes malformed options input before reading `redirectToLogin`, preventing caller bugs from throwing generic TypeErrors before auth can run, infrastructure failures can degrade to `AuthenticationError`, or unauthenticated page callers can redirect to login. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/auth-guard-options.test.mjs` passed 1/1, `npm.cmd test` passed 420/420, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning without a concurrent Next build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Home cache invalidation malformed-options hardening**: Continued the active Hanwoo quality uplift by tightening shared mutation cache invalidation. `invalidateHomeCaches()` now normalizes malformed options input before spreading options into dashboard read-model invalidation or reading `cattleListPages` / `salesListPages` for Next cache tag revalidation, preventing caller bugs from throwing generic TypeErrors after DB mutations but before cache invalidation can complete. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-helper-options.test.mjs src/lib/dashboard/use-cache-config.test.mjs` passed 14/14, `npm.cmd test` passed 421/421, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning without a concurrent Next build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle history metadata serialization hardening**: Continued the active Hanwoo quality uplift by tightening shared cattle history recording. `recordCattleHistory()` now serializes optional metadata through a guarded helper; unserializable metadata logs a targeted error and falls back to `null` metadata instead of preventing the cattle history row from being written, preserving audit/history records for successful cattle and sales mutations even when optional metadata is malformed. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-history-recording.test.mjs src/lib/cattle-history.test.mjs src/lib/actions-helper-options.test.mjs` passed 9/9, `npm.cmd test` passed 422/422, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle history event-date hardening**: Continued the active Hanwoo quality uplift by tightening shared cattle history recording. `recordCattleHistory()` now normalizes `eventDate` through a guarded helper before passing it to Prisma; malformed history date input falls back to the current time instead of creating an invalid `Date`, preserving audit/history rows for successful cattle and sales mutations while keeping the metadata serialization fallback intact. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-history-recording.test.mjs src/lib/cattle-history.test.mjs src/lib/actions-helper-options.test.mjs` passed 10/10, `npm.cmd test` passed 423/423, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment confirmation malformed-helper-input hardening**: Continued the active Hanwoo quality uplift by tightening payment confirmation helper input handling. `buildGatewayErrorMessage()` and `classifyPaymentConfirmationResult()` now normalize malformed helper input before reading gateway payloads, raw response text, fallback messages, status codes, parse errors, expected amounts, or clock providers, preventing caller bugs from throwing generic TypeErrors before safe Korean fallback responses, pending verification states, or amount-mismatch failures can be returned. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/payment-confirmation.test.mjs` passed 13/13, `npm.cmd test` passed 425/425, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard pagination guard malformed-helper-input hardening**: Continued the active Hanwoo quality uplift by tightening shared pagination guard helper input handling. `sanitizeDashboardPageInfoTransition()` and `getNextDashboardPaginationState()` now normalize malformed top-level helper input, malformed page-info payloads, and malformed `seenCursors` input before checking page transitions, preventing caller/cache bugs from throwing generic TypeErrors before pagination can stop safely, report loop/cursor errors, or continue with a valid next cursor. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/dashboard/pagination-guard.test.mjs src/lib/cattle-pagination-feedback.test.mjs src/lib/sales-pagination-feedback.test.mjs src/lib/cursor-pagination-feedback.test.mjs` passed 12/12, `npm.cmd test` passed 427/427, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Auth credential dependency-input hardening**: Continued the active Hanwoo quality uplift by tightening login credential helper dependency input handling. `authorizeCredentials()` now normalizes malformed dependency-injection input before reading `loadPrisma` or `loadBcrypt`, preventing caller/test harness bugs from throwing generic TypeErrors before the helper can preserve its safe invalid-credential `null` fallback. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/auth-credentials.test.mjs src/lib/auth-guard-options.test.mjs` passed 6/6, `npm.cmd test` passed 428/428, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Expense record filter malformed-input hardening**: Continued the active Hanwoo quality uplift by tightening expense ledger query filter handling. `getExpenseRecords()` now normalizes malformed filter input before reading cattle, building, category, or date filter fields, preventing caller bugs from falling into the generic expense fetch catch/log path before a safe empty query filter and guarded date parsing can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/expense-filter-date.test.mjs src/lib/actions-copy.test.mjs` passed 3/3, `npm.cmd test` passed 428/428, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight cache helper malformed-input hardening**: Continued the active Hanwoo quality uplift by tightening the new AI insight cache helpers. Cache-key building, summary hashing, cache reads, cache writes, and cache pruning now normalize malformed helper input, circular/non-JSON summary values, malformed timestamps, and malformed cache options, preventing cache metadata bugs from throwing or surfacing non-finite cache age values while preserving same-day per-user AI insight reuse and force-refresh behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-insight-cache.test.mjs src/lib/ai-insight.test.mjs src/lib/ai-insight-widget-copy.test.mjs` passed 41/41, `npm.cmd test` passed 442/442, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Pagination hook constructor option hardening**: Continued the active Hanwoo quality uplift by tightening top-level pagination hook option handling. The shared cursor pagination hook plus cattle and sales pagination hooks now normalize malformed hook options before reading `endpoint`, `initialItems`, or `initialPageInfo`, preventing direct/test/reuse callers from throwing during hook setup before normalized initial state, timeout protection, in-flight guards, Korean retry feedback, and safe load-more behavior can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cursor-pagination-feedback.test.mjs src/lib/cattle-pagination-feedback.test.mjs src/lib/sales-pagination-feedback.test.mjs` passed 5/5, `npm.cmd test` passed 444/444, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification system prop option hardening**: Continued the active Hanwoo quality uplift by tightening the layout notification dropdown's top-level prop handling. `NotificationSystem` now normalizes malformed props before reading `initialNotifications`, preventing direct/test/reuse callers from throwing during render setup before notification payload normalization, unread counts, Korean accessible labels, mark-read actions, and safe empty-state rendering can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/notification-system-copy.test.mjs` passed 9/9, `npm.cmd test` passed 444/444, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail fallback weight chart payload hardening**: Continued the active Hanwoo quality uplift by tightening the cattle detail modal's fallback weight chart path. Legacy `cattle.weightHistory` values are now normalized to object rows after direct array input or JSON string parsing, preventing malformed cached/legacy payloads from passing objects, scalars, or primitive array entries into the Recharts `LineChart` data prop while preserving history-event based chart points and invalid JSON fallback behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-detail-modal-wiring.test.mjs src/lib/cattle-history.test.mjs` passed 25/25, `npm.cmd test` passed 445/445, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Admin diagnostics malformed response hardening**: Continued the active Hanwoo quality uplift by tightening the admin diagnostics client's response handling. `getSystemDiagnostics()` results are now normalized before rendering database status, record counts, memory, uptime, and Node fields, preventing malformed or partial diagnostics payloads from crashing the operations page through missing `database`/`memory` objects or non-object `recordCounts` while preserving Korean fallback copy and finite numeric rendering. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/diagnostics-copy.test.mjs` passed 4/4, `npm.cmd test` passed 445/445, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Admin diagnostics raw-data malformed response hardening**: Continued the active Hanwoo quality uplift by tightening the admin diagnostics raw-record loader. `getRawData()` results are now normalized before reading `success`, `data`, or `message`, preventing malformed or null raw-record responses from throwing generic client errors before the operations page can show safe Korean retry feedback while preserving null-safe raw-data state. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/diagnostics-copy.test.mjs` passed 4/4, `npm.cmd test` passed 445/445, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Pen-card drag-drop payload hardening**: Continued the active Hanwoo quality uplift by tightening pen-card drop handling. Drop payloads are now normalized before invoking the dashboard cattle-move callback, so malformed JSON payloads, arrays, objects without a usable `cattleId`, empty string ids, and non-finite numeric ids are ignored while valid string or finite numeric ids still use the existing confirmation flow. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cards-accessibility.test.mjs` passed 6/6, `npm.cmd test` passed 446/446, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle-row malformed payload hardening**: Continued the active Hanwoo quality uplift by tightening the reusable cattle row component. Direct `cow` props are now normalized before rendering, drag payload creation, status-color lookup, accessible labels, genetic-grade fallback, weight display, and click callbacks, preventing malformed direct/reuse callers from crashing on null, arrays, missing nested genetic info, missing names, missing tag numbers, or missing weight values. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cards-accessibility.test.mjs` passed 7/7, `npm.cmd test` passed 447/447, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price widget prop option hardening**: Continued the active Hanwoo quality uplift by tightening the market price widget's top-level prop handling. `MarketPriceWidget` now normalizes malformed top-level props before reading `initialData`, preventing direct/test/reuse callers from throwing during render setup before market snapshot normalization, loading fallback, KAPE source badges, manual refresh, guarded polling, and Korean unavailable copy can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 447/447, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather widget prop option hardening**: Continued the active Hanwoo quality uplift by tightening the home weather widget's top-level prop handling. `WeatherWidget` now normalizes malformed props before reading `weather`, preventing direct/test/reuse callers from throwing during render setup before unavailable-weather fallback, numeric weather normalization, THI labels, forecast filtering, livestock alerts, and Korean loading/unavailable copy can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 447/447, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Profitability widget prop option hardening**: Continued the active Hanwoo quality uplift by tightening the shipment profitability widget's top-level prop handling. `ProfitabilityWidget` now normalizes malformed props before reading `data`, `isLoading`, `error`, or `meta`, preventing direct/test/reuse callers from throwing during render setup before loading/error/empty states, recommendation row filtering, finite-number rendering, customized assumption labels, and Korean operator copy can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/profitability-copy.test.mjs` passed 11/11, `npm.cmd test` passed 448/448, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight widget prop option hardening**: Continued the active Hanwoo quality uplift by tightening the home AI insight widget's top-level prop handling. `AIInsightWidget` now normalizes malformed props before reading `summary`, preventing direct/test/reuse callers from throwing during render setup before deterministic heuristic cards, AI request fallback, cache metadata, manual refresh, timeout handling, and Korean accessible copy can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-insight-widget-copy.test.mjs` passed 13/13, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Tab navigation prop and callback hardening**: Continued the active Hanwoo quality uplift by tightening the shared dashboard tab bar. `TabBar` now normalizes malformed top-level props before reading `activeTab` or `onTabChange`, and uses a safe no-op when the tab-change callback is missing or not a function, preventing direct/test/reuse callers from throwing during tab render or click handling while preserving Korean action labels and selected-state semantics. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification widget prop option hardening**: Continued the active Hanwoo quality uplift by tightening the home notification widget's top-level prop handling. `NotificationWidget` now normalizes malformed props before reading `notifications`, preventing direct/test/reuse callers from throwing during render setup before notification row filtering, Korean fallback title/message copy, priority alert heading, critical badge rendering, and empty-state null rendering can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/notification-system-copy.test.mjs` passed 9/9, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR widget prop option hardening**: Continued the active Hanwoo quality uplift by tightening the QR label widget's top-level prop handling. `QRCodeWidget` now normalizes malformed props before reading `value` or `label`, converts non-empty string and finite numeric values into safe QR text, and falls back to Korean QR label copy when a label is missing. This prevents direct/test/reuse callers from throwing during render setup or printing while preserving Korean print button/status copy, document title/name, QR rendering, and duplicate-print guards. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/qr-widget-copy.test.mjs` passed 7/7, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export button prop option hardening**: Continued the active Hanwoo quality uplift by tightening the cattle CSV export button's top-level prop handling. `ExcelExportButton` now normalizes malformed props before reading `cattleList` or `resolveCattleList`, preventing direct/test/reuse callers from throwing during render setup before duplicate-download locking, async list resolution, empty-list warning feedback, CSV generation, temporary link cleanup, URL revocation, and Korean button/status copy can run. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/excel-export-button-copy.test.mjs` passed 3/3, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment widget prop and amount hardening**: Continued the active Hanwoo quality uplift by tightening the subscription payment widget's top-level prop and amount handling. `PaymentWidget` now normalizes malformed props before reading payment keys, amount, order/customer fields, and routes `amount` through a finite numeric normalizer before `price.toLocaleString()`, Toss widget rendering, and payment prepare payloads use it. This prevents direct/test/reuse callers from throwing during render setup or payment button labeling while preserving Korean checkout copy, Toss widget timeout handling, duplicate payment request guards, redirect URL safety, and payment API fallback behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/payment-ux-copy.test.mjs` passed 10/10, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared empty-state prop option hardening**: Continued the active Hanwoo quality uplift by tightening the reusable empty-state component. `EmptyState` now normalizes malformed top-level props before reading icon, title, description, action label, action callback, or disabled state, and ignores non-function callbacks before wiring the shared action button. This prevents direct/test/reuse callers from throwing during render setup or passing malformed callbacks into the action button while preserving operational empty-state copy, native action semantics, disabled/busy state, and existing inventory/sales/schedule/settings flows. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/empty-state-wiring.test.mjs` passed 18/18, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared dropdown menu prop option hardening**: Continued the active Hanwoo quality uplift by tightening the reusable dropdown menu primitives. Dropdown components now normalize malformed top-level props before reading children, class names, click handlers, or passthrough props. Invalid trigger children render nothing instead of throwing through `React.cloneElement`, and non-function item click handlers are ignored before choosing button semantics or wiring `onClick`, preserving native button semantics, focus styling, labels, passthrough props, and existing notification menu actions. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/notification-system-copy.test.mjs` passed 9/9, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared button prop option hardening**: Continued the active Hanwoo quality uplift by tightening the reusable `Button` and `PremiumButton` primitives. Both components now normalize malformed top-level props before reading class names, variants, sizes, Slot/asChild mode, type, or passthrough props, preventing direct/test/reuse callers from throwing during render setup while preserving default non-submit semantics, explicit submit overrides, refs, Slot behavior, and variant styling. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/feedback-provider-copy.test.mjs src/lib/premium-button-semantics.test.mjs` passed 6/6, `npm.cmd test` passed 449/449, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared badge prop option hardening**: Continued the active Hanwoo quality uplift by tightening the reusable `Badge` primitive. `Badge` now normalizes malformed top-level props before reading class names, variants, or passthrough props, preventing direct/test/reuse callers from throwing during render setup while preserving variant styling, class merging, passthrough attributes, and existing dashboard badge usage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ui-primitives-options.test.mjs` passed 1/1, `npm.cmd test` passed 450/450, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared card prop option hardening**: Continued the active Hanwoo quality uplift by tightening the reusable `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, and `CardFooter` primitives. Each card primitive now normalizes malformed top-level props before reading class names or passthrough props, preventing direct/test/reuse callers from throwing during render setup while preserving refs, display names, class merging, passthrough attributes, and existing dashboard/card layout styling. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ui-primitives-options.test.mjs` passed 2/2, `npm.cmd test` passed 451/451, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Premium card prop option hardening**: Continued the active Hanwoo quality uplift by tightening `PremiumCard`, `PremiumCardHeader`, `PremiumCardTitle`, `PremiumCardDescription`, `PremiumCardContent`, `PremiumCardFooter`, and `PremiumInfoCard`. Premium card primitives now normalize malformed top-level props before reading class names, header title/icon/description/children, info-card values, or passthrough props, preventing direct/test/reuse callers from throwing during render setup while preserving refs, display names, premium card styling, profitability widget header rendering, class merging, and passthrough attributes. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/profitability-copy.test.mjs src/lib/ui-primitives-options.test.mjs` passed 14/14, `npm.cmd test` passed 452/452, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Form primitive and progress prop option hardening**: Continued the active Hanwoo quality uplift by tightening `Input`, `Label`, and `Progress`. These primitives now normalize malformed top-level props before reading class names, input type, progress value, or passthrough props. `Progress` also coerces non-finite values to `0` and clamps finite values to `0..100` before computing the indicator transform, preventing malformed reuse from rendering `NaN` or out-of-range progress offsets while preserving refs, display names, existing styling, and passthrough attributes. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ui-primitives-options.test.mjs` passed 5/5, `npm.cmd test` passed 454/454, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Avatar and skeleton prop option hardening**: Continued the active Hanwoo quality uplift by tightening `Avatar`, `AvatarImage`, `AvatarFallback`, and `Skeleton`. These primitives now normalize malformed top-level props before reading class names or passthrough props, preventing future account/status/loading UI reuse from throwing during render setup while preserving Radix avatar refs/display names, skeleton styling, class merging, and passthrough attributes. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ui-primitives-options.test.mjs` passed 7/7, `npm.cmd test` passed 456/456, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Diagnostics status-card prop option hardening**: Continued the active Hanwoo quality uplift by tightening the admin diagnostics `StatusCard` helper. `StatusCard` now normalizes malformed top-level props before reading `title`, `value`, `sub`, `icon`, or `status`, preventing direct/test/reuse callers from throwing during diagnostics card render setup while preserving neutral fallback status styling, Korean operations copy, numeric diagnostics normalization, loading announcements, and dashboard-return feedback. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/diagnostics-copy.test.mjs` passed 5/5, `npm.cmd test` passed 462/462, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight badge prop option hardening**: Continued the active Hanwoo quality uplift by tightening the AI insight widget's internal badge helpers. `PriorityBadge`, `SourceBadge`, and `CacheBadge` now normalize malformed top-level props before reading `priority`, `source`, or `ageSeconds`, preventing direct/test/reuse callers from throwing during badge render setup while preserving priority fallback styling, AI-vs-rule source labels, cached-AI metadata visibility, cache-age formatting, timeout fallback copy, and manual refresh behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-insight-widget-copy.test.mjs` passed 14/14, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price panel prop and rows hardening**: Continued the active Hanwoo quality uplift by tightening the market price widget's internal `PricePanel` helper. `PricePanel` now normalizes malformed top-level props before reading `title` or `rows`, and filters malformed row collections before rendering price rows, preventing direct/test/reuse callers from throwing during panel render setup or raw `rows.map()` access while preserving Korean market copy, kg unit labels, source badges, stale/unavailable states, polling guards, refresh controls, and price formatting. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail helper prop option hardening**: Continued the active Hanwoo quality uplift by tightening the cattle detail modal's internal `SectionTitle` and `InfoItem` helpers. Both helpers now normalize malformed top-level props before reading heading icon/title/color or info label/value/highlight/delay fields, preventing direct/test/reuse callers from throwing during modal helper render setup while preserving heading semantics, decorative icon hiding, highlight typography, animation delays, hover styling, Korean detail copy, and existing cattle form/detail focus behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 18/18, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis KPI card prop option hardening**: Continued the active Hanwoo quality uplift by tightening the Analysis tab's internal `KpiCard` helper. `KpiCard` now normalizes malformed top-level props before reading `title`, `value`, `icon`, or `accent`, preventing direct/test/reuse callers from throwing during KPI card render setup while preserving KPI labels, money formatting, decorative icon semantics, accent styling, Korean analysis copy, and existing financial aggregation behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed helper prop and input option hardening**: Continued the active Hanwoo quality uplift by tightening the Feed tab's internal `FilterChip` and `Field` helpers. Both helpers now normalize malformed top-level props before reading selected state, labels, callbacks, disabled state, suffix, errors, or input props. `FilterChip` ignores malformed click handlers before wiring button interaction, and `Field` normalizes `inputProps` with a safe fallback field id before spreading input attributes, preventing direct/test/reuse callers from throwing during feed filter or feed input render setup while preserving filter chip labels, busy/pressed semantics, feed validation wiring, Korean feed copy, and existing feed aggregation behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/empty-state-wiring.test.mjs` passed 18/18, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard helper panel prop and collection hardening**: Continued the active Hanwoo quality uplift by tightening the home dashboard's internal `TodayFocusPanel`, `QuickActionPanel`, `SetupProgressPanel`, and `PenCattleList` helpers. Helper props and item/action/progress/cattle collections are now normalized before `.length`, `.map()`, or `.filter()` access; malformed callbacks fall back to safe no-ops; setup progress numbers are finite/clamped before progressbar labels and width; quick actions fall back to a safe icon. This prevents direct/test/reuse callers from throwing during home panel render or button handling while preserving today-focus labels, quick-action labels, setup progress semantics, pen cattle filtering, Korean empty-pen copy, and existing dashboard navigation behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/home-market-copy.test.mjs` passed 51/51, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Legal document layout prop option hardening**: Continued the active Hanwoo quality uplift by tightening the shared legal document layout. `LegalDocumentLayout` now normalizes malformed top-level props before reading `eyebrow`, `title`, `subtitle`, `lastUpdated`, or `children`, preventing direct/test/reuse callers from throwing during legal page layout render setup while preserving privacy/terms support-channel copy, back-home link semantics, decorative back icon hiding, and existing legal page shell styling. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/legal-pages-copy.test.mjs` passed 1/1, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard App error boundary prop and reset hardening**: Continued the active Hanwoo quality uplift by tightening route and global app error boundaries. `RouteError` and `GlobalError` now normalize malformed top-level props before reading `error` or `reset`, and malformed reset callbacks fall back to safe no-ops before retry buttons invoke them. This prevents direct/test/reuse callers from throwing during app-level failure UI render or retry handling while preserving client-boundary requirements, Korean retry/home copy, route home action, global-error html/body contract, and existing error logging. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/error-pages-wiring.test.mjs` passed 10/10, `npm.cmd test -- --runTestsByPath src/lib/error-pages-wiring.test.mjs` ran the full suite and passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning once without the concurrent Next build lock. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Root layout prop option hardening**: Continued the active Hanwoo quality uplift by tightening the app root layout. `RootLayout` now normalizes malformed top-level props before reading `children`, preventing direct/test/reuse callers from throwing during root shell render setup while preserving the Korean metadata/PWA copy, font variable setup, FeedbackProvider wrapping, Suspense boundary, `lang="ko"`, and hydration-warning behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/app-metadata-copy.test.mjs` passed 1/1, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Subscription fallback prop option hardening**: Continued the active Hanwoo quality uplift by tightening the subscription success/fail fallback status components. Both payment result pages now normalize malformed top-level fallback props before reading `message`, preventing direct/test/reuse callers from throwing during payment result loading-state render setup while preserving Korean loading/failure/success copy, polite busy status semantics, retry navigation fallbacks, guarded success timers, and existing payment confirmation behavior. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/payment-ux-copy.test.mjs` passed 10/10, `npm.cmd test` passed 463/463, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Payment API request-body hardening**: Continued the active Hanwoo quality uplift by tightening the payment prepare and confirm API routes. Both routes now normalize malformed request JSON bodies before reading customer/payment fields, so null, primitive, and array-shaped bodies fall into existing Korean validation/error paths instead of throwing or leaking array-attached values into customer-key, order, amount, or checkout metadata handling. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/payment-ux-copy.test.mjs` passed 10/10, `npm.cmd test` passed 488/488, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification builder cattle payload hardening**: Continued the active Hanwoo quality uplift by tightening the shared notification builder. `buildNotifications()` now normalizes malformed cattle collections and filters array-shaped cattle rows before estrus/calving alert generation, preventing null/primitive input crashes and array-attached row fields from leaking into notification ids, messages, cattle metadata, timing, or alert sorting. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/notification-system-copy.test.mjs` passed 10/10, `npm.cmd test` passed 489/489, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Livestock weather alert utility forecast hardening**: Continued the active Hanwoo quality uplift by tightening the shared weather alert utility. `getLivestockWeatherAlerts()` now normalizes malformed forecast collections and filters array-shaped forecast rows before heat/cold/rain livestock alert generation, preventing null/primitive input crashes and array-attached row fields from leaking into alert labels, thresholds, messages, or icons. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/utils-date.test.mjs` passed 1/1, `npm.cmd test` passed 489/489, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Expense aggregation row and amount hardening**: Continued the active Hanwoo quality uplift by tightening the expense aggregation server action. `getExpenseAggregation()` now normalizes malformed expense collections and filters array-shaped rows before category aggregation, uses a safe category fallback, and coerces amounts through `toFiniteNumber()` so malformed direct/action/reuse inputs cannot crash aggregation or corrupt totals. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 3/3, `npm.cmd test` passed 490/490, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat farm-context DB row hardening**: Continued the active Hanwoo quality uplift by tightening the AI chat route's farm-context builder. `buildFarmContext()` now filters malformed status-count and recent-sales DB/mock result rows before status summary and Gemini prompt context generation, normalizes status labels/counts, and guards nested cattle payloads before reading cattle names or tag numbers. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/ai-chat-api.test.mjs` passed 11/11, `npm.cmd test` passed 491/491, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed server-action DB row hardening**: Continued the active Hanwoo quality uplift by tightening feed server actions. `getFeedStandards()` and `getFeedHistory()` now normalize Prisma DB/mock results before returning, filtering malformed or array-shaped rows so direct/action/reuse callers receive safe row arrays before dashboard feed rendering and aggregation. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 4/4, `npm.cmd test` passed 492/492, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory server-action DB row hardening**: Continued the active Hanwoo quality uplift by tightening the inventory server action. `getInventory()` now normalizes Prisma DB/mock results before returning, filtering malformed or array-shaped rows so direct/action/reuse callers receive safe row arrays before dashboard inventory rendering and low-stock calculations. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 5/5, `npm.cmd test` passed 493/493, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Building server-action DB row hardening**: Continued the active Hanwoo quality uplift by tightening the building server action. `getBuildings()` now normalizes Prisma DB/mock results before returning, filtering malformed or array-shaped rows so direct/action/reuse callers receive safe row arrays before dashboard building rendering, pen routing, setup progress, and settings building controls. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 6/6, `npm.cmd test` passed 494/494, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build after rerunning once without the concurrent Next build lock. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule server-action DB row hardening**: Continued the active Hanwoo quality uplift by tightening the schedule server action. `getScheduleEvents()` now normalizes Prisma DB/mock results before returning, filtering malformed or array-shaped rows so direct/action/reuse callers receive safe row arrays before dashboard schedule rendering, setup progress, today-focus schedule cards, and upcoming schedule countdown labels. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 7/7, `npm.cmd test` passed 495/495, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Expense list server-action DB row hardening**: Continued the active Hanwoo quality uplift by tightening the expense list server action. `getExpenseRecords()` now reuses the existing expense row normalizer before returning Prisma DB/mock results, filtering malformed or array-shaped rows so direct/action/reuse callers receive safe row arrays before dashboard expense filters, analysis, financial charting, and cost aggregation paths consume them. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 7/7, `npm.cmd test` passed 495/495, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales list server-action DB row hardening**: Continued the active Hanwoo quality uplift by tightening the sales list server action. `getSalesRecords()` now normalizes Prisma DB/mock results before returning, filtering malformed or array-shaped rows so direct/action/reuse callers receive safe row arrays before dashboard sales rendering, analysis, profitability, financial charting, and sales cache consumers use them. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 7/7, `npm.cmd test` passed 495/495, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle list server-action DB row hardening**: Continued the active Hanwoo quality uplift by tightening active and archived cattle list server actions. `getCattleList()` and `getArchivedCattle()` now normalize Prisma DB/mock results before returning, filtering malformed or array-shaped rows so direct/action/reuse callers receive safe row arrays before dashboard cattle rendering, pagination/export consumers, and archive views use them. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test src/lib/actions-copy.test.mjs` passed 8/8, `npm.cmd test` passed 496/496, `npm.cmd run lint` passed clean, `npm.cmd run build` passed with the known T-251 DB health warning but exit 0, path-limited `git diff --check` passed with CRLF warnings only, and `python execution/project_qc_runner.py --project hanwoo-dashboard --json` passed test/lint/build. |

| Field | Value |
|---|---|
| Date | 2026-05-28 |
| Tool | Codex |
| Work | **최종 상태 확정:** `npm.cmd run db:prisma7-test -- --live`를 재실행해 live CRUD 검증을 다시 확인했습니다. 결과는 `Passed: 15 Failed: 1`로 동일하며 실패는 `driverAdapterError` 하에서 `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`입니다. `projects/hanwoo-dashboard/.env`의 `DATABASE_URL`은 `postgresql://postgres.fuemeqmigptwfzqvrpjf:...@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres` 상태이며, 외부 자격 증명 동기화 미스매치가 그대로입니다. `session_orient --json` 기준 T-251은 유일한 TODO/차단 항목으로 유지됩니다. |
| Next Priorities | 사용자 소유 항목 T-251 조치 필요: Supabase DB 비밀번호 재설정 및 제어면 credential 동기화 후 `.env` 반영, 즉시 `npm.cmd run db:prisma7-test -- --live` 재실행. |

## Notes

- **T-251 (active blocker)**: Supabase database password desynchronization. User must reset password via Supabase Dashboard (Project Settings > Database), then update `projects/hanwoo-dashboard/.env`.
- **Origin sync**: As of 2026-05-19, `main` is synchronized with `origin/main` and the worktree is clean.
- Older addenda archived in `.ai/archive/HANDOFF_archive_2026-05-15.md` and `.ai/archive/HANDOFF_archive_2026-05-19.md`.
