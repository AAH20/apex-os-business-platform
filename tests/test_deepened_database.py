"""Tests for deepened database modules: query builder, pooling, replicas, sharding, FTS."""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime


class TestQueryBuilder:
    """Test the query builder module."""

    def test_select_basic(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("users")
        sql, params = qb.select("id", "name").build()
        assert "SELECT id, name FROM users" in sql
        assert params == []

    def test_select_where_clause(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("users")
        sql, params = qb.select("*").where("active", "=", True).build()
        assert "WHERE active = ?" in sql
        assert params == [True]

    def test_select_multiple_where(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("users")
        sql, params = qb.select("*").where("age", ">", 18).where("role", "=", "admin").build()
        assert sql.count("WHERE") == 1
        assert "AND" in sql
        assert params == [18, "admin"]

    def test_select_order_by_limit(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("users")
        sql, params = qb.select("*").order_by("created_at", "DESC").limit(10).build()
        assert "ORDER BY created_at DESC" in sql
        assert "LIMIT 10" in sql

    def test_insert(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("users")
        sql, params = qb.insert({"name": "Alice", "email": "alice@example.com"}).build()
        assert "INSERT INTO users" in sql
        assert "name" in sql and "email" in sql
        assert params == ["Alice", "alice@example.com"]

    def test_update(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("users")
        sql, params = qb.update({"name": "Bob"}).where("id", "=", 5).build()
        assert "UPDATE users SET" in sql
        assert "WHERE id = ?" in sql
        assert params == ["Bob", 5]

    def test_delete(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("users")
        sql, params = qb.delete().where("id", "=", 10).build()
        assert "DELETE FROM users" in sql
        assert params == [10]

    def test_join(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("orders")
        sql, params = qb.select("orders.*", "users.name").join("users", "orders.user_id = users.id").build()
        assert "JOIN users ON orders.user_id = users.id" in sql

    def test_group_by_having(self):
        from apex_os_bp.database.deepened import QueryBuilder
        qb = QueryBuilder("orders")
        sql, params = qb.select("user_id", "COUNT(*) as cnt").group_by("user_id").having("cnt", ">", 5).build()
        assert "GROUP BY user_id" in sql
        assert "HAVING cnt > ?" in sql
        assert params == [5]


class TestConnectionPooling:
    """Test connection pooling."""

    def test_pool_initialization(self):
        from apex_os_bp.database.deepened import ConnectionPool
        pool = ConnectionPool(max_size=5, timeout=30)
        assert pool.max_size == 5
        assert pool.timeout == 30
        assert pool.size() == 0

    def test_acquire_release(self):
        from apex_os_bp.database.deepened import ConnectionPool
        pool = ConnectionPool(max_size=2)
        conn = pool.acquire()
        assert conn is not None
        assert pool.size() == 1
        pool.release(conn)
        assert pool.size() == 0

    def test_pool_exhaustion(self):
        from apex_os_bp.database.deepened import ConnectionPool
        pool = ConnectionPool(max_size=1, timeout=0.1)
        conn1 = pool.acquire()
        with pytest.raises(TimeoutError):
            pool.acquire()
        pool.release(conn1)

    def test_pool_max_size_enforced(self):
        from apex_os_bp.database.deepened import ConnectionPool
        pool = ConnectionPool(max_size=3)
        conns = [pool.acquire() for _ in range(3)]
        assert pool.size() == 3
        for c in conns:
            pool.release(c)


class TestReadReplicas:
    """Test read replica routing."""

    def test_read_routing(self):
        from apex_os_bp.database.deepened import ReplicaRouter
        router = ReplicaRouter(replicas=["r1", "r2", "r3"])
        target = router.get_read_target()
        assert target in ["r1", "r2", "r3"]

    def test_write_routing(self):
        from apex_os_bp.database.deepened import ReplicaRouter
        router = ReplicaRouter(primary="master", replicas=["r1", "r2"])
        assert router.get_write_target() == "master"

    def test_replica_failover(self):
        from apex_os_bp.database.deepened import ReplicaRouter
        router = ReplicaRouter(replicas=["r1", "r2"])
        router.mark_unhealthy("r1")
        for _ in range(10):
            assert router.get_read_target() != "r1"


class TestSharding:
    """Test sharding logic."""

    def test_shard_key_routing(self):
        from apex_os_bp.database.deepened import ShardRouter
        router = Router(shards=["shard_0", "shard_1", "shard_2"])
        shard = router.get_shard("user_123")
        assert shard in ["shard_0", "shard_1", "shard_2"]

    def test_consistent_sharding(self):
        from apex_os_bp.database.deepened import ShardRouter
        router = ShardRouter(shards=["s0", "s1"])
        assert router.get_shard("key_a") == router.get_shard("key_a")

    def test_shard_count(self):
        from apex_os_bp.database.deepened import ShardRouter
        router = ShardRouter(shards=["a", "b", "c", "d"])
        assert router.shard_count() == 4


class TestFullTextSearch:
    """Test full-text search."""

    def test_fts_query_building(self):
        from apex_os_bp.database.deepened import FullTextSearch
        fts = FullTextSearch("documents")
        sql, params = fts.search("hello world").build()
        assert "MATCH" in sql or "to_tsvector" in sql.lower()
        assert "hello" in str(params)

    def test_fts_ranking(self):
        from apex_os_bp.database.deepened import FullTextSearch
        fts = FullTextSearch("documents")
        sql, params = fts.search("test").rank().build()
        assert "ts_rank" in sql or "RANK" in sql.upper()

    def test_fts_highlighting(self):
        from apex_os_bp.database.deepened import FullTextSearch
        fts = FullTextSearch("documents")
        sql, params = fts.search("python").highlight().build()
        assert "ts_headline" in sql or "highlight" in sql.lower()
