# Agentic Framework - Deployment Guide

## System Overview

The Agentic Framework is a multi-agent orchestration system that uses the Ralph Loop methodology for autonomous code generation and task execution.

### Architecture

```
┌──────────────────────────────────────────────────────┐
│              Load Balancer/Nginx (Optional)           │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                 Orchestrator (Port 8000)              │
│  - Main chat endpoint: /api/chat/public              │
│  - Health check: /health                             │
│  - Always routes through Ralph Loop                  │
└───────────────────────┬──────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│   Memory     │ │    MCP     │ │  Subagent  │
│  Service     │ │  Gateway   │ │  Manager   │
│  :8002       │ │  :8080     │ │  :8003     │
└──────────────┘ └────────────┘ └────────────┘
        │                              │
┌───────▼──────┐                ┌─────▼──────┐
│  Chroma DB   │                │  Agent Pool│
│  PostgreSQL  │                │            │
└──────────────┘                └────────────┘
```

## Prerequisites

- **AWS EC2 Instance** (t2.large or larger recommended)
- **Docker & Docker Compose** installed
- **Ollama** running on host (port 11434)
- **SSH Access** with key pair
- **Git** installed

## Quick Start Deployment

### 1. Clone Repository

```bash
git clone <repository-url>
cd agentic-framework
```

### 2. Configure Environment

Create `.env` file:

```bash
# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:32b
LLM_BASE_URL=http://host.docker.internal:11434/v1

# Optional: Other LLM Providers
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=...
# AZURE_OPENAI_API_KEY=...

# Memory Service
MEMORY_SERVICE_URL=http://memory-service:8002

# MCP Gateway
MCP_GATEWAY_URL=http://mcp-gateway:8080

# Subagent Manager
SUBAGENT_MANAGER_URL=http://subagent-manager:8003

# Database (for Memory Service)
POSTGRES_USER=agenticuser
POSTGRES_PASSWORD=agenticpass
POSTGRES_DB=memory_db
DATABASE_URL=postgresql://agenticuser:agenticpass@postgres:5432/memory_db

# Redis
REDIS_URL=redis://redis:6379

# ChromaDB
CHROMA_HOST=chroma
CHROMA_PORT=8000
```

### 3. Build and Start Services

```bash
# Build all services
docker compose build

# Start all services
docker compose up -d

# Check service status
docker compose ps
```

### 4. Verify Deployment

```bash
# Check orchestrator health
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/api/chat/public \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, test the system"}'
```

## Service Details

### Orchestrator (Main Service)

- **Port:** 8000
- **Key Endpoints:**
  - `POST /api/chat/public` - Public chat (no auth)
  - `POST /api/chat` - Authenticated chat
  - `GET /health` - Health check
  - `GET /api/sessions` - List sessions
  - `GET /api/sessions/{id}/history` - Get chat history

**Important:** All code generation requests are routed through Ralph Loop for consistent quality.

### Memory Service

- **Port:** 8002
- **Endpoints:**
  - `POST /memory/query` - Query memories
  - `POST /memory/commit` - Save new artifact
  - `GET /health` - Health check

### MCP Gateway

- **Port:** 8080
- **Purpose:** Model Context Protocol integration
- **Endpoints:**
  - `GET /health` - Health check
  - `POST /mcp/tools/list` - List available tools

### Subagent Manager

- **Port:** 8003
- **Purpose:** Manage agent pool
- **Endpoints:**
  - `POST /subagent/spawn` - Spawn new agent
  - `GET /health` - Health check

## Ralph Loop Configuration

The system uses Ralph Loop for ALL code generation tasks, regardless of complexity. This ensures:

- ✅ Consistent code quality
- ✅ Proper multi-agent workflow execution
- ✅ PRD-based implementation
- ✅ Automated testing and validation

### Ralph Loop Workflow

1. **PRD Generation**: Creates Product Requirements Document
2. **Story Breakdown**: Decomposes into user stories
3. **Implementation**: Generates code using specialized agents
4. **Validation**: Runs tests and quality checks
5. **Iteration**: Refines until all criteria met

## Automated Deployment Script

Create `deploy.sh`:

