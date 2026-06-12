# HANDOFF.md — Blind-to-X AI 릴레이 메모

## Latest Session (2026-06-12 | Claude Code | 적대적 비판 → boolean 강제 단일화 D-034)

- Work: 52회 디버그 루프가 파일별로 복붙한 `_as_bool()` 17개 변종을 근본 수정 — canonical `as_bool`/`as_optional_float`를 루트 `config.py`에 두고 `ConfigManager.get_bool()` 추가. pipeline 13개 파일의 로컬 정의를 `from config import as_bool as _as_bool`로 교체, 기본-켜짐 게이트 5곳(`daily_queue_floor`/`dedup_stage`/`fetch_stage`/`filter_profile_stage`/`viral_filter`)에 `default=True` 스레딩.
- 추가 수정: 잔존 raw-truthiness 취약 지점 7곳 — `persist_stage.py`(image AB·require_human_approval), `review_queue.py`(missing title/content 게이트 2곳), `image_generator.py`(openai.enabled), `cross_source_insight.py`(dry_run), `editorial_reviewer.py`(`is False` 비교), `draft_providers.py`(`is True` 비교), `config.py`(ProxyManager.enabled).
- scripts: standalone 4개(`notion_doctor`/`review_experiment_dry_run`/`source_preflight_evidence_doctor`/`source_preflight_strategy_simulation`)의 `_as_bool`을 canonical 본문으로 정렬 (기존엔 `"off"`→True/False가 스크립트마다 모순).
- 강제 장치: `tests/unit/test_boolean_coercion_contract.py` 신규 35개 — canonical 명세, pipeline 로컬 `_as_bool` 재정의 금지(AST 가드), scripts 사본 동작 동치, `_quote_powershell_arg` 3벌 동치, 취약 지점 회귀.
- 문서 정정: `_process_single_post_legacy()`는 이미 코드에서 제거됐는데 TASKS TODO/CONTEXT 지뢰밭 #15가 stale했음 → 정정. `classification_rules.yaml`은 활성 소비 중(단순 삭제 불가) 명시. D-034 기록.
- Tests: 계약 테스트 33+2 passed; 집중 스위트 164 passed; 전체 단위 `2503 passed, 9 skipped`; `ruff check .` pass; project QC runner `passed`.
- Notes: no commit/stage/push (워크스페이스에 광범위한 타 도구 WIP 존재). `pipeline/draft_prompts.py`/`feedback_loop.py`/`scripts/recompute_scores.py`의 `ruff format --check` 실패는 타 도구의 기존 WIP — 건드리지 않음. `pipeline/cli.py`는 내 수정 영역 포맷을 위해 `ruff format` 1회 적용.

## Latest Session (2026-06-11 | Codex | Debug loop 52)

- Work: fixed feed collector cross-source dedup config treating `dedup.cross_source_enabled: "false"` as enabled.
- Reproduction: `collect_feed_items()` with two duplicate cross-source candidates and `dedup.cross_source_enabled: "false"` returned one URL and `cross_source_dedup_count=1`.
- Root cause: feed collector used raw config truthiness for the cross-source dedup gate, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `feed_collector.py` and routed `dedup.cross_source_enabled` through it.
- Tests: focused feed collector pytest `7 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2468 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/feed_collector.py`, feed collector tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 51)

- Work: fixed bootstrap optional component flags treating `twitter.enabled: "false"` / `trends.enabled: "false"` as enabled.
- Reproduction: `init_components()` with `twitter.enabled: "false"` awaited `analytics_tracker.sync_metrics()` (`sync_await_count 1`).
- Root cause: bootstrap used raw config truthiness for optional analytics/trend startup flags, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `bootstrap.py` and routed `twitter.enabled` / `trends.enabled` startup gates through it.
- Tests: focused bootstrap cost/status pytest `13 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2465 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/bootstrap.py`, bootstrap cost/status tests, and shared `.ai` records; preserved pre-existing dirty WIP in `bootstrap.py`.

## Latest Session (2026-06-11 | Codex | Debug loop 50)

- Work: fixed source preflight problem-action logging treating `operator_action_required: "false"` as true.
- Reproduction: `_log_source_preflight_problem_actions()` with a problem action containing string `"false"` logged `operator_action_required=true`.
- Root cause: the CLI problem-action logger used raw `bool(action_item.get("operator_action_required"))`, so non-empty string `"false"` was true.
- Fix: added a narrow `_as_bool()` helper in `pipeline/cli.py` and used it for the logged `operator_action_required` flag.
- Tests: focused `test_main.py` pytest `49 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2461 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/cli.py`, `tests/unit/test_main.py`, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 49)

