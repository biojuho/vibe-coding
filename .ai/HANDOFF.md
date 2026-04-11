# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-11 |
| Tool | Codex |
| Work | Started with a shared workspace system audit (`python workspace/execution/health_check.py --json`, `python3.13 -m code_review_graph status`, and core toolchain probes), then fixed the two governance failures it exposed. `workspace/directives/INDEX.md` now indexes the five missing harness scripts, `workspace/directives/system_audit_action_plan.md` no longer leaves archived task `T-100` open, `python workspace/execution/health_check.py --category governance --json` now passes cleanly, and the full health check is down to one real failure: `MOONSHOT_API_KEY` returns `401 Unauthorized`. |
| Next Priorities | 1. Refresh or disable the invalid Moonshot credential so shared health checks go fully green. 2. Return to the outstanding `blind-to-x` timeout-related unit test failures. 3. Clean up the remaining Notion query 400 path in `pipeline/notion/_query.py` so direct status/date queries are reliable. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-11 |
| Tool | Codex |
| Work | Ran a shared workspace system audit with `python workspace/execution/health_check.py --json`, `python3.13 -m code_review_graph status`, and core toolchain probes. The runtime stack was broadly healthy, the code-review graph database was live (`11095` nodes / `81218` edges / `819` files), and `python -m pytest` worked even though bare `pytest` was not on `PATH` without an activated venv. The audit initially failed on three operator issues: `MOONSHOT_API_KEY` returned `401 Unauthorized`, five new harness scripts were missing from `workspace/directives/INDEX.md`, and `workspace/directives/system_audit_action_plan.md` still had an unchecked `[TASK: T-100]` follow-up that no longer mapped to an active `.ai/TASKS.md` item. |
| Next Priorities | 1. Fix the shared governance drift by updating `workspace/directives/INDEX.md` and clearing or relinking the stale `T-100` follow-up. 2. Refresh or disable the invalid Moonshot credential before any workflow relies on it. 3. Then return to the outstanding `blind-to-x` timeout failures and Notion query cleanup. |

## Notes

- Verification from this session:
  - `workspace`: `python workspace/execution/health_check.py --json`
  - `workspace`: `python3.13 -m code_review_graph status`
  - `workspace`: `python --version`
  - `workspace`: `python -m pytest --version`
  - `workspace`: `python -m ruff --version`
  - `workspace`: `node --version`
  - `workspace`: `npm --version`
  - `workspace`: `git --version`
  - `workspace`: bare `pytest --version` failed because the current shell does not have the venv on `PATH`
  - `workspace`: `python workspace/execution/health_check.py --category governance --json`
  - `workspace`: governance now passes after updating `workspace/directives/INDEX.md` and `workspace/directives/system_audit_action_plan.md`
- Earlier verification from recent `blind-to-x` sessions:
  - `projects/blind-to-x`: `python -m ruff check pipeline/draft_generator.py pipeline/process.py pipeline/process_stages/generate_review_stage.py pipeline/notion/_upload.py tests/unit/test_process_stages.py tests/unit/test_pipeline_flow.py tests/unit/test_notion_upload.py`
  - `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_process_stages.py -q -x`
  - `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_pipeline_flow.py::test_process_single_post_generation_failure_review_only_uploads_card tests/unit/test_pipeline_flow.py::test_process_single_post_generation_failure_non_review_stops_before_upload -q -x`
  - `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_upload.py -q -x`
  - `projects/blind-to-x`: `python main.py --source blind --popular --review-only --limit 2` (live run; queue climbed to 4)
  - `projects/blind-to-x`: `python main.py --source blind --popular --review-only --limit 1` (first rerun exposed the remaining 180s timeout, second rerun after disabling review-only QG retries uploaded the 5th card)
  - `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_feed_collector.py tests/unit/test_process_stages.py -q`
  - `projects/blind-to-x`: `python -m ruff check main.py pipeline/daily_queue_floor.py pipeline/feed_collector.py pipeline/process.py pipeline/process_stages/filter_profile_stage.py tests/unit/test_feed_collector.py tests/unit/test_process_stages.py`
  - `projects/blind-to-x`: helper check returned `DailyQueueFloorState(target=5, current=0, remaining=5, active=True)`
  - `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_upload.py tests/unit/test_regulation_checker.py -q`
  - `projects/blind-to-x`: `python -m ruff check pipeline/notion/_upload.py pipeline/regulation_checker.py tests/unit/test_notion_upload.py tests/unit/test_regulation_checker.py`
  - `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_query_mixin.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_backfill_notion_review_columns.py tests/unit/test_notion_upload.py -q`
  - `projects/blind-to-x`: `python -m ruff check pipeline/notion/_query.py pipeline/feedback_loop.py pipeline/draft_prompts.py scripts/backfill_notion_review_columns.py scripts/check_notion_views.py docs/operations_sop.md tests/unit/test_notion_query_mixin.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_backfill_notion_review_columns.py`
  - `projects/blind-to-x`: `py -3 scripts/check_notion_views.py`
  - `projects/blind-to-x`: `py -3 scripts/backfill_notion_review_columns.py --config config.yaml`
  - `projects/blind-to-x`: `py -3 scripts/backfill_notion_review_columns.py --config config.yaml --apply`
  - `projects/blind-to-x`: `py -3 scripts/backfill_notion_review_columns.py --config config.yaml` (post-apply verification, `candidates: 0`)
- The live Notion DB now has both the reviewer schema and the historical backfill applied.
- As of 2026-04-09 19:39 KST, the live Notion review queue contains 5 non-archived cards created on 2026-04-09.
- Empty-draft review cards now tell the operator what to do instead of only showing a vague regulation warning.
- Review-only runs now try to maintain a minimum of 5 Notion cards per day.
- Review-only runs now persist fallback cards even when draft generation fails, and those cards include the draft-generation error in the Notion memo for reviewers.
- A direct Notion database query path can still return HTTP 400 for some status/date filter combinations; `get_recent_pages()` fallback queries still work and were used for the live count check.
- `workspace/execution/health_check.py --json` no longer fails on governance drift; the remaining shared-health failure is the invalid `MOONSHOT_API_KEY`.
- The code-review graph CLI is healthy in this shell via `python3.13`; use it or the MCP tools before broad file scans when graph coverage is enough.
- UTF-8 markdown files in `.ai/` and `workspace/directives/` are fine on disk; earlier garbling came from the Windows cp949 console path, not file corruption.
- Do not revert unrelated in-progress edits elsewhere in the worktree.
- The required AI-context commit for this session should stage only `.ai/*` files unless the user explicitly asks for a broader commit.
