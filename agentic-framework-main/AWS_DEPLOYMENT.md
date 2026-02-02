# AWS Deployment Guide

Deploy the Agentic Framework to an AWS EC2 instance with a single Python script.

## Prerequisites

1. **AWS EC2 Instance**:
   - Ubuntu 22.04 LTS recommended
   - Minimum: t3.large (2 vCPU, 8GB RAM)
   - Recommended: t3.xlarge or larger (4 vCPU, 16GB RAM)
   - Storage: 50GB+ EBS volume
   - Security Group: Allow ports 22 (SSH), 80 (HTTP), 8000-8080 (APIs)

2. **Local Requirements**:
   - Python 3.7+ installed
   - SSH client (OpenSSH)
   - PEM key file: `king-ai-studio.pem` in parent directory

3. **Network**:
   - SSH access to EC2 instance
   - Internet connectivity for downloads

## Quick Deployment

### Single Command Deployment

```bash
python deploy.py
```

That's it! The script will:
1. ✅ Test SSH connection
2. 📦 Create deployment archive
3. 📤 Upload to server
4. 📂 Extract files
5. 🔧 Install dependencies (smart - skips if already installed)
6. ✅ Verify deployment

### What Gets Installed

The script intelligently checks for existing installations:

- **Docker & Docker Compose** - Container runtime
- **Ollama** - LLM inference engine  
- **DeepSeek R1 (14B)** - AI model
- **Node.js & npm** - Dashboard build tools
- **Nginx** - Web server for dashboard
- **PostgreSQL, Redis, MinIO** - Via Docker Compose

**First deployment:** ~15-20 minutes (downloads models)  
**Subsequent deployments:** ~3-5 minutes (reuses existing installs)

## Configuration

### Auto-Configured Settings

The script automatically configures:
- **IP Address**: 34.229.112.127 (edit in deploy.py if different)
- **SSH User**: ubuntu
- **PEM Key**: ../king-ai-studio.pem (relative to script)

### To Change IP Address

Edit `deploy.py`:
```python
AWS_IP = "your.ip.address.here"
```

## Deployment Output

```
==================================================
🚀 Agentic Framework Deployment to AWS
==================================================
Target: 34.229.112.127
User: ubuntu

[1/6] Testing SSH connection...
✅ SSH connection verified

[2/6] Preparing deployment package...
📦 Creating deployment archive...
  Added 1234 files
✅ Archive created: 45.3 MB

[3/6] Uploading to server...
✅ Upload complete

[4/6] Extracting on server...
✅ Files extracted

[5/6] Installing and configuring services...
[·] Checking Docker...
  ✓ Docker already installed
[·] Checking Ollama...
  → Installing Ollama...
  ✓ Ollama installed
[·] Checking Node.js...
  ✓ Node.js already installed
[·] Checking DeepSeek R1 model...
  → Pulling DeepSeek R1 model (this takes 5-10 min)...
  ✓ Model downloaded
[·] Configuring environment...
  ✓ Environment configured
[·] Building dashboard...
  ✓ Dashboard built
[·] Starting Docker services...
  ✓ Services started
[·] Configuring web server...
  ✓ Web server configured

✅ Deployment complete!

[6/6] Verifying deployment...
✅ API endpoint responding
✅ Dashboard accessible

==================================================
✅ DEPLOYMENT SUCCESSFUL!
==================================================

Access Points:
  Dashboard:    http://34.229.112.127
  API:          http://34.229.112.127:8000/health
  Memory:       http://34.229.112.127:8002/health
  Subagent Mgr: http://34.229.112.127:8003/health
  MCP Gateway:  http://34.229.112.127:8080/health

Deployment Time: 12m 34s

Next Steps:
  • Run tests: bash test-deployment.sh
  • View logs: ssh -i <pem> ubuntu@34.229.112.127 'cd /opt/agentic-framework && sudo docker compose logs'
  • Monitor: http://34.229.112.127/api/health
```

## Testing Deployment

```bash
bash test-deployment.sh
```

