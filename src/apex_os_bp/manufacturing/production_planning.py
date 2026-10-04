"""Production Planning module."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class PlanningError(Exception):
    """Production planning error."""


class OrderStatus(Enum):
    """Production order status."""
    PLANNED = "planned"
    RELEASED = "released"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkCenterType(Enum):
    """Type of work center."""
    MACHINING = "machining"
    ASSEMBLY = "assembly"
    PACKAGING = "packaging"
    QUALITY = "quality"
    MAINTENANCE = "maintenance"


@dataclass
class WorkCenter:
    """A production work center or resource."""
    name: str
    work_center_type: WorkCenterType = WorkCenterType.MACHINING
    capacity_per_hour: float = 1.0
    efficiency: float = 1.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_load: float = 0.0
    is_active: bool = True

    def available_capacity(self) -> float:
        """Remaining available capacity."""
        return max(0.0, self.capacity_per_hour * self.efficiency - self.current_load)

    def allocate(self, hours: float) -> bool:
        """Allocate hours to this work center."""
        if hours > self.available_capacity():
            return False
        self.current_load += hours
        return True

    def release(self, hours: float) -> None:
        """Release allocated hours."""
        self.current_load = max(0.0, self.current_load - hours)


@dataclass
class ProductionOrder:
    """A production order for manufacturing."""
    product_id: str
    product_name: str
    quantity: float
    due_date: datetime
    status: OrderStatus = OrderStatus.PLANNED
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bom_id: str = ""
    work_center_id: str = ""
    priority: int = 5
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    notes: str = ""

    def release(self) -> None:
        """Release the order for production."""
        if self.status != OrderStatus.PLANNED:
            raise PlanningError(f"Cannot release order in status: {self.status.value}")
        self.status = OrderStatus.RELEASED

    def start(self) -> None:
        """Mark order as started."""
        if self.status != OrderStatus.RELEASED:
            raise PlanningError(f"Cannot start order in status: {self.status.value}")
        self.status = OrderStatus.IN_PROGRESS
        self.actual_start = datetime.now()

    def complete(self) -> None:
        """Mark order as completed."""
        if self.status != OrderStatus.IN_PROGRESS:
            raise PlanningError(f"Cannot complete order in status: {self.status.value}")
        self.status = OrderStatus.COMPLETED
        self.actual_end = datetime.now()

    def cancel(self) -> None:
        """Cancel the order."""
        if self.status in (OrderStatus.COMPLETED,):
            raise PlanningError("Cannot cancel completed order")
        self.status = OrderStatus.CANCELLED

    def is_overdue(self) -> bool:
        """Check if order is past due date."""
        if self.status == OrderStatus.COMPLETED:
            return False
        return datetime.now() > self.due_date

    def lead_time_hours(self) -> float:
        """Calculate lead time in hours."""
        if self.scheduled_start and self.scheduled_end:
            delta = self.scheduled_end - self.scheduled_start
            return delta.total_seconds() / 3600.0
        return 0.0


class ProductionPlanner:
    """Engine for production planning and scheduling."""

    def __init__(self):
        self._orders: Dict[str, ProductionOrder] = {}
        self._work_centers: Dict[str, WorkCenter] = {}

    def add_work_center(self, wc: WorkCenter) -> None:
        """Register a work center."""
        self._work_centers[wc.id] = wc

    def get_work_center(self, wc_id: str) -> Optional[WorkCenter]:
        """Get a work center by ID."""
        return self._work_centers.get(wc_id)

    def create_order(
        self,
        product_id: str,
        product_name: str,
        quantity: float,
        due_date: datetime,
        priority: int = 5,
        bom_id: str = "",
    ) -> ProductionOrder:
        """Create a new production order."""
        order = ProductionOrder(
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            due_date=due_date,
            priority=priority,
            bom_id=bom_id,
        )
        self._orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Optional[ProductionOrder]:
        """Get a production order by ID."""
        return self._orders.get(order_id)

    def schedule_order(
        self,
        order_id: str,
        work_center_id: str,
        start_time: datetime,
        hours: float,
    ) -> bool:
        """Schedule an order on a work center."""
        order = self._orders.get(order_id)
        if not order:
            raise PlanningError(f"Order not found: {order_id}")

        wc = self._work_centers.get(work_center_id)
        if not wc:
            raise PlanningError(f"Work center not found: {work_center_id}")

        if not wc.allocate(hours):
            return False

        order.work_center_id = work_center_id
        order.scheduled_start = start_time
        order.scheduled_end = start_time + timedelta(hours=hours)
        return True

    def get_orders_by_status(self, status: OrderStatus) -> List[ProductionOrder]:
        """Get all orders with a given status."""
        return [o for o in self._orders.values() if o.status == status]

    def get_overdue_orders(self) -> List[ProductionOrder]:
        """Get all overdue orders."""
        return [o for o in self._orders.values() if o.is_overdue()]

    def capacity_check(self, work_center_id: str, hours: float) -> bool:
        """Check if a work center has available capacity."""
        wc = self._work_centers.get(work_center_id)
        if not wc:
            return False
        return wc.available_capacity() >= hours

    def utilization_rate(self, work_center_id: str) -> float:
        """Calculate utilization rate for a work center."""
        wc = self._work_centers.get(work_center_id)
        if not wc:
            return 0.0
        max_capacity = wc.capacity_per_hour * wc.efficiency
        if max_capacity == 0:
            return 0.0
        return wc.current_load / max_capacity

    def list_orders(self) -> List[ProductionOrder]:
        """List all production orders."""
        return list(self._orders.values())

    def list_work_centers(self) -> List[WorkCenter]:
        """List all work centers."""
        return list(self._work_centers.values())
