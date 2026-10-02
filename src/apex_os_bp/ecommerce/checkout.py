"""Checkout process: converts a cart into an order."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import (
    Address,
    Cart,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
)


@dataclass
class CheckoutResult:
    success: bool
    order: Optional[Order] = None
    error_message: str = ""
    requires_payment: bool = True


class Checkout:
    """Handles the checkout flow from cart to order."""

    def __init__(
        self,
        tax_rate: float = 0.0,
        shipping_rate: float = 0.0,
        free_shipping_threshold: float = 0.0,
    ) -> None:
        self.tax_rate = tax_rate
        self.shipping_rate = shipping_rate
        self.free_shipping_threshold = free_shipping_threshold

    def process(
        self,
        cart: Cart,
        customer: Customer,
        shipping_address: Address,
        billing_address: Optional[Address] = None,
        payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        notes: str = "",
    ) -> CheckoutResult:
        if cart.is_empty():
            return CheckoutResult(
                success=False,
                error_message="Cart is empty",
            )

        if not customer.validate():
            return CheckoutResult(
                success=False,
                error_message="Invalid customer data",
            )

        if not shipping_address.validate():
            return CheckoutResult(
                success=False,
                error_message="Invalid shipping address",
            )

        billing = billing_address or shipping_address
        if not billing.validate():
            return CheckoutResult(
                success=False,
                error_message="Invalid billing address",
            )

        # Validate stock for all items
        for item in cart.items:
            if not item.product.is_in_stock(item.quantity):
                return CheckoutResult(
                    success=False,
                    error_message=f"Insufficient stock for {item.product.name}",
                )

        # Build order items
        order_items = [
            OrderItem(
                product_id=item.product.id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.product.price,
            )
            for item in cart.items
        ]

        # Calculate shipping
        shipping_cost = 0.0
        if self.free_shipping_threshold > 0 and cart.total >= self.free_shipping_threshold:
            shipping_cost = 0.0
        else:
            shipping_cost = self.shipping_rate

        order = Order(
            customer_id=customer.id,
            items=order_items,
            status=OrderStatus.PENDING,
            shipping_address=shipping_address,
            billing_address=billing,
            notes=notes,
        )
        order.calculate_totals(tax_rate=self.tax_rate, shipping_cost=shipping_cost)

        # Reserve stock
        for item in cart.items:
            item.product.reserve(item.quantity)

        # Clear the cart
        cart.clear()

        return CheckoutResult(
            success=True,
            order=order,
            requires_payment=(payment_method != PaymentMethod.CASH_ON_DELIVERY),
        )
