# `workspace/scripts/` Guide

Workspace-wide operator and maintenance scripts live here.

## Recommended Operator Ladder

Use the control plane in this order unless you are debugging a specific issue:

| Tier | Command | Use it when | Output depth |
|------|---------|-------------|--------------|
| `FAST` | `python workspace/scripts/doctor.py` | You changed Python, venv, packages, or env vars and want a quick readiness signal | Local setup readiness |
| `STANDARD` | `python workspace/scripts/quality_gate.py` | You want a local pre-commit gate before handoff or review | Smoke + pytest + lint + high-severity static analysis |
| `DEEP` | `python workspace/execution/qaqc_runner.py` | You need the shared workspace approval-style pass and persisted QA/QC artifact | Cross-project QA/QC, governance, security, infra snapshot |
| `DIAGNOSTIC` | `python workspace/execution/health_check.py --category <name>` | Something is wrong and you need drill-down diagnostics instead of the default ladder | Focused env/api/filesystem/database/governance detail |

## Default Rule

- Start with `doctor.py`.
- If readiness looks fine, move to `quality_gate.py`.
- Use `qaqc_runner.py` when you need the deeper shared approval pass.
- Reach for `health_check.py` when you are isolating a problem, not as the default daily command.

## Scripts

| Script | Role | Typical use |
|--------|------|-------------|
| `doctor.py` | Fast readiness check | Daily setup verification |
| `quality_gate.py` | Standard local quality gate | Before commit / handoff |
| `smoke_check.py` | Lightweight import / compile validation | Called by `quality_gate.py` |
| `backup_data.py` | Backup critical local data | Manual / scheduled ops |
| `update_all.py` | Refresh local git repos | Manual maintenance |
| `seed_shorts_topics.py` | Seed shorts topics | One-off content ops |
| `schedule_yt_analytics.bat` | Trigger YouTube analytics collection | Task Scheduler / cron |

## `scripts/` vs `execution/`

- `workspace/scripts/`: operator entrypoints, quality gates, and maintenance helpers.
- `workspace/execution/`: deterministic business and control-plane modules.

## Active Backlog

Planning directives can describe future ideas, but execution priority lives in:

- `.ai/TASKS.md`
- `.ai/HANDOFF.md`

Treat roadmap-style directives as reference unless they are linked to an active task.
