# Vibe Coding Project Rules

## Overview

- Workspace: `Vibe Coding`
- OS: Windows 11
- Architecture: Directive -> Orchestration -> Execution
- Canonical structure:
  - `workspace/` for root-owned directives, execution code, scripts, and tests
  - `projects/` for product repositories
  - `infrastructure/` for MCP servers and shared services
  - `.ai/`, `.agents/`, `.claude/` stay at repo root

## Directory Rules

```text
Vibe coding/
├── .ai/
├── .agents/
├── .claude/
├── .github/
├── .tmp/
├── _archive/
├── infrastructure/
├── projects/
│   ├── blind-to-x/
│   ├── hanwoo-dashboard/
│   ├── knowledge-dashboard/
│   ├── shorts-maker-v2/
│   ├── suika-game-v2/
│   └── word-chain/
├── workspace/
│   ├── directives/
│   ├── execution/
│   │   └── pages/
│   ├── scripts/
│   └── tests/
└── venv/
```

## Coding Rules

### Common

- Use UTF-8.
- Keep secrets in `.env`; never hardcode credentials.
- Put temporary logs, reports, and regenerated artifacts in `.tmp/` or project-local `.tmp/`.
- Use canonical paths in docs and automation: `workspace/...` and `projects/...`.
- Do not assume root-level product folders are canonical anymore.

### Python

- Use `snake_case` for files and functions.
- Prefer existing tools in `workspace/execution/` before creating new ones.
- Use `pytest` and `ruff`.

### Frontend

- Preserve each project's existing design system and framework conventions.
- Keep app-specific code inside the owning project under `projects/`.

## Session Workflow

- At session start, read `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/DECISIONS.md`, `.ai/TOOL_MATRIX.md`.
- Before large changes, inspect the current structure and existing tools.
- After changes, update AI context files when structure, conventions, or risks changed.
- Use the 4-step QA/QC workflow for meaningful code changes.

## Important Constraints

- Nested projects remain independent repositories or independent codebases.
- Do not flatten `projects/` into a monorepo.
- Preserve user WIP in dirty trees.
- Legacy compatibility is allowed inside automation only; new docs and commands should use canonical paths.
