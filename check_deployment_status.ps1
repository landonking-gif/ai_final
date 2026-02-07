# Agentic Framework - CLI Status Check
# Check deployment status and get access URLs

Write-Host "📊 Agentic Framework - CLI Status Check" -ForegroundColor Green
Write-Host "=" * 40 -ForegroundColor Cyan

$cliPath = "LeCoder-cgpu-CLI"
if (!(Test-Path $cliPath)) {
    Write-Host "✗ LeCoder CLI not found" -ForegroundColor Red
    exit 1
}

Push-Location $cliPath

try {
    Write-Host "🔄 Checking Colab session status..." -ForegroundColor Blue
    $statusCommand = "npx tsx src/index.ts status"
    Invoke-Expression $statusCommand

    Write-Host ""
    Write-Host "📋 To check deployment output, run:" -ForegroundColor Cyan
    Write-Host "npx tsx src/index.ts run 'cat /content/deployment_output.log'" -ForegroundColor White

    Write-Host ""
    Write-Host "🌐 To get service URLs, run:" -ForegroundColor Cyan
    Write-Host "npx tsx src/index.ts run 'echo \"=== SERVICE URLS ===\" && ps aux | grep -E \"(ollama|postgres|redis|minio|ngrok)\" | grep -v grep'" -ForegroundColor White

} catch {
    Write-Host "✗ Status check failed: $_" -ForegroundColor Red
} finally {
    Pop-Location
}