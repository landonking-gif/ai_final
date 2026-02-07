# Agentic Framework - Colab Deployment Script
# Simple automated deployment using GitHub and Colab

param(
    [switch]$CreateNotebook,
    [switch]$OpenColab
)

Write-Host "🤖 Agentic Framework - Colab GPU Deployment" -ForegroundColor Magenta
Write-Host "=" * 50 -ForegroundColor Magenta

$notebookName = "agentic-framework-deploy-auto"
$notebookPath = "$PSScriptRoot\$notebookName.ipynb"
$githubUrl = "https://github.com/landonking-gif/ai_final/blob/main/$notebookName.ipynb"
$colabUrl = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/$notebookName.ipynb"

if ($CreateNotebook) {
    Write-Host "📝 Creating automated deployment notebook..." -ForegroundColor Cyan

    # Create a simplified notebook with the deployment steps
    $notebookContent = @"
{
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "# 🤖 Agentic Framework - Automated GPU Deployment\\n",
        "**Created:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')\\n\\n",
        "This notebook automatically deploys the full Agentic Framework stack on Colab GPU."
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {},
      "outputs": [],
      "source": [
        "# 🚀 ONE-CLICK DEPLOYMENT\\n",
        "import subprocess, os, time\\n",
        "print('🚀 Starting Agentic Framework deployment...')\\n",
        "print('=' * 60)\\n",
        "# Install system dependencies\\n",
        "print('📦 Installing system dependencies...')\\n",
        "!apt-get update -qq && apt-get install -y -qq postgresql redis-server\\n",
        "!curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y -qq nodejs\\n",
        "!wget -q https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio && chmod +x /usr/local/bin/minio\\n",
        "print('✅ System dependencies installed')\\n",
        "# Install Ollama\\n",
        "print('🤖 Installing Ollama...')\\n",
        "!curl -fsSL https://ollama.com/install.sh | sh\\n",
        "import subprocess\\n",
        "subprocess.Popen(['ollama', 'serve'], stdout=open('/tmp/ollama.log', 'w'), stderr=subprocess.STDOUT)\\n",
        "time.sleep(5)\\n",
        "print('✅ Ollama installed and running')\\n",
        "# Pull DeepSeek model\\n",
        "print('🧠 Pulling DeepSeek R1 14B model (may take 2-5 min)...')\\n",
        "!ollama pull deepseek-r1:14b\\n",
        "print('✅ Model downloaded')\\n",
        "# Clone and setup framework\\n",
        "print('🔄 Cloning Agentic Framework...')\\n",
        "!git clone https://github.com/landonking-gif/ai_final.git\\n",
        "%cd ai_final/agentic-framework-main\\n",
        "!pip install -r requirements.txt\\n",
        "print('✅ Framework cloned and dependencies installed')\\n",
        "# Start services\\n",
        "print('⚡ Starting services...')\\n",
        "!service postgresql start\\n",
        "!service redis-server start\\n",
        "import os\\n",
        "os.environ['MINIO_ACCESS_KEY'] = 'minioadmin'\\n",
        "os.environ['MINIO_SECRET_KEY'] = 'minioadmin'\\n",
        "subprocess.Popen(['minio', 'server', '/tmp/minio-data', '--address', ':9000'], env=os.environ.copy())\\n",
        "time.sleep(3)\\n",
        "print('✅ Infrastructure services started')\\n",
        "# Start microservices\\n",
        "services = [\\n",
        "    ('orchestrator', 'python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000'),\\n",
        "    ('memory-service', 'python -m uvicorn memory_service.main:app --host 0.0.0.0 --port 8001'),\\n",
        "    ('mcp-gateway', 'python -m uvicorn mcp_gateway.main:app --host 0.0.0.0 --port 8002'),\\n",
        "    ('code-executor', 'python -m uvicorn code_executor.main:app --host 0.0.0.0 --port 8003'),\\n",
        "    ('subagent-manager', 'python -m uvicorn subagent_manager.main:app --host 0.0.0.0 --port 8004')\\n",
        "]\\n",
        "for name, cmd in services:\\n",
        "    subprocess.Popen(cmd.split(), stdout=open(f'/tmp/{name}.log', 'w'), stderr=subprocess.STDOUT)\\n",
        "    time.sleep(2)\\n",
        "print('✅ All microservices started')\\n",
        "# Setup ngrok\\n",
        "print('🌐 Setting up ngrok tunnels...')\\n",
        "!wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz\\n",
        "!tar xvf ngrok-v3-stable-linux-amd64.tgz && chmod +x ngrok\\n",
        "# Start tunnels\\n",
        "tunnels = [('orchestrator', '8000'), ('dashboard', '3000'), ('api', '8001')]\\n",
        "for name, port in tunnels:\\n",
        "    subprocess.Popen(['./ngrok', 'http', port], stdout=open(f'/tmp/ngrok-{name}.log', 'w'), stderr=subprocess.STDOUT)\\n",
        "time.sleep(3)\\n",
        "print('✅ Ngrok tunnels configured')\\n",
        "# Final status\\n",
        "print('\\n🎉 DEPLOYMENT COMPLETE!')\\n",
        "print('=' * 60)\\n",
        "print('🌐 Service URLs:')\\n",
        "print('  Orchestrator: http://localhost:8000')\\n",
        "print('  Memory Service: http://localhost:8001')\\n",
        "print('  MCP Gateway: http://localhost:8002')\\n",
        "print('  Code Executor: http://localhost:8003')\\n",
        "print('  SubAgent Manager: http://localhost:8004')\\n",
        "print('\\n🔗 Check ngrok logs for public URLs')\\n",
        "print('=' * 60)"
      ]
    }
  ],
  "metadata": {
    "accelerator": "GPU",
    "colab": {
      "gpuType": "H100",
      "machine_shape": "hm",
      "provenance": []
    },
    "kernelspec": {
      "display_name": "Python 3",
      "language": "python",
      "name": "python3"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 4
}
"@

    $notebookContent | Out-File -FilePath $notebookPath -Encoding UTF8
    Write-Host "✅ Notebook created: $notebookPath" -ForegroundColor Green
}

