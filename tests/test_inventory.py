"""Tests for inventory module."""
import pytest

from apex_os_bp.inventory.catalog import ProductCatalog
from apex_os_bp.inventory.engine import InventoryEngine
from apex_os_bp.inventory.models import (
    OrderStatus,
    Product,
    ProductCategory,
    PurchaseOrder,
    PurchaseOrderLine,
    SalesOrderLine,
    StockItem,
    StockMovement,
    ValuationMethod,
)
from apex_os_bp.inventory.purchase import PurchaseOrderManager
from apex_os_bp.inventory.sales import SalesOrderManager
from apex_os_bp.inventory.stock import StockTracker
from apex_os_bp.inventory.valuation import InventoryValuation


# ═══════════════════════════════════════════════════════════════
# Product Catalog Tests
# ═══════════════════════════════════════════════════════════════

class TestProduct:
    """Test product data model."""

    def test_product_creation(self):
        """Product can be created."""
        product = Product.create(
            sku="SKU-001",
            name="Widget",
            category=ProductCategory.FINISHED_GOOD,
            unit_price=29.99,
            unit_cost=10.00,
        )
        assert product.sku == "SKU-001"
        assert product.name == "Widget"
        assert product.category == ProductCategory.FINISHED_GOOD
        assert product.unit_price == 29.99
        assert product.unit_cost == 10.00
        assert product.is_active is True
        assert product.id is not None

    def test_product_with_options(self):
        """Product with optional fields."""
        product = Product.create(
            sku="SKU-002",
            name="Gadget",
            category=ProductCategory.MERCHANDISE,
            unit_price=49.99,
            unit_cost=20.00,
            unit_of_measure="box",
            description="A fine gadget",
            reorder_point=10,
            reorder_quantity=100,
        )
        assert product.unit_of_measure == "box"
        assert product.description == "A fine gadget"
        assert product.reorder_point == 10
        assert product.reorder_quantity == 100


class TestProductCatalog:
    """Test product catalog."""

    def test_add_and_get_product(self):
        """Product can be added and retrieved."""
        catalog = ProductCatalog()
        product = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        catalog.add_product(product)
        assert catalog.get_product(product.id) == product

    def test_get_by_sku(self):
        """Product can be retrieved by SKU."""
        catalog = ProductCatalog()
        product = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        catalog.add_product(product)
        assert catalog.get_by_sku("SKU-001") == product

    def test_duplicate_sku_raises(self):
        """Duplicate SKU raises error."""
        catalog = ProductCatalog()
        p1 = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        p2 = Product.create("SKU-001", "Gadget", ProductCategory.FINISHED_GOOD, 39.99, 15.0)
        catalog.add_product(p1)
        with pytest.raises(ValueError):
            catalog.add_product(p2)

    def test_update_product(self):
        """Product can be updated."""
        catalog = ProductCatalog()
        product = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        catalog.add_product(product)
        catalog.update_product(product.id, name="Super Widget", unit_price=39.99)
        updated = catalog.get_product(product.id)
        assert updated.name == "Super Widget"
        assert updated.unit_price == 39.99

    def test_remove_product(self):
        """Product can be removed."""
        catalog = ProductCatalog()
        product = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        catalog.add_product(product)
        catalog.remove_product(product.id)
        assert catalog.get_product(product.id) is None
        assert catalog.get_by_sku("SKU-001") is None

    def test_list_products(self):
        """List all products."""
        catalog = ProductCatalog()
        catalog.add_product(Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0))
        catalog.add_product(Product.create("SKU-002", "Gadget", ProductCategory.MERCHANDISE, 49.99, 20.0))
        assert catalog.count() == 2
        assert len(catalog.list_products()) == 2

    def test_list_by_category(self):
        """Filter products by category."""
        catalog = ProductCatalog()
        catalog.add_product(Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0))
        catalog.add_product(Product.create("SKU-002", "Gadget", ProductCategory.MERCHANDISE, 49.99, 20.0))
        finished = catalog.list_products(category=ProductCategory.FINISHED_GOOD)
        assert len(finished) == 1
        assert finished[0].name == "Widget"

    def test_search_products(self):
        """Search products by name or SKU."""
        catalog = ProductCatalog()
        catalog.add_product(Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0))
        catalog.add_product(Product.create("SKU-002", "Gadget", ProductCategory.MERCHANDISE, 49.99, 20.0))
        results = catalog.search("Gadget")
        assert len(results) == 1
        assert results[0].name == "Gadget"
        results = catalog.search("SKU-001")
        assert len(results) == 1

    def test_inactive_products_filtered(self):
        """Inactive products excluded by default."""
        catalog = ProductCatalog()
        p = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        catalog.add_product(p)
        catalog.update_product(p.id, is_active=False)
        assert len(catalog.list_products()) == 0
        assert len(catalog.list_products(active_only=False)) == 1


