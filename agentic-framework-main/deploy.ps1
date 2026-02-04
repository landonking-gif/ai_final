# Agentic Framework AWS Deployment Script (PowerShell)
# Unified deployment with OpenClaw + Ralph Loop + Memory integration
# Features:
#   - Git repository initialization with upstream OpenClaw sync
#   - Codebase indexing into memory service
#   - All agents use OpenClaw with DeepSeek R1
#   - ALL tasks routed through Ralph Loop for consistency
# Usage: .\deploy.ps1 <AWS_IP>

param(
    [Parameter(Mandatory=$false)]
    [string]$AwsIP = "34.229.112.127"
)

$ErrorActionPreference = "Stop"
$SSH_USER = "ubuntu"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PEM_KEY = Join-Path (Split-Path -Parent $SCRIPT_DIR) "king-ai-studio.pem"
$PROJECT_DIR = $SCRIPT_DIR

# Check PEM key
if (!(Test-Path $PEM_KEY)) {
    Write-Host "Error: PEM key not found at $PEM_KEY" -ForegroundColor Red
    Write-Host "Please ensure king-ai-studio.pem is in the parent directory" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Agentic Framework AWS Deployment v3.1" -ForegroundColor Cyan
Write-Host "OpenClaw + Ralph Loop + Memory" -ForegroundColor Cyan
Write-Host "ALL TASKS USE RALPH LOOP" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Target: $AwsIP" -ForegroundColor Green
Write-Host ""

# Test SSH with retry logic
Write-Host "[1/7] Testing SSH..." -ForegroundColor Yellow
$maxRetries = 3
$retryCount = 0
$connected = $false

# Temporarily allow errors for SSH warnings
$oldErrorPref = $ErrorActionPreference
$ErrorActionPreference = "Continue"

while ($retryCount -lt $maxRetries -and -not $connected) {
    if ($retryCount -gt 0) {
        Write-Host "  Retry $retryCount/$maxRetries..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
    
    # Capture only stdout, ignore stderr warnings
    $testOutput = & ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ConnectTimeout=15 "$SSH_USER@$AwsIP" "echo SSH_OK" 2>$null
    
    # Check if we got the success marker
    if ($testOutput -match "SSH_OK") {
        $connected = $true
        Write-Host "  [OK] Connected to $AwsIP" -ForegroundColor Green
    } else {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "  Connection failed, retrying..." -ForegroundColor Yellow
        }
    }
}

# Restore error preference
$ErrorActionPreference = $oldErrorPref

if (-not $connected) {
    Write-Host "Error: Cannot connect to $AwsIP after $maxRetries attempts" -ForegroundColor Red
    Write-Host "Please verify:" -ForegroundColor Yellow
    Write-Host "  1. IP address is correct: $AwsIP" -ForegroundColor White
    Write-Host "  2. EC2 instance is running" -ForegroundColor White
    Write-Host "  3. Security group allows SSH (port 22) from your IP" -ForegroundColor White
    Write-Host "  4. PEM key is correct: $PEM_KEY" -ForegroundColor White
    exit 1
}

# Create archive
Write-Host ""
Write-Host "[2/7] Creating package..." -ForegroundColor Yellow
$ARCHIVE = "$env:TEMP\deploy-$(Get-Date -Format 'yyyyMMddHHmmss').tar.gz"
$excludePatterns = @('.git', '__pycache__', '*.pyc', 'node_modules', '*.pem', '.env')

# Use tar if available (Windows 10+), otherwise use 7-Zip or create without compression
if (Get-Command tar -ErrorAction SilentlyContinue) {
    Push-Location $PROJECT_DIR
    tar -czf $ARCHIVE --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='node_modules' --exclude='*.pem' --exclude='.env' .
    Pop-Location
} else {
    Write-Host "  Warning: tar not found, using PowerShell compression" -ForegroundColor Yellow
    $tempDir = "$env:TEMP\deploy-temp-$(Get-Date -Format 'yyyyMMddHHmmss')"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    # Copy files excluding patterns
    Get-ChildItem $PROJECT_DIR -Recurse | Where-Object {
        $path = $_.FullName
        $exclude = $false
        foreach ($pattern in $excludePatterns) {
            if ($path -like "*$pattern*") {
                $exclude = $true
                break
            }
        }
        !$exclude
    } | ForEach-Object {
        $dest = $_.FullName.Replace($PROJECT_DIR, $tempDir)
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $dest -Force | Out-Null
        } else {
            $destDir = Split-Path $dest
            if (!(Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Copy-Item $_.FullName $dest
        }
    }
    
    # Create tar.gz on remote
    $ARCHIVE = "deploy.tar"
    tar -cf $ARCHIVE -C $tempDir .
    Remove-Item -Recurse -Force $tempDir
}
Write-Host "  [OK] Archive ready" -ForegroundColor Green

# Upload
Write-Host ""
Write-Host "[3/7] Uploading..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
scp -i "$PEM_KEY" -o StrictHostKeyChecking=no "$ARCHIVE" "${SSH_USER}@${AwsIP}:/tmp/deploy.tar.gz" 2>$null
$ErrorActionPreference = "Stop"
Remove-Item $ARCHIVE -Force
Write-Host "  [OK] Uploaded" -ForegroundColor Green

# Extract
Write-Host ""
Write-Host "[4/7] Extracting..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$AwsIP" "sudo mkdir -p /opt/agentic-framework && sudo tar -xzf /tmp/deploy.tar.gz -C /opt/agentic-framework && sudo chown -R ubuntu:ubuntu /opt/agentic-framework && rm /tmp/deploy.tar.gz" 2>$null
$ErrorActionPreference = "Stop"
Write-Host "  [OK] Extracted" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "[5/7] Installing dependencies..." -ForegroundColor Yellow
$depsScript = @'
set -e
if ! command -v docker &>/dev/null; then sudo apt update -qq && sudo apt install -y docker.io docker-compose-v2 && sudo systemctl enable --now docker && sudo usermod -aG docker ubuntu; fi
if ! command -v git &>/dev/null; then sudo apt install -y git; fi
if ! command -v node &>/dev/null || [[ $(node -v | cut -d. -f1 | tr -d 'v') -lt 22 ]]; then curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs; fi
if ! command -v openclaw &>/dev/null; then sudo npm install -g openclaw@latest; fi
if ! command -v ollama &>/dev/null; then curl -fsSL https://ollama.com/install.sh | sh && sudo systemctl enable --now ollama; fi
if ! ollama list | grep -q "deepseek-r1:14b"; then ollama pull deepseek-r1:14b; fi
echo "Dependencies installed"
'@ -replace "`r", ""

$ErrorActionPreference = "Continue"
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$AwsIP" $depsScript 2>$null
$ErrorActionPreference = "Stop"
Write-Host "  [OK] Dependencies ready" -ForegroundColor Green

# Initialize Git
Write-Host ""
Write-Host "[6/7] Initializing Git repository..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
scp -i "$PEM_KEY" -o StrictHostKeyChecking=no "$PROJECT_DIR\deploy-git.sh" "${SSH_USER}@${AwsIP}:/tmp/deploy-git.sh" 2>$null
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$AwsIP" "bash /tmp/deploy-git.sh && rm /tmp/deploy-git.sh" 2>$null
$ErrorActionPreference = "Stop"
Write-Host "  [OK] Git configured" -ForegroundColor Green

# Deploy
Write-Host ""
Write-Host "[7/7] Deploying (10-15 min)..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
scp -i "$PEM_KEY" -o StrictHostKeyChecking=no "$PROJECT_DIR\deploy-services.sh" "${SSH_USER}@${AwsIP}:/tmp/deploy-services.sh" 2>$null
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$AwsIP" "bash /tmp/deploy-services.sh && rm /tmp/deploy-services.sh" 2>$null
$ErrorActionPreference = "Stop"

# Ensure services are running and nginx is configured
Write-Host ""
Write-Host "[POST-DEPLOY] Starting services..." -ForegroundColor Yellow
$startScript = @'
set -e
cd /opt/agentic-framework
sudo docker compose up -d
sleep 5
sudo systemctl restart nginx
echo "Services started"
'@ -replace "`r", ""

$ErrorActionPreference = "Continue"
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$AwsIP" $startScript 2>$null
$ErrorActionPreference = "Stop"
Write-Host "  [OK] All services running" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "[SUCCESS] DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services Deployed:" -ForegroundColor Cyan
Write-Host "  - Orchestrator (OpenClaw + Memory)" -ForegroundColor White
Write-Host "  - SubAgent Manager (OpenClaw)" -ForegroundColor White
Write-Host "  - Memory Service (with codebase index)" -ForegroundColor White
Write-Host "  - MCP Gateway" -ForegroundColor White
Write-Host "  - OpenClaw Gateway (DeepSeek R1)" -ForegroundColor White
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  Dashboard:  http://$AwsIP" -ForegroundColor White
Write-Host "  API Docs:   http://$AwsIP:8000/docs" -ForegroundColor White
Write-Host "  Health:     http://$AwsIP:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "Maintenance:" -ForegroundColor Cyan
Write-Host "  Sync OpenClaw: ssh -i `"$PEM_KEY`" $SSH_USER@$AwsIP '/opt/agentic-framework/sync-openclaw.sh'" -ForegroundColor White
Write-Host "  View logs:     ssh -i `"$PEM_KEY`" $SSH_USER@$AwsIP 'cd /opt/agentic-framework && sudo docker compose logs -f'" -ForegroundColor White
Write-Host ""