if ($OpenColab) {
    Write-Host "🌐 Opening notebook in Google Colab..." -ForegroundColor Blue
    try {
        Start-Process $colabUrl
        Write-Host "✅ Colab opened successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Could not open browser automatically" -ForegroundColor Red
        Write-Host "📋 Please manually open: $colabUrl" -ForegroundColor Yellow
    }
}

# Default behavior: create notebook and show instructions
if (-not $CreateNotebook -and -not $OpenColab) {
    Write-Host "📝 To create the deployment notebook:" -ForegroundColor Cyan
    Write-Host "   .\deploy-colab-automation.ps1 -CreateNotebook" -ForegroundColor White
    Write-Host "" -ForegroundColor Cyan
    Write-Host "🌐 To open in Colab after creating:" -ForegroundColor Cyan
    Write-Host "   .\deploy-colab-automation.ps1 -OpenColab" -ForegroundColor White
    Write-Host "" -ForegroundColor Cyan
    Write-Host "⚡ One-click deployment:" -ForegroundColor Cyan
    Write-Host "   .\deploy-colab-automation.ps1 -CreateNotebook -OpenColab" -ForegroundColor White
    Write-Host "" -ForegroundColor Cyan
    Write-Host "📋 Manual steps:" -ForegroundColor Yellow
    Write-Host "  1. Create notebook: $notebookName.ipynb" -ForegroundColor White
    Write-Host "  2. Upload to Colab: $colabUrl" -ForegroundColor White
    Write-Host "  3. Set runtime to GPU (H100)" -ForegroundColor White
    Write-Host "  4. Run the single deployment cell" -ForegroundColor White
}

Write-Host "🎯 Ready for automated deployment!" -ForegroundColor Green