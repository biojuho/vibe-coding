# Shorts Maker V2

One-click YouTube Shorts generation pipeline for topic research, scripts, TTS, visuals, rendering, thumbnails, and growth feedback loops.

## Status

This project is tracked by the workspace product-readiness dashboard. A launch-ready local state requires:

- focused project QC passing for tests and lint
- root launch documentation present
- local artifacts kept out of git
- API credentials configured in `.env`

Generated media, run logs, dashboards, and cost reports are local artifacts. Keep them under ignored output paths such as `output/`, `runs/`, `logs/`, and `.tmp/`.

## Quick Start

Run commands from `projects/shorts-maker-v2`.

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
shorts-maker-v2 doctor
```

Generate one Shorts video:

```powershell
shorts-maker-v2 run --topic "AI productivity tip" --channel ai_tech --config config.yaml
```

Batch-generate from a topic file:

```powershell
shorts-maker-v2 batch --topics-file .tmp/topics.txt --limit 5 --config config.yaml
```

## Operations

Common operator commands:

```powershell
shorts-maker-v2 costs --config config.yaml
shorts-maker-v2 dashboard --config config.yaml --out .tmp/dashboard.html
shorts-maker-v2 growth-sync --channel ai_tech --since-days 30 --out .tmp/growth-sync.json
```

Workspace verification from the repository root:

```powershell
python execution/project_qc_runner.py --project shorts-maker-v2 --json
python execution/product_readiness_score.py --json
```

Focused local verification from `projects/shorts-maker-v2`:

```powershell
python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1
python -m ruff check .
```

## Documentation

- `docs/README.md` - detailed package documentation used by `pyproject.toml`
- `ARCHITECTURE.md` - pipeline architecture and module boundaries
- `FEATURE.md` - feature map and expected product surface
- `docs/runbook.md` - operational runbook
- `.env.example` - required environment variable template
