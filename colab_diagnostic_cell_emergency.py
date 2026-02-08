# ╔══════════════════════════════════════════════════════════════╗
# ║  EMERGENCY DIAGNOSTIC - Run this if services fail           ║
# ╚══════════════════════════════════════════════════════════════╝
#
# Copy this entire cell and run it in Colab after your deployment
# to diagnose why services are failing
#

import subprocess
import os
import sys

print("="*70)
print("SERVICE FAILURE DIAGNOSTIC")
print("="*70)

# 1. Check if services are running
print("\n1. PROCESS CHECK:")
print("-"*70)
result = subprocess.run("ps aux | grep uvicorn | grep -v grep", shell=True, capture_output=True, text=True)
if result.stdout.strip():
    for line in result.stdout.strip().split('\n'):
        print(f"  {line[:120]}")
else:
    print("  ❌ NO uvicorn processes found!")

# 2. Check port bindings
print("\n2. PORT CHECK:")
print("-"*70)
for port in [8000, 8002, 8003, 8004, 8080]:
    result = subprocess.run(f"lsof -i :{port} 2>/dev/null", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            print(f"  Port {port}: {lines[1][:80]}")
    else:
        print(f" ❌ Port {port}: NOTHING LISTENING")

# 3. Check PYTHONPATH
print("\n3. ENVIRONMENT CHECK:")
print("-"*70)
print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
print(f"  Framework dir exists: {os.path.exists('/content/ai_final/agentic-framework-main')}")

# 4. Check Python packages
print("\n4. PACKAGE CHECK:")
print("-"*70)
packages = ['fastapi', 'uvicorn', 'redis', 'sqlalchemy', 'psycopg2']
for pkg in packages:
    try:
        __import__(pkg)
        print(f"  ✅ {pkg}")
    except:
        print(f"  ❌ {pkg} NOT INSTALLED")

# 5. Test module imports
print("\n5. MODULE IMPORT CHECK:")
print("-"*70)
sys.path.insert(0, '/content/ai_final/agentic-framework-main')
os.environ['PYTHONPATH'] = '/content/ai_final/agentic-framework-main'

modules_to_test = [
    'orchestrator.service.main',
    'memory_service.service.main',
    'subagent_manager.service.main',
    'mcp_gateway.service.main',
    'code_exec.service.main'
]

for mod in modules_to_test:
    try:
        __import__(mod)
        print(f"  ✅ {mod}")
    except Exception as e:
        print(f"  ❌ {mod}: {str(e)[:80]}")

# 6. Check service logs
print("\n6. SERVICE LOGS (Last 20 lines each):")
print("-"*70)

logs = {
    'Orchestrator': '/tmp/orchestrator.log',
    'Memory': '/tmp/memory_service.log',
    'SubAgent': '/tmp/subagent_manager.log',
    'MCP Gateway': '/tmp/mcp_gateway.log',
    'Code Exec': '/tmp/code_exec.log'
}

for name, logfile in logs.items():
    if os.path.exists(logfile):
        print(f"\n{name} ({logfile}):")
        result = subprocess.run(f"tail -20 {logfile}", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout)
        else:
            print("  (empty log)")
    else:
        print(f"\n{name}: LOG FILE NOT FOUND")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
print("\nLook for:")
print("  • ImportError or ModuleNotFoundError in logs")
print("  • Port already in use errors")
print("  • Missing PYTHONPATH or packages")
print("  • Failed module imports above")
