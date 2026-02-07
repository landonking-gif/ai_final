#!/usr/bin/env python3
"""
Pure Colab CLI - Execute notebooks programmatically without browser interaction
Uses Google Colab API directly with service account authentication
"""

import os
import sys
import time
import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import google.auth

class ColabCLI:
    def __init__(self):
        self.service = None
        self.api_key = None
        # Use the deployment notebook that contains the full setup
        self.colab_url = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/agentic-framework-deploy-auto.ipynb"

    def authenticate(self):
        """Authenticate using service account or API key"""
        print("🔐 Authenticating with Google Colab API...")

        # Try service account first
        try:
            key_path = os.path.join(os.path.dirname(__file__), 'colab-service-account.json')
            if os.path.exists(key_path):
                credentials = service_account.Credentials.from_service_account_file(
                    key_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.service = build('colab', 'v1', credentials=credentials)
                print("✅ Authenticated with service account")
                return True
        except Exception as e:
            print(f"⚠️ Service account auth failed: {e}")

        # Try API key
        try:
            api_key = os.environ.get('GOOGLE_API_KEY')
            if api_key:
                self.api_key = api_key
                print("✅ Authenticated with API key")
                return True
        except Exception as e:
            print(f"⚠️ API key auth failed: {e}")

        print("❌ No authentication method available")
        print("Please set up authentication:")
        print("1. Create a Google Cloud service account and download the JSON key")
        print("2. Save it as 'colab-service-account.json' in this directory")
        print("3. Or set GOOGLE_API_KEY environment variable")
        return False

    def create_notebook(self):
        """Create a new Colab notebook from the deployment notebook"""
        print("📓 Creating Colab notebook from deployment template...")

        try:
            # Create notebook with the deployment content
            notebook_data = {
                'name': 'projects/-/locations/us-central1/notebooks/agentic-framework-deploy',
                'environment': {
                    'type': 'RUNTIME_TYPE_UNSPECIFIED',
                    'runtimeType': 'RUNTIME_TYPE_GPU'
                },
                'source': {
                    'uri': self.colab_url
                }
            }

            if self.service:
                # Use service account
                request = self.service.projects().locations().notebooks().create(
                    parent='projects/-/locations/us-central1',
                    body=notebook_data
                )
                response = request.execute()
            else:
                # Use API key
                url = f"https://colab.googleapis.com/v1/projects/-/locations/us-central1/notebooks?key={self.api_key}"
                response = requests.post(url, json=notebook_data).json()

            notebook_id = response.get('name', '').split('/')[-1]
            notebook_url = f"https://colab.research.google.com/drive/{notebook_id}"
            print(f"✅ Created notebook: {notebook_id}")
            print(f"📎 Notebook URL: {notebook_url}")
            return notebook_id

        except Exception as e:
            print(f"❌ Failed to create notebook: {e}")
            print("💡 This might be due to:")
            print("   - Colab API not enabled in Google Cloud")
            print("   - Insufficient permissions on service account")
            print("   - Invalid API key")
            return None

    def execute_notebook(self, notebook_id):
        """Execute the notebook with GPU runtime"""
        print("🚀 Starting notebook execution with GPU runtime...")

        try:
            execute_data = {
                'executionTemplate': {
                    'runtimeType': 'RUNTIME_TYPE_GPU',
                    'acceleratorConfig': {
                        'type': 'ACCELERATOR_TYPE_NVIDIA_TESLA_T4',
                        'coreCount': 1
                    },
                    'idleShutdownTimeout': 3600,  # 1 hour timeout
                    'maxRuntime': 7200  # 2 hour max runtime
                }
            }

            if self.service:
                # Use service account
                request = self.service.projects().locations().notebooks().executions().create(
                    parent=f'projects/-/locations/us-central1/notebooks/{notebook_id}',
                    body=execute_data
                )
                response = request.execute()
            else:
                # Use API key
                url = f"https://colab.googleapis.com/v1/projects/-/locations/us-central1/notebooks/{notebook_id}/executions?key={self.api_key}"
                response = requests.post(url, json=execute_data).json()

            execution_id = response.get('name', '').split('/')[-1]
            print(f"✅ Started execution: {execution_id}")
            print("🎯 GPU runtime configured (T4 GPU)")
            return execution_id

        except Exception as e:
            print(f"❌ Failed to execute notebook: {e}")
            print("💡 This might be due to:")
            print("   - GPU quota exceeded")
            print("   - Colab service unavailable")
            print("   - Invalid notebook configuration")
            return None

    def monitor_execution(self, notebook_id, execution_id):
        """Monitor the execution progress with detailed status"""
        print("📊 Monitoring deployment progress...")
        print("This may take 10-15 minutes for full deployment")

        start_time = time.time()
        last_status = None

        try:
            while True:
                elapsed = int(time.time() - start_time)

                if self.service:
                    # Use service account
                    request = self.service.projects().locations().notebooks().executions().get(
                        name=f'projects/-/locations/us-central1/notebooks/{notebook_id}/executions/{execution_id}'
                    )
                    response = request.execute()
                else:
                    # Use API key
                    url = f"https://colab.googleapis.com/v1/projects/-/locations/us-central1/notebooks/{notebook_id}/executions/{execution_id}?key={self.api_key}"
                    response = requests.get(url).json()

                status = response.get('state', 'UNKNOWN')

                # Only print status changes
                if status != last_status:
                    timestamp = time.strftime('%H:%M:%S')
                    print(f"[{timestamp}] Status: {status} ({elapsed}s elapsed)")
                    last_status = status

                if status == 'SUCCEEDED':
                    print("✅ Execution completed successfully!")
                    self.get_execution_output(notebook_id, execution_id)
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    print(f"❌ Execution {status.lower()}")
                    error_msg = response.get('errorMessage', 'Unknown error')
                    print(f"Error: {error_msg}")
                    break
                elif status == 'RUNNING':
                    # Show progress dots
                    print(".", end="", flush=True)

                time.sleep(15)  # Check every 15 seconds

        except Exception as e:
            print(f"❌ Monitoring failed: {e}")
            print("💡 The execution may still be running. Check the notebook URL manually.")

    def get_execution_output(self, notebook_id, execution_id):
        """Get the execution output and extract service URLs"""
        print("📄 Retrieving deployment results...")

        try:
            if self.service:
                # Use service account
                request = self.service.projects().locations().notebooks().executions().get(
                    name=f'projects/-/locations/us-central1/notebooks/{notebook_id}/executions/{execution_id}'
                )
                response = request.execute()
            else:
                # Use API key
                url = f"https://colab.googleapis.com/v1/projects/-/locations/us-central1/notebooks/{notebook_id}/executions/{execution_id}?key={self.api_key}"
                response = requests.get(url).json()

            # Extract output information
            output_files = response.get('outputFiles', [])
            job_output = response.get('jobOutput', '')

            print("\n" + "="*60)
            print("🎉 DEPLOYMENT RESULTS")
            print("="*60)

            if job_output:
                print("📋 Execution Output:")
                print(job_output)
                print()

            # Look for common service URLs in output
            if 'ngrok' in job_output.lower():
                print("🌐 ngrok Tunnels Found:")
                # Extract ngrok URLs (basic pattern matching)
                lines = job_output.split('\n')
                for line in lines:
                    if 'ngrok' in line.lower() and ('http' in line or 'https' in line):
                        print(f"  {line.strip()}")

            if 'localhost' in job_output or '127.0.0.1' in job_output:
                print("🏠 Local Services:")
                lines = job_output.split('\n')
                for line in lines:
                    if ('localhost' in line or '127.0.0.1' in line) and ('running' in line.lower() or 'started' in line.lower()):
                        print(f"  {line.strip()}")

            print("\n🔗 Access URLs:")
            notebook_url = f"https://colab.research.google.com/drive/{notebook_id}"
            print(f"  📓 Colab Notebook: {notebook_url}")

            if output_files:
                print("📁 Output Files:")
                for output_file in output_files:
                    print(f"  {output_file}")

            print("\n💡 Next Steps:")
            print("  1. Open the Colab notebook URL above")
            print("  2. Check the ngrok tunnels for external access")
            print("  3. Monitor the services in the notebook output")
            print("  4. The deployment will keep running until you stop it")

        except Exception as e:
            print(f"❌ Failed to get output: {e}")
            print("💡 You can still check the notebook manually for results")

def main():
    print("🚀 Pure Colab CLI - No Browser Required")
    print("=" * 50)

    cli = ColabCLI()

    # Authenticate
    if not cli.authenticate():
        sys.exit(1)

    # Create notebook
    notebook_id = cli.create_notebook()
    if not notebook_id:
        sys.exit(1)

    # Execute notebook
    execution_id = cli.execute_notebook(notebook_id)
    if not execution_id:
        sys.exit(1)

    # Monitor execution
    cli.monitor_execution(notebook_id, execution_id)

    print("\n🎉 Deployment process complete!")
    print("Check the output above for service URLs and access information.")

if __name__ == "__main__":
    main()