# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause pinpointed 2026-05-11: `projects/hanwoo-dashboard/.env` has the Supabase template URL with `YOUR_PASSWORD` placeholder still unreplaced — host/user are real, only the password literal needs substitution from Supabase console. | User | Medium | 🔴 approval | 2026-05-08 |
| T-281 | `[workspace]` Publish/review PR #35 T-280 fix after explicit approval. Clean local branch `codex/t280-langfuse-preflight` contains `f9373cb`; separate local branch `recover/langfuse-preflight-from-stash` also contains `a8a4e2b` plus context commits and is ahead of `origin/recover/langfuse-preflight-from-stash`. The remote GitHub PR still points at `670859f` until pushed. Decide whether to push/cherry-pick the clean fix or reconcile the local PR branch through normal review. | User/AI | High | 🔴 approval | 2026-05-12 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-280 | `[workspace]` Fixed the PR #35 Langfuse smoke false-positive locally without pushing. Preferred local fix is `a8a4e2b fix(workspace): honor dotenv langfuse smoke keys` on branch `recover/langfuse-preflight-from-stash`: `main()` passes loaded `.env` into smoke, smoke resolves Langfuse keys plus host/base URL from `.env` or process env, temporarily injects/restores Langfuse env only around `_emit_langfuse_trace()`, fails before emit when keys cannot resolve, and adds regression coverage for dotenv-only keys, env restoration, unresolved keys, and `main()` forwarding. A separate clean scratch branch `codex/t280-langfuse-preflight` also contains narrower commit `f9373cb`. Verification for the preferred fix: `test_langfuse_preflight.py` `10 passed`, Langfuse + eval slice `16 passed`, targeted Ruff check/format clean, mapping check clean, compileall clean, diff check clean. No push/merge/deploy performed. | Codex | 2026-05-12 |
| T-273 | `[workspace]` Reviewed PR #35 (`recover/langfuse-preflight-from-stash`). PR metadata: open, review required, CI green, merge state `BEHIND`, changed files limited to `execution/langfuse_preflight.py`, `workspace/tests/test_langfuse_preflight.py`, and two Blind-to-X eval example YAML files. Verification in a temporary worktree: `python -m py_compile` passed for the preflight/eval modules, `workspace/tests/test_langfuse_preflight.py` `7 passed`, `workspace/tests/test_langfuse_preflight.py workspace/tests/test_eval_extract.py` `13 passed`, targeted Ruff passed, example YAML schemas matched `blind_to_x_eval_extract.py` output shape, `git diff --check origin/main...HEAD` clean, graph detect-changes risk `0.00`. Finding: the preflight smoke check can falsely report OK without sending a trace when keys exist only in `.env`, so T-280 was added before merge. | Codex | 2026-05-12 |
| T-279 | `[workspace]` Refactored low-risk internal benchmark tooling in feature commit `963ccf0`. Split `workspace/execution/benchmark_local.py` into focused helpers for keyword matching, SmartRouter classification, Ollama benchmark execution, aggregate stats, cloud-cost estimates, output assembly, and file persistence while preserving CLI/output behavior. Added `workspace/tests/test_benchmark_local.py` with fake Ollama/router coverage; no product runtime code, public API, routes, DB schema, env vars, or dependencies changed. Verification: targeted benchmark tests `6 passed`, targeted Ruff check/format clean, `py_compile` clean, graph update succeeded, graph `detect-changes --base HEAD --brief` risk `0.00`, staged `code_review_gate` produced advisory WARN from graph test-gap heuristics despite direct tests, and `git diff --check` clean aside from standard LF/CRLF warnings. | Codex | 2026-05-12 |
| T-278 | `[workspace]` Applied low-risk frontend validation-gate improvements in feature commit `7d3a447`. `hanwoo-dashboard` and `knowledge-dashboard` now use quoted Node test-runner globs in `npm test`; the frontend CI matrix now runs `npm test` before build/lint/smoke. No product runtime code, features, API/routes, DB schema, env vars, or dependencies changed. Verification: Hanwoo `npm test` now runs 68 tests (previous explicit list ran 55 and missed `use-cache-config.test.mjs`), Knowledge `npm test` 3 passed, both ESLint checks passed, Knowledge `npx tsc --noEmit` passed, both Next builds passed, graph detect-changes risk `0.00`, staged `code_review_gate` produced advisory WARN due concurrent benchmark worktree changes, and `git diff --check` was clean aside from standard LF/CRLF warnings. | Codex | 2026-05-12 |
| T-277 | `[workspace]` Continued behavior-preserving refactors for medium-risk internal workspace automation. Feature commit `9eaa7b7`. Split `workspace/execution/qaqc_runner.py` security scan, infrastructure probes, pytest command/result helpers, reporting, and persistence into smaller helpers; split `workspace/execution/harness_tool_registry.py` HITL authorization/logging and default permission groups; extracted shared `Issue` construction in `workspace/execution/_ci_analyzers.py`. Added direct helper coverage in `workspace/tests/test_qaqc_runner_extended.py`, new `test_harness_tool_registry.py`, and new `test_ci_analyzers.py`. Verification: targeted workspace tests `43 passed`, Ruff check/format clean, `py_compile` passed, graph update succeeded, graph `detect-changes --base HEAD --brief` risk `0.00`, governance health `overall: ok`, `git diff --check` clean aside from standard LF/CRLF warnings. Advisory staged `code_review_gate` still reported WARN from graph test-gap heuristics despite direct tests. | Codex | 2026-05-12 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
