# Pure Colab CLI Setup Script
# This script helps you set up authentication for the pure CLI deployment

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiKey,
    [Parameter(Mandatory=$false)]
    [string]$ServiceAccountPath,
    [switch]$TestAuth
)

Write-Host "🔧 Pure Colab CLI Setup" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check if required packages are installed
Write-Host "📦 Checking required packages..." -ForegroundColor Yellow
try {
    python -c "import googleapiclient; import google.auth" 2>$null
    Write-Host "✅ Google API client libraries installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Google API client libraries not found. Installing..." -ForegroundColor Red
    pip install google-api-python-client google-auth-httplib2
}

# Authentication setup
if ($ApiKey) {
    Write-Host "🔑 Setting up API Key authentication..." -ForegroundColor Yellow
    $env:GOOGLE_API_KEY = $ApiKey
    Write-Host "✅ API Key set" -ForegroundColor Green
} elseif ($ServiceAccountPath) {
    Write-Host "🔑 Setting up Service Account authentication..." -ForegroundColor Yellow
    if (Test-Path $ServiceAccountPath) {
        Copy-Item $ServiceAccountPath "colab-service-account.json" -Force
        Write-Host "✅ Service account JSON copied to colab-service-account.json" -ForegroundColor Green
    } else {
        Write-Host "❌ Service account file not found at: $ServiceAccountPath" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "🔍 Checking for existing authentication..." -ForegroundColor Yellow

    # Check for service account file
    if (Test-Path "colab-service-account.json") {
        Write-Host "✅ Found service account file: colab-service-account.json" -ForegroundColor Green
    } elseif ($env:GOOGLE_API_KEY) {
        Write-Host "✅ Found API key in environment" -ForegroundColor Green
    } else {
        Write-Host "❌ No authentication found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please provide authentication using one of these methods:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Method 1 - Service Account (Recommended):" -ForegroundColor Cyan
        Write-Host "  .\setup-colab-cli.ps1 -ServiceAccountPath 'path\to\service-account.json'" -ForegroundColor White
        Write-Host ""
        Write-Host "Method 2 - API Key:" -ForegroundColor Cyan
        Write-Host "  .\setup-colab-cli.ps1 -ApiKey 'your-api-key-here'" -ForegroundColor White
        Write-Host ""
        Write-Host "For detailed setup instructions, see: PURE_COLAB_CLI_README.md" -ForegroundColor Magenta
        exit 1
    }
}

# Test authentication if requested
if ($TestAuth) {
    Write-Host "🧪 Testing authentication..." -ForegroundColor Yellow
    try {
        python -c "
import os
import google.auth
from googleapiclient.discovery import build

# Test authentication
if os.path.exists('colab-service-account.json'):
    creds, project = google.auth.load_credentials_from_file('colab-service-account.json')
    print('✅ Service account authentication successful')
elif os.environ.get('GOOGLE_API_KEY'):
    # Test API key
    service = build('colab', 'v1', developerKey=os.environ['GOOGLE_API_KEY'])
    print('✅ API key authentication successful')
else:
    print('❌ No valid authentication found')
    exit(1)
        "
        Write-Host "✅ Authentication test passed!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Authentication test failed!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🎉 Setup complete! You can now run:" -ForegroundColor Green
Write-Host "   .\pure_colab_cli.ps1" -ForegroundColor White
Write-Host ""
Write-Host "For help, see: PURE_COLAB_CLI_README.md" -ForegroundColor Magenta