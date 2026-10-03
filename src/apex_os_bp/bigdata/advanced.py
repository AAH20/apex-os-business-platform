"""Big Data advanced features: partitioning, compression, indexing, query optimization, lifecycle."""
from __future__ import annotations
import gzip, hashlib, lzma, zlib
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional


# ── 1. Data Partitioning ─────────────────────────────────────────────────────
class PartitionStrategy(Enum):
    HASH = "hash"; RANGE = "range"; LIST = "list"; ROUND_ROBIN = "round_robin"

class Partitioner:
    def __init__(self, n: int, strategy: PartitionStrategy = PartitionStrategy.HASH):
        self.n, self.strategy, self._rr = n, strategy, 0
        self._list_map: dict[Any, int] = {}
        self._ranges: list[tuple[Any, Any]] = []
    def set_list_mapping(self, m: dict[Any, int]) -> None: self._list_map = m
    def set_range_boundaries(self, b: list[tuple[Any, Any]]) -> None: self._ranges = sorted(b, key=lambda x: x[0])
    def partition(self, key: Any) -> int:
        if self.strategy == PartitionStrategy.HASH:
            return int(hashlib.md5(str(key).encode()).hexdigest(), 16) % self.n
        if self.strategy == PartitionStrategy.ROUND_ROBIN:
            p, self._rr = self._rr % self.n, self._rr + 1
            return p
        if self.strategy == PartitionStrategy.LIST:
            return self._list_map.get(key, 0)
        for i, (lo, hi) in enumerate(self._ranges):
            if lo <= key < hi: return i
        return self.n - 1
    def partition_many(self, items: Iterable[tuple[Any, Any]]) -> dict[int, list[Any]]:
        b: dict[int, list[Any]] = defaultdict(list)
        for k, v in items: b[self.partition(k)].append(v)
        return dict(b)


# ── 2. Compression ───────────────────────────────────────────────────────────
class CompressionAlgorithm(Enum):
    NONE = "none"; GZIP = "gzip"; ZLIB = "zlib"; LZMA = "lzma"

class Compressor:
    def __init__(self, algo: CompressionAlgorithm = CompressionAlgorithm.GZIP): self.algo = algo
    def compress(self, data: bytes) -> bytes:
        if self.algo == CompressionAlgorithm.NONE: return data
        if self.algo == CompressionAlgorithm.GZIP: return gzip.compress(data, 6)
        if self.algo == CompressionAlgorithm.ZLIB: return zlib.compress(data, 6)
        return lzma.compress(data, preset=6)
    def decompress(self, data: bytes) -> bytes:
        if self.algo == CompressionAlgorithm.NONE: return data
        if self.algo == CompressionAlgorithm.GZIP: return gzip.decompress(data)
        if self.algo == CompressionAlgorithm.ZLIB: return zlib.decompress(data)
        return lzma.decompress(data)
    def ratio(self, original: bytes) -> float:
        return len(self.compress(original)) / max(len(original), 1)


# ── 3. Indexing ──────────────────────────────────────────────────────────────
class BTreeIndex:
    def __init__(self, order: int = 4): self.order, self._keys, self._vals = order, [], []
    def _pos(self, key: Any) -> int:
        lo, hi = 0, len(self._keys)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._keys[mid] < key: lo = mid + 1
            else: hi = mid
        return lo
    def insert(self, key: Any, row_id: int) -> None:
        i = self._pos(key)
        if i < len(self._keys) and self._keys[i] == key: self._vals[i].append(row_id)
        else: self._keys.insert(i, key); self._vals.insert(i, [row_id])
    def exact_match(self, key: Any) -> list[int]:
        i = self._pos(key)
        return list(self._vals[i]) if i < len(self._keys) and self._keys[i] == key else []
    def range_query(self, lo: Any, hi: Any) -> list[int]:
        return [rid for i, k in enumerate(self._keys) if lo <= k <= hi for rid in self._vals[i]]

