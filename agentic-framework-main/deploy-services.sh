#!/bin/bash
set -e
cd /opt/agentic-framework

mkdir -p ~/.openclaw/workspace/skills ~/.openclaw/workspace/.copilot/memory/diary ~/.openclaw/workspace/.copilot/memory/reflections

cat > ~/.openclaw/openclaw.json << 'OCLAWEND'
{
  "agent": {
    "model": "ollama/deepseek-r1:14b",
    "workspace": "~/.openclaw/workspace"
  },
  "gateway": {
    "port": 18789,
    "bind": "0.0.0.0"
  },
  "models": {
    "providers": {
      "ollama": {
        "baseUrl": "http://localhost:11434"
      }
    }
  }
}
OCLAWEND

[ ! -f ~/.openclaw/workspace/.copilot/memory/COPILOT.md ] && echo "# Copilot Memory" > ~/.openclaw/workspace/.copilot/memory/COPILOT.md

cat > .env << 'ENVEND'
ENVIRONMENT=production
LLM_PROVIDER=openclaw
DEFAULT_LLM_PROVIDER=openclaw
USE_OPENCLAW=true
OPENCLAW_GATEWAY_URL=ws://localhost:18789
OPENCLAW_MODEL=ollama/deepseek-r1:14b
LOCAL_MODEL=ollama/deepseek-r1:14b
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_ENDPOINT=http://host.docker.internal:11434
POSTGRES_HOST=postgres
POSTGRES_DB=agentic_memory
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_pass_2024
REDIS_HOST=redis
REDIS_PORT=6379
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
WEBSOCKET_ENABLED=true
WORKSPACE_ROOT=/opt/agentic-framework/workspace
MEMORY_SERVICE_URL=http://memory-service:8002
INDEX_CODEBASE=true
ENVEND

mkdir -p workspace/.copilot/memory/diary workspace/.copilot/memory/reflections

sudo docker compose down 2>/dev/null || true
sudo docker compose build
sudo docker compose up -d
sleep 20

echo "Checking services..."
for svc in postgres redis orchestrator mcp-gateway memory-service subagent-manager skill-executor; do
  if sudo docker compose ps | grep -q "$svc.*running\|$svc.*Up"; then
    echo "  [OK] $svc running"
  fi
done

sudo apt install -y nginx >/dev/null 2>&1

sudo tee /etc/nginx/sites-available/agentic-framework >/dev/null << 'NGINXEND'
server {
  listen 80;
  client_max_body_size 100M;
  location /api/ {
    proxy_pass http://localhost:8000/;
    proxy_set_header Host $host;
    proxy_read_timeout 300s;
  }
  location /ws {
    proxy_pass http://localhost:8000/ws;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
  }
  location /openclaw {
    proxy_pass http://localhost:18789;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
  location / {
    root /var/www/html;
    try_files $uri /index.html;
  }
}
NGINXEND

sudo ln -sf /etc/nginx/sites-available/agentic-framework /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
echo "Deployment complete"
