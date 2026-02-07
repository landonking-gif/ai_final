# Agentic Framework - Pure CLI Colab Deployment
# Uses LeCoder CLI to deploy entirely from VS Code terminal

Write-Host "🚀 Agentic Framework - Pure CLI Colab Deployment" -ForegroundColor Green
Write-Host "=" * 55 -ForegroundColor Cyan

# Check if LeCoder CLI is available
$cliPath = "LeCoder-cgpu-CLI"
if (!(Test-Path $cliPath)) {
    Write-Host "✗ LeCoder CLI not found at $cliPath" -ForegroundColor Red
    exit 1
}
Write-Host "✓ LeCoder CLI found" -ForegroundColor Green

# Check if deployment script exists
$deploymentScript = "colab_deployment.py"
if (!(Test-Path $deploymentScript)) {
    Write-Host "✗ Deployment script not found: $deploymentScript" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Deployment script found" -ForegroundColor Green

Write-Host ""
Write-Host "🔐 FIRST TIME SETUP REQUIRED:" -ForegroundColor Yellow
Write-Host "This will open your browser for Google OAuth authentication" -ForegroundColor White
Write-Host "You need to:" -ForegroundColor White
Write-Host "  1. Sign in with your Google account" -ForegroundColor White
Write-Host "  2. Grant permissions for Colab and Drive" -ForegroundColor White
Write-Host "  3. Close the browser tab when done" -ForegroundColor White
Write-Host ""

$confirmation = Read-Host "Ready to authenticate with Google? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Change to CLI directory and run authentication
Write-Host "🔄 Starting authentication..." -ForegroundColor Blue
Push-Location $cliPath

try {
    # Run authentication
    Write-Host "Opening browser for Google authentication..." -ForegroundColor Cyan
    $authCommand = "npx tsx src/index.ts connect --new-runtime"
    Write-Host "Running: $authCommand" -ForegroundColor Gray

    # This will open browser for auth and connect to Colab
    Invoke-Expression $authCommand

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Authentication failed" -ForegroundColor Red
        exit 1
    }

    Write-Host "✅ Authentication successful!" -ForegroundColor Green

} catch {
    Write-Host "✗ Authentication error: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}

Pop-Location

Write-Host ""
Write-Host "📤 UPLOADING DEPLOYMENT SCRIPT..." -ForegroundColor Cyan

# Upload the deployment script to Colab
Push-Location $cliPath
try {
    $uploadCommand = "npx tsx src/index.ts copy ..\\$deploymentScript /content/$deploymentScript"
    Write-Host "Running: $uploadCommand" -ForegroundColor Gray

    Invoke-Expression $uploadCommand

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Upload failed" -ForegroundColor Red
        exit 1
    }

    Write-Host "✅ Deployment script uploaded!" -ForegroundColor Green

} catch {
    Write-Host "✗ Upload error: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host ""
Write-Host "🚀 STARTING DEPLOYMENT..." -ForegroundColor Green

# Run the deployment script on Colab
Push-Location $cliPath
try {
    $runCommand = "npx tsx src/index.ts run --mode kernel 'exec(open(\`"$deploymentScript\`").read())'"
    Write-Host "Running: $runCommand" -ForegroundColor Gray
    Write-Host ""
    Write-Host "DEPLOYMENT OUTPUT:" -ForegroundColor Cyan
    Write-Host "=" * 30 -ForegroundColor Cyan

    # This will execute the Python deployment script
    Invoke-Expression $runCommand

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Deployment failed" -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "✅ DEPLOYMENT COMPLETED!" -ForegroundColor Green

} catch {
    Write-Host "✗ Deployment error: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host ""
Write-Host "🎯 DEPLOYMENT RESULTS:" -ForegroundColor Cyan
Write-Host "Check the output above for:" -ForegroundColor White
Write-Host "  • Service URLs and access points" -ForegroundColor White
Write-Host "  • ngrok tunnel addresses" -ForegroundColor White
Write-Host "  • Dashboard access information" -ForegroundColor White
Write-Host ""
Write-Host "Your Agentic Framework is now running on Google Colab GPU!" -ForegroundColor Green
Write-Host "All services are deployed and accessible via the provided URLs." -ForegroundColor White