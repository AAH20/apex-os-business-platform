"""Inventory engine — unified facade for inventory management."""
from __future__ import annotations

from typing import Dict, List, Optional

from apex_os_bp.inventory.catalog import ProductCatalog
from apex_os_bp.inventory.models import (
    OrderStatus,
    Product,
    ProductCategory,
    PurchaseOrder,
    PurchaseOrderLine,
    SalesOrder,
    SalesOrderLine,
    ValuationMethod,
)
from apex_os_bp.inventory.purchase import PurchaseOrderManager
from apex_os_bp.inventory.sales import SalesOrderManager
from apex_os_bp.inventory.stock import StockTracker
from apex_os_bp.inventory.valuation import InventoryValuation


class InventoryEngine:
    """Unified inventory management engine."""

    def __init__(self):
        self.catalog = ProductCatalog()
        self.stock = StockTracker()
        self.purchase_orders = PurchaseOrderManager()
        self.sales_orders = SalesOrderManager()
        self.valuation = InventoryValuation()

    # ── Product Catalog ──────────────────────────────────────────

    def add_product(self, product: Product) -> None:
        """Add a product to the catalog."""
        self.catalog.add_product(product)

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return self.catalog.get_product(product_id)

    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        return self.catalog.get_by_sku(sku)

    def list_products(
        self,
        category: Optional[ProductCategory] = None,
    ) -> List[Product]:
        """List products."""
        return self.catalog.list_products(category=category)

    # ── Stock Operations ─────────────────────────────────────────

    def receive_stock(
        self,
        product_id: str,
        location: str,
        quantity: int,
        unit_cost: float = 0.0,
        reference: Optional[str] = None,
    ) -> None:
        """Receive stock and update valuation."""
        self.stock.receive_stock(
            product_id=product_id,
            location=location,
            quantity=quantity,
            unit_cost=unit_cost,
            reference=reference,
        )
        self.valuation.add_cost_layer(product_id, quantity, unit_cost)

    def issue_stock(
        self,
        product_id: str,
        location: str,
        quantity: int,
        reference: Optional[str] = None,
        method: ValuationMethod = ValuationMethod.FIFO,
    ) -> float:
        """Issue stock and return the cost of goods issued."""
        movement = self.stock.issue_stock(
            product_id=product_id,
            location=location,
            quantity=quantity,
            reference=reference,
        )
        cost = self.valuation.remove_cost_layer(product_id, quantity, method)
        return cost

    def get_stock_level(self, product_id: str) -> int:
        """Get total stock level for a product."""
        return self.stock.get_total_quantity(product_id)

    def get_available_stock(self, product_id: str) -> int:
        """Get available stock for a product."""
        return self.stock.get_available_quantity(product_id)

    # ── Purchase Order Workflow ──────────────────────────────────

    def create_purchase_order(
        self,
        supplier_id: str,
        lines: Optional[List[PurchaseOrderLine]] = None,
    ) -> PurchaseOrder:
        """Create a purchase order."""
        return self.purchase_orders.create_order(supplier_id, lines)

    def receive_purchase_order(
        self,
        order_id: str,
        location: str = "main",
    ) -> None:
        """Receive a purchase order into stock."""
        order = self.purchase_orders.get_order(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        self.purchase_orders.receive_order(order_id)
        for line in order.lines:
            self.receive_stock(
                product_id=line.product_id,
                location=location,
                quantity=line.received_quantity,
                unit_cost=line.unit_cost,
                reference=order_id,
            )

    # ── Sales Order Workflow ────────────────────────────────────

    def create_sales_order(
        self,
        customer_id: str,
        lines: Optional[List[SalesOrderLine]] = None,
    ) -> SalesOrder:
        """Create a sales order."""
        return self.sales_orders.create_order(customer_id, lines)

    def fulfill_sales_order(
        self,
        order_id: str,
        location: str = "main",
        method: ValuationMethod = ValuationMethod.FIFO,
    ) -> float:
        """Fulfill a sales order, issuing stock. Returns COGS."""
        order = self.sales_orders.get_order(order_id)
        if not order:
            raise ValueError(f"Sales order not found: {order_id}")
        self.sales_orders.fulfill_order(order_id)
        total_cogs = 0.0
        for line in order.lines:
            cogs = self.issue_stock(
                product_id=line.product_id,
                location=location,
                quantity=line.fulfilled_quantity,
                reference=order_id,
                method=method,
            )
            total_cogs += cogs
        return total_cogs

    # ── Valuation ───────────────────────────────────────────────

    def get_inventory_value(
        self,
        method: ValuationMethod = ValuationMethod.FIFO,
    ) -> float:
        """Get total inventory value."""
        return self.valuation.get_total_inventory_value(method)

    def get_product_inventory_value(
        self,
        product_id: str,
        method: ValuationMethod = ValuationMethod.FIFO,
    ) -> float:
        """Get inventory value for a specific product."""
        return self.valuation.get_inventory_value(product_id, method)

    # ── Reporting ───────────────────────────────────────────────

    def get_inventory_report(self) -> Dict:
        """Generate inventory report."""
        products = self.catalog.list_products(active_only=False)
        report = {
            "total_products": len(products),
            "total_sku_count": len([p for p in products if p.is_active]),
            "total_inventory_value_fifo": self.get_inventory_value(ValuationMethod.FIFO),
            "total_inventory_value_weighted_avg": self.get_inventory_value(
                ValuationMethod.WEIGHTED_AVERAGE
            ),
            "products": [],
        }
        for product in products:
            qty = self.get_stock_level(product.id)
            report["products"].append({
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "quantity": qty,
                "unit_cost": product.unit_cost,
                "stock_value": qty * product.unit_cost,
            })
        return report
