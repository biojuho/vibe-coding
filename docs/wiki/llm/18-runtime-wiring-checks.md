# 18 - Runtime Wiring Checks
> `config-facts.json` and `code-facts.json` now work together. This page records how the wiki catches config providers that are documented in tracked YAML but not wired in runtime generation code. Related: [06-per-project](06-per-project.md), [14-maintenance-verification](14-maintenance-verification.md), [16-code-facts](16-code-facts.md), [17-config-facts](17-config-facts.md).

## Purpose

The previous manifests answered two separate questions:

| Manifest | Question |
|----------|----------|
| `code-facts.json` | What provider constants, default models, classes, methods, and `_generate_with_*` helpers exist in Python code? |
| `config-facts.json` | What provider fallback order, model defaults, pricing keys, and enabled flags exist in tracked YAML config? |

T-1580 adds the third question: **do tracked config providers have matching runtime wiring?**

## Current Checks

`execution/llm_wiki_audit.py --write-config-facts --json` now adds runtime checks into `docs/wiki/llm/config-facts.json`.

| Check | Comparison | Current result | Classification |
|-------|------------|----------------|----------------|
| `shorts_maker_v2_config_runtime_models` | `projects/shorts-maker-v2/config.yaml` provider order vs `LLMRouter.DEFAULT_MODELS` providers | `pass` | n/a |
| `blind_to_x_config_example_runtime_helpers` | `config.example.yaml` `llm.providers` vs `DraftProvidersMixin._generate_with_*` helper providers | `warning` | `accepted_known` |
| `blind_to_x_config_ci_runtime_helpers` | `config.ci.yaml` `llm.providers` vs `DraftProvidersMixin._generate_with_*` helper providers | `warning` | `accepted_known` |

The blind-to-x warning is intentional and now machine-visible:

| Direction | Providers |
|-----------|-----------|
| In tracked config but missing runtime helper | `deepseek`, `moonshot`, `zhipuai` |
| Runtime helper but outside tracked config | `ollama` |

That means a future change cannot silently remove or add these gaps. The gap list is part of the stable `config-facts.json` payload, so `config_facts_drift` fires when runtime helper coverage changes without regenerating and reviewing the manifest.

## A/B Decision

| Criterion | A. Keep prose warning only | B. Store runtime wiring checks in config facts |
|-----------|----------------------------|----------------------------------------------|
| Drift visibility | Easy to miss during review | Deterministic `config_facts_drift` detects changed helper coverage |
| Reader clarity | Warning may diverge from code | JSON shows exact `missing_runtime_providers` and `runtime_providers_outside_config` |
| Implementation scope | No code change | Small extension of the existing audit manifest |
| False confidence risk | High, because config coverage can still pass | Lower, because model/pricing coverage and runtime wiring are separate checks |

**Decision:** use B. Keep the prose warning in [06-per-project](06-per-project.md), but make `config-facts.json` the source of truth for the exact cross-manifest gap list.

## Warning Classification Policy

The audit deliberately separates **accepted known** manifest warnings from **unexpected** manifest warnings. This follows the same operational idea as SARIF's `baselineState`: a result can be new, unchanged, updated, or absent relative to a previous run, and tools need stable identity to decide which case applies. GitHub code scanning also records dismissal reasons and optional comments for alerts that are intentionally closed instead of fixed immediately.

| Criterion | A. Fail every manifest warning | B. Non-failing warnings with `accepted_known` vs `unexpected` |
|-----------|-------------------------------|--------------------------------------------------------------|
| New drift visibility | Strong, but mixed with existing debt | Strong; `manifest_check_unexpected_warning_count` isolates new drift |
| Current blind-to-x debt | Blocks every clean wiki audit until runtime providers are built | Remains visible with exact ids, provider gaps, and accepted reason |
| Review burden | Reviewers must remember which warnings are already known | JSON/text output carries classification and reason |
| False confidence risk | Low, but noisy enough to be bypassed | Low if automation watches unexpected count, not only pass/fail |

**Decision:** use B. The current two blind-to-x runtime-helper gaps are `accepted_known`. Any warning without explicit acceptance metadata is `unexpected`; the audit remains non-failing for now, but reviewers must treat unexpected warnings as new drift.

