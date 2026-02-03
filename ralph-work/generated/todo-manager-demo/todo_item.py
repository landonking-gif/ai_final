"""
TODO List Manager - TodoItem Class
Represents an individual todo item with all necessary attributes
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class Priority(Enum):
    """Priority levels for todo items"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TodoItem:
    """
    Represents a single todo item.
    
    Attributes:
        id (str): Unique identifier for the todo item
        title (str): Brief title of the todo
        description (str): Detailed description
        priority (Priority): Priority level (high/medium/low)
        completed (bool): Whether the todo is completed
        created_at (datetime): When the todo was created
        updated_at (datetime): When the todo was last updated
    """
    title: str
    description: str = ""
    priority: Priority = Priority.MEDIUM
    completed: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def mark_complete(self) -> None:
        """Mark this todo item as completed"""
        self.completed = True
        self.updated_at = datetime.now()
    
    def mark_incomplete(self) -> None:
        """Mark this todo item as incomplete"""
        self.completed = False
        self.updated_at = datetime.now()
    
    def update(self, title: Optional[str] = None, 
               description: Optional[str] = None,
               priority: Optional[Priority] = None) -> None:
        """
        Update todo item fields.
        
        Args:
            title: New title (optional)
            description: New description (optional)
            priority: New priority (optional)
        """
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if priority is not None:
            self.priority = priority
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert todo item to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value,
            'completed': self.completed,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TodoItem':
        """
        Create TodoItem from dictionary.
        
        Args:
            data: Dictionary containing todo item data
            
        Returns:
            TodoItem instance
        """
        item = cls(
            title=data['title'],
            description=data.get('description', ''),
            priority=Priority(data.get('priority', 'medium')),
            completed=data.get('completed', False),
            id=data.get('id', str(uuid.uuid4()))
        )
        if 'created_at' in data:
            item.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            item.updated_at = datetime.fromisoformat(data['updated_at'])
        return item
    
    def __str__(self) -> str:
        """String representation of todo item"""
        status = "✓" if self.completed else " "
        return f"[{status}] ({self.priority.value}) {self.title}"
