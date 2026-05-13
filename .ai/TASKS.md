# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause pinpointed 2026-05-11 and rechecked 2026-05-12: `projects/hanwoo-dashboard/.env` has the Supabase template URL with `YOUR_PASSWORD` placeholder still unreplaced — host/user are real, only the password literal needs substitution from Supabase console. Latest `npm run db:prisma7-test -- --live` again failed at the intended config guard. | User | Medium | 🔴 approval | 2026-05-08 |
| T-282 | `[workspace]` Human review/merge PR #35. Latest recheck after the user asked to continue: the PR branch is still `a663565`, includes the T-280 fix and `origin/main`, and all GitHub checks are green. GitHub still reports `reviewDecision: REVIEW_REQUIRED` / `mergeStateStatus: BLOCKED`; active auth is the PR author, so a non-author reviewer must approve before merge. | User | High | 🔴 approval | 2026-05-12 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-285 | `[workspace]` Behavior-preserving refactor of `workspace/execution/llm_client.py` (1199→1194 lines) — feature commit `ade1cef`. Extracted three single-source helpers without renaming any public interface: `_cache_creation_multiplier(cache_strategy)` (Anthropic 1h=2.0× / else 1.25× — 2 inline sites), `_resolve_client(providers, caller_script)` (4 module-level convenience functions), and `LLMClient._no_providers_error_message()` (`generate_json` + `_bridged_generate`). Authored `REFACTOR.md` documenting 18 frozen public symbols, 11 production importers + 5 test files, and explicitly out-of-scope items (`_generate_once`/`_get_client` per-provider split blocked by 141 test patches; `generate_json`/`generate_text` full loop fusion blocked by observable log-label / error-format / JSONDecodeError-branch differences). Verification: `pytest workspace/tests/{test_llm_client,test_llm_fallback_chain,test_llm_client_langfuse,test_llm_client_anthropic_cache,test_llm_bridge_integration,test_api_usage_tracker,test_topic_auto_generator}.py` -> `184 passed`; ruff check/format clean; `code_review_gate --base HEAD` `risk=0.00`; public-API import smoke (18 symbols) OK. Pre-commit gate reported advisory `warn risk=0.40` from graph test-gap heuristics on the new helpers (covered indirectly via existing `generate_json` / `generate_text` tests). | Claude Code (Opus 4.7 1M) | 2026-05-13 |
| T-284 | `[blind-to-x]` Decluttered reviewer Notion pages in local feature commit `bbe23bb`. `pipeline/notion/_upload.py` now builds reviewer-first pages with visible `검토 요약` and `채널 초안`, folded `진단 펼치기` / `원문 펼치기` / `부가 산출물 펼치기` sections, and richer summary signals for rank, editorial score, quality retries, quality scores, fact-check warnings, and publish platforms. `scripts/backfill_notion_review_columns.py` now recursively traverses child blocks so derived review columns still work after toggle nesting. `README.md` and `docs/ops-runbook.md` now recommend a smaller reviewer-focused Notion schema. Verification: targeted Ruff and `py_compile` clean, `test_notion_upload.py` + `test_backfill_notion_review_columns.py` `42 passed`, `test_notion_accuracy.py` `8 passed`, and staged `code_review_gate` reported only advisory `warn risk=0.40` from graph test-gap heuristics. | Codex | 2026-05-13 |
| T-283 | `[workspace]` Fixed the Windows MCP launcher regression for `code-review-graph`. Updated root/legacy MCP configs to run `python -m code_review_graph serve` instead of the broken `python3.13` WindowsApps stub, taught `execution/session_orient.py` to prefer `python` before `py -3.13`, and added regression coverage so orientation no longer false-negatives graph availability when the launcher shim is unhealthy. Verification: `python -m pytest --no-cov workspace/tests/test_mcp_config.py workspace/tests/test_session_orient.py -q --basetemp .tmp/pytest-mcp-fix` -> `21 passed`; `python execution/session_orient.py` now reports graph node/edge/file counts again. Two-tool concurrency: T-283 committed by Claude Code as `74b687e` while T-284 was committed concurrently by Codex; no conflicts. | Codex / Claude Code | 2026-05-13 |
| T-281 | `[workspace]` Published/reconciled PR #35 T-280 fix after user said to proceed until done. Remote `recover/langfuse-preflight-from-stash` is now `a663565`, containing `670859f` recovered Langfuse/eval files, `2061d4b` dotenv-aware smoke fix, and an `origin/main` merge to clear the behind state. Verification before/after push: Langfuse+eval local slice `16 passed`, targeted Ruff check/format clean, `py_compile` clean, diff check clean, graph/code-review gate risk `0.00`, and GitHub checks all green (`root-quality-gate`, `workspace-quality`, `blind-to-x-tests`, `shorts-maker-v2-tests`, both frontend app jobs, `test-summary`, GitGuardian). PR remains blocked only by required human review. | Codex | 2026-05-12 |
| T-280 | `[workspace]` Fixed the PR #35 Langfuse smoke false-positive locally without pushing. Preferred local fix is `a8a4e2b fix(workspace): honor dotenv langfuse smoke keys` on branch `recover/langfuse-preflight-from-stash`: `main()` passes loaded `.env` into smoke, smoke resolves Langfuse keys plus host/base URL from `.env` or process env, temporarily injects/restores Langfuse env only around `_emit_langfuse_trace()`, fails before emit when keys cannot resolve, and adds regression coverage for dotenv-only keys, env restoration, unresolved keys, and `main()` forwarding. A separate clean scratch branch `codex/t280-langfuse-preflight` also contains narrower commit `f9373cb`. Verification for the preferred fix: `test_langfuse_preflight.py` `10 passed`, Langfuse + eval slice `16 passed`, targeted Ruff check/format clean, mapping check clean, compileall clean, diff check clean. No push/merge/deploy performed. | Codex | 2026-05-12 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