This will verify:
- ✅ Ollama service with DeepSeek R1
- ✅ Orchestrator API (port 8000)
- ✅ Memory Service (port 8002)
- ✅ Subagent Manager (port 8003)
- ✅ MCP Gateway (port 8080)
- ✅ Skill Executor (port 8004)
- ✅ MinIO storage (port 9000)
- ✅ Dashboard (port 80)

## Accessing the Deployment

### Dashboard
```
http://34.229.112.127
```
Web interface for interacting with the AI system.

### API Endpoints
```
http://34.229.112.127:8000/health    # Orchestrator
http://34.229.112.127:8002/health    # Memory Service
http://34.229.112.127:8003/health    # Subagent Manager
http://34.229.112.127:8080/health    # MCP Gateway
```

### SSH Access
```bash
ssh -i ../king-ai-studio.pem ubuntu@34.229.112.127
cd /opt/agentic-framework
sudo docker compose ps
sudo docker compose logs -f orchestrator
```

## Troubleshooting

### SSH Connection Failed

```bash
# Check instance is running
aws ec2 describe-instances --instance-ids i-xxxxx

# Check security group allows SSH from your IP
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Test connection manually
ssh -i ../king-ai-studio.pem ubuntu@34.229.112.127 "echo OK"
```

### Services Not Starting

```bash
ssh -i ../king-ai-studio.pem ubuntu@34.229.112.127
cd /opt/agentic-framework

# Check service status
sudo docker compose ps

# View logs
sudo docker compose logs orchestrator
sudo docker compose logs --tail=50 -f

# Restart services
sudo docker compose restart
```

### Dashboard Not Loading

```bash
# Check Nginx status
sudo systemctl status nginx

# Check dashboard files
ls -la /var/www/dashboard/

# Restart Nginx
sudo systemctl restart nginx
```

### Model Not Downloaded

```bash
# Check Ollama
ollama list

# Pull model manually
ollama pull deepseek-r1:14b

# Check Ollama service
sudo systemctl status ollama
```

## Updating Deployment

To update after code changes:

```bash
# Simply run deploy again
python deploy.py
```

The script will:
- Skip reinstalling existing software
- Update code files
- Rebuild only changed components
- Restart services with new code

## Monitoring

### View Service Logs
```bash
ssh -i ../king-ai-studio.pem ubuntu@34.229.112.127 \
  'cd /opt/agentic-framework && sudo docker compose logs -f'
```

### Check Resource Usage
```bash
ssh -i ../king-ai-studio.pem ubuntu@34.229.112.127 \
  'free -h && df -h && docker stats --no-stream'
```

### Monitor API Health
```bash
while true; do
  curl -s http://34.229.112.127:8000/health | jq .
  sleep 5
done
```

## Cleanup

### Stop Services
```bash
ssh -i ../king-ai-studio.pem ubuntu@34.229.112.127 \
  'cd /opt/agentic-framework && sudo docker compose down'
```

### Remove Deployment
```bash
ssh -i ../king-ai-studio.pem ubuntu@34.229.112.127 \
  'sudo rm -rf /opt/agentic-framework'
```

## Production Considerations

1. **SSL/TLS**: Set up HTTPS with Let's Encrypt
2. **Firewall**: Restrict access to known IPs
3. **Secrets**: Change default passwords in .env
4. **Backups**: Configure automated backups for PostgreSQL
5. **Monitoring**: Set up CloudWatch or Prometheus
6. **Scaling**: Consider load balancer for multiple instances
7. **Updates**: Implement rolling update strategy

## Architecture

```
┌─────────────────┐
│   Dashboard     │  (Port 80)
│   (Nginx)       │
└────────┬────────┘
         │
┌────────▼────────────────────────────────┐
│         AWS EC2 Instance                │
│  ┌──────────────────────────────────┐   │
│  │  Orchestrator API    (8000)      │   │
│  │  Memory Service      (8002)      │   │
│  │  Subagent Manager    (8003)      │   │
│  │  MCP Gateway         (8080)      │   │
│  │  Skill Executor      (8004)      │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  Ollama + DeepSeek R1            │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  PostgreSQL, Redis, MinIO        │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Support

For issues or questions:
- Check service logs: `sudo docker compose logs`
- Review test output: `bash test-deployment.sh`
- Verify connectivity: `curl http://34.229.112.127:8000/health`
