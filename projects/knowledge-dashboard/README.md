# Joolife Knowledge Dashboard

GitHub repository activity and NotebookLM notebooks are surfaced in one internal dashboard.

## Getting Started

### 1. Sync dashboard data

Run the sync script to refresh the local dashboard dataset.

```bash
./sync.bat
```

The sync job writes internal data files to `data/`:

- `data/dashboard_data.json`
- `data/qaqc_result.json`
- `data/product_readiness.json`

It also reads shared repo context from `.ai/SESSION_LOG.md` and QA/QC trend history from `workspace/execution/qaqc_history_db.py`.
Product readiness can also be refreshed directly from the workspace root:

```bash
python execution/product_readiness_score.py
```

### 2. Configure dashboard access

Set `DASHBOARD_API_KEY` before starting the app. The dashboard page calls authenticated route handlers under `src/app/api/data/*`, so the raw JSON files are no longer served from `public/`.

### 3. Run the dashboard

```bash
npm run dev
```

Open `http://localhost:3000` in your browser and enter the configured API key when prompted.

## Tech Stack

- Framework: Next.js 16 + React 19
- Language: TypeScript
- Styling: Tailwind CSS
- Components: Radix UI + Lucide React
- Data sync: Python script + internal API routes

This project does not currently use Svelte, TanStack Query, Supabase/PostgreSQL, Redis, RabbitMQ, Go, Rust, Flutter, or native mobile runtimes. Follow the workspace policy in `../../docs/technology-stack.md` before introducing any of those.

## Folder Structure

- `scripts/`: data sync script
- `data/`: internal JSON data consumed by authenticated API routes
- `src/app/`: Next.js app router pages and API routes
- `src/components/`: dashboard UI components
- `sync.bat`: quick sync entrypoint

## Notes

- `public/` should only contain static assets, not dashboard or QA/QC JSON payloads.
- The API routes return `401` when the bearer key is missing or invalid.
- The API routes return `503` when `DASHBOARD_API_KEY` is not configured.
- The operations console reads `data/product_readiness.json`; regenerate it after QC runs, task-board changes, or release-blocker updates.
