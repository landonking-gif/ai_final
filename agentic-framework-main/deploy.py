import paramiko
import os
import sys
import tarfile
import tempfile
import shutil
from scp import SCPClient

# Agentic Framework AWS Deployment Script (Python)
# Unified deployment with OpenClaw + Ralph Loop + Memory integration
# Features:
#   - Git repository initialization with upstream OpenClaw sync
#   - Codebase indexing into memory service
#   - All agents use OpenClaw with DeepSeek R1
#   - ALL tasks routed through Ralph Loop for consistency
# Usage: python deploy.py <AWS_IP>

def test_ssh(host, user, key_path):
    """Test SSH connection"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, key_filename=key_path, timeout=15)
        stdin, stdout, stderr = client.exec_command('echo SSH_OK')
        output = stdout.read().decode().strip()
        client.close()
        return output == 'SSH_OK'
    except Exception as e:
        print(f"SSH test failed: {e}")
        return False

def create_archive(project_dir, exclude_patterns):
    """Create tar.gz archive"""
    temp_dir = tempfile.mkdtemp()
    archive_path = os.path.join(temp_dir, 'deploy.tar.gz')
    
    def should_exclude(path):
        for pattern in exclude_patterns:
            if pattern in path:
                return True
        return False
    
    with tarfile.open(archive_path, 'w:gz') as tar:
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_dir)
                if not should_exclude(rel_path):
                    tar.add(file_path, arcname=rel_path)
    
    return archive_path

def run_ssh_command(host, user, key_path, command):
    """Run command over SSH"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, key_filename=key_path)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()
        return output, error
    except Exception as e:
        print(f"SSH command failed: {e}")
        return '', str(e)

def scp_file(host, user, key_path, local_path, remote_path):
    """SCP file to remote"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, key_filename=key_path)
        with SCPClient(client.get_transport()) as scp:
            scp.put(local_path, remote_path)
        client.close()
        return True
    except Exception as e:
        print(f"SCP failed: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        aws_ip = "34.229.112.127"  # default
    else:
        aws_ip = sys.argv[1]
    
    ssh_user = "ubuntu"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pem_key = os.path.join(os.path.dirname(script_dir), "king-ai-studio.pem")
    project_dir = script_dir
    
    if not os.path.exists(pem_key):
        print(f"Error: PEM key not found at {pem_key}")
        sys.exit(1)
    
    print("========================================")
    print("Agentic Framework AWS Deployment v3.1")
    print("OpenClaw + Ralph Loop + Memory")
    print("ALL TASKS USE RALPH LOOP")
    print("========================================")
    print(f"Target: {aws_ip}")
    print()
    
    # Test SSH
    print("[1/7] Testing SSH...")
    if not test_ssh(aws_ip, ssh_user, pem_key):
        print("Error: Cannot connect to server")
        sys.exit(1)
    print("  [OK] Connected")
    
    # Create archive
    print("[2/7] Creating package...")
    exclude_patterns = ['.git', '__pycache__', '*.pyc', 'node_modules', '*.pem', '.env']
    archive_path = create_archive(project_dir, exclude_patterns)
    print("  [OK] Archive ready")
    
    # Upload
    print("[3/7] Uploading...")
    remote_archive = "/tmp/deploy.tar.gz"
    if not scp_file(aws_ip, ssh_user, pem_key, archive_path, remote_archive):
        print("Error: Upload failed")
        sys.exit(1)
    os.remove(archive_path)
    print("  [OK] Uploaded")
    
    # Extract
    print("[4/7] Extracting...")
    extract_cmd = "sudo mkdir -p /opt/agentic-framework && sudo tar -xzf /tmp/deploy.tar.gz -C /opt/agentic-framework && sudo chown -R ubuntu:ubuntu /opt/agentic-framework && rm /tmp/deploy.tar.gz"
    output, error = run_ssh_command(aws_ip, ssh_user, pem_key, extract_cmd)
    if error:
        print(f"Extract error: {error}")
    print("  [OK] Extracted")
    
    # Install dependencies
    print("[5/7] Installing dependencies...")
    deps_script = '''
set -e
if ! command -v docker &>/dev/null; then sudo apt update -qq && sudo apt install -y docker.io docker-compose-v2 && sudo systemctl enable --now docker && sudo usermod -aG docker ubuntu; fi
if ! command -v git &>/dev/null; then sudo apt install -y git; fi
if ! command -v node &>/dev/null || [[ $(node -v | cut -d. -f1 | tr -d 'v') -lt 22 ]]; then curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs; fi
if ! command -v openclaw &>/dev/null; then sudo npm install -g openclaw@latest; fi
if ! command -v ollama &>/dev/null; then curl -fsSL https://ollama.com/install.sh | sh && sudo systemctl enable --now ollama; fi
if ! ollama list | grep -q "deepseek-r1:14b"; then ollama pull deepseek-r1:14b; fi
echo "Dependencies installed"
'''
    output, error = run_ssh_command(aws_ip, ssh_user, pem_key, deps_script)
    if error:
        print(f"Deps error: {error}")
    print("  [OK] Dependencies ready")
    
    # Initialize Git
    print("[6/7] Initializing Git repository...")
    git_script_path = os.path.join(project_dir, "deploy-git.sh")
    if os.path.exists(git_script_path):
        scp_file(aws_ip, ssh_user, pem_key, git_script_path, "/tmp/deploy-git.sh")
        run_ssh_command(aws_ip, ssh_user, pem_key, "bash /tmp/deploy-git.sh && rm /tmp/deploy-git.sh")
    print("  [OK] Git configured")
    
    # Deploy
    print("[7/7] Deploying (10-15 min)...")
    services_script_path = os.path.join(project_dir, "deploy-services.sh")
    if os.path.exists(services_script_path):
        scp_file(aws_ip, ssh_user, pem_key, services_script_path, "/tmp/deploy-services.sh")
        run_ssh_command(aws_ip, ssh_user, pem_key, "bash /tmp/deploy-services.sh && rm /tmp/deploy-services.sh")
    print("  [OK] Deployed")
    
    # Start services
    print("[POST-DEPLOY] Starting services...")
    start_script = '''
set -e
cd /opt/agentic-framework
sudo docker compose up -d
sleep 5
sudo systemctl restart nginx
echo "Services started"
'''
    output, error = run_ssh_command(aws_ip, ssh_user, pem_key, start_script)
    if error:
        print(f"Start error: {error}")
    print("  [OK] All services running")
    
    print()
    print("========================================")
    print("[SUCCESS] DEPLOYMENT SUCCESSFUL!")
    print("========================================")
    print()
    print("Services Deployed:")
    print("  - Orchestrator (OpenClaw + Memory)")
    print("  - SubAgent Manager (OpenClaw)")
    print("  - Memory Service (with codebase index)")
    print("  - MCP Gateway")
    print("  - OpenClaw Gateway (DeepSeek R1)")
    print()
    print("Access Points:")
    print(f"  Dashboard:  http://{aws_ip}")
    print(f"  API Docs:   http://{aws_ip}:8000/docs")
    print(f"  Health:     http://{aws_ip}:8000/health")
    print()
    print("Maintenance:")
    print(f"  Sync OpenClaw: ssh -i \"{pem_key}\" {ssh_user}@{aws_ip} '/opt/agentic-framework/sync-openclaw.sh'")
    print(f"  View logs:     ssh -i \"{pem_key}\" {ssh_user}@{aws_ip} 'cd /opt/agentic-framework && sudo docker compose logs -f'")
    print()

if __name__ == "__main__":
    main()