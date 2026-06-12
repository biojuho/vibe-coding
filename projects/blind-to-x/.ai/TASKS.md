# 칸반 보드

## DONE (2026-06-12 Claude Code | D-034 boolean 강제 단일화)
- 52회 디버그 루프의 구조적 원인 해결: `_as_bool` 17개 변종 복붙 → `config.as_bool`/`ConfigManager.get_bool` 단일화.
  - pipeline 13개 파일 로컬 정의 제거 + 공유 import, 기본-켜짐 게이트 5곳 `default=True` 스레딩.
  - 잔존 raw-truthiness 7곳 수정 (persist_stage, review_queue×2, image_generator, cross_source_insight, editorial_reviewer, draft_providers, ProxyManager).
  - standalone scripts 4개 `_as_bool` canonical 정렬 ("off" 토큰 상호 모순 해소).
  - `test_boolean_coercion_contract.py` 35개: AST 재정의 금지 가드 + 동작 동치 계약 + 회귀.
  - stale 문서 정정: `_process_single_post_legacy` TODO는 이미 완료된 작업이었음 (코드 부재 확인).
  - 검증: 전체 단위 `2503 passed, 9 skipped`; ruff pass; project QC passed. no commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 52)
- Feed collector cross-source dedup now parses `dedup.cross_source_enabled: "false"` as disabled.
  - Reproduced duplicate cross-source candidates being deduped to one item with `cross_source_dedup_count=1` despite string `"false"`.
  - Added `_as_bool()` in `feed_collector.py` and used it for the cross-source dedup gate.
  - Added feed collector regression proving string false skips cross-source dedup and keeps both candidates.
  - Verification: focused feed collector pytest `7 passed`; targeted ruff check passed; project QC `2468 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 51)
- Bootstrap optional component startup now parses string `"false"` flags as false.
  - Reproduced `init_components()` awaiting analytics sync when `twitter.enabled` was string `"false"`.
  - Added `_as_bool()` in `bootstrap.py` and used it for `twitter.enabled` / `trends.enabled` startup gates.
  - Added bootstrap regression proving string false disables analytics sync and TrendMonitor initialization.
  - Verification: focused bootstrap cost/status pytest `13 passed`; targeted ruff check passed; project QC `2465 passed, 9 skipped`, lint passed.
  - No commit/stage/push; preserved pre-existing dirty WIP in `bootstrap.py`.

## DONE (2026-06-11 Codex Debug loop 50)
- Source preflight problem-action logs now parse `operator_action_required: "false"` as false.
  - Reproduced `_log_source_preflight_problem_actions()` logging `operator_action_required=true` for a problem action with string `"false"`.
  - Added a narrow `_as_bool()` helper in `pipeline/cli.py` and used it for the logged operator-action required flag.
  - Added CLI regression proving string `"false"` logs as `operator_action_required=false`.
  - Verification: focused `test_main.py` pytest `49 passed`; targeted ruff check passed; project QC `2461 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 49)
- Review queue report artifact/text output now parses string `"false"` as false.
  - Reproduced `format_review_queue_report()` printing `action_required=true`, `notion_writes=true`, `x_posts=true`, `publish_command=true`, and rerun/delta hints when artifact boolean fields were string `"false"`.
  - Added `_as_bool()` / `_format_bool()` in `review_queue_report.py` and routed persisted report boolean fields through them.
  - Added review queue report regression proving string false artifact flags stay false in incident, safety, command, truncation, and delta output.
  - Verification: focused review queue report pytest `37 passed`; targeted ruff check passed; project QC `2458 passed, 9 skipped`, lint passed.
  - No commit/stage/push; preserved pre-existing dirty WIP in the same files.