```bash
#!/bin/bash

set -e

echo "🚀 Agentic Framework Deployment Script"
echo "======================================="

# Configuration
SSH_KEY="${SSH_KEY:-king-ai-studio.pem}"
SERVER="${SERVER:-34.229.112.127}"
USER="${USER:-ubuntu}"
REMOTE_DIR="/opt/agentic-framework"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Upload files
log_info "Uploading files to server..."
scp -i "$SSH_KEY" -r \
    orchestrator/ \
    adapters/ \
    memory-service/ \
    mcp-gateway/ \
    subagent-manager/ \
    docker-compose.yml \
    requirements.txt \
    "${USER}@${SERVER}:/tmp/agentic-framework-deploy/"

# Step 2: Deploy on server
log_info "Deploying on server..."
ssh -i "$SSH_KEY" "${USER}@${SERVER}" << 'ENDSSH'
set -e

# Move files
sudo rm -rf /opt/agentic-framework.bak
sudo mv /opt/agentic-framework /opt/agentic-framework.bak 2>/dev/null || true
sudo mv /tmp/agentic-framework-deploy /opt/agentic-framework
cd /opt/agentic-framework

# Build services
echo "Building services..."
sudo docker compose build

# Start services
echo "Starting services..."
sudo docker compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check health
echo "Checking service health..."
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:8002/health || exit 1
curl -f http://localhost:8080/health || exit 1

echo "✅ Deployment successful!"
ENDSSH

log_info "Deployment complete!"

# Step 3: Run health checks
log_info "Running health checks..."
ssh -i "$SSH_KEY" "${USER}@${SERVER}" << 'ENDSSH'
cd /opt/agentic-framework
echo "Service Status:"
sudo docker compose ps
echo ""
echo "Recent Logs:"
sudo docker compose logs --tail=20 orchestrator
ENDSSH

log_info "✅ All checks passed!"
echo ""
echo "🎉 Deployment successful!"
echo "Dashboard: http://${SERVER}"
echo "API: http://${SERVER}:8000/api/chat/public"
```

Make it executable:

```bash
chmod +x deploy.sh
```

## Usage

### Using deploy.sh

```bash
# Default deployment
./deploy.sh

# Custom server
SERVER=1.2.3.4 SSH_KEY=my-key.pem ./deploy.sh
```

### Manual Deployment

```bash
# Upload files
scp -i key.pem -r . ubuntu@server:/tmp/deploy/

# SSH to server
ssh -i key.pem ubuntu@server

# Deploy
cd /tmp/deploy
sudo mv * /opt/agentic-framework/
cd /opt/agentic-framework
sudo docker compose build
sudo docker compose up -d
```

## Testing

### Basic Test

```python
import requests

response = requests.post(
    'http://localhost:8000/api/chat/public',
    json={'message': 'Write a Python function to calculate factorial'}
)

print(response.json())
```

### Comprehensive Test Suite

See `test_ralph_loop.py` for multi-step task testing.

## Monitoring

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f orchestrator

# Last N lines
docker compose logs --tail=100 orchestrator
```

### Service Status

```bash
# Check all services
docker compose ps

# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8002/health
curl http://localhost:8080/health
curl http://localhost:8003/health
```

## Troubleshooting

### Orchestrator Not Starting

```bash
# Check logs
docker compose logs orchestrator

# Common issues:
# 1. LLM_BASE_URL not accessible
# 2. Memory service not ready
# 3. Port 8000 already in use
```

### Memory Service Errors

```bash
# Check database connection
docker compose logs postgres

# Reset database
docker compose down -v
docker compose up -d
```

### Ralph Loop Timeouts

- Check LLM response time
- Increase timeout in agent.py
- Monitor agent manager logs

## Updating

### Update Single Service

```bash
# Rebuild specific service
docker compose build orchestrator

# Restart it
docker compose up -d orchestrator
```

### Full Update

```bash
# Pull latest changes
git pull

# Rebuild all
docker compose build

# Restart all
docker compose up -d
```

## Backup and Restore

### Backup

```bash
# Backup volumes
docker compose down
sudo tar -czf backup.tar.gz /var/lib/docker/volumes/agentic-framework_*

# Backup configuration
tar -czf config-backup.tar.gz .env docker-compose.yml
```

### Restore

```bash
# Restore volumes
docker compose down
sudo tar -xzf backup.tar.gz -C /

# Restart
docker compose up -d
```

## Performance Tuning

### Orchestrator

- Adjust `RALPH_LOOP_MAX_ITERATIONS` (default: 10)
- Increase `RALPH_LOOP_TIMEOUT` (default: 300s)
- Scale with `docker compose up -d --scale orchestrator=3`

### Memory Service

- Increase PostgreSQL connections
- Add connection pooling
- Configure ChromaDB persistence

## Security

### Production Recommendations

1. **Enable Authentication**: Remove `/api/chat/public` endpoint
2. **Use HTTPS**: Set up nginx with SSL
3. **API Keys**: Set all `_API_KEY` environment variables
4. **Network Isolation**: Use docker networks
5. **Firewall**: Restrict ports 8000, 8002, 8003, 8080

### Example Nginx Config

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Support

- **Documentation**: See `/docs` directory
- **Issues**: GitHub Issues
- **Logs**: `docker compose logs`

## License

See LICENSE file
