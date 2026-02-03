"""
Direct Ralph Loop Execution - Create TODO Manager Program
This runs Ralph directly without using the API
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the orchestrator service to path
sys.path.insert(0, str(Path(__file__).parent / "orchestrator" / "service"))

from ralph_loop import RalphLoop, PRD, UserStory

# Define the project
PROJECT_NAME = f"todo-manager-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
RALPH_WORK_DIR = Path(r"c:\Users\dmilner.AGV-040318-PC\Downloads\landon\ai_final\ralph-work")
PROJECT_DIR = RALPH_WORK_DIR / "generated" / PROJECT_NAME

# Create a PRD for the TODO Manager
def create_todo_manager_prd():
    """Create a Product Requirements Document for TODO Manager"""
    
    stories = [
        UserStory(
            story_id="todo-001",
            title="TodoItem Data Model",
            description="Create a TodoItem class to represent individual todo items",
            acceptance_criteria=[
                "TodoItem class with id, title, description, priority, completed, created_at, updated_at",
                "Priority can be 'high', 'medium', or 'low'",
                "Methods to mark as complete/incomplete",
                "All fields have proper type hints",
                "Comprehensive docstrings"
            ],
            priority=1
        ),
        UserStory(
            story_id="todo-002",
            title="TodoManager Core Logic",
            description="Create TodoManager class to manage todo items",
            acceptance_criteria=[
                "Add, update, delete todo items",
                "List all todos with optional filtering",
                "Save to and load from JSON file",
                "Input validation for all operations",
                "Error handling for file operations",
                "Complete docstrings"
            ],
            priority=1,
            dependencies=["todo-001"]
        ),
        UserStory(
            story_id="todo-003",
            title="Command Line Interface",
            description="Create CLI for interacting with TodoManager",
            acceptance_criteria=[
                "Commands: add, list, complete, delete",
                "Support for filtering by priority and status",
                "User-friendly prompts and error messages",
                "Help command showing usage",
                "Proper argument parsing"
            ],
            priority=2,
            dependencies=["todo-002"]
        ),
        UserStory(
            story_id="todo-004",
            title="Tests and Documentation",
            description="Add comprehensive tests and documentation",
            acceptance_criteria=[
                "Unit tests for TodoItem class (pytest)",
                "Unit tests for TodoManager class",
                "Integration tests for CLI",
                "README.md with installation and usage",
                "requirements.txt file",
                "Example usage in documentation"
            ],
            priority=2,
            dependencies=["todo-003"]
        )
    ]
    
    prd = PRD(
        name="TODO List Manager Application",
        description="A command-line TODO list manager with persistent storage",
        stories=stories,
        branch_name="feature/todo-manager"
    )
    
    return prd

async def main():
    """Run Ralph Loop to create the TODO Manager"""
    
    print("="*80)
    print("RALPH LOOP - DIRECT EXECUTION")
    print("="*80)
    print(f"Project: {PROJECT_NAME}")
    print(f"Output: {PROJECT_DIR}")
    print()
    
    try:
        # Create project directory
        PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create PRD
        print(">> Creating Product Requirements Document...")
        prd = create_todo_manager_prd()
        print(f"   Stories: {len(prd.stories)}")
        for story in prd.stories:
            print(f"   - {story.id}: {story.title}")
        print()
        
        # Initialize Ralph Loop
        print(">> Initializing Ralph Loop...")
        ralph = RalphLoop(
            project_root=PROJECT_DIR,
            prd=prd,
            ralph_work_dir=RALPH_WORK_DIR,
            max_iterations=20,
            max_retries_per_story=2
        )
        print(f"   Configured for {len(prd.stories)} stories")
        print()
        
        # Run Ralph Loop
        print(">> Starting Ralph Loop execution...")
        print("   This may take several minutes...")
        print()
        
        result = await ralph.run()
        
        # Show results
        print()
        print("="*80)
        print("RALPH LOOP COMPLETED")
        print("="*80)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Iterations: {result.get('iterations', 0)}")
        print(f"Duration: {result.get('duration_seconds', 0):.1f}s")
        print()
        
        stories_info = result.get('stories', {})
        print("Stories:")
        print(f"  Total: {stories_info.get('total', 0)}")
        print(f"  Completed: {stories_info.get('completed', 0)}")
        print(f"  Failed: {stories_info.get('failed', 0)}")
        print(f"  Completion: {stories_info.get('completion_percentage', 0)}%")
        print()
        
        # List generated files
        print("Generated files:")
        if PROJECT_DIR.exists():
            for file_path in sorted(PROJECT_DIR.rglob("*.py")):
                rel_path = file_path.relative_to(PROJECT_DIR)
                print(f"  {rel_path}")
        
        print()
        print(f"[+] Project location: {PROJECT_DIR}")
        print("="*80)
        
        return result
        
    except Exception as e:
        print()
        print("="*80)
        print(f"[-] ERROR: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    result = asyncio.run(main())
    
    if result and result.get('status') == 'completed':
        print("\n[+] Ralph Loop completed successfully!")
        print("    Ready for testing and validation")
        sys.exit(0)
    else:
        print("\n[-] Ralph Loop did not complete successfully")
        sys.exit(1)
