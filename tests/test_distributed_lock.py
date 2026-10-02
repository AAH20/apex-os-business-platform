"""Comprehensive tests for the distributed locking system."""

from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import pytest

from apex_os_bp.distributed_lock import (
    BaseDistributedLock,
    DatabaseDistributedLock,
    DeadlockDetector,
    LockHealth,
    LockMonitor,
    LockMetrics,
    LockRenewalManager,
    LockResult,
    LockStatus,
    RedisDistributedLock,
    WaitForGraph,
    WaitForEdge,
    LockOperation,
    DeadlockCycle,
    RenewalConfig,
    RenewalStats,
    HealthCheckResult,
)


# ---------------------------------------------------------------------------
# Base Lock Tests
# ---------------------------------------------------------------------------


class TestLockResult(unittest.TestCase):
    """Tests for LockResult."""

    def test_success_property(self):
        result = LockResult(status=LockStatus.ACQUIRED)
        assert result.success is True
        assert bool(result) is True

    def test_failure_property(self):
        result = LockResult(status=LockStatus.NOT_ACQUIRED)
        assert result.success is False
        assert bool(result) is False

    def test_error_field(self):
        result = LockResult(status=LockStatus.ERROR, error="connection lost")
        assert result.error == "connection lost"


class TestLockMetadata(unittest.TestCase):
    """Tests for LockMetadata."""

    def test_age_seconds(self):
        from apex_os_bp.distributed_lock.base import LockMetadata

        meta = LockMetadata(lock_name="test", created_at=time.monotonic() - 5.0)
        assert meta.age_seconds >= 5.0

    def test_ttl_remaining(self):
        from apex_os_bp.distributed_lock.base import LockMetadata

        meta = LockMetadata(
            lock_name="test",
            expires_at=time.monotonic() + 10.0,
        )
        assert meta.ttl_remaining is not None
        assert 9.0 <= meta.ttl_remaining <= 10.0

    def test_is_expired(self):
        from apex_os_bp.distributed_lock.base import LockMetadata

        meta = LockMetadata(
            lock_name="test",
            expires_at=time.monotonic() - 1.0,
        )
        assert meta.is_expired is True

    def test_not_expired(self):
        from apex_os_bp.distributed_lock.base import LockMetadata

        meta = LockMetadata(
            lock_name="test",
            expires_at=time.monotonic() + 10.0,
        )
        assert meta.is_expired is False

    def test_no_expiry(self):
        from apex_os_bp.distributed_lock.base import LockMetadata

        meta = LockMetadata(lock_name="test")
        assert meta.is_expired is False
        assert meta.ttl_remaining is None


# ---------------------------------------------------------------------------
# Redis Lock Tests
# ---------------------------------------------------------------------------


