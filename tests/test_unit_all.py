"""
Comprehensive unit tests for APEX-OS Business Platform.
Covers: utilities, data models, API clients, CRUD operations, validation.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
import json
import re

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

class TestUtilityFunctions:
    """Test all utility functions."""

    def test_string_slugify(self):
        """Test string slugification."""
        from utils.string_utils import slugify
        assert slugify("Hello World") == "hello-world"
        assert slugify("  Spaces  ") == "spaces"
        assert slugify("Special!@#Chars") == "specialchars"
        assert slugify("") == ""

    def test_string_camel_to_snake(self):
        """Test camelCase to snake_case conversion."""
        from utils.string_utils import camel_to_snake
        assert camel_to_snake("camelCase") == "camel_case"
        assert camel_to_snake("PascalCase") == "pascal_case"
        assert camel_to_snake("simple") == "simple"
        assert camel_to_snake("ABCDef") == "abc_def"

    def test_string_snake_to_camel(self):
        """Test snake_case to camelCase conversion."""
        from utils.string_utils import snake_to_camel
        assert snake_to_camel("snake_case") == "snakeCase"
        assert snake_to_camel("simple") == "simple"
        assert snake_to_camel("multiple_words_here") == "multipleWordsHere"

    def test_string_truncate(self):
        """Test string truncation."""
        from utils.string_utils import truncate
        assert truncate("Hello World", 5) == "Hello..."
        assert truncate("Hi", 10) == "Hi"
        assert truncate("", 5) == ""

    def test_date_format_iso(self):
        """Test ISO date formatting."""
        from utils.date_utils import format_iso
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert format_iso(dt) == "2024-01-15T10:30:00"

    def test_date_parse_iso(self):
        """Test ISO date parsing."""
        from utils.date_utils import parse_iso
        result = parse_iso("2024-01-15T10:30:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_date_days_between(self):
        """Test days between dates calculation."""
        from utils.date_utils import days_between
        d1 = date(2024, 1, 1)
        d2 = date(2024, 1, 15)
        assert days_between(d1, d2) == 14

    def test_date_add_days(self):
        """Test adding days to date."""
        from utils.date_utils import add_days
        d = date(2024, 1, 1)
        result = add_days(d, 10)
        assert result == date(2024, 1, 11)

    def test_currency_format(self):
        """Test currency formatting."""
        from utils.currency_utils import format_currency
        assert format_currency(Decimal("1234.56"), "USD") == "$1,234.56"
        assert format_currency(Decimal("0"), "USD") == "$0.00"

    def test_currency_parse(self):
        """Test currency parsing."""
        from utils.currency_utils import parse_currency
        assert parse_currency("$1,234.56") == Decimal("1234.56")
        assert parse_currency("0.00") == Decimal("0")

    def test_email_validate(self):
        """Test email validation."""
        from utils.validation_utils import is_valid_email
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("invalid") is False
        assert is_valid_email("") is False
        assert is_valid_email("test@") is False

    def test_phone_validate(self):
        """Test phone number validation."""
        from utils.validation_utils import is_valid_phone
        assert is_valid_phone("+1234567890") is True
        assert is_valid_phone("123") is False
        assert is_valid_phone("") is False

    def test_uuid_generate(self):
        """Test UUID generation."""
        from utils.id_utils import generate_uuid
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert uuid1 != uuid2
        assert len(uuid1) == 36

    def test_hash_password(self):
        """Test password hashing."""
        from utils.security_utils import hash_password, verify_password
        hashed = hash_password("secret123")
        assert hashed != "secret123"
        assert verify_password("secret123", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_sanitize_input(self):
        """Test input sanitization."""
        from utils.security_utils import sanitize_input
        assert sanitize_input("<script>alert('xss')</script>") == "&lt;script&gt;alert('xss')&lt;/script&gt;"
        assert sanitize_input("normal") == "normal"

    def test_deep_merge(self):
        """Test deep dictionary merge."""
        from utils.dict_utils import deep_merge
        a = {"x": 1, "nested": {"a": 1}}
        b = {"y": 2, "nested": {"b": 2}}
        result = deep_merge(a, b)
        assert result == {"x": 1, "y": 2, "nested": {"a": 1, "b": 2}}

    def test_chunk_list(self):
        """Test list chunking."""
        from utils.list_utils import chunk_list
        assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
        assert chunk_list([], 2) == []


# ============================================================================
# DATA MODELS
# ============================================================================

class TestDataModels:
    """Test all data models."""

    def test_user_model_creation(self):
        """Test User model creation."""
        from models.user import User
        user = User(id="u1", email="test@example.com", name="Test User")
        assert user.id == "u1"
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    def test_user_model_validation(self):
        """Test User model validation."""
        from models.user import User
        with pytest.raises(ValueError):
            User(id="u1", email="invalid-email", name="Test")

    def test_product_model_creation(self):
        """Test Product model creation."""
        from models.product import Product
        product = Product(
            id="p1", name="Widget", price=Decimal("19.99"),
            sku="WGT-001", quantity=100
        )
        assert product.id == "p1"
        assert product.name == "Widget"
        assert product.price == Decimal("19.99")

    def test_product_model_validation(self):
        """Test Product model validation."""
        from models.product import Product
        with pytest.raises(ValueError):
            Product(id="p1", name="", price=Decimal("-1"), sku="", quantity=-1)

    def test_order_model_creation(self):
        """Test Order model creation."""
        from models.order import Order, OrderItem
        items = [OrderItem(product_id="p1", quantity=2, price=Decimal("10.00"))]
        order = Order(id="o1", user_id="u1", items=items, status="pending")
        assert order.id == "o1"
        assert len(order.items) == 1
        assert order.status == "pending"

    def test_order_total_calculation(self):
        """Test Order total calculation."""
        from models.order import Order, OrderItem
        items = [
            OrderItem(product_id="p1", quantity=2, price=Decimal("10.00")),
            OrderItem(product_id="p2", quantity=1, price=Decimal("25.00")),
        ]
        order = Order(id="o1", user_id="u1", items=items)
        assert order.total == Decimal("45.00")

    def test_order_status_transitions(self):
        """Test Order status transition validation."""
        from models.order import Order, OrderItem
        order = Order(id="o1", user_id="u1", items=[], status="pending")
        assert order.can_transition_to("confirmed") is True
        assert order.can_transition_to("shipped") is False

    def test_customer_model_creation(self):
        """Test Customer model creation."""
        from models.customer import Customer
        customer = Customer(
            id="c1", name="Acme Corp", email="contact@acme.com",
            phone="+1234567890", tier="enterprise"
        )
        assert customer.id == "c1"
        assert customer.tier == "enterprise"

    def test_customer_tier_validation(self):
        """Test Customer tier validation."""
        from models.customer import Customer
        with pytest.raises(ValueError):
            Customer(id="c1", name="Test", email="t@t.com", tier="invalid")

    def test_invoice_model_creation(self):
        """Test Invoice model creation."""
        from models.invoice import Invoice
        invoice = Invoice(
            id="inv1", order_id="o1", amount=Decimal("100.00"),
            status="unpaid", due_date=date(2024, 2, 1)
        )
        assert invoice.id == "inv1"
        assert invoice.status == "unpaid"

    def test_invoice_status_validation(self):
        """Test Invoice status validation."""
        from models.invoice import Invoice
        with pytest.raises(ValueError):
            Invoice(id="inv1", order_id="o1", amount=Decimal("100"), status="invalid")

    def test_inventory_model_creation(self):
        """Test Inventory model creation."""
        from models.inventory import Inventory
        inv = Inventory(product_id="p1", warehouse_id="w1", quantity=50)
        assert inv.product_id == "p1"
        assert inv.quantity == 50

    def test_inventory_reserve(self):
        """Test inventory reservation."""
        from models.inventory import Inventory
        inv = Inventory(product_id="p1", warehouse_id="w1", quantity=50)
        assert inv.reserve(10) is True
        assert inv.available == 40
        assert inv.reserved == 10

    def test_inventory_reserve_insufficient(self):
        """Test inventory reservation with insufficient stock."""
        from models.inventory import Inventory
        inv = Inventory(product_id="p1", warehouse_id="w1", quantity=5)
        assert inv.reserve(10) is False

    def test_notification_model_creation(self):
        """Test Notification model creation."""
        from models.notification import Notification
        notif = Notification(
            id="n1", user_id="u1", type="order_update",
            message="Your order has shipped", read=False
        )
        assert notif.id == "n1"
        assert notif.read is False

    def test_audit_log_model_creation(self):
        """Test AuditLog model creation."""
        from models.audit_log import AuditLog
        log = AuditLog(
            id="a1", action="user.created", user_id="u1",
            resource_type="user", resource_id="u1", timestamp=datetime.now()
        )
        assert log.action == "user.created"


# ============================================================================
# API CLIENT METHODS
# ============================================================================

class TestApiClient:
    """Test all API client methods."""

    @pytest.fixture
    def mock_response(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": "test"}
        return response

    @pytest.mark.asyncio
    async def test_api_client_get(self, mock_response):
        """Test API client GET request."""
        from api.client import ApiClient
        client = ApiClient(base_url="https://api.example.com")
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            result = await client.get("/users")
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_api_client_post(self, mock_response):
        """Test API client POST request."""
        from api.client import ApiClient
        client = ApiClient(base_url="https://api.example.com")
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await client.post("/users", json={"name": "Test"})
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_api_client_put(self, mock_response):
        """Test API client PUT request."""
        from api.client import ApiClient
        client = ApiClient(base_url="https://api.example.com")
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_response
            )
            result = await client.put("/users/1", json={"name": "Updated"})
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_api_client_delete(self, mock_response):
        """Test API client DELETE request."""
        from api.client import ApiClient
        client = ApiClient(base_url="https://api.example.com")
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.delete = AsyncMock(
                return_value=mock_response
            )
            result = await client.delete("/users/1")
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_api_client_auth_header(self):
        """Test API client authentication header."""
        from api.client import ApiClient
        client = ApiClient(base_url="https://api.example.com", token="secret")
        assert client.headers["Authorization"] == "Bearer secret"

    @pytest.mark.asyncio
    async def test_api_client_error_handling(self):
        """Test API client error handling."""
        from api.client import ApiClient, ApiError
        client = ApiClient(base_url="https://api.example.com")
        error_response = Mock()
        error_response.status_code = 404
        error_response.json.return_value = {"error": "Not found"}
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=error_response
            )
            with pytest.raises(ApiError):
                await client.get("/nonexistent")

    @pytest.mark.asyncio
    async def test_api_client_timeout(self):
        """Test API client timeout handling."""
        from api.client import ApiClient, ApiTimeoutError
        client = ApiClient(base_url="https://api.example.com", timeout=0.001)
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            with pytest.raises(ApiTimeoutError):
                await client.get("/slow-endpoint")

    @pytest.mark.asyncio
    async def test_api_client_retry(self):
        """Test API client retry logic."""
        from api.client import ApiClient
        client = ApiClient(base_url="https://api.example.com", max_retries=3)
        fail_response = Mock()
        fail_response.status_code = 500
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "ok"}
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[fail_response, fail_response, success_response]
            )
            result = await client.get("/flaky")
            assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_api_client_pagination(self):
        """Test API client pagination."""
        from api.client import ApiClient
        client = ApiClient(base_url="https://api.example.com")
        page1 = Mock()
        page1.status_code = 200
        page1.json.return_value = {"data": [1, 2], "next": "page2"}
        page2 = Mock()
        page2.status_code = 200
        page2.json.return_value = {"data": [3, 4], "next": None}
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[page1, page2]
            )
            results = []
            async for item in client.paginate("/items"):
                results.append(item)
            assert results == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_api_client_rate_limit(self):
        """Test API client rate limiting."""
        from api.client import ApiClient, RateLimitError
        client = ApiClient(base_url="https://api.example.com")
        rate_response = Mock()
        rate_response.status_code = 429
        rate_response.headers = {"Retry-After": "60"}
        with patch("api.client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=rate_response
            )
            with pytest.raises(RateLimitError):
                await client.get("/limited")


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

class TestCrudOperations:
    """Test all CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.find = AsyncMock(return_value=[])
        db.find_one = AsyncMock(return_value=None)
        db.insert = AsyncMock(return_value=Mock(inserted_id="123"))
        db.update = AsyncMock(return_value=Mock(modified_count=1))
        db.delete = AsyncMock(return_value=Mock(deleted_count=1))
        return db

    @pytest.mark.asyncio
    async def test_crud_create(self, mock_db):
        """Test CRUD create operation."""
        from crud.base import BaseCrud
        crud = BaseCrud(mock_db, "users")
        result = await crud.create({"name": "Test", "email": "test@example.com"})
        assert result["inserted_id"] == "123"
        mock_db.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_crud_get_by_id(self, mock_db):
        """Test CRUD get by ID operation."""
        from crud.base import BaseCrud
        mock_db.find_one.return_value = {"_id": "123", "name": "Test"}
        crud = BaseCrud(mock_db, "users")
        result = await crud.get_by_id("123")
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_crud_get_all(self, mock_db):
        """Test CRUD get all operation."""
        from crud.base import BaseCrud
        mock_db.find.return_value = [
            {"_id": "1", "name": "User1"},
            {"_id": "2", "name": "User2"},
        ]
        crud = BaseCrud(mock_db, "users")
        result = await crud.get_all()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_crud_update(self, mock_db):
        """Test CRUD update operation."""
        from crud.base import BaseCrud
        crud = BaseCrud(mock_db, "users")
        result = await crud.update("123", {"name": "Updated"})
        assert result["modified_count"] == 1
        mock_db.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_crud_delete(self, mock_db):
        """Test CRUD delete operation."""
        from crud.base import BaseCrud
        crud = BaseCrud(mock_db, "users")
        result = await crud.delete("123")
        assert result["deleted_count"] == 1
        mock_db.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_crud_find_one(self, mock_db):
        """Test CRUD find one operation."""
        from crud.base import BaseCrud
        mock_db.find_one.return_value = {"_id": "123", "name": "Test"}
        crud = BaseCrud(mock_db, "users")
        result = await crud.find_one({"name": "Test"})
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_crud_find_many(self, mock_db):
        """Test CRUD find many operation."""
        from crud.base import BaseCrud
        mock_db.find.return_value = [{"_id": "1"}, {"_id": "2"}]
        crud = BaseCrud(mock_db, "users")
        result = await crud.find_many({"status": "active"})
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_crud_count(self, mock_db):
        """Test CRUD count operation."""
        from crud.base import BaseCrud
        mock_db.count = AsyncMock(return_value=42)
        crud = BaseCrud(mock_db, "users")
        result = await crud.count({"status": "active"})
        assert result == 42

    @pytest.mark.asyncio
    async def test_crud_exists(self, mock_db):
        """Test CRUD exists operation."""
        from crud.base import BaseCrud
        mock_db.find_one.return_value = {"_id": "123"}
        crud = BaseCrud(mock_db, "users")
        result = await crud.exists("123")
        assert result is True

    @pytest.mark.asyncio
    async def test_crud_bulk_create(self, mock_db):
        """Test CRUD bulk create operation."""
        from crud.base import BaseCrud
        mock_db.insert_many = AsyncMock(return_value=Mock(inserted_ids=["1", "2"]))
        crud = BaseCrud(mock_db, "users")
        result = await crud.bulk_create([{"name": "A"}, {"name": "B"}])
        assert len(result["inserted_ids"]) == 2

    @pytest.mark.asyncio
    async def test_crud_bulk_update(self, mock_db):
        """Test CRUD bulk update operation."""
        from crud.base import BaseCrud
        mock_db.update_many = AsyncMock(return_value=Mock(modified_count=5))
        crud = BaseCrud(mock_db, "users")
        result = await crud.bulk_update({"status": "active"}, {"last_seen": "2024-01-01"})
        assert result["modified_count"] == 5

    @pytest.mark.asyncio
    async def test_crud_bulk_delete(self, mock_db):
        """Test CRUD bulk delete operation."""
        from crud.base import BaseCrud
        mock_db.delete_many = AsyncMock(return_value=Mock(deleted_count=3))
        crud = BaseCrud(mock_db, "users")
        result = await crud.bulk_delete({"status": "inactive"})
        assert result["deleted_count"] == 3

    @pytest.mark.asyncio
    async def test_crud_search(self, mock_db):
        """Test CRUD search operation."""
        from crud.base import BaseCrud
        mock_db.find.return_value = [{"_id": "1", "name": "Test User"}]
        crud = BaseCrud(mock_db, "users")
        result = await crud.search("Test")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_crud_get_or_create(self, mock_db):
        """Test CRUD get or create operation."""
        from crud.base import BaseCrud
        mock_db.find_one.return_value = None
        crud = BaseCrud(mock_db, "users")
        result = await crud.get_or_create({"email": "test@example.com"}, {"name": "Test"})
        assert result["inserted_id"] == "123"

    @pytest.mark.asyncio
    async def test_crud_update_or_create(self, mock_db):
        """Test CRUD update or create operation."""
        from crud.base import BaseCrud
        mock_db.find_one.return_value = {"_id": "123", "name": "Old"}
        crud = BaseCrud(mock_db, "users")
        result = await crud.update_or_create({"email": "test@example.com"}, {"name": "New"})
        assert result["modified_count"] == 1