- Work: fixed review queue report text/artifact boolean handling treating string `"false"` as true.
- Reproduction: `format_review_queue_report()` with artifact-style `operator_action_required`, safety, command, delta, and truncation flags set to string `"false"` printed `action_required=true`, `notion_writes=true`, `x_posts=true`, `publish_command=true`, and rerun/delta hints.
- Root cause: review queue report formatting, summary, delta, and next-command helpers used raw `bool(value)` / truthiness for persisted report boolean fields, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` / `_format_bool()` in `review_queue_report.py` and routed report artifact boolean fields through them.
- Tests: focused review queue report pytest `37 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2458 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/commands/review_queue_report.py`, review queue report command tests, and shared `.ai` records; preserved pre-existing dirty WIP in the same files.

## Latest Session (2026-06-11 | Codex | Debug loop 48)

- Work: fixed source preflight strategy manual-ready gate treating `ready_for_manual_strategy_review: "false"` as ready.
- Reproduction: `_manual_ready_gate_result()` with rollout gate `ready_for_manual_strategy_review: "false"` returned `passed=True`, `status=pass`, and `exit_code=0`.
- Root cause: manual-ready gate used `bool(rollout_gate.get("ready_for_manual_strategy_review"))`, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `source_preflight_strategy_simulation.py` and routed the manual-ready flag through it.
- Tests: focused source preflight strategy pytest `16 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2451 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_preflight_strategy_simulation.py`, source preflight strategy tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 47)

- Work: fixed publish repair treating dict `fixable: "false"` as repairable.
- Reproduction: `repair_hold_draft()` with `fixable: "false"` and `external_link_in_body` stripped the URL and returned `changed=True`.
- Root cause: `_is_fixable_hold()` used `bool(decision.get("fixable"))` for dict decisions, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `publish_repair.py` and routed dict `fixable` through it.
- Tests: focused publish repair pytest `1 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2448 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/publish_repair.py`, new publish repair tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 46)

- Work: fixed publish decision treating research `value_reduction_failed: "false"` as failed.
- Reproduction: `decide_publish()` with the normal publishable fixture and `value_reduction_failed: "false"` returned `DROP` with reason `research_context value reduction failed`.
- Root cause: `_research_failed()` used `bool(research_context.get("value_reduction_failed"))`, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `publish_decision.py` and routed the research failure flag through it.
- Tests: focused publish decision pytest `7 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2444 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/publish_decision.py`, publish decision tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 45)

- Work: fixed fetch-stage scrape integrity config treating `scrape_quality.integrity_check_enabled: "false"` as enabled.
- Reproduction: `run_fetch_stage()` with config string `"false"` still called `classify_scrape_integrity()`; a failing classifier verdict made fetch return `False`.
- Root cause: fetch stage used `bool(config.get("scrape_quality.integrity_check_enabled", True))`, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `fetch_stage.py` and routed the integrity-check enabled flag through it.
- Tests: focused process stage pytest `55 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2442 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/process_stages/fetch_stage.py`, process stage tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 44)

- Work: fixed provider failure summaries treating string `"false"` retry/circuit flags as true.
- Reproduction: `summarize_provider_failures()` with `retryable: "false"` and `circuit_breaker_candidate: "false"` produced `retryable_count=1`, `non_retryable_count=0`, and `circuit_breaker_providers=["gemini"]`.
- Root cause: summary aggregation and failure brief used raw truthiness / `bool(value)` for string flags.
- Fix: added `_as_bool()` in `draft_generator.py` and reused parsed retry/circuit flags across counts, provider lists, primary priority, and failure brief.
- Tests: focused draft generator multi-provider pytest `14 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2438 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/draft_generator.py`, draft generator multi-provider tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 43)

- Work: fixed provider readiness treating explicit provider `enabled: "false"` as enabled.
- Reproduction: `_provider_key_diagnostics()` with `anthropic.enabled: "false"` and no Anthropic key returned `operator_action_required=True`, `missing_enabled_providers=["anthropic"]`, and `enabled=True`.
- Root cause: `_provider_explicitly_enabled()` used `bool(explicit)`, so non-empty string `"false"` was true.
- Fix: routed explicit provider enabled values through `_as_bool()`.
- Tests: focused notion doctor pytest `26 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2436 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/notion_doctor.py`, notion doctor tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 42)

- Work: fixed `notion_doctor` publish safety treating `twitter.enabled: "false"` as enabled.
- Reproduction: `_publish_safety_diagnostics()` with publish env flags cleared and config string `"false"` returned `operator_action_required=True`, `severity=warning`, and `twitter_config_enabled=True`.
- Root cause: publish safety diagnostics used `bool(config.get("twitter.enabled", False))`, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `scripts/notion_doctor.py` and routed `twitter.enabled` through it for publish safety.
- Tests: focused notion doctor pytest `25 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2433 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/notion_doctor.py`, notion doctor tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 41)

- Work: fixed daily queue floor `review.minimum_daily_queue_relax_per_source_limits: "false"` still relaxing per-source limits.
- Reproduction: `collect_feed_items()` with active daily queue floor, per-source limit `{"blind": 1}`, and config string `"false"` returned 3 Blind items instead of preserving the 1-item source cap.
- Root cause: `relax_per_source_limits()` used `bool(config.get(...))`, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `daily_queue_floor.py` and routed the per-source relaxation flag through it.
- Tests: focused feed collector pytest `6 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2429 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/daily_queue_floor.py`, feed collector tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 40)

- Work: fixed `ranking.llm_viral_boost: "false"` being passed to content profile builder as true.
- Reproduction: `_build_content_profile_dict()` with config string `"false"` passed `llm_viral_boost=True` to `build_content_profile()`.
- Root cause: filter profile stage used `bool(config.get("ranking.llm_viral_boost", False))`, so non-empty string `"false"` was true.
- Fix: routed `ranking.llm_viral_boost` through `_as_bool()`.
- Tests: focused process stage pytest `54 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2425 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/process_stages/filter_profile_stage.py`, process stage tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 39)

- Work: fixed ViralFilter config string `"false"` being treated as enabled.
- Reproduction: `ViralFilter({"viral_filter.enabled": "false", "gemini.api_key": "dummy"})._enabled` was `True`.
- Root cause: `ViralFilter.__init__()` used `bool(config.get("viral_filter.enabled", True))`, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `viral_filter.py` and routed `viral_filter.enabled` through it.
- Tests: focused viral filter pytest `11 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2422 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/viral_filter.py`, viral filter tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 38)

- Work: fixed dedup stage config string `"false"` not disabling Notion similarity checks.
- Reproduction: `dedup.notion_check_enabled: "false"` still awaited `find_similar_in_notion()` and blocked the post as `DUPLICATE_CONTENT`.
- Root cause: dedup stage used `bool(config.get("dedup.notion_check_enabled", True))`, so non-empty string `"false"` was treated as enabled.
- Fix: added `_as_bool()` in `dedup_stage.py` and routed the Notion similarity-check config through it.
- Tests: focused process stage pytest `53 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2417 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/process_stages/dedup_stage.py`, process stage tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 37)

- Work: fixed editorial gate config string `"false"` not disabling the gate.
- Reproduction: `_check_editorial_fit()` with `feed_filter.editorial_gate_enabled: "false"` still returned `False` with `failure_reason=editorial_hard_reject`.
- Root cause: filter profile stage used `not bool(config.get(...))`, so non-empty string `"false"` was treated as enabled.
- Fix: routed editorial gate enabled config through `_as_bool()`.
- Tests: focused process stage pytest `52 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2412 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/process_stages/filter_profile_stage.py`, process stage tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 36)

- Work: fixed editorial fit gate treating `hard_reject: "false"` as a hard reject.
- Reproduction: `_check_editorial_fit()` with score `70.0` and `hard_reject: "false"` returned `False` with `failure_reason=editorial_hard_reject`.
- Root cause: filter profile stage used Python truthiness for `fit["hard_reject"]`, so non-empty string `"false"` was true.
- Fix: added `_as_bool()` in `filter_profile_stage.py` and routed hard-reject gating/failure reason selection through it.
- Tests: focused process stage pytest `51 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2411 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/process_stages/filter_profile_stage.py`, process stage tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 35)

- Work: fixed review experiment operator action sorting treating priority 0 as priority 999.
- Reproduction: `_operator_actions()` returned `[('resolve_x_publish_status', 40), ('review_queue_action', 0)]`, putting a zero-priority review queue action behind lower-priority actions.
- Root cause: operator-action sorting and top-action aggregation used `int(... or 999)`, so valid numeric `0` became the default sort priority.
- Fix: added `_priority_value()` and routed operator-action sorting, candidate top action aggregation, and console top action aggregation through it.
- Tests: focused review experiment pytest `31 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2404 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/review_experiment_dry_run.py`, review experiment focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 34)

- Work: fixed recompute-score dry-run replacing explicit scrape quality score 0 with default 70.
- Reproduction: `_score_update_from_record()` with `scrape_quality_score: 0` passed `70.0` to `build_content_profile()`.
- Root cause: `_score_update_from_record()` used `float(record.get("scrape_quality_score") or 70)`, so valid numeric `0` was treated as missing.
- Fix: score update now defaults to `70.0` only when the source value is `None` or an empty string; explicit numeric/string zero is preserved.
- Tests: reproduction replay now passes `0.0`; focused recompute-score pytest `21 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2401 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/recompute_scores.py`, recompute-score focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 33)

- Work: fixed adaptive feedback weights dropping valid zero score metrics.
- Reproduction: five performance records with one `scrape_quality_score: 0` produced `{}` because the first record was excluded and the minimum valid count fell to four.
- Root cause: `compute_adaptive_weights()` used truthiness checks for score presence and `or 50` score fallback, so numeric `0` was treated as missing.
- Fix: adaptive-weight input normalization now converts values through `_optional_float()` and treats only `None`, blank strings, and non-numeric values as missing; zero remains valid.
- Tests: reproduction replay now returns non-empty weights; focused feedback-loop pytest `24 passed`; targeted ruff check passed; full Blind-to-X project QC passed with unit `2396 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `pipeline/feedback_loop.py`, feedback-loop focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 32)

