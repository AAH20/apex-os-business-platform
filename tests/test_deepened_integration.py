"""Tests for deepened integration modules: webhooks, API keys, marketplace, data mapping, analytics."""
import pytest
import json
import hmac
import hashlib
from unittest.mock import MagicMock, patch, call


class TestWebhooks:
    """Test webhook delivery."""

    def test_send_webhook(self):
        from apex_os_bp.integration.deepened import WebhookManager
        mgr = WebhookManager()
        with patch("apex_os.integration.webhooks.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            result = mgr.send("https://example.com/hook", {"event": "test"})
            assert result is True

    def test_webhook_signature(self):
        from apex_os_bp.integration.deepened import WebhookManager
        mgr = WebhookManager(secret="mysecret")
        sig = mgr.sign_payload('{"key":"val"}')
        assert sig is not None
        assert len(sig) > 0

    def test_webhook_signature_verification(self):
        from apex_os_bp.integration.deepened import WebhookManager
        mgr = WebhookManager(secret="mysecret")
        payload = '{"key":"val"}'
        sig = mgr.sign_payload(payload)
        assert mgr.verify_signature(payload, sig) is True

    def test_webhook_retry(self):
        from apex_os_bp.integration.deepened import WebhookManager
        mgr = WebhookManager(max_retries=3)
        with patch("apex_os.integration.webhooks.requests.post") as mock_post:
            mock_post.return_value.status_code = 500
            result = mgr.send("https://example.com/hook", {"event": "test"})
            assert result is False
            assert mock_post.call_count == 3


class TestAPIKeys:
    """Test API key management."""

    def test_generate_key(self):
        from apex_os_bp.integration.deepened import APIKeyManager
        mgr = APIKeyManager()
        key = mgr.generate(user_id=1, name="test-key")
        assert key is not None
        assert len(key) > 20

    def test_validate_key(self):
        from apex_os_bp.integration.deepened import APIKeyManager
        mgr = APIKeyManager()
        key = mgr.generate(user_id=1, name="test")
        assert mgr.validate(key) is True

    def test_revoke_key(self):
        from apex_os_bp.integration.deepened import APIKeyManager
        mgr = APIKeyManager()
        key = mgr.generate(user_id=1, name="test")
        mgr.revoke(key)
        assert mgr.validate(key) is False

    def test_key_scopes(self):
        from apex_os_bp.integration.deepened import APIKeyManager
        mgr = APIKeyManager()
        key = mgr.generate(user_id=1, name="scoped", scopes=["read", "write"])
        info = mgr.get_info(key)
        assert "read" in info["scopes"]
        assert "write" in info["scopes"]


class TestMarketplace:
    """Test marketplace integration."""

    def test_list_listings(self):
        from apex_os_bp.integration.deepened import Marketplace
        mkt = Marketplace()
        listings = mkt.list_listings()
        assert isinstance(listings, list)

    def test_create_listing(self):
        from apex_os_bp.integration.deepened import Marketplace
        mkt = Marketplace()
        listing = mkt.create_listing(title="Test", price=9.99)
        assert listing["title"] == "Test"
        assert listing["price"] == 9.99

    def test_search_listings(self):
        from apex_os_bp.integration.deepened import Marketplace
        mkt = Marketplace()
        mkt.create_listing(title="Widget", price=5.0)
        mkt.create_listing(title="Gadget", price=10.0)
        results = mkt.search("Widget")
        assert len(results) >= 1


class TestDataMapping:
    """Test data mapping/transformation."""

    def test_field_mapping(self):
        from apex_os_bp.integration.deepened import DataMapper
        mapper = DataMapper()
        mapper.map("first_name", "firstName")
        result = mapper.transform({"first_name": "Alice"})
        assert result == {"firstName": "Alice"}

    def test_nested_mapping(self):
        from apex_os_bp.integration.deepened import DataMapper
        mapper = DataMapper()
        mapper.map("user.name", "name")
        result = mapper.transform({"user": {"name": "Bob"}})
        assert result == {"name": "Bob"}

    def test_default_value(self):
        from apex_os_bp.integration.deepened import DataMapper
        mapper = DataMapper()
        mapper.map("missing", "output", default="N/A")
        result = mapper.transform({})
        assert result == {"output": "N/A"}

    def test_type_conversion(self):
        from apex_os_bp.integration.deepened import DataMapper
        mapper = DataMapper()
        mapper.map("age", "age", convert=int)
        result = mapper.transform({"age": "25"})
        assert result["age"] == 25


class TestIntegrationAnalytics:
    """Test integration analytics."""

    def test_track_request(self):
        from apex_os_bp.integration.deepened import IntegrationAnalytics
        analytics = IntegrationAnalytics()
        analytics.track_request(integration="stripe", status="success")
        assert analytics.request_count("stripe") == 1

    def test_track_error(self):
        from apex_os_bp.integration.deepened import IntegrationAnalytics
        analytics = IntegrationAnalytics()
        analytics.track_error(integration="stripe", error_type="timeout")
        assert analytics.error_count("stripe") == 1

    def test_success_rate(self):
        from apex_os_bp.integration.deepened import IntegrationAnalytics
        analytics = IntegrationAnalytics()
        analytics.track_request(integration="shopify", status="success")
        analytics.track_request(integration="shopify", status="success")
        analytics.track_error(integration="shopify", error_type="500")
        assert analytics.success_rate("shopify") == pytest.approx(0.667, 0.01)
