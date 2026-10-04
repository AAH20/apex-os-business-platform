"""Task manager — orchestrates all task features."""

from datetime import datetime
from typing import Optional

from .models import Task, TaskStatus, TaskPriority
from .creation import TaskCreator
from .assignment import TaskAssigner
from .scheduling import TaskScheduler
from .tracking import TaskTracker
from .notifications import NotificationService


class TaskManager:
    """High-level task management facade."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self.creator = TaskCreator()
        self.assigner = TaskAssigner()
        self.scheduler = TaskScheduler()
        self.tracker = TaskTracker()
        self.notifications = NotificationService()

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        creator: Optional[str] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[list] = None,
    ) -> Task:
        """Create and store a new task."""
        task = self.creator.create_task(
            title=title,
            description=description,
            priority=priority,
            creator=creator,
            due_date=due_date,
            tags=tags,
        )
        self._tasks[task.task_id] = task
        self.notifications.notify(task, task.events[-1])
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        assignee: Optional[str] = None,
    ) -> list:
        """List all tasks, optionally filtered."""
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if assignee is not None:
            tasks = [t for t in tasks if t.assignee == assignee]
        return tasks

    def assign_task(self, task_id: str, assignee: str) -> Optional[Task]:
        """Assign a task to a user."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        result = self.assigner.assign(task, assignee)
        self.notifications.notify(result, result.events[-1])
        return result

    def schedule_task(self, task_id: str, scheduled_at: datetime) -> Optional[Task]:
        """Schedule a task."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        result = self.scheduler.schedule(task, scheduled_at)
        self.notifications.notify(result, result.events[-1])
        return result

    def start_task(self, task_id: str) -> Optional[Task]:
        """Start working on a task."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        result = self.tracker.start(task)
        self.notifications.notify(result, result.events[-1])
        return result

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        result = self.tracker.complete(task)
        self.notifications.notify(result, result.events[-1])
        return result

    def update_progress(self, task_id: str, progress: int) -> Optional[Task]:
        """Update task progress."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        result = self.tracker.update_progress(task, progress)
        self.notifications.notify(result, result.events[-1])
        return result

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def get_overdue_tasks(self) -> list:
        """Get all overdue tasks."""
        return [t for t in self._tasks.values() if self.scheduler.is_overdue(t)]

    def get_tasks_due_soon(self, within_hours: int = 24) -> list:
        """Get tasks due within specified hours."""
        return [
            t for t in self._tasks.values()
            if self.scheduler.is_due_soon(t, within_hours)
        ]