- Work: fixed review experiment replacing explicit review queue priority 0 with default priority 15.
- Reproduction: a ready fixture with `review_queue_priority: 0` produced action priority `15`.
- Root cause: `_operator_actions()` used `int(_as_float(priority) or 15)`, so valid numeric `0.0` was treated as missing.
- Fix: review queue action priority now uses default `15` only when `_as_float()` returns `None`.
- Tests: reproduction replay now returns action priority `0`; focused review experiment pytest `30 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2390 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/review_experiment_dry_run.py`, review experiment focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 31)

- Work: fixed review experiment X publish status action matching being case-sensitive.
- Reproduction: a ready fixture with `x_publish_status: " failed "` produced `operator_action_required=False` and no actions.
- Root cause: status checks compared stripped text only against exact-case blocked labels (`Needs Edit`, `Blocked`, `Failed`).
- Fix: added `_x_publish_status_requires_action()` and routed operator-action aggregation/action generation through strip+lower matching.
- Tests: reproduction replay now returns required `True`, `resolve_x_publish_status`, and reason `failed`; focused review experiment pytest `29 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2388 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/review_experiment_dry_run.py`, review experiment focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 30)

- Work: fixed review experiment treating blank `review_queue_operator_action` as requiring operator action.
- Reproduction: a ready fixture with `review_queue_operator_action: "   "` produced `operator_action_required=True` while `operator_actions=[]`.
- Root cause: `_objective_metric_snapshot()` truth-tested the raw action string, while operator action generation strips blank text.
- Fix: review queue operator action is now stripped before contributing to `operator_action_required`.
- Tests: reproduction replay now returns `success=True`, candidate required `False`, and no actions; focused review experiment pytest `28 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2384 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/review_experiment_dry_run.py`, review experiment focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 29)

- Work: fixed review experiment replacing explicit zero draft quality scores with average fallback values.
- Reproduction: a fixture with `_quality_gate_score: 0` and `quality_gate_scores: [9, 10]` produced `draft_quality_score=9.5`.
- Root cause: `_draft_quality_score()` returned `primary_score or average`, so valid numeric `0.0` was treated as missing.
- Fix: primary draft quality score now returns whenever it is not `None`; fallback average is used only when no primary score exists.
- Tests: reproduction replay now returns `draft_quality_score=0.0`; focused review experiment pytest `27 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2382 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/review_experiment_dry_run.py`, review experiment focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 28)

- Work: fixed review experiment duplicate string flags being ignored or overwritten by similarity fallback.
- Reproduction: `duplicate_or_near_duplicate: "true"` produced duplicate `False` with no actions, while `duplicate_or_near_duplicate: "false"` plus high similarity produced duplicate `True` and `rewrite_duplicate_draft`.
- Root cause: `_duplicate_or_near_duplicate()` only respected explicit boolean values; string flags fell through to similarity scoring.
- Fix: explicit duplicate fields now use `_as_bool()` whenever present, before semantic-similarity fallback.
- Tests: reproduction replay now returns string true -> duplicate `True` with rewrite action, and string false plus high similarity -> duplicate `False` with no actions; focused review experiment pytest `26 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2379 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/review_experiment_dry_run.py`, review experiment focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 27)

- Work: fixed review experiment treating `draft_generation_failed="false"` as a failed draft.
- Reproduction: a ready fixture with publishable draft text and `draft_generation_failed: "false"` produced `success=False`, `operator_action_required=True`, and `regenerate_draft_after_recovery`.
- Root cause: `_draft_success()` and `_objective_metric_snapshot()` interpreted generation-failed flags through Python truthiness, so the non-empty string `"false"` became true.
- Fix: added `_draft_generation_failed()` and routed success/operator-action aggregation through `_as_bool(_first_present(...))`.
- Tests: reproduction replay now returns `success=True`, candidate required `False`, and no actions; focused review experiment pytest `25 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2376 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/review_experiment_dry_run.py`, review experiment focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 26)

