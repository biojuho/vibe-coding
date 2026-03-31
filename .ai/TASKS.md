# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-115 | Continue workspace TDR reduction after the corrected test-gap heuristic: next workspace hotspots are `code_improver.py` (46.2), `workers.py` (37.7), and `result_tracker_db.py` (37.4) | Claude | Low | 2026-03-31 |


## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|
| T-100 | Raise the remaining project coverage follow-up from the system audit so `shorts-maker-v2` and `blind-to-x` reach their documented target floors | Claude | 2026-03-31 | `blind-to-x` moved from **59.89%** to **71%** on 2026-03-31. 106 new tests for image_generator, image_upload, analytics_tracker, draft_analytics. Next: `shorts-maker-v2` coverage or remaining blind-to-x modules. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-114 | Added dedicated tests for `workspace/execution/pages/shorts_manager.py` (14 tests, 71% file coverage), extracted repeated issue-label formatting, and fixed `vibe_debt_auditor.py` so test-gap discovery scans all parent `tests/` directories instead of stopping at the first nested match. Latest rerun: `shorts_manager.py` score **43.9 -> 32.9**, workspace TDR **37.31% -> 29.25%**, overall TDR **40.87% -> 38.9%**. | Codex | 2026-03-31 |
| T-113 | Reduced debt in top 3 hotspots: `llm_client.py` 58.8→41.9 (bridged pattern extraction), `blind-to-x/main.py` 59.2→top10 탈락 (main() split + 20 tests), `karaoke.py` 56.4→top10 탈락 (_scale_style + _measure_words). TDR 41.4%→40.9%. | Claude | 2026-03-31 |
| T-112 | Consolidated workspace operator entrypoints into a canonical `FAST / STANDARD / DEEP / DIAGNOSTIC` workflow, added `operator_workflow.md`, clarified script help/README guidance, and made `health_check.py` Windows-safe for real diagnostic use. | Codex | 2026-03-31 |
| T-111 | Wired the local-only PR triage worktree helper into `workspace/execution/pr_triage_orchestrator.py`, added repo-specific validation profiles + `triage-report.json` artifacts, documented the new directive, and hardened Windows git-output decoding for non-ASCII paths. | Codex | 2026-03-31 |
| T-110 | Evaluated ACPX `pr-triage`, adopted the safe isolation slice as `workspace/execution/pr_triage_worktree.py`, documented the directive, updated INDEX mapping, and verified with focused worktree tests. | Codex | 2026-03-31 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
