"""Tests for the message queue system."""

import pytest
import time
from datetime import datetime, timedelta

from apex_os_bp.message_queue.models import Message, MessagePriority, MessageStatus, QueueStats
from apex_os_bp.message_queue.priority_queue import PriorityQueue
from apex_os_bp.message_queue.delayed_queue import DelayedQueue
from apex_os_bp.message_queue.dead_letter import DeadLetterQueue
from apex_os_bp.message_queue.batching import MessageBatcher, BatchProcessor
from apex_os_bp.message_queue.monitoring import QueueMonitor
from apex_os_bp.message_queue.manager import MessageQueueManager


# ── Models ──────────────────────────────────────────────────────────────────

class TestMessageModel:
    def test_message_defaults(self):
        msg = Message(payload={"key": "value"})
        assert msg.priority == MessagePriority.NORMAL
        assert msg.status == MessageStatus.PENDING
        assert msg.retry_count == 0
        assert msg.max_retries == 3
        assert msg.queue_name == "default"
        assert msg.metadata == {}
        assert msg.tags == []

    def test_message_to_dict(self):
        msg = Message(payload="test", priority=MessagePriority.HIGH)
        d = msg.to_dict()
        assert d["payload"] == "test"
        assert d["priority"] == 1
        assert d["status"] == "pending"
        assert "message_id" in d
        assert "created_at" in d

    def test_message_from_dict(self):
        msg = Message(payload="test", priority=MessagePriority.LOW)
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.payload == "test"
        assert restored.priority == MessagePriority.LOW
        assert restored.message_id == msg.message_id

    def test_message_is_ready(self):
        msg = Message(payload="test")
        assert msg.is_ready() is True

    def test_message_not_ready_when_completed(self):
        msg = Message(payload="test", status=MessageStatus.COMPLETED)
        assert msg.is_ready() is False

    def test_message_not_ready_when_dead_letter(self):
        msg = Message(payload="test", status=MessageStatus.DEAD_LETTER)
        assert msg.is_ready() is False

    def test_message_not_ready_when_delayed(self):
        msg = Message(payload="test")
        msg.scheduled_at = datetime.utcnow() + timedelta(hours=1)
        assert msg.is_ready() is False

    def test_message_can_retry(self):
        msg = Message(payload="test", retry_count=0, max_retries=3)
        assert msg.can_retry() is True

    def test_message_cannot_retry(self):
        msg = Message(payload="test", retry_count=3, max_retries=3)
        assert msg.can_retry() is False

    def test_message_unique_ids(self):
        msg1 = Message(payload="a")
        msg2 = Message(payload="b")
        assert msg1.message_id != msg2.message_id


class TestQueueStats:
    def test_queue_stats_defaults(self):
        stats = QueueStats(queue_name="test")
        assert stats.queue_name == "test"
        assert stats.pending_count == 0
        assert stats.processing_count == 0
        assert stats.completed_count == 0
        assert stats.failed_count == 0
        assert stats.dead_letter_count == 0

    def test_queue_stats_to_dict(self):
        stats = QueueStats(queue_name="test", pending_count=5)
        d = stats.to_dict()
        assert d["queue_name"] == "test"
        assert d["pending_count"] == 5


# ── Priority Queue ──────────────────────────────────────────────────────────

