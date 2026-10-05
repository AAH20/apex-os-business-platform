"""Big Data advanced features: partitioning, compression, indexing, query optimization, lifecycle."""
from __future__ import annotations
import gzip, hashlib, lzma, time, zlib
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, Iterable, Iterator, Optional, TypeVar

# Payload type for the generic streaming/ETL containers below (StreamIngestor,
# ETLPipeline, DataRecord). Declared here so the Generic[T] subscripting below
# type-checks; without it the module raised NameError on import.
T = TypeVar("T")


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
                self._stats.get(
                    table,
                    1000
                ) * 0.1 if isinstance(idx, BTreeIndex) and op in (">", "<", ">=", "<=") else float("inf"))
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
    def __init__(self): self._rules: dict[LifecycleStage, LifecycleRule] = {
                 }; self._data: dict[str, tuple[LifecycleStage, int]] = {}
    def add_rule(self, rule: LifecycleRule) -> None: self._rules[rule.stage] = rule
    def register(self, did: str, stage: LifecycleStage = LifecycleStage.HOT,
                 age: int = 0) -> None: self._data[did] = (stage, age)
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


# ── 6. Data Ingestion with Streaming ─────────────────────────────────────────
class IngestionError(Exception): """Raised when data ingestion fails."""


class StreamIngestor(Generic[T]):
    """Streaming data ingestion with buffering and retry logic."""
    def __init__(self, buffer_size: int = 1000, max_retries: int = 3) -> None:
        self.buffer_size, self.max_retries = buffer_size, max_retries
        self._buffer: list[DataRecord[T]] = []
        self._ingested, self._failed = 0, 0
    def ingest(self, source: Iterator[T], source_name: str) -> Iterator[DataRecord[T]]:
        for item in source:
            for attempt in range(self.max_retries):
                try:
                    record = DataRecord(data=item, source=source_name)
                    self._buffer.append(record); self._ingested += 1
                    if len(self._buffer) >= self.buffer_size: yield from self._flush()
                    yield record; break
                except Exception as exc:
                    if attempt == self.max_retries - 1:
                        self._failed += 1; raise IngestionError(f"Failed: {source_name}") from exc
                    time.sleep(0.1 * (attempt + 1))
    def _flush(self) -> Iterator[DataRecord[T]]:
        yield from self._buffer; self._buffer.clear()
    @property
    def stats(self) -> dict[str, int]:
        return {"ingested": self._ingested, "failed": self._failed, "buffered": len(self._buffer)}


# ── 7. Data Transformation with ETL ───────────────────────────────────────────
class ETLPipeline(Generic[T]):
    """Composable ETL pipeline with transforms, filters, and a loader sink."""
    def __init__(self) -> None:
        self._transforms: list[Callable[[T], T]] = []
        self._filters: list[Callable[[T], bool]] = []
        self._loader: Optional[Callable[[DataRecord[T]], None]] = None
    def add_transform(self, fn: Callable[[T], T]) -> ETLPipeline[T]: self._transforms.append(fn); return self
    def add_filter(self, fn: Callable[[T], bool]) -> ETLPipeline[T]: self._filters.append(fn); return self
    def set_loader(self, fn: Callable[[DataRecord[T]], None]) -> ETLPipeline[T]: self._loader = fn; return self
    def process(self, record: DataRecord[T]) -> Optional[DataRecord[T]]:
        try:
            data = record.data
            for pred in self._filters:
                if not pred(data): record.mark(RecordStatus.REJECTED, "filtered"); return record
            for tr in self._transforms: data = tr(data)
            record.data = data; record.mark(RecordStatus.TRANSFORMED, "etl_complete")
            if self._loader: self._loader(record)
            return record
        except Exception as exc:
            record.mark(RecordStatus.REJECTED, f"etl_error: {exc}"); return record


# ── 8. Data Quality Validation ────────────────────────────────────────────────
@dataclass
class QualityRule:
    name: str; check: Callable[[Any], bool]; severity: str = "error"; description: str = ""


