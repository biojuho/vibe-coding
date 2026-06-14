# Blind-to-X

## Cost Persistence Runtime Logs

Normal pipeline startup initializes `CostTracker` during `check_budget()`. After that existing initialization, the runtime logs `Cost persistence status: status=... fail_open=... event_count=... operation_count=... operations=... retained_event_count=... total_event_count=...`. When CostDB is fail-open, logs also include `Cost persistence operator action: ...`; this is observational only and must not enable automatic publish, source strategy changes, or CostDB repair.

Blind 게시글을 수집해서 점수화하고, Notion 검토 큐에 적재하는 운영 파이프라인입니다.

현재 기본 운영 모델은 `자동 수집 + 수동 검토 + 수동 발행`입니다. 특정 채널 자동 발행은 기본 전제가 아니며, 검토자가 Notion에서 먼저 판단하고 수동으로 결정하는 흐름을 우선합니다.

## 현재 운영 흐름

1. Blind 인기글 또는 트렌딩 글을 수집합니다.
2. 게시글 본문, 메타데이터, 스크린샷을 생성합니다.
3. 콘텐츠 인텔리전스가 아래 항목을 계산합니다.
   - `토픽 클러스터`
   - `훅 타입`
   - `감정 축`
   - `대상 독자`
   - `스크랩 품질 점수`
   - `발행 적합도 점수`
   - `성과 예측 점수`
   - `최종 랭크 점수`
4. LLM이 초안을 생성합니다.
   - 기본 fallback 순서: `Gemini -> DeepSeek -> xAI -> Moonshot -> ZhipuAI -> OpenAI -> Anthropic`
5. 상위 후보만 Notion `검토필요` 상태로 적재합니다.
6. 운영자가 Notion에서 승인 여부와 초안 타입을 결정합니다.
7. 발행은 사람이 직접 원하는 채널에 수동으로 올립니다.

## 현재 엔트리포인트

실행 진입점은 `blind_scraper.py`가 아니라 `main.py`입니다.

주요 명령:

