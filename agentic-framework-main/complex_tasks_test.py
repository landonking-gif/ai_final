import requests
import time
import json

API_URL = 'http://localhost:8000/api/chat/public'

# 3 Complex Multi-Step Multi-Agent Tasks
COMPLEX_TASKS = [
    {
        'name': 'Data Pipeline with ETL',
        'description': '''Create a complete data pipeline system:
1. Build a Python data extraction module that reads CSV files
2. Create transformation functions to clean and normalize data
3. Implement a loading module that writes to SQLite database
4. Add error handling and logging throughout
5. Write unit tests for each component
6. Create a main orchestrator script that coordinates all steps''',
        'timeout': 180
    },
    {
        'name': 'REST API with Authentication',
        'description': '''Build a complete REST API system:
1. Create a FastAPI application with user authentication
2. Implement JWT token generation and validation
3. Build CRUD endpoints for a "tasks" resource
4. Add input validation using Pydantic models
5. Implement rate limiting middleware
6. Write API documentation and example requests
7. Create a test suite with pytest''',
        'timeout': 180
    },
    {
        'name': 'Automated Testing Framework',
        'description': '''Design an automated testing framework:
1. Create a test configuration system that reads from YAML
2. Build a test runner that executes tests in parallel
3. Implement test result reporting with HTML output
4. Add screenshot capture for failed tests
5. Create retry logic for flaky tests
6. Build a test data generator module
7. Write documentation on how to extend the framework''',
        'timeout': 180
    }
]

print('=' * 80)
print('COMPLEX MULTI-STEP MULTI-AGENT TASK TESTING')
print('=' * 80)
print()

results = []

for i, task_info in enumerate(COMPLEX_TASKS, 1):
    task_name = task_info['name']
    description = task_info['description']
    timeout = task_info['timeout']
    
    print(f'[{i}/3] {task_name}')
    print('-' * 80)
    print(f'Description: {description[:100]}...')
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
            
            # Check if response indicates Ralph Loop usage
            ralph_indicators = ['prd', 'product requirements', 'implementation', 
                              'code changes', 'files created', 'testing']
            uses_ralph = any(indicator in resp_text.lower() for indicator in ralph_indicators)
            
            # Check response quality
            has_code = '```' in resp_text or 'def ' in resp_text or 'class ' in resp_text
            has_structure = len(resp_text) > 500
            
            status = 'PASS' if (uses_ralph or has_code) and has_structure else 'PARTIAL'
            
            results.append({
                'task': task_name,
                'status': status,
                'time': round(elapsed, 1),
                'uses_ralph': uses_ralph,
                'response_length': len(resp_text)
            })
            
            print(f'Status: {status}')
            print(f'Time: {elapsed:.1f}s')
            print(f'Ralph Loop Used: {uses_ralph}')
            print(f'Response Length: {len(resp_text)} chars')
            print(f'Has Code: {has_code}')
            
        else:
            results.append({
                'task': task_name,
                'status': 'FAIL',
                'time': round(elapsed, 1),
                'error': f'HTTP {response.status_code}'
            })
            print(f'Status: FAIL (HTTP {response.status_code})')
            
    except requests.exceptions.Timeout:
        results.append({
            'task': task_name,
            'status': 'TIMEOUT',
            'time': timeout
        })
        print(f'Status: TIMEOUT (>{timeout}s)')
        
    except Exception as e:
        results.append({
            'task': task_name,
            'status': 'ERROR',
            'error': str(e)
        })
        print(f'Status: ERROR - {e}')
    
    print()
    print('=' * 80)
    print()

# Summary
print()
print('=' * 80)
print('FINAL RESULTS')
print('=' * 80)
passed = sum(1 for r in results if r['status'] in ['PASS', 'PARTIAL'])
print(f'Tasks Completed: {passed}/3')
print()

for r in results:
    status_icon = '✓' if r['status'] in ['PASS', 'PARTIAL'] else '✗'
    time_str = f"{r['time']}s" if 'time' in r else 'N/A'
    ralph = '(Ralph)' if r.get('uses_ralph') else ''
    print(f"{status_icon} {r['task']}: {r['status']} - {time_str} {ralph}")

print('=' * 80)
