"""
Comprehensive unit tests for all APEX-OS Business Platform modules.
Covers: utilities, data models, API clients, CRUD operations, validation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import json
import re


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

class TestUtilities:
    """Test all utility functions."""

    def test_generate_uuid(self):
        """Test UUID generation produces valid unique IDs."""
        from utils.helpers import generate_uuid
        id1 = generate_uuid()
        id2 = generate_uuid()
        assert id1 != id2
        assert len(id1) == 36
        assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', id1)

    def test_hash_password(self):
        """Test password hashing produces consistent results with salt."""
        from utils.security import hash_password, verify_password
        password = "SecureP@ss123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_sanitize_string(self):
        """Test string sanitization removes dangerous characters."""
        from utils.helpers import sanitize_string
        assert sanitize_string("hello world") == "hello world"
        assert sanitize_string("<script>alert(1)</script>") == "alert1"
        assert sanitize_string("  spaces  ") == "spaces"

    def test_format_currency(self):
        """Test currency formatting."""
        from utils.helpers import format_currency
        assert format_currency(Decimal("1234.56")) == "$1,234.56"
        assert format_currency(Decimal("0")) == "$0.00"
        assert format_currency(Decimal("-50.5")) == "-$50.50"

    def test_parse_date(self):
        """Test date parsing from various formats."""
        from utils.helpers import parse_date
        assert parse_date("2024-01-15") == datetime(2024, 1, 15)
        assert parse_date("01/15/2024") == datetime(2024, 1, 15)
        assert parse_date("invalid") is None

    def test_truncate_string(self):
        """Test string truncation with ellipsis."""
        from utils.helpers import truncate_string
        assert truncate_string("short", 10) == "short"
        assert truncate_string("this is a long string", 10) == "this is..."
        assert truncate_string("exact", 5) == "exact"

    def test_deep_merge(self):
        """Test deep dictionary merging."""
        from utils.helpers import deep_merge
        dict1 = {"a": 1, "b": {"c": 2, "d": 3}}
        dict2 = {"b": {"c": 99}, "e": 4}
        result = deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": {"c": 99, "d": 3}, "e": 4}

    def test_chunk_list(self):
        """Test list chunking."""
        from utils.helpers import chunk_list
        data = list(range(10))
        chunks = list(chunk_list(data, 3))
        assert len(chunks) == 4
        assert chunks[0] == [0, 1, 2]
        assert chunks[-1] == [9]

    def test_retry_with_backoff(self):
        """Test retry mechanism with exponential backoff."""
        from utils.helpers import retry_with_backoff
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"

        assert flaky() == "success"
        assert call_count == 3

    def test_rate_limiter(self):
        """Test rate limiting logic."""
        from utils.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        assert limiter.allow_request("key1") is True
        assert limiter.allow_request("key1") is True
        assert limiter.allow_request("key1") is False
        assert limiter.allow_request("key2") is True

    def test_cache_ttl(self):
        """Test TTL cache behavior."""
        from utils.cache import TTLCache
        cache = TTLCache(ttl_seconds=1)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        cache.delete("key")
        assert cache.get("key") is None


# ============================================================================
# DATA MODELS
# ============================================================================

class TestDataModels:
    """Test all data model definitions and behaviors."""

    def test_user_model(self):
        """Test User model creation and validation."""
        from models.user import User
        user = User(id="u1", email="test@example.com", name="Test User", role="admin")
        assert user.id == "u1"
        assert user.email == "test@example.com"
        assert user.role == "admin"
        assert user.is_active is True
        assert user.created_at is not None

    def test_user_model_validation(self):
        """Test User model validation rules."""
        from models.user import User
        with pytest.raises(ValueError):
            User(id="u1", email="invalid-email", name="Test", role="admin")

    def test_product_model(self):
        """Test Product model."""
        from models.product import Product
        product = Product(
            id="p1", name="Widget", price=Decimal("29.99"),
            sku="WDG-001", stock=100, category="electronics"
        )
        assert product.name == "Widget"
        assert product.price == Decimal("29.99")
        assert product.stock == 100
        assert product.is_available is True

    def test_product_model_stock_check(self):
        """Test Product stock availability logic."""
        from models.product import Product
        product = Product(id="p1", name="Widget", price=Decimal("10.00"),
                        sku="W-1", stock=0, category="test")
        assert product.is_available is False

    def test_order_model(self):
        """Test Order model with line items."""
        from models.order import Order, OrderItem
        items = [OrderItem(product_id="p1", quantity=2, unit_price=Decimal("10.00"))]
        order = Order(id="o1", customer_id="c1", items=items, status="pending")
        assert order.total == Decimal("20.00")
        assert order.status == "pending"
        assert len(order.items) == 1

    def test_order_status_transitions(self):
        """Test Order status transition validation."""
        from models.order import Order, OrderItem
        order = Order(id="o1", customer_id="c1",
                     items=[OrderItem(product_id="p1", quantity=1, unit_price=Decimal("10.00"))])
        assert order.can_transition_to("confirmed") is True
        assert order.can_transition_to("shipped") is False
        order.status = "confirmed"
        assert order.can_transition_to("shipped") is True

    def test_customer_model(self):
        """Test Customer model."""
        from models.customer import Customer
        customer = Customer(
            id="c1", name="John Doe", email="john@example.com",
            phone="+1234567890", tier="premium"
        )
        assert customer.tier == "premium"
        assert customer.total_orders == 0

    def test_customer_tier_upgrade(self):
        """Test Customer tier upgrade logic."""
        from models.customer import Customer
        customer = Customer(id="c1", name="John", email="j@example.com",
                          phone="123", tier="basic")
        customer.total_spent = Decimal("5000.00")
        customer.update_tier()
        assert customer.tier == "gold"

    def test_inventory_model(self):
        """Test Inventory model."""
        from models.inventory import Inventory
        inv = Inventory(product_id="p1", warehouse_id="w1", quantity=50, reserved=10)
        assert inv.available == 40
        inv.reserve(5)
        assert inv.reserved == 15
        assert inv.available == 35

    def test_inventory_insufficient_stock(self):
        """Test Inventory raises on over-reservation."""
        from models.inventory import Inventory
        inv = Inventory(product_id="p1", warehouse_id="w1", quantity=5, reserved=0)
        with pytest.raises(ValueError):
            inv.reserve(10)

    def test_payment_model(self):
        """Test Payment model."""
        from models.payment import Payment
        payment = Payment(
            id="pay1", order_id="o1", amount=Decimal("100.00"),
            method="credit_card", status="completed"
        )
        assert payment.status == "completed"
        assert payment.amount == Decimal("100.00")

    def test_notification_model(self):
        """Test Notification model."""
        from models.notification import Notification
        notif = Notification(
            id="n1", user_id="u1", type="order_update",
            message="Your order has shipped", read=False
        )
        assert notif.read is False
        notif.mark_read()
        assert notif.read is True

    def test_audit_log_model(self):
        """Test AuditLog model."""
        from models.audit_log import AuditLog
        log = AuditLog(
            id="a1", action="user.login", user_id="u1",
            details={"ip": "127.0.0.1"}, timestamp=datetime.utcnow()
        )
        assert log.action == "user.login"
        assert log.details["ip"] == "127.0.0.1"


# ============================================================================
# API CLIENT METHODS
# ============================================================================

class TestAPIClients:
    """Test all API client methods with mocked HTTP."""

    @pytest.fixture
    def mock_response(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": "test"}
        response.raise_for_status = Mock()
        return response

    @pytest.mark.asyncio
    async def test_http_client_get(self, mock_response):
        """Test HTTP client GET request."""
        from api.http_client import HTTPClient
        with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            client = HTTPClient(base_url="https://api.example.com")
            result = await client.get("/test")
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_http_client_post(self, mock_response):
        """Test HTTP client POST request."""
        from api.http_client import HTTPClient
        with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            client = HTTPClient(base_url="https://api.example.com")
            result = await client.post("/test", json={"key": "value"})
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_http_client_put(self, mock_response):
        """Test HTTP client PUT request."""
        from api.http_client import HTTPClient
        with patch("aiohttp.ClientSession.put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value.__aenter__.return_value = mock_response
            client = HTTPClient(base_url="https://api.example.com")
            result = await client.put("/test/1", json={"key": "updated"})
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_http_client_delete(self, mock_response):
        """Test HTTP client DELETE request."""
        from api.http_client import HTTPClient
        with patch("aiohttp.ClientSession.delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value.__aenter__.return_value = mock_response
            client = HTTPClient(base_url="https://api.example.com")
            result = await client.delete("/test/1")
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_http_client_error_handling(self):
        """Test HTTP client handles errors gracefully."""
        from api.http_client import HTTPClient, APIError
        with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = Exception("Not found")
            mock_get.return_value.__aenter__.return_value = mock_response
            client = HTTPClient(base_url="https://api.example.com")
            with pytest.raises(APIError):
                await client.get("/missing")

    @pytest.mark.asyncio
    async def test_http_client_timeout(self):
        """Test HTTP client timeout handling."""
        from api.http_client import HTTPClient, APITimeoutError
        with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()
            client = HTTPClient(base_url="https://api.example.com", timeout=1)
            with pytest.raises(APITimeoutError):
                await client.get("/slow")

    @pytest.mark.asyncio
    async def test_http_client_retry(self):
        """Test HTTP client retry on failure."""
        from api.http_client import HTTPClient
        with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
            fail_resp = Mock()
            fail_resp.status_code = 500
            fail_resp.raise_for_status = Mock()
            ok_resp = Mock()
            ok_resp.status_code = 200
            ok_resp.json.return_value = {"ok": True}
            ok_resp.raise_for_status = Mock()
            mock_get.return_value.__aenter__.side_effect = [fail_resp, ok_resp]
            client = HTTPClient(base_url="https://api.example.com", max_retries=2)
            result = await client.get("/retry")
            assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_auth_client_token_refresh(self):
        """Test auth client token refresh."""
        from api.auth_client import AuthClient
        with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mock_post:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"access_token": "new_token", "expires_in": 3600}
            mock_resp.raise_for_status = Mock()
            mock_post.return_value.__aenter__.return_value = mock_resp
            client = AuthClient(base_url="https://auth.example.com")
            token = await client.refresh_token("refresh123")
            assert token == "new_token"

    @pytest.mark.asyncio
    async def test_webhook_client_signature(self):
        """Test webhook signature verification."""
        from api.webhook_client import WebhookClient
        client = WebhookClient(secret="webhook_secret")
        payload = b'{"event": "order.created"}'
        signature = client.sign_payload(payload)
        assert client.verify_signature(payload, signature) is True
        assert client.verify_signature(payload, "invalid") is False


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

class TestCRUDOperations:
    """Test all CRUD operations with mocked database."""

    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.execute = AsyncMock()
        db.fetchone = AsyncMock()
        db.fetchall = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_create_user(self, mock_db):
        """Test user creation."""
        from crud.user_crud import UserCRUD
        mock_db.execute.return_value = "u1"
        crud = UserCRUD(mock_db)
        result = await crud.create({"email": "new@example.com", "name": "New User"})
        assert result == "u1"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, mock_db):
        """Test user retrieval by ID."""
        from crud.user_crud import UserCRUD
        mock_db.fetchone.return_value = {"id": "u1", "email": "test@example.com"}
        crud = UserCRUD(mock_db)
        result = await crud.get_by_id("u1")
        assert result["id"] == "u1"
        assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_db):
        """Test user retrieval returns None when not found."""
        from crud.user_crud import UserCRUD
        mock_db.fetchone.return_value = None
        crud = UserCRUD(mock_db)
        result = await crud.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_users_pagination(self, mock_db):
        """Test user listing with pagination."""
        from crud.user_crud import UserCRUD
        mock_db.fetchall.return_value = [{"id": f"u{i}"} for i in range(10)]
        crud = UserCRUD(mock_db)
        result = await crud.list(page=1, per_page=10)
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_update_user(self, mock_db):
        """Test user update."""
        from crud.user_crud import UserCRUD
        mock_db.execute.return_value = 1
        crud = UserCRUD(mock_db)
        result = await crud.update("u1", {"name": "Updated Name"})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_user(self, mock_db):
        """Test user deletion."""
        from crud.user_crud import UserCRUD
        mock_db.execute.return_value = 1
        crud = UserCRUD(mock_db)
        result = await crud.delete("u1")
        assert result is True

    @pytest.mark.asyncio
    async def test_create_product(self, mock_db):
        """Test product creation."""
        from crud.product_crud import ProductCRUD
        mock_db.execute.return_value = "p1"
        crud = ProductCRUD(mock_db)
        result = await crud.create({"name": "New Product", "price": 19.99})
        assert result == "p1"

    @pytest.mark.asyncio
    async def test_product_search(self, mock_db):
        """Test product search with filters."""
        from crud.product_crud import ProductCRUD
        mock_db.fetchall.return_value = [{"id": "p1", "name": "Widget"}]
        crud = ProductCRUD(mock_db)
        result = await crud.search(query="widget", category="electronics")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_order(self, mock_db):
        """Test order creation with items."""
        from crud.order_crud import OrderCRUD
        mock_db.execute.return_value = "o1"
        crud = OrderCRUD(mock_db)
        result = await crud.create({
            "customer_id": "c1",
            "items": [{"product_id": "p1", "quantity": 2, "unit_price": 10.00}]
        })
        assert result == "o1"

    @pytest.mark.asyncio
    async def test_order_update_status(self, mock_db):
        """Test order status update."""
        from crud.order_crud import OrderCRUD
        mock_db.execute.return_value = 1
        crud = OrderCRUD(mock_db)
        result = await crud.update_status("o1", "confirmed")
        assert result is True

    @pytest.mark.asyncio
    async def test_inventory_adjustment(self, mock_db):
        """Test inventory quantity adjustment."""
        from crud.inventory_crud import InventoryCRUD
        mock_db.execute.return_value = 1
        crud = InventoryCRUD(mock_db)
        result = await crud.adjust_quantity("p1", "w1", delta=-5)
        assert result is True

    @pytest.mark.asyncio
    async def test_bulk_insert(self, mock_db):
        """Test bulk insert operation."""
        from crud.base_crud import BaseCRUD
        mock_db.execute.return_value = 5
        crud = BaseCRUD(mock_db, table="test_table")
        rows = [{"name": f"item{i}"} for i in range(5)]
        result = await crud.bulk_insert(rows)
        assert result == 5

    @pytest.mark.asyncio
    async def test_soft_delete(self, mock_db):
        """Test soft delete sets deleted_at."""
        from crud.base_crud import BaseCRUD
        mock_db.execute.return_value = 1
        crud = BaseCRUD(mock_db, table="test_table")
        result = await crud.soft_delete("id1")
        assert result is True


# ============================================================================
# VALIDATION LOGIC
# ============================================================================

class TestValidation:
    """Test all validation logic."""

    def test_email_validation(self):
        """Test email format validation."""
        from validation.validators import validate_email
        assert validate_email("test@example.com") is True
        assert validate_email("user.name+tag@domain.co") is True
        assert validate_email("invalid") is False
        assert validate_email("@domain.com") is False
        assert validate_email("user@") is False

    def test_phone_validation(self):
        """Test phone number validation."""
        from validation.validators import validate_phone
        assert validate_phone("+1234567890") is True
        assert validate_phone("+44 20 7946 0958") is True
        assert validate_phone("123") is False
        assert validate_phone("abc-def-ghij") is False

    def test_password_strength(self):
        """Test password strength validation."""
        from validation.validators import validate_password_strength
        assert validate_password_strength("StrongP@ss1") is True
        assert validate_password_strength("weak") is False
        assert validate_password_strength("nouppercase1!") is False
        assert validate_password_strength("NOLOWERCASE1!") is False
        assert validate_password_strength("NoDigits!@#") is False
        assert validate_password_strength("NoSpecial123") is False

    def test_sku_format(self):
        """Test SKU format validation."""
        from validation.validators import validate_sku
        assert validate_sku("WDG-001") is True
        assert validate_sku("ABC123") is True
        assert validate_sku("") is False
        assert validate_sku("invalid sku!") is False

    def test_price_range(self):
        """Test price range validation."""
        from validation.validators import validate_price
        assert validate_price(Decimal("0.01")) is True
        assert validate_price(Decimal("999999.99")) is True
        assert validate_price(Decimal("0")) is False
        assert validate_price(Decimal("-10")) is False
        assert validate_price(Decimal("1000000")) is False

    def test_quantity_validation(self):
        """Test quantity validation."""
        from validation.validators import validate_quantity
        assert validate_quantity(1) is True
        assert validate_quantity(1000) is True
        assert validate_quantity(0) is False
        assert validate_quantity(-5) is False

    def test_date_range_validation(self):
        """Test date range validation."""
        from validation.validators import validate_date_range
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        assert validate_date_range(start, end) is True
        assert validate_date_range(end, start) is False
        assert validate_date_range(start, start) is False

    def test_order_items_validation(self):
        """Test order items validation."""
        from validation.validators import validate_order_items
        valid_items = [{"product_id": "p1", "quantity": 1, "unit_price": 10.00}]
        assert validate_order_items(valid_items) is True
        assert validate_order_items([]) is False
        assert validate_order_items([{"product_id": "", "quantity": 1}]) is False

    def test_pagination_params(self):
        """Test pagination parameter validation."""
        from validation.validators import validate_pagination
        assert validate_pagination(page=1, per_page=10) == (1, 10)
        assert validate_pagination(page=0, per_page=10) == (1, 10)
        assert validate_pagination(page=1, per_page=200) == (1, 100)
        assert validate_pagination(page=-1, per_page=-5) == (1, 20)

    def test_required_fields(self):
        """Test required fields validation."""
        from validation.validators import validate_required_fields
        data = {"name": "Test", "email": "test@example.com"}
        assert validate_required_fields(data, ["name", "email"]) is True
        assert validate_required_fields(data, ["name", "phone"]) is False

    def test_string_length_validation(self):
        """Test string length validation."""
        from validation.validators import validate_string_length
        assert validate_string_length("hello", min_len=1, max_len=10) is True
        assert validate_string_length("", min_len=1, max_len=10) is False
        assert validate_string_length("this is too long", min_len=1, max_len=5) is False

    def test_enum_validation(self):
        """Test enum value validation."""
        from validation.validators import validate_enum
        assert validate_enum("admin", ["admin", "user", "guest"]) is True
        assert validate_enum("superuser", ["admin", "user", "guest"]) is False

    def test_json_schema_validation(self):
        """Test JSON schema validation."""
        from validation.validators import validate_json_schema
        schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
        assert validate_json_schema({"name": "Test"}, schema) is True
        assert validate_json_schema({"name": 123}, schema) is False
        assert validate_json_schema({}, schema) is False

    def test_url_validation(self):
        """Test URL format validation."""
        from validation.validators import validate_url
        assert validate_url("https://example.com") is True
        assert validate_url("http://localhost:8080/path") is True
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://files.example.com") is False

    def test_uuid_validation(self):
        """Test UUID format validation."""
        from validation.validators import validate_uuid
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert validate_uuid("not-a-uuid") is False
        assert validate_uuid("") is False

    def test_decimal_precision(self):
        """Test decimal precision validation."""
        from validation.validators import validate_decimal_precision
        assert validate_decimal_precision(Decimal("10.99"), max_digits=5, decimal_places=2) is True
        assert validate_decimal_precision(Decimal("10.999"), max_digits=5, decimal_places=2) is False
        assert validate_decimal_precision(Decimal("10000.00"), max_digits=5, decimal_places=2) is False


# ============================================================================
# INTEGRATION-STYLE UNIT TESTS
# ============================================================================

class TestModuleInteractions:
    """Test interactions between modules."""

    @pytest.mark.asyncio
    async def test_order_creation_updates_inventory(self):
        """Test that creating an order updates inventory."""
        from services.order_service import OrderService
        mock_db = Mock()
        mock_db.transaction = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.fetchone = AsyncMock(return_value={"stock": 100})
        service = OrderService(mock_db)
        with patch.object(service, '_reserve_inventory', new_callable=AsyncMock) as mock_reserve:
            mock_reserve.return_value = True
            result = await service.create_order({"customer_id": "c1", "items": []})
            mock_reserve.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_deactivation_cancels_orders(self):
        """Test that deactivating a user cancels pending orders."""
        from services.user_service import UserService
        mock_db = Mock()
        mock_db.execute = AsyncMock()
        service = UserService(mock_db)
        with patch.object(service, '_cancel_pending_orders', new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = 3
            result = await service.deactivate_user("u1")
            mock_cancel.assert_called_once_with("u1")

    @pytest.mark.asyncio
    async def test_payment_completes_order(self):
        """Test that payment completion updates order status."""
        from services.payment_service import PaymentService
        mock_db = Mock()
        mock_db.execute = AsyncMock()
        service = PaymentService(mock_db)
        with patch.object(service, '_complete_order', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = True
            result = await service.process_payment({"order_id": "o1", "amount": 100})
            mock_complete.assert_called_once_with("o1")

    @pytest.mark.asyncio
    async def test_low_stock_triggers_notification(self):
        """Test that low stock triggers a notification."""
        from services.inventory_service import InventoryService
        mock_db = Mock()
        mock_db.execute = AsyncMock()
        mock_db.fetchone = AsyncMock(return_value={"quantity": 2, "reorder_point": 5})
        service = InventoryService(mock_db)
        with patch.object(service, '_send_low_stock_alert', new_callable=AsyncMock) as mock_alert:
            await service.check_stock_level("p1")
            mock_alert.assert_called_once_with("p1")


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_concurrent_modification(self):
        """Test handling of concurrent modification conflicts."""
        from crud.base_crud import BaseCRUD
        mock_db = Mock()
        mock_db.execute = AsyncMock(side_effect=Exception("Concurrent modification"))
        crud = BaseCRUD(mock_db, table="test")
        with pytest.raises(Exception, match="Concurrent"):
            await crud.update("id", {"field": "value"})

    @pytest.mark.asyncio
    async def test_empty_result_set(self):
        """Test handling of empty result sets."""
        from crud.base_crud import BaseCRUD
        mock_db = Mock()
        mock_db.fetchall = AsyncMock(return_value=[])
        crud = BaseCRUD(mock_db, table="test")
        result = await crud.list()
        assert result == []

    def test_none_input_handling(self):
        """Test that None inputs are handled gracefully."""
        from utils.helpers import sanitize_string, truncate_string
        assert sanitize_string(None) == ""
        assert truncate_string(None, 10) == ""

    def test_very_large_input(self):
        """Test handling of very large inputs."""
        from utils.helpers import truncate_string
        large = "x" * 100000
        result = truncate_string(large, 100)
        assert len(result) == 103  # 100 + "..."

    def test_unicode_handling(self):
        """Test unicode string handling."""
        from utils.helpers import sanitize_string, validate_email
        assert sanitize_string("héllo wörld") == "héllo wörld"
        assert validate_email("user@münchen.de") is True

    def test_sql_injection_prevention(self):
        """Test that inputs are sanitized against SQL injection."""
        from utils.helpers import sanitize_string
        malicious = "'; DROP TABLE users; --"
        result = sanitize_string(malicious)
        assert "DROP" not in result
        assert ";" not in result


# ============================================================================
# PERFORMANCE AND RESOURCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance-related logic."""

    def test_caching_reduces_calls(self):
        """Test that caching reduces redundant calls."""
        from utils.cache import TTLCache
        cache = TTLCache(ttl_seconds=60)
        call_count = 0

        def expensive():
            nonlocal call_count
            call_count += 1
            return "result"

        # First call
        if not cache.get("key"):
            cache.set("key", expensive())
        # Second call should use cache
        if not cache.get("key"):
            cache.set("key", expensive())

        assert call_count == 1

    def test_batch_processing(self):
        """Test batch processing of large datasets."""
        from utils.helpers import chunk_list
        data = list(range(1000))
        chunks = list(chunk_list(data, 100))
        assert len(chunks) == 10
        assert sum(len(c) for c in chunks) == 1000

    def test_rate_limiter_blocks_excess(self):
        """Test rate limiter blocks excess requests."""
        from utils.rate_limiter import RateLimiter
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        results = [limiter.allow_request("key") for _ in range(10)]
        assert sum(results) == 5
        assert results[:5] == [True] * 5
        assert results[5:] == [False] * 5