# ═══════════════════════════════════════════════════════════════
# Stock Tracking Tests
# ═══════════════════════════════════════════════════════════════

class TestStockItem:
    """Test stock item."""

    def test_stock_item_creation(self):
        """Stock item can be created."""
        item = StockItem(product_id="p1", location="warehouse-a", quantity=100)
        assert item.product_id == "p1"
        assert item.location == "warehouse-a"
        assert item.quantity == 100
        assert item.reserved_quantity == 0
        assert item.available_quantity == 100

    def test_adjust_increase(self):
        """Stock can be increased."""
        item = StockItem(product_id="p1", location="main", quantity=50)
        item.adjust(25)
        assert item.quantity == 75

    def test_adjust_decrease(self):
        """Stock can be decreased."""
        item = StockItem(product_id="p1", location="main", quantity=50)
        item.adjust(-20)
        assert item.quantity == 30

    def test_adjust_below_zero_raises(self):
        """Adjusting below zero raises error."""
        item = StockItem(product_id="p1", location="main", quantity=10)
        with pytest.raises(ValueError):
            item.adjust(-15)

    def test_reserve_stock(self):
        """Stock can be reserved."""
        item = StockItem(product_id="p1", location="main", quantity=100)
        item.reserve(30)
        assert item.reserved_quantity == 30
        assert item.available_quantity == 70

    def test_reserve_too_much_raises(self):
        """Reserving more than available raises error."""
        item = StockItem(product_id="p1", location="main", quantity=10)
        with pytest.raises(ValueError):
            item.reserve(15)

    def test_release_stock(self):
        """Reserved stock can be released."""
        item = StockItem(product_id="p1", location="main", quantity=100)
        item.reserve(30)
        item.release(10)
        assert item.reserved_quantity == 20
        assert item.available_quantity == 80

    def test_release_too_much_raises(self):
        """Releasing more than reserved raises error."""
        item = StockItem(product_id="p1", location="main", quantity=100)
        item.reserve(10)
        with pytest.raises(ValueError):
            item.release(15)


class TestStockTracker:
    """Test stock tracker."""

    def test_receive_stock(self):
        """Stock can be received."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "main", 100, unit_cost=10.0)
        assert tracker.get_total_quantity("p1") == 100

    def test_issue_stock(self):
        """Stock can be issued."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "main", 100)
        tracker.issue_stock("p1", "main", 30)
        assert tracker.get_total_quantity("p1") == 70

    def test_issue_insufficient_raises(self):
        """Issuing more than available raises error."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "main", 10)
        with pytest.raises(ValueError):
            tracker.issue_stock("p1", "main", 15)

    def test_stock_across_locations(self):
        """Stock tracked across multiple locations."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "warehouse-a", 50)
        tracker.receive_stock("p1", "warehouse-b", 30)
        assert tracker.get_total_quantity("p1") == 80
        assert len(tracker.get_locations("p1")) == 2

    def test_transfer_stock(self):
        """Stock can be transferred between locations."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "warehouse-a", 100)
        tracker.transfer_stock("p1", "warehouse-a", "warehouse-b", 40)
        assert tracker.get_stock("p1", "warehouse-a").quantity == 60
        assert tracker.get_stock("p1", "warehouse-b").quantity == 40

    def test_movements_recorded(self):
        """Stock movements are recorded."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "main", 100)
        tracker.issue_stock("p1", "main", 30)
        movements = tracker.get_movements("p1")
        assert len(movements) == 2
        assert movements[0].movement_type == "in"
        assert movements[1].movement_type == "out"

    def test_reserve_and_release(self):
        """Stock can be reserved and released."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "main", 100)
        tracker.reserve_stock("p1", "main", 30)
        assert tracker.get_available_quantity("p1") == 70
        tracker.release_stock("p1", "main", 10)
        assert tracker.get_available_quantity("p1") == 80

    def test_low_stock_detection(self):
        """Low stock items can be detected."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "main", 5)
        tracker.receive_stock("p2", "main", 100)
        low = tracker.get_low_stock(reorder_point=10)
        assert len(low) == 1
        assert low[0].product_id == "p1"

    def test_stock_value(self):
        """Stock value can be calculated."""
        tracker = StockTracker()
        tracker.receive_stock("p1", "main", 50, unit_cost=10.0)
        assert tracker.get_stock_value("p1", 10.0) == 500.0


