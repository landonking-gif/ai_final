# Agentic Framework — Colab Deployment

One-click deployment of the full Agentic Framework stack on Google Colab with GPU.

## Quick Start

### From Windows (local machine)

```powershell
# Push code to GitHub and open Colab notebook
.\deploy\launch.ps1

# Or without pushing (if code is already on GitHub)
.\deploy\launch.ps1 -NoPush
```

### From Google Colab (manual)

1. Open: [Colab Notebook](https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/deploy/colab_notebook.ipynb)
2. Set GPU runtime: **Runtime → Change runtime type → T4 GPU**
3. **Runtime → Run all** (Ctrl+F9)
4. Wait ~5 minutes — public URLs printed at the end

## Architecture

| Service | Port | Description |
|---------|------|-------------|
| **Orchestrator** | 8000 | Main API — chat, Ralph Loop, routing |
| **Memory Service** | 8002 | Multi-tier storage (PostgreSQL + ChromaDB + MinIO) |
| **SubAgent Manager** | 8003 | Agent pool lifecycle and governance |
| **Code Executor** | 8004 | Sandboxed Python execution |
| **MCP Gateway** | 8080 | Model Context Protocol tool integration |
| **Dashboard** | 3000 | React web UI |
| **Ollama** | 11434 | Local LLM inference (DeepSeek R1 14B) |
| **PostgreSQL** | 5432 | Relational database |
| **Redis** | 6379 | Session cache (DB 0-4 per service) |
| **ChromaDB** | 8001 | Vector embeddings |
| **MinIO** | 9000/9001 | Object storage |

## Notebook Cells

| Cell | Purpose | When to use |
|------|---------|-------------|
| **1 — Deploy** | Full automated deployment | Run once at start |
| **2 — Diagnostics** | Health check all services | Anytime to check status |
| **3 — Recovery** | Restart a crashed service | When a service is down |
| **4 — Logs** | View service log output | When debugging issues |

## Diagnostic Commands

After deployment, run these in a new Colab cell:

```python
from colab_deploy import diagnose, recover_service, show_logs

# Full health report
diagnose()

# Restart a specific service
recover_service("orchestrator")
recover_service("memory_service")
recover_service("subagent_manager")
recover_service("mcp_gateway")
recover_service("code_exec")
recover_service("ollama")

# View logs
show_logs()                      # master deployment log
show_logs("orchestrator", 50)    # last 50 lines of a service
```

## Logs

All logs are in `/tmp/agentic_logs/`:

| File | Contents |
|------|----------|
| `deployment.log` | Master deployment log (all phases) |
| `orchestrator.log` | Orchestrator service output |
| `memory_service.log` | Memory service output |
| `subagent_manager.log` | SubAgent manager output |
| `mcp_gateway.log` | MCP Gateway output |
| `code_exec.log` | Code Executor output |
| `ollama.log` | Ollama LLM server output |
| `chromadb.log` | ChromaDB output |
| `minio.log` | MinIO output |
| `dashboard.log` | Dashboard output |

## Troubleshooting

### Service won't start
```python
from colab_deploy import show_logs
show_logs("service_name", 100)  # Check the last 100 lines
```

### Module import errors
Usually means PYTHONPATH isn't set or symlinks are missing. The deployment script handles both automatically. If you see `ModuleNotFoundError`, check:
```python
import os
print(os.environ.get("PYTHONPATH"))
# Should be: /content/ai_final/agentic-framework-main
```

### Port already in use
A previous deployment left a process running. Kill it:
```python
!lsof -i :8000  # find the PID
!kill -9 <PID>  # kill it
```

### ngrok tunnel not working
- Check your auth token isn't expired
- Free tier limits: 1 agent, 4 tunnels
- Check: `from pyngrok import ngrok; print(ngrok.get_tunnels())`

### Out of disk space
DeepSeek R1 14B is ~9GB. Clear space:
```python
!ollama rm deepseek-r1:14b  # remove the large model
!ollama pull llama3.2:3b    # use smaller model instead
```

### GPU out of memory
Switch to a smaller model by editing the config at the top of `colab_deploy.py`:
```python
PRIMARY_MODEL = "llama3.2:3b"  # instead of deepseek-r1:14b
```

## File Structure

```
deploy/
├── colab_deploy.py      # Main deployment script (runs in Colab)
├── colab_notebook.ipynb  # Colab notebook (4 cells)
├── launch.ps1            # Windows launcher (push + open browser)
└── README.md             # This file
```
