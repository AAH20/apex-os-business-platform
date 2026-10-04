"""Notification manager for orchestrating notifications."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from apex_os_bp.notifications.channels import (
    BaseChannel,
    ChannelResult,
)
from apex_os_bp.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)
from apex_os_bp.notifications.templates import TemplateRegistry

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages notification channels and sending."""

    def __init__(self):
        self._channels: Dict[NotificationChannel, BaseChannel] = {}
        self._template_registry = TemplateRegistry()
        self._notifications: Dict[str, Notification] = {}
        self._history: List[Notification] = []
        self._max_history = 10000

    def register_channel(self, channel: BaseChannel) -> None:
        """Register a notification channel."""
        self._channels[channel.channel_type] = channel

    def unregister_channel(self, channel_type: NotificationChannel) -> bool:
        """Unregister a notification channel."""
        if channel_type in self._channels:
            del self._channels[channel_type]
            return True
        return False

    def get_channel(self, channel_type: NotificationChannel) -> Optional[BaseChannel]:
        """Get a registered channel."""
        return self._channels.get(channel_type)

    @property
    def template_registry(self) -> TemplateRegistry:
        """Get the template registry."""
        return self._template_registry

    def create_notification(
        self,
        title: str,
        body: str,
        channels: List[NotificationChannel],
        recipients: List[str],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            title=title,
            body=body,
            channels=channels,
            recipients=recipients,
            priority=priority,
            template_id=template_id,
            template_data=template_data or {},
            metadata=metadata or {},
        )
        self._notifications[notification.id] = notification
        return notification

    def create_from_template(
        self,
        template_id: str,
        data: Dict[str, Any],
        recipients: List[str],
        channels: Optional[List[NotificationChannel]] = None,
        priority: Optional[NotificationPriority] = None,
    ) -> Optional[Notification]:
        """Create a notification from a template."""
        template = self._template_registry.get(template_id)
        if not template:
            logger.error(f"Template not found: {template_id}")
            return None

        rendered = template.render(data)
        if not rendered:
            return None

        channel_list = channels or [NotificationChannel(c) for c in template.channels]
        notif_priority = priority or NotificationPriority(template.default_priority)

        return self.create_notification(
            title=rendered["title"],
            body=rendered["body"],
            channels=channel_list,
            recipients=recipients,
            priority=notif_priority,
            template_id=template_id,
            template_data=data,
        )

    def send(self, notification: Notification) -> Dict[NotificationChannel, ChannelResult]:
        """Send a notification through all its channels."""
        results = {}

        for channel_type in notification.channels:
            channel = self._channels.get(channel_type)
            if not channel:
                results[channel_type] = ChannelResult(
                    success=False,
                    channel=channel_type,
                    error=f"Channel {channel_type.value} not registered",
                )
                notification.mark_failed(f"Channel {channel_type.value} not registered")
                continue

            result = channel.send(notification)
            results[channel_type] = result

            if result.success:
                notification.mark_sent()
            else:
                notification.mark_failed(result.error or "Unknown error")

        self._add_to_history(notification)
        return results

    def send_by_id(self, notification_id: str) -> Optional[Dict[NotificationChannel, ChannelResult]]:
        """Send a notification by its ID."""
        notification = self._notifications.get(notification_id)
        if not notification:
            logger.error(f"Notification not found: {notification_id}")
            return None
        return self.send(notification)

    def retry(self, notification: Notification) -> Dict[NotificationChannel, ChannelResult]:
        """Retry sending a failed notification."""
        if not notification.can_retry():
            logger.warning(f"Notification {notification.id} exceeded max retries")
            return {}

        notification.mark_retrying()
        return self.send(notification)

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        return self._notifications.get(notification_id)

    def get_history(
        self,
        status: Optional[NotificationStatus] = None,
        channel: Optional[NotificationChannel] = None,
    ) -> List[Notification]:
        """Get notification history with optional filters."""
        history = self._history
        if status:
            history = [n for n in history if n.status == status]
        if channel:
            history = [n for n in history if channel in n.channels]
        return history

    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        total = len(self._history)
        by_status: Dict[str, int] = {}
        by_channel: Dict[str, int] = {}

        for n in self._history:
            status_val = n.status.value
            by_status[status_val] = by_status.get(status_val, 0) + 1
            for ch in n.channels:
                ch_val = ch.value
                by_channel[ch_val] = by_channel.get(ch_val, 0) + 1

        channel_stats = {}
        for ch_type, ch in self._channels.items():
            channel_stats[ch_type.value] = ch.get_stats()

        return {
            "total": total,
            "by_status": by_status,
            "by_channel": by_channel,
            "channels": channel_stats,
        }

    def clear_history(self) -> None:
        """Clear notification history."""
        self._history.clear()

    def _add_to_history(self, notification: Notification) -> None:
        """Add notification to history."""
        self._history.append(notification)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
