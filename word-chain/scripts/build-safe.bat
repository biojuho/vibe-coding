@echo off
REM ============================================
REM  Word Chain - Windows Safe Build Script
REM  한글 경로에서 Vite 빌드 실패 시 워크어라운드
REM ============================================

SET SAFE_DIR=C:\temp\word-chain-build
SET SOURCE_DIR=%~dp0

echo [1/4] Creating temporary build directory...
if exist "%SAFE_DIR%" rmdir /S /Q "%SAFE_DIR%"
mkdir "%SAFE_DIR%"

echo [2/4] Copying source files (excluding node_modules, dist)...
robocopy "%SOURCE_DIR%" "%SAFE_DIR%" /E /XD node_modules dist .git /NFL /NDL /NP

echo [3/4] Installing dependencies and building...
pushd "%SAFE_DIR%"
call npm install
call npm run build
popd

echo [4/4] Copying dist back to source directory...
if exist "%SOURCE_DIR%dist" rmdir /S /Q "%SOURCE_DIR%dist"
xcopy "%SAFE_DIR%\dist" "%SOURCE_DIR%dist\" /E /I /Q

echo.
echo ✅ Build complete! Output: %SOURCE_DIR%dist
echo    (temp directory preserved at %SAFE_DIR% for debugging)
