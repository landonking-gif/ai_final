# Agentic Framework - Colab Deployment with CLI
# This script uses colab-cli to upload and open the deployment notebook

Write-Host "Agentic Framework - Colab Deployment" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Yellow

# Check if the notebook exists
$notebookPath = Join-Path $PSScriptRoot "colab_auto_run.ipynb"
if (!(Test-Path $notebookPath)) {
    Write-Host "Notebook not found: $notebookPath" -ForegroundColor Red
    Write-Host "Please ensure colab_auto_run.ipynb is in the same directory as this script." -ForegroundColor Red
    exit 1
}

Write-Host "Found deployment notebook: $notebookPath" -ForegroundColor Green

# Check if colab-cli is installed
try {
    $colabCliVersion = & colab-cli --version 2>$null
    Write-Host "✓ colab-cli installed: $colabCliVersion" -ForegroundColor Green
} catch {
    Write-Host "📦 Installing colab-cli..." -ForegroundColor Yellow
    try {
        & python -m pip install colab-cli
        Write-Host "✓ colab-cli installed" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed to install colab-cli. Please install manually: pip install colab-cli" -ForegroundColor Red
        exit 1
    }
}

Write-Host "" -ForegroundColor White
Write-Host "🔄 Uploading and opening notebook in Google Colab..." -ForegroundColor Cyan
Write-Host "This will:" -ForegroundColor White
Write-Host "  1. Upload colab_auto_run.ipynb to your Google Drive" -ForegroundColor White
Write-Host "  2. Open it in Google Colab" -ForegroundColor White
Write-Host "  3. You'll need to run all cells manually" -ForegroundColor White
Write-Host "" -ForegroundColor White

# Upload and open the notebook
try {
    & colab-cli open-nb "$notebookPath"
    Write-Host "" -ForegroundColor White
    Write-Host "✅ Notebook uploaded and opened successfully!" -ForegroundColor Green
} catch {
    Write-Host "" -ForegroundColor White
    Write-Host "✗ Failed to upload/open notebook: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Trying alternative method..." -ForegroundColor Yellow

    # Fallback: try to open in browser directly
    try {
        Start-Process "https://colab.research.google.com/notebooks/intro.ipynb"
        Write-Host "✓ Opened Google Colab in browser" -ForegroundColor Green
        Write-Host "You'll need to upload colab_auto_run.ipynb manually" -ForegroundColor Yellow
    } catch {
        Write-Host "✗ Could not open browser. Please manually open: https://colab.research.google.com" -ForegroundColor Red
    }
}

Write-Host "" -ForegroundColor White
Write-Host "📋 Manual Instructions:" -ForegroundColor Yellow
Write-Host "  1. Make sure you're logged into Google Colab" -ForegroundColor White
Write-Host "  2. If not uploaded automatically, upload colab_auto_run.ipynb" -ForegroundColor White
Write-Host "  3. Set runtime to GPU (H100) via Runtime > Change runtime type" -ForegroundColor White
Write-Host "  4. Click 'Runtime > Run all' or press Ctrl+F9" -ForegroundColor White
Write-Host "  5. Wait 10-15 minutes for full deployment" -ForegroundColor White
Write-Host "" -ForegroundColor White

Write-Host "The notebook will automatically deploy:" -ForegroundColor Cyan
Write-Host "  - Ollama + DeepSeek R1 14B (GPU)" -ForegroundColor White
Write-Host "  - PostgreSQL, Redis, ChromaDB, MinIO" -ForegroundColor White
Write-Host "  - 5 microservices + React dashboard" -ForegroundColor White
Write-Host "  - ngrok tunnels for external access" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Happy deploying! 🚀" -ForegroundColor Green

# Keep window open
Read-Host "Press Enter to exit"