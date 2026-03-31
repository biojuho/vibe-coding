# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for session-by-session detail and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Date | 2026-03-31 |
| Tool | Codex |
| Work | Ran a fresh full shared workspace QC pass and confirmed all active scopes remain green: `blind-to-x 560 passed / 16 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 1040 passed / 1 skipped`, total `2870 passed / 0 failed / 0 errors / 29 skipped`, `AST 20/20`, security `CLEAR (2 triaged issue(s))`, scheduler `6/6 Ready`, verdict `APPROVED`. |

### Previous Note

| Date | 2026-03-31 |
| Tool | Codex |
| Work | Re-ran `blind-to-x` project QC after the staged-pipeline cleanup and confirmed `APPROVED`: `560 passed / 0 failed / 16 skipped`, `AST 20/20`, security `CLEAR (2 triaged issue(s))`, scheduler `6/6 Ready`. |

## Current State

- Shared workspace QC latest rerun on `2026-03-31` is **`APPROVED`**: `blind-to-x 560 passed / 16 skipped`, `shorts-maker-v2 1270 passed / 12 skipped`, `root 1040 passed / 1 skipped`, total `2870 passed / 29 skipped`, `AST 20/20`, security `CLEAR (2 triaged issue(s))`, scheduler `6/6 Ready`.
- The 2 triaged security findings from the latest shared QC are both known false positives in `projects/blind-to-x/pipeline/cost_db.py`:
  - `f"SELECT * FROM {table}"` inside `archive_old_data()` only interpolates table names from the internal `_ARCHIVE_TABLES` frozenset; the date cutoff stays parameterized.
  - `f"DELETE FROM {table}"` inside `archive_old_data()` also only targets `_ARCHIVE_TABLES` members; the cutoff value stays parameterized.
- `projects/blind-to-x/pipeline/process.py` is now the active slim orchestrator again on `2026-03-30`, and the staged implementation lives behind `projects/blind-to-x/pipeline/process_stages/` with `projects/blind-to-x/pipeline/stages/` preserved as the compatibility import surface.
- `blind-to-x` public compatibility contracts are restored after the stage split:
  - `pipeline.process` again exposes `SPAM_KEYWORDS`, `extract_preferred_tweet_text`, `build_content_profile`, `build_review_decision`, and the legacy monkeypatch globals (`_ViralFilterCls`, `_sentiment_tracker`, `_nlm_enrich`) used by the unit suite.
  - `pipeline.commands.dry_run` and `pipeline.commands.reprocess` import paths work without touching callers.
  - Stage/runtime tests now rely on the clean `process_stages` code instead of the previously broken extraction artifacts.
- `blind-to-x` targeted regression bundle for the staged pipeline is green on `2026-03-30`: `33 passed` across `test_dry_run_filters.py`, `test_reprocess_command.py`, `test_pipeline_flow.py`, `test_cost_controls.py`, and `test_scrape_failure_classification.py`.
- `blind-to-x` latest project-only QC rerun on `2026-03-31` is **`APPROVED`**: `560 passed / 0 failed / 16 skipped`, `AST 20/20`, security `CLEAR (2 triaged issue(s))`, scheduler `6/6 Ready`.
- `workspace/execution/health_check.py` now boots correctly when run as a script and uses the canonical path contract: repo-root `.env` / `.tmp` / `CLAUDE.md` plus workspace-local `execution/` / `directives/`.
- `workspace/execution/code_evaluator.py` integrated into `graph_engine.py` for structured code evaluation (`is_approved`, `score`, `security_score`). If failed, generates explicit reflection feedback fed directly to `prepare_variants` (Optimizer loop). QA/QC fully passed.
- `blind-to-x` now has a reusable external-review kit for third-party LLM consultation:
  - Review docs live under `projects/blind-to-x/docs/external-review/`
  - The pack includes a project brief, share checklist, prompt templates, file manifest, and sanitized sample-case template
  - A local bundle of safe-to-share files was prepared at `.tmp/blind-to-x-external-review/` and zipped at `.tmp/blind-to-x-external-review.zip`
- `blind-to-x` now also has a first contract-cleanup slice from that review:
  - `projects/blind-to-x/pipeline/draft_contract.py` separates publishable drafts from auxiliary/review metadata
  - `DraftQualityGate`, `EditorialReviewer`, `draft_validator`, and `process.py` fact-check/readability loops now operate on publishable drafts only
  - `creator_take` is no longer required for draft-generation success; it remains optional reviewer metadata
  - Golden-example selection in `draft_generator.py` is now deterministic per input instead of random
  - The phased follow-up plan is documented in `projects/blind-to-x/docs/external-review/improvement-plan-2026-03-29.md`
