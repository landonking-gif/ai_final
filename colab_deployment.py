#!/usr/bin/env python3
"""
Agentic Framework — Fully Automatic Google Colab Deployment
============================================================
Run this single script to deploy the entire stack on Colab:
    !python colab_deployment.py

It will:
  1. Install system deps (PostgreSQL, Redis, Node.js 22, MinIO)
  2. Install Ollama + pull DeepSeek R1 14B (GPU-accelerated)
  3. Clone the repo & install Python packages
  4. Start PostgreSQL, Redis, ChromaDB, MinIO
  5. Start all 5 microservices + dashboard
  6. Create ngrok tunnels for external access
  7. Run health checks
  8. Enter a keep-alive watchdog loop (auto-restarts crashed services)
"""

import os
import subprocess
import sys
import time
import shutil
import urllib.request
import json
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════
REPO_URL = "https://github.com/landonking-gif/ai_final.git"
INSTALL_DIR = "/content/ai_final"
FRAMEWORK_DIR = f"{INSTALL_DIR}/agentic-framework-main"
PRIMARY_MODEL = "deepseek-r1:14b"
FALLBACK_MODEL = "llama3.2:3b"
NGROK_AUTH_TOKEN = ""  # Set for stable URLs: https://dashboard.ngrok.com/signup
START_DASHBOARD = True
ENABLE_NGROK = True


def run_cmd(cmd, desc=""):
    """Run a shell command with status output."""
    if desc:
        print(f"  [{desc}]", end=" ", flush=True)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if desc:
        print("OK" if result.returncode == 0 else f"WARN ({result.stderr[:120]})")
    return result


def is_service_alive(port):
    """Check if a service is responding on the given port."""
    try:
        url = f"http://localhost:{port}/health" if port != 11434 else f"http://localhost:{port}/api/tags"
        urllib.request.urlopen(url, timeout=5)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════
# PHASE 1: System Check & Dependencies
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("PHASE 1: SYSTEM CHECK & DEPENDENCY INSTALL")
print("=" * 60)

# GPU check
gpu_check = subprocess.run(
    ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
    capture_output=True, text=True
)
if gpu_check.returncode == 0:
    print(f"  [GPU] {gpu_check.stdout.strip()}")
else:
    print("  [GPU] No GPU detected — LLM inference will be slow!")

disk = shutil.disk_usage("/")
print(f"  [Disk] {disk.free / (1024**3):.1f} GB free")
print(f"  [Python] {sys.version.split()[0]}")

# Install system packages
print("\n  Installing system packages...")
run_cmd("apt-get update -qq 2>/dev/null", "apt update")
run_cmd("apt-get install -y -qq postgresql postgresql-client redis-server build-essential libpq-dev > /dev/null 2>&1",
        "PostgreSQL + Redis + build tools")
run_cmd("curl -fsSL https://deb.nodesource.com/setup_22.x | bash - > /dev/null 2>&1", "Node.js 22 repo")
run_cmd("apt-get install -y -qq nodejs > /dev/null 2>&1", "Node.js 22")
run_cmd("wget -q https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio && chmod +x /usr/local/bin/minio",
        "MinIO")

node_ver = subprocess.run("node --version", shell=True, capture_output=True, text=True)
print(f"  [Node.js] {node_ver.stdout.strip()}")
print("  Phase 1 complete.\n")


# ═══════════════════════════════════════════════════════════
# PHASE 2: Ollama + LLM Models
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("PHASE 2: OLLAMA + LLM MODEL SETUP")
print("=" * 60)

print("  Installing Ollama...", end=" ", flush=True)
result = subprocess.run("curl -fsSL https://ollama.com/install.sh | sh",
                        shell=True, capture_output=True, text=True)
print("OK" if result.returncode == 0 else f"WARN: {result.stderr[:200]}")

print("  Starting Ollama server...", end=" ", flush=True)
os.environ["OLLAMA_HOST"] = "0.0.0.0:11434"
subprocess.Popen(
    ["ollama", "serve"],
    stdout=open("/tmp/ollama.log", "w"),
    stderr=subprocess.STDOUT,
    env={**os.environ, "OLLAMA_HOST": "0.0.0.0:11434"}
)
time.sleep(5)
print("OK")

