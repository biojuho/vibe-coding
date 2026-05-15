## Rotation 2026-05-15 (archived addenda older than 2026-05-08)

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