## DONE (2026-06-11 Codex Debug loop 48)
- Source preflight manual-ready gate now parses `ready_for_manual_strategy_review: "false"` as blocked.
  - Reproduced `_manual_ready_gate_result()` returning `passed=True`, `status=pass`, and `exit_code=0` for rollout gate string `"false"`.
  - Added `_as_bool()` in `source_preflight_strategy_simulation.py` and used it for the manual-ready flag.
  - Added source preflight strategy regression proving string `"false"` blocks the required manual-ready gate.
  - Verification: focused source preflight strategy pytest `16 passed`; targeted ruff check passed; project QC `2451 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 47)
- Publish repair now parses dict `fixable: "false"` as false.
  - Reproduced `repair_hold_draft()` stripping a URL and returning `changed=True` when the decision dict had `fixable: "false"`.
  - Added `_as_bool()` in `publish_repair.py` and used it for dict decision `fixable`.
  - Added focused publish repair regression proving string `"false"` skips repair.
  - Verification: focused publish repair pytest `1 passed`; targeted ruff check passed; project QC `2448 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 46)
- Publish decision now parses research `value_reduction_failed: "false"` as false.
  - Reproduced a publishable draft being dropped when `value_reduction_failed` was the string `"false"`.
  - Added `_as_bool()` in `publish_decision.py` and used it for the research failure flag.
  - Added publish decision regression proving string `"false"` keeps the publishable draft ready.
  - Verification: focused publish decision pytest `7 passed`; targeted ruff check passed; project QC `2444 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 45)
- Fetch-stage scrape integrity config now parses string `"false"` as disabled.
  - Reproduced `run_fetch_stage()` calling `classify_scrape_integrity()` even when `scrape_quality.integrity_check_enabled: "false"`.
  - Added `_as_bool()` in `fetch_stage.py` and used it for the integrity-check enabled flag.
  - Added process-stage regression proving string `"false"` skips the integrity classifier.
  - Verification: focused process stage pytest `55 passed`; targeted ruff check passed; project QC `2442 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 44)
- Provider failure summaries now parse string `"false"` retry/circuit flags as false.
  - Reproduced `summarize_provider_failures()` counting `retryable: "false"` as retryable and adding `circuit_breaker_candidate: "false"` to circuit breaker providers.
  - Added `_as_bool()` in `draft_generator.py` and reused parsed retry/circuit flags across summary counts, provider lists, priority, and failure brief.
  - Added draft generator multi-provider regression proving string false flags stay false.
  - Verification: focused draft generator multi-provider pytest `14 passed`; targeted ruff check passed; project QC `2438 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 43)
- Provider readiness now parses explicit `enabled: "false"` as disabled.
  - Reproduced `_provider_key_diagnostics()` reporting Anthropic missing when `anthropic.enabled: "false"` and no key were present.
  - Routed explicit provider enabled values through `_as_bool()` in `_provider_explicitly_enabled()`.
  - Added notion doctor regression proving string `"false"` leaves the provider disabled and ready.
  - Verification: focused notion doctor pytest `26 passed`; targeted ruff check passed; project QC `2436 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 42)
- `notion_doctor` publish safety now parses `twitter.enabled: "false"` as disabled.
  - Reproduced `_publish_safety_diagnostics()` returning `operator_action_required=True`, `severity=warning`, and `twitter_config_enabled=True` for config string `"false"` with publish env flags cleared.
  - Added `_as_bool()` in `scripts/notion_doctor.py` and used it for `twitter.enabled` publish safety diagnostics.
  - Added notion doctor regression proving string `"false"` leaves publish safety ok with no operator actions.
  - Verification: focused notion doctor pytest `25 passed`; targeted ruff check passed; project QC `2433 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 41)
- Daily queue floor string `"false"` now keeps per-source limits.
  - Reproduced `collect_feed_items()` returning 3 Blind items with active daily queue floor, source cap `{"blind": 1}`, and `review.minimum_daily_queue_relax_per_source_limits: "false"`.
  - Added `_as_bool()` in `daily_queue_floor.py` and used it for the per-source relaxation flag.
  - Added feed collector regression proving string `"false"` preserves the 1-item source cap.
  - Verification: focused feed collector pytest `6 passed`; targeted ruff check passed; project QC `2429 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 40)
