# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | Re-ran the only remaining TODO after the user said "complete everything". `projects/hanwoo-dashboard/scripts/prisma7-runtime-test.mjs` now prints Prisma error `name`, `code`, `meta`, and nested `cause` details so live DB blockers are actionable instead of blank. |
| Next Priorities | Verification: `npm.cmd run db:prisma7-test` passed offline (`14 passed, 0 failed, 1 skipped`). `npm.cmd run db:prisma7-test -- --live` was retried with escalated network access and still failed at connection health with `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. T-251 remains user-owned: reset/resync the Supabase database password in the Supabase Dashboard, then rerun the live command. No push was performed. |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | **T-302 + T-303 completed after user said "다 처리해"**. Finished the remaining local WIP and workspace hygiene goal. `projects/shorts-maker-v2/tests/unit/test_orchestrator_unit.py` now covers SemanticQC orchestration: disabled path, pass manifest persistence, degraded non-blocking degraded-step metadata, error verdict persistence, and exception swallowing. Applied HANDOFF size cleanup with `python execution/handoff_rotator.py --json --keep-days 0`, moving 44 older addenda into `.ai/archive/HANDOFF_archive_2026-05-15.md` and reducing HANDOFF to 160 lines. Cleared the EOL-only dirty state in `projects/blind-to-x/pipeline/notion/_upload.py` without content changes. Closed `.ai/GOAL.md` back to inactive. |
| Next Priorities | Verification passed: `python -m pytest --no-cov tests/unit/test_orchestrator_unit.py -q --tb=short --maxfail=1 --basetemp ../../.tmp/pytest-shorts-orchestrator-unit` -> `49 passed, 2 warnings`; targeted Ruff passed for the SemanticQC/orchestrator slice; `python execution/handoff_rotator.py --check --json --keep-days 0` predicted 44 archivable addenda before rotation; SESSION_LOG is 396 lines, under the 1000-line limit. Remaining blocker is still T-251, which requires the user to reset/resync the Supabase DB password before live Prisma E2E can run. No push was performed. |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | **T-301 knowledge-dashboard readiness/QC signal repair completed**. Fixed the signal path by registering `knowledge-dashboard` in `workspace/execution/qaqc_runner.py`, removing the `root → knowledge-dashboard` fallback in `execution/product_readiness_score.py`, preserving existing project results when a default targeted deep QA/QC run updates the canonical artifact, and adding focused regression coverage. |
| Next Priorities | Verification passed: focused tests `31 passed`; targeted Ruff clean; `python workspace/execution/qaqc_runner.py --skip-infra --skip-debt` -> `APPROVED`, `4646 passed`. Readiness: overall `92 / blocked` only because T-251 is user-owned. |

## Notes

- **T-251 (active blocker)**: Supabase database password desynchronization. User must reset password via Supabase Dashboard (Project Settings > Database), then update `projects/hanwoo-dashboard/.env`.
- **Origin sync**: `main` is many commits ahead of `origin/main`. A push or PR is needed after explicit user approval.
- Older addenda archived in `.ai/archive/HANDOFF_archive_2026-05-15.md`.
