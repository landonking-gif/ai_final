# Automated Agentic Framework Colab Deployment using LeCoder CLI
# This script uses the LeCoder CLI to programmatically deploy the Agentic Framework to Google Colab

Write-Host "Starting automated Agentic Framework deployment to Google Colab..." -ForegroundColor Green

# Check if CLI is available
try {
    $cliVersion = & npx tsx "LeCoder-cgpu-CLI\src\index.ts" --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "CLI not available"
    }
    Write-Host "LeCoder CLI v$cliVersion is available" -ForegroundColor Green
} catch {
    Write-Host "LeCoder CLI is not properly installed. Please run the installation first." -ForegroundColor Red
    exit 1
}

# Check if deployment script exists
$deploymentScriptPath = "colab_deployment.py"
if (!(Test-Path $deploymentScriptPath)) {
    Write-Host "Deployment script not found at $deploymentScriptPath" -ForegroundColor Red
    exit 1
}
Write-Host "Deployment script found" -ForegroundColor Green

# Read the Python deployment script
try {
    $deploymentCode = Get-Content $deploymentScriptPath -Raw
    Write-Host "Deployment code loaded" -ForegroundColor Green
} catch {
    Write-Host "Failed to read deployment script: $_" -ForegroundColor Red
    exit 1
}

# Create a new GPU notebook
Write-Host "Creating new GPU-enabled Colab notebook..." -ForegroundColor Blue
try {
    $createCommand = "npx tsx LeCoder-cgpu-CLI\src\index.ts notebook create agentic-framework-deploy-cli --template gpu --json"
    $createOutput = Invoke-Expression $createCommand

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create notebook: $createOutput"
    }

    Write-Host "Notebook creation output: $createOutput" -ForegroundColor White

    # Try to extract notebook ID from output
    $notebookId = $null
    if ($createOutput -match 'id["\s:]+([^"\s,]+)') {
        $notebookId = $matches[1]
        Write-Host "Created notebook with ID: $notebookId" -ForegroundColor Green
    } else {
        Write-Host "Could not extract notebook ID from output" -ForegroundColor Yellow
        # Continue anyway, might still work
        $notebookId = "unknown"
    }
} catch {
    Write-Host "Failed to create notebook: $_" -ForegroundColor Red
    Write-Host "This requires Google OAuth authentication. I need help with:" -ForegroundColor Yellow
    Write-Host "1. Google Cloud Console access to create OAuth credentials" -ForegroundColor White
    Write-Host "2. Or an alternative authentication method" -ForegroundColor White
    Write-Host "3. Or help setting up the OAuth flow interactively" -ForegroundColor White
    exit 1
}

# Execute the deployment script in the notebook
Write-Host "Executing deployment script in Colab notebook..." -ForegroundColor Blue
try {
    # Use a temporary file to avoid command line length limits
    $tempScriptPath = [System.IO.Path]::GetTempFileName() + ".py"
    $deploymentCode | Out-File -FilePath $tempScriptPath -Encoding UTF8

    $runCommand = "npx tsx LeCoder-cgpu-CLI\src\index.ts run --mode kernel --verbose `"< $tempScriptPath`""
    Write-Host "Running: $runCommand" -ForegroundColor Gray

    $runOutput = Invoke-Expression $runCommand

    # Clean up temp file
    Remove-Item $tempScriptPath -ErrorAction SilentlyContinue

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to execute deployment script: $runOutput"
    }

    Write-Host "Deployment script executed successfully!" -ForegroundColor Green
    Write-Host "Output:" -ForegroundColor Cyan
    Write-Host $runOutput
} catch {
    Write-Host "Failed to execute deployment script: $_" -ForegroundColor Red
    exit 1
}

# Open the notebook in browser
Write-Host "Opening notebook in Google Colab..." -ForegroundColor Blue
try {
    if ($notebookId -and $notebookId -ne "unknown") {
        $openCommand = "npx tsx LeCoder-cgpu-CLI\src\index.ts notebook open $notebookId"
        $openOutput = Invoke-Expression $openCommand

        if ($LASTEXITCODE -eq 0) {
            Write-Host "Notebook opened successfully!" -ForegroundColor Green
        } else {
            Write-Host "Could not open notebook automatically" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Skipping notebook open - no valid notebook ID" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not open notebook automatically" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Automated deployment complete!" -ForegroundColor Green
Write-Host "Check the Colab notebook for deployment status and access your services." -ForegroundColor White
Write-Host "Your Agentic Framework is now running on Google Colab GPU!" -ForegroundColor White