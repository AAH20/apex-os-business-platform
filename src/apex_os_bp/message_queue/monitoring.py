"""Queue monitoring and metrics collection."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Optional

from .models import Message, MessageStatus, QueueStats


class QueueMonitor:
    """Monitors queue health, throughput, and message flow.

    Tracks metrics over time and provides alerting hooks.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queue_stats: dict[str, QueueStats] = {}
        self._processing_times: dict[str, list[float]] = defaultdict(list)
        self._throughput_window: list[tuple[float, str, str]] = []  # (timestamp, queue, action)
        self._alert_handlers: list[Callable[[str, dict[str, Any]], None]] = []
        self._alert_rules: list[dict[str, Any]] = []
        self._start_time = time.monotonic()

    def record_enqueue(self, message: Message) -> None:
        """Record a message enqueue event."""
        with self._lock:
            stats = self._get_or_create_stats(message.queue_name)
            stats.total_enqueued += 1
            stats.pending_count += 1
            self._record_throughput(message.queue_name, "enqueue")

    def record_dequeue(self, message: Message) -> None:
        """Record a message dequeue event."""
        with self._lock:
            stats = self._get_or_create_stats(message.queue_name)
            stats.pending_count = max(0, stats.pending_count - 1)
            stats.processing_count += 1
            self._record_throughput(message.queue_name, "dequeue")

    def record_complete(self, message: Message, processing_time_ms: float) -> None:
        """Record a message completion event."""
        with self._lock:
            stats = self._get_or_create_stats(message.queue_name)
            stats.processing_count = max(0, stats.processing_count - 1)
            stats.completed_count += 1
            stats.total_processed += 1
            self._processing_times[message.queue_name].append(processing_time_ms)
            # Keep only last 1000 measurements
            if len(self._processing_times[message.queue_name]) > 1000:
                self._processing_times[message.queue_name] = self._processing_times[message.queue_name][-1000:]
            self._update_avg_processing_time(message.queue_name)
            self._record_throughput(message.queue_name, "complete")

    def record_failure(self, message: Message) -> None:
        """Record a message failure event."""
        with self._lock:
            stats = self._get_or_create_stats(message.queue_name)
            stats.processing_count = max(0, stats.processing_count - 1)
            stats.failed_count += 1
            self._record_throughput(message.queue_name, "failure")

    def record_dead_letter(self, message: Message) -> None:
        """Record a message moving to dead letter queue."""
        with self._lock:
            stats = self._get_or_create_stats(message.queue_name)
            stats.dead_letter_count += 1
            self._record_throughput(message.queue_name, "dead_letter")

    def record_delayed(self, message: Message) -> None:
        """Record a message being delayed."""
        with self._lock:
            stats = self._get_or_create_stats(message.queue_name)
            stats.delayed_count += 1

    def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get statistics for a specific queue."""
        with self._lock:
            return self._get_or_create_stats(queue_name)

    def get_all_stats(self) -> dict[str, QueueStats]:
        """Get statistics for all queues."""
        with self._lock:
            return dict(self._queue_stats)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all queue activity."""
        with self._lock:
            total_pending = sum(s.pending_count for s in self._queue_stats.values())
            total_processing = sum(s.processing_count for s in self._queue_stats.values())
            total_completed = sum(s.completed_count for s in self._queue_stats.values())
            total_failed = sum(s.failed_count for s in self._queue_stats.values())
            total_dead_letter = sum(s.dead_letter_count for s in self._queue_stats.values())
            total_delayed = sum(s.delayed_count for s in self._queue_stats.values())

            uptime = time.monotonic() - self._start_time
            throughput = self._calculate_throughput()

            return {
                "total_queues": len(self._queue_stats),
                "total_pending": total_pending,
                "total_processing": total_processing,
                "total_completed": total_completed,
                "total_failed": total_failed,
                "total_dead_letter": total_dead_letter,
                "total_delayed": total_delayed,
                "uptime_seconds": uptime,
                "throughput_per_second": throughput,
            }

    def get_throughput(self, window_seconds: int = 60) -> dict[str, Any]:
        """Get throughput metrics over a time window."""
        with self._lock:
            cutoff = time.monotonic() - window_seconds
            recent = [(t, q, a) for t, q, a in self._throughput_window if t >= cutoff]

            enqueues = sum(1 for _, _, a in recent if a == "enqueue")
            dequeues = sum(1 for _, _, a in recent if a == "dequeue")
            completions = sum(1 for _, _, a in recent if a == "complete")
            failures = sum(1 for _, _, a in recent if a == "failure")

            return {
                "window_seconds": window_seconds,
                "enqueues": enqueues,
                "dequeues": dequeues,
                "completions": completions,
                "failures": failures,
                "enqueue_rate": enqueues / window_seconds,
                "completion_rate": completions / window_seconds,
            }

    def add_alert_rule(
        self,
        name: str,
        condition: Callable[[QueueStats], bool],
        handler: Callable[[str, dict[str, Any]], None],
    ) -> None:
        """Add an alert rule with a condition callback and handler."""
        self._alert_rules.append({
            "name": name,
            "condition": condition,
            "handler": handler,
        })

    def check_alerts(self) -> list[dict[str, Any]]:
        """Check all alert rules and trigger handlers for violations."""
        triggered = []
        with self._lock:
            for queue_name, stats in self._queue_stats.items():
                for rule in self._alert_rules:
                    try:
                        if rule["condition"](stats):
                            alert = {
                                "rule_name": rule["name"],
                                "queue_name": queue_name,
                                "stats": stats.to_dict(),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                            triggered.append(alert)
                            rule["handler"](rule["name"], alert)
                    except Exception:
                        pass  # Don't let alert errors crash the monitor
        return triggered

    def reset(self) -> None:
        """Reset all monitoring data."""
        with self._lock:
            self._queue_stats.clear()
            self._processing_times.clear()
            self._throughput_window.clear()
            self._start_time = time.monotonic()

    def _get_or_create_stats(self, queue_name: str) -> QueueStats:
        if queue_name not in self._queue_stats:
            self._queue_stats[queue_name] = QueueStats(queue_name=queue_name)
        return self._queue_stats[queue_name]

    def _record_throughput(self, queue_name: str, action: str) -> None:
        self._throughput_window.append((time.monotonic(), queue_name, action))
        # Keep only last 10000 events
        if len(self._throughput_window) > 10000:
            self._throughput_window = self._throughput_window[-10000:]

    def _update_avg_processing_time(self, queue_name: str) -> None:
        times = self._processing_times.get(queue_name, [])
        if times:
            self._queue_stats[queue_name].avg_processing_time_ms = sum(times) / len(times)

    def _calculate_throughput(self) -> float:
        cutoff = time.monotonic() - 60
        recent = [t for t, _, _ in self._throughput_window if t >= cutoff]
        if not recent:
            return 0.0
        return len(recent) / 60.0