class TestRedisDistributedLock(unittest.TestCase):
    """Tests for RedisDistributedLock."""

    def _make_mock_redis(self):
        mock_redis = MagicMock()
        mock_redis.set.return_value = True
        mock_redis.get.return_value = "test-token"
        mock_redis.pttl.return_value = 30000
        mock_redis.register_script.return_value = MagicMock()
        return mock_redis

    def test_acquire_success(self):
        mock_redis = self._make_mock_redis()
        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        result = lock.acquire(blocking=False)
        assert result.success is True
        assert result.status == LockStatus.ACQUIRED
        assert result.metadata is not None
        assert result.metadata.lock_name == "test_lock"

    def test_acquire_failure_not_blocking(self):
        mock_redis = MagicMock()
        mock_redis.set.return_value = None  # Key already exists
        mock_redis.register_script.return_value = MagicMock()

        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        result = lock.acquire(blocking=False)
        assert result.success is False
        assert result.status == LockStatus.NOT_ACQUIRED

    def test_acquire_timeout(self):
        mock_redis = MagicMock()
        mock_redis.set.return_value = None
        mock_redis.register_script.return_value = MagicMock()

        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        start = time.monotonic()
        result = lock.acquire(blocking=True, timeout=0.2)
        elapsed = time.monotonic() - start
        assert result.success is False
        assert elapsed >= 0.15  # Should have waited

    def test_release_success(self):
        mock_redis = self._make_mock_redis()
        release_script = MagicMock()
        release_script.return_value = 1
        mock_redis.register_script.return_value = release_script

        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        lock.acquire(blocking=False)
        result = lock.release()
        assert result.status == LockStatus.RELEASED

    def test_release_not_held(self):
        mock_redis = self._make_mock_redis()
        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        result = lock.release()
        assert result.status == LockStatus.NOT_ACQUIRED

    def test_renew_success(self):
        mock_redis = self._make_mock_redis()
        renew_script = MagicMock()
        renew_script.return_value = 1
        mock_redis.register_script.return_value = renew_script

        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        lock.acquire(blocking=False)
        result = lock.renew()
        assert result.status == LockStatus.RENEWED
        assert result.metadata.renewal_count == 1

    def test_renew_expired(self):
        mock_redis = self._make_mock_redis()
        renew_script = MagicMock()
        renew_script.return_value = 0  # Token mismatch
        mock_redis.register_script.return_value = renew_script

        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        lock.acquire(blocking=False)
        result = lock.renew()
        assert result.status == LockStatus.EXPIRED

    def test_is_locked_true(self):
        mock_redis = self._make_mock_redis()
        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        lock.acquire(blocking=False)
        mock_redis.get.return_value = lock.metadata.token
        assert lock.is_locked() is True

    def test_is_locked_false(self):
        mock_redis = self._make_mock_redis()
        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        assert lock.is_locked() is False

    def test_context_manager(self):
        mock_redis = self._make_mock_redis()
        release_script = MagicMock()
        release_script.return_value = 1
        mock_redis.register_script.return_value = release_script

        with RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        ) as lock:
            assert lock.metadata is not None
            mock_redis.get.return_value = lock.metadata.token
            assert lock.is_locked() is True

    def test_context_manager_failure(self):
        mock_redis = MagicMock()
        mock_redis.set.side_effect = Exception("Connection refused")
        mock_redis.register_script.return_value = MagicMock()

        with pytest.raises(RuntimeError):
            with RedisDistributedLock(
                "test_lock",
                ttl_seconds=10,
                redis_client=mock_redis,
            ) as lock:
                # Should not reach here
                pass

    def test_redis_key_prefix(self):
        mock_redis = self._make_mock_redis()
        lock = RedisDistributedLock(
            "my_lock",
            redis_client=mock_redis,
            prefix="custom:",
        )
        assert lock.redis_key == "custom:my_lock"

    def test_get_lock_info(self):
        mock_redis = self._make_mock_redis()
        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        lock.acquire(blocking=False)
        mock_redis.get.return_value = lock.metadata.token
        info = lock.get_lock_info()
        assert info is not None
        assert info["lock_name"] == "test_lock"
        assert info["ttl_ms"] == 30000

    def test_get_lock_info_none(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        info = lock.get_lock_info()
        assert info is None

    def test_acquire_error(self):
        mock_redis = MagicMock()
        mock_redis.set.side_effect = Exception("Connection refused")
        mock_redis.register_script.return_value = MagicMock()

        lock = RedisDistributedLock(
            "test_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )
        result = lock.acquire(blocking=False)
        assert result.status == LockStatus.ERROR
        assert "Connection refused" in result.error


# ---------------------------------------------------------------------------
# Database Lock Tests
# ---------------------------------------------------------------------------


class TestDatabaseDistributedLock(unittest.TestCase):
    """Tests for DatabaseDistributedLock."""

    def _make_mock_connection(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_derive_lock_key_deterministic(self):
        key1 = DatabaseDistributedLock._derive_lock_key("my_lock", 0)
        key2 = DatabaseDistributedLock._derive_lock_key("my_lock", 0)
        assert key1 == key2

    def test_derive_lock_key_different_names(self):
        key1 = DatabaseDistributedLock._derive_lock_key("lock_a", 0)
        key2 = DatabaseDistributedLock._derive_lock_key("lock_b", 0)
        assert key1 != key2

    def test_derive_lock_key_different_namespaces(self):
        key1 = DatabaseDistributedLock._derive_lock_key("my_lock", 0)
        key2 = DatabaseDistributedLock._derive_lock_key("my_lock", 1)
        assert key1 != key2

    def test_acquire_session_level_success(self):
        mock_conn, mock_cursor = self._make_mock_connection()
        mock_cursor.fetchone.return_value = (True,)

        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=mock_conn,
        )
        result = lock.acquire(blocking=False)
        assert result.success is True
        assert result.status == LockStatus.ACQUIRED

    def test_acquire_session_level_failure(self):
        mock_conn, mock_cursor = self._make_mock_connection()
        mock_cursor.fetchone.return_value = (False,)

        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=mock_conn,
        )
        result = lock.acquire(blocking=False)
        assert result.success is False
        assert result.status == LockStatus.NOT_ACQUIRED

    def test_acquire_transaction_level_success(self):
        mock_conn, mock_cursor = self._make_mock_connection()
        mock_cursor.fetchone.return_value = (True,)

        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=mock_conn,
            transaction_level=True,
        )
        result = lock.acquire(blocking=False)
        assert result.success is True

    def test_acquire_no_connection(self):
        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=None,
        )
        result = lock.acquire(blocking=False)
        assert result.status == LockStatus.ERROR

    def test_release_session_level(self):
        mock_conn, mock_cursor = self._make_mock_connection()
        mock_cursor.fetchone.side_effect = [(True,), (True,)]

        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=mock_conn,
        )
        lock.acquire(blocking=False)
        result = lock.release()
        assert result.status == LockStatus.RELEASED

    def test_release_not_held(self):
        mock_conn, _ = self._make_mock_connection()
        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=mock_conn,
        )
        result = lock.release()
        assert result.status == LockStatus.NOT_ACQUIRED

    def test_renew_updates_metadata(self):
        mock_conn, mock_cursor = self._make_mock_connection()
        mock_cursor.fetchone.return_value = (True,)

        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=mock_conn,
        )
        lock.acquire(blocking=False)
        result = lock.renew()
        assert result.status == LockStatus.RENEWED
        assert result.metadata.renewal_count == 1

    def test_is_locked_false_no_connection(self):
        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=None,
        )
        assert lock.is_locked() is False

    def test_is_locked_checks_pg_locks(self):
        mock_conn, mock_cursor = self._make_mock_connection()
        mock_cursor.fetchone.side_effect = [(True,), (1,)]

        lock = DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=mock_conn,
        )
        lock.acquire(blocking=False)
        assert lock.is_locked() is True

    def test_context_manager(self):
        mock_conn, mock_cursor = self._make_mock_connection()
        mock_cursor.fetchone.side_effect = [(True,), (True,)]

        with DatabaseDistributedLock(
            "test_lock",
            ttl_seconds=10,
            db_connection=mock_conn,
        ) as lock:
            assert lock.metadata is not None


