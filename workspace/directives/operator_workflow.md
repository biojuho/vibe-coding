# Operator Workflow

> Canonical control-plane operator ladder for the shared workspace.
> Active execution priority lives in `.ai/TASKS.md` and `.ai/HANDOFF.md`.

## Goal

Reduce operator confusion by making it obvious which check to run next.

## Default Ladder

1. `FAST` - `python workspace/scripts/doctor.py`
   Use after Python, package, venv, or `.env` changes.

2. `STANDARD` - `python workspace/scripts/quality_gate.py`
   Use before commit or handoff to catch local regressions.

3. `DEEP` - `python workspace/execution/qaqc_runner.py`
   Use when you need the shared approval-style pass and persisted QA/QC artifact.

4. `DIAGNOSTIC` - `python workspace/execution/health_check.py --category <name>`
   Use only when you are isolating a specific issue in `env`, `api`, `filesystem`, `database`, `environment`, or `governance`.

## Decision Table

| Situation | Command |
|-----------|---------|
| "Did my environment break?" | `doctor.py` |
| "Can I trust this local change set?" | `quality_gate.py` |
| "Is the shared workspace still approved?" | `qaqc_runner.py` |
| "Which subsystem is broken?" | `health_check.py --category ...` |

## Rules

- Do not add a new top-level operator script unless it clearly replaces one of the commands above.
- Prefer documenting escalation between existing entrypoints over introducing wrappers.
- If a planning directive is not tied to an active task, treat it as reference context rather than executable backlog.

## Outputs

- `doctor.py`: quick human-readable readiness summary
- `quality_gate.py`: local pass/fail gate for smoke, tests, lint, and static analysis
- `qaqc_runner.py`: persisted QA/QC JSON plus history DB entry
- `health_check.py`: focused diagnostic report or JSON detail

## Verification

- `python workspace/scripts/doctor.py`
- `python workspace/execution/health_check.py --category governance --json`
- `python workspace/scripts/quality_gate.py`
- `python workspace/execution/qaqc_runner.py`
