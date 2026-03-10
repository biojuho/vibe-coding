@echo off
chcp 65001 >nul

REM === 절대 경로 하드코딩 (한국어 경로 %~dp0 이슈 방지) ===
set "WORKDIR=C:\Users\박주호\Desktop\Vibe coding\blind-to-x"
set "PYTHON=C:\Users\박주호\AppData\Local\Python\pythoncore-3.14-64\python.exe"

cd /d "%WORKDIR%"
if %ERRORLEVEL% NEQ 0 (
    echo FATAL: Cannot change to work directory: %WORKDIR%
    exit /b 1
)

set LOGDIR=.tmp\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM 시간 문자열에서 공백 제거 (오전 시간대 앞 공백 이슈)
set "HR=%TIME:~0,2%"
set "HR=%HR: =0%"
set "MN=%TIME:~3,2%"
set LOGFILE=%LOGDIR%\scheduled_%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%HR%%MN%.log

echo ========================================== >> "%LOGFILE%" 2>&1
echo [%DATE% %TIME%] Starting Blind-to-X Scheduled Tasks >> "%LOGFILE%" 2>&1
echo Working Directory: %CD% >> "%LOGFILE%" 2>&1
echo Python: %PYTHON% >> "%LOGFILE%" 2>&1
echo ========================================== >> "%LOGFILE%" 2>&1

REM Lock 파일이 1시간 이상 된 경우 강제 삭제
if exist ".tmp\.running.lock" (
    forfiles /P ".tmp" /M ".running.lock" /D -0 /C "cmd /c echo Stale lock detected, removing... >> \"%LOGFILE%\" 2>&1 && del .tmp\.running.lock" 2>nul
)

set FAIL_COUNT=0

echo [%TIME%] Running Trending Scrape... >> "%LOGFILE%" 2>&1
"%PYTHON%" main.py --trending >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%TIME%] ERROR: Trending scrape failed with exit code %ERRORLEVEL% >> "%LOGFILE%" 2>&1
    set /a FAIL_COUNT+=1
)

echo [%TIME%] Running Popular Scrape... >> "%LOGFILE%" 2>&1
"%PYTHON%" main.py --popular >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%TIME%] ERROR: Popular scrape failed with exit code %ERRORLEVEL% >> "%LOGFILE%" 2>&1
    set /a FAIL_COUNT+=1
)

echo [%TIME%] Running Newsletter Build... >> "%LOGFILE%" 2>&1
"%PYTHON%" main.py --newsletter-build >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%TIME%] ERROR: Newsletter build failed with exit code %ERRORLEVEL% >> "%LOGFILE%" 2>&1
    set /a FAIL_COUNT+=1
)

echo ========================================== >> "%LOGFILE%" 2>&1
echo [%DATE% %TIME%] Finished. Failures: %FAIL_COUNT% >> "%LOGFILE%" 2>&1
echo ========================================== >> "%LOGFILE%" 2>&1

REM Lock 파일이 남아있으면 정리
if exist ".tmp\.running.lock" del ".tmp\.running.lock"

if %FAIL_COUNT% GTR 0 exit /b 1
exit /b 0