# ============================================================================
# VALIDATION LOGIC
# ============================================================================

class TestValidationLogic:
    """Test all validation logic."""

    def test_validate_required_fields(self):
        """Test required field validation."""
        from validators.common import validate_required
        data = {"name": "Test", "email": "test@example.com"}
        assert validate_required(data, ["name", "email"]) is True
        with pytest.raises(ValueError):
            validate_required(data, ["name", "phone"])

    def test_validate_email_format(self):
        """Test email format validation."""
        from validators.common import validate_email
        assert validate_email("test@example.com") is True
        assert validate_email("invalid") is False

    def test_validate_phone_format(self):
        """Test phone format validation."""
        from validators.common import validate_phone
        assert validate_phone("+1234567890") is True
        assert validate_phone("123") is False

    def test_validate_password_strength(self):
        """Test password strength validation."""
        from validators.common import validate_password
        assert validate_password("StrongP@ss1") is True
        assert validate_password("weak") is False

    def test_validate_min_length(self):
        """Test minimum length validation."""
        from validators.common import validate_min_length
        assert validate_min_length("hello", 3) is True
        assert validate_min_length("hi", 3) is False

    def test_validate_max_length(self):
        """Test maximum length validation."""
        from validators.common import validate_max_length
        assert validate_max_length("hi", 5) is True
        assert validate_max_length("hello world", 5) is False

    def test_validate_range(self):
        """Test numeric range validation."""
        from validators.common import validate_range
        assert validate_range(5, 1, 10) is True
        assert validate_range(15, 1, 10) is False

    def test_validate_date_range(self):
        """Test date range validation."""
        from validators.common import validate_date_range
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        assert validate_date_range(date(2024, 6, 15), start, end) is True
        assert validate_date_range(date(2025, 1, 1), start, end) is False

    def test_validate_unique(self):
        """Test uniqueness validation."""
        from validators.common import validate_unique
        existing = [{"email": "a@test.com"}, {"email": "b@test.com"}]
        assert validate_unique(existing, "email", "c@test.com") is True
        assert validate_unique(existing, "email", "a@test.com") is False

    def test_validate_json_schema(self):
        """Test JSON schema validation."""
        from validators.common import validate_json_schema
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        assert validate_json_schema({"name": "Test"}, schema) is True
        assert validate_json_schema({"name": 123}, schema) is False

    def test_validate_url(self):
        """Test URL validation."""
        from validators.common import validate_url
        assert validate_url("https://example.com") is True
        assert validate_url("not-a-url") is False

    def test_validate_uuid(self):
        """Test UUID validation."""
        from validators.common import validate_uuid
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert validate_uuid("not-a-uuid") is False

    def test_validate_credit_card(self):
        """Test credit card validation."""
        from validators.common import validate_credit_card
        assert validate_credit_card("4111111111111111") is True
        assert validate_credit_card("1234567890123456") is False

    def test_validate_postal_code(self):
        """Test postal code validation."""
        from validators.common import validate_postal_code
        assert validate_postal_code("12345") is True
        assert validate_postal_code("1234") is False

    def test_validate_currency_code(self):
        """Test currency code validation."""
        from validators.common import validate_currency_code
        assert validate_currency_code("USD") is True
        assert validate_currency_code("INVALID") is False

    def test_validate_order_items(self):
        """Test order items validation."""
        from validators.order import validate_order_items
        items = [{"product_id": "p1", "quantity": 2, "price": "10.00"}]
        assert validate_order_items(items) is True
        with pytest.raises(ValueError):
            validate_order_items([])

    def test_validate_order_total(self):
        """Test order total validation."""
        from validators.order import validate_order_total
        items = [{"price": "10.00", "quantity": 2}]
        assert validate_order_total(items, "20.00") is True
        with pytest.raises(ValueError):
            validate_order_total(items, "15.00")

    def test_validate_product_sku(self):
        """Test product SKU validation."""
        from validators.product import validate_sku
        assert validate_sku("PROD-001") is True
        assert validate_sku("") is False

    def test_validate_inventory_quantity(self):
        """Test inventory quantity validation."""
        from validators.inventory import validate_quantity
        assert validate_quantity(10) is True
        assert validate_quantity(-1) is False

    def test_validate_user_role(self):
        """Test user role validation."""
        from validators.user import validate_role
        assert validate_role("admin") is True
        assert validate_role("superuser") is False

    def test_validate_discount_code(self):
        """Test discount code validation."""
        from validators.discount import validate_discount_code
        assert validate_discount_code("SAVE20") is True
        assert validate_discount_code("") is False

    def test_validate_discount_percentage(self):
        """Test discount percentage validation."""
        from validators.discount import validate_percentage
        assert validate_percentage(20) is True
        assert validate_percentage(150) is False

    def test_validate_shipping_address(self):
        """Test shipping address validation."""
        from validators.address import validate_shipping_address
        address = {
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US"
        }
        assert validate_shipping_address(address) is True
        with pytest.raises(ValueError):
            validate_shipping_address({"street": "123 Main St"})

    def test_validate_tax_rate(self):
        """Test tax rate validation."""
        from validators.tax import validate_tax_rate
        assert validate_tax_rate(Decimal("0.08")) is True
        assert validate_tax_rate(Decimal("1.5")) is False

    def test_validate_webhook_url(self):
        """Test webhook URL validation."""
        from validators.webhook import validate_webhook_url
        assert validate_webhook_url("https://example.com/webhook") is True
        assert validate_webhook_url("http://insecure.com") is False

    def test_validate_api_key(self):
        """Test API key validation."""
        from validators.api import validate_api_key
        assert validate_api_key("ak_live_1234567890abcdef") is True
        assert validate_api_key("invalid") is False

    def test_validate_pagination_params(self):
        """Test pagination parameter validation."""
        from validators.common import validate_pagination
        assert validate_pagination(1, 20) is True
        assert validate_pagination(0, 20) is False
        assert validate_pagination(1, 200) is False

    def test_validate_sort_field(self):
        """Test sort field validation."""
        from validators.common import validate_sort_field
        allowed = ["name", "created_at", "price"]
        assert validate_sort_field("name", allowed) is True
        assert validate_sort_field("password", allowed) is False

    def test_validate_filter_operators(self):
        """Test filter operator validation."""
        from validators.common import validate_filter_operator
        assert validate_filter_operator("eq") is True
        assert validate_filter_operator("invalid") is False

    def test_validate_file_upload(self):
        """Test file upload validation."""
        from validators.file import validate_file_upload
        file = Mock()
        file.filename = "test.pdf"
        file.content_type = "application/pdf"
        file.size = 1024
        assert validate_file_upload(file, ["application/pdf"], 2048) is True
        assert validate_file_upload(file, ["image/png"], 2048) is False

    def test_validate_batch_size(self):
        """Test batch size validation."""
        from validators.common import validate_batch_size
        assert validate_batch_size(100) is True
        assert validate_batch_size(0) is False
        assert validate_batch_size(10000) is False
