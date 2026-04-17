@echo off
chcp 65001 >nul
cd /d "%~dp0"
set GOOGLE_APPLICATION_CREDENTIALS=%~dp0credentials.json
echo [INFO] Starting NotebookLM authentication...
echo [INFO] Sign in in the browser window if prompted.
venv\Scripts\python.exe -m notebooklm_mcp.auth_cli
if exist "%~dp0tokens\auth.json" (
  move /Y "%~dp0tokens\auth.json" "%~dp0tokens\auth.local.json" >nul
  echo [INFO] Cached tokens moved to tokens\auth.local.json
  echo [INFO] Keep this file local-only and out of git.
)
pause
