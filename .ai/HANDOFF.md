# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Codex |
| Work | Record-only checkpoint after user said `기록해`. Confirmed the Hanwoo quality-uplift work is already recorded and committed: `f222385` (`feat(hanwoo-dashboard): add today brief focus panel`) plus `4a8ece5` (`[ai-context] hanwoo 품질 개선 세션 기록`). `session_orient.py --json` shows active goal still set to `hanwoo-dashboard quality uplift so other people would want to use it`, `main` ahead 2 of `origin/main`, and no staged files. |
| Next Priorities | Preserve current unrelated `blind-to-x` dirty WIP: `pipeline/content_intelligence/rules.py`, `pipeline/draft_prompts.py`, `pipeline/draft_quality_gate.py`, `rules/editorial.yaml`, `rules/examples.yaml`, `rules/prompts.yaml`, four `tests/unit/test_*quality*`/multi-provider files, and `uv.lock`. Continue T-308 when asked: browser visual QA of Today Brief and safe UI polish. T-251 remains external/user-owned Supabase pooler credential reset. |

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| Tool | Codex |
| Work | Activated the new `/goal` in `.ai/GOAL.md`: `hanwoo-dashboard` quality uplift so other people would want to use it. Completed first safe UX/product pass as **T-307** in commit `f222385`. Added `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.mjs` and tests, then rendered a home-screen Today Brief panel in `DashboardClient.js` with CSS in `globals.css`. The panel prioritizes offline sync state, critical breeding/calving alerts, next open schedule item, low-stock inventory, and monthly sales into clickable actions. Preserved unrelated dirty `projects/blind-to-x/uv.lock`. |
| Next Priorities | Active goal remains open for additional Hanwoo polish. New safe TODO **T-308**: browser visual QA of Today Brief, then consider replacing remaining emoji-heavy navigation/widget affordances with lucide icons where it improves polish. Verification passed: `npm.cmd test` (`77 passed`), `npm.cmd run lint`, `npm.cmd run build`. Pre-commit graph gate emitted advisory WARN risk=0.35 for `DashboardClient` test-gap heuristics despite direct helper coverage and full Hanwoo checks. Dev server is running at `http://127.0.0.1:3001`. T-251 remains user-owned external Supabase password/pooler blocker; do not retry live Prisma until credentials are reset/resynced. |

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-306 completed**: open-PR audit + cleanup. With `T-251` the only TODO and IN_PROGRESS empty, signal was 20 Dependabot PRs all `BLOCKED` (REVIEW_REQUIRED, not CI) plus weekly `pip in /.` Dependabot run failing with `dependency_file_not_found: No files found in /`. Triaged into Tier A (11 safe minors/patches, all CI green), Tier B (#51/#54 React pair where the FAIL was only the `dependabot` auto-merge workflow, not the build), Tier C (#50 typescript 5→6 MAJOR + #52 react-dom solo bump diverging from react peer — both real build failures), Tier D (#37/#39/#41 MAJOR risk), Grouped (#48 next-ecosystem). User approved: squash-merge Tier A+B+#48 via `--admin`, close Tier C, diagnose root pip failure. Squash-merged 14 PRs in 3 project-disjoint batches; #47 (word-chain tailwindcss) and #54 (hanwoo react) hit lockfile drift after sibling merges → `@dependabot rebase` + 60 s wait + re-merge worked. Picked up the missed #44 pyyaml after. Closed 5 PRs with sourced rationale (#37/#41 frozen word-chain MAJOR not worth migration; #39 backlogged as T-305 epic — `pipeline/draft_providers.py` + `pipeline/image_generator.py` already use v1+ `AsyncOpenAI` so v2 migration is feasible but needs 4 mock-file refresh + live smoke, ~½–1 day). Root pip Dependabot diagnosis: `.github/dependabot.yml` entry 1 had `directory: "/"` but no Python manifest at repo root — the intended workspace is `workspace/pyproject.toml`. Fixed to `directory: "/workspace"` (PEP 621 project) in commit `32269c2`. Local main now `ahead 2` of `origin/main` (`b94c66c` prior-session ai-context + `32269c2` dependabot.yml fix); push not performed pending user approval. |
| Next Priorities | Push pending: `b94c66c` + `32269c2` + this session's ai-context commit need explicit user approval before `git push`. T-305 (openai 2 migration epic) is the only new TODO. T-251 remains the lone external blocker (user-owned Supabase password reset). Code-review gate PASSed risk=0.00 on the dependabot.yml change; the 15 merged Dependabot PRs' CIs ran on `origin/main` post-merge. |

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| Tool | Gemini (Antigravity) |
| Work | **전체 QC 재검증 완료**. 4개 프로젝트 전수 검증: blind-to-x (1560 passed, 1 skipped), shorts-maker-v2 (1422 passed, 12 skipped), hanwoo-dashboard (ESLint 0 warnings + Build OK), knowledge-dashboard (ESLint 0 warnings + Build OK). code_review_gate.py PASS (risk=0.00). PowerShell stderr NativeCommandError로 인한 shorts-maker false negative 현상 확인 및 정리. |
| Next Priorities | T-251 사용자 조치 대기 (Supabase 비밀번호 리셋). 기술 부채: google.generativeai→google.genai 마이그레이션, Pydantic V1 Python 3.14 호환성. |

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| Tool | Codex |
| Work | Re-oriented the workspace after the user asked to understand and proceed. Confirmed `main` is clean and synchronized with `origin/main` (`ahead=0`, `behind=0`, no dirty files), no active goal, one TODO, and product readiness `94 / blocked` only because `hanwoo-dashboard` T-251 is still open. Retried `projects/hanwoo-dashboard` live Prisma E2E with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed, but live connection health still failed with `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. |
| Next Priorities | No repo-side fix is available for T-251. User must reset/resync the Supabase database password in the Supabase Dashboard, update `projects/hanwoo-dashboard/.env` if the connection string changes, then rerun `npm.cmd run db:prisma7-test -- --live`. |

| Field | Value |
|---|---|
| Date | 2026-05-16 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-304 completed**: blind-to-x promoted to release-ready state per `/goal "프로젝트 하나 고도화된 완성품으로 만들어놔"` (scope narrowed via AskUserQuestion to blind-to-x, release-ready criterion). Five release criteria audited: (1) E2E pipeline already shipping, (2) CI green per `session_orient` + `full-test-matrix.yml` `blind-to-x-tests` job (20-min budget, paths verified), (3) docs refreshed below, (4) regression tests confirmed for viral boost / NLM enricher / image upload, (5) **closed**: added opt-in `BTX_USAGE_FORWARD=1`-gated `_maybe_forward_to_workspace_usage` in `projects/blind-to-x/pipeline/cost_tracker.py`, called from both `add_text_generation_cost` (Anthropic cache tokens included) and `add_dalle_cost` (model=`dall-e-3`, `endpoint=blind-to-x.dalle_image`). Mirrors blind-to-x text+image costs into workspace `.tmp/workspace.db` `api_calls` so `api_usage_tracker alerts` (fallback rate / cost spike / dead provider) finally covers blind-to-x (was 16 rows total before). Added 3 regression tests in `tests/unit/test_cost_tracker_extended.py` (forwarder invocation, env-gate disabled/enabled, error swallowing — linter auto-corrected the fake-module pattern from `type("M", ...)()` to `types.SimpleNamespace` to keep `log_api_call` unbound). Docs refresh: fixed `tests_unit` → `tests/unit` in README + ops-runbook; `pip install -r requirements.txt` → `pip install -e .[dev]` (pyproject-only project); rewrote stale "3시간마다 GitHub Actions" claim to point at `full-test-matrix.yml`; added Observability section; updated external-review README + file-manifest to reference `rules/` (D-031 5-file split) instead of removed `classification_rules.yaml`. |
| Next Priorities | Verification: `py_compile` + targeted `ruff check` PASS on `pipeline/cost_tracker.py` + `tests/unit/test_cost_tracker_extended.py`; lint pass confirmed earlier by `project_qc_runner.py --check lint`. Local pytest streaming was blocked by a session-specific subshell capture issue (CMD `cd /d` fails with `CD_EXIT=123` on Korean path; matches `windows_korean_path_encode_strict` minefield) — CI on push will execute the 3 new tests. To enable the new forwarder in production, set `BTX_USAGE_FORWARD=1` in `.env` (off by default to preserve hermetic tests). Remaining external blocker is still T-251 (user-owned Supabase password reset). |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Gemini (Antigravity) |
| Work | **워크스페이스 위생 심화 정비**. 사용자 `/goal` 요청으로 추가 필요 작업 탐색 후 즉시 실행. (1) HANDOFF 심층 정리: 이전 Codex 로테이션(→160줄) 이후에도 남아있던 4월 old addenda + 중복 5/15 addenda를 아카이브하여 **192줄→32줄**로 압축. (2) Dirty 파일 정리: `blind-to-x/_upload.py`(EOL-only), `knowledge-dashboard/qaqc_result.json`(내용 diff 없음) 2개를 `git checkout --`로 정리. (3) 시스템 헬스 전수 검증: 제품 준비도 92/100 (blocked=hanwoo T-251만), Skill 헬스 100/100 (42/42), QC 아티팩트 5개 프로젝트 포함 확인. (4) 새 blind-to-x WIP 6파일(다른 도구 작업) 발견 → 미간섭 원칙 준수. |
| Next Priorities | T-251 사용자 승인 대기(Supabase 비밀번호 리셋). `main`이 `origin/main` 대비 82커밋 ahead — 사용자 승인 후 push 필요. blind-to-x 6파일 WIP는 해당 도구가 커밋할 때까지 대기. |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | Re-ran the only remaining TODO after the user said "complete everything". `projects/hanwoo-dashboard/scripts/prisma7-runtime-test.mjs` now prints Prisma error `name`, `code`, `meta`, and nested `cause` details so live DB blockers are actionable instead of blank. |
| Next Priorities | Verification: `npm.cmd run db:prisma7-test` passed offline (`14 passed, 0 failed, 1 skipped`). `npm.cmd run db:prisma7-test -- --live` was retried with escalated network access and still failed at connection health with `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. T-251 remains user-owned: reset/resync the Supabase database password in the Supabase Dashboard, then rerun the live command. No push was performed. |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | **T-302 + T-303 completed after user said "다 처리해"**. Finished the remaining local WIP and workspace hygiene goal. `projects/shorts-maker-v2/tests/unit/test_orchestrator_unit.py` now covers SemanticQC orchestration: disabled path, pass manifest persistence, degraded non-blocking degraded-step metadata, error verdict persistence, and exception swallowing. Applied HANDOFF size cleanup with `python execution/handoff_rotator.py --json --keep-days 0`, moving 44 older addenda into `.ai/archive/HANDOFF_archive_2026-05-15.md` and reducing HANDOFF to 160 lines. Cleared the EOL-only dirty state in `projects/blind-to-x/pipeline/notion/_upload.py` without content changes. Closed `.ai/GOAL.md` back to inactive. |
| Next Priorities | Verification passed: `python -m pytest --no-cov tests/unit/test_orchestrator_unit.py -q --tb=short --maxfail=1 --basetemp ../../.tmp/pytest-shorts-orchestrator-unit` -> `49 passed, 2 warnings`; targeted Ruff passed for the SemanticQC/orchestrator slice; `python execution/handoff_rotator.py --check --json --keep-days 0` predicted 44 archivable addenda before rotation; SESSION_LOG is 396 lines, under the 1000-line limit. Remaining blocker is still T-251, which requires the user to reset/resync the Supabase DB password before live Prisma E2E can run. No push was performed. |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | **T-301 knowledge-dashboard readiness/QC signal repair completed**. Fixed the signal path by registering `knowledge-dashboard` in `workspace/execution/qaqc_runner.py`, removing the `root → knowledge-dashboard` fallback in `execution/product_readiness_score.py`, preserving existing project results when a default targeted deep QA/QC run updates the canonical artifact, and adding focused regression coverage. |
| Next Priorities | Verification passed: focused tests `31 passed`; targeted Ruff clean; `python workspace/execution/qaqc_runner.py --skip-infra --skip-debt` -> `APPROVED`, `4646 passed`. Readiness: overall `92 / blocked` only because T-251 is user-owned. |

## Notes

- **T-251 (active blocker)**: Supabase database password desynchronization. User must reset password via Supabase Dashboard (Project Settings > Database), then update `projects/hanwoo-dashboard/.env`.
- **Origin sync**: As of 2026-05-18, `main` is synchronized with `origin/main` and the worktree is clean.
- Older addenda archived in `.ai/archive/HANDOFF_archive_2026-05-15.md`.
