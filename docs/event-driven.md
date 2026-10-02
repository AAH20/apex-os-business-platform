# APEX-OS Business Platform — Event-Driven Architecture

## Table of Contents

1. [Overview](#overview)
2. [Event Sourcing](#event-sourcing)
3. [CQRS (Command Query Responsibility Segregation)](#cqrs)
4. [Saga Pattern](#saga-pattern)
5. [Event Streaming](#event-streaming)
6. [Event Replay](#event-replay)
7. [Implementation Reference](#implementation-reference)
8. [Operational Concerns](#operational-concerns)

---

## 1. Overview

APEX-OS Business Platform uses an **event-driven architecture (EDA)** as its foundational integration and state-management paradigm. Every state change in the system is captured as an immutable **event**, stored in an **event store**, and propagated to interested consumers via **event streaming**. This approach provides:

- **Full audit trail** — every mutation is recorded with its context
- **Temporal queries** — reconstruct state at any point in time
- **Loose coupling** — producers and consumers evolve independently
- **Resilience** — replay enables recovery from failures without data loss
- **Scalability** — CQRS separates read and write workloads for independent scaling

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Events are facts** | An event represents something that already happened; it is immutable and never modified or deleted |
| **Event sourcing** | State is derived by replaying events, not by storing current state directly |
| **CQRS** | Commands (writes) and queries (reads) use separate models and data stores |
| **Saga** | Long-running business transactions are decomposed into a sequence of local transactions with compensating actions |
| **Streaming** | Events are published to a distributed log for real-time consumption |
| **Replay** | Projections and read models can be rebuilt from the event log at any time |

---

## 2. Event Sourcing

### 2.1 Concept

Event sourcing persists the state of an entity as a sequence of state-changing events. Instead of storing the current state (e.g., `balance = 100`), we store the events that led to that state (`Deposited $50`, `Withdrawn $30`, `Deposited $80`). The current state is computed by replaying all events in order.

### 2.2 Event Store Schema

```sql
-- Core event store table
CREATE TABLE event_store (
    event_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id      UUID NOT NULL,
    aggregate_type    VARCHAR(128) NOT NULL,
    event_type        VARCHAR(256) NOT NULL,
    event_version     INTEGER NOT NULL,
    payload           JSONB NOT NULL,
    metadata          JSONB NOT NULL DEFAULT '{}',
    occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    recorded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    sequence_number   BIGSERIAL,
    tenant_id         UUID NOT NULL,
    correlation_id    UUID,
    causation_id      UUID,
    
    UNIQUE (aggregate_id, event_version)
);

-- Indexes for common access patterns
CREATE INDEX idx_event_store_aggregate ON event_store (aggregate_id, event_version);
CREATE INDEX idx_event_store_type ON event_store (event_type, occurred_at DESC);
CREATE INDEX idx_event_store_tenant ON event_store (tenant_id, occurred_at DESC);
CREATE INDEX idx_event_store_correlation ON event_store (correlation_id);
CREATE INDEX idx_event_store_sequence ON event_store (sequence_number);
```

### 2.3 Event Envelope

Every event follows a standard envelope structure:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "aggregate_id": "order-12345",
  "aggregate_type": "Order",
  "event_type": "OrderPlaced",
  "event_version": 1,
  "occurred_at": "2026-10-01T10:30:00.000Z",
  "recorded_at": "2026-10-01T10:30:00.050Z",
  "tenant_id": "tenant-abc",
  "correlation_id": "corr-001",
  "causation_id": null,
  "payload": {
    "customer_id": "cust-789",
    "items": [
      { "sku": "WIDGET-001", "quantity": 2, "unit_price": 29.99 }
    ],
    "total": 59.98,
    "currency": "USD"
  },
  "metadata": {
    "user_id": "user-42",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "source": "web-checkout"
  }
}
```

### 2.4 Aggregate Root Pattern

```python
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime

@dataclass
class DomainEvent:
    event_id: UUID
    aggregate_id: UUID
    event_type: str
    event_version: int
    occurred_at: datetime
    payload: dict
    metadata: dict = field(default_factory=dict)
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None


class AggregateRoot:
    """Base class for all event-sourced aggregates."""
    
    def __init__(self, aggregate_id: UUID):
        self._id = aggregate_id
        self._version = 0
        self._uncommitted_events: List[DomainEvent] = []
    
    @property
    def id(self) -> UUID:
        return self._id
    
    @property
    def version(self) -> int:
        return self._version
    
    def _apply(self, event: DomainEvent) -> None:
        """Apply an event to mutate aggregate state. Override in subclasses."""
        handler = getattr(self, f"_on_{event.event_type}", None)
        if handler:
            handler(event.payload)
        self._version = event.event_version
    
    def _raise_event(self, event_type: str, payload: dict, 
                     correlation_id: Optional[UUID] = None,
                     causation_id: Optional[UUID] = None) -> DomainEvent:
        """Create and apply a new domain event."""
        self._version += 1
        event = DomainEvent(
            event_id=uuid4(),
            aggregate_id=self._id,
            event_type=event_type,
            event_version=self._version,
            occurred_at=datetime.utcnow(),
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        self._apply(event)
        self._uncommitted_events.append(event)
        return event
    
    def load_from_history(self, events: List[DomainEvent]) -> None:
        """Rehydrate aggregate from a sequence of historical events."""
        for event in events:
            self._apply(event)
    
    def get_uncommitted_events(self) -> List[DomainEvent]:
        return list(self._uncommitted_events)
    
    def mark_committed(self) -> None:
        self._uncommitted_events.clear()


class Order(AggregateRoot):
    """Example: Order aggregate with event sourcing."""
    
    def __init__(self, aggregate_id: UUID):
        super().__init__(aggregate_id)
        self._customer_id: Optional[UUID] = None
        self._items: List[dict] = []
        self._status: str = "pending"
        self._total: float = 0.0
        self._currency: str = "USD"
    
    # --- Command handlers ---
    
    def place(self, customer_id: UUID, items: List[dict], 
              currency: str = "USD", correlation_id: Optional[UUID] = None) -> None:
        if self._status != "pending":
            raise ValueError(f"Cannot place order in status: {self._status}")
        self._raise_event("OrderPlaced", {
            "customer_id": str(customer_id),
            "items": items,
            "currency": currency,
        }, correlation_id=correlation_id)
    
    def confirm(self, correlation_id: Optional[UUID] = None) -> None:
        if self._status != "pending":
            raise ValueError(f"Cannot confirm order in status: {self._status}")
        self._raise_event("OrderConfirmed", {}, correlation_id=correlation_id)
    
    def ship(self, tracking_number: str, correlation_id: Optional[UUID] = None) -> None:
        if self._status != "confirmed":
            raise ValueError(f"Cannot ship order in status: {self._status}")
        self._raise_event("OrderShipped", {
            "tracking_number": tracking_number,
        }, correlation_id=correlation_id)
    
    def cancel(self, reason: str, correlation_id: Optional[UUID] = None) -> None:
        if self._status in ("shipped", "delivered"):
            raise ValueError(f"Cannot cancel order in status: {self._status}")
        self._raise_event("OrderCancelled", {
            "reason": reason,
        }, correlation_id=correlation_id)
    
    # --- Event handlers (state mutators) ---
    
    def _on_OrderPlaced(self, payload: dict) -> None:
        self._customer_id = UUID(payload["customer_id"])
        self._items = payload["items"]
        self._currency = payload["currency"]
        self._total = sum(
            item["quantity"] * item["unit_price"] for item in self._items
        )
        self._status = "pending"
    
    def _on_OrderConfirmed(self, payload: dict) -> None:
        self._status = "confirmed"
    
    def _on_OrderShipped(self, payload: dict) -> None:
        self._status = "shipped"
    
    def _on_OrderCancelled(self, payload: dict) -> None:
        self._status = "cancelled"
```

### 2.5 Event Store Repository

```python
from typing import List, Optional
from uuid import UUID
import json
import asyncpg


class EventStoreRepository:
    """Repository for persisting and loading events."""
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def append(self, events: List[DomainEvent], 
                     expected_version: int) -> bool:
        """
        Append events with optimistic concurrency control.
        Returns True on success, raises ConcurrencyException on conflict.
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for event in events:
                    # Optimistic concurrency check
                    current_version = await conn.fetchval(
                        "SELECT COALESCE(MAX(event_version), 0) "
                        "FROM event_store WHERE aggregate_id = $1",
                        event.aggregate_id
                    )
                    if current_version != expected_version:
                        raise ConcurrencyException(
                            f"Expected version {expected_version}, "
                            f"found {current_version}"
                        )
                    
                    await conn.execute(
                        """INSERT INTO event_store 
                           (event_id, aggregate_id, aggregate_type, event_type,
                            event_version, payload, metadata, occurred_at,
                            correlation_id, causation_id, tenant_id)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                        event.event_id,
                        event.aggregate_id,
                        self._aggregate_type,
                        event.event_type,
                        event.event_version,
                        json.dumps(event.payload),
                        json.dumps(event.metadata),
                        event.occurred_at,
                        event.correlation_id,
                        event.causation_id,
                        event.tenant_id,
                    )
                    expected_version += 1
        return True
    
    async def load(self, aggregate_id: UUID, 
                   from_version: int = 0) -> List[DomainEvent]:
        """Load all events for an aggregate, optionally from a specific version."""
        rows = await self._pool.fetch(
            """SELECT event_id, aggregate_id, aggregate_type, event_type,
                      event_version, payload, metadata, occurred_at,
                      correlation_id, causation_id, tenant_id
               FROM event_store 
               WHERE aggregate_id = $1 AND event_version > $2
               ORDER BY event_version ASC""",
            aggregate_id, from_version
        )
        return [self._row_to_event(row) for row in rows]
    
    async def load_all(self, after_sequence: int = 0, 
                       batch_size: int = 1000) -> List[DomainEvent]:
        """Load all events after a sequence number (for projections/replay)."""
        rows = await self._pool.fetch(
            """SELECT event_id, aggregate_id, aggregate_type, event_type,
                      event_version, payload, metadata, occurred_at,
                      correlation_id, causation_id, tenant_id, sequence_number
               FROM event_store 
               WHERE sequence_number > $1
               ORDER BY sequence_number ASC
               LIMIT $2""",
            after_sequence, batch_size
        )
        return [self._row_to_event(row) for row in rows]
    
    def _row_to_event(self, row) -> DomainEvent:
        return DomainEvent(
            event_id=row["event_id"],
            aggregate_id=row["aggregate_id"],
            event_type=row["event_type"],
            event_version=row["event_version"],
            occurred_at=row["occurred_at"],
            payload=json.loads(row["payload"]),
            metadata=json.loads(row["metadata"]),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
        )
```

### 2.6 Snapshots

For aggregates with long event histories, snapshots avoid replaying thousands of events:

```sql
CREATE TABLE snapshots (
    aggregate_id   UUID PRIMARY KEY,
    aggregate_type VARCHAR(128) NOT NULL,
    version        INTEGER NOT NULL,
    state          JSONB NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

```python
class SnapshotStore:
    """Manages aggregate snapshots for performance."""
    
    SNAPSHOT_FREQUENCY = 50  # Create snapshot every N events
    
    async def save_snapshot(self, aggregate: AggregateRoot) -> None:
        if aggregate.version % self.SNAPSHOT_FREQUENCY == 0:
            state = self._extract_state(aggregate)
            await self._pool.execute(
                """INSERT INTO snapshots (aggregate_id, aggregate_type, version, state)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (aggregate_id) DO UPDATE
                   SET version = $3, state = $4, created_at = now()""",
                aggregate.id, aggregate.type, aggregate.version, json.dumps(state)
            )
    
    async def load_snapshot(self, aggregate_id: UUID) -> Optional[tuple]:
        row = await self._pool.fetchrow(
            "SELECT version, state FROM snapshots WHERE aggregate_id = $1",
            aggregate_id
        )
        if row:
            return row["version"], json.loads(row["state"])
        return None
```

---

## 3. CQRS (Command Query Responsibility Segregation)

### 3.1 Concept

CQRS separates the **write model** (commands that change state) from the **read model** (queries that return data). In APEX-OS, the write side uses event sourcing; the side uses read-optimized projections built from the event stream.

```
┌──────────────┐     Commands      ┌─────────────────┐
│   Client     │ ───────────────►  │  Command Side    │
│              │                   │  (Event Store)   │
│              │ ◄───────────────  │                  │
│              │     Queries       └────────┬─────────┘
│              │                            │ Events
│              │                   ┌────────▼─────────┐
│              │ ◄───────────────  │   Read Side       │
│              │     DTOs/Views   │  (Projections)    │
└──────────────┘                   └──────────────────┘
```

### 3.2 Command Side

Commands are intent to change state. They are validated, processed by aggregates, and result in events.

```python
from dataclasses import dataclass
from uuid import UUID
from typing import Any


@dataclass
class Command:
    """Base class for all commands."""
    command_id: UUID
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


@dataclass
class PlaceOrderCommand(Command):
    customer_id: UUID
    items: list
    currency: str = "USD"


@dataclass
class ConfirmOrderCommand(Command):
    order_id: UUID


@dataclass
class ShipOrderCommand(Command):
    order_id: UUID
    tracking_number: str


@dataclass
class CancelOrderCommand(Command):
    order_id: UUID
    reason: str


class CommandHandler:
    """Handles commands by loading aggregates, executing logic, and saving events."""
    
    def __init__(self, event_store: EventStoreRepository, 
                 snapshot_store: SnapshotStore,
                 event_bus: "EventBus"):
        self._event_store = event_store
        self._snapshot_store = snapshot_store
        self._event_bus = event_bus
    
    async def handle(self, command: Command) -> None:
        handler = getattr(self, f"_handle_{type(command).__name__}", None)
        if not handler:
            raise ValueError(f"No handler for {type(command).__name__}")
        await handler(command)
    
    async def _handle_PlaceOrderCommand(self, cmd: PlaceOrderCommand) -> None:
        order = Order(uuid4())
        order.place(
            customer_id=cmd.customer_id,
            items=cmd.items,
            currency=cmd.currency,
            correlation_id=cmd.correlation_id,
        )
        await self._save_and_publish(order)
    
    async def _handle_ConfirmOrderCommand(self, cmd: ConfirmOrderCommand) -> None:
        order = await self._load_order(cmd.order_id)
        order.confirm(correlation_id=cmd.correlation_id)
        await self._save_and_publish(order)
    
    async def _handle_ShipOrderCommand(self, cmd: ShipOrderCommand) -> None:
        order = await self._load_order(cmd.order_id)
        order.ship(
            tracking_number=cmd.tracking_number,
            correlation_id=cmd.correlation_id,
        )
        await self._save_and_publish(order)
    
    async def _handle_CancelOrderCommand(self, cmd: CancelOrderCommand) -> None:
        order = await self._load_order(cmd.order_id)
        order.cancel(
            reason=cmd.reason,
            correlation_id=cmd.correlation_id,
        )
        await self._save_and_publish(order)
    
    async def _load_order(self, order_id: UUID) -> Order:
        # Try snapshot first
        snapshot = await self._snapshot_store.load_snapshot(order_id)
        if snapshot:
            version, state = snapshot
            order = Order(order_id)
            order._restore_from_snapshot(state)
            # Load events after snapshot
            events = await self._event_store.load(order_id, from_version=version)
            order.load_from_history(events)
        else:
            events = await self._event_store.load(order_id)
            order = Order(order_id)
            order.load_from_history(events)
        return order
    
    async def _save_and_publish(self, aggregate: AggregateRoot) -> None:
        events = aggregate.get_uncommitted_events()
        if not events:
            return
        await self._event_store.append(events, aggregate.version - len(events))
        await self._snapshot_store.save_snapshot(aggregate)
        for event in events:
            await self._event_bus.publish(event)
        aggregate.mark_committed()
```

### 3.3 Query Side

Queries are served from read-optimized projections (materialized views). They never touch the event store directly.

```sql
-- Read model: Order summary view
CREATE TABLE order_summary (
    order_id        UUID PRIMARY KEY,
    customer_id     UUID NOT NULL,
    status          VARCHAR(32) NOT NULL,
    total           DECIMAL(12,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL,
    item_count      INTEGER NOT NULL,
    placed_at       TIMESTAMPTZ NOT NULL,
    confirmed_at    TIMESTAMPTZ,
    shipped_at      TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    tracking_number VARCHAR(128),
    version         INTEGER NOT NULL
);

-- Read model: Customer order history
CREATE TABLE customer_order_history (
    customer_id     UUID NOT NULL,
    order_id        UUID NOT NULL,
    status          VARCHAR(32) NOT NULL,
    total           DECIMAL(12,2) NOT NULL,
    placed_at       TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (customer_id, order_id)
);

-- Read model: Product sales analytics
CREATE TABLE product_sales (
    sku             VARCHAR(64) NOT NULL,
    date            DATE NOT NULL,
    units_sold      INTEGER NOT NULL DEFAULT 0,
    revenue         DECIMAL(12,2) NOT NULL DEFAULT 0,
    order_count     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (sku, date)
);
```

```python
class OrderQueryService:
    """Query service for order read models."""
    
    def __init__(self, read_db: asyncpg.Pool):
        self._db = read_db
    
    async def get_order(self, order_id: UUID) -> Optional[dict]:
        row = await self._db.fetchrow(
            "SELECT * FROM order_summary WHERE order_id = $1", order_id
        )
        return dict(row) if row else None
    
    async def list_orders_by_customer(self, customer_id: UUID, 
                                       limit: int = 50, 
                                       offset: int = 0) -> List[dict]:
        rows = await self._db.fetch(
            """SELECT * FROM customer_order_history 
               WHERE customer_id = $1
               ORDER BY placed_at DESC
               LIMIT $2 OFFSET $3""",
            customer_id, limit, offset
        )
        return [dict(r) for r in rows]
    
    async def get_product_sales(self, sku: str, 
                                 start_date: date, 
                                 end_date: date) -> List[dict]:
        rows = await self._db.fetch(
            """SELECT * FROM product_sales 
               WHERE sku = $1 AND date BETWEEN $2 AND $3
               ORDER BY date ASC""",
            sku, start_date, end_date
        )
        return [dict(r) for r in rows]
```

### 3.4 Projections

Projections transform events into read-model updates. They are idempotent and can be replayed from scratch.

```python
from typing import Callable, Dict, List
import logging

logger = logging.getLogger(__name__)


class Projection:
    """Base class for read-model projections."""
    
    def __init__(self, read_db: asyncpg.Pool):
        self._db = read_db
        self._handlers: Dict[str, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Map event types to handler methods."""
        for attr_name in dir(self):
            if attr_name.startswith("on_"):
                event_type = attr_name[3:]  # Strip "on_" prefix
                self._handlers[event_type] = getattr(self, attr_name)
    
    async def handle(self, event: DomainEvent) -> None:
        handler = self._handlers.get(event.event_type)
        if handler:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    f"Projection failed for {event.event_type} "
                    f"(aggregate: {event.aggregate_id})"
                )
                raise
    
    async def reset(self) -> None:
        """Clear all projected data. Used during full replay."""
        raise NotImplementedError


class OrderSummaryProjection(Projection):
    """Projects order events into the order_summary read model."""
    
    async def reset(self) -> None:
        await self._db.execute("TRUNCATE order_summary")
    
    async def on_OrderPlaced(self, event: DomainEvent) -> None:
        p = event.payload
        await self._db.execute(
            """INSERT INTO order_summary 
               (order_id, customer_id, status, total, currency, 
                item_count, placed_at, version)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            event.aggregate_id,
            UUID(p["customer_id"]),
            "pending",
            sum(i["quantity"] * i["unit_price"] for i in p["items"]),
            p["currency"],
            len(p["items"]),
            event.occurred_at,
            event.event_version,
        )
    
    async def on_OrderConfirmed(self, event: DomainEvent) -> None:
        await self._db.execute(
            """UPDATE order_summary 
               SET status = 'confirmed', confirmed_at = $2, version = $3
               WHERE order_id = $1""",
            event.aggregate_id, event.occurred_at, event.event_version
        )
    
    async def on_OrderShipped(self, event: DomainEvent) -> None:
        await self._db.execute(
            """UPDATE order_summary 
               SET status = 'shipped', shipped_at = $2, 
                   tracking_number = $3, version = $4
               WHERE order_id = $1""",
            event.aggregate_id, event.occurred_at,
            event.payload["tracking_number"], event.event_version
        )
    
    async def on_OrderCancelled(self, event: DomainEvent) -> None:
        await self._db.execute(
            """UPDATE order_summary 
               SET status = 'cancelled', cancelled_at = $2, version = $3
               WHERE order_id = $1""",
            event.aggregate_id, event.occurred_at, event.event_version
        )


class CustomerOrderHistoryProjection(Projection):
    """Projects order events into customer_order_history read model."""
    
    async def reset(self) -> None:
        await self._db.execute("TRUNCATE customer_order_history")
    
    async def on_OrderPlaced(self, event: DomainEvent) -> None:
        p = event.payload
        await self._db.execute(
            """INSERT INTO customer_order_history 
               (customer_id, order_id, status, total, placed_at)
               VALUES ($1, $2, $3, $4, $5)""",
            UUID(p["customer_id"]),
            event.aggregate_id,
            "pending",
            sum(i["quantity"] * i["unit_price"] for i in p["items"]),
            event.occurred_at,
        )
    
    async def on_OrderConfirmed(self, event: DomainEvent) -> None:
        await self._db.execute(
            """UPDATE customer_order_history SET status = 'confirmed'
               WHERE order_id = $1""",
            event.aggregate_id
        )
    
    async def on_OrderShipped(self, event: DomainEvent) -> None:
        await self._db.execute(
            """UPDATE customer_order_history SET status = 'shipped'
               WHERE order_id = $1""",
            event.aggregate_id
        )
    
    async def on_OrderCancelled(self, event: DomainEvent) -> None:
        await self._db.execute(
            """UPDATE customer_order_history SET status = 'cancelled'
               WHERE order_id = $1""",
            event.aggregate_id
        )
```

### 3.5 Event Dispatcher (Projector Worker)

```python
import asyncio
from typing import List


class ProjectionWorker:
    """
    Background worker that reads events from the event store
    and dispatches them to projections.
    """
    
    def __init__(self, event_store: EventStoreRepository,
                 projections: List[Projection],
                 poll_interval: float = 0.1):
        self._event_store = event_store
        self._projections = projections
        self._poll_interval = poll_interval
        self._last_sequence = 0
        self._running = False
    
    async def start(self) -> None:
        self._running = True
        while self._running:
            events = await self._event_store.load_all(
                after_sequence=self._last_sequence
            )
            if not events:
                await asyncio.sleep(self._poll_interval)
                continue
            
            for event in events:
                for projection in self._projections:
                    await projection.handle(event)
                self._last_sequence = event.sequence_number
            
            logger.info(
                f"Processed {len(events)} events, "
                f"last sequence: {self._last_sequence}"
            )
    
    async def stop(self) -> None:
        self._running = False
    
    async def catch_up(self) -> None:
        """Process all pending events once (for startup)."""
        while True:
            events = await self._event_store.load_all(
                after_sequence=self._last_sequence, batch_size=500
            )
            if not events:
                break
            for event in events:
                for projection in self._projections:
                    await projection.handle(event)
                self._last_sequence = event.sequence_number
```

---

## 4. Saga Pattern

### 4.1 Concept

A **Saga** manages a long-running business transaction that spans multiple services or aggregates. Instead of a distributed ACID transaction (2PC), a Saga decomposes the transaction into a sequence of **local transactions**, each with a **compensating action** that undoes its effects if a subsequent step fails.

### 4.2 Saga Types

| Type | Description | When to Use |
|------|-------------|-------------|
| **Choreography** | Each service listens to events and triggers the next step; no central coordinator | Simple flows, few participants |
| **Orchestration** | A central orchestrator sends commands and handles responses; explicit state machine | Complex flows, many participants, need visibility |

APEX-OS uses **orchestration** for complex business processes (order fulfillment, payment processing) and **choreography** for simple event chains.

### 4.3 Order Fulfillment Saga (Orchestration)

```
┌─────────────┐
│  Saga       │
│ Orchestrator│
└──────┬──────┘
       │
       ├─► 1. Reserve Inventory ───► Inventory Service
       │    └─ Compensate: Release Inventory
       │
       ├─► 2. Process Payment ─────► Payment Service
       │    └─ Compensate: Refund Payment
       │
       ├─► 3. Create Shipment ─────► Shipping Service
       │    └─ Compensate: Cancel Shipment
       │
       └─► 4. Notify Customer ─────► Notification Service
            └─ Compensate: (none — notification is fire-and-forget)
```

### 4.4 Saga State Machine

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from uuid import UUID, uuid4
import json
import asyncpg
import logging

logger = logging.getLogger(__name__)


class SagaStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


class SagaStepStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


@dataclass
class SagaStep:
    name: str
    action: str           # Command to execute
    compensation: str     # Compensating command
    status: SagaStepStatus = SagaStepStatus.PENDING
    result: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class SagaInstance:
    saga_id: UUID
    saga_type: str
    status: SagaStatus
    current_step: int = 0
    steps: List[SagaStep] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    created_at: Any = None
    updated_at: Any = None


# --- Saga Definition ---

ORDER_FULFILLMENT_SAGA = {
    "name": "OrderFulfillment",
    "steps": [
        {
            "name": "reserve_inventory",
            "action": "ReserveInventory",
            "compensation": "ReleaseInventory",
        },
        {
            "name": "process_payment",
            "action": "ProcessPayment",
            "compensation": "RefundPayment",
        },
        {
            "name": "create_shipment",
            "action": "CreateShipment",
            "compensation": "CancelShipment",
        },
        {
            "name": "notify_customer",
            "action": "SendOrderConfirmation",
            "compensation": None,  # Fire-and-forget, no compensation
        },
    ],
}
```

### 4.5 Saga Orchestrator

```python
class SagaOrchestrator:
    """
    Central orchestrator for saga execution.
    Persists saga state for durability and recovery.
    """
    
    def __init__(self, db_pool: asyncpg.Pool, command_gateway: "CommandGateway"):
        self._db = db_pool
        self._gateway = command_gateway
        self._saga_definitions: Dict[str, dict] = {}
        self._register_saga_definitions()
    
    def _register_saga_definitions(self) -> None:
        self._saga_definitions["OrderFulfillment"] = ORDER_FULFILLMENT_SAGA
    
    async def start_saga(self, saga_type: str, 
                         context: dict,
                         correlation_id: Optional[UUID] = None) -> SagaInstance:
        """Start a new saga instance."""
        definition = self._saga_definitions.get(saga_type)
        if not definition:
            raise ValueError(f"Unknown saga type: {saga_type}")
        
        saga_id = uuid4()
        steps = [
            SagaStep(
                name=step["name"],
                action=step["action"],
                compensation=step["compensation"],
            )
            for step in definition["steps"]
        ]
        
        saga = SagaInstance(
            saga_id=saga_id,
            saga_type=saga_type,
            status=SagaStatus.RUNNING,
            current_step=0,
            steps=steps,
            context=context,
        )
        
        await self._persist_saga(saga)
        
        # Start executing
        await self._execute_next_step(saga)
        return saga
    
    async def _execute_next_step(self, saga: SagaInstance) -> None:
        """Execute the next step in the saga."""
        if saga.current_step >= len(saga.steps):
            # All steps completed
            saga.status = SagaStatus.COMPLETED
            await self._persist_saga(saga)
            logger.info(f"Saga {saga.saga_id} completed")
            return
        
        step = saga.steps[saga.current_step]
        step.status = SagaStepStatus.EXECUTING
        await self._persist_saga(saga)
        
        try:
            # Execute the action via command gateway
            result = await self._gateway.send(
                command_type=step.action,
                payload=saga.context,
                correlation_id=saga.saga_id,
            )
            step.status = SagaStepStatus.SUCCEEDED
            step.result = result
            saga.current_step += 1
            await self._persist_saga(saga)
            
            # Continue to next step
            await self._execute_next_step(saga)
            
        except Exception as e:
            logger.error(f"Saga {saga.saga_id} step {step.name} failed: {e}")
            step.status = SagaStepStatus.FAILED
            step.error = str(e)
            saga.status = SagaStatus.COMPENSATING
            await self._persist_saga(saga)
            
            # Start compensation
            await self._compensate(saga)
    
    async def _compensate(self, saga: SagaInstance) -> None:
        """Run compensating actions for all completed steps in reverse order."""
        logger.warning(f"Saga {saga.saga_id} entering compensation")
        
        # Compensate steps in reverse order (skip the failed step)
        for i in range(saga.current_step - 1, -1, -1):
            step = saga.steps[i]
            if step.compensation is None:
                step.status = SagaStepStatus.COMPENSATED
                continue
            
            step.status = SagaStepStatus.COMPENSATING
            await self._persist_saga(saga)
            
            try:
                await self._gateway.send(
                    command_type=step.compensation,
                    payload={
                        **saga.context,
                        "original_result": step.result,
                    },
                    correlation_id=saga.saga_id,
                )
                step.status = SagaStepStatus.COMPENSATED
                logger.info(f"Saga {saga.saga_id} step {step.name} compensated")
            except Exception as e:
                logger.critical(
                    f"Saga {saga.saga_id} compensation failed for {step.name}: {e}. "
                    f"Manual intervention required."
                )
                # Alert operations team — this requires manual resolution
                await self._alert_compensation_failure(saga, step, e)
            
            await self._persist_saga(saga)
        
        saga.status = SagaStatus.COMPENSATED
        await self._persist_saga(saga)
        logger.warning(f"Saga {saga.saga_id} compensated")
    
    async def _persist_saga(self, saga: SagaInstance) -> None:
        """Persist saga state to the database."""
        await self._db.execute(
            """INSERT INTO saga_instances 
               (saga_id, saga_type, status, current_step, steps, context, 
                created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, now(), now())
               ON CONFLICT (saga_id) DO UPDATE
               SET status = $3, current_step = $4, steps = $5, 
                   context = $6, updated_at = now()""",
            saga.saga_id,
            saga.saga_type,
            saga.status.value,
            saga.current_step,
            json.dumps([
                {
                    "name": s.name,
                    "action": s.action,
                    "compensation": s.compensation,
                    "status": s.status.value,
                    "result": s.result,
                    "error": s.error,
                }
                for s in saga.steps
            ]),
            json.dumps(saga.context),
        )
    
    async def _alert_compensation_failure(self, saga: SagaInstance, 
                                           step: SagaStep, 
                                           error: Exception) -> None:
        """Alert operations when compensation fails (requires manual fix)."""
        logger.critical(
            f"COMPENSATION FAILURE: Saga {saga.saga_id}, "
            f"step {step.name}, error: {error}"
        )
        # In production: send PagerDuty alert, create incident ticket, etc.
    
    async def recover_pending_sagas(self) -> None:
        """Recover sagas that were interrupted (e.g., after service restart)."""
        rows = await self._db.fetch(
            """SELECT saga_id FROM saga_instances 
               WHERE status IN ('running', 'compensating')"""
        )
        for row in rows:
            saga = await self._load_saga(row["saga_id"])
            if saga.status == SagaStatus.RUNNING:
                await self._execute_next_step(saga)
            elif saga.status == SagaStatus.COMPENSATING:
                await self._compensate(saga)
```

### 4.6 Saga Database Schema

```sql
CREATE TABLE saga_instances (
    saga_id         UUID PRIMARY KEY,
    saga_type       VARCHAR(128) NOT NULL,
    status          VARCHAR(32) NOT NULL,
    current_step    INTEGER NOT NULL DEFAULT 0,
    steps           JSONB NOT NULL,
    context         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_saga_status ON saga_instances (status) 
    WHERE status IN ('running', 'compensating');
CREATE INDEX idx_saga_type ON saga_instances (saga_type, created_at DESC);
```

### 4.7 Choreography Example

For simpler flows, choreography uses event-driven triggers without a central orchestrator:

```python
class InventoryService:
    """Listens to OrderPlaced, publishes InventoryReserved or InventoryUnavailable."""
    
    async def on_OrderPlaced(self, event: DomainEvent) -> None:
        order_id = event.aggregate_id
        items = event.payload["items"]
        
        try:
            await self._reserve_inventory(items)
            await self._event_bus.publish(DomainEvent(
                event_id=uuid4(),
                aggregate_id=order_id,
                aggregate_type="Order",
                event_type="InventoryReserved",
                event_version=event.event_version + 1,
                occurred_at=datetime.utcnow(),
                payload={"items": items},
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
            ))
        except InsufficientInventoryError:
            await self._event_bus.publish(DomainEvent(
                event_id=uuid4(),
                aggregate_id=order_id,
                aggregate_type="Order",
                event_type="InventoryUnavailable",
                event_version=event.event_version + 1,
                occurred_at=datetime.utcnow(),
                payload={"reason": "insufficient_stock", "items": items},
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
            ))


class PaymentService:
    """Listens to InventoryReserved, processes payment."""
    
    async def on_InventoryReserved(self, event: DomainEvent) -> None:
        order_id = event.aggregate_id
        # Process payment...
        await self._event_bus.publish(DomainEvent(
            event_id=uuid4(),
            aggregate_id=order_id,
            aggregate_type="Order",
            event_type="PaymentProcessed",
            event_version=event.event_version + 1,
            occurred_at=datetime.utcnow(),
            payload={"transaction_id": "txn-123", "amount": 59.98},
            correlation_id=event.correlation_id,
            causation_id=event.event_id,
        ))
```

---

## 5. Event Streaming

### 5.1 Concept

Event streaming publishes events to a distributed log (Apache Kafka, Redpanda, or Pulsar) where multiple consumers can independently read and process them. The log provides durability, ordering guarantees, and replay capability.

### 5.2 Architecture

```
                    ┌──────────────┐
                    │  Event Store │
                    │  (PostgreSQL)│
                    └──────┬───────┘
                           │ CDC / Polling
                    ┌──────▼───────┐
                    │  Event Bus   │
                    │  (Kafka /    │
                    │   Redpanda)  │
                    └──┬───┬───┬───┘
                       │   │   │
          ┌────────────┘   │   └────────────┐
          ▼                ▼                 ▼
    ┌──────────┐    ┌──────────┐     ┌──────────┐
    │Projection│    │Integration│    │ Analytics │
    │ Worker   │    │  Service  │     │  Engine  │
    └──────────┘    └──────────┘     └──────────┘
```

### 5.3 Topic Design

| Topic | Partitions | Retention | Consumers |
|-------|-----------|-----------|-----------|
| `apex.events.order` | 12 | 30 days | Projections, Analytics, Search |
| `apex.events.inventory` | 6 | 14 days | Projections, Reorder Alerts |
| `apex.events.payment` | 6 | 90 days | Projections, Fraud Detection |
| `apex.events.shipping` | 6 | 14 days | Projections, Tracking |
| `apex.events.customer` | 6 | 30 days | Projections, CRM Sync |
| `apex.events.audit` | 3 | 365 days | Compliance, Audit Trail |
| `apex.dead-letter` | 3 | 30 days | Manual Inspection |

### 5.4 Event Publisher

```python
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import json
import logging

logger = logging.getLogger(__name__)


class KafkaEventBus:
    """Publishes domain events to Kafka topics."""
    
    def __init__(self, bootstrap_servers: str, client_id: str = "apex-event-bus"):
        self._producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "client.id": client_id,
            "enable.idempotence": True,
            "acks": "all",
            "retries": 5,
            "max.in.flight.requests.per.connection": 5,
            "compression.type": "lz4",
        })
        self._topic_mapping = {
            "OrderPlaced": "apex.events.order",
            "OrderConfirmed": "apex.events.order",
            "OrderShipped": "apex.events.order",
            "OrderCancelled": "apex.events.order",
            "InventoryReserved": "apex.events.inventory",
            "InventoryReleased": "apex.events.inventory",
            "PaymentProcessed": "apex.events.payment",
            "PaymentFailed": "apex.events.payment",
            "PaymentRefunded": "apex.events.payment",
            "ShipmentCreated": "apex.events.shipping",
            "ShipmentCancelled": "apex.events.shipping",
            "CustomerCreated": "apex.events.customer",
            "CustomerUpdated": "apex.events.customer",
        }
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to the appropriate Kafka topic."""
        topic = self._topic_mapping.get(event.event_type)
        if not topic:
            logger.warning(f"No topic mapping for {event.event_type}, using default")
            topic = "apex.events.default"
        
        key = str(event.aggregate_id).encode("utf-8")
        value = json.dumps({
            "event_id": str(event.event_id),
            "aggregate_id": str(event.aggregate_id),
            "aggregate_type": event.aggregate_type,
            "event_type": event.event_type,
            "event_version": event.event_version,
            "occurred_at": event.occurred_at.isoformat(),
            "payload": event.payload,
            "metadata": event.metadata,
            "correlation_id": str(event.correlation_id) if event.correlation_id else None,
            "causation_id": str(event.causation_id) if event.causation_id else None,
        }, default=str).encode("utf-8")
        
        headers = {
            "tenant_id": str(event.tenant_id),
            "event_type": event.event_type,
        }
        
        self._producer.produce(
            topic=topic,
            key=key,
            value=value,
            headers=headers,
            callback=self._delivery_callback,
        )
        self._producer.poll(0)
    
    def _delivery_callback(self, err, msg) -> None:
        if err:
            logger.error(f"Failed to deliver message: {err}")
            # In production: write to dead-letter topic or retry queue
        else:
            logger.debug(
                f"Delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}"
            )
    
    async def flush(self) -> None:
        self._producer.flush()
    
    @staticmethod
    def ensure_topics(bootstrap_servers: str, topics_config: dict) -> None:
        """Create topics if they don't exist."""
        admin = AdminClient({"bootstrap.servers": bootstrap_servers})
        existing = admin.list_topics().topics
        
        new_topics = []
        for topic_name, config in topics_config.items():
            if topic_name not in existing:
                new_topics.append(NewTopic(
                    topic_name,
                    num_partitions=config["partitions"],
                    replication_factor=config.get("replication_factor", 3),
                    config={
                        "retention.ms": str(config["retention_days"] * 86400000),
                        "cleanup.policy": "delete",
                        "min.insync.replicas": "2",
                    },
                ))
        
        if new_topics:
            admin.create_topics(new_topics)
            logger.info(f"Created {len(new_topics)} topics")
```

### 5.5 Event Consumer

```python
from confluent_kafka import Consumer, KafkaError, TopicPartition
from confluent_kafka.admin import AdminClient
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class EventConsumer:
    """
    Consumes events from Kafka and dispatches to handlers.
    Supports consumer groups for load balancing and partition assignment.
    """
    
    def __init__(self, bootstrap_servers: str, group_id: str,
                 topics: List[str],
                 handler: Callable[[dict], asyncio.Coroutine]):
        self._consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 45000,
            "heartbeat.interval.ms": 15000,
            "isolation.level": "read_committed",
        })
        self._topics = topics
        self._handler = handler
        self._running = False
    
    async def start(self) -> None:
        self._consumer.subscribe(self._topics)
        self._running = True
        
        while self._running:
            msg = self._consumer.poll(timeout=1.0)
            if msg is None:
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logger.error(f"Consumer error: {msg.error()}")
                    await self._send_to_dead_letter(msg)
                    self._consumer.commit(msg)
                    continue
            
            try:
                event = json.loads(msg.value().decode("utf-8"))
                await self._handler(event)
                self._consumer.commit(msg)
            except Exception as e:
                logger.exception(f"Failed to process message: {e}")
                await self._send_to_dead_letter(msg)
                self._consumer.commit(msg)  # Skip poison pill
    
    async def _send_to_dead_letter(self, msg) -> None:
        """Send failed messages to dead-letter topic for inspection."""
        dlq_producer = Producer({
            "bootstrap.servers": self._consumer.config["bootstrap.servers"],
        })
        dlq_producer.produce(
            topic="apex.dead-letter",
            key=msg.key(),
            value=msg.value(),
            headers={
                "original_topic": msg.topic(),
                "original_partition": str(msg.partition()),
                "original_offset": str(msg.offset()),
                "error": "processing_failed",
            },
        )
        dlq_producer.flush()
    
    async def stop(self) -> None:
        self._running = False
        self._consumer.close()
```

### 5.6 Change Data Capture (CDC)

For production, use CDC to stream events from PostgreSQL to Kafka without application-level publishing:

```yaml
# Debezium connector configuration
{
  "name": "apex-event-store-cdc",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres.apex.svc.cluster.local",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "${secrets:postgres:debezium-password}",
    "database.dbname": "apex_event_store",
    "database.server.name": "apex-event-store",
    "table.include.list": "public.event_store",
    "plugin.name": "pgoutput",
    "publication.name": "dbz_publication",
    "slot.name": "debezium_slot",
    "transforms": "unwrap,route",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "transforms.unwrap.delete.handling.mode": "rewrite",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "([^.]+)\\.([^.]+)\\.([^.]+)",
    "transforms.route.replacement": "apex.events.$3"
  }
}
```

### 5.7 Stream Processing

For real-time aggregations and complex event processing:

```python
# Using Faust (Python stream processing) or ksqlDB
# Example: Real-time order totals using Faust

import faust

app = faust.App(
    "apex-order-analytics",
    broker="kafka://kafka.apex.svc.cluster.local:9092",
    value_serializer="json",
)

order_placed_topic = app.topic("apex.events.order", value_type=dict)

order_totals = app.Table("order_totals", default=float)
hourly_revenue = app.Table("hourly_revenue", default=float)


@app.agent(order_placed_topic)
async def process_order(events):
    async for event in events:
        if event["event_type"] == "OrderPlaced":
            total = event["payload"]["total"]
            currency = event["payload"]["currency"]
            hour_key = event["occurred_at"][:13]  # YYYY-MM-DDTHH
            
            order_totals[currency] += total
            hourly_revenue[hour_key] += total
            
            # Emit real-time metrics
            logger.info(f"Order total {currency}: {order_totals[currency]}")
```

---

## 6. Event Replay

### 6.1 Concept

Event replay is the ability to reprocess events from the event store to:
- Rebuild read models (projections) from scratch
- Recover from bugs in projection logic
- Perform temporal queries (what was the state at time T?)
- Debug and audit historical decisions
- Migrate to new read-model schemas

### 6.2 Full Replay

```python
class EventReplayService:
    """
    Replays events to rebuild projections or perform temporal analysis.
    """
    
    def __init__(self, event_store: EventStoreRepository,
                 projections: List[Projection],
                 read_db: asyncpg.Pool):
        self._event_store = event_store
        self._projections = projections
        self._read_db = read_db
    
    async def full_replay(self, projection_names: Optional[List[str]] = None,
                          batch_size: int = 1000) -> dict:
        """
        Rebuild specified projections (or all) from the event store.
        Returns statistics about the replay.
        """
        stats = {
            "total_events": 0,
            "processed_events": 0,
            "failed_events": 0,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "duration_seconds": 0,
        }
        
        # Reset projections
        projections_to_replay = (
            [p for p in self._projections if type(p).__name__ in projection_names]
            if projection_names else self._projections
        )
        
        for projection in projections_to_replay:
            logger.info(f"Resetting projection: {type(projection).__name__}")
            await projection.reset()
        
        # Replay all events
        last_sequence = 0
        while True:
            events = await self._event_store.load_all(
                after_sequence=last_sequence,
                batch_size=batch_size,
            )
            if not events:
                break
            
            for event in events:
                stats["total_events"] += 1
                try:
                    for projection in projections_to_replay:
                        await projection.handle(event)
                    stats["processed_events"] += 1
                except Exception as e:
                    stats["failed_events"] += 1
                    logger.error(
                        f"Replay failed for event {event.event_id} "
                        f"({event.event_type}): {e}"
                    )
                    # Continue with next event — don't stop the entire replay
                
                last_sequence = event.sequence_number
            
            logger.info(
                f"Replay progress: {stats['processed_events']}/{stats['total_events']} "
                f"events processed"
            )
        
        stats["end_time"] = datetime.utcnow().isoformat()
        stats["duration_seconds"] = (
            datetime.fromisoformat(stats["end_time"]) -
            datetime.fromisoformat(stats["start_time"])
        ).total_seconds()
        
        logger.info(f"Full replay complete: {stats}")
        return stats
    
    async def replay_to_point_in_time(self, target_time: datetime,
                                       projection_names: Optional[List[str]] = None) -> dict:
        """
        Rebuild projections to a specific point in time.
        Useful for temporal queries and debugging.
        """
        stats = {
            "target_time": target_time.isoformat(),
            "total_events": 0,
            "processed_events": 0,
        }
        
        projections_to_replay = (
            [p for p in self._projections if type(p).__name__ in projection_names]
            if projection_names else self._projections
        )
        
        for projection in projections_to_replay:
            await projection.reset()
        
        last_sequence = 0
        while True:
            events = await self._event_store.load_all(
                after_sequence=last_sequence,
                batch_size=1000,
            )
            if not events:
                break
            
            for event in events:
                if event.occurred_at > target_time:
                    break  # Stop at target time
                
                stats["total_events"] += 1
                try:
                    for projection in projections_to_replay:
                        await projection.handle(event)
                    stats["processed_events"] += 1
                except Exception as e:
                    logger.error(f"Replay failed for {event.event_id}: {e}")
                
                last_sequence = event.sequence_number
        
        return stats
    
    async def replay_aggregate(self, aggregate_id: UUID,
                                to_version: Optional[int] = None) -> AggregateRoot:
        """
        Replay events for a single aggregate to reconstruct its state.
        Optionally stop at a specific version.
        """
        events = await self._event_store.load(aggregate_id)
        
        if to_version is not None:
            events = [e for e in events if e.event_version <= to_version]
        
        if not events:
            raise ValueError(f"No events found for aggregate {aggregate_id}")
        
        aggregate_type = events[0].aggregate_type
        aggregate_class = self._get_aggregate_class(aggregate_type)
        aggregate = aggregate_class(aggregate_id)
        aggregate.load_from_history(events)
        
        return aggregate
    
    def _get_aggregate_class(self, aggregate_type: str) -> type:
        """Resolve aggregate class from type name."""
        registry = {
            "Order": Order,
            "Customer": Customer,
            "Inventory": Inventory,
        }
        cls = registry.get(aggregate_type)
        if not cls:
            raise ValueError(f"Unknown aggregate type: {aggregate_type}")
        return cls
```

### 6.3 Temporal Queries

```python
class TemporalQueryService:
    """
    Answer "what was the state at time T?" questions using event replay.
    """
    
    def __init__(self, event_store: EventStoreRepository):
        self._event_store = event_store
    
    async def get_state_at(self, aggregate_id: UUID, 
                           at_time: datetime) -> Optional[dict]:
        """Reconstruct aggregate state as of a specific point in time."""
        events = await self._event_store.load(aggregate_id)
        
        # Filter events that occurred at or before the target time
        relevant = [e for e in events if e.occurred_at <= at_time]
        
        if not relevant:
            return None
        
        # Replay to get state
        # (In production, use a state builder that captures intermediate state)
        aggregate_type = relevant[0].aggregate_type
        aggregate_class = self._get_aggregate_class(aggregate_type)
        aggregate = aggregate_class(aggregate_id)
        aggregate.load_from_history(relevant)
        
        return self._extract_state(aggregate)
    
    async def get_state_at_version(self, aggregate_id: UUID,
                                    version: int) -> Optional[dict]:
        """Reconstruct aggregate state at a specific version."""
        events = await self._event_store.load(aggregate_id, to_version=version)
        
        if not events:
            return None
        
        aggregate_type = events[0].aggregate_type
        aggregate_class = self._get_aggregate_class(aggregate_type)
        aggregate = aggregate_class(aggregate_id)
        aggregate.load_from_history(events)
        
        return self._extract_state(aggregate)
    
    async def get_history(self, aggregate_id: UUID,
                          from_time: Optional[datetime] = None,
                          to_time: Optional[datetime] = None) -> List[dict]:
        """Get the event history for an aggregate within a time range."""
        events = await self._event_store.load(aggregate_id)
        
        result = []
        for event in events:
            if from_time and event.occurred_at < from_time:
                continue
            if to_time and event.occurred_at > to_time:
                continue
            result.append({
                "event_type": event.event_type,
                "event_version": event.event_version,
                "occurred_at": event.occurred_at.isoformat(),
                "payload": event.payload,
            })
        
        return result
```

### 6.4 Replay API

```python
from fastapi import FastAPI, Query, HTTPException
from typing import Optional, List
from datetime import datetime
from uuid import UUID

app = FastAPI(title="APEX-OS Event Replay API")


@app.post("/api/v1/replay/full")
async def full_replay(
    projections: Optional[List[str]] = None,
    batch_size: int = Query(default=1000, ge=100, le=10000),
):
    """Trigger a full replay of all events to rebuild projections."""
    service = EventReplayService(event_store, projections_list, read_db)
    stats = await service.full_replay(projection_names=projections, batch_size=batch_size)
    return stats


@app.post("/api/v1/replay/point-in-time")
async def replay_point_in_time(
    target_time: datetime,
    projections: Optional[List[str]] = None,
):
    """Replay events up to a specific point in time."""
    service = EventReplayService(event_store, projections_list, read_db)
    stats = await service.replay_to_point_in_time(target_time, projections)
    return stats


@app.get("/api/v1/replay/aggregate/{aggregate_id}")
async def replay_aggregate(
    aggregate_id: UUID,
    to_version: Optional[int] = None,
):
    """Replay events for a single aggregate."""
    service = EventReplayService(event_store, projections_list, read_db)
    aggregate = await service.replay_aggregate(aggregate_id, to_version)
    return {
        "aggregate_id": str(aggregate.id),
        "version": aggregate.version,
        "state": service._extract_state(aggregate),
    }


@app.get("/api/v1/temporal/{aggregate_id}/state")
async def get_state_at_time(
    aggregate_id: UUID,
    at_time: datetime,
):
    """Get the state of an aggregate at a specific point in time."""
    service = TemporalQueryService(event_store)
    state = await service.get_state_at(aggregate_id, at_time)
    if state is None:
        raise HTTPException(status_code=404, detail="No state found")
    return state


@app.get("/api/v1/temporal/{aggregate_id}/history")
async def get_aggregate_history(
    aggregate_id: UUID,
    from_time: Optional[datetime] = None,
    to_time: Optional[datetime] = None,
):
    """Get event history for an aggregate within a time range."""
    service = TemporalQueryService(event_store)
    history = await service.get_history(aggregate_id, from_time, to_time)
    return {"aggregate_id": str(aggregate_id), "events": history}
```

### 6.5 Replay Best Practices

| Practice | Description |
|----------|-------------|
| **Idempotent projections** | Projections must produce the same result regardless of how many times they process an event |
| **Batch processing** | Process events in batches for throughput; commit offsets periodically |
| **Parallel replay** | Partition events by aggregate_id for parallel processing across workers |
| **Checkpointing** | Save replay progress to resume after interruption |
| **Shadow replay** | Run replay against a staging read model before swapping to production |
| **Versioned projections** | When changing projection logic, version the read model and migrate gradually |
| **Monitoring** | Track replay progress, lag, and failure rates with metrics and alerts |

---

## 7. Implementation Reference

### 7.1 Project Structure

```
apex-os-business-platform/
├── src/
│   ├── events/
│   │   ├── __init__.py
│   │   ├── event.py              # DomainEvent, AggregateRoot
│   │   ├── store.py              # EventStoreRepository
│   │   ├── snapshots.py          # SnapshotStore
│   │   └── bus.py                # EventBus (Kafka)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── base.py               # Command, CommandHandler
│   │   ├── order.py              # Order commands
│   │   └── inventory.py          # Inventory commands
│   ├── queries/
│   │   ├── __init__.py
│   │   ├── base.py               # QueryService
│   │   ├── order.py              # Order queries
│   │   └── customer.py           # Customer queries
│   ├── projections/
│   │   ├── __init__.py
│   │   ├── base.py               # Projection base
│   │   ├── order_summary.py      # Order summary projection
│   │   └── customer_history.py   # Customer history projection
│   ├── sagas/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # SagaOrchestrator
│   │   ├── definitions.py        # Saga definitions
│   │   └── recover.py            # Saga recovery
│   ├── streaming/
│   │   ├── __init__.py
│   │   ├── publisher.py          # KafkaEventBus
│   │   ├── consumer.py           # EventConsumer
│   │   └── cdc.py                # Debezium CDC config
│   ├── replay/
│   │   ├── __init__.py
│   │   ├── service.py            # EventReplayService
│   │   ├── temporal.py           # TemporalQueryService
│   │   └── api.py                # Replay REST API
│   └── aggregates/
│       ├── __init__.py
│       ├── order.py              # Order aggregate
│       ├── customer.py           # Customer aggregate
│       └── inventory.py          # Inventory aggregate
├── tests/
│   ├── unit/
│   │   ├── test_aggregates.py
│   │   ├── test_projections.py
│   │   └── test_sagas.py
│   ├── integration/
│   │   ├── test_event_store.py
│   │   ├── test_cqrs.py
│   │   └── test_replay.py
│   └── e2e/
│       └── test_order_flow.py
├── docs/
│   └── event-driven.md           # This document
├── docker-compose.yml            # Local dev environment
└── pyproject.toml
```

### 7.2 Docker Compose (Local Development)

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: apex_event_store
      POSTGRES_USER: apex
      POSTGRES_PASSWORD: apex_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/sql
      - ./src/events/migrations:/docker-entrypoint-initdb.d

  kafka:
    image: redpandadata/redpanda:latest
    command:
      - redpanda start
      - --smp 1
      - --memory 1G
      - --overprovisioned
      - --node-id 0
      - --kafka-addr PLAINTEXT://0.0.0.0:9092
      - --advertise-kafka-addr PLAINTEXT://localhost:9092
    ports:
      - "9092:9092"
      - "9644:9644"  # Admin API

  kafka-init:
    image: redpandadata/redpanda:latest
    depends_on:
      - kafka
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        sleep 5
        rpk topic create apex.events.order --partitions 12 --replicas 1 || true
        rpk topic create apex.events.inventory --partitions 6 --replicas 1 || true
        rpk topic create apex.events.payment --partitions 6 --replicas 1 || true
        rpk topic create apex.events.shipping --partitions 6 --replicas 1 || true
        rpk topic create apex.events.customer --partitions 6 --replicas 1 || true
        rpk topic create apex.events.audit --partitions 3 --replicas 1 || true
        rpk topic create apex.dead-letter --partitions 3 --replicas 1 || true

  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://apex:apex_dev_password@postgres:5432/apex_event_store
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    depends_on:
      - postgres
      - kafka

  projection-worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["python", "-m", "src.projections.worker"]
    environment:
      DATABASE_URL: postgresql://apex:apex_dev_password@postgres:5432/apex_event_store
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    depends_on:
      - postgres
      - kafka

volumes:
  postgres_data:
```

### 7.3 Configuration

```yaml
# config/events.yaml
event_store:
  database_url: ${DATABASE_URL}
  snapshot_frequency: 50
  batch_size: 1000

event_bus:
  type: kafka
  bootstrap_servers: ${KAFKA_BOOTSTRAP_SERVERS}
  client_id: apex-event-bus
  enable_idempotence: true
  acks: all
  retries: 5
  compression: lz4

projections:
  - name: OrderSummaryProjection
    topics: [apex.events.order]
    consumer_group: order-summary-projection
  - name: CustomerOrderHistoryProjection
    topics: [apex.events.order]
    consumer_group: customer-history-projection
  - name: ProductSalesProjection
    topics: [apex.events.order]
    consumer_group: product-sales-projection

sagas:
  recovery:
    enabled: true
    interval_seconds: 30
  timeout_seconds: 300

replay:
  batch_size: 1000
  checkpoint_interval: 10000
  max_retries: 3
  dead_letter_topic: apex.dead-letter

streaming:
  cdc:
    enabled: true
    connector: debezium
    publication: dbz_publication
  stream_processor:
    type: faust
    broker: ${KAFKA_BOOTSTRAP_SERVERS}
```

---

## 8. Operational Concerns

### 8.1 Monitoring

| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| `event_store.write_latency` | Histogram | p99 > 100ms |
| `event_bus.publish_latency` | Histogram | p99 > 50ms |
| `projection.lag_seconds` | Gauge | > 30s |
| `projection.processing_rate` | Counter | < 100 events/s |
| `saga.failure_rate` | Counter | > 1% |
| `saga.compensation_failure` | Counter | > 0 (page immediately) |
| `replay.progress` | Gauge | Stalled > 5min |
| `dead_letter.queue_size` | Gauge | > 100 |

### 8.2 Testing Strategy

```python
# Unit test: Aggregate behavior
async def test_order_place_confirm_ship_flow():
    order = Order(uuid4())
    order.place(customer_id=uuid4(), items=[
        {"sku": "WIDGET-001", "quantity": 2, "unit_price": 29.99}
    ])
    order.confirm()
    order.ship(tracking_number="TRACK-123")
    
    assert order.version == 3
    assert order._status == "shipped"
    assert len(order.get_uncommitted_events()) == 3


# Integration test: Event store round-trip
async def test_event_store_append_and_load():
    repo = EventStoreRepository(pool)
    order = Order(uuid4())
    order.place(customer_id=uuid4(), items=[
        {"sku": "WIDGET-001", "quantity": 1, "unit_price": 10.00}
    ])
    
    events = order.get_uncommitted_events()
    await repo.append(events, expected_version=0)
    order.mark_committed()
    
    loaded = await repo.load(order.id)
    assert len(loaded) == 1
    assert loaded[0].event_type == "OrderPlaced"


# Integration test: Projection rebuild
async def test_projection_full_replay():
    # Seed events
    for i in range(100):
        order = Order(uuid4())
        order.place(customer_id=uuid4(), items=[
            {"sku": f"SKU-{i}", "quantity": 1, "unit_price": 10.00}
        ])
        events = order.get_uncommitted_events()
        await event_store.append(events, expected_version=0)
        order.mark_committed()
    
    # Full replay
    projection = OrderSummaryProjection(read_db)
    service = EventReplayService(event_store, [projection], read_db)
    stats = await service.full_replay()
    
    assert stats["failed_events"] == 0
    count = await read_db.fetchval("SELECT COUNT(*) FROM order_summary")
    assert count == 100


# E2E test: Order fulfillment saga
async def test_order_fulfillment_saga_happy_path():
    orchestrator = SagaOrchestrator(db_pool, command_gateway)
    saga = await orchestrator.start_saga(
        "OrderFulfillment",
        context={
            "order_id": str(order_id),
            "customer_id": str(customer_id),
            "items": [{"sku": "WIDGET-001", "quantity": 2, "unit_price": 29.99}],
            "total": 59.98,
        },
    )
    
    # Wait for saga completion
    await asyncio.wait_for(
        wait_for_saga_completion(saga.saga_id),
        timeout=30,
    )
    
    saga = await orchestrator._load_saga(saga.saga_id)
    assert saga.status == SagaStatus.COMPLETED
    assert all(s.status == SagaStepStatus.SUCCEEDED for s in saga.steps)
```

### 8.3 Deployment Checklist

- [ ] Event store database migrated and indexed
- [ ] Kafka/Redpanda topics created with correct partition counts
- [ ] CDC connector configured and running
- [ ] Projection workers deployed with consumer groups
- [ ] Saga orchestrator deployed with recovery enabled
- [ ] Dead-letter topic monitored with alerting
- [ ] Replay API accessible to ops team
- [ ] Monitoring dashboards configured
- [ ] Runbooks written for common failure scenarios
- [ ] Load tests validate throughput requirements
- [ ] Disaster recovery plan tested (event store backup, Kafka replication)

### 8.4 Failure Scenarios and Recovery

| Scenario | Impact | Recovery |
|----------|--------|----------|
| Projection bug | Read model incorrect | Fix code, trigger full replay |
| Kafka unavailable | Events not streamed | Events accumulate in event store; replay when Kafka returns |
| Saga step fails | Partial execution | Automatic compensation; alert if compensation fails |
| Event store unavailable | Writes blocked | Retry with backoff; alert if persistent |
| Poison pill message | Consumer stuck | Dead-letter topic; manual inspection and reprocessing |
| Snapshot corruption | Slow aggregate load | Delete snapshot; replay from events |
| CDC lag | Delayed streaming | Monitor lag; scale CDC connectors |

---

## Appendix A: Event Catalog

| Event Type | Aggregate | Payload Fields | Description |
|------------|-----------|----------------|-------------|
| `OrderPlaced` | Order | customer_id, items, currency | Order created by customer |
| `OrderConfirmed` | Order | — | Order confirmed by system |
| `OrderShipped` | Order | tracking_number | Order shipped to customer |
| `OrderCancelled` | Order | reason | Order cancelled |
| `InventoryReserved` | Inventory | order_id, items | Stock reserved for order |
| `InventoryReleased` | Inventory | order_id, items | Reserved stock released |
| `PaymentProcessed` | Payment | order_id, amount, transaction_id | Payment captured |
| `PaymentFailed` | Payment | order_id, reason, error_code | Payment attempt failed |
| `PaymentRefunded` | Payment | order_id, amount, transaction_id | Payment refunded |
| `ShipmentCreated` | Shipping | order_id, carrier, tracking_number | Shipment label created |
| `ShipmentCancelled` | Shipping | order_id, tracking_number | Shipment cancelled |
| `CustomerCreated` | Customer | name, email, address | New customer registered |
| `CustomerUpdated` | Customer | fields_changed | Customer profile updated |

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **Event Sourcing** | Persisting state as a sequence of immutable events |
| **CQRS** | Separating read and write models |
| **Saga** | A sequence of local transactions with compensating actions |
| **Projection** | A read model built by processing events |
| **Replay** | Rebuilding state by reprocessing events |
| **Aggregate** | A cluster of domain objects treated as a single unit for data changes |
| **Command** | An intent to change system state |
| **Query** | A request for data that does not change state |
| **Correlation ID** | Links all events in a single business transaction |
| **Causation ID** | Links a response event to the event that caused it |
| **Snapshot** | A point-in-time save of aggregate state to avoid full replay |
| **CDC** | Change Data Capture — streaming database changes to downstream systems |
| **Dead Letter Queue** | A topic for messages that could not be processed |
