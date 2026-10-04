"""Priority queue implementation with O(log n) operations."""

from __future__ import annotations

import heapq
import threading
from typing import Any, Optional

from .models import Message


class PriorityQueue:
    """Thread-safe priority queue for messages.

    Lower priority value = higher priority (processed first).
    Messages with the same priority are processed FIFO.
    """

    def __init__(self, name: str = "default") -> None:
        self._name = name
        self._heap: list[tuple[int, float, str, Message]] = []
        self._lock = threading.Lock()
        self._counter = 0  # FIFO tiebreaker
        self._message_map: dict[str, Message] = {}

    @property
    def name(self) -> str:
        return self._name

    def __len__(self) -> int:
        with self._lock:
            return len(self._message_map)

    def enqueue(self, message: Message) -> None:
        """Add a message to the priority queue."""
        with self._lock:
            self._counter += 1
            # Heap: (priority, counter, message_id, message)
            entry = (message.priority.value, self._counter, message.message_id, message)
            heapq.heappush(self._heap, entry)
            self._message_map[message.message_id] = message

    def dequeue(self) -> Optional[Message]:
        """Remove and return the highest-priority message. Returns None if empty."""
        with self._lock:
            while self._heap:
                priority, counter, msg_id, message = heapq.heappop(self._heap)
                # Skip messages that were removed or are not ready
                if msg_id not in self._message_map:
                    continue
                if not message.is_ready():
                    # Put back if not ready (delayed)
                    heapq.heappush(self._heap, (priority, counter, msg_id, message))
                    return None
                del self._message_map[msg_id]
                return message
            return None

    def peek(self) -> Optional[Message]:
        """Return the highest-priority message without removing it."""
        with self._lock:
            for priority, counter, msg_id, message in self._heap:
                if msg_id in self._message_map and message.is_ready():
                    return message
            return None

    def remove(self, message_id: str) -> bool:
        """Remove a message by ID. Returns True if found and removed."""
        with self._lock:
            if message_id in self._message_map:
                del self._message_map[message_id]
                return True
            return False

    def get(self, message_id: str) -> Optional[Message]:
        """Get a message by ID without removing it."""
        with self._lock:
            return self._message_map.get(message_id)

    def clear(self) -> None:
        """Remove all messages from the queue."""
        with self._lock:
            self._heap.clear()
            self._message_map.clear()
            self._counter = 0

    def get_all_pending(self) -> list[Message]:
        """Return all pending messages sorted by priority."""
        with self._lock:
            return sorted(
                [m for m in self._message_map.values() if m.is_ready()],
                key=lambda m: (m.priority.value, m.created_at),
            )

    def get_stats(self) -> dict[str, Any]:
        """Return queue statistics."""
        with self._lock:
            pending = len(self._message_map)
            by_priority: dict[str, int] = {}
            for msg in self._message_map.values():
                p_name = msg.priority.name
                by_priority[p_name] = by_priority.get(p_name, 0) + 1
            return {
                "queue_name": self._name,
                "pending_count": pending,
                "by_priority": by_priority,
            }