# ---------------------------------------------------------------------------
# Lock Renewal Tests
# ---------------------------------------------------------------------------


class TestLockRenewalManager(unittest.TestCase):
    """Tests for LockRenewalManager."""

    def _make_mock_lock(self, name="test_lock"):
        mock_lock = MagicMock()
        mock_lock.lock_name = name
        mock_lock.ttl_seconds = 30.0
        mock_lock.renew.return_value = LockResult(status=LockStatus.RENEWED)
        return mock_lock

    def test_register_and_unregister(self):
        manager = LockRenewalManager()
        mock_lock = self._make_mock_lock()

        manager.register(mock_lock)
        assert manager.is_registered(mock_lock) is True

        manager.unregister(mock_lock)
        assert manager.is_registered(mock_lock) is False

    def test_register_already_registered(self):
        manager = LockRenewalManager()
        mock_lock = self._make_mock_lock()

        manager.register(mock_lock)
        manager.register(mock_lock)  # Should not create duplicate
        assert manager.is_registered(mock_lock) is True

        manager.shutdown()

    def test_get_stats(self):
        manager = LockRenewalManager()
        mock_lock = self._make_mock_lock()

        manager.register(mock_lock)
        stats = manager.get_stats(mock_lock)
        assert stats is not None
        assert stats.lock_name == "test_lock"

        manager.shutdown()

    def test_get_all_stats(self):
        manager = LockRenewalManager()
        mock_lock = self._make_mock_lock()

        manager.register(mock_lock)
        all_stats = manager.get_all_stats()
        assert "test_lock" in all_stats

        manager.shutdown()

    def test_shutdown(self):
        manager = LockRenewalManager()
        mock_lock = self._make_mock_lock()

        manager.register(mock_lock)
        manager.shutdown()
        assert manager.is_registered(mock_lock) is False

    def test_context_manager(self):
        with LockRenewalManager() as manager:
            mock_lock = self._make_mock_lock()
            manager.register(mock_lock)
            assert manager.is_registered(mock_lock) is True

    def test_renewal_loop_success(self):
        config = RenewalConfig(renewal_interval=0.05)
        manager = LockRenewalManager(config=config)
        mock_lock = self._make_mock_lock()

        manager.register(mock_lock)
        time.sleep(0.15)  # Allow at least one renewal
        manager.unregister(mock_lock)

        stats = manager.get_stats(mock_lock)
        assert stats is not None
        assert stats.renewals_attempted >= 1

    def test_renewal_loop_failure_callback(self):
        failures = []

        def on_failure(name, error):
            failures.append((name, str(error)))

        config = RenewalConfig(
            renewal_interval=0.05,
            stop_on_failure=True,
            on_failure=on_failure,
        )
        manager = LockRenewalManager(config=config)
        mock_lock = self._make_mock_lock()
        mock_lock.renew.return_value = LockResult(
            status=LockStatus.EXPIRED,
            error="Token mismatch",
        )

        manager.register(mock_lock)
        time.sleep(0.15)
        manager.shutdown()

        assert len(failures) >= 1
        assert failures[0][0] == "test_lock"

    def test_renewal_loop_success_callback(self):
        renewals = []

        def on_renewal(name, result):
            renewals.append(name)

        config = RenewalConfig(
            renewal_interval=0.05,
            on_renewal=on_renewal,
        )
        manager = LockRenewalManager(config=config)
        mock_lock = self._make_mock_lock()

        manager.register(mock_lock)
        time.sleep(0.15)
        manager.shutdown()

        assert len(renewals) >= 1

    def test_unregister_by_name(self):
        manager = LockRenewalManager()
        mock_lock = self._make_mock_lock("my_lock")

        manager.register(mock_lock)
        manager.unregister("my_lock")
        assert manager.is_registered("my_lock") is False

    def test_is_registered_by_name(self):
        manager = LockRenewalManager()
        mock_lock = self._make_mock_lock("my_lock")

        manager.register(mock_lock)
        assert manager.is_registered("my_lock") is True
        manager.shutdown()


