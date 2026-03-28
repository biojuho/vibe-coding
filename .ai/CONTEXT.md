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
- `workspace/execution/qaqc_runner.py` now runs `blind-to-x` as split unit/integration batches with a 900s timeout budget, fixing the previous false timeout in shared QC.
- `workspace/execution/graph_engine.py` and `projects/blind-to-x/pipeline/editorial_reviewer.py` now degrade gracefully when `langgraph` is not installed by using local fallback orchestration.
- `workspace/execution/graph_engine.py` now carries evaluator self-reflection between iterations and weights the latest review security score into final confidence instead of averaging every historical worker result.
- `workspace/execution/workers.py` now emits structured reviewer metadata with optional Pydantic validation plus a deterministic security scan so evaluator feedback is machine-readable even when the LLM falls back to text-only output.
- `projects/blind-to-x/pipeline/draft_generator.py` now honors `llm.cache_db_path` via a persistent `DraftCache` instance so cache behavior is stable across generator instances and tests.
- Windows Task Scheduler launchers are standardized through ASCII-safe `C:\btx\...` wrappers.
- Latest shared QC run on `2026-03-28` is **`APPROVED`**: `blind-to-x` 551 passed / 16 skipped, `shorts-maker-v2` 1075 passed / 12 skipped, `root` 1034 passed / 1 skipped, AST 20/20, security `CLEAR`, scheduler `6/6 Ready`.
- `projects/knowledge-dashboard` frontend QC was repaired on `2026-03-28`: `npm run lint` and `npm run build` are now green after fixing the conditional `useMemo` path in `ActivityTimeline.tsx` and replacing the empty `InputProps` interface with a type alias.
- `projects/hanwoo-dashboard` frontend QC was revalidated on `2026-03-28`: `npm run build` now passes again after refreshing the install tree with `npm install --legacy-peer-deps`, and `lucide-react` was bumped to a React 19-compatible release; lint still reports one `@next/next/no-page-custom-font` warning in `src/app/layout.js`.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py` targeted coverage was raised from 69% to 93% on `2026-03-27` with mock-heavy unit tests for review, verification, retry, and truncation paths.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` targeted coverage was raised from 73% to 97% on `2026-03-27` with mock-heavy tests for init paths, optional stages, hold/upload branches, and ShortsFactory/native render routing.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/render_step.py` targeted coverage was raised from 11% to 87% on `2026-03-27` with mocked `run()` happy/fallback flows plus Lyria/local-BGM/thumbnail coverage.
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py` targeted coverage was raised from 59% to 90% on `2026-03-27` with branch-heavy unit tests for fallback chains, checkpoint recovery, and regeneration.
- `projects/shorts-maker-v2` package-wide coverage was lifted to **87%** on `2026-03-28` by expanding existing provider/render suites plus `hwaccel`, then running `coverage run --source=src/shorts_maker_v2 -m pytest tests/unit tests/integration -q -o addopts=` end-to-end (`1144 passed, 12 skipped, 1 warning`).
- The strongest 2026-03-28 non-pipeline coverage gains in `projects/shorts-maker-v2` were `google_music_client.py` **99%**, `pexels_client.py` **95%**, `unsplash_client.py` **100%**, `video_renderer.py` **100%**, and `hwaccel.py` **96%**.
- The next low non-pipeline coverage cluster after the 87% milestone is `style_tracker.py` **54%** plus optional-provider clients `chatterbox_client.py` **49%** and `cosyvoice_client.py` **53%**.

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
| Blind-to-X draft tag contract | `generate_drafts()` validation now expects `twitter` outputs to include `reply` and `creator_take` tags alongside the main draft | When mocking provider responses in tests, include all required tags or bypass validation intentionally |
| Shorts full-suite flakiness | `shorts-maker-v2` previously failed on different tests across full-suite reruns while those same tests passed in isolation; one full `coverage run` passed on `2026-03-28`, but repeatability is still unconfirmed | Treat a single clean end-to-end run as encouraging, not closure; rerun the whole suite to confirm stability before closing T-058 |
| Duplicate project roots | Both `projects/shorts-maker-v2` and a legacy root-level `shorts-maker-v2` directory exist on this machine, which can confuse coverage/import collection | Run tests from `projects/shorts-maker-v2` and prefer `coverage run ... -m pytest ... -o addopts=` over `pytest-cov` when measuring targeted module coverage |
| Coverage report path matching | `coverage report` against a direct Windows source path can sometimes show `0%` unexpectedly even when coverage data exists | When that happens, use `coverage report -m --include="*module_name.py"` instead of a direct file-path report |
| Hanwoo install peers | `projects/hanwoo-dashboard` currently needs `npm install --legacy-peer-deps` because `next-auth@5.0.0-beta.25` does not declare Next 16 peers and Toss types still warn on TypeScript 5.9 | For fresh installs, use `npm install --legacy-peer-deps` until the dependency matrix is aligned |