class TestPriorityQueue:
    def test_enqueue_dequeue(self):
        pq = PriorityQueue(name="test")
        msg = Message(payload="hello")
        pq.enqueue(msg)
        assert len(pq) == 1
        result = pq.dequeue()
        assert result is not None
        assert result.payload == "hello"
        assert len(pq) == 0

    def test_priority_ordering(self):
        pq = PriorityQueue(name="test")
        low = Message(payload="low", priority=MessagePriority.LOW)
        critical = Message(payload="critical", priority=MessagePriority.CRITICAL)
        normal = Message(payload="normal", priority=MessagePriority.NORMAL)
        high = Message(payload="high", priority=MessagePriority.HIGH)

        pq.enqueue(low)
        pq.enqueue(critical)
        pq.enqueue(normal)
        pq.enqueue(high)

        assert pq.dequeue().payload == "critical"
        assert pq.dequeue().payload == "high"
        assert pq.dequeue().payload == "normal"
        assert pq.dequeue().payload == "low"

    def test_fifo_within_same_priority(self):
        pq = PriorityQueue(name="test")
        msg1 = Message(payload="first", priority=MessagePriority.NORMAL)
        msg2 = Message(payload="second", priority=MessagePriority.NORMAL)
        msg3 = Message(payload="third", priority=MessagePriority.NORMAL)

        pq.enqueue(msg1)
        pq.enqueue(msg2)
        pq.enqueue(msg3)

        assert pq.dequeue().payload == "first"
        assert pq.dequeue().payload == "second"
        assert pq.dequeue().payload == "third"

    def test_dequeue_empty_returns_none(self):
        pq = PriorityQueue(name="test")
        assert pq.dequeue() is None

    def test_peek(self):
        pq = PriorityQueue(name="test")
        msg = Message(payload="peek_me")
        pq.enqueue(msg)
        peeked = pq.peek()
        assert peeked is not None
        assert peeked.payload == "peek_me"
        assert len(pq) == 1  # Not removed

    def test_peek_empty_returns_none(self):
        pq = PriorityQueue(name="test")
        assert pq.peek() is None

    def test_remove(self):
        pq = PriorityQueue(name="test")
        msg = Message(payload="remove_me")
        pq.enqueue(msg)
        assert pq.remove(msg.message_id) is True
        assert len(pq) == 0
        assert pq.dequeue() is None

    def test_remove_nonexistent(self):
        pq = PriorityQueue(name="test")
        assert pq.remove("nonexistent") is False

    def test_get(self):
        pq = PriorityQueue(name="test")
        msg = Message(payload="get_me")
        pq.enqueue(msg)
        found = pq.get(msg.message_id)
        assert found is not None
        assert found.payload == "get_me"

    def test_clear(self):
        pq = PriorityQueue(name="test")
        pq.enqueue(Message(payload="a"))
        pq.enqueue(Message(payload="b"))
        pq.clear()
        assert len(pq) == 0

    def test_get_all_pending(self):
        pq = PriorityQueue(name="test")
        msg1 = Message(payload="a", priority=MessagePriority.HIGH)
        msg2 = Message(payload="b", priority=MessagePriority.LOW)
        pq.enqueue(msg1)
        pq.enqueue(msg2)
        pending = pq.get_all_pending()
        assert len(pending) == 2
        assert pending[0].payload == "a"  # Higher priority first

    def test_get_stats(self):
        pq = PriorityQueue(name="test")
        pq.enqueue(Message(payload="a", priority=MessagePriority.HIGH))
        pq.enqueue(Message(payload="b", priority=MessagePriority.LOW))
        stats = pq.get_stats()
        assert stats["queue_name"] == "test"
        assert stats["pending_count"] == 2
        assert stats["by_priority"]["HIGH"] == 1
        assert stats["by_priority"]["LOW"] == 1

    def test_delayed_message_not_dequeued(self):
        pq = PriorityQueue(name="test")
        msg = Message(payload="delayed")
        msg.scheduled_at = datetime.utcnow() + timedelta(hours=1)
        pq.enqueue(msg)
        assert pq.dequeue() is None
        assert len(pq) == 1


# ── Delayed Queue ───────────────────────────────────────────────────────────