- Work: fixed review experiment candidate signals treating provider failure `operator_action_required="false"` as required.
- Reproduction: a ready fixture with successful draft output and provider failure metadata `operator_action_required: "false"` produced `provider_failure_summary.operator_action_required=False` but candidate `operator_action_required=True` with no operator actions.
- Root cause: `_objective_metric_snapshot()` reused `bool(failure.get("operator_action_required"))` instead of the existing `_as_bool()` parser, so the non-empty string `"false"` became true.
- Fix: provider failure required aggregation now uses `_as_bool()` consistently with provider failure summary sanitization.
- Tests: reproduction replay now returns `success=True`, provider summary required `False`, candidate required `False`, and no actions; focused review experiment pytest `24 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2371 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/review_experiment_dry_run.py`, review experiment focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 25)

- Work: fixed recompute-score input validation accepting falsey non-array `historical_examples`.
- Reproduction: a JSON fixture with valid records and `historical_examples: ""` returned `status=ok`, `ok=True`, `historical_example_count=0`, and no errors.
- Root cause: `_load_input_records()` used `payload.get("historical_examples") or []`, so explicit falsey non-array values were silently converted to an empty list before the existing type check.
- Fix: `historical_examples` now defaults to `[]` only when the key is absent; explicit values are preserved and validated as arrays.
- Tests: reproduction replay now returns `status=fail`, `ok=False`, error `recompute_scores historical_examples must be an array`, and no warnings; focused recompute-score pytest `20 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2366 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/recompute_scores.py`, recompute-score focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 24)

- Work: fixed recompute-score input validation rejecting explicit empty `records` arrays.
- Reproduction: a JSON fixture with `{"records": [], "historical_examples": [], "candidate_ranking_weights": {"hook": 1.0}}` returned `status=fail`, `ok=False`, error `recompute_scores input must include a records/pages/items array`, and no `records_empty` warning.
- Root cause: `_load_input_records()` selected object input records through `payload.get("records") or payload.get("pages") or payload.get("items")`, so an explicit empty list was treated as missing and replaced with `None`.
- Fix: record-source selection now uses key presence for `records/pages/items`, preserving explicit empty arrays while still falling back when a key is absent.
- Tests: reproduction replay now returns `status=ok`, `ok=True`, `record_count=0`, `errors=[]`, `warnings=['records_empty']`; focused recompute-score pytest `19 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2359 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/recompute_scores.py`, recompute-score focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 23)

- Work: fixed source browser preflight empty-result reports being marked successful.
- Reproduction: `build_report([])` emitted `source_count=0`, `ready_count=0`, `problem_count=0`, `ok=True`, and `exit_code_for_report(..., fail_on_problem=True)=0`.
- Root cause: `_build_summary()` used `len(ready_sources) == len(results)` for `ok`, which is vacuously true when no probe results exist.
- Fix: `ok` now requires at least one result and all results ready: `bool(results) and len(ready_sources) == len(results)`.
- Tests: focused source browser probe pytest `40 passed`; related source-preflight pytest `94 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2354 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_browser_probe.py`, source browser focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 22)

- Work: fixed source browser failure artifact filename collisions for unsafe custom source names.
- Reproduction: two problem results with sources `!!!` and `@@@` both wrote `source-blocked.json`; the second failure report overwrote the first, leaving only one file and the first path reading source `@@@`.
- Root cause: `_with_failure_evidence()`, screenshots, and HTML snapshots used `_safe_slug(source)` directly; all-non-safe or non-ASCII source names collapse to fallback slug `source`.
- Fix: added `_source_artifact_slug()` and routed source-derived failure report, screenshot, click screenshot, and HTML snapshot filenames through it. Existing safe names keep their old paths; fallback `source` names get a stable short hash suffix.
- Tests: focused source browser probe pytest `39 passed`; related source-preflight pytest `93 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2350 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_browser_probe.py`, source browser focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 21)

- Work: fixed source preflight legacy inference trusting invalid failure-report `operator.action_required=false`.
- Reproduction: a legacy problem action with a failure report containing `operator.action_required=false` and a non-empty `operator.action` produced `DOCTOR_STATUS FAIL` but also `operator_action_required=False` and trend `operator_action_required_count=0`.
- Root cause: `build_evidence_payload()` used `failure_report.operator.action_required` for legacy inference whenever the field existed, even when `_validate_failure_report()` had already marked the report invalid with `operator_action_not_required`.
- Fix: failure-report operator-required values are trusted only when the failure report is valid; invalid reports fall back to non-empty operator action or non-ready status so they still require operator attention.
- Tests: focused evidence/trend pytest `39 passed`; related source-preflight pytest `92 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2348 passed, 9 skipped` and lint pass.
- Notes: first full QC attempt hit a transient `NameError: preparation` in `pipeline/draft_prompts.py`; the single failing test rerun passed and final full QC passed without editing that file. No commit/stage/push.

## Latest Session (2026-06-11 | Codex | Debug loop 20)

- Work: fixed source preflight failure-report `operator.action_required` string boolean validation.
- Reproduction: a valid failure report with `operator.action_required="true"` produced `DOCTOR_STATUS FAIL`, `failure_report_status=invalid`, issue `operator_action_not_required`, and trend `failure_report_status_counts={'invalid': 1}`.
- Root cause: `_validate_failure_report()` still used `operator.get("action_required") is not True`, so semantically true string values were rejected even after Loop 19 introduced explicit bool coercion for operator-required fields.
- Fix: routed failure-report operator validation through `_as_bool()` while preserving invalid handling for false values.
- Tests: focused evidence/trend pytest `37 passed`; related source-preflight pytest `90 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2343 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_preflight_evidence_doctor.py`, evidence/trend focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 19)

