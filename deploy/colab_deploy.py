#!/usr/bin/env python3
"""
Agentic Framework — Fully Automated Google Colab Deployment
=============================================================
Single-script deployment for the entire Agentic Framework stack on Google Colab.

Usage (in a Colab cell):
    !python /content/ai_final/deploy/colab_deploy.py

Phases:
  1. Preflight       — GPU check (required), disk, Python version
  2. System Deps     — PostgreSQL, Redis, Node.js 22, MinIO, Ollama
  3. LLM Models      — Pull DeepSeek R1 14B + llama3.2:3b
  4. Repo & Python   — Clone repo, symlinks, pip install
  5. Infrastructure  — Start PostgreSQL, Redis, ChromaDB, MinIO
  6. Microservices   — Start 5 services in dependency order + dashboard
  7. External Access  — ngrok tunnels for API + Dashboard
  8. Watchdog        — Auto-restart loop with continuous monitoring

Author: Agentic Framework Team
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import signal
import socket
import subprocess
import sys
import textwrap
import time
import traceback
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

REPO_URL       = "https://github.com/landonking-gif/ai_final.git"
INSTALL_DIR    = "/content/ai_final"
FRAMEWORK_DIR  = f"{INSTALL_DIR}/agentic-framework-main"
PRIMARY_MODEL  = "deepseek-r1:14b"
FALLBACK_MODEL = "llama3.2:3b"

NGROK_AUTH_TOKEN = "39MaIP07IiJMHPNDgd3raMEOL6r_2KyacFVXP68bbxBu9s8E8"

ENABLE_NGROK     = True
START_DASHBOARD  = True

# Timeouts (seconds)
SERVICE_HEALTH_TIMEOUT    = 45   # max wait for a service to become healthy
SERVICE_POLL_INTERVAL     = 2    # seconds between health polls
INFRA_START_WAIT          = 3    # wait after starting infra components
WATCHDOG_INTERVAL         = 60   # seconds between watchdog cycles
WATCHDOG_STATUS_INTERVAL  = 5    # cycles between status prints

# Logging
LOG_DIR       = "/tmp/agentic_logs"
MASTER_LOG    = f"{LOG_DIR}/deployment.log"
SERVICE_LOGS  = {
    "ollama":          f"{LOG_DIR}/ollama.log",
    "chromadb":        f"{LOG_DIR}/chromadb.log",
    "minio":           f"{LOG_DIR}/minio.log",
    "code_exec":       f"{LOG_DIR}/code_exec.log",
    "memory_service":  f"{LOG_DIR}/memory_service.log",
    "subagent_manager": f"{LOG_DIR}/subagent_manager.log",
    "mcp_gateway":     f"{LOG_DIR}/mcp_gateway.log",
    "orchestrator":    f"{LOG_DIR}/orchestrator.log",
    "dashboard":       f"{LOG_DIR}/dashboard.log",
}

# Service definitions (started in this order — dependency order matters)
SERVICE_DEFS = [
    {
        "name":   "Code Executor",
        "key":    "code_exec",
        "module": "code_exec.service.main:app",
        "port":   8004,
        "env":    {"REDIS_URL": "redis://localhost:6379/4"},
    },
    {
        "name":   "Memory Service",
        "key":    "memory_service",
        "module": "memory_service.service.main:app",
        "port":   8002,
        "env":    {"REDIS_URL": "redis://localhost:6379/2"},
    },
    {
        "name":   "SubAgent Manager",
        "key":    "subagent_manager",
        "module": "subagent_manager.service.main:app",
        "port":   8003,
        "env":    {
            "REDIS_URL": "redis://localhost:6379/1",
            "SUBAGENT_USE_OPENCLAW": "false",
            "SUBAGENT_LLM_PROVIDER": "ollama",
            "SUBAGENT_LLM_MODEL": PRIMARY_MODEL,
        },
    },
    {
        "name":   "MCP Gateway",
        "key":    "mcp_gateway",
        "module": "mcp_gateway.service.main:app",
        "port":   8080,
        "env":    {"REDIS_URL": "redis://localhost:6379/3"},
    },
    {
        "name":   "Orchestrator",
        "key":    "orchestrator",
        "module": "orchestrator.service.main:app",
        "port":   8000,
        "env":    {},
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

os.makedirs(LOG_DIR, exist_ok=True)

class ColorFormatter(logging.Formatter):
    """Colored console output with structured formatting."""
    COLORS = {
        "DEBUG":    "\033[90m",    # gray
        "INFO":     "\033[97m",    # white
        "WARNING":  "\033[93m",    # yellow
        "ERROR":    "\033[91m",    # red
        "CRITICAL": "\033[91;1m", # bold red
    }
    RESET = "\033[0m"
    ICONS = {
        "DEBUG":    "·",
        "INFO":     "→",
        "WARNING":  "⚠",
        "ERROR":    "✗",
        "CRITICAL": "☠",
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        icon  = self.ICONS.get(record.levelname, " ")
        ts    = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        msg   = record.getMessage()
        return f"{color}  {icon} [{ts}] {msg}{self.RESET}"


class FileFormatter(logging.Formatter):
    """Detailed file log with timestamp, level, module, and message."""
    def format(self, record):
        ts  = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        lvl = record.levelname.ljust(8)
        mod = (record.funcName or "main").ljust(20)
        msg = record.getMessage()
        out = f"[{ts}] {lvl} {mod} {msg}"
        if record.exc_info and record.exc_info[1]:
            out += "\n" + "".join(traceback.format_exception(*record.exc_info))
        return out


def setup_logging() -> logging.Logger:
    """Configure dual-output logging (console + file)."""
    log = logging.getLogger("deploy")
    log.setLevel(logging.DEBUG)
    log.handlers.clear()

    # Console handler (INFO+)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(ColorFormatter())
    log.addHandler(ch)

    # File handler (DEBUG+)
    fh = logging.FileHandler(MASTER_LOG, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(FileFormatter())
    log.addHandler(fh)

    return log

log = setup_logging()


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

class DeploymentError(Exception):
    """Fatal deployment error — causes immediate abort."""
    pass


class PhaseTracker:
    """Tracks deployment phases and timing."""
    def __init__(self):
        self.phases: List[Dict[str, Any]] = []
        self.deploy_start = time.time()

    @contextmanager
    def phase(self, number: int, name: str):
        """Context manager for deployment phases with timing."""
        log.info("")
        log.info("=" * 60)
        log.info(f"PHASE {number}: {name}")
        log.info("=" * 60)
        start = time.time()
        entry = {"phase": number, "name": name, "start": start, "status": "running", "errors": []}
        self.phases.append(entry)
        try:
            yield entry
            entry["status"] = "ok"
            elapsed = time.time() - start
            log.info(f"Phase {number} complete ({elapsed:.1f}s)")
        except DeploymentError:
            entry["status"] = "fatal"
            raise
        except Exception as e:
            entry["status"] = "error"
            entry["errors"].append(str(e))
            log.error(f"Phase {number} failed: {e}", exc_info=True)
            raise DeploymentError(f"Phase {number} ({name}) failed: {e}") from e

    def summary(self) -> str:
        """Return a summary table of all phases."""
        lines = ["", "DEPLOYMENT SUMMARY", "-" * 50]
        total = time.time() - self.deploy_start
        for p in self.phases:
            elapsed = (p.get("end", time.time()) - p["start"])
            icon = "✓" if p["status"] == "ok" else "✗" if p["status"] in ("error", "fatal") else "?"
            lines.append(f"  {icon} Phase {p['phase']}: {p['name']:<30s} ({elapsed:.1f}s)")
            for err in p.get("errors", []):
                lines.append(f"      Error: {err}")
        lines.append(f"\n  Total: {total:.1f}s ({total/60:.1f} min)")
        return "\n".join(lines)


tracker = PhaseTracker()


def run(cmd: str, desc: str = "", check: bool = False, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a shell command with logging.

    Args:
        cmd:     Shell command string.
        desc:    Human description (logged).
        check:   If True, raise on non-zero exit.
        timeout: Seconds before timeout (default 5 min).
    """
    log.debug(f"CMD: {cmd}")
    if desc:
        log.info(f"{desc}...")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            log.debug(f"CMD stdout: {result.stdout[-500:]}" if result.stdout else "CMD stdout: (empty)")
            log.debug(f"CMD stderr: {result.stderr[-500:]}" if result.stderr else "CMD stderr: (empty)")
            if check:
                raise DeploymentError(
                    f"Command failed (exit {result.returncode}): {cmd}\n"
                    f"stderr: {result.stderr[-300:]}"
                )
            elif desc:
                log.warning(f"{desc} returned exit code {result.returncode}")
        else:
            if desc:
                log.info(f"{desc} OK")
        return result
    except subprocess.TimeoutExpired:
        log.error(f"Command timed out after {timeout}s: {cmd}")
        if check:
            raise DeploymentError(f"Command timed out: {cmd}")
        return subprocess.CompletedProcess(cmd, 1, "", "timeout")