## Recent Quality Notes

- `shorts-maker-v2` full `tests/unit + tests/integration` under `coverage run` passed on `2026-03-28` with **1144 passed, 12 skipped, 1 warning** and package-wide coverage at **87%**, but repeatability of the earlier order-dependent failure still needs explicit confirmation.
- `blind-to-x` has a known env-specific `curl_cffi` CA-path reproducer that is ignored in shared QA/QC.
- Blind-to-X targeted redesign verification on `2026-03-26`: `103 passed, 1 warning` across the new editorial-filter / draft-fail-closed / few-shot fallback suites.
- The QA/QC contract uses machine-readable statuses such as `APPROVED`, `CONDITIONALLY_APPROVED`, `REJECTED`, `CLEAR`, and `WARNING`.
- Shared QC verification on `2026-03-28`: **`APPROVED`** with `2660 passed, 0 failed, 0 errors, 29 skipped`.
- Root QC regressions fixed on `2026-03-28`: optional `langgraph` fallback in `graph_engine.py`, UTF-8-safe subprocess execution in `workers.py`, and false-positive security hits removed from `reasoning_engine.py`.
- Graph-engine evaluator verification on `2026-03-28`: `ruff` is clean for `workspace/execution/graph_engine.py`, `workspace/execution/workers.py`, and `workspace/tests/test_graph_engine.py`; targeted test suite reports **34 passed**.
- Blind-to-X cache/test contract fixes on `2026-03-28`: `TweetDraftGenerator` now respects `llm.cache_db_path`, and cache/quality-gate tests were updated to the current `reply` + `creator_take` output contract.
- `knowledge-dashboard` frontend verification on `2026-03-28`: `npm run lint` and `npm run build` both pass after fixing the conditional `useMemo` hook path and the empty `InputProps` interface.
- `hanwoo-dashboard` frontend verification on `2026-03-28`: `npm run lint` reports only one `@next/next/no-page-custom-font` warning in `src/app/layout.js`, and `npm run build` passes after reinstalling with `--legacy-peer-deps` and regenerating Prisma client outputs.
- `shorts-maker-v2` script-step targeted verification on `2026-03-27`: `29 passed, 1 warning`; `coverage run` reports `script_step.py` at **93%**.
- `shorts-maker-v2` orchestrator targeted verification on `2026-03-27`: `38 passed, 1 warning`; `coverage run` reports `orchestrator.py` at **97%**.
- `shorts-maker-v2` render-step targeted verification on `2026-03-27`: `141 passed, 1 warning`; `coverage run` with `coverage report -m --include="*render_step.py"` reports `render_step.py` at **87%**.
- `shorts-maker-v2` media-step targeted verification on `2026-03-27`: `28 passed, 1 warning`; `coverage run` reports `media_step.py` at **90%**.
- `shorts-maker-v2` broader aggregate verification on `2026-03-27`: `411 passed, 1 warning`; `coverage run --source=src/shorts_maker_v2` reported **57%** total coverage for `src/shorts_maker_v2` before the 2026-03-28 provider/render + `hwaccel` uplift.
- `shorts-maker-v2` full aggregate verification on `2026-03-28`: `1144 passed, 12 skipped, 1 warning`; `coverage run --source=src/shorts_maker_v2 -m pytest tests/unit tests/integration -q -o addopts=` now reports **87%** total coverage for `src/shorts_maker_v2`.
