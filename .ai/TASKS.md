# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause pinpointed 2026-05-11: `projects/hanwoo-dashboard/.env` has the Supabase template URL with `YOUR_PASSWORD` placeholder still unreplaced — host/user are real, only the password literal needs substitution from Supabase console. | User | Medium | 🔴 approval | 2026-05-08 |
| T-280 | `[workspace]` Fix PR #35 before merge: `execution/langfuse_preflight.py::check_smoke_trace()` can report OK when `.env` has Langfuse keys but `os.environ` does not, because `_emit_langfuse_trace()` silently no-ops on missing env keys. Inject/restore `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` for the smoke path or call the SDK directly with explicit failure reporting, then add a regression test. | AI | High | 🟢 safe | 2026-05-12 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-273 | `[workspace]` Reviewed PR #35 (`recover/langfuse-preflight-from-stash`). PR metadata: open, review required, CI green, merge state `BEHIND`, changed files limited to `execution/langfuse_preflight.py`, `workspace/tests/test_langfuse_preflight.py`, and two Blind-to-X eval example YAML files. Verification in a temporary worktree: `python -m py_compile` passed for the preflight/eval modules, `workspace/tests/test_langfuse_preflight.py` `7 passed`, `workspace/tests/test_langfuse_preflight.py workspace/tests/test_eval_extract.py` `13 passed`, targeted Ruff passed, example YAML schemas matched `blind_to_x_eval_extract.py` output shape, `git diff --check origin/main...HEAD` clean, graph detect-changes risk `0.00`. Finding: the preflight smoke check can falsely report OK without sending a trace when keys exist only in `.env`, so T-280 was added before merge. | Codex | 2026-05-12 |
| T-279 | `[workspace]` Refactored low-risk internal benchmark tooling in feature commit `963ccf0`. Split `workspace/execution/benchmark_local.py` into focused helpers for keyword matching, SmartRouter classification, Ollama benchmark execution, aggregate stats, cloud-cost estimates, output assembly, and file persistence while preserving CLI/output behavior. Added `workspace/tests/test_benchmark_local.py` with fake Ollama/router coverage; no product runtime code, public API, routes, DB schema, env vars, or dependencies changed. Verification: targeted benchmark tests `6 passed`, targeted Ruff check/format clean, `py_compile` clean, graph update succeeded, graph `detect-changes --base HEAD --brief` risk `0.00`, staged `code_review_gate` produced advisory WARN from graph test-gap heuristics despite direct tests, and `git diff --check` clean aside from standard LF/CRLF warnings. | Codex | 2026-05-12 |
| T-278 | `[workspace]` Applied low-risk frontend validation-gate improvements in feature commit `7d3a447`. `hanwoo-dashboard` and `knowledge-dashboard` now use quoted Node test-runner globs in `npm test`; the frontend CI matrix now runs `npm test` before build/lint/smoke. No product runtime code, features, API/routes, DB schema, env vars, or dependencies changed. Verification: Hanwoo `npm test` now runs 68 tests (previous explicit list ran 55 and missed `use-cache-config.test.mjs`), Knowledge `npm test` 3 passed, both ESLint checks passed, Knowledge `npx tsc --noEmit` passed, both Next builds passed, graph detect-changes risk `0.00`, staged `code_review_gate` produced advisory WARN due concurrent benchmark worktree changes, and `git diff --check` was clean aside from standard LF/CRLF warnings. | Codex | 2026-05-12 |
| T-277 | `[workspace]` Continued behavior-preserving refactors for medium-risk internal workspace automation. Feature commit `9eaa7b7`. Split `workspace/execution/qaqc_runner.py` security scan, infrastructure probes, pytest command/result helpers, reporting, and persistence into smaller helpers; split `workspace/execution/harness_tool_registry.py` HITL authorization/logging and default permission groups; extracted shared `Issue` construction in `workspace/execution/_ci_analyzers.py`. Added direct helper coverage in `workspace/tests/test_qaqc_runner_extended.py`, new `test_harness_tool_registry.py`, and new `test_ci_analyzers.py`. Verification: targeted workspace tests `43 passed`, Ruff check/format clean, `py_compile` passed, graph update succeeded, graph `detect-changes --base HEAD --brief` risk `0.00`, governance health `overall: ok`, `git diff --check` clean aside from standard LF/CRLF warnings. Advisory staged `code_review_gate` still reported WARN from graph test-gap heuristics despite direct tests. | Codex | 2026-05-12 |
| T-276 | `[workspace]` Safely refactored low-risk internal tooling without functional/external behavior changes. Feature commit `30011d9`. Classified candidates by risk; avoided product/runtime modules with business semantics; split `execution/session_orient.py` git/render helpers, deduplicated `execution/code_review_gate.py` trivial-pass/report printing, and extracted JSONL/SQLite `CallRecord` builders in `workspace/execution/llm_usage_summary.py`. Added direct helper coverage. Verification: targeted workspace tests `72 passed`, Ruff check/format clean, `py_compile` passed, graph update succeeded, graph `detect-changes --base HEAD --brief` risk `0.00`, governance health `overall: ok`, `git diff --check` clean aside from standard LF/CRLF warnings. Advisory `execution/code_review_gate.py --base HEAD --json` still reported WARN from graph test-gap heuristics despite direct tests. | Codex | 2026-05-12 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
