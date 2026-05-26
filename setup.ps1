# ===================================================================
# Vibe Coding Workspace — Developer Experience Setup Script (1-Click)
# Safe, idempotent, and beautifully formatted for Windows PowerShell
# ===================================================================

$ErrorActionPreference = "Stop"
$UTF8Encoding = [System.Text.Encoding]::UTF8

# Set console output to UTF-8 to support beautiful emojis
[Console]::OutputEncoding = $UTF8Encoding

# Colors
$Indigo = "#6366f1"
$Purple = "#a855f7"
$Pink = "#ec4899"
$Emerald = "#10b981"
$Amber = "#f59e0b"
$Red = "#ef4444"
$Secondary = "#a0a0b8"

function Write-GradientHeader {
    Write-Host "" -ForegroundColor Cyan
    Write-Host "  ====================================================== " -ForegroundColor Magenta
    Write-Host "  🎵  Vibe Coding Workspace — Developer Experience Setup" -ForegroundColor Yellow
    Write-Host "  ====================================================== " -ForegroundColor Magenta
    Write-Host ""
}

function Write-Step {
    param([string]$Num, [string]$Title)
    Write-Host "[$Num/5] $Title..." -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Msg)
    Write-Host "  ✔ $Msg" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Msg)
    Write-Host "  ⚠ $Msg" -ForegroundColor Yellow
}

function Write-ErrorMsg {
    param([string]$Msg)
    Write-Host "  ✘ [ERROR] $Msg" -ForegroundColor Red
}

Write-GradientHeader

# -------------------------------------------------------------------
# [1/5] Prerequisite Verification
# -------------------------------------------------------------------
Write-Step "1" "Verifying core prerequisites"

# Check Python
try {
    $pyVersion = & py -3 --version 2>&1
    Write-Success "Python is available: $pyVersion"
} catch {
    Write-ErrorMsg "Python 3 launcher (py) is not installed or not in PATH."
    Write-Host "Please install Python 3.11+ from https://www.python.org/ and retry." -ForegroundColor Yellow
    Exit 1
}

# Check Node.js
try {
    $nodeVersion = & node --version 2>&1
    Write-Success "Node.js is available: $nodeVersion"
} catch {
    Write-ErrorMsg "Node.js is not installed or not in PATH."
    Write-Host "Please install Node.js 20+ from https://nodejs.org/ and retry." -ForegroundColor Yellow
    Exit 1
}

# Check npm (hanwoo-dashboard default runner)
try {
    $npmVersion = & npm --version 2>&1
    Write-Success "npm is available: v$npmVersion"
} catch {
    Write-ErrorMsg "npm is not installed or not in PATH."
    Exit 1
}

# -------------------------------------------------------------------
# [2/5] Setting up unified Python environment with uv
# -------------------------------------------------------------------
Write-Step "2" "Setting up unified Python environment with uv"

if (-not (Test-Path "venv")) {
    Write-Host "  Creating virtual environment (venv)..." -ForegroundColor Gray
    & py -3 -m venv venv
    Write-Success "Virtual environment created."
} else {
    Write-Success "Virtual environment already exists."
}

$pyPath = "venv\Scripts\python.exe"
$uvPath = "venv\Scripts\uv.exe"

Write-Host "  Upgrading pip and installing Astral uv..." -ForegroundColor Gray
& $pyPath -m pip install --upgrade pip uv 2>&1 | Out-Null
Write-Success "pip & uv successfully prepared."

Write-Host "  Syncing unified workspace (Control Plane + pipelines)..." -ForegroundColor Gray
& $uvPath sync
if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Unified Python workspace sync failed."
    Exit 1
}
Write-Success "Unified Python workspace synchronized successfully."

# -------------------------------------------------------------------
# [3/5] Installing Next.js Dashboard Dependencies
# -------------------------------------------------------------------
Write-Step "3" "Installing Next.js Dashboard dependencies"

