import requests
import time
import json

API_URL = 'http://34.229.112.127:8000/api/chat/public'

# 3 Multi-Step Tasks (less complex but still multi-step)
TASKS = [
    {
        'name': 'Task 1: CSV Data Processor',
        'description': 'Create a Python script that reads a CSV file, calculates statistics (mean, median), and writes results to a new file. Include error handling.',
        'timeout': 120
    },
    {
        'name': 'Task 2: Simple REST API',
        'description': 'Build a FastAPI application with two endpoints: GET /items that returns a list and POST /items that adds an item. Include basic validation.',
        'timeout': 120
    },
    {
        'name': 'Task 3: File Organizer',
        'description': 'Write a Python program that scans a directory, organizes files by extension into subdirectories, and creates a summary report.',
        'timeout': 120
    }
]

print('=' * 80)
print('MULTI-STEP TASK TESTING (Ralph Loop Required)')
print('=' * 80)
print()

results = []

for i, task_info in enumerate(TASKS, 1):
    task_name = task_info['name']
    description = task_info['description']
    timeout = task_info['timeout']
    
    print(f'[{i}/3] {task_name}')
    print('-' * 80)
    print(f'Task: {description}')
    print(f'Timeout: {timeout}s')
    print()
    
    try:
        start_time = time.time()
        print('Sending request...')
        
        response = requests.post(
            API_URL,
            json={'message': description},
            timeout=timeout
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            resp_data = response.json()
            resp_text = resp_data.get('response', '')
            
            # Check response quality
            has_code = '```' in resp_text or 'def ' in resp_text or 'class ' in resp_text
            has_structure = len(resp_text) > 200
            
            # Check for Ralph Loop indicators
            ralph_indicators = ['implementing', 'user story', 'acceptance criteria', 
                              'iteration', 'prd', 'generated code', 'files']
            uses_ralph = any(indicator.lower() in resp_text.lower() for indicator in ralph_indicators)
            
            status = 'PASS' if has_code and has_structure else 'PARTIAL'
            
            results.append({
                'task': task_name,
                'status': status,
                'time': round(elapsed, 1),
                'uses_ralph': uses_ralph,
                'response_length': len(resp_text),
                'has_code': has_code
            })
            
            print(f'✓ Status: {status}')
            print(f'  Time: {elapsed:.1f}s')
            print(f'  Ralph Loop: {"YES" if uses_ralph else "NO"}')
            print(f'  Response: {len(resp_text)} chars')
            print(f'  Has Code: {"YES" if has_code else "NO"}')
            
            # Show first 200 chars
            print(f'\n  Preview: {resp_text[:200]}...\n')
            
        else:
            results.append({
                'task': task_name,
                'status': 'FAIL',
                'time': round(elapsed, 1),
                'error': f'HTTP {response.status_code}'
            })
            print(f'✗ Status: FAIL (HTTP {response.status_code})')
            
    except requests.exceptions.Timeout:
        results.append({
            'task': task_name,
            'status': 'TIMEOUT',
            'time': timeout
        })
        print(f'✗ Status: TIMEOUT (>{timeout}s)')
        
    except Exception as e:
        results.append({
            'task': task_name,
            'status': 'ERROR',
            'error': str(e)
        })
        print(f'✗ Status: ERROR - {e}')
    
    print('=' * 80)
    print()

# Summary
print()
print('=' * 80)
print('FINAL RESULTS')
print('=' * 80)
passed = sum(1 for r in results if r['status'] in ['PASS', 'PARTIAL'])
ralph_count = sum(1 for r in results if r.get('uses_ralph', False))

print(f'Tasks Completed: {passed}/3')
print(f'Used Ralph Loop: {ralph_count}/3')
print()

for r in results:
    status_icon = '✓' if r['status'] in ['PASS', 'PARTIAL'] else '✗'
    time_str = f"{r['time']}s" if 'time' in r else 'N/A'
    ralph = '(Ralph)' if r.get('uses_ralph') else '(Direct)'
    code = 'Code✓' if r.get('has_code') else 'NoCode'
    print(f"{status_icon} {r['task']}: {r['status']} - {time_str} {ralph} {code}")

print('=' * 80)

if ralph_count == 3:
    print('\n✓ SUCCESS: All tasks used Ralph Loop as expected!')
else:
    print(f'\n⚠ WARNING: Only {ralph_count}/3 tasks used Ralph Loop')
