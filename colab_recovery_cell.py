# ╔══════════════════════════════════════════════════════════════╗
# ║  Quick Service Recovery - Restart Failed Services           ║
# ╚══════════════════════════════════════════════════════════════╝
#
# Run this cell to restart any failed microservices
#

import subprocess
import sys
import os
import time

FRAMEWORK_DIR = "/content/ai_final/agentic-framework-main"

# Make sure PYTHONPATH is set
os.environ['PYTHONPATH'] = FRAMEWORK_DIR

SERVICE_DEFS = [
    {"name": "Orchestrator",     "module": "orchestrator.service.main:app",     "port": 8000, "log": "/tmp/orchestrator.log",     "env": {}},
    {"name": "Memory Service",   "module": "memory_service.service.main:app",   "port": 8002, "log": "/tmp/memory_service.log",   "env": {"REDIS_URL": "redis://localhost:6379/2"}},
    {"name": "SubAgent Manager", "module": "subagent_manager.service.main:app", "port": 8003, "log": "/tmp/subagent_manager.log", "env": {"REDIS_URL": "redis://localhost:6379/1"}},
    {"name": "MCP Gateway",      "module": "mcp_gateway.service.main:app",      "port": 8080, "log": "/tmp/mcp_gateway.log",      "env": {"REDIS_URL": "redis://localhost:6379/3"}},
    {"name": "Code Executor",    "module": "code_exec.service.main:app",        "port": 8004, "log": "/tmp/code_exec.log",        "env": {"REDIS_URL": "redis://localhost:6379/4"}},
]

def is_running(port):
    """Check if service is responding on port"""
    try:
        import urllib.request
        url = f"http://localhost:{port}/health"
        urllib.request.urlopen(url, timeout=5)
        return True
    except:
        return False

def kill_port(port):
    """Kill any process using the port"""
    subprocess.run(f"lsof -ti :{port} | xargs kill -9 2>/dev/null", shell=True)
    time.sleep(1)

print("=" * 60)
print("RESTARTING FAILED SERVICES")
print("=" * 60)

restarted = 0
for svc in SERVICE_DEFS:
    if not is_running(svc['port']):
        print(f"\n  Restarting {svc['name']} on port {svc['port']}...")
        
        # Kill any zombie process on the port
        kill_port(svc['port'])
        
        # Prepare environment
        svc_env = {**os.environ, **svc['env']}
        
        # Start the service
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", svc["module"],
             "--host", "0.0.0.0", "--port", str(svc["port"])],
            cwd=FRAMEWORK_DIR,
            stdout=open(svc["log"], "w"),
            stderr=subprocess.STDOUT,
            env=svc_env
        )
        
        print(f"    PID: {proc.pid}")
        time.sleep(3)
        
        # Verify it started
        if is_running(svc['port']):
            print(f"    ✅ {svc['name']} started successfully")
            restarted += 1
        else:
            print(f"    ❌ {svc['name']} failed to start (check {svc['log']})")
    else:
        print(f"  ✅ {svc['name']:20s} - already running")

print("\n" + "=" * 60)
print(f"RECOVERY COMPLETE - {restarted} services restarted")
print("=" * 60)
print("\n  Wait 10 seconds, then re-run the smoke test!")