```bash
# 검토 큐 적재
py -3 main.py --source auto --popular --review-only --limit 5
py -3 main.py --source blind --popular --review-only --limit 5
py -3 main.py --source multi --popular --review-only --limit 5
py -3 main.py --source all --popular --review-only --limit 5

# Source browser preflight before a multi-source run.
# Run from projects/blind-to-x; on this Windows workspace, prefer the project venv.
# Inspect resolved main.py source-preflight options without browser, Notion, X, or provider calls.
.\.venv\Scripts\python.exe main.py --config config.example.yaml --source ppomppu --source-preflight-print-options

# For the standalone helper, `--source all` probes every known source; omitting --source has the same effect.
.\.venv\Scripts\python.exe scripts/source_browser_probe.py --source all --output .tmp/source_browser_probe.json --screenshot-dir screenshots/source_probe --failure-dir .tmp/failures/source_preflight

# Source browser preflight plus first-post click-through verification
.\.venv\Scripts\python.exe scripts/source_browser_probe.py --source ppomppu --click-through --output .tmp/source_browser_probe.json --screenshot-dir screenshots/source_probe --failure-dir .tmp/failures/source_preflight

# Optional heavier trace evidence; retained only when a source has a problem
.\.venv\Scripts\python.exe scripts/source_browser_probe.py --source ppomppu --click-through --output .tmp/source_browser_probe.json --screenshot-dir screenshots/source_probe --failure-dir .tmp/failures/source_preflight --trace-dir .tmp/traces/source_preflight

# Validate the captured preflight failure evidence without browser/network IO
.\.venv\Scripts\python.exe scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_probe.json --base-dir . --fail-on-warning

# Summarize recent local preflight failure evidence without browser/network IO
.\.venv\Scripts\python.exe scripts/source_preflight_trend_report.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_trend.json --json

# Compare current source-preflight handling against gate-directed handling without browser/network IO
.\.venv\Scripts\python.exe scripts/source_preflight_strategy_simulation.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_strategy_simulation.json --json

# Fast stdout-only check; prints primary_repair_*, repair_remaining, metric_missing, mismatch counts, scope, and top_operator_action without writing output.
.\.venv\Scripts\python.exe scripts/source_preflight_strategy_simulation.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --summary-only

# Optional local gate before manual source-strategy review; exits 2 when evidence is not ready.
.\.venv\Scripts\python.exe scripts/source_preflight_strategy_simulation.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_strategy_simulation.json --require-manual-ready

# The preflight JSON summary includes viewport, ready_sources, problem_sources, and recommended_source.
# recommended_source prefers the ready source with the strongest successful detail evidence.
# recommended_command gives a copyable guarded pipeline command for the recommended source,
# using the active Python interpreter and explicit project/config paths.
# Non-default viewport preflights preserve that viewport in recommended_command.
# problem_actions lists per-source operator next steps for blocked, click, browser, and timeout failures.
# problem_actions[].operator_action_required and problem_actions[].operator_action mirror the structured
# action fields in results[] and failure reports.
# problem_actions[].evidence may include failure_report_path, screenshot_path, html_snapshot_path, trace_path, and error.
# failure reports include failure_report.schema_version/captured_at and operator.action/operator.evidence.
# operator_action_mismatch means the preflight summary and failure report disagree;
# rerun the evidence doctor/capture before selector or timeout changes.
# source_preflight_evidence_doctor.py text output prints
# operator_action item=N source=SOURCE: required=true action=...
# source_preflight_trend_report.py summary.top_operator_actions preserves original operator_action text.
# source_preflight_trend_report.py summarizes operator_action_mismatch_count and operator_action_mismatch_source_counts.
# Its text output prints operator_action_mismatches before weekly aggregation.
# Optional --trace-dir writes Playwright trace.zip evidence only for problem runs; keep .tmp/traces out of commits.
# Trace-backed problem actions and failure reports expose trace_viewer_command and trace_viewer_hint.
# source_preflight_evidence_doctor.py validates those references before selector or timeout changes.
# source_preflight_evidence_doctor.py text output prints trace_viewer item=N source=SOURCE: playwright show-trace ...
# source_preflight_trend_report.py summarizes repeated source/status buckets across local reports
# and surfaces summary.top_source_action plus summary.top_source_remediation.checklist
# as source-specific operator steps.
# summary.top_source_evidence.open_first tells weekly reports which local artifact to open first
# for the most frequent source/status bucket without launching a browser.
# evidence_gate_status_counts separates fix_evidence_first, fallback_only, and strategy_review_ready.
# summary.evidence_field_counts and text evidence_fields show which local failure artifacts
# such as failure_report_path, screenshot_path, html_snapshot_path, trace_path, error,
# and exception_type are present before selector, timeout, or source-strategy changes.
# operator_recommendation turns those gates into the next dry-run action: repair evidence, fallback, or strategy review.
# source_preflight_strategy_simulation.py compares current vs gate-directed handling as an A/B dry-run.
# Its summary preserves trend summary.top_operator_actions for A/B review output.
# Its summary preserves operator_action_mismatch_count so stale evidence blocks manual strategy review.
# rollout_gate shows whether manual strategy review is ready; auto_apply_allowed stays false.
# --require-manual-ready turns rollout_gate into a local non-destructive CLI gate for operators.
# blocked manual_ready_gate output includes a source_preflight_evidence_doctor.py repair command.
# summary output includes primary_repair_type=..., primary_repair_buckets=SOURCE|STATUS=N,
# repair_remaining=N, metric_missing=current:N/10,candidate:N/10,
# operator_action_mismatch_count=N, operator_action_mismatch_sources=SOURCE=N,
# scope=local_preflight_evidence, and top_operator_action so stdout-only operators can see repair, metric, mismatch, and action coverage.
# trend output includes repair_command_count, repair_command_type_counts, and top_repair_commands.
# repair_command_queue items include buckets=source|status=count, and the weekly report prints the first Primary repair target.
# repair_command_debt blocks source strategy review until top repair commands have been run.
# Repair flow runbook: docs/source-preflight-repair-flow.md
# Automation can add --json to --summary-only and read summary.metric_missing, summary.operator_action_mismatch_count, and output.write_suppressed.
# Use main.py --source-preflight-print-options before browser capture to verify config/CLI precedence.
# Keep .tmp/failures, .tmp/traces, and screenshots/source_probe artifacts out of commits.
# HTML sources click the first post and fall back to the canonical detail URL
# if the click is obstructed; API-backed JobPlanet verifies the first post detail endpoint.

# Source browser gate, then continue only when the resolved source is ready
.\.venv\Scripts\python.exe main.py --source ppomppu --popular --review-only --limit 5 --require-source-ready --source-preflight-output .tmp/source_browser_preflight.json --source-preflight-screenshot-dir screenshots/source_preflight --source-preflight-failure-dir .tmp/failures/source_preflight

# Source browser gate with first-post click-through before a paid/LLM run
.\.venv\Scripts\python.exe main.py --source ppomppu --popular --review-only --limit 5 --require-source-ready --source-preflight-click-through --source-preflight-output .tmp/source_browser_preflight.json --source-preflight-screenshot-dir screenshots/source_preflight --source-preflight-failure-dir .tmp/failures/source_preflight

# Multi-source gate that continues with the strongest ready source when some sources are blocked.
# In main.py, `--source all` is an explicit alias for all configured input_sources.
.\.venv\Scripts\python.exe main.py --source all --popular --review-only --limit 5 --require-source-ready --source-preflight-click-through --source-preflight-use-recommended --source-preflight-output .tmp/source_browser_preflight.json --source-preflight-screenshot-dir screenshots/source_preflight --source-preflight-failure-dir .tmp/failures/source_preflight

# 승인된 항목 재처리용 경로
py -3 main.py --reprocess-approved --limit 5

# Notion 연결 및 스키마 진단
py -3 scripts/notion_doctor.py --config config.yaml

# 최근 항목 점수 재계산
py -3 scripts/recompute_scores.py --write-sample-input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --validate-input --input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --assert-runtime-contract --input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --config config.example.yaml --input .tmp/recompute_scores_fixture.json --dry-run --json
py -3 scripts/recompute_scores.py --days 30 --dry-run --json
py -3 scripts/recompute_scores.py --days 30

# 주간 리포트 생성
py -3 scripts/build_weekly_report.py --days 7

# Review experiment stdout-only dry-run; prints operator_actions_total, top_operator_action,
# rollout_blocker_count, rollout_blocker_codes, and top_rollout_blocker_action without writing output.
py -3 scripts/review_experiment_dry_run.py --input-mode review-records --input .tmp/review_queue_report_sample.json --min-items 1 --max-missing-rate 0.8 --summary-only

# Generate local weekly smoke inputs without Notion/browser/provider IO.
py -3 scripts/write_weekly_smoke_inputs.py --output-dir .tmp --manifest-output .tmp/weekly_smoke_manifest.json --self-check

# Local weekly A/B smoke without Notion/browser IO; check output for operator-action labels,
# Rollout blocker actions,
# Top source evidence,
# Primary repair target,
# Operator action mismatches, Strategy operator action mismatches,
# Recompute Scores Runtime Contract, and metric_missing=current:N/10,candidate:N/10.
py -3 scripts/build_weekly_report.py --payload-input .tmp/weekly_report_payload_smoke.json --review-experiment-input .tmp/weekly_report_experiment_smoke.json --source-preflight-trend-input .tmp/source_preflight_trend.json --source-preflight-strategy-input .tmp/source_preflight_strategy_simulation.json --recompute-contract-input .tmp/recompute_scores_runtime_contract_smoke.json --output .tmp/weekly_report_smoke.md

# Optional machine-readable verification for automation.
py -3 scripts/verify_weekly_smoke.py --report .tmp/weekly_report_smoke.md --review-experiment .tmp/weekly_report_experiment_smoke.json --source-preflight-trend .tmp/source_preflight_trend.json --source-preflight-strategy .tmp/source_preflight_strategy_simulation.json --recompute-contract .tmp/recompute_scores_runtime_contract_smoke.json --json
py -3 scripts/verify_weekly_smoke.py --manifest .tmp/weekly_smoke_manifest.json --verify-review-summary --verify-strategy-summary --json

# 전체 단위 테스트
py -3 -m pytest --no-cov -q tests/unit
```

