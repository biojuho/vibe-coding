# ============================================================
# BlindToX Windows Task Scheduler 비활성화 스크립트
# n8n으로 스케줄링 전환 시 이중 실행 방지용
# 사용법: PowerShell에서 실행 (자동으로 관리자 권한 요청)
# ============================================================

# 관리자 권한 자동 상승
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$tasks = @('BlindToX_0500', 'BlindToX_0900', 'BlindToX_1300', 'BlindToX_1700', 'BlindToX_2100')

Write-Host "=== BlindToX Task Scheduler 비활성화 ===" -ForegroundColor Yellow

foreach ($taskName in $tasks) {
    try {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        if ($task.State -ne 'Disabled') {
            Disable-ScheduledTask -TaskName $taskName | Out-Null
            Write-Host "[OK] $taskName 비활성화 완료" -ForegroundColor Green
        }
        else {
            Write-Host "[--] $taskName 이미 비활성화 상태" -ForegroundColor DarkGray
        }
    }
    catch {
        Write-Host "[!!] $taskName 찾을 수 없음" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== 최종 상태 확인 ===" -ForegroundColor Yellow
foreach ($taskName in $tasks) {
    try {
        $t = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        Write-Host "  $taskName : $($t.State)"
    }
    catch {
        Write-Host "  $taskName : (미등록)"
    }
}

Write-Host ""
Write-Host "n8n이 스케줄링을 담당합니다. http://localhost:5678 에서 확인하세요." -ForegroundColor Cyan
Write-Host "다시 활성화하려면: Enable-ScheduledTask -TaskName BlindToX_XXXX" -ForegroundColor DarkGray
