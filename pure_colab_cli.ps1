# Pure Colab CLI - Execute deployment entirely from VS Code
# Uses Google Colab API directly with service account authentication

Write-Host "🚀 Pure Colab CLI - No Browser Interaction" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Cyan

# Check if Python is available
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check if required packages are installed
Write-Host "🔍 Checking dependencies..." -ForegroundColor Blue
try {
    $pythonCmd = 'import googleapiclient; import google.auth'
    python -c $pythonCmd 2>$null
    Write-Host "✅ Google API client installed" -ForegroundColor Green
} catch {
    Write-Host "Installing Google API client..." -ForegroundColor Yellow
    pip install google-api-python-client google-auth-httplib2
}

# Check for authentication
Write-Host "🔐 Checking authentication..." -ForegroundColor Blue
$serviceAccountPath = Join-Path $PSScriptRoot "colab-service-account.json"
$hasServiceAccount = Test-Path $serviceAccountPath
$hasApiKey = $env:GOOGLE_API_KEY

if (!$hasServiceAccount -and !$hasApiKey) {
    Write-Host "❌ No authentication method found" -ForegroundColor Red
    Write-Host "" -ForegroundColor White
    Write-Host "SETUP REQUIRED:" -ForegroundColor Cyan
    Write-Host "Choose one authentication method:" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "Method 1 - Service Account (Recommended):" -ForegroundColor Green
    Write-Host "  1. Go to Google Cloud Console: https://console.cloud.google.com/" -ForegroundColor White
    Write-Host "  2. Create a new project or select existing" -ForegroundColor White
    Write-Host "  3. Enable Colab API: APIs & Services > Library > Search 'Colab'" -ForegroundColor White
    Write-Host "  4. Create Service Account: IAM & Admin > Service Accounts" -ForegroundColor White
    Write-Host "  5. Download JSON key and save as 'colab-service-account.json'" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "Method 2 - API Key:" -ForegroundColor Green
    Write-Host "  1. Go to Google Cloud Console" -ForegroundColor White
    Write-Host "  2. APIs & Services > Credentials > Create Credentials > API Key" -ForegroundColor White
    Write-Host "  3. Set environment variable: `$env:GOOGLE_API_KEY = 'your-api-key'" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "After setup, run this script again." -ForegroundColor Yellow
    exit 1
}

if ($hasServiceAccount) {
    Write-Host "✅ Service account key found" -ForegroundColor Green
} elseif ($hasApiKey) {
    Write-Host "✅ API key found" -ForegroundColor Green
}

Write-Host "" -ForegroundColor White
Write-Host "🎯 STARTING PURE CLI DEPLOYMENT" -ForegroundColor Green
Write-Host "This will execute entirely in VS Code - no browser required!" -ForegroundColor White
Write-Host "" -ForegroundColor White

$confirmation = Read-Host "Ready to start deployment? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Run the Python CLI
Write-Host "🚀 Executing deployment..." -ForegroundColor Blue
try {
    python pure_colab_cli.py
    Write-Host "" -ForegroundColor White
    Write-Host "✅ CLI execution completed!" -ForegroundColor Green
} catch {
    Write-Host "❌ CLI execution failed: $_" -ForegroundColor Red
    Write-Host "" -ForegroundColor White
    Write-Host "TROUBLESHOOTING:" -ForegroundColor Cyan
    Write-Host "1. Check your authentication setup" -ForegroundColor White
    Write-Host "2. Ensure Colab API is enabled in Google Cloud" -ForegroundColor White
    Write-Host "3. Verify your service account has proper permissions" -ForegroundColor White
    Write-Host "4. Try using an API key instead" -ForegroundColor White
    exit 1
}

Write-Host "" -ForegroundColor White
Write-Host "🎉 DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "Your Agentic Framework is now running on Google Colab GPU!" -ForegroundColor White
Write-Host "Check the output above for service URLs and access information." -ForegroundColor White