- `ranking.llm_viral_boost: "false"` now stays disabled in filter/profile stage.
  - Reproduced `_build_content_profile_dict()` passing `llm_viral_boost=True` for config string `"false"`.
  - Routed `ranking.llm_viral_boost` through `_as_bool()`.
  - Added process-stage regression proving string `"false"` passes `False` to `build_content_profile()`.
  - Verification: focused process stage pytest `54 passed`; targeted ruff check passed; project QC `2425 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 39)
- ViralFilter config string `"false"` now disables the filter.
  - Reproduced `ViralFilter(...)._enabled` becoming `True` for `viral_filter.enabled: "false"`.
  - Added `_as_bool()` in `viral_filter.py` and used it for `viral_filter.enabled`.
  - Added viral filter regression proving string `"false"` stores `_enabled=False` and returns default pass.
  - Verification: focused viral filter pytest `11 passed`; targeted ruff check passed; project QC `2422 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 38)
- Dedup stage config string `"false"` now disables Notion similarity checks.
  - Reproduced `dedup.notion_check_enabled: "false"` still calling `find_similar_in_notion()` and blocking as `DUPLICATE_CONTENT`.
  - Added `_as_bool()` in `dedup_stage.py` and used it for Notion similarity-check config.
  - Added process-stage regression proving string `"false"` skips the similarity check.
  - Verification: focused process stage pytest `53 passed`; targeted ruff check passed; project QC `2417 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 37)
- Editorial gate config string `"false"` now disables the gate.
  - Reproduced `_check_editorial_fit()` hard-rejecting content even with `feed_filter.editorial_gate_enabled: "false"`.
  - Routed the editorial gate enabled config through `_as_bool()`.
  - Added process-stage regression proving string `"false"` disables the editorial gate.
  - Verification: focused process stage pytest `52 passed`; targeted ruff check passed; project QC `2412 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 36)
- Editorial fit gate now parses string false hard-reject flags correctly.
  - Reproduced `_check_editorial_fit()` rejecting score 70 content when `hard_reject` was the string `"false"`.
  - Added `_as_bool()` and used it for hard-reject gate and failure reason selection.
  - Added process-stage regression proving string `"false"` passes when score is sufficient.
  - Verification: focused process stage pytest `51 passed`; targeted ruff check passed; project QC `2411 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 35)
- Review experiment operator action sorting now respects priority 0.
  - Reproduced `_operator_actions()` ordering `resolve_x_publish_status` priority 40 before `review_queue_action` priority 0.
  - Added `_priority_value()` and used it for operator-action sorting plus top-action priority aggregation.
  - Added review experiment regression proving priority 0 action sorts first.
  - Verification: focused review experiment pytest `31 passed`; targeted ruff check passed; project QC `2404 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 34)
- Recompute-score dry-run now preserves explicit scrape quality score 0.
  - Reproduced `_score_update_from_record()` passing `70.0` to `build_content_profile()` for `scrape_quality_score: 0`.
  - `_score_update_from_record()` now defaults to `70.0` only when the value is `None` or an empty string.
  - Added recompute-score regression proving explicit zero reaches the content-profile builder as `0.0`.
  - Verification: reproduction replay passed; focused recompute-score pytest `21 passed`; targeted ruff check passed; project QC `2401 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 33)
- Adaptive feedback weights now preserve explicit zero score metrics.
  - Reproduced five valid performance records returning `{}` when one record had `scrape_quality_score: 0`.
  - `compute_adaptive_weights()` now normalizes score inputs with `_optional_float()` and excludes only missing/blank/non-numeric values.
  - Added feedback-loop regression proving zero scores still count toward the minimum valid record count.
  - Verification: reproduction replay passed; focused feedback-loop pytest `24 passed`; targeted ruff check passed; project QC `2396 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 32)
- Review experiment preserves explicit review queue priority 0.
  - Reproduced `review_queue_priority: 0` producing action priority `15`.
  - `_operator_actions()` now defaults to `15` only when `_as_float(priority)` is `None`, not when it is `0.0`.
  - Added review experiment regression proving priority 0 is preserved.
  - Verification: reproduction replay passed; focused review experiment pytest `30 passed`; targeted ruff format/check passed; project QC `2390 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 31)
- Review experiment X publish status action matching is now case-insensitive.
  - Reproduced `x_publish_status: " failed "` producing required `False` with no operator action.
  - Added `_x_publish_status_requires_action()` and routed required/action generation through strip+lower matching.
  - Added review experiment regression proving lowercase failed status produces `resolve_x_publish_status`.
  - Verification: reproduction replay passed; focused review experiment pytest `29 passed`; targeted ruff format/check passed; project QC `2388 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 30)
