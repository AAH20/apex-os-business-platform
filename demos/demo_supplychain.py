#!/usr/bin/env python3
"""Supply Chain Demo — supplier, PO, receiving, stock, reporting."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Supplier:
    id: int
    name: str
    contact: str
    lead_time_days: int


@dataclass
class PurchaseOrder:
    id: int
    supplier: Supplier
    items: dict  # sku -> qty
    status: str = "OPEN"


@dataclass
class Inventory:
    stock: dict = field(default_factory=dict)  # sku -> qty

    def receive(self, po: PurchaseOrder):
        for sku, qty in po.items.items():
            self.stock[sku] = self.stock.get(sku, 0) + qty
        po.status = "RECEIVED"

    def adjust(self, sku: str, delta: int):
        self.stock[sku] = self.stock.get(sku, 0) + delta

    def report(self):
        print("\n=== INVENTORY REPORT ===")
        print(f"Generated: {datetime.now():%Y-%m-%d %H:%M}")
        print(f"{'SKU':<15} {'Qty':>6}")
        print("-" * 23)
        for sku, qty in sorted(self.stock.items()):
            print(f"{sku:<15} {qty:>6}")
        print(f"\nTotal SKUs: {len(self.stock)}")
        print(f"Total Units: {sum(self.stock.values())}")


def create_supplier():
    s = Supplier(id=1, name="Acme Parts Co.", contact="orders@acme.example", lead_time_days=5)
    print(f"[1] Created supplier: {s.name} (lead time {s.lead_time_days}d)")
    return s


def create_purchase_order(supplier):
    po = PurchaseOrder(id=1001, supplier=supplier, items={"WIDGET-A": 50, "WIDGET-B": 30})
    print(f"[2] Created PO #{po.id} for {po.supplier.name}: {po.items}")
    return po


def receive_inventory(po, inventory):
    inventory.receive(po)
    print(f"[3] Received PO #{po.id} → stock updated: {po.items}")


def update_stock(inventory):
    inventory.adjust("WIDGET-A", -5)  # issue 5 to production
    print(f"[4] Stock update: WIDGET-A -5 (production issue)")


def generate_report(inventory):
    inventory.report()


def main():
    print("=" * 50)
    print("  SUPPLY CHAIN DEMO")
    print("=" * 50)
    supplier = create_supplier()
    po = create_purchase_order(supplier)
    inventory = Inventory()
    receive_inventory(po, inventory)
    update_stock(inventory)
    generate_report(inventory)


if __name__ == "__main__":
    main()