# ---------------------------------------------------------------------------
# Deadlock Detection Tests
# ---------------------------------------------------------------------------


class TestWaitForGraph(unittest.TestCase):
    """Tests for WaitForGraph."""

    def test_add_edge(self):
        graph = WaitForGraph()
        edge = WaitForEdge(waiter="A", holder="B", lock_name="lock1")
        graph.add_edge(edge)
        assert graph.edge_count == 1

    def test_remove_edge(self):
        graph = WaitForGraph()
        edge = WaitForEdge(waiter="A", holder="B", lock_name="lock1")
        graph.add_edge(edge)
        assert graph.remove_edge("A", "B") is True
        assert graph.edge_count == 0

    def test_remove_nonexistent_edge(self):
        graph = WaitForGraph()
        assert graph.remove_edge("A", "B") is False

    def test_remove_all_edges_for(self):
        graph = WaitForGraph()
        graph.add_edge(WaitForEdge(waiter="A", holder="B", lock_name="lock1"))
        graph.add_edge(WaitForEdge(waiter="A", holder="C", lock_name="lock2"))
        graph.add_edge(WaitForEdge(waiter="B", holder="C", lock_name="lock3"))

        count = graph.remove_all_edges_for("A")
        assert count == 2
        assert graph.edge_count == 1

    def test_detect_cycle_simple(self):
        graph = WaitForGraph()
        graph.add_edge(WaitForEdge(waiter="A", holder="B", lock_name="lock1"))
        graph.add_edge(WaitForEdge(waiter="B", holder="A", lock_name="lock2"))

        cycle = graph.detect_cycle()
        assert cycle is not None
        assert len(cycle.cycle) == 2

    def test_detect_cycle_three_nodes(self):
        graph = WaitForGraph()
        graph.add_edge(WaitForEdge(waiter="A", holder="B", lock_name="lock1"))
        graph.add_edge(WaitForEdge(waiter="B", holder="C", lock_name="lock2"))
        graph.add_edge(WaitForEdge(waiter="C", holder="A", lock_name="lock3"))

        cycle = graph.detect_cycle()
        assert cycle is not None
        assert len(cycle.cycle) == 3

    def test_no_cycle(self):
        graph = WaitForGraph()
        graph.add_edge(WaitForEdge(waiter="A", holder="B", lock_name="lock1"))
        graph.add_edge(WaitForEdge(waiter="B", holder="C", lock_name="lock2"))

        cycle = graph.detect_cycle()
        assert cycle is None

    def test_detect_all_cycles(self):
        graph = WaitForGraph()
        # Cycle 1: A -> B -> A
        graph.add_edge(WaitForEdge(waiter="A", holder="B", lock_name="lock1"))
        graph.add_edge(WaitForEdge(waiter="B", holder="A", lock_name="lock2"))
        # Cycle 2: C -> D -> C
        graph.add_edge(WaitForEdge(waiter="C", holder="D", lock_name="lock3"))
        graph.add_edge(WaitForEdge(waiter="D", holder="C", lock_name="lock4"))

        cycles = graph.detect_all_cycles()
        assert len(cycles) == 2

    def test_get_graph_state(self):
        graph = WaitForGraph()
        graph.add_edge(WaitForEdge(waiter="A", holder="B", lock_name="lock1"))
        graph.add_edge(WaitForEdge(waiter="A", holder="C", lock_name="lock2"))

        state = graph.get_graph_state()
        assert "A" in state
        assert set(state["A"]) == {"B", "C"}

    def test_clear(self):
        graph = WaitForGraph()
        graph.add_edge(WaitForEdge(waiter="A", holder="B", lock_name="lock1"))
        graph.clear()
        assert graph.edge_count == 0
        assert graph.node_count == 0

    def test_node_count(self):
        graph = WaitForGraph()
        graph.add_edge(WaitForEdge(waiter="A", holder="B", lock_name="lock1"))
        graph.add_edge(WaitForEdge(waiter="B", holder="C", lock_name="lock2"))
        assert graph.node_count == 3


