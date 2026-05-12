# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause pinpointed 2026-05-11: `projects/hanwoo-dashboard/.env` has the Supabase template URL with `YOUR_PASSWORD` placeholder still unreplaced — host/user are real, only the password literal needs substitution from Supabase console. | User | Medium | 🔴 approval | 2026-05-08 |
| T-273 | `[workspace]` Review PR #35 (`recover/langfuse-preflight-from-stash`): confirm Langfuse preflight checklist coverage and validate that the recovered `golden_cases.example.yaml`/`rejected_cases.example.yaml` schemas match the promptfoo extractor. | User | Medium | 🔴 approval | 2026-05-12 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-274 | `[workspace]` Activated shared goal tracking: added `.ai/GOAL.md`, surfaced its active goal in `execution/session_orient.py`, and pinned the active/missing/render paths in `workspace/tests/test_session_orient.py`. Verification: session-orient tests `14 passed`, Ruff clean, CLI smoke showed `GOAL: active`, graph detect-changes risk `0.00`, `git diff --check` clean. Feature commit `1c5f341`; no push/deploy. | Codex | 2026-05-12 |
| T-272 | `[workspace]` Recovered dropped stash content as PR #35: extracted unique blobs (`execution/langfuse_preflight.py` 264 lines, `test_langfuse_preflight.py`, two `tests/eval/blind-to-x/*.example.yaml`) from `git fsck --unreachable` after stash@{0} was auto-pruned by a concurrent tool. Verified ruff clean + `7 passed`, branched into `recover/langfuse-preflight-from-stash`, PR opened. | Claude Code (Opus 4.7 1M) | 2026-05-12 |
| T-271 | `[workspace]` Added and verified the multi-tool startup orientation snapshot in `execution/session_orient.py`, with root agent docs updated to recommend it at session start. The CLI summarizes branch/ahead state, dirty files, active tasks, HANDOFF rotation pressure, SQLite/graph health, and recent CI. Verification: `workspace/tests/test_session_orient.py` `11 passed`, CLI smoke printed the expected snapshot, targeted Ruff/format/py_compile clean, and graph risk `0.00`. | Codex + concurrent local commit `252c413` | 2026-05-12 |
| T-270 | `[blind-to-x]` Audited the T-269 dead-code class across `pipeline/*` — grep `parent.parent.parent` + `spec_from_file_location`. Found 2 more broken sites: `pipeline/notion/_upload.py:571` (NLM 아티클의 Notion 블록 변환이 plain-text 폴백만 받던 상태) + `pipeline/notebooklm_enricher.py:32` (NotebookLM enrichment 전체 silent degraded). Both fixed: `parents[N] / workspace / execution / ...` + `.exists()` 가드. Control case `pipeline/process_stages/runtime.py:68` confirmed already correct. Added `tests/unit/test_workspace_path_pins.py` with 4 pin tests + `_repo_root_from()` helper that detects parents[N] miscalculation via `workspace/` + `projects/` sibling check. Verification: workspace_path_pins + viral_boost + notion_upload `46 passed`, touched 5 파일 Ruff clean. | Claude Code (Opus 4.7 1M) | 2026-05-12 |
| T-269 | `[blind-to-x]` Restored the LLM viral boost path by pointing `estimate_viral_boost_llm()` at `workspace/execution/llm_client.py` instead of the nonexistent project-local `execution/llm_client.py`; added hermetic regression tests that verify the workspace target, score clamping, graceful provider-missing fallback, and long-argument safety. Local commit `732f4e6` also tracks `qc_results.json`; no push was performed. Verification: focused viral boost tests `4 passed`, content-intelligence slice `25 passed`, Ruff clean, graph risk `0.00`, `git diff --check` clean. | Codex + concurrent local commit | 2026-05-12 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
