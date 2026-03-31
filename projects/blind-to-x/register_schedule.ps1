Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\scheduler_launchers.ps1"

$layout = Get-SchedulerLayout -ScriptRoot $PSScriptRoot
Ensure-BtxAsciiLaunchers -Layout $layout

$asciiRunBat = Join-Path $layout.AsciiRoot "run.bat"
$times = @("05:00", "09:00", "13:00", "17:00", "21:00")
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$existingTasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
    $_.TaskName -match "^BlindToX_\d{4}$"
}
foreach ($task in $existingTasks) {
    Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false
}

foreach ($time in $times) {
    $taskName = "BlindToX_$($time -replace ':', '')"

    $action = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$asciiRunBat`"" `
        -WorkingDirectory $layout.AsciiRoot

    $trigger = New-ScheduledTaskTrigger -Daily -At $time
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2)

    $principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Highest

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "blind-to-x at $time via C:\btx\run.bat" `
        -Force | Out-Null

    Write-Host "Registered: $taskName at $time (ASCII launcher)"
}

Write-Host ""
Write-Host "Schedule: 05:00, 09:00, 13:00, 17:00, 21:00"
Write-Host "Launcher: C:\btx\run.bat"
Write-Host "Project Root: $($layout.ProjectRoot)"
Write-Host ""
Write-Host "Verify: Get-ScheduledTask -TaskName 'BlindToX_*'"
