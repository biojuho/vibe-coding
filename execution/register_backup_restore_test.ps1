# register_backup_restore_test.ps1
# P1-3: OneDrive Backup Restore Test - Monthly Task Scheduler Registration
# Run as Administrator

$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$PYTHON = (Get-Command python -ErrorAction Stop).Source
$TASK_NAME = "VibeCoding_BackupRestoreTest"

Write-Host "[P1-3] Backup Restore Test Monthly Registration" -ForegroundColor Cyan
Write-Host ""

# 1. Check script exists
$ScriptPath = Join-Path $ROOT "execution\backup_restore_test.py"
Write-Host "[1/3] Checking script..." -ForegroundColor Yellow
if (Test-Path $ScriptPath) {
    Write-Host "  OK backup_restore_test.py found" -ForegroundColor Green
} else {
    Write-Host "  WARN backup_restore_test.py not found at: $ScriptPath" -ForegroundColor Yellow
    Write-Host "  Registering task anyway (script will be created later)" -ForegroundColor Gray
}

# 2. Register via schtasks.exe (monthly trigger, 1st at 09:00)
# New-ScheduledTaskTrigger -Monthly not supported on all PS versions -> use schtasks.exe
Write-Host "[2/3] Registering Task Scheduler (monthly, 1st at 09:00)..." -ForegroundColor Yellow

try {
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue

    # Use C:\ProgramData\VibeCoding as wrapper dir (pure ASCII, no Korean chars)
    $WrapperDir = "C:\ProgramData\VibeCoding"
    New-Item -ItemType Directory -Path $WrapperDir -Force | Out-Null

    $WrapperBat = Join-Path $WrapperDir "backup_restore_test.bat"
    @"
@echo off
cd /d "$ROOT"
"$PYTHON" "$ROOT\execution\backup_restore_test.py" %*
"@ | Out-File -FilePath $WrapperBat -Encoding ASCII

    Write-Host "     Wrapper: $WrapperBat" -ForegroundColor Gray

    # Register-ScheduledTask handles Unicode paths on the Task side
    $Action = New-ScheduledTaskAction -Execute $WrapperBat -WorkingDirectory $WrapperDir

    # Trigger: every 31 days starting 2026-04-01 09:00 (closest to monthly without -Monthly param)
    $Trigger = New-ScheduledTaskTrigger -Daily -DaysInterval 31 -At "2026-04-01 09:00"

    $Settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable

    Register-ScheduledTask `
        -TaskName $TASK_NAME `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Monthly OneDrive backup SQLite integrity check + Telegram alert" `
        -RunLevel Highest `
        | Out-Null

    Write-Host "  OK BackupRestoreTest registered" -ForegroundColor Green
    Write-Host "     Task: $TASK_NAME" -ForegroundColor Gray
    Write-Host "     Schedule: ~Monthly (every 31 days from 2026-04-01 09:00)" -ForegroundColor Gray
} catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
    Write-Host "     Please run as Administrator" -ForegroundColor Yellow
}

# 3. Verify
Write-Host "[3/3] Verifying registration..." -ForegroundColor Yellow
try {
    $task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction Stop
    Write-Host "  OK Task state: $($task.State)" -ForegroundColor Green
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TASK_NAME -ErrorAction SilentlyContinue
    if ($taskInfo) {
        Write-Host "  OK Next run: $($taskInfo.NextRunTime)" -ForegroundColor Green
    }
} catch {
    Write-Host "  WARN Could not verify (task may still be registered)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
Write-Host "  Manual test: python execution\backup_restore_test.py --dry-run" -ForegroundColor Gray
