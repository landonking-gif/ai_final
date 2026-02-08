# CRITICAL DIAGNOSTIC - Run this RIGHT NOW to see what's wrong

import subprocess
import os

print("="*70)
print("IMMEDIATE SERVICE DIAGNOSTIC")
print("="*70)

# Check if services are still running
print("\n1. PROCESS STATUS (should show 5 uvicorn processes):")
print("-"*70)
result = subprocess.run("ps aux | grep uvicorn | grep -v grep | wc -l", shell=True, capture_output=True, text=True)
count = int(result.stdout.strip()) if result.stdout.strip() else 0
print(f"Running uvicorn processes: {count}/5")

if count == 0:
    print("❌ NO SERVICES RUNNING - They all crashed!")
    print("\nChecking service logs for errors...\n")

# Check each service log for errors
logs = {
    'Orchestrator (8000)': '/tmp/orchestrator.log',
    'Memory (8002)': '/tmp/memory_service.log',
    'SubAgent (8003)': '/tmp/subagent_manager.log',
    'MCP (8080)': '/tmp/mcp_gateway.log',
    'Code Exec (8004)': '/tmp/code_exec.log'
}

print("\n2. SERVICE LOGS - LAST 30 LINES (ERRORS ONLY):")
print("-"*70)

for name, logfile in logs.items():
    print(f"\n### {name} ###")
    if os.path.exists(logfile):
        result = subprocess.run(f"tail -30 {logfile} | grep -iE '(error|exception|traceback|failed|ModuleNotFoundError|ImportError)'", 
                              shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout)
        else:
            # If no errors found, show last 15 lines anyway
            result = subprocess.run(f"tail -15 {logfile}", shell=True, capture_output=True, text=True)
            print(result.stdout if result.stdout.strip() else "(empty log)")
    else:
        print("❌ LOG FILE NOT FOUND")

# Check PYTHONPATH
print("\n3. ENVIRONMENT:")
print("-"*70)
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")

# Check if framework exists
framework_dir = '/content/ai_final/agentic-framework-main'
print(f"Framework dir exists: {os.path.exists(framework_dir)}")

# Try importing modules
print("\n4. MODULE IMPORT TEST:")
print("-"*70)
import sys
sys.path.insert(0, framework_dir)

test_modules = [
    'orchestrator.service.main',
    'memory_service.service.main',
    'code_exec.service.main',
    'mcp_gateway.service.main'
]

for mod in test_modules:
    try:
        __import__(mod)
        print(f"✅ {mod}")
    except Exception as e:
        print(f"❌ {mod}")
        print(f"   Error: {str(e)[:200]}")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
print("\nNEXT STEPS:")
print("1. If you see ModuleNotFoundError/ImportError: Reinstall requirements")
print("2. If you see 'Address already in use': Kill services and restart")
print("3. If logs are empty: Services never started - check Python path")
print("4. Copy the errors above and we'll fix them!")
