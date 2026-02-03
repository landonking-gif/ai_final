"""
Test Suite for TODO Manager
Tests the complete functionality of the TODO Manager application
"""
import sys
import os
from pathlib import Path

# Add the project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from todo_item import TodoItem, Priority
from todo_manager import TodoManager

def test_todo_item():
    """Test TodoItem functionality"""
    print("Testing TodoItem...")
    errors = []
    
    try:
        # Test creation
        item = TodoItem(title="Test Task", description="Test Description", priority=Priority.HIGH)
        assert item.title == "Test Task", "Title mismatch"
        assert item.description == "Test Description", "Description mismatch"
        assert item.priority == Priority.HIGH, "Priority mismatch"
        assert not item.completed, "Should not be completed"
        assert item.id, "ID should be generated"
        print("  [+] Creation: OK")
        
        # Test mark complete
        item.mark_complete()
        assert item.completed, "Should be completed"
        print("  [+] Mark complete: OK")
        
        # Test mark incomplete
        item.mark_incomplete()
        assert not item.completed, "Should be incomplete"
        print("  [+] Mark incomplete: OK")
        
        # Test update
        item.update(title="Updated Title", priority=Priority.LOW)
        assert item.title == "Updated Title", "Title should be updated"
        assert item.priority == Priority.LOW, "Priority should be updated"
        print("  [+] Update: OK")
        
        # Test serialization
        data = item.to_dict()
        assert 'id' in data, "Dict should have id"
        assert data['title'] == "Updated Title", "Dict title mismatch"
        print("  [+] Serialization: OK")
        
        # Test deserialization
        new_item = TodoItem.from_dict(data)
        assert new_item.title == item.title, "Deserialized title mismatch"
        assert new_item.id == item.id, "Deserialized ID mismatch"
        print("  [+] Deserialization: OK")
        
    except AssertionError as e:
        errors.append(f"TodoItem test failed: {e}")
    except Exception as e:
        errors.append(f"TodoItem test error: {e}")
    
    return errors

def test_todo_manager():
    """Test TodoManager functionality"""
    print("\\nTesting TodoManager...")
    errors = []
    
    # Use a test file
    test_file = project_dir / "test_todos.json"
    if test_file.exists():
        test_file.unlink()
    
    try:
        # Test initialization
        manager = TodoManager(str(test_file))
        assert len(manager.todos) == 0, "Should start empty"
        print("  [+] Initialization: OK")
        
        # Test add
        item1 = manager.add("Task 1", "Description 1", Priority.HIGH)
        assert len(manager.todos) == 1, "Should have 1 todo"
        assert item1.title == "Task 1", "Title mismatch"
        print("  [+] Add: OK")
        
        # Test add validation
        try:
            manager.add("", "", Priority.LOW)
            errors.append("Should reject empty title")
        except ValueError:
            print("  [+] Validation: OK")
        
        # Test add multiple
        item2 = manager.add("Task 2", "Description 2", Priority.MEDIUM)
        item3 = manager.add("Task 3", "Description 3", Priority.LOW)
        assert len(manager.todos) == 3, "Should have 3 todos"
        print("  [+] Multiple adds: OK")
        
        # Test list all
        all_todos = manager.list_all()
        assert len(all_todos) == 3, "Should list all 3"
        print("  [+] List all: OK")
        
        # Test filter by priority
        high_todos = manager.list_all(priority=Priority.HIGH)
        assert len(high_todos) == 1, "Should have 1 high priority"
        assert high_todos[0].id == item1.id, "Should be item1"
        print("  [+] Filter by priority: OK")
        
        # Test mark complete
        assert manager.mark_complete(item1.id), "Should mark complete"
        assert item1.completed, "Item should be completed"
        print("  [+] Mark complete: OK")
        
        # Test filter by completion
        pending = manager.list_all(completed=False)
        assert len(pending) == 2, "Should have 2 pending"
        completed = manager.list_all(completed=True)
        assert len(completed) == 1, "Should have 1 completed"
        print("  [+] Filter by completion: OK")
        
        # Test get by id
        found = manager.get_by_id(item2.id)
        assert found is not None, "Should find item"
        assert found.id == item2.id, "Should be item2"
        print("  [+] Get by ID: OK")
        
        # Test update
        assert manager.update(item2.id, title="Updated Task 2"), "Should update"
        assert item2.title == "Updated Task 2", "Title should be updated"
        print("  [+] Update: OK")
        
        # Test delete
        assert manager.delete(item3.id), "Should delete"
        assert len(manager.todos) == 2, "Should have 2 todos"
        print("  [+] Delete: OK")
        
        # Test persistence - save and reload
        manager.save()
        manager2 = TodoManager(str(test_file))
        assert len(manager2.todos) == 2, "Should load 2 todos"
        print("  [+] Persistence: OK")
        
        # Test stats
        stats = manager.get_stats()
        assert stats['total'] == 2, "Total should be 2"
        assert stats['completed'] == 1, "Completed should be 1"
        assert stats['pending'] == 1, "Pending should be 1"
        print("  [+] Statistics: OK")
        
    except AssertionError as e:
        errors.append(f"TodoManager test failed: {e}")
    except Exception as e:
        errors.append(f"TodoManager test error: {e}")
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
    
    return errors