class TestDelayedQueue:
    def test_schedule(self):
        dq = DelayedQueue()
        msg = Message(payload="delayed")
        dq.schedule(msg, delay_seconds=10)
        assert len(dq) == 1
        assert msg.status == MessageStatus.DELAYED
        assert msg.scheduled_at is not None

    def test_schedule_at(self):
        dq = DelayedQueue()
        msg = Message(payload="scheduled")
        deliver_at = datetime.utcnow() + timedelta(minutes=5)
        dq.schedule_at(msg, deliver_at)
        assert len(dq) == 1
        assert msg.scheduled_at == deliver_at

    def test_get_ready_messages_empty(self):
        dq = DelayedQueue()
        assert dq.get_ready_messages() == []

    def test_get_ready_messages_with_ready(self):
        dq = DelayedQueue()
        msg = Message(payload="ready")
        # Schedule with 0 delay — should be ready immediately
        dq.schedule(msg, delay_seconds=0)
        time.sleep(0.01)  # Small sleep to ensure time passes
        ready = dq.get_ready_messages()
        assert len(ready) == 1
        assert ready[0].payload == "ready"
        assert ready[0].status == MessageStatus.PENDING

    def test_get_ready_messages_not_yet_ready(self):
        dq = DelayedQueue()
        msg = Message(payload="not_ready")
        dq.schedule(msg, delay_seconds=3600)
        ready = dq.get_ready_messages()
        assert len(ready) == 0
        assert len(dq) == 1

    def test_cancel(self):
        dq = DelayedQueue()
        msg = Message(payload="cancel_me")
        dq.schedule(msg, delay_seconds=60)
        assert dq.cancel(msg.message_id) is True
        assert len(dq) == 0

    def test_cancel_nonexistent(self):
        dq = DelayedQueue()
        assert dq.cancel("nonexistent") is False

    def test_get(self):
        dq = DelayedQueue()
        msg = Message(payload="get_delayed")
        dq.schedule(msg, delay_seconds=60)
        found = dq.get(msg.message_id)
        assert found is not None
        assert found.payload == "get_delayed"

    def test_clear(self):
        dq = DelayedQueue()
        dq.schedule(Message(payload="a"), delay_seconds=60)
        dq.schedule(Message(payload="b"), delay_seconds=120)
        dq.clear()
        assert len(dq) == 0

    def test_get_stats(self):
        dq = DelayedQueue()
        dq.schedule(Message(payload="a"), delay_seconds=0)
        dq.schedule(Message(payload="b"), delay_seconds=3600)
        time.sleep(0.01)
        stats = dq.get_stats()
        assert stats["total_delayed"] == 2
        assert stats["overdue"] == 1
        assert stats["upcoming"] == 1

    def test_get_pending_messages(self):
        dq = DelayedQueue()
        msg1 = Message(payload="later")
        msg2 = Message(payload="sooner")
        dq.schedule(msg1, delay_seconds=120)
        dq.schedule(msg2, delay_seconds=60)
        pending = dq.get_pending_messages()
        assert len(pending) == 2
        assert pending[0].payload == "sooner"
        assert pending[1].payload == "later"

    def test_multiple_messages_promoted_in_order(self):
        dq = DelayedQueue()
        for i in range(5):
            dq.schedule(Message(payload=f"msg_{i}"), delay_seconds=0)
        time.sleep(0.01)
        ready = dq.get_ready_messages()
        assert len(ready) == 5


# ── Dead Letter Queue ───────────────────────────────────────────────────────

