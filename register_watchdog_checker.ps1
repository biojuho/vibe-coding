# register_watchdog_checker.ps1
# P1-2: Watchdog Heartbeat Checker Task Scheduler Registration
# Runs every 10 minutes to check heartbeat freshness
# Run as Administrator

$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$PYTHON = (Get-Command python -ErrorAction Stop).Source
$TASK_NAME_CHECKER = "VibeCoding_WatchdogHeartbeatChecker"
$TASK_NAME_WATCHDOG = "VibeCoding_PipelineWatchdog"

Write-Host "[P1-2] Watchdog Heartbeat Checker Registration" -ForegroundColor Cyan
Write-Host ""

# 1. Check if main watchdog task exists
Write-Host "[1/3] Checking main watchdog task..." -ForegroundColor Yellow
try {
    $mainTask = Get-ScheduledTask -TaskName $TASK_NAME_WATCHDOG -ErrorAction Stop
    Write-Host "  OK Main watchdog task found: $($mainTask.TaskName)" -ForegroundColor Green
} catch {
    Write-Host "  WARN No main watchdog task -- registering checker only" -ForegroundColor Yellow
}

# 2. Register Heartbeat Checker via Register-ScheduledTask (handles spaces correctly)
Write-Host "[2/3] Registering Heartbeat Checker task..." -ForegroundColor Yellow

try {
    Unregister-ScheduledTask -TaskName $TASK_NAME_CHECKER -Confirm:$false -ErrorAction SilentlyContinue

    $ScriptArg = "`"$ROOT\execution\pipeline_watchdog.py`" --check-alive"

    $Action = New-ScheduledTaskAction `
        -Execute $PYTHON `
        -Argument $ScriptArg `
        -WorkingDirectory $ROOT

    # Repeating trigger: every 10 minutes, starting now, indefinitely
    $Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 10) -Once -At (Get-Date)

    $Settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 3) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable

    Register-ScheduledTask `
        -TaskName $TASK_NAME_CHECKER `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Watchdog heartbeat check every 10 minutes." `
        -RunLevel Highest `
        | Out-Null

    Write-Host "  OK Heartbeat Checker registered" -ForegroundColor Green
    Write-Host "     Task: $TASK_NAME_CHECKER" -ForegroundColor Gray
    Write-Host "     Schedule: every 10 minutes" -ForegroundColor Gray
} catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
    Write-Host "     Please run as Administrator" -ForegroundColor Yellow
}

# 3. Verify registration
Write-Host "[3/3] Verifying registration..." -ForegroundColor Yellow
try {
    $task = Get-ScheduledTask -TaskName $TASK_NAME_CHECKER -ErrorAction Stop
    Write-Host "  OK Task state: $($task.State)" -ForegroundColor Green
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TASK_NAME_CHECKER -ErrorAction SilentlyContinue
    if ($taskInfo) {
        Write-Host "  OK Next run: $($taskInfo.NextRunTime)" -ForegroundColor Green
    }
} catch {
    Write-Host "  WARN Could not verify (task may still be registered)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
Write-Host "  Manual test: python execution\pipeline_watchdog.py --check-alive" -ForegroundColor Gray
