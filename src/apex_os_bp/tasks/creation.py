"""Task creation feature."""

from datetime import datetime
from typing import Optional

from .models import Task, TaskPriority, TaskEvent


class TaskCreator:
    """Creates new tasks with validation."""

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        creator: Optional[str] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[list] = None,
    ) -> Task:
        """Create a new task.

        Args:
            title: Short task title (required, non-empty).
            description: Detailed description.
            priority: Task priority level.
            creator: Who created the task.
            due_date: Optional deadline.
            tags: Optional list of tag strings.

        Returns:
            The newly created Task.

        Raises:
            ValueError: If title is empty.
        """
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty")

        task = Task(
            title=title.strip(),
            description=description,
            priority=priority,
            creator=creator,
            due_date=due_date,
            tags=tags or [],
        )

        event = TaskEvent(
            task_id=task.task_id,
            event_type="created",
            details={"title": task.title, "creator": creator},
        )
        task.events.append(event)

        return task
