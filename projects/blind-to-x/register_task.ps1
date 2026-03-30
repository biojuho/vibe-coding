Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\scheduler_launchers.ps1"

$layout = Get-SchedulerLayout -ScriptRoot $PSScriptRoot
Ensure-BtxAsciiLaunchers -Layout $layout

$asciiRunBat = Join-Path $layout.AsciiRoot "run_pipeline.bat"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

if (Get-ScheduledTask -TaskName "BlindToX_Pipeline" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName "BlindToX_Pipeline" -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$asciiRunBat`"" `
    -WorkingDirectory $layout.AsciiRoot
$trigger = New-ScheduledTaskTrigger -Once -At "06:00" -RepetitionInterval (New-TimeSpan -Hours 3) -RepetitionDuration (New-TimeSpan -Days 365)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Highest

Register-ScheduledTask `
    -TaskName "BlindToX_Pipeline" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Blind-to-X pipeline (3h interval) via C:\btx\run_pipeline.bat" `
    -Force | Out-Null

Write-Host "Registered: BlindToX_Pipeline via C:\btx\run_pipeline.bat"
