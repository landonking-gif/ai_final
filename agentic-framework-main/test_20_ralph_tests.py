"""
Comprehensive Ralph Loop Test Suite - 20 Tests
Tests Ralph's ability to handle various coding tasks
"""
import requests
import time
import json
import sys
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_URL = 'http://34.229.112.127:8000/api/chat/public'

# 20 Test Tasks covering different complexities
TESTS = [
    # Basic Python Functions (1-5)
    {
        'id': 'test-001',
        'name': 'Simple Calculator',
        'prompt': 'Create a Python calculator with add, subtract, multiply, and divide functions',
        'timeout': 90
    },
    {
        'id': 'test-002',
        'name': 'String Reverser',
        'prompt': 'Write a Python function that reverses a string without using built-in reverse',
        'timeout': 90
    },
    {
        'id': 'test-003',
        'name': 'Fibonacci Generator',
        'prompt': 'Create a Python function that generates the first N Fibonacci numbers',
        'timeout': 90
    },
    {
        'id': 'test-004',
        'name': 'Prime Checker',
        'prompt': 'Write a Python function to check if a number is prime',
        'timeout': 90
    },
    {
        'id': 'test-005',
        'name': 'List Sorter',
        'prompt': 'Implement a Python function that sorts a list using bubble sort',
        'timeout': 90
    },
    
    # File Operations (6-9)
    {
        'id': 'test-006',
        'name': 'JSON File Handler',
        'prompt': 'Create Python functions to read and write JSON files with error handling',
        'timeout': 90
    },
    {
        'id': 'test-007',
        'name': 'CSV Reader',
        'prompt': 'Build a Python script to read CSV file and calculate column averages',
        'timeout': 90
    },
    {
        'id': 'test-008',
        'name': 'Text File Analyzer',
        'prompt': 'Write a Python program that counts words, lines, and characters in a text file',
        'timeout': 90
    },
    {
        'id': 'test-009',
        'name': 'Directory Scanner',
        'prompt': 'Create a Python script that lists all files in a directory recursively',
        'timeout': 90
    },
    
    # Data Structures (10-13)
    {
        'id': 'test-010',
        'name': 'Stack Implementation',
        'prompt': 'Implement a Stack data structure in Python with push, pop, and peek methods',
        'timeout': 90
    },
    {
        'id': 'test-011',
        'name': 'Queue Implementation',
        'prompt': 'Create a Queue data structure in Python with enqueue and dequeue operations',
        'timeout': 90
    },
    {
        'id': 'test-012',
        'name': 'Binary Search Tree',
        'prompt': 'Implement a simple Binary Search Tree with insert and search methods',
        'timeout': 90
    },
    {
        'id': 'test-013',
        'name': 'Hash Table',
        'prompt': 'Build a basic Hash Table in Python with get, set, and remove operations',
        'timeout': 90
    },
    
    # Web & API (14-16)
    {
        'id': 'test-014',
        'name': 'Simple Web Scraper',
        'prompt': 'Create a Python web scraper using requests to fetch and parse HTML',
        'timeout': 120
    },
    {
        'id': 'test-015',
        'name': 'REST API Client',
        'prompt': 'Build a Python class to interact with a REST API (GET and POST)',
        'timeout': 120
    },
    {
        'id': 'test-016',
        'name': 'URL Validator',
        'prompt': 'Write a Python function to validate URLs using regex',
        'timeout': 90
    },
    
    # Advanced Features (17-20)
    {
        'id': 'test-017',
        'name': 'Email Validator',
        'prompt': 'Create a comprehensive email validator using Python regex',
        'timeout': 90
    },
    {
        'id': 'test-018',
        'name': 'Password Generator',
        'prompt': 'Build a secure password generator with customizable length and character types',
        'timeout': 90
    },
    {
        'id': 'test-019',
        'name': 'Date Time Handler',
        'prompt': 'Create Python functions to parse, format, and calculate date/time differences',
        'timeout': 90
    },
    {
        'id': 'test-020',
        'name': 'Config File Parser',
        'prompt': 'Write a Python class to parse and manage INI configuration files',
        'timeout': 90
    }
]