class HashIndex:
    def __init__(self): self._m: dict[Any, list[int]] = defaultdict(list)
    def insert(self, key: Any, row_id: int) -> None: self._m[key].append(row_id)
    def lookup(self, key: Any) -> list[int]: return list(self._m.get(key, []))
    def delete(self, key: Any, row_id: int) -> None:
        if key in self._m and row_id in self._m[key]: self._m[key].remove(row_id)

class InvertedIndex:
    def __init__(self): self._idx: dict[str, set[int]] = defaultdict(set)
    def add_document(self, doc_id: int, text: str) -> None:
        for t in text.lower().split(): self._idx[t].add(doc_id)
    def search(self, term: str) -> set[int]: return set(self._idx.get(term.lower(), set()))
    def search_and(self, *terms: str) -> set[int]:
        sets = [self.search(t) for t in terms]
        return set.intersection(*sets) if sets else set()


# ── 4. Query Optimization ────────────────────────────────────────────────────
@dataclass
class QueryPlan:
    operation: str
    estimated_cost: float
    index_used: Optional[str] = None
    filters: list[str] = field(default_factory=list)

class QueryOptimizer:
    def __init__(self): self._indexes: dict[str, Any] = {}; self._stats: dict[str, int] = {}
    def register_index(self, col: str, idx: Any) -> None: self._indexes[col] = idx
    def register_stats(self, table: str, rows: int) -> None: self._stats[table] = rows
    def optimize(self, table: str, filters: list[tuple[str, str, Any]]) -> QueryPlan:
        best_col, best_cost = None, float("inf")
        for col, op, _ in filters:
            if col not in self._indexes: continue
            idx = self._indexes[col]
            cost = 1.0 if isinstance(idx, HashIndex) and op == "=" else (
                self._stats.get(table, 1000) * 0.1 if isinstance(idx, BTreeIndex) and op in (">", "<", ">=", "<=") else float("inf"))
            if cost < best_cost: best_col, best_cost = col, cost
        if best_col is None: best_cost = float(self._stats.get(table, 1000))
        return QueryPlan("scan" if best_col is None else "index_scan", best_cost, best_col,
                         [f"{c} {o} {v}" for c, o, v in filters])
    def join_order(self, tables: list[str]) -> list[str]:
        return sorted(tables, key=lambda t: self._stats.get(t, 0))


# ── 5. Data Lifecycle Management ─────────────────────────────────────────────
class LifecycleStage(Enum):
    HOT = "hot"; WARM = "warm"; COLD = "cold"; ARCHIVE = "archive"; DELETE = "delete"

@dataclass
class LifecycleRule:
    stage: LifecycleStage
    max_age_days: int
    compression: CompressionAlgorithm = CompressionAlgorithm.GZIP
    move_to: Optional[LifecycleStage] = None

class LifecycleManager:
    def __init__(self): self._rules: dict[LifecycleStage, LifecycleRule] = {}; self._data: dict[str, tuple[LifecycleStage, int]] = {}
    def add_rule(self, rule: LifecycleRule) -> None: self._rules[rule.stage] = rule
    def register(self, did: str, stage: LifecycleStage = LifecycleStage.HOT, age: int = 0) -> None: self._data[did] = (stage, age)
    def age_all(self, days: int = 1) -> None:
        for did in self._data: s, a = self._data[did]; self._data[did] = (s, a + days)
    def evaluate(self) -> list[tuple[str, LifecycleStage, Optional[LifecycleStage]]]:
        return [(did, s, self._rules[s].move_to) for did, (s, a) in self._data.items()
                if s in self._rules and self._rules[s].move_to and a >= self._rules[s].max_age_days]
    def apply_transitions(self) -> list[str]:
        done = []
        for did, _, nxt in self.evaluate():
            _, age = self._data[did]; self._data[did] = (nxt, age); done.append(did)
        return done
    def get_stage(self, did: str) -> Optional[LifecycleStage]:
        return self._data.get(did, (None,))[0]
