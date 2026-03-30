# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for session-by-session detail and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Date | 2026-03-30 |
| Tool | Gemini (Antigravity) |
| Work | **T-089** Migrated all 7 direct `classification_rules.yaml` file-system consumers across 3 test files (`test_quality_improvements.py` TestBrandVoiceYAML ×4, `test_performance_tracker.py` TestClassificationRulesPlatformExtension, `test_p3_enhancements.py` TestSourceHintsConfig ×2) to `rules_loader.load_rules()`. Removed skipTest guards and stale `yaml`/`Path` module-level imports. Full 582-test suite still green (0 regressed). |

## Current State

- `workspace/execution/code_evaluator.py` integrated into `graph_engine.py` for structured code evaluation (`is_approved`, `score`, `security_score`). If failed, generates explicit reflection feedback fed directly to `prepare_variants` (Optimizer loop). QA/QC fully passed.
- Shared workspace QC is still green from the latest full rerun on `2026-03-28`: **`APPROVED`**, `2805 passed / 0 failed / 29 skipped`.
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
  - `projects/blind-to-x/pipeline/process.py` now routes the exported entrypoint through shared stage helpers for `dedup`, `fetch`, `filter_profile`, `generate_review`, and `persist`
  - Process results now include `stage_status` so failures and skips are tied to an explicit stage
  - `review_only=True` now overrides the final-rank queue threshold so manual reviewer runs still produce drafts, images, Notion rows, and draft analytics
  - The previous monolithic implementation remains as `_process_single_post_legacy`; do not edit that path by mistake when touching the active flow
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

1. Follow up **T-091** (Low): Remove `_process_single_post_legacy` and extract the new `_run_*_stage()` helpers out of `projects/blind-to-x/pipeline/process.py` into dedicated stage modules once it is safe to do a broader cleanup.
2. Distribute `docs/external-review/sample-cases.md` (Case A + Case B) to external reviewer alongside the existing `review-prompt.md`.

## Notes

- `coverage run` is the reliable measurement path for `shorts-maker-v2` on this Windows machine; `pytest-cov` can still trip over duplicate root/project paths.
- For `blind-to-x` external reviews, share the docs pack first and avoid sending `.env`, real `config.yaml`, raw Notion identifiers, or unredacted screenshots/logs.
- `projects/blind-to-x` already has unrelated user WIP in several pipeline files; avoid blanket commits or reverts in that repo and keep future edits narrowly scoped.
- For `blind-to-x` process changes, edit the exported `process_single_post()` near the bottom of `pipeline/process.py` or the shared `_run_*_stage()` helpers; `_process_single_post_legacy()` is now shadowed and should be treated as temporary reference only.
- For `blind-to-x` rule edits, treat `projects/blind-to-x/rules/*.yaml` as the source of truth; the root `classification_rules.yaml` is now a compatibility snapshot/fallback surface.
- The latest QC-only code delta in `blind-to-x` was a non-behavioral import-order fix in `pipeline/quality_gate.py` so `ruff` stays green after the rules-loader migration.
- When targeted `coverage report` looks wrong for a Windows path, prefer `coverage report -m --include="*module_name.py"`.
- `tests/unit/test_tts_providers.py` still relies on shared module-level `torch` / `torchaudio` MagicMocks; reset them per test when expanding that suite.
- `hanwoo-dashboard` still installs cleanly only with `npm install --legacy-peer-deps` because of peer drift around `next-auth@5.0.0-beta.25` and Next 16 / TypeScript 5.9.
