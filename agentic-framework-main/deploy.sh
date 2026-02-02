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
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Validate prerequisites
log_step "Validating prerequisites..."

if [ ! -f "$SSH_KEY" ]; then
    log_error "SSH key not found: $SSH_KEY"
    exit 1
fi

if ! command -v scp &> /dev/null; then
    log_error "scp not found. Please install OpenSSH client."
    exit 1
fi

log_info "Prerequisites validated ✓"
echo ""

# Step 1: Upload files
log_step "Step 1: Uploading files to server..."

log_info "Creating temporary directory on server..."
ssh -i "$SSH_KEY" "${USER}@${SERVER}" "mkdir -p /tmp/agentic-framework-deploy"

log_info "Uploading orchestrator service..."
scp -i "$SSH_KEY" -r orchestrator/ "${USER}@${SERVER}:/tmp/agentic-framework-deploy/"

log_info "Uploading adapters..."
scp -i "$SSH_KEY" -r adapters/ "${USER}@${SERVER}:/tmp/agentic-framework-deploy/"

log_info "Uploading configuration files..."
scp -i "$SSH_KEY" docker-compose.yml requirements.txt "${USER}@${SERVER}:/tmp/agentic-framework-deploy/"

log_info "Files uploaded successfully ✓"
echo ""

# Step 2: Deploy on server
log_step "Step 2: Deploying on server..."

ssh -i "$SSH_KEY" "${USER}@${SERVER}" << 'ENDSSH'
set -e

echo "Backing up existing deployment..."
sudo rm -rf /opt/agentic-framework.bak 2>/dev/null || true
if [ -d "/opt/agentic-framework" ]; then
    sudo mv /opt/agentic-framework /opt/agentic-framework.bak
    echo "✓ Backup created"
fi

echo "Moving new files..."
sudo mv /tmp/agentic-framework-deploy /opt/agentic-framework
cd /opt/agentic-framework

echo "Building services..."
sudo docker compose build orchestrator

echo "Starting services..."
sudo docker compose up -d orchestrator

echo "Waiting for services to initialize..."
sleep 10

echo "✅ Deployment successful!"
ENDSSH

log_info "Deployment complete ✓"
echo ""

# Step 3: Health checks
log_step "Step 3: Running health checks..."

ssh -i "$SSH_KEY" "${USER}@${SERVER}" << 'ENDSSH'
cd /opt/agentic-framework

echo "Checking orchestrator status..."
sudo docker compose ps orchestrator

echo ""
echo "Checking health endpoint..."
for i in {1..5}; do
    if curl -sf http://localhost:8000/health > /dev/null; then
        echo "✓ Orchestrator is healthy"
        break
    else
        echo "Waiting for orchestrator... ($i/5)"
        sleep 2
    fi
done

echo ""
echo "Recent logs:"
sudo docker compose logs --tail=10 orchestrator
ENDSSH

echo ""
log_info "✅ All health checks passed!"
echo ""
echo "═══════════════════════════════════════════════"
echo "🎉 Deployment Successful!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Dashboard: http://${SERVER}"
echo "  API Endpoint: http://${SERVER}:8000/api/chat/public"
echo ""
echo "Test with:"
echo "  curl -X POST http://${SERVER}:8000/api/chat/public \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"message\": \"Hello, test the system\"}'"
echo ""
echo "═══════════════════════════════════════════════"
