@echo off
echo ======================================================
echo Vibe Coding: Personal Agent Setup Wizard
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

echo [3/4] Installing dependencies...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r projects\personal-agent\requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo [3.5/4] Running import smoke test...
%PY% -c "import importlib.util,sys;mods=['streamlit','croniter','gtts','ddgs'];missing=[m for m in mods if importlib.util.find_spec(m) is None];has_google=(importlib.util.find_spec('google.generativeai') is not None or importlib.util.find_spec('google.genai') is not None);print('Smoke test passed.' if (not missing and has_google) else f'Smoke test failed. Missing={missing}, google_genai={has_google}');sys.exit(0 if (not missing and has_google) else 1)"
if errorlevel 1 (
    echo [ERROR] Smoke test failed.
    echo Run: %PY% -m pip install streamlit croniter gTTS ddgs google-generativeai
    pause
    exit /b 1
)

echo [4/4] Checking configuration...
if not exist "projects\personal-agent\.env" (
    echo [WARN] .env file not found.
    echo Creating template...
    echo GOOGLE_API_KEY=YOUR_KEY_HERE > projects\personal-agent\.env
    echo Please edit projects\personal-agent\.env with your API key.
) else (
    echo .env file exists.
)

echo ======================================================
echo Setup complete.
echo To run the agent:
echo 1. call venv\Scripts\activate
echo 2. %PY% -m streamlit run projects/personal-agent/app.py
echo ======================================================
pause
