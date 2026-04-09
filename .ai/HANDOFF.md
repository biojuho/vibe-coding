# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-09 |
| Tool | Codex |
| Work | Re-checked the live `blind-to-x` Notion DB after the user's report that 2026-04-09 had no new cards. The real failure path was review-only draft generation: invalid draft-tag outputs and review-stage regeneration timeouts prevented pages from being persisted. `pipeline/process_stages/generate_review_stage.py` now lets review-only continue to Notion even when draft generation fails, `pipeline/process.py` passes the review-only flag through, `pipeline/notion/_upload.py` shows the generation error in the review memo, and review-only quality-gate retries are disabled so the queue does not burn 180s per item. After focused pytest + Ruff, two real review-only runs were executed and the live Notion count reached 5 cards on 2026-04-09 by 19:39 KST. |
| Next Priorities | 1. Clean up the remaining Notion query 400 path in `pipeline/notion/_query.py` so direct status/date queries are reliable. 2. If review-only latency grows again, inspect whether any post-generation polish steps should also be skipped for review cards. 3. Keep an eye on provider output formatting because `invalid_draft_output:*` remains a common soft-failure class. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-09 |
| Tool | Codex |
| Work | Added a daily review queue floor for `blind-to-x`. Review-only runs now count today's Notion pages, target a minimum of five cards per day, relax candidate collection and review-stage filters while the floor is unmet, and keep spam/length guards intact. Verified with targeted pytest, Ruff, and a live floor probe. |
| Next Priorities | 1. Run the next real review-only pass and confirm today's Notion count climbs toward 5 in practice. 2. If the floor still under-fills, inspect whether length/spam or draft-generation failures are the remaining bottleneck. 3. Consider surfacing `daily_queue_floor_overrides` into the Notion memo if reviewers need extra context. |

## Notes

- Verification from this session:
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
- Do not revert unrelated in-progress edits elsewhere in the worktree.
- The required AI-context commit for this session should stage only `.ai/*` files unless the user explicitly asks for a broader commit.