if (Test-Path "projects\hanwoo-dashboard") {
    Write-Host "  Installing dependencies for hanwoo-dashboard..." -ForegroundColor Gray
    Push-Location "projects\hanwoo-dashboard"
    & npm install
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Write-ErrorMsg "hanwoo-dashboard npm install failed."
        Exit 1
    }
    
    Write-Host "  Generating Prisma Client..." -ForegroundColor Gray
    & npx prisma generate
    Pop-Location
    Write-Success "hanwoo-dashboard dependencies and Prisma client prepared."
} else {
    Write-Warning "hanwoo-dashboard directory not found. Skipping."
}

# -------------------------------------------------------------------
# [4/5] Environment Variable Verification
# -------------------------------------------------------------------
Write-Step "4" "Verifying environment variables"

$envTemplates = @(
    @{ template = ".env.example"; target = ".env" },
    @{ template = ".env.example"; target = "projects\blind-to-x\.env" },
    @{ template = "projects\hanwoo-dashboard\.env"; target = "projects\hanwoo-dashboard\.env" } # check existence
)

foreach ($envFile in $envTemplates) {
    $targetPath = $envFile.target
    $tmplPath = $envFile.template
    
    if (-not (Test-Path $targetPath)) {
        if ($tmplPath -eq $targetPath) {
            # Special case for Joolife .env if not found
            Write-Warning "Joolife dashboard .env not found. Creating a blank template."
            New-Item -ItemType File -Path $targetPath -Force | Out-Null
            Add-Content -Path $targetPath -Value "DATABASE_URL=`"postgresql://postgres:postgrespassword@localhost:5432/hanwoo_dev`""
            Add-Content -Path $targetPath -Value "AUTH_SECRET=`"1BPLHqdBW8+F5piKkUXrIB6BdHRBuNK6BvOMDANr2cU=`""
            Add-Content -Path $targetPath -Value "AUTH_URL=`"http://localhost:3001`""
        } else {
            Write-Host "  Copying $tmplPath to $targetPath..." -ForegroundColor Gray
            Copy-Item $tmplPath $targetPath
            Write-Success "Created $targetPath from template."
        }
    } else {
        Write-Success "$targetPath already exists."
    }
}

# -------------------------------------------------------------------
# [5/5] Running System Diagnostics
# -------------------------------------------------------------------
Write-Step "5" "Running workspace diagnostics"

if (Test-Path "workspace\scripts\doctor.py") {
    Write-Host "  Running workspace doctor script..." -ForegroundColor Gray
    & $uvPath run workspace\scripts\doctor.py
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Workspace doctor diagnostics completed successfully."
    } else {
        Write-Warning "Workspace doctor reported warning/failures. Please review the output above."
    }
} else {
    Write-Warning "Workspace doctor script not found."
}

# -------------------------------------------------------------------
# Summary Output
# -------------------------------------------------------------------
Write-Host ""
Write-Host "  ====================================================== " -ForegroundColor Magenta
Write-Host "  🚀  Setup Complete! Vibe Coding Workspace is Ready. " -ForegroundColor Green
Write-Host "  ====================================================== " -ForegroundColor Magenta
Write-Host ""
Write-Host "  🎯 Next Recommended Steps:" -ForegroundColor Yellow
Write-Host "  1. Run local infra (DB & Redis):" -ForegroundColor Gray
Write-Host "     docker-compose up -d" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Run Next.js Joolife Dashboard:" -ForegroundColor Gray
Write-Host "     cd projects\hanwoo-dashboard && npm run dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Launch Streamlit Shorts Manager:" -ForegroundColor Gray
Write-Host "     cd workspace && ..\venv\Scripts\uv run streamlit run execution\pages\shorts_manager.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "  4. Check README.md for complete details on architecture and pipelines." -ForegroundColor Gray
Write-Host ""
Write-Host "  🎵 Happy Vibe Coding! 🎵" -ForegroundColor Magenta
Write-Host ""