## Maintenance Flow

```bash
# Regenerate Python code facts if provider constants or helper methods changed.
py -3.13 execution/llm_wiki_audit.py --write-code-facts --json

# Regenerate tracked YAML config facts and runtime wiring checks.
py -3.13 execution/llm_wiki_audit.py --write-config-facts --json

# Final no-write audit.
py -3.13 execution/llm_wiki_audit.py --json

# CI/strict gate: fail only on unexpected manifest warnings.
py -3.13 execution/llm_wiki_audit.py --strict-manifest-warnings --json
# Release/current-head evidence artifact for the same strict gate.
py -3.13 execution/llm_wiki_audit.py --write-strict-release-evidence --json
# Reviewer-visible summary/checklist from the release packet.
py -3.13 .agents/skills/auto-research/scripts/llm_wiki_release_summary.py --root . --packet .tmp/release-authorization-packet.json --output .tmp/llm-wiki-release-summary.md --artifact-dir release-evidence/llm-wiki --json
```

The default final audit keeps these warnings non-failing. Text output separates `audit warnings` from `manifest warnings`, and JSON output exposes `summary.manifest_check_warning_count`, `summary.manifest_check_warning_classification_counts`, `summary.manifest_check_unexpected_warning_count`, `summary.config_fact_check_status_counts`, and `summary.manifest_check_warnings`. Treat `status: pass` plus `accepted_known` warnings as "structure is valid, known wiring gaps remain visible"; treat any `unexpected` manifest warning as new drift that needs review. Use `--strict-manifest-warnings` in CI or release checks to turn unexpected manifest warnings into exit 1 while still allowing accepted known debt. Use `--write-strict-release-evidence` when the same gate needs a durable artifact; the JSON records the release gate verdict, accepted/unexpected warning counts, the report payload, and current git HEAD when available. The auto-research release authorization packet consumes that JSON as `llm_wiki_strict_evidence`; missing evidence, failed strict status, or a HEAD mismatch becomes a release blocker and launch-objective audit evidence. `llm_wiki_release_summary.py` then turns the packet evidence into a stable `GITHUB_STEP_SUMMARY` checklist and can copy JSON/Markdown into `release-evidence/llm-wiki` so `actions/upload-artifact@v7` does not have to upload hidden `.tmp` paths directly.

When adding a blind-to-x provider to `config.example.yaml` or `config.ci.yaml`, also add the corresponding `DraftProvidersMixin._generate_with_<provider>` helper or record the provider as an intentional config-only gap in `config-facts.json` with `warning_classification: accepted_known` and a reviewable `accepted_reason`.

## 출처

- Official: Python `json` standard library documentation: <https://docs.python.org/3/library/json.html>
- Official: Python `argparse` standard library documentation: <https://docs.python.org/3/library/argparse.html>
- Official: Python `sys` standard library documentation: <https://docs.python.org/3/library/sys.html>
- Official: Python `warnings` standard library documentation: <https://docs.python.org/3/library/warnings.html>
- Official: Python `pathlib` standard library documentation: <https://docs.python.org/3/library/pathlib.html>
- Official standard: OASIS SARIF v2.1.0 Errata 01, `baselineState` and suppressions: <https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/sarif-v2.1.0-errata01-complete.pdf>
- Official: GitHub Docs, resolving and dismissing code scanning alerts: <https://docs.github.com/en/enterprise-server@3.17/code-security/how-tos/manage-security-alerts/manage-code-scanning-alerts/resolving-code-scanning-alerts>
- Official: GitHub Docs, workflow artifacts: <https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts>
- Official: GitHub `actions/upload-artifact`: <https://github.com/actions/upload-artifact>
- Official: GitHub Docs, workflow commands / job summaries: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands>
- Code evidence: `execution/llm_wiki_audit.py`, `workspace/tests/test_llm_wiki_audit.py`, `docs/wiki/llm/code-facts.json`, `docs/wiki/llm/config-facts.json`

*외부 자료 검증일: 2026-06-08 - manifest verification: current HEAD*
