# blind-to-x Windows 작업 스케줄러 등록
# 실행: PowerShell **관리자 권한**으로 .\register_schedule.ps1
#
# 핵심: ASCII 경로(C:\btx\launch.py) → 환경변수로 한국어 경로 런타임 해석
# Windows Task Scheduler XML이 한국어 문자를 깨뜨리는 문제 우회

$pythonExe = "python"  # PATH에 있으므로 OK, 또는 %LOCALAPPDATA%를 통해 해석
$launcherScript = "C:\btx\launch.py"
$times = @("05:00", "09:00", "13:00", "17:00", "21:00")
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# 기존 작업 정리
$existingTasks = schtasks /query /fo CSV 2>$null | ConvertFrom-Csv | Where-Object { $_.'TaskName' -match 'BlindToX' }
foreach ($task in $existingTasks) {
    $name = $task.'TaskName' -replace '\\', ''
    schtasks /delete /tn $name /f 2>$null
}

foreach ($time in $times) {
    $taskName = "BlindToX_$($time -replace ':', '')"

    schtasks /delete /tn $taskName /f 2>$null

    # ASCII-only 경로로 등록 (한국어 인코딩 이슈 없음)
    $action = New-ScheduledTaskAction `
        -Execute "python" `
        -Argument $launcherScript

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
        -Description "blind-to-x at $time via C:\btx\launch.py" `
        -Force

    Write-Host "Registered: $taskName at $time (ASCII launcher)"
}

Write-Host "`nSchedule: 05:00, 09:00, 13:00, 17:00, 21:00"
Write-Host "Launcher: C:\btx\launch.py (ASCII path, env vars for Korean)"
Write-Host "LogonType: Interactive (로그인 시 실행)"
Write-Host "`nVerify: schtasks /query /tn BlindToX_*"
