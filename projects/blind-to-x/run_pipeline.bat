@echo off
setlocal

for %%I in ("%~dp0.") do set "WORKDIR=%%~fI"
for %%I in ("%WORKDIR%\..\..") do set "REPO_ROOT=%%~fI"
set "UV=%REPO_ROOT%\venv\Scripts\uv.exe"
if not exist "%UV%" set "UV=%LOCALAPPDATA%\Python\pythoncore-3.14-64\Scripts\uv.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

cd /d "%WORKDIR%"
if %ERRORLEVEL% NEQ 0 exit /b 1

"%UV%" run main.py --trending
exit /b %ERRORLEVEL%