# ═══════════════════════════════════════════════════════════════
# Purchase Order Tests
# ═══════════════════════════════════════════════════════════════

class TestPurchaseOrder:
    """Test purchase order model."""

    def test_po_creation(self):
        """Purchase order can be created."""
        po = PurchaseOrder.create(supplier_id="sup-1")
        assert po.supplier_id == "sup-1"
        assert po.status == OrderStatus.DRAFT
        assert po.total_cost == 0.0

    def test_po_with_lines(self):
        """Purchase order with lines."""
        lines = [
            PurchaseOrderLine(product_id="p1", quantity=10, unit_cost=5.0),
            PurchaseOrderLine(product_id="p2", quantity=20, unit_cost=3.0),
        ]
        po = PurchaseOrder.create(supplier_id="sup-1", lines=lines)
        assert po.total_cost == 110.0
        assert po.total_quantity == 30

    def test_po_line_totals(self):
        """PO line totals calculated correctly."""
        line = PurchaseOrderLine(product_id="p1", quantity=10, unit_cost=5.5)
        assert line.line_total == 55.0
        assert not line.is_fully_received
        line.received_quantity = 10
        assert line.is_fully_received


class TestPurchaseOrderManager:
    """Test purchase order manager."""

    def test_create_order(self):
        """PO can be created."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        assert po.supplier_id == "sup-1"
        assert po.status == OrderStatus.DRAFT

    def test_add_line(self):
        """Line can be added to PO."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.add_line(po.id, "p1", 10, 5.0)
        assert len(po.lines) == 1
        assert po.total_cost == 50.0

    def test_add_line_non_draft_raises(self):
        """Cannot add line to non-draft PO."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.submit_order(po.id)
        with pytest.raises(ValueError):
            mgr.add_line(po.id, "p1", 10, 5.0)

    def test_submit_order(self):
        """PO can be submitted."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.submit_order(po.id)
        assert po.status == OrderStatus.PENDING

    def test_confirm_order(self):
        """PO can be confirmed."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.submit_order(po.id)
        mgr.confirm_order(po.id)
        assert po.status == OrderStatus.CONFIRMED

    def test_mark_shipped(self):
        """PO can be marked shipped."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.submit_order(po.id)
        mgr.confirm_order(po.id)
        mgr.mark_shipped(po.id)
        assert po.status == OrderStatus.SHIPPED

    def test_receive_full(self):
        """PO can be fully received."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.add_line(po.id, "p1", 10, 5.0)
        mgr.submit_order(po.id)
        mgr.confirm_order(po.id)
        mgr.mark_shipped(po.id)
        mgr.receive_order(po.id)
        assert po.status == OrderStatus.RECEIVED
        assert po.lines[0].received_quantity == 10

    def test_receive_partial(self):
        """PO can be partially received."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.add_line(po.id, "p1", 10, 5.0)
        mgr.submit_order(po.id)
        mgr.confirm_order(po.id)
        mgr.mark_shipped(po.id)
        mgr.receive_order(po.id, {0: 4})
        assert po.status != OrderStatus.RECEIVED
        assert po.lines[0].received_quantity == 4

    def test_cancel_order(self):
        """PO can be cancelled."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.cancel_order(po.id)
        assert po.status == OrderStatus.CANCELLED

    def test_cancel_received_raises(self):
        """Cannot cancel received PO."""
        mgr = PurchaseOrderManager()
        po = mgr.create_order("sup-1")
        mgr.add_line(po.id, "p1", 10, 5.0)
        mgr.submit_order(po.id)
        mgr.confirm_order(po.id)
        mgr.mark_shipped(po.id)
        mgr.receive_order(po.id)
        with pytest.raises(ValueError):
            mgr.cancel_order(po.id)

    def test_list_orders(self):
        """POs can be listed and filtered."""
        mgr = PurchaseOrderManager()
        po1 = mgr.create_order("sup-1")
        po2 = mgr.create_order("sup-2")
        mgr.submit_order(po1.id)
        assert len(mgr.list_orders()) == 2
        assert len(mgr.list_orders(supplier_id="sup-1")) == 1
        assert len(mgr.list_orders(status=OrderStatus.PENDING)) == 1

    def test_get_pending_orders(self):
        """Pending POs can be retrieved."""
        mgr = PurchaseOrderManager()
        po1 = mgr.create_order("sup-1")
        po2 = mgr.create_order("sup-2")
        mgr.submit_order(po1.id)
        pending = mgr.get_pending_orders()
        assert len(pending) == 2
        mgr.cancel_order(po2.id)
        pending = mgr.get_pending_orders()
        assert len(pending) == 1


# ═══════════════════════════════════════════════════════════════
# Sales Order Tests
# ═══════════════════════════════════════════════════════════════

class TestSalesOrder:
    """Test sales order model."""

    def test_so_creation(self):
        """Sales order can be created."""
        from apex_os_bp.inventory.models import SalesOrder
        so = SalesOrder.create(customer_id="cust-1")
        assert so.customer_id == "cust-1"
        assert so.status == OrderStatus.DRAFT
        assert so.total_revenue == 0.0

    def test_so_with_lines(self):
        """Sales order with lines."""
        from apex_os_bp.inventory.models import SalesOrder
        lines = [
            SalesOrderLine(product_id="p1", quantity=5, unit_price=20.0),
            SalesOrderLine(product_id="p2", quantity=3, unit_price=15.0),
        ]
        so = SalesOrder.create(customer_id="cust-1", lines=lines)
        assert so.total_revenue == 145.0
        assert so.total_quantity == 8

    def test_so_line_totals(self):
        """SO line totals calculated correctly."""
        line = SalesOrderLine(product_id="p1", quantity=5, unit_price=20.0)
        assert line.line_total == 100.0
        assert not line.is_fully_fulfilled
        line.fulfilled_quantity = 5
        assert line.is_fully_fulfilled


class TestSalesOrderManager:
    """Test sales order manager."""

    def test_create_order(self):
        """SO can be created."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        assert so.customer_id == "cust-1"
        assert so.status == OrderStatus.DRAFT

    def test_add_line(self):
        """Line can be added to SO."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        mgr.add_line(so.id, "p1", 5, 20.0)
        assert len(so.lines) == 1
        assert so.total_revenue == 100.0

    def test_add_line_non_draft_raises(self):
        """Cannot add line to non-draft SO."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        mgr.submit_order(so.id)
        with pytest.raises(ValueError):
            mgr.add_line(so.id, "p1", 5, 20.0)

    def test_submit_order(self):
        """SO can be submitted."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        mgr.submit_order(so.id)
        assert so.status == OrderStatus.PENDING

    def test_confirm_order(self):
        """SO can be confirmed."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        mgr.submit_order(so.id)
        mgr.confirm_order(so.id)
        assert so.status == OrderStatus.CONFIRMED

    def test_fulfill_full(self):
        """SO can be fully fulfilled."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        mgr.add_line(so.id, "p1", 5, 20.0)
        mgr.submit_order(so.id)
        mgr.confirm_order(so.id)
        mgr.fulfill_order(so.id)
        assert so.status == OrderStatus.SHIPPED
        assert so.lines[0].fulfilled_quantity == 5

    def test_fulfill_partial(self):
        """SO can be partially fulfilled."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        mgr.add_line(so.id, "p1", 10, 20.0)
        mgr.submit_order(so.id)
        mgr.confirm_order(so.id)
        mgr.fulfill_order(so.id, {0: 4})
        assert so.status != OrderStatus.SHIPPED
        assert so.lines[0].fulfilled_quantity == 4

    def test_cancel_order(self):
        """SO can be cancelled."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        mgr.cancel_order(so.id)
        assert so.status == OrderStatus.CANCELLED

    def test_cancel_shipped_raises(self):
        """Cannot cancel shipped SO."""
        mgr = SalesOrderManager()
        so = mgr.create_order("cust-1")
        mgr.add_line(so.id, "p1", 5, 20.0)
        mgr.submit_order(so.id)
        mgr.confirm_order(so.id)
        mgr.fulfill_order(so.id)
        with pytest.raises(ValueError):
            mgr.cancel_order(so.id)

    def test_list_orders(self):
        """SOs can be listed and filtered."""
        mgr = SalesOrderManager()
        so1 = mgr.create_order("cust-1")
        so2 = mgr.create_order("cust-2")
        mgr.submit_order(so1.id)
        assert len(mgr.list_orders()) == 2
        assert len(mgr.list_orders(customer_id="cust-1")) == 1
        assert len(mgr.list_orders(status=OrderStatus.PENDING)) == 1

    def test_get_open_orders(self):
        """Open SOs can be retrieved."""
        mgr = SalesOrderManager()
        so1 = mgr.create_order("cust-1")
        so2 = mgr.create_order("cust-2")
        mgr.submit_order(so1.id)
        open_orders = mgr.get_open_orders()
        assert len(open_orders) == 2
        mgr.cancel_order(so2.id)
        open_orders = mgr.get_open_orders()
        assert len(open_orders) == 1


# ═══════════════════════════════════════════════════════════════
# Inventory Valuation Tests
# ═══════════════════════════════════════════════════════════════

class TestInventoryValuation:
    """Test inventory valuation."""

    def test_add_cost_layer(self):
        """Cost layer can be added."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        assert val.get_product_quantity("p1") == 100

    def test_fifo_valuation(self):
        """FIFO valuation removes oldest layers first."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        val.add_cost_layer("p1", 100, 12.0)
        # Remove 150 — should take 100 @ 10 + 50 @ 12 = 1600
        cost = val.remove_cost_layer("p1", 150, ValuationMethod.FIFO)
        assert cost == 1600.0
        assert val.get_product_quantity("p1") == 50

    def test_lifo_valuation(self):
        """LIFO valuation removes newest layers first."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        val.add_cost_layer("p1", 100, 12.0)
        # Remove 150 — should take 100 @ 12 + 50 @ 10 = 1700
        cost = val.remove_cost_layer("p1", 150, ValuationMethod.LIFO)
        assert cost == 1700.0
        assert val.get_product_quantity("p1") == 50

    def test_weighted_average_valuation(self):
        """Weighted average valuation."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        val.add_cost_layer("p1", 100, 20.0)
        # Average cost = 15.0
        cost = val.remove_cost_layer("p1", 100, ValuationMethod.WEIGHTED_AVERAGE)
        assert cost == 1500.0
        assert val.get_product_quantity("p1") == 100

    def test_inventory_value_fifo(self):
        """Inventory value calculated correctly."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        val.add_cost_layer("p1", 50, 12.0)
        assert val.get_inventory_value("p1", ValuationMethod.FIFO) == 1600.0

    def test_total_inventory_value(self):
        """Total inventory value across all products."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        val.add_cost_layer("p2", 50, 20.0)
        assert val.get_total_inventory_value() == 2000.0

    def test_average_cost(self):
        """Average cost calculated correctly."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        val.add_cost_layer("p1", 100, 20.0)
        assert val.get_average_cost("p1") == 15.0

    def test_insufficient_stock_raises(self):
        """Removing more than available raises error."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 50, 10.0)
        with pytest.raises(ValueError):
            val.remove_cost_layer("p1", 100)

    def test_standard_cost_valuation(self):
        """Standard cost uses most recent cost."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        val.add_cost_layer("p1", 100, 15.0)
        # Standard cost = 15.0 (most recent)
        value = val.get_inventory_value("p1", ValuationMethod.STANDARD_COST)
        assert value == 3000.0

    def test_clear_valuation(self):
        """Valuation can be cleared."""
        val = InventoryValuation()
        val.add_cost_layer("p1", 100, 10.0)
        val.clear()
        assert val.get_product_quantity("p1") == 0


