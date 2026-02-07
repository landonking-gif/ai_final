@echo off
REM Agentic Framework - Colab Deployment with CLI
REM This script uses colab-cli to upload and open the deployment notebook

echo Agentic Framework - Colab Deployment
echo =====================================================

REM Check if the notebook exists
if not exist "colab_auto_run.ipynb" (
    echo Notebook not found: colab_auto_run.ipynb
    echo Please ensure colab_auto_run.ipynb is in the same directory as this script.
    pause
    exit /b 1
)
echo Found deployment notebook: colab_auto_run.ipynb

REM Check if colab-cli is installed
python -m colab_cli --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing colab-cli...
    python -m pip install colab-cli
    if %errorlevel% neq 0 (
        echo Failed to install colab-cli. Please install manually: pip install colab-cli
        pause
        exit /b 1
    )
    echo colab-cli installed
) else (
    echo colab-cli already installed
)

echo.
echo Uploading and opening notebook in Google Colab...
echo This will:
echo   1. Upload colab_auto_run.ipynb to your Google Drive
echo   2. Open it in Google Colab
echo   3. You'll need to run all cells manually
echo.

REM Upload and open the notebook
python -m colab_cli open-nb "colab_auto_run.ipynb"

if %errorlevel% equ 0 (
    echo.
    echo Notebook uploaded and opened successfully!
) else (
    echo.
    echo Failed to upload/open notebook. Trying fallback...
    start https://colab.research.google.com/notebooks/intro.ipynb
    if %errorlevel% equ 0 (
        echo Opened Google Colab in browser
        echo You'll need to upload colab_auto_run.ipynb manually
    ) else (
        echo Could not open browser. Please manually open: https://colab.research.google.com
    )
)

echo.
echo Manual Instructions:
echo   1. Make sure you're logged into Google Colab
echo   2. If not uploaded automatically, upload colab_auto_run.ipynb
echo   3. Set runtime to GPU (H100) via Runtime ^> Change runtime type
echo   4. Click 'Runtime ^> Run all' or press Ctrl+F9
echo   5. Wait 10-15 minutes for full deployment
echo.

echo The notebook will automatically deploy:
echo   - Ollama + DeepSeek R1 14B (GPU)
echo   - PostgreSQL, Redis, ChromaDB, MinIO
echo   - 5 microservices + React dashboard
echo   - ngrok tunnels for external access
echo.
echo Happy deploying!
pause