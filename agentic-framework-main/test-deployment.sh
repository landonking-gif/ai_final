#!/bin/bash

# Test script for Agentic Framework deployment
# Run this after deployment to verify everything is working
# Can run locally on the server OR remotely via SSH

# Detect if running locally on the server or remotely
if [ -f "/opt/agentic-framework/docker-compose.yml" ]; then
    # Running locally on the server
    LOCAL_MODE=true
    BASE_URL="http://localhost"
    echo "🧪 Testing Agentic Framework deployment (local mode)"
else
    # Running remotely, need SSH
    LOCAL_MODE=false
    
    # Auto-configured for remote
    SSH_USER=ubuntu
    PEM_KEY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)/king-ai-studio.pem"

    # Validate PEM key exists
    if [ ! -f "$PEM_KEY" ]; then
        echo "Error: PEM key file not found: $PEM_KEY"
        echo "Expected location: $(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)/king-ai-studio.pem"
        exit 1
    fi

    # Prompt for AWS_IP if not set
    if [ -z "$AWS_IP" ]; then
        read -p "Enter AWS instance IP address: " AWS_IP
    fi

    if [ -z "$AWS_IP" ]; then
        echo "Error: AWS_IP is required"
        exit 1
    fi

    BASE_URL="http://$AWS_IP"
    echo "🧪 Testing Agentic Framework deployment at $AWS_IP"
fi

echo "=================================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test function
test_endpoint() {
    local url=$1
    local name=$2
    echo -n "Testing $name... "

    if curl -s --max-time 10 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

# Test Ollama
echo -n "Testing Ollama... "
if [ "$LOCAL_MODE" = true ]; then
    if ollama list | grep -q deepseek 2>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
else
    if ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$AWS_IP" "ollama list | grep -q deepseek" 2>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
fi

# Test services
test_endpoint "$BASE_URL:8000/health" "Orchestrator API"
test_endpoint "$BASE_URL:8002/health" "Memory Service"
test_endpoint "$BASE_URL:8003/health" "Subagent Manager"
test_endpoint "$BASE_URL:8080/health" "MCP Gateway"
test_endpoint "$BASE_URL:8004/health" "Skill Executor"
test_endpoint "$BASE_URL:9000/minio/health/live" "MinIO"

# Test dashboard
echo -n "Testing Dashboard... "
if curl -s --max-time 10 "$BASE_URL" | grep -q "<!doctype html>"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${YELLOW}⚠️  FAIL (may need to build: cd /opt/agentic-framework/dashboard && sudo npm install && sudo npm run build)${NC}"
fi

echo ""
echo "📊 Docker service status:"
if [ "$LOCAL_MODE" = true ]; then
    cd /opt/agentic-framework && sudo docker compose ps
else
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$AWS_IP" "cd /opt/agentic-framework && sudo docker compose ps" 2>/dev/null || echo "Could not retrieve service status"
fi

echo ""
echo "🔍 System resource usage:"
if [ "$LOCAL_MODE" = true ]; then
    echo 'Memory:' && free -h && echo -e '\nDisk:' && df -h /
else
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$AWS_IP" "echo 'Memory:' && free -h && echo -e '\nDisk:' && df -h /" 2>/dev/null || echo "Could not retrieve system info"
fi

echo ""
echo -e "${GREEN}🌐 Service URLs:${NC}"
if [ "$LOCAL_MODE" = true ]; then
    # Get public IP for display - try multiple methods
    PUBLIC_IP=$(curl -s --max-time 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null)
    if [ -z "$PUBLIC_IP" ]; then
        PUBLIC_IP=$(curl -s --max-time 2 https://ipinfo.io/ip 2>/dev/null)
    fi
    if [ -z "$PUBLIC_IP" ]; then
        PUBLIC_IP=$(hostname -I | awk '{print $1}')
    fi
    if [ -z "$PUBLIC_IP" ]; then
        PUBLIC_IP="localhost"
    fi
    echo "  Dashboard:        http://$PUBLIC_IP"
    echo "  Orchestrator API: http://$PUBLIC_IP:8000"
    echo "  API Docs:         http://$PUBLIC_IP:8000/docs"
    echo "  Memory Service:   http://$PUBLIC_IP:8002"
    echo "  Subagent Manager: http://$PUBLIC_IP:8003"
    echo "  MCP Gateway:      http://$PUBLIC_IP:8080"
    echo "  Skill Executor:   http://$PUBLIC_IP:8004"
    echo "  MinIO Console:    http://$PUBLIC_IP:9001"
else
    echo "  Dashboard:        http://$AWS_IP"
    echo "  Orchestrator API: http://$AWS_IP:8000"
    echo "  API Docs:         http://$AWS_IP:8000/docs"
    echo "  Memory Service:   http://$AWS_IP:8002"
    echo "  Subagent Manager: http://$AWS_IP:8003"
    echo "  MCP Gateway:      http://$AWS_IP:8080"
    echo "  Skill Executor:   http://$AWS_IP:8004"
    echo "  MinIO Console:    http://$AWS_IP:9001"
fi
echo ""
echo "🎯 Next steps:"
if [ "$LOCAL_MODE" = true ]; then
    DISPLAY_IP=$PUBLIC_IP
else
    DISPLAY_IP=$AWS_IP
fi
echo "  1. Open the dashboard at http://$DISPLAY_IP"
echo "  2. Login with default credentials (admin/admin123)"
echo "  3. Create a workflow YAML file"
echo "  4. Monitor logs: docker compose logs -f [service]"
echo "  5. Configure production settings (SSL, auth, etc.)"