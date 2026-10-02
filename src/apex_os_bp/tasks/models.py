"""Task data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskEvent:
    """Represents a state change or action on a task."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict = field(default_factory=dict)


@dataclass
class Task:
    """Core task entity."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee: Optional[str] = None
    creator: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tags: list = field(default_factory=list)
    events: list = field(default_factory=list)
    progress: int = 0  # 0-100

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "assignee": self.assignee,
            "creator": self.creator,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tags": list(self.tags),
            "progress": self.progress,
        }
