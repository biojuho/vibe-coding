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

It also reads shared repo context from `.ai/SESSION_LOG.md` and QA/QC trend history from `workspace/execution/qaqc_history_db.py`.

### 2. Configure dashboard access

Set `DASHBOARD_API_KEY` before starting the app. The dashboard page calls authenticated route handlers under `src/app/api/data/*`, so the raw JSON files are no longer served from `public/`.

### 3. Run the dashboard

```bash
npm run dev
```

Open `http://localhost:3000` in your browser and enter the configured API key when prompted.

## Tech Stack

- Framework: Next.js 16
- Styling: Tailwind CSS
- Components: Radix UI + Lucide React
- Data sync: Python script + internal API routes

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
