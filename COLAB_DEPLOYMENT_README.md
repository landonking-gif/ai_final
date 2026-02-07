# Agentic Framework - Colab Deployment Guide

## 🚀 Deployment Options

Choose the deployment method that best fits your needs:

### 1. **Simple CLI Menu** (Recommended) - `deploy_cli_menu.ps1`
**Best for:** Most users who want CLI control without complexity
- ✅ **Zero OAuth issues** - Uses reliable GitHub integration
- ✅ **Interactive menu** - Choose what you want to do
- ✅ **Browser automation** - Opens Colab automatically
- ✅ **Status checking** - Verify GitHub accessibility
- ✅ **Step-by-step guidance** - Clear instructions for each step

```powershell
.\deploy_cli_menu.ps1
```

### 2. **Hybrid CLI** - `deploy_hybrid_cli.ps1`
**Best for:** Users who want automation but need browser fallback
- ✅ **Automated browser control** - Selenium automation
- ✅ **GPU runtime setup** - Automatic configuration
- ✅ **Deployment monitoring** - Live progress tracking
- ⚠️ **Requires Chrome** - Browser automation dependency

```powershell
.\deploy_hybrid_cli.ps1
```

### 3. **Direct Colab Open** - `deploy-colab-simple.ps1`
**Best for:** Quick deployment with minimal CLI interaction
- ✅ **One-command deployment** - Opens Colab instantly
- ✅ **Clear instructions** - Terminal guidance
- ✅ **GitHub integration** - No manual file uploads

```powershell
.\deploy-colab-simple.ps1
```

### 4. **Full CLI (OAuth)** - `deploy_full_cli.ps1` ⚠️
**Status:** Currently has OAuth issues with Google
- ❌ **OAuth problems** - Google authentication failing
- ❌ **Complex setup** - Requires Google Cloud Console
- ❌ **Unreliable** - May not work due to API changes

## 🎯 Quick Start (Recommended)

1. **Run the CLI menu:**
   ```powershell
   .\deploy_cli_menu.ps1
   ```

2. **Choose option 1** (Open Colab)

3. **Follow the on-screen instructions**

## 📋 What Gets Deployed

All methods deploy the same complete system:

- **🤖 Ollama + DeepSeek R1 14B** (GPU-accelerated inference)
- **🗄️ PostgreSQL** (Primary database)
- **⚡ Redis** (Cache layer)
- **🧠 ChromaDB** (Vector database for embeddings)
- **📦 MinIO** (Object storage)
- **🔧 5 Microservices** (API endpoints)
- **🎨 React Dashboard** (Web interface)
- **🌐 ngrok Tunnels** (External access URLs)

## ⚙️ Requirements

- **Python 3.8+** (for local scripts)
- **Google Account** (for Colab access)
- **Internet Connection** (for GitHub/Colab access)
- **Chrome Browser** (for automated methods)

## 🔧 Troubleshooting

### "OAuth Error" or "Invalid Request"
- Use the **CLI Menu** option instead (Option 1)
- Avoid the Full CLI method until OAuth is fixed

### "Chrome not found"
- Install Google Chrome
- Or use the CLI Menu option 1 (manual browser)

### "GitHub not accessible"
- Check internet connection
- Verify repository is public
- Try again in a few minutes

### Deployment fails in Colab
- Ensure GPU runtime is selected
- Check Colab status: https://colab.research.google.com/
- Try again during off-peak hours

## 📊 Access Your Services

After successful deployment:

1. **Check Cell 5 output** in Colab for service URLs
2. **Look for ngrok URLs** like `https://abc123.ngrok.io`
3. **Test the dashboard** at one of the provided URLs
4. **API endpoints** will be documented in the output

## 💡 Pro Tips

- **Use Colab Pro/Pro+** for longer runtimes (up to 24 hours)
- **Monitor Cell 5** for real-time service URLs
- **Save important URLs** before the session ends
- **GPU runtime is required** for LLM inference
- **Free tier** provides 12GB RAM and ~12 hours

## 🎉 Success!

Once deployed, you'll have a fully functional Agentic Framework running on Google Colab GPU with all services accessible via ngrok tunnels!

---

**Need help?** Check the deployment output in Colab or run the CLI menu for status checking.