class TestDeadlockDetector(unittest.TestCase):
    """Tests for DeadlockDetector."""

    def test_record_wait(self):
        detector = DeadlockDetector()
        detector.record_wait("A", "B", "lock1")
        assert detector.graph.edge_count == 1

    def test_record_acquired(self):
        detector = DeadlockDetector()
        detector.record_wait("A", "B", "lock1")
        detector.record_acquired("A", "lock1")
        assert detector.graph.edge_count == 0

    def test_record_released(self):
        detector = DeadlockDetector()
        detector.record_wait("A", "B", "lock1")
        detector.record_released("B", "lock1")
        assert detector.graph.edge_count == 0

    def test_check_deadlock_found(self):
        detector = DeadlockDetector()
        detector.record_wait("A", "B", "lock1")
        detector.record_wait("B", "A", "lock2")

        cycle = detector.check_deadlock()
        assert cycle is not None
        assert len(cycle.cycle) == 2

    def test_check_deadlock_not_found(self):
        detector = DeadlockDetector()
        detector.record_wait("A", "B", "lock1")

        cycle = detector.check_deadlock()
        assert cycle is None

    def test_detected_cycles(self):
        detector = DeadlockDetector()
        detector.record_wait("A", "B", "lock1")
        detector.record_wait("B", "A", "lock2")

        detector.check_deadlock()
        cycles = detector.detected_cycles
        assert len(cycles) == 1

    def test_start_stop(self):
        detector = DeadlockDetector(check_interval=0.05)
        detector.start()
        assert detector.is_running is True
        detector.stop()
        assert detector.is_running is False

    def test_context_manager(self):
        with DeadlockDetector(check_interval=10.0) as detector:
            assert detector.is_running is True
        assert detector.is_running is False

    def test_reset(self):
        detector = DeadlockDetector()
        detector.record_wait("A", "B", "lock1")
        detector.record_wait("B", "A", "lock2")
        detector.check_deadlock()

        detector.reset()
        assert detector.graph.edge_count == 0
        assert len(detector.detected_cycles) == 0

    def test_on_deadlock_callback(self):
        detected = []

        def on_deadlock(cycle):
            detected.append(cycle)

        detector = DeadlockDetector(on_deadlock_detected=on_deadlock)
        detector.record_wait("A", "B", "lock1")
        detector.record_wait("B", "A", "lock2")
        detector.check_deadlock()

        assert len(detected) == 1