- Review experiment no longer marks blank review queue action text as required.
  - Reproduced `review_queue_operator_action: "   "` producing required `True` with no operator actions.
  - `_objective_metric_snapshot()` now strips review queue action text before using it in required aggregation.
  - Added review experiment regression proving blank action text keeps ready draft action-free.
  - Verification: reproduction replay passed; focused review experiment pytest `28 passed`; targeted ruff format/check passed; project QC `2384 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 29)
- Review experiment keeps explicit zero draft quality scores.
  - Reproduced `_quality_gate_score: 0` being replaced by average fallback `9.5`.
  - `_draft_quality_score()` now falls back only when the primary score is `None`, not when it is `0.0`.
  - Added review experiment regression proving explicit 0 is preserved.
  - Verification: reproduction replay passed; focused review experiment pytest `27 passed`; targeted ruff format/check passed; project QC `2382 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 28)
- Review experiment duplicate string flags now override similarity fallback.
  - Reproduced `"true"` being ignored and `"false"` being overwritten by high similarity.
  - `_duplicate_or_near_duplicate()` now uses `_as_bool()` for explicit duplicate fields whenever present.
  - Added review experiment regression covering both string true and string false with high similarity.
  - Verification: reproduction replay passed; focused review experiment pytest `26 passed`; targeted ruff format/check passed; project QC `2379 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 27)
- Review experiment ready drafts no longer fail when `draft_generation_failed` is the string `"false"`.
  - Reproduced a publishable ready fixture producing `success=False`, required operator action, and `regenerate_draft_after_recovery`.
  - Added `_draft_generation_failed()` and routed generation flag handling through `_as_bool(_first_present(...))`.
  - Added review experiment regression proving `"false"` keeps the ready draft successful with no operator actions.
  - Verification: reproduction replay passed; focused review experiment pytest `25 passed`; targeted ruff format/check passed; project QC `2376 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 26)
- Review experiment candidate signals now respect provider failure `operator_action_required="false"`.
  - Reproduced a ready fixture where provider failure summary said required `False` but candidate `operator_action_required` was `True`.
  - `_objective_metric_snapshot()` now uses `_as_bool()` for provider failure required aggregation instead of Python truthiness.
  - Added review experiment regression proving `"false"` does not require candidate operator action when the draft is otherwise ready.
  - Verification: reproduction replay passed; focused review experiment pytest `24 passed`; targeted ruff format/check passed; project QC `2371 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 25)
- Recompute-score input validation now rejects falsey non-array `historical_examples` values.
  - Reproduced a fixture with valid records and `historical_examples: ""` returning `status=ok`, `ok=True`, and no errors.
  - `_load_input_records()` now defaults `historical_examples` to `[]` only when the key is absent, so explicit falsey values still reach the array type check.
  - Added recompute-score regression proving `validate_input(..., json_output=True)` exits 1 with `recompute_scores historical_examples must be an array`.
  - Verification: reproduction replay passed; focused recompute-score pytest `20 passed`; targeted ruff format/check passed; project QC `2366 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 24)
- Recompute-score input validation now accepts explicit empty `records` arrays as a warning-only fixture state.
  - Reproduced `{"records": [], "historical_examples": [], "candidate_ranking_weights": {"hook": 1.0}}` failing with `recompute_scores input must include a records/pages/items array`.
  - `_load_input_records()` now chooses `records/pages/items` by key presence, so an explicit empty array is preserved instead of being collapsed by `or` fallback.
  - Added recompute-score regression proving `validate_input(..., json_output=True)` returns exit 0 with `record_count=0`, no errors, and `warnings=["records_empty"]`.
  - Verification: reproduction replay passed; focused recompute-score pytest `19 passed`; targeted ruff format/check passed; project QC `2359 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 23)
- Source browser preflight empty-result reports no longer pass.
  - Reproduced `build_report([])` emitting `ok=True` and fail-on-problem exit 0.
  - `_build_summary()` now requires at least one probe result before a report can be `ok`.
  - Added source browser regression proving empty results return `ok=False` and fail-on-problem exit 1.
  - Verification: focused source browser probe pytest `40 passed`; related source-preflight pytest `94 passed`; project QC `2354 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 22)
