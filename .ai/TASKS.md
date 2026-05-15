# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Root cause: Supabase password desynchronization. We updated `.env` with `Hanwoo2026!@#` and port `6543`, but `npm run db:prisma7-test -- --live` failed with `ENOTFOUND tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. **Action Required**: The user MUST manually reset the database password via the Supabase Dashboard (Project Settings > Database) to resynchronize the control plane pooler credentials, then update `.env` if it changes. | User | Medium | approval | 2026-05-08 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-300 | `[workspace]` Fixed the `root` QC collection error surfaced by fresh qaqc data and the follow-on root QA/QC blockers. Added root `execution/` import coverage for `workspace/execution/tests`, made `ai_batch_runner.process_item` explicitly fail empty choices/null content, hardened `qaqc_runner` to use unique repo-local pytest basetemp paths on Windows, fixed repo/security scan exclusions to scope `.tmp` checks relative to their scan roots, quoted workspace DB audit identifiers, and stabilized frontend/TesterWorker subprocess tests on Windows. Verification: targeted subprocess suite 115 passed; `workspace/execution/tests/test_ai_batch_runner_regression.py` 2 passed; `workspace/tests` 1452 passed / 1 skipped; `workspace/execution/tests` 72 passed; final `python workspace/execution/qaqc_runner.py --project root --skip-infra --skip-debt --output .tmp/qaqc-root-approved-final.json` -> `APPROVED`, 1525 passed / 1 skipped. Commits `846cf5a` + `94fe1af`. | Antigravity + Codex | 2026-05-15 |
| T-299 | `[workspace]` hanwoo-dashboard hardening. Removed an untracked `scratch.mjs` containing a hardcoded Supabase password and added `scratch.*` gitignore patterns (commit `16fd387`). Fixed the readiness QC signal so hanwoo-dashboard is no longer scored `UNKNOWN`/blocked: `qaqc_runner.py` was pytest-only, so added `run_npm_test` + a node:test tap/spec summary parser and a `hanwoo-dashboard` PROJECTS entry; `product_readiness_score.py` and `sync_data.py` now read the git-tracked `public/qaqc_result.json` instead of the gitignored `data/` orphan (commit `3939cc3`). Regenerated the qaqc artifact (commit `5bd5b1e`): hanwoo-dashboard now `PASS 75`, readiness score 55→86 (remaining `blocked` is only the legitimate T-251 task blocker). Verification: `test_qaqc_runner_extended.py` `16 passed`, ruff clean, real `run_npm_test` against hanwoo returns `PASS 75`, full QA pass `CONDITIONALLY_APPROVED 4566 passed`. Surfaced T-300 (pre-existing `root` collection error masked by 6-week-stale data). | Claude Code (Opus 4.7 1M) | 2026-05-15 |
| T-289 | `[hanwoo-dashboard]` Committed the multi-session-stuck AI chat API contract WIP. Feature commit `49be0f9` extracts request parsing, validation, Gemini history normalization, SSE streaming, and JSON error envelopes from `/api/ai/chat/route.js` into `src/lib/ai-chat-api.mjs` with focused tests; the route now requires `requireAuthenticatedSession()` before reading `GEMINI_API_KEY` or farm DB context. Adds `API_SPEC.md` and links it from README. Verification: hanwoo-dashboard `npm test` `75 passed`, `npm run lint`, `npm run build` all pass. | Claude Code (Opus 4.7 1M) | 2026-05-15 |
| T-298 | `[workspace]` Completed the active Agent Skill health cleanup goal. `execution/skill_lint.py` now ignores fenced-code example references, distinguishes local bundled references from generated artifact filenames, resolves common skill subdirectories, and accepts broader trigger guidance markers. Updated active `.agents/skills/**/SKILL.md` metadata/references so skill health is `pass`, score `100`, 42 healthy / 42 active skills, 0 warnings, 0 errors. Verification: `python execution/skill_lint.py --json`; `workspace/tests/test_skill_lint.py` `7 passed`; targeted Ruff passed; `project_qc_runner.py --project knowledge-dashboard --json` passed. Feature commit `65cbe47`. Hygiene follow-up `bcfa2e5` (Claude Code): dropped a cp949-mojibake duplicate (`"?ъ슜"`) of `"사용"` from `TRIGGER_MARKERS`; re-verified score 100 / 7 passed / ruff clean. | Codex + Claude Code | 2026-05-15 |
| T-297 | `[knowledge-dashboard]` Made product-readiness scoring account for stale QA/QC data. `execution/product_readiness_score.py` now reads the QA/QC `timestamp`, marks QC stale after 7 days, caps stale QC credit, and recommends a QC refresh. `ProductReadinessPanel` displays QC age/stale status in each project card. Verification: product-readiness tests `4 passed`; Ruff passed; `npx tsc --noEmit`; knowledge-dashboard `npm test`, `npm run lint`, `npm run build`; `project_qc_runner.py --project knowledge-dashboard --json` passed; code-review gate pass risk `0.0` with the known trailing Windows `cp949` reader-thread exception. | Codex | 2026-05-15 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `safe`: can proceed immediately on a short "continue/go" command.
- `approval`: requires explicit user confirmation before execution.
- `safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `approval` tasks remain, stop and ask which one the user wants next.
