#!/bin/bash
set -e
cd /opt/agentic-framework

# Configure Ollama to listen on all interfaces
echo "Configuring Ollama..."
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null << 'OLLAMACONF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
OLLAMACONF
sudo systemctl daemon-reload
sudo systemctl restart ollama
sleep 5

# Pull and pre-load DeepSeek R1 14B thinking model
echo "Ensuring deepseek-r1:14b model is available..."
ollama pull deepseek-r1:14b 2>/dev/null || true
echo "Pre-loading Ollama model (this may take 30-90s on first run)..."
timeout 120 curl -s -X POST http://localhost:11434/api/generate -d '{"model":"deepseek-r1:14b","prompt":"Hello","stream":false}' > /dev/null 2>&1 || echo "  Model warmup skipped (will load on first request)"
echo "  [OK] Model ready"

mkdir -p ~/.openclaw/workspace/skills ~/.openclaw/workspace/.copilot/memory/diary ~/.openclaw/workspace/.copilot/memory/reflections

cat > ~/.openclaw/openclaw.json << 'OCLAWEND'
{
  "agent": {
    "model": "llama3.2:3b",
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
LOCAL_MODEL=llama3.2:3b
OPENCLAW_GATEWAY_URL=ws://openclaw:18789
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
  
  # Increased timeouts for LLM operations
  proxy_connect_timeout 600s;
  proxy_send_timeout 600s;
  proxy_read_timeout 600s;
  send_timeout 600s;
  
  location /api/ {
    proxy_pass http://localhost:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
    proxy_buffering off;
  }
  location /ws {
    proxy_pass http://localhost:8000/ws;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;
  }
  location /openclaw {
    proxy_pass http://localhost:18789;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
  }
  location / {
    root /var/www/html;
    try_files $uri /index.html;
  }
}
NGINXEND

sudo ln -sf /etc/nginx/sites-available/agentic-framework /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Build and deploy dashboard
echo "Building dashboard..."
cd dashboard
if [ ! -d "node_modules" ]; then
  echo "Installing dashboard dependencies..."
  npm install
fi
echo "Building production version..."
# Use /api prefix so nginx proxy handles the routing
npm run build
sudo rm -rf /var/www/html/*
sudo cp -r build/* /var/www/html/
cd ..
echo "Dashboard deployed to /var/www/html"

sudo nginx -t && sudo systemctl restart nginx
echo "Deployment complete"