- Source browser failure artifact filename collisions for unsafe custom source names fixed.
  - Reproduced sources `!!!` and `@@@` both writing `source-blocked.json`, with the second report overwriting the first.
  - Added `_source_artifact_slug()` so fallback `source` artifact names receive a stable short hash suffix while existing safe names keep old paths.
  - Routed failure report, screenshot, click screenshot, and HTML snapshot source filenames through the safer artifact slug.
  - Verification: focused source browser probe pytest `39 passed`; related source-preflight pytest `93 passed`; project QC `2350 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 21)
- Source preflight invalid failure-report `operator.action_required=false` required-count suppression fixed.
  - Reproduced invalid failure evidence still producing `operator_action_required=False` and trend `operator_action_required_count=0`.
  - `build_evidence_payload()` now trusts failure-report operator-required values only when the failure report is valid.
  - Added evidence doctor and trend regressions proving invalid `action_required=false` still requires operator attention.
  - Verification: focused evidence/trend pytest `39 passed`; related source-preflight pytest `92 passed`; final project QC `2348 passed, 9 skipped`, lint passed.
  - Note: one full QC attempt hit transient `NameError: preparation`; single-test rerun and final project QC passed without editing `pipeline/draft_prompts.py`.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 20)
- Source preflight failure-report `operator.action_required` string boolean validation fixed.
  - Reproduced `operator.action_required="true"` causing `operator_action_not_required`, invalid failure-report status, and trend invalid counts.
  - `_validate_failure_report()` now uses the shared `_as_bool()` parser for operator-required validation.
  - Added evidence doctor and trend regressions for string `"true"` preserving valid failure-report status.
  - Verification: focused evidence/trend pytest `37 passed`; related source-preflight pytest `90 passed`; project QC `2343 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 19)
- Source preflight `operator_action_required` string boolean parsing fixed.
  - Reproduced `operator_action_required="false"` becoming `True` in evidence doctor output and trend `operator_action_required_count=1`.
  - `build_evidence_payload()` now parses common boolean string/numeric forms before computing operator-action fields.
  - Added evidence doctor and trend regressions for string `"false"` preserving required count 0.
  - Verification: focused evidence/trend pytest `35 passed`; related source-preflight pytest `88 passed`; project QC `2338 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 18)
- Source preflight negative `--max-files` directory selection fixed.
  - Reproduced `--input-dir ... --max-files -1` selecting the older file because `matches[:-1]` silently meant "all but latest".
  - `_input_paths()` in trend report and strategy simulation now clamps `max_files` to `>= 0` before slicing.
  - Added regressions proving negative `--max-files` selects no files instead of an unintended subset.
  - Verification: focused trend/strategy pytest `31 passed`; related source-preflight pytest `86 passed`; project QC `2331 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 17)
- Source preflight explicit empty `--input-dir` fallback fixed.
  - Reproduced trend/strategy `--input-dir empty` returning the default `.tmp/source_browser_preflight.json` when that default file existed.
  - `_input_paths()` in trend report and strategy simulation now uses the default input only when no explicit `--input`/`--input-dir` selector was provided.
  - Added regressions proving explicit empty directories produce zero paths/report count instead of default fallback.
  - Verification: focused trend/strategy pytest `29 passed`; related source-preflight pytest `84 passed`; final project QC `2327 passed, 9 skipped`, lint passed.
  - Note: an initial full QC attempt hit a transient lint syntax error in `tests/unit/test_draft_prompts.py`; direct ruff/py_compile and final project QC passed without editing that file.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 16)
