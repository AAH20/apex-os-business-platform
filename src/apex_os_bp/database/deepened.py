"""Deepened database module: query builder, pooling, replicas, sharding, FTS."""
from __future__ import annotations

import hashlib
import heapq
import random
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── 1. Query Builder ────────────────────────────────────────────────────────

@dataclass
class Query:
    table: str
    columns: List[str] = field(default_factory=lambda: ["*"])
    where: List[Tuple[str, str, Any]] = field(default_factory=list)
    joins: List[Tuple[str, str, str, str]] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    aggregates: List[Tuple[str, str, str]] = field(default_factory=list)
    order_by: List[Tuple[str, str]] = field(default_factory=list)
    limit: Optional[int] = None
    offset: int = 0

    def select(self, *cols: str) -> "Query":
        self.columns = list(cols) if cols else ["*"]
        return self

    def filter(self, col: str, op: str, val: Any) -> "Query":
        self.where.append((col, op, val))
        return self

    def join(self, table: str, left: str, right: str, kind: str = "INNER") -> "Query":
        self.joins.append((table, kind, left, right))
        return self

    def group(self, *cols: str) -> "Query":
        self.group_by = list(cols)
        return self

    def agg(self, func: str, col: str, alias: str) -> "Query":
        self.aggregates.append((func.upper(), col, alias))
        return self

    def order(self, col: str, direction: str = "ASC") -> "Query":
        self.order_by.append((col, direction.upper()))
        return self

    def to_sql(self) -> Tuple[str, List[Any]]:
        params: List[Any] = []
        cols = ", ".join(self.columns)
        sql = f"SELECT {cols} FROM {self.table}"
        for table, kind, left, right in self.joins:
            sql += f" {kind} JOIN {table} ON {left} = {right}"
        if self.where:
            clauses = []
            for col, op, val in self.where:
                clauses.append(f"{col} {op} ?")
                params.append(val)
            sql += " WHERE " + " AND ".join(clauses)
        if self.group_by:
            sql += " GROUP BY " + ", ".join(self.group_by)
        if self.aggregates:
            agg_sql = ", ".join(f"{f}({c}) AS {a}" for f, c, a in self.aggregates)
            sql = sql.replace("SELECT *", f"SELECT {agg_sql}")
        if self.order_by:
            sql += " ORDER BY " + ", ".join(f"{c} {d}" for c, d in self.order_by)
        if self.limit is not None:
            sql += f" LIMIT {self.limit} OFFSET {self.offset}"
        return sql, params


# ── 2. Connection Pool with Health Checks ───────────────────────────────────

class Connection:
    def __init__(self, conn_id: str):
        self.conn_id = conn_id
        self.created_at = time.time()
        self.last_used = time.time()
        self._healthy = True

    def execute(self, sql: str, params: List[Any] = None) -> List[Dict]:
        self.last_used = time.time()
        return []

    def ping(self) -> bool:
        self._healthy = True
        return self._healthy

    def close(self) -> None:
        self._healthy = False


class ConnectionPool:
    def __init__(self, dsn: str, min_size: int = 2, max_size: int = 10,
                 max_idle: float = 300.0, health_interval: float = 30.0):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle = max_idle
        self._pool: List[Connection] = []
        self._lock = threading.Lock()
        self._health_interval = health_interval
        self._last_health_check = 0.0
        for _ in range(min_size):
            self._pool.append(self._create())

    def _create(self) -> Connection:
        return Connection(f"conn_{threading.get_ident()}_{len(self._pool)}")

    def acquire(self) -> Connection:
        with self._lock:
            self._health_check()
            if self._pool:
                return self._pool.pop()
            if len(self._pool) < self.max_size:
                return self._create()
            raise RuntimeError("Connection pool exhausted")

    def release(self, conn: Connection) -> None:
        with self._lock:
            if conn._healthy and len(self._pool) < self.max_size:
                self._pool.append(conn)
            else:
                conn.close()

    def _health_check(self) -> None:
        now = time.time()
        if now - self._last_health_check < self._health_interval:
            return
        self._last_health_check = now
        healthy = []
        for conn in self._pool:
            if conn.ping() and now - conn.last_used < self.max_idle:
                healthy.append(conn)
            else:
                conn.close()
        self._pool = healthy
        while len(self._pool) < self.min_size:
            self._pool.append(self._create())

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {"available": len(self._pool), "max": self.max_size}


# ── 3. Read Replicas with Load Balancing ────────────────────────────────────

