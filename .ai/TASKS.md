# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-082 | Push the next `shorts-maker-v2` output-quality pass: `caption_pillow.py` plus any remaining thumbnail helper branches | Codex | Medium | 2026-03-29 |
| T-084 | Fill `blind-to-x` external-review sample cases with 1-3 anonymized real inputs/outputs for higher-quality outside LLM critique | Codex | Low | 2026-03-29 |
| T-087 | Finish the next `blind-to-x` process cleanup pass: remove `_process_single_post_legacy` and extract stage helpers from `pipeline/process.py` into dedicated stage modules when the worktree is safer | Codex | Medium | 2026-03-29 |
| T-089 | Finish the `blind-to-x` rules migration: decide legacy `classification_rules.yaml` snapshot ownership and remove remaining direct consumers of the root file | Codex | Medium | 2026-03-29 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-090 | Split `blind-to-x` classification/editorial/prompt rules into `rules/*.yaml` and add the shared `pipeline/rules_loader.py` migration layer | Codex | 2026-03-29 |
| T-088 | `hanwoo-dashboard` npm audit remediation: 15 vuln → 0 (next 16.2.1, next-auth beta.30, prisma 7.6.0, serwist 9.5.7, overrides for picomatch/lodash/brace-expansion/effect) | Gemini | 2026-03-29 |
| T-072 | Apply Pydantic structural parsing and multi-metric (`security`, `score`) evaluation outputs in `CodeEvaluator` | Gemini | 2026-03-29 |
| T-071 | Integrate `CodeEvaluator` with `graph_engine.py` to create a closed Optimizer-Evaluator feedback loop with QA/QC validation | Gemini | 2026-03-29 |
| T-086 | Split `blind-to-x` `process_single_post()` into stage-oriented pipeline steps and preserve manual `review_only` draft generation via the staged flow | Codex | 2026-03-29 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