- Work: fixed source preflight string boolean parsing for `operator_action_required`.
- Reproduction: a problem action with `operator_action_required="false"` produced `operator_action_required=True` in the evidence doctor and `operator_action_required_count=1` in trend output because Python treats non-empty strings as truthy.
- Root cause: `build_evidence_payload()` used `bool(value)` for explicit problem-action `operator_action_required` and failure-report `operator.action_required`.
- Fix: added explicit boolean coercion for real booleans, numeric values, and common string forms (`true/false`, `1/0`, `yes/no`, `on/off`) before computing operator-action fields.
- Tests: focused evidence/trend pytest `35 passed`; related source-preflight pytest `88 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2338 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_preflight_evidence_doctor.py`, evidence/trend focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 18)

- Work: fixed source preflight negative `--max-files` directory selection.
- Reproduction: with two matching reports, `--input-dir ... --max-files -1` selected the older file in both trend and strategy input selection because Python slicing treated `matches[:-1]` as "all but latest".
- Root cause: duplicated `_input_paths()` logic passed `args.max_files` directly into list slicing without normalizing negative values.
- Fix: trend report and strategy simulation now clamp `max_files` to `>= 0` before slicing, so 0 or negative values select no files instead of an unintended subset.
- Tests: focused trend/strategy pytest `31 passed`; related source-preflight pytest `86 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2331 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_preflight_trend_report.py`, `scripts/source_preflight_strategy_simulation.py`, their focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 17)

- Work: fixed source preflight explicit empty `--input-dir` fallback to default input.
- Reproduction: with a valid default `.tmp/source_browser_preflight.json` present, running trend/strategy input selection with `--input-dir empty` returned the default file instead of zero paths, so reports were generated from a file the operator did not select.
- Root cause: duplicated `_input_paths()` logic appended `DEFAULT_INPUT_PATH` whenever the collected path list was empty, without distinguishing no selector from an explicit selector with zero matches.
- Fix: trend report and strategy simulation now fall back to the default input only when no `--input` or `--input-dir` selector was provided.
- Tests: focused trend/strategy pytest `29 passed`; related source-preflight pytest `84 passed`; targeted ruff format/check passed; final full Blind-to-X project QC passed with unit `2327 passed, 9 skipped` and lint pass.
- Notes: the first project QC attempt had unit `2325 passed, 9 skipped` but a transient lint syntax error in `tests/unit/test_draft_prompts.py`; direct `ruff check`/`py_compile` on that file and the final full QC passed without source edits there. No commit/stage/push.

## Latest Session (2026-06-11 | Codex | Debug loop 16)

- Work: fixed source preflight legacy operator-action inference from failure reports.
- Reproduction: a structurally valid timeout evidence report with a legacy problem action missing `action`, `operator_action`, and `operator_action_required` produced `operator_action_required=False`, empty `operator_action`, trend `operator_action_required_count=0`, and no top operator action despite the failure report containing `operator.action`.
- Root cause: `build_evidence_payload()` decided operator action fields before loading the failure report and never backfilled them from `failure_report.operator`.
- Fix: when the problem action does not explicitly set `operator_action_required`, the doctor now uses the failure report operator block or failure status to infer required/action fields, while preserving explicit false values.
- Tests: focused evidence/trend pytest `31 passed`; related source-preflight pytest `82 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2322 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_preflight_evidence_doctor.py`, `tests/unit/test_source_preflight_evidence_doctor.py`, `tests/unit/test_source_preflight_trend_report.py`, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 15)

- Work: fixed source preflight manual-ready fallback-only repair command drift.
- Reproduction: fallback-only complete evidence correctly had `summary.repair_command_count=0`, but `--require-manual-ready --json` still returned `manual_ready_gate.repair_command_count=1` and a synthesized `source_preflight_evidence_doctor.py` command.
- Root cause: `_manual_repair_commands()` fell back to synthetic evidence-doctor commands whenever the real repair queue/top commands were empty, even for fallback-only gates that need operator fallback use rather than evidence repair.
- Fix: manual-ready repair commands now come only from actual `summary.repair_command_queue` / `top_repair_commands`; fallback-only blocked gates keep an empty repair command list.
- Tests: focused strategy pytest `13 passed`; related source-preflight pytest `80 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2317 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_preflight_strategy_simulation.py`, `tests/unit/test_source_preflight_strategy_simulation.py`, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 14)

- Work: fixed source preflight strategy simulation `current.strategy_review_count` metric drift.
- Reproduction: mixed strategy-ready/fallback evidence had `evidence_gate_status_counts={"strategy_review_ready": 1, "fallback_only": 1}`, but current variant reported `strategy_review_count=2` and comparison reported `strategy_review_delta=-1`.
- Root cause: `_current_strategy_signals()` populated `strategy_review_count` with total `problem_count` instead of the actual `strategy_ready_count`.
- Fix: current variant now records `strategy_review_count=strategy_ready_count`, matching the candidate variant and evidence gate counts.
- Tests: focused strategy pytest `12 passed`; related source-preflight pytest `79 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2311 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_preflight_strategy_simulation.py`, `tests/unit/test_source_preflight_strategy_simulation.py`, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 13)

