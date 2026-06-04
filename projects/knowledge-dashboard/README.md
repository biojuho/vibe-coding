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
- `data/skill_lint.json`

It also reads shared repo context from `.ai/SESSION_LOG.md` and QA/QC trend history from `workspace/execution/qaqc_history_db.py`.
Product readiness can also be refreshed directly from the workspace root:

```bash
python execution/product_readiness_score.py
python execution/skill_lint.py
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

## Deployment

This is an internal, authenticated dashboard. To ship a production build:

1. **Set environment variables** (server-side only — never expose to the client):

   | Variable | Required | Purpose |
   |---|---|---|
   | `DASHBOARD_API_KEY` | ✅ | API key clients exchange for an `httpOnly` signed session cookie (ADR-023). Routes return `503` if unset, `401` if a request presents the wrong key. |
   | `DASHBOARD_SESSION_SECRET` | optional | Dedicated HMAC secret for signing session cookies. Defaults to `DASHBOARD_API_KEY`. Set a separate value to rotate sessions without changing the login key. |
   | `GITHUB_PERSONAL_ACCESS_TOKEN` | optional | Used by `sync_data.py` to fetch repo activity. |
   | `NOTEBOOKLM_AUTH_TOKEN_PATH` | optional | Override for the NotebookLM token file used during sync. |

   See `.env.example` for a copy-paste template.

2. **Generate the data set before deploy.** The dashboard reads JSON from `data/`
   (gitignored), so run the sync first. The sync reads workspace-wide context
   (`.ai/SESSION_LOG.md`, `workspace/execution/*`, NotebookLM tokens), so it must
   run from a **full workspace checkout**, not a bare copy of this sub-directory:

   ```bash
   npm run sync         # = python scripts/sync_data.py  (also: ./sync.bat)
   ```

3. **Build and start:**

   ```bash
   npm run build        # `prebuild` strips any public/*.json first (ADR-023)
   npm run verify-deploy  # confirms the API key + data files are present
   npm run start        # serves the production build
   ```

   **Vercel:** a vanilla Vercel build of this sub-path **cannot** run the sync (it
   needs the whole monorepo and the Python toolchain). Generate `data/*.json` in a
   predeploy step that has the full workspace, then deploy with the env vars set.

   **Docker:** a multi-stage `Dockerfile` (Next.js `output: "standalone"`) is
   included. Mount the synced data in:

   ```bash
   docker build -t knowledge-dashboard .
   docker run -p 3000:3000 -e DASHBOARD_API_KEY=… \
     -v "$PWD/data:/app/data:ro" knowledge-dashboard
   ```

   **Health probe:** `GET /api/health` is unauthenticated and returns `200` when
   `DASHBOARD_API_KEY` is configured, `503` otherwise — wire it to your load
   balancer / uptime monitor (the Docker image already has a `HEALTHCHECK`).

### Data & security invariants

- **Never commit data payloads.** `data/*.json` and `public/*.json` are gitignored.
  All dashboard/QA-QC data is served **only** through the authenticated
  `src/app/api/data/*` routes — never from `public/` (which is web-served without auth).
- `sync_data.py` mirrors the QA/QC artifact into the authenticated `data/qaqc_result.json`
  that `/api/data/qaqc` serves, so the route never returns a stale copy.
- Authentication is enforced in `src/lib/dashboard-auth.ts` (HMAC-SHA256 signed,
  12-hour TTL, timing-safe). Do not bypass it.

## Notes

- `public/` should only contain static assets, not dashboard or QA/QC JSON payloads.
- The API routes return `401` when the bearer key is missing or invalid.
- The API routes return `503` when `DASHBOARD_API_KEY` is not configured.
- The operations console reads `data/product_readiness.json`; regenerate it after QC runs, task-board changes, or release-blocker updates.
- The operations console reads `data/skill_lint.json` to show Agent Skill metadata/reference health.
