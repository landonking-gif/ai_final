# Agentic Framework - Colab Deployment Suite

This deployment suite provides multiple ways to automatically deploy the full Agentic Framework stack on Google Colab with GPU acceleration.

## 🚀 Quick Start

Choose your preferred deployment method:

### Option 1: PowerShell (Recommended for Windows)
```powershell
.\deploy_colab_simple.ps1
```

### Option 2: Batch File (Windows)
```batch
deploy_colab_simple.bat
```

### Option 3: Python Script (Cross-platform)
```bash
python deploy_colab_cli.py
```

## 📋 What Gets Deployed

The automated deployment includes:

- **Ollama + DeepSeek R1 14B** (GPU-accelerated LLM)
- **PostgreSQL** (relational database)
- **Redis** (caching & pub/sub)
- **ChromaDB** (vector database)
- **MinIO** (object storage)
- **5 Microservices**:
  - Orchestrator (main agent coordination)
  - Memory Service (persistent memory)
  - Subagent Manager (agent lifecycle)
  - MCP Gateway (tool integration)
  - Code Executor (safe code execution)
- **React Dashboard** (web interface)
- **ngrok Tunnels** (external access)

## 🔧 How It Works

The deployment scripts open the `colab_auto_run.ipynb` notebook **directly from your public GitHub repository** in Google Colab.

1. **Script opens**: `https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb`
2. **Colab loads** the notebook from GitHub
3. **You manually run** "Runtime > Run all"
4. **Notebook deploys** the full stack automatically

## ⚠️ Important Notes

- **GPU Required**: Colab GPU runtime is essential for Ollama/DeepSeek R1
- **Browser Login**: You must be logged into Google Colab
- **Manual Execution**: You need to run "Runtime > Run all" in Colab
- **colab-cli**: Automatically installed if missing
- **Google Drive**: Notebook gets uploaded to your Drive

## 🔍 Troubleshooting

### Common Issues

**"Repository not found"**
- Make sure the repository `landonking-gif/ai_final` is public
- Check that `colab_auto_run.ipynb` exists in the main branch

**"Runtime disconnected"**
- The notebook includes a keep-alive watchdog
- If it happens, re-run the last few cells

**"GPU not available"**
- Change runtime type to GPU (T4 or H100)
- Free tier has GPU limits - upgrade if needed

**"ngrok tunnel failed"**
- Check ngrok authentication in Cell 2
- Free tier has usage limits

### Getting Help

1. Check the script output for detailed error messages
2. Verify all cells executed successfully (green checkmarks)
3. Look for public URLs in the notebook output
4. Test API endpoints with curl or Postman

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐
│   React Dashboard │  │   External APIs   │
│   (Port 3000)     │  │   (ngrok URLs)    │
└─────────┬─────────┘  └─────────┬────────┘
          │                      │
┌─────────▼─────────┐  ┌─────────▼────────┐
│   MCP Gateway     │  │   Orchestrator    │
│   (Port 8001)     │  │   (Port 8000)     │
└─────────┬─────────┘  └─────────┬────────┘
          │                      │
┌─────────▼─────────┐  ┌─────────▼────────┐
│  Subagent Manager │  │  Memory Service  │
│   (Port 8002)     │  │   (Port 8003)     │
└─────────┬─────────┘  └─────────┬────────┘
          │                      │
┌─────────▼─────────┐  ┌─────────▼────────┐
│  Code Executor    │  │   Infrastructure │
│   (Port 8004)     │  │  PostgreSQL/Redis │
└───────────────────┘  │  ChromaDB/MinIO  │
                       └──────────────────┘
                              │
                       ┌──────▼──────┐
                       │   Ollama    │
                       │ DeepSeek R1 │
                       │  (GPU)      │
                       └─────────────┘
```

## 🎯 API Endpoints

After successful deployment, you'll have access to:

- **Dashboard**: `https://xxxxx.ngrok.io` (React web interface)
- **Orchestrator API**: `https://xxxxx.ngrok.io/api/v1/agents`
- **Memory Service**: `https://xxxxx.ngrok.io/api/v1/memory`
- **MCP Gateway**: `https://xxxxx.ngrok.io/api/v1/tools`

## 🔄 Development vs Production

This Colab deployment is perfect for:
- **Development**: Quick testing and prototyping
- **Demos**: Showcasing agent capabilities
- **Learning**: Understanding the framework architecture

For production use, consider:
- Dedicated GPU instances (AWS, GCP, Azure)
- Persistent databases (not ephemeral Colab storage)
- Load balancers and auto-scaling
- Proper authentication and security

## 📞 Support

If you encounter issues:
1. Check this README and troubleshooting section
2. Review the notebook execution logs
3. Verify your Colab environment (GPU, login status)
4. Test with a fresh Colab runtime

Happy deploying! 🚀