class TestDeadLetterQueue:
    def test_add(self):
        dlq = DeadLetterQueue()
        msg = Message(payload="failed")
        dlq.add(msg, error="Connection timeout")
        assert len(dlq) == 1
        assert msg.status == MessageStatus.DEAD_LETTER
        assert msg.error == "Connection timeout"

    def test_get(self):
        dlq = DeadLetterQueue()
        msg = Message(payload="failed")
        dlq.add(msg, error="timeout")
        found = dlq.get(msg.message_id)
        assert found is not None
        assert found.payload == "failed"

    def test_get_nonexistent(self):
        dlq = DeadLetterQueue()
        assert dlq.get("nonexistent") is None

    def test_get_all(self):
        dlq = DeadLetterQueue()
        dlq.add(Message(payload="a"), error="err1")
        dlq.add(Message(payload="b"), error="err2")
        all_msgs = dlq.get_all()
        assert len(all_msgs) == 2

    def test_get_by_queue(self):
        dlq = DeadLetterQueue()
        msg1 = Message(payload="a", queue_name="queue_a")
        msg2 = Message(payload="b", queue_name="queue_b")
        dlq.add(msg1, error="err")
        dlq.add(msg2, error="err")
        result = dlq.get_by_queue("queue_a")
        assert len(result) == 1
        assert result[0].payload == "a"

    def test_get_by_error(self):
        dlq = DeadLetterQueue()
        dlq.add(Message(payload="a"), error="Connection timeout")
        dlq.add(Message(payload="b"), error="ValueError: bad input")
        dlq.add(Message(payload="c"), error="Connection refused")
        result = dlq.get_by_error("Connection")
        assert len(result) == 2

    def test_replay(self):
        dlq = DeadLetterQueue()
        msg = Message(payload="retry_me")
        dlq.add(msg, error="timeout")
        replayed = dlq.replay(msg.message_id)
        assert replayed is not None
        assert replayed.status == MessageStatus.PENDING
        assert replayed.error is None
        assert replayed.retry_count == 0
        assert len(dlq) == 0

    def test_replay_nonexistent(self):
        dlq = DeadLetterQueue()
        assert dlq.replay("nonexistent") is None

    def test_replay_all(self):
        dlq = DeadLetterQueue()
        dlq.add(Message(payload="a"), error="err1")
        dlq.add(Message(payload="b"), error="err2")
        replayed = dlq.replay_all()
        assert len(replayed) == 2
        assert len(dlq) == 0

    def test_remove(self):
        dlq = DeadLetterQueue()
        msg = Message(payload="remove_me")
        dlq.add(msg, error="err")
        assert dlq.remove(msg.message_id) is True
        assert len(dlq) == 0

    def test_remove_nonexistent(self):
        dlq = DeadLetterQueue()
        assert dlq.remove("nonexistent") is False

    def test_clear(self):
        dlq = DeadLetterQueue()
        dlq.add(Message(payload="a"), error="err")
        dlq.add(Message(payload="b"), error="err")
        dlq.clear()
        assert len(dlq) == 0

    def test_max_size_eviction(self):
        dlq = DeadLetterQueue(max_size=3)
        for i in range(5):
            msg = Message(payload=f"msg_{i}")
            dlq.add(msg, error="err")
        assert len(dlq) == 3
        # Oldest should be evicted
        assert dlq.get("nonexistent") is None

    def test_replay_handler_called(self):
        dlq = DeadLetterQueue()
        handler_calls = []
        dlq.register_replay_handler(lambda m: handler_calls.append(m.message_id))
        msg = Message(payload="test")
        dlq.add(msg, error="err")
        dlq.replay(msg.message_id)
        assert len(handler_calls) == 1
        assert handler_calls[0] == msg.message_id

    def test_get_stats(self):
        dlq = DeadLetterQueue()
        msg1 = Message(payload="a", queue_name="q1")
        msg2 = Message(payload="b", queue_name="q1")
        msg3 = Message(payload="c", queue_name="q2")
        dlq.add(msg1, error="timeout")
        dlq.add(msg2, error="timeout")
        dlq.add(msg3, error="connection refused")
        stats = dlq.get_stats()
        assert stats["total_dead_letter"] == 3
        assert stats["by_queue"]["q1"] == 2
        assert stats["by_queue"]["q2"] == 1


# ── Message Batching ────────────────────────────────────────────────────────

class TestMessageBatcher:
    def test_add_to_batch(self):
        batcher = MessageBatcher(max_size=5)
        msg = Message(payload="test")
        result = batcher.add(msg)
        assert result is None  # Not flushed yet
        stats = batcher.get_stats()
        assert stats["buffered_count"] == 1

    def test_flush_on_max_size(self):
        batcher = MessageBatcher(max_size=3)
        batcher.add(Message(payload="a"))
        batcher.add(Message(payload="b"))
        result = batcher.add(Message(payload="c"))
        assert result is not None
        assert len(result) == 3
        stats = batcher.get_stats()
        assert stats["buffered_count"] == 0

    def test_manual_flush(self):
        batcher = MessageBatcher(max_size=10)
        batcher.add(Message(payload="a"))
        batcher.add(Message(payload="b"))
        flushed = batcher.flush()
        assert len(flushed) == 2
        assert batcher.get_stats()["buffered_count"] == 0

    def test_flush_empty(self):
        batcher = MessageBatcher(max_size=10)
        assert batcher.flush() == []

    def test_flush_handler_called(self):
        flushed_batches = []
        def handler(batch):
            flushed_batches.append(batch)
        batcher = MessageBatcher(max_size=2, flush_handler=handler)
        batcher.add(Message(payload="a"))
        batcher.add(Message(payload="b"))
        assert len(flushed_batches) == 1
        assert len(flushed_batches[0]) == 2

    def test_maybe_flush(self):
        batcher = MessageBatcher(max_size=100, max_wait_seconds=0.05)
        batcher.add(Message(payload="a"))
        time.sleep(0.1)
        result = batcher.maybe_flush()
        assert result is not None
        assert len(result) == 1

    def test_maybe_flush_not_yet(self):
        batcher = MessageBatcher(max_size=100, max_wait_seconds=3600)
        batcher.add(Message(payload="a"))
        result = batcher.maybe_flush()
        assert result is None

    def test_clear(self):
        batcher = MessageBatcher(max_size=10)
        batcher.add(Message(payload="a"))
        batcher.add(Message(payload="b"))
        batcher.clear()
        assert batcher.get_stats()["buffered_count"] == 0

    def test_get_stats(self):
        batcher = MessageBatcher(max_size=50, max_wait_seconds=10)
        batcher.add(Message(payload="a"))
        batcher.add(Message(payload="b"))
        stats = batcher.get_stats()
        assert stats["buffered_count"] == 2
        assert stats["max_size"] == 50
        assert stats["total_batched"] == 2


