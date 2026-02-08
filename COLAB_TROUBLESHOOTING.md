# Colab Deployment Troubleshooting Guide

## 🔍 Smoke Test Failed - Quick Fixes

Your smoke test shows these results:
- ✅ **PASS**: SubAgent Manager, Ollama LLM, LLM Inference
- ❌ **FAIL**: Orchestrator, Memory Service, MCP Gateway, Code Executor

### 🚀 Quick Recovery Steps

#### Step 1: Check Service Logs
Run this in a Colab cell:
```python
!tail -20 /tmp/orchestrator.log
!tail -20 /tmp/memory_service.log
!tail -20 /tmp/mcp_gateway.log
!tail -20 /tmp/code_exec.log
```

#### Step 2: Check What's Running
```python
!ps aux | grep uvicorn
!netstat -tuln | grep -E ':(8000|8002|8004|8080) '
```

#### Step 3: Restart Failed Services
Copy the code from `colab_recovery_cell.py` into a new Colab cell and run it. It will:
- Kill zombie processes
- Restart failed services
- Verify they started correctly

#### Step 4: Re-run Smoke Test
After waiting 10-15 seconds, re-run the smoke test cell.

---

## 🛠️ Common Issues & Fixes

### Issue 1: "Connection refused" (Port 111 error)
**Cause**: Service never started or crashed immediately

**Fix**:
```python
# Check if Python packages are installed
!pip list | grep fastapi
!pip list | grep uvicorn

# If missing, reinstall requirements
!pip install -r /content/ai_final/agentic-framework-main/requirements.txt
```

### Issue 2: "HTTP Error 404" (MCP Gateway)
**Cause**: Service is running but /health endpoint doesn't exist

**Fix**: MCP Gateway might use a different health check endpoint
```python
import urllib.request
try:
    # Try root endpoint
    urllib.request.urlopen("http://localhost:8080/", timeout=5)
    print("MCP Gateway is running!")
except Exception as e:
    print(f"Error: {e}")
```

### Issue 3: Import Errors in Logs
**Fix**:
```python
# Check PYTHONPATH
import os
print("PYTHONPATH:", os.environ.get('PYTHONPATH'))

# Set it if missing
os.environ['PYTHONPATH'] = '/content/ai_final/agentic-framework-main'

# Restart services after setting PYTHONPATH
```

### Issue 4: Database Connection Errors
**Fix**:
```python
# Check PostgreSQL
!pg_isready -h localhost -p 5432

# Restart if needed
!sudo service postgresql restart
!sleep 3
!pg_isready -h localhost -p 5432
```

### Issue 5: Redis Connection Errors
**Fix**:
```python
# Check Redis
!redis-cli ping

# Start if needed
!redis-server --daemonize yes
!sleep 2
!redis-cli ping
```

---

## 📋 Full Diagnostic Report

Run this for a complete diagnostic:
```python
!python /content/ai_final/colab_diagnostics.py
```

---

## 🔄 Nuclear Option: Full Restart

If nothing else works:
```python
# 1. Kill all services
!pkill -f uvicorn
!pkill -f ollama

# 2. Wait
import time
time.sleep(5)

# 3. Re-run deployment from Cell 3 (Phase 4 - Start Services)
# Skip the installation cells, just restart the services
```

---

## 💡 Prevention Tips

1. **Wait longer**: Services can take 30-60 seconds to fully initialize
2. **Check Colab resources**: Runtime > View resources (need GPU & enough RAM)
3. **One cell at a time**: Don't run all cells quickly - let services start
4. **Monitor logs**: Keep an eye on `/tmp/*.log` files for errors

---

## 📞 Still Having Issues?

Check these in order:
1. Colab runtime type: **Must be GPU (T4 or better)**
2. Colab connection: **Must show "Connected" with RAM/Disk available**
3. All logs: Look for **Python tracebacks** or **import errors**
4. Restart runtime: **Runtime > Restart runtime** and re-run from beginning

---

## ✅ Success Indicators

All services should show:
```
[PASS] Orchestrator API
[PASS] Memory Service  
[PASS] SubAgent Manager
[PASS] MCP Gateway
[PASS] Code Executor
[PASS] Ollama LLM

Results: 7/7 passed
ALL SYSTEMS GO!
```
