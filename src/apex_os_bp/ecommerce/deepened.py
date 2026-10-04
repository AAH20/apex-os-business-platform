"""Deepened e-commerce module: cart, orders, payments, inventory, catalog."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable


# ── Shopping Cart ──────────────────────────────────────────────────────────

@dataclass
class CartItem:
    product_id: str
    name: str
    quantity: int
    unit_price: float

    @property
    def line_total(self) -> float:
        return self.quantity * self.unit_price


class ShoppingCart:
    """Persistent shopping cart backed by JSON file storage."""

    def __init__(self, cart_id: str, storage_path: str = "data/carts"):
        self.cart_id = cart_id
        self.storage_path = Path(storage_path)
        self.items: list[CartItem] = []
        self._load()

    def _file(self) -> Path:
        return self.storage_path / f"{self.cart_id}.json"

    def _load(self) -> None:
        f = self._file()
        if f.exists():
            data = json.loads(f.read_text())
            self.items = [CartItem(**i) for i in data.get("items", [])]

    def _save(self) -> None:
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._file().write_text(json.dumps({
            "cart_id": self.cart_id,
            "items": [asdict(i) for i in self.items],
            "updated_at": datetime.utcnow().isoformat(),
        }, indent=2))

    def add_item(self, product_id: str, name: str, quantity: int, unit_price: float) -> None:
        for item in self.items:
            if item.product_id == product_id:
                item.quantity += quantity
                self._save()
                return
        self.items.append(CartItem(product_id, name, quantity, unit_price))
        self._save()

    def remove_item(self, product_id: str) -> None:
        self.items = [i for i in self.items if i.product_id != product_id]
        self._save()

    def update_quantity(self, product_id: str, quantity: int) -> None:
        for item in self.items:
            if item.product_id == product_id:
                item.quantity = max(0, quantity)
                if item.quantity == 0:
                    self.remove_item(product_id)
                else:
                    self._save()
                return

    @property
    def total(self) -> float:
        return sum(i.line_total for i in self.items)

    @property
    def item_count(self) -> int:
        return sum(i.quantity for i in self.items)

    def clear(self) -> None:
        self.items = []
        self._save()


# ── Order Management with State Machine ─────────────────────────────────────

class OrderState(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderStateMachine:
    """Finite state machine for order lifecycle."""

    TRANSITIONS: dict[OrderState, set[OrderState]] = {
        OrderState.PENDING: {OrderState.CONFIRMED, OrderState.CANCELLED},
        OrderState.CONFIRMED: {OrderState.PAID, OrderState.CANCELLED},
        OrderState.PAID: {OrderState.SHIPPED, OrderState.REFUNDED},
        OrderState.SHIPPED: {OrderState.DELIVERED, OrderState.REFUNDED},
        OrderState.DELIVERED: {OrderState.REFUNDED},
        OrderState.CANCELLED: set(),
        OrderState.REFUNDED: set(),
    }

    def __init__(self, state: OrderState = OrderState.PENDING):
        self.state = state
        self.history: list[tuple[OrderState, OrderState, str]] = []

    def can_transition(self, new_state: OrderState) -> bool:
        return new_state in self.TRANSITIONS.get(self.state, set())

    def transition(self, new_state: OrderState, reason: str = "") -> bool:
        if not self.can_transition(new_state):
            raise ValueError(
                f"Invalid transition: {self.state.value} → {new_state.value}"
            )
        old = self.state
        self.state = new_state
        self.history.append((old, new_state, reason))
        return True


@dataclass
class Order:
    order_id: str
    customer_id: str
    items: list[CartItem]
    total: float
    state_machine: OrderStateMachine = field(default_factory=OrderStateMachine)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def status(self) -> str:
        return self.state_machine.state.value

    def transition(self, new_state: OrderState, reason: str = "") -> bool:
        return self.state_machine.transition(new_state, reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "items": [asdict(i) for i in self.items],
            "total": self.total,
            "status": self.status,
            "created_at": self.created_at,
        }


class OrderManager:
    """Manages order creation, persistence, and lifecycle."""

    def __init__(self, storage_path: str = "data/orders"):
        self.storage_path = Path(storage_path)
        self.orders: dict[str, Order] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self.storage_path.exists():
            return
        for f in self.storage_path.glob("*.json"):
            data = json.loads(f.read_text())
            sm = OrderStateMachine(OrderState[data["status"].upper()])
            order = Order(
                order_id=data["order_id"],
                customer_id=data["customer_id"],
                items=[CartItem(**i) for i in data["items"]],
                total=data["total"],
                state_machine=sm,
                created_at=data["created_at"],
            )
            self.orders[order.order_id] = order

    def _save(self, order: Order) -> None:
        self.storage_path.mkdir(parents=True, exist_ok=True)
        f = self.storage_path / f"{order.order_id}.json"
        f.write_text(json.dumps(order.to_dict(), indent=2))

    def create_order(self, customer_id: str, cart: ShoppingCart) -> Order:
        order = Order(
            order_id=str(uuid.uuid4())[:8],
            customer_id=customer_id,
            items=list(cart.items),
            total=cart.total,
        )
        self.orders[order.order_id] = order
        self._save(order)
        return order

    def get_order(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

    def transition_order(self, order_id: str, new_state: OrderState, reason: str = "") -> bool:
        order = self.orders.get(order_id)
        if not order:
            return False
        result = order.transition(new_state, reason)
        if result:
            self._save(order)
        return result


# ── Payment Processing with Multiple Gateways ──────────────────────────────

class PaymentResult:
    def __init__(self, success: bool, transaction_id: str, message: str = ""):
        self.success = success
        self.transaction_id = transaction_id
        self.message = message


class PaymentGateway:
    """Base payment gateway interface."""

    name: str = "base"

    def charge(self, amount: float, currency: str, card_token: str) -> PaymentResult:
        raise NotImplementedError

    def refund(self, transaction_id: str, amount: float) -> PaymentResult:
        raise NotImplementedError


class StripeGateway(PaymentGateway):
    name = "stripe"

    def charge(self, amount: float, currency: str, card_token: str) -> PaymentResult:
        tx_id = f"stripe_{uuid.uuid4().hex[:12]}"
        return PaymentResult(True, tx_id, f"Charged {amount} {currency}")

    def refund(self, transaction_id: str, amount: float) -> PaymentResult:
        return PaymentResult(True, f"ref_{transaction_id}", f"Refunded {amount}")


class PayPalGateway(PaymentGateway):
    name = "paypal"

    def charge(self, amount: float, currency: str, card_token: str) -> PaymentResult:
        tx_id = f"paypal_{uuid.uuid4().hex[:12]}"
        return PaymentResult(True, tx_id, f"Charged {amount} {currency}")

    def refund(self, transaction_id: str, amount: float) -> PaymentResult:
        return PaymentResult(True, f"ref_{transaction_id}", f"Refunded {amount}")


class BankTransferGateway(PaymentGateway):
    name = "bank_transfer"

    def charge(self, amount: float, currency: str, card_token: str) -> PaymentResult:
        tx_id = f"bank_{uuid.uuid4().hex[:12]}"
        return PaymentResult(True, tx_id, f"Bank transfer initiated for {amount} {currency}")

    def refund(self, transaction_id: str, amount: float) -> PaymentResult:
        return PaymentResult(True, f"ref_{transaction_id}", f"Refund of {amount} initiated")


class PaymentProcessor:
    """Routes payments to configured gateways."""

    def __init__(self):
        self.gateways: dict[str, PaymentGateway] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for gw in (StripeGateway(), PayPalGateway(), BankTransferGateway()):
            self.gateways[gw.name] = gw

    def register_gateway(self, gateway: PaymentGateway) -> None:
        self.gateways[gateway.name] = gateway

    def process_payment(
        self, gateway_name: str, amount: float, currency: str, card_token: str
    ) -> PaymentResult:
        gw = self.gateways.get(gateway_name)
        if not gw:
            return PaymentResult(False, "", f"Unknown gateway: {gateway_name}")
        return gw.charge(amount, currency, card_token)

    def process_refund(
        self, gateway_name: str, transaction_id: str, amount: float
    ) -> PaymentResult:
        gw = self.gateways.get(gateway_name)
        if not gw:
            return PaymentResult(False, "", f"Unknown gateway: {gateway_name}")
        return gw.refund(transaction_id, amount)


# ── Inventory Management with Stock Alerts ─────────────────────────────────

@dataclass
class StockAlert:
    product_id: str
    current_stock: int
    threshold: int
    triggered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class InventoryManager:
    """Tracks stock levels and fires alerts when thresholds are breached."""

    def __init__(self, low_stock_threshold: int = 10):
        self.stock: dict[str, int] = {}
        self.reserved: dict[str, int] = {}
        self.low_stock_threshold = low_stock_threshold
        self.alerts: list[StockAlert] = []
        self.alert_handlers: list[Callable[[StockAlert], None]] = []

    def register_alert_handler(self, handler: Callable[[StockAlert], None]) -> None:
        self.alert_handlers.append(handler)

    def _check_alert(self, product_id: str) -> None:
        available = self.stock.get(product_id, 0) - self.reserved.get(product_id, 0)
        if available <= self.low_stock_threshold:
            alert = StockAlert(product_id, available, self.low_stock_threshold)
            self.alerts.append(alert)
            for handler in self.alert_handlers:
                handler(alert)

    def set_stock(self, product_id: str, quantity: int) -> None:
        self.stock[product_id] = quantity
        self._check_alert(product_id)

    def reserve(self, product_id: str, quantity: int) -> bool:
        available = self.stock.get(product_id, 0) - self.reserved.get(product_id, 0)
        if available < quantity:
            return False
        self.reserved[product_id] = self.reserved.get(product_id, 0) + quantity
        self._check_alert(product_id)
        return True

    def release_reservation(self, product_id: str, quantity: int) -> None:
        current = self.reserved.get(product_id, 0)
        self.reserved[product_id] = max(0, current - quantity)

    def confirm_reservation(self, product_id: str, quantity: int) -> None:
        self.release_reservation(product_id, quantity)
        self.stock[product_id] = self.stock.get(product_id, 0) - quantity
        self._check_alert(product_id)

    def restock(self, product_id: str, quantity: int) -> None:
        self.stock[product_id] = self.stock.get(product_id, 0) + quantity

    @property
    def available(self) -> dict[str, int]:
        return {
            pid: self.stock.get(pid, 0) - self.reserved.get(pid, 0)
            for pid in self.stock
        }


# ── Product Catalog with Faceted Search ────────────────────────────────────

@dataclass
class Product:
    product_id: str
    name: str
    description: str
    price: float
    category: str
    brand: str
    tags: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    in_stock: bool = True


class FacetedCatalog:
    """Product catalog supporting multi-facet filtering and search."""

    def __init__(self):
        self.products: dict[str, Product] = {}

    def add_product(self, product: Product) -> None:
        self.products[product.product_id] = product

    def remove_product(self, product_id: str) -> None:
        self.products.pop(product_id, None)

    def get_product(self, product_id: str) -> Product | None:
        return self.products.get(product_id)

    def search(
        self,
        query: str = "",
        category: str | None = None,
        brand: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        tags: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
        in_stock_only: bool = False,
    ) -> list[Product]:
        """Faceted search across multiple dimensions."""
        results: list[Product] = []
        for p in self.products.values():
            if query and query.lower() not in p.name.lower() and query.lower() not in p.description.lower():
                continue
            if category and p.category != category:
                continue
            if brand and p.brand != brand:
                continue
            if min_price is not None and p.price < min_price:
                continue
            if max_price is not None and p.price > max_price:
                continue
            if tags and not all(t in p.tags for t in tags):
                continue
            if attributes:
                match = all(p.attributes.get(k) == v for k, v in attributes.items())
                if not match:
                    continue
            if in_stock_only and not p.in_stock:
                continue
            results.append(p)
        return results

    def get_facets(self) -> dict[str, list[str]]:
        """Return available facet values for UI filtering."""
        categories = list({p.category for p in self.products.values()})
        brands = list({p.brand for p in self.products.values()})
        all_tags: set[str] = set()
        for p in self.products.values():
            all_tags.update(p.tags)
        return {
            "categories": sorted(categories),
            "brands": sorted(brands),
            "tags": sorted(all_tags),
        }

    def price_range(self) -> tuple[float, float]:
        prices = [p.price for p in self.products.values()]
        return (min(prices), max(prices)) if prices else (0.0, 0.0)