def run_visible(cmd: str, desc: str = "", timeout: int = 600) -> int:
    """Run a command with output visible to the user (for model pulls etc)."""
    log.debug(f"CMD (visible): {cmd}")
    if desc:
        log.info(f"{desc}...")
    try:
        result = subprocess.run(cmd, shell=True, timeout=timeout)
        return result.returncode
    except subprocess.TimeoutExpired:
        log.error(f"Command timed out after {timeout}s: {cmd}")
        return 1


def is_port_open(port: int) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection(("localhost", port), timeout=2):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def http_health(port: int, path: str = "/health", timeout: int = 3) -> Tuple[bool, str]:
    """Check HTTP health endpoint. Returns (ok, detail)."""
    url = f"http://localhost:{port}{path}"
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        body = req.read().decode("utf-8", errors="replace")[:200]
        return True, f"HTTP {req.getcode()} — {body}"
    except Exception as e:
        return False, str(e)[:120]


def wait_for_health(port: int, path: str = "/health", name: str = "",
                     max_wait: int = SERVICE_HEALTH_TIMEOUT) -> bool:
    """Poll health endpoint until success or timeout."""
    label = name or f"port {port}"
    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        ok, detail = http_health(port, path)
        if ok:
            log.info(f"{label} healthy (attempt {attempt}): {detail}")
            return True
        log.debug(f"{label} attempt {attempt}: {detail}")
        time.sleep(SERVICE_POLL_INTERVAL)
    log.error(f"{label} did NOT become healthy within {max_wait}s")
    return False


