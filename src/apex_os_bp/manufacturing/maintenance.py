"""Maintenance Management module."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class MaintenanceError(Exception):
    """Maintenance error."""


class AssetStatus(Enum):
    """Asset operational status."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"
    UNDER_MAINTENANCE = "under_maintenance"
    RETIRED = "retired"


class MaintenanceType(Enum):
    """Type of maintenance."""
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    PREDICTIVE = "predictive"
    EMERGENCY = "emergency"


class MaintenancePriority(Enum):
    """Maintenance priority."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class MaintenanceOrderStatus(Enum):
    """Maintenance order status."""
    OPEN = "open"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Asset:
    """A maintainable asset or equipment."""
    name: str
    asset_type: str
    location: str
    status: AssetStatus = AssetStatus.OPERATIONAL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    serial_number: str = ""
    manufacturer: str = ""
    model: str = ""
    install_date: Optional[datetime] = None
    last_maintenance_date: Optional[datetime] = None
    next_scheduled_maintenance: Optional[datetime] = None
    total_operating_hours: float = 0.0
    maintenance_interval_hours: float = 500.0
    notes: str = ""

    def is_due_for_maintenance(self) -> bool:
        """Check if asset is due for preventive maintenance."""
        if self.next_scheduled_maintenance:
            return datetime.now() >= self.next_scheduled_maintenance
        if self.last_maintenance_date and self.maintenance_interval_hours > 0:
            hours_since = self.total_operating_hours
            # Simplified: check if interval exceeded
            return hours_since >= self.maintenance_interval_hours
        return False

    def record_maintenance(self, hours: float = 0.0) -> None:
        """Record maintenance completion."""
        self.last_maintenance_date = datetime.now()
        self.next_scheduled_maintenance = datetime.now() + timedelta(hours=self.maintenance_interval_hours)
        self.status = AssetStatus.OPERATIONAL

    def add_operating_hours(self, hours: float) -> None:
        """Add operating hours to the asset."""
        self.total_operating_hours += hours

    def set_status(self, status: AssetStatus) -> None:
        """Set asset status."""
        self.status = status


@dataclass
class MaintenanceOrder:
    """A maintenance work order."""
    asset_id: str
    maintenance_type: MaintenanceType
    priority: MaintenancePriority
    description: str
    status: MaintenanceOrderStatus = MaintenanceOrderStatus.OPEN
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scheduled_date: Optional[datetime] = None
    started_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    assigned_technician: str = ""
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    parts_cost: float = 0.0
    labor_cost: float = 0.0
    downtime_hours: float = 0.0
    notes: str = ""

    def schedule(self, date: datetime, technician: str = "") -> None:
        """Schedule the maintenance order."""
        if self.status != MaintenanceOrderStatus.OPEN:
            raise MaintenanceError(f"Cannot schedule order in status: {self.status.value}")
        self.status = MaintenanceOrderStatus.SCHEDULED
        self.scheduled_date = date
        self.assigned_technician = technician

    def start(self) -> None:
        """Start the maintenance work."""
        if self.status != MaintenanceOrderStatus.SCHEDULED:
            raise MaintenanceError(f"Cannot start order in status: {self.status.value}")
        self.status = MaintenanceOrderStatus.IN_PROGRESS
        self.started_date = datetime.now()

    def complete(self, actual_hours: float, downtime_hours: float = 0.0) -> None:
        """Complete the maintenance order."""
        if self.status != MaintenanceOrderStatus.IN_PROGRESS:
            raise MaintenanceError(f"Cannot complete order in status: {self.status.value}")
        self.status = MaintenanceOrderStatus.COMPLETED
        self.completed_date = datetime.now()
        self.actual_hours = actual_hours
        self.downtime_hours = downtime_hours

    def cancel(self) -> None:
        """Cancel the maintenance order."""
        if self.status in (MaintenanceOrderStatus.COMPLETED,):
            raise MaintenanceError("Cannot cancel completed order")
        self.status = MaintenanceOrderStatus.CANCELLED

    def total_cost(self) -> float:
        """Total maintenance cost."""
        return self.parts_cost + self.labor_cost


class MaintenancePlanner:
    """Engine for maintenance management."""

    def __init__(self):
        self._assets: Dict[str, Asset] = {}
        self._orders: Dict[str, MaintenanceOrder] = {}

    def add_asset(self, asset: Asset) -> None:
        """Register an asset."""
        self._assets[asset.id] = asset

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get an asset by ID."""
        return self._assets.get(asset_id)

    def create_order(
        self,
        asset_id: str,
        maintenance_type: MaintenanceType,
        priority: MaintenancePriority,
        description: str,
        estimated_hours: float = 0.0,
    ) -> MaintenanceOrder:
        """Create a maintenance order."""
        asset = self._assets.get(asset_id)
        if not asset:
            raise MaintenanceError(f"Asset not found: {asset_id}")

        order = MaintenanceOrder(
            asset_id=asset_id,
            maintenance_type=maintenance_type,
            priority=priority,
            description=description,
            estimated_hours=estimated_hours,
        )
        self._orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Optional[MaintenanceOrder]:
        """Get a maintenance order by ID."""
        return self._orders.get(order_id)

    def schedule_order(
        self,
        order_id: str,
        date: datetime,
        technician: str = "",
    ) -> None:
        """Schedule a maintenance order."""
        order = self._orders.get(order_id)
        if not order:
            raise MaintenanceError(f"Order not found: {order_id}")
        order.schedule(date, technician)

    def start_order(self, order_id: str) -> None:
        """Start a maintenance order."""
        order = self._orders.get(order_id)
        if not order:
            raise MaintenanceError(f"Order not found: {order_id}")
        order.start()
        asset = self._assets.get(order.asset_id)
        if asset:
            asset.set_status(AssetStatus.UNDER_MAINTENANCE)

    def complete_order(
        self,
        order_id: str,
        actual_hours: float,
        downtime_hours: float = 0.0,
    ) -> None:
        """Complete a maintenance order."""
        order = self._orders.get(order_id)
        if not order:
            raise MaintenanceError(f"Order not found: {order_id}")
        order.complete(actual_hours, downtime_hours)
        asset = self._assets.get(order.asset_id)
        if asset:
            asset.record_maintenance(actual_hours)

    def get_orders_by_status(self, status: MaintenanceOrderStatus) -> List[MaintenanceOrder]:
        """Get orders by status."""
        return [o for o in self._orders.values() if o.status == status]

    def get_orders_by_asset(self, asset_id: str) -> List[MaintenanceOrder]:
        """Get orders for an asset."""
        return [o for o in self._orders.values() if o.asset_id == asset_id]

    def get_orders_by_type(self, mtype: MaintenanceType) -> List[MaintenanceOrder]:
        """Get orders by maintenance type."""
        return [o for o in self._orders.values() if o.maintenance_type == mtype]

    def get_open_orders(self) -> List[MaintenanceOrder]:
        """Get all open orders."""
        return [
            o for o in self._orders.values()
            if o.status in (
                MaintenanceOrderStatus.OPEN,
                MaintenanceOrderStatus.SCHEDULED,
                MaintenanceOrderStatus.IN_PROGRESS
            )
        ]

    def get_due_preventive_maintenance(self) -> List[Asset]:
        """Get assets due for preventive maintenance."""
        return [a for a in self._assets.values() if a.is_due_for_maintenance()]

    def get_asset_uptime(self, asset_id: str) -> float:
        """Calculate asset uptime percentage."""
        asset = self._assets.get(asset_id)
        if not asset:
            return 0.0
        orders = self.get_orders_by_asset(asset_id)
        total_downtime = sum(o.downtime_hours for o in orders if o.status == MaintenanceOrderStatus.COMPLETED)
        total_hours = asset.total_operating_hours
        if total_hours == 0:
            return 100.0
        uptime = ((total_hours - total_downtime) / total_hours) * 100.0
        return max(0.0, min(100.0, uptime))

    def total_maintenance_cost(self) -> float:
        """Total cost of all maintenance orders."""
        return sum(o.total_cost() for o in self._orders.values())

    def list_assets(self) -> List[Asset]:
        """List all assets."""
        return list(self._assets.values())

    def list_orders(self) -> List[MaintenanceOrder]:
        """List all maintenance orders."""
        return list(self._orders.values())
