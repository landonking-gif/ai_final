Write-Host "Agentic Framework - CLI Deployment Menu" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Cyan

# Check requirements
$scriptPath = Join-Path $PSScriptRoot "colab_deployment.py"
if (!(Test-Path $scriptPath)) {
    Write-Host "Error: colab_deployment.py not found at $scriptPath" -ForegroundColor Red
    exit 1
}
Write-Host "Requirements check passed" -ForegroundColor Green

$colabUrl = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb"

Write-Host ""
Write-Host "DEPLOYMENT OPTIONS:" -ForegroundColor Cyan
Write-Host "1. Open Colab (Recommended)" -ForegroundColor Green
Write-Host "2. Show instructions" -ForegroundColor Blue
Write-Host "3. Check status" -ForegroundColor Yellow
Write-Host ""

$choice = Read-Host "Choose option (1-3)"

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "OPENING COLAB..." -ForegroundColor Green
    Start-Process $colabUrl
    Write-Host "Colab opened in browser" -ForegroundColor Green

    Write-Host ""
    Write-Host "INSTRUCTIONS:" -ForegroundColor Cyan
    Write-Host "1. Login to Google Colab" -ForegroundColor White
    Write-Host "2. Set runtime to GPU" -ForegroundColor White
    Write-Host "3. Click Runtime -> Run all" -ForegroundColor White
    Write-Host "4. Wait 10-15 minutes" -ForegroundColor White
    Write-Host "5. Check Cell 5 for URLs" -ForegroundColor White
}
elseif ($choice -eq "2") {
    Write-Host ""
    Write-Host "DEPLOYMENT INSTRUCTIONS:" -ForegroundColor Cyan
    Write-Host "1. Open: $colabUrl" -ForegroundColor White
    Write-Host "2. Set GPU runtime" -ForegroundColor White
    Write-Host "3. Run all cells" -ForegroundColor White
    Write-Host "4. Monitor progress" -ForegroundColor White
}
elseif ($choice -eq "3") {
    Write-Host ""
    Write-Host "CHECKING STATUS..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/landonking-gif/ai_final/main/colab_auto_run.ipynb" -Method Head
        Write-Host "GitHub accessible: Yes" -ForegroundColor Green
    } catch {
        Write-Host "GitHub accessible: No" -ForegroundColor Red
    }
}
else {
    Write-Host "Invalid choice" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green