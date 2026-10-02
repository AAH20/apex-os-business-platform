"""Tests for the APEX-OS caching layer."""

from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from apex_os_bp.cache.memory_cache import MemoryCache
from apex_os_bp.cache.redis_cache import RedisCache
from apex_os_bp.cache.invalidation import CacheInvalidator, MultiLevelInvalidator
from apex_os_bp.cache.warming import CacheWarmer, WarmingScheduler
from apex_os_bp.cache.statistics import CacheStats, CacheStatsSnapshot, StatsCacheWrapper


# ---------------------------------------------------------------------------
# MemoryCache Tests
# ---------------------------------------------------------------------------


class TestMemoryCache(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = MemoryCache(max_size=100, default_ttl=60)

    def test_set_and_get(self) -> None:
        self.cache.set("foo", "bar")
        self.assertEqual(self.cache.get("foo"), "bar")

    def test_get_missing_returns_none(self) -> None:
        self.assertIsNone(self.cache.get("nonexistent"))

    def test_delete(self) -> None:
        self.cache.set("foo", "bar")
        self.assertTrue(self.cache.delete("foo"))
        self.assertIsNone(self.cache.get("foo"))
        self.assertFalse(self.cache.delete("foo"))

    def test_exists(self) -> None:
        self.cache.set("foo", "bar")
        self.assertTrue(self.cache.exists("foo"))
        self.assertFalse(self.cache.exists("nope"))

    def test_ttl_expiry(self) -> None:
        self.cache.set("foo", "bar", ttl=1)
        self.assertEqual(self.cache.get("foo"), "bar")
        time.sleep(1.1)
        self.assertIsNone(self.cache.get("foo"))

    def test_ttl_remaining(self) -> None:
        self.cache.set("foo", "bar", ttl=10)
        remaining = self.cache.ttl("foo")
        self.assertGreater(remaining, 0)
        self.assertLessEqual(remaining, 10)

    def test_ttl_missing_key(self) -> None:
        self.assertEqual(self.cache.ttl("missing"), -2)

    def test_clear(self) -> None:
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.cache.clear()
        self.assertIsNone(self.cache.get("a"))
        self.assertIsNone(self.cache.get("b"))
        self.assertEqual(self.cache.size(), 0)

    def test_keys(self) -> None:
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        keys = self.cache.keys()
        self.assertIn("a", keys)
        self.assertIn("b", keys)

    def test_max_size_eviction(self) -> None:
        cache = MemoryCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # should evict "a"
        self.assertIsNone(cache.get("a"))
        self.assertIsNotNone(cache.get("d"))

    def test_lru_order(self) -> None:
        cache = MemoryCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # refresh "a"
        cache.set("d", 4)  # should evict "b" (oldest)
        self.assertIsNotNone(cache.get("a"))
        self.assertIsNone(cache.get("b"))

    def test_get_or_set(self) -> None:
        cache = MemoryCache()
        value = cache.get_or_set("key", lambda: 42)
        self.assertEqual(value, 42)
        # second call should return cached
        value2 = cache.get_or_set("key", lambda: 99)
        self.assertEqual(value2, 42)

    def test_overwrite(self) -> None:
        self.cache.set("foo", "bar")
        self.cache.set("foo", "baz")
        self.assertEqual(self.cache.get("foo"), "baz")

    def test_thread_safety(self) -> None:
        cache = MemoryCache(max_size=1000)
        errors: list[Exception] = []

        def writer(start: int) -> None:
            try:
                for i in range(start, start + 100):
                    cache.set(f"key_{i}", i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 100,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(cache.size(), 1000)


# ---------------------------------------------------------------------------
# RedisCache Tests (mocked)
# ---------------------------------------------------------------------------


class TestRedisCache(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_redis = MagicMock()
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = True
        self.mock_redis.delete.return_value = 1
        self.mock_redis.exists.return_value = 1
        self.mock_redis.ttl.return_value = -1
        self.mock_redis.scan_iter.return_value = []
        self.mock_redis.ping.return_value = True
        self.mock_redis.pipeline.return_value = self.mock_redis
        self.mock_redis.incrby.return_value = 1

        with patch("apex_os_bp.cache.redis_cache.redis") as mock_module:
            mock_module.Redis.return_value = self.mock_redis
            self.cache = RedisCache()

    def test_set_and_get(self) -> None:
        import json

        self.mock_redis.get.return_value = json.dumps("bar")
        self.cache.set("foo", "bar")
        result = self.cache.get("foo")
        self.assertEqual(result, "bar")

    def test_get_missing(self) -> None:
        self.mock_redis.get.return_value = None
        self.assertIsNone(self.cache.get("missing"))

    def test_delete(self) -> None:
        self.mock_redis.delete.return_value = 1
        self.assertTrue(self.cache.delete("foo"))

    def test_exists(self) -> None:
        self.mock_redis.exists.return_value = 1
        self.assertTrue(self.cache.exists("foo"))

    def test_ttl(self) -> None:
        self.mock_redis.ttl.return_value = 300
        self.assertEqual(self.cache.ttl("foo"), 300)

    def test_flush(self) -> None:
        self.mock_redis.scan_iter.return_value = ["apex:foo", "apex:bar"]
        self.assertTrue(self.cache.flush())
        self.mock_redis.delete.assert_called_with("apex:foo", "apex:bar")

    def test_mget(self) -> None:
        import json

        self.mock_redis.mget.return_value = [json.dumps("a"), None, json.dumps("c")]
        result = self.cache.mget(["k1", "k2", "k3"])
        self.assertEqual(result, {"k1": "a", "k2": None, "k3": "c"})

    def test_mset(self) -> None:
        self.assertTrue(self.cache.mset({"a": 1, "b": 2}))

    def test_increment(self) -> None:
        self.mock_redis.incrby.return_value = 5
        self.assertEqual(self.cache.increment("counter", 3), 5)

    def test_expire(self) -> None:
        self.mock_redis.expire.return_value = True
        self.assertTrue(self.cache.expire("foo", 120))

    def test_keys(self) -> None:
        self.mock_redis.scan_iter.return_value = ["apex:foo", "apex:bar"]
        keys = self.cache.keys()
        self.assertEqual(keys, ["foo", "bar"])

    def test_ping(self) -> None:
        self.assertTrue(self.cache.ping())

    def test_ping_failure(self) -> None:
        self.mock_redis.ping.side_effect = Exception("connection refused")
        self.assertFalse(self.cache.ping())

    def test_key_prefix(self) -> None:
        self.cache.set("foo", "bar")
        call_args = self.mock_redis.set.call_args
        self.assertTrue(call_args[0][0].startswith("apex:"))

    def test_close(self) -> None:
        self.cache.close()
        self.mock_redis.close.assert_called_once()


# ---------------------------------------------------------------------------
# CacheInvalidator Tests
# ---------------------------------------------------------------------------


class TestCacheInvalidator(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MagicMock()
        self.backend.delete.return_value = True
        self.backend.keys.return_value = []
        self.backend.flush.return_value = True
        self.backend.get.return_value = None
        self.invalidator = CacheInvalidator(self.backend)

    def test_invalidate_single_key(self) -> None:
        self.assertTrue(self.invalidator.invalidate("foo"))
        self.backend.delete.assert_called_with("foo")

    def test_invalidate_pattern(self) -> None:
        import fnmatch

        all_keys = ["foo:1", "foo:2", "bar:1"]
        self.backend.keys.side_effect = lambda pattern="*": [
            k for k in all_keys if fnmatch.fnmatch(k, pattern)
        ]
        count = self.invalidator.invalidate_pattern("foo:*")
        self.assertEqual(count, 2)

    def test_invalidate_tags(self) -> None:
        self.invalidator.register_tag("key1", "tag_a")
        self.invalidator.register_tag("key2", "tag_a")
        self.invalidator.register_tag("key3", "tag_b")
        count = self.invalidator.invalidate_tags(["tag_a"])
        self.assertEqual(count, 2)

    def test_invalidate_all(self) -> None:
        self.assertTrue(self.invalidator.invalidate_all())
        self.backend.flush.assert_called_once()

    def test_register_and_invalidate_multiple_tags(self) -> None:
        self.invalidator.register_tags("key1", ["tag_a", "tag_b"])
        count = self.invalidator.invalidate_tags(["tag_a", "tag_b"])
        self.assertEqual(count, 1)

    def test_invalidate_with_callback(self) -> None:
        callback = MagicMock(return_value="result")
        result = self.invalidator.invalidate_with_callback("foo", callback)
        self.assertEqual(result, "result")
        callback.assert_called_once()

    def test_invalidate_conditional_true(self) -> None:
        self.backend.get.return_value = {"active": True}
        result = self.invalidator.invalidate_conditional(
            "foo", lambda v: v.get("active") is True
        )
        self.assertTrue(result)

    def test_invalidate_conditional_false(self) -> None:
        self.backend.get.return_value = {"active": False}
        result = self.invalidator.invalidate_conditional(
            "foo", lambda v: v.get("active") is True
        )
        self.assertFalse(result)

    def test_invalidate_conditional_missing(self) -> None:
        self.backend.get.return_value = None
        result = self.invalidator.invalidate_conditional("foo", lambda v: True)
        self.assertFalse(result)


class TestMultiLevelInvalidator(unittest.TestCase):
    def setUp(self) -> None:
        self.backend1 = MagicMock()
        self.backend2 = MagicMock()
        self.backend1.delete.return_value = True
        self.backend2.delete.return_value = True
        self.backend1.flush.return_value = True
        self.backend2.flush.return_value = True
        self.multi = MultiLevelInvalidator(self.backend1, self.backend2)

    def test_invalidate_all_tiers(self) -> None:
        self.assertTrue(self.multi.invalidate("foo"))
        self.backend1.delete.assert_called_with("foo")
        self.backend2.delete.assert_called_with("foo")

    def test_invalidate_pattern_all_tiers(self) -> None:
        self.backend1.keys.return_value = ["a", "b"]
        self.backend2.keys.return_value = ["c"]
        count = self.multi.invalidate_pattern("*")
        self.assertEqual(count, 3)

    def test_invalidate_all(self) -> None:
        self.assertTrue(self.multi.invalidate_all())

    def test_register_tag_all_tiers(self) -> None:
        self.multi.register_tag("key1", "tag_x")
        # Both invalidators should have the tag registered
        self.backend1.delete.return_value = True
        self.backend2.delete.return_value = True
        count = self.multi._invalidators[0].invalidate_tags(["tag_x"])
        self.assertEqual(count, 1)


# ---------------------------------------------------------------------------
# CacheWarmer Tests
# ---------------------------------------------------------------------------


class TestCacheWarmer(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MagicMock()
        self.backend.set.return_value = True
        self.backend.ttl.return_value = -2
        self.warmer = CacheWarmer(self.backend)

    def test_warm_entry(self) -> None:
        result = self.warmer.warm_entry("foo", lambda: "bar")
        self.assertTrue(result)
        self.backend.set.assert_called_with("foo", "bar", ttl=None)

    def test_warm_entry_with_ttl(self) -> None:
        result = self.warmer.warm_entry("foo", lambda: "bar", ttl=120)
        self.assertTrue(result)
        self.backend.set.assert_called_with("foo", "bar", ttl=120)

    def test_warm_entry_failure(self) -> None:
        result = self.warmer.warm_entry("foo", lambda: 1 / 0)
        self.assertFalse(result)

    def test_warm_entries(self) -> None:
        loaders = {
            "a": lambda: 1,
            "b": lambda: 2,
            "c": lambda: 3,
        }
        results = self.warmer.warm_entries(loaders)
        self.assertTrue(all(results.values()))
        self.assertEqual(len(results), 3)

    def test_warm_entries_partial_failure(self) -> None:
        loaders = {
            "a": lambda: 1,
            "b": lambda: 1 / 0,
            "c": lambda: 3,
        }
        results = self.warmer.warm_entries(loaders)
        self.assertTrue(results["a"])
        self.assertFalse(results["b"])
        self.assertTrue(results["c"])

    def test_warm_from_iterable(self) -> None:
        items = [("a", 1), ("b", 2), ("c", 3)]
        count = self.warmer.warm_from_iterable(items)
        self.assertEqual(count, 3)

    def test_warm_with_refresh_needed(self) -> None:
        self.backend.ttl.return_value = 10
        result = self.warmer.warm_with_refresh("foo", lambda: "bar", ttl=100)
        self.assertTrue(result)
        self.backend.set.assert_called_once()

    def test_warm_with_refresh_not_needed(self) -> None:
        self.backend.ttl.return_value = 95
        result = self.warmer.warm_with_refresh("foo", lambda: "bar", ttl=100)
        self.assertTrue(result)
        self.backend.set.assert_not_called()

    def test_schedule_warming(self) -> None:
        stop = self.warmer.schedule_warming(
            "foo", lambda: "bar", interval=60, immediate=False
        )
        self.assertIsInstance(stop, threading.Event)
        stop.set()

    def test_schedule_warming_immediate(self) -> None:
        stop = self.warmer.schedule_warming(
            "foo", lambda: "bar", interval=60, immediate=True
        )
        self.backend.set.assert_called()
        stop.set()


class TestWarmingScheduler(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MagicMock()
        self.backend.set.return_value = True
        self.backend.ttl.return_value = -2
        self.warmer = CacheWarmer(self.backend)
        self.scheduler = WarmingScheduler(self.warmer)

    def test_schedule_and_cancel(self) -> None:
        self.scheduler.schedule("foo", lambda: "bar", interval=60, immediate=False)
        self.assertIn("foo", self.scheduler._stop_events)
        result = self.scheduler.cancel("foo")
        self.assertTrue(result)
        self.assertNotIn("foo", self.scheduler._stop_events)

    def test_cancel_nonexistent(self) -> None:
        result = self.scheduler.cancel("nonexistent")
        self.assertFalse(result)

    def test_cancel_all(self) -> None:
        self.scheduler.schedule("a", lambda: 1, interval=60, immediate=False)
        self.scheduler.schedule("b", lambda: 2, interval=60, immediate=False)
        self.scheduler.cancel_all()
        self.assertEqual(len(self.scheduler._stop_events), 0)

    def test_schedule_replaces_existing(self) -> None:
        self.scheduler.schedule("foo", lambda: "bar", interval=60, immediate=False)
        old_event = self.scheduler._stop_events["foo"]
        self.scheduler.schedule("foo", lambda: "baz", interval=60, immediate=False)
        new_event = self.scheduler._stop_events["foo"]
        self.assertIsNot(old_event, new_event)
        self.assertTrue(old_event.is_set())


# ---------------------------------------------------------------------------
# CacheStats Tests
# ---------------------------------------------------------------------------


class TestCacheStats(unittest.TestCase):
    def setUp(self) -> None:
        self.stats = CacheStats()

    def test_initial_state(self) -> None:
        snapshot = self.stats.get_stats()
        self.assertEqual(snapshot.hits, 0)
        self.assertEqual(snapshot.misses, 0)
        self.assertEqual(snapshot.hit_rate, 0.0)

    def test_record_hit(self) -> None:
        self.stats.record_hit()
        self.assertEqual(self.stats.get_stats().hits, 1)

    def test_record_miss(self) -> None:
        self.stats.record_miss()
        self.assertEqual(self.stats.get_stats().misses, 1)

    def test_record_set(self) -> None:
        self.stats.record_set()
        self.assertEqual(self.stats.get_stats().sets, 1)

    def test_record_delete(self) -> None:
        self.stats.record_delete()
        self.assertEqual(self.stats.get_stats().deletes, 1)

    def test_record_eviction(self) -> None:
        self.stats.record_eviction()
        self.assertEqual(self.stats.get_stats().evictions, 1)

    def test_hit_rate(self) -> None:
        self.stats.record_hit()
        self.stats.record_hit()
        self.stats.record_miss()
        self.assertAlmostEqual(self.stats.get_stats().hit_rate, 2 / 3)

    def test_miss_rate(self) -> None:
        self.stats.record_hit()
        self.stats.record_miss()
        self.stats.record_miss()
        self.assertAlmostEqual(self.stats.get_stats().miss_rate, 2 / 3)

    def test_avg_latency(self) -> None:
        self.stats.record_hit(latency_ms=10.0)
        self.stats.record_hit(latency_ms=20.0)
        self.assertAlmostEqual(self.stats.get_stats().avg_latency_ms, 15.0)

    def test_reset(self) -> None:
        self.stats.record_hit()
        self.stats.record_miss()
        self.stats.record_set()
        self.stats.reset()
        snapshot = self.stats.get_stats()
        self.assertEqual(snapshot.hits, 0)
        self.assertEqual(snapshot.misses, 0)
        self.assertEqual(snapshot.sets, 0)
        self.assertEqual(snapshot.operations, 0)

    def test_summary(self) -> None:
        self.stats.record_hit()
        summary = self.stats.summary()
        self.assertIn("hit_rate", summary)
        self.assertIn("miss_rate", summary)
        self.assertIn("avg_latency_ms", summary)
        self.assertIn("uptime_seconds", summary)

    def test_to_dict(self) -> None:
        self.stats.record_hit()
        d = self.stats.get_stats().to_dict()
        self.assertIn("hits", d)
        self.assertIn("misses", d)
        self.assertIn("hit_rate", d)

    def test_uptime(self) -> None:
        self.assertGreaterEqual(self.stats.uptime_seconds, 0)

    def test_thread_safety(self) -> None:
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(100):
                    self.stats.record_hit()
                    self.stats.record_miss()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(self.stats.get_stats().hits, 1000)
        self.assertEqual(self.stats.get_stats().misses, 1000)


class TestStatsCacheWrapper(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MagicMock()
        self.backend.get.return_value = "value"
        self.backend.set.return_value = True
        self.backend.delete.return_value = True
        self.stats = CacheStats()
        self.wrapper = StatsCacheWrapper(self.backend, self.stats)

    def test_get_hit(self) -> None:
        result = self.wrapper.get("foo")
        self.assertEqual(result, "value")
        self.assertEqual(self.stats.get_stats().hits, 1)

    def test_get_miss(self) -> None:
        self.backend.get.return_value = None
        result = self.wrapper.get("foo")
        self.assertIsNone(result)
        self.assertEqual(self.stats.get_stats().misses, 1)

    def test_set(self) -> None:
        self.wrapper.set("foo", "bar")
        self.assertEqual(self.stats.get_stats().sets, 1)

    def test_delete(self) -> None:
        self.wrapper.delete("foo")
        self.assertEqual(self.stats.get_stats().deletes, 1)

    def test_delegation(self) -> None:
        self.backend.custom_method.return_value = "delegated"
        result = self.wrapper.custom_method()
        self.assertEqual(result, "delegated")

    def test_stats_property(self) -> None:
        self.assertIs(self.wrapper.stats, self.stats)


# ---------------------------------------------------------------------------
# CacheStatsSnapshot Tests
# ---------------------------------------------------------------------------


class TestCacheStatsSnapshot(unittest.TestCase):
    def test_default_values(self) -> None:
        snap = CacheStatsSnapshot()
        self.assertEqual(snap.hits, 0)
        self.assertEqual(snap.misses, 0)
        self.assertEqual(snap.hit_rate, 0.0)

    def test_hit_rate_calculation(self) -> None:
        snap = CacheStatsSnapshot(hits=3, misses=1)
        self.assertAlmostEqual(snap.hit_rate, 0.75)

    def test_miss_rate_calculation(self) -> None:
        snap = CacheStatsSnapshot(hits=1, misses=3)
        self.assertAlmostEqual(snap.miss_rate, 0.75)

    def test_avg_latency_calculation(self) -> None:
        snap = CacheStatsSnapshot(total_latency_ms=100.0, operations=4)
        self.assertAlmostEqual(snap.avg_latency_ms, 25.0)

    def test_to_dict_keys(self) -> None:
        snap = CacheStatsSnapshot(hits=1, misses=1)
        d = snap.to_dict()
        expected_keys = {
            "hits", "misses", "sets", "deletes", "evictions",
            "hit_rate", "miss_rate", "avg_latency_ms", "operations",
        }
        self.assertEqual(set(d.keys()), expected_keys)


if __name__ == "__main__":
    unittest.main()
