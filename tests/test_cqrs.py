"""Comprehensive tests for the CQRS system."""

import pytest
from decimal import Decimal
from uuid import UUID, uuid4

from apex_os_bp.cqrs import (
    AggregateNotFoundError,
    CancelOrderCommand,
    CommandValidationError,
    ConcurrencyError,
    CreateCustomerCommand,
    CreateOrderCommand,
    CreateProductCommand,
    CustomerAggregate,
    CustomerCreatedEvent,
    CustomerReadModel,
    CustomerUpdatedEvent,
    GetCustomerQuery,
    GetOrderQuery,
    GetProductQuery,
    HandlerNotFoundError,
    InMemoryEventStore,
    ListCustomersQuery,
    ListOrdersQuery,
    ListProductsQuery,
    OrderAggregate,
    OrderCancelledEvent,
    OrderCreatedEvent,
    OrderReadModel,
    OrderUpdatedEvent,
    ProductAggregate,
    ProductCreatedEvent,
    ProductReadModel,
    ProductUpdatedEvent,
    QueryValidationError,
    Repository,
    UpdateCustomerCommand,
    UpdateOrderCommand,
    UpdateProductCommand,
    CQRSBus,
    CreateOrderHandler,
    UpdateOrderHandler,
    CancelOrderHandler,
    CreateCustomerHandler,
    UpdateCustomerHandler,
    CreateProductHandler,
    UpdateProductHandler,
    GetOrderHandler,
    ListOrdersHandler,
    GetCustomerHandler,
    ListCustomersHandler,
    GetProductHandler,
    ListProductsHandler,
    OrderCreatedHandler,
    OrderUpdatedHandler,
    OrderCancelledHandler,
    CustomerCreatedHandler,
    CustomerUpdatedHandler,
    ProductCreatedHandler,
    ProductUpdatedHandler,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def event_store():
    return InMemoryEventStore()


@pytest.fixture
def order_read_model():
    return OrderReadModel()


@pytest.fixture
def customer_read_model():
    return CustomerReadModel()


@pytest.fixture
def product_read_model():
    return ProductReadModel()


@pytest.fixture
def bus():
    return CQRSBus()


@pytest.fixture
def sample_customer_id():
    return uuid4()


@pytest.fixture
def sample_order_id():
    return uuid4()


@pytest.fixture
def sample_product_id():
    return uuid4()


# ============================================================
# Command Handler Tests
# ============================================================


class TestCreateOrderHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        handler = CreateOrderHandler()
        customer_id = uuid4()
        items = [{"product_id": str(uuid4()), "quantity": 2, "price": "10.00"}]
        command = CreateOrderCommand(
            customer_id=customer_id,
            items=items,
            currency="USD",
            notes="Test order",
        )
        events = await handler.handle(command)
        assert len(events) == 1
        assert isinstance(events[0], OrderCreatedEvent)
        assert events[0].metadata["customer_id"] == str(customer_id)
        assert events[0].metadata["items"] == items
        assert events[0].metadata["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_handle_missing_customer_id(self):
        handler = CreateOrderHandler()
        command = CreateOrderCommand(
            customer_id=UUID(int=0),
            items=[{"product_id": str(uuid4()), "quantity": 1}],
        )
        with pytest.raises(CommandValidationError, match="customer_id is required"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_handle_missing_items(self):
        handler = CreateOrderHandler()
        command = CreateOrderCommand(
            customer_id=uuid4(),
            items=[],
        )
        with pytest.raises(CommandValidationError, match="items are required"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_handle_missing_currency(self):
        handler = CreateOrderHandler()
        command = CreateOrderCommand(
            customer_id=uuid4(),
            items=[{"product_id": str(uuid4()), "quantity": 1}],
            currency="",
        )
        with pytest.raises(CommandValidationError, match="currency is required"):
            await handler.handle(command)


class TestUpdateOrderHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        handler = UpdateOrderHandler()
        order_id = uuid4()
        command = UpdateOrderCommand(
            order_id=order_id,
            items=[{"product_id": str(uuid4()), "quantity": 3}],
            notes="Updated",
        )
        events = await handler.handle(command)
        assert len(events) == 1
        assert isinstance(events[0], OrderUpdatedEvent)
        assert events[0].aggregate_id == order_id

    @pytest.mark.asyncio
    async def test_handle_missing_order_id(self):
        handler = UpdateOrderHandler()
        command = UpdateOrderCommand(order_id=UUID(int=0))
        with pytest.raises(CommandValidationError, match="order_id is required"):
            await handler.handle(command)


class TestCancelOrderHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        handler = CancelOrderHandler()
        order_id = uuid4()
        command = CancelOrderCommand(order_id=order_id, reason="Customer request")
        events = await handler.handle(command)
        assert len(events) == 1
        assert isinstance(events[0], OrderCancelledEvent)
        assert events[0].metadata["reason"] == "Customer request"

    @pytest.mark.asyncio
    async def test_handle_missing_order_id(self):
        handler = CancelOrderHandler()
        command = CancelOrderCommand(order_id=UUID(int=0), reason="test")
        with pytest.raises(CommandValidationError, match="order_id is required"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_handle_missing_reason(self):
        handler = CancelOrderHandler()
        command = CancelOrderCommand(order_id=uuid4(), reason="")
        with pytest.raises(CommandValidationError, match="reason is required"):
            await handler.handle(command)


class TestCreateCustomerHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        handler = CreateCustomerHandler()
        command = CreateCustomerCommand(
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            address="123 Main St",
        )
        events = await handler.handle(command)
        assert len(events) == 1
        assert isinstance(events[0], CustomerCreatedEvent)
        assert events[0].metadata["name"] == "John Doe"
        assert events[0].metadata["email"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_handle_missing_name(self):
        handler = CreateCustomerHandler()
        command = CreateCustomerCommand(name="", email="john@example.com")
        with pytest.raises(CommandValidationError, match="name is required"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_handle_missing_email(self):
        handler = CreateCustomerHandler()
        command = CreateCustomerCommand(name="John", email="")
        with pytest.raises(CommandValidationError, match="email is required"):
            await handler.handle(command)


class TestUpdateCustomerHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        handler = UpdateCustomerHandler()
        customer_id = uuid4()
        command = UpdateCustomerCommand(
            customer_id=customer_id,
            name="Jane Doe",
            email="jane@example.com",
        )
        events = await handler.handle(command)
        assert len(events) == 1
        assert isinstance(events[0], CustomerUpdatedEvent)
        assert events[0].aggregate_id == customer_id

    @pytest.mark.asyncio
    async def test_handle_missing_customer_id(self):
        handler = UpdateCustomerHandler()
        command = UpdateCustomerCommand(customer_id=UUID(int=0))
        with pytest.raises(CommandValidationError, match="customer_id is required"):
            await handler.handle(command)


class TestCreateProductHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        handler = CreateProductHandler()
        command = CreateProductCommand(
            name="Widget",
            description="A useful widget",
            price=Decimal("19.99"),
            sku="WIDGET-001",
            category="Tools",
        )
        events = await handler.handle(command)
        assert len(events) == 1
        assert isinstance(events[0], ProductCreatedEvent)
        assert events[0].metadata["name"] == "Widget"
        assert events[0].metadata["sku"] == "WIDGET-001"

    @pytest.mark.asyncio
    async def test_handle_missing_name(self):
        handler = CreateProductHandler()
        command = CreateProductCommand(
            name="",
            description="test",
            price=Decimal("10.00"),
            sku="SKU-001",
        )
        with pytest.raises(CommandValidationError, match="name is required"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_handle_missing_sku(self):
        handler = CreateProductHandler()
        command = CreateProductCommand(
            name="Widget",
            description="test",
            price=Decimal("10.00"),
            sku="",
        )
        with pytest.raises(CommandValidationError, match="sku is required"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_handle_negative_price(self):
        handler = CreateProductHandler()
        command = CreateProductCommand(
            name="Widget",
            description="test",
            price=Decimal("-5.00"),
            sku="SKU-001",
        )
        with pytest.raises(CommandValidationError, match="price must be non-negative"):
            await handler.handle(command)


class TestUpdateProductHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        handler = UpdateProductHandler()
        product_id = uuid4()
        command = UpdateProductCommand(
            product_id=product_id,
            name="Updated Widget",
            price=Decimal("29.99"),
        )
        events = await handler.handle(command)
        assert len(events) == 1
        assert isinstance(events[0], ProductUpdatedEvent)
        assert events[0].aggregate_id == product_id

    @pytest.mark.asyncio
    async def test_handle_missing_product_id(self):
        handler = UpdateProductHandler()
        command = UpdateProductCommand(product_id=UUID(int=0))
        with pytest.raises(CommandValidationError, match="product_id is required"):
            await handler.handle(command)


# ============================================================
# Query Handler Tests
# ============================================================


class TestGetOrderHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        order_id = uuid4()
        read_model = {
            order_id: {
                "order_id": str(order_id),
                "customer_id": str(uuid4()),
                "status": "pending",
            }
        }
        handler = GetOrderHandler(read_model)
        query = GetOrderQuery(order_id=order_id)
        result = await handler.handle(query)
        assert result is not None
        assert result["order_id"] == str(order_id)

    @pytest.mark.asyncio
    async def test_handle_not_found(self):
        handler = GetOrderHandler({})
        query = GetOrderQuery(order_id=uuid4())
        result = await handler.handle(query)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_missing_order_id(self):
        handler = GetOrderHandler({})
        query = GetOrderQuery(order_id=UUID(int=0))
        with pytest.raises(QueryValidationError, match="order_id is required"):
            await handler.handle(query)


class TestListOrdersHandler:
    @pytest.mark.asyncio
    async def test_handle_empty(self):
        handler = ListOrdersHandler({})
        query = ListOrdersQuery()
        result = await handler.handle(query)
        assert result == []

    @pytest.mark.asyncio
    async def test_handle_with_data(self):
        orders = {}
        for i in range(5):
            oid = uuid4()
            orders[oid] = {
                "order_id": str(oid),
                "customer_id": str(uuid4()),
                "status": "pending",
            }
        handler = ListOrdersHandler(orders)
        query = ListOrdersQuery(limit=3)
        result = await handler.handle(query)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handle_filter_by_customer(self):
        customer_id = uuid4()
        orders = {}
        for i in range(3):
            oid = uuid4()
            orders[oid] = {
                "order_id": str(oid),
                "customer_id": str(customer_id),
                "status": "pending",
            }
        other_id = uuid4()
        orders[other_id] = {
            "order_id": str(other_id),
            "customer_id": str(uuid4()),
            "status": "pending",
        }
        handler = ListOrdersHandler(orders)
        query = ListOrdersQuery(customer_id=customer_id)
        result = await handler.handle(query)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handle_filter_by_status(self):
        orders = {}
        for i in range(3):
            oid = uuid4()
            orders[oid] = {
                "order_id": str(oid),
                "customer_id": str(uuid4()),
                "status": "pending",
            }
        cancelled_id = uuid4()
        orders[cancelled_id] = {
            "order_id": str(cancelled_id),
            "customer_id": str(uuid4()),
            "status": "cancelled",
        }
        handler = ListOrdersHandler(orders)
        query = ListOrdersQuery(status="cancelled")
        result = await handler.handle(query)
        assert len(result) == 1
        assert result[0]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_handle_pagination(self):
        orders = {}
        for i in range(10):
            oid = uuid4()
            orders[oid] = {
                "order_id": str(oid),
                "customer_id": str(uuid4()),
                "status": "pending",
            }
        handler = ListOrdersHandler(orders)
        query = ListOrdersQuery(limit=5, offset=5)
        result = await handler.handle(query)
        assert len(result) == 5


class TestGetCustomerHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        customer_id = uuid4()
        read_model = {
            customer_id: {
                "customer_id": str(customer_id),
                "name": "John",
                "email": "john@example.com",
            }
        }
        handler = GetCustomerHandler(read_model)
        query = GetCustomerQuery(customer_id=customer_id)
        result = await handler.handle(query)
        assert result is not None
        assert result["name"] == "John"

    @pytest.mark.asyncio
    async def test_handle_not_found(self):
        handler = GetCustomerHandler({})
        query = GetCustomerQuery(customer_id=uuid4())
        result = await handler.handle(query)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_missing_customer_id(self):
        handler = GetCustomerHandler({})
        query = GetCustomerQuery(customer_id=UUID(int=0))
        with pytest.raises(QueryValidationError, match="customer_id is required"):
            await handler.handle(query)


class TestListCustomersHandler:
    @pytest.mark.asyncio
    async def test_handle_empty(self):
        handler = ListCustomersHandler({})
        query = ListCustomersQuery()
        result = await handler.handle(query)
        assert result == []

    @pytest.mark.asyncio
    async def test_handle_with_data(self):
        customers = {}
        for i in range(5):
            cid = uuid4()
            customers[cid] = {
                "customer_id": str(cid),
                "name": f"Customer {i}",
                "email": f"customer{i}@example.com",
            }
        handler = ListCustomersHandler(customers)
        query = ListCustomersQuery(limit=3)
        result = await handler.handle(query)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handle_search(self):
        customers = {}
        for name in ["Alice Smith", "Bob Jones", "Charlie Brown"]:
            cid = uuid4()
            customers[cid] = {
                "customer_id": str(cid),
                "name": name,
                "email": f"{name.lower().replace(' ', '.')}@example.com",
            }
        handler = ListCustomersHandler(customers)
        query = ListCustomersQuery(search="alice")
        result = await handler.handle(query)
        assert len(result) == 1
        assert result[0]["name"] == "Alice Smith"

    @pytest.mark.asyncio
    async def test_handle_pagination(self):
        customers = {}
        for i in range(10):
            cid = uuid4()
            customers[cid] = {
                "customer_id": str(cid),
                "name": f"Customer {i}",
                "email": f"customer{i}@example.com",
            }
        handler = ListCustomersHandler(customers)
        query = ListCustomersQuery(limit=5, offset=5)
        result = await handler.handle(query)
        assert len(result) == 5


class TestGetProductHandler:
    @pytest.mark.asyncio
    async def test_handle_success(self):
        product_id = uuid4()
        read_model = {
            product_id: {
                "product_id": str(product_id),
                "name": "Widget",
                "sku": "WIDGET-001",
            }
        }
        handler = GetProductHandler(read_model)
        query = GetProductQuery(product_id=product_id)
        result = await handler.handle(query)
        assert result is not None
        assert result["name"] == "Widget"

    @pytest.mark.asyncio
    async def test_handle_not_found(self):
        handler = GetProductHandler({})
        query = GetProductQuery(product_id=uuid4())
        result = await handler.handle(query)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_missing_product_id(self):
        handler = GetProductHandler({})
        query = GetProductQuery(product_id=UUID(int=0))
        with pytest.raises(QueryValidationError, match="product_id is required"):
            await handler.handle(query)


class TestListProductsHandler:
    @pytest.mark.asyncio
    async def test_handle_empty(self):
        handler = ListProductsHandler({})
        query = ListProductsQuery()
        result = await handler.handle(query)
        assert result == []

    @pytest.mark.asyncio
    async def test_handle_with_data(self):
        products = {}
        for i in range(5):
            pid = uuid4()
            products[pid] = {
                "product_id": str(pid),
                "name": f"Product {i}",
                "category": "Tools" if i < 3 else "Electronics",
            }
        handler = ListProductsHandler(products)
        query = ListProductsQuery(limit=3)
        result = await handler.handle(query)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handle_filter_by_category(self):
        products = {}
        for i in range(3):
            pid = uuid4()
            products[pid] = {
                "product_id": str(pid),
                "name": f"Tool {i}",
                "category": "Tools",
            }
        for i in range(2):
            pid = uuid4()
            products[pid] = {
                "product_id": str(pid),
                "name": f"Gadget {i}",
                "category": "Electronics",
            }
        handler = ListProductsHandler(products)
        query = ListProductsQuery(category="Electronics")
        result = await handler.handle(query)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_handle_search(self):
        products = {}
        for name in ["Widget A", "Widget B", "Gadget C"]:
            pid = uuid4()
            products[pid] = {
                "product_id": str(pid),
                "name": name,
                "description": f"Description for {name}",
            }
        handler = ListProductsHandler(products)
        query = ListProductsQuery(search="widget")
        result = await handler.handle(query)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_handle_pagination(self):
        products = {}
        for i in range(10):
            pid = uuid4()
            products[pid] = {
                "product_id": str(pid),
                "name": f"Product {i}",
                "category": "General",
            }
        handler = ListProductsHandler(products)
        query = ListProductsQuery(limit=5, offset=5)
        result = await handler.handle(query)
        assert len(result) == 5


# ============================================================
# Read Model Tests
# ============================================================


class TestOrderReadModel:
    def test_project_order_created(self):
        model = OrderReadModel()
        event = OrderCreatedEvent(
            aggregate_id=uuid4(),
            metadata={
                "customer_id": str(uuid4()),
                "items": [{"product_id": "123", "quantity": 2}],
                "currency": "USD",
                "notes": "Test",
            },
        )
        model.project(event)
        assert len(model._orders) == 1
        order = list(model._orders.values())[0]
        assert order["status"] == "pending"
        assert order["currency"] == "USD"

    def test_project_order_updated(self):
        model = OrderReadModel()
        order_id = uuid4()
        created_event = OrderCreatedEvent(
            aggregate_id=order_id,
            metadata={
                "customer_id": str(uuid4()),
                "items": [{"product_id": "123", "quantity": 1}],
                "currency": "USD",
            },
        )
        model.project(created_event)
        updated_event = OrderUpdatedEvent(
            aggregate_id=order_id,
            metadata={"items": [{"product_id": "456", "quantity": 3}]},
        )
        model.project(updated_event)
        order = model.get(order_id)
        assert order["items"] == [{"product_id": "456", "quantity": 3}]

    def test_project_order_cancelled(self):
        model = OrderReadModel()
        order_id = uuid4()
        created_event = OrderCreatedEvent(
            aggregate_id=order_id,
            metadata={
                "customer_id": str(uuid4()),
                "items": [],
                "currency": "USD",
            },
        )
        model.project(created_event)
        cancel_event = OrderCancelledEvent(
            aggregate_id=order_id,
            metadata={"reason": "No longer needed"},
        )
        model.project(cancel_event)
        order = model.get(order_id)
        assert order["status"] == "cancelled"

    def test_get_not_found(self):
        model = OrderReadModel()
        assert model.get(uuid4()) is None

    def test_list_empty(self):
        model = OrderReadModel()
        assert model.list() == []

    def test_list_with_filter(self):
        model = OrderReadModel()
        customer_id = uuid4()
        for i in range(3):
            model.project(OrderCreatedEvent(
                aggregate_id=uuid4(),
                metadata={
                    "customer_id": str(customer_id),
                    "items": [],
                    "currency": "USD",
                },
            ))
        model.project(OrderCreatedEvent(
            aggregate_id=uuid4(),
            metadata={
                "customer_id": str(uuid4()),
                "items": [],
                "currency": "USD",
            },
        ))
        results = model.list(customer_id=customer_id)
        assert len(results) == 3


class TestCustomerReadModel:
    def test_project_customer_created(self):
        model = CustomerReadModel()
        event = CustomerCreatedEvent(
            aggregate_id=uuid4(),
            metadata={
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
            },
        )
        model.project(event)
        assert len(model._customers) == 1
        customer = list(model._customers.values())[0]
        assert customer["name"] == "John Doe"
        assert customer["email"] == "john@example.com"

    def test_project_customer_updated(self):
        model = CustomerReadModel()
        customer_id = uuid4()
        model.project(CustomerCreatedEvent(
            aggregate_id=customer_id,
            metadata={"name": "John", "email": "john@example.com"},
        ))
        model.project(CustomerUpdatedEvent(
            aggregate_id=customer_id,
            metadata={"name": "John Updated"},
        ))
        customer = model.get(customer_id)
        assert customer["name"] == "John Updated"
        assert customer["email"] == "john@example.com"

    def test_get_not_found(self):
        model = CustomerReadModel()
        assert model.get(uuid4()) is None

    def test_list_search(self):
        model = CustomerReadModel()
        for name in ["Alice", "Bob", "Charlie"]:
            model.project(CustomerCreatedEvent(
                aggregate_id=uuid4(),
                metadata={"name": name, "email": f"{name.lower()}@example.com"},
            ))
        results = model.list(search="ali")
        assert len(results) == 1
        assert results[0]["name"] == "Alice"


class TestProductReadModel:
    def test_project_product_created(self):
        model = ProductReadModel()
        event = ProductCreatedEvent(
            aggregate_id=uuid4(),
            metadata={
                "name": "Widget",
                "description": "A widget",
                "price": "19.99",
                "sku": "WIDGET-001",
                "category": "Tools",
            },
        )
        model.project(event)
        assert len(model._products) == 1
        product = list(model._products.values())[0]
        assert product["name"] == "Widget"
        assert product["sku"] == "WIDGET-001"

    def test_project_product_updated(self):
        model = ProductReadModel()
        product_id = uuid4()
        model.project(ProductCreatedEvent(
            aggregate_id=product_id,
            metadata={
                "name": "Widget",
                "description": "A widget",
                "price": "19.99",
                "sku": "WIDGET-001",
            },
        ))
        model.project(ProductUpdatedEvent(
            aggregate_id=product_id,
            metadata={"price": "29.99"},
        ))
        product = model.get(product_id)
        assert product["price"] == "29.99"

    def test_get_not_found(self):
        model = ProductReadModel()
        assert model.get(uuid4()) is None

    def test_list_filter_by_category(self):
        model = ProductReadModel()
        for i in range(3):
            model.project(ProductCreatedEvent(
                aggregate_id=uuid4(),
                metadata={
                    "name": f"Tool {i}",
                    "category": "Tools",
                    "price": "10.00",
                    "sku": f"TOOL-{i}",
                },
            ))
        model.project(ProductCreatedEvent(
            aggregate_id=uuid4(),
            metadata={
                "name": "Gadget",
                "category": "Electronics",
                "price": "50.00",
                "sku": "GADGET-001",
            },
        ))
        results = model.list(category="Electronics")
        assert len(results) == 1


# ============================================================
# Write Model (Aggregate) Tests
# ============================================================


class TestOrderAggregate:
    def test_create(self):
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        customer_id = uuid4()
        items = [{"product_id": "123", "quantity": 2}]
        aggregate.create(customer_id, items, "USD", "Test order")
        assert aggregate.id == order_id
        assert len(aggregate.uncommitted_events()) == 1
        assert isinstance(aggregate.uncommitted_events()[0], OrderCreatedEvent)

    def test_update(self):
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        aggregate.create(uuid4(), [{"product_id": "123", "quantity": 1}], "USD")
        aggregate.mark_committed()
        aggregate.update(items=[{"product_id": "456", "quantity": 3}])
        assert len(aggregate.uncommitted_events()) == 1
        assert isinstance(aggregate.uncommitted_events()[0], OrderUpdatedEvent)

    def test_cancel(self):
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        aggregate.create(uuid4(), [{"product_id": "123", "quantity": 1}], "USD")
        aggregate.mark_committed()
        aggregate.cancel("Customer request")
        assert len(aggregate.uncommitted_events()) == 1
        assert isinstance(aggregate.uncommitted_events()[0], OrderCancelledEvent)

    def test_apply_created_event(self):
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        event = OrderCreatedEvent(
            aggregate_id=order_id,
            metadata={
                "customer_id": str(uuid4()),
                "items": [{"product_id": "123", "quantity": 1}],
                "currency": "USD",
            },
        )
        aggregate.apply(event)
        assert aggregate._status == "pending"
        assert aggregate._version == 1

    def test_apply_cancelled_event(self):
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        aggregate.create(uuid4(), [], "USD")
        event = OrderCancelledEvent(
            aggregate_id=order_id,
            metadata={"reason": "Test"},
        )
        aggregate.apply(event)
        assert aggregate._status == "cancelled"
        assert aggregate._version == 2

    def test_mark_committed(self):
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        aggregate.create(uuid4(), [], "USD")
        assert len(aggregate.uncommitted_events()) == 1
        aggregate.mark_committed()
        assert len(aggregate.uncommitted_events()) == 0


class TestCustomerAggregate:
    def test_create(self):
        customer_id = uuid4()
        aggregate = CustomerAggregate(customer_id)
        aggregate.create("John Doe", "john@example.com", "+1234567890")
        assert aggregate.id == customer_id
        assert len(aggregate.uncommitted_events()) == 1
        assert isinstance(aggregate.uncommitted_events()[0], CustomerCreatedEvent)

    def test_update(self):
        customer_id = uuid4()
        aggregate = CustomerAggregate(customer_id)
        aggregate.create("John", "john@example.com")
        aggregate.mark_committed()
        aggregate.update(name="John Updated")
        assert len(aggregate.uncommitted_events()) == 1
        assert isinstance(aggregate.uncommitted_events()[0], CustomerUpdatedEvent)

    def test_apply_created_event(self):
        customer_id = uuid4()
        aggregate = CustomerAggregate(customer_id)
        event = CustomerCreatedEvent(
            aggregate_id=customer_id,
            metadata={"name": "John", "email": "john@example.com"},
        )
        aggregate.apply(event)
        assert aggregate._name == "John"
        assert aggregate._version == 1

    def test_mark_committed(self):
        customer_id = uuid4()
        aggregate = CustomerAggregate(customer_id)
        aggregate.create("John", "john@example.com")
        assert len(aggregate.uncommitted_events()) == 1
        aggregate.mark_committed()
        assert len(aggregate.uncommitted_events()) == 0


class TestProductAggregate:
    def test_create(self):
        product_id = uuid4()
        aggregate = ProductAggregate(product_id)
        aggregate.create("Widget", "A widget", "19.99", "WIDGET-001", "Tools")
        assert aggregate.id == product_id
        assert len(aggregate.uncommitted_events()) == 1
        assert isinstance(aggregate.uncommitted_events()[0], ProductCreatedEvent)

    def test_update(self):
        product_id = uuid4()
        aggregate = ProductAggregate(product_id)
        aggregate.create("Widget", "A widget", "19.99", "WIDGET-001")
        aggregate.mark_committed()
        aggregate.update(price="29.99")
        assert len(aggregate.uncommitted_events()) == 1
        assert isinstance(aggregate.uncommitted_events()[0], ProductUpdatedEvent)

    def test_apply_created_event(self):
        product_id = uuid4()
        aggregate = ProductAggregate(product_id)
        event = ProductCreatedEvent(
            aggregate_id=product_id,
            metadata={
                "name": "Widget",
                "description": "A widget",
                "price": "19.99",
                "sku": "WIDGET-001",
            },
        )
        aggregate.apply(event)
        assert aggregate._name == "Widget"
        assert aggregate._version == 1

    def test_mark_committed(self):
        product_id = uuid4()
        aggregate = ProductAggregate(product_id)
        aggregate.create("Widget", "A widget", "19.99", "WIDGET-001")
        assert len(aggregate.uncommitted_events()) == 1
        aggregate.mark_committed()
        assert len(aggregate.uncommitted_events()) == 0


# ============================================================
# Event Handler Tests
# ============================================================


class TestOrderCreatedHandler:
    @pytest.mark.asyncio
    async def test_handle(self):
        read_model = {}
        handler = OrderCreatedHandler(read_model)
        order_id = uuid4()
        event = OrderCreatedEvent(
            aggregate_id=order_id,
            metadata={
                "customer_id": str(uuid4()),
                "items": [{"product_id": "123", "quantity": 1}],
                "currency": "USD",
            },
        )
        await handler.handle(event)
        assert order_id in read_model
        assert read_model[order_id]["status"] == "pending"


class TestOrderUpdatedHandler:
    @pytest.mark.asyncio
    async def test_handle_existing_order(self):
        order_id = uuid4()
        read_model = {
            order_id: {
                "order_id": str(order_id),
                "items": [{"product_id": "123", "quantity": 1}],
                "status": "pending",
            }
        }
        handler = OrderUpdatedHandler(read_model)
        event = OrderUpdatedEvent(
            aggregate_id=order_id,
            metadata={"items": [{"product_id": "456", "quantity": 3}]},
        )
        await handler.handle(event)
        assert read_model[order_id]["items"] == [{"product_id": "456", "quantity": 3}]

    @pytest.mark.asyncio
    async def test_handle_nonexistent_order(self):
        read_model = {}
        handler = OrderUpdatedHandler(read_model)
        event = OrderUpdatedEvent(
            aggregate_id=uuid4(),
            metadata={"items": []},
        )
        await handler.handle(event)
        assert len(read_model) == 0


class TestOrderCancelledHandler:
    @pytest.mark.asyncio
    async def test_handle_existing_order(self):
        order_id = uuid4()
        read_model = {
            order_id: {"order_id": str(order_id), "status": "pending"}
        }
        handler = OrderCancelledHandler(read_model)
        event = OrderCancelledEvent(
            aggregate_id=order_id,
            metadata={"reason": "Test"},
        )
        await handler.handle(event)
        assert read_model[order_id]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_handle_nonexistent_order(self):
        read_model = {}
        handler = OrderCancelledHandler(read_model)
        event = OrderCancelledEvent(
            aggregate_id=uuid4(),
            metadata={"reason": "Test"},
        )
        await handler.handle(event)
        assert len(read_model) == 0


class TestCustomerCreatedHandler:
    @pytest.mark.asyncio
    async def test_handle(self):
        read_model = {}
        handler = CustomerCreatedHandler(read_model)
        customer_id = uuid4()
        event = CustomerCreatedEvent(
            aggregate_id=customer_id,
            metadata={"name": "John", "email": "john@example.com"},
        )
        await handler.handle(event)
        assert customer_id in read_model
        assert read_model[customer_id]["name"] == "John"


class TestCustomerUpdatedHandler:
    @pytest.mark.asyncio
    async def test_handle_existing_customer(self):
        customer_id = uuid4()
        read_model = {
            customer_id: {
                "customer_id": str(customer_id),
                "name": "John",
                "email": "john@example.com",
            }
        }
        handler = CustomerUpdatedHandler(read_model)
        event = CustomerUpdatedEvent(
            aggregate_id=customer_id,
            metadata={"name": "John Updated"},
        )
        await handler.handle(event)
        assert read_model[customer_id]["name"] == "John Updated"

    @pytest.mark.asyncio
    async def test_handle_nonexistent_customer(self):
        read_model = {}
        handler = CustomerUpdatedHandler(read_model)
        event = CustomerUpdatedEvent(
            aggregate_id=uuid4(),
            metadata={"name": "Test"},
        )
        await handler.handle(event)
        assert len(read_model) == 0


class TestProductCreatedHandler:
    @pytest.mark.asyncio
    async def test_handle(self):
        read_model = {}
        handler = ProductCreatedHandler(read_model)
        product_id = uuid4()
        event = ProductCreatedEvent(
            aggregate_id=product_id,
            metadata={
                "name": "Widget",
                "description": "A widget",
                "price": "19.99",
                "sku": "WIDGET-001",
            },
        )
        await handler.handle(event)
        assert product_id in read_model
        assert read_model[product_id]["name"] == "Widget"


class TestProductUpdatedHandler:
    @pytest.mark.asyncio
    async def test_handle_existing_product(self):
        product_id = uuid4()
        read_model = {
            product_id: {
                "product_id": str(product_id),
                "name": "Widget",
                "price": "19.99",
            }
        }
        handler = ProductUpdatedHandler(read_model)
        event = ProductUpdatedEvent(
            aggregate_id=product_id,
            metadata={"price": "29.99"},
        )
        await handler.handle(event)
        assert read_model[product_id]["price"] == "29.99"

    @pytest.mark.asyncio
    async def test_handle_nonexistent_product(self):
        read_model = {}
        handler = ProductUpdatedHandler(read_model)
        event = ProductUpdatedEvent(
            aggregate_id=uuid4(),
            metadata={"price": "10.00"},
        )
        await handler.handle(event)
        assert len(read_model) == 0


# ============================================================
# Event Store Tests
# ============================================================


class TestInMemoryEventStore:
    @pytest.mark.asyncio
    async def test_append_and_get(self, event_store):
        aggregate_id = uuid4()
        events = [
            OrderCreatedEvent(aggregate_id=aggregate_id, metadata={}),
        ]
        await event_store.append(aggregate_id, events)
        stored = await event_store.get_events(aggregate_id)
        assert len(stored) == 1
        assert stored[0].aggregate_id == aggregate_id

    @pytest.mark.asyncio
    async def test_append_multiple(self, event_store):
        aggregate_id = uuid4()
        events = [
            OrderCreatedEvent(aggregate_id=aggregate_id, metadata={}),
            OrderUpdatedEvent(aggregate_id=aggregate_id, metadata={}),
        ]
        await event_store.append(aggregate_id, events)
        stored = await event_store.get_events(aggregate_id)
        assert len(stored) == 2

    @pytest.mark.asyncio
    async def test_concurrency_error(self, event_store):
        aggregate_id = uuid4()
        await event_store.append(aggregate_id, [OrderCreatedEvent(aggregate_id=aggregate_id)])
        with pytest.raises(ConcurrencyError):
            await event_store.append(
                aggregate_id,
                [OrderUpdatedEvent(aggregate_id=aggregate_id)],
                expected_version=0,
            )

    @pytest.mark.asyncio
    async def test_get_all_events(self, event_store):
        for _ in range(3):
            aggregate_id = uuid4()
            await event_store.append(
                aggregate_id,
                [OrderCreatedEvent(aggregate_id=aggregate_id)],
            )
        all_events = await event_store.get_all_events()
        assert len(all_events) == 3

    @pytest.mark.asyncio
    async def test_get_events_by_type(self, event_store):
        aggregate_id = uuid4()
        await event_store.append(
            aggregate_id,
            [
                OrderCreatedEvent(aggregate_id=aggregate_id),
                OrderUpdatedEvent(aggregate_id=aggregate_id),
            ],
        )
        created_events = await event_store.get_events_by_type("OrderCreated")
        assert len(created_events) == 1

    @pytest.mark.asyncio
    async def test_clear(self, event_store):
        aggregate_id = uuid4()
        await event_store.append(
            aggregate_id,
            [OrderCreatedEvent(aggregate_id=aggregate_id)],
        )
        event_store.clear()
        all_events = await event_store.get_all_events()
        assert len(all_events) == 0


# ============================================================
# Repository Tests
# ============================================================


class TestRepository:
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, event_store):
        repo = Repository(event_store, OrderAggregate)
        with pytest.raises(AggregateNotFoundError):
            await repo.get_by_id(uuid4())

    @pytest.mark.asyncio
    async def test_save_and_get(self, event_store):
        repo = Repository(event_store, OrderAggregate)
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        aggregate.create(uuid4(), [{"product_id": "123", "quantity": 1}], "USD")
        await repo.save(aggregate)
        loaded = await repo.get_by_id(order_id)
        assert loaded.id == order_id
        assert loaded._status == "pending"

    @pytest.mark.asyncio
    async def test_exists_true(self, event_store):
        repo = Repository(event_store, OrderAggregate)
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        aggregate.create(uuid4(), [], "USD")
        await repo.save(aggregate)
        assert await repo.exists(order_id) is True

    @pytest.mark.asyncio
    async def test_exists_false(self, event_store):
        repo = Repository(event_store, OrderAggregate)
        assert await repo.exists(uuid4()) is False

    @pytest.mark.asyncio
    async def test_save_no_uncommitted(self, event_store):
        repo = Repository(event_store, OrderAggregate)
        order_id = uuid4()
        aggregate = OrderAggregate(order_id)
        await repo.save(aggregate)
        assert await repo.exists(order_id) is False


# ============================================================
# CQRS Bus Tests
# ============================================================


class TestCQRSBus:
    @pytest.mark.asyncio
    async def test_send_command(self, bus):
        handler = CreateOrderHandler()
        bus.register_command_handler(CreateOrderCommand, handler)
        customer_id = uuid4()
        command = CreateOrderCommand(
            customer_id=customer_id,
            items=[{"product_id": "123", "quantity": 1}],
            currency="USD",
        )
        events = await bus.send(command)
        assert len(events) == 1
        assert isinstance(events[0], OrderCreatedEvent)

    @pytest.mark.asyncio
    async def test_send_command_no_handler(self, bus):
        command = CreateOrderCommand(
            customer_id=uuid4(),
            items=[{"product_id": "123", "quantity": 1}],
            currency="USD",
        )
        with pytest.raises(HandlerNotFoundError):
            await bus.send(command)

    @pytest.mark.asyncio
    async def test_query(self, bus):
        order_id = uuid4()
        read_model = {order_id: {"order_id": str(order_id), "status": "pending"}}
        handler = GetOrderHandler(read_model)
        bus.register_query_handler(GetOrderQuery, handler)
        query = GetOrderQuery(order_id=order_id)
        result = await bus.query(query)
        assert result is not None
        assert result["order_id"] == str(order_id)

    @pytest.mark.asyncio
    async def test_query_no_handler(self, bus):
        query = GetOrderQuery(order_id=uuid4())
        with pytest.raises(HandlerNotFoundError):
            await bus.query(query)

    @pytest.mark.asyncio
    async def test_publish_event(self, bus):
        read_model = {}
        handler = OrderCreatedHandler(read_model)
        bus.register_event_handler(OrderCreatedEvent, handler)
        order_id = uuid4()
        event = OrderCreatedEvent(
            aggregate_id=order_id,
            metadata={
                "customer_id": str(uuid4()),
                "items": [],
                "currency": "USD",
            },
        )
        await bus.publish(event)
        assert order_id in read_model

    @pytest.mark.asyncio
    async def test_publish_no_handlers(self, bus):
        event = OrderCreatedEvent(aggregate_id=uuid4(), metadata={})
        await bus.publish(event)

    @pytest.mark.asyncio
    async def test_publish_all(self, bus):
        read_model = {}
        handler = OrderCreatedHandler(read_model)
        bus.register_event_handler(OrderCreatedEvent, handler)
        events = [
            OrderCreatedEvent(aggregate_id=uuid4(), metadata={}),
            OrderCreatedEvent(aggregate_id=uuid4(), metadata={}),
        ]
        await bus.publish_all(events)
        assert len(read_model) == 2

    @pytest.mark.asyncio
    async def test_multiple_event_handlers(self, bus):
        read_model1 = {}
        read_model2 = {}
        handler1 = OrderCreatedHandler(read_model1)
        handler2 = OrderCreatedHandler(read_model2)
        bus.register_event_handler(OrderCreatedEvent, handler1)
        bus.register_event_handler(OrderCreatedEvent, handler2)
        order_id = uuid4()
        event = OrderCreatedEvent(aggregate_id=order_id, metadata={})
        await bus.publish(event)
        assert order_id in read_model1
        assert order_id in read_model2
