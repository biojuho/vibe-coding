# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-082 | Push the next `shorts-maker-v2` output-quality pass: `caption_pillow.py` plus any remaining thumbnail helper branches | Codex | Medium | 2026-03-29 |
| T-084 | Fill `blind-to-x` external-review sample cases with 1-3 anonymized real inputs/outputs for higher-quality outside LLM critique | Codex | Low | 2026-03-29 |
| T-087 | Finish the next `blind-to-x` process cleanup pass: remove `_process_single_post_legacy` and extract stage helpers from `pipeline/process.py` into dedicated stage modules when the worktree is safer | Codex | Medium | 2026-03-29 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-086 | Split `blind-to-x` `process_single_post()` into stage-oriented pipeline steps and preserve manual `review_only` draft generation via the staged flow | Codex | 2026-03-29 |
| T-085 | Apply the first `blind-to-x` external-review cleanup slice: draft contract helpers, publishable-only review/gate flow, and deterministic example selection | Codex | 2026-03-29 |
| T-083 | Prepare `blind-to-x` external LLM review pack with docs, prompt templates, share checklist, and local bundle/zip | Codex | 2026-03-29 |
| T-081 | Extend `shorts-maker-v2` thumbnail live-path hardening with Canva OAuth refresh, video-frame extraction cleanup coverage, and fail-fast HTTP download handling | Codex | 2026-03-29 |
| T-080 | Harden `shorts-maker-v2` thumbnail temp-artifact cleanup and long-title wrapping | Codex | 2026-03-29 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
