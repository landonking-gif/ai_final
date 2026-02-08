#!/usr/bin/env python3
"""
Colab Deployment Diagnostics & Recovery
Run this in your Colab notebook to diagnose and fix failed services
"""

import subprocess
import os
import sys
import time

FRAMEWORK_DIR = "/content/ai_final/agentic-framework-main"

SERVICE_DEFS = [
    {"name": "Orchestrator",     "module": "orchestrator.service.main:app",     "port": 8000, "log": "/tmp/orchestrator.log"},
    {"name": "Memory Service",   "module": "memory_service.service.main:app",   "port": 8002, "log": "/tmp/memory_service.log"},
    {"name": "SubAgent Manager", "module": "subagent_manager.service.main:app", "port": 8003, "log": "/tmp/subagent_manager.log"},
    {"name": "MCP Gateway",      "module": "mcp_gateway.service.main:app",      "port": 8080, "log": "/tmp/mcp_gateway.log"},
    {"name": "Code Executor",    "module": "code_exec.service.main:app",        "port": 8004, "log": "/tmp/code_exec.log"},
]

print("=" * 70)
print("COLAB DEPLOYMENT DIAGNOSTICS")
print("=" * 70)

# Check if processes are running
print("\n1. Checking Running Processes:")
print("-" * 70)
for svc in SERVICE_DEFS:
    result = subprocess.run(
        f"ps aux | grep '{svc['module']}' | grep -v grep",
        shell=True,
        capture_output=True,
        text=True
    )
    if result.stdout.strip():
        print(f"  ✅ {svc['name']:20s} - RUNNING")
    else:
        print(f"  ❌ {svc['name']:20s} - NOT RUNNING")

# Check ports
print("\n2. Checking Port Availability:")
print("-" * 70)
for svc in SERVICE_DEFS:
    result = subprocess.run(
        f"netstat -tuln | grep ':{svc['port']} ' || lsof -i :{svc['port']} 2>/dev/null",
        shell=True,
        capture_output=True,
        text=True
    )
    if result.stdout.strip():
        print(f"  ✅ Port {svc['port']:5d} - IN USE ({svc['name']})")
    else:
        print(f"  ❌ Port {svc['port']:5d} - FREE (service not listening)")

# Check log files
print("\n3. Checking Service Logs (last 10 lines):")
print("-" * 70)
for svc in SERVICE_DEFS:
    if os.path.exists(svc['log']):
        print(f"\n  📄 {svc['name']} ({svc['log']}):")
        result = subprocess.run(
            f"tail -10 {svc['log']}",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                print(f"     {line}")
        else:
            print("     (empty log)")
    else:
        print(f"\n  ⚠️  {svc['name']} - LOG FILE NOT FOUND")

# Check dependencies
print("\n4. Checking Dependencies:")
print("-" * 70)
deps = [
    ("PostgreSQL", "pg_isready -h localhost -p 5432"),
    ("Redis", "redis-cli ping"),
    ("Ollama", "curl -s http://localhost:11434/api/tags >/dev/null && echo PONG || echo FAIL"),
]
for name, cmd in deps:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if "PONG" in result.stdout or result.returncode == 0:
        print(f"  ✅ {name:15s} - OK")
    else:
        print(f"  ❌ {name:15s} - FAIL")

# Check environment
print("\n5. Checking Environment Variables:")
print("-" * 70)
env_vars = [
    "POSTGRES_URL",
    "REDIS_URL",
    "OLLAMA_ENDPOINT",
    "PYTHONPATH"
]
for var in env_vars:
    value = os.environ.get(var, "(not set)")
    print(f"  {var:20s} = {value}")

print("\n" + "=" * 70)
print("RECOVERY ACTIONS")
print("=" * 70)

print("\nTo restart failed services, run these commands in separate cells:\n")

for svc in SERVICE_DEFS:
    result = subprocess.run(
        f"ps aux | grep '{svc['module']}' | grep -v grep",
        shell=True,
        capture_output=True,
        text=True
    )
    if not result.stdout.strip():
        print(f"# Restart {svc['name']}")
        print(f"import subprocess, sys, os")
        print(f"subprocess.Popen([")
        print(f"    sys.executable, '-m', 'uvicorn', '{svc['module']}',")
        print(f"    '--host', '0.0.0.0', '--port', '{svc['port']}'")
        print(f"], cwd='/content/ai_final/agentic-framework-main',")
        print(f"   stdout=open('{svc['log']}', 'w'),")
        print(f"   stderr=subprocess.STDOUT)")
        print(f"print('Started {svc['name']} on port {svc['port']}')\n")

print("\n" + "=" * 70)
print("COMMON FIXES")
print("=" * 70)
print("""
1. Python Module Import Errors:
   - Run: pip install -r /content/ai_final/agentic-framework-main/requirements.txt

2. Port Already in Use:
   - Find process: lsof -i :<port>
   - Kill it: kill -9 <PID>
   
3. Database Connection Errors:
   - Restart PostgreSQL: sudo service postgresql restart
   - Check connection: pg_isready -h localhost -p 5432

4. Redis Connection Errors:
   - Start Redis: redis-server --daemonize yes
   - Test: redis-cli ping

5. Missing Environment Variables:
   - Source the .env file: export $(cat /content/ai_final/agentic-framework-main/.env | xargs)

6. Permission Errors:
   - Fix ownership: chown -R $(whoami) /content/ai_final

7. If all else fails:
   - Restart Colab runtime: Runtime > Restart runtime
   - Re-run all cells from the beginning
""")

print("=" * 70)
print("END DIAGNOSTICS")
print("=" * 70)
