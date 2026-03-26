<#
.SYNOPSIS
  MCP 서버 Tier 3 on-demand 토글 스크립트
.DESCRIPTION
  Tier 3 MCP 서버(youtube-mcp, cloudinary-mcp, n8n-mcp, notebooklm-mcp)를
  활성화/비활성화/상태 확인합니다.
.PARAMETER Action
  Enable, Disable, Status 중 택 1
.EXAMPLE
  .\mcp_toggle.ps1 -Action Status
  .\mcp_toggle.ps1 -Action Disable
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Enable","Disable","Status")]
    [string]$Action
)

$Tier3Servers = @(
    @{ Name = "youtube-mcp";     Pattern = "youtube[-_]mcp" }
    @{ Name = "cloudinary-mcp";  Pattern = "cloudinary[-_]mcp" }
    @{ Name = "n8n-mcp";         Pattern = "n8n[-_]mcp" }
    @{ Name = "notebooklm-mcp"; Pattern = "notebooklm[-_]mcp" }
)

function Get-McpProcesses {
    param([string]$Pattern)
    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -match $Pattern -or $_.ProcessName -match $Pattern
    }
}

function Show-Status {
    Write-Host "`n=== MCP Tier 3 Server Status ===" -ForegroundColor Cyan
    foreach ($srv in $Tier3Servers) {
        $procs = Get-McpProcesses -Pattern $srv.Pattern
        if ($procs) {
            $mem = ($procs | Measure-Object WorkingSet64 -Sum).Sum / 1MB
            Write-Host "  [ON]  $($srv.Name) — $($procs.Count) process(es), $([math]::Round($mem,1)) MB" -ForegroundColor Green
        } else {
            Write-Host "  [OFF] $($srv.Name)" -ForegroundColor DarkGray
        }
    }
    Write-Host ""
}

function Invoke-Disable {
    Write-Host "`n=== Disabling Tier 3 MCP Servers ===" -ForegroundColor Yellow
    $totalFreed = 0
    foreach ($srv in $Tier3Servers) {
        $procs = Get-McpProcesses -Pattern $srv.Pattern
        if ($procs) {
            $mem = ($procs | Measure-Object WorkingSet64 -Sum).Sum / 1MB
            $totalFreed += $mem
            $procs | Stop-Process -Force -ErrorAction SilentlyContinue
            Write-Host "  [STOPPED] $($srv.Name) — freed ~$([math]::Round($mem,1)) MB" -ForegroundColor Red
        } else {
            Write-Host "  [SKIP]    $($srv.Name) — not running" -ForegroundColor DarkGray
        }
    }
    Write-Host "`n  Total freed: ~$([math]::Round($totalFreed,1)) MB" -ForegroundColor Cyan
}

function Invoke-Enable {
    Write-Host "`n=== Enable Tier 3 MCP Servers ===" -ForegroundColor Green
    Write-Host "  Tier 3 서버는 AI 도구(Claude Code, Cursor 등)가 자동 시작합니다." -ForegroundColor White
    Write-Host "  해당 AI 도구를 재시작하면 MCP 서버가 자동으로 다시 연결됩니다." -ForegroundColor White
    Write-Host ""
    Write-Host "  또는 수동 시작:" -ForegroundColor Yellow
    Write-Host "    npx youtube-mcp" -ForegroundColor Gray
    Write-Host "    npx cloudinary-mcp" -ForegroundColor Gray
    Write-Host "    python -m n8n_mcp" -ForegroundColor Gray
    Write-Host "    python -m notebooklm_mcp" -ForegroundColor Gray
}

switch ($Action) {
    "Status"  { Show-Status }
    "Disable" { Invoke-Disable; Show-Status }
    "Enable"  { Invoke-Enable; Show-Status }
}