## 설치

```bash
# 의존성은 pyproject.toml에 정의되어 있습니다. 프로젝트 루트에서:
pip install -e .[dev]
py -3 -m playwright install chromium
# or, when using the project venv on Windows:
.\.venv\Scripts\python.exe -m playwright install chromium
```

## 설정

1. `config.example.yaml`을 복사해서 `config.yaml`을 만듭니다.
2. `.env.example`을 복사해서 `.env`를 만들고 운영 키를 넣습니다.
3. 키 파일은 절대 커밋하지 않습니다. 이미 노출된 키가 있다면 공급자 콘솔에서 즉시 폐기 후 재발급합니다.
4. 먼저 아래 명령으로 Notion 연결을 확인합니다.

```bash
py -3 scripts/notion_doctor.py --config config.yaml
```

`notion_doctor` output includes `publish_safety_check` in both text and JSON modes. For the default manual-review operating model, confirm `operator_action_required=false`, `auto_publish_env_enabled=false`, `image_generation_env_enabled=false`, `twitter_config_enabled=false`, `manual_publish_required=true`, `side_effect_env_keys_enabled=(none)` in text output or an empty JSON list, and `credential_values_redacted=true`. If `credential_env_key_count` is non-zero, the output may list only environment variable names; secret values must stay redacted.

