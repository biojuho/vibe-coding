# Source Preflight Repair Flow

This runbook is for local evidence repair before any source selector, timeout, or strategy change.
It does not authorize an auto-publish default, automatic Notion writes, X/Threads/blog posts, browser reruns, or source-strategy edits.

## Inputs

- Source preflight report: `.tmp/source_browser_preflight*.json`
- Failure reports: `.tmp/failures/source_preflight/*.json`
- Screenshots: `screenshots/source_preflight/*`
- Optional trace zip files: `.tmp/traces/source_preflight/*.zip`

Keep all generated evidence under `.tmp/`, `screenshots/`, or another ignored local artifact path. Do not commit evidence files, traces, screenshots, logs, keys, tokens, or databases.

## Flow

0. Inspect the effective `main.py` source-preflight options before launching a browser.

```powershell
py -3 main.py --config config.example.yaml --source ppomppu --source-preflight-print-options
```

The output is JSON and should show `browser_probe_will_run=false`, `notion_writes=false`, `x_posts=false`, `read_only=true`, `auto_apply_allowed=false`, and `manual_strategy_review_required=true`. Use it to confirm source selection, config defaults, CLI overrides, safety policy, and artifact paths before running a capture command. This command does not launch Playwright, call providers, write Notion, or post to X/Threads/blog.

1. Capture source evidence only when needed.

```powershell
py -3 main.py --source all --popular --review-only --limit 5 --require-source-ready --source-preflight-click-through --source-preflight-use-recommended --source-preflight-output .tmp/source_browser_preflight.json --source-preflight-screenshot-dir screenshots/source_preflight --source-preflight-failure-dir .tmp/failures/source_preflight
```

Add trace capture only when screenshot/html/error evidence is not enough:

```powershell
py -3 main.py --source all --popular --review-only --limit 5 --require-source-ready --source-preflight-click-through --source-preflight-use-recommended --source-preflight-output .tmp/source_browser_preflight.json --source-preflight-screenshot-dir screenshots/source_preflight --source-preflight-failure-dir .tmp/failures/source_preflight --source-preflight-trace-dir .tmp/traces/source_preflight
```

2. Validate the captured evidence before changing source strategy.

```powershell
py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight.json --base-dir . --fail-on-warning
```

If the doctor prints `repair_commands`, run the first relevant command, then rerun the doctor. Do not tune selectors or timeouts while `fix_evidence_first` remains.

`operator_action_mismatch` is a stale-evidence signal: the preflight summary and failure report disagree. Repair or recapture evidence first; selector, timeout, and source-strategy review wait until the doctor returns `strategy_review_ready`.

Strategy simulation preserves `operator_action_mismatch_count` and keeps mismatch-driven stale evidence in `fix_evidence_first`, so `--require-manual-ready` blocks with `manual_ready_gate.status=blocked` until the evidence is repaired.

3. Summarize repeated local failures without browser, Notion, X, or provider calls.

```powershell
py -3 scripts/source_preflight_trend_report.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_trend.json --json
```

Review these fields first:

- `summary.repair_command_count`
- `summary.repair_command_type_counts`
- `summary.top_repair_commands`
- `summary.evidence_gate_status_counts`
- `summary.operator_recommendation`

Run `summary.top_repair_commands` before any source strategy review when `repair_command_count > 0`.

4. Run the strategy dry-run gate.

```powershell
py -3 scripts/source_preflight_strategy_simulation.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_strategy_simulation.json --require-manual-ready
```

Expected outcomes:

- Ready for manual review: `manual_ready_gate.status=pass`, `repair_command_count=0`, `ready_for_manual_strategy_review=true`.
- Repair blocked: `comparison.recommendation=repair_evidence_first`, `manual_ready_gate.status=blocked`, `blocked_by` includes `repair_command_debt`, and the command exits `2`.

When blocked, run `manual_ready_gate.primary_repair_command` first. If `manual_ready_gate.repair_command_remaining_count > 0`, continue through `manual_ready_gate.repair_commands` before rerunning the gate.

For a fast stdout-only check that does not write output, run the same inputs with `--summary-only`. Confirm `primary_repair_type=TYPE`, `primary_repair_buckets=SOURCE|STATUS=N`, `repair_remaining=N`, `metric_missing=current:N/10,candidate:N/10`, `operator_action_mismatch_count=N`, `operator_action_mismatch_sources=SOURCE=N`, `scope=local_preflight_evidence`, `top_operator_action_count=N`, `top_operator_action_sources=SOURCE=N`, and `top_operator_action=...` before opening JSON. If `top_operator_action_count=0`, inspect the full trend JSON before treating the summary as action-complete.

5. Render weekly evidence from local JSON only.

```powershell
py -3 scripts/build_weekly_report.py --payload-input .tmp/weekly_report_payload_smoke.json --review-experiment-input .tmp/weekly_report_experiment_smoke.json --source-preflight-trend-input .tmp/source_preflight_trend.json --source-preflight-strategy-input .tmp/source_preflight_strategy_simulation.json --output .tmp/weekly_report_smoke.md
```

Confirm the report shows:

- `Source Preflight Trend (dry-run)`
- `Repair commands: total=...`
- `Source Preflight Strategy A/B (dry-run)`
- `Blocked checklist`
- `Manual-ready gate`
- `repair_command_debt` when repair commands remain

## Decision Rules

- Apply: run evidence doctor or source preflight capture commands that only repair local evidence.
- Apply: use ready fallback source for the current run when failures are `fallback_only`.
- Apply: review selectors/timeouts manually only after `strategy_review_ready` evidence is structurally complete.
- Do Not Apply: automatic selector/timeout/source changes from the dry-run output.
- Do Not Apply: automatic publish, Notion writes, X/Threads/blog posts, or provider calls from this flow.
- Risk: trace zip and screenshot artifacts can contain page data; keep them local and ignored.
