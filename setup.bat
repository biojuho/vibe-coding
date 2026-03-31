@echo off
echo ======================================================
echo Vibe Coding Workspace Setup
echo ======================================================

echo [1/4] Checking Python installation...
py -3 --version
if errorlevel 1 (
    echo [ERROR] Python 3 launcher (py) is not available.
    pause
    exit /b 1
)

echo [2/4] Setting up virtual environment...
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

echo [3/4] Installing root dependencies...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
%PY% -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [ERROR] Root dependency installation failed.
    pause
    exit /b 1
)

echo [3.5/4] Installing shared editable project packages...
%PY% -m pip install -e .\projects\shorts-maker-v2
if errorlevel 1 (
    echo [ERROR] shorts-maker-v2 editable install failed.
    pause
    exit /b 1
)

echo [4/4] Running workspace doctor...
%PY% workspace\scripts\doctor.py

echo ======================================================
echo Setup complete.
echo Canonical commands:
echo 1. call venv\Scripts\activate
echo 2. %PY% workspace\scripts\smoke_check.py
echo 3. %PY% -m streamlit run workspace\execution\pages\shorts_manager.py
echo ======================================================
pause
