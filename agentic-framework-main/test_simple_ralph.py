import requests
import time

API_URL = 'http://34.229.112.127:8000/api/chat/public'

# 3 Simple but multi-step tasks
TASKS = [
    'Write a Python function to calculate fibonacci numbers',
    'Create a simple calculator with add, subtract, multiply, divide',
    'Build a function that checks if a string is a palindrome'
]

print('=' * 80)
print('TESTING RALPH LOOP ROUTING (3 SIMPLE MULTI-STEP TASKS)')
print('=' * 80)
print()

results = []

for i, task in enumerate(TASKS, 1):
    print(f'[{i}/3] {task}')
    print('-' * 80)
    
    try:
        start = time.time()
        print('Sending...', end='', flush=True)
        
        response = requests.post(
            API_URL,
            json={'message': task},
            timeout=90
        )
        
        elapsed = time.time() - start
        print(f' {elapsed:.1f}s')
        
        if response.status_code == 200:
            resp_text = response.json().get('response', '')
            
            # Check indicators
            has_code = '```' in resp_text or 'def ' in resp_text
            ralph_keywords = ['implementing', 'prd', 'user story', 'iteration', 
                            'ralph', 'acceptance', 'generated']
            uses_ralph = any(kw.lower() in resp_text.lower() for kw in ralph_keywords)
            
            status = 'PASS' if has_code else 'FAIL'
            
            print(f'Status: {status}')
            print(f'Has Code: {"YES" if has_code else "NO"}')
            print(f'Ralph Loop: {"YES" if uses_ralph else "NO"}')
            print(f'Length: {len(resp_text)} chars')
            
            results.append({
                'task': task[:50],
                'status': status,
                'time': elapsed,
                'ralph': uses_ralph,
                'code': has_code
            })
            
        else:
            print(f'FAIL: HTTP {response.status_code}')
            results.append({'task': task[:50], 'status': 'FAIL', 'time': elapsed})
            
    except requests.exceptions.Timeout:
        print('TIMEOUT')
        results.append({'task': task[:50], 'status': 'TIMEOUT', 'time': 90})
    except Exception as e:
        print(f'ERROR: {e}')
        results.append({'task': task[:50], 'status': 'ERROR'})
    
    print()

print('=' * 80)
print('RESULTS')
print('=' * 80)

passed = sum(1 for r in results if r.get('status') == 'PASS')
ralph_used = sum(1 for r in results if r.get('ralph', False))

for i, r in enumerate(results, 1):
    status_icon = '✓' if r.get('status') == 'PASS' else '✗'
    ralph_icon = '(R)' if r.get('ralph') else '   '
    time_str = f"{r.get('time', 0):.1f}s" if 'time' in r else 'N/A'
    print(f"{status_icon} [{i}/3] {r['task'][:45]:45} {time_str:>6} {ralph_icon}")

print('=' * 80)
print(f'Passed: {passed}/3 | Ralph Loop Used: {ralph_used}/3')
print('=' * 80)