- Source preflight legacy operator-action inference fixed.
  - Reproduced valid timeout evidence where the problem action omitted `action`, `operator_action`, and `operator_action_required`; doctor/trend then dropped the failure report operator action and counted required actions as 0.
  - `build_evidence_payload()` now backfills missing operator action fields from `failure_report.operator` or failure status, while preserving explicit `operator_action_required=False`.
  - Added doctor and trend regressions for legacy summary actions that rely on failure report operator metadata.
  - Verification: focused evidence/trend pytest `31 passed`; related source-preflight pytest `82 passed`; project QC `2322 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 15)
- Source preflight manual-ready fallback-only repair command drift fixed.
  - Reproduced fallback-only complete evidence with `summary.repair_command_count=0` but `manual_ready_gate.repair_command_count=1` and a synthesized evidence-doctor command.
  - `_manual_repair_commands()` now returns only actual repair queue/top commands, so fallback-only gates do not instruct evidence repair.
  - Added CLI regression coverage for `--require-manual-ready --json` fallback-only output with empty repair commands.
  - Verification: focused strategy pytest `13 passed`; related source-preflight pytest `80 passed`; project QC `2317 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 14)
- Source preflight strategy simulation current strategy-review metric fixed.
  - Reproduced mixed evidence with `strategy_review_ready=1`, `fallback_only=1`, but current variant reported `strategy_review_count=2` and `strategy_review_delta=-1`.
  - `_current_strategy_signals()` now records `strategy_review_count` from actual `strategy_ready_count`, not total `problem_count`.
  - Added regression assertions for current/candidate strategy-review counts and zero delta.
  - Verification: focused strategy pytest `12 passed`; related source-preflight pytest `79 passed`; project QC `2311 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 13)
- Source preflight relative base-dir plus explicit input path resolution fixed.
  - Reproduced `--base-dir .tmp/relative-base-loop13 --input .tmp/relative-base-loop13/source_browser_preflight.json` resolving to a double-prefixed missing JSON path.
  - Added explicit-input path resolvers in evidence doctor, trend report, and strategy simulation so paths already under `base_dir` are not prefixed again.
  - Default input and evidence artifact paths remain base-dir relative.
  - Verification: focused evidence/trend/strategy pytest `41 passed`; related source-preflight pytest `79 passed`; project QC `2306 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 12)
- Weekly smoke self-check manifest artifact consistency fixed.
  - Reproduced `--self-check --manifest-output --json` printing `self_check` to stdout while the disk manifest omitted `self_check`.
  - `scripts/write_weekly_smoke_inputs.py` now rewrites `manifest_output` after computing self-check so the artifact matches the final payload.
  - Added JSON/text self-check assertions that the written manifest includes `self_check`.
  - Verification: writer focused pytest `15 passed`; related weekly smoke/report pytest `108 passed`; project QC `2299 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 11)
- Weekly smoke manifest PowerShell copy-ready command quoting fixed for output/manifest paths with metacharacters.
  - Reproduced `commands.write_inputs` for `.tmp/weekly&smoke-loop11` causing PowerShell `AmpersandNotAllowed`.
  - `scripts/write_weekly_smoke_inputs.py` now uses a PowerShell literal-safe command formatter instead of `subprocess.list2cmdline()`.
  - `scripts/verify_weekly_smoke.py` manifest command validation now accepts single-quoted path-valued option fragments.
  - Added unit coverage for `&` paths and updated command expectations to the shared formatter.
  - Verification: writer focused pytest `15 passed`; related weekly smoke/report pytest `108 passed`; project QC `2293 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 10)