print(f"  Pulling {PRIMARY_MODEL} (this may take 2-8 min)...")
subprocess.run(["ollama", "pull", PRIMARY_MODEL], capture_output=False, text=True)

print(f"  Pulling {FALLBACK_MODEL}...")
subprocess.run(["ollama", "pull", FALLBACK_MODEL], capture_output=False, text=True)

print("\n  Available models:")
subprocess.run(["ollama", "list"], capture_output=False, text=True)
print("  Phase 2 complete.\n")


# ═══════════════════════════════════════════════════════════
# PHASE 3: Clone Repo + Install Python Packages
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("PHASE 3: REPO CLONE & PYTHON DEPENDENCIES")
print("=" * 60)

if os.path.exists(INSTALL_DIR):
    print("  Repo exists — pulling latest...")
    subprocess.run(["git", "-C", INSTALL_DIR, "pull"], capture_output=False, text=True)
else:
    print(f"  Cloning {REPO_URL}...")
    subprocess.run(["git", "clone", REPO_URL, INSTALL_DIR], capture_output=False, text=True)

os.chdir(FRAMEWORK_DIR)

# Symlinks for Python imports (hyphenated dirs -> underscored)
symlinks = {
    "memory_service": "memory-service",
    "subagent_manager": "subagent-manager",
    "mcp_gateway": "mcp-gateway",
    "code_exec": "code-exec",
}
for link_name, target in symlinks.items():
    if not os.path.exists(link_name) and os.path.exists(target):
        os.symlink(target, link_name)
        print(f"  Symlink: {link_name} -> {target}")

print("\n  Installing Python packages (2-3 min)...")
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "-r", f"{FRAMEWORK_DIR}/requirements.txt"],
    capture_output=False, text=True
)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "pyngrok", "asyncpg", "aiofiles", "psutil"],
    capture_output=False, text=True
)

print("  Installing OpenClaw...")
subprocess.run(["npm", "install", "-g", "openclaw@latest"], capture_output=True, text=True)

if FRAMEWORK_DIR not in sys.path:
    sys.path.insert(0, FRAMEWORK_DIR)
os.environ["PYTHONPATH"] = FRAMEWORK_DIR

print(f"  Framework: {FRAMEWORK_DIR}")
print("  Phase 3 complete.\n")


# ═══════════════════════════════════════════════════════════
# PHASE 4: Start Infrastructure + Services
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("PHASE 4: INFRASTRUCTURE & SERVICES")
print("=" * 60)

os.chdir(FRAMEWORK_DIR)

# ── Infrastructure ──
print("\n── Infrastructure ──")

# PostgreSQL
print("  Starting PostgreSQL...", end=" ", flush=True)
subprocess.run("service postgresql start", shell=True, capture_output=True)
time.sleep(2)
for cmd in [
    "CREATE USER agent_user WITH PASSWORD 'agent_pass' CREATEDB;",
    "CREATE DATABASE agentic_framework OWNER agent_user;",
    "GRANT ALL PRIVILEGES ON DATABASE agentic_framework TO agent_user;",
]:
    subprocess.run(["sudo", "-u", "postgres", "psql", "-c", cmd],
                   capture_output=True, text=True)
pg = subprocess.run(["sudo", "-u", "postgres", "psql", "-c", "SELECT 1;"],
                    capture_output=True, text=True)
print("OK" if pg.returncode == 0 else "FAIL")

# Redis
print("  Starting Redis...", end=" ", flush=True)
subprocess.run("redis-server --daemonize yes --port 6379", shell=True, capture_output=True)
time.sleep(1)
redis_ok = subprocess.run("redis-cli ping", shell=True, capture_output=True, text=True)
print("OK" if "PONG" in redis_ok.stdout else "FAIL")

# ChromaDB
print("  Starting ChromaDB...", end=" ", flush=True)
os.makedirs("/tmp/chroma_data", exist_ok=True)
subprocess.Popen(
    ["chroma", "run", "--host", "0.0.0.0", "--port", "8001", "--path", "/tmp/chroma_data"],
    stdout=open("/tmp/chroma.log", "w"), stderr=subprocess.STDOUT
)
time.sleep(3)
print("OK")

