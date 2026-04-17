# n8n Workflow Automation

## Architecture

```text
n8n (Docker:5678) -> HTTP -> Bridge Server (Host:9876) -> subprocess -> Python pipelines
```

- `n8n`: Docker container that runs the workflow UI and scheduler.
- `Bridge Server`: local FastAPI bridge that exposes a small allowlist of commands.
- `Pipelines`: existing Blind-to-X and Shorts Maker Python entrypoints.

## Quick Start

```bash
# 1. Install bridge dependencies (first time only)
pip install fastapi uvicorn

# 2. Export local credentials before startup
# BRIDGE_TOKEN=<your-bridge-token>
# N8N_BASIC_AUTH_PASSWORD=<strong-local-password>

# 3. Start the system
start_n8n.bat

# 4. Open n8n UI
# http://localhost:5678
# Username: ${N8N_BASIC_AUTH_USER:-admin}
# Password: your local N8N_BASIC_AUTH_PASSWORD value

# 5. Import workflows from infrastructure/n8n/workflows/
```

## Stop

```bash
stop_n8n.bat
```

## File Layout

```text
infrastructure/n8n/
├── docker-compose.yml
├── bridge_server.py
├── healthcheck.py
├── start_n8n.bat
├── stop_n8n.bat
├── logs/
└── workflows/
```

## Security Notes

- Bridge requests are authenticated with the `BRIDGE_TOKEN` environment variable.
- n8n basic auth reads `N8N_BASIC_AUTH_USER` and `N8N_BASIC_AUTH_PASSWORD`.
- The checked-in compose file only contains placeholders and safe defaults.
- Keep live credentials in your local shell or local `.env`, not in this README.

## First-Time n8n Setup

1. Start the stack and create your n8n account if prompted.
2. In `Settings -> Credentials`, add `Header Auth`.
3. Use `Authorization` as the header name.
4. Use `Bearer <your BRIDGE_TOKEN>` as the header value.
5. Import the JSON workflows from `infrastructure/n8n/workflows/`.