- `blind-to-x` now also has a staged `process_single_post()` entrypoint:
  - `projects/blind-to-x/pipeline/process.py` routes the exported entrypoint through explicit `dedup`, `fetch`, `filter_profile`, `generate_review`, and `persist` stages
  - Process results include `stage_status` so failures and skips are tied to an explicit stage
  - `review_only=True` still overrides only the final-rank queue threshold so manual reviewer runs keep generating drafts, images, Notion rows, and draft analytics
  - Stage-module compatibility is now intentional: edit `pipeline/process_stages/` for behavior, and keep `pipeline/stages/` as the stable import bridge
- `blind-to-x` rule configuration is now mid-migration from the single `classification_rules.yaml` file to split source-of-truth files under `projects/blind-to-x/rules/`:
  - `projects/blind-to-x/pipeline/rules_loader.py` merges `classification.yaml`, `examples.yaml`, `prompts.yaml`, `platforms.yaml`, and `editorial.yaml`
  - Major runtime consumers now load rules through that shared loader instead of directly opening the legacy root YAML
  - `scripts/update_classification_rules.py` and `scripts/analyze_draft_performance.py` now target the split layout and regenerate the legacy snapshot when needed
- `shorts-maker-v2` package-wide verification remains at **91% total coverage** from the latest full-suite baseline (`1217 passed, 13 skipped, 1 warning`).
- Core `shorts-maker-v2` hotspot coverage remains strong:
  - `pipeline/script_step.py` **93%**
  - `pipeline/orchestrator.py` **97%**
  - `pipeline/render_step.py` **87%**
  - `pipeline/media_step.py` **90%**
  - `utils/dashboard.py` **97%**
  - `utils/style_tracker.py` **100%**
  - `providers/google_music_client.py` **99%**
  - `providers/pexels_client.py` **95%**
  - `providers/unsplash_client.py` **100%**
  - `render/video_renderer.py` **100%**
- `shorts-maker-v2` repeatability hardening already landed for MoviePy temp audio cleanup in [video_renderer.py](/c:/Users/박주호/Desktop/Vibe coding/projects/shorts-maker-v2/src/shorts_maker_v2/render/video_renderer.py).
- `shorts-maker-v2` thumbnail hardening now covers both output quality and run-to-run stability:
  - [thumbnail_step.py](/c:/Users/박주호/Desktop/Vibe coding/projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/thumbnail_step.py) no longer uses fixed-name temp artifacts for extracted frames or DALL-E / Gemini / Canva intermediates.
  - Temp artifact names now derive from the final thumbnail filename, so job-specific runs do not clobber each other in a shared output directory.
  - Long single-token titles now fall back to char-level wrapping instead of overflowing the thumbnail canvas.
  - The selected background path is passed through method calls instead of mutating shared instance state.
  - Canva download now fails fast on HTTP errors instead of silently writing an error body as if it were a PNG.
  - Targeted `coverage run` now shows `thumbnail_step.py` at **88%** in the isolated thumbnail suite.

## Verification Highlights

