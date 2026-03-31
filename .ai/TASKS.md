# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-106 | Apply ruff format to remaining 10 unformatted files in `workspace/` | Any | Low | 2026-03-30 |
| T-109 | Add phase-2 selective-context upgrades: file-summary cache, agent profiles, and adaptive pruning on top of `repo_map.py` / `context_selector.py` | Any | Medium | 2026-03-31 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|
| T-100 | Raise the remaining project coverage follow-up from the system audit so `shorts-maker-v2` and `blind-to-x` reach their documented target floors | Codex | 2026-03-31 | `blind-to-x` moved from **56.56%** to **59.89%** on 2026-03-31. Next candidates: `image_generator.py` + `image_upload.py`, or analytics modules. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-108 | Added deterministic `repo_map.py` + `context_selector.py`, wired selective repository context into `VibeCodingGraph`, fixed `ThoughtDecomposer` task extraction (`task_text`), updated directive ownership, and verified with 39 passing workspace tests plus governance/mapping checks. | Codex | 2026-03-31 |
| T-107 | Project critique + tech debt cleanup: removed stages/ bridge (65 LOC), deleted legacy classification_rules.yaml (64KB), cleaned legacy path compat (path_contract, error_analyzer, qaqc_runner, smoke_check), slimmed STATUS.md (109->35), consolidated ADR (20+->9), merged ADR-002/013 contradiction. blind-to-x 605 passed, workspace 1026 passed. | Claude | 2026-03-31 |
| T-105 | Verified 5 pre-existing test failures resolved: ShortsFactory legacy tests pass/skip, cp949 test passes | Claude | 2026-03-31 |
| T-101 | Reduced MCP control-plane overhead by removing redundant `filesystem` MCP, adding AI-client footprint guard | Codex | 2026-03-31 |
| T-102 | Expanded Shorts golden render integration to 30-second sample with MoviePy+FFmpeg verification | Codex | 2026-03-31 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