- Source preflight evidence doctor PowerShell trace viewer command quoting fixed for trace paths with metacharacters.
  - Reproduced `playwright show-trace .tmp/traces/source&preflight.zip` causing PowerShell `AmpersandNotAllowed`.
  - `scripts/source_preflight_evidence_doctor.py` now uses a PowerShell literal-safe command formatter instead of `subprocess.list2cmdline()`.
  - Added unit coverage for `playwright show-trace '.tmp/traces/source&preflight.zip'`.
  - Verification: evidence doctor focused pytest `15 passed`; related preflight pytest `76 passed`; project QC `2290 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex T-2373)
- Auto-research current blocker evidence refreshed after Blind-to-X debug loop 8.
  - No Blind-to-X product/source edits.
  - Refreshed session orientation, dirty handoff plan, GitHub inventory, product readiness, launch objective audit, completion audit, and debug-loop inventory.
  - Current selector remains `blocked / dirty_worktree_handoff_current / adoptable_candidate_count=0`.
  - Completion audit remains `incomplete` (`15` items, `6` complete, `15` issues, `9` blocked); debug inventory expected-exited `1` with `5` blocked and `0` actionable.
  - Boundary unchanged: continue only after explicit scoped authorization, explicit push/user push, or Supabase credential reset/resync before T-251.

## DONE (2026-06-11 Codex T-2372)
- Auto-research debug inventory UTF-16 input self-anneal completed.
  - Reproduced the false-proof path where PowerShell-written UTF-16 JSON made `debug_loop_inventory.py` load `{}` and still print an expected completion-blocked exit message.
  - `debug_loop_inventory.py` now supports UTF-8-SIG plus UTF-16 fallback for provided JSON artifacts.
  - Added CLI coverage proving UTF-16 session/selector/readiness/audit/dirty-handoff inputs still produce the real completion-blocked inventory.
  - Verification: focused pytest `63 passed`; `py_compile` passed; targeted `ruff check` and `ruff format --check` passed; live inventory wrote `.tmp/debug-loop-known-bugs-current.*` with `blocked=5`, `actionable=0`.
  - Boundary unchanged: selector remains blocked on current dirty handoff, and no Blind-to-X product/source edit was made.

## DONE (2026-06-11 Codex Debug loop 9)
- Source browser probe PowerShell copy-ready command quoting fixed for trace paths with metacharacters.
  - Reproduced trace viewer command parse failure for `.tmp/traces/source&preflight.zip`: PowerShell `AmpersandNotAllowed`.
  - `scripts/source_browser_probe.py` now uses a PowerShell literal-safe command formatter for recommended, trace viewer, and evidence repair commands.
  - Added regression coverage for quoting `& playwright show-trace '.tmp/traces/source&preflight.zip'`.
  - Verification: source browser focused pytest `38 passed`; related preflight pytest `75 passed`; project QC `2282 passed, 9 skipped`, lint passed.
  - No commit/stage/push.

## DONE (2026-06-11 Codex Debug loop 8)
- Project QC runner false-fail normalized for successful Blind-to-X pytest runs.
  - Reproduced runner output with pytest success summary but returncode `4294967295`, causing `status=failed` and exit 1.
  - Direct resolved pytest command exited 0, isolating the issue to the runner/Popen capture path.
  - Root `execution/project_qc_runner.py` now normalizes only pytest post-pass sentinel return codes when stderr is empty and stdout has a successful pytest summary.
  - Verification: workspace project_qc_runner pytest `19 passed`; runner command now passes with Blind-to-X unit `2278 passed, 9 skipped` and lint pass.
  - No commit/stage/push; workspace has broad unrelated WIP.

## DONE (2026-06-11 Codex Debug loop 7)
- Review queue report follow-up command quoting fixed for PowerShell metacharacter artifact paths.
  - Reproduced `.tmp/review&queue-loop7.json` output path causing PowerShell `AmpersandNotAllowed` when the generated `operator_next_commands[0].command` was copied.
  - `_quote_command_arg()` now quotes any argument outside a conservative shell-safe character set instead of only whitespace/quote values.
  - Added unit coverage for `--review-queue-report-output '.tmp/review&queue-loop7.json'`.
  - Verification: focused review queue pytest `36 passed`; related main/runner pytest `92 passed`; direct full unit `2270 passed, 9 skipped`; full ruff lint passed.
  - Note: project QC runner returned progress-only exit 1 twice with no fresh Blind-to-X artifact; direct runner-equivalent pytest/lint passed.

## DONE (2026-06-11 Codex Debug loop 6)
- Weekly smoke copy-ready command quoting fixed for output paths with spaces.
  - Reproduced `commands.write_inputs` failure from `.tmp/weekly smoke loop6/manifest.json`: copied command exited 2 with argparse `unrecognized arguments`.
  - `scripts/write_weekly_smoke_inputs.py` now formats copy-ready command strings with `subprocess.list2cmdline()`.
  - `scripts/verify_weekly_smoke.py` manifest contract checks now accept quoted path-valued option fragments.
  - Tests updated so command expectations work under QC `--basetemp` paths containing `Vibe coding`.
  - Verification: writer/verifier focused pytest `81 passed`; ruff format/check passed; project QC `2258 passed, 9 skipped`, lint passed.

## DONE (2026-06-11 Codex T-2368)
- Auto-research handoff-only approval packet refresh after concurrent dirty drift.
  - No Blind-to-X product/source edits.
  - Added root ignored evidence-only packets for Shorts Maker V2 history fact shorts, tool-wide Pillow deprecation fixes, workspace handoff/task rotator fixes, and Blind-to-X review queue report command quoting.
  - Verification: `test_history_fact_shorts.py` -> `8 passed`; `test_tool_pillow_deprecations.py` -> `7 passed`; matching `py_compile` checks passed; `test_handoff_rotator.py` -> `19 passed`; `test_tasks_done_rotator.py` -> `12 passed`; `test_review_queue_report_command.py` -> `36 passed`.
  - Current root approval audit: `status=ok`, dirty coverage `167/167`, pathspecs `81`, virtual failures `0`, accepted ignored-output deletion advisory `0`, real staged `0`.
  - Selector remains `blocked / dirty_worktree_handoff_current / adoptable_candidate_count=0`; completion audit remains `incomplete`.

## DONE (이번 세션)
- 자율 디버깅 루프 (2026-06-11, Codex): 재현 가능한 formatter gate 실패 수정
  - 0단계: QC runner 일시 실패, ambient Python 환경 불일치, formatter gate 실패를 후보화하고 우선순위 산정
  - `pipeline/draft_prompts.py` 포맷/줄끝 불일치 수정
  - 검증: `ruff format --check .`, `ruff check .`, 관련 pytest 64개, `project_qc_runner.py --project blind-to-x --json` 통과
- 선별 정확도 게이트 (D-032): 본문 포함 편집 적합도 게이트 `_check_editorial_fit` 구현
  - D-029가 명시했으나 미구현이던 `min_editorial_score`/`hard_reject` 후처리 검증을 실제로 강제
  - `FILTERED_EDITORIAL` 에러 코드 추가, `feed_filter.editorial_gate_enabled` 토글 추가
  - `TestEditorialGate` 7개 테스트 추가 + 파이프라인 e2e 픽스처 현실화
- 수집 정확도 게이트 (D-033): 스크레이프 무결성 분류기 구현
  - `pipeline/scrape_integrity.py` + `fetch_stage._check_scrape_integrity` — 로그인 월·삭제 글·봇 차단 페이지를 수집 실패로 분류
  - `scrape_quality.integrity_check_enabled` / `min_article_chars` 설정 추가
  - `test_scrape_integrity.py` 14개 + `TestFetchStage` 3개 테스트 추가

## IN_PROGRESS
- 없음

## TODO
- ~~`_process_single_post_legacy()` 제거~~ → 이미 완료됨 (2026-06-12 확인: 코드에 부재, D-032 게이트는 유일한 active staged 경로에 적용 중)
- stage helper 파일 분리, 레거시 `classification_rules.yaml` 소비 경로 정리 (주의: rules.py/regulation_checker.py/분석 스크립트가 활성 소비 중 — 단순 삭제 불가)
- 선별 정확도 후속: 운영 데이터 누적 후 `min_editorial_score` 임계값 튜닝, Notion 카드에 `editorial_fit` 진단 노출 검토
- ~~scripts 후속 통합~~ → 완료 (2026-06-12): `_as_float` 2벌 canonical 정렬(bool→None 명세 — bool이 1.0으로 승격되던 build_weekly_report 모순 해소), `_input_paths`+경로 헬퍼 2벌 AST 동일성 계약 고정. `test_boolean_coercion_contract.py` 38개로 확장, 전체 단위 2506 passed
## DONE (2026-06-11 Codex)
- Debug loop 5: weekly smoke repair-command contract fixed
  - Reproduced failing copy-ready command: `source_preflight_evidence_doctor.py --input .tmp\source_browser_preflight-blind.json --fail-on-warning --json` returned missing JSON.
  - `write_weekly_smoke_inputs.py` now writes source-preflight doctor input JSON and matching failure-report JSON; source strategy repair commands follow `--output-dir`.
  - Updated runbook/README JSON examples to preserve `repair_queue` in verifier failure payloads.
  - Verification: exact doctor command PASS, manifest verify PASS, direct unit suite PASS, project QC PASS.