def tail_log(logfile: str, lines: int = 30) -> str:
    """Read last N lines of a log file."""
    try:
        with open(logfile, "r", errors="replace") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except FileNotFoundError:
        return "(log file not found)"
    except Exception as e:
        return f"(error reading log: {e})"


def start_background_process(cmd: list, logfile: str, env: dict = None,
                               cwd: str = None) -> subprocess.Popen:
    """Start a background process with its output redirected to a log file."""
    log.debug(f"Starting background: {' '.join(cmd)} -> {logfile}")
    fh = open(logfile, "w")
    proc = subprocess.Popen(
        cmd,
        stdout=fh,
        stderr=subprocess.STDOUT,
        env=env or os.environ.copy(),
        cwd=cwd,
    )
    log.debug(f"Started PID {proc.pid}")
    return proc


# Track all started processes for cleanup
_processes: Dict[str, subprocess.Popen] = {}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: PREFLIGHT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def phase_1_preflight():
    with tracker.phase(1, "PREFLIGHT CHECKS"):
        # GPU check (required)
        gpu = run("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader")
        if gpu.returncode != 0:
            log.critical("NO GPU DETECTED. This deployment requires a GPU runtime.")
            log.critical("Go to: Runtime → Change runtime type → GPU (T4 or better)")
            raise DeploymentError("GPU required but not found. Select a GPU runtime in Colab.")
        gpu_info = gpu.stdout.strip()
        log.info(f"GPU: {gpu_info}")

        # VRAM check
        vram_check = run("nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits")
        if vram_check.returncode == 0:
            vram_mb = int(vram_check.stdout.strip())
            log.info(f"VRAM: {vram_mb} MB ({vram_mb/1024:.1f} GB)")
            if vram_mb < 8000:
                log.warning(f"Only {vram_mb} MB VRAM — DeepSeek R1 14B needs ~10GB. May fall back to smaller model.")

        # Disk space
        disk = shutil.disk_usage("/")
        free_gb = disk.free / (1024**3)
        log.info(f"Disk: {free_gb:.1f} GB free / {disk.total / (1024**3):.1f} GB total")
        if free_gb < 10:
            log.warning(f"Low disk space ({free_gb:.1f} GB free). Recommend 15+ GB.")
            if free_gb < 5:
                raise DeploymentError(f"Insufficient disk space: {free_gb:.1f} GB free (need ≥5 GB)")

        # Python
        py_ver = sys.version.split()[0]
        log.info(f"Python: {py_ver}")
        major, minor = sys.version_info[:2]
        if major < 3 or (major == 3 and minor < 10):
            raise DeploymentError(f"Python 3.10+ required, found {py_ver}")

        # Colab detection
        in_colab = "COLAB_GPU" in os.environ or os.path.exists("/content")
        log.info(f"Environment: {'Google Colab' if in_colab else 'Non-Colab (may need adjustments)'}")

        log.info("Preflight checks passed")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: SYSTEM DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════

def phase_2_system_deps():
    with tracker.phase(2, "SYSTEM DEPENDENCIES"):
        # apt update
        run("apt-get update -qq 2>/dev/null", "apt-get update")

        # PostgreSQL + Redis + build tools
        run("apt-get install -y -qq postgresql postgresql-client redis-server "
            "build-essential libpq-dev > /dev/null 2>&1",
            "Install PostgreSQL, Redis, build-essential")

        # Node.js 22
        run("curl -fsSL https://deb.nodesource.com/setup_22.x | bash - > /dev/null 2>&1",
            "Add Node.js 22 repo")
        run("apt-get install -y -qq nodejs > /dev/null 2>&1", "Install Node.js")
        node_ver = run("node --version")
        log.info(f"Node.js version: {node_ver.stdout.strip()}")

        # MinIO
        run("wget -q https://dl.min.io/server/minio/release/linux-amd64/minio "
            "-O /usr/local/bin/minio && chmod +x /usr/local/bin/minio",
            "Install MinIO binary")

        # Ollama - install using Colab-optimized method
        log.info("Installing Ollama...")
        ollama_exists = run("which ollama", check=False).returncode == 0
        if not ollama_exists:
            # Method 1: Try official install script with bash
            log.info("Attempting Ollama install via official script...")
            result = run("bash -c 'curl -fsSL https://ollama.com/install.sh | bash'",
                        check=False, timeout=180)
            
            # Check if it worked
            if run("which ollama", check=False).returncode == 0:
                log.info("Ollama installed via official script")
            else:
                # Method 2: Download from Ollama's CDN directly
                log.warning("Official script failed, trying direct download...")
                result = run(
                    "curl -fL https://ollama.com/download/ollama-linux-amd64 "
                    "-o /usr/local/bin/ollama && chmod +x /usr/local/bin/ollama",
                    check=False, timeout=120
                )
                
                # If CDN fails, try GitHub releases with correct asset name
                if result.returncode != 0 or run("which ollama", check=False).returncode != 0:
                    log.warning("CDN download failed, trying GitHub archive...")
                    # Download and extract from GitHub releases (they distribute as tgz)
                    run(
                        "curl -fsSL https://github.com/ollama/ollama/releases/download/v0.1.22/ollama-linux-amd64.tgz "
                        "| tar -xz -C /usr/local/bin/ ollama 2>/dev/null || "
                        "curl -fsSL https://github.com/ollama/ollama/releases/download/v0.1.14/ollama-linux-amd64 "
                        "-o /usr/local/bin/ollama && chmod +x /usr/local/bin/ollama",
                        "Download Ollama from archive", check=True, timeout=120
                    )
            
            # Verify installation worked
            result = run("ollama --version", check=True)
            log.info(f"Ollama installed: {result.stdout.strip()}")
        else:
            log.info("Ollama already installed")

        log.info("All system dependencies installed")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: LLM MODELS