class ReadRouter:
    def __init__(self, replicas: List[ConnectionPool], strategy: str = "round_robin"):
        self.replicas = replicas
        self.strategy = strategy
        self._rr_index = 0
        self._lock = threading.Lock()

    def _round_robin(self) -> ConnectionPool:
        with self._lock:
            pool = self.replicas[self._rr_index % len(self.replicas)]
            self._rr_index += 1
            return pool

    def _least_connections(self) -> ConnectionPool:
        return min(self.replicas, key=lambda p: p.stats()["max"] - p.stats()["available"])

    def _random(self) -> ConnectionPool:
        return random.choice(self.replicas)

    def get_pool(self) -> ConnectionPool:
        if self.strategy == "least_connections":
            return self._least_connections()
        if self.strategy == "random":
            return self._random()
        return self._round_robin()

    def execute_read(self, sql: str, params: List[Any] = None) -> List[Dict]:
        pool = self.get_pool()
        conn = pool.acquire()
        try:
            return conn.execute(sql, params)
        finally:
            pool.release(conn)


# ── 4. Sharding with Consistent Hashing ─────────────────────────────────────

class ConsistentHashRing:
    def __init__(self, replicas: int = 150):
        self.replicas = replicas
        self._ring: Dict[int, str] = {}
        self._nodes: set = set()
        self._sorted_keys: List[int] = []

    def add_node(self, node: str) -> None:
        self._nodes.add(node)
        for i in range(self.replicas):
            key = self._hash(f"{node}:{i}")
            self._ring[key] = node
        self._sorted_keys = sorted(self._ring.keys())

    def remove_node(self, node: str) -> None:
        self._nodes.discard(node)
        for i in range(self.replicas):
            key = self._hash(f"{node}:{i}")
            self._ring.pop(key, None)
        self._sorted_keys = sorted(self._ring.keys())

    def get_node(self, key: str) -> Optional[str]:
        if not self._ring:
            return None
        h = self._hash(key)
        idx = self._bisect_right(self._sorted_keys, h)
        if idx == len(self._sorted_keys):
            idx = 0
        return self._ring[self._sorted_keys[idx]]

    @staticmethod
    def _hash(key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    @staticmethod
    def _bisect_right(a: List[int], x: int) -> int:
        lo, hi = 0, len(a)
        while lo < hi:
            mid = (lo + hi) // 2
            if x < a[mid]:
                hi = mid
            else:
                lo = mid + 1
        return lo


class ShardManager:
    def __init__(self, shard_pools: Dict[str, ConnectionPool], virtual_nodes: int = 150):
        self.pools = shard_pools
        self.ring = ConsistentHashRing(virtual_nodes)
        for node in shard_pools:
            self.ring.add_node(node)

    def shard_key(self, table: str, key: Any) -> str:
        return f"{table}:{key}"

    def get_pool(self, table: str, key: Any) -> ConnectionPool:
        node = self.ring.get_node(self.shard_key(table, key))
        if node is None:
            raise RuntimeError("No shards available")
        return self.pools[node]

    def execute(self, table: str, key: Any, sql: str, params: List[Any] = None) -> List[Dict]:
        pool = self.get_pool(table, key)
        conn = pool.acquire()
        try:
            return conn.execute(sql, params)
        finally:
            pool.release(conn)


# ── 5. Full-Text Search with Ranking ────────────────────────────────────────

@dataclass
class SearchResult:
    doc_id: str
    score: float
    snippet: str = ""


class FullTextSearch:
    def __init__(self):
        self._index: Dict[str, Dict[str, int]] = defaultdict(dict)  # term -> {doc_id: freq}
        self._doc_len: Dict[str, int] = {}
        self._doc_count = 0

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def add_document(self, doc_id: str, text: str) -> None:
        tokens = self._tokenize(text)
        self._doc_len[doc_id] = len(tokens)
        self._doc_count += 1
        for tok in tokens:
            self._index[tok][doc_id] = self._index[tok].get(doc_id, 0) + 1

    def remove_document(self, doc_id: str) -> None:
        if doc_id not in self._doc_len:
            return
        for term in list(self._index.keys()):
            self._index[term].pop(doc_id, None)
            if not self._index[term]:
                del self._index[term]
        del self._doc_len[doc_id]
        self._doc_count -= 1

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        terms = self._tokenize(query)
        if not terms:
            return []
        scores: Dict[str, float] = defaultdict(float)
        avg_len = sum(self._doc_len.values()) / max(len(self._doc_len), 1)
        k1, b = 1.5, 0.75
        for term in terms:
            postings = self._index.get(term, {})
            if not postings:
                continue
            idf = max(0.0, (self._doc_count - len(postings) + 0.5) / (len(postings) + 0.5))
            for doc_id, tf in postings.items():
                doc_len = self._doc_len.get(doc_id, 1)
                norm = tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / avg_len))
                scores[doc_id] += idf * norm
        ranked = heapq.nlargest(top_k, scores.items(), key=lambda x: x[1])
        return [SearchResult(doc_id=d, score=s) for d, s in ranked]
