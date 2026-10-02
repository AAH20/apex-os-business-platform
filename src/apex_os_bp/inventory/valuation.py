"""Inventory valuation."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from apex_os_bp.inventory.models import ValuationMethod


class InventoryValuation:
    """Inventory valuation using various methods."""

    def __init__(self):
        # Track cost layers: list of (quantity, unit_cost) tuples per product
        self._cost_layers: Dict[str, List[Tuple[int, float]]] = {}

    def add_cost_layer(self, product_id: str, quantity: int, unit_cost: float) -> None:
        """Add a cost layer (e.g., from a purchase receipt)."""
        if product_id not in self._cost_layers:
            self._cost_layers[product_id] = []
        self._cost_layers[product_id].append((quantity, unit_cost))

    def remove_cost_layer(
        self,
        product_id: str,
        quantity: int,
        method: ValuationMethod = ValuationMethod.FIFO,
    ) -> float:
        """Remove quantity from cost layers, returning total cost."""
        if product_id not in self._cost_layers:
            raise ValueError(f"No cost layers for product: {product_id}")

        layers = self._cost_layers[product_id]
        total_cost = 0.0
        remaining = quantity

        if method == ValuationMethod.FIFO:
            # First in, first out - remove from oldest layers
            while remaining > 0 and layers:
                layer_qty, layer_cost = layers[0]
                if layer_qty <= remaining:
                    total_cost += layer_qty * layer_cost
                    remaining -= layer_qty
                    layers.pop(0)
                else:
                    total_cost += remaining * layer_cost
                    layers[0] = (layer_qty - remaining, layer_cost)
                    remaining = 0
        elif method == ValuationMethod.LIFO:
            # Last in, first out - remove from newest layers
            while remaining > 0 and layers:
                layer_qty, layer_cost = layers[-1]
                if layer_qty <= remaining:
                    total_cost += layer_qty * layer_cost
                    remaining -= layer_qty
                    layers.pop()
                else:
                    total_cost += remaining * layer_cost
                    layers[-1] = (layer_qty - remaining, layer_cost)
                    remaining = 0
        elif method == ValuationMethod.WEIGHTED_AVERAGE:
            # Calculate weighted average cost
            total_qty = sum(q for q, _ in layers)
            total_layer_cost = sum(q * c for q, c in layers)
            if total_qty == 0:
                raise ValueError("No stock available for weighted average")
            avg_cost = total_layer_cost / total_qty
            total_cost = quantity * avg_cost
            # Remove proportionally from all layers
            new_layers = []
            for layer_qty, layer_cost in layers:
                new_qty = int(layer_qty * (1 - quantity / total_qty))
                if new_qty > 0:
                    new_layers.append((new_qty, layer_cost))
            self._cost_layers[product_id] = new_layers
            return total_cost
        else:
            raise ValueError(f"Unsupported valuation method: {method}")

        if remaining > 0:
            raise ValueError(f"Insufficient stock to remove {quantity}, only {quantity - remaining} available")

        return total_cost

    def get_inventory_value(
        self,
        product_id: str,
        method: ValuationMethod = ValuationMethod.FIFO,
    ) -> float:
        """Get total inventory value for a product."""
        if product_id not in self._cost_layers:
            return 0.0

        layers = self._cost_layers[product_id]

        if method == ValuationMethod.WEIGHTED_AVERAGE:
            total_qty = sum(q for q, _ in layers)
            total_cost = sum(q * c for q, c in layers)
            if total_qty == 0:
                return 0.0
            return total_cost
        elif method == ValuationMethod.STANDARD_COST:
            # Use the most recent cost as standard cost
            if not layers:
                return 0.0
            std_cost = layers[-1][1]
            total_qty = sum(q for q, _ in layers)
            return total_qty * std_cost
        else:
            # FIFO and LIFO value remaining inventory the same way
            return sum(q * c for q, c in layers)

    def get_total_inventory_value(
        self,
        method: ValuationMethod = ValuationMethod.FIFO,
    ) -> float:
        """Get total value of all inventory."""
        return sum(
            self.get_inventory_value(pid, method)
            for pid in self._cost_layers
        )

    def get_product_quantity(self, product_id: str) -> int:
        """Get total quantity in cost layers for a product."""
        if product_id not in self._cost_layers:
            return 0
        return sum(q for q, _ in self._cost_layers[product_id])

    def get_average_cost(self, product_id: str) -> float:
        """Get weighted average cost for a product."""
        if product_id not in self._cost_layers:
            return 0.0
        layers = self._cost_layers[product_id]
        total_qty = sum(q for q, _ in layers)
        if total_qty == 0:
            return 0.0
        total_cost = sum(q * c for q, c in layers)
        return total_cost / total_qty

    def get_cost_layers(self, product_id: str) -> List[Tuple[int, float]]:
        """Get cost layers for a product."""
        return list(self._cost_layers.get(product_id, []))

    def clear(self) -> None:
        """Clear all cost layers."""
        self._cost_layers.clear()
