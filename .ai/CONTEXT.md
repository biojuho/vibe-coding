# Vibe Coding Context

> Local-only workspace. Do not push, pull, or deploy from this repo unless the user explicitly changes that policy.

## Workspace Summary

- Name: `Vibe Coding (Joolife)`
- Purpose: shared AI tooling plus multiple product projects
- Root runtime: Python 3.14, `pytest`, `ruff`, `venv`, `.env`
- Canonical path contract:
  - `workspace/...` for root-owned automation and docs
  - `projects/<name>/...` for product repos
  - `infrastructure/...` for MCP/services

## Active Projects

| Project | Status | Stack | Canonical Path |
|---|---|---|---|
| `blind-to-x` | Active | Python pipeline, Notion, Cloudinary | `projects/blind-to-x` |
| `shorts-maker-v2` | Active | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | `projects/shorts-maker-v2` |
| `hanwoo-dashboard` | Active | Next.js, React, Prisma, Tailwind | `projects/hanwoo-dashboard` |
| `knowledge-dashboard` | Maintenance | Next.js, TypeScript, Tailwind | `projects/knowledge-dashboard` |
| `suika-game-v2` | Frozen | Vite, Vanilla JS, Matter.js | `projects/suika-game-v2` |
| `word-chain` | Frozen | React, Vite, Tailwind | `projects/word-chain` |

## Canonical Structure

```text
Vibe coding/
├── .ai/
├── .agents/
├── .claude/
├── .github/
├── .tmp/
├── _archive/
├── infrastructure/
├── projects/
│   ├── blind-to-x/
│   ├── hanwoo-dashboard/
│   ├── knowledge-dashboard/
│   ├── shorts-maker-v2/
│   ├── suika-game-v2/
│   └── word-chain/
├── workspace/
│   ├── directives/
│   ├── execution/
│   │   └── pages/
│   ├── scripts/
│   └── tests/
└── venv/
```

## Current State

- Workspace simplification refactor is in progress on `2026-03-26`.
- Root-owned directories `directives/`, `execution/`, `scripts/`, and `tests/` were moved under `workspace/`.
- Product directories were moved under `projects/`.
- Root automation is being updated to resolve both canonical project paths and legacy root paths internally during migration.
- `workspace/execution/qaqc_runner.py` and `workspace/execution/joolife_hub.py` now target the canonical layout.
- QA/QC output is now expected at `projects/knowledge-dashboard/public/qaqc_result.json`.
- Blind-to-X scheduled entrypoints and n8n bridge defaults now target canonical paths: `projects/blind-to-x` and `workspace/execution`.
- `projects/blind-to-x` now applies X-first editorial filtering (`pre_editorial_score`), fail-closed draft generation, and few-shot fallback (`performance -> approved -> YAML`) after the 2026-03-26 curation redesign.
- Windows Task Scheduler launchers are standardized through ASCII-safe `C:\btx\...` wrappers.
- Latest shared QC run on `2026-03-26` is `CONDITIONALLY_APPROVED`: root passes, blind-to-x hits runner timeout, shorts-maker-v2 has suite-only flaky failures, knowledge-dashboard lint fails.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py` targeted coverage was raised from 69% to 93% on `2026-03-27` with mock-heavy unit tests for review, verification, retry, and truncation paths.

## Shared Services

- MCP servers are configured via `.mcp.json` and related files at repo root.
- Telegram bot and other external providers use root `.env`.
- `infrastructure/` remains top-level and is not part of `workspace/`.

## Minefield

| Risk | Details | Safe Pattern |
|---|---|---|
| Windows console encoding | Emoji and non-ASCII console output can fail under cp949 paths or terminals | Prefer ASCII-safe logging or logger-based output |
| Windows CA path + `curl_cffi` | Non-ASCII filesystem paths can trigger Error 77 | Copy cert bundle to ASCII-safe path and set `CURL_CA_BUNDLE` |
| pytest `addopts` conflicts | Project-local `pytest.ini` or `pyproject` coverage options can conflict with orchestrated runs | Use `-o addopts=` in shared runners |
| Legacy path assumptions | Old docs and scripts may still reference root `pages/` or root product dirs | Use `workspace/...` and `projects/...` in new code/docs |
| Dirty nested repos | Product repos may contain user WIP | Never revert or overwrite unrelated changes |
| PowerShell ScheduledTasks cmdlets | `Register-ScheduledTask` / `Unregister-ScheduledTask` can return `Access is denied` on this machine even when `schtasks` works | Regenerate `C:\btx\...` launchers first; if cmdlets fail, inspect with `Get-ScheduledTask` and use `schtasks` fallback for recovery |
| Shared QC timeout budget | `blind-to-x` full suite currently exceeds the runner's fixed 300s timeout even though unit/integration pass when run separately | Treat a runner TIMEOUT as inconclusive; rerun `tests/unit` and `tests/integration` separately or raise/split the timeout |
| Shorts full-suite flakiness | `shorts-maker-v2` can fail on different tests across full-suite reruns while those same tests pass in isolation | Suspect order dependence or leaked global state before editing production code; rerun isolated tests to confirm |
| Duplicate project roots | Both `projects/shorts-maker-v2` and a legacy root-level `shorts-maker-v2` directory exist on this machine, which can confuse coverage/import collection | Run tests from `projects/shorts-maker-v2` and prefer `coverage run ... -m pytest ... -o addopts=` over `pytest-cov` when measuring targeted module coverage |

## Recent Quality Notes

- `shorts-maker-v2` recently passed broad targeted suites and coverage uplift work, but full `tests/unit + tests/integration` reruns on `2026-03-26` were unstable.
- `blind-to-x` has a known env-specific `curl_cffi` CA-path reproducer that is ignored in shared QA/QC.
- Blind-to-X targeted redesign verification on `2026-03-26`: `103 passed, 1 warning` across the new editorial-filter / draft-fail-closed / few-shot fallback suites.
- The QA/QC contract uses machine-readable statuses such as `APPROVED`, `CONDITIONALLY_APPROVED`, `REJECTED`, `CLEAR`, and `WARNING`.
- `knowledge-dashboard` currently fails lint with a conditional `useMemo` hook and an empty interface declaration.
- `hanwoo-dashboard` lint is green aside from one `@next/next/no-page-custom-font` warning in `src/app/layout.js`.
- `shorts-maker-v2` script-step targeted verification on `2026-03-27`: `29 passed, 1 warning`; `coverage run` reports `script_step.py` at **93%**.
