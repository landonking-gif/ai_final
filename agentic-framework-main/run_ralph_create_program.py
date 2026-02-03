"""
Run Ralph Loop to Create a Program
This will generate a complete program using Ralph and save it to ralph-work
"""
import requests
import time
import json
import re
from pathlib import Path
from datetime import datetime

API_URL = 'http://34.229.112.127:8000/api/chat/public'
RALPH_WORK_DIR = Path(r"c:\Users\dmilner.AGV-040318-PC\Downloads\landon\ai_final\ralph-work")

# Define a program to create
PROGRAM_TASK = """
Create a complete Python TODO List Manager application with the following features:

1. A TodoItem class with:
   - id, title, description, priority (high/medium/low), completed status
   - created_at and updated_at timestamps
   - Method to mark as complete/incomplete

2. A TodoManager class with:
   - Add new todo items
   - List all todos (with optional filters by priority and completion status)
   - Update a todo item
   - Delete a todo item
   - Save todos to JSON file
   - Load todos from JSON file

3. A command-line interface (main.py) that allows users to:
   - Add a new todo
   - View all todos
   - Mark todo as complete
   - Delete a todo
   - Filter todos by priority or completion status

4. Include:
   - Comprehensive docstrings for all classes and methods
   - Input validation and error handling
   - Unit tests using pytest
   - README.md with usage instructions
   - requirements.txt file

Make it a production-ready, well-documented application with proper code structure.
"""

def extract_and_save_code(response_text, project_name):
    """Extract code blocks from response and save to ralph-work"""
    project_dir = RALPH_WORK_DIR / "generated" / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Pattern to match code blocks with filenames
    pattern = r'```(?:python|py)[:\s]+([\w/._-]+\.(?:py|md|txt|json|yaml|yml))\n(.*?)```'
    matches = re.findall(pattern, response_text, re.DOTALL)
    
    files_saved = []
    
    if matches:
        for filename, content in matches:
            file_path = project_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content.strip())
            
            files_saved.append(str(file_path))
            print(f"  [+] Saved: {filename}")
    
    # Also look for generic Python code blocks without filenames
    if not files_saved:
        generic_pattern = r'```(?:python|py)\n(.*?)```'
        generic_matches = re.findall(generic_pattern, response_text, re.DOTALL)
        
        for i, content in enumerate(generic_matches):
            if content.strip():
                # Try to infer filename from content
                if 'class Todo' in content or 'TodoItem' in content:
                    filename = 'todo_item.py'
                elif 'class TodoManager' in content:
                    filename = 'todo_manager.py'
                elif 'if __name__' in content:
                    filename = 'main.py'
                elif 'def test_' in content:
                    filename = f'test_todo_{i}.py'
                elif '# README' in content or 'Usage' in content:
                    filename = 'README.md'
                else:
                    filename = f'code_{i}.py'
                
                file_path = project_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                
                files_saved.append(str(file_path))
                print(f"  [+] Saved: {filename}")
    
    # Save full response
    response_file = project_dir / "ralph_response.txt"
    with open(response_file, 'w', encoding='utf-8') as f:
        f.write(response_text)
    
    return files_saved, project_dir

def run_ralph_loop():
    """Run Ralph to create the program"""
    project_name = f"todo-manager-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print("="*80)
    print("RALPH LOOP - PROGRAM CREATION")
    print("="*80)
    print(f"Project: {project_name}")
    print(f"Output: {RALPH_WORK_DIR / 'generated' / project_name}")
    print()
    print("Task:")
    print(PROGRAM_TASK[:200] + "...")
    print()
    
    start_time = time.time()
    
    try:
        print(">> Sending request to Ralph Loop...")
        
        response = requests.post(
            API_URL,
            json={'message': PROGRAM_TASK},
            timeout=300  # 5 minutes
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            resp_data = response.json()
            resp_text = resp_data.get('response', '')
            
            print(f"[+] Response received in {elapsed:.1f}s")
            print(f"    Length: {len(resp_text)} chars")
            print()
            
            # Extract and save code
            print(">> Extracting and saving code...")
            files_saved, project_dir = extract_and_save_code(resp_text, project_name)
            
            print()
            print(f"[+] Project created successfully!")
            print(f"    Location: {project_dir}")
            print(f"    Files saved: {len(files_saved)}")
            print()
            
            # Show file structure
            print(">> Project structure:")
            for file_path in sorted(files_saved):
                rel_path = Path(file_path).relative_to(project_dir)
                print(f"    {rel_path}")
            
            return {
                'success': True,
                'project_dir': str(project_dir),
                'files': files_saved,
                'response': resp_text,
                'time': elapsed
            }
        else:
            print(f"[-] FAIL: HTTP {response.status_code}")
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'time': elapsed
            }
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"[-] TIMEOUT after {elapsed:.1f}s")
        return {
            'success': False,
            'error': 'Timeout',
            'time': elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[-] ERROR: {e}")
        return {
            'success': False,
            'error': str(e),
            'time': elapsed
        }

if __name__ == '__main__':
    result = run_ralph_loop()
    
    print()
    print("="*80)
    if result['success']:
        print("[+] RALPH LOOP COMPLETED SUCCESSFULLY")
        print(f"    Project location: {result['project_dir']}")
        print()
        print("Next steps:")
        print("  1. Review the generated code")
        print("  2. Test for errors")
        print("  3. Verify documentation and comments")
    else:
        print("[-] RALPH LOOP FAILED")
        print(f"    Error: {result.get('error', 'Unknown')}")
    print("="*80)
