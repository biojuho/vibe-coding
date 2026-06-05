---
name: auto-research
description: Bounded Karpathy-style autonomous research and product-improvement loop. Use when the user asks for 오토리서치, autoresearch, Karpathy-style self-improvement, continuous A/B testing, product launch polish, GitHub PR/dependency triage, or browser-click QA that should research, implement, verify, compare variants, and adopt only evidence-backed improvements.
---

# Auto Research

Run a bounded self-improvement loop that turns "keep improving this product" into small experiments with clear metrics, verification, and GitHub-safe adoption.

## Core Rule

Never treat "loop forever" as permission to make unbounded, blind, or unrelated changes. Convert it into repeatable cycles:

1. Pick one target project and one hypothesis.
2. Capture baseline evidence.
3. Build one candidate variant.
4. Verify with tests, app-click QA, and current external research when relevant.
5. Compare baseline vs candidate with an explicit metric.
6. Adopt, revert, or open a follow-up based on evidence.
7. Record the cycle so the next agent can continue.

## Workflow

### 1. Rehydrate State

In the `Vibe coding` workspace, read `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/DECISIONS.md`, and `.ai/TOOL_MATRIX.md`, then run:

```bash
python execution/session_orient.py --json
```

Use graph/context tools before broad text search when they are available. Preserve unrelated dirty-tree work.

### 2. Scope One Experiment

Choose the next cycle from the user's goal, active tasks, GitHub PRs, product readiness gaps, or visible UI defects. Write a compact hypothesis:

```text
If we change <surface>, then <metric or user workflow> improves because <reason>.
```

Define:

- Editable files or modules
- Frozen comparison inputs
- Required gates
- Baseline and candidate metrics
- Stop condition for the current cycle

If the work touches UI, include direct browser/app-click verification. If it touches dependencies or GitHub PRs, inventory current PRs first.

### 3. Research Before Editing

For libraries, GitHub workflows, browser issues, or product patterns that may have changed, search current official docs, release notes, GitHub issues, and primary sources before coding. Record source URLs in notes or references. Avoid copying unverified blog claims into implementation decisions.

Use `references/karpathy-autoresearch.md` for the source concept and `references/loop-contract.md` for the reusable loop contract.

### 4. Build Variant

Implement the smallest candidate that can prove or disprove the hypothesis. Keep the mutable surface narrow, similar to Karpathy's editable-file boundary: one feature area, one PR, one dependency family, or one user flow per cycle.

When using app-click QA:

- Start the dev server if needed.
- Click the critical workflow manually or through Playwright/browser automation.
- Inspect console and network errors.
- Capture screenshots when visual regressions are possible.
- Fix observed issues before scoring.

### 5. Verify And Compare

Run the focused gate first, then broaden only as risk increases. Typical gates:

- Unit/integration tests for touched files
- Lint/typecheck/build
- `git diff --check`
- Project QC runner when available
- Browser smoke for user-facing flows
- Live checks only when credentials and cost boundaries are clear

Use `scripts/ab_decision.py` when metrics are numeric. The candidate is adopted only when required gates pass and the weighted score improves beyond the configured minimum delta.

## Completion Audit

Before claiming a launch, product-complete state, or long-running objective is complete, build a requirement-to-evidence manifest and run:

```bash
python .agents/skills/auto-research/scripts/completion_audit.py .tmp/completion-audit.json --json
```

Read `references/completion-audit.md` for the manifest shape. A `complete` result requires every explicit requirement to have artifacts, current evidence, `verified: true`, and complete coverage. Incomplete or blocked items mean the next auto-research cycle must continue instead of declaring success.

To generate a launch-objective manifest from current workspace evidence first, run:

```bash
python .agents/skills/auto-research/scripts/launch_objective_audit.py --root . --output .tmp/launch-objective-audit.json --json
python .agents/skills/auto-research/scripts/completion_audit.py .tmp/launch-objective-audit.json --json --allow-incomplete
```

### 6. Adopt, Commit, Push

Adopt the candidate only when evidence is stronger than the baseline. Revert candidate edits when the evidence is worse or inconclusive, without touching unrelated user changes.

Commit only scoped changes. Push only when the user explicitly requested push for this session or the repository's current workflow requires it. If pushing would also publish unrelated ahead commits, state that boundary before pushing unless the user already asked for all pending commits to be pushed.

### 7. Continue Across Sessions

After each material cycle, update `.ai/TASKS.md`, `.ai/HANDOFF.md`, and `.ai/SESSION_LOG.md`. If the user asked to keep improving until stopped, add the next concrete experiment as TODO or IN_PROGRESS so the next session can continue without rediscovery.

## GitHub Project Inventory

Run the local inventory helper before GitHub-wide work:

```bash
python .agents/skills/auto-research/scripts/github_project_inventory.py --root . --include-prs --json
```

Use it to identify active projects, GitHub workflow files, Dependabot state, open PRs, and dirty-tree risks.

## Browser QA Evidence Inventory

Run the local browser QA inventory before choosing the next app-click cycle:

```bash
python .agents/skills/auto-research/scripts/browser_qa_inventory.py --root . --json
```

Use it to identify browser apps with verified direct-click evidence, current `output/playwright` screenshots, and projects that still need a browser QA pass.
The inventory reports fresh and stale retained screenshots; refresh screenshots older than the configured freshness window before using them as launch evidence.
Keep auto-research JSON output ASCII-escaped so Windows PowerShell default file reads do not corrupt Korean profile paths in evidence files.

## Dependency Freshness Inventory

Run the local npm dependency freshness inventory before choosing dependency work:

```bash
python .agents/skills/auto-research/scripts/dependency_freshness_inventory.py --root . --json
```

Use it to separate direct patch/minor adoption candidates from major migrations and prerelease/stable channel mismatches. Treat `defer_major_migration` and `defer_channel_mismatch` as separate upgrade experiments, not routine freshness work.
Prerelease packages that are current on their matching npm dist-tag are reported as `current_prerelease_channel` instead of deferred, so lower stable `latest` tags do not become false blockers.
Deferred major migrations may include lockfile peer blocker evidence when installed package peer ranges do not allow the target major.
When every remaining major migration is peer-blocked, treat the next action as waiting for upstream peer support instead of retrying a forced install.

## A/B Decision Helper

Create a manifest and score it:

```bash
python .agents/skills/auto-research/scripts/ab_decision.py .tmp/ab-manifest.json
```

Use this for deterministic keep-or-adopt decisions. Do not use it as a substitute for reading failures or inspecting screenshots.

## Stop Conditions

Stop the current cycle and report clearly when:

- Required credentials, paid quotas, or external approvals are unavailable.
- Required gates fail after reasonable self-repair.
- The candidate is not better than baseline.
- The work would require reverting or overwriting unrelated user changes.
- The next improvement is a distinct new experiment better tracked as a follow-up.