`notion_doctor` also includes `provider_key_check`. Confirm `credential_values_redacted=true`, inspect `missing_enabled_providers`, and use each warning row's `env_key_states` plus `operator_action` to set the named env key or config value. The output may list names such as `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, and `OPENAI_API_KEY`, but must not print API key values.

When Notion calls fail after retries, inspect `notion_failure_classification.category`, `retry_recommended`, `wait_seconds`, and `primary_repair` before rerun. Retry/backoff categories (`rate_limited`, `service_overload`, `transient_server_error`) are separate from repair-first categories (`credential_invalid`, `permission_or_sharing`, `object_not_found_or_not_shared`, `schema_or_payload`).

Automation should route `notion_operator_action` by category: `credential_invalid` means rotate or replace `NOTION_API_KEY`; `permission_or_sharing` means share the target database/data source with the integration; `object_not_found_or_not_shared` means verify `NOTION_DATABASE_ID` and sharing; retry categories mean honor `Retry-After`/backoff before schema changes.

For automation examples, see the redacted `notion_doctor --json` failure sample in `docs/ops-runbook.md`; route on `notion_retry_summary.last_status`, `notion_failure_classification.category`, `notion_failure_classification.primary_repair`, and `notion_operator_action`, not on raw error text.

Failure `actions` separate setup, permission, and transient repairs: set missing `NOTION_API_KEY`/`NOTION_DATABASE_ID` first, treat `NOTION_API_KEY` as the Notion integration Bearer token, verify `NOTION_DATABASE_ID` matches the selected database/data_source collection mode, use a data source ID with `Notion-Version 2025-09-03` for `collection_kind=data_source`, share the resource for 403/404 failures, and retry/backoff for transient categories before changing schema.

`.env.example` is a safe template. Keep `AUTO_PUBLISH=false`, `OPENAI_IMAGE_ENABLED=false`, and publish/API token placeholders such as `TWITTER_*`, `X_BEARER_TOKEN`, and `THREADS_ACCESS_TOKEN` blank there. Unit tests parse this file with `python-dotenv`; put real credentials only in your local `.env`, never in `.env.example` or committed files.

## 필수 환경 변수

최소 운영 기준:

```env
NOTION_API_KEY=...
NOTION_DATABASE_ID=...
```

Blind 로그인까지 자동화하려면:

```env
BLIND_EMAIL=...
BLIND_PASSWORD=...
```

LLM 초안 생성을 위해 최소 1개 이상 필요:

```env
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
XAI_API_KEY=...
DEEPSEEK_API_KEY=...
MOONSHOT_API_KEY=...
ZHIPUAI_API_KEY=...
OPENAI_API_KEY=...
```

이미지 생성까지 사용하려면:

```env
OPENAI_IMAGE_ENABLED=true
OPENAI_API_KEY=...
```

Cloudinary 업로드를 권장합니다:

```env
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

X 자동 발행은 선택 사항입니다. 쓰지 않는다면 Twitter 키는 없어도 됩니다.

## Notion 운영 규칙

권장 상태값:

- `수집됨`
- `검토필요`
- `승인됨`
- `보류`
- `반려`
- `발행완료`
- `성과반영완료`

핵심 검토용 속성:

- `콘텐츠`
- `원본 URL`
- `메모`
- `운영자 해석`
- `근거 앵커`
- `검토 포인트`
- `피드백 요청`
- `위험 신호`
- `반려 사유`
- `발행 플랫폼`
- `트윗 본문`
- `Threads 본문`
- `블로그 본문`
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

페이지 본문 운영 원칙:

- 상단은 `검토 요약`과 `X 업로드 카드`만 먼저 봅니다.
- `X 업로드 카드`의 `X 본문`을 그대로 복사하고, 원문 링크/해시태그는 `첫 답글 / 출처 메모`로 분리합니다.
- `진단 펼치기`, `원문 펼치기`, `부가 산출물 펼치기` 토글은 필요할 때만 엽니다.
- 보드 뷰에 원문/진단용 긴 컬럼을 과하게 노출하지 않는 것을 권장합니다.

Notion 뷰 구성은 [`docs/ops-runbook.md`](docs/ops-runbook.md) 기준으로 맞추는 것을 권장합니다.

리뷰용 컬럼을 실제 Notion DB에 추가하려면:

```bash
py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply
```

기존 카드까지 새 리뷰 컬럼으로 채우려면:

```bash
py -3 scripts/backfill_notion_review_columns.py --config config.yaml --apply
```

## 추천 일간 운영

1. 검토 큐 적재

```bash
py -3 main.py --source auto --popular --review-only --limit 5
```

`review-only` 단계에서는 AI 이미지 생성을 미루고 텍스트 초안과 스코어링만 수행합니다. 비용은 승인 이후에 집행하는 것이 기본 정책입니다.

2. Notion에서 `승인 상태 = 검토필요` 뷰를 확인합니다.
3. `검토 포인트`, `피드백 요청`, `위험 신호`, `반려 사유` 컬럼 기준으로 판단합니다.
4. 괜찮은 항목만 `승인됨`으로 바꾸고 초안을 편집합니다.
5. 실제 발행은 사람이 수동으로 진행합니다.

## 추천 주간 운영

1. 최근 7일 리포트 생성

```bash
py -3 scripts/build_weekly_report.py --days 7
```

   For a review-card A/B stdout-only smoke, run `scripts/review_experiment_dry_run.py --summary-only` and confirm `missing_metric_rate=N`, `top_missing_metric=METRIC`, `top_missing_metric_count=N`, `top_missing_owner=OWNER`, `top_missing_owner_count=N`, `top_missing_owner_metric=METRIC`, `operator_actions_total=N`, `safety_risk_items=N`, `safety_risk_flags=FLAG=N`, `provider_failure_categories=CATEGORY=N`, `provider_failure_providers=PROVIDER=N`, `primary_provider_failure_categories=CATEGORY=N`, `primary_provider_failure_providers=PROVIDER=N`, `top_operator_action=...`, `top_operator_action_reason=...`, `rollout_blocker_count=N`, `rollout_blocker_codes=CODE[,CODE]`, and `top_rollout_blocker_action=...` before opening JSON. For a local A/B and source-preflight trend smoke that does not call Notion or launch a browser, run `scripts/write_weekly_smoke_inputs.py --output-dir .tmp --manifest-output .tmp/weekly_smoke_manifest.json --self-check` first, then use the `--payload-input` command in [`docs/ops-runbook.md`](docs/ops-runbook.md). Confirm `Review top operator actions:`, `Missing metric owners:`, `Safety risk flags:`, `Provider failures:`, `primary_categories=`, `primary_providers=`, `Provider failure repair:`, `Rollout blocker actions:`, `Source trend operator actions:`, `Top source evidence:`, `Primary repair target:`, `Operator action mismatches:`, `Strategy operator action mismatches:`, `Recompute Scores Runtime Contract (dry-run)`, `metric_missing=current:N/10,candidate:N/10`, and `Source operator actions:` in the output, or use `scripts/verify_weekly_smoke.py` and its `weekly_smoke=ok` status before treating review/source/recompute safety coverage as reviewed. Automation can add `--json` to the writer and read `schema_version`, `safety_contract`, `commands`, `commands.review_summary`, `commands.verify_manifest`, `expected_report_fragments`, `expected_review_stdout_fragments`, `expected_strategy_stdout_fragments`, `expected_repair_queue`, `self_check`, and `paths`; text mode prints `self_check=ok` when the generated manifest contract and local input files pass. Verifier automation can use `scripts/verify_weekly_smoke.py --manifest .tmp/weekly_smoke_manifest.json --verify-review-summary --verify-strategy-summary --json` and read `ok`, `errors`, `error_categories`, `paths`, `repair_queue`, `repair_queue.primary_repair_target`, `manifest_repair_queue`, and `strategy_summary` when `expected_repair_queue` or `expected_strategy_stdout_fragments` is present; the review-summary check reconstructs the local command from manifest paths instead of executing the manifest command string, while the strategy-summary check formats `paths.source_preflight_strategy` without browser, Notion, or provider IO. Manifest verification rejects stale or unsafe metadata with `manifest_schema_version_mismatch`, `manifest_profile_mismatch`, `manifest_safety_mismatch:*`, `manifest_missing_expected_fragment:*`, `manifest_missing_expected_review_stdout_fragment:*`, `manifest_invalid_expected_strategy_stdout_fragment:*`, `missing_strategy_stdout_fragment:*`, `manifest_expected_repair_queue_mismatch:*`, `manifest_missing_commands`, `manifest_missing_command:*`, or `manifest_command_missing_fragment:*`; with `--verify-review-summary`, missing sample input or stdout drift fails as `review_summary_missing_input:*` or `missing_review_summary_stdout_fragment:*` under `error_categories=["review_summary"]`, and stale strategy stdout fragments fail under `error_categories=["strategy_summary"]`. Command-contract failures mean the manifest no longer preserves the copy-ready `write_inputs`, `review_summary`, `build_report`, `verify_text`, `verify_json`, and `verify_manifest` commands, including `--manifest-output .tmp/weekly_smoke_manifest.json`, `--verify-review-summary`, `--verify-strategy-summary`, `--recompute-contract-input`, `--recompute-contract`, and `--self-check` when present. Unsafe manifests return `error_categories=["manifest"]`, and text mode prints `weekly_smoke=fail category=manifest`, for example `manifest_safety_mismatch:notion_writes=expected_false,actual_True`. Keep sample inputs and outputs under `.tmp/` and do not commit them.
   For the exact stale structured repair-queue shape, see the `Stale expected repair queue example` in [`docs/ops-runbook.md`](docs/ops-runbook.md); it shows `manifest_expected_repair_queue_mismatch:total=expected_7,actual_6` while preserving the actual `repair_queue` object and adding `manifest_repair_queue` mismatch metadata.
   When manifest review-summary verification runs with `--json`, the payload includes a `review_summary` block with `review_records`, `executed`, `returncode`, `expected_stdout_fragment_count`, `matched_stdout_fragment_count`, `missing_stdout_fragment_count`, and `timeout_seconds` so automation can debug the exact local sample and contract coverage. For failure triage, read `review_summary.diagnosis`, `review_summary.failure_reasons`, `review_summary.missing_stdout_fragments`, `review_summary.missing_input`, `review_summary.stdout_drift`, `review_summary.timeout`, `review_summary.nonzero_exit`, `review_summary.run_failed`, and `review_summary.manifest_contract_error` instead of parsing raw error strings. The primary diagnosis is always the first prioritized `review_summary.failure_reasons` entry, so automation can route on `review_summary.diagnosis` while still preserving secondary causes. If parent `error_categories=["manifest"]` appears with a `review_summary` block, the review-summary child did not run (`executed=false`, `returncode=null`); fix the manifest/writer contract first, then rerun review-summary verification. On child-process failures, `review_summary.child_error_tail`, `review_summary.child_error_tail_source`, and `review_summary.child_error_tail_truncated` may also appear with a bounded stderr/stdout tail. Text mode keeps review-summary failures compact as `weekly_smoke=fail reason=...`; child stderr/stdout tails stay JSON-only in `review_summary.child_error_tail`. For review-summary child failures, text mode reports `review_summary_timeout`, `review_summary_run_failed:*`, `review_summary_missing_input:*`, `review_summary_exit_code:*`, and `missing_review_summary_stdout_fragment:*` only as reason fragments. If `review_summary.nonzero_exit=true`, inspect `review_summary.child_error_tail` when present, fix the child process failure first, and treat `matched_stdout_fragment_count` as partial evidence only; a zero match count means the subprocess failed before summary output, while a partial match count means the summary started but its stdout contract was incomplete.
   For exact review-summary JSON shapes, see the `Review-summary stdout drift example`, `Review-summary missing input example`, `Review-summary manifest contract example`, `Review-summary timeout example`, `Review-summary run failed example`, `Review-summary nonzero exit example`, and `Review-summary mixed nonzero/stdout drift example` in [`docs/ops-runbook.md`](docs/ops-runbook.md); they show `diagnosis="stdout_drift"`, `diagnosis="missing_input"`, `diagnosis="manifest_contract"`, `manifest_invalid_expected_review_stdout_fragment:*`, `diagnosis="timeout"`, `diagnosis="run_failed"`, `diagnosis="nonzero_exit"`, the missing stdout fragment list, the missing local sample path, the manifest contract flag, the child process return code, the bounded child error tail, the child process launch exception, and a combined nonzero child exit with secondary stdout drift.
   When `missing_metric_rate_high` blocks rollout, the weekly report `Next manual action:` preserves the owner-specific action, for example `cost_tracking: Include token_cost_estimate from the generation cost tracker.`, instead of only showing a generic fill-missing-metrics instruction.
   Automation can read `summary.candidate_rollout_blocker_actions[]` for a flat repair queue with `code`, `source`, `operator_action`, and owner/top-metric fields when available. The weekly report renders the same queue as `Rollout blocker actions:` so human review sees the repair list without opening JSON.
   For provider failures, read `provider_failure_summary.primary_failure` and `primary_operator_action` before rerunning. Treat auth, quota/billing, and invalid-output primary failures as repair-first; treat rate-limit, overload, server, timeout, and network primary failures as retry/backoff candidates. Do not change fallback order only because a primary failure is retryable.

   Command-contract drift example:

   ```json
   {"error_categories":["manifest"],"errors":["manifest_command_missing_fragment:write_inputs:--manifest-output .tmp/weekly_smoke_manifest.json"],"manifest":".tmp/weekly_smoke_manifest.json","ok":false,"paths":{"recompute_contract":".tmp/recompute_scores_runtime_contract_smoke.json","report":".tmp/weekly_report_smoke.md","review_experiment":".tmp/weekly_report_experiment_smoke.json","source_preflight_strategy":".tmp/source_preflight_strategy_simulation.json","source_preflight_trend":".tmp/source_preflight_trend.json"},"repair_queue":{"consistency":"ok","count_total":6,"full_queue_available":true,"listed":6,"present":true,"primary_repair_command_present":true,"primary_repair_target":{"buckets":{"blind|blocked":1},"command":"py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json --fail-on-warning","count":1,"present":true,"sources":{"blind":1},"type":"evidence_doctor"},"queue_item_count":6,"source":"manual_ready_gate.repair_commands","total":6},"status":"fail"}
   ```

   리포트 끝에 `## Best-of-N Comment-Weight Tuning (dry-run)` 섹션이 자동으로 임베드됩니다 (`scripts/tune_best_of_n_weight.py`의 dry-run 분석을 30일 윈도우로 호출). 표본이 부족하거나 tuner가 실패해도 본문은 깨지지 않으며 (fail-open), 권장 `llm.best_of_n_comment_weight` 값이 표시될 때만 설정 검토를 시작하면 됩니다.

