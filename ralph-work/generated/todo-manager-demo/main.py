"""
TODO List Manager - Command Line Interface
Main entry point for the TODO manager application
"""
import sys
from todo_manager import TodoManager
from todo_item import Priority


def print_help():
    """Print usage instructions"""
    print("""
TODO List Manager - Usage:
    
Commands:
    add <title> [description] [priority]  - Add a new todo
    list [all|pending|completed]         - List todos
    complete <id>                         - Mark todo as complete
    incomplete <id>                       - Mark todo as incomplete
    delete <id>                           - Delete a todo
    stats                                 - Show statistics
    help                                  - Show this help message
    exit                                  - Exit the program

Priority levels: high, medium, low (default: medium)

Examples:
    add "Buy groceries" "Milk, eggs, bread" high
    list pending
    complete abc123
    """)


def main():
    """Main CLI loop"""
    manager = TodoManager()
    
    print("="*60)
    print("TODO LIST MANAGER")
    print("="*60)
    print("Type 'help' for usage instructions")
    print()
    
    while True:
        try:
            command = input("> ").strip()
            
            if not command:
                continue
            
            parts = command.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if cmd == "exit":
                print("Goodbye!")
                break
            
            elif cmd == "help":
                print_help()
            
            elif cmd == "add":
                # Parse: title [description] [priority]
                if not args:
                    print("Error: Title required")
                    continue
                
                # Simple parsing - first quoted string is title, second is description
                parts = args.split('"')
                if len(parts) >= 2:
                    title = parts[1]
                    rest = parts[2].strip() if len(parts) > 2 else ""
                    desc_parts = rest.split('"')
                    description = desc_parts[1] if len(desc_parts) >= 2 else ""
                    
                    # Check for priority
                    priority = Priority.MEDIUM
                    priority_str = desc_parts[2].strip().lower() if len(desc_parts) > 2 else ""
                    if priority_str in ['high', 'medium', 'low']:
                        priority = Priority(priority_str)
                else:
                    # No quotes, just use as title
                    title = args
                    description = ""
                    priority = Priority.MEDIUM
                
                item = manager.add(title, description, priority)
                print(f"[+] Added: {item}")
            
            elif cmd == "list":
                filter_type = args.lower() if args else "all"
                
                if filter_type == "pending":
                    todos = manager.list_all(completed=False)
                elif filter_type == "completed":
                    todos = manager.list_all(completed=True)
                else:
                    todos = manager.list_all()
                
                if not todos:
                    print("No todos found")
                else:
                    print(f"\n{len(todos)} todo(s):")
                    print("-" * 60)
                    for todo in todos:
                        print(f"{todo.id[:8]}... {todo}")
                        if todo.description:
                            print(f"            {todo.description}")
                    print("-" * 60)
            
            elif cmd == "complete":
                if not args:
                    print("Error: Todo ID required")
                    continue
                
                todo_id = args.strip()
                # Support partial ID matching
                matched = None
                for todo in manager.todos:
                    if todo.id.startswith(todo_id):
                        matched = todo.id
                        break
                
                if matched and manager.mark_complete(matched):
                    print(f"[+] Marked as complete")
                else:
                    print(f"[-] Todo not found: {todo_id}")
            
            elif cmd == "incomplete":
                if not args:
                    print("Error: Todo ID required")
                    continue
                
                todo_id = args.strip()
                matched = None
                for todo in manager.todos:
                    if todo.id.startswith(todo_id):
                        matched = todo.id
                        break
                
                if matched and manager.mark_incomplete(matched):
                    print(f"[+] Marked as incomplete")
                else:
                    print(f"[-] Todo not found: {todo_id}")
            
            elif cmd == "delete":
                if not args:
                    print("Error: Todo ID required")
                    continue
                
                todo_id = args.strip()
                matched = None
                for todo in manager.todos:
                    if todo.id.startswith(todo_id):
                        matched = todo.id
                        break
                
                if matched and manager.delete(matched):
                    print(f"[+] Deleted")
                else:
                    print(f"[-] Todo not found: {todo_id}")
            
            elif cmd == "stats":
                stats = manager.get_stats()
                print()
                print("Statistics:")
                print(f"  Total: {stats['total']}")
                print(f"  Completed: {stats['completed']}")
                print(f"  Pending: {stats['pending']}")
                print(f"  Priority breakdown:")
                print(f"    High: {stats['by_priority']['high']}")
                print(f"    Medium: {stats['by_priority']['medium']}")
                print(f"    Low: {stats['by_priority']['low']}")
            
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for usage instructions")
        
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == '__main__':
    main()
