<#
.SYNOPSIS
  MCP Tier 3 on-demand toggle and AI client footprint guard.
.DESCRIPTION
  Shows Tier 3 MCP server status, disables running Tier 3 servers to reclaim
  memory, and warns when multiple AI tool clients are active at the same time.
.PARAMETER Action
  Enable, Disable, Status, or Guard.
.EXAMPLE
  .\mcp_toggle.ps1 -Action Status
  .\mcp_toggle.ps1 -Action Disable
  .\mcp_toggle.ps1 -Action Guard
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Enable", "Disable", "Status", "Guard")]
    [string]$Action
)

$Tier3Servers = @(
    @{ Name = "youtube-mcp"; Pattern = "youtube[-_]mcp" }
    @{ Name = "cloudinary-mcp"; Pattern = "cloudinary[-_]mcp" }
    @{ Name = "n8n-mcp"; Pattern = "n8n[-_]mcp" }
    @{ Name = "notebooklm-mcp"; Pattern = "notebooklm[-_]mcp" }
)

$AiToolClients = @(
    @{ Name = "Claude"; Patterns = @("^claude$", "claude") }
    @{ Name = "Cursor"; Patterns = @("^cursor$", "cursor") }
    @{ Name = "VS Code"; Patterns = @("^code$", "code") }
)

function Get-ProcessMatches {
    param([string[]]$Patterns)

    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $name = $_.ProcessName
        $commandLine = $_.CommandLine
        $matched = $false
        foreach ($pattern in $Patterns) {
            if ($name -match $pattern -or $commandLine -match $pattern) {
                $matched = $true
                break
            }
        }
        $matched
    }
}

function Show-AiToolStatus {
    Write-Host "`n=== AI Tool Client Status ===" -ForegroundColor Cyan
    $activeTools = @()

    foreach ($tool in $AiToolClients) {
        $procs = @(Get-ProcessMatches -Patterns $tool.Patterns)
        if ($procs.Count -gt 0) {
            $mem = ($procs | Measure-Object WorkingSet64 -Sum).Sum / 1MB
            $activeTools += $tool.Name
            Write-Host "  [ON]  $($tool.Name) - $($procs.Count) process(es), $([math]::Round($mem, 1)) MB" -ForegroundColor Green
        }
        else {
            Write-Host "  [OFF] $($tool.Name)" -ForegroundColor DarkGray
        }
    }

    Write-Host ""
    if ($activeTools.Count -gt 1) {
        Write-Host "  [WARN] Multiple AI tool clients are active: $($activeTools -join ', ')" -ForegroundColor Yellow
        Write-Host "         Close extra AI tool windows to reclaim MCP memory before deep sessions." -ForegroundColor Yellow
        return $false
    }

    if ($activeTools.Count -eq 1) {
        Write-Host "  [OK] Single AI tool client footprint detected." -ForegroundColor Green
    }
    else {
        Write-Host "  [OK] No overlapping AI tool clients detected." -ForegroundColor Green
    }

    return $true
}

function Show-Tier3Status {
    Write-Host "`n=== MCP Tier 3 Server Status ===" -ForegroundColor Cyan
    foreach ($srv in $Tier3Servers) {
        $procs = @(Get-ProcessMatches -Patterns @($srv.Pattern))
        if ($procs.Count -gt 0) {
            $mem = ($procs | Measure-Object WorkingSet64 -Sum).Sum / 1MB
            Write-Host "  [ON]  $($srv.Name) - $($procs.Count) process(es), $([math]::Round($mem, 1)) MB" -ForegroundColor Green
        }
        else {
            Write-Host "  [OFF] $($srv.Name)" -ForegroundColor DarkGray
        }
    }
    Write-Host ""
}

function Invoke-Disable {
    Write-Host "`n=== Disabling Tier 3 MCP Servers ===" -ForegroundColor Yellow
    $totalFreed = 0
    foreach ($srv in $Tier3Servers) {
        $procs = @(Get-ProcessMatches -Patterns @($srv.Pattern))
        if ($procs.Count -gt 0) {
            $mem = ($procs | Measure-Object WorkingSet64 -Sum).Sum / 1MB
            $totalFreed += $mem
            $procs | Stop-Process -Force -ErrorAction SilentlyContinue
            Write-Host "  [STOPPED] $($srv.Name) - freed ~$([math]::Round($mem, 1)) MB" -ForegroundColor Red
        }
        else {
            Write-Host "  [SKIP]    $($srv.Name) - not running" -ForegroundColor DarkGray
        }
    }
    Write-Host "`n  Total freed: ~$([math]::Round($totalFreed, 1)) MB" -ForegroundColor Cyan
}

function Invoke-Enable {
    Write-Host "`n=== Enable Tier 3 MCP Servers ===" -ForegroundColor Green
    Write-Host "  Tier 3 servers start automatically when the related AI tool reconnects." -ForegroundColor White
    Write-Host "  Restart the AI client or run the specific server manually when needed." -ForegroundColor White
    Write-Host ""
    Write-Host "  Manual start examples:" -ForegroundColor Yellow
    Write-Host "    npx youtube-mcp" -ForegroundColor Gray
    Write-Host "    npx cloudinary-mcp" -ForegroundColor Gray
    Write-Host "    python -m n8n_mcp" -ForegroundColor Gray
    Write-Host "    python -m notebooklm_mcp" -ForegroundColor Gray
}

function Invoke-Guard {
    $isHealthy = Show-AiToolStatus
    if (-not $isHealthy) {
        exit 1
    }
}

switch ($Action) {
    "Status" {
        Show-AiToolStatus | Out-Null
        Show-Tier3Status
    }
    "Disable" {
        Invoke-Disable
        Show-Tier3Status
    }
    "Enable" {
        Invoke-Enable
        Show-Tier3Status
    }
    "Guard" {
        Invoke-Guard
    }
}
