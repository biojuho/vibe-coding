Set-StrictMode -Version Latest

function Get-SchedulerLayout {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptRoot
    )

    $projectRoot = (Resolve-Path $ScriptRoot).Path
    $repoRoot = (Resolve-Path (Join-Path $projectRoot "..\..")).Path
    $workspaceRoot = Join-Path $repoRoot "workspace"

    return @{
        ProjectRoot = $projectRoot
        RepoRoot = $repoRoot
        WorkspaceRoot = $workspaceRoot
        AsciiRoot = "C:\btx"
    }
}

function Write-Utf8NoBomFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content.TrimStart("`r", "`n"), $encoding)
}

function Ensure-BtxAsciiLaunchers {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Layout
    )

    $asciiRoot = $Layout.AsciiRoot
    $projectRoot = $Layout.ProjectRoot -replace "\\", "/"

    New-Item -ItemType Directory -Path $asciiRoot -Force | Out-Null

    Write-Utf8NoBomFile -Path (Join-Path $asciiRoot "run.bat") -Content @"
@echo off
setlocal
set "PYTHON=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" "C:\btx\launch.py"
exit /b %ERRORLEVEL%
"@

    Write-Utf8NoBomFile -Path (Join-Path $asciiRoot "run_pipeline.bat") -Content @"
@echo off
setlocal
set "PYTHON=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" "C:\btx\launch_pipeline.py"
exit /b %ERRORLEVEL%
"@

    Write-Utf8NoBomFile -Path (Join-Path $asciiRoot "launch.py") -Content @"
from __future__ import annotations

import os
import subprocess
import sys

PROJECT_ROOT = r"$projectRoot"
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "run_scheduled.py")
PYTHON = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Python", "pythoncore-3.14-64", "python.exe")

if not os.path.exists(PYTHON):
    PYTHON = sys.executable

if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    result = subprocess.run([PYTHON, SCRIPT_PATH], cwd=PROJECT_ROOT)
    sys.exit(result.returncode)
"@

    Write-Utf8NoBomFile -Path (Join-Path $asciiRoot "launch_pipeline.py") -Content @"
from __future__ import annotations

import os
import subprocess
import sys

PROJECT_ROOT = r"$projectRoot"
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "run_pipeline.bat")

if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    result = subprocess.run(["cmd.exe", "/c", SCRIPT_PATH], cwd=PROJECT_ROOT)
    sys.exit(result.returncode)
"@
}
