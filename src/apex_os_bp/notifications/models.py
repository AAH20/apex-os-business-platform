"""Notification data models."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NotificationStatus(str, Enum):
    """Status of a notification."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Available notification channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


@dataclass
class Notification:
    """A notification to be sent through one or more channels."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    body: str = ""
    channels: List[NotificationChannel] = field(default_factory=list)
    recipients: List[str] = field(default_factory=list)
    priority: NotificationPriority = NotificationPriority.NORMAL
    status: NotificationStatus = NotificationStatus.PENDING
    template_id: Optional[str] = None
    template_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    sent_at: Optional[float] = None
    delivered_at: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def mark_sent(self) -> None:
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = time.time()

    def mark_delivered(self) -> None:
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = time.time()

    def mark_failed(self, error: str) -> None:
        """Mark notification as failed."""
        self.status = NotificationStatus.FAILED
        self.error_message = error

    def mark_retrying(self) -> None:
        """Mark notification as retrying."""
        self.status = NotificationStatus.RETRYING
        self.retry_count += 1

    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return self.retry_count < self.max_retries

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "channels": [c.value for c in self.channels],
            "recipients": self.recipients,
            "priority": self.priority.value,
            "status": self.status.value,
            "template_id": self.template_id,
            "template_data": self.template_data,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "sent_at": self.sent_at,
            "delivered_at": self.delivered_at,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Notification:
        """Create notification from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            body=data.get("body", ""),
            channels=[NotificationChannel(c) for c in data.get("channels", [])],
            recipients=data.get("recipients", []),
            priority=NotificationPriority(data.get("priority", "normal")),
            status=NotificationStatus(data.get("status", "pending")),
            template_id=data.get("template_id"),
            template_data=data.get("template_data", {}),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            sent_at=data.get("sent_at"),
            delivered_at=data.get("delivered_at"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )
