# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Auto | Created |
| --- | --- | --- | --- | --- | --- |
| T-251 | `[hanwoo-dashboard]` Run Prisma 7 live CRUD E2E once a real Supabase `DATABASE_URL` is configured. Current `--live` run is blocked by placeholder `projects/hanwoo-dashboard/.env`; script guard now fails clearly on that state (`512496c`). | User/AI | Medium | 🔴 approval | 2026-05-08 |
| T-257 | `[blind-to-x]` Apply anthropic prompt caching to async draft path: refactor reviewer-memory + system preamble in `pipeline/draft_prompts.py` to be a stable cacheable block + variable suffix, then wire `cache_control` into `_generate_with_anthropic` in `pipeline/draft_providers.py`. Out of scope for T-255 because that path uses `AsyncAnthropic` directly with user-only messages. | AI | Medium | 🔴 approval | 2026-05-08 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-259 | `[shorts-maker-v2 & hanwoo-dashboard]` 콘텐츠 인텔리전스(C-1), Safe Zone QC(B-3), 파이프라인 메트릭(C-2), Next.js 16 `use cache`(A-3) 구현 완료. 1,359개 테스트 통과. | Gemini (Antigravity) | 2026-05-08 |
| T-258 | `[workspace]` Phase C AI context infra: `execution/handoff_rotator.py` (HANDOFF.md 7-day rotation, idempotent, --check/--json/--keep-days), `execution/code_review_gate.py` (deterministic risk gate wrapping code_review_graph with auto impact_radius on warn/fail, optional architecture_overview, --strict). 24 unit tests added (12 + 12). CLAUDE/AGENTS/GEMINI.md updated with rotation policy and gate workflow. First rotation applied: HANDOFF.md 279→216 줄, 9 stale addenda archived. | Claude Code (Opus 4.7 1M) | 2026-05-08 |
| T-255 | `[workspace/llm_client]` Anthropic prompt caching landed in `4303474`: `cache_strategy` (off / 5m / 1h), anthropic-only `cache_control`, cache token capture, and cost weighting for 5m writes (`1.25x`), 1h writes (`2.0x`), and cache reads (`0.10x`). Verification: relevant LLM/cache suite `181 passed`, Ruff/py_compile clean. | Codex | 2026-05-08 |
| T-253 | `[infra/llm]` Langfuse opt-in observability landed in `57c38bd`: localhost-bound v3 self-host stack, `_emit_langfuse_trace` no-op-by-default hook, JSONL metrics helper, and blind-to-x async provider attempt tracing. Verification: workspace Langfuse suite `104 passed`, blind-to-x draft provider suite `24 passed`, compose config validated. | Codex | 2026-05-08 |
| T-254 | `[workspace/eval]` Promptfoo regression eval landed in `6634d82`: Notion golden/rejected YAML extractor, promptfoo runner with baseline comparison and Telegram alert option, prompt/test assets, and generated dataset ignores. Verification: extractor tests `6 passed`, Ruff/py_compile/YAML parse clean, dry-run smoke returns expected dataset warnings. | Codex | 2026-05-08 |

- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.

### Smart Continue Lite - Auto Column Rules

- `🟢 safe`: can proceed immediately on a short "continue/go" command.
- `🔴 approval`: requires explicit user confirmation before execution.
- `🟢 safe` limit: at most 7 files changed, roughly 250 added lines, same feature/module boundary, and no package install, DB schema, auth/security, public API, stack, infra, or CI changes.
- If only `🔴 approval` tasks remain, stop and ask which one the user wants next.
