"""
TODO List Manager - TodoManager Class
Manages a collection of todo items with persistence
"""
import json
from pathlib import Path
from typing import List, Optional
from todo_item import TodoItem, Priority


class TodoManager:
    """
    Manages a collection of todo items.
    
    Attributes:
        todos (List[TodoItem]): List of all todo items
        data_file (Path): Path to the JSON file for persistence
    """
    
    def __init__(self, data_file: str = "todos.json"):
        """
        Initialize TodoManager.
        
        Args:
            data_file: Path to JSON file for saving todos
        """
        self.data_file = Path(data_file)
        self.todos: List[TodoItem] = []
        self.load()
    
    def add(self, title: str, description: str = "", 
            priority: Priority = Priority.MEDIUM) -> TodoItem:
        """
        Add a new todo item.
        
        Args:
            title: Todo title
            description: Detailed description
            priority: Priority level
            
        Returns:
            The created TodoItem
            
        Raises:
            ValueError: If title is empty
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        
        item = TodoItem(
            title=title.strip(),
            description=description.strip(),
            priority=priority
        )
        self.todos.append(item)
        self.save()
        return item
    
    def list_all(self, priority: Optional[Priority] = None,
                 completed: Optional[bool] = None) -> List[TodoItem]:
        """
        List all todos with optional filtering.
        
        Args:
            priority: Filter by priority (optional)
            completed: Filter by completion status (optional)
            
        Returns:
            List of filtered TodoItems
        """
        filtered = self.todos
        
        if priority is not None:
            filtered = [t for t in filtered if t.priority == priority]
        
        if completed is not None:
            filtered = [t for t in filtered if t.completed == completed]
        
        return filtered
    
    def get_by_id(self, todo_id: str) -> Optional[TodoItem]:
        """
        Get a todo item by ID.
        
        Args:
            todo_id: The unique ID of the todo
            
        Returns:
            TodoItem if found, None otherwise
        """
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None
    
    def update(self, todo_id: str, **kwargs) -> bool:
        """
        Update a todo item.
        
        Args:
            todo_id: ID of the todo to update
            **kwargs: Fields to update (title, description, priority)
            
        Returns:
            True if updated, False if not found
        """
        todo = self.get_by_id(todo_id)
        if todo:
            todo.update(**kwargs)
            self.save()
            return True
        return False
    
    def delete(self, todo_id: str) -> bool:
        """
        Delete a todo item.
        
        Args:
            todo_id: ID of the todo to delete
            
        Returns:
            True if deleted, False if not found
        """
        todo = self.get_by_id(todo_id)
        if todo:
            self.todos.remove(todo)
            self.save()
            return True
        return False
    
    def mark_complete(self, todo_id: str) -> bool:
        """
        Mark a todo as complete.
        
        Args:
            todo_id: ID of the todo
            
        Returns:
            True if marked, False if not found
        """
        todo = self.get_by_id(todo_id)
        if todo:
            todo.mark_complete()
            self.save()
            return True
        return False
    
    def mark_incomplete(self, todo_id: str) -> bool:
        """
        Mark a todo as incomplete.
        
        Args:
            todo_id: ID of the todo
            
        Returns:
            True if marked, False if not found
        """
        todo = self.get_by_id(todo_id)
        if todo:
            todo.mark_incomplete()
            self.save()
            return True
        return False
    
    def save(self) -> None:
        """Save todos to JSON file"""
        try:
            data = [todo.to_dict() for todo in self.todos]
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving todos: {e}")
    
    def load(self) -> None:
        """Load todos from JSON file"""
        if not self.data_file.exists():
            return
        
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            self.todos = [TodoItem.from_dict(item) for item in data]
        except Exception as e:
            print(f"Error loading todos: {e}")
            self.todos = []
    
    def get_stats(self) -> dict:
        """
        Get statistics about todos.
        
        Returns:
            Dictionary with todo statistics
        """
        total = len(self.todos)
        completed = sum(1 for t in self.todos if t.completed)
        pending = total - completed
        
        by_priority = {
            'high': sum(1 for t in self.todos if t.priority == Priority.HIGH),
            'medium': sum(1 for t in self.todos if t.priority == Priority.MEDIUM),
            'low': sum(1 for t in self.todos if t.priority == Priority.LOW)
        }
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'by_priority': by_priority
        }
