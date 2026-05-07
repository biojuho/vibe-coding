# Vibe Coding Workspace

Root workspace for shared AI tooling, automation, and multiple product projects.

## Canonical Layout

- `.ai/`, `.agents/`, `.claude/`, `.github/`: shared AI/tooling control plane
- `workspace/`: root-owned directives, execution code, scripts, and tests
- `projects/`: app and pipeline projects
- `infrastructure/`: MCP servers and shared services
- `.tmp/`: regenerated local intermediates and reports
- `_archive/`: archived legacy material

## Installation

This repository uses [uv](https://astral.sh/uv) to manage isolated environments for each project.

```bash
# 1. Install uv in a root venv (or install globally: pip install uv)
py -3 -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip uv

# 2. Sync workspace environment (Control Plane)
cd workspace
..\venv\Scripts\uv.exe sync
cd ..

# 3. Sync blind-to-x environment (Dashboard / Pipeline)
cd projects\blind-to-x
..\..\venv\Scripts\uv.exe sync
cd ..\..

# 4. Sync shorts-maker-v2 environment (Video Automation)
cd projects\shorts-maker-v2
..\..\venv\Scripts\uv.exe sync
cd ..\..
```

## Common Commands (Workspace)

Navigate to the `workspace` directory before running these:
```bash
cd workspace
..\venv\Scripts\uv.exe run scripts\doctor.py
..\venv\Scripts\uv.exe run scripts\smoke_check.py
..\venv\Scripts\uv.exe run scripts\quality_gate.py
..\venv\Scripts\uv.exe run execution\qaqc_runner.py
..\venv\Scripts\uv.exe run streamlit run execution\pages\shorts_manager.py
```

## Testing

Navigate to the `workspace` directory before running these:
```bash
cd workspace
..\venv\Scripts\uv.exe run pytest -q tests
..\venv\Scripts\uv.exe run pytest -q execution\tests
```

## Projects

- `projects/blind-to-x`
- `projects/shorts-maker-v2`
- `projects/hanwoo-dashboard`
- `projects/knowledge-dashboard`
- `projects/suika-game-v2`
- `projects/word-chain`

## Technology Stack

See `docs/technology-stack.md` for the workspace stack policy.

- Current web default: React/Next.js with JavaScript or TypeScript.
- Current SaaS data path: PostgreSQL/Supabase-compatible database access through Prisma where applicable.
- Current async/cache path: Redis/BullMQ for internal jobs, plus native Fetch API wrappers for HTTP calls.
- Candidate-only: Svelte/SvelteKit, Go, Rust, Flutter/native mobile, RabbitMQ, and TanStack Query require an explicit design note before adoption.

## Shorts Workflow

1. `cd workspace && ..\venv\Scripts\uv.exe run streamlit run execution\pages\shorts_manager.py`
2. Save per-channel settings.
3. Render from Shorts Manager or run `..\venv\Scripts\uv.exe run execution\shorts_daily_runner.py` from `workspace`.
4. Review QA/QC in `..\venv\Scripts\uv.exe run streamlit run execution\pages\qaqc_status.py`.
5. Upload from the manager when credentials are available.

## Notes

- Canonical paths use `workspace/...` and `projects/...`.
- Internal automation still accepts legacy root project resolution during migration.
- Nested projects stay independent; this repo does not flatten them into a monorepo.
