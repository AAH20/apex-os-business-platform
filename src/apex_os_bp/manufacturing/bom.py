"""Bill of Materials (BOM) module."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class BOMError(Exception):
    """BOM-related error."""
    pass


class BOMStatus(Enum):
    """BOM lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    OBSOLETE = "obsolete"


@dataclass
class BOMItem:
    """A single component line in a BOM."""
    component_id: str
    component_name: str
    quantity: float
    unit: str = "ea"
    scrap_factor: float = 0.0
    reference_designator: str = ""
    notes: str = ""

    def effective_quantity(self) -> float:
        """Quantity including scrap factor."""
        return self.quantity * (1.0 + self.scrap_factor)


@dataclass
class BOM:
    """Bill of Materials for a product."""
    product_id: str
    product_name: str
    version: str = "1.0"
    status: BOMStatus = BOMStatus.DRAFT
    items: List[BOMItem] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    labor_hours: float = 0.0
    machine_hours: float = 0.0
    setup_hours: float = 0.0

    def add_item(self, item: BOMItem) -> None:
        """Add a component to the BOM."""
        self.items.append(item)

    def remove_item(self, component_id: str) -> bool:
        """Remove a component from the BOM."""
        original_len = len(self.items)
        self.items = [i for i in self.items if i.component_id != component_id]
        return len(self.items) < original_len

    def total_component_quantity(self) -> float:
        """Sum of all component quantities."""
        return sum(item.quantity for item in self.items)

    def total_effective_quantity(self) -> float:
        """Sum of all effective quantities (with scrap)."""
        return sum(item.effective_quantity() for item in self.items)

    def activate(self) -> None:
        """Activate the BOM for production use."""
        if not self.items:
            raise BOMError("Cannot activate BOM with no items")
        self.status = BOMStatus.ACTIVE

    def obsolete(self) -> None:
        """Mark BOM as obsolete."""
        self.status = BOMStatus.OBSOLETE


class BOMEngine:
    """Engine for managing BOMs and performing explosions."""

    def __init__(self):
        self._boms: Dict[str, BOM] = {}

    def create_bom(
        self,
        product_id: str,
        product_name: str,
        version: str = "1.0",
    ) -> BOM:
        """Create a new BOM."""
        bom = BOM(
            product_id=product_id,
            product_name=product_name,
            version=version,
        )
        self._boms[bom.id] = bom
        return bom

    def get_bom(self, bom_id: str) -> Optional[BOM]:
        """Retrieve a BOM by ID."""
        return self._boms.get(bom_id)

    def find_by_product(self, product_id: str) -> List[BOM]:
        """Find all BOMs for a product."""
        return [b for b in self._boms.values() if b.product_id == product_id]

    def explode(self, bom_id: str, quantity: float = 1.0) -> List[Dict]:
        """Explode a BOM into its component requirements."""
        bom = self._boms.get(bom_id)
        if not bom:
            raise BOMError(f"BOM not found: {bom_id}")
        if bom.status != BOMStatus.ACTIVE:
            raise BOMError(f"BOM is not active: {bom.status.value}")

        requirements = []
        for item in bom.items:
            requirements.append({
                "component_id": item.component_id,
                "component_name": item.component_name,
                "quantity": item.effective_quantity() * quantity,
                "unit": item.unit,
                "scrap_factor": item.scrap_factor,
            })
        return requirements

    def explode_multi_level(
        self,
        bom_id: str,
        quantity: float = 1.0,
    ) -> List[Dict]:
        """Explode a BOM recursively through all levels."""
        bom = self._boms.get(bom_id)
        if not bom:
            raise BOMError(f"BOM not found: {bom_id}")

        result = []
        for item in bom.items:
            # Check if component has its own BOM
            sub_boms = self.find_by_product(item.component_id)
            active_sub = [b for b in sub_boms if b.status == BOMStatus.ACTIVE]

            if active_sub:
                sub_reqs = self.explode_multi_level(active_sub[0].id, item.effective_quantity() * quantity)
                result.extend(sub_reqs)
            else:
                result.append({
                    "component_id": item.component_id,
                    "component_name": item.component_name,
                    "quantity": item.effective_quantity() * quantity,
                    "unit": item.unit,
                    "level": 1,
                })
        return result

    def calculate_cost(self, bom_id: str, component_costs: Dict[str, float]) -> float:
        """Calculate total material cost for a BOM."""
        bom = self._boms.get(bom_id)
        if not bom:
            raise BOMError(f"BOM not found: {bom_id}")

        total = 0.0
        for item in bom.items:
            unit_cost = component_costs.get(item.component_id, 0.0)
            total += item.effective_quantity() * unit_cost
        return total

    def list_boms(self) -> List[BOM]:
        """List all BOMs."""
        return list(self._boms.values())
