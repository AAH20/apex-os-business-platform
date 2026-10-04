"""Task assignment feature."""

from datetime import datetime

from .models import Task, TaskEvent


class TaskAssigner:
    """Assigns and reassigns tasks to users."""

    def assign(self, task: Task, assignee: str) -> Task:
        """Assign a task to a user.

        Args:
            task: The task to assign.
            assignee: The user to assign the task to.

        Returns:
            The updated task.

        Raises:
            ValueError: If assignee is empty.
        """
        if not assignee or not assignee.strip():
            raise ValueError("Assignee cannot be empty")

        old_assignee = task.assignee
        task.assignee = assignee.strip()
        task.updated_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.task_id,
            event_type="assigned",
            details={"old_assignee": old_assignee, "new_assignee": task.assignee},
        )
        task.events.append(event)

        return task

    def unassign(self, task: Task) -> Task:
        """Remove assignment from a task.

        Args:
            task: The task to unassign.

        Returns:
            The updated task.
        """
        old_assignee = task.assignee
        task.assignee = None
        task.updated_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.task_id,
            event_type="unassigned",
            details={"old_assignee": old_assignee},
        )
        task.events.append(event)

        return task

    def reassign(self, task: Task, new_assignee: str) -> Task:
        """Reassign a task to a different user.

        Args:
            task: The task to reassign.
            new_assignee: The new user to assign the task to.

        Returns:
            The updated task.
        """
        return self.assign(task, new_assignee)
