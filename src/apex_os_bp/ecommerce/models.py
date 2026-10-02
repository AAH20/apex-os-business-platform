"""Data models for the e-commerce system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cash_on_delivery"


@dataclass
class Address:
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone: Optional[str] = None

    def validate(self) -> bool:
        return all(
            [
                bool(self.street.strip()),
                bool(self.city.strip()),
                bool(self.state.strip()),
                bool(self.postal_code.strip()),
                bool(self.country.strip()),
            ]
        )


@dataclass
class Customer:
    id: str = field(default_factory=_new_id)
    name: str = ""
    email: str = ""
    shipping_address: Optional[Address] = None
    billing_address: Optional[Address] = None

    def validate(self) -> bool:
        return bool(self.name.strip()) and bool(self.email.strip())


@dataclass
class Product:
    id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    price: float = 0.0
    sku: str = ""
    stock_quantity: int = 0
    category: str = ""
    image_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)

    def validate(self) -> bool:
        return (
            bool(self.name.strip())
            and self.price >= 0
            and self.stock_quantity >= 0
            and bool(self.sku.strip())
        )

    def is_in_stock(self, quantity: int = 1) -> bool:
        return self.is_active and self.stock_quantity >= quantity

    def reserve(self, quantity: int) -> bool:
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            return True
        return False

    def release(self, quantity: int) -> None:
        self.stock_quantity += quantity


@dataclass
class CartItem:
    product: Product
    quantity: int = 1

    @property
    def subtotal(self) -> float:
        return round(self.product.price * self.quantity, 2)

    def validate(self) -> bool:
        return self.quantity > 0 and self.product.is_in_stock(self.quantity)


@dataclass
class Cart:
    id: str = field(default_factory=_new_id)
    customer_id: Optional[str] = None
    items: list[CartItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def total(self) -> float:
        return round(sum(item.subtotal for item in self.items), 2)

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    def add_item(self, product: Product, quantity: int = 1) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if not product.is_in_stock(quantity):
            raise ValueError(f"Insufficient stock for {product.name}")
        for item in self.items:
            if item.product.id == product.id:
                new_qty = item.quantity + quantity
                if not product.is_in_stock(new_qty):
                    raise ValueError(f"Insufficient stock for {product.name}")
                item.quantity = new_qty
                self.updated_at = _utcnow()
                return
        self.items.append(CartItem(product=product, quantity=quantity))
        self.updated_at = _utcnow()

    def remove_item(self, product_id: str) -> None:
        self.items = [i for i in self.items if i.product.id != product_id]
        self.updated_at = _utcnow()

    def update_quantity(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            self.remove_item(product_id)
            return
        for item in self.items:
            if item.product.id == product_id:
                if not item.product.is_in_stock(quantity):
                    raise ValueError(f"Insufficient stock for {item.product.name}")
                item.quantity = quantity
                self.updated_at = _utcnow()
                return
        raise ValueError(f"Product {product_id} not in cart")

    def clear(self) -> None:
        self.items.clear()
        self.updated_at = _utcnow()

    def is_empty(self) -> bool:
        return len(self.items) == 0


@dataclass
class OrderItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return round(self.unit_price * self.quantity, 2)


@dataclass
class Order:
    id: str = field(default_factory=_new_id)
    customer_id: str = ""
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    shipping_address: Optional[Address] = None
    billing_address: Optional[Address] = None
    subtotal: float = 0.0
    tax: float = 0.0
    shipping_cost: float = 0.0
    total: float = 0.0
    payment_id: Optional[str] = None
    notes: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def calculate_totals(self, tax_rate: float = 0.0, shipping_cost: float = 0.0) -> None:
        self.subtotal = round(sum(item.subtotal for item in self.items), 2)
        self.tax = round(self.subtotal * tax_rate, 2)
        self.shipping_cost = round(shipping_cost, 2)
        self.total = round(self.subtotal + self.tax + self.shipping_cost, 2)

    def update_status(self, status: OrderStatus) -> None:
        self.status = status
        self.updated_at = _utcnow()


@dataclass
class Payment:
    id: str = field(default_factory=_new_id)
    order_id: str = ""
    amount: float = 0.0
    method: PaymentMethod = PaymentMethod.CREDIT_CARD
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    currency: str = "USD"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def update_status(self, status: PaymentStatus) -> None:
        self.status = status
        self.updated_at = _utcnow()