2. 최근 30일 점수 재계산

```bash
py -3 scripts/recompute_scores.py --write-sample-input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --validate-input --input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --assert-runtime-contract --input .tmp/recompute_scores_fixture.json --json
py -3 scripts/recompute_scores.py --config config.example.yaml --input .tmp/recompute_scores_fixture.json --dry-run --json
py -3 scripts/recompute_scores.py --days 30 --dry-run --json
py -3 scripts/recompute_scores.py --days 30
```

Use `--write-sample-input` to create a known-good fixture in `.tmp`, then validate it before editing `candidate_ranking_weights`.
Run `--validate-input` first and require `status="ok"`, empty `errors`, `safety.notion_reads=false`, and `safety.notion_writes=false` before using a fixture for scoring comparison.
Check the dry-run JSON for `mode="dry-run"`, `safety.notion_writes=false`, `planned`, `score_update_samples`, and `operator_action` before running the write command.
Use `--input .tmp/recompute_scores_fixture.json --dry-run --json` for an offline score fixture that does not read or write Notion; the fixture may be either a records array or an object with `records` and optional `historical_examples`.
`--validate-input` only checks fixture shape and safety flags; `--input ... --dry-run` also runs content-intelligence scoring and may initialize optional local/ML model caches such as Hugging Face. For strict offline scoring dry-runs, prepare the cache first before setting `HF_HUB_OFFLINE=1`.
First-class runtime-contract gate before scoring:

```bash
py -3 scripts/recompute_scores.py --assert-runtime-contract --input .tmp/recompute_scores_fixture.json --json
```

Use this first-class gate instead of maintaining the jq/Python one-liner; it exits 0 only when validation is ok and the runtime contract says validation loads no runtime dependencies or scoring.
Optional field-level check for saved validation JSON:

```bash
py -3 scripts/recompute_scores.py --validate-input --input .tmp/recompute_scores_fixture.json --json > .tmp/recompute_scores_validate.json
jq -e '.ok == true and (.errors | length) == 0 and .safety.notion_reads == false and .safety.notion_writes == false and .runtime_contract.validation.loads_runtime_dependencies == false and .runtime_contract.validation.scoring_runs == false and .runtime_contract.scoring_dry_run.scoring_dependencies_may_initialize == true' .tmp/recompute_scores_validate.json
```

If `jq` is not installed, use the Python fallback:

```bash
py -3 -c "import json,pathlib; p=json.loads(pathlib.Path('.tmp/recompute_scores_validate.json').read_text(encoding='utf-8-sig')); ok=p.get('ok') is True and not p.get('errors') and p['safety']['notion_reads'] is False and p['safety']['notion_writes'] is False and p['runtime_contract']['validation']['loads_runtime_dependencies'] is False and p['runtime_contract']['validation']['scoring_runs'] is False and p['runtime_contract']['scoring_dry_run']['scoring_dependencies_may_initialize'] is True; raise SystemExit(0 if ok else 1)"
```

