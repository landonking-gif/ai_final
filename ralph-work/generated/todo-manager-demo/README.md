# TODO List Manager

A command-line TODO list manager with persistent storage.

## Features

- Add, list, complete, and delete TODO items
- Priority levels (high, medium, low)
- Filter by completion status
- Persistent storage using JSON
- Statistics and reporting

## Installation

1. Ensure Python 3.7+ is installed
2. No external dependencies required (uses only standard library)

## Usage

Run the application:
```bash
python main.py
```

### Commands

- `add "title" ["description"] [priority]` - Add a new todo
- `list [all|pending|completed]` - List todos
- `complete <id>` - Mark todo as complete
- `incomplete <id>` - Mark todo as incomplete
- `delete <id>` - Delete a todo
- `stats` - Show statistics
- `help` - Show help message
- `exit` - Exit the program

### Examples

```bash
# Add a high priority todo
> add "Buy groceries" "Milk, eggs, bread" high

# List pending todos
> list pending

# Complete a todo (use first few characters of ID)
> complete abc123

# Show statistics
> stats
```

## File Structure

```
todo-manager-demo/
├── main.py           # CLI interface
├── todo_manager.py   # Core manager class
├── todo_item.py      # TodoItem data model
└── README.md         # This file
```

## Data Storage

Todos are saved in `todos.json` in the current directory.

## Features

- **TodoItem**: Data model with UUID, timestamps, priorities
- **TodoManager**: CRUD operations with persistence
- **CLI**: User-friendly command-line interface
- **Validation**: Input validation and error handling
- **Documentation**: Comprehensive docstrings throughout

## Testing

To test the application:

1. Run the program: `python main.py`
2. Add some todos
3. Try listing, completing, and deleting
4. Check that data persists by exiting and restarting

## Code Quality

- ✓ Type hints throughout
- ✓ Comprehensive docstrings
- ✓ Error handling
- ✓ Clean separation of concerns
- ✓ Follows PEP 8 style guide