def check_code_quality():
    """Check code quality aspects"""
    print("\\nChecking code quality...")
    issues = []
    
    # Check if files exist
    files = ['todo_item.py', 'todo_manager.py', 'main.py', 'README.md']
    for filename in files:
        filepath = project_dir / filename
        if not filepath.exists():
            issues.append(f"Missing file: {filename}")
        else:
            print(f"  [+] File exists: {filename}")
    
    # Check for docstrings
    for filename in ['todo_item.py', 'todo_manager.py']:
        filepath = project_dir / filename
        if filepath.exists():
            content = filepath.read_text()
            if '"""' in content or "'''" in content:
                print(f"  [+] Has docstrings: {filename}")
            else:
                issues.append(f"Missing docstrings: {filename}")
    
    # Check for type hints
    for filename in ['todo_item.py', 'todo_manager.py']:
        filepath = project_dir / filename
        if filepath.exists():
            content = filepath.read_text()
            if '->' in content and ':' in content:
                print(f"  [+] Has type hints: {filename}")
            else:
                issues.append(f"Missing type hints: {filename}")
    
    # Check for error handling
    for filename in ['todo_manager.py']:
        filepath = project_dir / filename
        if filepath.exists():
            content = filepath.read_text()
            if 'try:' in content and 'except' in content:
                print(f"  [+] Has error handling: {filename}")
            else:
                issues.append(f"Missing error handling: {filename}")
    
    return issues

def main():
    """Run all tests"""
    print("="*70)
    print("TODO MANAGER - COMPREHENSIVE TESTING")
    print("="*70)
    print(f"Project: {project_dir}")
    print()
    
    all_errors = []
    
    # Run tests
    all_errors.extend(test_todo_item())
    all_errors.extend(test_todo_manager())
    quality_issues = check_code_quality()
    
    # Summary
    print()
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    if all_errors:
        print(f"\\n[-] ERRORS FOUND: {len(all_errors)}")
        for error in all_errors:
            print(f"    - {error}")
    else:
        print("\\n[+] ALL TESTS PASSED!")
    
    if quality_issues:
        print(f"\\n[~] CODE QUALITY ISSUES: {len(quality_issues)}")
        for issue in quality_issues:
            print(f"    - {issue}")
    else:
        print("\\n[+] CODE QUALITY: EXCELLENT")
    
    print()
    
    if not all_errors and not quality_issues:
        print("[++] PROGRAM IS FULLY FUNCTIONAL WITH EXCELLENT DOCUMENTATION")
        return 0
    elif not all_errors:
        print("[+] PROGRAM WORKS BUT HAS MINOR QUALITY ISSUES")
        return 0
    else:
        print("[-] PROGRAM HAS ERRORS THAT NEED FIXING")
        return 1

if __name__ == '__main__':
    exit(main())
