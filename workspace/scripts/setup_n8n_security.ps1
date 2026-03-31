# setup_n8n_security.ps1
# P1-6: n8n Binding Fix to 127.0.0.1 + Firewall Rule
# Run as Administrator required for firewall rules

$ErrorActionPreference = "Continue"

$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$N8N_PORT = 5678

Write-Host "[P1-6] n8n Security Hardening" -ForegroundColor Cyan
Write-Host ""

# 1. Check .env for N8N_HOST setting
Write-Host "[1/3] Checking .env for N8N_HOST..." -ForegroundColor Yellow

$EnvFiles = @(
    (Join-Path $ROOT ".env"),
    (Join-Path $ROOT ".env.llm"),
    (Join-Path $ROOT ".env.social"),
    (Join-Path $ROOT ".env.project")
)

$N8N_FOUND = $false
foreach ($envFile in $EnvFiles) {
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw -Encoding UTF8
        if ($content -match "N8N_HOST") {
            Write-Host "  OK N8N_HOST found in: $envFile" -ForegroundColor Green
            $N8N_FOUND = $true
        }
    }
}

if (-not $N8N_FOUND) {
    Write-Host "  INFO N8N_HOST not configured. Add to docker-compose.yml:" -ForegroundColor Yellow
    Write-Host "    environment:" -ForegroundColor Gray
    Write-Host "      - N8N_HOST=127.0.0.1" -ForegroundColor Gray
    Write-Host "      - N8N_PORT=$N8N_PORT" -ForegroundColor Gray
    Write-Host "      - WEBHOOK_URL=http://127.0.0.1:$N8N_PORT/" -ForegroundColor Gray

    $dockerFiles = Get-ChildItem -Path $ROOT -Name "docker-compose*.yml" -ErrorAction SilentlyContinue
    if ($dockerFiles) {
        Write-Host "  Docker Compose files found:" -ForegroundColor Yellow
        foreach ($f in $dockerFiles) {
            Write-Host "    - $f" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  OK N8N_HOST is configured" -ForegroundColor Green
}

# 2. Check current binding status
Write-Host ""
Write-Host "[2/3] Checking n8n port binding (port: $N8N_PORT)..." -ForegroundColor Yellow
try {
    $netstat = netstat -an | Select-String ":$N8N_PORT "
    if ($netstat) {
        Write-Host "  Current n8n binding:" -ForegroundColor Yellow
        foreach ($line in $netstat) {
            $lineStr = $line.ToString().Trim()
            if ($lineStr -match "0\.0\.0\.0:$N8N_PORT") {
                Write-Host "  WARN $lineStr (external access enabled!)" -ForegroundColor Red
            } elseif ($lineStr -match "127\.0\.0\.1:$N8N_PORT") {
                Write-Host "  OK   $lineStr (localhost only - safe)" -ForegroundColor Green
            } else {
                Write-Host "  INFO $lineStr" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "  INFO n8n not running (port $N8N_PORT not in use)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  WARN netstat check failed" -ForegroundColor Yellow
}

# 3. Add firewall rule (block external inbound on port 5678)
Write-Host ""
Write-Host "[3/3] Adding Windows Firewall inbound block rule..." -ForegroundColor Yellow

$FW_RULE_NAME = "Block n8n External Access (Port $N8N_PORT)"

try {
    # Remove existing rule first
    Remove-NetFirewallRule -DisplayName $FW_RULE_NAME -ErrorAction SilentlyContinue

    # Block ALL inbound on port 5678 (n8n bound to 127.0.0.1 is already protected;
    # This adds defense-in-depth blocking external TCP inbound)
    New-NetFirewallRule `
        -DisplayName $FW_RULE_NAME `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $N8N_PORT `
        -Action Block `
        -Profile Any `
        -Description "Block all inbound TCP on n8n port. n8n should be bound to 127.0.0.1 only." `
        | Out-Null

    Write-Host "  OK Firewall block rule added" -ForegroundColor Green
    Write-Host "     Rule: $FW_RULE_NAME" -ForegroundColor Gray
    Write-Host "     Port: $N8N_PORT (all inbound TCP blocked)" -ForegroundColor Gray
    Write-Host "     Note: Local services using 127.0.0.1 are not affected" -ForegroundColor Gray
} catch {
    Write-Host "  WARN Firewall rule failed: $_" -ForegroundColor Yellow
    Write-Host "     Manual: New-NetFirewallRule -DisplayName '$FW_RULE_NAME' -Direction Inbound -Protocol TCP -LocalPort $N8N_PORT -Action Block" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Add N8N_HOST=127.0.0.1 to Docker Compose" -ForegroundColor Gray
Write-Host "    2. Restart n8n and verify: netstat -an | findstr $N8N_PORT" -ForegroundColor Gray
Write-Host "    3. For external access, use Cloudflare Tunnel" -ForegroundColor Gray
