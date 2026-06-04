@echo off
setlocal
echo Starting knowledge-dashboard data sync...

rem Resolve the project root from this script's location so the path is not
rem machine-specific. Prefer the workspace NotebookLM venv if present, else the
rem system python. No "pause" so this can run unattended in cron / n8n / CI.
set "VENV_PY=%~dp0..\..\infrastructure\notebooklm-mcp\venv\Scripts\python.exe"

if exist "%VENV_PY%" (
	"%VENV_PY%" "%~dp0scripts\sync_data.py"
) else (
	python "%~dp0scripts\sync_data.py"
)

endlocal
