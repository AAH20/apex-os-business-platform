"""Comprehensive tests for the e-commerce system."""

from __future__ import annotations

import pytest

from apex_os_bp.ecommerce import (
    Address,
    Cart,
    CartItem,
    Catalog,
    Checkout,
    Customer,
    Order,
    OrderItem,
    OrderManager,
    OrderStatus,
    Payment,
    PaymentGateway,
    PaymentMethod,
    PaymentStatus,
    Product,
    ShoppingCart,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_product():
    return Product(
        name="Test Widget",
        description="A test widget",
        price=29.99,
        sku="WIDGET-001",
        stock_quantity=100,
        category="widgets",
    )


@pytest.fixture
def sample_products():
    return [
        Product(name="Widget A", price=10.0, sku="WA-001", stock_quantity=50, category="widgets"),
        Product(name="Widget B", price=20.0, sku="WB-001", stock_quantity=30, category="widgets"),
        Product(name="Gadget X", price=99.99, sku="GX-001", stock_quantity=10, category="gadgets"),
    ]


@pytest.fixture
def sample_address():
    return Address(
        street="123 Main St",
        city="Springfield",
        state="IL",
        postal_code="62701",
        country="USA",
        phone="555-0100",
    )


@pytest.fixture
def sample_customer(sample_address):
    return Customer(
        name="John Doe",
        email="john@example.com",
        shipping_address=sample_address,
        billing_address=sample_address,
    )


@pytest.fixture
def catalog(sample_products):
    cat = Catalog()
    for p in sample_products:
        cat.add_product(p)
    return cat


@pytest.fixture
def cart(sample_product):
    c = Cart()
    c.add_item(sample_product, 2)
    return c


@pytest.fixture
def checkout():
    return Checkout(tax_rate=0.08, shipping_rate=5.99, free_shipping_threshold=100.0)


@pytest.fixture
def order_manager():
    return OrderManager()


@pytest.fixture
def payment_gateway():
    return PaymentGateway()


# ── Product Catalog Tests ──────────────────────────────────────────────


class TestCatalog:
    def test_add_and_get_product(self, catalog, sample_products):
        p = catalog.get_product(sample_products[0].id)
        assert p is not None
        assert p.name == "Widget A"

    def test_get_product_by_sku(self, catalog):
        p = catalog.get_product_by_sku("WA-001")
        assert p is not None
        assert p.name == "Widget A"

    def test_get_product_by_sku_not_found(self, catalog):
        assert catalog.get_product_by_sku("NONEXISTENT") is None

    def test_update_product(self, catalog, sample_products):
        updated = catalog.update_product(sample_products[0].id, price=15.0)
        assert updated.price == 15.0

    def test_update_product_not_found(self, catalog):
        with pytest.raises(ValueError):
            catalog.update_product("nonexistent-id", price=10.0)

    def test_remove_product(self, catalog, sample_products):
        assert catalog.remove_product(sample_products[0].id) is True
        assert catalog.get_product(sample_products[0].id) is None

    def test_remove_product_not_found(self, catalog):
        assert catalog.remove_product("nonexistent") is False

    def test_list_products(self, catalog):
        products = catalog.list_products()
        assert len(products) == 3

    def test_list_products_by_category(self, catalog):
        widgets = catalog.list_products(category="widgets")
        assert len(widgets) == 2

    def test_list_products_active_only(self, catalog, sample_products):
        catalog.update_product(sample_products[0].id, is_active=False)
        active = catalog.list_products(active_only=True)
        assert len(active) == 2
        all_products = catalog.list_products(active_only=False)
        assert len(all_products) == 3

    def test_search_products(self, catalog):
        results = catalog.search("widget")
        assert len(results) == 2

    def test_search_products_by_description(self, catalog):
        results = catalog.search("gadget")
        assert len(results) == 1

    def test_get_categories(self, catalog):
        cats = catalog.get_categories()
        assert "widgets" in cats
        assert "gadgets" in cats

    def test_count(self, catalog):
        assert catalog.count() == 3

    def test_clear(self, catalog):
        catalog.clear()
        assert catalog.count() == 0

    def test_add_invalid_product(self, catalog):
        bad_product = Product(name="", price=-1, sku="", stock_quantity=-5)
        with pytest.raises(ValueError):
            catalog.add_product(bad_product)


# ── Shopping Cart Tests ────────────────────────────────────────────────


class TestShoppingCart:
    def test_add_item(self, sample_product):
        c = Cart()
        c.add_item(sample_product, 3)
        assert c.item_count == 3
        assert c.total == pytest.approx(89.97)

    def test_add_item_increases_quantity(self, sample_product):
        c = Cart()
        c.add_item(sample_product, 2)
        c.add_item(sample_product, 3)
        assert c.item_count == 5
        assert len(c.items) == 1

    def test_add_item_insufficient_stock(self, sample_product):
        c = Cart()
        with pytest.raises(ValueError):
            c.add_item(sample_product, 200)

    def test_add_item_zero_quantity(self, sample_product):
        c = Cart()
        with pytest.raises(ValueError):
            c.add_item(sample_product, 0)

    def test_remove_item(self, sample_product):
        c = Cart()
        c.add_item(sample_product, 2)
        c.remove_item(sample_product.id)
        assert c.is_empty()

    def test_update_quantity(self, sample_product):
        c = Cart()
        c.add_item(sample_product, 2)
        c.update_quantity(sample_product.id, 5)
        assert c.item_count == 5

    def test_update_quantity_to_zero_removes(self, sample_product):
        c = Cart()
        c.add_item(sample_product, 2)
        c.update_quantity(sample_product.id, 0)
        assert c.is_empty()

    def test_update_quantity_insufficient_stock(self, sample_product):
        c = Cart()
        c.add_item(sample_product, 2)
        with pytest.raises(ValueError):
            c.update_quantity(sample_product.id, 200)

    def test_update_quantity_not_found(self, sample_product):
        c = Cart()
        with pytest.raises(ValueError):
            c.update_quantity("nonexistent", 1)

    def test_clear_cart(self, sample_product):
        c = Cart()
        c.add_item(sample_product, 2)
        c.clear()
        assert c.is_empty()
        assert c.total == 0.0

    def test_cart_total_multiple_items(self, sample_products):
        c = Cart()
        c.add_item(sample_products[0], 2)
        c.add_item(sample_products[1], 1)
        assert c.total == pytest.approx(40.0)

    def test_cart_is_empty(self):
        c = Cart()
        assert c.is_empty()

    def test_cart_not_empty(self, sample_product):
        c = Cart()
        c.add_item(sample_product, 1)
        assert not c.is_empty()

    def test_shopping_cart_wrapper(self, sample_product):
        sc = ShoppingCart(customer_id="cust-1")
        sc.add_item(sample_product, 2)
        assert sc.get_total() == pytest.approx(59.98)
        assert sc.get_item_count() == 2
        assert not sc.is_empty()

    def test_shopping_cart_remove(self, sample_product):
        sc = ShoppingCart()
        sc.add_item(sample_product, 2)
        sc.remove_item(sample_product.id)
        assert sc.is_empty()

    def test_shopping_cart_clear(self, sample_product):
        sc = ShoppingCart()
        sc.add_item(sample_product, 2)
        sc.clear()
        assert sc.is_empty()

    def test_shopping_cart_update_quantity(self, sample_product):
        sc = ShoppingCart()
        sc.add_item(sample_product, 2)
        sc.update_quantity(sample_product.id, 5)
        assert sc.get_item_count() == 5

    def test_shopping_cart_to_cart(self, sample_product):
        sc = ShoppingCart()
        sc.add_item(sample_product, 1)
        cart = sc.to_cart()
        assert isinstance(cart, Cart)
        assert cart.item_count == 1


# ── Checkout Tests ─────────────────────────────────────────────────────


class TestCheckout:
    def test_successful_checkout(self, cart, sample_customer, sample_address, checkout):
        result = checkout.process(
            cart=cart,
            customer=sample_customer,
            shipping_address=sample_address,
        )
        assert result.success is True
        assert result.order is not None
        assert result.order.status == OrderStatus.PENDING
        assert result.order.total > 0
        assert result.requires_payment is True

    def test_checkout_empty_cart(self, sample_customer, sample_address, checkout):
        empty_cart = Cart()
        result = checkout.process(
            cart=empty_cart,
            customer=sample_customer,
            shipping_address=sample_address,
        )
        assert result.success is False
        assert "empty" in result.error_message.lower()

    def test_checkout_invalid_customer(self, cart, sample_address, checkout):
        bad_customer = Customer(name="", email="")
        result = checkout.process(
            cart=cart,
            customer=bad_customer,
            shipping_address=sample_address,
        )
        assert result.success is False
        assert "customer" in result.error_message.lower()

    def test_checkout_invalid_shipping_address(self, cart, sample_customer, checkout):
        bad_address = Address(street="", city="", state="", postal_code="", country="")
        result = checkout.process(
            cart=cart,
            customer=sample_customer,
            shipping_address=bad_address,
        )
        assert result.success is False
        assert "shipping" in result.error_message.lower()

    def test_checkout_insufficient_stock(self, sample_customer, sample_address, checkout):
        product = Product(name="Limited", price=50.0, sku="LTD-001", stock_quantity=10)
        c = Cart()
        c.add_item(product, 5)
        # Reduce stock after adding to cart so checkout validation catches it
        product.stock_quantity = 2
        result = checkout.process(
            cart=c,
            customer=sample_customer,
            shipping_address=sample_address,
        )
        assert result.success is False
        assert "stock" in result.error_message.lower()

    def test_checkout_clears_cart(self, cart, sample_customer, sample_address, checkout):
        checkout.process(
            cart=cart,
            customer=sample_customer,
            shipping_address=sample_address,
        )
        assert cart.is_empty()

    def test_checkout_reserves_stock(self, sample_product, sample_customer, sample_address, checkout):
        initial_stock = sample_product.stock_quantity
        c = Cart()
        c.add_item(sample_product, 3)
        checkout.process(
            cart=c,
            customer=sample_customer,
            shipping_address=sample_address,
        )
        assert sample_product.stock_quantity == initial_stock - 3

    def test_checkout_with_tax(self, sample_product, sample_customer, sample_address):
        co = Checkout(tax_rate=0.10, shipping_rate=0.0)
        c = Cart()
        c.add_item(sample_product, 1)
        result = co.process(cart=c, customer=sample_customer, shipping_address=sample_address)
        assert result.success is True
        expected_subtotal = 29.99
        expected_tax = round(expected_subtotal * 0.10, 2)
        assert result.order.subtotal == pytest.approx(expected_subtotal)
        assert result.order.tax == pytest.approx(expected_tax)
        assert result.order.total == pytest.approx(expected_subtotal + expected_tax)

    def test_checkout_free_shipping(self, sample_product, sample_customer, sample_address):
        co = Checkout(tax_rate=0.0, shipping_rate=10.0, free_shipping_threshold=50.0)
        c = Cart()
        c.add_item(sample_product, 2)  # 59.98 > 50.0
        result = co.process(cart=c, customer=sample_customer, shipping_address=sample_address)
        assert result.success is True
        assert result.order.shipping_cost == 0.0

    def test_checkout_paid_shipping(self, sample_product, sample_customer, sample_address):
        co = Checkout(tax_rate=0.0, shipping_rate=10.0, free_shipping_threshold=100.0)
        c = Cart()
        c.add_item(sample_product, 1)  # 29.99 < 100.0
        result = co.process(cart=c, customer=sample_customer, shipping_address=sample_address)
        assert result.success is True
        assert result.order.shipping_cost == 10.0

    def test_checkout_cash_on_delivery_no_payment_required(
        self, sample_product, sample_customer, sample_address, checkout
    ):
        c = Cart()
        c.add_item(sample_product, 1)
        result = checkout.process(
            cart=c,
            customer=sample_customer,
            shipping_address=sample_address,
            payment_method=PaymentMethod.CASH_ON_DELIVERY,
        )
        assert result.success is True
        assert result.requires_payment is False

    def test_checkout_with_notes(self, sample_product, sample_customer, sample_address, checkout):
        c = Cart()
        c.add_item(sample_product, 1)
        result = checkout.process(
            cart=c,
            customer=sample_customer,
            shipping_address=sample_address,
            notes="Gift wrap please",
        )
        assert result.success is True
        assert "Gift wrap" in result.order.notes

    def test_checkout_billing_defaults_to_shipping(
        self, sample_product, sample_customer, sample_address, checkout
    ):
        c = Cart()
        c.add_item(sample_product, 1)
        result = checkout.process(
            cart=c,
            customer=sample_customer,
            shipping_address=sample_address,
            billing_address=None,
        )
        assert result.success is True
        assert result.order.billing_address is not None


# ── Order Management Tests ─────────────────────────────────────────────


class TestOrderManager:
    def test_create_and_get_order(self, order_manager):
        order = Order(customer_id="cust-1", total=50.0)
        order_manager.create_order(order)
        fetched = order_manager.get_order(order.id)
        assert fetched is not None
        assert fetched.id == order.id

    def test_get_order_not_found(self, order_manager):
        assert order_manager.get_order("nonexistent") is None

    def test_update_status(self, order_manager):
        order = Order(customer_id="cust-1")
        order_manager.create_order(order)
        updated = order_manager.update_status(order.id, OrderStatus.CONFIRMED)
        assert updated.status == OrderStatus.CONFIRMED

    def test_update_status_not_found(self, order_manager):
        with pytest.raises(ValueError):
            order_manager.update_status("nonexistent", OrderStatus.CONFIRMED)

    def test_cancel_order(self, order_manager):
        order = Order(customer_id="cust-1")
        order_manager.create_order(order)
        cancelled = order_manager.cancel_order(order.id)
        assert cancelled.status == OrderStatus.CANCELLED

    def test_cancel_shipped_order_fails(self, order_manager):
        order = Order(customer_id="cust-1")
        order_manager.create_order(order)
        order_manager.update_status(order.id, OrderStatus.SHIPPED)
        with pytest.raises(ValueError):
            order_manager.cancel_order(order.id)

    def test_cancel_delivered_order_fails(self, order_manager):
        order = Order(customer_id="cust-1")
        order_manager.create_order(order)
        order_manager.update_status(order.id, OrderStatus.DELIVERED)
        with pytest.raises(ValueError):
            order_manager.cancel_order(order.id)

    def test_get_orders_by_customer(self, order_manager):
        order_manager.create_order(Order(customer_id="cust-1"))
        order_manager.create_order(Order(customer_id="cust-1"))
        order_manager.create_order(Order(customer_id="cust-2"))
        orders = order_manager.get_orders_by_customer("cust-1")
        assert len(orders) == 2

    def test_get_orders_by_status(self, order_manager):
        o1 = Order(customer_id="cust-1")
        o2 = Order(customer_id="cust-2")
        order_manager.create_order(o1)
        order_manager.create_order(o2)
        order_manager.update_status(o1.id, OrderStatus.CONFIRMED)
        confirmed = order_manager.get_orders_by_status(OrderStatus.CONFIRMED)
        assert len(confirmed) == 1

    def test_list_orders(self, order_manager):
        order_manager.create_order(Order(customer_id="cust-1"))
        order_manager.create_order(Order(customer_id="cust-2"))
        assert len(order_manager.list_orders()) == 2

    def test_add_note(self, order_manager):
        order = Order(customer_id="cust-1")
        order_manager.create_order(order)
        order_manager.add_note(order.id, "First note")
        order_manager.add_note(order.id, "Second note")
        fetched = order_manager.get_order(order.id)
        assert "First note" in fetched.notes
        assert "Second note" in fetched.notes

    def test_add_note_not_found(self, order_manager):
        with pytest.raises(ValueError):
            order_manager.add_note("nonexistent", "note")

    def test_count(self, order_manager):
        order_manager.create_order(Order(customer_id="cust-1"))
        assert order_manager.count() == 1

    def test_clear(self, order_manager):
        order_manager.create_order(Order(customer_id="cust-1"))
        order_manager.clear()
        assert order_manager.count() == 0


# ── Payment Gateway Tests ──────────────────────────────────────────────


class TestPaymentGateway:
    def _make_order(self, total=100.0):
        return Order(customer_id="cust-1", total=total)

    def test_authorize_payment(self, payment_gateway):
        order = self._make_order()
        result = payment_gateway.authorize(order)
        assert result.success is True
        assert result.payment is not None
        assert result.payment.status == PaymentStatus.AUTHORIZED
        assert result.transaction_id is not None

    def test_authorize_zero_total_fails(self, payment_gateway):
        order = self._make_order(total=0.0)
        result = payment_gateway.authorize(order)
        assert result.success is False

    def test_capture_payment(self, payment_gateway):
        order = self._make_order()
        auth = payment_gateway.authorize(order)
        capture = payment_gateway.capture(auth.payment.id)
        assert capture.success is True
        assert capture.payment.status == PaymentStatus.CAPTURED

    def test_capture_not_found(self, payment_gateway):
        result = payment_gateway.capture("nonexistent")
        assert result.success is False

    def test_capture_wrong_status_fails(self, payment_gateway):
        order = self._make_order()
        auth = payment_gateway.authorize(order)
        payment_gateway.capture(auth.payment.id)
        # Second capture should fail
        result = payment_gateway.capture(auth.payment.id)
        assert result.success is False

    def test_refund_payment(self, payment_gateway):
        order = self._make_order()
        auth = payment_gateway.authorize(order)
        payment_gateway.capture(auth.payment.id)
        refund = payment_gateway.refund(auth.payment.id)
        assert refund.success is True
        assert refund.payment.status == PaymentStatus.REFUNDED

    def test_refund_not_captured_fails(self, payment_gateway):
        order = self._make_order()
        auth = payment_gateway.authorize(order)
        result = payment_gateway.refund(auth.payment.id)
        assert result.success is False

    def test_void_payment(self, payment_gateway):
        order = self._make_order()
        auth = payment_gateway.authorize(order)
        void = payment_gateway.void(auth.payment.id)
        assert void.success is True
        assert void.payment.status == PaymentStatus.CANCELLED

    def test_void_captured_fails(self, payment_gateway):
        order = self._make_order()
        auth = payment_gateway.authorize(order)
        payment_gateway.capture(auth.payment.id)
        result = payment_gateway.void(auth.payment.id)
        assert result.success is False

    def test_process_payment(self, payment_gateway):
        order = self._make_order()
        result = payment_gateway.process_payment(order)
        assert result.success is True
        assert result.payment.status == PaymentStatus.CAPTURED

    def test_get_payment(self, payment_gateway):
        order = self._make_order()
        auth = payment_gateway.authorize(order)
        payment = payment_gateway.get_payment(auth.payment.id)
        assert payment is not None
        assert payment.id == auth.payment.id

    def test_get_payment_not_found(self, payment_gateway):
        assert payment_gateway.get_payment("nonexistent") is None

    def test_get_payment_by_order(self, payment_gateway):
        order = self._make_order()
        auth = payment_gateway.authorize(order)
        payment = payment_gateway.get_payment_by_order(order.id)
        assert payment is not None
        assert payment.order_id == order.id

    def test_get_payment_by_order_not_found(self, payment_gateway):
        assert payment_gateway.get_payment_by_order("nonexistent") is None

    def test_list_payments(self, payment_gateway):
        order = self._make_order()
        payment_gateway.authorize(order)
        payment_gateway.authorize(order)
        assert len(payment_gateway.list_payments()) == 2

    def test_count(self, payment_gateway):
        order = self._make_order()
        payment_gateway.authorize(order)
        assert payment_gateway.count() == 1

    def test_clear(self, payment_gateway):
        order = self._make_order()
        payment_gateway.authorize(order)
        payment_gateway.clear()
        assert payment_gateway.count() == 0

    def test_payment_with_different_methods(self, payment_gateway):
        order = self._make_order()
        for method in PaymentMethod:
            result = payment_gateway.authorize(order, method=method)
            assert result.success is True
            assert result.payment.method == method

    def test_payment_with_currency(self, payment_gateway):
        order = self._make_order()
        result = payment_gateway.authorize(order, currency="EUR")
        assert result.success is True
        assert result.payment.currency == "EUR"


# ── Integration Tests ──────────────────────────────────────────────────


class TestEcommerceIntegration:
    def test_full_purchase_flow(
        self, catalog, sample_customer, sample_address, checkout, order_manager, payment_gateway
    ):
        # 1. Browse catalog
        products = catalog.list_products()
        assert len(products) > 0

        # 2. Add items to cart
        cart = Cart(customer_id=sample_customer.id)
        for p in products[:2]:
            cart.add_item(p, 1)

        # 3. Checkout
        result = checkout.process(
            cart=cart,
            customer=sample_customer,
            shipping_address=sample_address,
        )
        assert result.success is True
        order = result.order

        # 4. Create order in manager
        order_manager.create_order(order)

        # 5. Process payment
        pay_result = payment_gateway.process_payment(order)
        assert pay_result.success is True

        # 6. Update order status
        order_manager.update_status(order.id, OrderStatus.CONFIRMED)
        order_manager.update_status(order.id, OrderStatus.PROCESSING)
        order_manager.update_status(order.id, OrderStatus.SHIPPED)

        # 7. Verify final state
        final_order = order_manager.get_order(order.id)
        assert final_order.status == OrderStatus.SHIPPED
        assert final_order.total > 0

        payment = payment_gateway.get_payment_by_order(order.id)
        assert payment is not None
        assert payment.status == PaymentStatus.CAPTURED

    def test_order_cancellation_flow(
        self, catalog, sample_customer, sample_address, checkout, order_manager, payment_gateway
    ):
        products = catalog.list_products()
        cart = Cart(customer_id=sample_customer.id)
        cart.add_item(products[0], 1)

        result = checkout.process(
            cart=cart,
            customer=sample_customer,
            shipping_address=sample_address,
        )
        assert result.success is True
        order = result.order
        order_manager.create_order(order)

        # Cancel before shipping
        cancelled = order_manager.cancel_order(order.id)
        assert cancelled.status == OrderStatus.CANCELLED

    def test_multiple_orders_per_customer(
        self, catalog, sample_customer, sample_address, checkout, order_manager
    ):
        products = catalog.list_products()

        for i in range(3):
            cart = Cart(customer_id=sample_customer.id)
            cart.add_item(products[i], 1)
            result = checkout.process(
                cart=cart,
                customer=sample_customer,
                shipping_address=sample_address,
            )
            assert result.success is True
            order_manager.create_order(result.order)

        orders = order_manager.get_orders_by_customer(sample_customer.id)
        assert len(orders) == 3


# ── Model Tests ────────────────────────────────────────────────────────


class TestModels:
    def test_product_validate(self):
        p = Product(name="Test", price=10.0, sku="T-001", stock_quantity=5)
        assert p.validate() is True

    def test_product_validate_invalid(self):
        p = Product(name="", price=-1, sku="", stock_quantity=-1)
        assert p.validate() is False

    def test_product_is_in_stock(self):
        p = Product(name="Test", price=10.0, sku="T-001", stock_quantity=5)
        assert p.is_in_stock(3) is True
        assert p.is_in_stock(10) is False

    def test_product_reserve(self):
        p = Product(name="Test", price=10.0, sku="T-001", stock_quantity=5)
        assert p.reserve(3) is True
        assert p.stock_quantity == 2
        assert p.reserve(5) is False

    def test_product_release(self):
        p = Product(name="Test", price=10.0, sku="T-001", stock_quantity=5)
        p.release(3)
        assert p.stock_quantity == 8

    def test_address_validate(self):
        a = Address(street="123 Main", city="Springfield", state="IL", postal_code="62701", country="USA")
        assert a.validate() is True

    def test_address_validate_invalid(self):
        a = Address(street="", city="", state="", postal_code="", country="")
        assert a.validate() is False

    def test_customer_validate(self):
        c = Customer(name="John", email="john@example.com")
        assert c.validate() is True

    def test_customer_validate_invalid(self):
        c = Customer(name="", email="")
        assert c.validate() is False

    def test_cart_item_subtotal(self):
        p = Product(name="Test", price=10.0, sku="T-001", stock_quantity=5)
        item = CartItem(product=p, quantity=3)
        assert item.subtotal == pytest.approx(30.0)

    def test_cart_item_validate(self):
        p = Product(name="Test", price=10.0, sku="T-001", stock_quantity=5)
        item = CartItem(product=p, quantity=3)
        assert item.validate() is True

    def test_cart_item_validate_invalid_quantity(self):
        p = Product(name="Test", price=10.0, sku="T-001", stock_quantity=5)
        item = CartItem(product=p, quantity=0)
        assert item.validate() is False

    def test_order_item_subtotal(self):
        item = OrderItem(product_id="p1", product_name="Test", quantity=2, unit_price=15.0)
        assert item.subtotal == pytest.approx(30.0)

    def test_order_calculate_totals(self):
        items = [
            OrderItem(product_id="p1", product_name="A", quantity=2, unit_price=10.0),
            OrderItem(product_id="p2", product_name="B", quantity=1, unit_price=20.0),
        ]
        order = Order(items=items)
        order.calculate_totals(tax_rate=0.1, shipping_cost=5.0)
        assert order.subtotal == pytest.approx(40.0)
        assert order.tax == pytest.approx(4.0)
        assert order.shipping_cost == pytest.approx(5.0)
        assert order.total == pytest.approx(49.0)

    def test_order_update_status(self):
        order = Order()
        order.update_status(OrderStatus.CONFIRMED)
        assert order.status == OrderStatus.CONFIRMED

    def test_payment_update_status(self):
        payment = Payment()
        payment.update_status(PaymentStatus.CAPTURED)
        assert payment.status == PaymentStatus.CAPTURED
