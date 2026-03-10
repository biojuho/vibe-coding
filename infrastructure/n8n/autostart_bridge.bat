@echo off
REM n8n Bridge Server 자동 시작 (Windows 시작 시 실행)
REM 이 파일은 시작프로그램 폴더에 바로가기로 등록됩니다.
chcp 65001 >nul 2>&1

REM Docker가 준비될 때까지 대기 (최대 120초)
set DOCKER_EXE="C:\Program Files\Docker\Docker\resources\bin\docker.exe"
set /a waited=0
:wait_docker
%DOCKER_EXE% info >nul 2>&1
if %ERRORLEVEL%==0 goto docker_ready
if %waited% GEQ 120 goto docker_timeout
timeout /t 5 /nobreak >nul
set /a waited+=5
goto wait_docker

:docker_ready
REM 브릿지 서버 시작 (숨김 창)
start /min "" "C:\Users\박주호\Desktop\Vibe coding\venv\Scripts\pythonw.exe" "C:\Users\박주호\Desktop\Vibe coding\infrastructure\n8n\bridge_server.py"
exit /b 0

:docker_timeout
echo Docker not ready after 120s
exit /b 1
