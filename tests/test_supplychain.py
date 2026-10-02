"""Comprehensive tests for the supply chain management system."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date, datetime, timedelta

# Ensure the src directory is on the Python path
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"
    ),
)

from apex_os_bp.supplychain import (
    Carrier,
    DemandForecast,
    DemandForecaster,
    ForecastResult,
    ForecastingMethod,
    InventoryItem,
    LogisticsManager,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderManager,
    PurchaseOrderStatus,
    Shipment,
    ShipmentStatus,
    StockMovement,
    StockMovementType,
    Supplier,
    SupplierManager,
    SupplierStatus,
    SupplierTier,
    TrackingEvent,
    Warehouse,
    WarehouseManager,
    WarehouseZone,
)


# ═══════════════════════════════════════════════════════════════════════
# Supplier Management Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSupplier(unittest.TestCase):
    """Tests for the Supplier dataclass."""

    def test_create_supplier(self):
        s = Supplier(name="Acme Corp", contact_email="acme@example.com")
        self.assertEqual(s.name, "Acme Corp")
        self.assertEqual(s.contact_email, "acme@example.com")
        self.assertEqual(s.status, SupplierStatus.PROSPECT)
        self.assertEqual(s.tier, SupplierTier.BRONZE)
        self.assertEqual(s.rating, 0.0)
        self.assertTrue(s.id)

    def test_supplier_validation_empty_name(self):
        with self.assertRaises(ValueError):
            Supplier(name="", contact_email="test@example.com")

    def test_supplier_validation_invalid_email(self):
        with self.assertRaises(ValueError):
            Supplier(name="Test", contact_email="not-an-email")

    def test_supplier_validation_rating_too_high(self):
        with self.assertRaises(ValueError):
            Supplier(
                name="Test",
                contact_email="test@example.com",
                rating=6.0,
            )

    def test_supplier_validation_rating_negative(self):
        with self.assertRaises(ValueError):
            Supplier(
                name="Test",
                contact_email="test@example.com",
                rating=-1.0,
            )

    def test_supplier_validation_negative_lead_time(self):
        with self.assertRaises(ValueError):
            Supplier(
                name="Test",
                contact_email="test@example.com",
                lead_time_days=-5,
            )

    def test_supplier_approve(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.approve()
        self.assertEqual(s.status, SupplierStatus.APPROVED)

    def test_supplier_approve_blacklisted_raises(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.blacklist("Fraud")
        with self.assertRaises(ValueError):
            s.approve()

    def test_supplier_suspend(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.approve()
        s.suspend("Quality issues")
        self.assertEqual(s.status, SupplierStatus.SUSPENDED)
        self.assertIn("Quality issues", s.notes)

    def test_supplier_suspend_blacklisted_raises(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.blacklist("Fraud")
        with self.assertRaises(ValueError):
            s.suspend("test")

    def test_supplier_blacklist(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.blacklist("Fraud detected")
        self.assertEqual(s.status, SupplierStatus.BLACKLISTED)
        self.assertIn("Fraud", s.notes)

    def test_supplier_update_rating(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.update_rating(4.5)
        self.assertEqual(s.rating, 4.5)
        self.assertEqual(s.tier, SupplierTier.PLATINUM)

    def test_supplier_update_rating_gold(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.update_rating(4.2)
        self.assertEqual(s.tier, SupplierTier.GOLD)

    def test_supplier_update_rating_silver(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.update_rating(3.5)
        self.assertEqual(s.tier, SupplierTier.SILVER)

    def test_supplier_update_rating_bronze(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.update_rating(2.0)
        self.assertEqual(s.tier, SupplierTier.BRONZE)

    def test_supplier_update_rating_invalid(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        with self.assertRaises(ValueError):
            s.update_rating(5.5)

    def test_supplier_update_lead_time(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        s.update_lead_time(14)
        self.assertEqual(s.lead_time_days, 14)

    def test_supplier_update_lead_time_negative(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        with self.assertRaises(ValueError):
            s.update_lead_time(-1)

    def test_supplier_to_dict(self):
        s = Supplier(
            name="Acme",
            contact_email="acme@example.com",
            rating=4.0,
            status=SupplierStatus.APPROVED,
        )
        d = s.to_dict()
        self.assertEqual(d["name"], "Acme")
        self.assertEqual(d["rating"], 4.0)
        self.assertEqual(d["status"], "approved")
        self.assertIn("id", d)
        self.assertIn("created_at", d)


class TestSupplierManager(unittest.TestCase):
    """Tests for the SupplierManager."""

    def setUp(self):
        self.mgr = SupplierManager()

    def test_add_supplier(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        self.mgr.add_supplier(s)
        self.assertEqual(self.mgr.count(), 1)

    def test_add_duplicate_supplier(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        self.mgr.add_supplier(s)
        with self.assertRaises(ValueError):
            self.mgr.add_supplier(s)

    def test_get_supplier(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        self.mgr.add_supplier(s)
        found = self.mgr.get_supplier(s.id)
        self.assertEqual(found.name, "Acme")

    def test_get_supplier_not_found(self):
        self.assertIsNone(self.mgr.get_supplier("nonexistent"))

    def test_get_supplier_by_email(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        self.mgr.add_supplier(s)
        found = self.mgr.get_supplier_by_email("acme@example.com")
        self.assertEqual(found.name, "Acme")

    def test_get_supplier_by_email_not_found(self):
        self.assertIsNone(self.mgr.get_supplier_by_email("nobody@example.com"))

    def test_remove_supplier(self):
        s = Supplier(name="Acme", contact_email="acme@example.com")
        self.mgr.add_supplier(s)
        self.assertTrue(self.mgr.remove_supplier(s.id))
        self.assertEqual(self.mgr.count(), 0)

    def test_remove_supplier_not_found(self):
        self.assertFalse(self.mgr.remove_supplier("nonexistent"))

    def test_list_suppliers(self):
        self.mgr.add_supplier(
            Supplier(name="A", contact_email="a@example.com")
        )
        self.mgr.add_supplier(
            Supplier(name="B", contact_email="b@example.com")
        )
        self.assertEqual(len(self.mgr.list_suppliers()), 2)

    def test_list_suppliers_filter_by_status(self):
        s1 = Supplier(name="A", contact_email="a@example.com")
        s1.approve()
        s2 = Supplier(name="B", contact_email="b@example.com")
        self.mgr.add_supplier(s1)
        self.mgr.add_supplier(s2)
        approved = self.mgr.list_suppliers(status=SupplierStatus.APPROVED)
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0].name, "A")

    def test_list_suppliers_filter_by_tier(self):
        s1 = Supplier(name="A", contact_email="a@example.com")
        s1.update_rating(4.5)  # platinum
        s2 = Supplier(name="B", contact_email="b@example.com")
        self.mgr.add_supplier(s1)
        self.mgr.add_supplier(s2)
        platinum = self.mgr.list_suppliers(tier=SupplierTier.PLATINUM)
        self.assertEqual(len(platinum), 1)

    def test_list_suppliers_filter_by_country(self):
        s1 = Supplier(
            name="A", contact_email="a@example.com", country_code="US"
        )
        s2 = Supplier(
            name="B", contact_email="b@example.com", country_code="UK"
        )
        self.mgr.add_supplier(s1)
        self.mgr.add_supplier(s2)
        us = self.mgr.list_suppliers(country_code="US")
        self.assertEqual(len(us), 1)

    def test_get_approved_suppliers(self):
        s1 = Supplier(name="A", contact_email="a@example.com")
        s1.approve()
        s2 = Supplier(name="B", contact_email="b@example.com")
        self.mgr.add_supplier(s1)
        self.mgr.add_supplier(s2)
        approved = self.mgr.get_approved_suppliers()
        self.assertEqual(len(approved), 1)

    def test_get_top_rated(self):
        s1 = Supplier(name="A", contact_email="a@example.com", rating=3.0)
        s2 = Supplier(name="B", contact_email="b@example.com", rating=5.0)
        s3 = Supplier(name="C", contact_email="c@example.com", rating=4.0)
        self.mgr.add_supplier(s1)
        self.mgr.add_supplier(s2)
        self.mgr.add_supplier(s3)
        top = self.mgr.get_top_rated(limit=2)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0].name, "B")
        self.assertEqual(top[1].name, "C")

    def test_clear(self):
        self.mgr.add_supplier(
            Supplier(name="A", contact_email="a@example.com")
        )
        self.mgr.clear()
        self.assertEqual(self.mgr.count(), 0)


# ═══════════════════════════════════════════════════════════════════════
# Purchase Order Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPurchaseOrderItem(unittest.TestCase):
    """Tests for PurchaseOrderItem."""

    def test_create_item(self):
        item = PurchaseOrderItem(
            product_sku="WIDGET-001",
            product_name="Widget",
            quantity=100,
            unit_price=9.99,
        )
        self.assertEqual(item.product_sku, "WIDGET-001")
        self.assertEqual(item.quantity, 100)
        self.assertEqual(item.unit_price, 9.99)
        self.assertEqual(item.received_quantity, 0)

    def test_item_validation_empty_sku(self):
        with self.assertRaises(ValueError):
            PurchaseOrderItem(
                product_sku="", product_name="Widget", quantity=1, unit_price=1.0
            )

    def test_item_validation_zero_quantity(self):
        with self.assertRaises(ValueError):
            PurchaseOrderItem(
                product_sku="SKU", product_name="Widget", quantity=0, unit_price=1.0
            )

    def test_item_validation_negative_price(self):
        with self.assertRaises(ValueError):
            PurchaseOrderItem(
                product_sku="SKU", product_name="Widget", quantity=1, unit_price=-1.0
            )

    def test_item_validation_received_exceeds_quantity(self):
        with self.assertRaises(ValueError):
            PurchaseOrderItem(
                product_sku="SKU",
                product_name="Widget",
                quantity=5,
                unit_price=1.0,
                received_quantity=10,
            )

    def test_line_total(self):
        item = PurchaseOrderItem(
            product_sku="SKU", product_name="Widget", quantity=10, unit_price=5.0
        )
        self.assertEqual(item.line_total, 50.0)

    def test_pending_quantity(self):
        item = PurchaseOrderItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=10,
            unit_price=5.0,
            received_quantity=3,
        )
        self.assertEqual(item.pending_quantity, 7)

    def test_is_fully_received(self):
        item = PurchaseOrderItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=10,
            unit_price=5.0,
            received_quantity=10,
        )
        self.assertTrue(item.is_fully_received)

    def test_is_not_fully_received(self):
        item = PurchaseOrderItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=10,
            unit_price=5.0,
            received_quantity=5,
        )
        self.assertFalse(item.is_fully_received)

    def test_receive(self):
        item = PurchaseOrderItem(
            product_sku="SKU", product_name="Widget", quantity=10, unit_price=5.0
        )
        item.receive(4)
        self.assertEqual(item.received_quantity, 4)

    def test_receive_zero_raises(self):
        item = PurchaseOrderItem(
            product_sku="SKU", product_name="Widget", quantity=10, unit_price=5.0
        )
        with self.assertRaises(ValueError):
            item.receive(0)

    def test_receive_exceeds_raises(self):
        item = PurchaseOrderItem(
            product_sku="SKU", product_name="Widget", quantity=10, unit_price=5.0
        )
        with self.assertRaises(ValueError):
            item.receive(11)

    def test_to_dict(self):
        item = PurchaseOrderItem(
            product_sku="SKU", product_name="Widget", quantity=10, unit_price=5.0
        )
        d = item.to_dict()
        self.assertEqual(d["product_sku"], "SKU")
        self.assertEqual(d["line_total"], 50.0)
        self.assertEqual(d["pending_quantity"], 10)


class TestPurchaseOrder(unittest.TestCase):
    """Tests for PurchaseOrder."""

    def test_create_order(self):
        po = PurchaseOrder(supplier_id="sup-001")
        self.assertEqual(po.supplier_id, "sup-001")
        self.assertEqual(po.status, PurchaseOrderStatus.DRAFT)
        self.assertEqual(po.total_amount, 0.0)
        self.assertTrue(po.id)

    def test_order_validation_empty_supplier(self):
        with self.assertRaises(ValueError):
            PurchaseOrder(supplier_id="")

    def test_add_item(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="Widget", quantity=10, unit_price=5.0
            )
        )
        self.assertEqual(len(po.items), 1)
        self.assertEqual(po.total_amount, 50.0)

    def test_add_item_non_draft_raises(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1",
                product_name="Widget",
                quantity=10,
                unit_price=5.0,
            )
        )
        po.submit()
        with self.assertRaises(ValueError):
            po.add_item(
                PurchaseOrderItem(
                    product_sku="SKU2",
                    product_name="Gadget",
                    quantity=5,
                    unit_price=3.0,
                )
            )

    def test_remove_item(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="Widget", quantity=10, unit_price=5.0
            )
        )
        self.assertTrue(po.remove_item("SKU1"))
        self.assertEqual(len(po.items), 0)

    def test_remove_item_not_found(self):
        po = PurchaseOrder(supplier_id="sup-001")
        self.assertFalse(po.remove_item("NONEXISTENT"))

    def test_remove_item_non_draft_raises(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="Widget", quantity=10, unit_price=5.0
            )
        )
        po.submit()
        with self.assertRaises(ValueError):
            po.remove_item("SKU1")

    def test_total_quantity(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU2", product_name="B", quantity=20, unit_price=3.0
            )
        )
        self.assertEqual(po.total_quantity, 30)

    def test_total_received(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1",
                product_name="A",
                quantity=10,
                unit_price=5.0,
                received_quantity=4,
            )
        )
        self.assertEqual(po.total_received, 4)

    def test_is_fully_received(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1",
                product_name="A",
                quantity=10,
                unit_price=5.0,
                received_quantity=10,
            )
        )
        self.assertTrue(po.is_fully_received)

    def test_is_partially_received(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1",
                product_name="A",
                quantity=10,
                unit_price=5.0,
                received_quantity=5,
            )
        )
        self.assertTrue(po.is_partially_received)

    def test_submit(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.submit()
        self.assertEqual(po.status, PurchaseOrderStatus.SUBMITTED)

    def test_submit_empty_raises(self):
        po = PurchaseOrder(supplier_id="sup-001")
        with self.assertRaises(ValueError):
            po.submit()

    def test_submit_non_draft_raises(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.submit()
        with self.assertRaises(ValueError):
            po.submit()

    def test_approve(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.submit()
        po.approve()
        self.assertEqual(po.status, PurchaseOrderStatus.APPROVED)

    def test_approve_non_submitted_raises(self):
        po = PurchaseOrder(supplier_id="sup-001")
        with self.assertRaises(ValueError):
            po.approve()

    def test_send_to_supplier(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.submit()
        po.approve()
        po.send_to_supplier()
        self.assertEqual(po.status, PurchaseOrderStatus.SENT)

    def test_send_non_approved_raises(self):
        po = PurchaseOrder(supplier_id="sup-001")
        with self.assertRaises(ValueError):
            po.send_to_supplier()

    def test_receive_item(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.submit()
        po.approve()
        po.send_to_supplier()
        po.receive_item("SKU1", 5)
        self.assertEqual(po.status, PurchaseOrderStatus.PARTIALLY_RECEIVED)

    def test_receive_item_fully(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.submit()
        po.approve()
        po.send_to_supplier()
        po.receive_item("SKU1", 10)
        self.assertEqual(po.status, PurchaseOrderStatus.RECEIVED)
        self.assertIsNotNone(po.actual_delivery)

    def test_receive_item_not_found(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.submit()
        po.approve()
        po.send_to_supplier()
        with self.assertRaises(ValueError):
            po.receive_item("NONEXISTENT", 1)

    def test_receive_item_wrong_status(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        with self.assertRaises(ValueError):
            po.receive_item("SKU1", 1)

    def test_cancel(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        po.cancel("No longer needed")
        self.assertEqual(po.status, PurchaseOrderStatus.CANCELLED)
        self.assertIn("No longer needed", po.notes)

    def test_cancel_received_raises(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1",
                product_name="A",
                quantity=10,
                unit_price=5.0,
                received_quantity=10,
            )
        )
        po.status = PurchaseOrderStatus.RECEIVED
        with self.assertRaises(ValueError):
            po.cancel()

    def test_close(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1",
                product_name="A",
                quantity=10,
                unit_price=5.0,
                received_quantity=10,
            )
        )
        po.status = PurchaseOrderStatus.RECEIVED
        po.close()
        self.assertEqual(po.status, PurchaseOrderStatus.CLOSED)

    def test_close_non_received_raises(self):
        po = PurchaseOrder(supplier_id="sup-001")
        with self.assertRaises(ValueError):
            po.close()

    def test_to_dict(self):
        po = PurchaseOrder(supplier_id="sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        d = po.to_dict()
        self.assertEqual(d["supplier_id"], "sup-001")
        self.assertEqual(d["status"], "draft")
        self.assertEqual(d["total_amount"], 50.0)
        self.assertEqual(len(d["items"]), 1)


class TestPurchaseOrderManager(unittest.TestCase):
    """Tests for PurchaseOrderManager."""

    def setUp(self):
        self.mgr = PurchaseOrderManager()

    def test_create_order(self):
        po = self.mgr.create_order("sup-001")
        self.assertEqual(po.supplier_id, "sup-001")
        self.assertEqual(po.status, PurchaseOrderStatus.DRAFT)
        self.assertEqual(self.mgr.count(), 1)

    def test_get_order(self):
        po = self.mgr.create_order("sup-001")
        found = self.mgr.get_order(po.id)
        self.assertEqual(found.id, po.id)

    def test_get_order_not_found(self):
        self.assertIsNone(self.mgr.get_order("nonexistent"))

    def test_remove_order(self):
        po = self.mgr.create_order("sup-001")
        self.assertTrue(self.mgr.remove_order(po.id))
        self.assertEqual(self.mgr.count(), 0)

    def test_remove_order_not_found(self):
        self.assertFalse(self.mgr.remove_order("nonexistent"))

    def test_list_orders(self):
        self.mgr.create_order("sup-001")
        self.mgr.create_order("sup-002")
        self.assertEqual(len(self.mgr.list_orders()), 2)

    def test_list_orders_filter_by_status(self):
        po = self.mgr.create_order("sup-001")
        self.mgr.create_order("sup-002")
        drafts = self.mgr.list_orders(status=PurchaseOrderStatus.DRAFT)
        self.assertEqual(len(drafts), 2)

    def test_list_orders_filter_by_supplier(self):
        self.mgr.create_order("sup-001")
        self.mgr.create_order("sup-002")
        self.mgr.create_order("sup-001")
        orders = self.mgr.list_orders(supplier_id="sup-001")
        self.assertEqual(len(orders), 2)

    def test_get_orders_by_supplier(self):
        self.mgr.create_order("sup-001")
        self.mgr.create_order("sup-002")
        self.mgr.create_order("sup-001")
        orders = self.mgr.get_orders_by_supplier("sup-001")
        self.assertEqual(len(orders), 2)

    def test_get_open_orders(self):
        po1 = self.mgr.create_order("sup-001")
        po2 = self.mgr.create_order("sup-002")
        po2.cancel()
        open_orders = self.mgr.get_open_orders()
        self.assertEqual(len(open_orders), 1)
        self.assertEqual(open_orders[0].id, po1.id)

    def test_get_total_spend(self):
        po = self.mgr.create_order("sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        self.mgr.create_order("sup-002")
        total = self.mgr.get_total_spend()
        self.assertEqual(total, 50.0)

    def test_get_total_spend_by_supplier(self):
        po = self.mgr.create_order("sup-001")
        po.add_item(
            PurchaseOrderItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_price=5.0
            )
        )
        self.mgr.create_order("sup-002")
        total = self.mgr.get_total_spend(supplier_id="sup-001")
        self.assertEqual(total, 50.0)

    def test_clear(self):
        self.mgr.create_order("sup-001")
        self.mgr.clear()
        self.assertEqual(self.mgr.count(), 0)


# ═══════════════════════════════════════════════════════════════════════
# Logistics Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCarrier(unittest.TestCase):
    """Tests for Carrier."""

    def test_create_carrier(self):
        c = Carrier(name="FedEx", code="FDX")
        self.assertEqual(c.name, "FedEx")
        self.assertEqual(c.code, "FDX")
        self.assertTrue(c.is_active)
        self.assertTrue(c.id)

    def test_carrier_validation_empty_name(self):
        with self.assertRaises(ValueError):
            Carrier(name="")

    def test_get_tracking_url(self):
        c = Carrier(
            name="FedEx",
            tracking_url_template="https://fedex.com/track?num={tracking_number}",
        )
        url = c.get_tracking_url("12345")
        self.assertIn("12345", url)

    def test_get_tracking_url_no_template(self):
        c = Carrier(name="FedEx")
        url = c.get_tracking_url("12345")
        self.assertEqual(url, "")

    def test_to_dict(self):
        c = Carrier(name="FedEx", code="FDX")
        d = c.to_dict()
        self.assertEqual(d["name"], "FedEx")
        self.assertEqual(d["code"], "FDX")


class TestTrackingEvent(unittest.TestCase):
    """Tests for TrackingEvent."""

    def test_create_event(self):
        event = TrackingEvent(
            timestamp=datetime(2024, 1, 15, 10, 30),
            location="New York",
            description="Package picked up",
            status=ShipmentStatus.PICKED_UP,
        )
        self.assertEqual(event.location, "New York")
        self.assertEqual(event.status, ShipmentStatus.PICKED_UP)

    def test_to_dict(self):
        event = TrackingEvent(
            timestamp=datetime(2024, 1, 15, 10, 30),
            location="NYC",
            description="Picked up",
        )
        d = event.to_dict()
        self.assertEqual(d["location"], "NYC")
        self.assertIn("timestamp", d)


class TestShipment(unittest.TestCase):
    """Tests for Shipment."""

    def test_create_shipment(self):
        s = Shipment(
            carrier_id="carrier-001",
            origin="New York",
            destination="Los Angeles",
            weight_kg=10.5,
        )
        self.assertEqual(s.carrier_id, "carrier-001")
        self.assertEqual(s.origin, "New York")
        self.assertEqual(s.destination, "Los Angeles")
        self.assertEqual(s.weight_kg, 10.5)
        self.assertEqual(s.status, ShipmentStatus.PENDING)
        self.assertTrue(s.id)

    def test_shipment_validation_empty_carrier(self):
        with self.assertRaises(ValueError):
            Shipment(carrier_id="", origin="A", destination="B")

    def test_shipment_validation_empty_origin(self):
        with self.assertRaises(ValueError):
            Shipment(carrier_id="c1", origin="", destination="B")

    def test_shipment_validation_empty_destination(self):
        with self.assertRaises(ValueError):
            Shipment(carrier_id="c1", origin="A", destination="")

    def test_shipment_validation_negative_weight(self):
        with self.assertRaises(ValueError):
            Shipment(carrier_id="c1", origin="A", destination="B", weight_kg=-1)

    def test_shipment_validation_negative_cost(self):
        with self.assertRaises(ValueError):
            Shipment(carrier_id="c1", origin="A", destination="B", shipping_cost=-1)

    def test_volume_cm3(self):
        s = Shipment(
            carrier_id="c1",
            origin="A",
            destination="B",
            dimensions_cm=(10.0, 20.0, 30.0),
        )
        self.assertEqual(s.volume_cm3, 6000.0)

    def test_is_delivered(self):
        s = Shipment(carrier_id="c1", origin="A", destination="B")
        self.assertFalse(s.is_delivered)
        s.status = ShipmentStatus.DELIVERED
        self.assertTrue(s.is_delivered)

    def test_is_in_transit(self):
        s = Shipment(carrier_id="c1", origin="A", destination="B")
        self.assertFalse(s.is_in_transit)
        s.status = ShipmentStatus.IN_TRANSIT
        self.assertTrue(s.is_in_transit)

    def test_transit_time_hours(self):
        s = Shipment(carrier_id="c1", origin="A", destination="B")
        self.assertIsNone(s.transit_time_hours)
        s.actual_delivery = datetime.utcnow() + timedelta(hours=48)
        self.assertIsNotNone(s.transit_time_hours)
        self.assertAlmostEqual(s.transit_time_hours, 48.0, delta=1.0)

    def test_add_event(self):
        s = Shipment(carrier_id="c1", origin="A", destination="B")
        event = s.add_event("NYC", "Picked up", ShipmentStatus.PICKED_UP)
        self.assertEqual(len(s.events), 1)
        self.assertEqual(event.location, "NYC")
        self.assertEqual(s.status, ShipmentStatus.PICKED_UP)

    def test_update_status(self):
        s = Shipment(carrier_id="c1", origin="A", destination="B")
        s.update_status(ShipmentStatus.IN_TRANSIT, "Chicago", "In transit")
        self.assertEqual(s.status, ShipmentStatus.IN_TRANSIT)
        self.assertEqual(len(s.events), 1)

    def test_update_status_delivered(self):
        s = Shipment(carrier_id="c1", origin="A", destination="B")
        s.update_status(ShipmentStatus.DELIVERED, "LA", "Delivered")
        self.assertEqual(s.status, ShipmentStatus.DELIVERED)
        self.assertIsNotNone(s.actual_delivery)

    def test_cancel(self):
        s = Shipment(carrier_id="c1", origin="A", destination="B")
        s.cancel("Damaged")
        self.assertEqual(s.status, ShipmentStatus.CANCELLED)
        self.assertIn("Damaged", s.notes)

    def test_cancel_delivered_raises(self):
        s = Shipment(carrier_id="c1", origin="A", destination="B")
        s.status = ShipmentStatus.DELIVERED
        with self.assertRaises(ValueError):
            s.cancel()

    def test_to_dict(self):
        s = Shipment(
            carrier_id="c1",
            origin="A",
            destination="B",
            weight_kg=5.0,
        )
        d = s.to_dict()
        self.assertEqual(d["carrier_id"], "c1")
        self.assertEqual(d["weight_kg"], 5.0)
        self.assertIn("events", d)


class TestLogisticsManager(unittest.TestCase):
    """Tests for LogisticsManager."""

    def setUp(self):
        self.mgr = LogisticsManager()

    def test_add_carrier(self):
        c = Carrier(name="FedEx")
        self.mgr.add_carrier(c)
        self.assertEqual(self.mgr.count_carriers(), 1)

    def test_add_duplicate_carrier(self):
        c = Carrier(name="FedEx")
        self.mgr.add_carrier(c)
        with self.assertRaises(ValueError):
            self.mgr.add_carrier(c)

    def test_get_carrier(self):
        c = Carrier(name="FedEx")
        self.mgr.add_carrier(c)
        found = self.mgr.get_carrier(c.id)
        self.assertEqual(found.name, "FedEx")

    def test_get_carrier_not_found(self):
        self.assertIsNone(self.mgr.get_carrier("nonexistent"))

    def test_list_carriers(self):
        self.mgr.add_carrier(Carrier(name="FedEx", is_active=True))
        self.mgr.add_carrier(Carrier(name="UPS", is_active=False))
        self.assertEqual(len(self.mgr.list_carriers()), 2)
        self.assertEqual(len(self.mgr.list_carriers(active_only=True)), 1)

    def test_create_shipment(self):
        s = self.mgr.create_shipment(
            carrier_id="c1", origin="A", destination="B", weight_kg=5.0
        )
        self.assertEqual(s.carrier_id, "c1")
        self.assertEqual(self.mgr.count_shipments(), 1)

    def test_get_shipment(self):
        s = self.mgr.create_shipment(carrier_id="c1", origin="A", destination="B")
        found = self.mgr.get_shipment(s.id)
        self.assertEqual(found.id, s.id)

    def test_get_shipment_not_found(self):
        self.assertIsNone(self.mgr.get_shipment("nonexistent"))

    def test_remove_shipment(self):
        s = self.mgr.create_shipment(carrier_id="c1", origin="A", destination="B")
        self.assertTrue(self.mgr.remove_shipment(s.id))
        self.assertEqual(self.mgr.count_shipments(), 0)

    def test_remove_shipment_not_found(self):
        self.assertFalse(self.mgr.remove_shipment("nonexistent"))

    def test_list_shipments(self):
        self.mgr.create_shipment(carrier_id="c1", origin="A", destination="B")
        self.mgr.create_shipment(carrier_id="c2", origin="C", destination="D")
        self.assertEqual(len(self.mgr.list_shipments()), 2)

    def test_list_shipments_filter_by_status(self):
        s1 = self.mgr.create_shipment(carrier_id="c1", origin="A", destination="B")
        self.mgr.create_shipment(carrier_id="c2", origin="C", destination="D")
        s1.status = ShipmentStatus.DELIVERED
        delivered = self.mgr.list_shipments(status=ShipmentStatus.DELIVERED)
        self.assertEqual(len(delivered), 1)

    def test_list_shipments_filter_by_carrier(self):
        self.mgr.create_shipment(carrier_id="c1", origin="A", destination="B")
        self.mgr.create_shipment(carrier_id="c2", origin="C", destination="D")
        self.mgr.create_shipment(carrier_id="c1", origin="E", destination="F")
        shipments = self.mgr.list_shipments(carrier_id="c1")
        self.assertEqual(len(shipments), 2)

    def test_get_active_shipments(self):
        s1 = self.mgr.create_shipment(carrier_id="c1", origin="A", destination="B")
        self.mgr.create_shipment(carrier_id="c2", origin="C", destination="D")
        s1.status = ShipmentStatus.DELIVERED
        active = self.mgr.get_active_shipments()
        self.assertEqual(len(active), 1)

    def test_get_shipments_by_carrier(self):
        self.mgr.create_shipment(carrier_id="c1", origin="A", destination="B")
        self.mgr.create_shipment(carrier_id="c2", origin="C", destination="D")
        self.mgr.create_shipment(carrier_id="c1", origin="E", destination="F")
        shipments = self.mgr.get_shipments_by_carrier("c1")
        self.assertEqual(len(shipments), 2)

    def test_get_total_shipping_cost(self):
        self.mgr.create_shipment(
            carrier_id="c1", origin="A", destination="B", shipping_cost=10.0
        )
        self.mgr.create_shipment(
            carrier_id="c2", origin="C", destination="D", shipping_cost=20.0
        )
        self.assertEqual(self.mgr.get_total_shipping_cost(), 30.0)

    def test_clear(self):
        self.mgr.add_carrier(Carrier(name="FedEx"))
        self.mgr.create_shipment(carrier_id="c1", origin="A", destination="B")
        self.mgr.clear()
        self.assertEqual(self.mgr.count_carriers(), 0)
        self.assertEqual(self.mgr.count_shipments(), 0)


# ═══════════════════════════════════════════════════════════════════════
# Warehouse Tests
# ═══════════════════════════════════════════════════════════════════════


class TestWarehouseZone(unittest.TestCase):
    """Tests for WarehouseZone."""

    def test_create_zone(self):
        z = WarehouseZone(name="Receiving", code="RCV", capacity=500.0)
        self.assertEqual(z.name, "Receiving")
        self.assertEqual(z.code, "RCV")
        self.assertEqual(z.capacity, 500.0)
        self.assertTrue(z.is_active)
        self.assertTrue(z.id)

    def test_zone_validation_empty_name(self):
        with self.assertRaises(ValueError):
            WarehouseZone(name="")

    def test_zone_validation_negative_capacity(self):
        with self.assertRaises(ValueError):
            WarehouseZone(name="Test", capacity=-1)

    def test_volume_m3(self):
        z = WarehouseZone(name="Test", capacity=100.0)
        self.assertEqual(z.volume_m3, 100.0)

    def test_to_dict(self):
        z = WarehouseZone(name="Receiving", code="RCV")
        d = z.to_dict()
        self.assertEqual(d["name"], "Receiving")
        self.assertEqual(d["code"], "RCV")


class TestInventoryItem(unittest.TestCase):
    """Tests for InventoryItem."""

    def test_create_item(self):
        item = InventoryItem(
            product_sku="WIDGET-001",
            product_name="Widget",
            quantity=100,
            unit_cost=5.0,
        )
        self.assertEqual(item.product_sku, "WIDGET-001")
        self.assertEqual(item.quantity, 100)
        self.assertEqual(item.unit_cost, 5.0)
        self.assertTrue(item.id)

    def test_item_validation_empty_sku(self):
        with self.assertRaises(ValueError):
            InventoryItem(product_sku="", product_name="Widget")

    def test_item_validation_negative_quantity(self):
        with self.assertRaises(ValueError):
            InventoryItem(
                product_sku="SKU", product_name="Widget", quantity=-1
            )

    def test_item_validation_negative_unit_cost(self):
        with self.assertRaises(ValueError):
            InventoryItem(
                product_sku="SKU", product_name="Widget", unit_cost=-1.0
            )

    def test_total_value(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10, unit_cost=5.0
        )
        self.assertEqual(item.total_value, 50.0)

    def test_needs_reorder(self):
        item = InventoryItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=5,
            reorder_point=10,
        )
        self.assertTrue(item.needs_reorder)

    def test_no_reorder_needed(self):
        item = InventoryItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=15,
            reorder_point=10,
        )
        self.assertFalse(item.needs_reorder)

    def test_is_overstocked(self):
        item = InventoryItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=200,
            max_stock=100,
        )
        self.assertTrue(item.is_overstocked)

    def test_not_overstocked(self):
        item = InventoryItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=50,
            max_stock=100,
        )
        self.assertFalse(item.is_overstocked)

    def test_is_expired(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        item = InventoryItem(
            product_sku="SKU",
            product_name="Widget",
            expiry_date=yesterday,
        )
        self.assertTrue(item.is_expired)

    def test_not_expired(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        item = InventoryItem(
            product_sku="SKU",
            product_name="Widget",
            expiry_date=tomorrow,
        )
        self.assertFalse(item.is_expired)

    def test_no_expiry_date(self):
        item = InventoryItem(product_sku="SKU", product_name="Widget")
        self.assertFalse(item.is_expired)

    def test_add_stock(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        item.add_stock(5)
        self.assertEqual(item.quantity, 15)

    def test_add_stock_zero_raises(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        with self.assertRaises(ValueError):
            item.add_stock(0)

    def test_add_stock_with_cost(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10, unit_cost=5.0
        )
        item.add_stock(5, unit_cost=6.0)
        self.assertEqual(item.unit_cost, 6.0)

    def test_remove_stock(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        item.remove_stock(4)
        self.assertEqual(item.quantity, 6)

    def test_remove_stock_zero_raises(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        with self.assertRaises(ValueError):
            item.remove_stock(0)

    def test_remove_stock_exceeds_raises(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        with self.assertRaises(ValueError):
            item.remove_stock(11)

    def test_adjust_stock(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        item.adjust_stock(20, "Cycle count")
        self.assertEqual(item.quantity, 20)
        self.assertIn("Cycle count", item.notes)

    def test_adjust_stock_negative_raises(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        with self.assertRaises(ValueError):
            item.adjust_stock(-1)

    def test_to_dict(self):
        item = InventoryItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=10,
            unit_cost=5.0,
        )
        d = item.to_dict()
        self.assertEqual(d["product_sku"], "SKU")
        self.assertEqual(d["total_value"], 50.0)
        self.assertIn("needs_reorder", d)


class TestStockMovement(unittest.TestCase):
    """Tests for StockMovement."""

    def test_create_movement(self):
        m = StockMovement(
            item_id="item-001",
            movement_type=StockMovementType.RECEIPT,
            quantity=50,
        )
        self.assertEqual(m.item_id, "item-001")
        self.assertEqual(m.movement_type, StockMovementType.RECEIPT)
        self.assertEqual(m.quantity, 50)
        self.assertTrue(m.id)

    def test_movement_validation_empty_item(self):
        with self.assertRaises(ValueError):
            StockMovement(
                item_id="",
                movement_type=StockMovementType.RECEIPT,
                quantity=1,
            )

    def test_movement_validation_zero_quantity(self):
        with self.assertRaises(ValueError):
            StockMovement(
                item_id="item-001",
                movement_type=StockMovementType.RECEIPT,
                quantity=0,
            )

    def test_to_dict(self):
        m = StockMovement(
            item_id="item-001",
            movement_type=StockMovementType.ISSUE,
            quantity=10,
        )
        d = m.to_dict()
        self.assertEqual(d["item_id"], "item-001")
        self.assertEqual(d["movement_type"], "issue")


class TestWarehouse(unittest.TestCase):
    """Tests for Warehouse."""

    def test_create_warehouse(self):
        w = Warehouse(name="Main Warehouse", code="WH01")
        self.assertEqual(w.name, "Main Warehouse")
        self.assertEqual(w.code, "WH01")
        self.assertTrue(w.is_active)
        self.assertTrue(w.id)

    def test_warehouse_validation_empty_name(self):
        with self.assertRaises(ValueError):
            Warehouse(name="")

    def test_total_capacity(self):
        w = Warehouse(name="Main")
        w.add_zone(WarehouseZone(name="A", capacity=100.0))
        w.add_zone(WarehouseZone(name="B", capacity=200.0))
        self.assertEqual(w.total_capacity, 300.0)

    def test_zone_count(self):
        w = Warehouse(name="Main")
        w.add_zone(WarehouseZone(name="A"))
        w.add_zone(WarehouseZone(name="B"))
        self.assertEqual(w.zone_count, 2)

    def test_add_zone(self):
        w = Warehouse(name="Main")
        z = WarehouseZone(name="A")
        w.add_zone(z)
        self.assertEqual(len(w.zones), 1)

    def test_remove_zone(self):
        w = Warehouse(name="Main")
        z = WarehouseZone(name="A")
        w.add_zone(z)
        self.assertTrue(w.remove_zone(z.id))
        self.assertEqual(len(w.zones), 0)

    def test_remove_zone_not_found(self):
        w = Warehouse(name="Main")
        self.assertFalse(w.remove_zone("nonexistent"))

    def test_get_zone(self):
        w = Warehouse(name="Main")
        z = WarehouseZone(name="A")
        w.add_zone(z)
        found = w.get_zone(z.id)
        self.assertEqual(found.name, "A")

    def test_get_zone_not_found(self):
        w = Warehouse(name="Main")
        self.assertIsNone(w.get_zone("nonexistent"))

    def test_to_dict(self):
        w = Warehouse(name="Main", code="WH01")
        w.add_zone(WarehouseZone(name="A", capacity=100.0))
        d = w.to_dict()
        self.assertEqual(d["name"], "Main")
        self.assertEqual(d["total_capacity"], 100.0)
        self.assertEqual(d["zone_count"], 1)


class TestWarehouseManager(unittest.TestCase):
    """Tests for WarehouseManager."""

    def setUp(self):
        self.mgr = WarehouseManager()

    def test_add_warehouse(self):
        w = Warehouse(name="Main")
        self.mgr.add_warehouse(w)
        self.assertEqual(self.mgr.count_warehouses(), 1)

    def test_add_duplicate_warehouse(self):
        w = Warehouse(name="Main")
        self.mgr.add_warehouse(w)
        with self.assertRaises(ValueError):
            self.mgr.add_warehouse(w)

    def test_get_warehouse(self):
        w = Warehouse(name="Main")
        self.mgr.add_warehouse(w)
        found = self.mgr.get_warehouse(w.id)
        self.assertEqual(found.name, "Main")

    def test_get_warehouse_not_found(self):
        self.assertIsNone(self.mgr.get_warehouse("nonexistent"))

    def test_remove_warehouse(self):
        w = Warehouse(name="Main")
        self.mgr.add_warehouse(w)
        self.assertTrue(self.mgr.remove_warehouse(w.id))
        self.assertEqual(self.mgr.count_warehouses(), 0)

    def test_remove_warehouse_not_found(self):
        self.assertFalse(self.mgr.remove_warehouse("nonexistent"))

    def test_list_warehouses(self):
        self.mgr.add_warehouse(Warehouse(name="A", is_active=True))
        self.mgr.add_warehouse(Warehouse(name="B", is_active=False))
        self.assertEqual(len(self.mgr.list_warehouses()), 2)
        self.assertEqual(len(self.mgr.list_warehouses(active_only=True)), 1)

    def test_add_inventory_item(self):
        item = InventoryItem(product_sku="SKU", product_name="Widget")
        self.mgr.add_inventory_item(item)
        self.assertEqual(self.mgr.count_inventory_items(), 1)

    def test_add_duplicate_inventory_item(self):
        item = InventoryItem(product_sku="SKU", product_name="Widget")
        self.mgr.add_inventory_item(item)
        with self.assertRaises(ValueError):
            self.mgr.add_inventory_item(item)

    def test_get_inventory_item(self):
        item = InventoryItem(product_sku="SKU", product_name="Widget")
        self.mgr.add_inventory_item(item)
        found = self.mgr.get_inventory_item(item.id)
        self.assertEqual(found.product_sku, "SKU")

    def test_get_inventory_item_not_found(self):
        self.assertIsNone(self.mgr.get_inventory_item("nonexistent"))

    def test_get_inventory_by_sku(self):
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU1", product_name="A")
        )
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU1", product_name="A2")
        )
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU2", product_name="B")
        )
        items = self.mgr.get_inventory_by_sku("SKU1")
        self.assertEqual(len(items), 2)

    def test_remove_inventory_item(self):
        item = InventoryItem(product_sku="SKU", product_name="Widget")
        self.mgr.add_inventory_item(item)
        self.assertTrue(self.mgr.remove_inventory_item(item.id))
        self.assertEqual(self.mgr.count_inventory_items(), 0)

    def test_remove_inventory_item_not_found(self):
        self.assertFalse(self.mgr.remove_inventory_item("nonexistent"))

    def test_list_inventory(self):
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU1", product_name="A")
        )
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU2", product_name="B")
        )
        self.assertEqual(len(self.mgr.list_inventory()), 2)

    def test_list_inventory_filter_by_zone(self):
        item1 = InventoryItem(
            product_sku="SKU1", product_name="A", zone_id="zone1"
        )
        item2 = InventoryItem(
            product_sku="SKU2", product_name="B", zone_id="zone2"
        )
        self.mgr.add_inventory_item(item1)
        self.mgr.add_inventory_item(item2)
        items = self.mgr.list_inventory(zone_id="zone1")
        self.assertEqual(len(items), 1)

    def test_list_inventory_filter_by_warehouse(self):
        w = Warehouse(name="Main")
        z = WarehouseZone(name="A")
        w.add_zone(z)
        self.mgr.add_warehouse(w)
        item = InventoryItem(
            product_sku="SKU1", product_name="A", zone_id=z.id
        )
        self.mgr.add_inventory_item(item)
        items = self.mgr.list_inventory(warehouse_id=w.id)
        self.assertEqual(len(items), 1)

    def test_get_low_stock_items(self):
        self.mgr.add_inventory_item(
            InventoryItem(
                product_sku="SKU1",
                product_name="A",
                quantity=5,
                reorder_point=10,
            )
        )
        self.mgr.add_inventory_item(
            InventoryItem(
                product_sku="SKU2",
                product_name="B",
                quantity=20,
                reorder_point=10,
            )
        )
        low = self.mgr.get_low_stock_items()
        self.assertEqual(len(low), 1)
        self.assertEqual(low[0].product_sku, "SKU1")

    def test_get_expired_items(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU1", product_name="A", expiry_date=yesterday)
        )
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU2", product_name="B", expiry_date=tomorrow)
        )
        expired = self.mgr.get_expired_items()
        self.assertEqual(len(expired), 1)

    def test_get_total_inventory_value(self):
        self.mgr.add_inventory_item(
            InventoryItem(
                product_sku="SKU1", product_name="A", quantity=10, unit_cost=5.0
            )
        )
        self.mgr.add_inventory_item(
            InventoryItem(
                product_sku="SKU2", product_name="B", quantity=20, unit_cost=3.0
            )
        )
        self.assertEqual(self.mgr.get_total_inventory_value(), 110.0)

    def test_get_total_quantity(self):
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU1", product_name="A", quantity=10)
        )
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU2", product_name="B", quantity=20)
        )
        self.assertEqual(self.mgr.get_total_quantity(), 30)

    def test_record_movement(self):
        m = StockMovement(
            item_id="item-001",
            movement_type=StockMovementType.RECEIPT,
            quantity=50,
        )
        self.mgr.record_movement(m)
        self.assertEqual(self.mgr.count_movements(), 1)

    def test_record_duplicate_movement(self):
        m = StockMovement(
            item_id="item-001",
            movement_type=StockMovementType.RECEIPT,
            quantity=50,
        )
        self.mgr.record_movement(m)
        with self.assertRaises(ValueError):
            self.mgr.record_movement(m)

    def test_get_movement(self):
        m = StockMovement(
            item_id="item-001",
            movement_type=StockMovementType.RECEIPT,
            quantity=50,
        )
        self.mgr.record_movement(m)
        found = self.mgr.get_movement(m.id)
        self.assertEqual(found.item_id, "item-001")

    def test_get_movement_not_found(self):
        self.assertIsNone(self.mgr.get_movement("nonexistent"))

    def test_list_movements(self):
        self.mgr.record_movement(
            StockMovement(
                item_id="item-001",
                movement_type=StockMovementType.RECEIPT,
                quantity=50,
            )
        )
        self.mgr.record_movement(
            StockMovement(
                item_id="item-002",
                movement_type=StockMovementType.ISSUE,
                quantity=10,
            )
        )
        self.assertEqual(len(self.mgr.list_movements()), 2)

    def test_list_movements_filter_by_item(self):
        self.mgr.record_movement(
            StockMovement(
                item_id="item-001",
                movement_type=StockMovementType.RECEIPT,
                quantity=50,
            )
        )
        self.mgr.record_movement(
            StockMovement(
                item_id="item-002",
                movement_type=StockMovementType.ISSUE,
                quantity=10,
            )
        )
        movements = self.mgr.list_movements(item_id="item-001")
        self.assertEqual(len(movements), 1)

    def test_list_movements_filter_by_type(self):
        self.mgr.record_movement(
            StockMovement(
                item_id="item-001",
                movement_type=StockMovementType.RECEIPT,
                quantity=50,
            )
        )
        self.mgr.record_movement(
            StockMovement(
                item_id="item-002",
                movement_type=StockMovementType.ISSUE,
                quantity=10,
            )
        )
        movements = self.mgr.list_movements(
            movement_type=StockMovementType.RECEIPT
        )
        self.assertEqual(len(movements), 1)

    def test_receive_stock(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        self.mgr.add_inventory_item(item)
        m = self.mgr.receive_stock(item.id, 50, reference="PO-001")
        self.assertEqual(m.movement_type, StockMovementType.RECEIPT)
        self.assertEqual(m.quantity, 50)
        updated = self.mgr.get_inventory_item(item.id)
        self.assertEqual(updated.quantity, 60)

    def test_receive_stock_item_not_found(self):
        with self.assertRaises(ValueError):
            self.mgr.receive_stock("nonexistent", 10)

    def test_issue_stock(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=50
        )
        self.mgr.add_inventory_item(item)
        m = self.mgr.issue_stock(item.id, 10, reference="SO-001")
        self.assertEqual(m.movement_type, StockMovementType.ISSUE)
        self.assertEqual(m.quantity, 10)
        updated = self.mgr.get_inventory_item(item.id)
        self.assertEqual(updated.quantity, 40)

    def test_issue_stock_item_not_found(self):
        with self.assertRaises(ValueError):
            self.mgr.issue_stock("nonexistent", 10)

    def test_transfer_stock(self):
        item = InventoryItem(
            product_sku="SKU",
            product_name="Widget",
            quantity=50,
            zone_id="zone1",
        )
        self.mgr.add_inventory_item(item)
        m = self.mgr.transfer_stock(item.id, 10, to_zone_id="zone2")
        self.assertEqual(m.movement_type, StockMovementType.TRANSFER)
        self.assertEqual(m.from_zone_id, "zone1")
        self.assertEqual(m.to_zone_id, "zone2")

    def test_transfer_stock_item_not_found(self):
        with self.assertRaises(ValueError):
            self.mgr.transfer_stock("nonexistent", 10, to_zone_id="zone2")

    def test_transfer_stock_exceeds_raises(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=5
        )
        self.mgr.add_inventory_item(item)
        with self.assertRaises(ValueError):
            self.mgr.transfer_stock(item.id, 10, to_zone_id="zone2")

    def test_adjust_stock(self):
        item = InventoryItem(
            product_sku="SKU", product_name="Widget", quantity=10
        )
        self.mgr.add_inventory_item(item)
        m = self.mgr.adjust_stock(item.id, 20, reason="Cycle count")
        self.assertEqual(m.movement_type, StockMovementType.ADJUSTMENT)
        updated = self.mgr.get_inventory_item(item.id)
        self.assertEqual(updated.quantity, 20)

    def test_adjust_stock_item_not_found(self):
        with self.assertRaises(ValueError):
            self.mgr.adjust_stock("nonexistent", 10)

    def test_clear(self):
        self.mgr.add_warehouse(Warehouse(name="Main"))
        self.mgr.add_inventory_item(
            InventoryItem(product_sku="SKU", product_name="Widget")
        )
        self.mgr.clear()
        self.assertEqual(self.mgr.count_warehouses(), 0)
        self.assertEqual(self.mgr.count_inventory_items(), 0)
        self.assertEqual(self.mgr.count_movements(), 0)


# ═══════════════════════════════════════════════════════════════════════
# Demand Forecasting Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDemandForecast(unittest.TestCase):
    """Tests for DemandForecast configuration."""

    def test_create_forecast(self):
        f = DemandForecast(
            product_sku="WIDGET-001",
            historical_data=[100, 120, 110, 130, 125],
        )
        self.assertEqual(f.product_sku, "WIDGET-001")
        self.assertEqual(f.method, ForecastingMethod.MOVING_AVERAGE)
        self.assertEqual(f.forecast_periods, 1)
        self.assertTrue(f.id)

    def test_forecast_validation_empty_sku(self):
        with self.assertRaises(ValueError):
            DemandForecast(product_sku="", historical_data=[1, 2, 3])

    def test_forecast_validation_zero_periods(self):
        with self.assertRaises(ValueError):
            DemandForecast(
                product_sku="SKU",
                historical_data=[1, 2, 3],
                forecast_periods=0,
            )

    def test_forecast_validation_alpha_too_high(self):
        with self.assertRaises(ValueError):
            DemandForecast(
                product_sku="SKU",
                historical_data=[1, 2, 3],
                alpha=1.5,
            )

    def test_forecast_validation_alpha_negative(self):
        with self.assertRaises(ValueError):
            DemandForecast(
                product_sku="SKU",
                historical_data=[1, 2, 3],
                alpha=-0.1,
            )

    def test_forecast_validation_zero_seasonality(self):
        with self.assertRaises(ValueError):
            DemandForecast(
                product_sku="SKU",
                historical_data=[1, 2, 3],
                seasonality_period=0,
            )

    def test_forecast_validation_negative_data(self):
        with self.assertRaises(ValueError):
            DemandForecast(product_sku="SKU", historical_data=[1, -2, 3])

    def test_data_count(self):
        f = DemandForecast(
            product_sku="SKU", historical_data=[1, 2, 3, 4, 5]
        )
        self.assertEqual(f.data_count, 5)

    def test_mean_demand(self):
        f = DemandForecast(
            product_sku="SKU", historical_data=[10, 20, 30]
        )
        self.assertEqual(f.mean_demand, 20.0)

    def test_mean_demand_empty(self):
        f = DemandForecast(product_sku="SKU", historical_data=[])
        self.assertEqual(f.mean_demand, 0.0)

    def test_std_deviation(self):
        f = DemandForecast(
            product_sku="SKU", historical_data=[2, 4, 4, 4, 5, 5, 7, 9]
        )
        self.assertAlmostEqual(f.std_deviation, 2.138, places=2)

    def test_std_deviation_single_value(self):
        f = DemandForecast(product_sku="SKU", historical_data=[5])
        self.assertEqual(f.std_deviation, 0.0)

    def test_trend_positive(self):
        f = DemandForecast(
            product_sku="SKU", historical_data=[1, 2, 3, 4, 5]
        )
        self.assertGreater(f.trend, 0)

    def test_trend_negative(self):
        f = DemandForecast(
            product_sku="SKU", historical_data=[5, 4, 3, 2, 1]
        )
        self.assertLess(f.trend, 0)

    def test_trend_single_value(self):
        f = DemandForecast(product_sku="SKU", historical_data=[5])
        self.assertEqual(f.trend, 0.0)

    def test_to_dict(self):
        f = DemandForecast(
            product_sku="SKU",
            historical_data=[10, 20, 30],
            method=ForecastingMethod.MOVING_AVERAGE,
        )
        d = f.to_dict()
        self.assertEqual(d["product_sku"], "SKU")
        self.assertEqual(d["method"], "moving_average")
        self.assertEqual(d["mean_demand"], 20.0)
        self.assertIn("trend", d)


class TestForecastResult(unittest.TestCase):
    """Tests for ForecastResult."""

    def test_create_result(self):
        r = ForecastResult(
            product_sku="SKU",
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_values=[100.0, 110.0, 120.0],
        )
        self.assertEqual(r.product_sku, "SKU")
        self.assertEqual(len(r.forecast_values), 3)
        self.assertTrue(r.id)

    def test_result_validation_empty_sku(self):
        with self.assertRaises(ValueError):
            ForecastResult(
                product_sku="",
                method=ForecastingMethod.MOVING_AVERAGE,
                forecast_values=[100.0],
            )

    def test_result_validation_negative_values(self):
        with self.assertRaises(ValueError):
            ForecastResult(
                product_sku="SKU",
                method=ForecastingMethod.MOVING_AVERAGE,
                forecast_values=[-100.0],
            )

    def test_total_forecast(self):
        r = ForecastResult(
            product_sku="SKU",
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_values=[100.0, 200.0, 300.0],
        )
        self.assertEqual(r.total_forecast, 600.0)

    def test_average_forecast(self):
        r = ForecastResult(
            product_sku="SKU",
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_values=[100.0, 200.0, 300.0],
        )
        self.assertEqual(r.average_forecast, 200.0)

    def test_average_forecast_empty(self):
        r = ForecastResult(
            product_sku="SKU",
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_values=[],
        )
        self.assertEqual(r.average_forecast, 0.0)

    def test_max_forecast(self):
        r = ForecastResult(
            product_sku="SKU",
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_values=[100.0, 300.0, 200.0],
        )
        self.assertEqual(r.max_forecast, 300.0)

    def test_min_forecast(self):
        r = ForecastResult(
            product_sku="SKU",
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_values=[100.0, 300.0, 200.0],
        )
        self.assertEqual(r.min_forecast, 100.0)

    def test_to_dict(self):
        r = ForecastResult(
            product_sku="SKU",
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_values=[100.0, 200.0],
        )
        d = r.to_dict()
        self.assertEqual(d["product_sku"], "SKU")
        self.assertEqual(d["total_forecast"], 300.0)
        self.assertIn("mae", d)
        self.assertIn("rmse", d)
        self.assertIn("mape", d)


class TestDemandForecaster(unittest.TestCase):
    """Tests for DemandForecaster."""

    def setUp(self):
        self.forecaster = DemandForecaster()

    def test_create_forecast(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50],
        )
        self.assertEqual(f.product_sku, "SKU")
        self.assertEqual(self.forecaster.count_forecasts(), 1)

    def test_get_forecast(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU", historical_data=[10, 20, 30]
        )
        found = self.forecaster.get_forecast(f.id)
        self.assertEqual(found.product_sku, "SKU")

    def test_get_forecast_not_found(self):
        self.assertIsNone(self.forecaster.get_forecast("nonexistent"))

    def test_remove_forecast(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU", historical_data=[10, 20, 30]
        )
        self.assertTrue(self.forecaster.remove_forecast(f.id))
        self.assertEqual(self.forecaster.count_forecasts(), 0)

    def test_remove_forecast_not_found(self):
        self.assertFalse(self.forecaster.remove_forecast("nonexistent"))

    def test_list_forecasts(self):
        self.forecaster.create_forecast(
            product_sku="SKU1", historical_data=[10, 20, 30]
        )
        self.forecaster.create_forecast(
            product_sku="SKU2", historical_data=[40, 50, 60]
        )
        self.assertEqual(len(self.forecaster.list_forecasts()), 2)

    def test_list_forecasts_filter_by_sku(self):
        self.forecaster.create_forecast(
            product_sku="SKU1", historical_data=[10, 20, 30]
        )
        self.forecaster.create_forecast(
            product_sku="SKU2", historical_data=[40, 50, 60]
        )
        forecasts = self.forecaster.list_forecasts(product_sku="SKU1")
        self.assertEqual(len(forecasts), 1)

    def test_generate_forecast_moving_average(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50],
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_periods=3,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(len(result.forecast_values), 3)
        self.assertTrue(all(v > 0 for v in result.forecast_values))

    def test_generate_forecast_exponential_smoothing(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50],
            method=ForecastingMethod.EXPONENTIAL_SMOOTHING,
            forecast_periods=3,
            alpha=0.5,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(len(result.forecast_values), 3)

    def test_generate_forecast_linear_regression(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50],
            method=ForecastingMethod.LINEAR_REGRESSION,
            forecast_periods=3,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(len(result.forecast_values), 3)
        # Linear regression on perfectly linear data should produce increasing values
        self.assertGreaterEqual(
            result.forecast_values[1], result.forecast_values[0]
        )

    def test_generate_forecast_seasonal_naive(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30, 10, 20, 30],
            method=ForecastingMethod.SEASONAL_NAIVE,
            forecast_periods=3,
            seasonality_period=3,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(len(result.forecast_values), 3)

    def test_generate_forecast_weighted_moving_average(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50],
            method=ForecastingMethod.WEIGHTED_MOVING_AVERAGE,
            forecast_periods=3,
            weights=[1, 2, 3],
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(len(result.forecast_values), 3)

    def test_generate_forecast_not_found(self):
        with self.assertRaises(ValueError):
            self.forecaster.generate_forecast("nonexistent")

    def test_generate_forecast_with_confidence_intervals(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50],
            forecast_periods=3,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(len(result.confidence_lower), 3)
        self.assertEqual(len(result.confidence_upper), 3)
        for i in range(3):
            self.assertLessEqual(result.confidence_lower[i], result.forecast_values[i])
            self.assertGreaterEqual(result.confidence_upper[i], result.forecast_values[i])

    def test_generate_forecast_with_backtest_metrics(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50, 60, 70, 80],
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_periods=1,
        )
        result = self.forecaster.generate_forecast(f.id)
        # With 8 data points, backtest should produce metrics
        self.assertGreaterEqual(result.mae, 0)
        self.assertGreaterEqual(result.rmse, 0)
        self.assertGreaterEqual(result.mape, 0)

    def test_get_results(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30],
            forecast_periods=1,
        )
        self.forecaster.generate_forecast(f.id)
        results = self.forecaster.get_results("SKU")
        self.assertEqual(len(results), 1)

    def test_get_results_empty(self):
        results = self.forecaster.get_results("NONEXISTENT")
        self.assertEqual(len(results), 0)

    def test_compare_methods(self):
        results = self.forecaster.compare_methods(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50],
            forecast_periods=3,
        )
        self.assertEqual(len(results), len(ForecastingMethod))
        for method in ForecastingMethod:
            self.assertIn(method.value, results)

    def test_get_best_method(self):
        best_method, best_result = self.forecaster.get_best_method(
            product_sku="SKU",
            historical_data=[10, 20, 30, 40, 50],
            forecast_periods=1,
        )
        self.assertIn(best_method, [m.value for m in ForecastingMethod])
        self.assertIsInstance(best_result, ForecastResult)

    def test_clear(self):
        self.forecaster.create_forecast(
            product_sku="SKU", historical_data=[10, 20, 30]
        )
        self.forecaster.clear()
        self.assertEqual(self.forecaster.count_forecasts(), 0)

    def test_moving_average_empty_data(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[],
            method=ForecastingMethod.MOVING_AVERAGE,
            forecast_periods=3,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(result.forecast_values, [0.0, 0.0, 0.0])

    def test_exponential_smoothing_empty_data(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[],
            method=ForecastingMethod.EXPONENTIAL_SMOOTHING,
            forecast_periods=3,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(result.forecast_values, [0.0, 0.0, 0.0])

    def test_linear_regression_empty_data(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[],
            method=ForecastingMethod.LINEAR_REGRESSION,
            forecast_periods=3,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(result.forecast_values, [0.0, 0.0, 0.0])

    def test_seasonal_naive_empty_data(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[],
            method=ForecastingMethod.SEASONAL_NAIVE,
            forecast_periods=3,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(result.forecast_values, [0.0, 0.0, 0.0])

    def test_forecast_dates_generated(self):
        f = self.forecaster.create_forecast(
            product_sku="SKU",
            historical_data=[10, 20, 30],
            forecast_periods=5,
        )
        result = self.forecaster.generate_forecast(f.id)
        self.assertEqual(len(result.forecast_dates), 5)
        # Dates should be in the future
        today = date.today()
        for d in result.forecast_dates:
            parsed = date.fromisoformat(d)
            self.assertGreater(parsed, today)


if __name__ == "__main__":
    unittest.main()
