@echo off
REM Watchdog heartbeat freshness checker
REM Task Scheduler에서 10분마다 실행
REM 워치독이 30분 이상 미응답이면 Telegram 알림 + 자동 재시작 시도

cd /d "C:\Users\박주호\Desktop\Vibe coding"
call venv\Scripts\activate.bat

REM heartbeat 확인 (Telegram 알림 포함)
python execution\pipeline_watchdog.py --check-alive

REM exit code 1이면 워치독 사망 → 재시작 시도
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] Watchdog dead, attempting restart...
    start /B python execution\pipeline_watchdog.py
    echo [%date% %time%] Watchdog restarted.
)