class QualityValidator:
    """Configurable data quality validation with severity-aware rules."""
    def __init__(self) -> None: self._rules: list[QualityRule] = []
    def add_rule(self, rule: QualityRule) -> QualityValidator: self._rules.append(rule); return self
    def validate(self, record: DataRecord[T]) -> tuple[bool, list[str]]:
        violations: list[str] = []
        for rule in self._rules:
            try:
                if not rule.check(record.data): violations.append(f"{rule.name}: {rule.description}")
            except Exception as exc: violations.append(f"{rule.name}: raised {exc}")
        passed = not any(r.severity == "error" for r in self._rules
                         if any(v.startswith(r.name) for v in violations))
        record.mark(RecordStatus.VALIDATED if passed else RecordStatus.REJECTED, "quality")
        return passed, violations


# ── 9. Data Lineage Tracking ──────────────────────────────────────────────────
@dataclass
class LineageNode:
    node_id: str; operation: str; inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list); timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class LineageTracker:
    """DAG-based data lineage tracking with upstream/downstream traversal."""
    def __init__(self) -> None:
        self._nodes: dict[str, LineageNode] = {}; self._edges: dict[str, list[str]] = {}
    def record_operation(self, operation: str, input_ids: list[str], output_ids: list[str],
                          metadata: Optional[dict[str, Any]] = None) -> LineageNode:
        nid = hashlib.sha256(f"{operation}:{time.time()}:{','.join(input_ids)}".encode()).hexdigest()[:16]
        node = LineageNode(nid, operation, input_ids, output_ids, metadata=metadata or {})
        self._nodes[nid] = node
        for inp in input_ids: self._edges.setdefault(inp, []).append(nid)
        return node
    def get_upstream(self, record_id: str) -> list[LineageNode]:
        visited: set[str] = set(); result: list[LineageNode] = []; stack = [record_id]
        while stack:
            cur = stack.pop()
            for node in self._nodes.values():
                if cur in node.outputs and node.node_id not in visited:
                    visited.add(node.node_id); result.append(node); stack.extend(node.inputs)
        return result
    def get_downstream(self, record_id: str) -> list[LineageNode]:
        visited: set[str] = set(); result: list[LineageNode] = []; stack = [record_id]
        while stack:
            cur = stack.pop()
            for nid in self._edges.get(cur, []):
                if nid not in visited:
                    visited.add(nid); node = self._nodes[nid]; result.append(node); stack.extend(node.outputs)
        return result


# ── 10. Data Catalog Management ───────────────────────────────────────────────
class CatalogError(Exception): """Raised when catalog operations fail."""


@dataclass
class CatalogEntry:
    name: str; schema: dict[str, str]; location: str; format: str; owner: str
    created_at: float = field(default_factory=time.time); updated_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list); description: str = ""
    row_count: int = 0; column_count: int = 0


class DataCatalog:
    """Data catalog for discoverability, governance, and metadata management."""
    def __init__(self) -> None: self._entries: dict[str, CatalogEntry] = {}
    def register(self, entry: CatalogEntry) -> None:
        if entry.name in self._entries: raise CatalogError(f"'{entry.name}' exists")
        self._entries[entry.name] = entry
    def update(self, name: str, **kwargs: Any) -> CatalogEntry:
        if name not in self._entries: raise CatalogError(f"'{name}' not found")
        entry = self._entries[name]
        for k, v in kwargs.items():
            if hasattr(entry, k): setattr(entry, k, v)
        entry.updated_at = time.time(); return entry
    def get(self, name: str) -> CatalogEntry:
        if name not in self._entries: raise CatalogError(f"'{name}' not found")
        return self._entries[name]
    def search(self, tag: Optional[str] = None, owner: Optional[str] = None) -> list[CatalogEntry]:
        r = list(self._entries.values())
        if tag: r = [e for e in r if tag in e.tags]
        if owner: r = [e for e in r if e.owner == owner]
        return r
    def remove(self, name: str) -> None:
        if name not in self._entries: raise CatalogError(f"'{name}' not found")
        del self._entries[name]
    def list_all(self) -> list[CatalogEntry]: return list(self._entries.values())
