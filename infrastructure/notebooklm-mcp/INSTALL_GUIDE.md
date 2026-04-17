# NotebookLM MCP Install Guide

## Copy To Another Machine

Copy the `notebooklm-mcp` folder without the virtual environment.

Required files:
- `credentials.json`
- `install.bat`
- `requirements.txt`
- `authenticate_notebooklm.bat`
- `run_notebooklm.bat`

## Setup

### 1. Install dependencies

```batch
cd notebooklm-mcp
install.bat
```

### 2. Authenticate

```batch
authenticate_notebooklm.bat
```

When the browser opens, sign in with the Google account that can access NotebookLM.

### 3. Keep tokens local-only

- The checked-in `tokens/auth.json` file is a template.
- Real cached tokens should live in `tokens/auth.local.json`.
- You can also point tools at a custom file with `NOTEBOOKLM_AUTH_TOKEN_PATH`.

### 4. Configure MCP

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "python",
      "args": ["-m", "notebooklm_mcp"],
      "cwd": "C:/path/to/notebooklm-mcp",
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "C:/path/to/notebooklm-mcp/credentials.json"
      }
    }
  }
}
```

### 5. Run

```batch
run_notebooklm.bat
```

## Requirements

- Python 3.10+
- Google Cloud project credentials in `credentials.json`