def run_test(test_info, test_num, total):
    """Run a single test and return results"""
    print(f"\\n{'='*80}")
    print(f"[{test_num}/{total}] {test_info['id']}: {test_info['name']}")
    print('='*80)
    
    result = {
        'id': test_info['id'],
        'name': test_info['name'],
        'status': 'UNKNOWN',
        'time': 0,
        'error': None
    }
    
    try:
        start_time = time.time()
        print(f">> Sending: {test_info['prompt'][:70]}...")
        
        response = requests.post(
            API_URL,
            json={'message': test_info['prompt']},
            timeout=test_info['timeout']
        )
        
        elapsed = time.time() - start_time
        result['time'] = round(elapsed, 2)
        
        if response.status_code == 200:
            resp_data = response.json()
            resp_text = resp_data.get('response', '')
            
            # Check for code generation
            has_code = '```' in resp_text or 'def ' in resp_text or 'class ' in resp_text
            has_error = 'error' in resp_text.lower() and 'handling' not in resp_text.lower()
            
            if has_code and not has_error:
                result['status'] = 'PASS'
                print(f"[+] PASS - {elapsed:.1f}s - {len(resp_text)} chars")
            else:
                result['status'] = 'PARTIAL'
                result['error'] = 'No code generated or contains errors'
                print(f"[~] PARTIAL - {elapsed:.1f}s")
        else:
            result['status'] = 'FAIL'
            result['error'] = f'HTTP {response.status_code}'
            print(f"[-] FAIL - HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        result['status'] = 'TIMEOUT'
        result['time'] = test_info['timeout']
        result['error'] = f"Timeout after {test_info['timeout']}s"
        print(f"[-] TIMEOUT after {test_info['timeout']}s")
        
    except Exception as e:
        result['status'] = 'ERROR'
        result['error'] = str(e)
        print(f"[-] ERROR: {e}")
    
    return result

def main():
    """Run all 20 tests"""
    print("="*80)
    print("RALPH LOOP - 20 TEST SUITE")
    print("="*80)
    print(f"Testing against: {API_URL}")
    print(f"Total tests: {len(TESTS)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    start_time = time.time()
    
    for i, test in enumerate(TESTS, 1):
        result = run_test(test, i, len(TESTS))
        results.append(result)
        
        # Brief pause between tests
        if i < len(TESTS):
            time.sleep(2)
    
    total_time = time.time() - start_time
    
    # Summary
    print("\\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['status'] == 'PASS')
    partial = sum(1 for r in results if r['status'] == 'PARTIAL')
    failed = sum(1 for r in results if r['status'] in ['FAIL', 'TIMEOUT', 'ERROR'])
    
    print(f"Total Tests: {len(results)}")
    print(f"[+] Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"[~] Partial: {partial} ({partial/len(results)*100:.1f}%)")
    print(f"[-] Failed: {failed} ({failed/len(results)*100:.1f}%)")
    print(f"\\nTotal Time: {total_time/60:.1f} minutes")
    print(f"Average Time: {sum(r['time'] for r in results)/len(results):.1f}s per test")
    
    # Detailed results
    print("\\n" + "-"*80)
    print("DETAILED RESULTS")
    print("-"*80)
    for r in results:
        status_symbol = {
            'PASS': '[+]',
            'PARTIAL': '[~]',
            'FAIL': '[-]',
            'TIMEOUT': '[T]',
            'ERROR': '[E]'
        }.get(r['status'], '[?]')
        
        print(f"{status_symbol} {r['id']:<12} {r['name']:<30} {r['time']:>6.1f}s  {r['status']}")
        if r['error']:
            print(f"  +-- {r['error']}")
    
    # Save results
    output_file = f"c:\\Users\\dmilner.AGV-040318-PC\\Downloads\\landon\\ai_final\\ralph-work\\test-outputs\\test-run-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'passed': passed,
            'partial': partial,
            'failed': failed,
            'total_time': total_time,
            'results': results
        }, f, indent=2)
    
    print(f"\\n[+] Results saved to: {output_file}")
    
    return passed, failed

if __name__ == '__main__':
    passed, failed = main()
    exit(0 if failed == 0 else 1)