# ═══════════════════════════════════════════════════════════════════════════════

def phase_3_llm_models():
    with tracker.phase(3, "LLM MODELS (Ollama)"):
        # Start Ollama server
        log.info("Starting Ollama server...")
        ollama_env = {**os.environ, "OLLAMA_HOST": "0.0.0.0:11434"}
        _processes["ollama"] = start_background_process(
            ["ollama", "serve"],
            SERVICE_LOGS["ollama"],
            env=ollama_env,
        )
        time.sleep(5)

        # Verify Ollama is running
        if not wait_for_health(11434, "/api/tags", "Ollama", max_wait=30):
            # Try reading log for why it failed
            log.error(f"Ollama log:\n{tail_log(SERVICE_LOGS['ollama'], 20)}")
            raise DeploymentError("Ollama server failed to start")

        # Pull primary model
        log.info(f"Pulling {PRIMARY_MODEL} (this may take 2-8 minutes)...")
        rc = run_visible(f"ollama pull {PRIMARY_MODEL}", timeout=600)
        if rc != 0:
            log.warning(f"Failed to pull {PRIMARY_MODEL} — will try fallback only")

        # Pull fallback model
        log.info(f"Pulling {FALLBACK_MODEL}...")
        rc = run_visible(f"ollama pull {FALLBACK_MODEL}", timeout=300)
        if rc != 0:
            log.warning(f"Failed to pull {FALLBACK_MODEL}")

        # Verify models
        result = run("ollama list")
        log.info(f"Available models:\n{result.stdout}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: REPO CLONE & PYTHON PACKAGES
# ═══════════════════════════════════════════════════════════════════════════════

def phase_4_repo_and_python():
    with tracker.phase(4, "REPO & PYTHON DEPENDENCIES"):
        # Clone or pull
        if os.path.exists(INSTALL_DIR):
            log.info("Repository exists — pulling latest changes...")
            run(f"git -C {INSTALL_DIR} pull", "git pull")
        else:
            log.info(f"Cloning {REPO_URL}...")
            run(f"git clone {REPO_URL} {INSTALL_DIR}", "git clone", check=True, timeout=120)

        # Verify framework dir exists
        if not os.path.isdir(FRAMEWORK_DIR):
            raise DeploymentError(f"Framework directory not found: {FRAMEWORK_DIR}")

        os.chdir(FRAMEWORK_DIR)
        log.info(f"Working directory: {FRAMEWORK_DIR}")

        # Create Python-importable symlinks (hyphenated → underscored)
        symlinks = {
            "memory_service":  "memory-service",
            "subagent_manager": "subagent-manager",
            "mcp_gateway":     "mcp-gateway",
            "code_exec":       "code-exec",
        }
        for link_name, target in symlinks.items():
            link_path = os.path.join(FRAMEWORK_DIR, link_name)
            target_path = os.path.join(FRAMEWORK_DIR, target)
            if os.path.exists(link_path):
                log.debug(f"Symlink already exists: {link_name}")
                continue
            if not os.path.exists(target_path):
                log.warning(f"Target directory does not exist: {target}")
                continue
            os.symlink(target, link_name)
            log.info(f"Created symlink: {link_name} → {target}")

        # Install Python packages
        log.info("Installing Python packages from requirements.txt (2-3 min)...")
        run(f"{sys.executable} -m pip install -q -r {FRAMEWORK_DIR}/requirements.txt",
            "pip install requirements", timeout=300)

        # Install extra packages needed for Colab deployment
        log.info("Installing Colab extras (pyngrok, asyncpg, aiofiles, psutil)...")
        run(f"{sys.executable} -m pip install -q pyngrok asyncpg aiofiles psutil",
            "pip install extras")

        # Install OpenClaw globally (used by SubAgent Manager)
        run("npm install -g openclaw@latest 2>/dev/null", "Install OpenClaw (npm)")

        # Set PYTHONPATH
        if FRAMEWORK_DIR not in sys.path:
            sys.path.insert(0, FRAMEWORK_DIR)
        os.environ["PYTHONPATH"] = FRAMEWORK_DIR

        log.info("Repo cloned, symlinks created, packages installed")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

def phase_5_infrastructure():
    with tracker.phase(5, "INFRASTRUCTURE"):
        os.chdir(FRAMEWORK_DIR)

        # ── PostgreSQL ──
        log.info("Starting PostgreSQL...")
        run("service postgresql start", "PostgreSQL start")
        time.sleep(2)

        # Create user & database (ignore errors if already exist)
        pg_commands = [
            "CREATE USER agent_user WITH PASSWORD 'agent_pass' CREATEDB;",
            "CREATE DATABASE agentic_framework OWNER agent_user;",
            "GRANT ALL PRIVILEGES ON DATABASE agentic_framework TO agent_user;",
        ]
        for cmd in pg_commands:
            result = run(f"sudo -u postgres psql -c \"{cmd}\"")
            log.debug(f"PG: {cmd[:60]}... → rc={result.returncode}")

        # Verify PostgreSQL
        pg_test = run("sudo -u postgres psql -c 'SELECT 1;'")
        if pg_test.returncode == 0:
            log.info("PostgreSQL OK")
        else:
            log.error(f"PostgreSQL verification failed: {pg_test.stderr[:200]}")
            raise DeploymentError("PostgreSQL failed to start or configure")

        # ── Redis ──
        log.info("Starting Redis...")
        run("redis-server --daemonize yes --port 6379", "Redis start")
        time.sleep(1)
        redis_test = run("redis-cli ping")
        if "PONG" in redis_test.stdout:
            log.info("Redis OK (PONG)")
        else:
            log.error(f"Redis verification failed: {redis_test.stdout} {redis_test.stderr}")
            raise DeploymentError("Redis failed to start")

        # ── ChromaDB ──
        log.info("Starting ChromaDB...")
        os.makedirs("/tmp/chroma_data", exist_ok=True)
        _processes["chromadb"] = start_background_process(
            ["chroma", "run", "--host", "0.0.0.0", "--port", "8001", "--path", "/tmp/chroma_data"],
            SERVICE_LOGS["chromadb"],
        )
        time.sleep(INFRA_START_WAIT)
        if is_port_open(8001):
            log.info("ChromaDB OK (port 8001)")
        else:
            log.warning("ChromaDB may still be starting (port 8001 not open yet)")

        # ── MinIO ──
        log.info("Starting MinIO...")
        os.makedirs("/tmp/minio_data", exist_ok=True)
        minio_env = {**os.environ, "MINIO_ROOT_USER": "minioadmin", "MINIO_ROOT_PASSWORD": "minioadmin"}
        _processes["minio"] = start_background_process(
            ["/usr/local/bin/minio", "server", "/tmp/minio_data",
             "--address", ":9000", "--console-address", ":9001"],
            SERVICE_LOGS["minio"],
            env=minio_env,
        )
        time.sleep(INFRA_START_WAIT)
        if is_port_open(9000):
            log.info("MinIO OK (port 9000)")
        else:
            log.warning("MinIO may still be starting (port 9000 not open yet)")

        # ── Environment Variables ──
        log.info("Configuring environment variables...")
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

        # Write .env file
        env_path = f"{FRAMEWORK_DIR}/.env"
        with open(env_path, "w") as f:
            for k, v in env_vars.items():
                f.write(f"{k}={v}\n")
        log.info(f"Wrote {len(env_vars)} env vars to {env_path}")

        # Create workspace directories
        for d in [
            "workspace/.copilot/memory/diary",
            "workspace/.copilot/memory/reflections",
            "workspace/ralph-work",
        ]:
            os.makedirs(f"{FRAMEWORK_DIR}/{d}", exist_ok=True)
        log.info("Workspace directories created")

        log.info("All infrastructure services started")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: MICROSERVICES + DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def phase_6_services():
    with tracker.phase(6, "MICROSERVICES & DASHBOARD"):
        os.chdir(FRAMEWORK_DIR)

        base_env = os.environ.copy()
        base_env["PYTHONPATH"] = FRAMEWORK_DIR

        healthy = []
        failed  = []

        for svc in SERVICE_DEFS:
            name   = svc["name"]
            key    = svc["key"]
            module = svc["module"]
            port   = svc["port"]
            logfile = SERVICE_LOGS[key]

            log.info(f"Starting {name} on port {port}...")

            svc_env = {**base_env, **svc["env"]}
            proc = start_background_process(
                [sys.executable, "-m", "uvicorn", module,
                 "--host", "0.0.0.0", "--port", str(port)],
                logfile,
                env=svc_env,
                cwd=FRAMEWORK_DIR,
            )
            _processes[key] = proc

            # Wait for health
            if wait_for_health(port, "/health", name, max_wait=SERVICE_HEALTH_TIMEOUT):
                # Verify process still alive
                if proc.poll() is None:
                    log.info(f"{name} HEALTHY (PID {proc.pid}, port {port})")
                    healthy.append(name)
                else:
                    log.error(f"{name} process exited with code {proc.returncode}")
                    log.error(f"Last 20 lines of {logfile}:\n{tail_log(logfile, 20)}")
                    failed.append(name)
            else:
                if proc.poll() is not None:
                    log.error(f"{name} CRASHED (exit code {proc.returncode})")
                else:
                    log.error(f"{name} NOT RESPONDING (PID {proc.pid} alive but /health failing)")
                log.error(f"Last 30 lines of {logfile}:\n{tail_log(logfile, 30)}")
                failed.append(name)

        # ── Dashboard ──
        dashboard_ok = False
        if START_DASHBOARD:
            log.info("Starting Dashboard...")
            dashboard_dir = f"{FRAMEWORK_DIR}/dashboard"

            # Try extracting pre-built archive first
            tar_path = f"{dashboard_dir}/dashboard-build.tar.gz"
            build_dir = f"{dashboard_dir}/build"
            has_build = os.path.isdir(build_dir) and os.listdir(build_dir)

            if not has_build and os.path.isfile(tar_path):
                log.info("Extracting dashboard-build.tar.gz...")
                run(f"tar xzf {tar_path} -C {dashboard_dir}", "Extract dashboard build")
                has_build = os.path.isdir(build_dir) and os.listdir(build_dir)

            if has_build:
                log.info("Serving pre-built dashboard on port 3000...")
                _processes["dashboard"] = start_background_process(
                    ["npx", "serve", "-s", "build", "-l", "3000"],
                    SERVICE_LOGS["dashboard"],
                    env={**os.environ, "PORT": "3000"},
                    cwd=dashboard_dir,
                )
                time.sleep(5)
                dashboard_ok = wait_for_health(3000, "/", "Dashboard", max_wait=15)
            elif os.path.isfile(f"{dashboard_dir}/package.json"):
                log.info("No pre-built dashboard — running npm install & npm start (30-60s)...")
                run(f"cd {dashboard_dir} && npm install", "npm install (dashboard)", timeout=120)
                _processes["dashboard"] = start_background_process(
                    ["npm", "start"],
                    SERVICE_LOGS["dashboard"],
                    env={**os.environ, "PORT": "3000", "BROWSER": "none"},
                    cwd=dashboard_dir,
                )
                time.sleep(30)
                dashboard_ok = wait_for_health(3000, "/", "Dashboard", max_wait=30)
            else:
                log.warning("Dashboard source not found — skipping")

            if dashboard_ok:
                log.info("Dashboard HEALTHY (port 3000)")
                healthy.append("Dashboard")
            else:
                log.warning(f"Dashboard failed to start — check {SERVICE_LOGS['dashboard']}")
                log.warning(f"Dashboard log:\n{tail_log(SERVICE_LOGS['dashboard'], 15)}")
        else:
            log.info("Dashboard disabled (START_DASHBOARD=False)")

        # ── Summary ──
        log.info("")
        log.info(f"Services healthy: {len(healthy)}/{len(SERVICE_DEFS) + (1 if START_DASHBOARD else 0)}")
        for s in healthy:
            log.info(f"  ✓ {s}")
        for s in failed:
            log.error(f"  ✗ {s}")

        if failed:
            log.warning(f"{len(failed)} service(s) failed to start. Deployment will continue — "
                       "the watchdog may recover them.")

        return healthy, failed, dashboard_ok


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: EXTERNAL ACCESS (ngrok)
# ═══════════════════════════════════════════════════════════════════════════════

def phase_7_external_access(dashboard_ok: bool):
    api_url       = "http://localhost:8000"
    dashboard_url = "http://localhost:3000"

    with tracker.phase(7, "EXTERNAL ACCESS (ngrok)"):
        if not ENABLE_NGROK:
            log.info("ngrok disabled — services available at localhost only")
            return api_url, dashboard_url

        try:
            from pyngrok import ngrok

            if NGROK_AUTH_TOKEN:
                ngrok.set_auth_token(NGROK_AUTH_TOKEN)
                log.info("ngrok auth token configured")
            else:
                log.warning("No ngrok auth token — tunnels will be rate-limited")

            # API tunnel
            log.info("Creating ngrok tunnel for API (port 8000)...")
            api_tunnel = ngrok.connect(8000, "http")
            api_url = api_tunnel.public_url
            log.info(f"API tunnel: {api_url}")

            # Dashboard tunnel
            if START_DASHBOARD and dashboard_ok:
                log.info("Creating ngrok tunnel for Dashboard (port 3000)...")
                dash_tunnel = ngrok.connect(3000, "http")
                dashboard_url = dash_tunnel.public_url
                log.info(f"Dashboard tunnel: {dashboard_url}")
            else:
                log.info("Skipping dashboard tunnel (not running)")

            os.environ["COLAB_API_URL"]       = api_url
            os.environ["COLAB_DASHBOARD_URL"] = dashboard_url

        except ImportError:
            log.error("pyngrok not installed — install with: pip install pyngrok")
        except Exception as e:
            log.error(f"ngrok failed: {e}", exc_info=True)
            log.warning("Services available at localhost only")

    return api_url, dashboard_url


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 8: WATCHDOG
# ═══════════════════════════════════════════════════════════════════════════════

def phase_8_watchdog():
    """Continuously monitor and auto-restart crashed services."""
    log.info("")
    log.info("=" * 60)
    log.info("WATCHDOG ACTIVE — Monitoring services")
    log.info("=" * 60)
    log.info(f"Check interval: {WATCHDOG_INTERVAL}s | Status every {WATCHDOG_STATUS_INTERVAL} cycles")
    log.info("Press Ctrl+C / Interrupt kernel to stop")
    log.info("")

    base_env = os.environ.copy()
    base_env["PYTHONPATH"] = FRAMEWORK_DIR
    cycle = 0
    total_restarts = 0

    try:
        while True:
            cycle += 1
            cycle_restarts = 0

            # Check microservices
            for svc in SERVICE_DEFS:
                ok, detail = http_health(svc["port"])
                if not ok:
                    log.warning(f"[Watchdog] {svc['name']} DOWN on port {svc['port']} — restarting...")
                    svc_env = {**base_env, **svc["env"]}
                    _processes[svc["key"]] = start_background_process(
                        [sys.executable, "-m", "uvicorn", svc["module"],
                         "--host", "0.0.0.0", "--port", str(svc["port"])],
                        SERVICE_LOGS[svc["key"]],
                        env=svc_env,
                        cwd=FRAMEWORK_DIR,
                    )
                    time.sleep(8)
                    ok2, _ = http_health(svc["port"])
                    if ok2:
                        log.info(f"[Watchdog] {svc['name']} restarted successfully")
                    else:
                        log.error(f"[Watchdog] {svc['name']} failed to restart — check {SERVICE_LOGS[svc['key']]}")
                    cycle_restarts += 1

            # Check Ollama
            ok, _ = http_health(11434, "/api/tags")
            if not ok:
                log.warning("[Watchdog] Ollama DOWN — restarting...")
                ollama_env = {**os.environ, "OLLAMA_HOST": "0.0.0.0:11434"}
                _processes["ollama"] = start_background_process(
                    ["ollama", "serve"],
                    SERVICE_LOGS["ollama"],
                    env=ollama_env,
                )
                time.sleep(5)
                cycle_restarts += 1

            total_restarts += cycle_restarts

            # Status update
            if cycle % WATCHDOG_STATUS_INTERVAL == 0:
                now = datetime.now().strftime("%H:%M:%S")
                alive = sum(1 for s in SERVICE_DEFS if http_health(s["port"])[0])
                ollama_ok = http_health(11434, "/api/tags")[0]
                log.info(
                    f"[Watchdog {now}] Services: {alive}/{len(SERVICE_DEFS)} | "
                    f"Ollama: {'OK' if ollama_ok else 'DOWN'} | "
                    f"Restarts this cycle: {cycle_restarts} | Total: {total_restarts}"
                )

            time.sleep(WATCHDOG_INTERVAL)

    except KeyboardInterrupt:
        log.info("[Watchdog] Stopped by user")


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS (callable from notebook cells)
# ═══════════════════════════════════════════════════════════════════════════════

def diagnose():
    """Run a full diagnostic check. Call from a Colab cell:
        from colab_deploy import diagnose
        diagnose()
    """
    print("\n" + "=" * 60)
    print("AGENTIC FRAMEWORK — DIAGNOSTIC REPORT")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Service Health
    print("\n── Service Health ──")
    all_checks = [
        ("Orchestrator",     8000, "/health"),
        ("Memory Service",   8002, "/health"),
        ("SubAgent Manager", 8003, "/health"),
        ("Code Executor",    8004, "/health"),
        ("MCP Gateway",      8080, "/health"),
        ("Ollama",          11434, "/api/tags"),
        ("Dashboard",        3000, "/"),
        ("ChromaDB",         8001, "/api/v1/heartbeat"),
        ("MinIO",            9000, "/minio/health/live"),
    ]
    for name, port, path in all_checks:
        ok, detail = http_health(port, path, timeout=5)
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name:20s} (:{port}) — {detail[:60]}")

    # 2. Process check
    print("\n── Running Processes ──")
    ps = subprocess.run("ps aux | grep -E 'uvicorn|ollama|chroma|minio|serve|node' | grep -v grep",
                        shell=True, capture_output=True, text=True)
    for line in ps.stdout.strip().split("\n"):
        if line.strip():
            parts = line.split()
            pid = parts[1] if len(parts) > 1 else "?"
            cmd  = " ".join(parts[10:]) if len(parts) > 10 else line
            print(f"  PID {pid}: {cmd[:80]}")

    # 3. Port check
    print("\n── Port Bindings ──")
    for port in [5432, 6379, 8000, 8001, 8002, 8003, 8004, 8080, 9000, 11434, 3000]:
        bound = is_port_open(port)
        icon = "✓" if bound else "✗"
        print(f"  {icon} :{port}")

    # 4. GPU status
    print("\n── GPU ──")
    gpu = subprocess.run("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu "
                         "--format=csv,noheader", shell=True, capture_output=True, text=True)
    if gpu.returncode == 0:
        print(f"  {gpu.stdout.strip()}")
    else:
        print("  No GPU detected")

    # 5. Disk
    disk = shutil.disk_usage("/")
    print(f"\n── Disk: {disk.free/(1024**3):.1f} GB free / {disk.total/(1024**3):.1f} GB total ──")

    # 6. Recent logs
    print("\n── Recent Log Entries (last 5 lines each) ──")
    for svc_name, logfile in SERVICE_LOGS.items():
        if os.path.isfile(logfile):
            print(f"\n  [{svc_name}] {logfile}")
            content = tail_log(logfile, 5)
            for line in content.strip().split("\n"):
                print(f"    {line[:100]}")

    # 7. ngrok tunnels
    print("\n── ngrok Tunnels ──")
    try:
        from pyngrok import ngrok
        tunnels = ngrok.get_tunnels()
        if tunnels:
            for t in tunnels:
                print(f"  {t.public_url} → {t.config.get('addr', '?')}")
        else:
            print("  No active tunnels")
    except Exception as e:
        print(f"  ngrok not available: {e}")

    print("\n" + "=" * 60)
    print("END DIAGNOSTIC REPORT")
    print("=" * 60 + "\n")


