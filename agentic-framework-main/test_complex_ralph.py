"""
Complex Multi-Step Task Testing for Ralph Loop
Tests 3 sophisticated tasks that require multiple agents and comprehensive workflow
"""
import requests
import time
import json

API_URL = 'http://34.229.112.127:8000/api/chat/public'

# 3 Complex Multi-Step Tasks
COMPLEX_TASKS = [
    {
        'name': 'Task 1: Web Scraper with Database',
        'prompt': '''Create a complete web scraping system:
1. Build a Python web scraper using requests and BeautifulSoup
2. Extract article titles, dates, and content from a news website
3. Store the scraped data in a SQLite database with proper schema
4. Add error handling for network failures and invalid HTML
5. Implement rate limiting to be respectful of the target site
6. Create a function to query the database and display results
7. Write comprehensive tests for each component

Make it a complete, production-ready solution with proper error handling.''',
        'timeout': 240  # 4 minutes
    },
    {
        'name': 'Task 2: REST API with Middleware',
        'prompt': '''Build a complete FastAPI application:
1. Create a REST API for managing a todo list
2. Implement user authentication with JWT tokens
3. Add middleware for request logging and timing
4. Include CRUD operations (Create, Read, Update, Delete)
5. Use Pydantic models for request/response validation
6. Add rate limiting to prevent abuse
7. Write API documentation and include example requests
8. Create pytest test suite with 80%+ coverage

Ensure the API follows REST best practices and is production-ready.''',
        'timeout': 240  # 4 minutes
    },
    {
        'name': 'Task 3: Data Analysis Pipeline',
        'prompt': '''Design a data analysis pipeline:
1. Create a CSV data loader with validation
2. Implement data cleaning functions (handle nulls, outliers, duplicates)
3. Build statistical analysis functions (mean, median, std dev, correlations)
4. Add data visualization using matplotlib (histograms, scatter plots)
5. Create a report generator that outputs HTML summary
6. Include logging for all pipeline stages
7. Write unit tests for each transformation
8. Add a main orchestrator that runs the entire pipeline

Make it modular, well-documented, and extensible.''',
        'timeout': 240  # 4 minutes
    }
]

