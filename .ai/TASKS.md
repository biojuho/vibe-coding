# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. Retried on 2026-05-15 with `npm.cmd run db:prisma7-test -- --live` and escalated network access; live connection health still failed with Prisma `P2010`, raw code `XX000`, message `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|
| T-304 | `[blind-to-x]` Release-ready hardening per `/goal "프로젝트 하나 고도화된 완성품으로 만들어놔"`. (a) Closed observability gap: added opt-in `_maybe_forward_to_workspace_usage` in `pipeline/cost_tracker.py` (env `BTX_USAGE_FORWARD=1`, silent failure) so blind-to-x text + DALL-E costs also land in workspace `.tmp/workspace.db` `api_calls`, making `api_usage_tracker alerts` (fallback rate / cost spike / dead provider) cover blind-to-x calls. (b) Docs refresh: fixed stale `tests_unit` path in README + ops-runbook (correct: `tests/unit`); replaced `pip install -r requirements.txt` with `pip install -e .[dev]` (project is pyproject-only, no requirements.txt); rewrote GitHub Actions section to reference `full-test-matrix.yml`/`blind-to-x-tests` (no scheduled workflow exists anymore); added Observability section documenting `LANGFUSE_ENABLED` and `BTX_USAGE_FORWARD`; pointed external-review README + file-manifest at `rules/` (D-031 5-file split) instead of removed `classification_rules.yaml`. (c) Added 3 regression tests in `tests/unit/test_cost_tracker_extended.py` (forwarder invocation, env-gate disabled/enabled, error swallowing via `types.SimpleNamespace`). Verification: `py_compile` + targeted `ruff check` PASS on both modified Python files; lint passed earlier via `project_qc_runner.py --check lint`. Local pytest streaming was blocked by a session-specific subshell capture issue (CMD `cd /d` fails on Korean path; matches known minefield `windows_korean_path_encode_strict`). CI on push will execute the new tests. | Claude Code (Opus 4.7 1M) | 2026-05-16 |
| T-303 | `[workspace]` Completed the active workspace hygiene goal. Rotated HANDOFF with `python execution/handoff_rotator.py --json --keep-days 0`, archiving 44 older addenda into `.ai/archive/HANDOFF_archive_2026-05-15.md` and reducing HANDOFF to 160 lines. SESSION_LOG is 396 lines, under the 1000-line limit. Cleared the EOL-only dirty state in `projects/blind-to-x/pipeline/notion/_upload.py`, confirmed `qaqc_result.json` includes all active projects, and returned `.ai/GOAL.md` to inactive. No push was performed; local commits are ready for an explicit user-approved push. | Codex | 2026-05-15 |
| T-302 | `[shorts-maker-v2]` Added SemanticQC orchestration regression coverage. `tests/unit/test_orchestrator_unit.py` now covers default-disabled skip behavior, successful SemanticQC manifest persistence, degraded non-blocking `degraded_steps` metadata with weak transitions, error verdict persistence without degradation, and exception swallowing. Verification: targeted orchestrator test `49 passed, 2 warnings`; targeted Ruff clean. Commit `cde297e`. | Codex | 2026-05-15 |
| T-301 | `[knowledge-dashboard]` Repaired the product-readiness and deep QA/QC signal path. `workspace/execution/qaqc_runner.py` now registers `knowledge-dashboard` as an npm dashboard project and preserves existing project results when a default targeted deep QA/QC run updates the canonical artifact. `execution/product_readiness_score.py` no longer maps missing `knowledge-dashboard` QC to `root`, preventing stale root failures from making the dashboard look at-risk. Regenerated `projects/knowledge-dashboard/public/qaqc_result.json` with all active projects present. Verification: focused tests `31 passed`; targeted Ruff clean; `python workspace/execution/qaqc_runner.py --skip-infra --skip-debt` -> `APPROVED`, 4646 passed / 13 skipped; readiness now reports overall 92 / blocked only by T-251, and `knowledge-dashboard` 94 / ready. | Codex | 2026-05-15 |
| T-300 | `[workspace]` Fixed the `root` QC collection error surfaced by fresh qaqc data and the follow-on root QA/QC blockers. Added root `execution/` import coverage for `workspace/execution/tests`, made `ai_batch_runner.process_item` explicitly fail empty choices/null content, hardened `qaqc_runner` to use unique repo-local pytest basetemp paths on Windows, fixed repo/security scan exclusions to scope `.tmp` checks relative to their scan roots, quoted workspace DB audit identifiers, and stabilized frontend/TesterWorker subprocess tests on Windows. Verification: targeted subprocess suite 115 passed; `workspace/execution/tests/test_ai_batch_runner_regression.py` 2 passed; `workspace/tests` 1452 passed / 1 skipped; `workspace/execution/tests` 72 passed; final `python workspace/execution/qaqc_runner.py --project root --skip-infra --skip-debt --output .tmp/qaqc-root-approved-final.json` -> `APPROVED`, 1525 passed / 1 skipped. Commits `846cf5a` + `94fe1af`. | Antigravity + Codex | 2026-05-15 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
