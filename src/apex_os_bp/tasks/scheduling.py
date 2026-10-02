"""Task scheduling feature."""

from datetime import datetime, timedelta
from typing import Optional

from .models import Task, TaskEvent


class TaskScheduler:
    """Schedules tasks for future execution and manages due dates."""

    def schedule(self, task: Task, scheduled_at: datetime) -> Task:
        """Schedule a task for a specific time.

        Args:
            task: The task to schedule.
            scheduled_at: When the task should be executed.

        Returns:
            The updated task.

        Raises:
            ValueError: If scheduled_at is in the past.
        """
        if scheduled_at < datetime.utcnow():
            raise ValueError("Scheduled time cannot be in the past")

        task.scheduled_at = scheduled_at
        task.updated_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.task_id,
            event_type="scheduled",
            details={"scheduled_at": scheduled_at.isoformat()},
        )
        task.events.append(event)

        return task

    def reschedule(self, task: Task, new_time: datetime) -> Task:
        """Change the scheduled time of a task.

        Args:
            task: The task to reschedule.
            new_time: The new scheduled time.

        Returns:
            The updated task.
        """
        return self.schedule(task, new_time)

    def set_due_date(self, task: Task, due_date: datetime) -> Task:
        """Set or update the due date of a task.

        Args:
            task: The task to update.
            due_date: The due date.

        Returns:
            The updated task.
        """
        task.due_date = due_date
        task.updated_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.task_id,
            event_type="due_date_set",
            details={"due_date": due_date.isoformat()},
        )
        task.events.append(event)

        return task

    def is_overdue(self, task: Task) -> bool:
        """Check if a task is past its due date.

        Args:
            task: The task to check.

        Returns:
            True if the task has a due date in the past and is not completed.
        """
        if task.due_date is None:
            return False
        if task.status.value == "completed":
            return False
        return datetime.utcnow() > task.due_date

    def is_due_soon(self, task: Task, within_hours: int = 24) -> bool:
        """Check if a task is due within a given time window.

        Args:
            task: The task to check.
            within_hours: Hours to look ahead.

        Returns:
            True if the task is due within the specified hours.
        """
        if task.due_date is None:
            return False
        if task.status.value == "completed":
            return False
        now = datetime.utcnow()
        return now <= task.due_date <= now + timedelta(hours=within_hours)
