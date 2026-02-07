# ============================================================
# Agentic Framework - Google Colab Deployment Helper
# ============================================================
# This script prepares and pushes the codebase to GitHub,
# then provides instructions to deploy on Google Colab.
#
# Usage: .\colab_deploy.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$FRAMEWORK_DIR = Join-Path $SCRIPT_DIR "agentic-framework-main"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Agentic Framework - Colab Deployment" -ForegroundColor Cyan
Write-Host "GPU-Accelerated (H100) + Local AI" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Ensure latest code is pushed to GitHub
Write-Host "[1/3] Syncing code to GitHub..." -ForegroundColor Yellow

Push-Location $SCRIPT_DIR

# Check if there are uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Host "  Uncommitted changes found. Committing..." -ForegroundColor Yellow
    git add -A
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    git commit -m "Colab deployment sync - $timestamp"
}

# Push to origin
git push origin main 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Code pushed to GitHub" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Push failed - ensure remote is configured" -ForegroundColor Yellow
    Write-Host "  Run: git remote add origin https://github.com/landonking-gif/ai_final.git" -ForegroundColor White
}

Pop-Location

# Step 2: Validate the deployment notebook exists
Write-Host ""
Write-Host "[2/3] Checking deployment notebook..." -ForegroundColor Yellow

$notebookPath = Join-Path $SCRIPT_DIR "colab_deploy.ipynb"
if (Test-Path $notebookPath) {
    Write-Host "  [OK] colab_deploy.ipynb found" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] colab_deploy.ipynb not found!" -ForegroundColor Red
    Write-Host "  Generate it first using VS Code / Copilot" -ForegroundColor Yellow
    exit 1
}

# Ensure notebook is committed
Push-Location $SCRIPT_DIR
$nbStatus = git status --porcelain colab_deploy.ipynb
if ($nbStatus) {
    git add colab_deploy.ipynb
    git commit -m "Add Colab deployment notebook"
    git push origin main 2>$null
    Write-Host "  [OK] Notebook pushed to GitHub" -ForegroundColor Green
}
Pop-Location

# Step 3: Print deployment instructions
Write-Host ""
Write-Host "[3/3] Deployment Instructions" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "HOW TO DEPLOY ON GOOGLE COLAB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Option A: Open notebook directly from GitHub" -ForegroundColor Cyan
Write-Host "  1. Go to: https://colab.research.google.com" -ForegroundColor White
Write-Host "  2. Click File > Open notebook > GitHub tab" -ForegroundColor White
Write-Host "  3. Enter repo: landonking-gif/ai_final" -ForegroundColor White
Write-Host "  4. Select: colab_deploy.ipynb" -ForegroundColor White
Write-Host ""
Write-Host "Option B: Upload notebook manually" -ForegroundColor Cyan
Write-Host "  1. Go to: https://colab.research.google.com" -ForegroundColor White
Write-Host "  2. Click File > Upload notebook" -ForegroundColor White
Write-Host "  3. Upload: $notebookPath" -ForegroundColor White
Write-Host ""
Write-Host "Option C: Direct URL (after pushing to GitHub)" -ForegroundColor Cyan
Write-Host "  Open: https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_deploy.ipynb" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT SETUP STEPS:" -ForegroundColor Yellow
Write-Host "  1. Set runtime to GPU: Runtime > Change runtime type > GPU (H100)" -ForegroundColor White
Write-Host "  2. Run all cells in order (Cell 1 through Cell 9)" -ForegroundColor White
Write-Host "  3. Cell 7 will give you the public URL to access the API" -ForegroundColor White
Write-Host ""
Write-Host "SERVICES DEPLOYED:" -ForegroundColor Cyan
Write-Host "  - Orchestrator (port 8000) - Main API + WebSocket" -ForegroundColor White
Write-Host "  - Memory Service (port 8002) - 4-tier storage" -ForegroundColor White
Write-Host "  - SubAgent Manager (port 8003) - Agent lifecycle" -ForegroundColor White
Write-Host "  - MCP Gateway (port 8080) - Tool integration" -ForegroundColor White
Write-Host "  - Code Executor (port 8004) - Sandboxed execution" -ForegroundColor White
Write-Host "  - Ollama (port 11434) - GPU LLM inference" -ForegroundColor White
Write-Host "  - PostgreSQL (port 5432) - Structured storage" -ForegroundColor White
Write-Host "  - Redis (port 6379) - Session/cache" -ForegroundColor White
Write-Host "  - ChromaDB (port 8001) - Vector storage" -ForegroundColor White
Write-Host "  - MinIO (port 9000) - Object storage" -ForegroundColor White
Write-Host ""
Write-Host "NOTE: Colab sessions are temporary (12-24 hrs max)." -ForegroundColor Yellow
Write-Host "      Data is lost when the session ends." -ForegroundColor Yellow
Write-Host "      Use Google Drive mount for persistent storage." -ForegroundColor Yellow
Write-Host ""
