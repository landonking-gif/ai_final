# Agentic Framework - Hybrid CLI Deployment
# Uses GitHub integration with enhanced CLI automation

Write-Host "🚀 Agentic Framework - Hybrid CLI Deployment" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Cyan

# Check if required tools are available
Write-Host "🔍 Checking requirements..." -ForegroundColor Blue

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "✗ Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python available" -ForegroundColor Green

if (!(Test-Path "colab_deployment.py")) {
    Write-Host "✗ Deployment script not found" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Deployment script found" -ForegroundColor Green

# GitHub Colab URL
$colabUrl = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb"

Write-Host ""
Write-Host "🎯 DEPLOYMENT OPTIONS:" -ForegroundColor Cyan
Write-Host "1. Automated Browser (Recommended)" -ForegroundColor Green
Write-Host "2. Manual Browser (Backup)" -ForegroundColor Yellow
Write-Host ""

$choice = Read-Host "Choose deployment method (1 or 2)"

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "🤖 AUTOMATED DEPLOYMENT" -ForegroundColor Green
    Write-Host "This will open Chrome and automate the deployment process." -ForegroundColor White
    Write-Host ""

    # Check if Chrome is available
    $chromePaths = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
    )

    $chromePath = $null
    foreach ($path in $chromePaths) {
        if (Test-Path $path) {
            $chromePath = $path
            break
        }
    }

    if (!$chromePath) {
        Write-Host "⚠️ Chrome not found. Switching to manual method..." -ForegroundColor Yellow
        $choice = "2"
    } else {
        Write-Host "✓ Chrome found at: $chromePath" -ForegroundColor Green

        $confirm = Read-Host "Ready to start automated deployment? (y/N)"
        if ($confirm -ne 'y' -and $confirm -ne 'Y') {
            Write-Host "Deployment cancelled." -ForegroundColor Yellow
            exit 0
        }

        # Create automation script
        $automationScript = @"
import time
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

def automate_colab():
    print("🚀 Starting automated Colab deployment...")

    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # Uncomment to run headless: chrome_options.add_argument("--headless")

    try:
        # Open Colab
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ Chrome opened successfully")

        driver.get("$colabUrl")
        print("✅ Colab notebook opened")

        # Wait for page to load
        time.sleep(5)

        # Set GPU runtime
        print("🔄 Setting GPU runtime...")
        try:
            # Click Runtime menu
            runtime_menu = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Runtime')]"))
            )
            runtime_menu.click()
            time.sleep(1)

            # Click Change runtime type
            change_runtime = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Change runtime type')]"))
            )
            change_runtime.click()
            time.sleep(2)

            # Select GPU
            gpu_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'GPU')]"))
            )
            gpu_option.click()
            time.sleep(1)

            # Click Save
            save_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Save')]"))
            )
            save_btn.click()

            print("✅ GPU runtime set")
            time.sleep(3)

        except Exception as e:
            print(f"⚠️ Could not set GPU runtime automatically: {e}")
            print("Please manually set runtime to GPU")

        # Start deployment
        print("🚀 Starting deployment...")
        try:
            # Click Runtime -> Run all
            runtime_menu = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Runtime')]"))
            )
            runtime_menu.click()
            time.sleep(1)

            run_all = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Run all')]"))
            )
            run_all.click()

            print("✅ Deployment started!")
            print()
            print("📋 MONITORING DEPLOYMENT:")
            print("- Keep this window open")
            print("- Deployment takes 10-15 minutes")
            print("- Check Colab tab for progress")
            print("- Look for service URLs in Cell 5 output")
            print()
            input("Press Enter when deployment is complete...")

        except Exception as e:
            print(f"⚠️ Could not start automatic execution: {e}")
            print("Please manually click 'Runtime > Run all' in Colab")

        driver.quit()
        print("🎉 Automation complete!")

    except Exception as e:
        print(f"✗ Automation failed: {e}")
        print("Falling back to manual method...")
        return False

    return True

if __name__ == "__main__":
    success = automate_colab()
    if not success:
        print()
        print("📋 MANUAL DEPLOYMENT INSTRUCTIONS:")
        print("1. Open: $colabUrl")
        print("2. Set runtime to GPU (Runtime > Change runtime type)")
        print("3. Click Runtime > Run all")
        print("4. Wait 10-15 minutes")
        print("5. Check Cell 5 for service URLs")
"@

        # Save automation script
        $automationScript | Out-File -FilePath "automate_colab.py" -Encoding UTF8

        Write-Host "🔄 Starting automated deployment..." -ForegroundColor Blue
        python automate_colab.py

        # Clean up
        Remove-Item "automate_colab.py" -ErrorAction SilentlyContinue

    }
} elseif ($choice -eq "2") {
    Write-Host ""
    Write-Host "🌐 MANUAL BROWSER DEPLOYMENT" -ForegroundColor Yellow
    Write-Host "Opening Colab in your default browser..." -ForegroundColor White

    Start-Process $colabUrl
    Write-Host "✅ Colab opened in browser" -ForegroundColor Green
} else {
    Write-Host "✗ Invalid choice. Exiting." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📋 DEPLOYMENT INSTRUCTIONS:" -ForegroundColor Cyan
Write-Host "1. Make sure you're logged into Google Colab" -ForegroundColor White
Write-Host "2. Set runtime to GPU (Runtime → Change runtime type → T4 GPU)" -ForegroundColor White
Write-Host "3. Click 'Runtime → Run all' or press Ctrl+F9" -ForegroundColor White
Write-Host "4. Wait 10-15 minutes for full deployment" -ForegroundColor White
Write-Host ""

Write-Host "🎯 WHAT GETS DEPLOYED:" -ForegroundColor Cyan
Write-Host "  • Ollama + DeepSeek R1 14B (GPU)" -ForegroundColor White
Write-Host "  • PostgreSQL, Redis, ChromaDB, MinIO" -ForegroundColor White
Write-Host "  • 5 microservices + React dashboard" -ForegroundColor White
Write-Host "  • ngrok tunnels for external access" -ForegroundColor White
Write-Host ""

Write-Host "📊 ACCESS INFORMATION:" -ForegroundColor Cyan
Write-Host "  → Check Cell 5 output for ngrok URLs" -ForegroundColor White
Write-Host "  → Dashboard available at one of the URLs" -ForegroundColor White
Write-Host "  → Services auto-restart if crashed" -ForegroundColor White
Write-Host ""

Write-Host "✅ READY TO DEPLOY!" -ForegroundColor Green
Write-Host "Follow the steps above in your Colab tab." -ForegroundColor White