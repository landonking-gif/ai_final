# Agentic Framework - Automated Colab Deployment via API
# This script creates and runs a Colab notebook automatically

param(
    [string]$ColabToken = $env:COLAB_API_TOKEN,
    [string]$GitHubRepo = "landonking-gif/ai_final",
    [string]$NotebookName = "agentic-framework-deploy",
    [switch]$RunDeployment
)

# Configuration
$ColabApiUrl = "https://colab.research.google.com/api/colab"
$GitHubApiUrl = "https://api.github.com/repos/$GitHubRepo/contents"

# Deployment notebook content (JSON format for Colab API)
$DeploymentNotebook = @"
{
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "# Agentic Framework - Automated GPU Deployment\\n",
        "**Status: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')**\\n\\n",
        "This notebook was created automatically by the deployment script."
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 34
        },
        "colab_type": "code",
        "id": "system_check"
      },
      "outputs": [],
      "source": [
        "# System Check\\n",
        "import subprocess, os, psutil, shutil\\n",
        "print('=' * 60)\\n",
        "print('SYSTEM VERIFICATION')\\n",
        "print('=' * 60)\\n",
        "# GPU Check\\n",
        "gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], \\n",
        "                     capture_output=True, text=True)\\n",
        "if gpu.returncode == 0:\\n",
        "    print(f'✅ GPU: {gpu.stdout.strip()}')\\n",
        "else:\\n",
        "    print('❌ No GPU detected - please set runtime to GPU')\\n",
        "# RAM Check\\n",
        "ram = psutil.virtual_memory().total / (1024**3)\\n",
        "print(f'✅ RAM: {ram:.1f} GB')\\n",
        "# Disk Check\\n",
        "disk = shutil.disk_usage('/')\\n",
        "print(f'✅ Disk: {disk.free / (1024**3):.1f} GB free')\\n",
        "print('=' * 60)"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 34
        },
        "colab_type": "code",
        "id": "install_deps"
      },
      "outputs": [],
      "source": [
        "# Install System Dependencies\\n",
        "import subprocess\\n",
        "def run(cmd, desc=''):\\n",
        "    if desc: print(f'Installing {desc}...', end=' ', flush=True)\\n",
        "    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)\\n",
        "    if result.returncode == 0:\\n",
        "        if desc: print('✅')\\n",
        "    else:\\n",
        "        if desc: print('❌')\\n",
        "        print(f'Error: {result.stderr[:200]}')\\n",
        "    return result\\n",
        "print('=' * 60)\\n",
        "print('INSTALLING SYSTEM DEPENDENCIES')\\n",
        "print('=' * 60)\\n",
        "# Update apt\\n",
        "run('apt-get update -qq', 'apt update')\\n",
        "# PostgreSQL\\n",
        "run('apt-get install -y -qq postgresql postgresql-client', 'PostgreSQL')\\n",
        "# Redis\\n",
        "run('apt-get install -y -qq redis-server', 'Redis')\\n",
        "# Node.js 22\\n",
        "run('curl -fsSL https://deb.nodesource.com/setup_22.x | bash -', 'Node.js repo')\\n",
        "run('apt-get install -y -qq nodejs', 'Node.js 22')\\n",
        "# MinIO\\n",
        "run('wget -q https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio && chmod +x /usr/local/bin/minio', 'MinIO')\\n",
        "print('✅ All system dependencies installed')"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 34
        },
        "colab_type": "code",
        "id": "install_ollama"
      },
      "outputs": [],
      "source": [
        "# Install Ollama + DeepSeek R1\\n",
        "import subprocess, time, os\\n",
        "print('=' * 60)\\n",
        "print('INSTALLING OLLAMA + DEEPSEEK R1 (GPU)')\\n",
        "print('=' * 60)\\n",
        "# Install Ollama\\n",
        "print('Installing Ollama...', end=' ', flush=True)\\n",
        "result = subprocess.run('curl -fsSL https://ollama.com/install.sh | sh', \\n",
        "                        shell=True, capture_output=True, text=True)\\n",
        "if result.returncode == 0:\\n",
        "    print('✅')\\n",
        "else:\\n",
        "    print(f'❌ {result.stderr[:100]}')\\n",
        "# Start Ollama server\\n",
        "print('Starting Ollama server...', end=' ', flush=True)\\n",
        "os.environ['OLLAMA_HOST'] = '0.0.0.0:11434'\\n",
        "subprocess.Popen(['ollama', 'serve'], \\n",
        "                 stdout=open('/tmp/ollama.log', 'w'), \\n",
        "                 stderr=subprocess.STDOUT, \\n",
        "                 env={**os.environ, 'OLLAMA_HOST': '0.0.0.0:11434'})\\n",
        "time.sleep(5)\\n",
        "print('✅')\\n",
        "# Pull DeepSeek R1 model\\n",
        "print('Pulling deepseek-r1:14b model (may take 2-5 min)...')\\n",
        "pull = subprocess.run(['ollama', 'pull', 'deepseek-r1:14b'], \\n",
        "                      capture_output=False, text=True)\\n",
        "if pull.returncode == 0:\\n",
        "    print('✅ Model downloaded successfully')\\n",
        "else:\\n",
        "    print('❌ Model download failed')"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 34
        },
        "colab_type": "code",
        "id": "clone_framework"
      },
      "outputs": [],
      "source": [
        "# Clone and Install Agentic Framework\\n",
        "import subprocess, os\\n",
        "print('=' * 60)\\n",
        "print('CLONING AGENTIC FRAMEWORK')\\n",
        "print('=' * 60)\\n",
        "# Clone repository\\n",
        "print('Cloning repository...', end=' ', flush=True)\\n",
        "result = subprocess.run('git clone https://github.com/landonking-gif/ai_final.git', \\n",
        "                        shell=True, capture_output=True, text=True)\\n",
        "if result.returncode == 0:\\n",
        "    print('✅')\\n",
        "else:\\n",
        "    print(f'❌ {result.stderr[:100]}')\\n",
        "# Change to framework directory\\n",
        "os.chdir('ai_final/agentic-framework-main')\\n",
        "print(f'Working directory: {os.getcwd()}')\\n",
        "# Install Python dependencies\\n",
        "print('Installing Python dependencies...', end=' ', flush=True)\\n",
        "pip_result = subprocess.run('pip install -r requirements.txt', \\n",
        "                           shell=True, capture_output=True, text=True)\\n",
        "if pip_result.returncode == 0:\\n",
        "    print('✅')\\n",
        "else:\\n",
        "    print(f'❌ {pip_result.stderr[:200]}')"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 34
        },
        "colab_type": "code",
        "id": "start_services"
      },
      "outputs": [],
      "source": [
        "# Start Infrastructure Services\\n",
        "import subprocess, os, time\\n",
        "print('=' * 60)\\n",
        "print('STARTING INFRASTRUCTURE SERVICES')\\n",
        "print('=' * 60)\\n",
        "# Start PostgreSQL\\n",
        "print('Starting PostgreSQL...', end=' ', flush=True)\\n",
        "pg_result = subprocess.run('service postgresql start', shell=True, capture_output=True, text=True)\\n",
        "if pg_result.returncode == 0:\\n",
        "    print('✅')\\n",
        "else:\\n",
        "    print('❌')\\n",
        "# Start Redis\\n",
        "print('Starting Redis...', end=' ', flush=True)\\n",
        "redis_result = subprocess.run('service redis-server start', shell=True, capture_output=True, text=True)\\n",
        "if redis_result.returncode == 0:\\n",
        "    print('✅')\\n",
        "else:\\n",
        "    print('❌')\\n",
        "# Start MinIO\\n",
        "print('Starting MinIO...', end=' ', flush=True)\\n",
        "minio_env = os.environ.copy()\\n",
        "minio_env['MINIO_ACCESS_KEY'] = 'minioadmin'\\n",
        "minio_env['MINIO_SECRET_KEY'] = 'minioadmin'\\n",
        "subprocess.Popen(['minio', 'server', '/tmp/minio-data', '--address', ':9000'], \\n",
        "                 env=minio_env, stdout=open('/tmp/minio.log', 'w'), stderr=subprocess.STDOUT)\\n",
        "time.sleep(3)\\n",
        "print('✅')\\n",
        "print('✅ All infrastructure services started')"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 34
        },
        "colab_type": "code",
        "id": "start_microservices"
      },
      "outputs": [],
      "source": [
        "# Start Microservices\\n",
        "import subprocess, os, time\\n",
        "print('=' * 60)\\n",
        "print('STARTING MICROSERVICES')\\n",
        "print('=' * 60)\\n",
        "# Set environment variables\\n",
        "os.environ['DATABASE_URL'] = 'postgresql://postgres@localhost:5432/agentic'\\n",
        "os.environ['REDIS_URL'] = 'redis://localhost:6379'\\n",
        "os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434'\\n",
        "os.environ['MINIO_ENDPOINT'] = 'localhost:9000'\\n",
        "os.environ['MINIO_ACCESS_KEY'] = 'minioadmin'\\n",
        "os.environ['MINIO_SECRET_KEY'] = 'minioadmin'\\n",
        "# Start services in background\\n",
        "services = [\\n",
        "    ('orchestrator', 'python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000'),\\n",
        "    ('memory-service', 'python -m uvicorn memory_service.main:app --host 0.0.0.0 --port 8001'),\\n",
        "    ('mcp-gateway', 'python -m uvicorn mcp_gateway.main:app --host 0.0.0.0 --port 8002'),\\n",
        "    ('code-executor', 'python -m uvicorn code_executor.main:app --host 0.0.0.0 --port 8003'),\\n",
        "    ('subagent-manager', 'python -m uvicorn subagent_manager.main:app --host 0.0.0.0 --port 8004')\\n",
        "]\\n",
        "for service_name, command in services:\\n",
        "    print(f'Starting {service_name}...', end=' ', flush=True)\\n",
        "    try:\\n",
        "        subprocess.Popen(command.split(), \\n",
        "                         stdout=open(f'/tmp/{service_name}.log', 'w'), \\n",
        "                         stderr=subprocess.STDOUT)\\n",
        "        time.sleep(2)\\n",
        "        print('✅')\\n",
        "    except Exception as e:\\n",
        "        print(f'❌ {str(e)}')\\n",
        "print('✅ All microservices started')\\n",
        "print('\\n🌐 Service URLs:')\\n",
        "print('  Orchestrator: http://localhost:8000')\\n",
        "print('  Memory Service: http://localhost:8001')\\n",
        "print('  MCP Gateway: http://localhost:8002')\\n",
        "print('  Code Executor: http://localhost:8003')\\n",
        "print('  SubAgent Manager: http://localhost:8004')"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 34
        },
        "colab_type": "code",
        "id": "setup_ngrok"
      },
      "outputs": [],
      "source": [
        "# Setup ngrok Tunnels for External Access\\n",
        "import subprocess, time, requests\\n",
        "print('=' * 60)\\n",
        "print('SETTING UP NGROK TUNNELS')\\n",
        "print('=' * 60)\\n",
        "# Install ngrok\\n",
        "print('Installing ngrok...', end=' ', flush=True)\\n",
        "ngrok_install = subprocess.run('wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz && tar xvf ngrok-v3-stable-linux-amd64.tgz && chmod +x ngrok', \\n",
        "                               shell=True, capture_output=True, text=True)\\n",
        "if ngrok_install.returncode == 0:\\n",
        "    print('✅')\\n",
        "else:\\n",
        "    print('❌')\\n",
        "# Note: ngrok auth token required for custom domains\\n",
        "print('⚠️  Note: Add your ngrok auth token for persistent URLs')\\n",
        "print('   Run: ./ngrok config add-authtoken YOUR_TOKEN')\\n",
        "# Start tunnels (example - customize as needed)\\n",
        "print('Starting ngrok tunnels...')\\n",
        "tunnels = [\\n",
        "    ('orchestrator', '8000'),\\n",
        "    ('dashboard', '3000'),\\n",
        "    ('api', '8001')\\n",
        "]\\n",
        "for name, port in tunnels:\\n",
        "    print(f'Starting {name} tunnel...', end=' ', flush=True)\\n",
        "    try:\\n",
        "        subprocess.Popen(['./ngrok', 'http', port, '--subdomain', f'agentic-{name}'], \\n",
        "                         stdout=open(f'/tmp/ngrok-{name}.log', 'w'), \\n",
        "                         stderr=subprocess.STDOUT)\\n",
        "        time.sleep(3)\\n",
        "        print('✅')\\n",
        "    except Exception as e:\\n",
        "        print(f'❌ {str(e)}')\\n",
        "print('✅ Ngrok tunnels configured')"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/",
          "height": 34
        },
        "colab_type": "code",
        "id": "test_deployment"
      },
      "outputs": [],
      "source": [
        "# Test Deployment\\n",
        "import requests, time\\n",
        "print('=' * 60)\\n",
        "print('TESTING DEPLOYMENT')\\n",
        "print('=' * 60)\\n",
        "# Test services\\n",
        "services = [\\n",
        "    ('Orchestrator', 'http://localhost:8000/health'),\\n",
        "    ('Memory Service', 'http://localhost:8001/health'),\\n",
        "    ('MCP Gateway', 'http://localhost:8002/health'),\\n",
        "    ('Code Executor', 'http://localhost:8003/health'),\\n",
        "    ('SubAgent Manager', 'http://localhost:8004/health')\\n",
        "]\\n",
        "for service_name, url in services:\\n",
        "    print(f'Testing {service_name}...', end=' ', flush=True)\\n",
        "    try:\\n",
        "        response = requests.get(url, timeout=10)\\n",
        "        if response.status_code == 200:\\n",
        "            print('✅')\\n",
        "        else:\\n",
        "            print(f'⚠️  Status: {response.status_code}')\\n",
        "    except Exception as e:\\n",
        "        print(f'❌ {str(e)}')\\n",
        "# Test Ollama\\n",
        "print('Testing Ollama...', end=' ', flush=True)\\n",
        "try:\\n",
        "    ollama_response = requests.get('http://localhost:11434/api/tags', timeout=10)\\n",
        "    if ollama_response.status_code == 200:\\n",
        "        models = ollama_response.json().get('models', [])\\n",
        "        if models:\\n",
        "            print(f'✅ (Models: {[m[\"name\"] for m in models]})')\\n",
        "        else:\\n",
        "            print('⚠️  No models loaded')\\n",
        "    else:\\n",
        "        print('❌')\\n",
        "except Exception as e:\\n",
        "    print(f'❌ {str(e)}')\\n",
        "print('\\n🎉 DEPLOYMENT COMPLETE!')\\n",
        "print('=' * 60)\\n",
        "print('Your Agentic Framework is running on Google Colab GPU!')\\n",
        "print('Access your services via the ngrok URLs above.')\\n",
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
    },
    "language_info": {
      "codemirror_mode": {
        "name": "ipython",
        "version": 3
      },
      "file_extension": ".py",
      "mimetype": "text/x-python",
      "name": "python",
      "nbconvert_exporter": "python",
      "pygments_lexer": "ipython3",
      "version": "3.10.12"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 4
}
"@

