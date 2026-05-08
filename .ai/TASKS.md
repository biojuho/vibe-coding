# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Current `--live` run is blocked by placeholder `projects/hanwoo-dashboard/.env`; script guard now fails clearly on that state (`512496c`). | User/AI | Medium | 🔴 approval | 2026-05-08 |
| T-253 | `[infra/llm]` Implement `directives/llm_observability_langfuse.md` — self-hosted Langfuse stack under `infrastructure/langfuse/`, opt-in `LANGFUSE_ENABLED` env, trace hooks in `workspace/execution/llm_client.py` and `projects/blind-to-x/pipeline/draft_providers.py`. Includes Docker compose + new test. | AI | High | 🔴 approval | 2026-05-08 |
| T-254 | `[workspace/eval]` Implement `directives/llm_eval_promptfoo.md` — Notion-driven golden/rejected case extractor (`execution/blind_to_x_eval_extract.py`), promptfoo config at `tests/eval/blind-to-x/`, weekly runner with regression alert via Telegram. | AI | Medium | 🔴 approval | 2026-05-08 |
| T-255 | `[workspace/llm_client]` Implement `directives/anthropic_prompt_caching.md` — `cache_strategy` parameter on `LLMClient.generate_*`, anthropic-only `cache_control` injection, `api_usage` schema migration (`cache_creation_tokens`, `cache_read_tokens`), regression test. | AI | High | 🔴 approval | 2026-05-08 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-256 | `[workspace/skills]` Installed 3 agent skills via `npx skills add` (autoskills had a Windows download bug + wrong `wshobson/agent-skills` repo reference): `bash-defensive-patterns` (wshobson/agents), `accessibility` (addyosmani/web-quality-skills), `seo` (addyosmani/web-quality-skills). All linked to Claude Code; `skills-lock.json` updated. | Claude Code (Opus 4.7 1M) | 2026-05-08 |
| T-246 | `[workspace]` Finished remaining approved WIP by project: JobPlanet `_new_page_cm()` page lifecycle, Shorts Maker V2 karaoke timing/channel branding, Hanwoo Prisma 7 stability script and manifest icons, plus tracked `find-skills` registry entry. | Codex | 2026-05-08 |
| T-250 | `[hanwoo-dashboard]` Prisma 7 런타임 안정성 테스트 (H-5): `prisma7-runtime-test.mjs` 신규 생성, 14/14 offline passed (Client Gen 4, Adapter 4, Pool 3, Errors 3), Live CRUD E2E 준비 완료 (`--live` 플래그). `npm run db:prisma7-test` 스크립트 추가. | Gemini (Antigravity) | 2026-05-08 |
| T-249 | `[workspace]` Reflected requested stack policy: current defaults are React/Next.js, JS/TS, PostgreSQL/Supabase-compatible Prisma access, Redis/BullMQ, and Fetch API wrappers; Svelte, Go, Rust, Flutter/native, RabbitMQ, and TanStack Query are candidate-only until a design note exists. | Codex | 2026-05-08 |
| T-120 | `[infrastructure/n8n]` Made `psutil` optional in `bridge_server.py` (real CI blocker — fastapi/pydantic already had fallbacks); extended `test_auto_schedule_paths.py` regression to block fastapi+pydantic+psutil together; wired the test file into `root-quality-gate.yml` and `full-test-matrix.yml`. | Claude Code (Opus 4.7 1M) | 2026-05-07 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
