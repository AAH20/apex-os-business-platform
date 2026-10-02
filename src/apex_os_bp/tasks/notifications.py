"""Task notifications feature."""

from datetime import datetime
from typing import Callable, Optional

from .models import Task, TaskEvent


class NotificationService:
    """Sends notifications for task events."""

    def __init__(self):
        self._handlers: list[Callable] = []
        self._notifications: list[dict] = []

    def register_handler(self, handler: Callable) -> None:
        """Register a notification handler callback."""
        self._handlers.append(handler)

    def notify(self, task: Task, event: TaskEvent) -> dict:
        """Send a notification for a task event.

        Args:
            task: The task that triggered the event.
            event: The event details.

        Returns:
            The notification record.
        """
        notification = {
            "notification_id": str(len(self._notifications) + 1),
            "task_id": task.task_id,
            "event_type": event.event_type,
            "message": self._format_message(task, event),
            "timestamp": datetime.utcnow().isoformat(),
            "read": False,
        }
        self._notifications.append(notification)

        for handler in self._handlers:
            handler(notification)

        return notification

    def _format_message(self, task: Task, event: TaskEvent) -> str:
        """Format a human-readable notification message."""
        templates = {
            "created": f"Task '{task.title}' was created",
            "assigned": f"Task '{task.title}' was assigned to {task.assignee}",
            "unassigned": f"Task '{task.title}' was unassigned",
            "scheduled": f"Task '{task.title}' was scheduled",
            "due_date_set": f"Task '{task.title}' due date updated",
            "status_changed": f"Task '{task.title}' status changed to {task.status.value}",
            "completed": f"Task '{task.title}' was completed",
            "cancelled": f"Task '{task.title}' was cancelled",
            "progress_updated": f"Task '{task.title}' progress updated to {task.progress}%",
        }
        return templates.get(event.event_type, f"Task '{task.title}': {event.event_type}")

    def get_notifications(self, unread_only: bool = False) -> list:
        """Get all notifications, optionally filtered to unread only."""
        if unread_only:
            return [n for n in self._notifications if not n["read"]]
        return list(self._notifications)

    def mark_read(self, notification_id: int) -> bool:
        """Mark a notification as read."""
        for n in self._notifications:
            if n["notification_id"] == str(notification_id):
                n["read"] = True
                return True
        return False

    def clear(self) -> None:
        """Clear all notifications."""
        self._notifications.clear()