- Work: fixed source preflight relative `--base-dir` plus explicit relative `--input` path resolution.
- Reproduction: `--base-dir .tmp/relative-base-loop13 --input .tmp/relative-base-loop13/source_browser_preflight.json` was resolved as `.tmp/relative-base-loop13/.tmp/relative-base-loop13/source_browser_preflight.json`, causing missing JSON / `invalid_evidence`.
- Root cause: trend, strategy, and evidence-doctor input path resolution reused the evidence artifact resolver, which always prefixes relative paths with `base_dir`.
- Fix: added explicit-input resolvers that preserve relative paths already pointing inside `base_dir`, while keeping default/evidence artifact paths base-dir relative.
- Tests: focused evidence/trend/strategy pytest `41 passed`; related source-preflight pytest `79 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2306 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched source preflight evidence/trend/strategy scripts, their focused tests, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 12)

- Work: fixed weekly smoke `--self-check --manifest-output` artifact consistency.
- Reproduction: running `write_weekly_smoke_inputs.py --self-check --manifest-output ... --json` printed a payload containing `self_check`, but the manifest written to disk did not include `self_check`.
- Root cause: `main()` wrote the manifest before computing `build_self_check_payload()` and never rewrote the artifact after adding `payload["self_check"]`.
- Fix: after self-check computation, rewrite `manifest_output` with the final payload so stdout and disk manifest match.
- Tests: writer focused pytest `15 passed`; related weekly smoke/report pytest `108 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2299 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/write_weekly_smoke_inputs.py`, `tests/unit/test_write_weekly_smoke_inputs.py`, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 11)

- Work: fixed weekly smoke manifest copy-ready command quoting for PowerShell metacharacter output/manifest paths.
- Reproduction: `commands.write_inputs` emitted `py -3 scripts/write_weekly_smoke_inputs.py --output-dir .tmp/weekly&smoke-loop11 --manifest-output .tmp/weekly&smoke-loop11/manifest.json`; PowerShell parsing failed with `AmpersandNotAllowed`.
- Root cause: `write_weekly_smoke_inputs.py` still used cmd.exe-oriented `subprocess.list2cmdline()` for PowerShell-facing manifest commands; the manifest validator also only accepted unquoted/double-quoted path fragments for some options.
- Fix: added a PowerShell literal-safe formatter in `scripts/write_weekly_smoke_inputs.py`, updated `scripts/verify_weekly_smoke.py` to accept single-quoted path fragments, and added `&` path regression coverage.
- Tests: writer focused pytest `15 passed`; related weekly smoke/report pytest `108 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2293 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/write_weekly_smoke_inputs.py`, `scripts/verify_weekly_smoke.py`, `tests/unit/test_write_weekly_smoke_inputs.py`, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 10)

- Work: fixed `source_preflight_evidence_doctor` trace viewer command quoting for PowerShell metacharacter trace paths.
- Reproduction: `_trace_viewer_command(".tmp/traces/source&preflight.zip")` emitted `playwright show-trace .tmp/traces/source&preflight.zip`; PowerShell parsing failed with `AmpersandNotAllowed`.
- Root cause: `source_preflight_evidence_doctor.py` used cmd.exe-oriented `subprocess.list2cmdline()` for copy-ready PowerShell operator commands, leaving bare metacharacters when no whitespace forced quoting.
- Fix: added a PowerShell literal-safe formatter in `scripts/source_preflight_evidence_doctor.py` and routed evidence doctor command generation through it.
- Tests: evidence doctor focused pytest `15 passed`; related preflight pytest `76 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2290 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_preflight_evidence_doctor.py`, `tests/unit/test_source_preflight_evidence_doctor.py`, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | T-2373)

- Work: refreshed current auto-research blocker evidence after Blind-to-X debug loop 8, without Blind-to-X product/source edits.
- Current proof: dirty handoff plan is current at dirty `167`, staged `0`, ahead `919`, signature `223d7ec3d70841fb86d4ca0c7682d988960b79528f61de1285145d2c1414ad19`.
- Selector: `blocked / dirty_worktree_handoff_current / adoptable_candidate_count=0`; scoped authorization menu check remains `ok`, rendered matches, uncovered `0/0`.
- Completion: launch completion audit remains `incomplete` (`15` items, `6` complete, `15` issues, `9` blocked); debug inventory expected-exited `1` with `5` blocked and `0` actionable.
- Guardrails: no stage/commit/push/revert, no cleanup `--apply`, no live provider/Notion/X/DB calls, no T-251 retry, and no `update_goal`.

## Latest Session (2026-06-11 | Codex | T-2372)

- Work: fixed auto-research debug inventory input loading so UTF-16 JSON artifacts written by PowerShell do not masquerade as the expected completion-blocked exit path.
- Root cause: `debug_loop_inventory.py` treated unreadable/UTF-16 JSON inputs as `{}`, then still exited with the completion-blocked code when `--fail-on-completion-blocked` was enabled.
- Fix: `.agents/skills/auto-research/scripts/debug_loop_inventory.py` now reads JSON inputs with UTF-8-SIG first and falls back to UTF-16 before returning empty data for genuinely missing/invalid inputs.
- Tests: `workspace/tests/test_auto_research_debug_loop_inventory.py` adds UTF-16 CLI coverage for provided session/selector/readiness/audit/dirty-handoff artifacts.
- Verification: focused pytest `63 passed`; `py_compile` passed; targeted `ruff check` and `ruff format --check` passed; live debug inventory rerun returned expected completion-blocked exit 1 with `blocked=5`, `actionable=0`.
- Guardrails: no Blind-to-X product/source edits, no stage/commit/push/revert, no cleanup `--apply`, no live provider/Notion/X/DB calls, no T-251 retry, and no `update_goal`.

## Latest Session (2026-06-11 | Codex | Debug loop 9)

- Work: fixed `source_browser_probe` PowerShell copy-ready trace viewer/repair command quoting for metacharacter paths.
- Reproduction: `_build_trace_viewer_guidance({"trace_path": ".tmp/traces/source&preflight.zip"})` emitted `& playwright show-trace .tmp/traces/source&preflight.zip`; PowerShell parsing failed with `AmpersandNotAllowed`.
- Root cause: `source_browser_probe.py` used `subprocess.list2cmdline()`, which is cmd.exe-oriented and leaves PowerShell metacharacters such as `&` bare when no whitespace forces quotes.
- Fix: added a PowerShell literal-safe formatter in `scripts/source_browser_probe.py` and routed recommended, trace viewer, and evidence repair commands through it.
- Tests: source browser focused pytest `38 passed`; related preflight pytest `75 passed`; targeted ruff format/check passed; full Blind-to-X project QC passed with unit `2282 passed, 9 skipped` and lint pass.
- Notes: no commit/stage/push. This loop touched `scripts/source_browser_probe.py`, `tests/unit/test_source_browser_probe.py`, and shared `.ai` records.

## Latest Session (2026-06-11 | Codex | Debug loop 8)

- Work: fixed `project_qc_runner.py --project blind-to-x --json` progress-only/false-fail behavior after successful pytest output.
- Reproduction: runner test check emitted full pytest success stdout (`2270 passed, 9 skipped`) but returned Windows `4294967295`, causing status `failed` and exit 1; direct resolved pytest command exited 0.
- Root cause: Windows/Popen pytest capture can report a post-success sentinel return code even when pytest stdout has a clean success summary and stderr is empty.
- Fix: root `execution/project_qc_runner.py` now normalizes only pytest commands with returncode `-1`/`4294967295`, empty stderr, and a successful pytest summary; raw returncode/reason are preserved when normalization happens.
- Tests: workspace project_qc_runner pytest `19 passed`; targeted ruff format/check passed; reproduced runner command now passes and writes partial artifact. Latest Blind-to-X runner output: unit `2278 passed, 9 skipped`; lint pass.
- Notes: this touched root `execution/project_qc_runner.py` and `workspace/tests/test_project_qc_runner.py` in addition to project context files. No commit was made because the workspace has broad unrelated WIP.

## Latest Session (2026-06-11 | Codex | Debug loop 7)

- Work: fixed review queue report follow-up commands when output artifact paths contain PowerShell metacharacters such as `&`.
- Reproduction: built `operator_next_commands[0].command` with `artifact_path=.tmp/review&queue-loop7.json`; PowerShell `Invoke-Expression` failed with `AmpersandNotAllowed`.
- Root cause: `_quote_command_arg()` only quoted whitespace/quote characters, so PowerShell metacharacters could remain bare in copy-ready commands.
- Fix: `pipeline/commands/review_queue_report.py` now quotes any arg outside a conservative shell-safe character set.
- Tests: review queue command focused pytest `36 passed`; related main/runner pytest `92 passed`; targeted ruff format/check passed; direct full unit suite `2270 passed, 9 skipped`; full `ruff check .` passed.
- Notes: `project_qc_runner.py --project blind-to-x --json` twice returned progress-only exit 1 with no fresh Blind-to-X artifact and no surviving Blind-to-X pytest child. Direct full pytest/lint passed using the same project venv and repo-local basetemp.

## Latest Session (2026-06-11 | Codex | Debug loop 6)

- Work: fixed weekly smoke copy-ready commands when `--output-dir` or `--manifest-output` contains spaces.
- Reproduction: generated `.tmp/weekly smoke loop6/manifest.json`, copied `commands.write_inputs`, and PowerShell `Invoke-Expression` failed with argparse `unrecognized arguments: smoke loop6 ...` / exit 2.
- Root cause: manifest command generation used unquoted f-strings for path args; the manifest validator also rejected valid quoted path-valued options.
- Fix: `scripts/write_weekly_smoke_inputs.py` now builds command strings with `subprocess.list2cmdline()`, and `scripts/verify_weekly_smoke.py` accepts quoted path-valued command fragments for manifest contract checks.
- Tests: focused writer/verifier pytest `81 passed`; targeted ruff format/check passed; project QC passed with unit `2258 passed, 9 skipped` and lint pass.
- Notes: `code-review-graph` MCP tools were not exposed in this environment, so verification used deterministic pytest/ruff/QC gates. No commit was made because the workspace has broad unrelated WIP.

## Latest Session (2026-06-11 | Codex | T-2368)

- Work: auto-research handoff-only approval packet refresh after concurrent dirty drift.
- Scope: no Blind-to-X product/source edits by this handoff task. Root approval surface now covers dirty `167/167` with `81` pathspec packets and real staged `0`.
- Added root ignored packets: `APPROVE_SHORTS_MAKER_V2_HISTORY_FACT_SHORTS`, `APPROVE_SHORTS_MAKER_V2_TOOL_PILLOW_DEPRECATIONS`, `APPROVE_WORKSPACE_HANDOFF_ROTATOR_SUFFIX_HEADING`, `APPROVE_WORKSPACE_TASKS_DONE_ROTATOR_CHECKLISTS`, and `APPROVE_BLIND_TO_X_REVIEW_QUEUE_REPORT_COMMAND`.
- Verification: Shorts Maker V2 focused history fact test `8 passed`, tool Pillow deprecation test `7 passed`, matching `py_compile` checks, workspace handoff rotator test `19 passed`, workspace tasks done rotator test `12 passed`, and Blind-to-X review queue report command test `36 passed`.
- Current selector: `blocked / dirty_worktree_handoff_current / adoptable_candidate_count=0`; completion audit remains `incomplete` (`15` items, `6` complete, `15` issues, `9` blocked).
- Guardrails: no `update_goal`, stage, commit, push, revert, cleanup `--apply`, product edit, live provider call, or T-251 retry.

## 마지막 세션 (2026-06-11 | Codex)

| 항목 | 내용 |
|---|---|
| 작업 | 자율 디버깅 루프 0단계+3개 루프: QC runner 일시 실패 재현성 확인, ambient Python 환경 분리, formatter gate 수정 |
| 상태 | ✅ 완료 |
| 테스트 | `ruff format --check .`, `ruff check .`, 관련 pytest 64개, `project_qc_runner.py --project blind-to-x --json` 통과 |

### 디버깅 루프 결과

- B-001: `project_qc_runner.py --project blind-to-x --json`가 최초 1회 `returncode 4294967295`로 실패했지만, 동일 커맨드/수동 basetemp A-B/재실행에서 안정 재현되지 않았다. 최종 표준 QC는 `2208 passed, 9 skipped`, lint pass.
- B-002: ambient `python`은 프로젝트 `.venv`가 아니라 pytest-cov/cloudinary/playwright 누락으로 실패한다. 프로젝트 표준은 `.venv` 또는 `project_qc_runner.py`이며, `.venv` 기본 pytest는 coverage 포함 `2203 passed, 9 skipped`로 통과했다. 코드 버그가 아니라 실행환경 주의사항으로 분리.
- B-003: `ruff format --check .`가 `pipeline/draft_prompts.py`에서 실패. `ruff format pipeline\draft_prompts.py`로 포맷/줄끝 상태를 정리했고 재검증 통과.

### 다음 AI에게

- 테스트는 ambient `python` 대신 `projects/blind-to-x\.venv\Scripts\python.exe` 또는 워크스페이스 루트의 `python execution\project_qc_runner.py --project blind-to-x --json`를 사용.
- `.tmp` 안의 오래된 pytest 임시 디렉터리는 Windows 권한 잠금으로 `rg` 접근 거부를 낼 수 있다. QC 자체는 repo-local basetemp로 통과하므로, 실패로 단정하지 말고 표준 runner 결과를 우선한다.

## 마지막 세션 (2026-05-22 | Claude Code)

| 항목 | 내용 |
|---|---|
| 작업 | 수집·선별 정확도 고도화 — 편집 적합도 게이트 (D-032) + 스크레이프 무결성 게이트 (D-033) |
| 상태 | ✅ 완료 |
| 테스트 | 유닛 테스트 전건 통과, ruff clean |

### D-033 — 스크레이프 콘텐츠 무결성 게이트 (수집 정확도)

문제: Blind처럼 콘텐츠를 로그인 뒤로 가두는 사이트는 세션 쿠키 만료 시 로그인 월 HTML을
반환한다. 스크래퍼는 이를 '성공'으로 보고 한국어 텍스트를 추출하고, 그 텍스트는
`assess_quality`(한국어 비율·길이)를 통과해 검토 큐를 오염시킨다. 추출한 것이 게시물이
맞는지 검증하는 레이어가 없었다.

해결:
- `pipeline/scrape_integrity.py` 신규 — 하드(봇 차단·캡차, 길이 무관)/소프트(로그인·삭제,
  본문 짧을 때만) 2계층 시그니처로 비-게시물을 결정론 분류.
- `fetch_stage._check_scrape_integrity()` — `assess_quality` 직전에 실행. 모든 소스 공통
  chokepoint. `blocked`→`SCRAPE_FAILED`, `non_article`→`SCRAPE_PARSE_FAILED`.
- 설정: `scrape_quality.integrity_check_enabled`(기본 true), `min_article_chars`(기본 220).
- 테스트: `test_scrape_integrity.py` 14개 + `TestFetchStage` 통합 3개.

### D-032 — 본문 포함 편집 적합도 게이트 (선별 정확도)

### 배경 — 발견한 결함

D-029는 "본문 포함 전체 editorial 검증(`min_editorial_score` 60)은 scrape 후 `process.py`에서
수행"한다고 명시했고 `config.yaml`에도 `feed_filter.min_editorial_score` 키가 주석과 함께
존재했다. 그러나 **실제 코드 경로는 한 번도 구현되지 않았다.** `hard_reject` 신호는 계산만
되고 스크레이프 이후 전 구간에서 폐기되고 있었다.

결과: `final_rank_score = scrape_quality*0.35 + publishability*0.40 + performance*0.25` 가중합
때문에, 스크랩 품질·성과 휴리스틱이 높으면 편집 적합도가 낮은(추상적·파생각 없는) 글도
60 임계값을 넘겨 검토 큐에 적재됐다. → 선별 정확도 누수.

### 완료된 변경

- `pipeline/process_stages/filter_profile_stage.py`: `_check_editorial_fit()` 신규 추가.
  `_build_profile_and_decision` 뒤·`_check_viral_and_calendar`(LLM) 앞에 배치.
  `hard_reject` 또는 점수 < `min_editorial_score`면 `FILTERED_EDITORIAL`로 차단.
  `daily_queue_floor` 활성 시 override. 진단용 `editorial_fit`을 `post_data`에 보존.
- `config.py` / `blind_scraper.py`: `ERROR_FILTERED_EDITORIAL` 에러 코드 추가/재노출.
- `config.yaml` / `config.example.yaml` / `config.ci.yaml`: `feed_filter.editorial_gate_enabled: true`
  추가, `min_editorial_score` 주석 정정(`process.py` → `filter_profile_stage`).
- `tests/unit/test_process_stages.py`: `TestEditorialGate` 7개 테스트 추가, `_ctx_with_content`
  픽스처 본문을 현실화.
- `tests/unit/test_cost_controls.py` / `test_pipeline_flow.py`: 파이프라인 e2e 스텁 본문을
  편집 게이트를 통과하는 현실적인 글로 교체.
- `.ai/DECISIONS.md` D-032, `.ai/CONTEXT.md` 지뢰밭 #13/#17 갱신.

### 주의사항

- `_check_editorial_fit`이 기본 활성이다. 파이프라인 전체를 도는 신규 테스트의 스텁 본문은
  숫자·인용·장면·직장 맥락이 있어야 게이트를 통과한다. 추상적 본문은 `editorial_hard_reject`.
- `feed_filter` 키는 `config.example.yaml`/`config.ci.yaml`과 동기화 유지
  (`test_config_workflow_sync.py`가 keyset 검증).
- 게이트는 active staged `process_single_post()`에만 적용된다. `_process_single_post_legacy()`는
  미적용 — 레거시 제거 시 함께 정리.

### 다음 AI에게

- 선별 정확도 후속 작업 후보: 운영 데이터 누적 후 `min_editorial_score` 임계값 튜닝,
  Notion 검토 카드에 `editorial_fit` 진단(점수·차원·하드리젝 사유) 노출.
- 게이트 차단율이 너무 높으면 `feed_filter.min_editorial_score`를 낮추거나
  `editorial_gate_enabled: false`로 임시 비활성 가능.
## Last Session (2026-06-11 | Codex)

| Item | Content |
|---|---|
| Work | Debug loop 5: fixed weekly smoke repair-command contract for source-preflight evidence doctor inputs |
| Status | Done |
| Tests | `source_preflight_evidence_doctor.py --input .tmp\source_browser_preflight-blind.json --fail-on-warning --json` PASS; `write_weekly_smoke_inputs.py --manifest-output .tmp\weekly_smoke_manifest_current.json --self-check --json` PASS; `verify_weekly_smoke.py --manifest .tmp\weekly_smoke_manifest_current.json --verify-review-summary --verify-strategy-summary --json` PASS; direct `pytest --no-cov tests/unit` PASS; `project_qc_runner.py --project blind-to-x --json` PASS |

### Notes for Next AI

- Root cause: `source_preflight_strategy_payload()` advertised copy-ready commands for `.tmp/source_browser_preflight-{source}.json`, but `write_weekly_smoke_inputs()` did not generate those doctor input reports.
- Fix: writer now emits source-preflight repair input JSON plus matching failure-report JSON, and repair queue commands are derived from `--output-dir`.
- Docs were updated because verifier payloads now preserve `repair_queue` in manifest/review-summary failure examples.
- One QC runner attempt returned only progress lines and exit 1 after a shorter timeout; direct pytest passed, and a retry with longer timeout passed. Treat this as runner/runtime instability unless the artifact contains a concrete failing test.
