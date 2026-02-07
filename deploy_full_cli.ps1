# Agentic Framework - Complete CLI Deployment
# Full deployment using LeCoder CLI - stays entirely in VS Code

Write-Host "🚀 Agentic Framework - Complete CLI Deployment" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Cyan

# Configuration
$cliPath = "LeCoder-cgpu-CLI"
$deploymentScript = "colab_deployment.py"
$remoteScriptPath = "/content/$deploymentScript"

# Validate requirements
if (!(Test-Path $cliPath)) {
    Write-Host "✗ LeCoder CLI not found at $cliPath" -ForegroundColor Red
    exit 1
}

if (!(Test-Path $deploymentScript)) {
    Write-Host "✗ Deployment script not found: $deploymentScript" -ForegroundColor Red
    exit 1
}

Write-Host "✓ All requirements met" -ForegroundColor Green

# Check if already authenticated
Write-Host ""
Write-Host "🔐 Checking authentication status..." -ForegroundColor Blue
Push-Location $cliPath

$authStatus = & npx tsx src/index.ts status 2>&1
if ($authStatus -match "not authenticated" -or $authStatus -match "error") {
    Write-Host "⚠️  Not authenticated. Starting authentication..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📋 AUTHENTICATION REQUIRED:" -ForegroundColor Cyan
    Write-Host "A browser window will open for Google OAuth." -ForegroundColor White
    Write-Host "Complete the authentication process, then return here." -ForegroundColor White
    Write-Host ""

    $ready = Read-Host "Press Enter when ready to authenticate"
    Write-Host "🔄 Starting authentication..." -ForegroundColor Blue

    & npx tsx src/index.ts connect --new-runtime

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Authentication failed" -ForegroundColor Red
        Pop-Location
        exit 1
    }

    Write-Host "✅ Authentication successful!" -ForegroundColor Green
} else {
    Write-Host "✅ Already authenticated" -ForegroundColor Green
}

Pop-Location

# Upload deployment script
Write-Host ""
Write-Host "📤 Uploading deployment script..." -ForegroundColor Blue
Push-Location $cliPath

& npx tsx src/index.ts copy ..\$deploymentScript $remoteScriptPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Upload failed" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "✅ Script uploaded successfully" -ForegroundColor Green
Pop-Location

# Start deployment
Write-Host ""
Write-Host "🚀 Starting deployment on Colab GPU..." -ForegroundColor Green
Write-Host "This will take 10-15 minutes. Monitor the output below." -ForegroundColor Yellow
Write-Host ""

Push-Location $cliPath

# Run the deployment script
Write-Host "DEPLOYMENT OUTPUT:" -ForegroundColor Cyan
Write-Host "=" * 30 -ForegroundColor Cyan

& npx tsx src/index.ts run --mode kernel "exec(open('$deploymentScript').read())"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ Deployment failed or was interrupted" -ForegroundColor Red
    Write-Host "You can check the status later with: .\check_deployment_status.ps1" -ForegroundColor Yellow
    Pop-Location
    exit 1
}

Pop-Location

Write-Host ""
Write-Host "🎉 DEPLOYMENT COMPLETED!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 ACCESS INFORMATION:" -ForegroundColor Cyan
Write-Host "Run the following commands to get service URLs:" -ForegroundColor White
Write-Host ""
Write-Host "  .\check_deployment_status.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "Or manually check with:" -ForegroundColor White
Write-Host "  cd LeCoder-cgpu-CLI" -ForegroundColor White
Write-Host "  npx tsx src/index.ts run 'ps aux | grep -E \"(ollama|ngrok|minio)\" | grep -v grep'" -ForegroundColor White
Write-Host ""
Write-Host "Your Agentic Framework is running on Google Colab GPU! 🎯" -ForegroundColor Green