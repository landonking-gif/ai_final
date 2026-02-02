"""Quick test of single Ralph Loop task"""
import requests
import time

API_URL = 'http://34.229.112.127:8000/api/chat/public'

task = 'Create a Python calculator with add, subtract, multiply and divide functions. Include error handling.'

print("Testing Ralph Loop with single task")
print(f"Task: {task}")
print("\nSending request...")

start = time.time()

try:
    response = requests.post(
        API_URL,
        json={'message': task},
        timeout=180  # 3 minutes
    )
    
    elapsed = time.time() - start
    
    if response.status_code == 200:
        resp_text = response.json().get('response', '')
        
        print(f"\n✓ Success in {elapsed:.1f}s ({int(elapsed//60)}:{int(elapsed%60):02d})")
        print(f"  Response length: {len(resp_text)} chars")
        print(f"  Has code: {'```' in resp_text or 'def ' in resp_text}")
        print(f"  Ralph indicators: {sum(1 for x in ['prd', 'story', 'iteration'] if x in resp_text.lower())}")
        
        print(f"\nFirst 400 chars:")
        print("-" * 80)
        print(resp_text[:400])
        print("-" * 80)
    else:
        print(f"✗ Failed: HTTP {response.status_code}")
        
except requests.exceptions.Timeout:
    print(f"✗ Timeout after {time.time() - start:.1f}s")
except Exception as e:
    print(f"✗ Error: {e}")
