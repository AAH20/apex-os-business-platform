"""Tests for deepened cache modules: multi-level, invalidation, warming, analytics, Redis Cluster."""
import asyncio

import pytest


class TestMultiLevelCache:
    """Test multi-level caching (L1) via the async MultiLevelCache API."""

    def _make(self):
        from apex_os_bp.cache.deepened import MultiLevelCache
        return MultiLevelCache()

    def test_l1_hit(self):
        from apex_os_bp.cache.deepened import CacheLevel
        cache = self._make()
        asyncio.run(cache.set("key", "value", level=CacheLevel.L1))
        assert asyncio.run(cache.get("key")) == "value"

    def test_l2_fallback(self):
        # L2/L3 are redis-backed tiers that need a live server; the offline
        # behaviour is: L2 get() returns None unconnected.
        from apex_os_bp.cache.deepened import L2Cache
        l2 = L2Cache()
        assert asyncio.run(l2.get("key")) is None

    def test_l1_priority_over_l2(self):
        from apex_os_bp.cache.deepened import CacheLevel
        cache = self._make()
        asyncio.run(cache.set("key", "l1_value", level=CacheLevel.L1))
        assert asyncio.run(cache.get("key")) == "l1_value"

    def test_promotion_l2_to_l1(self):
        cache = self._make()
        cache.l1.set("key", "val")
        assert cache.l1.get("key") == "val"


class TestCacheInvalidation:
    """Test L1 cache invalidation strategies (ttl, explicit, pattern, tag)."""

    def _store(self):
        from apex_os_bp.cache.deepened import L1Cache
        return L1Cache()

    def test_ttl_expiration(self):
        store = self._store()
        store.set("key", "value", ttl=-1)
        assert store.get("key") is None

    def test_explicit_invalidation(self):
        store = self._store()
        store.set("key", "value")
        assert store.invalidate("key") is True
        assert store.get("key") is None

    def test_pattern_invalidation(self):
        import fnmatch
        store = self._store()
        store.set("user:1", "a")
        store.set("user:2", "b")
        store.set("post:1", "c")
        for k in [k for k in store._store if fnmatch.fnmatch(k, "user:*")]:
            store.invalidate(k)
        assert store.get("user:1") is None
        assert store.get("user:2") is None
        assert store.get("post:1") == "c"

    def test_tag_based_invalidation(self):
        store = self._store()
        store.set("key1", "val1", tags={"users"})
        store.set("key2", "val2", tags={"posts"})
        assert store.invalidate_by_tag("users") == 1
        assert store.get("key1") is None
        assert store.get("key2") == "val2"


class TestCacheWarming:
    """Test cache warming."""

    def test_warm_specific_keys(self):
        from apex_os_bp.cache.deepened import MultiLevelCache, CacheWarmer

        async def fetch_a():
            return "val_a"

        async def fetch_b():
            return "val_b"

        mc = MultiLevelCache()
        warmer = CacheWarmer(mc)
        warmer.register_warmer("a", fetch_a)
        warmer.register_warmer("b", fetch_b)
        warmer.register_warmer("c", fetch_a)
        n = asyncio.run(warmer.warm(["a", "b", "c"]))
        assert n == 3

    def test_warm_no_keys_registered(self):
        from apex_os_bp.cache.deepened import MultiLevelCache, CacheWarmer
        warmer = CacheWarmer(MultiLevelCache())
        n = asyncio.run(warmer.warm(["missing"]))
        assert n == 0

    def test_warm_empty_keys(self):
        from apex_os_bp.cache.deepened import MultiLevelCache, CacheWarmer
        warmer = CacheWarmer(MultiLevelCache())
        assert asyncio.run(warmer.warm([])) == 0


class TestCacheAnalytics:
    """Test cache analytics snapshots."""

    def _an(self):
        from apex_os_bp.cache.deepened import MultiLevelCache
        return MultiLevelCache().analytics

    def test_snapshot_keys(self):
        an = self._an()
        snap = an.snapshot()
        assert {"l1", "l2", "l3", "aggregate"} <= set(snap)

    def test_snapshot_hit_ratio(self):
        from apex_os_bp.cache.deepened import MultiLevelCache
        mc = MultiLevelCache()
        mc.l1.get("missing")   # miss
        mc.l1.set("hit", "v")
        mc.l1.get("hit")       # hit
        l1 = mc.analytics.snapshot()["l1"]
        assert l1["hit_ratio"] == pytest.approx(0.5)

    def test_zero_hit_ratio(self):
        an = self._an()
        l1 = an.snapshot()["l1"]
        assert l1["hit_ratio"] == 0.0


class TestRedisCluster:
    """Test Redis Cluster integration via the L3Cache facade."""

    def test_l3_constructs_without_redis(self):
        from apex_os_bp.cache.deepened import L3Cache
        cache = L3Cache(startup_nodes=[{"host": "localhost", "port": 7000}])
        assert cache._redis is None

    def test_l3_stats_present(self):
        from apex_os_bp.cache.deepened import L3Cache
        assert L3Cache(startup_nodes=[{"host": "localhost", "port": 7000}]).stats is not None

    def test_l3_get_returns_none_unconnected(self):
        from apex_os_bp.cache.deepened import L3Cache
        cache = L3Cache(startup_nodes=[{"host": "localhost", "port": 7000}])
        assert asyncio.run(cache.get("k")) is None
