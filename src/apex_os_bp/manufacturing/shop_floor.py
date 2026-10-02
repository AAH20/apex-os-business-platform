"""Shop Floor Control module."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class ShopFloorError(Exception):
    """Shop floor error."""
    pass


class WorkOrderStatus(Enum):
    """Work order status."""
    CREATED = "created"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class OperationStatus(Enum):
    """Operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class Operation:
    """A single operation in a work order."""
    sequence: int
    description: str
    work_center_id: str
    setup_time_minutes: float = 0.0
    run_time_minutes: float = 0.0
    status: OperationStatus = OperationStatus.PENDING
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actual_setup_minutes: float = 0.0
    actual_run_minutes: float = 0.0
    completed_quantity: float = 0.0
    defect_quantity: float = 0.0

    def total_standard_time(self) -> float:
        """Total standard time in minutes."""
        return self.setup_time_minutes + self.run_time_minutes

    def total_actual_time(self) -> float:
        """Total actual time in minutes."""
        return self.actual_setup_minutes + self.actual_run_minutes

    def efficiency(self) -> float:
        """Calculate operation efficiency."""
        standard = self.total_standard_time()
        if standard == 0:
            return 1.0
        actual = self.total_actual_time()
        if actual == 0:
            return 1.0
        return standard / actual

    def start(self) -> None:
        """Start the operation."""
        if self.status != OperationStatus.PENDING:
            raise ShopFloorError(f"Cannot start operation in status: {self.status.value}")
        self.status = OperationStatus.IN_PROGRESS

    def complete(self, completed_qty: float, defect_qty: float = 0.0) -> None:
        """Complete the operation."""
        if self.status != OperationStatus.IN_PROGRESS:
            raise ShopFloorError(f"Cannot complete operation in status: {self.status.value}")
        self.status = OperationStatus.COMPLETED
        self.completed_quantity = completed_qty
        self.defect_quantity = defect_qty


@dataclass
class WorkOrder:
    """A shop floor work order."""
    product_id: str
    product_name: str
    quantity: float
    status: WorkOrderStatus = WorkOrderStatus.CREATED
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operations: List[Operation] = field(default_factory=list)
    production_order_id: str = ""
    dispatch_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    completed_quantity: float = 0.0
    defect_quantity: float = 0.0
    notes: str = ""

    def add_operation(self, operation: Operation) -> None:
        """Add an operation to the work order."""
        self.operations.append(operation)
        self.operations.sort(key=lambda op: op.sequence)

    def dispatch(self) -> None:
        """Dispatch the work order to the shop floor."""
        if self.status != WorkOrderStatus.CREATED:
            raise ShopFloorError(f"Cannot dispatch work order in status: {self.status.value}")
        self.status = WorkOrderStatus.DISPATCHED
        self.dispatch_date = datetime.now()

    def start(self) -> None:
        """Start the work order."""
        if self.status != WorkOrderStatus.DISPATCHED:
            raise ShopFloorError(f"Cannot start work order in status: {self.status.value}")
        self.status = WorkOrderStatus.IN_PROGRESS
        self.start_date = datetime.now()

    def complete(self, completed_qty: float, defect_qty: float = 0.0) -> None:
        """Complete the work order."""
        if self.status != WorkOrderStatus.IN_PROGRESS:
            raise ShopFloorError(f"Cannot complete work order in status: {self.status.value}")
        self.status = WorkOrderStatus.COMPLETED
        self.completion_date = datetime.now()
        self.completed_quantity = completed_qty
        self.defect_quantity = defect_qty

    def close(self) -> None:
        """Close the work order."""
        if self.status != WorkOrderStatus.COMPLETED:
            raise ShopFloorError(f"Cannot close work order in status: {self.status.value}")
        self.status = WorkOrderStatus.CLOSED

    def current_operation(self) -> Optional[Operation]:
        """Get the current active operation."""
        for op in self.operations:
            if op.status in (OperationStatus.PENDING, OperationStatus.IN_PROGRESS):
                return op
        return None

    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.operations:
            return 0.0
        completed = sum(1 for op in self.operations if op.status == OperationStatus.COMPLETED)
        return (completed / len(self.operations)) * 100.0

    def total_standard_time(self) -> float:
        """Total standard time for all operations."""
        return sum(op.total_standard_time() for op in self.operations)

    def total_actual_time(self) -> float:
        """Total actual time for all operations."""
        return sum(op.total_actual_time() for op in self.operations)


class ShopFloor:
    """Engine for shop floor control."""

    def __init__(self):
        self._work_orders: Dict[str, WorkOrder] = {}

    def create_work_order(
        self,
        product_id: str,
        product_name: str,
        quantity: float,
        production_order_id: str = "",
    ) -> WorkOrder:
        """Create a new work order."""
        wo = WorkOrder(
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            production_order_id=production_order_id,
        )
        self._work_orders[wo.id] = wo
        return wo

    def get_work_order(self, wo_id: str) -> Optional[WorkOrder]:
        """Get a work order by ID."""
        return self._work_orders.get(wo_id)

    def dispatch_work_order(self, wo_id: str) -> None:
        """Dispatch a work order."""
        wo = self._work_orders.get(wo_id)
        if not wo:
            raise ShopFloorError(f"Work order not found: {wo_id}")
        wo.dispatch()

    def start_work_order(self, wo_id: str) -> None:
        """Start a work order."""
        wo = self._work_orders.get(wo_id)
        if not wo:
            raise ShopFloorError(f"Work order not found: {wo_id}")
        wo.start()

    def complete_work_order(self, wo_id: str, completed_qty: float, defect_qty: float = 0.0) -> None:
        """Complete a work order."""
        wo = self._work_orders.get(wo_id)
        if not wo:
            raise ShopFloorError(f"Work order not found: {wo_id}")
        wo.complete(completed_qty, defect_qty)

    def close_work_order(self, wo_id: str) -> None:
        """Close a work order."""
        wo = self._work_orders.get(wo_id)
        if not wo:
            raise ShopFloorError(f"Work order not found: {wo_id}")
        wo.close()

    def get_work_orders_by_status(self, status: WorkOrderStatus) -> List[WorkOrder]:
        """Get work orders by status."""
        return [wo for wo in self._work_orders.values() if wo.status == status]

    def get_active_work_orders(self) -> List[WorkOrder]:
        """Get all active (in-progress) work orders."""
        return [
            wo for wo in self._work_orders.values()
            if wo.status in (WorkOrderStatus.DISPATCHED, WorkOrderStatus.IN_PROGRESS)
        ]

    def get_work_orders_by_product(self, product_id: str) -> List[WorkOrder]:
        """Get work orders for a product."""
        return [wo for wo in self._work_orders.values() if wo.product_id == product_id]

    def average_efficiency(self) -> float:
        """Calculate average efficiency across all operations."""
        total_standard = 0.0
        total_actual = 0.0
        for wo in self._work_orders.values():
            total_standard += wo.total_standard_time()
            total_actual += wo.total_actual_time()
        if total_actual == 0:
            return 1.0
        return total_standard / total_actual

    def list_work_orders(self) -> List[WorkOrder]:
        """List all work orders."""
        return list(self._work_orders.values())
