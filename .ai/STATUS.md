# Vibe Coding Status & Activity

> This file tracks the current repo state and recurring minefields. Use `qaqc_history.db` or the latest QA/QC artifact for detailed historical totals.

## Current State

- Canonical layout: `workspace/` (root automation), `projects/` (product repos), `infrastructure/` (MCP servers)
- QA/QC output: `projects/knowledge-dashboard/data/qaqc_result.json`
- `blind-to-x`: staged pipeline (`pipeline/process_stages/`), rules under `rules/`, X-first editorial filtering
- `shorts-maker-v2`: 91% coverage, MoviePy + FFmpeg dual backend, golden render verification
- `hanwoo-dashboard`: Next.js 16, Prisma 7.6, 0 npm vulnerabilities
- `knowledge-dashboard`: internal `data/*.json` + authenticated `/api/data/*` delivery, `public/*.json` removed
- `knowledge-dashboard`: chart analytics now flow through `src/lib/dashboard-insights.ts` with search-aware diversity, coverage, concentration, weighted health scoring, and recommendation playbooks
- `knowledge-dashboard`: browser auth now exchanges `DASHBOARD_API_KEY` for a signed `httpOnly` session cookie via `src/app/api/auth/session/route.ts`, `src/lib/dashboard-auth.ts` is the shared gate for `/api/data/*`, and the raw key is no longer persisted in the browser
- `knowledge-dashboard`: dashboard fetches now validate payload shape before `setData`, generic data-load failures render a separate recovery state, `Unspecified` language-heavy slices are treated as metadata gaps, and local node tests cover the insight engine
- Frontend CI now includes runtime smoke checks for `hanwoo-dashboard` and `knowledge-dashboard`
- Governance gate: `governance_checks.py` validates `.ai` files, relay claims, directive mapping, task backlog
- Windows Task Scheduler: ASCII-safe `C:\btx\...` wrappers
- Security: all f-string SQL findings were reviewed and triaged as false positives with allowlist/regex validation still in place

## Minefield

| Risk | Details | Safe Pattern |
| --- | --- | --- |
| Windows console encoding | cp949 terminals can mangle non-ASCII logs | Prefer ASCII-safe logging in scripts and verification output |
| Windows CA path + `curl_cffi` | Non-ASCII certificate paths can trigger Error 77 | Copy the cert bundle to an ASCII path and set `CURL_CA_BUNDLE` |
| pytest `addopts` conflicts | Repo and project pytest config can collide | Use `-o addopts=` in shared runner commands |
| Relay claim drift | `HANDOFF.md` can diverge from the real worktree | Run `health_check.py --category governance --json` when in doubt |
| Dirty nested repos | User/WIP changes already exist across several projects | Never revert unrelated changes; isolate work to the intended tree |
| PowerShell ScheduledTasks | `Register-ScheduledTask` may fail with access denied | Fall back to `schtasks` |
| BTX draft contract | Twitter `reply` is required and `creator_take` is optional metadata | Use `draft_contract.py` helpers |
| BTX `CostDatabase._connect()` | Older call sites still depend on the alias | Keep the alias until that migration is fully closed |
| Health check root split | `workspace/` content and repo-root files can be mixed accidentally | Keep `execution/` and `directives/` under `workspace/`, with `.env` at repo root |
| Shared provider test mocks | TTS/provider mocks can leak between tests | Reset shared mocks between tests |
| Duplicate project roots | `projects/shorts-maker-v2` coexists with older root-level paths | Run commands from `projects/` paths |
| Hanwoo install peers | `next-auth@5` beta still reports a Next 16 peer mismatch | Use `npm install --legacy-peer-deps` |

## Recent Quality Notes

- Use `workspace/execution/qaqc_history_db.py` when you need the detailed shared QA/QC totals or historical comparisons.
- `projects/knowledge-dashboard` verification on `2026-04-02`: `npm run lint`, `npm run build`, `npm test`, and `npm run smoke` all passed after the signed-session auth refactor.
