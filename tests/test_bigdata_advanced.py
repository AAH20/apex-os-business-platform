"""Tests for bigdata/advanced.py."""

import pytest
from apex_os_bp.bigdata.advanced import (
    BTreeIndex,
    Compressor,
    CompressionAlgorithm,
    HashIndex,
    InvertedIndex,
    LifecycleManager,
    LifecycleRule,
    LifecycleStage,
    Partitioner,
    PartitionStrategy,
    QueryOptimizer,
)


# ── Partitioning ─────────────────────────────────────────────────────────────

class TestPartitioner:
    def test_hash_deterministic(self):
        p = Partitioner(4, PartitionStrategy.HASH)
        assert p.partition("foo") == p.partition("foo")

    def test_hash_within_range(self):
        p = Partitioner(8, PartitionStrategy.HASH)
        for i in range(100):
            assert 0 <= p.partition(i) < 8

    def test_round_robin_cycles(self):
        p = Partitioner(3, PartitionStrategy.ROUND_ROBIN)
        results = [p.partition(None) for _ in range(6)]
        assert results == [0, 1, 2, 0, 1, 2]

    def test_list_mapping(self):
        p = Partitioner(3, PartitionStrategy.LIST)
        p.set_list_mapping({"a": 0, "b": 1, "c": 2})
        assert p.partition("a") == 0
        assert p.partition("b") == 1
        assert p.partition("unknown") == 0

    def test_range_boundaries(self):
        p = Partitioner(3, PartitionStrategy.RANGE)
        p.set_range_boundaries([(0, 10), (10, 20), (20, 30)])
        assert p.partition(5) == 0
        assert p.partition(15) == 1
        assert p.partition(25) == 2
        assert p.partition(99) == 2

    def test_partition_many(self):
        p = Partitioner(2, PartitionStrategy.HASH)
        items = [("k1", "v1"), ("k2", "v2"), ("k3", "v3")]
        buckets = p.partition_many(items)
        assert sum(len(v) for v in buckets.values()) == 3


# ── Compression ──────────────────────────────────────────────────────────────

class TestCompressor:
    @pytest.mark.parametrize("algo", [CompressionAlgorithm.GZIP, CompressionAlgorithm.ZLIB, CompressionAlgorithm.LZMA])
    def test_round_trip(self, algo):
        c = Compressor(algo)
        data = b"hello world " * 100
        assert c.decompress(c.compress(data)) == data

    def test_none_passthrough(self):
        c = Compressor(CompressionAlgorithm.NONE)
        data = b"raw data"
        assert c.compress(data) == data
        assert c.decompress(data) == data

    def test_ratio_less_than_one(self):
        c = Compressor(CompressionAlgorithm.GZIP)
        data = b"aaaaaaaaaa" * 1000
        assert c.ratio(data) < 1.0


# ── Indexing ─────────────────────────────────────────────────────────────────

class TestBTreeIndex:
    def test_insert_and_exact(self):
        idx = BTreeIndex()
        idx.insert(10, 0)
        idx.insert(5, 1)
        idx.insert(10, 2)
        assert sorted(idx.exact_match(10)) == [0, 2]
        assert idx.exact_match(5) == [1]
        assert idx.exact_match(99) == []

    def test_range_query(self):
        idx = BTreeIndex()
        for i in range(20):
            idx.insert(i, i)
        assert sorted(idx.range_query(5, 10)) == [5, 6, 7, 8, 9, 10]


class TestHashIndex:
    def test_lookup(self):
        idx = HashIndex()
        idx.insert("a", 1)
        idx.insert("a", 2)
        idx.insert("b", 3)
        assert sorted(idx.lookup("a")) == [1, 2]
        assert idx.lookup("b") == [3]
        assert idx.lookup("z") == []

    def test_delete(self):
        idx = HashIndex()
        idx.insert("k", 1)
        idx.delete("k", 1)
        assert idx.lookup("k") == []


class TestInvertedIndex:
    def test_search(self):
        idx = InvertedIndex()
        idx.add_document(1, "hello world")
        idx.add_document(2, "world peace")
        assert idx.search("hello") == {1}
        assert idx.search("world") == {1, 2}

    def test_search_and(self):
        idx = InvertedIndex()
        idx.add_document(1, "quick brown fox")
        idx.add_document(2, "quick brown dog")
        idx.add_document(3, "lazy dog")
        assert idx.search_and("quick", "brown") == {1, 2}
        assert idx.search_and("quick", "dog") == set()


# ── Query Optimization ───────────────────────────────────────────────────────

class TestQueryOptimizer:
    def test_selects_hash_index(self):
        opt = QueryOptimizer()
        opt.register_index("id", HashIndex())
        opt.register_stats("users", 10000)
        plan = opt.optimize("users", [("id", "=", 42)])
        assert plan.operation == "index_scan"
        assert plan.index_used == "id"
        assert plan.estimated_cost == 1.0

    def test_selects_btree_for_range(self):
        opt = QueryOptimizer()
        opt.register_index("age", BTreeIndex())
        opt.register_stats("users", 10000)
        plan = opt.optimize("users", [("age", ">", 30)])
        assert plan.index_used == "age"
        assert plan.estimated_cost < 10000

    def test_full_scan_when_no_index(self):
        opt = QueryOptimizer()
        opt.register_stats("logs", 5000)
        plan = opt.optimize("logs", [("msg", "like", "%error%")])
        assert plan.operation == "scan"
        assert plan.estimated_cost == 5000

    def test_join_order_smallest_first(self):
        opt = QueryOptimizer()
        opt.register_stats("a", 1000)
        opt.register_stats("b", 10)
        opt.register_stats("c", 100)
        assert opt.join_order(["a", "b", "c"]) == ["b", "c", "a"]


# ── Lifecycle Management ─────────────────────────────────────────────────────

class TestLifecycleManager:
    def test_register_and_age(self):
        lm = LifecycleManager()
        lm.register("d1", LifecycleStage.HOT, age_days=0)
        lm.age_all(5)
        assert lm.get_stage("d1") == LifecycleStage.HOT

    def test_transition_on_age(self):
        lm = LifecycleManager()
        lm.add_rule(LifecycleRule(LifecycleStage.HOT, max_age_days=7, move_to=LifecycleStage.COLD))
        lm.register("d1", LifecycleStage.HOT, age_days=10)
        transitions = lm.evaluate()
        assert len(transitions) == 1
        assert transitions[0][2] == LifecycleStage.COLD

    def test_apply_transitions(self):
        lm = LifecycleManager()
        lm.add_rule(LifecycleRule(LifecycleStage.HOT, max_age_days=7, move_to=LifecycleStage.COLD))
        lm.register("d1", LifecycleStage.HOT, age_days=10)
        result = lm.apply_transitions()
        assert result == ["d1"]
        assert lm.get_stage("d1") == LifecycleStage.COLD

    def test_no_transition_when_young(self):
        lm = LifecycleManager()
        lm.add_rule(LifecycleRule(LifecycleStage.HOT, max_age_days=30, move_to=LifecycleStage.COLD))
        lm.register("d1", LifecycleStage.HOT, age_days=5)
        assert lm.evaluate() == []
