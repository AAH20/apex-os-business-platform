"""Tests for deepened cache modules: multi-level, invalidation, warming, analytics, Redis Cluster."""
import pytest
from unittest.mock import MagicMock, patch, call


class TestMultiLevelCache:
    """Test multi-level caching (L1/L2)."""

    def test_l1_hit(self):
        from apex_os_bp.cache.deepened import MultiLevelCache
        cache = MultiLevelCache()
        cache.l1_set("key", "value")
        assert cache.get("key") == "value"

    def test_l2_fallback(self):
        from apex_os_bp.cache.deepened import MultiLevelCache
        cache = MultiLevelCache()
        cache.l2_set("key", "l2_value")
        assert cache.get("key") == "l2_value"

    def test_l1_priority_over_l2(self):
        from apex_os_bp.cache.deepened import MultiLevelCache
        cache = MultiLevelCache()
        cache.l1_set("key", "l1_value")
        cache.l2_set("key", "l2_value")
        assert cache.get("key") == "l1_value"

    def test_promotion_l2_to_l1(self):
        from apex_os_bp.cache.deepened import MultiLevelCache
        cache = MultiLevelCache()
        cache.l2_set("key", "val")
        cache.get("key")
        assert cache.l1_get("key") == "val"


class TestCacheInvalidation:
    """Test cache invalidation strategies."""

    def test_ttl_expiration(self):
        from apex_os_bp.cache.deepened import InvalidationManager
        mgr = InvalidationManager()
        mgr.set("key", "value", ttl=0)
        assert mgr.get("key") is None

    def test_explicit_invalidation(self):
        from apex_os_bp.cache.deepened import InvalidationManager
        mgr = InvalidationManager()
        mgr.set("key", "value")
        mgr.invalidate("key")
        assert mgr.get("key") is None

    def test_pattern_invalidation(self):
        from apex_os_bp.cache.deepened import InvalidationManager
        mgr = InvalidationManager()
        mgr.set("user:1", "a")
        mgr.set("user:2", "b")
        mgr.set("post:1", "c")
        mgr.invalidate_pattern("user:*")
        assert mgr.get("user:1") is None
        assert mgr.get("user:2") is None
        assert mgr.get("post:1") == "c"

    def test_tag_based_invalidation(self):
        from apex_os_bp.cache.deepened import InvalidationManager
        mgr = InvalidationManager()
        mgr.set("key1", "val1", tags=["users"])
        mgr.set("key2", "val2", tags=["posts"])
        mgr.invalidate_tag("users")
        assert mgr.get("key1") is None
        assert mgr.get("key2") == "val2"


class TestCacheWarming:
    """Test cache warming."""

    def test_warm_specific_keys(self):
        from apex_os_bp.cache.deepened import CacheWarmer
        warmer = CacheWarmer()
        fetcher = MagicMock(side_effect=lambda k: f"val_{k}")
        warmer.warm(["a", "b", "c"], fetcher)
        assert warmer.get("a") == "val_a"
        assert warmer.get("b") == "val_b"

    def test_warm_with_ttl(self):
        from apex_os_bp.cache.deepened import CacheWarmer
        warmer = CacheWarmer()
        warmer.warm(["x"], lambda k: "data", ttl=300)
        assert warmer.ttl("x") == 300

    def test_warm_empty_keys(self):
        from apex_os_bp.cache.deepened import CacheWarmer
        warmer = CacheWarmer()
        fetcher = MagicMock()
        warmer.warm([], fetcher)
        fetcher.assert_not_called()


class TestCacheAnalytics:
    """Test cache analytics."""

    def test_hit_counting(self):
        from apex_os_bp.cache.deepened import CacheAnalytics
        stats = CacheAnalytics()
        stats.record_hit()
        stats.record_hit()
        stats.record_miss()
        assert stats.hits == 2
        assert stats.misses == 1

    def test_hit_ratio(self):
        from apex_os_bp.cache.deepened import CacheAnalytics
        stats = CacheAnalytics()
        for _ in range(7):
            stats.record_hit()
        for _ in range(3):
            stats.record_miss()
        assert stats.hit_ratio() == 0.7

    def test_zero_hit_ratio(self):
        from apex_os_bp.cache.deepened import CacheAnalytics
        stats = CacheAnalytics()
        assert stats.hit_ratio() == 0.0


class TestRedisCluster:
    """Test Redis Cluster integration."""

    def test_cluster_connection(self):
        from apex_os_bp.cache.deepened import RedisClusterCache
        with patch("apex_os.cache.redis_cluster.RedisCluster") as mock_rc:
            cache = RedisClusterCache(startup_nodes=[{"host": "localhost", "port": 7000}])
            assert cache.client is not None

    def test_cluster_get_set(self):
        from apex_os_bp.cache.deepened import RedisClusterCache
        with patch("apex_os.cache.redis_cluster.RedisCluster") as mock_rc:
            instance = mock_rc.from_url.return_value
            cache = RedisClusterCache(startup_nodes=[{"host": "localhost", "port": 7000}])
            cache.set("foo", "bar")
            instance.set.assert_called_with("foo", "bar")

    def test_cluster_failover(self):
        from apex_os_bp.cache.deepened import RedisClusterCache
        with patch("apex_os.cache.redis_cluster.RedisCluster") as mock_rc:
            mock_rc.from_url.side_effect = Exception("failover")
            with pytest.raises(Exception):
                RedisClusterCache(startup_nodes=[{"host": "bad", "port": 0}])
