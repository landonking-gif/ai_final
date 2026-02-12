<#
.SYNOPSIS
    Launch the Agentic Framework Colab deployment.

.DESCRIPTION
    1. Commits and pushes any local changes to GitHub
    2. Opens the Colab deployment notebook in your browser
    3. Prints instructions for running the deployment

.NOTES
    Requirements: Git must be configured with push access to the repo.
#>

param(
    [switch]$NoPush,
    [switch]$Help
)

$ErrorActionPreference = "Continue"

# Colors
function Write-Header($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)     { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg)   { Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)    { Write-Host "  [X]  $msg" -ForegroundColor Red }
function Write-Step($n, $msg) { Write-Host "  $n. $msg" -ForegroundColor White }

$ColabUrl = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/deploy/colab_notebook.ipynb"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if ($Help) {
    Write-Host ""
    Write-Host "  Agentic Framework - Colab Deployment Launcher"
    Write-Host "  ================================================"
    Write-Host ""
    Write-Host "  Usage:"
    Write-Host "    .\deploy\launch.ps1           # Push changes and open Colab"
    Write-Host "    .\deploy\launch.ps1 -NoPush   # Open Colab without pushing"
    Write-Host "    .\deploy\launch.ps1 -Help     # Show this help"
    Write-Host ""
    Write-Host "  What it does:"
    Write-Host "    1. Stages and commits any uncommitted changes"
    Write-Host "    2. Pushes to GitHub (main branch)"
    Write-Host "    3. Opens the Colab notebook in your default browser"
    Write-Host "    4. You select GPU runtime and click Run All"
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "  Agentic Framework - Colab Deployment Launcher" -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan

# Step 1: Push to GitHub
if (-not $NoPush) {
    Write-Header "PUSHING TO GITHUB"

    Push-Location $RepoRoot

    # Check for changes
    $status = git status --porcelain 2>&1
    if ($status) {
        Write-Ok "Found uncommitted changes - staging and committing..."
        git add -A
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        git commit -m "deploy: auto-commit before Colab deployment ($timestamp)"
        Write-Ok "Committed"
    } else {
        Write-Ok "No uncommitted changes"
    }

    Write-Ok "Pushing to origin/main..."
    $pushResult = git push origin main 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Push successful"
    } else {
        Write-Warn "Push may have failed: $pushResult"
        Write-Warn "Continuing anyway - Colab will use whatever is on GitHub"
    }

    Pop-Location
} else {
    Write-Warn "Skipping git push (-NoPush flag)"
}

# Step 2: Open Colab
Write-Header "OPENING COLAB"
Write-Ok "URL: $ColabUrl"

try {
    Start-Process $ColabUrl
    Write-Ok "Browser opened"
} catch {
    Write-Err "Could not open browser automatically"
    Write-Host "  Open this URL manually:" -ForegroundColor White
    Write-Host "  $ColabUrl" -ForegroundColor Yellow
}

# Step 3: Instructions
Write-Header "NEXT STEPS (in Google Colab)"
Write-Step "1" "Select GPU runtime: Runtime -> Change runtime type -> T4 GPU"
Write-Step "2" "Run all cells: Runtime -> Run all (or Ctrl+F9)"
Write-Step "3" "Wait ~5 minutes for full deployment"
Write-Step "4" "Your public API and Dashboard URLs will be printed at the end"
Write-Host ""
Write-Step "" "To check status later, run Cell 2 (Diagnostics)"
Write-Step "" "To restart a service, run Cell 3 (Recovery)"
Write-Host ""
Write-Host "  ================================================" -ForegroundColor Green
Write-Host "  Deployment will be fully automatic after Run All" -ForegroundColor Green
Write-Host "  ================================================" -ForegroundColor Green
Write-Host ""
