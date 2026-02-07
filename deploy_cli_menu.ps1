# Agentic Framework - Simple CLI Deployment
# Reliable CLI deployment using GitHub integration

Write-Host "Agentic Framework - Simple CLI Deployment" -ForegroundColor Green
Write-Host "=" * 48 -ForegroundColor Cyan

# Check requirements
Write-Host "🔍 Checking requirements..." -ForegroundColor Blue

if (!(Test-Path "colab_deployment.py")) {
    Write-Host "✗ Deployment script not found" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Deployment script found" -ForegroundColor Green

# GitHub Colab URL
$colabUrl = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb"

Write-Host ""
Write-Host "🎯 CLI DEPLOYMENT MENU:" -ForegroundColor Cyan
Write-Host "1. Open Colab (Manual deployment)" -ForegroundColor Green
Write-Host "2. Show deployment instructions" -ForegroundColor Blue
Write-Host "3. Check GitHub accessibility" -ForegroundColor Yellow
Write-Host "4. Create deployment summary" -ForegroundColor Magenta
Write-Host ""

$choice = Read-Host "Choose an option (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "🌐 OPENING COLAB" -ForegroundColor Green
        Write-Host "Opening Colab in your default browser..." -ForegroundColor White

        try {
            Start-Process $colabUrl
            Write-Host "✅ Colab opened successfully!" -ForegroundColor Green
        } catch {
            Write-Host "✗ Failed to open browser: $_" -ForegroundColor Red
            Write-Host "Please manually open: $colabUrl" -ForegroundColor Yellow
        }

        Write-Host ""
        Write-Host "📋 NEXT STEPS:" -ForegroundColor Cyan
        Write-Host "1. Login to Google Colab if prompted" -ForegroundColor White
        Write-Host "2. Set runtime to GPU (Runtime → Change runtime type → GPU)" -ForegroundColor White
        Write-Host "3. Click 'Runtime → Run all'" -ForegroundColor White
        Write-Host "4. Monitor deployment progress (10-15 minutes)" -ForegroundColor White
    }

    "2" {
        Write-Host ""
        Write-Host "📚 DEPLOYMENT INSTRUCTIONS" -ForegroundColor Cyan
        Write-Host "=" * 30 -ForegroundColor Cyan
        Write-Host ""
        Write-Host "STEP 1: Access Colab" -ForegroundColor Green
        Write-Host "  -> Open: $colabUrl" -ForegroundColor White
        Write-Host "  -> Login with your Google account" -ForegroundColor White
        Write-Host ""

        Write-Host "STEP 2: Configure Runtime" -ForegroundColor Green
        Write-Host "  -> Click: Runtime -> Change runtime type" -ForegroundColor White
        Write-Host "  -> Select: GPU (T4, A100, or V100)" -ForegroundColor White
        Write-Host "  -> Click: Save" -ForegroundColor White
        Write-Host ""

        Write-Host "STEP 3: Start Deployment" -ForegroundColor Green
        Write-Host "  -> Click: Runtime -> Run all" -ForegroundColor White
        Write-Host "  -> Or press: Ctrl+F9" -ForegroundColor White
        Write-Host ""

        Write-Host "STEP 4: Monitor Progress" -ForegroundColor Green
        Write-Host "  -> Watch the output cells execute" -ForegroundColor White
        Write-Host "  -> Deployment takes 10-15 minutes" -ForegroundColor White
        Write-Host "  -> Check Cell 5 for service URLs" -ForegroundColor White
        Write-Host ""

        Write-Host "🎯 SERVICES DEPLOYED:" -ForegroundColor Cyan
        Write-Host "  -> Ollama + DeepSeek R1 14B (GPU inference)" -ForegroundColor White
        Write-Host "  -> PostgreSQL database" -ForegroundColor White
        Write-Host "  -> Redis cache" -ForegroundColor White
        Write-Host "  -> ChromaDB vector database" -ForegroundColor White
        Write-Host "  -> MinIO object storage" -ForegroundColor White
        Write-Host "  -> 5 microservices + React dashboard" -ForegroundColor White
        Write-Host "  -> ngrok tunnels for external access" -ForegroundColor White
    }

    "3" {
        Write-Host ""
        Write-Host "🔍 CHECKING GITHUB ACCESSIBILITY" -ForegroundColor Yellow

        try {
            $response = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/landonking-gif/ai_final/main/colab_auto_run.ipynb" -Method Head -TimeoutSec 10
            Write-Host "✅ GitHub repository is accessible (Status: $($response.StatusCode))" -ForegroundColor Green
        } catch {
            Write-Host "✗ GitHub repository not accessible: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "Check your internet connection or repository permissions" -ForegroundColor Yellow
        }

        try {
            $response = Invoke-WebRequest -Uri $colabUrl -Method Head -TimeoutSec 10
            Write-Host "✅ Colab integration working (Status: $($response.StatusCode))" -ForegroundColor Green
        } catch {
            Write-Host "⚠️ Colab integration check failed: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "Colab may be temporarily unavailable" -ForegroundColor White
        }
    }

    "4" {
        Write-Host ""
        Write-Host "📋 DEPLOYMENT SUMMARY" -ForegroundColor Magenta
        Write-Host "=" * 25 -ForegroundColor Magenta
        Write-Host ""

        # Check local files
        $files = @(
            "colab_deployment.py",
            "colab_auto_run.ipynb",
            "requirements.txt",
            "pyproject.toml"
        )

        Write-Host "📁 LOCAL FILES:" -ForegroundColor Cyan
        foreach ($file in $files) {
            if (Test-Path $file) {
                Write-Host "  ✓ $file" -ForegroundColor Green
            } else {
                Write-Host "  ✗ $file (missing)" -ForegroundColor Red
            }
        }

        Write-Host ""
        Write-Host "🌐 REMOTE ACCESS:" -ForegroundColor Cyan
        Write-Host "  -> Colab URL: $colabUrl" -ForegroundColor White
        Write-Host "  -> Repository: https://github.com/landonking-gif/ai_final" -ForegroundColor White

        Write-Host ""
        Write-Host "⚙️ DEPLOYMENT CONFIG:" -ForegroundColor Cyan
        Write-Host "  -> Runtime: GPU required (T4/A100 recommended)" -ForegroundColor White
        Write-Host "  -> Duration: 10-15 minutes" -ForegroundColor White
        Write-Host "  -> Services: 5 microservices + databases" -ForegroundColor White
        Write-Host "  -> Access: ngrok tunnels (external URLs)" -ForegroundColor White

        Write-Host ""
        Write-Host "🎯 SUCCESS CRITERIA:" -ForegroundColor Cyan
        Write-Host "  -> All cells execute without errors" -ForegroundColor White
        Write-Host "  -> Cell 5 shows service URLs" -ForegroundColor White
        Write-Host "  -> No 'Error' or 'Exception' messages" -ForegroundColor White
        Write-Host "  -> ngrok URLs are accessible" -ForegroundColor White
    }

    default {
        Write-Host "✗ Invalid choice. Please select 1-4." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "💡 PRO TIPS:" -ForegroundColor Cyan
Write-Host "  -> Use Colab Pro/Pro+ for longer runtimes" -ForegroundColor White
Write-Host "  -> Monitor Cell 5 output for service URLs" -ForegroundColor White
Write-Host "  -> Save important URLs before session ends" -ForegroundColor White
Write-Host "  -> GPU runtime is required for LLM inference" -ForegroundColor White
Write-Host "  -> Free tier provides 12GB RAM and ~12 hours" -ForegroundColor White
Write-Host ""

if ($choice -eq "1") {
    Write-Host "HAPPY DEPLOYING!" -ForegroundColor Green
    Write-Host 'Your Agentic Framework will be running on Colab GPU soon!' -ForegroundColor White
}