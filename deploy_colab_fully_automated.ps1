# Agentic Framework - Fully Automated Colab Deployment
# Uses Selenium to automate the entire deployment process

Write-Host "🚀 Agentic Framework - Fully Automated Colab Deployment" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python available: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check if required packages are installed
Write-Host "🔄 Checking dependencies..." -ForegroundColor Blue
try {
    python -c "import selenium; import webdriver_manager" 2>$null
    Write-Host "✓ Selenium and webdriver-manager installed" -ForegroundColor Green
} catch {
    Write-Host "Installing required packages..." -ForegroundColor Yellow
    pip install selenium webdriver-manager
}

# Check if Chrome is available
try {
    $chromeVersion = & "C:\Program Files\Google\Chrome\Application\chrome.exe" --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Chrome browser available" -ForegroundColor Green
    } else {
        throw "Chrome not found"
    }
} catch {
    Write-Host "⚠️ Chrome browser not found at default location" -ForegroundColor Yellow
    Write-Host "Please ensure Chrome is installed" -ForegroundColor White
}

# Check if deployment script exists
$deploymentScript = "colab_deployment.py"
if (!(Test-Path $deploymentScript)) {
    Write-Host "✗ Deployment script not found: $deploymentScript" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Deployment script found" -ForegroundColor Green

Write-Host ""
Write-Host "🎯 STARTING AUTOMATED DEPLOYMENT" -ForegroundColor Green
Write-Host ""
Write-Host "This script will:" -ForegroundColor Cyan
Write-Host "  1. Open Chrome and navigate to Colab" -ForegroundColor White
Write-Host "  2. Create a new notebook with GPU runtime" -ForegroundColor White
Write-Host "  3. Load the deployment script" -ForegroundColor White
Write-Host "  4. Start the automatic deployment" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  IMPORTANT: Do not close the Chrome window during deployment!" -ForegroundColor Yellow
Write-Host ""

# Confirm before starting
$confirmation = Read-Host "Ready to start automated deployment? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Run the automated deployment
Write-Host "🔄 Starting automation..." -ForegroundColor Blue
try {
    python colab_automated_deploy.py
    Write-Host "✅ Automation completed!" -ForegroundColor Green
} catch {
    Write-Host "✗ Automation failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual deployment instructions:" -ForegroundColor Yellow
    Write-Host "1. Open: https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb" -ForegroundColor White
    Write-Host "2. Set runtime to GPU (Runtime > Change runtime type)" -ForegroundColor White
    Write-Host "3. Click 'Runtime > Run all'" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "🎉 Deployment process started!" -ForegroundColor Green
Write-Host "Monitor the Chrome window for progress." -ForegroundColor White
Write-Host "The deployment will take 10-15 minutes." -ForegroundColor White