# Hotfix deployment - only update agent.py file
$ErrorActionPreference = "Stop"

$HOST_IP = "34.229.112.127"
$KEY_FILE = "$env:USERPROFILE\.ssh\aws-ec2-key.pem"
$REMOTE_USER = "ubuntu"

Write-Host "Starting hotfix deployment..." -ForegroundColor Cyan

# Copy the fixed agent.py file
Write-Host "`nUploading fixed agent.py..." -ForegroundColor Yellow
scp -i $KEY_FILE -o StrictHostKeyChecking=no `
    "c:\Users\dmilner.AGV-040318-PC\Downloads\landon\ai_final\agentic-framework-main\orchestrator\service\agent.py" `
    "${REMOTE_USER}@${HOST_IP}:/home/ubuntu/agentic-framework/orchestrator/service/agent.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to upload agent.py" -ForegroundColor Red
    exit 1
}

Write-Host "`nRebuilding orchestrator container..." -ForegroundColor Yellow
ssh -i $KEY_FILE -o StrictHostKeyChecking=no "${REMOTE_USER}@${HOST_IP}" @"
cd /home/ubuntu/agentic-framework
docker compose build orchestrator
docker compose up -d orchestrator
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to rebuild/restart orchestrator" -ForegroundColor Red
    exit 1
}

Write-Host "`nWaiting for orchestrator to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Test the fix
Write-Host "`nTesting orchestrator health..." -ForegroundColor Yellow
$health = Invoke-WebRequest -Uri "http://${HOST_IP}:8000/health" -UseBasicParsing -TimeoutSec 5
Write-Host "Health check: $($health.StatusCode)" -ForegroundColor Green

Write-Host "`n✅ Hotfix deployment complete!" -ForegroundColor Green
Write-Host "The orchestrator has been updated and restarted." -ForegroundColor Cyan
