"""Stock tracking and management."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from apex_os_bp.inventory.models import StockItem, StockMovement


class StockTracker:
    """Stock tracking across locations."""

    def __init__(self):
        # Key: (product_id, location) -> StockItem
        self._stock: Dict[Tuple[str, str], StockItem] = {}
        self._movements: List[StockMovement] = []

    def get_stock(self, product_id: str, location: str) -> Optional[StockItem]:
        """Get stock item for product at location."""
        return self._stock.get((product_id, location))

    def get_or_create_stock(self, product_id: str, location: str) -> StockItem:
        """Get existing stock or create new."""
        key = (product_id, location)
        if key not in self._stock:
            self._stock[key] = StockItem(product_id=product_id, location=location)
        return self._stock[key]

    def get_total_quantity(self, product_id: str) -> int:
        """Get total quantity across all locations."""
        return sum(
            item.quantity
            for (pid, _), item in self._stock.items()
            if pid == product_id
        )

    def get_available_quantity(self, product_id: str) -> int:
        """Get total available quantity across all locations."""
        return sum(
            item.available_quantity
            for (pid, _), item in self._stock.items()
            if pid == product_id
        )

    def get_locations(self, product_id: str) -> List[str]:
        """Get all locations where product is stocked."""
        return [
            loc for (pid, loc) in self._stock.keys()
            if pid == product_id
        ]

    def receive_stock(
        self,
        product_id: str,
        location: str,
        quantity: int,
        unit_cost: float = 0.0,
        reference: Optional[str] = None,
        lot_number: Optional[str] = None,
        notes: str = "",
    ) -> StockMovement:
        """Receive stock into a location."""
        if quantity <= 0:
            raise ValueError("Receive quantity must be positive")
        item = self.get_or_create_stock(product_id, location)
        item.adjust(quantity)
        movement = StockMovement.create(
            product_id=product_id,
            location=location,
            quantity=quantity,
            movement_type="in",
            unit_cost=unit_cost,
            reference=reference,
            notes=notes,
        )
        self._movements.append(movement)
        return movement

    def issue_stock(
        self,
        product_id: str,
        location: str,
        quantity: int,
        reference: Optional[str] = None,
        notes: str = "",
    ) -> StockMovement:
        """Issue stock from a location."""
        if quantity <= 0:
            raise ValueError("Issue quantity must be positive")
        item = self._stock.get((product_id, location))
        if not item:
            raise ValueError(f"No stock found for {product_id} at {location}")
        item.adjust(-quantity)
        movement = StockMovement.create(
            product_id=product_id,
            location=location,
            quantity=quantity,
            movement_type="out",
            reference=reference,
            notes=notes,
        )
        self._movements.append(movement)
        return movement

    def transfer_stock(
        self,
        product_id: str,
        from_location: str,
        to_location: str,
        quantity: int,
        notes: str = "",
    ) -> Tuple[StockMovement, StockMovement]:
        """Transfer stock between locations."""
        self.issue_stock(product_id, from_location, quantity, notes=notes)
        movement_in = self.receive_stock(product_id, to_location, quantity, notes=notes)
        # Get the outbound movement we just created
        movement_out = self._movements[-2]
        return movement_out, movement_in

    def reserve_stock(self, product_id: str, location: str, quantity: int) -> None:
        """Reserve stock at a location."""
        item = self._stock.get((product_id, location))
        if not item:
            raise ValueError(f"No stock found for {product_id} at {location}")
        item.reserve(quantity)

    def release_stock(self, product_id: str, location: str, quantity: int) -> None:
        """Release reserved stock at a location."""
        item = self._stock.get((product_id, location))
        if not item:
            raise ValueError(f"No stock found for {product_id} at {location}")
        item.release(quantity)

    def get_movements(
        self,
        product_id: Optional[str] = None,
        location: Optional[str] = None,
    ) -> List[StockMovement]:
        """Get stock movements, optionally filtered."""
        movements = self._movements
        if product_id:
            movements = [m for m in movements if m.product_id == product_id]
        if location:
            movements = [m for m in movements if m.location == location]
        return movements

    def get_stock_value(self, product_id: str, unit_cost: float) -> float:
        """Get total stock value for a product."""
        return self.get_total_quantity(product_id) * unit_cost

    def list_all_stock(self) -> List[StockItem]:
        """List all stock items."""
        return list(self._stock.values())

    def get_low_stock(self, reorder_point: int) -> List[StockItem]:
        """Get stock items below reorder point."""
        return [
            item for item in self._stock.values()
            if item.quantity <= reorder_point
        ]
