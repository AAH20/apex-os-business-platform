"""Message queue data models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class MessagePriority(int, Enum):
    """Message priority levels (lower value = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class MessageStatus(str, Enum):
    """Message lifecycle status."""
    PENDING = "pending"
    DELAYED = "delayed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    RETRYING = "retrying"


@dataclass
class Message:
    """A single message in the queue."""
    payload: Any
    priority: MessagePriority = MessagePriority.NORMAL
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    queue_name: str = "default"
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    delay_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "payload": self.payload,
            "priority": self.priority.value,
            "queue_name": self.queue_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "delay_seconds": self.delay_seconds,
            "metadata": self.metadata,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            payload=data["payload"],
            priority=MessagePriority(data.get("priority", 2)),
            message_id=data.get("message_id", str(uuid.uuid4())),
            queue_name=data.get("queue_name", "default"),
            status=MessageStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
            processed_at=datetime.fromisoformat(data["processed_at"]) if data.get("processed_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            delay_seconds=data.get("delay_seconds", 0.0),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
        )

    def is_ready(self) -> bool:
        """Check if the message is ready to be processed."""
        if self.status in (MessageStatus.COMPLETED, MessageStatus.DEAD_LETTER):
            return False
        if self.scheduled_at and datetime.utcnow() < self.scheduled_at:
            return False
        return True

    def can_retry(self) -> bool:
        """Check if the message can be retried."""
        return self.retry_count < self.max_retries


@dataclass
class QueueStats:
    """Statistics for a single queue."""
    queue_name: str
    pending_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    dead_letter_count: int = 0
    delayed_count: int = 0
    total_enqueued: int = 0
    total_processed: int = 0
    avg_processing_time_ms: float = 0.0
    oldest_message_age_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_name": self.queue_name,
            "pending_count": self.pending_count,
            "processing_count": self.processing_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "dead_letter_count": self.dead_letter_count,
            "delayed_count": self.delayed_count,
            "total_enqueued": self.total_enqueued,
            "total_processed": self.total_processed,
            "avg_processing_time_ms": self.avg_processing_time_ms,
            "oldest_message_age_seconds": self.oldest_message_age_seconds,
        }
