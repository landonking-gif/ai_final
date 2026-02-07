# Pure Colab CLI Setup Guide

## 🚀 Pure Colab CLI - No Browser Required

This CLI executes your Agentic Framework deployment entirely from VS Code using the Google Colab API directly.

## 📋 Prerequisites

- Python 3.8+
- Google Cloud Project
- Colab API enabled

## 🔐 Authentication Setup

Choose **one** of the following authentication methods:

### Method 1: Service Account (Recommended)

1. **Create Google Cloud Project**
   - Go to: https://console.cloud.google.com/
   - Create new project or select existing

2. **Enable Colab API**
   - Go to: APIs & Services → Library
   - Search for "Colab"
   - Enable "Colab API"

3. **Create Service Account**
   - Go to: IAM & Admin → Service Accounts
   - Click "Create Service Account"
   - Name: `colab-deployer`
   - Role: `Colab Enterprise User` or `Editor`
   - Click "Done"

4. **Generate JSON Key**
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key" → JSON
   - Download the JSON file
   - Rename to: `colab-service-account.json`
   - Place in the same directory as this script

### Method 2: API Key

1. **Create API Key**
   - Go to: APIs & Services → Credentials
   - Click "Create Credentials" → "API Key"
   - Copy the API key

2. **Set Environment Variable**
   ```powershell
   $env:GOOGLE_API_KEY = "your-api-key-here"
   ```

## 🚀 Usage

### First Time Setup
```powershell
# Run setup (will guide you through authentication)
.\pure_colab_cli.ps1
```

### Subsequent Deployments
```powershell
# Deploy directly (no browser interaction)
.\pure_colab_cli.ps1
```

## 🎯 What Happens

1. **Authentication** - Uses service account or API key
2. **Notebook Creation** - Creates Colab notebook programmatically
3. **GPU Runtime** - Configures T4/A100 GPU automatically
4. **Code Execution** - Runs your deployment script
5. **Live Monitoring** - Shows progress in VS Code terminal
6. **Output Retrieval** - Gets service URLs and access info

## 📊 Output

The CLI will show:
- Execution status
- Service URLs
- ngrok tunnel addresses
- Access credentials
- Dashboard links

## 🔧 Troubleshooting

### "Authentication failed"
- Verify your service account JSON file
- Check API key is set correctly
- Ensure Colab API is enabled

### "Permission denied"
- Grant proper roles to service account
- Enable required APIs in Google Cloud

### "Quota exceeded"
- Check Google Cloud quotas
- Wait and retry
- Consider Colab Pro for higher limits

### "Execution failed"
- Check Colab status: https://colab.research.google.com/
- Verify notebook URL is accessible
- Try different runtime type

## 💡 Pro Tips

- **Service Account** is more reliable than API keys
- **Colab Pro/Pro+** provides longer runtimes and better GPUs
- **Monitor output** for service URLs after deployment
- **Save URLs** before session ends

## 🎉 Success

Once deployed, you'll have your complete Agentic Framework running on Colab GPU with all services accessible via the provided URLs - all from VS Code!

---

**Need help?** Check the Google Cloud Console for API status and the VS Code output for detailed error messages.