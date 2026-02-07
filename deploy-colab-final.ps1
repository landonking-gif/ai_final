# Automated Agentic Framework Colab Deployment
# This script creates and opens the automated deployment notebook

Write-Host "🚀 Agentic Framework Colab Deployment" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if the automated notebook exists
$notebookPath = "agentic-framework-deploy-auto.ipynb"
if (!(Test-Path $notebookPath)) {
    Write-Host "❌ Automated deployment notebook not found!" -ForegroundColor Red
    Write-Host "   Please ensure the notebook exists in the workspace." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Automated deployment notebook found" -ForegroundColor Green

# Open the notebook in Google Colab
Write-Host "🌐 Opening automated deployment notebook in Google Colab..." -ForegroundColor Blue
Write-Host "   URL: https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/agentic-framework-deploy-auto.ipynb" -ForegroundColor White

# Try to open in default browser
try {
    Start-Process "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/agentic-framework-deploy-auto.ipynb"
    Write-Host "✅ Notebook opened in browser" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Could not open browser automatically" -ForegroundColor Yellow
    Write-Host "   Please manually open the URL above" -ForegroundColor White
}

Write-Host ""
Write-Host "📋 Deployment Instructions:" -ForegroundColor Cyan
Write-Host "  1. Set runtime to GPU (H100 recommended) in Colab" -ForegroundColor White
Write-Host "  2. Run the single deployment cell" -ForegroundColor White
Write-Host "  3. Wait for completion (~10-15 minutes)" -ForegroundColor White
Write-Host "  4. Access your services via the generated URLs" -ForegroundColor White
Write-Host ""
Write-Host "🎉 Your Agentic Framework will be running on Google Colab GPU!" -ForegroundColor Green