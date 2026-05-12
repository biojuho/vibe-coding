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
| T-277 | `[workspace]` Continued behavior-preserving refactors for medium-risk internal workspace automation. Feature commit `9eaa7b7`. Split `workspace/execution/qaqc_runner.py` security scan, infrastructure probes, pytest command/result helpers, reporting, and persistence into smaller helpers; split `workspace/execution/harness_tool_registry.py` HITL authorization/logging and default permission groups; extracted shared `Issue` construction in `workspace/execution/_ci_analyzers.py`. Added direct helper coverage in `workspace/tests/test_qaqc_runner_extended.py`, new `test_harness_tool_registry.py`, and new `test_ci_analyzers.py`. Verification: targeted workspace tests `43 passed`, Ruff check/format clean, `py_compile` passed, graph update succeeded, graph `detect-changes --base HEAD --brief` risk `0.00`, governance health `overall: ok`, `git diff --check` clean aside from standard LF/CRLF warnings. Advisory staged `code_review_gate` still reported WARN from graph test-gap heuristics despite direct tests. | Codex | 2026-05-12 |
| T-276 | `[workspace]` Safely refactored low-risk internal tooling without functional/external behavior changes. Feature commit `30011d9`. Classified candidates by risk; avoided product/runtime modules with business semantics; split `execution/session_orient.py` git/render helpers, deduplicated `execution/code_review_gate.py` trivial-pass/report printing, and extracted JSONL/SQLite `CallRecord` builders in `workspace/execution/llm_usage_summary.py`. Added direct helper coverage. Verification: targeted workspace tests `72 passed`, Ruff check/format clean, `py_compile` passed, graph update succeeded, graph `detect-changes --base HEAD --brief` risk `0.00`, governance health `overall: ok`, `git diff --check` clean aside from standard LF/CRLF warnings. Advisory `execution/code_review_gate.py --base HEAD --json` still reported WARN from graph test-gap heuristics despite direct tests. | Codex | 2026-05-12 |
| T-275 | `[hanwoo-dashboard]` Reproduced the login failure under a database-unavailable condition: Auth.js credentials callback returned `Configuration` because Prisma errors escaped `authorize`. Fixed by extracting `authorizeCredentials()` and degrading DB/load/compare failures to invalid credentials (`null`) while keeping valid login behavior unchanged. Added Node regression tests and wired them into `npm test`. Verification: `npm test` `55 passed`, `npm run lint`, `npm run build`, `npm run smoke`, targeted login POST returned `CredentialsSignin&code=credentials` with no `Configuration`, project QC passed, graph risk `0.00`, `git diff --check` clean aside from LF/CRLF warnings. | Codex | 2026-05-12 |
| T-274 | `[workspace]` Activated shared goal tracking: added `.ai/GOAL.md`, surfaced its active goal in `execution/session_orient.py`, and pinned the active/missing/render paths in `workspace/tests/test_session_orient.py`. Verification: session-orient tests `14 passed`, Ruff clean, CLI smoke showed `GOAL: active`, graph detect-changes risk `0.00`, `git diff --check` clean. Feature commit `1c5f341`; no push/deploy. | Codex | 2026-05-12 |
| T-272 | `[workspace]` Recovered dropped stash content as PR #35: extracted unique blobs (`execution/langfuse_preflight.py` 264 lines, `test_langfuse_preflight.py`, two `tests/eval/blind-to-x/*.example.yaml`) from `git fsck --unreachable` after stash@{0} was auto-pruned by a concurrent tool. Verified ruff clean + `7 passed`, branched into `recover/langfuse-preflight-from-stash`, PR opened. | Claude Code (Opus 4.7 1M) | 2026-05-12 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