# ═══════════════════════════════════════════════════════════════
# Inventory Engine Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestInventoryEngine:
    """Test unified inventory engine."""

    def test_full_purchase_to_stock_workflow(self):
        """Full workflow: create PO, receive, check stock."""
        engine = InventoryEngine()
        product = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        engine.add_product(product)

        po = engine.create_purchase_order("sup-1", [PurchaseOrderLine(product.id, 100, 10.0)])
        engine.purchase_orders.submit_order(po.id)
        engine.purchase_orders.confirm_order(po.id)
        engine.purchase_orders.mark_shipped(po.id)
        engine.receive_purchase_order(po.id, location="main")

        assert engine.get_stock_level(product.id) == 100
        assert engine.get_product_inventory_value(product.id) == 1000.0

    def test_full_sales_workflow(self):
        """Full workflow: receive stock, create SO, fulfill."""
        engine = InventoryEngine()
        product = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        engine.add_product(product)
        engine.receive_stock(product.id, "main", 100, unit_cost=10.0)

        so = engine.create_sales_order("cust-1", [SalesOrderLine(product.id, 30, 29.99)])
        engine.sales_orders.submit_order(so.id)
        engine.sales_orders.confirm_order(so.id)
        cogs = engine.fulfill_sales_order(so.id, location="main")

        assert engine.get_stock_level(product.id) == 70
        assert cogs == 300.0  # 30 * 10.0

    def test_inventory_report(self):
        """Inventory report generated correctly."""
        engine = InventoryEngine()
        p1 = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        p2 = Product.create("SKU-002", "Gadget", ProductCategory.MERCHANDISE, 49.99, 20.0)
        engine.add_product(p1)
        engine.add_product(p2)
        engine.receive_stock(p1.id, "main", 50, unit_cost=10.0)
        engine.receive_stock(p2.id, "main", 25, unit_cost=20.0)

        report = engine.get_inventory_report()
        assert report["total_products"] == 2
        assert report["total_inventory_value_fifo"] == 1000.0

    def test_stock_reservation_workflow(self):
        """Stock can be reserved for sales orders."""
        engine = InventoryEngine()
        product = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        engine.add_product(product)
        engine.receive_stock(product.id, "main", 100)

        engine.stock.reserve_stock(product.id, "main", 30)
        assert engine.get_available_stock(product.id) == 70

        engine.stock.release_stock(product.id, "main", 10)
        assert engine.get_available_stock(product.id) == 80

    def test_multiple_valuation_methods(self):
        """Different valuation methods produce different results."""
        engine = InventoryEngine()
        product = Product.create("SKU-001", "Widget", ProductCategory.FINISHED_GOOD, 29.99, 10.0)
        engine.add_product(product)
        engine.receive_stock(product.id, "main", 100, unit_cost=10.0)
        engine.receive_stock(product.id, "main", 100, unit_cost=15.0)

        fifo_val = engine.get_product_inventory_value(product.id, ValuationMethod.FIFO)
        avg_val = engine.get_product_inventory_value(product.id, ValuationMethod.WEIGHTED_AVERAGE)
        assert fifo_val == 2500.0
        assert avg_val == 2500.0

        # Issue stock and compare COGS
        engine2 = InventoryEngine()
        engine2.add_product(product)
        engine2.receive_stock(product.id, "main", 100, unit_cost=10.0)
        engine2.receive_stock(product.id, "main", 100, unit_cost=15.0)
        cogs_fifo = engine2.issue_stock(product.id, "main", 150, method=ValuationMethod.FIFO)
        assert cogs_fifo == 1750.0  # 100*10 + 50*15

        engine3 = InventoryEngine()
        engine3.add_product(product)
        engine3.receive_stock(product.id, "main", 100, unit_cost=10.0)
        engine3.receive_stock(product.id, "main", 100, unit_cost=15.0)
        cogs_lifo = engine3.issue_stock(product.id, "main", 150, method=ValuationMethod.LIFO)
        assert cogs_lifo == 2000.0  # 100*15 + 50*10