def recover_service(service_key: str):
    """Restart a specific service. Call from a Colab cell:
        from colab_deploy import recover_service
        recover_service("orchestrator")

    Valid keys: code_exec, memory_service, subagent_manager, mcp_gateway, orchestrator, ollama
    """
    if service_key == "ollama":
        print(f"Restarting Ollama...")
        ollama_env = {**os.environ, "OLLAMA_HOST": "0.0.0.0:11434"}
        _processes["ollama"] = start_background_process(
            ["ollama", "serve"],
            SERVICE_LOGS["ollama"],
            env=ollama_env,
        )
        time.sleep(5)
        ok, detail = http_health(11434, "/api/tags")
        print(f"Ollama: {'HEALTHY' if ok else 'FAILED'} — {detail}")
        return ok

    svc = next((s for s in SERVICE_DEFS if s["key"] == service_key), None)
    if not svc:
        print(f"Unknown service key: {service_key}")
        print(f"Valid keys: {', '.join(s['key'] for s in SERVICE_DEFS)}, ollama")
        return False

    print(f"Restarting {svc['name']} on port {svc['port']}...")

    # Kill existing process if still tracked
    if service_key in _processes:
        old = _processes[service_key]
        if old.poll() is None:
            old.terminate()
            try:
                old.wait(timeout=5)
            except:
                old.kill()

    base_env = os.environ.copy()
    base_env["PYTHONPATH"] = FRAMEWORK_DIR
    svc_env = {**base_env, **svc["env"]}

    _processes[service_key] = start_background_process(
        [sys.executable, "-m", "uvicorn", svc["module"],
         "--host", "0.0.0.0", "--port", str(svc["port"])],
        SERVICE_LOGS[service_key],
        env=svc_env,
        cwd=FRAMEWORK_DIR,
    )
    time.sleep(8)

    ok, detail = http_health(svc["port"])
    print(f"{svc['name']}: {'HEALTHY' if ok else 'FAILED'} — {detail}")
    if not ok:
        print(f"Check log: {SERVICE_LOGS[service_key]}")
        print(f"Last 15 lines:\n{tail_log(SERVICE_LOGS[service_key], 15)}")
    return ok