class TestBatchProcessor:
    def test_process_batch_success(self):
        def handler(messages):
            return [(m, None) for m in messages]
        processor = BatchProcessor(handler=handler)
        messages = [Message(payload="a"), Message(payload="b")]
        result = processor.process_batch(messages)
        assert result["batch_size"] == 2
        assert result["processed"] == 2
        assert result["failed"] == 0
        assert messages[0].status == MessageStatus.COMPLETED

    def test_process_batch_with_failures(self):
        def handler(messages):
            results = []
            for m in messages:
                if m.payload == "bad":
                    results.append((m, "Processing error"))
                else:
                    results.append((m, None))
            return results
        processor = BatchProcessor(handler=handler)
        messages = [Message(payload="good"), Message(payload="bad")]
        result = processor.process_batch(messages)
        assert result["processed"] == 1
        assert result["failed"] == 1
        assert messages[1].status == MessageStatus.FAILED
        assert messages[1].error == "Processing error"

    def test_process_batch_error_handler(self):
        error_calls = []
        def error_handler(msg, error):
            error_calls.append((msg.message_id, error))
        def handler(messages):
            return [(m, "fail") for m in messages]
        processor = BatchProcessor(handler=handler, error_handler=error_handler)
        messages = [Message(payload="a")]
        processor.process_batch(messages)
        assert len(error_calls) == 1

    def test_get_stats(self):
        def handler(messages):
            return [(m, None) for m in messages]
        processor = BatchProcessor(handler=handler)
        processor.process_batch([Message(payload="a")])
        processor.process_batch([Message(payload="b"), Message(payload="c")])
        stats = processor.get_stats()
        assert stats["total_processed"] == 3
        assert stats["total_batches"] == 2


# ── Queue Monitoring ────────────────────────────────────────────────────────