# ---------------------------------------------------------------------------
# Monitoring Tests
# ---------------------------------------------------------------------------


class TestLockMetrics(unittest.TestCase):
    """Tests for LockMetrics."""

    def test_success_rate(self):
        m = LockMetrics(
            lock_name="test",
            acquisitions_total=10,
            acquisitions_success=8,
        )
        assert m.success_rate == 0.8

    def test_success_rate_zero(self):
        m = LockMetrics(lock_name="test")
        assert m.success_rate == 0.0

    def test_average_wait_time(self):
        m = LockMetrics(
            lock_name="test",
            acquisitions_total=2,
            total_wait_time_seconds=10.0,
        )
        assert m.average_wait_time == 5.0

    def test_average_hold_time(self):
        m = LockMetrics(
            lock_name="test",
            releases_total=2,
            total_hold_time_seconds=20.0,
        )
        assert m.average_hold_time == 10.0

    def test_contention_ratio(self):
        m = LockMetrics(
            lock_name="test",
            acquisitions_total=10,
            acquisitions_failed=3,
        )
        assert m.contention_ratio == 0.3

    def test_to_dict(self):
        m = LockMetrics(lock_name="test", acquisitions_total=5)
        d = m.to_dict()
        assert d["lock_name"] == "test"
        assert d["acquisitions_total"] == 5
        assert "success_rate" in d
        assert "contention_ratio" in d


class TestLockMonitor(unittest.TestCase):
    """Tests for LockMonitor."""

    def _make_mock_lock(self, name="test_lock"):
        mock_lock = MagicMock()
        mock_lock.lock_name = name
        mock_lock.ttl_seconds = 30.0
        return mock_lock

    def test_record_acquisition_success(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()
        result = LockResult(status=LockStatus.ACQUIRED, wait_time=0.5)

        monitor.record_acquisition(mock_lock, result)
        metrics = monitor.get_metrics("test_lock")
        assert metrics is not None
        assert metrics.acquisitions_total == 1
        assert metrics.acquisitions_success == 1
        assert metrics.current_holders == 1

    def test_record_acquisition_failure(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()
        result = LockResult(status=LockStatus.NOT_ACQUIRED, wait_time=1.0)

        monitor.record_acquisition(mock_lock, result)
        metrics = monitor.get_metrics("test_lock")
        assert metrics.acquisitions_failed == 1
        assert metrics.current_holders == 0

    def test_record_release(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()

        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))
        time.sleep(0.01)
        monitor.record_release(mock_lock)

        metrics = monitor.get_metrics("test_lock")
        assert metrics.releases_total == 1
        assert metrics.current_holders == 0
        assert metrics.total_hold_time_seconds > 0

    def test_record_renewal(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()

        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))
        monitor.record_renewal(mock_lock, LockResult(status=LockStatus.RENEWED))
        metrics = monitor.get_metrics("test_lock")
        assert metrics.renewals_total == 1

    def test_record_renewal_failure(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()

        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))
        monitor.record_renewal(mock_lock, LockResult(status=LockStatus.EXPIRED))
        metrics = monitor.get_metrics("test_lock")
        assert metrics.renewals_failed == 1

    def test_record_error(self):
        monitor = LockMonitor()
        monitor.record_error("test_lock", "Connection timeout")
        metrics = monitor.get_metrics("test_lock")
        assert metrics.errors == 1

    def test_check_health_healthy(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()

        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))
        result = monitor.check_health("test_lock")
        assert result.health == LockHealth.HEALTHY

    def test_check_health_no_metrics(self):
        monitor = LockMonitor()
        result = monitor.check_health("nonexistent")
        assert result.health == LockHealth.ERROR

    def test_check_health_contended(self):
        monitor = LockMonitor(alert_threshold_contention=0.3)
        mock_lock = self._make_mock_lock()

        # 3 failures out of 4 = 75% contention
        for _ in range(3):
            monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.NOT_ACQUIRED))
        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))

        result = monitor.check_health("test_lock")
        assert result.health == LockHealth.CONTENTED

    def test_check_health_deadlocked(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()

        # All failures = deadlocked
        for _ in range(5):
            monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.NOT_ACQUIRED))

        result = monitor.check_health("test_lock")
        assert result.health == LockHealth.DEADLOCKED

    def test_get_all_metrics(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()

        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))
        all_metrics = monitor.get_all_metrics()
        assert "test_lock" in all_metrics

    def test_get_summary(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()

        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))
        summary = monitor.get_summary()
        assert summary["total_locks"] == 1
        assert summary["total_acquisitions"] == 1

    def test_get_summary_empty(self):
        monitor = LockMonitor()
        summary = monitor.get_summary()
        assert summary["total_locks"] == 0

    def test_reset_specific(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock("lock_a")
        mock_lock_b = self._make_mock_lock("lock_b")

        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))
        monitor.record_acquisition(mock_lock_b, LockResult(status=LockStatus.ACQUIRED))

        monitor.reset("lock_a")
        assert monitor.get_metrics("lock_a") is None
        assert monitor.get_metrics("lock_b") is not None

    def test_reset_all(self):
        monitor = LockMonitor()
        mock_lock = self._make_mock_lock()

        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))
        monitor.reset()
        assert monitor.get_metrics("test_lock") is None

    def test_alert_callback(self):
        alerts = []

        def on_alert(name, message):
            alerts.append((name, message))

        monitor = LockMonitor(
            alert_threshold_contention=0.3,
            on_alert=on_alert,
        )
        mock_lock = self._make_mock_lock()

        # Trigger high contention
        for _ in range(4):
            monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.NOT_ACQUIRED))
        monitor.record_acquisition(mock_lock, LockResult(status=LockStatus.ACQUIRED))

        assert len(alerts) >= 1
        assert alerts[0][0] == "test_lock"