def show_logs(service_key: str = None, lines: int = 50):
    """Show log output. Call from a Colab cell:
        from colab_deploy import show_logs
        show_logs("orchestrator")      # specific service
        show_logs()                     # master deployment log
    """
    if service_key is None:
        print(f"── Master Deployment Log ({MASTER_LOG}) ──")
        print(tail_log(MASTER_LOG, lines))
    elif service_key in SERVICE_LOGS:
        logfile = SERVICE_LOGS[service_key]
        print(f"── {service_key} ({logfile}) ──")
        print(tail_log(logfile, lines))
    else:
        print(f"Unknown service: {service_key}")
        print(f"Valid: {', '.join(SERVICE_LOGS.keys())}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DEPLOYMENT ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run the full deployment pipeline."""
    log.info("=" * 60)
    log.info("AGENTIC FRAMEWORK — AUTOMATED COLAB DEPLOYMENT")
    log.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Log file: {MASTER_LOG}")
    log.info("=" * 60)

    try:
        # Phases 1-5: Setup
        phase_1_preflight()
        phase_2_system_deps()
        phase_3_llm_models()
        phase_4_repo_and_python()
        phase_5_infrastructure()

        # Phase 6: Services
        healthy, failed, dashboard_ok = phase_6_services()

        # Phase 7: External access
        api_url, dashboard_url = phase_7_external_access(dashboard_ok)

        # Final status
        log.info("")
        log.info("+" + "=" * 58 + "+")
        log.info("|  DEPLOYMENT COMPLETE                                     |")
        log.info("+" + "=" * 58 + "+")
        log.info(f"|  API:        {api_url:<45s}|")
        log.info(f"|  API Docs:   {(api_url + '/docs'):<45s}|")
        log.info(f"|  Health:     {(api_url + '/health'):<45s}|")
        log.info(f"|  WebSocket:  {(api_url.replace('http','ws') + '/ws'):<45s}|")
        if dashboard_ok:
            log.info(f"|  Dashboard:  {dashboard_url:<45s}|")
        log.info("+" + "=" * 58 + "+")
        log.info("")
        log.info("Local endpoints:")
        log.info("  Orchestrator:    http://localhost:8000")
        log.info("  Memory Service:  http://localhost:8002")
        log.info("  SubAgent Mgr:    http://localhost:8003")
        log.info("  MCP Gateway:     http://localhost:8080")
        log.info("  Code Executor:   http://localhost:8004")
        log.info("  Ollama LLM:      http://localhost:11434")
        if dashboard_ok:
            log.info("  Dashboard:       http://localhost:3000")
        log.info("")
        log.info(f"Logs directory: {LOG_DIR}")
        log.info(f"Master log:     {MASTER_LOG}")
        log.info("")
        log.info("Diagnostic tools (run in a new cell):")
        log.info("  from colab_deploy import diagnose, recover_service, show_logs")
        log.info("  diagnose()                      # full health report")
        log.info("  recover_service('orchestrator')  # restart a service")
        log.info("  show_logs('orchestrator', 50)    # view service logs")
        log.info("")

        # Print summary
        log.info(tracker.summary())

        # Phase 8: Watchdog (runs forever)
        phase_8_watchdog()

    except DeploymentError as e:
        log.critical(f"DEPLOYMENT FAILED: {e}")
        log.info("")
        log.info("Troubleshooting:")
        log.info(f"  1. Check the master log: !cat {MASTER_LOG}")
        log.info(f"  2. Check service logs:   !ls -la {LOG_DIR}/")
        log.info("  3. Run diagnostics:      from colab_deploy import diagnose; diagnose()")
        log.info("")
        log.info(tracker.summary())
        sys.exit(1)

    except Exception as e:
        log.critical(f"UNEXPECTED ERROR: {e}", exc_info=True)
        log.info(tracker.summary())
        sys.exit(1)


if __name__ == "__main__":
    main()
