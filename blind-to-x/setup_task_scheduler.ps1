# Windows 작업 스케줄러 등록 스크립트

$TaskName = "Blind-to-X-Scheduler"
$Description = "Runs Blind-to-X full pipeline including trending, popular, and newsletter building."
$ScriptDir = $PSScriptRoot
$ActionPayload = "$ScriptDir\run_scheduled.bat"

# 작업 실행 방식 지정
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ActionPayload`""

# 트리거 설정: 매일 오전 9시에 실행
$trigger = New-ScheduledTaskTrigger -Daily -At 9am

# 기존에 동일한 이름의 태스크가 있다면 삭제
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Unregistered existing task '$TaskName'."
}

# 작업 스케줄러 등록
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName $TaskName -Description $Description

Write-Host ""
Write-Host "Success! Scheduled task '$TaskName' has been registered."
Write-Host "It will execute '$ActionPayload' daily at 9:00 AM."
Write-Host ""
Write-Host "To change the schedule or view details, open 'Task Scheduler' (taskschd.msc) on Windows."