The first-class gate reads only the validation JSON path and does not run scoring, Notion reads, Notion writes, X posts, providers, or browser capture.
For scoring-weight A/B, add `candidate_ranking_weights` to the fixture object and inspect `score_comparison.average_score_delta`, `improved_count`, `regressed_count`, and `variants.candidate.signals.operator_action_required` before changing `ranking.weights`.

3. 리포트를 보고 `ranking.final_rank_min`, `review.queue_limit_per_run`, `llm.providers` 순서를 조정합니다.

## GitHub Actions

현재 CI는 워크스페이스 매트릭스 워크플로 (`.github/workflows/full-test-matrix.yml`)의 `blind-to-x-tests` 잡으로 통합되어 있으며, `main` 푸시 / PR 시 자동 실행됩니다.

- 단위 테스트: `python -m pytest tests/unit -q --tb=short --maxfail=1`
- 통합 테스트: `python -m pytest tests/integration ... --ignore=tests/integration/test_curl_cffi.py`

크론/스케줄 실행은 현재 활성화되어 있지 않습니다. 정기 적재가 필요하면 별도 스케줄러(예: workspace `execution/scheduler_engine.py`)를 사용합니다.

## 관측성 (Observability)

- **Langfuse 트레이스**: `LANGFUSE_ENABLED=1` 환경변수가 설정되면 `pipeline/draft_providers.py`가 워크스페이스 Langfuse 훅으로 LLM 호출 메타데이터(프로바이더, 모델, 토큰, 지연, 성공 여부)를 전송합니다.
- **워크스페이스 사용량 미러링**: `BTX_USAGE_FORWARD=1` 일 때 `pipeline/cost_tracker.py`가 프로젝트 로컬 `btx_costs.db` 기록과 동시에 워크스페이스 `.tmp/workspace.db`의 `api_calls` 테이블에도 사용량을 미러링합니다. 워크스페이스 알림(`api_usage_tracker alerts` — fallback rate / cost spike / dead provider)이 blind-to-x 호출까지 감지하도록 활성화합니다.
- 프로젝트 로컬 cost db (`btx_costs.db`)는 항상 기록되며 진실의 원천(authoritative source)입니다. 미러링은 부가 관측 채널입니다.
- CostDB가 잠기거나 읽기 전용이 되면 `CostTracker.get_cost_persistence_status()`는 `status=degraded`, `fail_open=true`, `event_count`, `retained_event_count`, `total_event_count`, `operation_count`, `last_operation`, `last_error_type`, `error_types`, `operations`, `operator_action`을 반환합니다. Summary에는 `Cost Persistence: degraded`, `Cost Persistence Last Error`, `Cost Persistence Action`이 표시되며, 파이프라인은 in-memory counters로 계속 진행합니다. `btx_costs.db`, archive DB, `.tmp/workspace.db`는 커밋하지 않습니다.

## 장애 대응

`scripts/notion_doctor.py`가 실패하면:

- `NOTION_API_KEY`가 Notion integration Bearer token인지
- `NOTION_DATABASE_ID`가 현재 database/data_source collection mode에 맞는 ID인지
- 403/404라면 대상 database/data_source가 integration에 공유되어 있는지
- 429/5xx/529라면 `Retry-After`/backoff 이후 재시도할 문제인지
- Notion 속성명

을 먼저 확인합니다.

Blind 수집 실패가 늘어나면:

- `.tmp/app_debug.log`
- `.tmp/failures`

를 확인해서 사이트 구조 변경 또는 차단 여부를 봅니다.

LLM 호출이 실패하면:

- `Gemini -> DeepSeek -> xAI -> Moonshot -> ZhipuAI -> OpenAI -> Anthropic` 순서로 자동 fallback 됩니다.
- 특정 공급자를 우선으로 쓰고 싶다면 `config.yaml`의 `llm.providers` 순서를 바꾸면 됩니다.

## 테스트 현황

최근 기준으로 아래가 검증된 상태입니다.

- Notion 스키마 진단 통과
- `review-only` 실배치 성공
- Anthropic 잔액 부족 시 Gemini fallback 성공
- 검토 큐 적재 성공
- 환경변수 기반 런타임 fallback 테스트 통과

자동 발행은 현재 기본 운영 범위가 아니므로, 특정 채널 키가 없어도 검토 큐 운영은 정상적으로 가능합니다.
