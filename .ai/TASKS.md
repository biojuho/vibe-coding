# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-112 | Consolidate workspace operator entrypoints (`doctor.py`, `health_check.py`, `quality_gate.py`, `qaqc_runner.py`) into one documented fast/standard/deep workflow and trim plan-vs-backlog drift in the control plane | Codex | High | 2026-03-31 |


## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|
| T-100 | Raise the remaining project coverage follow-up from the system audit so `shorts-maker-v2` and `blind-to-x` reach their documented target floors | Claude | 2026-03-31 | `blind-to-x` moved from **59.89%** to **71%** on 2026-03-31. 106 new tests for image_generator, image_upload, analytics_tracker, draft_analytics. Next: `shorts-maker-v2` coverage or remaining blind-to-x modules. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-111 | Wired the local-only PR triage worktree helper into `workspace/execution/pr_triage_orchestrator.py`, added repo-specific validation profiles + `triage-report.json` artifacts, documented the new directive, and hardened Windows git-output decoding for non-ASCII paths. | Codex | 2026-03-31 |
| T-110 | Evaluated ACPX `pr-triage`, adopted the safe isolation slice as `workspace/execution/pr_triage_worktree.py`, documented the directive, updated INDEX mapping, and verified with focused worktree tests. | Codex | 2026-03-31 |
| T-109 | Extended test coverage for context selector (>80%), profile testing, limits testing. Fixed `repo_map.py` sqlite3 winerror lock issue. | Antigravity | 2026-03-31 |
| T-106 | Apply ruff format to remaining unformatted files across the workspace (`ruff format .ai` and python files) | Gemini | 2026-03-31 |
| T-108 | Added deterministic `repo_map.py` + `context_selector.py`, wired selective repository context into `VibeCodingGraph`, fixed `ThoughtDecomposer` task extraction (`task_text`), updated directive ownership, and verified with 39 passing workspace tests plus governance/mapping checks. | Codex | 2026-03-31 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
