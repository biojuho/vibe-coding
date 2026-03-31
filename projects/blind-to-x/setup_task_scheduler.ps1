Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scheduleScript = Join-Path $PSScriptRoot "register_schedule.ps1"
$pipelineScript = Join-Path $PSScriptRoot "register_task.ps1"

Write-Host "Registering BlindToX time-slot tasks..."
& $scheduleScript

Write-Host ""
Write-Host "Registering BlindToX pipeline task..."
& $pipelineScript

Write-Host ""
Write-Host "All BlindToX scheduler tasks have been refreshed."
