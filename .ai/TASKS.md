# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause pinpointed 2026-05-11: `projects/hanwoo-dashboard/.env` has the Supabase template URL with `YOUR_PASSWORD` placeholder still unreplaced — host/user are real, only the password literal needs substitution from Supabase console. | User | Medium | 🔴 approval | 2026-05-08 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-268 | `[workspace]` Multi-branch consolidation to single `main`: PR #33 squash-merge preserved T-251 root-cause `[ai-context]` (`9262f5c` → `8a691a4`); cherry-picked unique `47b6590` stabilization (→`9e58483`); confirmed `b29b967` LLM usage summary already absorbed in `c856f35`. Pushed origin/main = `ae60610` (9 commits); deleted duplicate `feat/` and `refactor/` branches locally + on origin. `stash@{0}` retains 264-line `execution/langfuse_preflight.py` + tests for user review. | Claude Code (Opus 4.7 1M) | 2026-05-12 |
| T-267 | `[workspace]` Full active-project QC re-run per user request. `python execution\project_qc_runner.py --json` returned `status: passed` across `blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, and `knowledge-dashboard`; supporting graph risk `0.00`, governance `ok`, staged gate `pass`. No code changes were made by Codex for the QC run. | Codex | 2026-05-11 |
| T-266 | `[workspace]` Quieted staged code-review gate for docs-only commits: `execution/code_review_gate.py --staged` now filters staged files to code/config candidates before invoking `code_review_graph`, so `.ai`/Markdown-only commits pass without stale graph warnings. Verification: `workspace/tests/test_code_review_gate.py` `20 passed`, Ruff/format/py_compile clean, post-commit `--staged --json` pass. | Codex | 2026-05-11 |
| T-265 | `[workspace/shorts-maker-v2]` Product-readiness monitoring finish: added LLM usage summary CLI, wired API anomaly alerts into daily reports, added staged advisory code-review gate to pre-commit, resolved governance mapping drift, and fixed Shorts auto-topic UTF-8 output when called directly on Windows. Verification: workspace focused suite `105 passed`, Shorts focused suite passed, Ruff/format/py_compile clean, governance health `ok`, and full `python execution\project_qc_runner.py --json` passed across all active projects. | Codex | 2026-05-11 |
| T-264 | `[workspace/shorts-maker-v2]` Product-readiness finalization: added API usage anomaly alerts (`alerts` CLI for fallback-rate, cost-spike, and dead expected-provider detection), documented the daily monitoring flow, synchronized Shorts Maker V2 `pytrends` dependency with `uv.lock`, and reran full active project QC. Verification: API tracker `43 passed`, Ruff/format clean, `uv lock --check`, graph risk `0.00`, and `python execution\project_qc_runner.py --json` passed across all active projects. | Codex | 2026-05-11 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
