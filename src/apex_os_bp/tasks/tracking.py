"""Task tracking feature."""

from datetime import datetime
from typing import Optional

from .models import Task, TaskStatus, TaskEvent


class TaskTracker:
    """Tracks task progress and status transitions."""

    def start(self, task: Task) -> Task:
        """Mark a task as in progress.

        Args:
            task: The task to start.

        Returns:
            The updated task.
        """
        old_status = task.status
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.task_id,
            event_type="status_changed",
            details={"old_status": old_status.value, "new_status": task.status.value},
        )
        task.events.append(event)

        return task

    def complete(self, task: Task) -> Task:
        """Mark a task as completed.

        Args:
            task: The task to complete.

        Returns:
            The updated task.
        """
        old_status = task.status
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.progress = 100
        task.updated_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.task_id,
            event_type="completed",
            details={"old_status": old_status.value},
        )
        task.events.append(event)

        return task

    def cancel(self, task: Task, reason: str = "") -> Task:
        """Cancel a task.

        Args:
            task: The task to cancel.
            reason: Optional cancellation reason.

        Returns:
            The updated task.
        """
        old_status = task.status
        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.task_id,
            event_type="cancelled",
            details={"old_status": old_status.value, "reason": reason},
        )
        task.events.append(event)

        return task

    def update_progress(self, task: Task, progress: int) -> Task:
        """Update task progress percentage.

        Args:
            task: The task to update.
            progress: Progress value 0-100.

        Returns:
            The updated task.

        Raises:
            ValueError: If progress is not between 0 and 100.
        """
        if not 0 <= progress <= 100:
            raise ValueError("Progress must be between 0 and 100")

        task.progress = progress
        task.updated_at = datetime.utcnow()

        if progress == 100 and task.status != TaskStatus.COMPLETED:
            self.complete(task)
        elif progress > 0 and task.status == TaskStatus.PENDING:
            self.start(task)

        event = TaskEvent(
            task_id=task.task_id,
            event_type="progress_updated",
            details={"progress": progress},
        )
        task.events.append(event)

        return task

    def get_progress(self, task: Task) -> int:
        """Get current progress of a task.

        Args:
            task: The task to check.

        Returns:
            Progress percentage (0-100).
        """
        return task.progress

    def get_status(self, task: Task) -> TaskStatus:
        """Get current status of a task.

        Args:
            task: The task to check.

        Returns:
            Current task status.
        """
        return task.status

    def get_completion_time(self, task: Task) -> Optional[datetime]:
        """Get the completion time of a task.

        Args:
            task: The task to check.

        Returns:
            Completion datetime or None if not completed.
        """
        return task.completed_at
