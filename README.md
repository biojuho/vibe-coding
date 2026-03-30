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

```bash
py -3 -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m pip install -r requirements-dev.txt
venv\Scripts\python.exe -m pip install -e .\projects\shorts-maker-v2
```

## Common Commands

```bash
venv\Scripts\python.exe workspace\scripts\doctor.py
venv\Scripts\python.exe workspace\scripts\smoke_check.py
venv\Scripts\python.exe workspace\scripts\quality_gate.py
venv\Scripts\python.exe workspace\execution\qaqc_runner.py
venv\Scripts\python.exe -m streamlit run workspace\execution\pages\shorts_manager.py
```

## Testing

```bash
venv\Scripts\python.exe -m pytest -q workspace\tests
venv\Scripts\python.exe -m pytest -q workspace\execution\tests
venv\Scripts\python.exe workspace\scripts\quality_gate.py
```

## Projects

- `projects/blind-to-x`
- `projects/shorts-maker-v2`
- `projects/hanwoo-dashboard`
- `projects/knowledge-dashboard`
- `projects/suika-game-v2`
- `projects/word-chain`

## Shorts Workflow

1. Add topics in `workspace/execution/pages/shorts_manager.py`.
2. Save per-channel settings.
3. Render from Shorts Manager or `python workspace/execution/shorts_daily_runner.py`.
4. Review QA/QC in `workspace/execution/pages/qaqc_status.py`.
5. Upload from the manager when credentials are available.

## Notes

- Canonical paths use `workspace/...` and `projects/...`.
- Internal automation still accepts legacy root project resolution during migration.
- Nested projects stay independent; this repo does not flatten them into a monorepo.
