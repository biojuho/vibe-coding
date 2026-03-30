@echo off
setlocal

for %%I in ("%~dp0.") do set "WORKDIR=%%~fI"
for %%I in ("%WORKDIR%\..\..") do set "REPO_ROOT=%%~fI"
set "PYTHON=%REPO_ROOT%\venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

cd /d "%WORKDIR%"
if %ERRORLEVEL% NEQ 0 exit /b 1

"%PYTHON%" "%WORKDIR%\main.py" --trending
exit /b %ERRORLEVEL%
