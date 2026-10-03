"""Deepened event sourcing: store, replay, versioning, projections, sagas."""
from __future__ import annotations
import copy, json, time, uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

# ─── Event Store (append-only log) ───────────────────────────────────────────

@dataclass(frozen=True)
class Event:
    """Immutable domain event."""
    event_id: str
    aggregate_id: str
    event_type: str
    version: int
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class EventStore:
    """Append-only event log with optional file persistence."""
    def __init__(self, storage_path: Optional[Path] = None):
        self._events: List[Event] = []
        self._index: Dict[str, List[int]] = {}
        self._storage_path = storage_path
        if storage_path and storage_path.exists():
            self._load()

    def append(self, event: Event) -> None:
        existing = self._index.get(event.aggregate_id, [])
        if existing:
            last = self._events[existing[-1]]
            if last.version >= event.version:
                raise ValueError(f"Version conflict: {event.aggregate_id} expected > {last.version}, got {event.version}")
        idx = len(self._events)
        self._events.append(event)
        self._index.setdefault(event.aggregate_id, []).append(idx)
        self._persist()

    def get_events(self, aggregate_id: str, after_version: int = 0) -> List[Event]:
        return [self._events[i] for i in self._index.get(aggregate_id, []) if self._events[i].version > after_version]

    def all_events(self) -> List[Event]:
        return list(self._events)

    def _persist(self) -> None:
        if not self._storage_path: return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._storage_path, "w") as f:
            for e in self._events:
                f.write(json.dumps({"event_id": e.event_id, "aggregate_id": e.aggregate_id,
                    "event_type": e.event_type, "version": e.version, "payload": e.payload,
                    "timestamp": e.timestamp, "metadata": e.metadata}) + "\n")

    def _load(self) -> None:
        with open(self._storage_path) as f:
            for line in f:
                event = Event(**json.loads(line))
                idx = len(self._events)
                self._events.append(event)
                self._index.setdefault(event.aggregate_id, []).append(idx)

# ─── Event Replay with Snapshotting ──────────────────────────────────────────

@dataclass
class Snapshot:
    aggregate_id: str
    state: Dict[str, Any]
    version: int
    timestamp: float = field(default_factory=time.time)

class SnapshotStore:
    """Stores and retrieves aggregate snapshots."""
    def __init__(self, path: Optional[Path] = None):
        self._snapshots: Dict[str, Snapshot] = {}
        self._path = path
        if path and path.exists(): self._load()

    def save(self, snapshot: Snapshot) -> None:
        self._snapshots[snapshot.aggregate_id] = snapshot
        self._persist()

    def get(self, aggregate_id: str) -> Optional[Snapshot]:
        return self._snapshots.get(aggregate_id)

    def _persist(self) -> None:
        if not self._path: return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            for s in self._snapshots.values():
                f.write(json.dumps({"aggregate_id": s.aggregate_id, "state": s.state,
                    "version": s.version, "timestamp": s.timestamp}) + "\n")

    def _load(self) -> None:
        with open(self._path) as f:
            for line in f:
                snap = Snapshot(**json.loads(line))
                self._snapshots[snap.aggregate_id] = snap