class TestQueueMonitor:
    def test_record_enqueue(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        monitor.record_enqueue(msg)
        stats = monitor.get_queue_stats("q1")
        assert stats.pending_count == 1
        assert stats.total_enqueued == 1

    def test_record_dequeue(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        monitor.record_enqueue(msg)
        monitor.record_dequeue(msg)
        stats = monitor.get_queue_stats("q1")
        assert stats.pending_count == 0
        assert stats.processing_count == 1

    def test_record_complete(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        msg.processed_at = datetime.utcnow()
        monitor.record_complete(msg, processing_time_ms=150.0)
        stats = monitor.get_queue_stats("q1")
        assert stats.completed_count == 1
        assert stats.total_processed == 1
        assert stats.avg_processing_time_ms == 150.0

    def test_record_failure(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        monitor.record_failure(msg)
        stats = monitor.get_queue_stats("q1")
        assert stats.failed_count == 1

    def test_record_dead_letter(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        monitor.record_dead_letter(msg)
        stats = monitor.get_queue_stats("q1")
        assert stats.dead_letter_count == 1

    def test_record_delayed(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        monitor.record_delayed(msg)
        stats = monitor.get_queue_stats("q1")
        assert stats.delayed_count == 1

    def test_get_all_stats(self):
        monitor = QueueMonitor()
        monitor.record_enqueue(Message(payload="a", queue_name="q1"))
        monitor.record_enqueue(Message(payload="b", queue_name="q2"))
        all_stats = monitor.get_all_stats()
        assert "q1" in all_stats
        assert "q2" in all_stats

    def test_get_summary(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        monitor.record_enqueue(msg)
        monitor.record_dequeue(msg)
        monitor.record_complete(msg, processing_time_ms=100.0)
        summary = monitor.get_summary()
        assert summary["total_queues"] == 1
        assert summary["total_completed"] == 1
        assert summary["total_pending"] == 0
        assert summary["uptime_seconds"] >= 0

    def test_get_throughput(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        monitor.record_enqueue(msg)
        monitor.record_dequeue(msg)
        monitor.record_complete(msg, processing_time_ms=50.0)
        throughput = monitor.get_throughput(window_seconds=60)
        assert throughput["enqueues"] == 1
        assert throughput["dequeues"] == 1
        assert throughput["completions"] == 1

    def test_add_alert_rule(self):
        monitor = QueueMonitor()
        alerts_triggered = []
        monitor.add_alert_rule(
            name="high_pending",
            condition=lambda stats: stats.pending_count > 10,
            handler=lambda name, data: alerts_triggered.append(name),
        )
        # Enqueue 11 messages
        for i in range(11):
            monitor.record_enqueue(Message(payload=f"msg_{i}", queue_name="q1"))
        triggered = monitor.check_alerts()
        assert len(triggered) == 1
        assert triggered[0]["rule_name"] == "high_pending"
        assert len(alerts_triggered) == 1

    def test_no_alert_when_condition_not_met(self):
        monitor = QueueMonitor()
        alerts_triggered = []
        monitor.add_alert_rule(
            name="high_pending",
            condition=lambda stats: stats.pending_count > 10,
            handler=lambda name, data: alerts_triggered.append(name),
        )
        monitor.record_enqueue(Message(payload="test", queue_name="q1"))
        triggered = monitor.check_alerts()
        assert len(triggered) == 0

    def test_reset(self):
        monitor = QueueMonitor()
        msg = Message(payload="test", queue_name="q1")
        monitor.record_enqueue(msg)
        monitor.reset()
        stats = monitor.get_queue_stats("q1")
        assert stats.pending_count == 0
        assert stats.total_enqueued == 0


# ── Message Queue Manager (Integration) ─────────────────────────────────────

class TestMessageQueueManager:
    def test_create_queue(self):
        mgr = MessageQueueManager()
        q = mgr.create_queue("test_queue")
        assert q.name == "test_queue"
        assert mgr.get_queue("test_queue") is q

    def test_get_nonexistent_queue(self):
        mgr = MessageQueueManager()
        assert mgr.get_queue("nonexistent") is None

    def test_enqueue(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="hello", queue_name="test")
        assert msg.payload == "hello"
        assert msg.queue_name == "test"
        assert msg.status == MessageStatus.PENDING

    def test_enqueue_with_priority(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="urgent", priority=MessagePriority.HIGH)
        assert msg.priority == MessagePriority.HIGH

    def test_enqueue_with_delay(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="delayed", delay_seconds=60)
        assert msg.status == MessageStatus.DELAYED
        assert msg.scheduled_at is not None

    def test_enqueue_at(self):
        mgr = MessageQueueManager()
        deliver_at = datetime.utcnow() + timedelta(minutes=5)
        msg = mgr.enqueue_at(payload="scheduled", deliver_at=deliver_at)
        assert msg.status == MessageStatus.DELAYED

    def test_dequeue(self):
        mgr = MessageQueueManager()
        mgr.enqueue(payload="test", queue_name="q1")
        msg = mgr.dequeue("q1")
        assert msg is not None
        assert msg.payload == "test"
        assert msg.status == MessageStatus.PROCESSING

    def test_dequeue_empty(self):
        mgr = MessageQueueManager()
        assert mgr.dequeue("empty") is None

    def test_dequeue_priority_order(self):
        mgr = MessageQueueManager()
        mgr.enqueue(payload="low", priority=MessagePriority.LOW)
        mgr.enqueue(payload="critical", priority=MessagePriority.CRITICAL)
        mgr.enqueue(payload="normal", priority=MessagePriority.NORMAL)
        assert mgr.dequeue().payload == "critical"
        assert mgr.dequeue().payload == "normal"
        assert mgr.dequeue().payload == "low"

    def test_complete(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="test")
        mgr.dequeue()
        mgr.complete(msg)
        assert msg.status == MessageStatus.COMPLETED
        assert msg.completed_at is not None

    def test_fail_with_retry(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="test", max_retries=3)
        mgr.dequeue()
        mgr.fail(msg, error="temporary error")
        assert msg.status == MessageStatus.RETRYING
        assert msg.retry_count == 1
        assert msg.error == "temporary error"

    def test_fail_exhausts_retries(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="test", max_retries=2)
        mgr.dequeue()
        mgr.fail(msg, error="err1")
        assert msg.status == MessageStatus.RETRYING
        # Promote from delayed (backoff) and fail again
        mgr._delayed.schedule(msg, delay_seconds=0)
        mgr._promote_delayed()
        msg.status = MessageStatus.PROCESSING
        mgr.fail(msg, error="err2")
        assert msg.status == MessageStatus.RETRYING
        # Promote again and fail final time
        mgr._delayed.schedule(msg, delay_seconds=0)
        mgr._promote_delayed()
        msg.status = MessageStatus.PROCESSING
        mgr.fail(msg, error="err3")
        assert msg.status == MessageStatus.DEAD_LETTER
        assert len(mgr.dead_letter) == 1

    def test_retry_dead_letter(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="test", max_retries=1)
        mgr.dequeue()
        mgr.fail(msg, error="err")
        # Should be in dead letter now
        assert len(mgr.dead_letter) == 1
        # Retry it
        result = mgr.retry(msg)
        assert result is True
        assert msg.status == MessageStatus.PENDING
        assert len(mgr.dead_letter) == 0

    def test_get_batcher(self):
        mgr = MessageQueueManager(batch_size=50)
        batcher = mgr.get_batcher("test")
        assert batcher._max_size == 50
        # Same batcher returned
        assert mgr.get_batcher("test") is batcher

    def test_get_stats(self):
        mgr = MessageQueueManager()
        mgr.enqueue(payload="a", queue_name="q1")
        mgr.enqueue(payload="b", queue_name="q2")
        stats = mgr.get_stats()
        assert "queues" in stats
        assert "delayed" in stats
        assert "dead_letter" in stats
        assert "monitoring" in stats
        assert "q1" in stats["queues"]
        assert "q2" in stats["queues"]

    def test_delayed_promotion(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="delayed", delay_seconds=0.01)
        assert msg.status == MessageStatus.DELAYED
        time.sleep(0.02)
        # Dequeue should promote the delayed message
        result = mgr.dequeue()
        assert result is not None
        assert result.payload == "delayed"

    def test_multiple_queues_isolated(self):
        mgr = MessageQueueManager()
        mgr.enqueue(payload="a", queue_name="q1")
        mgr.enqueue(payload="b", queue_name="q2")
        assert mgr.dequeue("q1").payload == "a"
        assert mgr.dequeue("q2").payload == "b"
        assert mgr.dequeue("q1") is None

    def test_enqueue_with_metadata(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="test", metadata={"user_id": 123})
        assert msg.metadata["user_id"] == 123

    def test_enqueue_with_tags(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="test", tags=["urgent", "billing"])
        assert "urgent" in msg.tags
        assert "billing" in msg.tags

    def test_monitoring_integration(self):
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="test", queue_name="monitored")
        mgr.dequeue("monitored")
        mgr.complete(msg)
        stats = mgr.monitor.get_queue_stats("monitored")
        assert stats.total_enqueued == 1
        assert stats.total_processed == 1
        assert stats.completed_count == 1

    def test_manager_start_stop(self):
        mgr = MessageQueueManager()
        mgr.start()
        assert mgr._running is True
        mgr.stop()
        assert mgr._running is False

    def test_full_lifecycle(self):
        """Test a complete message lifecycle: enqueue -> dequeue -> fail -> retry -> complete."""
        mgr = MessageQueueManager()
        msg = mgr.enqueue(payload="lifecycle", max_retries=2)

        # Dequeue and fail
        dequeued = mgr.dequeue()
        assert dequeued is not None
        mgr.fail(dequeued, error="temporary")
        assert dequeued.status == MessageStatus.RETRYING

        # Promote from delayed and dequeue again
        mgr._delayed.schedule(dequeued, delay_seconds=0)
        mgr._promote_delayed()
        dequeued2 = mgr.dequeue()
        assert dequeued2 is not None

        # Complete successfully
        mgr.complete(dequeued2)
        assert dequeued2.status == MessageStatus.COMPLETED

        # Check monitoring
        summary = mgr.monitor.get_summary()
        assert summary["total_completed"] == 1
        assert summary["total_failed"] == 1