- `venv\Scripts\python.exe workspace\execution\health_check.py --category filesystem --json` -> **overall `ok`** (`execution/`, `directives/`, repo-root `.tmp`, `.env`, `CLAUDE.md`)
- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests\test_health_check.py -q -o addopts=` -> **35 passed**
- `venv\Scripts\python.exe workspace\execution\qaqc_runner.py -p blind-to-x -o .tmp/qaqc_blind-to-x_recheck2_2026-03-30.json` -> **`APPROVED`** / `560 passed / 16 skipped`
- `venv\Scripts\python.exe workspace\execution\qaqc_runner.py -o .tmp/qaqc_system_check_final_2026-03-30.json` -> **`APPROVED`** / `2870 passed / 0 failed / 0 errors / 29 skipped`
- `venv\Scripts\python.exe -m pytest tests/unit/test_thumbnail_step.py -q -o addopts=` (`projects/shorts-maker-v2`) -> **39 passed, 1 warning**
- `venv\Scripts\python.exe -m ruff check src/shorts_maker_v2/pipeline/thumbnail_step.py tests/unit/test_thumbnail_step.py` (`projects/shorts-maker-v2`) -> clean
- `venv\Scripts\python.exe -m coverage run --source=src/shorts_maker_v2 -m pytest tests/unit/test_thumbnail_step.py -q -o addopts=` + `coverage report -m --include="*thumbnail_step.py"` (`projects/shorts-maker-v2`) -> **39 passed, 1 warning**; isolated report showed `thumbnail_step.py` **88%**
- `venv\Scripts\python.exe -m pytest tests/unit/test_orchestrator_unit.py -k "thumbnail or run_success_path_covers_upload_thumbnail_srt_and_series" -q -o addopts=` (`projects/shorts-maker-v2`) -> **2 passed, 35 deselected, 1 warning**
- `python -m pytest tests/unit/test_draft_contract.py tests/unit/test_draft_generator_multi_provider.py tests/unit/test_pipeline_flow.py tests/unit/test_quality_improvements.py -q -o addopts= -k "not slow"` (`projects/blind-to-x`) -> **70 passed, 1 warning**
- `python -m py_compile pipeline/process.py` (`projects/blind-to-x`) -> clean
- `python -m pytest tests/unit/test_pipeline_flow.py tests/unit/test_cost_controls.py tests/unit/test_dry_run_filters.py tests/unit/test_scrape_failure_classification.py tests/unit/test_reprocess_command.py -q -o addopts=` (`projects/blind-to-x`) -> **33 passed, 1 warning**
- `python -m pytest tests/unit/test_draft_contract.py tests/unit/test_draft_generator_multi_provider.py tests/unit/test_pipeline_flow.py tests/unit/test_quality_improvements.py tests/unit/test_cost_controls.py tests/unit/test_dry_run_filters.py tests/unit/test_scrape_failure_classification.py tests/unit/test_reprocess_command.py -q -o addopts= -k "not slow"` (`projects/blind-to-x`) -> **92 passed, 1 warning**
- `python -m pytest tests/unit/test_rules_loader.py tests/unit/test_regulation_checker.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_performance_tracker.py -q -o addopts=` (`projects/blind-to-x`) -> **56 passed, 1 warning**
- `python -m pytest tests/unit/test_quality_improvements.py tests/unit/test_draft_generator_multi_provider.py tests/unit/test_pipeline_flow.py -q -o addopts=` (`projects/blind-to-x`) -> **65 passed, 1 warning**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_optimizations.py -v --no-header -o addopts=` -> **13 passed** ✅ (TestClassificationRulesYAML 3/3 포함)

## Next Priorities

1. Triage the `blind-to-x` project-only security backlog surfaced by QA/QC (`18 actionable issue(s)`) and decide whether any are release-blocking versus documentation debt.

## Notes

- `coverage run` is the reliable measurement path for `shorts-maker-v2` on this Windows machine; `pytest-cov` can still trip over duplicate root/project paths.
- During active BlindToX schedule windows, the infra snapshot can show `4/6 Ready` because the remaining two tasks are legitimately `Running`; confirm with `schtasks /query` before treating that as a regression.
- For `blind-to-x` external reviews, share the docs pack first and avoid sending `.env`, real `config.yaml`, raw Notion identifiers, or unredacted screenshots/logs.
- `projects/blind-to-x` already has unrelated user WIP in several pipeline files; avoid blanket commits or reverts in that repo and keep future edits narrowly scoped.
- For `blind-to-x` staged process changes, edit `projects/blind-to-x/pipeline/process_stages/` for behavior and treat `projects/blind-to-x/pipeline/stages/` as a compatibility bridge only.
- `pipeline.process` still has compatibility globals for tests/commands; if a refactor removes one, expect the unit suite to fail before runtime regressions are obvious.
- The latest `blind-to-x` project QC artifact is `.tmp/qaqc_blind_to_x_2026-03-31.json`.
- The latest shared QC artifact is `.tmp/qaqc_system_check_2026-03-31.json`.
- If the security scanner starts flagging `cost_db.py` again, check `workspace/execution/qaqc_runner.py` triage rules before attempting a code rewrite; the current two hits are already documented false positives tied to `_ARCHIVE_TABLES`.
- `workspace/execution/health_check.py` now depends on the repo-root vs workspace-root split; keep `.env`, `.tmp`, `.git`, `venv`, and `CLAUDE.md` on repo root checks, but keep `execution/` and `directives/` on the workspace root.
- For `blind-to-x` rule edits, treat `projects/blind-to-x/rules/*.yaml` as the source of truth; the root `classification_rules.yaml` is now a compatibility snapshot/fallback surface.
- The latest QC-only code delta in `blind-to-x` was a non-behavioral import-order fix in `pipeline/quality_gate.py` so `ruff` stays green after the rules-loader migration.
- When targeted `coverage report` looks wrong for a Windows path, prefer `coverage report -m --include="*module_name.py"`.
- `tests/unit/test_tts_providers.py` still relies on shared module-level `torch` / `torchaudio` MagicMocks; reset them per test when expanding that suite.
- `hanwoo-dashboard` still installs cleanly only with `npm install --legacy-peer-deps` because of peer drift around `next-auth@5.0.0-beta.25` and Next 16 / TypeScript 5.9.
