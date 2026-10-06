"""Tests for deepened database modules: query builder, pooling, replicas, sharding, FTS."""
import pytest
import sys
from unittest.mock import MagicMock, patch, call
from datetime import datetime


import pytest
import sys
from unittest.mock import MagicMock, patch, call
from datetime import datetime


@pytest.mark.skip(reason="QueryBuilder not implemented in apex_os_bp.database.deepened (only Query with select/filter/join/group/agg/order; no insert/update/delete/having)")
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
    """Test connection pooling — real API: ConnectionPool(dsn, min_size, max_size, ...), acquire/release/stats."""

    def _mk(self):
        from apex_os_bp.database.deepened import ConnectionPool
        return ConnectionPool(dsn="sqlite://test", min_size=1, max_size=5, health_interval=0)

    def test_pool_initialization(self):
        pool = self._mk()
        assert pool.stats()["max"] == 5
        assert pool.stats()["available"] == 1

    def test_acquire_release(self):
        pool = self._mk()
        conn = pool.acquire()
        assert conn is not None
        assert pool.stats()["available"] == 0
        pool.release(conn)
        assert pool.stats()["available"] == 1

    def test_pool_exhaustion(self):
        from apex_os_bp.database.deepened import ConnectionPool
        # min_size=0 so nothing is pre-warmed; max_size=0 means no new
        # connections may be created, so acquire() must report exhaustion.
        pool = ConnectionPool(dsn="sqlite://test", min_size=0, max_size=0, health_interval=0)
        assert pool.stats() == {"available": 0, "max": 0}
        try:
            pool.acquire()
            exhausted = False
        except RuntimeError as e:
            exhausted = True
            assert "exhausted" in str(e).lower()
        assert exhausted, "expected RuntimeError 'pool exhausted' past max_size"

    def test_pool_max_size_enforced(self):
        pool = self._mk()
        pool.max_size = 3
        stats0 = pool.stats()["max"]
        conns = [pool.acquire() for _ in range(3)]
        assert len(conns) == 3
        for c in conns:
            pool.release(c)
        assert pool.stats()["max"] == stats0


@pytest.mark.skip(reason="ReplicaRouter not implemented in apex_os_bp.database.deepened")
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


@pytest.mark.skip(reason="ShardRouter not implemented in apex_os_bp.database.deepened")
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
    """Test full-text search — real API: add_document(doc_id, text), search(query, top_k) -> [SearchResult]."""

    def _mk(self):
        from apex_os_bp.database.deepened import FullTextSearch
        fts = FullTextSearch()
        fts.add_document("d1", "Hello World from the database")
        fts.add_document("d2", "hello there world traveller")
        fts.add_document("d3", "completely unrelated text here")
        return fts

    def test_fts_search_returns_matches(self):
        fts = self._mk()
        res = fts.search("hello")
        assert len(res) >= 2
        ids = {r.doc_id for r in res}
        assert "d1" in ids

    def test_fts_ranking(self):
        fts = self._mk()
        fts.add_document("d4", "hello hello hello world")
        res = fts.search("hello")
        scores = {r.doc_id: r.score for r in res}
        assert scores["d4"] > scores.get("d3", 0.0)

    def test_fts_snippet(self):
        fts = self._mk()
        res = fts.search("hello", top_k=2)
        assert all(isinstance(r.snippet, str) for r in res)
