# Agentic Framework - Colab Deployment
# This script opens the deployment notebook directly from GitHub in Google Colab

Write-Host "Agentic Framework - Colab Deployment"
Write-Host ("=" * 60)

# Check if the notebook exists locally (for reference)
$notebookPath = Join-Path $PSScriptRoot "colab_auto_run.ipynb"
if (!(Test-Path $notebookPath)) {
    Write-Host "Warning: Local notebook not found: $notebookPath"
    Write-Host "The script will still try to open it from GitHub."
} else {
    Write-Host "Found local deployment notebook: $notebookPath"
}

# Create Colab URL for GitHub repository
$colabUrl = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb"

Write-Host ""
Write-Host "Opening Google Colab deployment notebook from GitHub..."
Write-Host "URL: $colabUrl"
Write-Host ""
Write-Host "INSTRUCTIONS:"
Write-Host "  1. Make sure you're logged into Google Colab"
Write-Host "  2. Set runtime to GPU (H100) via Runtime > Change runtime type"
Write-Host "  3. Click 'Runtime > Run all' or press Ctrl+F9"
Write-Host "  4. Wait 10-15 minutes for full deployment"
Write-Host ""

# Open Colab with the GitHub notebook
try {
    Start-Process $colabUrl
    Write-Host "Colab opened successfully with deployment notebook!"
} catch {
    Write-Host "Could not open browser automatically."
    Write-Host "Please manually open: $colabUrl"
}

Write-Host ""
Write-Host "The notebook will automatically deploy:"
Write-Host "  - Ollama + DeepSeek R1 14B (GPU)"
Write-Host "  - PostgreSQL, Redis, ChromaDB, MinIO"
Write-Host "  - 5 microservices + React dashboard"
Write-Host "  - ngrok tunnels for external access"
Write-Host ""
Write-Host "Happy deploying!"

# Keep window open
Read-Host "Press Enter to exit"