class ReplayEngine:
    """Rebuilds aggregate state from snapshot + events."""
    def __init__(self, event_store: EventStore, snapshot_store: SnapshotStore):
        self._event_store = event_store
        self._snapshot_store = snapshot_store

    def replay(self, aggregate_id: str,
        apply_fn: Callable[[Dict[str, Any], Event], Dict[str, Any]],
        initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        snap = self._snapshot_store.get(aggregate_id)
        if snap:
            state = copy.deepcopy(snap.state)
            after_version = snap.version
        else:
            state = copy.deepcopy(initial_state or {})
            after_version = 0
        for event in self._event_store.get_events(aggregate_id, after_version):
            state = apply_fn(state, event)
        return state

    def maybe_snapshot(self, aggregate_id: str, state: Dict[str, Any],
        version: int, threshold: int = 10) -> None:
        snap = self._snapshot_store.get(aggregate_id)
        if snap is None or version - snap.version >= threshold:
            self._snapshot_store.save(Snapshot(
                aggregate_id=aggregate_id, state=copy.deepcopy(state), version=version))

# ─── Event Versioning with Upcasting ─────────────────────────────────────────

class Upcaster(Protocol):
    source_version: int
    target_version: int
    def upcast(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...

class UpcasterRegistry:
    """Registry and dispatcher for event upcasters."""
    def __init__(self):
        self._upcasters: Dict[str, List[Upcaster]] = {}

    def register(self, event_type: str, upcaster: Upcaster) -> None:
        self._upcasters.setdefault(event_type, []).append(upcaster)

    def upcast(self, event: Event) -> Event:
        upcasters = self._upcasters.get(event.event_type, [])
        if not upcasters: return event
        current = event
        for uc in sorted(upcasters, key=lambda u: u.source_version):
            if current.version == uc.source_version:
                current = Event(event_id=current.event_id, aggregate_id=current.aggregate_id,
                    event_type=current.event_type, version=uc.target_version,
                    payload=uc.upcast(current.payload), timestamp=current.timestamp,
                    metadata=current.metadata)
        return current

# ─── Projections with Read Models ────────────────────────────────────────────

class Projection(ABC):
    """Base class for read-model projections."""
    def __init__(self):
        self._handlers: Dict[str, Callable[[Dict[str, Any], Event], Dict[str, Any]]] = {}
        self._register_handlers()

    @abstractmethod
    def _register_handlers(self) -> None: ...

    def handle(self, state: Dict[str, Any], event: Event) -> Dict[str, Any]:
        handler = self._handlers.get(event.event_type)
        return handler(state, event) if handler else state

    def project(self, events: List[Event]) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        for event in events:
            state = self.handle(state, event)
        return state

class ProjectionEngine:
    """Manages multiple projections and dispatches events."""
    def __init__(self):
        self._projections: List[Projection] = []

    def register(self, projection: Projection) -> None:
        self._projections.append(projection)

    def dispatch(self, event: Event) -> None:
        for proj in self._projections:
            proj.handle({}, event)

    def rebuild(self, events: List[Event]) -> List[Dict[str, Any]]:
        return [proj.project(events) for proj in self._projections]

# ─── Event-Driven Sagas with Compensation ────────────────────────────────────

class SagaStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    COMPENSATING = auto()
    COMPENSATED = auto()
    FAILED = auto()

@dataclass
class SagaStep:
    name: str
    action: Callable[[], None]
    compensation: Callable[[], None]
    executed: bool = False

class Saga:
    """Event-driven saga with automatic compensation on failure."""
    def __init__(self, saga_id: Optional[str] = None):
        self.saga_id = saga_id or str(uuid.uuid4())
        self._steps: List[SagaStep] = []
        self._status = SagaStatus.PENDING
        self._current_step = 0

    def add_step(self, name: str, action: Callable[[], None],
        compensation: Callable[[], None]) -> "Saga":
        self._steps.append(SagaStep(name, action, compensation))
        return self

    def execute(self) -> bool:
        self._status = SagaStatus.RUNNING
        for i, step in enumerate(self._steps):
            self._current_step = i
            try:
                step.action()
                step.executed = True
            except Exception:
                self._compensate(i)
                self._status = SagaStatus.COMPENSATED
                return False
        self._status = SagaStatus.COMPLETED
        return True

    def _compensate(self, failed_index: int) -> None:
        self._status = SagaStatus.COMPENSATING
        for step in reversed(self._steps[:failed_index]):
            if step.executed:
                try: step.compensation()
                except Exception: pass

    @property
    def status(self) -> SagaStatus:
        return self._status

class SagaOrchestrator:
    """Orchestrates saga execution triggered by events."""
    def __init__(self):
        self._sagas: Dict[str, Saga] = {}
        self._event_triggers: Dict[str, Callable[[], Saga]] = {}

    def on_event(self, event_type: str, saga_factory: Callable[[], Saga]) -> None:
        self._event_triggers[event_type] = saga_factory

    def handle_event(self, event: Event) -> Optional[Saga]:
        factory = self._event_triggers.get(event.event_type)
        if not factory: return None
        saga = factory()
        self._sagas[saga.saga_id] = saga
        saga.execute()
        return saga

    def get_saga(self, saga_id: str) -> Optional[Saga]:
        return self._sagas.get(saga_id)
