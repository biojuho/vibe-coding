@echo off
REM n8n 시스템 종료 스크립트
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo n8n 시스템 종료 중...

REM Docker 컨테이너 종료
docker compose down
echo   → n8n 컨테이너 종료 완료

REM 브릿지 서버 종료
taskkill /FI "WINDOWTITLE eq n8n-bridge*" /F >nul 2>&1
echo   → 브릿지 서버 종료 완료

echo.
echo 종료 완료!
pause
