"""Deepened data warehouse: ETL, star schema, marts, SCD, quality."""
from __future__ import annotations
import hashlib, logging, time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")

class StepStatus(Enum):
    PENDING = "pending"; RUNNING = "running"; SUCCESS = "success"; FAILED = "failed"; SKIPPED = "skipped"

@dataclass
class StepResult:
    name: str; status: StepStatus; records_processed: int = 0; error: str | None = None; duration_ms: float = 0.0

class ETLStep(ABC, Generic[T]):
    def __init__(self, name: str) -> None:
        self.name = name; self._next: ETLStep | None = None
    def then(self, step: ETLStep) -> ETLStep:
        self._next = step; return step
    @abstractmethod
    def execute(self, context: dict[str, Any]) -> T: ...
    def run(self, context: dict[str, Any]) -> StepResult:
        start = time.perf_counter()
        try:
            data = self.execute(context); context[self.name] = data
            duration = (time.perf_counter() - start) * 1000
            result = StepResult(self.name, StepStatus.SUCCESS, len(data) if hasattr(data, "__len__") else 0, duration_ms=duration)
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            result = StepResult(self.name, StepStatus.FAILED, error=str(exc), duration_ms=duration)
            logger.error("Step %s failed: %s", self.name, exc)
        if self._next and result.status == StepStatus.SUCCESS:
            nr = self._next.run(context)
            return StepResult(f"{self.name} -> {nr.name}", nr.status, nr.records_processed, nr.error, result.duration_ms + nr.duration_ms)
        return result

class ExtractStep(ETLStep[list[dict]]):
    def __init__(self, name: str, source: Callable[[], list[dict]]) -> None:
        super().__init__(name); self._source = source
    def execute(self, context: dict[str, Any]) -> list[dict]: return self._source()

class TransformStep(ETLStep[list[dict]]):
    def __init__(self, name: str, transform: Callable[[list[dict]], list[dict]]) -> None:
        super().__init__(name); self._transform = transform
    def execute(self, context: dict[str, Any]) -> list[dict]: return self._transform(context[list(context.keys())[-1]])

class LoadStep(ETLStep[dict]):
    def __init__(self, name: str, loader: Callable[[list[dict]], dict]) -> None:
        super().__init__(name); self._loader = loader
    def execute(self, context: dict[str, Any]) -> dict: return self._loader(context[list(context.keys())[-1]])

class ETLPipeline:
    def __init__(self, name: str) -> None:
        self.name = name; self._first: ETLStep | None = None; self._last: ETLStep | None = None
    def add(self, step: ETLStep) -> ETLPipeline:
        if self._first is None: self._first = self._last = step
        else:
            assert self._last is not None; self._last.then(step); self._last = step
        return self
    def run(self, context: dict[str, Any] | None = None) -> list[StepResult]:
        ctx = context or {}; results: list[StepResult] = []; step = self._first
        while step:
            result = step.run(ctx); results.append(result)
            if result.status == StepStatus.FAILED: break
            step = step._next
        return results

@dataclass(frozen=True)
class DimensionKey:
    name: str; data_type: str

@dataclass
class Dimension:
    name: str; attributes: list[str]; key: DimensionKey; records: list[dict[str, Any]] = field(default_factory=list)
    def add(self, record: dict[str, Any]) -> None:
        if self.key.name not in record: raise ValueError(f"Missing key {self.key.name} in {self.name}")
        self.records.append(record)
    def lookup(self, key_value: Any) -> dict[str, Any] | None:
        for rec in self.records:
            if rec[self.key.name] == key_value: return rec
        return None

@dataclass
class Fact:
    name: str; dimensions: list[DimensionKey]; measures: list[str]; records: list[dict[str, Any]] = field(default_factory=list)
    def add(self, record: dict[str, Any]) -> None:
        for dim in self.dimensions:
            if dim.name not in record: raise ValueError(f"Missing FK {dim.name} in {self.name}")
        self.records.append(record)
    def join(self, dimension: Dimension, fk_attr: str) -> list[dict[str, Any]]:
        enriched = []
        for row in self.records:
            dim_row = dimension.lookup(row[fk_attr])
            if dim_row: enriched.append({**row, **{f"{dimension.name}_{k}": v for k, v in dim_row.items()}})
        return enriched

