@echo off
REM YouTube Analytics → Notion 자동 수집 스케줄러 등록
REM 매일 오전 9시 실행
REM 관리자 권한으로 실행하세요

SET TASK_NAME=YT_Analytics_To_Notion
SET WORKSPACE_DIR=C:\Users\박주호\Desktop\Vibe coding\workspace
SET SCRIPT_PATH=execution\yt_analytics_to_notion.py
SET UV_PATH=C:\Users\박주호\Desktop\Vibe coding\venv\Scripts\uv.exe
SET LOG_PATH=C:\Users\박주호\Desktop\Vibe coding\logs\yt_analytics.log

echo [%TIME%] YouTube Analytics 스케줄러 등록 시작...

schtasks /create /tn "%TASK_NAME%" ^
    /tr "cmd.exe /c \"cd /d \"%WORKSPACE_DIR%\" && \"%UV_PATH%\" run \"%SCRIPT_PATH%\" >> \"%LOG_PATH%\" 2>&1\"" ^
    /sc DAILY ^
    /st 09:00 ^
    /ru "%USERNAME%" ^
    /f

IF %ERRORLEVEL% EQU 0 (
    echo ✅ 스케줄러 등록 완료!
    echo    태스크명: %TASK_NAME%
    echo    실행시간: 매일 오전 09:00
    echo    로그파일: %LOG_PATH%
    echo.
    echo 확인하려면: schtasks /query /tn "%TASK_NAME%"
    echo 수동실행: schtasks /run /tn "%TASK_NAME%"
    echo 삭제하려면: schtasks /delete /tn "%TASK_NAME%" /f
) ELSE (
    echo ❌ 등록 실패. 관리자 권한으로 다시 실행하세요.
)

pause
