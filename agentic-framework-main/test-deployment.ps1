# Agentic Framework Deployment Test
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Agentic Framework Deployment Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

[string]$ip = "34.229.112.127"
$tests = 0
$passed = 0

# Test Health Endpoints
Write-Host "[1] Health Endpoints" -ForegroundColor Blue
try {
    $url = "http://$($ip):8000/health"
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) { Write-Host "  ✓ Orchestrator" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ Orchestrator" -ForegroundColor Red }
    $tests++
} catch { Write-Host "  ✗ Orchestrator: $($_.Exception.Message)" -ForegroundColor Red; $tests++ }

try {
    $url = "http://$($ip):8002/health"
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) { Write-Host "  ✓ Memory Service" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ Memory Service" -ForegroundColor Red }
    $tests++
} catch { Write-Host "  ✗ Memory Service: $($_.Exception.Message)" -ForegroundColor Red; $tests++ }

try {
    $url = "http://$($ip):8003/health"
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) { Write-Host "  ✓ Subagent Manager" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ Subagent Manager" -ForegroundColor Red }
    $tests++
} catch { Write-Host "  ✗ Subagent Manager: $($_.Exception.Message)" -ForegroundColor Red; $tests++ }

try {
    $url = "http://$($ip):8080/health"
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) { Write-Host "  ✓ MCP Gateway" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ MCP Gateway" -ForegroundColor Red }
    $tests++
} catch { Write-Host "  ✗ MCP Gateway: $($_.Exception.Message)" -ForegroundColor Red; $tests++ }

# Test API Documentation
Write-Host "`n[2] API Documentation" -ForegroundColor Blue
try {
    $url = "http://$($ip):8000/docs"
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) { Write-Host "  ✓ OpenAPI Docs" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ OpenAPI Docs" -ForegroundColor Red }
    $tests++
} catch { Write-Host "  ✗ OpenAPI Docs: $($_.Exception.Message)" -ForegroundColor Red; $tests++ }

# Test Redis
Write-Host "`n[3] Redis Connectivity" -ForegroundColor Blue
$redisTest = ssh -i "c:\Users\dmilner.AGV-040318-PC\Downloads\landon\ai_final\king-ai-studio.pem" -o StrictHostKeyChecking=no ubuntu@$ip "sudo docker exec agentic-framework-redis-1 redis-cli -a redis_pass_2024 ping 2>/dev/null"
if ($redisTest -eq "PONG") { Write-Host "  ✓ Redis PING" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ Redis PING" -ForegroundColor Red }
$tests++

# Test PostgreSQL
Write-Host "`n[4] PostgreSQL Connectivity" -ForegroundColor Blue
$pgTest = ssh -i "c:\Users\dmilner.AGV-040318-PC\Downloads\landon\ai_final\king-ai-studio.pem" -o StrictHostKeyChecking=no ubuntu@$ip "sudo docker exec agentic-framework-postgres-1 pg_isready -U postgres 2>&1"
if ($pgTest -match "accepting connections") { Write-Host "  ✓ PostgreSQL" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ PostgreSQL" -ForegroundColor Red }
$tests++

# Test Service Integration
Write-Host "`n[5] Service Integration" -ForegroundColor Blue
try {url = "http://$($ip):8000/health"
    $health = Invoke-RestMethod -Uri $url
    $health = Invoke-RestMethod "http://$ip:8000/health" -UseBasicParsing
    if ($health.dependencies.mcp_gateway -eq "healthy") { Write-Host "  ✓ MCP Gateway Integration" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ MCP Gateway Integration" -ForegroundColor Red }
    $tests++
    if ($health.dependencies.memory_service -eq "healthy") { Write-Host "  ✓ Memory Service Integration" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ Memory Service Integration" -ForegroundColor Red }
    $tests++
    if ($health.dependencies.subagent_manager -eq "healthy") { Write-Host "  ✓ Subagent Manager Integration" -ForegroundColor Green; $passed++ } else { Write-Host "  ✗ Subagent Manager Integration" -ForegroundColor Red }
    $tests++
} catch {
    Write-Host "  ✗ Service Integration Failed" -ForegroundColor Red
    $tests += 3
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Results: $passed/$tests passed" -ForegroundColor $(if ($passed -eq $tests) { "Green" } else { "Yellow" })
Write-Host "========================================" -ForegroundColor Cyan

if ($passed -eq $tests) {
    Write-Host "`n✅ ALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "`nDeployment URL: http://$ip:8000/docs`n" -ForegroundColor Cyan
} else {
    Write-Host "`n⚠ Some tests failed" -ForegroundColor Yellow
    Write-Host "Check logs: ssh ubuntu@$ip 'sudo docker compose logs'`n" -ForegroundColor Gray
}
