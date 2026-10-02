"""Message batching for efficient bulk processing."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from .models import Message, MessageStatus


class MessageBatcher:
    """Batches messages for efficient bulk processing.

    Flushes when either max_size is reached or max_wait_seconds elapses.
    """

    def __init__(
        self,
        max_size: int = 100,
        max_wait_seconds: float = 5.0,
        flush_handler: Optional[Callable[[list[Message]], None]] = None,
    ) -> None:
        self._max_size = max_size
        self._max_wait_seconds = max_wait_seconds
        self._flush_handler = flush_handler
        self._buffer: list[Message] = []
        self._lock = threading.Lock()
        self._last_flush = time.monotonic()
        self._total_batched = 0
        self._total_flushes = 0

    def add(self, message: Message) -> Optional[list[Message]]:
        """Add a message to the batch. Returns the batch if it was flushed."""
        flushed: Optional[list[Message]] = None

        with self._lock:
            self._buffer.append(message)
            self._total_batched += 1

            if len(self._buffer) >= self._max_size:
                flushed = self._do_flush()

        return flushed

    def flush(self) -> list[Message]:
        """Force flush the current batch."""
        with self._lock:
            return self._do_flush()

    def _do_flush(self) -> list[Message]:
        """Internal flush — must be called with lock held."""
        if not self._buffer:
            return []
        batch = self._buffer[:]
        self._buffer.clear()
        self._last_flush = time.monotonic()
        self._total_flushes += 1

        if self._flush_handler:
            self._flush_handler(batch)
        return batch

    def maybe_flush(self) -> Optional[list[Message]]:
        """Flush if max_wait_seconds have elapsed since last flush."""
        with self._lock:
            elapsed = time.monotonic() - self._last_flush
            if elapsed >= self._max_wait_seconds and self._buffer:
                return self._do_flush()
        return None

    def get_stats(self) -> dict[str, Any]:
        """Return batching statistics."""
        with self._lock:
            return {
                "buffered_count": len(self._buffer),
                "max_size": self._max_size,
                "max_wait_seconds": self._max_wait_seconds,
                "total_batched": self._total_batched,
                "total_flushes": self._total_flushes,
            }

    def clear(self) -> None:
        """Clear the buffer without flushing."""
        with self._lock:
            self._buffer.clear()
            self._last_flush = time.monotonic()


class BatchProcessor:
    """Processes batches of messages with a handler function."""

    def __init__(
        self,
        handler: Callable[[list[Message]], list[tuple[Message, Optional[str]]]],
        error_handler: Optional[Callable[[Message, str], None]] = None,
    ) -> None:
        self._handler = handler
        self._error_handler = error_handler
        self._total_processed = 0
        self._total_failed = 0
        self._total_batches = 0

    def process_batch(self, messages: list[Message]) -> dict[str, Any]:
        """Process a batch of messages. Returns processing results."""
        results = self._handler(messages)
        processed = 0
        failed = 0

        for message, error in results:
            if error:
                failed += 1
                message.status = MessageStatus.FAILED
                message.error = error
                if self._error_handler:
                    self._error_handler(message, error)
            else:
                processed += 1
                message.status = MessageStatus.COMPLETED

        self._total_processed += processed
        self._total_failed += failed
        self._total_batches += 1

        return {
            "batch_size": len(messages),
            "processed": processed,
            "failed": failed,
        }

    def get_stats(self) -> dict[str, Any]:
        """Return batch processing statistics."""
        return {
            "total_processed": self._total_processed,
            "total_failed": self._total_failed,
            "total_batches": self._total_batches,
        }
