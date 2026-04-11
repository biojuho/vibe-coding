# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-11 |
| Tool | Codex |
| Work | Closed the remaining `blind-to-x` unit-suite blocker after the shared workspace audit. The real failure was not the old timeout tests: `NotionUploader` unit tests could still pick up `NOTION_DATABASE_ID` / `NOTION_PROP_*` values left behind by `.env`-loading code paths, so `tests/unit/conftest.py` now clears those env vars in the autouse isolation fixture before every test. Verified the ambient-env reproduction, kept `NOTION_PROP_*` override tests passing, and then ran the full `tests/unit` suite to green (`1481 passed, 1 skipped`). |
| Next Priorities | 1. Clean up the remaining direct Notion query HTTP 400 path in `projects/blind-to-x/pipeline/notion/_query.py` so live status/date filters stop depending on fallbacks. 2. Leave `hanwoo-dashboard` UX/UI work alone unless the user explicitly redirects the session. 3. If Moonshot should be re-enabled later, add a fresh key and re-run the shared health check. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-11 |
| Tool | Codex |
| Work | Started with a shared workspace system audit (`python workspace/execution/health_check.py --json`, `python3.13 -m code_review_graph status`, and core toolchain probes), then fixed the two governance failures it exposed. `workspace/directives/INDEX.md` now indexes the five missing harness scripts, `workspace/directives/system_audit_action_plan.md` no longer leaves archived task `T-100` open, and `python workspace/execution/health_check.py --category governance --json` passes cleanly. |
| Next Priorities | 1. Handle the remaining Moonshot-related health-check failure path. 2. Return to the outstanding `blind-to-x` timeout failures. 3. Then clean up the remaining Notion query 400 path in `pipeline/notion/_query.py`. |

## Notes

- Verification from this session:
  - `projects/blind-to-x`: ambient-env reproduction now passes after the fixture hardening: `$env:NOTION_DATABASE_ID='...'; python -m pytest --no-cov tests/unit/test_notion_upload.py -q -k update_collection_properties_uses_database_endpoint -x`
  - `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/test_notion_accuracy.py -q -k env_override_has_priority -x`
  - `projects/blind-to-x`: `python -m pytest --no-cov tests/unit/ -q` (`1481 passed, 1 skipped`)
  - `projects/blind-to-x`: `python -m ruff check tests/unit/conftest.py`
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
  - `workspace`: `python -m pytest --no-cov workspace/tests/test_health_check.py -q`
  - `workspace`: `python -m ruff check workspace/execution/health_check.py workspace/tests/test_health_check.py`
  - `workspace`: full health check now reports `overall: warn` with `fail: 0`
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
- `workspace/execution/health_check.py --json` no longer fails on governance drift or Moonshot auth; it currently reports `warn` because Moonshot and Groq are unset plus the root venv is not activated.
- The code-review graph CLI is healthy in this shell via `python3.13`; use it or the MCP tools before broad file scans when graph coverage is enough.
- `projects/blind-to-x/tests/unit/conftest.py` now clears `NOTION_DATABASE_ID` and any `NOTION_PROP_*` overrides before each unit test. If a test needs those values, set them explicitly inside the test with `monkeypatch.setenv()` / `patch.dict(...)`.
- UTF-8 markdown files in `.ai/` and `workspace/directives/` are fine on disk; earlier garbling came from the Windows cp949 console path, not file corruption.
- Do not revert unrelated in-progress edits elsewhere in the worktree.
- The required AI-context commit for this session should stage only `.ai/*` files unless the user explicitly asks for a broader commit.
