# Blind-to-X Ops Runbook

## Weekly Smoke Manifest Command Contract

Manifest command-contract failures use `manifest_missing_commands`, `manifest_missing_command:*`, or `manifest_command_missing_fragment:*`. They mean the manifest no longer preserves the copy-ready `write_inputs`, `review_summary`, `build_report`, `verify_text`, `verify_json`, and `verify_manifest` commands, including `--manifest-output .tmp/weekly_smoke_manifest.json`, `--verify-review-summary`, `--verify-strategy-summary`, and `--self-check` when present.

Command-contract drift example:

```json
{"error_categories":["manifest"],"errors":["manifest_command_missing_fragment:write_inputs:--manifest-output .tmp/weekly_smoke_manifest.json"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"status":"fail"}
```

이 문서는 `자동 수집 + 수동 검토 + 수동 발행` 운영 모델 기준 런북입니다.

## 1. Notion 데이터베이스 구성

핵심 검토용 속성:

- `콘텐츠`
- `메모`
- `상태`
- `생성일`
- `원본 URL`
- `운영자 해석`
- `검토 포인트`
- `피드백 요청`
- `위험 신호`
- `근거 앵커`
- `반려 사유`
- `트윗 본문`
- `Threads 본문`
- `블로그 본문`
- `발행 플랫폼`
- `원본 소스`
- `토픽 클러스터`
- `감정 축`
- `최종 랭크 점수`
- `성과 등급`

선택 운영/회고용 속성:

- `트윗 링크`
- `24h 조회수`
- `24h 좋아요`
- `24h 리트윗`

페이지 본문 원칙:

- 상단에서는 `검토 요약`과 `X 업로드 카드`만 먼저 확인합니다.
- `X 업로드 카드`의 `X 본문`을 복사해 게시하고, 원문 링크/해시태그는 `첫 답글 / 출처 메모`로 분리합니다.
- `진단 펼치기`, `원문 펼치기`, `부가 산출물 펼치기`는 필요할 때만 엽니다.
- 보드에는 긴 원문/진단 컬럼보다 검토 판단용 컬럼을 우선 노출합니다.

권장 상태값:

- `검토필요`
- `승인됨`
- `보류`
- `반려`
- `발행완료`

## 2. 권장 뷰

### 검토 큐

- 필터: `상태 = 검토필요`
- 정렬 1: `최종 랭크 점수` 내림차순
- 정렬 2: `발행 적합도 점수` 내림차순
- 표시 권장 컬럼:
- `콘텐츠`
- `원본 소스`
- `토픽 클러스터`
- `감정 축`
- `근거 앵커`
- `검토 포인트`
- `피드백 요청`
- `위험 신호`
- `최종 랭크 점수`
- `트윗 본문`
- `발행 플랫폼`
- `반려 사유`

### 승인 대기

- 필터: `상태 = 승인됨`
- 정렬: `생성일` 내림차순
- 용도: 사람이 실제 발행 전 마지막 확인

### 보류/반려

- 필터: `상태 IN (보류, 반려)`
- 정렬: `생성일` 내림차순
- 용도: 어떤 `반려 사유`와 `위험 신호`가 반복되는지 회고

### 성과 회고

- 필터: `트윗 링크 is not empty`
- 정렬 1: `24h 조회수` 내림차순
- 정렬 2: `24h 좋아요` 내림차순
- 용도: 잘 된 조합과 안 된 조합 파악

## 3. 일간 운영 절차

### 오전

검토 큐 적재:

```powershell
py -3 main.py --source auto --popular --review-only --limit 5
```

`review-only` 실행은 텍스트 초안과 점수 계산까지만 수행합니다. AI 이미지는 승인 이후 발행 단계에서만 생성하도록 비용을 늦춥니다.

검토할 때 보는 기준:

- `검토 포인트`에 적힌 판단 기준이 실제 초안과 맞는지
- `근거 앵커`가 초안에 자연스럽게 살아 있는지
- `운영자 해석`이 과장 없이 납득되는지
- `위험 신호`가 실제 문제인지, 아니면 과한 경고인지
- 반려할 경우 `반려 사유`에 이유를 태그로 남겼는지

처리 기준:

- 바로 쓸 만하면 `승인됨`
- 소재는 괜찮지만 다듬어야 하면 `보류`
- 소재 자체가 약하면 `반려`

### 오후

- `승인됨` 항목만 원하는 채널에 수동으로 올립니다.
- 올린 뒤 아래 속성을 사람이 채웁니다.
  - `트윗 링크`
  - `발행 플랫폼`
  - `발행 시각`
  - `상태 = 발행완료`

## 4. 주간 운영 절차

리포트 생성:

```powershell
py -3 scripts/build_weekly_report.py --days 7
```

점수 재계산:

```powershell
py -3 scripts/recompute_scores.py --write-sample-input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --validate-input --input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --assert-runtime-contract --input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --config config.example.yaml --input .tmp/recompute_scores_fixture.json --dry-run --json
py -3 scripts/recompute_scores.py --days 30 --dry-run --json
py -3 scripts/recompute_scores.py --days 30
```

Use `--write-sample-input` to create a known-good fixture in `.tmp`, then validate it before editing `candidate_ranking_weights`.
Run `--validate-input` first and require `status="ok"`, empty `errors`, `safety.notion_reads=false`, and `safety.notion_writes=false` before using a fixture for scoring comparison.
Before the write command, confirm the dry-run JSON shows `mode="dry-run"`, `safety.notion_writes=false`, `planned`, `score_update_samples`, and `operator_action`.
For scoring-weight comparisons that must avoid Notion reads and writes, use `--input .tmp/recompute_scores_fixture.json --dry-run --json`; the local fixture may be either a records array or an object with `records` and optional `historical_examples`.
`--validate-input` only checks fixture shape and safety flags; `--input ... --dry-run` also runs content-intelligence scoring and may initialize optional local/ML model caches such as Hugging Face. For strict offline scoring dry-runs, prepare the cache first before setting `HF_HUB_OFFLINE=1`.
First-class runtime-contract gate before scoring:

```powershell
py -3 scripts/recompute_scores.py --assert-runtime-contract --input .tmp/recompute_scores_fixture.json --json
```

Use this first-class gate instead of maintaining the jq/Python one-liner; it exits 0 only when validation is ok and the runtime contract says validation loads no runtime dependencies or scoring.
Optional field-level check for saved validation JSON:

```powershell
py -3 scripts/recompute_scores.py --validate-input --input .tmp/recompute_scores_fixture.json --json | Set-Content -Encoding utf8 .tmp/recompute_scores_validate.json
jq -e '.ok == true and (.errors | length) == 0 and .safety.notion_reads == false and .safety.notion_writes == false and .runtime_contract.validation.loads_runtime_dependencies == false and .runtime_contract.validation.scoring_runs == false and .runtime_contract.scoring_dry_run.scoring_dependencies_may_initialize == true' .tmp/recompute_scores_validate.json
```

If `jq` is not installed, use the Python fallback:

```powershell
py -3 -c "import json,pathlib; p=json.loads(pathlib.Path('.tmp/recompute_scores_validate.json').read_text(encoding='utf-8-sig')); ok=p.get('ok') is True and not p.get('errors') and p['safety']['notion_reads'] is False and p['safety']['notion_writes'] is False and p['runtime_contract']['validation']['loads_runtime_dependencies'] is False and p['runtime_contract']['validation']['scoring_runs'] is False and p['runtime_contract']['scoring_dry_run']['scoring_dependencies_may_initialize'] is True; raise SystemExit(0 if ok else 1)"
```

