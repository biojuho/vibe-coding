@echo off
setlocal
chcp 65001 >nul

for %%I in ("%~dp0.") do set "WORKDIR=%%~fI"
for %%I in ("%WORKDIR%\..\..") do set "REPO_ROOT=%%~fI"
set "UV=%REPO_ROOT%\venv\Scripts\uv.exe"
if not exist "%UV%" set "UV=%LOCALAPPDATA%\Python\pythoncore-3.14-64\Scripts\uv.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

cd /d "%WORKDIR%"
if %ERRORLEVEL% NEQ 0 (
    echo FATAL: Cannot change to work directory: %WORKDIR%
    exit /b 1
)

set LOGDIR=.tmp\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set "HR=%TIME:~0,2%"
set "HR=%HR: =0%"
set "MN=%TIME:~3,2%"
set LOGFILE=%LOGDIR%\scheduled_%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%HR%%MN%.log

echo ========================================== >> "%LOGFILE%" 2>&1
echo [%DATE% %TIME%] Starting Blind-to-X Scheduled Tasks >> "%LOGFILE%" 2>&1
echo Working Directory: %CD% >> "%LOGFILE%" 2>&1
echo UV: %UV% >> "%LOGFILE%" 2>&1
echo ========================================== >> "%LOGFILE%" 2>&1

if exist ".tmp\.running.lock" (
    forfiles /P ".tmp" /M ".running.lock" /D -0 /C "cmd /c echo Stale lock detected, removing... >> \"%LOGFILE%\" 2>&1 && del .tmp\.running.lock" 2>nul
)

set FAIL_COUNT=0

echo [%TIME%] Running Trending Scrape... >> "%LOGFILE%" 2>&1
"%UV%" run main.py --trending >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%TIME%] ERROR: Trending scrape failed with exit code %ERRORLEVEL% >> "%LOGFILE%" 2>&1
    set /a FAIL_COUNT+=1
)

echo [%TIME%] Running Popular Scrape... >> "%LOGFILE%" 2>&1
"%UV%" run main.py --popular >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%TIME%] ERROR: Popular scrape failed with exit code %ERRORLEVEL% >> "%LOGFILE%" 2>&1
    set /a FAIL_COUNT+=1
)

echo ========================================== >> "%LOGFILE%" 2>&1
echo [%DATE% %TIME%] Finished. Failures: %FAIL_COUNT% >> "%LOGFILE%" 2>&1
echo ========================================== >> "%LOGFILE%" 2>&1

if exist ".tmp\.running.lock" del ".tmp\.running.lock"

if %FAIL_COUNT% GTR 0 exit /b 1
exit /b 0
