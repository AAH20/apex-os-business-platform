"""Shopping cart management."""

from __future__ import annotations

from typing import Optional

from .models import Cart, CartItem, Product


class ShoppingCart:
    """Manages shopping cart operations."""

    def __init__(self, customer_id: Optional[str] = None) -> None:
        self.cart = Cart(customer_id=customer_id)

    def add_item(self, product: Product, quantity: int = 1) -> Cart:
        self.cart.add_item(product, quantity)
        return self.cart

    def remove_item(self, product_id: str) -> Cart:
        self.cart.remove_item(product_id)
        return self.cart

    def update_quantity(self, product_id: str, quantity: int) -> Cart:
        self.cart.update_quantity(product_id, quantity)
        return self.cart

    def clear(self) -> Cart:
        self.cart.clear()
        return self.cart

    def get_total(self) -> float:
        return self.cart.total

    def get_item_count(self) -> int:
        return self.cart.item_count

    def is_empty(self) -> bool:
        return self.cart.is_empty()

    def get_items(self) -> list[CartItem]:
        return list(self.cart.items)

    def to_cart(self) -> Cart:
        return self.cart
