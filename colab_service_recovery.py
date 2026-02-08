# SERVICE RECOVERY - Restart crashed services

import subprocess
import sys
import os
import time

FRAMEWORK_DIR = "/content/ai_final/agentic-framework-main"
os.environ['PYTHONPATH'] = FRAMEWORK_DIR
sys.path.insert(0, FRAMEWORK_DIR)

SERVICES = [
    {"name": "Code Executor", "module": "code_exec.service.main:app", "port": 8004, "log": "/tmp/code_exec.log"},
    {"name": "Memory Service", "module": "memory_service.service.main:app", "port": 8002, "log": "/tmp/memory_service.log"},
    {"name": "SubAgent Manager", "module": "subagent_manager.service.main:app", "port": 8003, "log": "/tmp/subagent_manager.log"},
    {"name": "MCP Gateway", "module": "mcp_gateway.service.main:app", "port": 8080, "log": "/tmp/mcp_gateway.log"},
    {"name": "Orchestrator", "module": "orchestrator.service.main:app", "port": 8000, "log": "/tmp/orchestrator.log"},
]

def is_running(port):
    """Check if service is responding"""
    try:
        import urllib.request
        urllib.request.urlopen(f"http://localhost:{port}/health", timeout=5)
        return True
    except:
        return False

def kill_port(port):
    """Kill any process using the port"""
    subprocess.run(f"lsof -ti :{port} | xargs kill -9 2>/dev/null", shell=True)
    time.sleep(1)

print("="*70)
print("SERVICE RECOVERY - RESTARTING CRASHED SERVICES")
print("="*70)

# First, check what's actually running
print("\n1. Current Status:")
for svc in SERVICES:
    status = "✅ RUNNING" if is_running(svc['port']) else "❌ DOWN"
    print(f"  {svc['name']:20s} (:{svc['port']}) - {status}")

print("\n2. Restarting Failed Services:")
restarted = 0
failed = 0

for svc in SERVICES:
    if not is_running(svc['port']):
        print(f"\n  Restarting {svc['name']}...")
        
        # Kill zombies
        kill_port(svc['port'])
        
        # Start service
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", svc["module"],
             "--host", "0.0.0.0", "--port", str(svc["port"])],
            cwd=FRAMEWORK_DIR,
            stdout=open(svc["log"], "w"),
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONPATH": FRAMEWORK_DIR}
        )
        
        print(f"    Started PID {proc.pid}, waiting 10s...")
        time.sleep(10)
        
        # Verify
        if is_running(svc['port']):
            print(f"    ✅ {svc['name']} is now healthy!")
            restarted += 1
        else:
            # Check if process crashed
            if proc.poll() is not None:
                print(f"    ❌ Service crashed (exit code {proc.returncode})")
                print(f"    Check logs: tail -30 {svc['log']}")
            else:
                print(f"    ⚠️  Service running but not responding")
                print(f"    Check logs: tail -30 {svc['log']}")
            failed += 1

print("\n" + "="*70)
print(f"RECOVERY COMPLETE: {restarted} restarted, {failed} still failing")
print("="*70)

if failed > 0:
    print("\nFor failed services, check logs:")
    for svc in SERVICES:
        if not is_running(svc['port']):
            print(f"  !tail -50 {svc['log']}")
    
    print("\nCommon fixes:")
    print("  1. Missing packages: !pip install -r /content/ai_final/agentic-framework-main/requirements.txt")
    print("  2. Module errors: Check PYTHONPATH is set correctly")
    print("  3. Port conflicts: Make sure ports aren't blocked")
else:
    print("\n✅ All services recovered! Re-run smoke test.")