# ---------------------------------------------------------------------------
# Integration-style Tests
# ---------------------------------------------------------------------------


class TestDistributedLockIntegration(unittest.TestCase):
    """Integration tests combining multiple components."""

    def test_redis_lock_with_monitor(self):
        mock_redis = MagicMock()
        mock_redis.set.return_value = True
        mock_redis.get.return_value = "token"
        mock_redis.pttl.return_value = 30000
        release_script = MagicMock(return_value=1)
        mock_redis.register_script.return_value = release_script

        monitor = LockMonitor()
        lock = RedisDistributedLock(
            "integration_lock",
            ttl_seconds=10,
            redis_client=mock_redis,
        )

        result = lock.acquire(blocking=False)
        monitor.record_acquisition(lock, result)

        metrics = monitor.get_metrics("integration_lock")
        assert metrics.acquisitions_success == 1

        lock.release()
        monitor.record_release(lock)
        assert metrics.releases_total == 1

    def test_deadlock_detector_with_monitor(self):
        detector = DeadlockDetector()
        monitor = LockMonitor()

        detector.record_wait("txn_A", "txn_B", "lock_1")
        detector.record_wait("txn_B", "txn_A", "lock_2")

        cycle = detector.check_deadlock()
        assert cycle is not None

        mock_lock = MagicMock()
        mock_lock.lock_name = "lock_1"
        monitor.record_error("lock_1", "Deadlock detected")

        health = monitor.check_health("lock_1")
        assert health.health == LockHealth.ERROR

    def test_renewal_with_monitor(self):
        config = RenewalConfig(renewal_interval=0.05)
        manager = LockRenewalManager(config=config)
        monitor = LockMonitor()

        mock_lock = MagicMock()
        mock_lock.lock_name = "renewed_lock"
        mock_lock.ttl_seconds = 30.0
        mock_lock.renew.return_value = LockResult(status=LockStatus.RENEWED)

        manager.register(mock_lock)
        time.sleep(0.15)

        stats = manager.get_stats("renewed_lock")
        assert stats.renewals_attempted >= 1

        # Record renewals in monitor
        for _ in range(stats.renewals_succeeded):
            monitor.record_renewal(mock_lock, LockResult(status=LockStatus.RENEWED))

        metrics = monitor.get_metrics("renewed_lock")
        assert metrics.renewals_total >= 1

        manager.shutdown()


if __name__ == "__main__":
    unittest.main()