class SCDType2:
    def __init__(self, name: str, natural_key: str, tracked_attrs: list[str]) -> None:
        self.name = name; self.natural_key = natural_key; self.tracked_attrs = tracked_attrs
        self._records: list[dict[str, Any]] = []; self._versions: dict[Any, int] = {}
    def _hash(self, record: dict[str, Any]) -> str:
        payload = "|".join(str(record.get(a, "")) for a in self.tracked_attrs)
        return hashlib.sha256(payload.encode()).hexdigest()[:12]
    def apply(self, incoming: dict[str, Any], effective_date: datetime | None = None) -> dict[str, Any]:
        nk = incoming[self.natural_key]; now = effective_date or datetime.now(timezone.utc)
        current = self.get_current(nk)
        if current is None: version = 1
        elif self._hash(current) == self._hash(incoming): return current
        else:
            version = self._versions.get(nk, 1) + 1
            current["expired_date"] = now; current["is_current"] = False
        new_record = {**incoming, "scd_version": version, "effective_date": now,
                      "expired_date": None, "is_current": True, "row_hash": self._hash(incoming)}
        self._records.append(new_record); self._versions[nk] = version
        return new_record
    def get_current(self, nk_val: Any) -> dict[str, Any] | None:
        for rec in reversed(self._records):
            if rec[self.natural_key] == nk_val and rec.get("is_current"): return rec
        return None
    def get_history(self, nk_val: Any) -> list[dict[str, Any]]:
        return [r for r in self._records if r[self.natural_key] == nk_val]

@dataclass
class DataMart:
    name: str; source_fact: Fact; dimensions: list[str]
    measures: dict[str, Callable[[list[dict]], Any]]
    _aggregated: dict[tuple, dict[str, Any]] = field(default_factory=dict)
    def build(self) -> dict[tuple, dict[str, Any]]:
        buckets: dict[tuple, list[dict]] = {}
        for row in self.source_fact.records:
            key = tuple(row.get(d) for d in self.dimensions); buckets.setdefault(key, []).append(row)
        self._aggregated = {}
        for key, rows in buckets.items():
            entry: dict[str, Any] = dict(zip(self.dimensions, key, strict=True))
            for m_name, agg in self.measures.items(): entry[m_name] = agg(rows)
            self._aggregated[key] = entry
        return self._aggregated
    def query(self, **filters: Any) -> list[dict[str, Any]]:
        return [e for e in self._aggregated.values() if all(e.get(d) == v for d, v in filters.items())]

class Severity(Enum):
    INFO = "info"; WARNING = "warning"; ERROR = "error"; CRITICAL = "critical"

@dataclass
class QualityRule:
    name: str; check: Callable[[dict[str, Any]], bool]; severity: Severity; description: str = ""

@dataclass
class QualityReport:
    rule_name: str; severity: Severity; passed: int; failed: int
    failed_records: list[dict[str, Any]] = field(default_factory=list)

class DataQualityEngine:
    def __init__(self) -> None: self._rules: list[QualityRule] = []
    def add_rule(self, rule: QualityRule) -> DataQualityEngine:
        self._rules.append(rule); return self
    def validate(self, records: list[dict[str, Any]]) -> list[QualityReport]:
        reports = []
        for rule in self._rules:
            passed, failed = 0, []
            for rec in records:
                if rule.check(rec): passed += 1
                else: failed.append(rec)
            reports.append(QualityReport(rule.name, rule.severity, passed, len(failed), failed))
        return reports
    def is_clean(self, records: list[dict[str, Any]]) -> bool:
        return all(r.failed == 0 for r in self.validate(records))

def not_null(*fields: str) -> QualityRule:
    return QualityRule(f"not_null_{'_'.join(fields)}", lambda rec: all(rec.get(f) is not None for f in fields), Severity.ERROR)

def unique(field: str) -> QualityRule:
    seen: set = set()
    def _check(rec: dict[str, Any]) -> bool:
        val = rec.get(field)
        if val in seen: return False
        seen.add(val); return True
    return QualityRule(f"unique_{field}", _check, Severity.CRITICAL)

def range_check(field: str, low: float, high: float) -> QualityRule:
    return QualityRule(f"range_{field}", lambda rec: low <= rec.get(field, float("inf")) <= high, Severity.WARNING)

def referential_integrity(fk_field: str, dimension: Dimension) -> QualityRule:
    return QualityRule(f"fk_{fk_field}_{dimension.name}", lambda rec: dimension.lookup(rec.get(fk_field)) is not None, Severity.ERROR)
