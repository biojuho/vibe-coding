# Vibe Coding: Personal Agent (Jarvis)

[![root-quality-gate](https://github.com/<OWNER>/<REPO>/actions/workflows/root-quality-gate.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/root-quality-gate.yml)

Your all-in-one AI assistant for desktop control, daily briefings, and fun.

## Features
- **Daily Briefing**: Weather, news, and voice synthesis (TTS).
- **Desktop Control**: Launch apps, open websites, and monitor system stats.
- **RAG Brain**: Chat with your local documents using Gemini/OpenAI providers.
- **Word Chain Game**: Play a game of word chain with the AI.

## Installation
1. Run `setup.bat` (Windows) to install dependencies.
2. Configure required API keys in `.env`.

## Usage
```bash
venv\Scripts\activate
venv\Scripts\python.exe -m streamlit run projects/personal-agent/app.py
```

Readiness check:
```bash
venv\Scripts\python.exe scripts\doctor.py
```

Run tests:
```bash
venv\Scripts\python.exe -m pip install -r requirements-dev.txt
venv\Scripts\python.exe -m pytest -q tests
```

Quality gate (single command):
```bash
venv\Scripts\python.exe scripts\quality_gate.py
```

CI uses the same command:
```bash
python scripts/quality_gate.py
```

## Root Repository Bootstrap
Initialize and connect this workspace as the root Joolife repository:

```bash
git init
git branch -M main
git remote add origin https://github.com/<OWNER>/<REPO>.git
git push -u origin main
```

Root tracking policy:
- Included: `execution/`, `scripts/`, `tests/`, `pages/`, `directives/`, `_archive/personal-agent/`, and root config/docs files.
- Excluded: nested independent repos (`blind-to-x/`, `hanwoo-dashboard/`, `knowledge-dashboard/`) and side projects via `.gitignore`.

## CI Quality Gate
- Workflow file: `.github/workflows/root-quality-gate.yml`
- Trigger: `push` / `pull_request` on `main`
- Runtime: `ubuntu-latest`, Python `3.14`
- Command: `python scripts/quality_gate.py`

Recommended repository rollout:
1. Enable branch protection for `main` (PR merge only).
2. Add `root-quality-gate` as a required status check.
3. Triage failures by phase in logs: `smoke_check`, `pytest`, `static analysis`.

Recommended initial commits:
1. `chore(repo): bootstrap root joolife repository skeleton`
2. `ci(quality): add root quality gate workflow and dependencies`

## Maintenance Scripts
Upgrade nested repositories safely:
```bash
venv\Scripts\python.exe scripts\update_all.py --list-only
venv\Scripts\python.exe scripts\update_all.py --strategy ff-only
```

Create data backups:
```bash
venv\Scripts\python.exe scripts\backup_data.py --with-env
venv\Scripts\python.exe scripts\backup_data.py --dry-run --with-env
```

## Legal and Privacy Disclaimer
1. **Local Execution**: This software runs on your local machine. The developer does not collect or store your data.
2. **API Usage**: User prompts may be processed by external model providers according to your configuration.
3. **No Liability**: The user assumes all responsibility for use of this software.
4. **Copyright**: External content summaries are for informational purposes.

## License
MIT License.