# MinIO
print("  Starting MinIO...", end=" ", flush=True)
os.makedirs("/tmp/minio_data", exist_ok=True)
subprocess.Popen(
    ["/usr/local/bin/minio", "server", "/tmp/minio_data",
     "--address", ":9000", "--console-address", ":9001"],
    stdout=open("/tmp/minio.log", "w"), stderr=subprocess.STDOUT,
    env={**os.environ, "MINIO_ROOT_USER": "minioadmin", "MINIO_ROOT_PASSWORD": "minioadmin"}
)
time.sleep(2)
print("OK")

# ── Environment Variables ──
env_vars = {
    "POSTGRES_URL": "postgresql://agent_user:agent_pass@localhost:5432/agentic_framework",
    "REDIS_URL": "redis://localhost:6379/0",
    "MCP_GATEWAY_URL": "http://localhost:8080",
    "MEMORY_SERVICE_URL": "http://localhost:8002",
    "SUBAGENT_MANAGER_URL": "http://localhost:8003",
    "CODE_EXECUTOR_URL": "http://localhost:8004",
    "OLLAMA_ENDPOINT": "http://localhost:11434",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "LOCAL_MODEL": PRIMARY_MODEL,
    "FALLBACK_MODEL": FALLBACK_MODEL,
    "DEFAULT_LLM_PROVIDER": "ollama",
    "LLM_PROVIDER": "ollama",
    "USE_OPENCLAW": "false",
    "CHROMA_URL": "http://localhost:8001",
    "MINIO_ENDPOINT": "localhost:9000",
    "MINIO_ACCESS_KEY": "minioadmin",
    "MINIO_SECRET_KEY": "minioadmin",
    "JWT_SECRET_KEY": "colab-dev-secret-key-change-in-production",
    "ENVIRONMENT": "development",
    "PYTHONPATH": FRAMEWORK_DIR,
    "WORKSPACE_ROOT": f"{FRAMEWORK_DIR}/workspace",
    "WEBSOCKET_ENABLED": "true",
    "INDEX_CODEBASE": "true",
}
for k, v in env_vars.items():
    os.environ[k] = v

with open(f"{FRAMEWORK_DIR}/.env", "w") as f:
    for k, v in env_vars.items():
        f.write(f"{k}={v}\n")

for d in ["workspace/.copilot/memory/diary", "workspace/.copilot/memory/reflections", "workspace/ralph-work"]:
    os.makedirs(f"{FRAMEWORK_DIR}/{d}", exist_ok=True)

print("  Environment configured.")

# ── Start Microservices ──
print("\n── Microservices ──")

# Ensure PYTHONPATH is set for all services
service_env = {**os.environ}
service_env['PYTHONPATH'] = FRAMEWORK_DIR

SERVICE_DEFS = [
    {"name": "Code Executor",    "module": "code_exec.service.main:app",        "port": 8004, "log": "/tmp/code_exec.log",        "env": {"REDIS_URL": "redis://localhost:6379/4"}},
    {"name": "Memory Service",   "module": "memory_service.service.main:app",   "port": 8002, "log": "/tmp/memory_service.log",   "env": {"REDIS_URL": "redis://localhost:6379/2"}},
    {"name": "SubAgent Manager", "module": "subagent_manager.service.main:app", "port": 8003, "log": "/tmp/subagent_manager.log", "env": {"REDIS_URL": "redis://localhost:6379/1", "SUBAGENT_USE_OPENCLAW": "false", "SUBAGENT_LLM_PROVIDER": "ollama", "SUBAGENT_LLM_MODEL": PRIMARY_MODEL}},
    {"name": "MCP Gateway",      "module": "mcp_gateway.service.main:app",      "port": 8080, "log": "/tmp/mcp_gateway.log",      "env": {"REDIS_URL": "redis://localhost:6379/3"}},
    {"name": "Orchestrator",     "module": "orchestrator.service.main:app",     "port": 8000, "log": "/tmp/orchestrator.log",     "env": {}},
]

def check_service_health(port, max_retries=10):
    """Wait for service to respond on health endpoint"""
    for i in range(max_retries):
        try:
            # Try health endpoint first
            urllib.request.urlopen(f"http://localhost:{port}/health", timeout=2)
            return True
        except:
            # For dashboard (port 3000), try root endpoint
            if port == 3000:
                try:
                    urllib.request.urlopen(f"http://localhost:{port}/", timeout=2)
                    return True
                except:
                    pass
            time.sleep(1)
    return False

