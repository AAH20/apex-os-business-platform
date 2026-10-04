"""Main message queue manager — orchestrates all queue components."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Optional

from .models import Message, MessagePriority, MessageStatus
from .priority_queue import PriorityQueue
from .delayed_queue import DelayedQueue
from .dead_letter import DeadLetterQueue
from .batching import MessageBatcher
from .monitoring import QueueMonitor


class MessageQueueManager:
    """Unified message queue manager.

    Combines priority queues, delayed delivery, dead letter handling,
    batching, and monitoring into a single interface.
    """

    def __init__(
        self,
        max_retries: int = 3,
        dead_letter_max_size: int = 10000,
        batch_size: int = 100,
        batch_wait_seconds: float = 5.0,
    ) -> None:
        self._queues: dict[str, PriorityQueue] = {}
        self._delayed = DelayedQueue()
        self._dead_letter = DeadLetterQueue(max_size=dead_letter_max_size)
        self._monitor = QueueMonitor()
        self._max_retries = max_retries
        self._batch_size = batch_size
        self._batch_wait_seconds = batch_wait_seconds
        self._batchers: dict[str, MessageBatcher] = {}
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    @property
    def monitor(self) -> QueueMonitor:
        return self._monitor

    @property
    def dead_letter(self) -> DeadLetterQueue:
        return self._dead_letter

    @property
    def delayed(self) -> DelayedQueue:
        return self._delayed

    def create_queue(self, name: str) -> PriorityQueue:
        """Create a new named queue."""
        with self._lock:
            if name not in self._queues:
                self._queues[name] = PriorityQueue(name=name)
            return self._queues[name]

    def get_queue(self, name: str) -> Optional[PriorityQueue]:
        """Get a queue by name."""
        return self._queues.get(name)

    def enqueue(
        self,
        payload: Any,
        queue_name: str = "default",
        priority: MessagePriority = MessagePriority.NORMAL,
        delay_seconds: float = 0.0,
        max_retries: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> Message:
        """Enqueue a message for processing."""
        message = Message(
            payload=payload,
            priority=priority,
            queue_name=queue_name,
            max_retries=max_retries if max_retries is not None else self._max_retries,
            metadata=metadata or {},
            tags=tags or [],
        )

        if delay_seconds > 0:
            self._delayed.schedule(message, delay_seconds)
            self._monitor.record_delayed(message)
        else:
            queue = self.create_queue(queue_name)
            queue.enqueue(message)
            self._monitor.record_enqueue(message)

        return message

    def enqueue_at(
        self,
        payload: Any,
        deliver_at: datetime,
        queue_name: str = "default",
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """Enqueue a message for delivery at a specific time."""
        message = Message(
            payload=payload,
            priority=priority,
            queue_name=queue_name,
            metadata=metadata or {},
        )
        self._delayed.schedule_at(message, deliver_at)
        self._monitor.record_delayed(message)
        return message

    def dequeue(self, queue_name: str = "default") -> Optional[Message]:
        """Dequeue the next ready message from a queue."""
        # First, promote any ready delayed messages
        self._promote_delayed()

        queue = self._queues.get(queue_name)
        if not queue:
            return None

        message = queue.dequeue()
        if message:
            message.status = MessageStatus.PROCESSING
            message.processed_at = datetime.utcnow()
            self._monitor.record_dequeue(message)
        return message

    def complete(self, message: Message) -> None:
        """Mark a message as successfully completed."""
        message.status = MessageStatus.COMPLETED
        message.completed_at = datetime.utcnow()
        processing_time = 0.0
        if message.processed_at:
            processing_time = (message.completed_at - message.processed_at).total_seconds() * 1000
        self._monitor.record_complete(message, processing_time)

    def fail(self, message: Message, error: str) -> None:
        """Mark a message as failed. Retries or sends to dead letter queue."""
        message.error = error

        if message.can_retry():
            message.retry_count += 1
            # Re-enqueue with exponential backoff
            backoff = 2 ** message.retry_count
            self._delayed.schedule(message, delay_seconds=backoff)
            message.status = MessageStatus.RETRYING
        else:
            message.retry_count += 1
            message.status = MessageStatus.DEAD_LETTER
            self._dead_letter.add(message, error)
            self._monitor.record_dead_letter(message)

        self._monitor.record_failure(message)

    def retry(self, message: Message) -> bool:
        """Manually retry a failed message."""
        if message.status == MessageStatus.DEAD_LETTER:
            replayed = self._dead_letter.replay(message.message_id)
            if replayed:
                queue = self.create_queue(message.queue_name)
                queue.enqueue(replayed)
                self._monitor.record_enqueue(replayed)
                return True
        return False

    def get_batcher(self, queue_name: str = "default") -> MessageBatcher:
        """Get or create a batcher for a queue."""
        if queue_name not in self._batchers:
            self._batchers[queue_name] = MessageBatcher(
                max_size=self._batch_size,
                max_wait_seconds=self._batch_wait_seconds,
            )
        return self._batchers[queue_name]

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive queue statistics."""
        queue_stats = {}
        for name, queue in self._queues.items():
            queue_stats[name] = queue.get_stats()

        return {
            "queues": queue_stats,
            "delayed": self._delayed.get_stats(),
            "dead_letter": self._dead_letter.get_stats(),
            "monitoring": self._monitor.get_summary(),
        }

    def start(self) -> None:
        """Start the background worker for delayed message promotion."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        """Stop the background worker."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            self._worker_thread = None

    def _promote_delayed(self) -> None:
        """Move ready delayed messages to their target queues."""
        ready = self._delayed.get_ready_messages()
        for message in ready:
            queue = self.create_queue(message.queue_name)
            queue.enqueue(message)
            self._monitor.record_enqueue(message)

    def _worker_loop(self) -> None:
        """Background worker that promotes delayed messages."""
        while self._running:
            try:
                self._promote_delayed()
                # Also flush batchers that have exceeded wait time
                for batcher in self._batchers.values():
                    batcher.maybe_flush()
            except Exception:
                pass
            time.sleep(0.1)
