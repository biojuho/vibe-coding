@echo off
echo ======================================================
echo Vibe Coding Workspace Setup (uv based)
echo ======================================================

echo [1/4] Checking Python installation...
py -3 --version
if errorlevel 1 (
    echo [ERROR] Python 3 launcher (py) is not available.
    pause
    exit /b 1
)

echo [2/4] Setting up root venv for uv runner...
if not exist "venv" (
    echo Creating venv...
    py -3 -m venv venv
) else (
    echo venv already exists.
)

set "PY=venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] venv python not found: %PY%
    pause
    exit /b 1
)

echo [3/4] Installing uv and syncing sub-projects...
%PY% -m pip install --upgrade pip uv
if errorlevel 1 (
    echo [ERROR] uv installation failed.
    pause
    exit /b 1
)

set "UV=venv\Scripts\uv.exe"

echo Syncing workspace...
cd workspace
..\uv sync
if errorlevel 1 exit /b 1
cd ..

echo Syncing projects/blind-to-x...
cd projects\blind-to-x
..\..\uv sync
if errorlevel 1 exit /b 1
cd ..\..

echo Syncing projects/shorts-maker-v2...
cd projects\shorts-maker-v2
..\..\uv sync
if errorlevel 1 exit /b 1
cd ..\..

echo [4/4] Running workspace doctor...
cd workspace
..\uv run scripts\doctor.py
cd ..

echo ======================================================
echo Setup complete.
echo Canonical commands:
echo 1. cd workspace ^&^& ..\venv\Scripts\uv.exe run scripts\doctor.py
echo 2. cd projects\blind-to-x ^&^& ..\..\venv\Scripts\uv.exe run main.py
echo ======================================================
pause
