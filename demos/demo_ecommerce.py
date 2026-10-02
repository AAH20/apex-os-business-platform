"""E-commerce demo: product → cart → checkout → payment → fulfillment.

Run: python demos/demo_ecommerce.py
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Product:
    name: str
    price: float
    sku: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class Cart:
    items: list[tuple[Product, int]] = field(default_factory=list)

    def add(self, product: Product, qty: int = 1) -> None:
        self.items.append((product, qty))

    @property
    def total(self) -> float:
        return sum(p.price * q for p, q in self.items)


@dataclass
class Order:
    order_id: str
    cart: Cart
    status: str = "pending"


def create_product() -> Product:
    p = Product(name="Mechanical Keyboard", price=149.99)
    print(f"[1] Created product: {p.name} (SKU: {p.sku}) — ${p.price:.2f}")
    return p


def add_to_cart(product: Product) -> Cart:
    cart = Cart()
    cart.add(product, qty=1)
    print(f"[2] Added to cart: {product.name} × 1 — cart total: ${cart.total:.2f}")
    return cart


def checkout(cart: Cart) -> Order:
    order = Order(order_id=str(uuid.uuid4())[:12], cart=cart)
    print(f"[3] Checkout complete — order {order.order_id} placed (${cart.total:.2f})")
    return order


def process_payment(order: Order) -> None:
    order.status = "paid"
    print(f"[4] Payment processed for order {order.order_id} — status: {order.status}")


def fulfill_order(order: Order) -> None:
    order.status = "fulfilled"
    print(f"[5] Order {order.order_id} fulfilled — status: {order.status}")


def main() -> None:
    print("=== E-commerce Demo ===")
    product = create_product()
    cart = add_to_cart(product)
    order = checkout(cart)
    process_payment(order)
    fulfill_order(order)
    print("=== Done ===")


if __name__ == "__main__":
    main()