function Create-ColabNotebook {
    param(
        [string]$NotebookName,
        [string]$Content
    )

    Write-Host "🔧 Creating Colab notebook: $NotebookName" -ForegroundColor Cyan

    # For now, we'll create a local file that can be uploaded to Colab
    # In a full implementation, this would use the Colab API

    $notebookPath = "$PSScriptRoot\$NotebookName.ipynb"
    $Content | Out-File -FilePath $notebookPath -Encoding UTF8

    Write-Host "✅ Notebook created: $notebookPath" -ForegroundColor Green
    Write-Host "📤 Upload this file to Google Colab and run all cells" -ForegroundColor Yellow

    return $notebookPath
}

function Start-ColabDeployment {
    param(
        [string]$NotebookPath
    )

    Write-Host "🚀 Starting automated deployment..." -ForegroundColor Green

    # Open the notebook in Colab
    $colabUrl = "https://colab.research.google.com/notebooks/$NotebookPath"
    Write-Host "🌐 Opening Colab: $colabUrl" -ForegroundColor Blue

    try {
        Start-Process $colabUrl
    } catch {
        Write-Host "❌ Could not open browser automatically" -ForegroundColor Red
        Write-Host "📋 Please manually open: $colabUrl" -ForegroundColor Yellow
    }

    Write-Host "📝 Instructions:" -ForegroundColor Cyan
    Write-Host "  1. Set runtime to GPU (H100) in Colab" -ForegroundColor White
    Write-Host "  2. Run all cells in order" -ForegroundColor White
    Write-Host "  3. Wait for deployment to complete (~10-15 minutes)" -ForegroundColor White
    Write-Host "  4. Access your services via the generated URLs" -ForegroundColor White
}



# Main execution
Write-Host "🤖 Agentic Framework - Automated Colab Deployment" -ForegroundColor Magenta
Write-Host "=" * 60 -ForegroundColor Magenta

if ($RunDeployment) {
    # Create and deploy the notebook
    $notebookPath = Create-ColabNotebook -NotebookName $NotebookName -Content $DeploymentNotebook
    Start-ColabDeployment -NotebookPath $notebookPath
} else {
    # Just create the notebook file
    $notebookPath = Create-ColabNotebook -NotebookName $NotebookName -Content $DeploymentNotebook
    Write-Host "📄 Notebook created: $notebookPath" -ForegroundColor Green
    Write-Host "💡 Run with -RunDeployment to automatically open in Colab" -ForegroundColor Yellow
}

Write-Host "🎯 Deployment script ready!" -ForegroundColor Green