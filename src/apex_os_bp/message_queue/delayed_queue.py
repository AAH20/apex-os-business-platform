"""Delayed message queue with scheduled delivery."""

from __future__ import annotations

import heapq
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from .models import Message, MessageStatus


class DelayedQueue:
    """Queue for messages that should be delivered after a delay.

    Messages are stored in a min-heap ordered by their scheduled delivery time.
    A background worker promotes messages to the target queue when ready.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[float, str, Message]] = []
        self._lock = threading.Lock()
        self._message_map: dict[str, Message] = {}
        self._counter = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._message_map)

    def schedule(self, message: Message, delay_seconds: float) -> Message:
        """Schedule a message for delayed delivery."""
        message.delay_seconds = delay_seconds
        message.scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        message.status = MessageStatus.DELAYED

        with self._lock:
            self._counter += 1
            # Heap: (scheduled_timestamp, counter, message_id, message)
            entry = (message.scheduled_at.timestamp(), self._counter, message.message_id, message)
            heapq.heappush(self._heap, entry)
            self._message_map[message.message_id] = message
        return message

    def schedule_at(self, message: Message, deliver_at: datetime) -> Message:
        """Schedule a message for delivery at a specific time."""
        delay = (deliver_at - datetime.utcnow()).total_seconds()
        if delay < 0:
            delay = 0
        message.delay_seconds = delay
        message.scheduled_at = deliver_at
        message.status = MessageStatus.DELAYED

        with self._lock:
            self._counter += 1
            entry = (deliver_at.timestamp(), self._counter, message.message_id, message)
            heapq.heappush(self._heap, entry)
            self._message_map[message.message_id] = message
        return message

    def get_ready_messages(self) -> list[Message]:
        """Get all messages whose delay has elapsed."""
        ready: list[Message] = []
        now = datetime.utcnow().timestamp()

        with self._lock:
            while self._heap and self._heap[0][0] <= now:
                _, _, msg_id, message = heapq.heappop(self._heap)
                if msg_id in self._message_map:
                    del self._message_map[msg_id]
                    message.status = MessageStatus.PENDING
                    ready.append(message)
        return ready

    def cancel(self, message_id: str) -> bool:
        """Cancel a delayed message. Returns True if found."""
        with self._lock:
            if message_id in self._message_map:
                del self._message_map[message_id]
                return True
            return False

    def get(self, message_id: str) -> Optional[Message]:
        """Get a delayed message by ID."""
        with self._lock:
            return self._message_map.get(message_id)

    def clear(self) -> None:
        """Remove all delayed messages."""
        with self._lock:
            self._heap.clear()
            self._message_map.clear()
            self._counter = 0

    def get_stats(self) -> dict[str, Any]:
        """Return delayed queue statistics."""
        with self._lock:
            now = datetime.utcnow().timestamp()
            overdue = sum(1 for ts, _, _, _ in self._heap if ts <= now)
            upcoming = len(self._heap) - overdue
            return {
                "total_delayed": len(self._heap),
                "overdue": overdue,
                "upcoming": upcoming,
            }

    def get_pending_messages(self) -> list[Message]:
        """Return all pending delayed messages sorted by scheduled time."""
        with self._lock:
            return [m for _, _, _, m in sorted(self._heap, key=lambda x: x[0])]