for svc in SERVICE_DEFS:
    print(f"  Starting {svc['name']} (:{svc['port']})...", end=" ", flush=True)
    svc_env = {**service_env, **svc["env"]}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", svc["module"],
         "--host", "0.0.0.0", "--port", str(svc["port"])],
        cwd=FRAMEWORK_DIR,
        stdout=open(svc["log"], "w"),
        stderr=subprocess.STDOUT,
        env=svc_env
    )
    
    # Wait for service to be healthy
    if check_service_health(svc["port"]):
        print(f"OK (PID {proc.pid})")
    else:
        print(f"WARN (PID {proc.pid}, check {svc['log']})")

# ── Dashboard ──
dashboard_running = False
if START_DASHBOARD:
    print("\n── Dashboard ──")
    dashboard_dir = f"{FRAMEWORK_DIR}/dashboard"
    if os.path.exists(f"{dashboard_dir}/build"):
        print("  Serving pre-built dashboard (port 3000)...", end=" ", flush=True)
        subprocess.Popen(
            ["npx", "serve", "-s", "build", "-l", "3000"],
            cwd=dashboard_dir,
            stdout=open("/tmp/dashboard.log", "w"),
            stderr=subprocess.STDOUT,
            env={**os.environ, "PORT": "3000"}
        )
        time.sleep(5)
        # Verify dashboard started
        if check_service_health(3000, max_retries=5):
            print("OK")
            dashboard_running = True
        else:
            print("WARN (check /tmp/dashboard.log)")
    elif os.path.exists(f"{dashboard_dir}/package.json"):
        print("  Installing deps & starting (may take 30s)...", end=" ", flush=True)
        subprocess.run(["npm", "install"], cwd=dashboard_dir, capture_output=True)
        subprocess.Popen(
            ["npm", "start"],
            cwd=dashboard_dir,
            stdout=open("/tmp/dashboard.log", "w"),
            stderr=subprocess.STDOUT,
            env={**os.environ, "PORT": "3000", "BROWSER": "none"}
        )
        # React apps need 20-30 seconds to build and start
        time.sleep(25)
        # Verify dashboard started
        if check_service_health(3000, max_retries=10):
            print("OK")
            dashboard_running = True
        else:
            print("WARN (check /tmp/dashboard.log)")
    else:
        print("  Dashboard source not found - skipping")
else:
    print("\n  Dashboard disabled (START_DASHBOARD=False)")

# ── Health Checks ──
print("\n  Waiting 10s for final initialization...")
time.sleep(10)

print("\n── Health Checks ──")
endpoints = [
    ("Orchestrator",     "http://localhost:8000/health"),
    ("Memory Service",   "http://localhost:8002/health"),
    ("SubAgent Manager", "http://localhost:8003/health"),
    ("MCP Gateway",      "http://localhost:8080/health"),
    ("Code Executor",    "http://localhost:8004/health"),
    ("Ollama",           "http://localhost:11434/api/tags"),
]

all_ok = True
for name, url in endpoints:
    try:
        req = urllib.request.urlopen(url, timeout=10)
        print(f"  {name:20s} : OK ({req.getcode()})")
    except Exception as e:
        all_ok = False
        print(f"  {name:20s} : STARTING ({str(e)[:50]})")

if all_ok:
    print("\n  ALL SERVICES HEALTHY")
else:
    print("\n  Some services still starting — they should be ready in ~30s.")
print("  Phase 4 complete.\n")


# ═══════════════════════════════════════════════════════════
# PHASE 5: External Access (ngrok)
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("PHASE 5: EXTERNAL ACCESS")
print("=" * 60)

api_url = "http://localhost:8000"
dashboard_url = "http://localhost:3000"

