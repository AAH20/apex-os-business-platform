"""Dead letter queue for failed messages."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Callable, Optional

from .models import Message, MessageStatus


class DeadLetterQueue:
    """Stores messages that have exhausted all retry attempts.

    Provides inspection, replay, and purge capabilities.
    """

    def __init__(self, max_size: int = 10000) -> None:
        self._max_size = max_size
        self._messages: dict[str, Message] = {}
        self._lock = threading.Lock()
        self._replay_handlers: list[Callable[[Message], None]] = []

    def __len__(self) -> int:
        with self._lock:
            return len(self._messages)

    def add(self, message: Message, error: str) -> Message:
        """Add a failed message to the dead letter queue."""
        message.status = MessageStatus.DEAD_LETTER
        message.error = error
        message.completed_at = datetime.utcnow()

        with self._lock:
            # Evict oldest if at capacity
            if len(self._messages) >= self._max_size:
                oldest_key = min(
                    self._messages.keys(),
                    key=lambda k: self._messages[k].completed_at or datetime.utcnow(),
                )
                del self._messages[oldest_key]
            self._messages[message.message_id] = message
        return message

    def get(self, message_id: str) -> Optional[Message]:
        """Retrieve a dead letter message by ID."""
        with self._lock:
            return self._messages.get(message_id)

    def get_all(self) -> list[Message]:
        """Return all dead letter messages."""
        with self._lock:
            return list(self._messages.values())

    def get_by_queue(self, queue_name: str) -> list[Message]:
        """Return dead letter messages filtered by original queue name."""
        with self._lock:
            return [m for m in self._messages.values() if m.queue_name == queue_name]

    def get_by_error(self, error_pattern: str) -> list[Message]:
        """Return dead letter messages whose error matches a substring."""
        with self._lock:
            return [m for m in self._messages.values() if m.error and error_pattern in m.error]

    def replay(self, message_id: str) -> Optional[Message]:
        """Replay a dead letter message: reset it for reprocessing."""
        with self._lock:
            message = self._messages.get(message_id)
            if message is None:
                return None
            # Reset message state
            message.status = MessageStatus.PENDING
            message.error = None
            message.retry_count = 0
            message.completed_at = None
            message.scheduled_at = None
            del self._messages[message_id]

        # Notify replay handlers
        for handler in self._replay_handlers:
            handler(message)
        return message

    def replay_all(self) -> list[Message]:
        """Replay all dead letter messages."""
        with self._lock:
            message_ids = list(self._messages.keys())
        replayed = []
        for msg_id in message_ids:
            msg = self.replay(msg_id)
            if msg:
                replayed.append(msg)
        return replayed

    def remove(self, message_id: str) -> bool:
        """Permanently remove a message from the dead letter queue."""
        with self._lock:
            if message_id in self._messages:
                del self._messages[message_id]
                return True
            return False

    def clear(self) -> None:
        """Remove all dead letter messages."""
        with self._lock:
            self._messages.clear()

    def register_replay_handler(self, handler: Callable[[Message], None]) -> None:
        """Register a callback invoked when a message is replayed."""
        self._replay_handlers.append(handler)

    def get_stats(self) -> dict[str, Any]:
        """Return dead letter queue statistics."""
        with self._lock:
            by_queue: dict[str, int] = {}
            by_error: dict[str, int] = {}
            for msg in self._messages.values():
                by_queue[msg.queue_name] = by_queue.get(msg.queue_name, 0) + 1
                error_key = msg.error[:50] if msg.error else "unknown"
                by_error[error_key] = by_error.get(error_key, 0) + 1
            return {
                "total_dead_letter": len(self._messages),
                "by_queue": by_queue,
                "by_error": by_error,
                "max_size": self._max_size,
            }
