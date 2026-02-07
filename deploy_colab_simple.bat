@echo off
REM Agentic Framework - Colab Deployment
REM This script opens the deployment notebook directly from GitHub in Google Colab

echo Agentic Framework - Colab Deployment
echo =====================================================

REM Check if the notebook exists locally (for reference)
if not exist "colab_auto_run.ipynb" (
    echo Warning: Local notebook not found: colab_auto_run.ipynb
    echo The script will still try to open it from GitHub.
) else (
    echo Found local deployment notebook: colab_auto_run.ipynb
)

REM Create Colab URL for GitHub repository
set "COLAB_URL=https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb"

echo.
echo Opening Google Colab deployment notebook from GitHub...
echo URL: %COLAB_URL%
echo.
echo INSTRUCTIONS:
echo   1. Make sure you're logged into Google Colab
echo   2. Set runtime to GPU (H100) via Runtime ^> Change runtime type
echo   3. Click 'Runtime ^> Run all' or press Ctrl+F9
echo   4. Wait 10-15 minutes for full deployment
echo.

REM Open Colab with the GitHub notebook
start %COLAB_URL%

if %errorlevel% equ 0 (
    echo Colab opened successfully with deployment notebook!
) else (
    echo Could not open browser automatically.
    echo Please manually open: %COLAB_URL%
)
echo The notebook will automatically deploy:
echo   - Ollama + DeepSeek R1 14B (GPU)
echo   - PostgreSQL, Redis, ChromaDB, MinIO
echo   - 5 microservices + React dashboard
echo   - ngrok tunnels for external access
echo.
echo Happy deploying!
pause