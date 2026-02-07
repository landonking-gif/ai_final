# Agentic Framework - CLI-Style Colab Deployment
# Opens Colab and provides automated instructions without manual browser interaction

Write-Host "🚀 Agentic Framework - CLI Colab Deployment" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan

# Check if deployment files exist
$deploymentScript = "colab_deployment.py"
$notebookPath = "colab_auto_run.ipynb"

if (!(Test-Path $deploymentScript)) {
    Write-Host "✗ Deployment script not found: $deploymentScript" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Deployment script found" -ForegroundColor Green

if (!(Test-Path $notebookPath)) {
    Write-Host "⚠️ Local notebook not found, will use GitHub version" -ForegroundColor Yellow
} else {
    Write-Host "✓ Local notebook found" -ForegroundColor Green
}

# GitHub Colab URL
$colabUrl = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb"

Write-Host ""
Write-Host "🔄 Opening Google Colab..." -ForegroundColor Blue

# Open Colab in default browser
try {
    Start-Process $colabUrl
    Write-Host "✅ Colab opened successfully!" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to open browser: $_" -ForegroundColor Red
    Write-Host "Please manually open: $colabUrl" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "📋 AUTOMATED DEPLOYMENT INSTRUCTIONS:" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "STEP 1: Runtime Setup" -ForegroundColor Green
Write-Host "  → Click: Runtime → Change runtime type" -ForegroundColor White
Write-Host "  → Select: T4 GPU (or A100 if available)" -ForegroundColor White
Write-Host "  → Click: Save" -ForegroundColor White
Write-Host ""

Write-Host "STEP 2: Start Deployment" -ForegroundColor Green
Write-Host "  → Click: Runtime → Run all (or press Ctrl+F9)" -ForegroundColor White
Write-Host ""

Write-Host "STEP 3: Monitor Progress" -ForegroundColor Green
Write-Host "  → Watch the output cells for deployment progress" -ForegroundColor White
Write-Host "  → Deployment takes 10-15 minutes" -ForegroundColor White
Write-Host ""

Write-Host "🎯 WHAT GETS DEPLOYED:" -ForegroundColor Cyan
Write-Host "  • Ollama + DeepSeek R1 14B (GPU-accelerated)" -ForegroundColor White
Write-Host "  • PostgreSQL, Redis, ChromaDB, MinIO databases" -ForegroundColor White
Write-Host "  • 5 microservices + React dashboard" -ForegroundColor White
Write-Host "  • ngrok tunnels for external access" -ForegroundColor White
Write-Host ""

Write-Host "📊 ACCESS INFORMATION:" -ForegroundColor Cyan
Write-Host "  → Check Cell 5 output for ngrok URLs" -ForegroundColor White
Write-Host "  → Dashboard will be available at one of the URLs" -ForegroundColor White
Write-Host "  → Services auto-restart if they crash" -ForegroundColor White
Write-Host ""

Write-Host "⚠️  IMPORTANT NOTES:" -ForegroundColor Yellow
Write-Host "  • Keep Colab tab open during deployment" -ForegroundColor White
Write-Host "  • GPU runtime is required for LLM inference" -ForegroundColor White
Write-Host "  • Free tier: 12GB RAM, ~12 hours runtime" -ForegroundColor White
Write-Host "  • Colab Pro/Pro+: More resources, longer runtime" -ForegroundColor White
Write-Host ""

Write-Host "✅ READY TO DEPLOY!" -ForegroundColor Green
Write-Host "Follow the steps above in the Colab tab that just opened." -ForegroundColor White
Write-Host ""

# Wait for user confirmation
Read-Host "Press Enter when deployment is complete (or Ctrl+C to exit now)"

Write-Host ""
Write-Host "🎉 Deployment should now be running!" -ForegroundColor Green
Write-Host "Check the Colab output for your service URLs." -ForegroundColor White