The first-class gate reads only the validation JSON path and does not run scoring, Notion reads, Notion writes, X posts, providers, or browser capture.
For candidate scoring weights, add `candidate_ranking_weights` to the fixture object and review `score_comparison.average_score_delta`, `improved_count`, `regressed_count`, and `variants.candidate.signals.operator_action_required`. Treat any `score_regression` guardrail as manual review work, not automatic config approval.

리포트에서 보는 포인트:

- 어떤 `토픽 클러스터`가 자주 살아남는지
- 어떤 `훅 타입`이 승인률이 높은지
- 어떤 `감정 축`이 너무 과하거나 약한지
- `최종 랭크 점수`와 실제 체감 품질이 계속 맞는지
- `반려 사유`가 특정 토픽/훅에 몰리는지

## 5. 조정 규칙

검토 큐가 너무 많이 쌓이면:

- `ranking.final_rank_min`을 올립니다.
- `review.queue_limit_per_run`을 줄입니다.

검토 큐가 너무 적으면:

- `ranking.final_rank_min`을 조금 내립니다.
- `review.queue_limit_per_run`을 늘립니다.

LLM 품질이 흔들리면:

- `config.yaml`의 `llm.providers` 순서를 바꿉니다.
- 예: `gemini -> deepseek -> xai -> moonshot -> zhipuai -> openai -> anthropic`

## 6. 점검 명령

Notion 스키마 점검:

```powershell
py -3 scripts/notion_doctor.py --config config.yaml
```

실패하면 `credential_check`를 먼저 봅니다. `missing_credentials`가 있으면 `NOTION_API_KEY`와 `NOTION_DATABASE_ID`를 프로젝트 `.env`, `BLIND_TO_X_ENV_PATH`가 가리키는 파일, 또는 `config.yaml`에 채운 뒤 다시 실행합니다. `NOTION_API_KEY`는 Notion integration Bearer token이어야 합니다. `credentials_present: true`인데 실패하면 `NOTION_DATABASE_ID`가 현재 collection mode의 database/data_source ID와 맞는지, 그리고 대상 database/data_source가 integration에 공유되어 있는지부터 확인합니다. `collection_kind=data_source`에서는 `Notion-Version 2025-09-03` 경로를 쓰므로 data source ID가 필요합니다.

자동화에서 읽어야 하면 JSON 모드를 사용합니다.

```powershell
py -3 scripts/notion_doctor.py --config config.yaml --json
```

Notion doctor failure triage order:

1. `credential_check` - fix missing `NOTION_API_KEY` or `NOTION_DATABASE_ID` before schema work.
2. `publish_safety_check` - keep `operator_action_required=false`, `auto_publish_env_enabled=false`, `image_generation_env_enabled=false`, `twitter_config_enabled=false`, `manual_publish_required=true`, `side_effect_env_keys_enabled=(none)` in text output or an empty JSON list, and `credential_values_redacted=true` for the manual-review operating model.
3. `error_code` and `error_message` - classify permission, sharing, schema, or transient Notion failures.
4. `notion_retry_summary`, `notion_failure_classification`, and `notion_operator_action` - decide whether to retry later, reduce request rate, or fix credential, sharing, ID, schema, or payload issues before rerun.
5. `accessible_objects` - confirm the integration can see the intended database/data source before changing IDs.
6. `actions` - run only the listed repair command that matches the failing check: missing credentials first, Bearer token validity, database/data_source ID and collection mode, 403/404 sharing, retry/backoff categories, URL property, then schema sync.

JSON mode may list environment variable names such as `TWITTER_ACCESS_TOKEN`, but it must not print credential values. Do not commit JSON output, `.env`, logs, screenshots, or `.tmp/failures` evidence.

Notion retry classification:

1. `notion_failure_classification.category` - use `rate_limited`, `service_overload`, or `transient_server_error` for retry/backoff decisions; use `credential_invalid`, `permission_or_sharing`, `object_not_found_or_not_shared`, or `schema_or_payload` for repair-before-rerun decisions.
2. `notion_failure_classification.retry_recommended` and `wait_seconds` - if true, respect `Retry-After` or the recorded backoff before retrying.
3. `notion_failure_classification.primary_repair` - summarizes the first manual action, such as `respect_retry_after_or_backoff`, `share_database_with_integration`, or `fix_schema_or_payload`.

Automation mapping:

1. `credential_invalid` -> use `notion_operator_action` to rotate or replace `NOTION_API_KEY`; do not edit schema.
2. `permission_or_sharing` -> share the target database/data source with the Notion integration; do not change IDs first.
3. `object_not_found_or_not_shared` -> verify `NOTION_DATABASE_ID` and sharing before sync or backfill.
4. `rate_limited`, `service_overload`, or `transient_server_error` -> honor `Retry-After`/backoff before changing schema or credentials.

Redacted `notion_doctor --json` failure sample for automation:

```json
{
  "status": "FAIL",
  "ok": false,
  "token_masked": "ntn_...alue",
  "error_code": "ERROR_NOTION_SCHEMA_FETCH_FAILED",
  "error_message": "not shared with integration",
  "accessible_objects": ["database:Review Queue (abc123)"],
  "notion_retry_summary": {
    "last_status": 403,
    "retryable": false
  },
  "notion_failure_classification": {
    "category": "permission_or_sharing",
    "retry_recommended": false,
    "primary_repair": "share_database_with_integration"
  },
  "notion_operator_action": "Share the target database/data source with the Notion integration before rerun.",
  "actions": [
    "For 403 restricted_resource or 404 object_not_found, share the target database/data source with the integration"
  ]
}
```

Automation should treat this sample as a field contract, not as a committed runtime artifact: keep real JSON output, `.env`, logs, screenshots, and `.tmp/failures` evidence out of commits.

Provider key check interpretation:

1. `provider_key_check.operator_action_required` - if true, at least one enabled LLM provider is missing both usable env keys and config values.
2. `provider_key_check.missing_enabled_providers` - only providers enabled by explicit flags or `llm.providers` appear here.
3. `provider_key_check.ready_enabled_provider_count` and `provider_key_check.enabled_provider_count` - use these counts to confirm fallback capacity before paid or review-only runs.
4. `provider_key_check.credential_values_redacted` - keep this `true`; the check may expose env key names and set/missing states, but never credential values.
5. `provider_key_check.checks[].provider`, `enabled`, `ready`, `severity`, `env_keys`, `env_state`, `env_key_states`, `config_key`, `config_state`, and `operator_action` - use the warning rows to set the named env key or config value, or disable the unused provider.
6. Provider aliases are normalized: `claude` to `anthropic`, `grok` to `xai`, and `chatgpt` to `openai`.