def format_time(seconds):
    """Format seconds into MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

def test_complex_task(task_info, task_num, total_tasks):
    """Test a single complex task"""
    name = task_info['name']
    prompt = task_info['prompt']
    timeout = task_info['timeout']
    
    print(f"\n{'='*80}")
    print(f"[{task_num}/{total_tasks}] {name}")
    print('='*80)
    print(f"Timeout: {timeout}s ({format_time(timeout)})")
    print()
    
    start_time = time.time()
    
    try:
        print(f">> Sending request... ", end='', flush=True)
        
        response = requests.post(
            API_URL,
            json={'message': prompt},
            timeout=timeout
        )
        
        elapsed = time.time() - start_time
        print(f"[+] Response received in {format_time(elapsed)}")
        
        if response.status_code == 200:
            resp_data = response.json()
            resp_text = resp_data.get('response', '')
            
            # Analyze response quality
            has_code = '```' in resp_text or 'def ' in resp_text or 'class ' in resp_text
            code_blocks = resp_text.count('```')
            ralph_indicators = ['prd', 'user story', 'implementation', 'acceptance', 
                              'iteration', 'ralph', 'generated', 'testing']
            uses_ralph = sum(1 for ind in ralph_indicators if ind.lower() in resp_text.lower())
            
            # Check for key components
            has_imports = 'import ' in resp_text
            has_functions = 'def ' in resp_text
            has_classes = 'class ' in resp_text
            has_tests = 'test' in resp_text.lower() or 'pytest' in resp_text.lower()
            has_docs = any(marker in resp_text for marker in ['"""', "'''", '# ', 'Args:', 'Returns:'])
            
            # Calculate quality score
            quality_checks = [
                has_code,
                code_blocks >= 3,
                has_imports,
                has_functions,
                has_classes,
                has_tests,
                has_docs,
                len(resp_text) > 1000
            ]
            quality_score = sum(quality_checks)
            
            # Determine status
            if quality_score >= 6:
                status = 'EXCELLENT'
                icon = '[**]'
            elif quality_score >= 4:
                status = 'GOOD'
                icon = '[+]'
            elif quality_score >= 2:
                status = 'PARTIAL'
                icon = '[~]'
            else:
                status = 'POOR'
                icon = '[-]'
            
            print()
            print(f"{icon} Status: {status}")
            print(f"  Quality Score: {quality_score}/8")
            print(f"  Response Length: {len(resp_text):,} chars")
            print(f"  Code Blocks: {code_blocks}")
            print(f"  Ralph Indicators: {uses_ralph}")
            print(f"  Components: {'Imports' if has_imports else ''} {'Functions' if has_functions else ''} {'Classes' if has_classes else ''} {'Tests' if has_tests else ''} {'Docs' if has_docs else ''}")
            print(f"  Time: {elapsed:.1f}s ({format_time(elapsed)})")
            
            # Show snippet
            print()
            print(">> Response Preview (first 300 chars):")
            print("-" * 80)
            preview = resp_text[:300].replace('\n', '\n  ')
            print(f"  {preview}...")
            print("-" * 80)
            
            return {
                'task': name,
                'status': status,
                'quality_score': quality_score,
                'time': elapsed,
                'uses_ralph': uses_ralph > 0,
                'length': len(resp_text),
                'code_blocks': code_blocks
            }
            
        else:
            print(f"\n[-] FAIL: HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return {
                'task': name,
                'status': 'FAIL',
                'time': elapsed,
                'error': f'HTTP {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"\n[-] TIMEOUT after {format_time(elapsed)}")
        return {
            'task': name,
            'status': 'TIMEOUT',
            'time': elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[-] ERROR: {str(e)}")
        return {
            'task': name,
            'status': 'ERROR',
            'time': elapsed,
            'error': str(e)
        }

def main():
    """Run all complex task tests"""
    print("\n" + "="*80)
    print("COMPLEX MULTI-STEP TASK TESTING - RALPH LOOP VALIDATION")
    print("="*80)
    print(f"Testing {len(COMPLEX_TASKS)} sophisticated multi-agent workflows")
    print(f"Expected behavior: ALL tasks should use Ralph Loop")
    print("="*80)
    
    results = []
    total_time = 0
    
    for i, task_info in enumerate(COMPLEX_TASKS, 1):
        result = test_complex_task(task_info, i, len(COMPLEX_TASKS))
        results.append(result)
        total_time += result.get('time', 0)
        
        # Short pause between tasks
        if i < len(COMPLEX_TASKS):
            print(f"\n>> Pausing 5 seconds before next task...")
            time.sleep(5)
    
    # Summary
    print("\n\n" + "="*80)
    print("FINAL RESULTS SUMMARY")
    print("="*80)
    
    excellent = sum(1 for r in results if r.get('status') == 'EXCELLENT')
    good = sum(1 for r in results if r.get('status') == 'GOOD')
    partial = sum(1 for r in results if r.get('status') == 'PARTIAL')
    poor = sum(1 for r in results if r.get('status') == 'POOR')
    failed = sum(1 for r in results if r.get('status') in ['FAIL', 'TIMEOUT', 'ERROR'])
    
    ralph_count = sum(1 for r in results if r.get('uses_ralph', False))
    avg_quality = sum(r.get('quality_score', 0) for r in results) / len(results) if results else 0
    
    print(f"\n>> Results Breakdown:")
    print(f"  [**] Excellent: {excellent}")
    print(f"  [+]  Good: {good}")
    print(f"  [~]  Partial: {partial}")
    print(f"  [-]  Poor/Failed: {poor + failed}")
    print()
    print(f">> Metrics:")
    print(f"  Average Quality Score: {avg_quality:.1f}/8.0")
    print(f"  Ralph Loop Usage: {ralph_count}/{len(results)}")
    print(f"  Total Time: {format_time(total_time)}")
    print(f"  Average Time: {format_time(total_time / len(results))}")
    print()
    
    # Detailed table
    print(">> Detailed Results:")
    print("-" * 80)
    for i, r in enumerate(results, 1):
        status_icon = {'EXCELLENT': '[**]', 'GOOD': '[+]', 'PARTIAL': '[~]', 'POOR': '[-]', 
                       'FAIL': '[-]', 'TIMEOUT': '[T]', 'ERROR': '[E]'}
        icon = status_icon.get(r.get('status'), '?')
        name = r['task'][:40]
        status = r.get('status', 'UNKNOWN')
        score = r.get('quality_score', 0)
        time_str = format_time(r.get('time', 0))
        ralph = 'R' if r.get('uses_ralph') else ' '
        
        print(f"{icon} [{i}] {name:40} {status:10} {score}/8 {time_str:>6} [{ralph}]")
    
    print("="*80)
    
    # Final verdict
    success_rate = (excellent + good) / len(results) * 100 if results else 0
    print()
    if success_rate >= 80:
        print("[++] OVERALL: EXCELLENT - Ralph Loop is working well!")
    elif success_rate >= 60:
        print("[+]  OVERALL: GOOD - Ralph Loop is functional with minor issues")
    elif success_rate >= 40:
        print("[~]  OVERALL: PARTIAL - Ralph Loop needs optimization")
    else:
        print("[-]  OVERALL: POOR - Ralph Loop requires significant fixes")
    
    print(f"   Success Rate: {success_rate:.1f}%")
    print("="*80)

if __name__ == "__main__":
    main()
