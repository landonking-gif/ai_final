#!/usr/bin/env python3
"""
Agentic Framework - Colab Deployment
This script opens the deployment notebook directly from GitHub in Google Colab
"""

import os
import sys
import pathlib
import webbrowser

def main():
    print("🚀 Agentic Framework - Colab Deployment")
    print("=" * 60)

    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8+ required. Please upgrade Python.")
        return False

    print(f"✓ Python {sys.version.split()[0]}")

    # Check if notebook exists locally (for reference)
    script_dir = pathlib.Path(__file__).parent
    notebook_path = script_dir / "colab_auto_run.ipynb"

    if not notebook_path.exists():
        print(f"⚠️  Warning: Local notebook not found: {notebook_path}")
        print("The script will still try to open it from GitHub.")
    else:
        print(f"✓ Found local deployment notebook: {notebook_path}")

    # Create Colab URL for GitHub repository
    colab_url = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb"

    print("\n🔄 Opening Google Colab deployment notebook from GitHub...")
    print(f"URL: {colab_url}")
    print()
    print("INSTRUCTIONS:")
    print("  1. Make sure you're logged into Google Colab")
    print("  2. Set runtime to GPU (H100) via Runtime > Change runtime type")
    print("  3. Click 'Runtime > Run all' or press Ctrl+F9")
    print("  4. Wait 10-15 minutes for full deployment")
    print()

    # Try to open in default browser
    try:
        webbrowser.open(colab_url)
        print("✅ Colab opened successfully with deployment notebook!")
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Please manually open: {colab_url}")

    print("\nThe notebook will automatically deploy:")
    print("  - Ollama + DeepSeek R1 14B (GPU)")
    print("  - PostgreSQL, Redis, ChromaDB, MinIO")
    print("  - 5 microservices + React dashboard")
    print("  - ngrok tunnels for external access")
    print("\nHappy deploying! 🚀")

    return True

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)