This check may list env key names such as `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, and `OPENAI_API_KEY`; it must not print API key values.

`status`, `ok`, `credential_check`, `error_code`, `error_message`, `accessible_objects`, `actions`를 보고 실패 원인을 분기합니다. 출력에는 원본 토큰 대신 `token_masked`만 포함됩니다.

검토용 컬럼/옵션 동기화:

```powershell
py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply
```

기존 카드 리뷰 컬럼 백필:

```powershell
py -3 scripts/backfill_notion_review_columns.py --config config.yaml --apply
```

소스 preflight 실패 증거 확인:

```powershell
py -3 scripts/source_browser_probe.py --source all --click-through --output .tmp/source_browser_probe.json --screenshot-dir screenshots/source_probe --failure-dir .tmp/failures/source_preflight
```

Pipeline gate runs should pass the same evidence directory explicitly with `--source-preflight-failure-dir .tmp/failures/source_preflight` when using `main.py --require-source-ready`.

더 무거운 Playwright trace 증거가 필요할 때만 `--trace-dir .tmp/traces/source_preflight` 또는 `main.py --source-preflight-trace-dir .tmp/traces/source_preflight`를 명시합니다. trace zip은 문제 source가 있을 때만 보존되며, `.tmp/traces/`는 커밋하지 않습니다.

캡처된 증거가 완전한지 먼저 검증합니다. 이 명령은 브라우저, Notion, X/Threads/블로그를 호출하지 않고 JSON과 참조된 로컬 증거 파일만 읽습니다.

```powershell
py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_probe.json --base-dir . --fail-on-warning
```

여러 로컬 preflight 리포트에서 반복되는 실패 유형을 보려면 trend report를 생성합니다. 출력은 `.tmp/`에 두고 커밋하지 않습니다.

```powershell
py -3 scripts/source_preflight_trend_report.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_trend.json --json
```

Trend JSON exposes `summary.evidence_field_counts`, and text output prints `evidence_fields:`. Check this before selector, timeout, or source-strategy changes to confirm whether local reports consistently include `failure_report_path`, `screenshot_path`, `html_snapshot_path`, `trace_path`, `error`, or `exception_type`. Trend JSON also exposes `summary.top_source_evidence.open_first`, and weekly reports render it as `Top source evidence:` so the first artifact for the top source/status bucket is visible without launching a browser.

When a problem action has `trace_path`, the preflight summary and failure report expose `trace_viewer_command` and `trace_viewer_hint`. `source_preflight_evidence_doctor.py` text output also prints `trace_viewer item=N source=SOURCE: playwright show-trace ...`, so operators can open the trace before selector, timeout, or source-strategy changes.

Source strategy A/B dry-run:

```powershell
py -3 scripts/source_preflight_strategy_simulation.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_strategy_simulation.json --json
```

Manual-ready gate:

```powershell
py -3 scripts/source_preflight_strategy_simulation.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_strategy_simulation.json --require-manual-ready
```

`summary.problem_actions[].evidence`를 먼저 확인합니다. `failure_report_path`, `screenshot_path`, `html_snapshot_path`, `error`, `click_screenshot_path`, `click_error`가 있으면 그 증거를 보고 원인과 다음 조치를 판단합니다. 증거 확인 전에는 timeout을 늘리거나 selector를 바꾸지 말고, `recommended_source`나 `recommended_command`가 있으면 준비된 fallback source로 이번 실행을 진행합니다.

`failure_report_path`가 가리키는 JSON에는 `failure_report.schema_version`, `failure_report.tool`, `failure_report.captured_at`, `operator.action_required`, `operator.action`, `operator.evidence`가 포함됩니다. `classification.status`가 `browser_unavailable`이고 `operator.action`에 Playwright Chromium 설치가 나오면 같은 Python 환경에서 `py -3 -m playwright install chromium`을 실행하거나, 프로젝트 venv를 쓰는 운영자는 `.venv\Scripts\python.exe -m playwright install chromium`으로 설치한 뒤 preflight를 다시 실행합니다. `.tmp/failures/`와 screenshot/html snapshot 출력은 증거 확인용이며 커밋하지 않습니다.

`source_preflight_evidence_doctor.py`와 trend report의 `evidence_gate_status_counts`는 `fix_evidence_first`, `fallback_only`, `strategy_review_ready`로 후속 조치를 나눕니다. `fix_evidence_first`가 있으면 selector/timeout 변경 전에 누락된 증거부터 보강하고, `fallback_only`는 이번 실행을 준비된 source로 넘기며, `strategy_review_ready`만 timeout/selector/source 전략 검토 후보로 봅니다.

`summary.operator_recommendation`은 gate count를 `repair_evidence`, `use_ready_fallback`, `review_source_strategy`, `split_fallback_and_strategy_review` 중 하나로 요약해 주간 dry-run 리포트에 표시합니다. 이 값은 운영자가 다음 조치를 고르는 로컬 판단 보조이며, Notion 쓰기, X 발행, 브라우저 실행을 시작하지 않습니다.

`source_preflight_strategy_simulation.py`는 같은 저장된 preflight JSON으로 `current_top_source_action`과 `candidate_gate_directed_operator_recommendation`을 비교합니다. `comparison.recommendation=adopt_candidate`라도 실제 selector/timeout/source 변경을 자동 적용하지 않으며, 후보가 줄이는 값은 `unsafe_strategy_change_count` 같은 운영 리스크입니다.

`rollout_gate`는 이 dry-run을 사람이 source strategy 검토에 써도 되는지 분리해서 표시합니다. `ready_for_manual_strategy_review=true`는 저장된 evidence가 수동 검토 후보라는 뜻이고, `auto_apply_allowed=false`는 selector/timeout/source 변경, Notion 쓰기, X 발행이 자동으로 실행되지 않는다는 안전 계약입니다. `blocked_by`에 `repair_evidence_first`나 `fallback_only_sources_present`가 있으면 그 이유부터 처리합니다.

`--require-manual-ready`는 기본 동작을 바꾸지 않는 선택적 로컬 gate입니다. gate가 준비되지 않으면 exit `2`와 `manual_ready_gate.status=blocked`를 반환하지만, 여전히 저장된 JSON evidence만 읽고 출력 JSON만 씁니다. `manual_ready_gate.primary_repair_command`와 주간 리포트의 `Repair command`는 같은 저장 evidence에 대해 `source_preflight_evidence_doctor.py --json --fail-on-warning`을 다시 실행하는 copy-ready 명령입니다. 입력 report가 여러 개면 `manual_ready_gate.repair_command_count`와 주간 리포트의 `Repair commands: count=..., remaining=...`로 전체 개수와 primary 외 남은 명령 수를 확인하고, 먼저 표시된 primary command부터 실행합니다. 자동 브라우저 실행, Notion 쓰기, X 발행, selector/timeout/source 변경은 하지 않습니다.

When repair command counts tie, `top_repair_commands` and `manual_ready_gate.primary_repair_command` order `source_preflight_evidence_doctor.py` before source recapture or trace capture commands. Run the evidence doctor first so saved evidence is inspected or repaired before browser recapture, Notion writes, X posting, selector changes, timeout changes, or source strategy changes.

`summary.repair_command_queue` preserves the full ordered repair queue for `manual_ready_gate.repair_commands`; `top_repair_commands` is display-only and may be limited for concise stdout/report output. For aggregated duplicate commands, `sum(summary.repair_command_queue[].count)` must match `manual_ready_gate.repair_command_count`, while weekly report `Repair queue: listed=N` remains the unique command string count. Each queue item can also carry `buckets=source|status=count` so the first source/status repair bucket is visible without opening JSON. The weekly report also prints `count_total=N` and `consistency=ok|mismatch` from `summary.repair_command_queue_consistency` so stdout-only review can catch stale queue metadata without opening JSON.

Weekly smoke manifests include `Repair queue:`, `Primary repair target:`, `count_total=6`, and `consistency=ok` in `expected_report_fragments`, and `verify_weekly_smoke.py` checks blocked `manual_ready_gate.repair_commands` presence, primary command membership, `summary.repair_command_queue` count coverage, per-item bucket/source fragments for the primary repair target, and `summary.repair_command_queue_consistency` before accepting the report.

During weekly report review, if `repair_remaining>=1`, read `Primary repair target:` first for the command type, duplicate count, source/status bucket, and source count, then run the displayed `Repair command`. Use the input source strategy JSON's `manual_ready_gate.repair_commands` only for the remaining queue after the primary target is assigned.

Generated manifests also include `expected_repair_queue`, which mirrors the structured `repair_queue` JSON object that `verify_weekly_smoke.py --json` emits from `paths.source_preflight_strategy`, including `primary_repair_target` details. Manifest mode and writer `--self-check` compare the expected object against the source-preflight strategy JSON before accepting the smoke packet. Use this to catch stale generated manifests before parsing report Markdown. When the verifier runs with `--json`, manifest mode also emits `manifest_repair_queue` when `expected_repair_queue` is present; automation should read `manifest_repair_queue.ok`, `manifest_repair_queue.checked`, `manifest_repair_queue.matched_key_count`, `manifest_repair_queue.mismatch_count`, and `manifest_repair_queue.mismatched_keys` to distinguish stale expectations from missing inputs without parsing errors. A stale object fails under `error_categories=["manifest"]` as `manifest_expected_repair_queue_mismatch:*`; malformed or unavailable inputs fail as `manifest_expected_repair_queue_not_object`, `manifest_expected_repair_queue_missing_strategy_path`, or `manifest_expected_repair_queue_unavailable`.

Compact manifest expectation:

```json
"expected_repair_queue": {
  "present": true,
  "total": 6,
  "listed": 6,
  "count_total": 6,
  "consistency": "ok",
  "full_queue_available": true,
  "queue_item_count": 6,
  "primary_repair_command_present": true,
  "primary_repair_target": {
    "present": true,
    "command": "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning",
    "type": "evidence_doctor",
    "count": 1,
    "buckets": {"blind|blocked": 1},
    "sources": {"blind": 1}
  },
  "source": "manual_ready_gate.repair_commands"
}
```

Stale expected repair queue example:

```json
{"error_categories":["manifest"],"errors":["manifest_expected_repair_queue_mismatch:total=expected_7,actual_6"],"manifest":".tmp/weekly_smoke_manifest.json","manifest_repair_queue":{"actual_key_count":10,"actual_present":true,"checked":true,"expected_is_object":true,"expected_key_count":10,"expected_present":true,"matched_key_count":9,"mismatch_count":1,"mismatched_keys":["total"],"ok":false,"source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","status":"fail"},"ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"status":"fail"}
```

`verify_weekly_smoke.py --json` also emits a structured `repair_queue` object when manual-ready repair data is present. Automation should read `repair_queue.total`, `repair_queue.listed`, `repair_queue.count_total`, `repair_queue.consistency`, `repair_queue.full_queue_available`, `repair_queue.queue_item_count`, `repair_queue.primary_repair_command_present`, and `repair_queue.primary_repair_target` instead of parsing the Markdown report line.

Compact expected shape:

```json
"repair_queue": {
  "total": 6,
  "listed": 6,
  "count_total": 6,
  "consistency": "ok",
  "full_queue_available": true,
  "queue_item_count": 6,
  "primary_repair_command_present": true,
  "primary_repair_target": {
    "present": true,
    "type": "evidence_doctor",
    "count": 1,
    "buckets": {"blind|blocked": 1},
    "sources": {"blind": 1}
  }
}
```

Mismatch shape:

```json
"repair_queue": {
  "total": 2,
  "listed": 1,
  "count_total": 1,
  "consistency": "mismatch",
  "full_queue_available": false,
  "queue_item_count": 1,
  "primary_repair_command_present": true,
  "primary_repair_target": {
    "present": true,
    "type": "evidence_doctor",
    "count": 2,
    "buckets": {},
    "sources": {"blind": 2}
  }
}
```

PowerShell extraction:

```powershell
$payload = py -3 scripts/verify_weekly_smoke.py --manifest .tmp/weekly_smoke_manifest.json --verify-review-summary --verify-strategy-summary --json | ConvertFrom-Json
$payload.manifest_repair_queue | ConvertTo-Json -Compress
$payload.repair_queue | ConvertTo-Json -Compress
```

CLI 한 줄 요약에도 `repair_queue=ok|mismatch`, `primary_repair_type=TYPE`, `primary_repair_count=N`, `primary_repair_buckets=SOURCE|STATUS=N`, `primary_repair_sources=SOURCE=N`, `repair_remaining=N`, `metric_missing=current:N/10,candidate:N/10`, `operator_action_mismatch_count=N`, `operator_action_mismatch_sources=SOURCE=N`, `evidence_fields=FIELD=N`, `scope=local_preflight_evidence`를 표시하므로, JSON을 열지 않는 stdout-only 운영자도 repair command count/queue 정합성, 첫 repair target의 source/status bucket, primary 외 남은 repair command 수, stale-evidence mismatch, evidence coverage, 비용 없는 local evidence dry-run의 미측정 metric 수를 바로 확인할 수 있습니다.

자동화가 파일을 쓰지 않고 구조화 결과만 읽어야 하면 `source_preflight_strategy_simulation.py --summary-only --json`을 사용합니다. 이때 `output.write_suppressed=true`, `output.suppression_flags=["summary_only"]`, `summary.metric_missing`, `summary.metric_total`, `summary.repair_command_queue[].buckets`, `summary.operator_action_mismatch_count`, `summary.operator_action_mismatch_source_counts`, `summary.evidence_field_counts`, `summary.measurement_scope.mode`를 확인합니다.

주간 리포트나 summary-only stdout에서 `repair_remaining`이 1 이상이면 먼저 `Primary repair target:` 또는 `primary_repair_type` / `primary_repair_buckets`를 확인하고 표시된 `Repair command`를 실행한 뒤, 나머지 명령은 입력으로 쓴 source strategy JSON의 `manual_ready_gate.repair_commands`에서 확인합니다.

주간 리포트의 `Blocked checklist`는 `blocked_by` 원인을 operator action으로 바꾼 요약입니다. `repair_evidence_first`는 evidence doctor를 먼저 실행하고, `fallback_only_sources_present`는 ready fallback source를 쓰되 strategy 변경은 수동 검토로 남깁니다. 새 blocker가 아직 매핑되지 않았으면 `inspect rollout_gate.operator_action` fallback으로 표시되므로 `Gate action`을 먼저 확인합니다.

`Safety risk flags`는 source strategy A/B의 current/candidate `safety_risk_flags`를 같은 줄에 보여줍니다. `candidate=-`이면 후보 쪽에 추가 safety flag가 없다는 뜻이고, `evidence_repair_required`가 보이면 strategy 검토 전에 evidence repair를 먼저 처리합니다.

`Outcome signals`는 current/candidate의 `success`와 `operator_action_required`를 나란히 보여줍니다. `candidate_success=false`이거나 `candidate_operator_action_required=true`이면 JSON을 열기 전에 먼저 `Gate action`, `Blocked checklist`, `Manual-ready gate`를 확인합니다.

`Provider/model/cost`는 source strategy A/B current/candidate의 `provider`, `model`, `token_cost_estimate`를 한 줄에 보여줍니다. 값이 `source_preflight/.../$0.0000`이면 외부 LLM 호출 없이 로컬 preflight evidence만 비교한 dry-run입니다.

`A/B metrics`는 source strategy A/B current/candidate의 `latency_ms`, `draft_quality_score`, `duplicate_or_near_duplicate`를 한 줄에 보여줍니다. `-`는 해당 dry-run이 외부 LLM 호출 없이 로컬 evidence만 비교해 latency나 draft quality를 새로 측정하지 않았다는 뜻입니다.

`Metric coverage`는 source strategy A/B의 current/candidate missing metric 수와 측정 범위를 보여줍니다. 주간 리포트도 CLI 한 줄 요약과 같은 `metric_missing=current:N/10,candidate:N/10` 키를 함께 표시합니다. `scope=local_preflight_evidence`, `external_llm_calls=false`, `costed_generation=false`이면 `latency_ms`/`draft_quality_score`의 `-` 값은 수집 실패가 아니라 비용 없는 로컬 dry-run의 의도된 미측정 항목입니다.

호환성 참고: source strategy JSON이 compact summary 형태라서 `summary.missing_metric_counts`나 `summary.missing_metric_names`가 없어도, 주간 리포트는 `summary.metric_missing`과 `summary.metric_total`을 fallback alias로 읽어 같은 `Metric coverage` 줄을 렌더링합니다. 자동화는 `summary-only --json` 출력에서 이 두 필드를 유지하면 됩니다.

전체 테스트:

```powershell
py -3 -m pytest --no-cov -q tests/unit
```

Windows 로컬 검증에서 전체 unit은 2-6분 제한을 넘길 수 있습니다. timeout을 hang으로 판단하기 전에 repo-local basetemp와 faulthandler/durations를 켠 긴 실행으로 확인합니다.

```powershell
py -3 -m pytest --no-cov -q tests/unit --durations=20 -o faulthandler_timeout=120 -o faulthandler_exit_on_timeout=true --basetemp ..\..\.tmp\pytest-blind-to-x-unit
```

검토 카드 A/B dry-run:

```powershell
py -3 scripts/review_experiment_dry_run.py --input-mode review-records --input .tmp/review_queue_report_sample.json --min-items 1 --max-missing-rate 0.8 --summary-only
```

이 명령은 Notion, X, Threads, 블로그에 쓰지 않고 콘솔에 rollout gate만 출력합니다. 빠른 운영 판단에는 `--summary-only`를 쓰고, 자동화가 구조화 결과를 읽어야 하면 `--summary-only --json`을 같이 사용합니다.

Review experiment summary-only stdout includes `missing_metric_rate=N`, `top_missing_metric=METRIC`, `top_missing_metric_count=N`, `top_missing_owner=OWNER`, `top_missing_owner_count=N`, `top_missing_owner_metric=METRIC`, `operator_actions_total=N`, `avg_operator_actions=N`, `high_noise_items=N`, `safety_risk_items=N`, `safety_risk_flags=FLAG=N`, `provider_failure_categories=CATEGORY=N`, `provider_failure_providers=PROVIDER=N`, `primary_provider_failure_categories=CATEGORY=N`, `primary_provider_failure_providers=PROVIDER=N`, `top_operator_action=...`, `top_operator_action_count=N`, `top_operator_action_reason=...`, `rollout_blocker_count=N`, `rollout_blocker_codes=CODE[,CODE]`, and `top_rollout_blocker_action=...` so stdout-only operators can see objective-metric gaps, owner gaps, action noise, rollout blockers, provider failure causes, the first provider repair target, and safety risk before opening JSON.

Weekly report payload smoke renders review experiment top actions as `Review top operator actions:` when `summary.candidate_top_operator_actions[]` is present, review missing metric owners as `Missing metric owners:` when `summary.candidate_top_missing_metric_owners[]` is present, review safety risk as `Safety risk flags:` when `summary.candidate_safety_risk_item_count` is non-zero, review provider failures as `Provider failures:` when total or primary provider failure counts are present, review primary provider repair guidance as `Provider failure repair:` when `summary.candidate_primary_provider_failure_actions[]` is present, review rollout blocker actions as `Rollout blocker actions:` when `summary.candidate_rollout_blocker_actions[]` is present, source trend top actions as `Source trend operator actions:` when `summary.top_operator_actions[]` is present, source trend evidence coverage as `Evidence fields:` when `summary.evidence_field_counts` is present, source trend first artifact guidance as `Top source evidence:` when `summary.top_source_evidence` is present, trend stale-evidence mismatch counts as `Operator action mismatches:` when `summary.operator_action_mismatch_count` is non-zero, source strategy first repair guidance as `Primary repair target:` when `summary.repair_command_queue[]` is present, and strategy stale-evidence mismatch counts as `Strategy operator action mismatches:` when source strategy `summary.operator_action_mismatch_count` is non-zero. The `Provider failures:` line keeps total `categories=` / `providers=` counts from `summary.candidate_provider_failure_category_counts` and `summary.candidate_provider_failure_provider_counts` for incident shape, then appends `primary_categories=` / `primary_providers=` from `summary.candidate_primary_provider_failure_category_counts` and `summary.candidate_primary_provider_failure_provider_counts` so the first repair target is visible without opening JSON. The `Provider failure repair:` line surfaces `provider`, `category`, `model`, retryability, circuit-breaker hint, and `operator_action` from `summary.candidate_primary_provider_failure_actions[]` so the first provider repair can be assigned without opening JSON. The `Primary repair target:` line surfaces source strategy repair type, duplicate count, first source/status bucket, and source count from `summary.repair_command_queue[]` so the first evidence repair can be assigned without opening JSON. These labels keep review-card action noise separate from source-preflight action noise. The local verifier loads `.tmp/weekly_report_experiment_smoke.json`, `.tmp/source_preflight_trend.json`, and `.tmp/source_preflight_strategy_simulation.json`, then checks the top review action count/action/reason text, review missing metric owner/count/top metric text, review blocker action code/source/action text, review provider failure category/provider text, review primary provider failure category/provider text, review provider repair action text, top source trend action text, source trend evidence field coverage, top source evidence open-first text, primary repair target type/count/bucket/source text, trend mismatch source count, and strategy mismatch source count in the generated markdown.

Provider failure triage order: read `provider_failure_summary.primary_failure` and `primary_operator_action` before retrying the full fallback chain. `primary_failure.category` is the repair reason chosen from the prioritized failure list; auth, quota/billing, and invalid-output categories are repair-first and should be fixed before another retry, while rate-limit, overload, server, timeout, and network categories are retry/backoff candidates. `candidate_provider_failure_*` counts describe the total incident shape, but `candidate_primary_provider_failure_*` counts identify the first repair target for weekly review. Apply: keep this primary repair axis in dry-run/reporting output. Do not apply: do not change LLM fallback order only because the primary failure is retryable or transient. Risk: if provider status/rate-limit semantics drift, update `classify_provider_failure()` and rerun `review_experiment_dry_run.py --summary-only` before changing operator guidance.

When `summary.candidate_experiment_confidence.issues[]` includes `missing_metric_rate_high`, the weekly report `Next manual action:` should preserve the owner-specific `operator_action`, for example `cost_tracking: Include token_cost_estimate from the generation cost tracker.`. This keeps rollout blockers tied to the team or pipeline component that must repair the missing metric.
Automation that only needs the blocker repair queue can read `summary.candidate_rollout_blocker_actions[]` instead of parsing nested confidence issues. Each item preserves `code`, `source`, `operator_action`, and when present the `owner`, `top_metric`, and count fields. The weekly report renders the same queue as `Rollout blocker actions:` for human review.

```powershell
py -3 scripts/review_experiment_dry_run.py --input-mode review-records --input .tmp/review_queue_report_sample.json --min-items 1 --max-missing-rate 0.8 --summary-only --json
```

JSON stdout에서 `output.write_suppressed = true`이면 리포트 파일 쓰기가 억제된 실행입니다. `output.suppression_flags`는 `summary_only` 또는 `no_write`처럼 어떤 플래그가 쓰기를 막았는지 기록합니다.

주간 리포트 A/B 섹션만 로컬에서 확인하려면 Notion을 호출하지 않는 payload smoke를 사용합니다. 입력 JSON은 `.tmp/`에 두고 커밋하지 않습니다.

```powershell
py -3 scripts/write_weekly_smoke_inputs.py --output-dir .tmp --manifest-output .tmp/weekly_smoke_manifest.json --self-check
```

자동화가 입력 생성 결과를 구조화해서 읽어야 하면 같은 명령에 `--json`을 붙이고 `schema_version`, `safety_contract`, `commands`, `expected_report_fragments`, `expected_review_stdout_fragments`, `expected_strategy_stdout_fragments`, `expected_repair_queue`, `self_check`, `paths`를 확인합니다. text mode는 생성된 manifest contract와 로컬 입력 파일이 유효하면 `self_check=ok`를 출력합니다. `commands.review_summary`, `commands.build_report`, `commands.verify_text`, `commands.verify_json`, `commands.verify_manifest`는 같은 output dir 기준의 copy-ready 후속 명령입니다. 기본 `expected_review_stdout_fragments`는 `provider_failure_categories=auth=1,rate_limit=1`, `provider_failure_providers=gemini=1,openai=1`, `primary_provider_failure_categories=auth=1`, `primary_provider_failure_providers=openai=1`도 포함하므로 provider failure sample에서 primary repair-axis 라벨과 값의 드리프트를 잡습니다. 기본 `expected_strategy_stdout_fragments`는 `primary_repair_buckets=blind|blocked=1`, `primary_repair_sources=blind=1`, `repair_remaining=5`, `metric_missing=current:2/10,candidate:2/10`, `operator_action_mismatch_sources=ppomppu=1`, and `scope=local_preflight_evidence`를 포함하므로 source strategy summary-only stdout의 primary repair target과 stale-evidence axis drift를 잡습니다.

```powershell
py -3 scripts/build_weekly_report.py --payload-input .tmp/weekly_report_payload_smoke.json --review-experiment-input .tmp/weekly_report_experiment_smoke.json --source-preflight-trend-input .tmp/source_preflight_trend.json --source-preflight-strategy-input .tmp/source_preflight_strategy_simulation.json --recompute-contract-input .tmp/recompute_scores_runtime_contract_smoke.json --output .tmp/weekly_report_smoke.md
```

`metric_missing` 확인만 자동화하려면 생성된 smoke 파일을 로컬에서 읽습니다.

```powershell
py -3 scripts/verify_weekly_smoke.py --report .tmp/weekly_report_smoke.md --review-experiment .tmp/weekly_report_experiment_smoke.json --source-preflight-trend .tmp/source_preflight_trend.json --source-preflight-strategy .tmp/source_preflight_strategy_simulation.json --recompute-contract .tmp/recompute_scores_runtime_contract_smoke.json
```

```powershell
py -3 scripts/verify_weekly_smoke.py --report .tmp/weekly_report_smoke.md --review-experiment .tmp/weekly_report_experiment_smoke.json --source-preflight-trend .tmp/source_preflight_trend.json --source-preflight-strategy .tmp/source_preflight_strategy_simulation.json --recompute-contract .tmp/recompute_scores_runtime_contract_smoke.json --json
```

```powershell
py -3 scripts/verify_weekly_smoke.py --manifest .tmp/weekly_smoke_manifest.json --verify-review-summary --verify-strategy-summary --json
```

`--verify-review-summary` reconstructs the local review summary command from manifest paths, runs that dry-run child process, and checks `expected_review_stdout_fragments` against real stdout. It does not execute the manifest command string. Missing review input fails as `review_summary_missing_input:*`; stdout drift fails as `missing_review_summary_stdout_fragment:*`; JSON output reports these under `error_categories=["review_summary"]`.
When this check runs with `--json`, the payload includes a `review_summary` block with `review_records`, `executed`, `returncode`, `expected_stdout_fragment_count`, `matched_stdout_fragment_count`, `missing_stdout_fragment_count`, and `timeout_seconds` so automation can debug the exact local sample and contract coverage. For failure triage, read `review_summary.diagnosis`, `review_summary.failure_reasons`, `review_summary.missing_stdout_fragments`, `review_summary.missing_input`, `review_summary.stdout_drift`, `review_summary.timeout`, `review_summary.nonzero_exit`, `review_summary.run_failed`, and `review_summary.manifest_contract_error` instead of parsing raw error strings. The primary diagnosis is always the first prioritized `review_summary.failure_reasons` entry, so automation can route on `review_summary.diagnosis` while still preserving secondary causes. If parent `error_categories=["manifest"]` appears with a `review_summary` block, the review-summary child did not run (`executed=false`, `returncode=null`); fix the manifest/writer contract first, then rerun review-summary verification. On child-process failures, `review_summary.child_error_tail`, `review_summary.child_error_tail_source`, and `review_summary.child_error_tail_truncated` may also appear with a bounded stderr/stdout tail.
Text mode keeps review-summary failures compact as `weekly_smoke=fail reason=...`; child stderr/stdout tails stay JSON-only in `review_summary.child_error_tail`. For review-summary child failures, text mode reports `review_summary_timeout`, `review_summary_run_failed:*`, `review_summary_missing_input:*`, `review_summary_exit_code:*`, and `missing_review_summary_stdout_fragment:*` only as reason fragments.
If `review_summary.nonzero_exit=true`, inspect `review_summary.child_error_tail` when present, fix the child process failure first, and treat `matched_stdout_fragment_count` as partial evidence only. A nonzero review-summary run can still emit enough stdout to match some fragments, but any `review_summary.failure_reasons` entry for `stdout_drift` means the manifest/stdout contract should be checked again after the child exit is fixed. A zero match count with `nonzero_exit=true` usually means the subprocess failed before summary output; a partial match count means the summary started but its contract was incomplete.

Generated manifests also verify `expected_strategy_stdout_fragments` against the local source strategy formatter for `paths.source_preflight_strategy`. The generated `verify_manifest` command includes `--verify-strategy-summary` so this source-strategy stdout contract is visible next to `--verify-review-summary`. Unlike the review-summary check, this formats `.tmp/source_preflight_strategy_simulation.json` in-process as summary-only stdout; it does not run browser, Notion, providers, X, or the manifest command string. It checks fragments such as `repair_queue=ok`, `primary_repair_type=evidence_doctor`, `primary_repair_buckets=blind|blocked=1`, `primary_repair_sources=blind=1`, `repair_remaining=5`, `operator_action_mismatch_sources=ppomppu=1`, and `scope=local_preflight_evidence`.
When manifest mode runs with `--json`, the payload includes a `strategy_summary` block with `source_preflight_strategy`, `executed`, `expected_stdout_fragment_count`, `matched_stdout_fragment_count`, `missing_stdout_fragment_count`, `missing_stdout_fragments`, `diagnosis`, `failure_reasons`, `missing_input`, `stdout_drift`, `format_failed`, and `manifest_contract_error`. For triage, read `strategy_summary.diagnosis`, `strategy_summary.failure_reasons`, `strategy_summary.missing_stdout_fragments`, `strategy_summary.stdout_drift`, `strategy_summary.format_failed`, and `strategy_summary.manifest_contract_error` instead of parsing raw error strings. Stale strategy fragments fail as `missing_strategy_stdout_fragment:*` under `error_categories=["strategy_summary"]`; malformed expected fragments fail as `manifest_invalid_expected_strategy_stdout_fragment:*` under `error_categories=["manifest"]`.

Review-summary failure triage order:

1. `missing_input` / `review_summary_missing_input:*` - regenerate or point the manifest at `.tmp/review_queue_report_sample.json` before running summary checks.
2. `manifest_contract` / `manifest_invalid_expected_review_stdout_fragment:*` - fix the local manifest contract before treating the review-summary child command as suspect.
3. `timeout` / `review_summary_timeout` - inspect `review_summary.child_error_tail` when present, then remove the local hang or rerun after the dry-run blockage is fixed.
4. `run_failed` / `review_summary_run_failed:*` - inspect `review_summary.child_error_tail_source="exception"` and fix the local process launch, import, or environment failure.
5. `nonzero_exit` / `review_summary_exit_code:*` - inspect the bounded stderr/stdout tail and fix the child process failure before judging stdout fragments.
6. `stdout_drift` / `missing_review_summary_stdout_fragment:*` - only after higher-priority failures are clear, update stdout expectations or the review summary output.

Review-summary stdout drift example:

```json
{"error_categories":["review_summary"],"errors":["missing_review_summary_stdout_fragment:not-present-in-review-summary"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"review_summary":{"diagnosis":"stdout_drift","executed":true,"expected_stdout_fragment_count":11,"failure_reasons":["stdout_drift"],"manifest_contract_error":false,"matched_stdout_fragment_count":10,"missing_input":false,"missing_stdout_fragment_count":1,"missing_stdout_fragments":["not-present-in-review-summary"],"nonzero_exit":false,"ok":false,"returncode":0,"review_records":".tmp/review_queue_report_sample.json","run_failed":false,"status":"fail","stdout_drift":true,"timeout":false,"timeout_seconds":30},"status":"fail"}
```

Review-summary missing input example:

```json
{"error_categories":["review_summary"],"errors":["review_summary_missing_input:.tmp/missing_review_queue_report_sample.json"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"review_summary":{"diagnosis":"missing_input","executed":false,"expected_stdout_fragment_count":10,"failure_reasons":["missing_input"],"manifest_contract_error":false,"matched_stdout_fragment_count":0,"missing_input":true,"missing_stdout_fragment_count":0,"missing_stdout_fragments":[],"nonzero_exit":false,"ok":false,"returncode":null,"review_records":".tmp/missing_review_queue_report_sample.json","run_failed":false,"status":"fail","stdout_drift":false,"timeout":false,"timeout_seconds":30},"status":"fail"}
```

Review-summary manifest contract example:

```json
{"error_categories":["manifest"],"errors":["manifest_invalid_expected_review_stdout_fragment:42"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"review_summary":{"diagnosis":"manifest_contract","executed":false,"expected_stdout_fragment_count":10,"failure_reasons":["manifest_contract"],"manifest_contract_error":true,"matched_stdout_fragment_count":0,"missing_input":false,"missing_stdout_fragment_count":0,"missing_stdout_fragments":[],"nonzero_exit":false,"ok":false,"returncode":null,"review_records":".tmp/review_queue_report_sample.json","run_failed":false,"status":"fail","stdout_drift":false,"timeout":false,"timeout_seconds":30},"status":"fail"}
```

Review-summary timeout example:

```json
{"error_categories":["review_summary"],"errors":["review_summary_timeout"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"review_summary":{"child_error_tail":"Timeout tail: partial stderr before termination","child_error_tail_source":"stderr","child_error_tail_truncated":false,"diagnosis":"timeout","executed":true,"expected_stdout_fragment_count":10,"failure_reasons":["timeout"],"manifest_contract_error":false,"matched_stdout_fragment_count":0,"missing_input":false,"missing_stdout_fragment_count":0,"missing_stdout_fragments":[],"nonzero_exit":false,"ok":false,"returncode":null,"review_records":".tmp/review_queue_report_sample.json","run_failed":false,"status":"fail","stdout_drift":false,"timeout":true,"timeout_seconds":30},"status":"fail"}
```

Review-summary run failed example:

```json
{"error_categories":["review_summary"],"errors":["review_summary_run_failed:OSError"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"review_summary":{"child_error_tail":"OSError: CreateProcess failed for review summary","child_error_tail_source":"exception","child_error_tail_truncated":false,"diagnosis":"run_failed","executed":false,"expected_stdout_fragment_count":10,"failure_reasons":["run_failed"],"manifest_contract_error":false,"matched_stdout_fragment_count":0,"missing_input":false,"missing_stdout_fragment_count":0,"missing_stdout_fragments":[],"nonzero_exit":false,"ok":false,"returncode":null,"review_records":".tmp/review_queue_report_sample.json","run_failed":true,"status":"fail","stdout_drift":false,"timeout":false,"timeout_seconds":30},"status":"fail"}
```

Review-summary mixed nonzero/stdout drift example:

```json
{"error_categories":["review_summary"],"errors":["review_summary_exit_code:1","missing_review_summary_stdout_fragment:missing_metric_rate=0.7"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"review_summary":{"child_error_tail":"Traceback tail: JSONDecodeError: invalid review records","child_error_tail_source":"stderr","child_error_tail_truncated":false,"diagnosis":"nonzero_exit","executed":true,"expected_stdout_fragment_count":10,"failure_reasons":["nonzero_exit","stdout_drift"],"manifest_contract_error":false,"matched_stdout_fragment_count":9,"missing_input":false,"missing_stdout_fragment_count":1,"missing_stdout_fragments":["missing_metric_rate=0.7"],"nonzero_exit":true,"ok":false,"returncode":1,"review_records":".tmp/review_queue_report_sample.json","run_failed":false,"status":"fail","stdout_drift":true,"timeout":false,"timeout_seconds":30},"status":"fail"}
```

Review-summary nonzero exit example:

```json
{"error_categories":["review_summary"],"errors":["review_summary_exit_code:2"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"review_summary":{"child_error_tail":"Traceback tail: RuntimeError: review summary child failed","child_error_tail_source":"stderr","child_error_tail_truncated":false,"diagnosis":"nonzero_exit","executed":true,"expected_stdout_fragment_count":10,"failure_reasons":["nonzero_exit"],"manifest_contract_error":false,"matched_stdout_fragment_count":10,"missing_input":false,"missing_stdout_fragment_count":0,"missing_stdout_fragments":[],"nonzero_exit":true,"ok":false,"returncode":2,"review_records":".tmp/review_queue_report_sample.json","run_failed":false,"status":"fail","stdout_drift":false,"timeout":false,"timeout_seconds":30},"status":"fail"}
```

성공하면 `weekly_smoke=ok`를 출력합니다. 실패하면 `weekly_smoke=fail reason=...`에 누락된 입력/라벨/metric 조각이 표시됩니다. 자동화가 stdout 문자열을 파싱하지 않게 하려면 같은 명령에 `--json`을 붙이고 `ok`, `status`, `errors`, `error_categories`, `paths`를 읽습니다. `--manifest` 모드는 `schema_version`, `profile`, `safety_contract`, `expected_report_fragments`, `expected_review_stdout_fragments`, `expected_strategy_stdout_fragments`, `expected_repair_queue`도 먼저 검증하므로 stale/unsafe manifest는 `manifest_schema_version_mismatch`, `manifest_profile_mismatch`, `manifest_safety_mismatch:*`, `manifest_missing_expected_fragment:*`, `manifest_missing_expected_review_stdout_fragment:*`, `manifest_invalid_expected_strategy_stdout_fragment:*`, `missing_strategy_stdout_fragment:*`, `manifest_expected_repair_queue_mismatch:*`로 실패합니다. unsafe manifest의 JSON 실패 예시는 `error_categories=["manifest"]`와 `manifest_safety_mismatch:notion_writes=expected_false,actual_True`입니다. text mode에서도 manifest 실패는 `weekly_smoke=fail category=manifest`로 표시됩니다. 이 verifier는 review `Review top operator actions:`, review `Missing metric owners:`, review `Rollout blocker actions:`, trend `Source trend operator actions:`, trend `Top source evidence:`, trend mismatch `Operator action mismatches:`, strategy mismatch `Strategy operator action mismatches:`, strategy `Source operator actions:` 라벨을 각각 구분해 확인합니다.

이 명령은 `--payload-input`에 있는 주간 리포트 payload를 그대로 렌더링하고, `--review-experiment-input`의 dry-run 결과를 `Review Experiment A/B Summary (dry-run)` 섹션에, `--source-preflight-trend-input`의 로컬 증거 집계를 `Source Preflight Trend (dry-run)` 섹션에, `--source-preflight-strategy-input`의 source strategy A/B를 `Source Preflight Strategy A/B (dry-run)` 섹션에 붙입니다. Notion 조회, Notion 쓰기, X/Threads/블로그 발행, 브라우저 실행은 하지 않습니다. 출력에서 `Safety: read_only=true`, `notion_writes=false`, `x_posts=false`, `manual_publish_required=true`, `Outcome signals`, `Provider/model/cost`, `A/B metrics`, `Metric coverage`, `metric_missing=current:N/10,candidate:N/10`, `Safety risk flags`, `Rollout gate`, `Blocked checklist`, `Manual-ready gate`, `repair_remaining=N`, `Repair command`, `Gate action`, `Top source action`, `Top source evidence`, `Top source checklist`, `Next manual action`을 먼저 확인합니다.

> 경로는 `tests/unit/` 입니다. 워크스페이스 표준 검증은 루트에서:
>
> ```powershell
> py -3 execution\project_qc_runner.py --project blind-to-x --json
> ```

Weekly smoke verifier checks `Primary repair target:` as a source strategy label alongside `Source operator actions:`. The output checklist should include `Primary repair target` before `Repair command` whenever `repair_remaining=N` is non-zero.

Weekly smoke also renders `Recompute Scores Runtime Contract (dry-run)` from `.tmp/recompute_scores_runtime_contract_smoke.json` (`recompute_scores_runtime_contract_smoke.json`); keep `--recompute-contract-input` in the report command and `--recompute-contract` in verifier commands so `Recompute command` and runtime-contract gate status stay visible without opening JSON.

## Source Preflight Structured Operator Actions

`summary.problem_actions[]` includes `operator_action_required=true` and `operator_action` matching `action`, so stdout, weekly report, and trend tooling can read the same structured operator signal as `results[]` and failure reports.

If the doctor reports `operator_action_mismatch`, the preflight summary and failure report disagree about the next manual action. Treat it as `fix_evidence_first`: rerun the evidence doctor or recapture the source preflight before selector, timeout, or source-strategy review.

Trend JSON exposes `summary.operator_action_mismatch_count` and `summary.operator_action_mismatch_source_counts`, and weekly reports render `Operator action mismatches:` when the count is non-zero. Use this to spot repeated stale-evidence sources before opening individual failure reports.

Trend CLI JSON exposes the same mismatch counts, and text mode prints `operator_action_mismatches:` before weekly aggregation. If this appears, rerun the evidence doctor or recapture the source preflight before building the weekly report.

`source_preflight_evidence_doctor.py` text output prints `operator_action item=N source=SOURCE: required=true action=...` before repair commands, so stdout-only operators can see the required action even when evidence is already structurally PASS.

For trace-backed evidence, `source_preflight_evidence_doctor.py` text output prints `trace_viewer item=N source=SOURCE: playwright show-trace ...`, and the structured item includes `trace_viewer_command` and `trace_viewer_hint`.

`source_preflight_trend_report.py` preserves original operator actions in `summary.operator_action_counts` and `summary.top_operator_actions[]`, and weekly reports render those top actions before the recomputed source/status action. It also emits `summary.top_source_evidence` so weekly reports show the first local failure artifact to open for the top source/status bucket.

Strategy simulation summary preserves trend `summary.top_operator_actions[]`, repair queue `buckets=source|status=count`, and weekly `Source Preflight Strategy A/B` output renders `Source operator actions` plus `Primary repair target` so original evidence-doctor action text and the first repair bucket stay visible next to the rollout gate.

Strategy simulation summary preserves `operator_action_mismatch_count`; mismatch-derived stale evidence stays in `fix_evidence_first`, makes `manual_ready_gate.status=blocked`, and must be repaired before manual source-strategy review.

Source strategy summary-only stdout also includes `primary_repair_type=TYPE`, `primary_repair_buckets=SOURCE|STATUS=N`, `operator_action_mismatch_count=N`, `operator_action_mismatch_sources=SOURCE=N`, `top_operator_action_count=N`, `top_operator_action_sources=SOURCE=N`, and `top_operator_action=...` so stdout-only operators can see the first repair bucket, stale evidence, and the original evidence-doctor action without opening JSON.

## Cost Persistence Fail-Open Triage

`CostTracker.get_cost_persistence_status()` is the machine-readable CostDB health signal. When SQLite persistence degrades, expect `status=degraded`, `fail_open=true`, `event_count`, `retained_event_count`, `total_event_count`, `operation_count`, `operations`, `last_operation`, `last_error_type`, `error_types`, and `operator_action`.

The human summary should show `Cost Persistence: degraded`, `Cost Persistence Last Error`, and `Cost Persistence Action`. Follow the operator action first: check `.tmp/btx_costs.db` permissions/locks and continue with in-memory counters until the DB recovers. Do not commit `btx_costs.db`, archive DB files, `.tmp/workspace.db`, logs, or generated cost evidence.

At runtime, `check_budget()` logs the same state after the existing `CostTracker` is initialized. Search logs for `Cost persistence status: status=... fail_open=... event_count=... operation_count=... operations=... retained_event_count=... total_event_count=...` and, when fail-open is active, `Cost persistence operator action: ...`. This runtime log is observational only; it must not trigger automatic publish, source strategy changes, or CostDB repair.

## 7. 현재 범위 밖

- 특정 채널 자동 발행
- Twitter 성과 자동 수집
- 별도 관리자 대시보드

이 세 가지는 현재 기본 운영 범위가 아닙니다.
