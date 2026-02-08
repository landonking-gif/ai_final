# Dashboard Troubleshooting - Run this if dashboard fails

# Check if dashboard process is running
!ps aux | grep -E "(npm|node|serve)" | grep -v grep

# Check if port 3000 is in use
!lsof -i :3000 2>/dev/null || echo "Nothing on port 3000"

# Check dashboard logs
print("\n=== DASHBOARD LOG ===")
!tail -50 /tmp/dashboard.log 2>/dev/null || echo "No dashboard log found"

# Check if dashboard directory exists
import os
dashboard_dir = "/content/ai_final/agentic-framework-main/dashboard"
print(f"\n=== DASHBOARD DIRECTORY ===")
print(f"Exists: {os.path.exists(dashboard_dir)}")
if os.path.exists(dashboard_dir):
    !ls -la {dashboard_dir}
    
    if os.path.exists(f"{dashboard_dir}/build"):
        print("\nPre-built dashboard found")
        !ls -la {dashboard_dir}/build
    elif os.path.exists(f"{dashboard_dir}/package.json"):
        print("\nSource dashboard found - needs build")
    else:
        print("\nNo dashboard found!")

# Manual dashboard start options
print("\n=== MANUAL START OPTIONS ===")
print("\nOption 1 - If build/ folder exists:")
print("  cd /content/ai_final/agentic-framework-main/dashboard")
print("  npx serve -s build -l 3000 &")
print("\nOption 2 - Start from source:")
print("  cd /content/ai_final/agentic-framework-main/dashboard")
print("  npm install")
print("  PORT=3000 BROWSER=none npm start &")
print("\nOption 3 - Disable dashboard:")
print("  Set START_DASHBOARD = False in config cell and re-run")
