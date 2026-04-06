@echo off
REM =============================================
REM  n8n Bridge Server + Docker 시작 스크립트
REM =============================================
REM  사용법: start_n8n.bat
REM  1) 브릿지 서버 (호스트 Python) 시작
REM  2) n8n Docker 컨테이너 시작
REM =============================================

chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ========================================
echo   n8n 워크플로우 자동화 시스템 시작
echo ========================================
echo.

REM --- Step 1: 브릿지 서버 시작 (백그라운드) ---
echo [1/2] 브릿지 서버 시작 중...

set "VENV_UV=C:\Users\박주호\Desktop\Vibe coding\venv\Scripts\uv.exe"
set "WORKSPACE_DIR=C:\Users\박주호\Desktop\Vibe coding\workspace"

REM 브릿지 서버를 새 창에서 실행
start "n8n-bridge" cmd.exe /c "cd /d "%WORKSPACE_DIR%" && "%VENV_UV%" run "%~dp0bridge_server.py""
echo   → 브릿지 서버: http://127.0.0.1:9876
echo.

REM --- Step 2: n8n Docker 컨테이너 시작 ---
echo [2/2] n8n Docker 컨테이너 시작 중...
docker compose up -d
echo   → n8n UI: http://localhost:5678
echo.

echo ========================================
echo   시스템 시작 완료!
echo   - n8n UI:     http://localhost:5678
echo   - Bridge API: http://127.0.0.1:9876
echo ========================================
echo.
pause