if ENABLE_NGROK:
    try:
        from pyngrok import ngrok

        if NGROK_AUTH_TOKEN:
            ngrok.set_auth_token(NGROK_AUTH_TOKEN)

        print("  Creating tunnel for API (port 8000)...")
        api_tunnel = ngrok.connect(8000, "http")
        api_url = api_tunnel.public_url

        if START_DASHBOARD and dashboard_running:
            print("  Creating tunnel for Dashboard (port 3000)...")
            dash_tunnel = ngrok.connect(3000, "http")
            dashboard_url = dash_tunnel.public_url
        elif START_DASHBOARD and not dashboard_running:
            print("  Skipping dashboard tunnel (dashboard not running)")
            dashboard_url = "http://localhost:3000 (not available)"

        os.environ["COLAB_API_URL"] = api_url
        os.environ["COLAB_DASHBOARD_URL"] = dashboard_url

        print("")
        print("+" + "=" * 58 + "+")
        print("|  PUBLIC ACCESS URLS                                      |")
        print("+" + "=" * 58 + "+")
        print(f"|  API:        {api_url:<45s}|")
        print(f"|  API Docs:   {api_url + '/docs':<45s}|")
        print(f"|  Health:     {api_url + '/health':<45s}|")
        print(f"|  WebSocket:  {api_url.replace('http', 'ws') + '/ws':<45s}|")
        if START_DASHBOARD and dashboard_running:
            print(f"|  Dashboard:  {dashboard_url:<45s}|")
        elif START_DASHBOARD:
            print(f"|  Dashboard:  NOT AVAILABLE (check /tmp/dashboard.log) |")
        print("+" + "=" * 58 + "+")
    except Exception as e:
        print(f"  ngrok failed: {e}")
        print("  Services available at localhost only.")
else:
    print("  ngrok disabled.")

print("\n  Local endpoints:")
print("    Orchestrator:    http://localhost:8000")
print("    Memory Service:  http://localhost:8002")
print("    SubAgent Mgr:    http://localhost:8003")
print("    MCP Gateway:     http://localhost:8080")
print("    Code Executor:   http://localhost:8004")
print("    Ollama LLM:      http://localhost:11434")
if START_DASHBOARD and dashboard_running:
    print("    Dashboard:       http://localhost:3000")
elif START_DASHBOARD:
    print("    Dashboard:       http://localhost:3000 (NOT RUNNING - check logs)")
print("  Phase 5 complete.\n")


# ═══════════════════════════════════════════════════════════
# PHASE 6: Keep-Alive Watchdog
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("DEPLOYMENT COMPLETE — WATCHDOG STARTING")
print("=" * 60)
print("  Monitoring services every 60s with auto-restart.")
print("  Status updates every 5 minutes.")
print("  Press Ctrl+C to stop.\n")


def restart_service(svc):
    """Restart a crashed microservice."""
    print(f"    Restarting {svc['name']} (:{svc['port']})...", end=" ", flush=True)
    svc_env = {**os.environ, **svc["env"]}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", svc["module"],
         "--host", "0.0.0.0", "--port", str(svc["port"])],
        cwd=FRAMEWORK_DIR,
        stdout=open(svc["log"], "a"),
        stderr=subprocess.STDOUT,
        env=svc_env
    )
    time.sleep(5)
    print(f"PID {proc.pid}")


cycle = 0
try:
    while True:
        cycle += 1
        restarts = 0

        # Check microservices
        for svc in SERVICE_DEFS:
            if not is_service_alive(svc["port"]):
                restart_service(svc)
                restarts += 1

        # Check Ollama
        if not is_service_alive(11434):
            print("    Restarting Ollama...", end=" ", flush=True)
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=open("/tmp/ollama.log", "a"),
                stderr=subprocess.STDOUT,
                env={**os.environ, "OLLAMA_HOST": "0.0.0.0:11434"}
            )
            time.sleep(5)
            print("OK")
            restarts += 1

        # Status update every 5 minutes
        if cycle % 5 == 0:
            now = datetime.now().strftime("%H:%M:%S")
            alive = sum(1 for s in SERVICE_DEFS if is_service_alive(s["port"]))
            ollama_ok = is_service_alive(11434)
            print(f"  [{now}] Services: {alive}/{len(SERVICE_DEFS)} | Ollama: {'OK' if ollama_ok else 'DOWN'} | Restarts: {restarts}")

        time.sleep(60)

except KeyboardInterrupt:
    print("\n  Watchdog stopped.")