# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-111 | Wire the new local-only PR triage worktree helper into a higher-level read-only triage orchestrator with repo-specific validation profiles when the user asks for the next slice | Codex | Medium | 2026-03-31 |


## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|
| T-100 | Raise the remaining project coverage follow-up from the system audit so `shorts-maker-v2` and `blind-to-x` reach their documented target floors | Codex | 2026-03-31 | `blind-to-x` moved from **56.56%** to **59.89%** on 2026-03-31. Next candidates: `image_generator.py` + `image_upload.py`, or analytics modules. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-110 | Evaluated ACPX `pr-triage`, adopted the safe isolation slice as `workspace/execution/pr_triage_worktree.py`, documented the directive, updated INDEX mapping, and verified with focused worktree tests. | Codex | 2026-03-31 |
| T-109 | Extended test coverage for context selector (>80%), profile testing, limits testing. Fixed `repo_map.py` sqlite3 winerror lock issue. | Antigravity | 2026-03-31 |
| T-106 | Apply ruff format to remaining unformatted files across the workspace (`ruff format .ai` and python files) | Gemini | 2026-03-31 |
| T-108 | Added deterministic `repo_map.py` + `context_selector.py`, wired selective repository context into `VibeCodingGraph`, fixed `ThoughtDecomposer` task extraction (`task_text`), updated directive ownership, and verified with 39 passing workspace tests plus governance/mapping checks. | Codex | 2026-03-31 |
| T-107 | Project critique + tech debt cleanup: removed stages/ bridge (65 LOC), deleted legacy classification_rules.yaml (64KB), cleaned legacy path compat (path_contract, error_analyzer, qaqc_runner, smoke_check), slimmed STATUS.md (109->35), consolidated ADR (20+->9), merged ADR-002/013 contradiction. blind-to-x 605 passed, workspace 1026 passed. | Claude | 2026-03-31 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