# ============================================================================
# SECURITY TESTS
# ============================================================================

class TestSecurity:
    """Test security-related functionality."""

    def test_password_never_stored_plaintext(self):
        """Test passwords are never stored in plaintext."""
        from utils.security import hash_password
        password = "MySecret123!"
        hashed = hash_password(password)
        assert password not in hashed
        assert hashed != password
        assert len(hashed) > 50

    def test_token_expiration(self):
        """Test token expiration logic."""
        from utils.security import is_token_expired
        past = datetime.utcnow() - timedelta(hours=1)
        future = datetime.utcnow() + timedelta(hours=1)
        assert is_token_expired(past) is True
        assert is_token_expired(future) is False

    def test_input_sanitization_xss(self):
        """Test XSS prevention in input sanitization."""
        from utils.helpers import sanitize_string
        xss = '<script>alert("xss")</script>'
        result = sanitize_string(xss)
        assert "<script>" not in result
        assert "alert" in result  # text content preserved

    def test_sensitive_data_masking(self):
        """Test sensitive data masking."""
        from utils.security import mask_sensitive_data
        assert mask_sensitive_data("1234567890123456") == "************3456"
        assert mask_sensitive_data("test@example.com") == "t***@example.com"
        assert mask_sensitive_data("short") == "***"


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestConfiguration:
    """Test configuration and settings."""

    def test_default_settings(self):
        """Test default configuration values."""
        from config.settings import Settings
        settings = Settings()
        assert settings.debug is False
        assert settings.database_url is not None
        assert settings.secret_key is not None

    def test_environment_override(self):
        """Test environment variable overrides."""
        import os
        os.environ["APEX_DEBUG"] = "true"
        from config.settings import Settings
        settings = Settings()
        assert settings.debug is True
        del os.environ["APEX_DEBUG"]

    def test_database_url_parsing(self):
        """Test database URL parsing."""
        from config.settings import parse_database_url
        result = parse_database_url("postgresql://user:pass@host:5432/dbname")
        assert result["user"] == "user"
        assert result["password"] == "pass"
        assert result["host"] == "host"
        assert result["port"] == 5432
        assert result["database"] == "dbname"


# ============================================================================
# LOGGING AND MONITORING TESTS
# ============================================================================

class TestLogging:
    """Test logging and monitoring functionality."""

    def test_structured_logging(self):
        """Test structured log formatting."""
        from utils.logging import format_log_entry
        entry = format_log_entry("test_event", {"key": "value"}, level="INFO")
        assert "test_event" in entry
        assert "key" in entry
        assert "value" in entry

    def test_log_sanitization(self):
        """Test that logs sanitize sensitive data."""
        from utils.logging import sanitize_log_data
        data = {"password": "secret", "username": "user", "token": "abc123"}
        result = sanitize_log_data(data)
        assert result["password"] == "***"
        assert result["token"] == "***"
        assert result["username"] == "user"

    def test_metrics_collection(self):
        """Test metrics collection."""
        from utils.metrics import MetricsCollector
        collector = MetricsCollector()
        collector.increment("requests")
        collector.increment("requests")
        collector.record_latency("db_query", 0.05)
        assert collector.get_count("requests") == 2
        assert collector.get_avg_latency("db_query") == 0.05


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
