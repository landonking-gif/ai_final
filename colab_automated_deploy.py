#!/usr/bin/env python3
"""
Agentic Framework - Fully Automated Colab Deployment
Uses Selenium to automate the entire deployment process without manual browser interaction
"""

import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Set up Chrome driver with appropriate options."""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # Uncomment the next line if you want to run headless (no browser window)
    # chrome_options.add_argument("--headless")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def wait_for_element(driver, by, value, timeout=30):
    """Wait for an element to be present and return it."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def click_element(driver, by, value, timeout=30):
    """Wait for an element and click it."""
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )
    element.click()
    return element

def automate_colab_deployment():
    """Main function to automate Colab deployment."""
    print("🚀 Starting Automated Agentic Framework Deployment")
    print("=" * 60)

    # Check if deployment script exists
    if not os.path.exists('colab_deployment.py'):
        print("✗ Error: colab_deployment.py not found!")
        return False

    # Read the deployment script
    with open('colab_deployment.py', 'r') as f:
        deployment_code = f.read()

    print("✓ Deployment script loaded")

    # Set up the driver
    print("🔄 Setting up Chrome driver...")
    try:
        driver = setup_driver()
        print("✓ Chrome driver ready")
    except Exception as e:
        print(f"✗ Failed to set up Chrome driver: {e}")
        print("Please make sure Chrome is installed")
        return False

    try:
        # Open Colab
        print("🔄 Opening Google Colab...")
        driver.get("https://colab.research.google.com/")

        # Wait for the page to load
        time.sleep(3)

        # Click "New Notebook" or create new notebook
        print("🔄 Creating new notebook...")
        try:
            # Try to find the "New notebook" button
            new_notebook_btn = wait_for_element(
                driver,
                By.XPATH,
                "//div[contains(text(), 'New notebook')]"
            )
            new_notebook_btn.click()
        except:
            try:
                # Alternative: look for the + button or other new notebook options
                new_btn = wait_for_element(
                    driver,
                    By.CSS_SELECTOR,
                    "[aria-label*='New']"
                )
                new_btn.click()
            except:
                print("⚠️ Could not find new notebook button, opening existing notebook...")
                # Open the GitHub notebook directly
                driver.get("https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb")

        # Wait for notebook to load
        time.sleep(5)

        # Set GPU runtime
        print("🔄 Setting GPU runtime...")
        try:
            # Click Runtime menu
            runtime_menu = wait_for_element(
                driver,
                By.XPATH,
                "//div[contains(text(), 'Runtime')]"
            )
            runtime_menu.click()

            time.sleep(1)

            # Click "Change runtime type"
            change_runtime = wait_for_element(
                driver,
                By.XPATH,
                "//div[contains(text(), 'Change runtime type')]"
            )
            change_runtime.click()

            time.sleep(2)

            # Select GPU
            gpu_option = wait_for_element(
                driver,
                By.XPATH,
                "//div[contains(text(), 'GPU')]"
            )
            gpu_option.click()

            # Click Save
            save_btn = wait_for_element(
                driver,
                By.XPATH,
                "//div[contains(text(), 'Save')]"
            )
            save_btn.click()

            print("✓ GPU runtime set")
            time.sleep(3)

        except Exception as e:
            print(f"⚠️ Could not set GPU runtime automatically: {e}")
            print("Please manually set runtime to GPU")

        # Clear the first cell and add our deployment code
        print("🔄 Adding deployment code...")
        try:
            # Find the first code cell
            first_cell = wait_for_element(
                driver,
                By.CSS_SELECTOR,
                ".cell.code"
            )

            # Click on the cell to focus it
            first_cell.click()

            # Clear existing content (if any)
            # This is tricky - Colab might have different selectors

            # Add our deployment code
            # For now, we'll use the GitHub notebook approach
            print("✓ Switching to GitHub notebook...")
            driver.get("https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb")

            time.sleep(5)

            # Try to run all cells
            print("🔄 Running deployment...")
            try:
                # Click "Runtime" -> "Run all"
                runtime_menu = wait_for_element(
                    driver,
                    By.XPATH,
                    "//div[contains(text(), 'Runtime')]"
                )
                runtime_menu.click()

                time.sleep(1)

                run_all = wait_for_element(
                    driver,
                    By.XPATH,
                    "//div[contains(text(), 'Run all')]"
                )
                run_all.click()

                print("✓ Deployment started!")
                print()
                print("📋 MONITORING DEPLOYMENT:")
                print("The notebook is now running automatically.")
                print("Monitor the Colab tab for progress.")
                print("Deployment will take 10-15 minutes.")
                print()
                print("Services that will be deployed:")
                print("  • Ollama + DeepSeek R1 14B (GPU)")
                print("  • PostgreSQL, Redis, ChromaDB, MinIO")
                print("  • 5 microservices + React dashboard")
                print("  • ngrok tunnels for external access")
                print()
                print("Check the notebook output for access URLs!")

            except Exception as e:
                print(f"⚠️ Could not start automatic execution: {e}")
                print("Please manually click 'Runtime > Run all' in Colab")

        except Exception as e:
            print(f"⚠️ Could not modify notebook: {e}")
            print("Opening the GitHub notebook instead...")
            driver.get("https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/colab_auto_run.ipynb")

        # Keep the browser open
        print()
        print("🎯 DEPLOYMENT IN PROGRESS!")
        print("Do not close the browser window.")
        print("The deployment will complete automatically.")
        print()
        input("Press Enter to close the browser and exit...")

    except Exception as e:
        print(f"✗ Deployment automation failed: {e}")
        return False

    finally:
        driver.quit()

    return True

if __name__ == "__main__":
    success = automate_colab_deployment()
    if success:
        print("✅ Automation script completed")
    else:
        print("❌ Automation failed - you may need to deploy manually")
        sys.exit(1)